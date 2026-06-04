"""Plugin discovery + loading (09 §3, 17 step 17).

Two mechanisms resolve into the in-memory :class:`PluginRegistry` at server/CLI
startup:

1. **Python entry points** under the ``datadoom.plugins`` group (preferred for
   published ``datadoom-plugin-*`` packages).
2. **A local plugins directory** (``$DATADOOM_HOME/plugins/*.py``) auto-imported
   for prototyping and per-project plugins.

Each discovered object is registered (validated + inserted into the engine
tables). Conflicts and broken plugins fail loudly with a clear message rather
than silently degrading a run.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from importlib.metadata import entry_points
from pathlib import Path
from types import ModuleType

from .registry import PluginError, PluginRegistry, get_registry, resolve_kind_class

ENTRY_POINT_GROUP = "datadoom.plugins"


def default_plugins_dir() -> Path:
    """``$DATADOOM_HOME/plugins`` (or ``~/.datadoom/plugins``).

    Resolved from the environment directly so this package depends only on the
    engine (it does not import ``datadoom.config``).
    """
    home_env = os.environ.get("DATADOOM_HOME")
    home = Path(home_env).expanduser() if home_env else Path.home() / ".datadoom"
    return home / "plugins"


def _instantiate(target: object, *, where: str) -> object:
    """Coerce an entry-point/discovered target to a plugin *instance*."""
    if inspect.isclass(target):
        try:
            return target()
        except Exception as exc:  # noqa: BLE001 - surface as a clean plugin error
            raise PluginError(f"could not instantiate {where}: {exc}") from exc
    return target


def load_entry_points(registry: PluginRegistry) -> list[str]:
    """Register every plugin advertised under the ``datadoom.plugins`` group."""
    loaded: list[str] = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            target = ep.load()
        except Exception as exc:  # noqa: BLE001
            raise PluginError(f"entry point {ep.name!r} failed to import: {exc}") from exc
        obj = _instantiate(target, where=f"entry point {ep.name!r}")
        version = _dist_version(ep)
        record = registry.register(obj, source="entrypoint", version=version)
        loaded.append(f"{record.kind}:{record.name}")
    return loaded


def load_local_dir(registry: PluginRegistry, directory: Path) -> list[str]:
    """Import every ``*.py`` in ``directory`` and register the plugin classes it defines."""
    loaded: list[str] = []
    if not directory.is_dir():
        return loaded
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _import_path(path)
        for _, member in inspect.getmembers(module, inspect.isclass):
            # Only classes *defined here* (skip the imported ABCs themselves).
            if member.__module__ != module.__name__:
                continue
            if resolve_kind_class(member) is None:
                continue
            record = registry.register(member(), source="local", module=str(path))
            loaded.append(f"{record.kind}:{record.name}")
    return loaded


def _import_path(path: Path) -> ModuleType:
    mod_name = f"datadoom_local_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise PluginError(f"could not load local plugin {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        sys.modules.pop(mod_name, None)
        raise PluginError(f"local plugin {path.name} failed to import: {exc}") from exc
    return module


def _dist_version(ep: object) -> str | None:
    dist = getattr(ep, "dist", None)
    return getattr(dist, "version", None) if dist is not None else None


def load_plugins(
    registry: PluginRegistry | None = None,
    *,
    use_entry_points: bool = True,
    local_dir: Path | None = None,
    use_local: bool = True,
) -> PluginRegistry:
    """Seed built-ins, then discover entry-point and local-directory plugins.

    Idempotent for built-ins; intended to be called once at startup. ``local_dir``
    defaults to :func:`default_plugins_dir` when ``use_local`` is set.
    """
    registry = registry or get_registry()
    registry.seed_builtins()
    if use_entry_points:
        load_entry_points(registry)
    if use_local:
        load_local_dir(registry, local_dir or default_plugins_dir())
    return registry
