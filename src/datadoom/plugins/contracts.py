"""Plugin author contract surface — re-exported as ``datadoom.plugin`` (09 §4).

A plugin is a small class implementing one of the engine's typed base classes.
This module re-exports those ABCs (so authors import them from a stable name that
does not change as the engine's internal layout evolves) and ships the tiny
``schema`` helper for declaring a plugin's ``param_schema`` JSON-schema fragment.

The canonical ABCs live in ``datadoom.engine`` — the engine *consumes* registered
plugin instances through the registry (it never imports ``datadoom.plugins``); the
registry mutates the engine's lookup tables in place (10 §4). Plugins therefore
depend only on these ABCs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from datadoom.engine.causal.functions import StructuralFn
from datadoom.engine.difficulty.probes import ProbeModel
from datadoom.engine.dist.base import Distribution
from datadoom.engine.export.base import Exporter
from datadoom.engine.failure.base import FailureMode

__all__ = [
    "Distribution",
    "StructuralFn",
    "FailureMode",
    "Exporter",
    "ProbeModel",
    "schema",
    "PLUGIN_BASES",
    "KEY_ATTR",
]

# Plugin kind -> the base class an instance must subclass. The order is the
# precedence used when resolving an object's kind (kinds are disjoint in practice).
PLUGIN_BASES: dict[str, type] = {
    "distribution": Distribution,
    "structural_fn": StructuralFn,
    "failure_mode": FailureMode,
    "exporter": Exporter,
    "probe_model": ProbeModel,
}

# The attribute that names each kind inside its registry. Exporters key on
# ``format`` (it matches ``export.formats[]``); everything else keys on ``name``.
KEY_ATTR: dict[str, str] = {
    "distribution": "name",
    "structural_fn": "name",
    "failure_mode": "name",
    "exporter": "format",
    "probe_model": "name",
}


def schema(
    properties: Mapping[str, Mapping[str, Any]],
    *,
    required: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Wrap a property map into a JSON-schema ``object`` the Canvas can render.

    ``param_schema = schema({"k": {"type": "number", "minimum": 0}})`` →
    ``{"type": "object", "properties": {...}, "required": [...]}``. The UI reads
    this fragment and renders form controls (number inputs with min/max, enums as
    dropdowns…) wherever the plugin is selectable, with no frontend changes (09 §6).
    """
    obj: dict[str, Any] = {"type": "object", "properties": dict(properties)}
    if required:
        obj["required"] = list(required)
    return obj
