"""The difficulty dial: knobs that make a dataset harder, baked into the frame.

The adaptive loop (``calibrate.py``) is a 1-D root-find — it can only bisect a
single monotone scalar. So the lean-default knob set is composed into **one
bisectable dial** ``d``:

    d ∈ [0, 1):  feature-observation noise η ramps 0 → η_max
    d ∈ [1, 2]:  η held at η_max, label-flip rate ρ ramps 0 → ρ_max

Feature noise is the primary lever — it adds Gaussian observation noise to the
numeric predictors while **leaving the authored causal graph untouched** (so the
``causal_truth`` report stays honest: the label still depends on the true
signal, the features are just noisier observations of it). Label flipping is the
deep-end extension used when feature noise saturates before reaching a very low
target band.

Determinism: the per-column noise draws and the label-flip draws are taken
*once* (independent of ``d``) and merely *scaled* by the dial. This makes the
realized frame a continuous, monotone function of ``d`` and guarantees the
flipped-row set is **nested** as ρ grows — clean monotonicity for the bisection,
and byte-identical output for a given final dial (invariant #6).

`causal` (coefficient shrink) and `imbalance` are recognized knob *names* in the
spec but are not active levers in v0.1; the calibrator reports which knobs it
actually used. See the difficulty backlog in ``status.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from ..rng import RNGFactory

# At η = η_max each numeric predictor receives additive noise with std equal to
# η_max × the feature's own (clean) standard deviation — a 1.5σ observation
# blur, enough to wash most linear signal out of a strong feature.
FEATURE_NOISE_MAX = 1.5
# Label flips top out at 0.5 — at which point a binary label is pure coin-flip
# (AUROC → 0.5), the hardest any classification task can be.
LABEL_FLIP_MAX = 0.5
# The dial spans the feature-noise region [0,1) then the label-noise region [1,2].
DIAL_MAX = 2.0

# Knob names the dial actively implements; others are accepted-but-inactive.
ACTIVE_KNOBS = ("noise", "label_noise")


@dataclass
class KnobState:
    """The decomposed knob values realized at a given dial position."""

    dial: float
    feature_noise: float  # realized η
    label_flip: float  # realized ρ

    def to_dict(self) -> dict[str, float]:
        return {"dial": self.dial, "feature_noise": self.feature_noise, "label_flip": self.label_flip}


class DifficultyDial:
    """Pre-draws the perturbations once, then realizes any dial position cheaply.

    Holding the draws fixed and scaling by the dial is what makes ``μ(d)``
    monotone (nested label flips, proportional feature blur) so the calibrator's
    bisection is well-posed.
    """

    def __init__(
        self,
        base: pd.DataFrame,
        label: str,
        rng: RNGFactory,
        knobs: list[str],
        used_namespaces: list[str],
    ) -> None:
        self.base = base
        self.label = label
        self.n = len(base)
        self.use_feature_noise = "noise" in knobs
        self.use_label_noise = "label_noise" in knobs

        # Numeric predictors only (booleans/categoricals/datetimes are left to
        # the label-flip lever; the label column itself is never blurred).
        self.numeric_cols: list[str] = [
            c
            for c in base.columns
            if c != label
            and pd.api.types.is_numeric_dtype(base[c])
            and not pd.api.types.is_bool_dtype(base[c])
        ]
        self._z: dict[str, np.ndarray] = {}
        self._sd: dict[str, float] = {}
        self._is_int: dict[str, bool] = {}
        if self.use_feature_noise:
            for c in self.numeric_cols:
                col = base[c]
                self._sd[c] = float(np.nanstd(col.to_numpy(dtype=float)))
                self._is_int[c] = pd.api.types.is_integer_dtype(col)
                self._z[c] = rng.difficulty(f"feature:{c}").standard_normal(self.n)
                used_namespaces.append(f"difficulty:feature:{c}")

        self._u: np.ndarray | None = None
        if self.use_label_noise:
            self._u = rng.difficulty("label").random(self.n)
            used_namespaces.append("difficulty:label")

    # --- dial → knob magnitudes -----------------------------------------------------
    def feature_noise_at(self, dial: float) -> float:
        if not self.use_feature_noise:
            return 0.0
        return min(dial, 1.0) * FEATURE_NOISE_MAX

    def label_flip_at(self, dial: float) -> float:
        if not self.use_label_noise:
            return 0.0
        return max(0.0, dial - 1.0) * LABEL_FLIP_MAX

    # --- realize a frame at a dial position -----------------------------------------
    def realize(self, dial: float) -> tuple[pd.DataFrame, KnobState]:
        eta = self.feature_noise_at(dial)
        rho = self.label_flip_at(dial)
        frame = self.base.copy()

        if eta > 0.0:
            for c in self.numeric_cols:
                sd = self._sd[c]
                if sd <= 0.0:
                    continue  # constant column — nothing to blur
                noisy = frame[c].to_numpy(dtype=float) + eta * sd * self._z[c]
                if self._is_int[c]:
                    frame[c] = np.rint(noisy).astype("int64")  # preserve int dtype
                else:
                    frame[c] = noisy

        if rho > 0.0 and self._u is not None:
            flip = self._u < rho  # nested as ρ grows → monotone
            frame[self.label] = _flip_label(frame[self.label], flip)

        return frame, KnobState(dial=dial, feature_noise=eta, label_flip=rho)

    def noise_to_signal(self, eta: float) -> float:
        """Var(ε)/Var(signal) for the feature noise (05 §5.4): equals η²."""
        return float(eta * eta) if self.numeric_cols else 0.0


def _flip_label(series: pd.Series, flip: np.ndarray) -> pd.Series:
    """Flip the selected label rows to a *different* class.

    Boolean → logical NOT; binary categorical → swap to the other category;
    k-ary categorical → rotate to the next category (deterministic, always a
    genuine change). Mirrors the ``label_noise`` failure mode's "flip to a
    different class" guarantee.
    """
    if pd.api.types.is_bool_dtype(series):
        out = series.to_numpy().copy()
        out[flip] = ~out[flip]
        return pd.Series(out, index=series.index)

    out = series.to_numpy().copy()
    categories = sorted(pd.unique(series.dropna()))
    if len(categories) < 2:
        return series  # nothing to flip into
    nxt = {c: categories[(i + 1) % len(categories)] for i, c in enumerate(categories)}
    flipped = np.array([nxt.get(v, v) for v in out[flip]], dtype=out.dtype)
    out[flip] = flipped
    return pd.Series(out, index=series.index)
