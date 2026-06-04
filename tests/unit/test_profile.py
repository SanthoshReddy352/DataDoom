"""Per-column profile + ML-handling advice (the "Column Guide").

The profile is derived ground truth: the engine knows each column's type, how a
derived column was generated, and exactly which failure modes hit it. These tests
assert the report card is correct (roles, stats, failure attribution), that every
issue carries actionable advice, and that the whole section is deterministic so it
stays on the reproducible-artifact path (invariant #6).
"""

from __future__ import annotations

import json

import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.advice import build_issue, severity_rank
from datadoom.engine.profile import build_profile

SEED = 42

# A spec that exercises every attribution path: derived columns, a boolean target,
# and the full stack of failure modes (missingness, label noise, drift, leakage).
FAILURE_SPEC = {
    "datadoom_version": "1",
    "name": "profile-fixture",
    "rows": 4000,
    "features": {
        "age": {"type": "numeric", "dist": "normal", "params": {"mean": 40, "std": 12}, "min": 18, "max": 90, "dtype": "int"},
        "education": {"type": "categorical", "categories": ["hs", "college", "grad"], "weights": [0.5, 0.4, 0.1]},
        "income": {"type": "numeric", "dtype": "float", "min": 0},
        "is_fraud": {"type": "boolean"},
    },
    "causal": {
        "edges": [
            {"from": "age", "to": "income", "fn": "linear", "weight": 800, "bias": 10000},
            {"from": "education", "to": "income", "fn": "map", "mapping": {"hs": 0, "college": 15000, "grad": 40000}},
            {"from": "income", "to": "is_fraud", "fn": "logistic", "weight": -0.00002, "bias": 1.0},
        ],
        "noise": {"income": {"dist": "normal", "params": {"mean": 0, "std": 5000}}, "is_fraud": {"dist": "none"}},
    },
    "failures": [
        {"type": "mnar", "column": "income", "rate": 0.12, "strength": 2.5},
        {"type": "mcar", "columns": ["age"], "rate": 0.05},
        {"type": "label_noise", "column": "is_fraud", "rate": 0.03},
        {"type": "feature_noise", "column": "age", "dist": "normal", "params": {"mean": 0, "std": 2}},
        {"type": "drift", "column": "income", "schedule": {"kind": "linear", "magnitude": 8000}},
        {"type": "leakage", "target": "is_fraud", "into": "fraud_score", "noise": 0.05},
    ],
}


@pytest.fixture(scope="module")
def profile() -> dict:
    res = generate(parse_spec(FAILURE_SPEC), seed=SEED)
    assert res.report.profile is not None
    return res.report.profile


def _col(profile: dict, name: str) -> dict:
    return next(c for c in profile["columns"] if c["name"] == name)


def test_every_shipped_and_planted_column_profiled(profile: dict) -> None:
    names = {c["name"] for c in profile["columns"]}
    assert names == {"age", "education", "income", "is_fraud", "fraud_score"}
    assert profile["summary"]["n_columns"] == 5
    assert profile["summary"]["n_rows"] == 4000


def test_roles_and_derivation(profile: dict) -> None:
    assert _col(profile, "age")["role"] == "feature"
    assert _col(profile, "income")["role"] == "derived"
    assert _col(profile, "income")["parents"] == ["age", "education"]
    assert _col(profile, "is_fraud")["role"] == "label"  # boolean causal sink
    assert _col(profile, "fraud_score")["role"] == "leakage_proxy"
    assert profile["summary"]["label"] == "is_fraud"


def test_numeric_stats_present_for_derived_column(profile: dict) -> None:
    stats = _col(profile, "income")["stats"]
    assert stats is not None
    for key in ("mean", "std", "min", "p25", "median", "p75", "max"):
        assert isinstance(stats[key], float)
    assert stats["min"] <= stats["median"] <= stats["max"]


def test_categorical_breakdown_and_balance(profile: dict) -> None:
    edu = _col(profile, "education")
    assert edu["stats"] is None
    vals = {c["value"] for c in edu["categories"]}
    assert vals == {"hs", "college", "grad"}
    assert abs(sum(c["pct"] for c in edu["categories"]) - 1.0) < 1e-9
    assert edu["imbalance"]["classes"] == 3


def test_failure_attribution_per_column(profile: dict) -> None:
    def modes(name: str) -> set[str]:
        return {i["mode"] for i in _col(profile, name)["issues"]}

    assert modes("income") == {"mnar", "drift"}
    assert modes("age") == {"mcar", "feature_noise"}
    assert modes("is_fraud") == {"label_noise"}
    assert modes("fraud_score") == {"leakage"}
    assert _col(profile, "education")["issues"] == []


def test_injected_snapshot_reflects_realized_missingness(profile: dict) -> None:
    # income gets ~12% MNAR missingness in the injected variant; clean stays full.
    inc = _col(profile, "income")
    assert inc["missing_pct"] == 0.0
    assert inc["injected"]["missing_pct"] == pytest.approx(0.12, abs=0.03)


def test_leakage_is_critical_with_advice(profile: dict) -> None:
    issue = _col(profile, "fraud_score")["issues"][0]
    assert issue["mode"] == "leakage"
    assert issue["severity"] == "critical"
    assert "drop" in issue["recommendation"].lower()
    assert issue["techniques"]


def test_every_issue_has_actionable_advice(profile: dict) -> None:
    for col in profile["columns"]:
        for issue in col["issues"]:
            assert issue["title"] and issue["explanation"]
            assert issue["recommendation"]
            assert issue["magnitude"]
            assert issue["severity"] in ("critical", "high", "medium", "low")


def test_issues_sorted_by_severity(profile: dict) -> None:
    for col in profile["columns"]:
        ranks = [severity_rank(i["severity"]) for i in col["issues"]]
        assert ranks == sorted(ranks, reverse=True)


def test_profile_is_deterministic() -> None:
    spec = parse_spec(FAILURE_SPEC)
    a = generate(spec, seed=SEED).report.profile
    b = generate(spec, seed=SEED).report.profile
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_class_imbalance_issue_fires_on_skewed_label() -> None:
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "imbalance-fixture",
            "rows": 3000,
            "features": {
                "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                "y": {"type": "boolean", "rate": 0.05},
            },
            "difficulty": {"target": "intermediate", "label": "y"},
        }
    )
    profile = generate(spec, seed=SEED).report.profile
    y = _col(profile, "y")
    imb = next((i for i in y["issues"] if i["mode"] == "class_imbalance"), None)
    assert imb is not None
    assert "minority" in imb["explanation"].lower() or "balance" in imb["explanation"].lower()
    assert any("class weight" in t.lower() or "smote" in t.lower() for t in imb["techniques"])


def test_advice_severity_escalates_with_magnitude() -> None:
    low = build_issue("mcar", magnitude="2% missing", fraction=0.02)
    high = build_issue("mcar", magnitude="40% missing", fraction=0.40)
    assert severity_rank(high.severity) > severity_rank(low.severity)


def test_unknown_mechanism_falls_back_gracefully() -> None:
    issue = build_issue("some_plugin_mode", magnitude="x", fraction=None)
    assert issue.severity == "medium"
    assert issue.title


def test_build_profile_without_failures_has_no_issues() -> None:
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "clean-fixture",
            "rows": 500,
            "features": {"a": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}}},
        }
    )
    res = generate(spec, seed=SEED)
    profile = build_profile(spec, res.frame)
    assert profile["summary"]["total_issues"] == 0
    assert profile["columns"][0]["issues"] == []


def test_build_profile_handles_empty_injected_columns() -> None:
    # A planted column present only in the injected frame is still profiled.
    spec = parse_spec(FAILURE_SPEC)
    res = generate(spec, seed=SEED)
    assert res.injected is not None
    profile = build_profile(spec, res.frame, injected=res.injected, failure_diffs=None)
    # No diffs → no issues, but the injected-only column (fraud_score) still appears.
    assert any(c["name"] == "fraud_score" for c in profile["columns"])
    assert profile["summary"]["total_issues"] == 0
