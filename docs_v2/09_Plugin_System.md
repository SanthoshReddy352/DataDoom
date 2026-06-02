# 09 — Plugin System

> The community growth engine. Plugins let third parties add capability **without forking core**, and they appear in the web UI automatically. Obeys `00_README_Index.md`.

---

## 1. Why Plugins Are Central

For DataDoom to become a *large* open-source project, most new capability over time must come from the community, not the core team. The plugin system is therefore a **first-class, stable API**, not an afterthought. Design goals:

1. **No core changes** to add a distribution, failure mode, exporter, structural function, template, or probe model.
2. **UI auto-integration:** a plugin declares a JSON-schema fragment; the Canvas renders its config controls with no frontend work.
3. **Determinism-safe:** plugins must use the injected seeded RNG; the contract makes the right way the easy way.
4. **Discoverable & installable:** `pip install datadoom-plugin-foo` is enough; also a local plugins directory for quick experiments.

---

## 2. Plugin Types

| Kind | Base class | Adds | Spec touchpoint |
|---|---|---|---|
| `distribution` | `Distribution` | a sampling distribution | `features.<f>.dist` |
| `structural_fn` | `StructuralFn` | a causal/structural equation | `causal.edges[].fn` |
| `failure_mode` | `FailureMode` | a corruption transform | `failures[].type` |
| `exporter` | `Exporter` | an output format/adapter | `export.formats[]` |
| `template` | *(data only)* | a domain spec | template gallery |
| `probe_model` | `ProbeModel` | a difficulty baseline | `difficulty.probe` |

---

## 3. Discovery & Loading

Two mechanisms, both resolved at server/engine startup into the in-memory **registry**:

1. **Python entry points** (preferred for published plugins):
   ```toml
   # in a plugin package's pyproject.toml
   [project.entry-points."datadoom.plugins"]
   weibull = "datadoom_weibull:WeibullDistribution"
   ```
2. **Local plugins directory:** `$DATADOOM_HOME/plugins/*.py` (auto-imported; great for prototyping and per-project plugins).

The registry validates each plugin (correct base class, unique `name`, valid schema), records it (optionally in the `plugins` table, `07`), and exposes it via `GET /api/plugins`. Conflicts (duplicate names) fail loudly at startup with a clear message.

---

## 4. Plugin Contracts (interfaces)

All plugins are small classes implementing a typed base. Illustrative (Python):

### 4.1 Distribution
```python
from datadoom.plugin import Distribution, schema

class WeibullDistribution(Distribution):
    name = "weibull"
    # JSON-schema fragment the UI renders for `params`
    param_schema = schema({
        "k":      {"type": "number", "minimum": 0, "title": "Shape (k)"},
        "lam":    {"type": "number", "minimum": 0, "title": "Scale (λ)"},
    })

    def validate(self, params: dict) -> None:
        if params["k"] <= 0 or params["lam"] <= 0:
            raise ValueError("k and lam must be > 0")

    def sample(self, n: int, params: dict, rng) -> "np.ndarray":
        # MUST use the injected rng (numpy Generator) — never global random
        return params["lam"] * rng.weibull(params["k"], size=n)

    def cdf(self, x, params: dict):           # enables KS reporting
        ...
```

### 4.2 StructuralFn
```python
class SaturatingFn(StructuralFn):
    name = "saturating"
    param_schema = schema({"weight": {"type":"number"}, "cap": {"type":"number"}})
    def apply(self, parent_values, params, rng):
        return np.minimum(params["weight"] * parent_values, params["cap"])
```

### 4.3 FailureMode
```python
class SeasonalMissing(FailureMode):
    name = "seasonal_missing"
    param_schema = schema({"column": {"type":"string"},
                           "peak_month": {"type":"integer","minimum":1,"maximum":12},
                           "rate": {"type":"number","minimum":0,"maximum":1}})
    def apply(self, df, params, rng):
        # return (modified_df, diff_summary_dict); preserve all other columns
        ...
```

### 4.4 Exporter
```python
class FeatherExporter(Exporter):
    name = "feather"
    extension = "feather"
    def write(self, df, path: str) -> None: ...
```

### 4.5 ProbeModel
```python
class XGBProbe(ProbeModel):
    name = "xgb"
    def fit_score(self, X_train, y_train, X_test, y_test, task: str, rng) -> float:
        # return the task metric (e.g. AUROC); must be deterministic given rng/seed
        ...
```

### 4.6 Template (data only — no code)
A template is a shared spec file plus metadata:
```yaml
# datadoom_template_fraud/template.datadoom.yaml  (+ template.meta.yaml)
# discovered via entry point group "datadoom.templates" or local templates dir
```

---

## 5. The RNG / Determinism Contract (mandatory)

- Every method that produces randomness receives an injected `rng` (a `numpy.random.Generator`) scoped to a stable namespace. **Plugins must use only this `rng`.**
- Banned in plugins (enforced by the plugin lint in CI and documented): stdlib `random`, `np.random.*` globals, `uuid4`, `time`, hashing for randomness, thread-count-dependent reductions.
- A plugin that violates determinism fails the **plugin contract test** (`13`) which runs the plugin twice with the same seed and asserts identical output.

---

## 6. UI Auto-Integration

- Each plugin exposes `param_schema` (a JSON-schema fragment).
- `GET /api/plugins` returns `{ name, kind, schema, ... }`.
- The Canvas renders the schema into form controls (number inputs with min/max, enums as dropdowns, etc.) wherever that plugin is selectable (distribution dropdown, fn dropdown, failure accordion, export checklist).
- Result: **installing a plugin makes it appear in the UI with zero frontend changes.**

---

## 7. Versioning, Compatibility & Trust

- Plugins declare a compatible DataDoom API range (`datadoom>=X,<Y`). The loader warns/skips incompatible plugins.
- Plugin `name`s are global within an install; we recommend prefixing community packages `datadoom-plugin-*`.
- **Security note (see `14`):** plugins are arbitrary Python and run in-process with full privileges. DataDoom does **not** sandbox plugins. Installing a plugin = trusting its code, same as any `pip install`. The UI labels third-party plugins clearly; core ships a curated set.

---

## 8. Built-in vs Plugin (what ships in core)

- **Core (built-in, always present):** Normal, LogNormal, Poisson, Pareto, Uniform, Exponential, Bernoulli, Categorical, Datetime, lorem text; linear/logistic/polynomial/map/identity structural fns; MCAR/MAR/MNAR/label_noise/feature_noise/drift/covariate_shift/leakage; CSV/Parquet/JSON exporters; logreg/tree probes; a starter template set.
- **Everything else** (Weibull, GAN-based generators, XGBoost probe, exotic formats, domain template packs) is a **plugin** — including features we deliberately keep out of core (e.g. GPU/GAN generation can live in a `datadoom-plugin-gan` that the core does not depend on).

This keeps the core small, deterministic, and dependency-light, while letting the ecosystem grow without bound.

---

## 9. Authoring Workflow (contributor-facing)

1. `datadoom plugin new --kind distribution my_dist` scaffolds a package (entry point, base class stub, test stub, README).
2. Implement `sample`/`apply`/`write`/`fit_score` using the injected `rng`.
3. `datadoom plugin check ./` runs the contract tests (determinism, schema validity, interface completeness).
4. `pip install -e .` → the plugin appears in `datadoom` and the UI.
5. Publish to PyPI as `datadoom-plugin-*`; optionally submit the template/plugin to the community index.
