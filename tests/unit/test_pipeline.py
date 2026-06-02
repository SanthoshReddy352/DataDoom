"""Pipeline-level behavior: stages, clamping record, derived-feature guard."""

from __future__ import annotations

import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.errors import SpecValidationError


def _numeric_spec(**feat):
    return parse_spec(
        {
            "datadoom_version": "1",
            "name": "p",
            "rows": 5000,
            "seed": 1,
            "features": {"x": {"type": "numeric", "dist": "normal", **feat}},
        }
    )


def test_clamping_is_recorded() -> None:
    spec = _numeric_spec(params={"mean": 0, "std": 1}, min=-1, max=1)
    result = generate(spec, seed=1)
    fc = result.compliance.features[0]
    # A standard normal clamped to [-1, 1] truncates ~32% of mass.
    assert fc.clamped_fraction > 0.2
    assert result.frame["x"].min() >= -1 and result.frame["x"].max() <= 1


def test_clamping_marks_ks_not_applicable() -> None:
    # Truncation introduces point masses at the bounds → a continuous KS test
    # would falsely reject. It must be excluded from the score, not failed.
    spec = _numeric_spec(params={"mean": 0, "std": 1}, min=-1, max=1)
    fc = generate(spec, seed=1).compliance.features[0]
    assert fc.applicable is False and fc.passed is None
    # A correct-but-clamped sole feature must not drag compliance to 0.
    assert generate(spec, seed=1).compliance.score == 1.0


def test_no_clamp_continuous_is_ks_applicable() -> None:
    spec = _numeric_spec(params={"mean": 0, "std": 1})
    fc = generate(spec, seed=1).compliance.features[0]
    assert fc.clamped_fraction == 0.0
    assert fc.applicable is True and fc.passed is not None


def test_int_dtype_is_integral_and_ks_not_applicable() -> None:
    # Integer rounding discretizes a continuous target; the continuous KS test
    # is invalid, so it is reported but excluded from the score.
    spec = _numeric_spec(params={"mean": 100, "std": 10}, dtype="int")
    result = generate(spec, seed=1)
    assert str(result.frame["x"].dtype).startswith("int")
    fc = result.compliance.features[0]
    assert fc.applicable is False and fc.passed is None
    # The empirical moments still track the requested target.
    assert abs(fc.empirical["mean"] - 100) < 1.0


def test_derived_numeric_without_dist_or_edge_rejected() -> None:
    # A numeric feature with no dist that is not a causal target is unsamplable.
    with pytest.raises(SpecValidationError) as e:
        parse_spec(
            {
                "datadoom_version": "1",
                "name": "d",
                "rows": 10,
                "features": {"income": {"type": "numeric"}},
            }
        )
    assert e.value.locator == "features.income"


def test_derived_feature_is_computed_by_causal_engine() -> None:
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "d",
            "rows": 200,
            "seed": 1,
            "features": {
                "edu": {"type": "categorical", "categories": ["a", "b"]},
                "income": {"type": "numeric"},  # derived, no dist
            },
            "causal": {"edges": [{"from": "edu", "to": "income", "fn": "map",
                                  "mapping": {"a": 1, "b": 2}}]},
        }
    )
    result = generate(spec, seed=1)
    # income is exactly the map of edu (no noise declared).
    inc = result.frame["income"].to_numpy()
    edu = result.frame["edu"].to_numpy()
    assert set(inc[edu == "a"]) == {1.0}
    assert set(inc[edu == "b"]) == {2.0}


def test_column_order_matches_spec() -> None:
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "o",
            "rows": 5,
            "features": {
                "z": {"type": "boolean", "rate": 0.5},
                "a": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            },
        }
    )
    result = generate(spec, seed=1)
    assert list(result.frame.columns) == ["z", "a"]
