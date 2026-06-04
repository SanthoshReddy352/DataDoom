# DataDoom spec authoring — reference for AI models

This is a **dense, authoritative reference** for an AI/agent tasked with writing a
DataDoom spec (`*.datadoom.yaml`) from a natural-language request. It is the prose
companion to the **machine-readable capabilities manifest**, which you should fetch
programmatically when available:

```bash
datadoom spec-reference          # JSON manifest on stdout (CLI)
GET /api/spec-reference           # same manifest over HTTP
```

The manifest is generated from the live engine registries, so it always reflects
the running build **and any installed plugins** (extra distributions, structural
functions, failure modes, exporters). When a plugin is present, prefer the
manifest's names over this static list.

> For a gentle, human-oriented tutorial see
> [20_YAML_Authoring_Reference](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/20_YAML_Authoring_Guide.md).
> This document is the
> terse contract optimized for correct machine generation.

---

## 0. Output contract (follow exactly)

1. **Emit only YAML** for a single spec document — no prose, no code fences unless
   the caller asked for them.
2. **Use only the names/fields enumerated here** (or in the manifest). Never
   invent a distribution, structural function, failure type, difficulty tier,
   feature type, or export format. If unsure, choose the closest listed option.
3. **Honor every rule in §9.** A spec that violates one is rejected by
   `datadoom validate` with a `locator`. Self-check before returning.
4. Prefer the **simplest spec** that satisfies the request. Add `causal`,
   `failures`, or `difficulty` only when the request implies them.
5. Always set `datadoom_version: "1"`, a slug `name`, an integer `rows`, and a
   `seed` (for reproducibility) unless told otherwise.
6. Numbers are YAML numbers (no quotes); dates and the version are quoted strings.

---

## 1. Document skeleton

```yaml
datadoom_version: "1"     # REQUIRED, always "1"
name: "slug-name"         # REQUIRED, matches [A-Za-z0-9_-]+ (no spaces)
description: "..."        # optional
seed: 42                  # optional int — fixes the draws (not part of the hash)
rows: 1000                # REQUIRED, int >= 1
features: { ... }         # REQUIRED — map of column name -> feature (§2)
causal: { ... }           # optional — derive columns from others (§4)
difficulty: { ... }       # optional — calibrate a binary label's hardness (§6)
failures: [ ... ]         # optional — ordered data-quality corruptions (§5)
export: { ... }           # optional — output formats/variants/splits (§7)
meta: { ... }             # optional — free-form, ignored by the engine
```

Column names must start with a letter or `_`. Every feature may also carry
`description` (string) and `emit` (bool — `false` makes it **latent**: computed
and able to drive the SEM, but not exported and excluded from probe/compliance).

---

## 2. Feature types

Each feature has a `type` selecting its fields.

### `numeric` — numbers from a distribution (or causal-derived)
```yaml
age: { type: numeric, dist: normal, params: { mean: 40, std: 12 }, min: 18, max: 90, dtype: int }
```
- `dist`: a distribution name (§3). **Omit `dist`** to make it a **causal-derived**
  column (its values then come from `causal` edges; it must be an edge `to`).
- `params`: object — the keys required by `dist`.
- `min` / `max`: optional clamps. `dtype`: `float` (default) or `int` (rounds).

### `categorical` — one label per row
```yaml
tier: { type: categorical, categories: [bronze, silver, gold], weights: [0.6, 0.3, 0.1] }
```
- `categories`: non-empty string list. `weights`: optional non-negative list,
  positionally matched, normalized (default uniform).

### `boolean` — true/false
```yaml
active: { type: boolean, rate: 0.4 }     # P(true)=0.4; default 0.5
```
Omit `rate` and a boolean may instead be a **causal-derived** target (no `rate`).

### `datetime` — timestamps in a range
```yaml
ts: { type: datetime, start: "2023-01-01", end: "2024-12-31", granularity: day }
```
- `granularity`: `second` | `minute` | `hour` | `day` (default `day`).

### `text` — strings (filler or realistic)
```yaml
note:    { type: text, generator: lorem, length: { min: 5, max: 30 } }
person:  { type: text, generator: name, locale: en }
```
- `generator`: `lorem` (uses `length`) or a realistic key (§8). `locale`: default `en`.

### `timeseries` — ordered additive series over the row index
```yaml
temp:
  type: timeseries
  trend: { slope: 0.002, intercept: 20 }
  seasonality:
    - { amplitude: 6, period: 24, phase: 0 }      # daily
    - { amplitude: 2, period: 168, phase: 1.5 }   # weekly
  ar: [0.5]            # AR(1); sum(|coeffs|) MUST be < 1
  noise_std: 0.8
  dtype: float
```
Realizes `Xt = trend + Σ seasonality + AR(p) + N(0, noise_std²)`. **Row order is
the time axis** (preserved). A timeseries may be a causal **parent**; it is never
a causal target and is **not** distribution-compliance assessed.

---

## 3. Distributions (`numeric.dist` and `feature_noise.dist`)

| name | required `params` | constraints / notes |
|---|---|---|
| `normal` | `mean`, `std` | `std > 0`; any real value |
| `lognormal` | `mu`, `sigma` | `sigma > 0`; positive-only; `mu`/`sigma` are in log space (median = e^mu) |
| `uniform` | `low`, `high` | `high > low`; flat |
| `exponential` | `scale` | `scale > 0`; non-negative; mean = scale |
| `poisson` | `lam` | `lam > 0`; **discrete** integer counts |
| `pareto` | `alpha`, `xm` | both `> 0`; values `>= xm`; heavy tail |

Pick by shape: counts → `poisson`; money/positive-skew → `lognormal` (or `pareto`
for heavy tails); bounded score → `normal` + `min`/`max`; latency → `exponential`.

---

## 4. Causal graph (`causal`)

Derive columns from others. A derived feature is declared with **no `dist`/`rate`**
and appears as an edge `to`.

```yaml
causal:
  edges:
    - { from: age,       to: income,   fn: linear,   weight: 800, bias: 10000 }
    - { from: education, to: income,   fn: map,      mapping: { hs: 0, college: 15000, grad: 40000 } }
    - { from: income,    to: is_fraud, fn: logistic, weight: -0.00002, bias: 1.0 }
  noise:
    income:   { dist: normal, params: { mean: 0, std: 5000 } }
    is_fraud: { dist: none }
  interventions:
    - { do: { income: 50000 } }    # optional: pin a node to a constant
```

A node **sums** its incoming edges' contributions, then adds node `noise`. A
boolean target's summed value is turned into a probability (use `logistic` as its
incoming edge) and sampled.

**Structural functions (`fn`):**

| `fn` | contribution | needs | parent type |
|---|---|---|---|
| `linear` | `weight·parent + bias` | `weight` (+ `bias?`) | numeric/boolean/timeseries |
| `logistic` | `σ(weight·parent + bias)` | `weight` (+ `bias?`) | numeric/boolean/timeseries |
| `polynomial` | `Σ coeffs[i]·parent^i` | `coeffs` (list) | numeric/boolean/timeseries |
| `map` | `mapping[parent]` | `mapping` (covers all categories) | **categorical** |
| `identity` | `parent` | — | numeric/boolean/timeseries |

`noise[node]` is `{ dist: none }` (deterministic) or `{ dist: <name>, params: {…} }`.

---

## 5. Failures (`failures`) — ordered list

Applied after a clean baseline is captured; export `injected` to write the
corrupted file (§7). Each item has `type` + fields. `rate` is a fraction in `[0,1]`.

| `type` | purpose | fields |
|---|---|---|
| `mcar` | random blanks | `column` **or** `columns:[…]`; `rate` |
| `mar` | blanks driven by another column | `column`; `driver`; `rate`; `strength?` (def 2.0) |
| `mnar` | blanks driven by the column's own value | `column`; `driver?`; `rate`; `strength?` (def 2.0) |
| `label_noise` | flip/reassign a label | `column` (boolean/categorical); `rate` |
| `feature_noise` | add noise to a number | `column` (numeric); `dist`; `params` |
| `drift` | shift across the row index | `column` (numeric); `schedule` |
| `covariate_shift` | rescale to target moments | `column` (numeric); `target:{mean?,std?}` |
| `leakage` | plant a proxy column | `target` (numeric/boolean); `into` (new ≠ target); `noise?` (def 0.05) |

`drift.schedule`: `{ kind: linear|step, magnitude: <total shift> }` (or `rate:
<per-row slope>`; `at: 0..1` jump point for `step`, default 0.5).

```yaml
failures:
  - { type: mnar, column: income, rate: 0.12, strength: 2.5 }
  - { type: label_noise, column: is_fraud, rate: 0.03 }
  - { type: drift, column: income, schedule: { kind: linear, magnitude: 8000 } }
  - { type: leakage, target: is_fraud, into: fraud_score, noise: 0.05 }
```

A failure must not reference a latent (`emit:false`) feature.

---

## 6. Difficulty (`difficulty`) — binary classification only

Calibrates the dataset so a baseline probe lands in a target AUROC band.

```yaml
difficulty:
  target: advanced        # tier name OR { band: [0.72, 0.80] }
  label: defaulted        # boolean / 2-class categorical; not latent
  probe: logreg           # logreg | tree
  max_iters: 10           # int >= 1 (default 8)
  knobs: [noise, label_noise]   # subset of {noise, label_noise}
```

| tier | AUROC band |
|---|---|
| `beginner` | 0.90–0.99 |
| `intermediate` | 0.80–0.90 |
| `advanced` | 0.72–0.80 |
| `kaggle` | 0.62–0.72 |

Best paired with a causal label (often a **latent** `risk_score` `emit:false` that
combines drivers via `logistic`). Note: calibration **blurs predictors**, so the
distribution-compliance score legitimately drops — that is intended.

---

## 7. Export (`export`)

```yaml
export:
  formats: [csv, json, parquet]   # default [csv]; parquet needs the optional extra
  versions: [clean, injected]     # default [clean]; injected only with failures
  splits: { train: 0.8, test: 0.2 }   # ratios MUST sum to 1.0
  shuffle: true                   # default true
  metadata: true                  # default true
```

---

## 8. Realistic text generators (`text.generator`)

`lorem` (filler) plus these seeded providers:
`name, first_name, last_name, email, username, phone, occupation, title,
nationality, address, street, city, state, country, postal_code, company,
currency, price, url, hostname, ipv4, word, sentence, color`.

---

## 9. Hard rules (validation will enforce these)

1. Required top-level keys present; `name` is a slug; `rows >= 1`.
2. A causal-derived feature has **no `dist`/`rate`** and **is** some edge's `to`.
3. A feature is never both sampled (`dist`) and a causal target.
4. The causal graph is **acyclic**; only numeric/boolean nodes can be targets.
5. `map` needs a categorical parent and a mapping covering **every** category;
   other fns need a numeric/boolean/timeseries parent.
6. `difficulty.label` is boolean or 2-class categorical and not latent; `knobs ⊆
   {noise, label_noise}`; `target` is a tier or `{band:[a,b]}`.
7. Failures are ordered; `export.versions` must include `injected` to emit the
   corrupted file; a failure can't reference a latent.
8. `export.splits` ratios sum to 1.0; `export.formats` are known formats.
9. Time-series `ar` satisfies `sum(|coeffs|) < 1`; seasonality `period > 0`.
10. Distribution `params` satisfy their domain (e.g. `std > 0`, `uniform.high >
    low`, `poisson.lam > 0`).

---

## 10. Worked few-shot examples

### Request: "1k customers with age, country, and a 30%-true churn flag."
```yaml
datadoom_version: "1"
name: "customers-basic"
seed: 42
rows: 1000
features:
  age:     { type: numeric, dist: normal, params: { mean: 42, std: 13 }, min: 18, max: 90, dtype: int }
  country: { type: categorical, categories: [US, UK, IN, DE], weights: [4, 2, 3, 1] }
  churned: { type: boolean, rate: 0.3 }
export: { formats: [csv] }
```

### Request: "Fraud dataset where income depends on age+education and drives fraud, with MNAR income and a leaky proxy. Train/test split."
```yaml
datadoom_version: "1"
name: "fraud-causal"
seed: 7
rows: 5000
features:
  age:       { type: numeric, dist: normal, params: { mean: 40, std: 12 }, min: 18, max: 90, dtype: int }
  education: { type: categorical, categories: [hs, college, grad], weights: [0.5, 0.4, 0.1] }
  income:    { type: numeric, dtype: float, min: 0 }   # derived
  is_fraud:  { type: boolean }                          # derived target
causal:
  edges:
    - { from: age,       to: income,   fn: linear,   weight: 800, bias: 10000 }
    - { from: education, to: income,   fn: map,      mapping: { hs: 0, college: 15000, grad: 40000 } }
    - { from: income,    to: is_fraud, fn: logistic, weight: -0.00002, bias: 1.0 }
  noise:
    income:   { dist: normal, params: { mean: 0, std: 5000 } }
    is_fraud: { dist: none }
failures:
  - { type: mnar,    column: income,   rate: 0.12, strength: 2.5 }
  - { type: leakage, target: is_fraud, into: fraud_score, noise: 0.05 }
export:
  formats: [csv]
  versions: [clean, injected]
  splits: { train: 0.8, test: 0.2 }
```

### Request: "Credit-default benchmark calibrated to 'advanced' difficulty, with a hidden risk score."
```yaml
datadoom_version: "1"
name: "credit-advanced"
seed: 17
rows: 6000
features:
  income:     { type: numeric, dist: normal, params: { mean: 60000, std: 20000 }, min: 0 }
  debt_ratio: { type: numeric, dist: normal, params: { mean: 0.35, std: 0.12 }, min: 0 }
  inquiries:  { type: numeric, dist: poisson, params: { lam: 2 }, dtype: int }
  risk_score: { type: numeric, dtype: float, emit: false }   # latent
  defaulted:  { type: boolean }                              # label (derived)
causal:
  edges:
    - { from: income,     to: risk_score, fn: linear,   weight: -0.00003 }
    - { from: debt_ratio, to: risk_score, fn: linear,   weight: 6.0 }
    - { from: inquiries,  to: risk_score, fn: linear,   weight: 0.5 }
    - { from: risk_score, to: defaulted,  fn: logistic, weight: 3.0, bias: -0.5 }
  noise:
    risk_score: { dist: none }
    defaulted:  { dist: none }
difficulty:
  target: advanced
  label: defaulted
  probe: logreg
  knobs: [noise, label_noise]
export: { formats: [csv] }
```

### Request: "Hourly temperature time-series for a year with daily seasonality and a warming trend."
```yaml
datadoom_version: "1"
name: "temperature-hourly"
seed: 1
rows: 8760
features:
  temperature:
    type: timeseries
    trend: { slope: 0.0005, intercept: 15 }
    seasonality:
      - { amplitude: 8, period: 24, phase: 0 }
    ar: [0.6]
    noise_std: 1.0
    dtype: float
export: { formats: [csv] }
```

---

*After generating, the author can verify with `datadoom validate <file>` and
generate with `datadoom run <file> --seed <n> --out <dir>`. The reproducibility
contract: same `(spec, seed)` → identical bytes.*
