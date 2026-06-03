"""FailureMode ABC + shared helpers (05 §4, 04 §7).

A failure mode is a deterministic corruption transform applied *after* the clean
baseline is captured. Each mode reads its config (the failure spec entry minus
``type``), mutates the working ``injected`` frame in place, and returns a **diff
summary** describing what it changed (fraction nullified, realized rate, shift
magnitude, leakage correlation…). The clean baseline is never touched.

All randomness flows through an injected ``numpy.random.Generator`` (``RNG(failure:i)``)
so the injected variant is itself reproducible on the pinned path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from ..errors import SpecValidationError
from ..spec.models import Feature


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically-stable logistic function."""
    return np.where(z >= 0, 1.0 / (1.0 + np.exp(-z)), np.exp(z) / (1.0 + np.exp(z)))


def standardize(values: np.ndarray) -> np.ndarray:
    """Z-score a numeric (or boolean) driver; constant/degenerate columns map to
    zeros. NaN-robust: previously-injected missing values contribute a 0 score
    rather than poisoning the whole column."""
    x = np.asarray(values, dtype=float)
    std = float(np.nanstd(x))
    if std == 0.0 or not np.isfinite(std):
        return np.zeros_like(x)
    z = (x - float(np.nanmean(x))) / std
    return np.nan_to_num(z, nan=0.0)


def calibrate_logistic_intercept(scores: np.ndarray, target_rate: float) -> float:
    """Find ``a`` so that ``mean(sigmoid(a + scores)) == target_rate``.

    The mean of the logistic is monotonic in the intercept, so a bisection
    converges. This lets MAR/MNAR honor the requested *expected* missing rate
    while keeping the missingness **dependent on the driver/value** (the whole
    point of those mechanisms).
    """
    if target_rate <= 0.0:
        return float("-inf")
    if target_rate >= 1.0:
        return float("inf")
    lo, hi = -60.0, 60.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if float(np.mean(sigmoid(mid + scores))) < target_rate:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --- validation helpers --------------------------------------------------------------


def require_rate(params: Mapping[str, Any], locator: str) -> float:
    rate = params.get("rate")
    if rate is None:
        raise SpecValidationError("missing required 'rate'", locator=f"{locator}.rate")
    rate = float(rate)
    if not 0.0 <= rate <= 1.0:
        raise SpecValidationError("rate must be in [0, 1]", locator=f"{locator}.rate")
    return rate


def require_feature(
    params: Mapping[str, Any],
    key: str,
    features: Mapping[str, Feature],
    locator: str,
) -> str:
    ref = params.get(key)
    if not isinstance(ref, str):
        raise SpecValidationError(f"missing required '{key}'", locator=f"{locator}.{key}")
    if ref not in features:
        raise SpecValidationError(
            f"{key} {ref!r} is not a declared feature", locator=f"{locator}.{key}"
        )
    return ref


class FailureMode(ABC):
    """ABC for a corruption transform (05 §4)."""

    name: str

    def validate(
        self, params: Mapping[str, Any], features: Mapping[str, Feature], locator: str
    ) -> None:
        """Check the config carries the fields this mode needs and they reference
        real features. Raise :class:`SpecValidationError` on the first problem."""
        return None

    @abstractmethod
    def apply(
        self,
        rng: np.random.Generator,
        frame: pd.DataFrame,
        params: Mapping[str, Any],
        features: Mapping[str, Feature],
    ) -> dict[str, Any]:
        """Mutate ``frame`` in place and return a diff summary."""
