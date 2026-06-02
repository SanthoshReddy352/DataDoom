"""Spec validation: valid specs parse; invalid cases raise with a locator."""

from __future__ import annotations

import pytest

from datadoom.engine.errors import SpecValidationError
from datadoom.engine.spec import parse_spec


def _spec(**overrides):
    base = {
        "datadoom_version": "1",
        "name": "ok",
        "rows": 100,
        "features": {
            "age": {"type": "numeric", "dist": "normal", "params": {"mean": 40, "std": 12}},
            "edu": {"type": "categorical", "categories": ["a", "b"], "weights": [0.5, 0.5]},
        },
    }
    base.update(overrides)
    return base


def test_valid_spec_parses() -> None:
    spec = parse_spec(_spec())
    assert spec.name == "ok"
    assert set(spec.features) == {"age", "edu"}


def test_unsupported_version() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(datadoom_version="99"))
    assert e.value.locator == "datadoom_version"


def test_unknown_distribution() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(features={"a": {"type": "numeric", "dist": "wat", "params": {}}}))
    assert e.value.locator == "features.a.dist"


def test_missing_dist_param() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(features={"a": {"type": "numeric", "dist": "normal", "params": {"mean": 1}}}))
    assert e.value.locator == "features.a.params"


def test_bad_std() -> None:
    with pytest.raises(SpecValidationError):
        parse_spec(_spec(features={"a": {"type": "numeric", "dist": "normal",
                                         "params": {"mean": 1, "std": 0}}}))


def test_weights_length_mismatch() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(features={"c": {"type": "categorical", "categories": ["a", "b"],
                                         "weights": [1.0]}}))
    assert e.value.locator == "features.c.weights"


def test_min_greater_than_max() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(features={"a": {"type": "numeric", "dist": "uniform",
                                         "params": {"low": 0, "high": 1}, "min": 5, "max": 1}}))
    assert e.value.locator == "features.a"


def test_causal_cycle_rejected() -> None:
    spec = _spec(
        features={
            "a": {"type": "numeric"},
            "b": {"type": "numeric"},
        },
        causal={"edges": [{"from": "a", "to": "b", "fn": "identity"},
                          {"from": "b", "to": "a", "fn": "identity"}]},
    )
    with pytest.raises(SpecValidationError) as e:
        parse_spec(spec)
    assert "acyclic" in str(e.value)


def test_valid_multinode_dag_accepted() -> None:
    # a -> b -> c with a -> c is acyclic and must parse. Targets (b, c) are
    # derived (no dist), so there is no sampled/derived ambiguity.
    spec = _spec(
        features={
            "a": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "b": {"type": "numeric"},
            "c": {"type": "numeric"},
        },
        causal={"edges": [
            {"from": "a", "to": "b", "fn": "identity"},
            {"from": "b", "to": "c", "fn": "identity"},
            {"from": "a", "to": "c", "fn": "identity"},
        ]},
    )
    parsed = parse_spec(spec)
    assert set(parsed.features) == {"a", "b", "c"}


def test_self_loop_rejected_as_cycle() -> None:
    # a -> a is the minimal cycle; 'a' is derived so it reaches the cycle check.
    spec = _spec(
        features={"a": {"type": "numeric"}},
        causal={"edges": [{"from": "a", "to": "a", "fn": "identity"}]},
    )
    with pytest.raises(SpecValidationError) as e:
        parse_spec(spec)
    assert "acyclic" in str(e.value)


def test_causal_unknown_reference() -> None:
    spec = _spec(causal={"edges": [{"from": "ghost", "to": "age", "fn": "identity"}]})
    with pytest.raises(SpecValidationError) as e:
        parse_spec(spec)
    assert e.value.locator == "causal.edges[0]"


def test_sampled_and_derived_conflict() -> None:
    # 'age' has a dist AND is a causal target -> ambiguous.
    spec = _spec(
        features={
            "edu": {"type": "categorical", "categories": ["a", "b"]},
            "age": {"type": "numeric", "dist": "normal", "params": {"mean": 1, "std": 1}},
        },
        causal={"edges": [{"from": "edu", "to": "age", "fn": "map", "mapping": {"a": 1, "b": 2}}]},
    )
    with pytest.raises(SpecValidationError) as e:
        parse_spec(spec)
    assert e.value.locator == "features.age"


def test_export_splits_must_sum_to_one() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(export={"splits": {"train": 0.7, "test": 0.2}}))
    assert e.value.locator == "export.splits"


def test_difficulty_label_must_exist() -> None:
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(difficulty={"target": "kaggle", "label": "ghost"}))
    assert e.value.locator == "difficulty.label"


def test_failure_reference_and_rate() -> None:
    with pytest.raises(SpecValidationError):
        parse_spec(_spec(failures=[{"type": "mcar", "column": "ghost", "rate": 0.1}]))
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_spec(failures=[{"type": "mcar", "column": "age", "rate": 1.5}]))
    assert e.value.locator == "failures[0].rate"
