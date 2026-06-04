"""Critical audit for difficulty calibration (P4) — the analogue of
test_dataset_audit.py (P2) and test_failure_audit.py (P3).

Rather than trust the reported numbers, these recover the calibration's claims
from the *shipped* frame: an independent probe reproduces the reported AUROC
(the report is honest about the data on disk), the feature-noise variance
matches the closed form Var = σ²(1+η²) (05 §5.4), and every named tier lands a
fresh baseline in its band at scale (the 05 §5.3 / 13 §4 calibration test).
"""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.difficulty import PROBES, evaluate


def _separable_spec(rows: int, target, seed: int = 7, max_iters: int = 12):
    body = {
        "datadoom_version": "1",
        "name": "diff-audit",
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
        "difficulty": {"target": target, "label": "label", "probe": "logreg", "max_iters": max_iters},
    }
    return parse_spec(body)


def test_report_metric_matches_independent_probe() -> None:
    """The achieved metric is honest about the *shipped* frame, not an artifact
    of the one split the loop happened to use — a fresh independent split on the
    data on disk reproduces it."""
    spec = _separable_spec(rows=8000, target="advanced")
    result = generate(spec, seed=spec.seed)
    achieved = result.difficulty["achieved_metric"]
    # Independent split seeds the loop never used.
    fresh = evaluate(PROBES["logreg"], result.frame, "label", split_seed=999_983, est_seed=12345)
    assert abs(fresh.metric - achieved) < 0.04


def test_feature_noise_variance_matches_closed_form() -> None:
    """Var(shipped) ≈ σ²(1 + η²): the baked observation noise is exactly the
    reported η, no hidden refit (05 §5.4, invariant #3)."""
    spec = _separable_spec(rows=12000, target="kaggle")
    result = generate(spec, seed=spec.seed)
    eta = result.difficulty["feature_noise"]
    assert eta > 0.0  # kaggle genuinely turned the feature-noise knob
    # x1 ~ Normal(0, 1) clean, so the shipped variance should be ~ (1 + η²).
    shipped_var = float(np.var(result.frame["x1"].to_numpy(dtype=float)))
    expected = 1.0 * (1.0 + eta * eta)
    assert abs(shipped_var - expected) / expected < 0.08
    # And the reported noise-to-signal equals η² (05 §5.4).
    assert abs(result.difficulty["reference"]["noise_to_signal"] - eta * eta) < 1e-9


@pytest.mark.parametrize("tier", ["beginner", "intermediate", "advanced", "kaggle"])
def test_every_tier_lands_a_baseline_in_band(tier) -> None:
    """05 §5.3 / 13 §4: each named tier calibrates a fresh baseline into its band."""
    spec = _separable_spec(rows=8000, target=tier, max_iters=14)
    result = generate(spec, seed=spec.seed)
    d = result.difficulty
    a, b = d["target"]["band"]
    assert d["band_met"] is True, f"{tier}: achieved {d['achieved_metric']:.3f} not in [{a},{b}]"
    # Independent re-evaluation also lands in (a small slack on) the band.
    fresh = evaluate(PROBES["logreg"], result.frame, "label", split_seed=424_242, est_seed=7).metric
    assert a - 0.04 <= fresh <= b + 0.04


def test_harder_tier_needs_more_noise() -> None:
    """Monotone end-to-end: a harder target requires a larger dial / more noise."""
    easy = generate(_separable_spec(8000, "intermediate"), seed=7).difficulty
    hard = generate(_separable_spec(8000, "kaggle"), seed=7).difficulty
    assert hard["dial"] >= easy["dial"]
    assert hard["feature_noise"] + hard["label_flip"] >= easy["feature_noise"] + easy["label_flip"]
