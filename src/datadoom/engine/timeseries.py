"""Time-series generation — additive decomposition (05 §6).

A time-series feature realizes an ordered series over the row index ``t = 0 … n−1``:

    Xₜ = T(t) + S(t) + AR(p) + εₜ
    T(t) = slope·t + intercept                          # linear trend
    S(t) = Σ Aⱼ·sin(2π·t/periodⱼ + phaseⱼ)             # (multi-)seasonality
    AR(p): Yₜ = Σ_{i=1}^p φᵢ·Y_{t−i} + εₜ               # autoregressive residual
    εₜ ~ Normal(0, σ²)  from RNG(noise:<series>)

The deterministic mean ``T(t)+S(t)`` is vectorised; the AR residual is an inherent
sequential recursion (each term depends on its predecessors) seeded with
``Y_{t<0} = 0`` — a fixed, reproducible warm-start (no hidden burn-in draws). With
no ``ar`` coefficients the residual is plain i.i.d. noise ``εₜ``.

This module is pure and frawework-free; all randomness flows through the injected
``numpy.random.Generator`` so the series is byte-reproducible on the pinned path.
Multivariate / hierarchical series are deferred (plugin / post-v1), per 05 §6.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Trend:
    slope: float = 0.0
    intercept: float = 0.0


@dataclass(frozen=True)
class Seasonality:
    amplitude: float
    period: float
    phase: float = 0.0


def generate_series(
    rng: np.random.Generator,
    n: int,
    *,
    trend: Trend | None = None,
    seasonality: Sequence[Seasonality] = (),
    ar: Sequence[float] = (),
    noise_std: float = 1.0,
) -> np.ndarray:
    """Realize one additive time-series of length ``n`` (05 §6).

    Args:
        rng: the per-series noise generator (``RNG(noise:<name>)``).
        n: series length (row count).
        trend: linear ``slope·t + intercept`` component (or ``None``).
        seasonality: zero or more sinusoidal components, summed.
        ar: autoregressive coefficients ``[φ₁ … φ_p]`` on the residual.
        noise_std: σ of the Gaussian innovations ``εₜ``.

    Returns:
        A float ``ndarray`` of length ``n`` in row order.
    """
    t = np.arange(n, dtype=float)

    mean = np.zeros(n, dtype=float)
    if trend is not None:
        mean += trend.slope * t + trend.intercept
    for s in seasonality:
        mean += s.amplitude * np.sin(2.0 * np.pi * t / s.period + s.phase)

    eps = rng.normal(0.0, noise_std, size=n) if noise_std > 0 else np.zeros(n, dtype=float)

    coeffs = list(ar)
    if not coeffs:
        return mean + eps

    # Zero-mean AR(p) residual: Yₜ = Σ φᵢ·Y_{t−i} + εₜ, warm-started at Y_{<0}=0.
    p = len(coeffs)
    y = np.zeros(n, dtype=float)
    for i in range(n):
        acc = eps[i]
        for j in range(p):
            k = i - j - 1
            if k >= 0:
                acc += coeffs[j] * y[k]
        y[i] = acc
    return mean + y
