"""In-memory plugin registry (09 §3, 17 step 17).

The registry is the single place that knows *every* capability available to a
run — both core built-ins and discovered plugins. Registering a plugin inserts
its instance into the matching **engine lookup table** (the same dict the
pipeline reads by name), so a registered distribution/fn/failure/exporter/probe
is picked up with no engine change. The engine never imports this module; the
dependency points the other way (``engine ← plugins``, 10 §4).

Conflicts (a plugin reusing a built-in or another plugin's name) fail loudly so
an install never silently shadows a capability.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from .contracts import KEY_ATTR, PLUGIN_BASES


class PluginError(Exception):
    """A plugin failed validation (wrong base class, bad schema, missing name)."""


class PluginConflictError(PluginError):
    """Two capabilities of the same kind claim the same name."""


_ALLOWED_SCHEMA_TYPES = {"object", "string", "number", "integer", "boolean", "array", "null"}


@dataclass(frozen=True)
class PluginRecord:
    """Metadata for one registered capability (built-in or plugin)."""

    name: str
    kind: str
    source: str  # "builtin" | "entrypoint" | "local"
    module: str | None = None
    version: str | None = None
    schema: dict[str, Any] | None = None

    @property
    def builtin(self) -> bool:
        return self.source == "builtin"

    def to_info(self) -> dict[str, Any]:
        """Shape consumed by ``GET /api/plugins`` (08 §10)."""
        return {
            "name": self.name,
            "kind": self.kind,
            "version": self.version,
            "schema": self.schema,
            "source": self.source,
            "builtin": self.builtin,
            "enabled": True,
        }


def resolve_kind(obj: object) -> str | None:
    """Return the plugin kind ``obj`` (an instance) implements, or ``None``."""
    for kind, base in PLUGIN_BASES.items():
        if isinstance(obj, base):
            return kind
    return None


def resolve_kind_class(cls: object) -> str | None:
    """Return the plugin kind a *class* implements, or ``None`` (skips the ABCs)."""
    if not isinstance(cls, type):
        return None
    for kind, base in PLUGIN_BASES.items():
        if cls is not base and issubclass(cls, base):
            return kind
    return None


def validate_param_schema(schema: object, *, where: str = "param_schema") -> None:
    """Lightweight sanity check that ``schema`` is a renderable JSON-schema fragment."""
    if not isinstance(schema, dict):
        raise PluginError(f"{where} must be a dict (use the schema() helper)")
    stype = schema.get("type")
    if stype is not None and stype not in _ALLOWED_SCHEMA_TYPES:
        raise PluginError(f"{where} has unsupported type {stype!r}")
    props = schema.get("properties")
    if stype == "object" and not isinstance(props, dict):
        raise PluginError(f"{where} of type 'object' needs a 'properties' dict")
    if isinstance(props, dict):
        for pname, pspec in props.items():
            if not isinstance(pspec, dict):
                raise PluginError(f"{where}.properties[{pname!r}] must be a dict")
            ptype = pspec.get("type")
            if ptype is not None and ptype not in _ALLOWED_SCHEMA_TYPES:
                raise PluginError(f"{where}.properties[{pname!r}] has unsupported type {ptype!r}")


def _engine_registries() -> dict[str, MutableMapping[str, Any]]:
    """The five live engine lookup tables, keyed by plugin kind.

    Imported lazily so this module loads without forcing the whole engine, and so
    the dicts are the *canonical* objects the pipeline reads (mutating them in
    place propagates to every ``from ... import REGISTRY`` reference).
    """
    from datadoom.engine.causal.functions import STRUCTURAL_FNS
    from datadoom.engine.difficulty.probes import PROBES
    from datadoom.engine.dist.builtins import REGISTRY
    from datadoom.engine.export import EXPORTERS
    from datadoom.engine.failure.modes import FAILURE_MODES

    return {
        "distribution": REGISTRY,
        "structural_fn": STRUCTURAL_FNS,
        "failure_mode": FAILURE_MODES,
        "exporter": EXPORTERS,
        "probe_model": PROBES,
    }


class PluginRegistry:
    """Tracks records and keeps the engine lookup tables in sync."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], PluginRecord] = {}
        self._builtins_seeded = False

    def seed_builtins(self) -> None:
        """Record the core built-ins already present in the engine tables (idempotent)."""
        if self._builtins_seeded:
            return
        for kind, reg in _engine_registries().items():
            for key, obj in reg.items():
                self._records[(kind, key)] = PluginRecord(
                    name=key,
                    kind=kind,
                    source="builtin",
                    module=type(obj).__module__,
                    schema=_schema_of(obj),
                )
        self._builtins_seeded = True

    def register(
        self,
        obj: object,
        *,
        source: str,
        module: str | None = None,
        version: str | None = None,
    ) -> PluginRecord:
        """Validate ``obj`` and insert it into its engine table. Raise on conflict."""
        kind = resolve_kind(obj)
        if kind is None:
            bases = ", ".join(PLUGIN_BASES)
            raise PluginError(
                f"{type(obj).__name__} is not a plugin: it must subclass one of [{bases}]"
            )
        key_attr = KEY_ATTR[kind]
        key = getattr(obj, key_attr, None)
        if not isinstance(key, str) or not key:
            raise PluginError(
                f"{kind} plugin {type(obj).__name__} must set a non-empty '{key_attr}'"
            )
        if (kind, key) in self._records:
            existing = self._records[(kind, key)]
            raise PluginConflictError(
                f"{kind} {key!r} is already registered (source={existing.source}); "
                "capability names must be unique within an install"
            )
        schema = _schema_of(obj)
        if schema is not None:
            validate_param_schema(schema, where=f"{kind} {key!r} param_schema")

        _engine_registries()[kind][key] = obj
        record = PluginRecord(
            name=key,
            kind=kind,
            source=source,
            module=module or type(obj).__module__,
            version=version,
            schema=schema,
        )
        self._records[(kind, key)] = record
        return record

    def records(self) -> list[PluginRecord]:
        return sorted(self._records.values(), key=lambda r: (r.kind, r.name))

    def to_info(self) -> list[dict[str, Any]]:
        return [r.to_info() for r in self.records()]

    def get(self, kind: str, name: str) -> PluginRecord | None:
        return self._records.get((kind, name))

    def reset(self) -> None:
        """Remove every non-built-in from the engine tables and records (test aid)."""
        regs = _engine_registries()
        for (kind, key), rec in list(self._records.items()):
            if rec.source != "builtin":
                regs[kind].pop(key, None)
                del self._records[(kind, key)]


def _schema_of(obj: object) -> dict[str, Any] | None:
    schema = getattr(obj, "param_schema", None)
    return dict(schema) if isinstance(schema, dict) else None


_DEFAULT = PluginRegistry()


def get_registry() -> PluginRegistry:
    """The process-wide registry (shared by the API, CLI, and engine tables)."""
    return _DEFAULT
