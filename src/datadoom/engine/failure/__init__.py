"""Failure injection — deterministic corruption transforms (05 §4, 04 §7).

A clean baseline is captured before injection and always preserved alongside the
injected variant. Each mode draws from ``RNG(failure:i)`` so the injected frame
is itself reproducible on the pinned path.
"""

from __future__ import annotations

from .apply import apply_failures
from .base import FailureMode
from .modes import FAILURE_MODES

__all__ = [
    "FailureMode",
    "FAILURE_MODES",
    "apply_failures",
]
