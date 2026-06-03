"""Built-in failure modes (05 §4, 04 §7).

Each mode mutates the working *injected* frame in place and returns a diff
summary. The clean baseline is captured before any of these run, so it is always
recoverable. All draws come from the injected ``RNG(failure:i)``.

Honest definitions (no hidden refitting):

* **mcar** — mask ``mᵢ ~ Bernoulli(rate)`` independent of the data.
* **mar** — ``P(M=1 | driver) = σ(a + s·z(driver))``; the intercept ``a`` is
  calibrated so the *expected* missing rate equals ``rate`` while missingness
  still depends on the **observed** driver.
* **mnar** — same logistic mechanism but on the column's **own value** (or an
  unobserved driver): missingness depends on the value itself.
* **label_noise** — flip a boolean label / reassign a categorical label to a
  *different* class with probability ``rate``.
* **feature_noise** — additive ``x' = x + ε``, ``ε ~ dist(params)``.
* **drift** — concept drift over the row index: ``x'[t] = x[t] + magnitude·g(t)``
  (``g`` linear ``t/(n-1)`` or a step).
* **covariate_shift** — affine moment-match toward a target ``{mean, std}``.
* **leakage** — plant ``into = target + small noise``: a high-MI proxy for the
  label.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from ..dist.builtins import REGISTRY
from ..errors import SpecValidationError
from ..spec.models import (
    BooleanFeature,
    CategoricalFeature,
    Feature,
    NumericFeature,
)
from .base import (
    FailureMode,
    calibrate_logistic_intercept,
    require_feature,
    require_rate,
    sigmoid,
    standardize,
)

# --- shared helpers ------------------------------------------------------------------


def _nullify(frame: pd.DataFrame, col: str, mask: np.ndarray) -> int:
    """Set ``NaN`` where ``mask`` is true, upcasting int/bool columns as needed."""
    series = frame[col]
    if pd.api.types.is_integer_dtype(series):
        frame[col] = series.astype("float64")
    elif pd.api.types.is_bool_dtype(series):
        frame[col] = series.astype("object")
    frame.loc[mask, col] = np.nan
    return int(mask.sum())


def _is_int_feature(feat: Feature | None) -> bool:
    return isinstance(feat, NumericFeature) and feat.dtype == "int"


def _assign_numeric(frame: pd.DataFrame, col: str, values: np.ndarray, is_int: bool) -> None:
    """Write a numeric result, rounding to int only when safe.

    A prior failure may have already nullified some cells; ``NaN`` cannot be cast
    to ``int64``, so we keep the column float in that case to preserve the
    injected missingness rather than corrupting it into garbage integers.
    """
    if is_int and not np.isnan(values).any():
        frame[col] = np.rint(values).astype("int64")
    else:
        frame[col] = values


def _require_float_coercible(
    name: str, features: Mapping[str, Feature], role: str, locator: str
) -> None:
    """A logistic driver must be numeric/boolean (``standardize`` coerces to float)."""
    feat = features[name]
    if not isinstance(feat, (NumericFeature, BooleanFeature)):
        raise SpecValidationError(
            f"{role} {name!r} must be numeric/boolean; it is type {feat.type!r}",
            locator=locator,
        )


def _logistic_missing(
    rng: np.random.Generator,
    driver_values: np.ndarray,
    rate: float,
    strength: float,
) -> np.ndarray:
    """Draw a calibrated, driver-dependent missingness mask."""
    scores = strength * standardize(driver_values)
    intercept = calibrate_logistic_intercept(scores, rate)
    probs = sigmoid(intercept + scores)
    return rng.random(len(driver_values)) < probs


# --- missingness ---------------------------------------------------------------------


class MCAR(FailureMode):
    name = "mcar"

    def _columns(self, params: Mapping[str, Any]) -> list[str]:
        cols = params.get("columns")
        if isinstance(cols, list):
            return [str(c) for c in cols]
        col = params.get("column")
        return [str(col)] if col is not None else []

    def validate(self, params, features, locator):
        require_rate(params, locator)
        cols = self._columns(params)
        if not cols:
            raise SpecValidationError(
                "mcar requires 'column' or 'columns'", locator=f"{locator}.columns"
            )
        for c in cols:
            if c not in features:
                raise SpecValidationError(
                    f"column {c!r} is not a declared feature", locator=f"{locator}.columns"
                )

    def apply(self, rng, frame, params, features):
        rate = float(params["rate"])
        n = len(frame)
        nulled: dict[str, float] = {}
        for col in self._columns(params):
            mask = rng.random(n) < rate
            count = _nullify(frame, col, mask)
            nulled[col] = count / n if n else 0.0
        return {"mechanism": "mcar", "rate": rate, "nullified_fraction": nulled}


class MAR(FailureMode):
    name = "mar"

    def validate(self, params, features, locator):
        require_rate(params, locator)
        require_feature(params, "column", features, locator)
        driver = require_feature(params, "driver", features, locator)
        _require_float_coercible(driver, features, "mar 'driver'", f"{locator}.driver")

    def apply(self, rng, frame, params, features):
        rate = float(params["rate"])
        column = str(params["column"])
        driver = str(params["driver"])
        strength = float(params.get("strength", 2.0))
        mask = _logistic_missing(rng, frame[driver].to_numpy(), rate, strength)
        n = len(frame)
        count = _nullify(frame, column, mask)
        return {
            "mechanism": "mar",
            "column": column,
            "driver": driver,
            "target_rate": rate,
            "realized_rate": count / n if n else 0.0,
        }


class MNAR(FailureMode):
    name = "mnar"

    def validate(self, params, features, locator):
        require_rate(params, locator)
        column = require_feature(params, "column", features, locator)
        # `driver` is optional for MNAR (defaults to the column's own value).
        driver = params.get("driver")
        if driver is not None:
            driver = require_feature(params, "driver", features, locator)
        effective = str(driver or column)
        _require_float_coercible(effective, features, "mnar driver", f"{locator}.driver")

    def apply(self, rng, frame, params, features):
        rate = float(params["rate"])
        column = str(params["column"])
        driver = str(params.get("driver") or column)
        strength = float(params.get("strength", 2.0))
        mask = _logistic_missing(rng, frame[driver].to_numpy(), rate, strength)
        n = len(frame)
        count = _nullify(frame, column, mask)
        return {
            "mechanism": "mnar",
            "column": column,
            "driver": driver,
            "self_dependent": driver == column,
            "target_rate": rate,
            "realized_rate": count / n if n else 0.0,
        }


# --- label / feature corruption ------------------------------------------------------


class LabelNoise(FailureMode):
    name = "label_noise"

    def validate(self, params, features, locator):
        require_rate(params, locator)
        col = require_feature(params, "column", features, locator)
        feat = features[col]
        if not isinstance(feat, (BooleanFeature, CategoricalFeature)):
            raise SpecValidationError(
                f"label_noise requires a boolean/categorical 'column'; {col!r} is "
                f"type {feat.type!r}",
                locator=f"{locator}.column",
            )

    def apply(self, rng, frame, params, features):
        rate = float(params["rate"])
        column = str(params["column"])
        n = len(frame)
        flip = rng.random(n) < rate
        feat = features.get(column)
        series = frame[column]

        if pd.api.types.is_bool_dtype(series) or isinstance(feat, BooleanFeature):
            vals = series.to_numpy(dtype=bool)
            frame[column] = np.where(flip, ~vals, vals)
            flipped = int(flip.sum())
        else:
            cats = (
                list(feat.categories)
                if isinstance(feat, CategoricalFeature)
                else sorted(series.dropna().unique().tolist())
            )
            k = len(cats)
            if k < 2:
                return {"mechanism": "label_noise", "column": column, "flipped_fraction": 0.0}
            index = {c: i for i, c in enumerate(cats)}
            codes = series.map(index).to_numpy()
            # Reassign flipped rows to a *different* class (offset in 1..k-1).
            offset = rng.integers(1, k, size=n)
            new_codes = (codes + offset) % k
            arr = series.to_numpy(dtype=object).copy()
            cats_arr = np.array(cats, dtype=object)
            valid = flip & ~pd.isna(codes)
            arr[valid] = cats_arr[new_codes[valid].astype(int)]
            frame[column] = arr
            flipped = int(valid.sum())
        return {
            "mechanism": "label_noise",
            "column": column,
            "rate": rate,
            "flipped_fraction": flipped / n if n else 0.0,
        }


class FeatureNoise(FailureMode):
    name = "feature_noise"

    def validate(self, params, features, locator):
        col = require_feature(params, "column", features, locator)
        feat = features[col]
        if not isinstance(feat, NumericFeature):
            raise SpecValidationError(
                f"feature_noise requires a numeric 'column'; {col!r} is type {feat.type!r}",
                locator=f"{locator}.column",
            )
        dist_name = params.get("dist")
        if dist_name is None:
            raise SpecValidationError("feature_noise requires 'dist'", locator=f"{locator}.dist")
        dist = REGISTRY.get(str(dist_name))
        if dist is None:
            raise SpecValidationError(
                f"unknown noise distribution {dist_name!r}", locator=f"{locator}.dist"
            )
        dist.validate(params.get("params", {}), locator=f"{locator}.params")

    def apply(self, rng, frame, params, features):
        column = str(params["column"])
        n = len(frame)
        dist = REGISTRY[str(params["dist"])]
        eps = dist.sample(rng, n, params.get("params", {}))
        original = frame[column].to_numpy(dtype=float)
        noised = original + eps
        _assign_numeric(frame, column, noised, _is_int_feature(features.get(column)))
        return {
            "mechanism": "feature_noise",
            "column": column,
            "dist": str(params["dist"]),
            "realized_noise_std": float(np.std(eps)),
            "realized_mean_shift": float(np.nanmean(noised) - np.nanmean(original)),
        }


# --- distributional shifts -----------------------------------------------------------


class Drift(FailureMode):
    name = "drift"

    def validate(self, params, features, locator):
        col = require_feature(params, "column", features, locator)
        feat = features[col]
        if not isinstance(feat, NumericFeature):
            raise SpecValidationError(
                f"drift requires a numeric 'column'; {col!r} is type {feat.type!r}",
                locator=f"{locator}.column",
            )
        sched = params.get("schedule", {})
        if not isinstance(sched, Mapping):
            raise SpecValidationError("drift 'schedule' must be a mapping", locator=f"{locator}.schedule")
        kind = sched.get("kind", "linear")
        if kind not in ("linear", "step"):
            raise SpecValidationError(
                f"unknown drift schedule kind {kind!r} (expected 'linear' or 'step')",
                locator=f"{locator}.schedule.kind",
            )

    def apply(self, rng, frame, params, features):
        column = str(params["column"])
        n = len(frame)
        sched = dict(params.get("schedule", {}))
        kind = sched.get("kind", "linear")
        idx = np.arange(n, dtype=float)
        if kind == "step":
            at = float(sched.get("at", 0.5))
            g = (idx >= at * n).astype(float)
        else:  # linear
            g = idx / (n - 1) if n > 1 else np.zeros(n)
        magnitude = sched.get("magnitude")
        if magnitude is None:
            # `rate` reads as a per-row slope: total end-to-start shift = rate·(n-1).
            magnitude = float(sched.get("rate", 0.0)) * (n - 1)
        magnitude = float(magnitude)
        delta = magnitude * g
        shifted = frame[column].to_numpy(dtype=float) + delta
        _assign_numeric(frame, column, shifted, _is_int_feature(features.get(column)))
        half = n // 2
        first = float(np.nanmean(delta[:half])) if half else 0.0
        second = float(np.nanmean(delta[half:])) if n - half else 0.0
        return {
            "mechanism": "drift",
            "column": column,
            "kind": kind,
            "total_shift": magnitude,
            "mean_shift_second_vs_first_half": second - first,
        }


class CovariateShift(FailureMode):
    name = "covariate_shift"

    def validate(self, params, features, locator):
        col = require_feature(params, "column", features, locator)
        feat = features[col]
        if not isinstance(feat, NumericFeature):
            raise SpecValidationError(
                f"covariate_shift requires a numeric 'column'; {col!r} is type {feat.type!r}",
                locator=f"{locator}.column",
            )
        target = params.get("target")
        if not isinstance(target, Mapping) or not ({"mean", "std"} & set(target)):
            raise SpecValidationError(
                "covariate_shift requires a 'target' with 'mean' and/or 'std'",
                locator=f"{locator}.target",
            )

    def apply(self, rng, frame, params, features):
        column = str(params["column"])
        target = dict(params.get("target", {}))
        x = frame[column].to_numpy(dtype=float)
        mu = float(np.nanmean(x))
        sd = float(np.nanstd(x))
        tmean = float(target.get("mean", mu))
        tstd = target.get("std")
        if tstd is not None and sd > 0.0:
            shifted = (x - mu) * (float(tstd) / sd) + tmean
        else:
            shifted = x + (tmean - mu)
        _assign_numeric(frame, column, shifted, _is_int_feature(features.get(column)))
        return {
            "mechanism": "covariate_shift",
            "column": column,
            "before": {"mean": mu, "std": sd},
            "after": {"mean": float(np.nanmean(shifted)), "std": float(np.nanstd(shifted))},
        }


class Leakage(FailureMode):
    name = "leakage"

    def validate(self, params, features, locator):
        target = require_feature(params, "target", features, locator)
        feat = features[target]
        if not isinstance(feat, (NumericFeature, BooleanFeature)):
            raise SpecValidationError(
                f"leakage 'target' must be numeric/boolean; {target!r} is type {feat.type!r}",
                locator=f"{locator}.target",
            )
        into = params.get("into")
        if not isinstance(into, str):
            raise SpecValidationError("leakage requires 'into'", locator=f"{locator}.into")
        # `into` is the planted proxy column; it may be a *new* column. It must
        # not collide with the target itself.
        if into == target:
            raise SpecValidationError(
                "leakage 'into' must differ from 'target'", locator=f"{locator}.into"
            )

    def apply(self, rng, frame, params, features):
        target = str(params["target"])
        into = str(params["into"])
        tgt = frame[target].to_numpy(dtype=float)
        noise_level = float(params.get("noise", 0.05))
        sd = float(np.nanstd(tgt)) or 1.0
        proxy = tgt + rng.normal(0.0, noise_level * sd, len(frame))
        frame[into] = proxy
        # Realized leakage strength: Pearson correlation between proxy and target.
        with np.errstate(invalid="ignore"):
            corr = np.corrcoef(np.nan_to_num(proxy), np.nan_to_num(tgt))[0, 1]
        return {
            "mechanism": "leakage",
            "target": target,
            "into": into,
            "noise_level": noise_level,
            "realized_correlation": float(corr) if np.isfinite(corr) else None,
        }


FAILURE_MODES: dict[str, FailureMode] = {
    m.name: m
    for m in (
        MCAR(),
        MAR(),
        MNAR(),
        LabelNoise(),
        FeatureNoise(),
        Drift(),
        CovariateShift(),
        Leakage(),
    )
}
