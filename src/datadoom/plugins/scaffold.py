"""Plugin authoring workflow: scaffolder + contract checker (09 §9, 17 step 17).

``scaffold_plugin`` writes a ready-to-publish ``datadoom-plugin-*`` package (entry
point, base-class stub, contract test, README) so a contributor starts from a
working, deterministic plugin. ``check_object`` / ``check_plugin`` run the plugin
contract tests (13 §5): interface completeness, schema validity, determinism, and
a static RNG-hygiene scan — the same checks that gate the ecosystem.
"""

from __future__ import annotations

import importlib.util
import inspect
import io
import re
import sys
import tempfile
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .contracts import KEY_ATTR, PLUGIN_BASES
from .registry import PluginError, resolve_kind, resolve_kind_class, validate_param_schema

# stdlib/global sources of non-reproducible randomness, banned in the data path (09 §5).
_BANNED_RNG = re.compile(
    r"\b(np|numpy)\.random\.|(?<![\w.])random\.|\buuid4\b|\btime\.time\b|"
    r"\bdatetime\.now\b|\bsecrets\.",
)

_KIND_SUFFIX = {
    "distribution": "Distribution",
    "structural_fn": "StructuralFn",
    "failure_mode": "FailureMode",
    "exporter": "Exporter",
    "probe_model": "ProbeModel",
}


# --- contract checking ---------------------------------------------------------------


@dataclass
class ObjectCheck:
    """Result of running the plugin contract on a single instance."""

    name: str
    kind: str | None
    results: list[tuple[str, str, str]] = field(default_factory=list)  # (check, status, detail)

    @property
    def ok(self) -> bool:
        return all(status != "fail" for _, status, _ in self.results)

    def add(self, check: str, status: str, detail: str = "") -> None:
        self.results.append((check, status, detail))

    def summary(self) -> str:
        head = f"{self.name} ({self.kind or 'unknown kind'})"
        lines = [
            f"  [{status.upper():4}] {check}" + (f" - {detail}" if detail else "")
            for check, status, detail in self.results
        ]
        return "\n".join([head, *lines])


def check_object(obj: object) -> ObjectCheck:
    """Run interface / schema / determinism / RNG-hygiene checks on one plugin instance."""
    kind = resolve_kind(obj)
    report = ObjectCheck(name=type(obj).__name__, kind=kind)

    if kind is None:
        report.add("interface", "fail", "does not subclass a known plugin base")
        return report
    key_attr = KEY_ATTR[kind]
    key = getattr(obj, key_attr, None)
    if not isinstance(key, str) or not key:
        report.add("interface", "fail", f"missing non-empty '{key_attr}'")
    else:
        report.add("interface", "pass", f"{key_attr}={key!r}")

    schema = getattr(obj, "param_schema", None)
    if schema is None:
        report.add("schema", "skip", "no param_schema (uses native UI controls)")
    else:
        try:
            validate_param_schema(schema)
            report.add("schema", "pass", "valid JSON-schema fragment")
        except PluginError as exc:
            report.add("schema", "fail", str(exc))

    _check_determinism(obj, kind, report)
    _check_rng_hygiene(obj, report)
    return report


def _check_determinism(obj: object, kind: str, report: ObjectCheck) -> None:
    try:
        if kind == "distribution":
            params = getattr(obj, "example_params", None)
            if not isinstance(params, dict):
                report.add("determinism", "skip", "set `example_params` for an auto-check")
                return
            a = obj.sample(np.random.default_rng(0), 256, params)  # type: ignore[attr-defined]
            b = obj.sample(np.random.default_rng(0), 256, params)  # type: ignore[attr-defined]
            ok = np.array_equal(np.asarray(a), np.asarray(b))
            report.add("determinism", "pass" if ok else "fail", "256 draws, two seeded RNGs")
        elif kind == "exporter":
            df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
            with tempfile.TemporaryDirectory() as tmp:
                p1, p2 = Path(tmp) / "1", Path(tmp) / "2"
                obj.write(df, p1)  # type: ignore[attr-defined]
                obj.write(df, p2)  # type: ignore[attr-defined]
                ok = p1.read_bytes() == p2.read_bytes()
            report.add("determinism", "pass" if ok else "fail", "byte-stable on two writes")
        else:
            report.add(
                "determinism", "skip", f"{kind} determinism is covered by its engine tests"
            )
    except Exception as exc:  # noqa: BLE001
        report.add("determinism", "fail", f"raised {type(exc).__name__}: {exc}")


def _strip_noncode(source: str) -> str:
    """Blank out comments and string literals, preserving layout, so the RNG-hygiene
    scan never trips on the word "random" in a docstring or comment."""
    lines = [list(line) for line in source.splitlines(keepends=True)]
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type not in (tokenize.COMMENT, tokenize.STRING):
                continue
            (sr, sc), (er, ec) = tok.start, tok.end
            for r in range(sr, er + 1):
                row = lines[r - 1]
                c0 = sc if r == sr else 0
                c1 = ec if r == er else len(row)
                for c in range(c0, min(c1, len(row))):
                    if row[c] != "\n":
                        row[c] = " "
    except (tokenize.TokenError, IndentationError):
        return source
    return "".join("".join(row) for row in lines)


def _check_rng_hygiene(obj: object, report: ObjectCheck) -> None:
    try:
        source = inspect.getsource(type(obj))
    except (OSError, TypeError):
        report.add("rng_hygiene", "skip", "source unavailable")
        return
    hits = sorted({m.group(0) for m in _BANNED_RNG.finditer(_strip_noncode(source))})
    if hits:
        report.add(
            "rng_hygiene", "fail", "use the injected rng only; found " + ", ".join(hits)
        )
    else:
        report.add("rng_hygiene", "pass", "uses only the injected rng")


def check_plugin(target: str | Path) -> list[ObjectCheck]:
    """Check every plugin class defined by a ``.py`` file, a directory, or a module.

    A directory is searched (non-recursively into ``build``/``tests``) for files
    that define plugin classes; each is imported in isolation and checked.
    """
    path = Path(target)
    if path.suffix == ".py" and path.is_file():
        files = [path]
    elif path.is_dir():
        files = [
            p
            for p in sorted(path.rglob("*.py"))
            if not any(part in {"build", "dist", ".venv", "tests", "__pycache__"} for part in p.parts)
        ]
    else:
        raise PluginError(f"nothing to check at {target!r} (expected a .py file or directory)")

    reports: list[ObjectCheck] = []
    seen: set[str] = set()
    for file in files:
        module = _import_file(file)
        for _, member in inspect.getmembers(module, inspect.isclass):
            if member.__module__ != module.__name__:
                continue
            if resolve_kind_class(member) is None:
                continue
            if member.__qualname__ in seen:
                continue
            seen.add(member.__qualname__)
            try:
                instance = member()
            except Exception as exc:  # noqa: BLE001
                bad = ObjectCheck(name=member.__name__, kind=resolve_kind_class(member))
                bad.add("interface", "fail", f"could not instantiate: {exc}")
                reports.append(bad)
                continue
            reports.append(check_object(instance))
    if not reports:
        raise PluginError(f"found no plugin classes under {target!r}")
    return reports


def _import_file(path: Path) -> Any:
    mod_name = f"datadoom_check_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise PluginError(f"could not import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        sys.modules.pop(mod_name, None)
        raise PluginError(f"{path.name} failed to import: {exc}") from exc
    return module


# --- scaffolding ---------------------------------------------------------------------


def _camel(name: str) -> str:
    parts = re.split(r"[-_\s]+", name.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def scaffold_plugin(kind: str, name: str, dest: str | Path = ".") -> Path:
    """Write a ``datadoom-plugin-<name>`` package skeleton; return its root directory."""
    if kind not in PLUGIN_BASES:
        raise PluginError(f"unknown kind {kind!r}; choose one of {', '.join(PLUGIN_BASES)}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise PluginError(
            f"invalid plugin name {name!r}; use a lowercase identifier (e.g. 'weibull')"
        )

    module = f"datadoom_plugin_{name}"
    dist_name = f"datadoom-plugin-{name.replace('_', '-')}"
    class_name = _camel(name) + _KIND_SUFFIX[kind]
    root = Path(dest) / dist_name
    if root.exists():
        raise PluginError(f"{root} already exists")
    pkg = root / "src" / module
    tests = root / "tests"
    pkg.mkdir(parents=True)
    tests.mkdir(parents=True)

    (root / "pyproject.toml").write_text(
        _PYPROJECT.format(dist=dist_name, module=module, name=name, cls=class_name),
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text(
        _STUBS[kind].format(cls=class_name, name=name), encoding="utf-8"
    )
    (tests / "test_contract.py").write_text(
        _TEST_STUB.format(module=module, cls=class_name), encoding="utf-8"
    )
    (root / "README.md").write_text(
        _README.format(dist=dist_name, kind=kind, name=name, cls=class_name, module=module),
        encoding="utf-8",
    )
    return root


_PYPROJECT = '''\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{dist}"
version = "0.1.0"
description = "A DataDoom plugin."
requires-python = ">=3.11"
dependencies = ["datadoom"]

# Discovered by DataDoom's plugin loader at startup (09 §3).
[project.entry-points."datadoom.plugins"]
{name} = "{module}:{cls}"

[tool.hatch.build.targets.wheel]
packages = ["src/{module}"]
'''

_TEST_STUB = '''\
"""Plugin contract test — runs the same checks as `datadoom plugin check`."""

from datadoom.plugins.scaffold import check_object
from {module} import {cls}


def test_contract() -> None:
    report = check_object({cls}())
    assert report.ok, "\\n" + report.summary()
'''

_README = """\
# {dist}

A DataDoom **{kind}** plugin contributing `{name}` ({cls}).

## Develop

```bash
pip install -e .          # the plugin appears in `datadoom` and the web UI
datadoom plugin check .   # run the contract tests (interface/schema/determinism/RNG)
pytest                    # the bundled contract test
```

Implement the method bodies in `src/{module}/__init__.py`, using **only** the
injected `rng` for randomness (stdlib `random`, `np.random.*` globals, `uuid4`,
`time` are banned — they break reproducibility and fail the contract check).
"""


_STUBS = {
    "distribution": '''\
"""A DataDoom distribution plugin."""

from __future__ import annotations

import numpy as np
from datadoom.plugin import Distribution, schema


class {cls}(Distribution):
    name = "{name}"
    required_params = ("scale",)
    # Rendered by the Canvas wherever a distribution is selectable (09 §6).
    param_schema = schema({{"scale": {{"type": "number", "minimum": 0, "title": "Scale"}}}})
    # Used by `datadoom plugin check` for the automated determinism check.
    example_params = {{"scale": 2.0}}

    def sample(self, rng, n, params):
        # MUST use the injected rng (a numpy Generator) — never global random.
        return params["scale"] * rng.standard_exponential(size=n)

    def cdf(self, x, params):  # enables KS compliance reporting
        return 1.0 - np.exp(-np.asarray(x, dtype=float) / params["scale"])
''',
    "structural_fn": '''\
"""A DataDoom structural-function plugin (a causal/SEM edge)."""

from __future__ import annotations

import numpy as np
from datadoom.plugin import StructuralFn, schema


class {cls}(StructuralFn):
    name = "{name}"
    # Structural fns read the fixed CausalEdge fields (weight/bias/coeffs/mapping);
    # here `weight` is the slope and `bias` is the saturation cap.
    param_schema = schema({{
        "weight": {{"type": "number", "title": "Weight (slope)"}},
        "bias": {{"type": "number", "title": "Saturation cap"}},
    }})

    def contribution(self, parent, edge):
        weight = edge.weight if edge.weight is not None else 1.0
        cap = edge.bias if edge.bias is not None else float("inf")
        return np.minimum(weight * np.asarray(parent, dtype=float), cap)
''',
    "failure_mode": '''\
"""A DataDoom failure-mode plugin (a corruption transform)."""

from __future__ import annotations

import numpy as np
from datadoom.plugin import FailureMode, schema


class {cls}(FailureMode):
    name = "{name}"
    param_schema = schema({{
        "column": {{"type": "string", "title": "Column"}},
        "rate": {{"type": "number", "minimum": 0, "maximum": 1, "title": "Rate"}},
    }})

    def apply(self, rng, frame, params, features):
        col = params["column"]
        rate = float(params.get("rate", 0.1))
        mask = rng.random(size=len(frame)) < rate
        frame.loc[mask, col] = np.nan  # corrupt the working (injected) copy in place
        return {{"column": col, "nulled_fraction": float(mask.mean())}}
''',
    "exporter": '''\
"""A DataDoom exporter plugin (an output format)."""

from __future__ import annotations

from pathlib import Path

from datadoom.engine.export.checksums import sha256_bytes
from datadoom.plugin import Exporter
from datadoom.engine.export.base import ArtifactInfo


class {cls}(Exporter):
    format = "{name}"

    def write(self, df, path):
        path = Path(path)
        # Write deterministically — no timestamps/ambient state (invariant #6).
        payload = df.to_json(orient="records", indent=2).encode("utf-8")
        path.write_bytes(payload)
        return ArtifactInfo(
            path=str(path),
            format=self.format,
            checksum_sha256=sha256_bytes(payload),
            size_bytes=len(payload),
        )
''',
    "probe_model": '''\
"""A DataDoom probe-model plugin (a difficulty baseline)."""

from __future__ import annotations

from datadoom.plugin import ProbeModel


class {cls}(ProbeModel):
    name = "{name}"

    def estimator(self, seed):
        # Return a fresh scikit-learn classifier exposing predict_proba; seed any
        # randomness so the probe metric is reproducible (it drives calibration).
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(n_estimators=50, max_depth=6, random_state=seed)
''',
}
