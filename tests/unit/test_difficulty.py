"""Difficulty targeting (P4): probe, adaptive bisection, tier→band, determinism.

Covers 17 step 15's bullets — "ProbeModel + logreg/tree; adaptive loop
(bisection on knobs); achieved-metric reporting; validate tier→band mapping" —
plus honest-miss reporting and the pipeline difficulty stage. The dataset audit
(empirical band recovery, 05 §5.3 / 13 §4) lives in test_difficulty_audit.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.difficulty import (
    PROBES,
    TIER_BANDS,
    DifficultyDial,
    evaluate,
    resolve_target,
)
from datadoom.engine.errors import SpecValidationError
from datadoom.engine.rng import RNGFactory


def _separable_spec(rows: int = 4000, seed: int = 7, **difficulty):
    """A strongly-separable binary label: label = logistic(x1+x2+x3) (steep).

    Clean AUROC ≈ 0.97 (too easy), so the loop must engage the knobs to reach
    any band below 'beginner' — ideal for exercising calibration.
    """
    body = {
        "datadoom_version": "1",
        "name": "diff-test",
        "seed": seed,
        "rows": rows,
        "features": {
            "x1": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "x2": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "x3": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "score": {"type": "numeric", "dtype": "float"},
            "label": {"type": "boolean"},
        },
        "causal": {
            "edges": [
                {"from": "x1", "to": "score", "fn": "linear", "weight": 1.0},
                {"from": "x2", "to": "score", "fn": "linear", "weight": 1.0},
                {"from": "x3", "to": "score", "fn": "linear", "weight": 1.0},
                {"from": "score", "to": "label", "fn": "logistic", "weight": 3.0, "bias": 0.0},
            ],
            "noise": {"score": {"dist": "none"}, "label": {"dist": "none"}},
        },
    }
    if difficulty:
        body["difficulty"] = {"label": "label", "probe": "logreg", **difficulty}
    return parse_spec(body)


def _clean_frame_and_rng(spec):
    """Generate the pre-difficulty clean frame + a matching RNG factory."""
    plain = parse_spec({k: v for k, v in spec.body().items() if k != "difficulty"})
    result = generate(plain, seed=plain.seed)
    rng = RNGFactory(result.spec_hash, result.seed)
    return result.frame, rng


# --- probe model --------------------------------------------------------------------


def test_probe_scores_separable_label_high() -> None:
    spec = _separable_spec()
    frame, _ = _clean_frame_and_rng(spec)
    res = evaluate(PROBES["logreg"], frame, "label", split_seed=1, est_seed=1)
    assert res.metric_name == "auroc"
    assert res.metric > 0.9  # the clean label is highly separable


def test_probe_scores_noise_label_at_chance() -> None:
    # A label independent of every feature → AUROC ≈ 0.5 (no signal, honest).
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {
            "a": rng.normal(size=2000),
            "b": rng.normal(size=2000),
            "label": rng.random(2000) < 0.5,
        }
    )
    res = evaluate(PROBES["tree"], frame, "label", split_seed=2, est_seed=2)
    assert abs(res.metric - 0.5) < 0.06


def test_probe_constant_label_is_chance_not_crash() -> None:
    frame = pd.DataFrame({"a": np.arange(100.0), "label": [True] * 100})
    res = evaluate(PROBES["logreg"], frame, "label", split_seed=1, est_seed=1)
    assert res.metric == 0.5


# --- tier → band mapping (05 §5.3) --------------------------------------------------


def test_tier_band_mapping() -> None:
    assert resolve_target("kaggle").band == TIER_BANDS["kaggle"]
    t = resolve_target({"task": "classification", "metric": "auroc", "band": [0.5, 0.6]})
    assert t.band == (0.5, 0.6)
    assert t.tier is None


def test_all_named_tiers_resolve() -> None:
    for tier, band in TIER_BANDS.items():
        assert resolve_target(tier).band == band


# --- dial monotonicity (the premise the bisection relies on) ------------------------


def test_metric_is_monotone_nonincreasing_in_dial() -> None:
    spec = _separable_spec(rows=5000)
    frame, rng = _clean_frame_and_rng(spec)
    dial = DifficultyDial(frame, "label", rng, ["noise", "label_noise"], [])
    metrics = []
    for d in np.linspace(0.0, 2.0, 9):
        realized, _ = dial.realize(float(d))
        metrics.append(evaluate(PROBES["logreg"], realized, "label", split_seed=3, est_seed=3).metric)
    # Non-increasing within a small probe-variance tolerance.
    for lo, hi in zip(metrics[1:], metrics[:-1], strict=True):
        assert lo <= hi + 0.03
    assert metrics[0] > metrics[-1] + 0.2  # clean clearly easier than max difficulty


def test_label_flips_are_nested_as_rho_grows() -> None:
    spec = _separable_spec(rows=3000)
    frame, rng = _clean_frame_and_rng(spec)
    dial = DifficultyDial(frame, "label", rng, ["noise", "label_noise"], [])
    f_small, s_small = dial.realize(1.2)  # small rho
    f_big, s_big = dial.realize(1.8)  # larger rho
    assert s_big.label_flip > s_small.label_flip > 0
    flipped_small = (f_small["label"].to_numpy() != frame["label"].to_numpy())
    flipped_big = (f_big["label"].to_numpy() != frame["label"].to_numpy())
    # Every row flipped at the smaller rho is still flipped at the larger rho.
    assert np.all(flipped_big[flipped_small])


# --- adaptive loop lands in band ----------------------------------------------------


@pytest.mark.parametrize("tier", ["intermediate", "advanced", "kaggle"])
def test_calibration_hits_band(tier) -> None:
    spec = _separable_spec(rows=5000, target=tier, max_iters=12)
    result = generate(spec, seed=spec.seed)
    d = result.difficulty
    a, b = d["target"]["band"]
    assert d["band_met"] is True
    assert a <= d["achieved_metric"] <= b
    assert d["note"] is None


def test_calibration_increases_difficulty_with_knobs() -> None:
    spec = _separable_spec(rows=5000, target="kaggle", max_iters=12)
    result = generate(spec, seed=spec.seed)
    d = result.difficulty
    # kaggle is well below the clean ~0.97, so real knob turning happened.
    assert d["dial"] > 0.0
    assert d["feature_noise"] > 0.0
    assert d["reference"]["noise_to_signal"] > 0.0


# --- honest miss (no silent failure, invariant #3) ----------------------------------


def test_already_harder_than_band_ships_clean_and_flags() -> None:
    # Beginner band [0.90, 0.99]; ask for it but the *clean* label is weak so it
    # is already below the band and cannot be eased → honest miss at dial 0.
    body = {
        "datadoom_version": "1",
        "name": "weak",
        "seed": 1,
        "rows": 3000,
        "features": {
            "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "y": {"type": "boolean", "rate": 0.5},  # independent of x
        },
        "difficulty": {"target": "beginner", "label": "y", "probe": "logreg"},
    }
    result = generate(parse_spec(body), seed=1)
    d = result.difficulty
    assert d["band_met"] is False
    assert d["dial"] == 0.0
    assert d["note"] is not None and "already harder" in d["note"]


# --- determinism --------------------------------------------------------------------


def test_calibration_is_deterministic(tmp_path) -> None:
    spec = _separable_spec(rows=4000, target="advanced", max_iters=10)
    r1 = generate(spec, seed=spec.seed, out_dir=tmp_path / "a")
    r2 = generate(spec, seed=spec.seed, out_dir=tmp_path / "b")
    assert r1.difficulty == r2.difficulty
    pd.testing.assert_frame_equal(r1.frame, r2.frame)
    assert (tmp_path / "a" / "data.csv").read_bytes() == (tmp_path / "b" / "data.csv").read_bytes()


def test_difficulty_section_in_report() -> None:
    spec = _separable_spec(rows=3000, target="advanced")
    result = generate(spec, seed=spec.seed)
    rep = result.report.to_dict()
    assert rep["difficulty"] is not None
    assert rep["difficulty"]["metric_name"] == "auroc"
    assert "trace" in rep["difficulty"]


# --- validation ---------------------------------------------------------------------


def test_validation_rejects_non_classification_label() -> None:
    body = {
        "datadoom_version": "1",
        "name": "bad",
        "rows": 100,
        "features": {"v": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}}},
        "difficulty": {"target": "kaggle", "label": "v"},
    }
    with pytest.raises(SpecValidationError, match="binary"):
        generate(parse_spec(body), seed=1)


def test_validation_rejects_multiclass_label() -> None:
    body = {
        "datadoom_version": "1",
        "name": "bad",
        "rows": 100,
        "features": {"c": {"type": "categorical", "categories": ["a", "b", "c"]}},
        "difficulty": {"target": "kaggle", "label": "c"},
    }
    with pytest.raises(SpecValidationError, match="binary"):
        generate(parse_spec(body), seed=1)


def test_validation_rejects_unknown_probe_tier_knob() -> None:
    base = {
        "datadoom_version": "1",
        "name": "bad",
        "rows": 100,
        "features": {"y": {"type": "boolean"}},
    }
    with pytest.raises(SpecValidationError, match="probe"):
        generate(parse_spec({**base, "difficulty": {"target": "kaggle", "label": "y", "probe": "svm"}}), seed=1)
    with pytest.raises(SpecValidationError, match="tier"):
        generate(parse_spec({**base, "difficulty": {"target": "wizard", "label": "y"}}), seed=1)
    with pytest.raises(SpecValidationError, match="knob"):
        generate(
            parse_spec({**base, "difficulty": {"target": "kaggle", "label": "y", "knobs": ["imbalance"]}}),
            seed=1,
        )


def test_validation_rejects_bad_explicit_band() -> None:
    body = {
        "datadoom_version": "1",
        "name": "bad",
        "rows": 100,
        "features": {"y": {"type": "boolean"}},
        "difficulty": {"target": {"band": [0.9, 0.5]}, "label": "y"},
    }
    with pytest.raises(SpecValidationError, match="band"):
        generate(parse_spec(body), seed=1)
