"""Failure-injection orchestration (03 §4 stage 6, 05 §4).

Captures the clean baseline, then applies the spec's ordered failure list to a
copy, each mode drawing from its own ``RNG(failure:i)``. Returns the injected
frame and the per-mode diff summaries. The clean frame is never mutated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from .modes import FAILURE_MODES

if TYPE_CHECKING:  # avoid a runtime import cycle with pipeline
    from ..pipeline import RunContext


def apply_failures(ctx: RunContext, clean: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Apply the spec's failures in order to a copy of ``clean``.

    Returns ``(injected_frame, diffs)`` where each diff records the mode and its
    realized effect. ``ctx.used_namespaces`` gains a ``failure:i`` entry per mode
    so the determinism report covers the injected stream too.
    """
    injected = clean.copy(deep=True)
    diffs: list[dict[str, Any]] = []
    for i, failure in enumerate(ctx.spec.failures):
        mode = FAILURE_MODES[failure.type]
        params = failure.model_dump()
        params.pop("type", None)
        rng = ctx.rng.failure(i)
        ctx.used_namespaces.append(f"failure:{i}")
        summary = mode.apply(rng, injected, params, ctx.spec.features)
        diffs.append({"index": i, "type": failure.type, **summary})
    return injected, diffs
