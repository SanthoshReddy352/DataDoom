# DataDoom — Product Requirements Document (v2, Open Source)

> **Supersedes:** `PRD.md` (HackForge AI). This is the canonical product definition.
> **Product:** DataDoom — an open-source engine for controllable, reproducible synthetic data.
> **License intent:** Apache-2.0 (permissive, adoption-friendly, patent grant).
> **Primary surface:** the **web app** (a local-first Canvas). The CLI is a launcher/automation surface, **not** the point of contact.
> **Companion doc:** architecture rationale in `DataDoom_Critical_Analysis_and_Recommended_Architecture.md`.

---

## 1. Vision

**DataDoom lets anyone design a dataset the way they reason about it — distributions, causal relationships, difficulty, and failure modes — and regenerate it identically, forever, from a single file.**

It is not a "row generator" and not a prompt wrapper. It is a **controllable experimental data laboratory** you install and run yourself. You describe the *reality* you want to simulate; DataDoom produces a dataset that provably matches that description and can be reproduced bit-for-bit by anyone with the same spec.

The north star: **a synthetic dataset should be as version-controllable, shareable, and reproducible as source code.**

---

## 2. Why Open Source, and Why Installable

DataDoom is designed to be a **widely adopted open-source project**, not a personal tool and not a hosted SaaS. That choice drives the whole design:

- **Zero-friction adoption.** `pip install datadoom` → `datadoom` → a browser opens. No account, no cloud, no API key, no external services. Works fully offline. (Reference adoption model: Jupyter, Label Studio, MLflow, Streamlit.)
- **Reproducibility is the killer OSS feature.** A DataDoom spec is a small text file. Commit it to git; anyone who runs it gets the *identical* dataset. This makes synthetic data citable in papers, shareable in repos, and usable as a fixture in CI.
- **Extensibility is the growth engine.** The community — not the core team — should be able to add distributions, failure modes, domain templates, and exporters via a **plugin system**, without touching core.
- **Trust through transparency.** Synthetic-data correctness claims (determinism, distribution compliance, causal structure) are only believable if the code is open and the guarantees are testable. Open source *is* the credibility.

**Non-goal:** DataDoom is not a billing platform, not multi-tenant SaaS, and not a managed cloud product in its core. A hosted/team edition may exist later as an *optional* layer, but the open-source core must be complete and excellent on its own.

---

## 3. Users & Use Cases

### 3.1 Personas

1. **The ML practitioner / data scientist** — needs realistic, *hard*, structured data to develop and stress-test models when real data is scarce, sensitive, or unavailable.
2. **The hackathon organizer / participant** — needs a ready dataset + problem statement + hidden test split, generated in minutes from a template.
3. **The educator / student** — needs datasets with *known* ground truth (true causal graph, true noise level) to teach and learn ML and statistics.
4. **The library/tool author** — needs deterministic fixtures and edge-case data for tests and benchmarks.
5. **The contributor** — wants to extend DataDoom with a new distribution, failure mode, domain template, or exporter and have it adopted.

### 3.2 Core jobs-to-be-done

- "Give me 50k rows where `income` causally depends on `age` and `education`, with a realistic 12% missingness in `income` that's correlated with low education (MNAR)."
- "Generate a fraud-detection dataset at 'Kaggle-hard' difficulty with a hidden test split."
- "Reproduce exactly the dataset from this paper's `dataset.datadoom.yaml`."
- "Use the same fixture dataset in CI so my model tests are deterministic."

---

## 4. Product Principles

1. **Local-first, zero-config.** Runs on a laptop with no external dependencies (SQLite + local files by default). Cloud/team features are strictly opt-in.
2. **Spec-as-the-source-of-truth.** Everything the UI does is captured in a human-readable, version-controllable **DataDoom Spec** (YAML/JSON). The website edits the spec; the engine executes the spec; git stores the spec.
3. **Reproducible by construction.** `spec + seed → identical dataset`, enforced as a hard, tested guarantee on a defined execution path.
4. **Honest guarantees.** We report what is statistically true; we never claim a guarantee the math doesn't support (see §7.5).
5. **Composable & extensible.** Distributions, failure modes, templates, and exporters are plugins discovered at runtime.
6. **The website is the front door; the API is the back door.** Great UX for humans, clean programmatic API for automation — both drive the same engine.

---

## 5. Surfaces (How Users Interact)

DataDoom ships **one engine** with three surfaces over it. The **web app is primary.**

### 5.1 Web App (primary point of contact)
A local-first single-page app served by the DataDoom server. This is the Canvas described in the User Flow Guide:
- Dashboard of datasets/specs (Draft / Running / Completed / Failed).
- **Schema builder** (smart-table view): columns, types, distributions, parameters.
- **Causal graph builder** (node/edge canvas, React Flow): define and visualize the DAG; live cycle detection.
- **Failure injection configurator** with live diff preview.
- **Difficulty target** selector with empirical feedback.
- **Real-time generation tracker** (WebSocket/SSE stage updates + live logs).
- **Results**: data preview, distribution charts, correlation matrix, evaluation/compliance report, clean-vs-injected comparison.
- **Export** to file formats + downloadable spec + metadata.

Launched by: `datadoom` (starts server, opens browser). No login required for local mode.

### 5.2 CLI (launcher + automation, *not* the point of contact)
- `datadoom` — start the web app (the normal entry point).
- `datadoom run spec.yaml [--seed N] [--out ./data]` — headless generation for CI/scripts.
- `datadoom validate spec.yaml` — static validation of a spec.
- `datadoom verify spec.yaml --against artifact.csv` — confirm an artifact matches a spec+seed (reproducibility check).
- `datadoom plugins list/install` — manage extensions.

### 5.3 Python Library (embedding)
```python
import datadoom as dd
spec = dd.Spec.from_file("dataset.datadoom.yaml")
ds = dd.generate(spec, seed=42)        # deterministic
df = ds.to_pandas()                    # or .to_torch(), .to_parquet(...)
print(ds.report.compliance_score)
```
For use in notebooks, pipelines, tests, and other libraries.

---

## 6. The DataDoom Spec (the heart of the project)

A single declarative, versioned file that fully determines a dataset. The web UI is a structured editor for it; the engine is its interpreter. Example shape:

```yaml
datadoom_version: "1"
name: "fraud-detection-medium"
seed: 42                      # optional; omitted → deterministic seed recorded on first run
rows: 50000

features:
  age:        { type: numeric, dist: normal,  params: { mean: 40, std: 12 }, min: 18 }
  education:  { type: categorical, categories: [hs, college, grad], weights: [0.5, 0.4, 0.1] }
  income:     { type: numeric, dist: lognormal, params: { mu: 10, sigma: 0.6 } }
  is_fraud:   { type: boolean }

causal:                        # DAG; nodes are features, edges are dependencies
  edges:
    - { from: age,        to: income, fn: linear, weight: 800 }
    - { from: education,  to: income, fn: map, mapping: { hs: 0, college: 15000, grad: 40000 } }
    - { from: income,     to: is_fraud, fn: logistic, weight: -0.00002, bias: -2 }

difficulty:
  target: kaggle               # beginner | intermediate | advanced | kaggle | { metric: auroc, band: [0.72, 0.78] }

failures:
  - { type: mnar, column: income, rate: 0.12, driver: education }
  - { type: label_noise, column: is_fraud, rate: 0.03 }

export:
  formats: [csv, parquet]
  splits: { train: 0.7, test: 0.2, hidden_test: 0.1 }
  metadata: true               # writes spec hash, seed, distribution & causal summary, checksums
```

**Properties that make this the project's center of gravity:**
- It is the unit of sharing, versioning, citation, and reproduction.
- `spec_hash = sha256(canonical(spec))`; `(spec_hash, seed)` uniquely identifies an artifact.
- Forward/backward compatibility via `datadoom_version` and additive-only schema evolution.

---

## 7. Core Capabilities (Scope)

### 7.1 Deterministic generation engine
- Seeded RNG wrapper used by **all** randomness (no stdlib `random`/`uuid4`/`time` in the data path).
- `(spec_hash, seed) → bitwise-identical artifact` on the pinned single-threaded CPU path (see §7.5).
- Memory-aware chunking / streaming for large row counts.

### 7.2 Distributions
- Built-in: Normal, LogNormal, Poisson, Pareto, Uniform, Exponential, Bernoulli, Categorical, Datetime, Bounded/truncated variants.
- Custom distributions via **plugin interface**.
- Honest post-generation **compliance report** (empirical fit, KS statistic + p-value) — reported, not "auto-corrected" (see §7.5).

### 7.3 Causal / structural generation
- User-authored **DAG**; cycle detection; topological execution.
- **Structural equations** per node: linear, logistic, polynomial, mapping, custom (plugin).
- Noise terms with configurable variance.
- **Interventions** (`do(X=x)`) and **counterfactual** generation.
- Outputs the *true* causal graph as ground truth — a key teaching/research feature.

### 7.4 Failure injection
- Missingness: MCAR, MAR, MNAR.
- Label noise, feature noise, adversarial perturbation (bounded).
- Concept drift, covariate shift, data leakage traps.
- Each is a plugin-able transform with a **before/after diff** the UI visualizes.
- Always produces a **clean baseline + injected variant** for comparison.

### 7.5 Honest statistical guarantees (explicit design stance)
- **Reproducibility:** guaranteed and CI-tested on the pinned path (single-threaded, fixed library versions, CPU). We do **not** claim bitwise reproducibility across GPUs/threads/heterogeneous nodes.
- **Distribution compliance:** we *sample correctly from the requested distribution* and *report* the empirical fit. We do **not** run a "KS auto-correction loop" that refits parameters to the sample — that overfits sampling noise and contradicts the user's intent. (Fitting to a *user-supplied real reference sample* is a separate, opt-in feature.)
- **Difficulty:** treated as an **empirical target**, not a closed-form index. DataDoom regenerates/adjusts noise & imbalance until a held-out **probe model** lands in the requested metric band, and reports the achieved metric. Named tiers (Beginner…Kaggle) map to validated metric bands.

### 7.6 Difficulty calibration
- Probe models (small, fast) measure separability / achievable AUROC-or-accuracy.
- Adaptive loop adjusts noise/imbalance toward the target band.
- Report shows target vs. achieved with the baseline model used.

### 7.7 Templates / domain library
- Built-in starter templates (fraud, churn, healthcare readmission, etc.): each yields dataset + problem statement + metric + hidden split.
- **Community templates** are just shared spec files — installable/importable, reviewable in PRs.

### 7.8 Export & reporting
- Formats: CSV, Parquet, JSON; adapters for pandas/polars, PyTorch `Dataset`, TF `Dataset`, Hugging Face `datasets`.
- Splits (train/test/hidden).
- Metadata bundle: spec, spec_hash, seed, distribution summary, correlation matrix, causal graph, failure log, checksums.

---

## 8. Extensibility / Plugin System (growth engine)

A documented, stable extension API so the community can add capability without forking core. Plugin types:

| Plugin type | Adds |
|---|---|
| `Distribution` | new sampling distribution |
| `StructuralFn` | new causal/structural equation form |
| `FailureMode` | new corruption/injection transform |
| `Exporter` | new output format/adapter |
| `Template` | new domain dataset spec (data-only, no code) |
| `ProbeModel` | new difficulty-measuring baseline |

- Discovered via Python entry points (`pip install datadoom-plugin-xyz`) and/or a local plugins dir.
- Each plugin declares a schema fragment that the **web UI renders automatically** (so new plugins appear in the Canvas with no frontend changes).
- Determinism contract: plugins must use the injected seeded RNG; CI template enforces it.

---

## 9. Architecture (summary — full rationale in companion doc)

**Modular monolith**, Python-first, distribution added only when measured load demands it.

- **Backend/engine:** Python 3.11 + FastAPI; engine as importable modules (`rng`, `dist`, `causal`, `difficulty`, `failure`, `export`).
- **Jobs:** in-process worker pool by default; optional Redis-backed queue (Celery/RQ/Arq) for heavier/team setups.
- **Storage:** **SQLite + local filesystem by default** (zero-config); optional Postgres + S3-compatible for server/team mode.
- **Realtime:** WebSocket/SSE progress straight from the worker.
- **Frontend:** React + TypeScript + React Flow + Tailwind, bundled and served by the backend.
- **Contracts:** OpenAPI auto-generated from FastAPI/Pydantic.
- **Packaging:** PyPI wheel (`pip install datadoom`), `pipx`, Docker image, optional conda.

**Explicitly out of the core:** Kafka, gRPC, Go services, day-one Kubernetes, multi-region, multi-tenant RLS, billing, GPU GAN/VAE clusters. (May return later as *optional* editions/plugins, never as core requirements.)

---

## 10. Scope Boundaries

### In scope (v1)
Tabular + time-series; deterministic engine; distributions; causal DAG/SEM; failure injection; difficulty targeting; reports; export adapters; web Canvas; CLI launcher + headless run; Python API; plugin system; templates; local-first install.

### Deferred (post-v1, opt-in)
Graph/network data; richer time-series (multivariate, hierarchical); team/server mode (Postgres, accounts, sharing); hosted edition; advanced probe models.

### Out of scope (core)
GAN/VAE image synthesis; multi-modal image/text generation; SaaS billing & quotas; multi-region infra; "KS auto-correction" theater; any non-deterministic data-path code.

---

## 11. Success Metrics (OSS-appropriate)

DataDoom's success is **adoption and contribution**, not revenue:

- **Install & reach:** PyPI downloads/month; Docker pulls; GitHub stars.
- **Reproducibility integrity:** bitwise-reproduction failure rate **< 0.1%** on the pinned path (measured in CI across OSes).
- **Distribution compliance:** reported compliance score **> 95%** on built-in distributions.
- **Community health:** number of external contributors; number of community plugins/templates; time-to-first-response on issues/PRs.
- **Time-to-first-dataset:** from `pip install` to a generated dataset in **< 5 minutes** for a new user.
- **Citations / real-world use:** specs found in public repos and papers.

---

## 12. Roadmap (capability-ordered, solo/small-team + AI friendly)

| Phase | Deliverable |
|---|---|
| **P0 — Deterministic core** | Seeded RNG, distributions, compliance report, spec parser, CSV export, headless `datadoom run`. Bitwise-reproduction CI test. |
| **P1 — Web Canvas (MVP)** | Server + bundled React app; schema builder; results preview; `datadoom` launches browser. The product becomes demoable. |
| **P2 — Causal engine** | DAG builder (React Flow), SEM execution, cycle detection, interventions, true-graph ground-truth output. |
| **P3 — Failure injection** | MCAR/MAR/MNAR, noise, drift, leakage; live diff + clean-vs-injected comparison. |
| **P4 — Difficulty targeting** | Probe models, adaptive loop, validated tier→band mapping, evaluation report. |
| **P5 — Ecosystem** | Plugin API + docs, entry-point discovery, template library, export adapters (Parquet/PyTorch/TF/HF), `datadoom plugins`. |
| **P6 — Project maturity** | Docs site, contribution guide, governance, release automation, cross-OS reproducibility matrix; optional Redis/Postgres team mode. |

GANs/multi-region/Kafka/billing are **not scheduled** — they are explicitly out of the core.

---

## 13. Open-Source Project Foundations (must-haves for "huge")

Adoption is a product feature. v1 ships with:

- **License:** Apache-2.0 + clear CLA/DCO policy.
- **Docs:** quickstart (`< 5 min`), spec reference, plugin authoring guide, architecture overview, examples gallery.
- **Repo hygiene:** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates, good first issues, semver + changelog.
- **CI:** lint, type-check, tests, **determinism/reproducibility matrix across OS + Python versions**, plugin contract tests.
- **Trust signals:** reproducible-build proof, signed releases, security policy.
- **Governance:** maintainer model + roadmap transparency so contributors know the project is alive and welcoming.

---

## 14. Conclusion

DataDoom v2 is a **local-first, installable, open-source synthetic-data laboratory** whose primary surface is a web Canvas and whose center of gravity is a **reproducible, version-controllable spec file**. It wins not by out-scaling cloud SaaS competitors, but by being **trustworthy, extensible, and effortless to install** — letting anyone simulate a controllable reality, share it as a file, and reproduce it exactly. Its differentiation is sharpened to the four defensible axes — **reproducibility, causal structure, difficulty targeting, and failure injection** — and its open architecture turns those guarantees into community-verifiable, community-extensible truth.
