# Writing a DataDoom spec — the absolute-beginner's guide

This guide teaches you to write a DataDoom **spec file** (a `.datadoom.yaml`) from
scratch. A spec is the *single recipe* for a synthetic dataset: you describe the
columns, how they relate, what failures to inject, and how hard the learning task
should be — and DataDoom regenerates the **exact same data** from it, forever.

> You don't need to know statistics to start. Copy the minimal example, change
> the numbers, run it, look at the output. Every section below tells you, for
> each setting: **what it is, its type, what it generates, and a snippet.**

**Contents**

1. [The mental model](#1-the-mental-model)
2. [Your first spec (the skeleton)](#2-your-first-spec-the-skeleton)
3. [Top-level keys](#3-top-level-keys)
4. [Features — the columns](#4-features--the-columns)
5. [Numeric distributions reference](#5-numeric-distributions-reference)
6. [The causal graph — making columns depend on each other](#6-the-causal-graph)
7. [Failure injection — dirtying the data on purpose](#7-failure-injection)
8. [Difficulty — dialing the task to a target](#8-difficulty)
9. [Export — formats, splits, variants](#9-export)
10. [Running your spec](#10-running-your-spec)
11. [How DataDoom reports "did the data match?"](#11-how-datadoom-reports-fit-compliance)
12. [A full worked example](#12-a-full-worked-example)
13. [Quick reference / cheat-sheet](#13-quick-reference--cheat-sheet)

---

## 1. The mental model

```
            ┌──────────────────────┐        ┌──────────┐
 spec.yaml ─┤  (spec_hash, seed)   ├──────▶ │ data.csv │  (identical every run)
            └──────────────────────┘        └──────────┘
```

- A **spec** is a plain YAML document. It is *declarative*: you say **what** you
  want, not how to compute it.
- DataDoom hashes the spec into a `spec_hash`. Together with a **seed** (an
  integer), that pair determines every random draw. Same `(spec, seed)` → byte-
  for-byte identical output, on any machine, forever. The seed is **not** part of
  the hash, so changing the seed gives you a *different but equally valid* sample
  of the *same* design.
- The pipeline runs in fixed stages: **sample base columns → run the causal graph
  → calibrate difficulty → inject failures → check compliance → write files.**
  You configure each stage with a top-level key.

You can write specs by hand (this guide) or build them visually in the web Canvas
— both produce the identical YAML.

---

## 2. Your first spec (the skeleton)

Save this as `my-first.datadoom.yaml`:

```yaml
datadoom_version: "1"          # always "1" for now
name: "my-first"               # slug: letters, digits, _ or -
description: "My first synthetic dataset."
seed: 42                       # optional; makes runs reproducible
rows: 1000                     # how many rows to generate

features:
  age:
    type: numeric
    dist: normal
    params: { mean: 40, std: 12 }
  country:
    type: categorical
    categories: [US, UK, IN]

export:
  formats: [csv]
```

Run it:

```powershell
datadoom run my-first.datadoom.yaml --seed 42 --out out/
```

You'll get `out/data.csv` (the data), `out/metadata.json` (provenance + fit
report), and a resolved copy of the spec. That's the whole loop.

---

## 3. Top-level keys

These are the keys allowed at the root of the document. Only `datadoom_version`,
`name`, `rows`, and `features` are required.

| Key | Type | Required | What it does |
|---|---|---|---|
| `datadoom_version` | string | ✅ | Spec format version. Always `"1"`. |
| `name` | string (slug) | ✅ | Dataset name. Must match `[A-Za-z0-9_-]+` (no spaces). |
| `description` | string | — | Free-text description. |
| `seed` | integer | — | Fixes the random draws. Omit and DataDoom picks one per run (still recorded in `metadata.json`). Pass `--seed` on the CLI to override. |
| `rows` | integer ≥ 1 | ✅ | Number of rows to generate. |
| `features` | mapping | ✅ | The columns. **See [§4](#4-features--the-columns).** |
| `causal` | mapping | — | A DAG that derives some columns from others. **See [§6](#6-the-causal-graph).** |
| `difficulty` | mapping | — | Calibrate a classification label to a target difficulty. **See [§8](#8-difficulty).** |
| `failures` | list | — | Ordered data-quality corruptions. **See [§7](#7-failure-injection).** |
| `export` | mapping | — | Output formats, splits, variants. **See [§9](#9-export).** |
| `meta` | mapping | — | Anything you want (e.g. `problem_statement`, `tags`). Ignored by the engine. |

> **Type note:** YAML types map straight to what you'd expect — `mean: 40` is a
> number, `name: "US"` a string, `[US, UK]` a list, `{ mean: 40 }` a mapping.
> Quote strings that look like numbers/dates (`"2024-01-01"`, `"1"`).

---

## 4. Features — the columns

`features` is a mapping of **column name → definition**. The column name must
start with a letter or `_`. Every definition has a `type` that selects which
extra fields are valid. There are five types:

| `type` | Generates | Key fields |
|---|---|---|
| `numeric` | numbers from a distribution (or derived by the causal graph) | `dist`, `params`, `min`, `max`, `dtype` |
| `categorical` | one label per row from a fixed set | `categories`, `weights` |
| `boolean` | true/false | `rate` |
| `datetime` | timestamps in a range | `start`, `end`, `granularity` |
| `text` | strings (filler or realistic) | `generator`, `locale`, `length` |

Every feature also accepts two shared optional fields:

| Field | Type | Default | What it does |
|---|---|---|---|
| `description` | string | — | Documents the column. |
| `emit` | bool | `true` | `false` makes the feature **latent**: it is computed and can drive the causal graph, but is **not written** to the output (a hidden confounder / latent score). See [§6](#6-the-causal-graph). |

### 4.1 `numeric`

Numbers drawn from a probability distribution, optionally clamped and/or rounded
to integers.

| Field | Type | Default | What it does |
|---|---|---|---|
| `dist` | string | — | Which distribution to draw from (see [§5](#5-numeric-distributions-reference)). **Omit `dist`** to make the column *derived* — its values come from the causal graph instead ([§6](#6-the-causal-graph)). |
| `params` | mapping | `{}` | Distribution parameters (e.g. `{ mean: 40, std: 12 }`). The required keys depend on `dist`. |
| `min` | number | none | Lower clamp. Values below `min` are pulled up to `min`. |
| `max` | number | none | Upper clamp. Values above `max` are pulled down to `max`. |
| `dtype` | `float` \| `int` | `float` | `int` rounds each value to the nearest whole number. |

```yaml
age:
  type: numeric
  dist: normal
  params: { mean: 40, std: 12 }
  min: 18          # nobody under 18
  max: 90          # nobody over 90
  dtype: int       # whole years
```

> **Clamping & rounding are honest.** When you clamp or round, the realized data
> is no longer a perfect continuous draw (mass piles up at the bounds; values
> snap to integers). DataDoom *reports* that and judges fit with the right test —
> see [§11](#11-how-datadoom-reports-fit-compliance). It never silently refits.

### 4.2 `categorical`

One label per row, chosen from a fixed list.

| Field | Type | Default | What it does |
|---|---|---|---|
| `categories` | list of strings | — (required, ≥ 1) | The possible labels. |
| `weights` | list of numbers | uniform | Relative likelihood of each category, **positionally matched** to `categories`. Need not sum to 1 — they're normalized. Must be non-negative. |

```yaml
education:
  type: categorical
  categories: [hs, college, grad]
  weights: [0.5, 0.4, 0.1]     # 50% / 40% / 10%
```

Omit `weights` for an even split across all categories.

### 4.3 `boolean`

A true/false column.

| Field | Type | Default | What it does |
|---|---|---|---|
| `rate` | number in `[0, 1]` | `0.5` | Probability of `true`. |

```yaml
is_member:
  type: boolean
  rate: 0.3        # ~30% true
```

### 4.4 `datetime`

Timestamps drawn uniformly within a range.

| Field | Type | Default | What it does |
|---|---|---|---|
| `start` | string date | — (required) | Earliest timestamp, e.g. `"2023-01-01"`. |
| `end` | string date | — (required) | Latest timestamp (must be ≥ `start`). |
| `granularity` | `second`\|`minute`\|`hour`\|`day` | `day` | Resolution of the sampled timestamps. `day` → no time-of-day component. |

```yaml
signup_date:
  type: datetime
  start: "2023-01-01"
  end: "2024-12-31"
  granularity: day
```

### 4.5 `text`

String columns — either lorem-ipsum filler or realistic values (names, emails,
addresses, …) via the bundled provider library. **Realistic providers are
seeded**, so text is reproducible too.

| Field | Type | Default | What it does |
|---|---|---|---|
| `generator` | string | `lorem` | `lorem` = filler words; or any realistic provider key (table below). |
| `locale` | string | `en` | Locale for realistic providers (e.g. `en`, `de`, `fr`). |
| `length` | `{min, max}` | `{min: 5, max: 30}` | **Only for `lorem`:** word-count range per cell. |

```yaml
note:
  type: text
  generator: lorem
  length: { min: 5, max: 20 }

customer_name:
  type: text
  generator: name        # realistic full names
  locale: en
```

**Realistic `generator` keys:**

| Group | Keys |
|---|---|
| People | `name`, `first_name`, `last_name`, `email`, `username`, `phone`, `occupation`, `title`, `nationality` |
| Places | `address`, `street`, `city`, `state`, `country`, `postal_code` |
| Business/finance | `company`, `currency`, `price` |
| Internet | `url`, `hostname`, `ipv4` |
| Generic text | `word`, `sentence`, `color` |

---

## 5. Numeric distributions reference

These are the values for `dist:` on a `numeric` feature. Each row lists the
**required `params`**, what the distribution looks like, and an example.

| `dist` | `params` (all required) | Shape / support | Example |
|---|---|---|---|
| `normal` | `mean`, `std` (`std` > 0) | Symmetric bell curve, any real value | `{ mean: 40, std: 12 }` |
| `lognormal` | `mu`, `sigma` (`sigma` > 0) | Right-skewed, **positive only** (good for income, prices) | `{ mu: 10.5, sigma: 0.4 }` |
| `uniform` | `low`, `high` (`low` < `high`) | Flat — every value in `[low, high]` equally likely | `{ low: 0, high: 1 }` |
| `exponential` | `scale` (> 0) | Decaying, **non-negative** (waiting times) | `{ scale: 2.0 }` |
| `poisson` | `lam` (> 0) | **Discrete counts** 0,1,2,…; `lam` is the mean | `{ lam: 3 }` |
| `pareto` | `alpha`, `xm` (both > 0) | Heavy-tailed power law, **values ≥ `xm`** | `{ alpha: 2.5, xm: 1000 }` |

Notes:
- `lognormal`'s `mu`/`sigma` are the mean/SD **of the underlying normal** (in log
  space), not of the realized values. If you want a median of `M`, use
  `mu = ln(M)`.
- `poisson` always produces integers — you don't need `dtype: int` (but it's
  harmless).
- For `pareto`, `xm` is the minimum value and `alpha` controls tail heaviness
  (smaller = heavier tail).

```yaml
income:
  type: numeric
  dist: lognormal
  params: { mu: 10.5, sigma: 0.4 }   # median ≈ e^10.5 ≈ 36 316
  min: 0
visits:
  type: numeric
  dist: poisson
  params: { lam: 3 }                  # average 3 visits
```

---

## 6. The causal graph

By default every feature is sampled **independently**. The `causal` block lets
some columns be **derived** from others through a directed acyclic graph (DAG) of
structural equations — so you can encode real relationships like
`age → income → is_fraud`.

### 6.1 How a derived feature works

1. Declare the feature **without a `dist`** (numeric or boolean). That marks it as
   *derived* — its values will be computed, not sampled.
2. Add `causal.edges` pointing into it. Each edge contributes a number; a node
   **sums its incoming edges' contributions** and adds optional node noise.
3. For a **boolean** derived target, the summed value is treated as a probability
   (via the structural function) and a true/false is drawn from it.

```yaml
features:
  age:        { type: numeric, dist: normal, params: { mean: 40, std: 12 }, min: 18, max: 90, dtype: int }
  education:  { type: categorical, categories: [hs, college, grad], weights: [0.5, 0.4, 0.1] }
  income:     { type: numeric, dtype: float, min: 0 }   # derived (no dist)
  is_fraud:   { type: boolean }                          # derived target (no rate)

causal:
  edges:
    - { from: age,       to: income,   fn: linear,   weight: 800, bias: 10000 }
    - { from: education, to: income,   fn: map,      mapping: { hs: 0, college: 15000, grad: 40000 } }
    - { from: income,    to: is_fraud, fn: logistic, weight: -0.00002, bias: 1.0 }
  noise:
    income:   { dist: normal, params: { mean: 0, std: 5000 } }
    is_fraud: { dist: none }
```

This reads: *income = 800·age + 10000 + (0/15000/40000 by education) + N(0, 5000)
noise; the chance of fraud falls as income rises.*

### 6.2 `causal.edges`

A list of edges. Each edge has:

| Field | Type | What it does |
|---|---|---|
| `from` | string | Source (parent) feature name. |
| `to` | string | Destination (derived) feature name. |
| `fn` | string | The **structural function** (table below). |
| `weight` | number | Used by `linear` / `logistic`. |
| `bias` | number | Optional constant added by `linear` / `logistic`. |
| `coeffs` | list of numbers | Used by `polynomial` (`coeffs[i]` multiplies `xⁱ`). |
| `mapping` | mapping | Used by `map`: category → number. Must cover **every** category of the parent. |

**Structural functions (`fn`):**

| `fn` | Contribution of the edge | Needs | Use it for |
|---|---|---|---|
| `linear` | `weight · parent + bias` | `weight` (+ optional `bias`) | A straight-line effect. |
| `logistic` | `1 / (1 + e^−(weight·parent + bias))` | `weight` (+ optional `bias`) | Squashing a driver into a 0–1 probability — typically the **last** edge into a boolean target. |
| `polynomial` | `Σ coeffs[i] · parentⁱ` | `coeffs` (non-empty) | Curved / non-linear effects. |
| `map` | look up `mapping[parent_category]` | `mapping` covering all categories | Turning a **categorical** parent into a number. |
| `identity` | `parent` unchanged | — | Passing a value straight through. |

> Booleans are read as `0/1` when used as a numeric parent. A derived node may
> only be `numeric` or `boolean`. The graph must be **acyclic** (no loops) — the
> validator rejects cycles with a clear message.

### 6.3 `causal.noise`

A mapping of **derived node name → noise spec**, adding randomness on top of the
summed contributions.

| Form | Meaning |
|---|---|
| `{ dist: none }` | No noise — the node is a deterministic function of its parents. |
| `{ dist: <name>, params: {…} }` | Add a draw from any [numeric distribution](#5-numeric-distributions-reference) each row (usually `normal` with `mean: 0`). |

### 6.4 `causal.interventions` (optional)

Force a node to a constant value for **every** row (a `do(X = x₀)` operation from
causal inference). Descendants still react to the fixed value.

```yaml
causal:
  interventions:
    - { do: { income: 50000 } }   # pin income, see how is_fraud responds
```

| Field | Type | What it does |
|---|---|---|
| `do` | mapping `{feature: value}` | Fixes each named feature to a constant; overrides its edges. |

---

## 7. Failure injection

`failures` is an **ordered list** of corruptions applied *after* a clean baseline
is captured. The clean data is always preserved; the corrupted variant ships as
`data.injected.csv` when you ask for it (see [§9](#9-export)). Each failure has a
`type` plus type-specific fields. Failures run **top to bottom**, each seeing the
previous one's output.

Common to most: `column` (the feature to corrupt) and `rate` (a fraction in
`[0, 1]`).

### 7.1 Missingness (introduces blanks / `NaN`)

| `type` | What it does | Fields |
|---|---|---|
| `mcar` | **M**issing **C**ompletely **A**t **R**andom — blank cells chosen independently of the data. | `columns` (list) **or** `column`; `rate` |
| `mar` | **M**issing **A**t **R**andom — blanking probability depends on **another observed** column (`driver`). | `column`; `driver`; `rate`; `strength` (optional, default `2.0`) |
| `mnar` | **M**issing **N**ot **A**t **R**andom — blanking depends on the **column's own value** (or a given `driver`). | `column`; `driver` (optional, defaults to the column itself); `rate`; `strength` (optional, default `2.0`) |

For `mar`/`mnar`, `rate` is the *expected* fraction blanked (DataDoom calibrates
the mechanism to hit it), while `strength` sets how strongly the driver skews
*which* rows go missing.

```yaml
failures:
  - { type: mcar, columns: [age], rate: 0.05 }
  - { type: mnar, column: income, rate: 0.12, strength: 2.5 }   # high earners under-report
```

### 7.2 Label & feature corruption

| `type` | What it does | Fields |
|---|---|---|
| `label_noise` | Flip a boolean / reassign a categorical label to a **different** class. | `column` (boolean or categorical); `rate` |
| `feature_noise` | Add random noise to a numeric column: `x' = x + ε`. | `column` (numeric); `dist`; `params` |

```yaml
  - { type: label_noise, column: is_fraud, rate: 0.03 }
  - { type: feature_noise, column: age, dist: normal, params: { mean: 0, std: 2 } }
```

### 7.3 Distributional shift

| `type` | What it does | Fields |
|---|---|---|
| `drift` | Shift a numeric column gradually across the row index (concept drift). | `column`; `schedule` |
| `covariate_shift` | Affine-rescale a numeric column to hit a target mean/std. | `column`; `target: {mean?, std?}` |

The `drift` **`schedule`** is a mapping:

| Field | Type | What it does |
|---|---|---|
| `kind` | `linear` \| `step` | `linear` ramps smoothly; `step` jumps at a point. |
| `magnitude` | number | Total end-to-start shift. |
| `rate` | number | Alternative to `magnitude`: per-row slope (total = `rate·(n−1)`). |
| `at` | number in `[0,1]` | For `step` only: the fraction of the way through where the jump happens (default `0.5`). |

```yaml
  - { type: drift, column: income, schedule: { kind: linear, magnitude: 8000 } }
  - { type: covariate_shift, column: age, target: { mean: 50, std: 8 } }
```

### 7.4 Leakage

| `type` | What it does | Fields |
|---|---|---|
| `leakage` | Plant a **new** column that is a near-perfect proxy for a target (a classic "too good to be true" feature). | `target` (numeric/boolean); `into` (new column name, ≠ target); `noise` (optional, default `0.05`) |

`noise` is the proxy's noise level relative to the target's spread — smaller =
stronger (more obvious) leakage.

```yaml
  - { type: leakage, target: is_fraud, into: fraud_score, noise: 0.05 }
```

> Every failure also reports its **realized** effect (actual missing rate, flip
> fraction, leakage correlation, …) in `metadata.json`, computed from the data —
> not your requested knob. The numbers are honest.

---

## 8. Difficulty

The `difficulty` block calibrates a **binary classification** dataset so a
baseline model lands in a target accuracy band — useful for making benchmarks of
a known hardness. DataDoom runs a probe model, measures AUROC, and adaptively
adds noise until it lands in the band (reported honestly, misses flagged).

| Field | Type | Default | What it does |
|---|---|---|---|
| `target` | string **or** `{band: [a, b]}` | — | A named tier (table below) or an explicit AUROC band like `{ band: [0.7, 0.8] }`. |
| `label` | string | — (required) | The column the probe predicts. Must be a **boolean or 2-class categorical** feature. |
| `probe` | `logreg` \| `tree` | `logreg` | The baseline model used to measure difficulty. |
| `max_iters` | integer ≥ 1 | `8` | How many calibration steps to try. |
| `knobs` | list | `[noise, label_noise]` | Which levers to turn: `noise` (blur the predictors — primary) and `label_noise` (flip labels — deep end). |

**Named tiers** (target baseline AUROC, where 0.5 = chance, 1.0 = perfect):

| Tier | AUROC band | Feel |
|---|---|---|
| `beginner` | 0.90 – 0.99 | Easy — strong signal |
| `intermediate` | 0.80 – 0.90 | Moderate |
| `advanced` | 0.72 – 0.80 | Hard |
| `kaggle` | 0.62 – 0.72 | Very hard — near the edge of learnability |

```yaml
difficulty:
  target: advanced        # or: target: { band: [0.72, 0.80] }
  label: defaulted
  probe: logreg
  max_iters: 10
  knobs: [noise, label_noise]
```

> Difficulty works best on a dataset whose label is **generated by a causal
> graph** ([§6](#6-the-causal-graph)) — often with a **latent** `risk_score`
> (`emit: false`) that combines drivers into the label, so the probe must predict
> from genuine observables. See the worked example in [§12](#12-a-full-worked-example).

> **Expect a lower compliance score when you use `difficulty`.** Calibration
> deliberately *blurs the predictors* (the `noise` knob) to hit the target band,
> so those features no longer match their requested distribution and the fit
> tests in [§11](#11-how-datadoom-reports-fit-compliance) report a miss. That is
> **honest and intended** — the calibrated frame is the shipped dataset.

---

## 9. Export

The optional `export` block controls the output. All fields are optional.

| Field | Type | Default | What it does |
|---|---|---|---|
| `formats` | list | `[csv]` | Output formats: `csv`, `json`, `parquet`. (Parquet needs the `parquet` extra installed.) |
| `versions` | list | `[clean]` | Which variants to write: `clean` and/or `injected`. Use `[clean, injected]` to also write the corrupted `data.injected.csv` (only meaningful with `failures`). |
| `splits` | mapping | none | Split the rows into named files whose ratios **must sum to 1.0**, e.g. `{ train: 0.8, test: 0.2 }`. |
| `shuffle` | bool | `true` | Shuffle rows before splitting/writing (deterministically). |
| `metadata` | bool | `true` | Whether to write `metadata.json`. |

```yaml
export:
  formats: [csv, parquet]
  versions: [clean, injected]
  splits: { train: 0.8, test: 0.2 }
```

---

## 10. Running your spec

With the project's virtual environment active (`.venv`):

```powershell
# Validate (shape + cross-field checks, with a precise locator on errors)
datadoom validate my.datadoom.yaml

# Generate into out/
datadoom run my.datadoom.yaml --seed 42 --out out/

# Prove reproducibility (regenerates and compares checksums)
datadoom verify my.datadoom.yaml --seed 42
```

Outputs in `out/`:
- `data.csv` — your dataset (plus `data.injected.csv` if you exported `injected`).
- `metadata.json` — seed, `spec_hash`, per-file checksums, the **compliance**
  report ([§11](#11-how-datadoom-reports-fit-compliance)), and realized failure /
  difficulty stats.
- a resolved copy of the spec.

Prefer a UI? `datadoom serve` opens the web Canvas, which writes the exact same
YAML. Start from a built-in template with `datadoom template use <name> --out
my.datadoom.yaml`.

---

## 11. How DataDoom reports fit (compliance)

After generating, DataDoom checks each sampled numeric feature against the
distribution you requested and records the result in `metadata.json` under
`compliance`. It **never refits** parameters to the data — it reports the truth.

It picks the statistically valid test for each feature's shape:

| Feature shape | Test used (`test` field) | Why |
|---|---|---|
| Continuous, `float`, no clamping (e.g. plain `normal`/`lognormal`) | **Kolmogorov–Smirnov** (`ks`) against the requested CDF | The data is a clean continuous draw. |
| Integer (`dtype: int`), discrete (`poisson`), or **clamped** (`min`/`max`) | **Chi-square goodness-of-fit** (`chi2_gof`) against the *effective* PMF | Rounding/clamping/discreteness change the realized distribution; the boundary bins absorb the clamped tail mass. A KS test would falsely reject here. |

Each feature reports `passed` (did the fit hold at α = 0.05?), the `p_value`, the
empirical moments, and a `note` explaining the choice. A feature only shows
**`n/a`** (abstains, `test: "none"`) when no valid test can be formed (e.g. a
near-constant column). The overall `compliance_score` is the pass rate over
**assessable** features — a correct generator is never penalized for a transform
you deliberately applied (a clamped integer `age` now earns a real *pass*, not a
0).

```jsonc
// metadata.json → compliance.features[…]
{
  "feature": "age", "dist": "normal", "test": "chi2_gof",
  "p_value": 0.148, "passed": true,
  "clamped_fraction": 0.033,
  "note": "chi-square goodness-of-fit vs the effective PMF (57 bins, dof 56); KS not applicable (integer discretization, clamping (3.3%))"
}
```

---

## 12. A full worked example

A causal credit-default dataset, dialed to the `advanced` difficulty band, with a
latent risk score and a couple of injected failures — every section in one file:

```yaml
datadoom_version: "1"
name: "credit-default-demo"
description: "Causal credit-default benchmark with latent risk, calibrated difficulty, and failures."
seed: 17
rows: 6000

features:
  income:
    type: numeric
    dist: normal
    params: { mean: 60000, std: 20000 }
    min: 0
  debt_ratio:
    type: numeric
    dist: normal
    params: { mean: 0.35, std: 0.12 }
    min: 0
  inquiries:
    type: numeric
    dist: poisson
    params: { lam: 2 }
    dtype: int
  risk_score:
    type: numeric          # latent: combines the drivers into one logit
    dtype: float
    emit: false            # hidden — drives the label but is NOT shipped
  defaulted:
    type: boolean          # the label (derived)

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
  max_iters: 10
  knobs: [noise, label_noise]

failures:
  - { type: mnar, column: income, rate: 0.10, strength: 2.0 }   # high earners hide income
  - { type: label_noise, column: defaulted, rate: 0.02 }         # a few mislabels

export:
  formats: [csv]
  versions: [clean, injected]
  splits: { train: 0.8, test: 0.2 }

meta:
  problem_statement: "Predict defaulted from income, debt_ratio, inquiries."
  tags: [causal, difficulty, failure-injection, classification]
```

Run it, then open `metadata.json` to see the compliance report, the realized
difficulty (achieved AUROC + the calibration trace), and the realized failure
effects.

---

## 13. Quick reference / cheat-sheet

```yaml
datadoom_version: "1"
name: "slug-name"
seed: 42
rows: 1000

features:
  num:   { type: numeric, dist: normal, params: { mean: 0, std: 1 }, min: -3, max: 3, dtype: float }
  cat:   { type: categorical, categories: [a, b, c], weights: [3, 2, 1] }
  flag:  { type: boolean, rate: 0.3 }
  when:  { type: datetime, start: "2023-01-01", end: "2024-12-31", granularity: day }
  label: { type: text, generator: name, locale: en }
  hidden:{ type: numeric, dist: normal, params: { mean: 0, std: 1 }, emit: false }   # latent

causal:
  edges:
    - { from: num, to: derived, fn: linear, weight: 2, bias: 1 }
    - { from: cat, to: derived, fn: map, mapping: { a: 0, b: 5, c: 10 } }
  noise:
    derived: { dist: normal, params: { mean: 0, std: 1 } }
  interventions:
    - { do: { num: 0 } }

failures:
  - { type: mcar,            columns: [num], rate: 0.05 }
  - { type: mar,             column: num, driver: flag, rate: 0.1, strength: 2.0 }
  - { type: mnar,            column: num, rate: 0.1, strength: 2.0 }
  - { type: label_noise,     column: cat, rate: 0.03 }
  - { type: feature_noise,   column: num, dist: normal, params: { mean: 0, std: 0.5 } }
  - { type: drift,           column: num, schedule: { kind: linear, magnitude: 5 } }
  - { type: covariate_shift, column: num, target: { mean: 1, std: 2 } }
  - { type: leakage,         target: flag, into: flag_proxy, noise: 0.05 }

difficulty:
  target: intermediate     # beginner | intermediate | advanced | kaggle | { band: [a, b] }
  label: flag
  probe: logreg            # logreg | tree
  max_iters: 8
  knobs: [noise, label_noise]

export:
  formats: [csv]           # csv | json | parquet
  versions: [clean]        # clean | injected
  splits: { train: 0.8, test: 0.2 }
  shuffle: true
  metadata: true
```

**Distribution params:** `normal{mean,std}` · `lognormal{mu,sigma}` ·
`uniform{low,high}` · `exponential{scale}` · `poisson{lam}` · `pareto{alpha,xm}`.

**Structural fns:** `linear{weight,bias?}` · `logistic{weight,bias?}` ·
`polynomial{coeffs}` · `map{mapping}` · `identity`.

---

*See `examples/*.datadoom.yaml` for runnable specs covering each feature, and
`docs_v2/04_DataDoom_Spec_Reference.md` for the formal schema. Manual
walkthroughs with expected output live in `testing_guide.md`.*
