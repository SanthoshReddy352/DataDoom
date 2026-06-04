"""Difficulty targeting: empirical calibration to a baseline-metric band (05 §5).

A dataset's difficulty is defined *operationally* by the score a standard probe
model achieves on it. ``calibrate_difficulty`` runs an adaptive bisection over a
single :class:`~datadoom.engine.difficulty.knobs.DifficultyDial` until the probe
metric lands in the target band, then returns the calibrated frame to ship and a
report of what was achieved (honestly, including misses).
"""

from __future__ import annotations

from .calibrate import (
    TIER_BANDS,
    DifficultyResult,
    Target,
    calibrate_difficulty,
    resolve_target,
)
from .knobs import ACTIVE_KNOBS, DIAL_MAX, DifficultyDial, KnobState
from .probes import PROBES, ProbeModel, ProbeResult, evaluate

__all__ = [
    "ACTIVE_KNOBS",
    "DIAL_MAX",
    "DifficultyDial",
    "DifficultyResult",
    "KnobState",
    "PROBES",
    "ProbeModel",
    "ProbeResult",
    "TIER_BANDS",
    "Target",
    "calibrate_difficulty",
    "evaluate",
    "resolve_target",
]
