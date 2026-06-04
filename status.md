# DataDoom — Implementation Status

> Single source of truth for **what is built**. The design lives in `docs_v2/`;
> this file tracks delivery against it. Update it whenever a task's status
> changes or a task is broken down into subtasks.
>
> **Last updated:** 2026-06-04 (Task 19 hardening complete — docs site, release
> automation/Docker, repro/perf/a11y; team mode deferred as a future addon)

## How to read this file

- Top-level tasks follow the build sequence in `docs_v2/17_Implementation_Guide.md`
  and the phases in `docs_v2/16_Engineering_Roadmap.md`.
- When a task needs breaking down, add subtasks under it (`5` → `5.1`, `5.2`, …)
  and log each one in the table.
- The **Master Log** is the at-a-glance table; the **Detail** sections below
  carry per-subtask rows and notes.

### Status legend

| Symbol | Meaning |
|---|---|
| ✅ | Done — implemented and verified (tests/gates green) |
| 🚧 | In progress |
| ⬜ | Not started |
| ⏸️ | Blocked / waiting |
| 🔄 | Needs rework (regressed or design changed) |

---

## Master Log

| ID | Task | Phase | Status | Updated |
|---|---|---|---|---|
| 0.1 | Initialize repo, layout, `pyproject.toml`, LICENSE, governance | P0 tooling | ✅ | 2026-06-01 |
| 0.2 | Quality gates: Ruff, mypy, import-linter, pytest, pre-commit, CI | P0 tooling | ✅ | 2026-06-01 |
| 1 | `engine/rng.py` — seeded RNG factory | P0 engine | ✅ | 2026-06-01 |
| 2 | `engine/spec/` — models, hashing, validation | P0 engine | ✅ | 2026-06-01 |
| 3 | `engine/dist/` — distributions + KS compliance | P0 engine | ✅ | 2026-06-01 |
| 4 | `engine/export/` — CSV + metadata + checksums | P0 engine | ✅ | 2026-06-01 |
| 5 | `engine/pipeline.py` + `RunContext` | P0 engine | ✅ | 2026-06-01 |
| 6 | `cli/main.py` + golden specs + repro CI | P0 engine | ✅ | 2026-06-01 |
| TH | P0 correctness-test hardening (gaps from test review) | P0 engine | ✅ | 2026-06-01 |
| 7 | `store/` — SQLAlchemy models, SQLite, Alembic | P1 | ✅ | 2026-06-01 |
| 8 | `jobs/worker.py` — in-process worker + progress | P1 | ✅ | 2026-06-01 |
| 9 | `api/` — FastAPI app, routes, WebSocket | P1 | ✅ | 2026-06-01 |
| 10 | `frontend/` — React Canvas MVP | P1 | ✅ | 2026-06-01 |
| 11 | `engine/causal/` — DAG/SEM + interventions | P2 | ✅ | 2026-06-02 |
| 12 | Frontend Graph view (React Flow) | P2 | ✅ | 2026-06-02 |
| 13 | `engine/failure/` — MCAR/MAR/MNAR, noise, drift… | P3 | ✅ | 2026-06-02 |
| 14 | Frontend Failure Configurator + Comparison | P3 | ✅ | 2026-06-02 |
| E1 | Realistic text providers (mimesis), seeded for determinism | Enhancement | ✅ | 2026-06-03 |
| E2 | Frontend Generation-Overview dashboard tab (from metadata) | Enhancement | ✅ | 2026-06-03 |
| E3 | Latent features (`emit: false`) — hidden confounders / latent scores | Enhancement | ✅ | 2026-06-03 |
| E4 | Web "Import from YAML" (paste/upload → validate → create) | Enhancement | ✅ | 2026-06-03 |
| 15 | `engine/difficulty/` — probes + adaptive loop | P4 | ✅ | 2026-06-03 |
| 16 | Frontend difficulty UI + evaluation report | P4 | ✅ | 2026-06-03 |
| 17 | `plugins/` — registry + loader + scaffolder + UI gallery | P5 | ✅ | 2026-06-03 |
| 18 | Exporters (Parquet/JSON) + templates + time-series + adapters | P5 | ✅ | 2026-06-03 |
| 18.5 | AI spec-authoring contract (capabilities manifest + LLM reference) | P5 | ✅ | 2026-06-03 |
| 18.6 | Hackathon mode — enterprise template pack + `level` catalog facet | P5 | ✅ | 2026-06-03 |
| E5 | Column Guide — per-column data profile + failure attribution + ML advice | Enhancement | ✅ | 2026-06-04 |
| E6 | Locked spec YAML per generation (tracked artifact + per-run download) | Enhancement | ✅ | 2026-06-04 |
| E7 | Audit report bound into the bundle + correct artifact naming in Export | Enhancement | ✅ | 2026-06-04 |
| 19 | Hardening: docs site, release automation, repro/perf/a11y (team mode deferred) | P6 | ✅ | 2026-06-04 |
| 19.1 | Docs site (mkdocs-material) + GitHub Pages workflow + operator runbook | P6 | ✅ | 2026-06-04 |
| 19.2 | Release automation (PyPI OIDC + provenance) + Docker image | P6 | ✅ | 2026-06-04 |
| 19.3 | Repro-matrix hardening + badges + perf budget + accessibility pass | P6 | ✅ | 2026-06-04 |

**P0 exit gate:** ✅ same spec+seed → identical checksum, proven via
`datadoom verify` and `tests/determinism` (see [testing_guide.md](testing_guide.md)).

**P1 exit gate:** ✅ `datadoom serve` boots the FastAPI app + bundled web Canvas;
in-browser **create → edit schema → generate (live WS tracker) → preview →
export** works end-to-end, and the same `(spec, seed)` reproduces identical CSV
bytes over the API. Automated coverage in `tests/api` + `tests/unit/test_store.py`;
manual walkthrough in [testing_guide.md](testing_guide.md) Groups **H** and **I**.

---

## Detail — Phase 0 (Done)

### 0.1 — Initialize ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 0.1.1 | Monorepo layout (`src/datadoom/...`, `tests/`, `examples/`, `.github/`) | ✅ | per `docs_v2/10` |
| 0.1.2 | `pyproject.toml` (hatchling, deps, `datadoom` entry point, dev extras) | ✅ | |
| 0.1.3 | `LICENSE` (Apache-2.0) | ✅ | |
| 0.1.4 | Governance: `CONTRIBUTING`, `CODE_OF_CONDUCT`, `SECURITY`, `GOVERNANCE`, `CHANGELOG`, PR template | ✅ | per `docs_v2/15` |
| 0.1.5 | `src/datadoom/version.py` + public API in `__init__.py` | ✅ | `Spec, generate, load_spec, parse_spec, validate_spec, __version__` |

### 0.2 — Quality gates ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 0.2.1 | Ruff config + clean | ✅ | `B008` ignored for Typer CLI only |
| 0.2.2 | mypy config (strict-ish on engine) | ✅ | clean whole-package run in `.venv` (22 files) |
| 0.2.3 | import-linter contracts (engine framework-free + layers) | ✅ | 2 contracts kept |
| 0.2.4 | pytest config | ✅ | |
| 0.2.5 | `.pre-commit-config.yaml` | ✅ | ruff + mypy + import-linter |
| 0.2.6 | CI `ci.yml` (lint→type→import-lint→test, win/mac/linux × 3.11/3.12) | ✅ | |
| 0.2.7 | `repro-matrix.yml` (bitwise determinism gate) | ✅ | `OMP_NUM_THREADS=1` |
| 0.2.8 | Gate: `test_version` passes | ✅ | |

### 1 — `engine/rng.py` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 1.1 | Key derivation `sha256(spec_hash:seed:ns)[:8]→uint64` | ✅ | `05 §1.2` |
| 1.2 | Per-namespace `Generator(PCG64(key))` + convenience builders | ✅ | feature/noise/failure/shuffle |
| 1.3 | Tests: identical draws, namespace independence, no perturbation | ✅ | `tests/unit/test_rng.py` (5) |

### 2 — `engine/spec/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 2.1 | Pydantic v2 models (`models.py`) | ✅ | discriminated feature union |
| 2.2 | Canonical JSON + `spec_hash` (`hashing.py`, seed excluded) | ✅ | `05 §1.1` |
| 2.3 | Cross-field validation (`validate.py`) with locators | ✅ | refs, acyclicity, derived-vs-sampled, splits, rates |
| 2.4 | `load_spec`/`parse_spec` (YAML/JSON) | ✅ | |
| 2.5 | Tests: parse, each invalid case w/ locator, hash excludes seed | ✅ | `tests/unit/test_hashing.py` (4), `test_spec_validate.py` (13) |

### 3 — `engine/dist/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 3.1 | `Distribution` ABC (`base.py`) | ✅ | `sample`/`cdf`/`validate` |
| 3.2 | Numeric builtins: normal, lognormal, poisson, pareto, uniform, exponential | ✅ | `REGISTRY` |
| 3.3 | Non-numeric samplers: categorical, boolean, datetime, text(lorem) | ✅ | |
| 3.4 | KS compliance, **no refit** (`compliance.py`) | ✅ | `05 §2.3` |
| 3.5 | Tests: empirical params, KS rejection ≈ α, wrong-params rejection | ✅ | `tests/unit/test_dist.py` (5) |

### 4 — `engine/export/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 4.1 | `Exporter` ABC + `ArtifactInfo` | ✅ | |
| 4.2 | Byte-stable CSV writer (forced `\n`, stable columns) | ✅ | `csv_exporter.py` |
| 4.3 | Reproducible `metadata.json` (no timestamps) | ✅ | `metadata.py` |
| 4.4 | SHA256 per file | ✅ | `checksums.py` |
| 4.5 | Tests: byte-stable CSV, stable checksum, LF newlines, column order | ✅ | `tests/unit/test_export.py` (3) |

### 5 — `engine/pipeline.py` + `RunContext` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 5.1 | `RunContext` + `ProgressEmitter` no-op sink | ✅ | |
| 5.2 | Stages: intake→snapshot→seed→base→compliance→packaging | ✅ | single `generate()` entry point |
| 5.3 | Base feature generation (sampling, clamp record, int cast) | ✅ | derived features guard until P2 causal |
| 5.4 | Packaging: write `data.csv` + `metadata.json` + resolved spec | ✅ | |
| 5.5 | Tests: clamp recorded, dtype, column order, determinism | ✅ | `tests/unit/test_pipeline.py` (5) |

### 6 — `cli/main.py` + golden + repro CI ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 6.1 | Typer app: `run`, `validate`, `verify`, `version` | ✅ | |
| 6.2 | Golden spec + pinned checksum (`tests/golden/`) | ✅ | keyed per numpy version |
| 6.3 | Determinism gate (`tests/determinism/`) | ✅ | 5 tests |
| 6.4 | Example spec (`examples/tabular-basic.datadoom.yaml`) | ✅ | |

### TH — P0 correctness-test hardening ✅

Gaps found while reviewing whether the suite catches *logical* (not just
structural) errors. These tests assert correct **behavior/arithmetic** that a
bug could previously pass CI on. Now implemented (+23 tests, suite 42 → 65). Test
specs live in `testing_guide.md` → "Group G".

| ID | Subtask | Status | Notes |
|---|---|---|---|
| TH.1 | Distribution statistical correctness | ✅ | `tests/unit/test_dist_correctness.py` |
| TH.1.1 | `lognormal` — moments/median match `θ` | ✅ | mean = `exp(mu+sigma²/2)`, median = `exp(mu)`, support > 0 |
| TH.1.2 | `poisson` — mean≈var≈`lam`, integer output | ✅ | |
| TH.1.3 | `pareto` — mean (α>2) + **support ≥ xm** | ✅ | guards `(pareto(α)+1)*xm` formula |
| TH.1.4 | `exponential` — mean≈scale, **support ≥ 0** | ✅ | |
| TH.1.5 | cdf↔sampler agreement: each dist **passes** KS on correct params | ✅ | continuous dists, multi-seed pass rate; poisson excluded (discrete) |
| TH.2 | Categorical weight fidelity (weighted props, uniform default, unnormalized→normalized) | ✅ | |
| TH.3 | Boolean `rate` fidelity (empirical P(true)≈rate) | ✅ | |
| TH.4 | Datetime bounds + granularity (within `[start,end]`, whole-unit, dtype) | ✅ | guards the `astype` refactor |
| TH.5 | Text length within `[min,max]` tokens | ✅ | |
| TH.6 | Hashing **discrimination** (param change → different hash; reordered `categories` → different hash) | ✅ | `tests/unit/test_hashing.py` (additions) |
| TH.7 | Valid multi-node DAG **accepted**; self-loop `a→a` rejected | ✅ | `tests/unit/test_spec_validate.py` (additions) |
| TH.8 | Metadata integrity (recorded checksum == file sha; `spec_hash`; resolved seed written) | ✅ | `tests/unit/test_metadata.py` (new) |

---

## Detail — Phase 1 (Done)

> Server stack (`store → jobs → api`) + the bundled web Canvas. New import-linter
> contract added: **store depends only on engine** (3 contracts total). Server
> deps live in the `[server]` extra (also pulled into `[dev]`). `config.py` adds
> layered config + `$DATADOOM_HOME`.

### 7 — `store/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 7.1 | ORM models mirroring 06/07 (`models.py`) | ✅ | datasets/specs/runs/artifacts/reports/plugins; soft `current_spec_id`/`latest_run_id` to break the cycle |
| 7.2 | SQLite engine + WAL/FK/synchronous pragmas (`db.py`) | ✅ | `Database` session scope; `:memory:` uses `create_all` |
| 7.3 | Repositories (`repositories.py`) | ✅ | Dataset/Spec/Run/Artifact/Report; spec immutability = new version + repoint |
| 7.4 | Local FS `ArtifactStore` (`artifacts.py`) | ✅ | `<artifacts>/<dataset>/<run>/…`; cascade dir removal |
| 7.5 | Alembic `0001_init` + auto-`upgrade head` on startup | ✅ | `migrations/env.py`, `versions/0001_init.py`; cascade FKs (incl. runs→specs) |
| 7.6 | Tests: CRUD, immutability, cascade, migration↔models | ✅ | `tests/unit/test_store.py` (5) |

### 8 — `jobs/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 8.1 | `EventHub` — per-run pub/sub + replay + cancel flags (`progress.py`) | ✅ | thread→loop marshaling via `call_soon_threadsafe`; late subscribers replay |
| 8.2 | `HubProgressEmitter` — engine stage events → WS shapes | ✅ | synthesizes per-stage `done`; raises `RunCancelled` at boundaries |
| 8.3 | `WorkerPool` — thread-pool runner (`worker.py`) | ✅ | loads snapshot, drives `engine.pipeline`, persists artifacts+report, flips status |

### 9 — `api/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 9.1 | App factory + lifespan + SPA mount (`app.py`) | ✅ | binds hub loop; serves `webdist/` with client-routing fallback |
| 9.2 | Deps (DB session, no-op auth) + error envelope (`deps.py`, `errors.py`) | ✅ | 422+`locator`, 409, 404, request-validation, 500 |
| 9.3 | Schemas + serializers (`schemas.py`, `serializers.py`) | ✅ | OpenAPI at `/api/openapi.json` (23 paths) |
| 9.4 | Routes: specs, datasets+versioning, runs, artifacts/preview/report/bundle, templates, plugins, meta | ✅ | idempotency replay; reproducible-checksum path |
| 9.5 | WebSocket hub endpoint + SSE fallback (`ws.py`) | ✅ | `/api/ws/runs/{id}`, `/api/runs/{id}/events`; accepts client `cancel` |
| 9.6 | Resource estimator (`estimate.py`, doc 12) | ✅ | runtime/RAM/size; no cost/GPU |
| 9.7 | CLI `datadoom serve` | ✅ | lazy-imports the server extra |
| 9.8 | Tests: routes, 422/409, idempotency, run lifecycle, WS | ✅ | `tests/api/test_api.py` (12) |

### 10 — `frontend/` (web Canvas MVP) ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 10.1 | Vite + React + TS + Tailwind + TanStack Query + Zustand scaffold | ✅ | builds into `src/datadoom/webdist/` (shipped in the wheel) |
| 10.2 | Editorial "Paper & Ink" design system + **theme toggling** | ✅ | light Paper default + dark Ink + System; `t` shortcut; persists; no-flash |
| 10.3 | Dashboard + Create Dataset modal | ✅ | cards, status badges, search, duplicate/delete |
| 10.4 | Canvas: schema table + contextual Inspector + autosave + spec drawer | ✅ | per-type controls; live preview histogram; Validate/Generate |
| 10.5 | Generation Tracker (live WS) + StageStepper + console | ✅ | streams stages→completed; cancel; reproducibility chips |
| 10.6 | Results (Preview / Distributions / Correlation / Evaluation) + Export | ✅ | honest KS chips; compliance pull-stat; determinism; bundle download |

> Deferred to later phases (design states already in place): Failure configurator
> (P3), Difficulty UI (P4), Templates/Plugins galleries (P5). The Graph view (P2)
> shipped in task **12**.

---

## Detail — Phase 2 (Causal engine — done)

> Engine (task **11**) + web Graph view (task **12**) delivered. The pipeline
> grows a `causal` stage (intake → snapshot → seed → base_generation → **causal**
> → compliance → packaging); only root features are sampled in `base_generation`,
> causal targets are computed by the SEM walk. New core dependency: **networkx**
> (DAG build + lexicographical topological sort); frontend adds **reactflow**.

### 11 — `engine/causal/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 11.1 | `graph.py` — networkx `CausalDag` (sorted nodes, lexicographical topo sort, defensive cycle reject) | ✅ | author-order in-edges per node for stable FP summation |
| 11.2 | `functions.py` — `StructuralFn` ABC + builtins (linear, logistic, polynomial, map, identity) | ✅ | per-fn `validate` (required params) |
| 11.3 | `execute.py` — SEM walk; per-node noise via `RNG(noise:v)`; boolean child = `Bernoulli(σ)` via `RNG(feature:v)`; `do(X=x₀)` interventions | ✅ | interventions fix the node + are honored by descendants in topo order |
| 11.4 | Pipeline `causal` stage (skip derived in base, compute in topo order) | ✅ | `_derived_features` skips targets in base_generation |
| 11.5 | Validation: structural-fn known + params, parent-type/fn compatibility, `map` covers all categories, numeric/boolean targets only, orphan derived-numeric rejected, noise dist known, intervention refs | ✅ | extends `spec/validate.py` |
| 11.6 | Reports: `causal_truth` (true graph + interventions + topo order) + `mutual_information` matrix (05 §7) | ✅ | persisted via new `reports.mutual_information` column (model + `0002_report_mutual_information` + repo + API schema/serializer) |
| 11.7 | KS-compliance applicability fix: continuous KS only counts for continuous/float/un-clamped features; integer/discrete/clamped → reported with moments but `applicable: False`, excluded from the score | ✅ | fixes false `compliance=0.0` on correct integer/clamped features; `engine/dist/compliance.py` + score over applicable only |
| 11.8 | Tests: coefficient recovery, cycle reject, intervention detach, map/poly/logistic, parent-type validation, KS applicability, determinism, true-graph/MI report | ✅ | `tests/unit/test_causal.py` (22) + compliance tests; +`examples/causal-fraud.datadoom.yaml` (age int + clamp, realistic) in the determinism gate |
| 11.9 | End-to-end dataset audits (generate → analyze realized frame) for **both** the non-causal `tabular-basic` and causal `causal-fraud` examples | ✅ | `tests/unit/test_dataset_audit.py` (13): per-feature moments/bounds/weights/rate/date-range/text-len + honest KS-applicability for the distribution-only set; SEM coefficient/calibration recovery for the causal set. Suite 82 → 123 |

### 12 — Frontend Graph view (React Flow) ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 12.1 | `reactflow` dep + typed causal graph/report shapes (`lib/types.ts`) | ✅ | `CausalGraph`/`CausalEdge`/`CausalTruth`/`MatrixReport`; `passed: boolean\|null` + `applicable`/`note` |
| 12.2 | `lib/causal.ts` — topo layering, client cycle detection, derived set, fn metadata, derived↔dist reconcile, interventions | ✅ | `reconcileDerived` strips `dist` from new targets / restores it when a node loses its last edge |
| 12.3 | `CausalGraphEditor` — React Flow nodes/edges, drag-to-connect, **live cycle-rejection toast**, topological auto-layout, intervention/derived badges | ✅ | inactive (intervened-target) edges dashed/faded |
| 12.4 | `CausalInspector` — structural-fn editor (linear/logistic/polynomial/map/identity + params), per-node noise, `do()` intervention toggle | ✅ | map shows a row per parent category; parent-type/fn mismatch flagged inline |
| 12.5 | Canvas **Table ⇄ Graph** view toggle + contextual right panel | ✅ | feature Inspector in Table; CausalInspector in Graph |
| 12.6 | Results: **Causal Graph** tab (read-only true DAG via `CausalGraphView`) + **Correlation & MI** heatmaps; honest KS-applicability (`n/a`) display | ✅ | edge labels show fn+weight; intervened edges dashed; compliance shows `N of M applicable` |
| 12.7 | Build into `src/datadoom/webdist/` (tsc strict clean) + end-to-end API smoke (SPA served; causal run → report carries `causal_truth`/`mutual_information`) | ✅ | 123 backend tests still green |

> **P2 exit gate:** ✅ author `age→income→is_fraud` (+`education→income`) — in the
> CLI/engine *and* in-browser via the Canvas **Graph** view — generate, and inspect
> the true graph + correlation/MI in Results. See `examples/causal-fraud.datadoom.yaml`,
> [testing_guide.md](testing_guide.md) Groups **J** (engine) and **L** (web Graph view).
> **Phase 2 complete.**

#### 11.10 — compliance for integer/discrete/clamped features (chi-square GoF) ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 11.10 | Real pass/fail for integer/discrete/clamped features via a chi-square goodness-of-fit against the **effective** PMF (replaces the prior `applicable: False` abstention) | ✅ | 2026-06-03 |

Previously, when a continuous KS test was not valid (integer `dtype`, a discrete
distribution like poisson, or `min`/`max` clamping that piles mass at the bounds)
the feature *abstained* — reported with its KS stat + moments but marked
`applicable: False` and excluded from the score (avoiding the prior bug that
scored a correct integer `age` at `0.0`). Now those features earn a **real
verdict** via a chi-square goodness-of-fit against the effective distribution:
binned counts vs the truncated-and-discretized PMF, where the boundary bins
absorb the (possibly clamped) tail mass — interior bin `k` → `F(k+½)−F(k−½)`, min
bin → `F(kmin+½)`, max bin → `1−F(kmax−½)` (for a discrete CDF the ±½ edges
coincide with the integer steps, so the same formula yields the exact PMF). A
continuous **clamped float** column is handled with point-mass boundary bins
(`P(min)=F(min)`, `P(max)=1−F(max)`) plus equal-width interior bins. Sparse bins
merge by Cochran's rule (`E ≥ 5`); `dof = bins − 1` (no params are fit — they
come from the spec, so the test stays honest). A feature only abstains now
(`test: "none"`) when no valid test can be formed (near-constant column).
`FeatureCompliance` gains `test` (`ks`/`chi2_gof`/`none`) and a `gof` detail
dict. **Determinism-safe:** compliance lives only in `metadata.json`; the golden
gate pins `data.csv`, which is unchanged. `engine/dist/compliance.py` + pipeline
wiring (clamp bounds) + frontend (`Results` "Fit p" column, GoF/χ² chips) + CLI
summary ("assessed" not "KS-assessed"). Tests: `tests/unit/test_dist.py`
(poisson/int/clamped earn a pass; wrong-λ GoF rejects; constant abstains),
`test_pipeline.py`, `test_dataset_audit.py` updated (age + visits now `chi2_gof`
passes; basic dataset scores 1.0). New author guide:
[docs_v2/20_YAML_Authoring_Guide.md](docs_v2/20_YAML_Authoring_Guide.md) §11.

## Detail — Phase 3 (Failure injection — engine done)

> Engine (task **13**) delivered. The pipeline grows a `failure_injection` stage
> (intake → snapshot → seed → base_generation → causal → **failure_injection** →
> compliance → packaging): the clean baseline is captured first, then the spec's
> ordered failures corrupt a *copy*, each drawing from `RNG(failure:i)`. Compliance
> is still assessed on the clean frame; the injected variant ships as
> `data.injected.csv` when `export.versions` includes `injected`. The
> persistence/API/report schema already carried a `failures` section (stubbed from
> P1), so it lights up with no migration. Frontend Failure Configurator (task 14)
> remains open.

### 13 — `engine/failure/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 13.1 | `base.py` — `FailureMode` ABC + helpers (stable `sigmoid`, NaN-robust `standardize`, **logistic intercept calibration** by bisection, rate/reference validators) | ✅ | calibration makes MAR/MNAR honor the *expected* rate while staying driver/value-dependent |
| 13.2 | `modes.py` — 8 builtins: `mcar`, `mar`, `mnar`, `label_noise`, `feature_noise`, `drift` (linear/step), `covariate_shift` (affine moment-match), `leakage` | ✅ | each mutates the injected copy + returns a diff summary; honest math, no refitting |
| 13.3 | `apply.py` + `__init__.py` — orchestrator (`apply_failures`) + `FAILURE_MODES` registry | ✅ | sequential, per-mode `RNG(failure:i)`; clean frame deep-copied first |
| 13.4 | Pipeline `failure_injection` stage + `RunResult.injected`; injected CSV artifact (versioned) + metadata `failures` | ✅ | `ArtifactInfo.version` (`clean`/`injected`); worker persists per-artifact version |
| 13.5 | `reports.py` — `failures` section (count + per-mode diffs); `validate.py` — dispatch to mode validators (unknown type rejected; per-mode field/type/reference checks) | ✅ | replaces the generic P1 stub with type-aware validation |
| 13.6 | NaN-preservation fix: int columns already nullified by a prior failure stay float under `feature_noise`/`drift`/`covariate_shift` (NaN can't cast to int64) | ✅ | `_assign_numeric` guard; missingness survives a later additive transform |
| 13.7 | Tests: rate accuracy, MAR/MNAR driver/value correlation, label-flip-to-different-class, feature-noise std, drift schedule, covariate moment-match, leakage MI/correlation, clean-baseline preserved + reproducible, injected determinism, 12 validation cases | ✅ | `tests/unit/test_failure.py` (26) + `data.injected.csv` byte-stability in the determinism gate; suite 123 → 151 |
| 13.8 | `examples/failure-fraud.datadoom.yaml` (causal-fraud DAG + 6 stacked failures; `versions: [clean, injected]`) in the determinism gate | ✅ | CLI `run`/`verify` green; both variants byte-stable |
| 13.9 | **Critical mathematical audit** — recover each mechanism's parameters from the realized data vs exact/asymptotic theory (the P3 analogue of `test_dataset_audit.py`) | ✅ | `tests/unit/test_failure_audit.py` (14): MAR/MNAR **IRLS logistic-slope recovery** + calibrated rate; categorical **uniform transition matrix** (off-diag = p/(k−1)); boolean symmetric flip + marginal `q(1−p)+(1−q)p`; feature-noise σ + **KS-Gaussian** + independence; drift exact ramp (max err ~1e-14); covariate_shift exact moments (1e-6); leakage **corr = 1/√(1+η²)** (1e-3); MCAR 3σ band + Welch-t independence. Suite 151 → 165 |

### 14 — Frontend Failure Configurator + Comparison ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 14.1 | Typed `Failure`/`FailuresReport`/`FailureDiff` shapes (`lib/types.ts`); `preview(version)` on the API client | ✅ | `target` is a union (moment spec for covariate_shift, column name for leakage) mirroring the engine's loose model |
| 14.2 | `lib/failures.ts` — mechanism metadata registry (label/category/blurb/math/accent), `defaultFailure`, `summarizeFailure`, **declarative impact estimates** (e.g. leakage corr = 1/√(1+η²)), client pre-flight validation, `reconcileFailures` on rename/delete | ✅ | impact is a consequence of the knobs, **not** a re-simulation — honest; authoritative effect comes from the run report |
| 14.3 | `FailureConfigurator` — Canvas **Failures** view: ordered pipeline of stage cards (reorder ↑/↓, delete, select, live impact chip, inline validation), grouped **Add failure** menu (Missingness/Noise/Shift/Leakage), clean-baseline guarantee banner, empty state, injected-export toggle | ✅ | third Segmented tab with a count badge; matches Table/Graph main+inspector layout |
| 14.4 | `FailureInspector` — per-step editor (aside): type-aware controls (column/driver selects, rate/strength/noise sliders, dist+params, drift schedule, target moments, multi-column chips), **live impact card** + the honest math | ✅ | mirrors the column Inspector pattern |
| 14.5 | Canvas wiring: `failures` view + selection, reconcile failures on column rename/delete, auto-enable `export.versions: [clean, injected]` on first failure | ✅ | `pages/Canvas.tsx` |
| 14.6 | `ComparisonView` + Results **Comparison** tab (shown when the run has failures): summary pull-stats, **per-mode realized-effect cards** (authoritative engine diffs with bars/gauges/sparklines), clean-vs-injected **distribution overlays**, and a **cell-level diff table** (nullified ∅ / changed / planted-column highlights, "changed rows only" filter) | ✅ | fetches the injected preview via `preview(version="injected")` |
| 14.7 | New `--warning-tint`/`--info-tint` tokens; build into `src/datadoom/webdist/` (tsc strict clean); end-to-end API contract verified (run → `report.failures` realized stats; `clean`+`injected` artifacts; injected preview carries the planted column + nulls; SPA serves) | ✅ | mnar realized 0.233, leakage corr 0.999 over HTTP |
| 14.8 | **UX fixes (round 2):** stale-cache lost-updates (sync `["dataset",id]` on save + unmount flush + re-arm loader on id change), visible autosave errors (was stuck on "saving…"), Menu scroll no longer self-closes, single-line Add-failure button/menu, generate **with/without failures** (strip-and-restore snapshot — clean run, config preserved), Comparison **"changed rows only"** excludes the planted column (+count), failure badges surfaced on **Table columns & Graph nodes** | ✅ | verified: without-failures → `report.failures: None` + clean-only artifact + spec restored |
| 14.9 | **Full settings visibility + faithful Results graph:** edge params expand to one row each (`edgeParamRows`: weight/bias, every coeff, every map entry) — no ellipsis — in Table/Graph/Results; the Results **Causal Graph** now loads the editor's saved `graph-nodes` layout (exact positions + node sizes) and mirrors the editor node, so it renders the graph the user actually built | ✅ | `CausalGraphView` reuses per-dataset layout; `fitView` preserves spacing |

> **P3 exit gate:** ✅ author failures (MNAR + label noise + leakage …) in the
> Canvas **Failures** view, generate, and inspect the realized diffs + clean-vs-
> injected comparison in Results — the clean variant remains available. See
> `examples/failure-fraud.datadoom.yaml`, [testing_guide.md](testing_guide.md)
> Groups **M** (engine) and **N** (web). **Phase 3 complete.**

## Detail — Phase 4 (Difficulty targeting — done)

> Engine (task **15**) + web difficulty UI (task **16**) delivered. The pipeline
> grows a `difficulty` stage (… → causal → **difficulty** → failure_injection →
> compliance → packaging): difficulty calibrates the *clean* frame to a target
> baseline-AUROC band, then failures corrupt a copy and compliance is assessed on
> the calibrated data. New core dependency: **scikit-learn** (the baseline probe
> models) — pinned to a minor line like numpy/mimesis because the probe metric
> drives the adaptive loop's knob selection and so sits on the
> determinism-critical path. The `reports.difficulty` JSON column already existed
> from `0001_init`, so the report lights up with **no migration**.

### 15 — `engine/difficulty/` ✅

> **Knob design (decided with the user):** the *lean default* — a single
> bisectable "difficulty dial" composed of **feature-observation noise** (primary;
> blurs numeric predictors, leaving the authored causal graph intact → honest
> `causal_truth`) then **label flips** (deep-end, engaged when feature noise
> saturates). The draws are taken once and *scaled* by the dial, so μ(d) is
> monotone (nested flips, proportional blur) and the bisection is well-posed.
> `causal` shrink / `imbalance` are recognized but **not** active in v0.1 (rejected
> by validation with a clear message — no silently-ignored config); see backlog.

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 15.1 | `probes.py` — `ProbeModel` ABC + `logreg`/`tree` (scikit-learn), seeded design matrix (numeric/bool/one-hot/datetime), binary-AUROC metric + reference (linear separability, class balance) | ✅ | degenerate cases (no features / one class) score at chance 0.5, no crash |
| 15.2 | `knobs.py` — `DifficultyDial`: pre-draws perturbations once, realizes any dial cheaply; feature noise `N(0,(η·sd)²)` (int dtype preserved via round) + nested label flips | ✅ | `noise_to_signal = η²` (05 §5.4) |
| 15.3 | `calibrate.py` — adaptive bisection on the dial; tier→band map (05 §5.3); bracket + honest-miss fallback (already-harder / too-strong / out-of-iters) with closest-shipped + note | ✅ | `DifficultyResult` (achieved, iters, dial, η, ρ, knobs, reference, trace, note) |
| 15.4 | Pipeline `difficulty` stage (calibrate clean frame before failures/compliance); `RunResult.difficulty`; `build_report(difficulty=…)` → `reports.difficulty` (no migration) | ✅ | calibrated frame is the shipped clean baseline |
| 15.5 | `validate.py` — binary-classification label only (boolean / 2-class categorical), known probe, tier-or-band target, knobs ⊆ {noise, label_noise} | ✅ | default spec knobs updated `["noise","label_noise"]` |
| 15.6 | Tests: probe high/chance/constant, tier mapping, **dial monotonicity** + nested flips, band-hit (intermediate/advanced/kaggle), honest-miss, determinism, validation | ✅ | `tests/unit/test_difficulty.py` (18) |
| 15.7 | **Audit** (P4 analogue of dataset/failure audits): independent probe reproduces the reported AUROC; feature-noise `Var=σ²(1+η²)`; every tier lands a fresh baseline in band (05 §5.3 / 13 §4); harder tier ⇒ more noise | ✅ | `tests/unit/test_difficulty_audit.py` (8) |
| 15.8 | `examples/difficulty-credit.datadoom.yaml` (strong credit-default label calibrated to `advanced`) in the determinism gate; CLI `run`/`verify` byte-stable | ✅ | API round-trip test (run → `report.difficulty`) in `tests/api` |
| 15.9 | scikit-learn pinned core dep + mypy/import-linter clean (engine stays framework-free); **Phase-3 audit** refactored hand-rolled IRLS → scikit-learn `LogisticRegression(C=inf)` now the dep exists | ✅ | suite 165 → 225 |

### 16 — Frontend difficulty UI + evaluation report ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 16.1 | Typed `Difficulty` config + `DifficultyReport` shapes (`lib/types.ts`); `lib/difficulty.ts` (tier metadata/bands, probes, knob meta, labelable-column + default + client validation helpers) | ✅ | mirrors engine tiers/validation |
| 16.2 | Canvas **Difficulty** view (`DifficultyConfigurator`): enable/disable, tier cards + custom band, AUROC band meter preview, label/probe selects, knob toggles, max-iters, honest explainer + client validation | ✅ | 4th Segmented tab with an enabled dot; contextual aside |
| 16.3 | Canvas wiring: `difficulty` view + `setDifficulty` (history/autosave), floating-hash hidden | ✅ | `pages/Canvas.tsx` |
| 16.4 | Results **Difficulty** tab (`DifficultyView`, shown when the run has a target): achieved-vs-target headline + band/met badge, reusable `BandMeter` (0.5–1.0 AUROC, tier bands + marker), how-it-got-there stats (dial/η/ρ/noise-to-signal/separability/balance), active knobs, **bisection trace** table, honest-miss note | ✅ | Evaluation tab's stale "Phase 4" placeholder replaced with the achieved summary |
| 16.5 | Build into `src/datadoom/webdist/` (tsc strict clean + vite) | ✅ | end-to-end API contract verified over the TestClient |

> **P4 exit gate:** ✅ set `target: kaggle` (or any tier) on a binary label — in the
> engine/CLI *and* in-browser via the Canvas **Difficulty** view — generate, and a
> baseline probe lands in the band, reported honestly (achieved metric + iterations
> + knobs + trace, misses flagged). See `examples/difficulty-credit.datadoom.yaml`,
> [testing_guide.md](testing_guide.md) Groups **P** (engine) and **Q** (web).
> **Phase 4 complete.**

#### Backlog — `causal` shrink + `imbalance` difficulty knobs (deferred)

The lean default ships two active knobs (feature noise + label flips). Two more
were scoped and deliberately deferred (validation rejects them today rather than
accept dead config): **`causal` shrink** (scale the label's incoming edge weights
toward 0 — the purest intrinsic-difficulty lever, but it rewrites the generative
graph so `causal_truth` would report shrunk weights; needs an honest-reporting
story + SEM re-execution per dial step) and **`imbalance`** (shift the label's
class balance as a difficulty/secondary lever). Both compose onto the same dial as
extra leading/secondary regions; deferred as orthogonal to the P4 gate.

## Detail — Phase 5 (Ecosystem — in progress)

> The plugin system (task **17**) is delivered: a plugin is a small class
> implementing one of the engine ABCs (re-exported as `datadoom.plugin`),
> discovered at startup and **inserted into the engine's own lookup tables** so it
> works in the CLI, the API, and the web UI with no core change. The engine never
> imports `plugins/`; the dependency points the other way (`engine ← plugins`),
> enforced by a new 4th import-linter contract. Tasks 18–19 (exporters/templates/
> time-series, then 1.0 hardening) remain.

### 17 — `plugins/` ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 17.1 | `contracts.py` — re-export the 5 ABCs as `datadoom.plugin` + `schema()` helper + `PLUGIN_BASES`/`KEY_ATTR` (exporter keys on `format`, others on `name`) | ✅ | also a thin `datadoom/plugin.py` public shim |
| 17.2 | `registry.py` — `PluginRegistry`/`PluginRecord`: kind detection (isinstance/issubclass), conflict-fail, `param_schema` validation; registers **into the live engine dicts** (`REGISTRY`/`STRUCTURAL_FNS`/`FAILURE_MODES`/`EXPORTERS`/`PROBES`) so the pipeline picks plugins up by name; `reset()` test aid | ✅ | built-ins seeded from the engine dicts (source `builtin`); mutating in place propagates to every `from … import REGISTRY` reference |
| 17.3 | `loader.py` — `load_plugins()`: seed built-ins → entry points (`datadoom.plugins` group) → local dir (`$DATADOOM_HOME/plugins/*.py`); broken/duplicate plugins fail loudly | ✅ | reads `$DATADOOM_HOME` from env directly (no `config` import → plugins stays engine-only) |
| 17.4 | `scaffold.py` — `scaffold_plugin(kind,name,dir)` writes a `datadoom-plugin-*` package (entry point, working stub per kind, contract test, README); `check_object`/`check_plugin` run the contract checks (interface, schema, determinism, **RNG-hygiene static scan** that tokenizes out comments/strings) | ✅ | scaffold → `datadoom plugin check` is green for all 5 kinds |
| 17.5 | Engine ABCs gain an additive `param_schema` class attr (default `None`) so plugins declare a UI schema; built-ins leave it `None` (native controls) | ✅ | `dist`/`causal`/`failure`/`export`/`difficulty` base classes |
| 17.6 | API: `GET /api/plugins` returns the live registry; `create_app` loads plugins at startup; `PluginInfo` gains `source`/`builtin` | ✅ | 24 core capabilities over HTTP (6 dist / 5 fn / 8 failure / 3 exporter / 2 probe) |
| 17.7 | CLI: `datadoom plugin list/new/check`; `run`/`validate`/`verify` load plugins first (headless parity) | ✅ | |
| 17.8 | Frontend: real **Plugins** gallery (replaces the placeholder) — grouped by kind, source badges, version/schema; `lib/schemaForm.tsx` renders a `param_schema` fragment into controls (09 §6) | ✅ | `api.listPlugins`, `PluginInfo` types; built into `webdist/` (tsc strict + vite) |
| 17.9 | 4th import-linter contract "plugins depend only on engine" + engine forbidden of `datadoom.plugins`; `tests/plugin_contract/` (16): built-ins register/pass, plugin flows through a run, local-dir + entry-point discovery, conflict-fail, schema/determinism/RNG-hygiene rejection, scaffold→check | ✅ | suite 235 → 251; ruff/mypy/import-linter green |

> **P5 gate (partial):** ✅ install/declare a plugin (entry point or local `.py`) →
> it appears in `datadoom plugin list`, in `GET /api/plugins`, in the web **Plugins**
> gallery, and is usable in a run by name — with zero engine change. See
> [testing_guide.md](testing_guide.md) Group **S**.

### 18 — Exporters + Templates + Time-series + Adapters ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 18.1 | **Exporters (JSON + Parquet)** — `json_exporter.py` (byte-stable records array; numpy/NaN/Timestamp normalized) + `parquet_exporter.py` (lazy `pyarrow`, fixed write opts); `EXPORTERS` registry; pipeline writes every `export.formats` × version; `validate.py` rejects unknown formats; preview falls back csv→json→parquet; `Exporter.extension`/`ext` | ✅ | pyarrow is the optional `[parquet]` extra (errors with an install hint if absent); JSON byte-stable + parquet same-env stable; frontend Generate modal gains an output-formats checklist (CSV locked); `tests/unit/test_export_formats.py` (6) |
| 18.2 | **Templates** — `src/datadoom/templates/` (loader + typed `CATALOG`, `importlib.resources`) + **8 domain starters** across 8 domains (finance/saas/healthcare/e-commerce/iot/people/marketing/insurance) spanning causal, failures, difficulty, latent, plus quick distribution-only and realistic-text (mimesis) tables; `GET /api/templates` + `/{id}` (full spec); CLI `datadoom template list/show/use`; web **Templates** gallery — a flat responsive grid (one-click → create dataset → Canvas) | ✅ | every template parses+validates+generates (parametrized test-gated over the whole catalog); `tests/unit/test_templates.py` + `tests/api` (3) |
| 18.3 | **Time-series** — `engine/timeseries.py` (additive `T(t)+S(t)+AR(p)+εₜ`, 05 §6) + `TimeseriesFeature` spec surface + validation (AR stationarity Σ\|φ\|<1, period>0, min/max) + determinism | ✅ | row order is the time axis; root feature, may be a causal parent, never a target, not compliance-assessed; εₜ via `RNG(noise:<name>)`; `examples/timeseries-sensor.datadoom.yaml` in the determinism gate; `tests/unit/test_timeseries.py` (12). Frontend: `timeseries` feature type + Inspector editor (trend/seasonality list/AR/noise/clamp/dtype) + summary/colors |
| 18.4 | **Framework adapters** — `src/datadoom/adapters/`: `load_dataframe` (pandas, core; auto-detects csv/parquet/json + clean/injected), `to_torch_dataset`/`to_tf_dataset`/`to_hf_dataset` (lazy-imported, optional `[torch]`/`[tf]`/`[hf]` extras with install hints) | ✅ | 5th import-linter contract "adapters depend only on engine"; engine forbidden of `datadoom.adapters`; `tests/unit/test_adapters.py` (pandas paths + importorskip for torch/hf + missing-backend hint) |
| 18.5 | **AI spec-authoring contract** — `engine/reference.py` `build_capabilities()` (machine-readable manifest of every distribution/fn/failure/tier/feature-type/exporter/provider + rules, built from the **live registries** so plugins appear) + `datadoom spec-reference` CLI + `GET /api/spec-reference` + LLM reference doc | ✅ | `docs_v2/21_LLM_Spec_Authoring_Reference.md` (validated few-shots) + beginner `docs_v2/20_YAML_Authoring_Guide.md`; `tests/unit/test_reference.py` + `tests/api` |

> **P5 gate (full):** ✅ templates + Parquet/JSON exporters + time-series + framework
> adapters + the AI-authoring manifest all ship. Start from a template, author any
> feature type (incl. `timeseries`) in the Canvas or by YAML, export CSV/JSON/Parquet,
> load a run into pandas/torch/tf/HF, and fetch the capabilities manifest for tooling.
> See [testing_guide.md](testing_guide.md) Groups **T**/**U**. **Phase 5 complete.**

#### 18.6 — Hackathon mode (enterprise template pack + level facet) ✅

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 18.6 | A curated **hackathon** template pack — enterprise-grade ML challenges built by *composition* (no new engine features), plus a `level` catalog facet to surface them | ✅ | 2026-06-03 |

"Hackathon mode" is delivered as a **data-only, additive** layer on the existing
templates system (task 18.2) — no engine/spec change, honoring the locked
invariants and "prefer data over a core special-case". Four flagship challenges,
one per domain, each composing a **deep multi-hop causal DAG**, a **latent
confounder** (`emit: false`), **mixed feature types**, a **stacked data-quality
failure profile**, and (where it fits) a **calibrated difficulty band** — i.e. a
realistic dataset you actually build a model on:

- **`credit-default-challenge`** (Finance) — demographics+employment → income →
  latent `risk_score` → `defaulted`; calibrated to `advanced` (probe AUROC ≈
  0.77, ~33% default); MNAR income + MAR/drifting debt-to-income + leaked
  `collections_flag` + label noise; 80/20 split.
- **`clinical-deterioration`** (Healthcare) — a **hidden confounder**: latent
  `severity` drives *both* the observed vitals (HR/lactate/BP) and the outcome,
  so vitals are confounded proxies; calibrated to `advanced` (AUROC ≈ 0.73, ~33%
  positive); MNAR/MAR/MCAR clinical missingness.
- **`predictive-maintenance`** (Industrial IoT) — three additive **time-series**
  sensor streams + load + grade → latent `wear_index` → `needs_maintenance`
  (~29%); the load regime **drifts** + gains noise + MCAR, plus a leaked
  `maintenance_alarm`; row-order is the time axis (no shuffling).
- **`telecom-churn-challenge`** (Telecom) — **realistic-text** identity fields
  (mimesis name/email/city) beside the real signal → latent `dissatisfaction` →
  `churned`; calibrated to the hard `kaggle` band (AUROC ≈ 0.64, ~26% churn);
  MNAR usage + noisy labels; the identifiers are a drop-the-PII trap.

Each template carries a `meta.challenge` brief (title / task / target / metric /
difficulty band / train-test split / hidden-structure + gotchas) — free-form
`meta`, ignored by the engine. **Surfacing:** `TemplateMeta`/`TemplateSummary`
gain a `level` field (`"starter"` | `"hackathon"`); `datadoom template list`
gains a `--level` filter and a `[hackathon]` tag; the web **Templates** gallery
leads with the flagships, adds a Trophy badge + an All/Hackathon/Starter filter.
All four parse/validate/`run`/`verify` byte-stable and are covered by the
existing parametrized `tests/unit/test_templates.py` (whole-catalog gate);
ruff/mypy/import-linter green; full suite 297 green; frontend tsc+vite clean.

## Detail — Phase 5+ (remaining)

**Phase 5 is complete** (tasks 17 + 18, including time-series, framework adapters,
and the AI spec-authoring contract). **Task 19** (1.0 hardening) is **complete**
across its three in-scope deliverables (team mode is **deferred** as a future
addon — see `docs_v2/22` §6):

| ID | Subtask | Status | Notes |
|---|---|---|---|
| 19.1 | **Docs site** — `mkdocs.yml` (material theme) + curated `docs_site/` pages that *embed* the authoritative `docs_v2/` sources via the include-markdown plugin (single source of truth); `docs` extra in `pyproject.toml`; `.github/workflows/docs.yml` (`mkdocs build --strict` on PR, `gh-deploy` on main); operator runbook `docs_v2/22` (Pages/PyPI/Docker/release/provenance steps the maintainer runs) | ✅ | `mkdocs build --strict` green locally; site = index/authoring/llm-reference/spec-reference/plugins/architecture/examples; doc index (00) extended to 20–22 |
| 19.2 | **Release automation + Docker** — `release.yml` (build frontend → wheel/sdist → clean-venv smoke → keyless Sigstore provenance → GitHub Release → PyPI via OIDC trusted publishing → GHCR image) + multi-stage `Dockerfile`/`.dockerignore` (Node stage builds the Canvas, slim Python runtime, non-root, `/data` volume) + non-gating docker build/smoke job in `ci.yml` + CHANGELOG brought current through Phase 5/hardening | ✅ | **Fixed a packaging bug:** the wheel was shipping **without** `webdist` — `python -m build` builds wheel-from-sdist and the sdist dropped the gitignored Canvas, so the `artifacts` glob (wheel-only) had nothing to include. Moved it to `[tool.hatch.build]` so sdist+wheel both force-include it; verified `webdist/index.html` + 17 assets now in both, fresh-venv wheel smoke green (version + deterministic run + Canvas bundled), `twine check` PASSED. Docker image build deferred to CI (local daemon not running); operator steps in `docs_v2/22` §2–4 |
| 19.3 | **Repro/perf/a11y** — pinned numpy in the repro-matrix CI cells so the golden gate **asserts** (not skips); **platform-keyed** golden checksum (per doc 13: bitwise within an OS/arch, statistical across) with CI emitting each cell's value to record; CI/repro/docs/license badges + README status refresh; perf-budget smoke (marked, non-gating) + CI job; frontend accessibility pass | ✅ | golden checksum re-keyed `numpy-2.4.6` → `Windows-AMD64-numpy-2.4.6`; determinism gate still green |

> **Team mode** (Postgres/S3/Redis + auth + `owner_id`) is intentionally **out of
> the 1.0 hardening scope** and parked as a future addon (`docs_v2/22` §6,
> `docs_v2/16` P6/Post-1.0).

---

## Change history

| Date | Change |
|---|---|
| 2026-06-04 | Delivered **19.3 — repro/perf/accessibility**, completing **task 19** (1.0 hardening; team mode stays deferred). **Repro matrix:** `repro-matrix.yml` now installs a **pinned numpy** (`==2.4.6`, the version the golden checksum was recorded against) so the golden gate **asserts** instead of skipping on version drift, and each cell prints its `platform-numpy` checksum to the job summary for one-time recording. Re-keyed the golden checksum **per platform** (`numpy-2.4.6` → `Windows-AMD64-numpy-2.4.6`) and updated `test_golden_checksum_pinned` accordingly — this matches doc 13's honest scope (**bitwise** within an OS/arch, **statistical** across) instead of a single key that wrongly implied cross-platform byte-identity; unrecorded platforms skip with a copy-pasteable instruction. **Badges + README:** added CI / Reproducibility-Matrix / Docs / Python / License badges and rewrote the stale "Phase 0 in progress" status (now Phases 0–5 + hardening), fixed the nonexistent `iris_like` example and the `verify` usage, and added install/serve/docs. **Perf budget:** new `tests/perf/test_perf_budget.py` (50k-row causal generate under a generous wall-clock + throughput floor), registered the `perf` marker and **deselected it by default** (`addopts = -m 'not perf'`) so it's non-flaky; a non-gating `perf` job + a non-gating `docker` job added to `ci.yml`. **Accessibility:** `Modal` gains a real **focus trap** + focus restore + `role="dialog"`/`aria-modal`/`aria-labelledby` (respecting child `autoFocus`); `Toaster` is now an `aria-live` region (`alert` for errors) with a labelled dismiss; `Layout` gains a **skip-to-content** link, labelled landmarks (Primary/Breadcrumb/Sidebar), a focusable `<main>`, and an `aria-label`/`aria-expanded` collapse toggle; two unlabelled icon-only menu triggers (Dashboard, GenerationsPanel) got `aria-label`s. Frontend rebuilt into `webdist` (tsc strict + vite clean). Full gate green: ruff, mypy (89 files), import-linter 5/5, **pytest 322 passed / 2 skipped / 1 deselected**; determinism gate still green; `pytest -m perf` passes. testing_guide.md gains Group **Z**. |
| 2026-06-04 | Delivered **19.2 — release automation + Docker**. New `.github/workflows/release.yml` (tag-driven, tokenless): build the web Canvas (Node) → `python -m build` sdist+wheel → `twine check` → smoke the wheel in a clean venv (`datadoom version` + a deterministic run + assert the Canvas is bundled) → **keyless Sigstore build-provenance** (`actions/attest-build-provenance`, OIDC) → GitHub Release → **PyPI via OIDC trusted publishing** (no token, `pypi` environment) → **GHCR** image (`docker/metadata`+`build-push`). New multi-stage `Dockerfile` (`node:20-slim` builds `webdist` → `python:3.11-slim` runtime, non-root `datadoom` user, `/data` volume, binds `0.0.0.0:8000`) + `.dockerignore`; a **non-gating** docker build+smoke job added to `ci.yml`. `CHANGELOG.md` `[Unreleased]` brought current (Phases 1–5 + enhancements + hardening). **Caught and fixed a real packaging bug:** the wheel shipped without `webdist` because `python -m build` builds the wheel *from the sdist* and the sdist dropped the gitignored Canvas (the `artifacts` glob was wheel-target-only); moved `artifacts` to `[tool.hatch.build]` so both sdist and wheel force-include `webdist/**` + `templates/*.yaml`. Verified: `webdist/index.html` + 17 assets present in both sdist & wheel, fresh-venv wheel install smoke green, `twine check` PASSED. (Docker image not built locally — daemon not running; CI covers it.) Suite still **322 passed / 2 skipped**; ruff/mypy/import-linter green. testing_guide.md gains Group **Y**. |
| 2026-06-04 | Started **task 19 (1.0 hardening)**, broken into 19.1/19.2/19.3; **team mode deferred** as a future addon. Delivered **19.1 — docs site**: a `mkdocs-material` site (`mkdocs.yml`, `docs_dir: docs_site`) whose pages *embed* the authoritative `docs_v2/` sources via the `mkdocs-include-markdown-plugin` (zero duplication — design docs stay the single source of truth). New `docs` optional-dependency group; curated pages (home/quickstart, YAML authoring [embeds doc 20], LLM/agent reference [embeds doc 21], spec reference, plugins, architecture, examples gallery). New `.github/workflows/docs.yml` builds with `mkdocs build --strict` on PRs and `gh-deploy`s to GitHub Pages on `main`. New operator runbook **`docs_v2/22_Release_and_Publishing_Runbook.md`** documents the maintainer-only steps (Pages enablement, PyPI Trusted Publishing via OIDC, GHCR/Docker, keyless Sigstore provenance, badges) — explicitly parking team mode as a future addon. Doc index (`docs_v2/00`) extended to list 20–22; `site/` gitignored. Made the embedded pages **fully strict-clean** (zero warnings): a GitHub-compatible `toc` slugify in `mkdocs.yml` so docs_v2 anchors resolve, one absolute-link fix in doc 21, and a corrected `#13` TOC anchor in doc 20 (the single-dash form was inconsistent with its `#4` sibling and was already broken on GitHub). `mkdocs build --strict` exits 0 locally with no anchor warnings; engine/tests untouched (docs-only). testing_guide.md gains Group **X**. |
| 2026-06-04 | **Audit report TOC + breadcrumb/error-boundary fix.** (1) `audit_report.md` now opens with a clickable **table of contents** (`engine/audit.py`): a `## Contents` list links to every section and nests per-column entries under the column guide (with issue counts), via GitHub-style heading slugs (`_slug`); the run metadata moved under a linkable `## Overview`. New `test_audit_report_has_navigable_toc` asserts every TOC anchor resolves to a heading. (2) Fixed the stuck **error-boundary**: `ErrorBoundary` took a render error and never cleared it on navigation, so clicking a breadcrumb left the "Reset view" fallback on screen. It now accepts a `resetKey` (the route pathname, passed from `Layout` via `useLocation`) and clears the error in `componentDidUpdate` when the route changes — navigating away recovers the view automatically. Suite **322** green, ruff/mypy clean, frontend tsc+vite rebuilt into `webdist`. |
| 2026-06-04 | Implemented **E7 — Audit report in the bundle + correct Export naming**. New pure/deterministic `engine/audit.py` renders the full `ReportBundle` (compliance, the **column guide** with per-column stats + data-quality issues + ML advice, injected failures, causal truth, difficulty, determinism checksums) to a timestamp-free `audit_report.md`. The pipeline writes it after `build_report` and registers it as a tracked artifact (`version: "audit"`, `format: "md"`), kept out of the metadata checksum map; it's automatically in the bundle zip and downloadable individually. So the new results now ship **alongside** data/metadata/spec. Also fixed Export naming: the API `Artifact` now carries the authoritative `filename` (basename of the storage URI) so the UI no longer guesses — the **injected** data file shows as `data.injected.csv` (not a second `data.csv`), with clean/injected/spec/audit badges + descriptions, and the audit report leads. Rebuilt `webdist`. Subset-based artifact assertions kept it safe; new `tests/unit/test_audit.py` (4 tests); suite **321** green, ruff/mypy/import-linter clean, frontend tsc+vite clean. testing_guide.md Group F updated. |
| 2026-06-04 | Implemented **E6 — Locked spec YAML per generation** (version-control reproducibility): the resolved spec (canonical body + baked-in seed), already written to `spec.resolved.yaml` on every run, is now a **tracked, checksummed artifact** (`version: "spec"`, `format: "yaml"`) — appended in `pipeline._package` and kept **out of** the metadata determinism checksum map so `metadata.json` stays byte-identical (golden tests unaffected). New API `GET /api/runs/{id}/spec.yaml` serves it as a download; `RunSummary` now carries `spec_hash` (via a read-only `GenerationRunRow.spec` relationship → serializer), the version-control anchor. Frontend: generation cards show a **🔒 spec `<hash12>`** chip and a **Spec YAML** download button; the ExportModal labels the artifact `spec.resolved.yaml` with a "locked spec" badge (and now names injected variants correctly). All artifact-list assertions used subset checks, so registering the new artifact is safe (CSV stays index 0 for determinism tests). New `test_resolved_spec_is_locked_and_downloadable`; suite **317** green, ruff/mypy/import-linter clean, frontend tsc clean. testing_guide.md gains a Group-H entry. |
| 2026-06-04 | Implemented **E5 — Column Guide** ("data exploration made simple"): a per-column report card that turns the engine's ground truth into actionable EDA. New pure-engine `engine/profile.py` builds, per shipped/planted column: role (feature/label/derived/leakage_proxy), dtype, summary stats (mean/std/min/p25/median/p75/max/skew for numeric; top categories + class-balance for discrete), causal parents (incl. derived columns), realized **post-injection** snapshot (missing% + moments), and **failure attribution** — which modes hit the column with their realized magnitudes (inverted from the failure diffs). New `engine/advice.py` is a static, deterministic knowledge base mapping each mechanism (+ class imbalance) → plain-language explanation, the single best handling approach, and concrete ML techniques; severity escalates with corruption magnitude and leakage is flagged **critical** ("drop before training"). Best-effort label detection (difficulty.label, else a boolean/categorical causal sink). Wired through `reports.ReportBundle.profile` → `ReportRow.profile` (Alembic **0004_report_profile**) → serializer → `schemas.Report.profile`; pipeline now passes `spec`+`injected` into `build_report`. Frontend: `Report.profile` types + new **Column Guide** tab (`ColumnGuideView.tsx`) with severity-ranked issue cards, stat grids, class-distribution bars, and a highlighted "how to handle it" recommendation per issue. Pure/deterministic (no RNG, no refit — invariants #1/#3/#6 intact); engine imports nothing new (lint-imports 5/5). New `tests/unit/test_profile.py` (16 tests: attribution, stats, determinism, imbalance, advice, fallbacks); full suite **316** green, ruff/mypy clean, frontend tsc clean. testing_guide.md gains the Column-Guide test. |
| 2026-06-03 | Implemented **task 18.6 — hackathon mode**: a curated, **data-only/additive** enterprise template pack on top of the existing templates system (no engine or spec change). Four flagship challenges — `credit-default-challenge` (Finance; deep DAG → latent risk → `advanced` band + MNAR/MAR/drift/leakage/label-noise), `clinical-deterioration` (Healthcare; latent-severity **confounder** drives vitals *and* outcome + `advanced` band + MNAR/MAR/MCAR), `predictive-maintenance` (IoT; 3 additive **time-series** → latent wear → label + drift/noise/MCAR/leakage), `telecom-churn-challenge` (Telecom; **realistic-text** identity + latent dissatisfaction → hard `kaggle` band + MNAR). Each carries a `meta.challenge` brief (target/metric/split/gotchas). `TemplateMeta`/`TemplateSummary` gain a `level` facet (`starter`\|`hackathon`); `datadoom template list --level` filter + `[hackathon]` tag; web **Templates** gallery leads with flagships + Trophy badge + level filter. Logistic biases tuned so labels are realistic minorities (26–33%) and difficulty bands are met (verified via the engine API). All four validate/`run`/`verify` byte-stable; covered by the existing whole-catalog `test_templates.py`; full suite **297** green; ruff/mypy/import-linter 5/5; frontend tsc+vite clean into `webdist/`. testing_guide.md gains Group **V**. |
| 2026-06-03 | **Completed Phase 5** (task 18.3/18.4/18.5). **Time-series (18.3):** `engine/timeseries.py` realizes the additive `Xₜ=T(t)+S(t)+AR(p)+εₜ` (05 §6) — vectorised trend+seasonality, sequential AR(p) residual warm-started at 0, εₜ via `RNG(noise:<name>)`. New `TimeseriesFeature` (trend/seasonality[]/ar/noise_std/min/max/dtype) on the discriminated union; validation adds AR stationarity (Σ\|φ\|<1), `period>0`, `min≤max`; allowed as a causal **parent** (float-coercible), never a target, skipped by distribution compliance. `examples/timeseries-sensor.datadoom.yaml` added to the determinism gate; `tests/unit/test_timeseries.py` (12: component math, AR autocorrelation, validation, byte-repro, causal-child recovery). Frontend: `timeseries` feature type + Inspector editor + summary/colors (tsc clean). **Adapters (18.4):** `src/datadoom/adapters/` — `load_dataframe` (pandas, core; auto-detects csv/parquet/json, clean/injected) + `to_torch_dataset`/`to_tf_dataset`/`to_hf_dataset` (lazy-imported behind optional `[torch]`/`[tf]`/`[hf]` extras with install hints). 5th import-linter contract "adapters depend only on engine"; `tests/unit/test_adapters.py` (pandas paths + importorskip + missing-backend hint). **AI authoring (18.5):** `engine/reference.py` `build_capabilities()` — a machine-readable manifest of every distribution/structural-fn/failure/tier/feature-type/exporter/provider + the hard validation rules, built from the **live registries** (so plugins appear); exposed via `datadoom spec-reference` (CLI) and `GET /api/spec-reference`. New docs `docs_v2/20_YAML_Authoring_Guide.md` (beginner) + `docs_v2/21_LLM_Spec_Authoring_Reference.md` (AI contract, all four few-shots validate). `tests/unit/test_reference.py` + `tests/api`. Suite 275 → 297 (+2 skipped torch/hf); ruff/mypy clean; import-linter 5/5; both frontends built into `webdist/`. **Phase 5 complete.** |
| 2026-06-03 | Implemented backlog **task 11.10** — chi-square goodness-of-fit compliance for integer/discrete/clamped features (see the 11.10 detail above). Suite 272 → 275. New beginner guide `docs_v2/20_YAML_Authoring_Guide.md`. |
| 2026-06-01 | Phase 0 implemented end-to-end (tasks 0.1–6); all gates green. Status file created. |
| 2026-06-01 | Switched dev workflow to a project-local `.venv` (Python 3.11). mypy whole-package now clean. Updated testing_guide.md + CLAUDE.md. |
| 2026-06-01 | Test review: logged task **TH** (correctness-test hardening, TH.1–TH.8) — gaps where a logic bug could pass CI. Specs added to testing_guide.md Group G; implementation pending user go-ahead. |
| 2026-06-01 | Added `design/UI_Design_Prompts.md` — structured Claude Design prompts for the full frontend (design system + 12 screens), to be built with Claude Design in P1. |
| 2026-06-01 | Implemented task **TH** (correctness-test hardening, TH.1–TH.8): +23 tests (suite 42 → 65), all gates green. New `tests/unit/test_dist_correctness.py` + `test_metadata.py`; additions to `test_hashing.py` and `test_spec_validate.py`. Promoted testing_guide.md Group G from planned to implemented. |
| 2026-06-01 | Reworked `design/UI_Design_Prompts.md` to the **editorial / magazine** aesthetic ("The Lab Journal"): serif headlines, kickers/pull-stats, hairline rules, and **first-class theme toggling** — a "Paper" (light, default) + "Ink" (dark) + System system designed into every screen, with the brand's reserved Ember hazard accent preserved. |
| 2026-06-01 | Implemented Phase 1 backend (tasks **7–9**): `config.py` (+`$DATADOOM_HOME`), `store/` (ORM + SQLite/WAL + repositories + local artifact store + Alembic `0001_init`), `jobs/` (in-process `WorkerPool` + `EventHub` replay/cancel), `api/` (FastAPI factory, routes, error envelope, WebSocket + SSE, estimator, `datadoom serve`), and `engine/reports.py` (report assembly w/ Pearson correlation). New import-linter contract "store depends only on engine" (3 total). +17 tests (suite 65 → 82); ruff/mypy/import-linter green. |
| 2026-06-01 | Implemented Phase 1 frontend (task **10**): React+TS+Vite+Tailwind web Canvas with the editorial Paper/Ink theme system, Dashboard, Canvas (schema table + Inspector + live preview + autosave + spec drawer), live WS Generation Tracker, Results (preview/distributions/correlation/evaluation), and Export. Builds into `src/datadoom/webdist/` and is served by `datadoom serve`. **P1 exit gate met.** testing_guide.md gains Groups **H** (server/API) and **I** (web Canvas + theme toggling). |
| 2026-06-02 | Implemented Phase 2 engine (task **11**): new `engine/causal/` (`graph.py` networkx DAG + lexicographical topo sort; `functions.py` `StructuralFn` ABC + linear/logistic/polynomial/map/identity; `execute.py` SEM walk with per-node noise via `RNG(noise:v)`, boolean children via `RNG(feature:v)`, and `do()` interventions). Pipeline grows a `causal` stage (roots sampled in base, targets derived in topo order). Validation extended (structural-fn params, map coverage, numeric/boolean targets, orphan derived-numeric, noise dist, intervention refs). Reports add `causal_truth` + a `mutual_information` matrix — the latter persisted via a new `reports.mutual_information` column (ORM model + `0002_report_mutual_information` migration + repository + API schema/serializer). Added `networkx>=3.1` core dep + mypy override. New `examples/causal-fraud.datadoom.yaml`; ruff/mypy/import-linter green. testing_guide.md gains Group **J**. Frontend Graph view (task 12) still open. |
| 2026-06-02 | Fixed a logical error in **KS compliance** surfaced by auditing the causal example: a one-sample continuous KS test was being run against integer-rounded and `min`/`max`-clamped data, so a *correct* `age` (mean 40.02 vs target 40) scored `compliance 0.0`. KS now only counts toward the score when valid (continuous distribution + float dtype + no clamping); integer/discrete(poisson)/clamped features are still reported (KS stat + empirical moments) but marked `applicable: False` and excluded. Score = passes/applicable; `to_dict` adds `applicable_features`/`assessed_features`; CLI shows `(N KS-assessed, M n/a)`. Also added causal **parent-type/fn compatibility** validation (e.g. `linear` from a categorical parent now fails cleanly instead of a runtime `ValueError`). Empirically verified the SEM: OLS recovers age_w≈798/bias≈9933/edu_w≈1.005 (targets 800/10000/1.0), noise std≈5077 (target 5000), and `is_fraud` logistic calibration matches per-bin. +8 tests (suite 103 → 110). |
| 2026-06-02 | Logged a **backlog** item (task 11 detail): an effective-distribution goodness-of-fit (chi-square against the truncated+discretized PMF) so integer/discrete/clamped features can earn a real compliance pass instead of abstaining (`applicable: False`). Added **end-to-end dataset-audit tests** (`tests/unit/test_dataset_audit.py`, 13) that generate from the shipped examples and assert the realized frame matches the spec — for the **non-causal** `tabular-basic` (per-feature moments, bounds, categorical weights, boolean rate, datetime range, text length, honest KS-applicability) and the **causal** `causal-fraud` (OLS coefficient recovery, noise scale, logistic calibration, true-graph). Suite 110 → 123; ruff/mypy/import-linter green. testing_guide.md gains Group **K**. |
| 2026-06-02 | Implemented Phase 2 frontend (task **12**): the web **Graph view**. Added `reactflow`; typed the causal graph + report shapes in `lib/types.ts`; `lib/causal.ts` (topological auto-layout, client-side cycle detection, derived↔dist reconciliation, intervention helpers). New `CausalGraphEditor` (drag-to-connect with live cycle-rejection toast, topological layout, derived/intervention badges), `CausalInspector` (structural-fn editor for linear/logistic/polynomial/map/identity + per-node noise + `do()` intervention), and a read-only `CausalGraphView`. Canvas gains a **Table ⇄ Graph** toggle with a contextual right panel; Results gains a **Causal Graph** tab (true DAG) and a **Correlation & MI** tab, and now renders KS-applicability honestly (`n/a` for integer/discrete/clamped, with `N of M applicable`). Built into `src/datadoom/webdist/` (tsc strict clean); end-to-end API smoke confirms the SPA serves and a causal run's report carries `causal_truth`/`mutual_information`. **Phase 2 complete.** testing_guide.md gains Group **L**. |
| 2026-06-02 | Fixed `sqlite3.OperationalError: no such column: reports.mutual_information` on existing databases created before the `0002_report_mutual_information` migration existed. The model and migration were correct, but existing DBs (stuck at `0001_init`) had never had the upgrade applied. Applied `alembic upgrade head` to bring the on-disk schema up to date. |
| 2026-06-02 | Implemented Phase 3 engine (task **13**): new `engine/failure/` (`base.py` `FailureMode` ABC + helpers — stable `sigmoid`, NaN-robust `standardize`, logistic-intercept calibration; `modes.py` 8 builtins — mcar/mar/mnar/label_noise/feature_noise/drift/covariate_shift/leakage, each returning a diff summary; `apply.py` orchestrator + `FAILURE_MODES` registry). Pipeline grows a `failure_injection` stage that captures the clean baseline then corrupts a copy via `RNG(failure:i)`; `RunResult.injected` + a versioned `data.injected.csv` artifact (`ArtifactInfo.version`) written when `export.versions` includes `injected`; metadata gains a `failures` block. `reports.py` populates the `failures` section (already wired through store/API from P1 — no migration). `validate.py` now dispatches to per-mode validators (unknown type + per-mode field/type/reference checks). Fixed a NaN-cast bug (`_assign_numeric`) so additive transforms preserve earlier injected missingness on int columns. Added `examples/failure-fraud.datadoom.yaml`; `tests/unit/test_failure.py` (26) + injected byte-stability in the determinism gate. Suite 123 → 151; ruff/mypy/import-linter green; CLI `run`/`verify` confirmed. Frontend Failure Configurator (task 14) still open. testing_guide.md gains Group **M**. |
| 2026-06-02 | Added a **critical mathematical audit** for the failure modes (task **13.9**, `tests/unit/test_failure_audit.py`, 14) — the P3 analogue of the Phase-2 dataset audit: generate at n=20k and *recover each mechanism's parameters from the realized frame* rather than eyeballing a rough rate. Empirically verified (n=40k probe): **MAR/MNAR** IRLS logistic regression recovers the `strength` slope (1.50/3.00 → 1.497/3.021) with the calibrated intercept hitting the 0.20 rate; **categorical label_noise** transition matrix is uniform (off-diagonals = p/(k−1) = 0.0667, diagonal = 1−p); **boolean label_noise** flip is class-symmetric and the marginal matches `q(1−p)+(1−q)p`; **feature_noise** ε passes KS-Gaussian (p≈0.98), recovers σ, independent of x; **drift** is an exact linear ramp (max error ~1e-14); **covariate_shift** hits target mean/std to 8 decimals; **leakage** correlation matches the closed form `1/√(1+η²)` to 5 decimals; **MCAR** sits in the binomial 3σ band with Welch-t confirming independence. Suite 151 → 165; all gates green. |
| 2026-06-03 | Implemented enhancement **E2**: the web **Generation Overview** dashboard tab (default tab on the Results page), composed entirely from the reproducible metadata (spec + report + artifacts) — no engine change. New `OverviewView.tsx`: headline numerals (rows/columns/compliance/failure-modes/seed), a dependency-free SVG **donut** of column-type composition (reusing `TYPE_COLOR`), a **distribution-family** bar list, a conditional **causal-structure** summary (edges/derived/interventions), a conditional **failure-by-mode** bar list, and an **artifacts** table (format/version/human size/short checksum). Also wired realistic-generator authoring into the Canvas: `TextControls` (Inspector) gains a grouped Generator dropdown + Locale select (length inputs only for `lorem`); `lib/types.ts` gains `TextFeature.locale`, `TEXT_GENERATORS`, `TEXT_LOCALES`; `summary.ts` shows locale (not token length) for realistic generators. Frontend builds (tsc strict + vite) clean into `webdist/`. testing_guide.md gains **O1**. |
| 2026-06-03 | Implemented enhancement **E1**: realistic-but-deterministic text providers backed by *mimesis*. New `engine/dist/providers.py` — a 24-key provider catalog (name/first_name/last_name/email/username/phone/occupation/title/nationality/address/street/city/state/country/postal_code/company/currency/price/url/hostname/ipv4/word/sentence/color) plus `resolve_locale`. mimesis is seeded per-feature from a 32-bit int pulled off the feature's own `RNG(feature:name)` (isolated, non-global), so `(spec_hash, seed)` stays byte-reproducible on the pinned mimesis line — same contract as the numpy pin. `TextFeature` gains optional `generator` (non-`lorem`) + `locale`; `pipeline._sample_feature` dispatches lorem→`sample_text` else `sample_provider`; `validate.py` rejects unknown generator/locale early. Added `mimesis>=19,<20` core dep, `examples/people-realistic.datadoom.yaml` (also in the determinism gate), `tests/unit/test_providers.py` (10). ruff/mypy/import-linter green (engine stays framework-free — mimesis is a pure offline lib). testing_guide.md gains **G5b**. |
| 2026-06-03 | Implemented enhancement **E4**: web **"Import from YAML"**. New `POST /api/specs/parse` parses raw YAML/JSON text through the same PyYAML loader + `engine.spec` validation the CLI uses (syntax + validation errors → 422 with a `locator`). Dashboard gains a **From YAML** action → `ImportYamlModal` (paste **or** upload/drag a `.yaml`/`.json` → Validate → Import & open Canvas), then the existing Generate flow runs it. `tests/api` +3 (parse ok / syntax-error / validation-error locator). Suite 232 → 235; frontend tsc strict + vite clean. testing_guide.md gains **Q3**. |
| 2026-06-03 | Implemented enhancement **E3**: **latent features** (`emit: false`) — a feature that drives sampling / the SEM and appears in the true causal graph but is **not shipped** (excluded from the CSV, the difficulty probe, compliance, correlation/MI). Models hidden confounders and latent scores behind a label. Hash-safe: `emit` defaults to `None` and is only canonicalized when explicitly `false`, so existing spec hashes (and the golden checksum) are unchanged. Pipeline drops latents right after the causal stage (before difficulty/failures/compliance/packaging); validation forbids a latent difficulty-label or a failure that references a latent. **Resolves a reviewer-flagged smell** in `examples/difficulty-credit.datadoom.yaml`: `risk_score` (the logit-combining latent) is now `emit: false`, so the probe predicts `defaulted` from genuine observables — no redundant proxy column — while the latent still appears in the true causal graph. (For the record: the prior example didn't actually leak — `risk_score` was an exact linear combo of the roots, R²=1.0, adding 0 to the linear probe; clean AUROC 0.90 not 0.95+, and label noise was never maxed — but shipping a redundant latent was poor hygiene.) New `tests/unit/test_latent.py` (7, incl. hidden-confounder correlation + hash-safety). Frontend: `emit` on feature types, Inspector **Latent (not exported)** toggle, a `latent` table badge, and latents excluded from difficulty label candidates. Suite 225 → 232. testing_guide.md gains Group **R**. |
| 2026-06-03 | Implemented Phase 4 (tasks **15–16**): **difficulty targeting**. New `engine/difficulty/` — `probes.py` (`ProbeModel` ABC + scikit-learn `logreg`/`tree`, seeded design matrix + binary-AUROC), `knobs.py` (`DifficultyDial`: feature-observation noise → label flips, draws pre-taken and scaled so μ(d) is monotone), `calibrate.py` (adaptive bisection on the dial, tier→band map 05 §5.3, honest-miss fallback). The pipeline grows a `difficulty` stage that calibrates the clean frame to a target baseline-AUROC band before failures/compliance; `RunResult.difficulty` + `reports.difficulty` (column already existed from `0001_init` → **no migration**). Validation restricts to binary-classification labels, known probe, tier-or-band target, knobs ⊆ {noise, label_noise}. **Knob design decided with the user — the lean default** (feature noise primary + label flips deep end; causal shrink/imbalance deferred to backlog). Added **scikit-learn** as a pinned core dep (probe metric is on the determinism-critical path); engine stays framework-free (import-linter green). Refactored the Phase-3 failure audit's hand-rolled IRLS → scikit-learn `LogisticRegression(C=inf)` now the dep exists. Frontend: typed `Difficulty`/`DifficultyReport` + `lib/difficulty.ts`; Canvas **Difficulty** view (`DifficultyConfigurator`: tier cards/custom band, AUROC band meter, label/probe/knobs/iters, honest explainer); Results **Difficulty** tab (`DifficultyView`: achieved-vs-target + `BandMeter`, knob stats, bisection trace) — replaces the Evaluation tab's stale Phase-4 placeholder. New `examples/difficulty-credit.datadoom.yaml` (in the determinism gate); `tests/unit/test_difficulty.py` (18) + `test_difficulty_audit.py` (8) + API round-trip. Suite 165 → 225; ruff/mypy/import-linter green; frontend tsc strict + vite clean into `webdist/`. **P4 exit gate met — Phase 4 complete.** testing_guide.md gains Groups **P**/**Q**. |
| 2026-06-02 | Implemented Phase 3 frontend (task **14**): the web **Failure Configurator + Comparison**. Canvas gains a third **Failures** view (`FailureConfigurator` + `FailureInspector`) — an ordered, reorderable pipeline of stage cards with a grouped Add-failure menu, type-aware controls (column/driver selects, rate/strength/noise sliders, dist+params, drift schedule, target moments, multi-column chips), live declarative impact estimates, inline validation, a clean-baseline guarantee banner, and an injected-export toggle (auto-enabled on first failure). `lib/failures.ts` holds the mechanism metadata, defaults, summaries, honest impact math, client pre-flight validation, and rename/delete reconciliation. Results gains a **Comparison** tab (`ComparisonView`, shown when the run injected failures): summary pull-stats, per-mode realized-effect cards (authoritative engine diffs as bars/gauges/sparklines), clean-vs-injected distribution overlays, and a cell-level diff table (nullified/changed/planted-column highlights + "changed rows only"). Added `--warning-tint`/`--info-tint` design tokens. Built into `src/datadoom/webdist/` (tsc strict clean); end-to-end API contract verified over HTTP (run → `report.failures` realized stats; `clean`+`injected` artifacts; injected preview carries the planted column + nulls; SPA serves). **P3 exit gate met — Phase 3 complete.** testing_guide.md gains Group **N**. |
| 2026-06-03 | Implemented Phase 5 task **18.1 + 18.2** — **exporters + templates** (time-series 18.3 + framework adapters 18.4 deferred). **Exporters:** new `engine/export/json_exporter.py` (byte-stable records array; numpy/NaN/Timestamp normalized) and `parquet_exporter.py` (lazy `pyarrow`, fixed write opts, errors with an install hint if the optional `[parquet]` extra is absent); `EXPORTERS` now holds csv/json/parquet. The pipeline's `_package` writes **every** `export.formats` × version (`data.<ext>` / `data.injected.<ext>`), `validate.py` rejects unknown formats (locator `export.formats`), and the preview route falls back csv→json→parquet. Added `Exporter.extension`/`ext`, the `[parquet]` extra (+ pyarrow in dev), and a frontend output-formats checklist in the Generate modal (CSV locked). **Templates:** new `src/datadoom/templates/` (typed `CATALOG` + `importlib.resources` loader) with **8 domain starters** — fraud-detection (causal+failures), customer-churn (difficulty+latent), hospital-readmission (causal+latent), and quick distribution-only/realistic-text tables (e-commerce orders, IoT sensor readings, people directory via mimesis, marketing A/B test, insurance claims with a Pareto heavy tail) — each parametrized-test-gated to parse/validate/generate; `GET /api/templates` + `/{id}` (full spec), CLI `datadoom template list/show/use`, and a web **Templates** gallery rendered as a flat responsive grid with a domain chip per card (one-click → create dataset → Canvas, replacing the placeholder). The plugin registry now seeds **24** built-ins (3 exporters). `tests/unit/test_export_formats.py` (6) + `test_templates.py` (parametrized over the catalog) + `tests/api` (4). Suite 251 → 272; ruff/mypy/import-linter green; both frontends built into `webdist/`. **P5 gate (templates + Parquet) met.** testing_guide.md gains Group **T**. |
| 2026-06-03 | Implemented Phase 5 task **17** — the **plugin system**. New `src/datadoom/plugins/` (`contracts.py` re-exports the 5 engine ABCs as `datadoom.plugin` + a `schema()` helper; `registry.py` `PluginRegistry`/`PluginRecord` — kind detection, conflict-fail, `param_schema` validation, registers **into the live engine dicts** so the pipeline picks plugins up by name; `loader.py` `load_plugins()` — built-ins → entry points (`datadoom.plugins`) → local `$DATADOOM_HOME/plugins/*.py`; `scaffold.py` `scaffold_plugin` + `check_object`/`check_plugin` contract checks incl. a tokenize-based RNG-hygiene scan) + a `datadoom/plugin.py` public shim. The 5 engine ABCs gain an additive `param_schema` class attr (default `None`). API: `GET /api/plugins` returns the live registry (`PluginInfo` + `source`/`builtin`); `create_app` loads plugins at startup. CLI: `datadoom plugin list/new/check`; `run`/`validate`/`verify` load plugins first. Frontend: real **Plugins** gallery (replaces the placeholder) grouped by kind with source badges + `lib/schemaForm.tsx` rendering a `param_schema` fragment into controls; built into `webdist/`. New 4th import-linter contract "plugins depend only on engine" + engine forbidden of `datadoom.plugins` (engine ← plugins). `tests/plugin_contract/test_plugins.py` (16): built-ins register/pass, a plugin distribution flows through a run (Weibull mean ≈ λ·Γ(1+1/k)), local-dir + entry-point discovery, conflict-fail, schema/determinism/RNG-hygiene rejection, scaffold→check for all 5 kinds. Suite 235 → 251; ruff/mypy/import-linter green; CLI + `GET /api/plugins` verified. **P5 plugin gate met** (declare a plugin → appears in `plugin list`/API/UI and is usable by name, zero engine change). testing_guide.md gains Group **S**. Tasks 18–19 remain. |
