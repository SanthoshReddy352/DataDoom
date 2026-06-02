"""Built-in distributions and feature samplers (04 §4, 05 §2).

Numeric distributions referenced by ``dist:`` live in :data:`REGISTRY`. Sampling
flows entirely through the injected ``numpy.random.Generator`` so results are
deterministic on the pinned path. Non-numeric feature kinds (categorical,
boolean, datetime, text) have dedicated samplers used by the pipeline.
"""

from __future__ import annotations

from typing import Mapping

import numpy as np
from scipy import stats

from ..errors import SpecValidationError
from .base import Distribution


def _require_positive(params: Mapping[str, float], keys: tuple[str, ...], locator: str | None) -> None:
    for k in keys:
        if k in params and params[k] <= 0:
            raise SpecValidationError(f"param {k!r} must be > 0", locator=locator)


class Normal(Distribution):
    name = "normal"
    required_params = ("mean", "std")

    def _validate_domain(self, params, locator):
        _require_positive(params, ("std",), locator)

    def sample(self, rng, n, params):
        return rng.normal(params["mean"], params["std"], size=n)

    def cdf(self, x, params):
        return stats.norm.cdf(x, loc=params["mean"], scale=params["std"])


class LogNormal(Distribution):
    name = "lognormal"
    required_params = ("mu", "sigma")

    def _validate_domain(self, params, locator):
        _require_positive(params, ("sigma",), locator)

    def sample(self, rng, n, params):
        return rng.lognormal(params["mu"], params["sigma"], size=n)

    def cdf(self, x, params):
        return stats.lognorm.cdf(x, s=params["sigma"], scale=np.exp(params["mu"]))


class Poisson(Distribution):
    name = "poisson"
    required_params = ("lam",)

    def _validate_domain(self, params, locator):
        _require_positive(params, ("lam",), locator)

    def sample(self, rng, n, params):
        return rng.poisson(params["lam"], size=n)

    def cdf(self, x, params):
        return stats.poisson.cdf(x, mu=params["lam"])


class Pareto(Distribution):
    name = "pareto"
    required_params = ("alpha", "xm")

    def _validate_domain(self, params, locator):
        _require_positive(params, ("alpha", "xm"), locator)

    def sample(self, rng, n, params):
        # numpy draws Lomax (Pareto II); classical Pareto I = (lomax + 1) * xm.
        return (rng.pareto(params["alpha"], size=n) + 1.0) * params["xm"]

    def cdf(self, x, params):
        return stats.pareto.cdf(x, b=params["alpha"], scale=params["xm"])


class Uniform(Distribution):
    name = "uniform"
    required_params = ("low", "high")

    def _validate_domain(self, params, locator):
        if params["low"] >= params["high"]:
            raise SpecValidationError("uniform requires low < high", locator=locator)

    def sample(self, rng, n, params):
        return rng.uniform(params["low"], params["high"], size=n)

    def cdf(self, x, params):
        return stats.uniform.cdf(x, loc=params["low"], scale=params["high"] - params["low"])


class Exponential(Distribution):
    name = "exponential"
    required_params = ("scale",)

    def _validate_domain(self, params, locator):
        _require_positive(params, ("scale",), locator)

    def sample(self, rng, n, params):
        return rng.exponential(params["scale"], size=n)

    def cdf(self, x, params):
        return stats.expon.cdf(x, scale=params["scale"])


REGISTRY: dict[str, Distribution] = {
    d.name: d
    for d in (Normal(), LogNormal(), Poisson(), Pareto(), Uniform(), Exponential())
}


# --- Non-numeric feature samplers ----------------------------------------------------


def sample_categorical(
    rng: np.random.Generator, n: int, categories: list[str], weights: list[float] | None
) -> np.ndarray:
    if weights is None:
        probs = None
    else:
        total = float(sum(weights))
        probs = [w / total for w in weights]
    return rng.choice(np.asarray(categories, dtype=object), size=n, p=probs)


def sample_boolean(rng: np.random.Generator, n: int, rate: float) -> np.ndarray:
    return rng.random(size=n) < rate


def sample_datetime(
    rng: np.random.Generator,
    n: int,
    start: str,
    end: str,
    granularity: str,
) -> np.ndarray:
    """Uniformly sample timestamps in [start, end] at the given granularity."""
    unit = {"second": "s", "minute": "m", "hour": "h", "day": "D"}[granularity]
    # Cast both endpoints to the chosen unit so their difference is an integer
    # number of steps — avoids unit-mismatch and stays fully deterministic.
    start_dt = np.datetime64(start).astype(f"datetime64[{unit}]")
    end_dt = np.datetime64(end).astype(f"datetime64[{unit}]")
    span_steps = int((end_dt - start_dt).astype("int64"))
    if span_steps < 0:
        raise SpecValidationError("datetime end must be >= start")
    offsets = rng.integers(0, span_steps + 1, size=n)
    return start_dt + offsets.astype(f"timedelta64[{unit}]")


_LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua ut enim ad minim veniam quis nostrud "
    "exercitation ullamco laboris nisi aliquip ex ea commodo consequat"
).split()


def sample_text(
    rng: np.random.Generator, n: int, min_len: int, max_len: int
) -> np.ndarray:
    words = np.asarray(_LOREM, dtype=object)
    lengths = rng.integers(min_len, max_len + 1, size=n)
    out = np.empty(n, dtype=object)
    for i in range(n):
        idx = rng.integers(0, len(words), size=int(lengths[i]))
        out[i] = " ".join(words[idx])
    return out
