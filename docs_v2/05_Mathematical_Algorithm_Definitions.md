# 05 — Mathematical & Algorithm Definitions

> The honest mathematical foundation. Obeys `00_README_Index.md`. Where the legacy docs were wrong (KS auto-correction; bitwise-everywhere), this doc states the correct, defensible version.

All algorithms assume: an immutable spec snapshot, a deterministic seed, execution inside a `RunContext`, and statistical reports persisted as first-class outputs.

---

## 1. Determinism Framework

### 1.1 Canonical serialization & spec hash
Let `spec'` = the spec with the `seed` field removed. Define canonical JSON `C(spec')`:
- object keys sorted lexicographically,
- no insignificant whitespace,
- numbers normalized (no trailing zeros; integers as integers),
- arrays preserve author order (order is semantic for `failures`, `categories`, `weights`).

Then `spec_hash = SHA256(C(spec'))` (hex).

### 1.2 Seeded RNG model
Given `spec_hash` and integer `seed S`, define per-namespace keys:
`key(ns) = SHA256(spec_hash || ":" || S || ":" || ns)` → first 8 bytes → uint64.

Each namespace gets an independent generator: `RNG(ns) = numpy.random.Generator(PCG64(key(ns)))`.

Namespaces (`ns`) are stable strings: `feature:<name>`, `noise:<name>`, `failure:<index>`, `probe:<name>`, `shuffle`. Independent namespaces guarantee that adding a feature does not perturb others' streams.

### 1.3 Reproducibility theorem (scoped)
For identical `(spec_hash, S)` executed on the **pinned path** (single-threaded BLAS, pinned numpy/scipy, CPU), the produced artifact bytes are identical:
`D(spec_hash, S) = D'(spec_hash, S)` ⇒ equal SHA256 checksums.

**Scope caveat (honest):** this holds on the pinned path only. Multithreaded BLAS reductions, GPU kernels, and cross-architecture FP differences can break bitwise equality; we do not claim it there. Verified by the CI repro matrix (`13`).

---

## 2. Distribution Sampling & Honest Compliance

### 2.1 Sampling
For feature `f` with target `D(θ)`, draw `X = {x₁..xₙ}` from `RNG(feature:f)`. Sampling is **correct by construction** — the data *is* drawn from `D(θ)`.

Optional clamp to `[min,max]` is a truncation `x ← clip(x, min, max)`; truncation changes the realized distribution and is recorded.

### 2.2 Empirical fit & KS reporting
Empirical CDF: `Fₙ(x) = (1/n) Σ I(xᵢ ≤ x)`.
KS statistic: `Dₙ = supₓ |Fₙ(x) − F(x; θ)|`; report `Dₙ` and its p-value.

**Compliance score** over `m` numeric features: `Score = (1/m) Σ I(p_value_j > α)`, default `α = 0.05`. Target: > 95% (a sanity check on the generator and on clamping side-effects).

### 2.3 What we do NOT do (correction of the legacy error)
We **do not** run `θ* = argmin_θ KS(Fₙ, F(θ))` against our own sample. Re-fitting parameters to the realized sample overfits finite-sample noise and makes the data match itself rather than the user's requested `θ` — it would *break* the guarantee it pretends to give. The ~5% KS "failures" at `α=0.05` are expected sampling variance, not defects.

**Legitimate, opt-in alternative — reference fitting:** if the user supplies a *real reference sample* `R`, we may fit `θ̂ = MLE(R)` (or moment-match) **before** sampling, then sample from `D(θ̂)`. This is "match my real data," a different, honest feature — never an automatic post-hoc loop.

---

## 3. Structural Equation Modeling (Causal Engine)

Given DAG `G=(V,E)` (validated acyclic). Compute topological order `τ(V)`.

For each node `v` with incoming edges `e₁..e_k` from parents `p₁..p_k`:
```
contrib(v) = Σ_j  fn_{e_j}( value(p_j) ; params_{e_j} )
v          = contrib(v) + ε_v
```
- `ε_v ~ noise[v]` drawn from `RNG(noise:v)` (or 0 if `dist: none`).
- Structural functions:
  - `linear`: `w·p (+ b)`
  - `logistic`: `σ(w·p + b)`, `σ(z)=1/(1+e^{-z})` → probability; for boolean child, sample `Bernoulli(σ)` from `RNG(feature:v)`.
  - `polynomial`: `Σ_i c_i p^i`
  - `map`: categorical `p` → `mapping[p]`
  - `identity`: `p`
  - plugin: arbitrary `f(p; θ)` honoring the RNG contract.

Generation walks `τ(V)`; roots are sampled in §2, derived nodes computed as above.

### 3.1 Interventions & counterfactuals
`do(X = x₀)`: replace `X`'s structural equation with the constant `x₀` and remove its incoming edges; recompute descendants.
Counterfactual contrast: `Δ = E[Y | do(X=x₀)] − E[Y | X=x_obs]`, estimated empirically over the generated rows.

---

## 4. Failure Injection Algorithms

Applied after a clean baseline `D_clean` is captured; produce `D_injected`. Each uses its own `RNG(failure:i)`.

- **MCAR:** mask `mᵢ ~ Bernoulli(p)` independent of data; set NaN where `m=1`.
- **MAR:** `P(M=1 | X_obs) = σ(β·driver)`; missingness depends on an *observed* driver column.
- **MNAR:** `P(M=1 | X) = σ(γ·X)`; missingness depends on the value itself (or an unobserved driver).
- **Label noise:** flip label with prob `p` (for binary), or perturb within class set.
- **Feature noise:** `x' = x + ε`, `ε ~ dist(params)`.
- **Concept drift:** parameters shift over index/time `t`: `θ(t) = θ₀ + λ·g(t)` (e.g. linear `g(t)=t/n`).
- **Covariate shift:** resample/reweight a feature toward a target distribution `P_test ≠ P_train` (mixture reweighting).
- **Leakage:** construct `into = h(target) + small noise`, planting a high-MI proxy for the label.

Each failure reports a **diff summary** (e.g. fraction nullified, MI(into; target), distribution shift magnitude).

---

## 5. Difficulty Calibration (Empirical Target)

Difficulty is defined operationally: a dataset is "as hard as" the score a standard baseline achieves on it.

### 5.1 Probe evaluation
Split `D` into train/holdout (seeded). Train probe model `M` (default `logreg`; or `tree`/plugin) on the label column. Compute the task metric `μ` on the holdout (AUROC for binary classification; accuracy/F1/RMSE as appropriate).

### 5.2 Adaptive loop
Target band `[a,b]` (from explicit band or a named tier). Iterate up to `max_iters`:
```
generate → evaluate μ
if μ ∈ [a,b]: stop (success)
elif μ > b:   make harder  (increase noise σ and/or class imbalance, within `knobs`)
else:         make easier  (decrease noise / rebalance)
adjust step via simple bisection on the knob magnitude
```
Report achieved `μ`, iterations used, final knob values, and whether the band was met. If not met within `max_iters`, return the closest and flag it (honest — no silent failure).

### 5.3 Named tier → band mapping
Tiers map to validated bands for binary classification AUROC (tunable, validated in `13`):
| tier | band (AUROC) |
|---|---|
| beginner | [0.90, 0.99] |
| intermediate | [0.80, 0.90] |
| advanced | [0.72, 0.80] |
| kaggle | [0.62, 0.72] |

> These numbers are **calibration targets**, validated against real baselines before release; they are not asserted as ground truth in v0.1. Regression tests in `13` keep them honest.

### 5.4 Reference metrics (reported, not optimized blindly)
For transparency we also report (without combining them into a single opaque index):
- Linear separability proxy: holdout accuracy of a linear probe.
- Noise-to-signal: `Var(ε)/Var(signal)` where signal is known (we generated it).
- Per-feature entropy `H(Xⱼ) = −Σ p log p` and mutual-information matrix `I(Xᵢ;Xⱼ)`.
- Class imbalance ratio.

We deliberately **avoid** a single `D_final = Σ wᵢ·scoreᵢ` index with arbitrary weights — it mixes unnormalized scales and isn't interpretable.

---

## 6. Time-Series Generation

Additive decomposition for a series `Xₜ`:
```
Xₜ = T(t) + S(t) + AR(p) + εₜ
T(t) = α·t + β                      # trend
S(t) = A·sin(2πt/period + φ)        # seasonality
AR(p): Xₜ ⊃ Σ_{i=1}^p φ_i X_{t−i}   # autoregressive component
εₜ ~ Normal(0, σ²) from RNG(noise:series)
```
Stationarity/▕φ▏ constraints validated. Multivariate/hierarchical series are deferred (plugin/post-v1).

---

## 7. Statistical Compliance Summary (artifact-level)

Persisted into `Report`:
- per-feature: target params, empirical params, KS `Dₙ`, p-value, clamp effect.
- correlation matrix (Pearson) + MI matrix.
- causal ground-truth graph (the true `G`).
- difficulty: target band, achieved metric, probe, iterations.
- failure diff summaries.
- determinism: `spec_hash`, `seed`, per-namespace key digests, artifact checksums.

---

## 8. Determinism Validation Constraint

Let `A₁, A₂` be artifact checksums from two pinned-path runs with identical `(spec_hash, S)`. Constraint: `A₁ = A₂`. Any violation increments a `reproducibility_failure` metric and **fails CI** (`13`).

---

## 9. Complexity Notes (feeds Resource Estimation, doc 12)

- Base sampling: `O(n·f)`.
- SEM execution: `O(n·(f + |E|))`.
- Failure injection: `O(n·(#failures))`.
- Difficulty probe: `O(iters · train_cost(M, n, f))` — the dominant cost when enabled; keep probes small/fast.
- KS reporting: `O(n log n)` per numeric feature (sorting for ECDF).

---

## 10. Mapping to System Components

| Math section | Module (`engine/`) | Doc |
|---|---|---|
| §1 determinism | `rng`, `spec` | 03, 13 |
| §2 distributions | `dist` | 04, 09 |
| §3 SEM | `causal` | 04 |
| §4 failures | `failure` | 04 |
| §5 difficulty | `difficulty` | 04, 13 |
| §6 time-series | `dist`/timeseries | 04 |
| §7–8 reports/validation | `pipeline`, reports | 06, 13 |
