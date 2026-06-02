# 16 — Engineering Roadmap

> Capability-ordered phases for a small team + AI. Each phase ends with something **demoable and shippable**. Obeys `00_README_Index.md`. Build steps in `17`.

---

## 0. Principles

- **Vertical slices, not horizontal layers.** Each phase delivers an end-to-end path a user can run, not an isolated subsystem.
- **The deterministic core comes first** and everything builds on it.
- **The website appears early** (P1) because it's the point of contact — we don't build months of backend before anything is visible.
- **Plugins/extensibility are a phase**, not bolted on at the end.
- Phases are sized for clarity, not calendar precision; a solo dev + AI can move fast on the engine and UI.

---

## P0 — Deterministic Core (the foundation)
**Goal:** prove the headline guarantee with a headless path.

Deliverables:
- `engine.rng` seeded factory + key derivation (`05 §1`).
- `engine.spec` models, validation, canonicalization, `spec_hash` (`04`, `06 §1`).
- `engine.dist` built-in distributions + KS/compliance reporting (honest, no auto-correct).
- `engine.export` CSV + metadata + checksums.
- `engine.pipeline` minimal (intake→snapshot→seed→base→compliance→packaging).
- `datadoom run spec.yaml --seed N --out dir` and `datadoom verify`.
- `tests/determinism` + first golden specs + repro CI cell.

**Exit:** same spec+seed → identical checksum, proven in CI on ≥1 platform.

---

## P1 — Web Canvas MVP (becomes a product)
**Goal:** a user can build a simple tabular schema in the browser and generate/preview/export.

Deliverables:
- FastAPI app + bundled SPA scaffold; `datadoom` launches browser.
- REST: datasets CRUD, spec validate/estimate, run create, artifacts, preview (`08`).
- WebSocket live tracker (`08 §7`).
- Frontend: Dashboard, Canvas **Table view** + Inspector (numeric/categorical/boolean/datetime), Generation Tracker, Results (preview + distributions), Export.
- SQLite store + Alembic `0001_init` (`07`).
- In-process job worker (`03 §3.3`).

**Exit:** `pip install` (from source) → `datadoom` → create dataset → generate 50k rows → preview → export CSV. Time-to-first-dataset < 5 min.

---

## P2 — Causal Engine
**Goal:** the core differentiator — author causal structure.

Deliverables:
- `engine.causal`: DAG build (networkx), cycle detection, topo sort, SEM execution, built-in structural fns (linear/logistic/polynomial/map/identity).
- Interventions / counterfactual generation (`05 §3.1`).
- Frontend **Graph view** (React Flow): nodes/edges, edge creation, live cycle rejection, structural-fn editor, intervention toggle.
- Reports: correlation + MI matrices, **true causal graph** ground truth.
- Tests: SEM coefficient recovery, acyclicity, namespace independence.

**Exit:** define `age→income→is_fraud`, generate, and see the true graph + correlations in Results.

---

## P3 — Failure Injection
**Goal:** robustness testing with clean-vs-injected comparison.

Deliverables:
- `engine.failure`: MCAR/MAR/MNAR, label_noise, feature_noise, drift, covariate_shift, leakage.
- Clean baseline always preserved; injected variant produced.
- Frontend Failure Configurator (accordions, sliders), **live diff preview**, Comparison view.
- `POST /api/runs/{id}/inject`.
- Tests: rate accuracy, driver correlation, leakage MI, drift schedule.

**Exit:** inject 12% MNAR + 3% label noise; see the diff and comparison.

---

## P4 — Difficulty Targeting
**Goal:** "make it Kaggle-hard" actually works and is honest.

Deliverables:
- `engine.difficulty`: probe models (logreg/tree), adaptive loop, achieved-metric reporting.
- Tier→band mapping **validated** against real baselines (`05 §5.3`, `13 §4`).
- Frontend difficulty selector + evaluation report (target vs achieved + probe used).
- Tests: tier bands hold across sampled datasets.

**Exit:** request `kaggle`, get a dataset whose baseline AUROC lands in the documented band, reported transparently.

---

## P5 — Ecosystem (extensibility + templates)
**Goal:** the community can extend DataDoom; new users start fast.

Deliverables:
- Plugin registry + loader (entry points + local dir), ABCs in `datadoom.plugin` (`09`).
- Plugin contract tests + `datadoom plugin new/check`.
- UI auto-rendering of plugin `param_schema`.
- Export adapters: Parquet/JSON + pandas/PyTorch/TF/HF (`07`/`08`).
- Built-in template library + Templates gallery + `templates/use`.
- Time-series generator (`05 §6`).

**Exit:** `pip install datadoom-plugin-sample` → it shows up in the UI; a user starts from a fraud template in one click.

---

## P6 — Project Maturity (1.0 readiness)
**Goal:** trustworthy, documented, releasable; optional team mode.

Deliverables:
- Cross-OS × cross-Python **repro matrix** green; reproducibility badge (`13`).
- Docs site (quickstart, spec ref, plugin guide, architecture, examples).
- Governance/contrib files, release automation, signed releases, Docker image (`15`, `14`).
- Optional **team mode**: Postgres + S3 + Redis/RQ + auth + `owner_id` scoping (all opt-in).
- Accessibility pass; performance budgets enforced.

**Exit:** tag **1.0** — stable spec format + plugin API, green repro matrix, complete docs, fresh-install smoke test on all OSes.

---

## Post-1.0 (deferred, opt-in, mostly plugins)
- Graph/network datasets; richer/multivariate time-series.
- Advanced probes (XGBoost/LightGBM) as plugins.
- Reference-fitting from real samples (`05 §2.3`) UI.
- Hosted/team edition hardening.
- *(Out of core:* GAN/VAE image synthesis as an optional `datadoom-plugin-gan`, never a core dependency.)

---

## Release Mapping
- **0.1 (Alpha):** P0 + P1.
- **0.x (Beta):** P2 → P3 → P4 → P5.
- **1.0:** P6 complete.

---

## Cross-Phase Invariants (every phase must uphold)
1. Determinism guarantee never regresses (repro tests gate every merge).
2. `engine/` stays framework-free; layering holds (`10 §4`).
3. Honest statistics — no distribution auto-correction; report, don't fake.
4. Local-first, offline-capable; no telemetry.
5. New capability prefers a plugin over core bloat.
