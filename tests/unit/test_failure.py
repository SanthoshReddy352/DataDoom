"""Failure injection (P3): MCAR/MAR/MNAR, label/feature noise, drift, covariate
shift, leakage.

Covers 17 step 13's test bullets — "rate accuracy, driver correlation, leakage
MI, drift schedule" — plus the clean-baseline guarantee, determinism of the
injected variant, and per-mode validation.
"""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.errors import SpecValidationError

BASE_FEATURES = {
    "x": {"type": "numeric", "dist": "normal", "params": {"mean": 50, "std": 10}},
    "y": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 5}},
    "flag": {"type": "boolean", "rate": 0.4},
    "color": {"type": "categorical", "categories": ["r", "g", "b"], "weights": [0.5, 0.3, 0.2]},
}


def _spec(failures, *, rows=4000, features=None, **overrides):
    base = {
        "datadoom_version": "1",
        "name": "failuretest",
        "rows": rows,
        "seed": 11,
        "features": features or dict(BASE_FEATURES),
        "failures": failures,
    }
    base.update(overrides)
    return parse_spec(base)


def _run(failures, **kw):
    res = generate(_spec(failures, **kw), seed=11)
    return res, res.frame, res.injected


def _diff(res, index):
    return res.report.failures["modes"][index]


# --- MCAR --------------------------------------------------------------------------


def test_mcar_rate_accuracy_and_clean_preserved() -> None:
    res, clean, inj = _run([{"type": "mcar", "columns": ["x"], "rate": 0.1}])
    assert clean["x"].isna().sum() == 0  # baseline untouched
    frac = inj["x"].isna().mean()
    assert frac == pytest.approx(0.1, abs=0.02)
    assert _diff(res, 0)["nullified_fraction"]["x"] == pytest.approx(frac)


def test_mcar_multiple_columns_independent() -> None:
    res, _clean, inj = _run([{"type": "mcar", "columns": ["x", "y"], "rate": 0.1}])
    assert inj["x"].isna().mean() == pytest.approx(0.1, abs=0.02)
    assert inj["y"].isna().mean() == pytest.approx(0.1, abs=0.02)
    # Masks are drawn from independent streams, so co-missingness ≈ p² ≪ p.
    both = (inj["x"].isna() & inj["y"].isna()).mean()
    assert both < 0.04


# --- MAR / MNAR --------------------------------------------------------------------


def test_mar_missingness_depends_on_observed_driver() -> None:
    res, clean, inj = _run(
        [{"type": "mar", "column": "y", "rate": 0.2, "driver": "x", "strength": 3.0}]
    )
    mask = inj["y"].isna().to_numpy()
    assert mask.mean() == pytest.approx(0.2, abs=0.03)  # calibrated to target
    # Positive strength → higher driver ⇒ more likely missing.
    assert clean["x"].to_numpy()[mask].mean() > clean["x"].to_numpy()[~mask].mean() + 2.0


def test_mnar_missingness_depends_on_own_value() -> None:
    res, clean, inj = _run([{"type": "mnar", "column": "x", "rate": 0.2, "strength": 3.0}])
    mask = inj["x"].isna().to_numpy()
    assert mask.mean() == pytest.approx(0.2, abs=0.03)
    # Self-dependent: the nullified rows had higher true x.
    assert clean["x"].to_numpy()[mask].mean() > clean["x"].to_numpy()[~mask].mean() + 2.0
    assert _diff(res, 0)["self_dependent"] is True


# --- label noise -------------------------------------------------------------------


def test_label_noise_boolean_flip_rate() -> None:
    res, clean, inj = _run([{"type": "label_noise", "column": "flag", "rate": 0.1}])
    flipped = (clean["flag"].to_numpy() != inj["flag"].to_numpy())
    assert flipped.mean() == pytest.approx(0.1, abs=0.02)
    assert _diff(res, 0)["flipped_fraction"] == pytest.approx(flipped.mean())


def test_label_noise_categorical_reassigns_to_other_class() -> None:
    res, clean, inj = _run([{"type": "label_noise", "column": "color", "rate": 0.15}])
    changed = clean["color"].to_numpy() != inj["color"].to_numpy()
    assert changed.mean() == pytest.approx(0.15, abs=0.02)
    # Every changed cell is a *valid, different* category.
    assert set(inj["color"].unique()) <= {"r", "g", "b"}
    assert not (inj["color"].to_numpy()[changed] == clean["color"].to_numpy()[changed]).any()


# --- feature noise -----------------------------------------------------------------


def test_feature_noise_additive_std() -> None:
    res, clean, inj = _run(
        [{"type": "feature_noise", "column": "y", "dist": "normal", "params": {"mean": 0, "std": 3}}]
    )
    delta = inj["y"].to_numpy() - clean["y"].to_numpy()
    assert delta.std() == pytest.approx(3.0, abs=0.2)
    assert abs(delta.mean()) < 0.3
    assert _diff(res, 0)["realized_noise_std"] == pytest.approx(3.0, abs=0.2)


# --- drift -------------------------------------------------------------------------


def test_drift_linear_schedule_is_monotone() -> None:
    res, clean, inj = _run(
        [{"type": "drift", "column": "x", "schedule": {"kind": "linear", "magnitude": 20.0}}]
    )
    delta = inj["x"].to_numpy() - clean["x"].to_numpy()
    n = len(delta)
    # Linear ramp 0 → magnitude across the index.
    assert delta[0] == pytest.approx(0.0, abs=1e-9)
    assert delta[-1] == pytest.approx(20.0, abs=1e-9)
    assert delta[n // 2 :].mean() > delta[: n // 2].mean()
    assert _diff(res, 0)["total_shift"] == pytest.approx(20.0)


def test_drift_rate_alias_sets_per_row_slope() -> None:
    res, clean, inj = _run(
        [{"type": "drift", "column": "x", "schedule": {"kind": "linear", "rate": 0.01}}],
        rows=1001,
    )
    delta = inj["x"].to_numpy() - clean["x"].to_numpy()
    # magnitude = rate·(n-1) = 0.01·1000 = 10.
    assert delta[-1] == pytest.approx(10.0, abs=1e-9)


# --- covariate shift ---------------------------------------------------------------


def test_covariate_shift_matches_target_moments() -> None:
    res, _clean, inj = _run(
        [{"type": "covariate_shift", "column": "x", "target": {"mean": 80, "std": 4}}]
    )
    assert inj["x"].mean() == pytest.approx(80.0, abs=0.2)
    assert inj["x"].std() == pytest.approx(4.0, abs=0.2)


# --- leakage -----------------------------------------------------------------------


def test_leakage_plants_high_correlation_proxy_column() -> None:
    res, clean, inj = _run([{"type": "leakage", "target": "flag", "into": "leak", "noise": 0.05}])
    assert "leak" not in clean.columns  # not in the clean baseline
    assert "leak" in inj.columns
    corr = np.corrcoef(inj["leak"].to_numpy(), clean["flag"].to_numpy().astype(float))[0, 1]
    assert abs(corr) > 0.95
    assert _diff(res, 0)["realized_correlation"] == pytest.approx(corr, abs=1e-6)


# --- cross-cutting guarantees ------------------------------------------------------


def test_clean_baseline_preserved_and_reproducible() -> None:
    failures = [
        {"type": "mnar", "column": "x", "rate": 0.1},
        {"type": "label_noise", "column": "flag", "rate": 0.05},
    ]
    a = generate(_spec(failures), seed=11)
    b = generate(_spec(failures), seed=11)
    # Failures run on a copy: the clean baseline carries no injected missingness…
    assert a.frame.isna().sum().sum() == 0
    # …it differs from the injected variant…
    assert not a.injected.equals(a.frame)
    # …and it is itself reproducible across runs of the same spec.
    assert a.frame.equals(b.frame)


def test_injected_variant_is_deterministic() -> None:
    failures = [
        {"type": "mnar", "column": "x", "rate": 0.15},
        {"type": "feature_noise", "column": "y", "dist": "normal", "params": {"mean": 0, "std": 2}},
        {"type": "leakage", "target": "flag", "into": "leak"},
    ]
    a = generate(_spec(failures), seed=11).injected
    b = generate(_spec(failures), seed=11).injected
    assert a.equals(b)


def test_no_failures_means_no_injected_section() -> None:
    res = generate(_spec([]), seed=11)
    assert res.injected is None
    assert res.report.failures is None


# --- validation --------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure, locator_contains",
    [
        ({"type": "bogus", "column": "x"}, "type"),
        ({"type": "mcar", "columns": ["x"], "rate": 1.5}, "rate"),
        ({"type": "mcar", "rate": 0.1}, "columns"),
        ({"type": "mcar", "columns": ["nope"], "rate": 0.1}, "columns"),
        ({"type": "label_noise", "column": "x", "rate": 0.1}, "column"),
        ({"type": "feature_noise", "column": "color", "dist": "normal"}, "column"),
        ({"type": "feature_noise", "column": "x", "dist": "nope"}, "dist"),
        ({"type": "mar", "column": "y", "rate": 0.1, "driver": "color"}, "driver"),
        ({"type": "drift", "column": "x", "schedule": {"kind": "wobble"}}, "schedule"),
        ({"type": "covariate_shift", "column": "x", "target": {}}, "target"),
        ({"type": "leakage", "target": "flag", "into": "flag"}, "into"),
        ({"type": "leakage", "target": "color", "into": "leak"}, "target"),
    ],
)
def test_failure_validation_rejects(failure, locator_contains) -> None:
    with pytest.raises(SpecValidationError) as exc:
        generate(_spec([failure]), seed=11)
    assert locator_contains in (exc.value.locator or "")
