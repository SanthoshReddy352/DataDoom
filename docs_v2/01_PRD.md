# 01 — Product Requirements Document (DataDoom v2, Open Source)

> Canonical product definition. Obeys the locked decisions in `00_README_Index.md`.

---

## 1. Vision

**DataDoom lets anyone design a dataset the way they reason about it — distributions, causal relationships, difficulty, and failure modes — and regenerate it identically, forever, from a single file.**

It is not a row generator and not a prompt wrapper. It is a **controllable experimental data laboratory** you install and run yourself. You describe the reality you want to simulate; DataDoom produces a dataset that provably matches that description and can be reproduced bit-for-bit by anyone with the same spec.

**North star:** *a synthetic dataset should be as version-controllable, shareable, and reproducible as source code.*

---

## 2. Problem Statement

Teams need realistic datasets when real data is **scarce, sensitive, expensive, or non-existent** — for model development, teaching, benchmarking, and hackathons. The current options each fail on a key axis:

- **Prompt an LLM:** convenient, but not reproducible, can't enforce distributions, has no explicit causal structure, no difficulty control, and no systematic failure modes.
- **Hand-roll with NumPy/Faker:** flexible but ad-hoc, unshareable, undocumented, and rarely reproducible across machines.
- **Existing synthetic-data libraries (SDV, etc.):** strong at fitting real data, but weaker at *authoring from scratch* with explicit causal graphs, an interactive UI, difficulty targeting, and a shareable spec artifact.

**Nobody combines, in one installable, local-first tool with a real UI:** (a) strict seed reproducibility, (b) user-authored causal DAG/SEM, (c) explicit ML-difficulty targeting, and (d) systematic failure-mode injection. **That combination is DataDoom's reason to exist.**

---

## 3. Why Open Source & Installable

DataDoom is designed to become a **widely adopted open-source project**, not a personal tool and not a hosted SaaS. That choice drives the entire design:

1. **Zero-friction adoption.** `pip install datadoom` → `datadoom` → a browser opens. No account, no cloud, no API key. Works offline. (Adoption model: Jupyter, Label Studio, MLflow, Streamlit.)
2. **Reproducibility is the killer OSS feature.** A spec is a small text file; commit it to git and anyone regenerates the *identical* dataset. This makes synthetic data citable in papers and usable as fixtures in CI.
3. **Extensibility is the growth engine.** The community adds distributions, failure modes, templates, and exporters via plugins — without touching core.
4. **Trust through transparency.** Correctness claims (determinism, compliance, causal structure) are only believable if the code is open and the guarantees are testable. Open source *is* the credibility.

**Non-goal:** DataDoom core is not billing, not multi-tenant SaaS, not managed cloud. A hosted/team edition may exist later as an *optional* layer; the OSS core must be complete and excellent alone.

---

## 4. Users & Use Cases

### 4.1 Personas
1. **ML practitioner / data scientist** — needs realistic, hard, structured data to build and stress-test models.
2. **Hackathon organizer / participant** — needs dataset + problem statement + metric + hidden split in minutes.
3. **Educator / student** — needs datasets with *known ground truth* (true causal graph, true noise) to teach/learn.
4. **Library / tool author** — needs deterministic fixtures and edge-case data for tests and benchmarks.
5. **Contributor** — wants to extend DataDoom and get it adopted.

### 4.2 Jobs-to-be-done (representative)
- "50k rows where `income` causally depends on `age` & `education`, with 12% MNAR missingness in `income` correlated with low education."
- "A fraud-detection dataset at 'Kaggle-hard' difficulty with a hidden test split."
- "Reproduce exactly the dataset from this paper's `dataset.datadoom.yaml`."
- "Use the same fixture in CI so model tests are deterministic."

---

## 5. Product Principles

1. **Local-first, zero-config.** Runs on a laptop with no external services (SQLite + local files). Cloud/team features strictly opt-in.
2. **Spec-as-source-of-truth.** Everything the UI does is captured in a human-readable, versionable spec. UI edits it; engine executes it; git stores it.
3. **Reproducible by construction.** `spec + seed → identical dataset`, enforced and CI-tested on the pinned path.
4. **Honest guarantees.** We report what is statistically true; we never claim a guarantee the math doesn't support.
5. **Composable & extensible.** Distributions, failure modes, templates, exporters are runtime-discovered plugins.
6. **Website is the front door; API is the back door.** Great human UX + clean programmatic API, both over one engine.

---

## 6. Surfaces

DataDoom ships **one engine** with three surfaces. The **web app is primary**. (Full UX in `02_User_Flow_Guide.md`; surface details in `03_Technical_Architecture.md` and `08_API_Contract.md`.)

- **Web App (primary):** local-first SPA served by the DataDoom server — dashboard, schema builder, causal-graph canvas, failure configurator, difficulty selector, real-time generation tracker, results & reports, export. Launched by `datadoom`.
- **CLI (launcher + automation):** `datadoom` (start app), `datadoom run spec.yaml`, `datadoom validate`, `datadoom verify`, `datadoom plugins`.
- **Python Library (embedding):** `import datadoom as dd; ds = dd.generate(dd.Spec.from_file(...), seed=42)`.

---

## 7. Functional Requirements (Capabilities)

> Math in `05_Mathematical_Algorithm_Definitions.md`; spec syntax in `04_DataDoom_Spec_Reference.md`.

### 7.1 Deterministic generation engine
- Seeded RNG wrapper used by **all** randomness (engine invariant #1).
- `(spec_hash, seed) → bitwise-identical artifact` on the pinned path.
- Memory-aware chunking / streaming for large row counts.

### 7.2 Distributions
- Built-in: Normal, LogNormal, Poisson, Pareto, Uniform, Exponential, Bernoulli, Categorical, Datetime, truncated/bounded variants.
- Custom distributions via plugin.
- **Honest** post-generation compliance report (empirical fit, KS stat + p-value). No auto-correction theater.

### 7.3 Causal / structural generation
- User-authored DAG; cycle detection; topological execution.
- Structural equations per node: linear, logistic, polynomial, mapping, custom (plugin).
- Configurable noise terms.
- Interventions `do(X=x)` and counterfactual generation.
- Emits the **true causal graph** as ground truth.

### 7.4 Failure injection
- Missingness: MCAR / MAR / MNAR.
- Label noise, feature noise, bounded adversarial perturbation.
- Concept drift, covariate shift, leakage traps.
- Each is a plugin-able transform with a before/after diff; always preserves a **clean baseline + injected variant**.

### 7.5 Difficulty calibration
- Small fast probe models measure separability / achievable metric.
- Adaptive loop adjusts noise/imbalance toward target band.
- Report shows target vs. achieved and the baseline model used.

### 7.6 Templates / domain library
- Built-in starter templates (fraud, churn, readmission, …): dataset + problem statement + metric + hidden split.
- Community templates are shared spec files — importable, reviewable in PRs.

### 7.7 Export & reporting
- Formats: CSV, Parquet, JSON; adapters for pandas/polars, PyTorch `Dataset`, TF `Dataset`, Hugging Face `datasets`.
- Splits: train/test/hidden.
- Metadata bundle: spec, spec_hash, seed, distribution summary, correlation matrix, causal graph, failure log, checksums.

### 7.8 Extensibility
- Plugin types: Distribution, StructuralFn, FailureMode, Exporter, Template, ProbeModel (see `09_Plugin_System.md`).
- Plugins declare a schema fragment the web UI renders automatically.

---

## 8. Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Install** | `pip install datadoom` succeeds on Win/macOS/Linux, Python 3.11+; first dataset in **< 5 min**. |
| **Offline** | Full core functionality with no network access. |
| **Reproducibility** | Bitwise-repro failure rate **< 0.1%** on pinned path, measured in CI across OSes. |
| **Compliance** | Reported compliance score **> 95%** for built-in distributions at default sample sizes. |
| **Performance** | 50k rows × 20 features tabular generation in **< 10 s** on a typical laptop CPU. |
| **Footprint** | Runs in **< 2 GB RAM** for default workloads; streaming path for large rows. |
| **Accessibility** | Web UI keyboard-navigable; WCAG-AA color contrast in default (dark) theme. |
| **Privacy** | No telemetry by default; any analytics strictly opt-in (see `14_Security_and_Privacy.md`). |

---

## 9. Scope Boundaries

**In (v1 core):** tabular + time-series; deterministic engine; distributions; causal DAG/SEM; failure injection; difficulty targeting; reports; export adapters; web Canvas; CLI; Python API; plugin system; templates; local-first install.

**Deferred (opt-in, post-v1):** graph/network data; richer/multivariate time-series; team/server mode (Postgres, accounts, sharing); hosted edition; advanced probe models.

**Out (core):** GAN/VAE image synthesis; multi-modal image/text; SaaS billing/quotas/SLA; multi-region infra; Kafka; gRPC/Protobuf; multi-tenant RLS; non-deterministic data-path code.

---

## 10. Success Metrics (OSS-appropriate)

- **Reach:** PyPI downloads/month; Docker pulls; GitHub stars.
- **Reproducibility integrity:** repro failure rate < 0.1% on pinned path (CI, cross-OS).
- **Compliance:** compliance score > 95% on built-ins.
- **Community health:** external contributors; community plugins/templates; issue/PR response time.
- **Time-to-first-dataset:** `pip install` → generated dataset in < 5 min.
- **Real-world use:** specs found in public repos/papers.

*(Explicitly **not** revenue or paid retention — those belong to a possible future hosted edition, not the OSS core.)*

---

## 11. Release Strategy

- **0.1 (Alpha):** deterministic tabular core + headless `datadoom run` + minimal web Canvas (schema → generate → preview/export).
- **0.x (Beta):** causal engine, failure injection, difficulty targeting, plugin API, templates.
- **1.0:** stable spec format + plugin API, docs site, cross-OS reproducibility matrix green, export adapters complete.

Versioning: **SemVer**; the **spec format** is versioned independently via `datadoom_version` with additive-only evolution within a major.

---

## 12. Assumptions & Risks

| Risk | Mitigation |
|---|---|
| Name/package collision (`datadoom`) | Verify PyPI + GitHub availability before 0.1 tag. |
| Cross-platform bitwise determinism is subtle (BLAS threads, FP) | Pin single-threaded path + version-pin numpy/scipy; CI repro matrix (doc 13). |
| Scope creep back toward the old SaaS design | Scope fences in `00` are enforced in review. |
| "Why not just an LLM / SDV?" positioning | Sharpen to the 4-axis differentiator; lean on (not rebuild) libraries. |
| Difficulty labels not meaningful | Validate tier→band mapping against real baselines (doc 05/13). |

---

## 13. Conclusion

DataDoom v2 is a **local-first, installable, open-source synthetic-data laboratory** whose primary surface is a web Canvas and whose center of gravity is a **reproducible, version-controllable spec file**. It wins not by out-scaling cloud SaaS, but by being **trustworthy, extensible, and effortless to install** — sharpened to four defensible axes: **reproducibility, causal structure, difficulty targeting, and failure injection.**
