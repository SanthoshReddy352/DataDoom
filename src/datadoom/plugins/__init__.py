"""DataDoom plugin system — registry + loader + scaffolder (09, 17 step 17).

Plugins extend DataDoom *without forking core*: a small class implementing one of
the engine ABCs (re-exported as ``datadoom.plugin``) is discovered at startup and
inserted into the engine's lookup tables, so it works in the CLI, the API, and the
web UI with no core change. This package depends only on the engine (10 §4).
"""

from __future__ import annotations

from .contracts import (
    Distribution,
    Exporter,
    FailureMode,
    ProbeModel,
    StructuralFn,
    schema,
)
from .loader import default_plugins_dir, load_plugins
from .registry import (
    PluginConflictError,
    PluginError,
    PluginRecord,
    PluginRegistry,
    get_registry,
)
from .scaffold import ObjectCheck, check_object, check_plugin, scaffold_plugin

__all__ = [
    "Distribution",
    "StructuralFn",
    "FailureMode",
    "Exporter",
    "ProbeModel",
    "schema",
    "load_plugins",
    "default_plugins_dir",
    "get_registry",
    "PluginRegistry",
    "PluginRecord",
    "PluginError",
    "PluginConflictError",
    "scaffold_plugin",
    "check_plugin",
    "check_object",
    "ObjectCheck",
]
