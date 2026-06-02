# 04 — DataDoom Spec Reference

> The **spec is the center of gravity** of the entire product. The web UI edits it; the engine executes it; git versions it; `(spec_hash, seed)` reproduces it. Obeys `00_README_Index.md`.

---

## 1. What a Spec Is

A DataDoom Spec is a single declarative document (YAML primary, JSON accepted) that **fully determines a dataset**. Given a spec and a seed, generation is deterministic and reproducible. The spec is:

- **Human-readable & writable** — editable by hand or via the Canvas.
- **Version-controllable** — a small text file you commit to git.
- **Shareable & citable** — the unit of reproduction (papers, repos, CI fixtures).
- **The UI's data model** — every Canvas control maps to a spec field.

File naming convention: `*.datadoom.yaml` (e.g. `fraud-detection.datadoom.yaml`).

---

## 2. Top-Level Structure

```yaml
datadoom_version: "1"          # spec format major version (required)
name: "fraud-detection-medium" # required, slug-friendly
description: "..."             # optional
seed: 42                       # optional; if omitted, a seed is generated and recorded on first run
rows: 50000                    # required, integer ≥ 1

features:   { ... }            # required: map of feature_name → FeatureDefinition
causal:     { ... }            # optional: DAG of dependencies between features
difficulty: { ... }            # optional: target difficulty
failures:   [ ... ]            # optional: ordered list of failure injections
export:     { ... }            # optional: formats, splits, metadata
meta:       { ... }            # optional: free-form (authorship, tags, problem_statement)
```

### Required vs optional
- **Required:** `datadoom_version`, `name`, `rows`, `features`.
- Everything else is optional; absence means "skip that pipeline stage."

---

## 3. Identity & Determinism Fields

- `seed` (int, optional): if omitted, the engine generates one (from OS entropy) **once**, records it in the run's metadata and the saved spec, and reuses it for "Regenerate (same seed)."
- `spec_hash` is **not** written by the author. It is computed: `sha256(canonical_json(spec_without_seed))`. Two specs with identical content (modulo `seed`) share a `spec_hash`; an artifact is identified by `(spec_hash, seed)`.
- **Canonicalization** (so hashing is stable): keys sorted, no insignificant whitespace, numbers normalized, `seed` excluded. Defined precisely in `05_Mathematical_Algorithm_Definitions.md §1`.

---

## 4. `features` — Feature Definitions

A map of `feature_name → FeatureDefinition`. Names must be unique and match `^[A-Za-z_][A-Za-z0-9_]*$`.

Common fields:
```yaml
<name>:
  type: numeric | categorical | boolean | datetime | text
  description: "..."        # optional
  # type-specific fields below
  # derived features omit `dist` and are defined via `causal` (see §5)
```

### 4.1 numeric
```yaml
age:
  type: numeric
  dist: normal             # normal | lognormal | poisson | pareto | uniform | exponential | <plugin>
  params: { mean: 40, std: 12 }
  min: 18                  # optional clamp (post-sample truncation)
  max: 90                  # optional clamp
  dtype: int               # int | float (default float)
```

**Built-in distributions & params:**

| `dist` | required `params` | notes |
|---|---|---|
| `normal` | `mean`, `std` | std > 0 |
| `lognormal` | `mu`, `sigma` | sigma > 0; underlying normal params |
| `poisson` | `lam` | lam > 0; integer output |
| `pareto` | `alpha`, `xm` | alpha > 0, xm > 0 |
| `uniform` | `low`, `high` | low < high |
| `exponential` | `scale` | scale > 0 |
| *(plugin)* | declared by plugin | UI renders plugin's schema |

`min`/`max` apply a **truncation/clamp** after sampling (reported in compliance, since clamping perturbs the distribution).

### 4.2 categorical
```yaml
education:
  type: categorical
  categories: [hs, college, grad]
  weights: [0.5, 0.4, 0.1]    # optional; default uniform; normalized if not summing to 1
```

### 4.3 boolean
```yaml
is_member:
  type: boolean
  rate: 0.3                    # P(true); default 0.5
```

### 4.4 datetime
```yaml
signup_date:
  type: datetime
  start: "2023-01-01"
  end: "2024-12-31"
  granularity: day             # second | minute | hour | day
  dist: uniform                # uniform | (seasonality via plugin/time-series)
```

### 4.5 text
```yaml
note:
  type: text
  generator: lorem             # lorem | template | <plugin>
  length: { min: 10, max: 40 } # tokens
```
> Text in v1 is intentionally simple (no LLM dependency). Richer text generators arrive as plugins.

### 4.6 Derived features
A feature that is produced by the causal layer (not sampled directly) declares only its `type` and is wired up in `causal`. Its `dist` is omitted; its values come from its structural equation + noise.
```yaml
income: { type: numeric, dtype: float }   # value defined by causal edges below
```

---

## 5. `causal` — Causal Graph (DAG / SEM)

Defines dependencies between features. The graph must be **acyclic**; cycles are rejected at validation (engine + UI).

```yaml
causal:
  edges:
    - from: age        # parent feature
      to: income       # child (derived) feature
      fn: linear       # structural function
      weight: 800
    - from: education
      to: income
      fn: map
      mapping: { hs: 0, college: 15000, grad: 40000 }
    - from: income
      to: is_fraud
      fn: logistic
      weight: -0.00002
      bias: -2
  noise:               # optional per-node additive noise
    income:   { dist: normal, params: { mean: 0, std: 5000 } }
    is_fraud: { dist: none }
```

**Semantics.** For each child node `v` in topological order:
`v = combine( fn_e(parent_e) for each incoming edge e ) + ε_v`, where `combine` is summation by default. (Formalized in `05 §3`.)

**Structural functions (`fn`):**

| `fn` | params | meaning |
|---|---|---|
| `linear` | `weight`, optional `bias` | `weight * parent (+ bias)` |
| `logistic` | `weight`, `bias` | `σ(weight*parent + bias)` → probability (for boolean/0-1 children) |
| `polynomial` | `coeffs: [...]` | `Σ coeffs[i] * parent^i` |
| `map` | `mapping: {cat: value}` | map categorical parent to numeric contribution |
| `identity` | — | pass-through |
| *(plugin)* | declared by plugin | custom StructuralFn |

**Interventions / counterfactuals** (advanced):
```yaml
causal:
  interventions:
    - do: { income: 0 }     # fix income; detach its incoming edges
  # generates counterfactual values for downstream nodes
```

---

## 6. `difficulty` — Difficulty Targeting

Difficulty is an **empirical target**, not a closed-form score (see `05 §5`).

```yaml
difficulty:
  target: kaggle               # beginner | intermediate | advanced | kaggle
  # OR explicit band:
  # target: { task: classification, metric: auroc, band: [0.72, 0.78] }
  label: is_fraud              # the target column the probe model predicts
  probe: logreg                # logreg | tree | <plugin>  (baseline model)
  max_iters: 8                 # adaptive regeneration attempts
  knobs: [noise, imbalance]    # what the loop may adjust
```

Named tiers map to validated metric bands (defined/tuned in `05 §5` and `13`). The engine reports **achieved** metric vs. target and which knobs it adjusted.

---

## 7. `failures` — Failure Injection

An **ordered list**; transforms apply in sequence after a clean baseline is captured. The clean dataset is always preserved alongside the injected variant.

```yaml
failures:
  - type: mnar
    column: income
    rate: 0.12
    driver: education          # missingness depends on this column (MNAR/MAR)
  - type: mcar
    columns: [age, note]
    rate: 0.05
  - type: label_noise
    column: is_fraud
    rate: 0.03
  - type: feature_noise
    column: age
    dist: normal
    params: { mean: 0, std: 2 }
  - type: drift
    column: income
    schedule: { kind: linear, rate: 0.01 } # over row index / time
  - type: covariate_shift
    column: age
    target: { mean: 55 }       # shift test distribution
  - type: leakage
    target: is_fraud
    into: helper_feature        # plant a leaky proxy
```

| `type` | key params | |
|---|---|---|
| `mcar` | `column(s)`, `rate` | missing completely at random |
| `mar` | `column`, `rate`, `driver` | missingness depends on an observed column |
| `mnar` | `column`, `rate`, `driver` | missingness depends on the (possibly unobserved) value/driver |
| `label_noise` | `column`, `rate` | flip/perturb labels |
| `feature_noise` | `column`, `dist`, `params` | additive noise |
| `drift` | `column`, `schedule` | concept drift over index/time |
| `covariate_shift` | `column`, `target` | shift feature distribution |
| `leakage` | `target`, `into` | plant a leakage trap |
| *(plugin)* | declared by plugin | custom FailureMode |

---

## 8. `export` — Output

```yaml
export:
  formats: [csv, parquet]        # csv | parquet | json | <plugin>
  versions: [clean, injected]    # which dataset variants to write
  splits:
    train: 0.7
    test: 0.2
    hidden_test: 0.1             # ratios must sum to 1.0 (if present)
  shuffle: true                  # deterministic shuffle (seeded)
  metadata: true                 # write metadata.json + report.html + the spec
```

Output layout (local):
```
<artifacts>/<dataset>/<run_id>/
  clean/train.parquet  clean/test.parquet  clean/hidden_test.parquet
  injected/train.parquet ...
  metadata.json        # spec_hash, seed, distribution summary, correlation matrix, checksums
  report.html          # human-readable evaluation report
  spec.datadoom.yaml   # the exact spec used (with resolved seed)
```

---

## 9. Validation Rules (enforced at stage 1)

1. `datadoom_version` is supported.
2. `name` matches slug pattern; `rows ≥ 1`.
3. Each feature `type` is known; type-specific params present and valid (e.g. `std > 0`, `weights ≥ 0`).
4. `dist` resolves to a built-in or a loaded plugin.
5. Causal graph: all `from`/`to` reference declared features; **graph is acyclic**; derived features have ≥1 incoming edge; no feature is both directly sampled (`dist`) and fully derived.
6. `difficulty.label` references a real feature; `probe` resolves.
7. Failure `column(s)`/`driver`/`target` reference real features; `rate ∈ [0,1]`.
8. `export.splits` ratios sum to 1.0 (when present); formats resolve.

Validation errors carry a **locator** (feature name / edge / list index) so the UI can highlight the offending control.

---

## 10. Versioning & Compatibility

- `datadoom_version` is the **spec format** major version, independent of the package SemVer.
- Within a major version, evolution is **additive only** (new optional fields). Breaking changes bump the major and ship a `datadoom migrate` path.
- Unknown **optional** fields from a newer minor are ignored with a warning (forward-compatible reads); unknown **required** semantics fail closed.

---

## 11. Complete Example

```yaml
datadoom_version: "1"
name: "fraud-detection-medium"
description: "Synthetic fraud dataset with causal income→fraud link, Kaggle-hard."
seed: 42
rows: 50000

features:
  age:        { type: numeric, dist: normal, params: { mean: 40, std: 12 }, min: 18, max: 90, dtype: int }
  education:  { type: categorical, categories: [hs, college, grad], weights: [0.5, 0.4, 0.1] }
  income:     { type: numeric, dtype: float }          # derived
  is_fraud:   { type: boolean }                          # derived (target)

causal:
  edges:
    - { from: age,       to: income,  fn: linear,   weight: 800, bias: 10000 }
    - { from: education, to: income,  fn: map,      mapping: { hs: 0, college: 15000, grad: 40000 } }
    - { from: income,    to: is_fraud, fn: logistic, weight: -0.00002, bias: -1.5 }
  noise:
    income: { dist: normal, params: { mean: 0, std: 5000 } }

difficulty:
  target: kaggle
  label: is_fraud
  probe: logreg
  max_iters: 8
  knobs: [noise, imbalance]

failures:
  - { type: mnar, column: income, rate: 0.12, driver: education }
  - { type: label_noise, column: is_fraud, rate: 0.03 }

export:
  formats: [csv, parquet]
  versions: [clean, injected]
  splits: { train: 0.7, test: 0.2, hidden_test: 0.1 }
  shuffle: true
  metadata: true

meta:
  problem_statement: "Predict is_fraud. Hidden test withheld."
  metric: auroc
  tags: [fintech, classification]
```
