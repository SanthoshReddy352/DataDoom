"""Distributions sample correctly and KS reporting is honest (no refit)."""

from __future__ import annotations

import numpy as np

from datadoom.engine.dist import REGISTRY, assess_numeric
from datadoom.engine.rng import RNGFactory


def test_normal_empirical_params_within_tolerance() -> None:
    rng = RNGFactory("h", 1).feature("x")
    x = REGISTRY["normal"].sample(rng, 50_000, {"mean": 40, "std": 12})
    assert abs(float(np.mean(x)) - 40) < 0.3
    assert abs(float(np.std(x, ddof=1)) - 12) < 0.3


def test_uniform_respects_bounds() -> None:
    rng = RNGFactory("h", 1).feature("x")
    x = REGISTRY["uniform"].sample(rng, 10_000, {"low": -2, "high": 5})
    assert x.min() >= -2 and x.max() <= 5


def test_ks_rejection_rate_matches_alpha_when_params_correct() -> None:
    # If sampling is correct (and we do NOT refit), the rejection rate at alpha
    # should hover near alpha — a handful of "failures" out of many seeds.
    rejects = 0
    trials = 60
    for s in range(trials):
        rng = RNGFactory("h", s).feature("x")
        x = REGISTRY["normal"].sample(rng, 2000, {"mean": 0, "std": 1})
        fc = assess_numeric("x", "normal", {"mean": 0, "std": 1}, x, alpha=0.05)
        rejects += 0 if fc.passed else 1
    rate = rejects / trials
    # Generous band around alpha=0.05 — the point is it is small but non-zero,
    # which would be impossible if we were refitting to the sample.
    assert rate < 0.25


def test_ks_rejects_when_params_wrong() -> None:
    # Proves the KS test is live: assess correct data against a wrong target.
    rng = RNGFactory("h", 1).feature("x")
    x = REGISTRY["normal"].sample(rng, 5000, {"mean": 0, "std": 1})
    fc = assess_numeric("x", "normal", {"mean": 10, "std": 1}, x, alpha=0.05)
    assert not fc.passed
    assert fc.p_value < 0.05


def test_compliance_score_aggregates() -> None:
    from datadoom.engine.dist import ComplianceReport

    rep = ComplianceReport(alpha=0.05)
    rng = RNGFactory("h", 1).feature("x")
    good = REGISTRY["normal"].sample(rng, 4000, {"mean": 0, "std": 1})
    rep.features.append(assess_numeric("a", "normal", {"mean": 0, "std": 1}, good))
    rep.features.append(assess_numeric("b", "normal", {"mean": 99, "std": 1}, good))
    assert rep.score == 0.5


def test_poisson_is_not_ks_applicable() -> None:
    # Poisson is discrete: a continuous KS test does not apply (Group E).
    rng = RNGFactory("h", 1).feature("x")
    x = REGISTRY["poisson"].sample(rng, 4000, {"lam": 3})
    fc = assess_numeric("x", "poisson", {"lam": 3}, x)
    assert fc.applicable is False and fc.passed is None
    assert "discrete" in (fc.note or "")


def test_int_dtype_is_not_ks_applicable() -> None:
    rng = RNGFactory("h", 1).feature("x")
    x = REGISTRY["normal"].sample(rng, 4000, {"mean": 0, "std": 1})
    fc = assess_numeric("x", "normal", {"mean": 0, "std": 1}, x, dtype="int")
    assert fc.applicable is False and fc.passed is None


def test_score_excludes_non_applicable_features() -> None:
    from datadoom.engine.dist import ComplianceReport

    rng = RNGFactory("h", 1).feature("x")
    rep = ComplianceReport(alpha=0.05)
    good = REGISTRY["normal"].sample(rng, 4000, {"mean": 0, "std": 1})
    counts = REGISTRY["poisson"].sample(rng, 4000, {"lam": 3})
    rep.features.append(assess_numeric("ok", "normal", {"mean": 0, "std": 1}, good))
    rep.features.append(assess_numeric("pois", "poisson", {"lam": 3}, counts))  # n/a
    # Only the applicable feature counts; the discrete one is excluded, not failed.
    assert rep.score == 1.0
    assert rep.to_dict()["applicable_features"] == 1
    assert rep.to_dict()["assessed_features"] == 2
