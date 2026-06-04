"""Plugin system: registry, loader, scaffolder, and the contract checks (13 §5).

Covers task 17: built-ins register with the right kind and all pass the contract;
a registered plugin flows through the *engine* (a run uses it); discovery via the
local directory and entry points; conflict-fail; and the contract checker catches
non-deterministic / RNG-impure / bad-schema plugins.
"""

from __future__ import annotations

import tempfile
import types
from pathlib import Path

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.causal.functions import STRUCTURAL_FNS
from datadoom.engine.difficulty.probes import PROBES
from datadoom.engine.dist.builtins import REGISTRY
from datadoom.engine.export import EXPORTERS
from datadoom.engine.failure.modes import FAILURE_MODES
from datadoom.plugin import Distribution, schema
from datadoom.plugins import (
    PluginConflictError,
    PluginError,
    PluginRegistry,
    check_object,
    check_plugin,
    load_plugins,
    scaffold_plugin,
)
from datadoom.plugins import loader as loader_mod

_ENGINE_DICTS = [REGISTRY, STRUCTURAL_FNS, FAILURE_MODES, EXPORTERS, PROBES]


@pytest.fixture
def registry() -> PluginRegistry:
    """A fresh registry; any capability it adds to the engine tables is removed after."""
    baselines = [set(d.keys()) for d in _ENGINE_DICTS]
    reg = PluginRegistry()
    reg.seed_builtins()
    yield reg
    for d, base in zip(_ENGINE_DICTS, baselines, strict=True):
        for key in list(d.keys()):
            if key not in base:
                del d[key]


# --- sample plugins (module-level so RNG-hygiene `getsource` works) ------------------


class WeibullDistribution(Distribution):
    name = "weibull"
    required_params = ("k", "lam")
    param_schema = schema(
        {"k": {"type": "number", "minimum": 0}, "lam": {"type": "number", "minimum": 0}}
    )
    example_params = {"k": 1.5, "lam": 2.0}

    def sample(self, rng, n, params):
        return params["lam"] * rng.weibull(params["k"], size=n)

    def cdf(self, x, params):
        return 1.0 - np.exp(-((np.asarray(x, dtype=float) / params["lam"]) ** params["k"]))


class NonDeterministicDistribution(Distribution):
    name = "nondet"
    example_params = {}

    def sample(self, rng, n, params):
        # BAD: a fresh global generator ignores the injected, seeded rng.
        return np.random.default_rng().normal(size=n)

    def cdf(self, x, params):
        return np.zeros_like(np.asarray(x, dtype=float))


# --- built-ins -----------------------------------------------------------------------


def test_builtins_registered(registry: PluginRegistry) -> None:
    records = registry.records()
    by_kind: dict[str, int] = {}
    for r in records:
        assert r.builtin and r.source == "builtin"
        by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
    assert by_kind == {
        "distribution": 6,
        "structural_fn": 5,
        "failure_mode": 8,
        "exporter": 3,
        "probe_model": 2,
    }


def test_builtins_pass_contract(registry: PluginRegistry) -> None:
    from datadoom.plugins.registry import PLUGIN_BASES, _engine_registries

    for kind, reg in _engine_registries().items():
        for obj in reg.values():
            report = check_object(obj)
            assert report.kind == kind
            assert report.ok, report.summary()
    assert set(PLUGIN_BASES) == {
        "distribution",
        "structural_fn",
        "failure_mode",
        "exporter",
        "probe_model",
    }


# --- registration flows through the engine -------------------------------------------


def test_registered_distribution_used_by_engine(registry: PluginRegistry) -> None:
    registry.register(WeibullDistribution(), source="entrypoint", version="0.1.0")
    assert "weibull" in REGISTRY  # the canonical table the pipeline reads

    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "wb",
            "rows": 4000,
            "features": {"x": {"type": "numeric", "dist": "weibull", "params": {"k": 1.5, "lam": 2.0}}},
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = generate(spec, seed=7, out_dir=tmp)
    # E[X] = lam * Γ(1 + 1/k) ≈ 2 * 0.9027 ≈ 1.805
    assert len(result.frame) == 4000
    assert abs(float(result.frame["x"].mean()) - 1.805) < 0.1


def test_conflict_fails_loudly(registry: PluginRegistry) -> None:
    registry.register(WeibullDistribution(), source="entrypoint")
    with pytest.raises(PluginConflictError):
        registry.register(WeibullDistribution(), source="local")
    # A plugin reusing a *built-in* name also conflicts.

    class ShadowNormal(Distribution):
        name = "normal"

        def sample(self, rng, n, params):
            return rng.normal(size=n)

        def cdf(self, x, params):
            return np.zeros_like(np.asarray(x, dtype=float))

    with pytest.raises(PluginConflictError):
        registry.register(ShadowNormal(), source="local")


def test_register_rejects_non_plugin(registry: PluginRegistry) -> None:
    with pytest.raises(PluginError):
        registry.register(object(), source="local")


# --- discovery -----------------------------------------------------------------------


def test_local_dir_discovery(registry: PluginRegistry, tmp_path: Path) -> None:
    plugin_file = tmp_path / "my_plugin.py"
    plugin_file.write_text(
        "from datadoom.plugin import Distribution\n"
        "import numpy as np\n"
        "class TriDist(Distribution):\n"
        "    name = 'triangular_demo'\n"
        "    def sample(self, rng, n, params):\n"
        "        return rng.triangular(0, 0.5, 1, size=n)\n"
        "    def cdf(self, x, params):\n"
        "        return np.zeros_like(np.asarray(x, dtype=float))\n",
        encoding="utf-8",
    )
    loaded = loader_mod.load_local_dir(registry, tmp_path)
    assert "distribution:triangular_demo" in loaded
    assert "triangular_demo" in REGISTRY


def test_entry_point_discovery(registry: PluginRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = types.SimpleNamespace(
        name="weibull",
        dist=types.SimpleNamespace(version="9.9"),
        load=lambda: WeibullDistribution,
    )

    def fake_entry_points(*, group: str):
        return [fake] if group == loader_mod.ENTRY_POINT_GROUP else []

    monkeypatch.setattr(loader_mod, "entry_points", fake_entry_points)
    loaded = loader_mod.load_entry_points(registry)
    assert loaded == ["distribution:weibull"]
    assert registry.get("distribution", "weibull").version == "9.9"


def test_load_plugins_idempotent_builtins() -> None:
    # Calling load_plugins twice on the shared registry must not double-count/conflict.
    reg1 = load_plugins(use_local=False, use_entry_points=False)
    n1 = len(reg1.records())
    reg2 = load_plugins(use_local=False, use_entry_points=False)
    assert reg1 is reg2
    assert len(reg2.records()) == n1 == 24


# --- contract checker ----------------------------------------------------------------


def test_checker_flags_nondeterministic_and_impure() -> None:
    report = check_object(NonDeterministicDistribution())
    statuses = {check: status for check, status, _ in report.results}
    assert statuses["determinism"] == "fail"
    assert statuses["rng_hygiene"] == "fail"
    assert not report.ok


def test_checker_flags_bad_schema() -> None:
    class BadSchema(Distribution):
        name = "bad_schema"
        param_schema = {"type": "object", "properties": "not-a-dict"}

        def sample(self, rng, n, params):
            return rng.normal(size=n)

        def cdf(self, x, params):
            return np.zeros_like(np.asarray(x, dtype=float))

    report = check_object(BadSchema())
    statuses = {check: status for check, status, _ in report.results}
    assert statuses["schema"] == "fail"
    assert not report.ok


# --- scaffolder ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "kind", ["distribution", "structural_fn", "failure_mode", "exporter", "probe_model"]
)
def test_scaffold_then_check_passes(kind: str, tmp_path: Path) -> None:
    short = kind.split("_")[0]
    root = scaffold_plugin(kind, f"demo{short}", tmp_path)
    assert (root / "pyproject.toml").exists()
    init = root / "src" / f"datadoom_plugin_demo{short}" / "__init__.py"
    assert init.exists()
    reports = check_plugin(init)
    assert reports and all(r.ok for r in reports), "\n".join(r.summary() for r in reports)


def test_scaffold_rejects_bad_inputs(tmp_path: Path) -> None:
    with pytest.raises(PluginError):
        scaffold_plugin("not_a_kind", "foo", tmp_path)
    with pytest.raises(PluginError):
        scaffold_plugin("distribution", "Bad-Name", tmp_path)
