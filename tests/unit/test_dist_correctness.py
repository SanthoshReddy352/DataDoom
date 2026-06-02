"""Distribution *correctness* tests (status.md task TH.1-TH.5).

These assert the realized samples have the right *distribution* — moments,
support, weights, bounds — not merely "some numbers". A logic/arithmetic bug in
a sampler (e.g. a wrong Pareto formula or a swapped weight normalization) would
pass the structural suite but fail here. Sampling is deterministic on a fixed
seed, so the tolerances below have plenty of margin.
"""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine.dist import (
    REGISTRY,
    assess_numeric,
    sample_boolean,
    sample_categorical,
    sample_datetime,
    sample_text,
)
from datadoom.engine.rng import RNGFactory


def _feature_rng(seed: int = 1):
    return RNGFactory("correctness", seed).feature("x")


# --- TH.1 numeric distribution moments & support -------------------------------------


def test_lognormal_moments_match_theta() -> None:
    # median = exp(mu); mean = exp(mu + sigma^2 / 2).
    mu, sigma = 0.0, 0.5
    x = REGISTRY["lognormal"].sample(_feature_rng(), 200_000, {"mu": mu, "sigma": sigma})
    assert (x > 0).all()  # lognormal support is (0, inf)
    assert abs(float(np.median(x)) - np.exp(mu)) < 0.03
    assert abs(float(np.mean(x)) - np.exp(mu + sigma**2 / 2)) < 0.03


def test_poisson_mean_var_and_integral() -> None:
    lam = 4.0
    x = REGISTRY["poisson"].sample(_feature_rng(), 200_000, {"lam": lam})
    assert np.issubdtype(x.dtype, np.integer)  # discrete count output
    assert abs(float(np.mean(x)) - lam) < 0.05
    assert abs(float(np.var(x)) - lam) < 0.1  # mean == var for Poisson


def test_pareto_support_and_mean() -> None:
    # Guards the (lomax + 1) * xm reconstruction of classical Pareto I.
    alpha, xm = 3.0, 2.0
    x = REGISTRY["pareto"].sample(_feature_rng(), 200_000, {"alpha": alpha, "xm": xm})
    assert (x >= xm).all()  # support is [xm, inf)
    # mean = alpha * xm / (alpha - 1), finite for alpha > 1.
    assert abs(float(np.mean(x)) - alpha * xm / (alpha - 1)) < 0.1


def test_exponential_support_and_mean() -> None:
    scale = 2.5
    x = REGISTRY["exponential"].sample(_feature_rng(), 200_000, {"scale": scale})
    assert (x >= 0).all()  # support is [0, inf)
    assert abs(float(np.mean(x)) - scale) < 0.05


# --- TH.1.5 cdf <-> sampler agreement ------------------------------------------------

# Continuous distributions only: a correct cdf paired with a correct sampler
# should *pass* the continuous KS test the overwhelming majority of the time. A
# wrong cdf would be rejected on essentially every seed. (Poisson is discrete and
# legitimately fails a continuous KS test — see Group E — so it is excluded.)
_CONTINUOUS = {
    "normal": {"mean": 0.0, "std": 1.0},
    "lognormal": {"mu": 0.0, "sigma": 0.5},
    "pareto": {"alpha": 3.0, "xm": 2.0},
    "uniform": {"low": -2.0, "high": 5.0},
    "exponential": {"scale": 2.5},
}


@pytest.mark.parametrize("dist_name, params", list(_CONTINUOUS.items()))
def test_cdf_matches_sampler_passes_ks(dist_name: str, params: dict[str, float]) -> None:
    trials = 20
    passes = 0
    for s in range(trials):
        rng = RNGFactory("ks", s).feature("x")
        x = REGISTRY[dist_name].sample(rng, 3000, params)
        fc = assess_numeric("x", dist_name, params, x, alpha=0.05)
        passes += 1 if fc.passed else 0
    # With a correct cdf the pass rate hugs (1 - alpha); allow generous slack for
    # sampling variance / numpy-version differences. A wrong cdf scores ~0.
    assert passes >= 15


# --- TH.2 categorical weight fidelity ------------------------------------------------


def _proportions(values: np.ndarray, categories: list[str]) -> dict[str, float]:
    n = len(values)
    return {c: float(np.count_nonzero(values == c)) / n for c in categories}


def test_categorical_weighted_proportions() -> None:
    cats = ["a", "b", "c"]
    weights = [0.6, 0.3, 0.1]
    x = sample_categorical(_feature_rng(), 200_000, cats, weights)
    props = _proportions(x, cats)
    for c, w in zip(cats, weights, strict=True):
        assert abs(props[c] - w) < 0.01


def test_categorical_uniform_when_no_weights() -> None:
    cats = ["a", "b", "c", "d"]
    x = sample_categorical(_feature_rng(), 200_000, cats, None)
    props = _proportions(x, cats)
    for c in cats:
        assert abs(props[c] - 0.25) < 0.01


def test_categorical_unnormalized_weights_normalize() -> None:
    # [3, 1] must behave as [0.75, 0.25].
    cats = ["a", "b"]
    x = sample_categorical(_feature_rng(), 200_000, cats, [3, 1])
    props = _proportions(x, cats)
    assert abs(props["a"] - 0.75) < 0.01
    assert abs(props["b"] - 0.25) < 0.01


# --- TH.3 boolean rate fidelity ------------------------------------------------------


def test_boolean_rate_fidelity() -> None:
    rate = 0.3
    x = sample_boolean(_feature_rng(), 200_000, rate)
    assert x.dtype == bool
    assert abs(float(np.mean(x)) - rate) < 0.01


# --- TH.4 datetime bounds & granularity ----------------------------------------------


def test_datetime_within_bounds_and_dtype() -> None:
    start, end = "2020-01-01", "2020-12-31"
    x = sample_datetime(_feature_rng(), 50_000, start, end, "day")
    assert str(x.dtype) == "datetime64[D]"  # whole-day granularity in the dtype
    assert x.min() >= np.datetime64(start)
    assert x.max() <= np.datetime64(end)


def test_datetime_hour_granularity_unit() -> None:
    x = sample_datetime(_feature_rng(), 10_000, "2020-01-01", "2020-01-02", "hour")
    assert str(x.dtype) == "datetime64[h]"
    assert x.min() >= np.datetime64("2020-01-01T00", "h")
    assert x.max() <= np.datetime64("2020-01-02T00", "h")


# --- TH.5 text length ----------------------------------------------------------------


def test_text_token_length_within_bounds() -> None:
    min_len, max_len = 3, 8
    x = sample_text(_feature_rng(), 5000, min_len, max_len)
    token_counts = [len(s.split()) for s in x]
    assert min(token_counts) >= min_len
    assert max(token_counts) <= max_len
