"""Causal engine (P2): SEM execution, structural fns, interventions, true graph.

Covers 17 step 11's test bullets — "coefficient recovery on known DAGs; cycle
rejection; intervention detaches edges" — plus structural-fn validation and the
report's causal_truth section.
"""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.causal import CausalDag, resolve_interventions
from datadoom.engine.causal.graph import CausalEdge
from datadoom.engine.errors import SpecValidationError


def _spec(**overrides):
    base = {
        "datadoom_version": "1",
        "name": "causal",
        "rows": 4000,
        "seed": 7,
        "features": {},
        "causal": {"edges": []},
    }
    base.update(overrides)
    return parse_spec(base)


# --- structural-equation correctness ------------------------------------------------


def test_linear_coefficient_recovery() -> None:
    # y = 3*x + 5 (+ small noise). OLS slope on the realized data ≈ 3.
    spec = _spec(
        features={
            "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 10}},
            "y": {"type": "numeric"},
        },
        causal={
            "edges": [{"from": "x", "to": "y", "fn": "linear", "weight": 3.0, "bias": 5.0}],
            "noise": {"y": {"dist": "normal", "params": {"mean": 0, "std": 1}}},
        },
    )
    df = generate(spec, seed=7).frame
    slope, intercept = np.polyfit(df["x"].to_numpy(), df["y"].to_numpy(), 1)
    assert slope == pytest.approx(3.0, abs=0.05)
    assert intercept == pytest.approx(5.0, abs=0.3)


def test_map_edge_assigns_category_values() -> None:
    spec = _spec(
        features={
            "g": {"type": "categorical", "categories": ["a", "b", "c"]},
            "y": {"type": "numeric"},
        },
        causal={"edges": [{"from": "g", "to": "y", "fn": "map",
                           "mapping": {"a": 1, "b": 2, "c": 3}}]},
    )
    df = generate(spec, seed=7).frame
    for cat, val in (("a", 1.0), ("b", 2.0), ("c", 3.0)):
        assert set(df.loc[df["g"] == cat, "y"]) == {val}


def test_logistic_boolean_child_rate_matches_sigmoid() -> None:
    # Constant parent so the Bernoulli rate is a known sigmoid value.
    spec = _spec(
        features={
            "x": {"type": "numeric", "dist": "uniform", "params": {"low": 1.0, "high": 1.0001}},
            "flag": {"type": "boolean"},
        },
        causal={"edges": [{"from": "x", "to": "flag", "fn": "logistic",
                           "weight": 0.0, "bias": 0.0}]},
    )
    df = generate(spec, seed=7).frame
    # σ(0) = 0.5 → ~half True.
    assert df["flag"].dtype == bool
    assert df["flag"].mean() == pytest.approx(0.5, abs=0.05)


def test_polynomial_edge() -> None:
    # y = 2 + 0*x + 1*x^2
    spec = _spec(
        features={
            "x": {"type": "numeric", "dist": "uniform", "params": {"low": -3, "high": 3}},
            "y": {"type": "numeric"},
        },
        causal={"edges": [{"from": "x", "to": "y", "fn": "polynomial", "coeffs": [2, 0, 1]}]},
    )
    df = generate(spec, seed=7).frame
    expected = 2 + df["x"].to_numpy() ** 2
    assert np.allclose(df["y"].to_numpy(), expected)


def test_multi_parent_contributions_sum() -> None:
    spec = _spec(
        features={
            "a": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "b": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "y": {"type": "numeric"},
        },
        causal={"edges": [
            {"from": "a", "to": "y", "fn": "linear", "weight": 2.0},
            {"from": "b", "to": "y", "fn": "linear", "weight": -1.0},
        ]},
    )
    df = generate(spec, seed=7).frame
    expected = 2.0 * df["a"].to_numpy() - 1.0 * df["b"].to_numpy()
    assert np.allclose(df["y"].to_numpy(), expected)


# --- interventions ------------------------------------------------------------------


def test_intervention_fixes_value_and_propagates() -> None:
    # x -> y -> z. do(y=10): y becomes constant; z is computed from the fixed y.
    spec = _spec(
        features={
            "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "y": {"type": "numeric"},
            "z": {"type": "numeric"},
        },
        causal={
            "edges": [
                {"from": "x", "to": "y", "fn": "linear", "weight": 100.0},
                {"from": "y", "to": "z", "fn": "linear", "weight": 2.0},
            ],
            "interventions": [{"do": {"y": 10}}],
        },
    )
    df = generate(spec, seed=7).frame
    assert set(df["y"]) == {10.0}          # y detached from x, fixed
    assert np.allclose(df["z"].to_numpy(), 20.0)  # z = 2 * 10


def test_resolve_interventions_flattens_do_map() -> None:
    assert resolve_interventions([{"do": {"a": 1}}, {"do": {"b": 2.5}}]) == {"a": 1.0, "b": 2.5}


# --- graph / validation -------------------------------------------------------------


def test_cycle_rejected_at_graph_construction() -> None:
    edges = [CausalEdge(**{"from": "a", "to": "b", "fn": "identity"}),
             CausalEdge(**{"from": "b", "to": "a", "fn": "identity"})]
    with pytest.raises(SpecValidationError):
        CausalDag(edges, ["a", "b"])


def test_topological_order_is_deterministic() -> None:
    edges = [CausalEdge(**{"from": "a", "to": "c", "fn": "identity"}),
             CausalEdge(**{"from": "b", "to": "c", "fn": "identity"})]
    dag = CausalDag(edges, ["a", "b", "c"])
    order = dag.topological_order()
    assert order.index("a") < order.index("c")
    assert order.index("b") < order.index("c")
    assert dag.topological_order() == order  # stable across calls


def test_unknown_structural_fn_rejected() -> None:
    with pytest.raises(SpecValidationError) as e:
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "x", "to": "y", "fn": "wat"}]},
        )
    assert e.value.locator == "causal.edges[0].fn"


def test_linear_edge_missing_weight_rejected() -> None:
    with pytest.raises(SpecValidationError):
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "x", "to": "y", "fn": "linear"}]},
        )


def test_map_edge_must_cover_all_categories() -> None:
    with pytest.raises(SpecValidationError) as e:
        _spec(
            features={"g": {"type": "categorical", "categories": ["a", "b"]},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "g", "to": "y", "fn": "map", "mapping": {"a": 1}}]},
        )
    assert "mapping" in (e.value.locator or "")


def test_map_requires_categorical_parent() -> None:
    # A `map` edge from a numeric parent is a type error, caught at validation.
    with pytest.raises(SpecValidationError) as e:
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "x", "to": "y", "fn": "map", "mapping": {"1": 2}}]},
        )
    assert e.value.locator == "causal.edges[0].fn"


def test_numeric_fn_rejects_categorical_parent() -> None:
    # linear/logistic/polynomial/identity need a float-coercible parent.
    with pytest.raises(SpecValidationError) as e:
        _spec(
            features={"g": {"type": "categorical", "categories": ["a", "b"]},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "g", "to": "y", "fn": "linear", "weight": 2.0}]},
        )
    assert e.value.locator == "causal.edges[0].fn"


def test_boolean_parent_is_accepted_by_numeric_fn() -> None:
    # Booleans coerce to 0/1, so identity/linear over a boolean parent is valid.
    spec = _spec(
        features={"b": {"type": "boolean", "rate": 0.5}, "y": {"type": "numeric"}},
        causal={"edges": [{"from": "b", "to": "y", "fn": "linear", "weight": 10.0}]},
    )
    df = generate(spec, seed=7).frame
    assert set(np.unique(df["y"].to_numpy())) <= {0.0, 10.0}


def test_non_numeric_target_rejected() -> None:
    with pytest.raises(SpecValidationError):
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "g": {"type": "categorical", "categories": ["a", "b"]}},
            causal={"edges": [{"from": "x", "to": "g", "fn": "identity"}]},
        )


def test_unknown_noise_distribution_rejected() -> None:
    with pytest.raises(SpecValidationError) as e:
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "x", "to": "y", "fn": "identity"}],
                    "noise": {"y": {"dist": "wat"}}},
        )
    assert e.value.locator == "causal.noise.y.dist"


def test_intervention_unknown_feature_rejected() -> None:
    with pytest.raises(SpecValidationError):
        _spec(
            features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                      "y": {"type": "numeric"}},
            causal={"edges": [{"from": "x", "to": "y", "fn": "identity"}],
                    "interventions": [{"do": {"ghost": 1}}]},
        )


# --- report: true graph -------------------------------------------------------------


def test_report_carries_true_causal_graph() -> None:
    spec = _spec(
        features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                  "y": {"type": "numeric"}},
        causal={"edges": [{"from": "x", "to": "y", "fn": "linear", "weight": 2.0}]},
    )
    report = generate(spec, seed=7).report
    truth = report.causal_truth
    assert truth is not None
    assert truth["edges"][0] == {"from": "x", "to": "y", "fn": "linear", "weight": 2.0, "active": True}
    assert truth["topological_order"].index("x") < truth["topological_order"].index("y")


def test_report_marks_intervened_edges_inactive() -> None:
    spec = _spec(
        features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                  "y": {"type": "numeric"}},
        causal={"edges": [{"from": "x", "to": "y", "fn": "linear", "weight": 2.0}],
                "interventions": [{"do": {"y": 0}}]},
    )
    truth = generate(spec, seed=7).report.causal_truth
    assert truth["edges"][0]["active"] is False
    assert truth["interventions"] == {"y": 0.0}


def test_mutual_information_matrix_present_for_dependent_columns() -> None:
    spec = _spec(
        features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                  "y": {"type": "numeric"}},
        causal={"edges": [{"from": "x", "to": "y", "fn": "linear", "weight": 5.0}]},
    )
    mi = generate(spec, seed=7).report.mutual_information
    assert mi is not None
    cols = mi["columns"]
    xi, yi = cols.index("x"), cols.index("y")
    # A near-deterministic dependence has clearly positive mutual information.
    assert mi["matrix"][xi][yi] > 0.5


# --- determinism --------------------------------------------------------------------


def test_causal_output_is_deterministic() -> None:
    spec = _spec(
        features={"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                  "y": {"type": "numeric"},
                  "flag": {"type": "boolean"}},
        causal={
            "edges": [
                {"from": "x", "to": "y", "fn": "linear", "weight": 2.0},
                {"from": "y", "to": "flag", "fn": "logistic", "weight": 0.5, "bias": 0.0},
            ],
            "noise": {"y": {"dist": "normal", "params": {"mean": 0, "std": 1}}},
        },
    )
    a = generate(spec, seed=7).frame
    b = generate(spec, seed=7).frame
    assert a.equals(b)
