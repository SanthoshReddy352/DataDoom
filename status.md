# DataDoom — Implementation Status

> Single source of truth for **what is built**. The design lives in `docs_v2/`;
> this file tracks delivery against it. Update it whenever a task's status
> changes or a task is broken down into subtasks.
>
> **Last updated:** 2026-06-02

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
| 13 | `engine/failure/` — MCAR/MAR/MNAR, noise, drift… | P3 | ⬜ | — |
| 14 | Frontend Failure Configurator + Comparison | P3 | ⬜ | — |
| 15 | `engine/difficulty/` — probes + adaptive loop | P4 | ⬜ | — |
| 16 | Frontend difficulty UI + evaluation report | P4 | ⬜ | — |
| 17 | `plugins/` — registry + loader + scaffolder | P5 | ⬜ | — |
| 18 | Exporters (Parquet/JSON) + templates + time-series | P5 | ⬜ | — |
| 19 | Hardening, docs site, release automation, team mode | P6 | ⬜ | — |

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

#### Backlog — compliance for integer/discrete/clamped features (deferred)

Today, when a continuous KS test is not valid (integer `dtype`, a discrete
distribution like poisson, or `min`/`max` clamping that piles mass at the bounds)
the feature is **reported with its KS stat + empirical moments but marked
`applicable: False`** and excluded from the score — it *abstains* rather than
falsely failing (the prior bug scored a correct integer `age` at `0.0`). A future
enhancement would let those features earn a **real pass** via a goodness-of-fit
test against the *effective* distribution: a chi-square (or G-test) on binned
counts versus the truncated-and-discretized PMF, where boundary bins absorb the
clamped tail mass (`P(min)=F(min+½)`, `P(max)=1−F(max−½)`). That turns "n/a" into
an actual validated pass/fail for the most common real-world feature shapes
(ages, counts, bounded scores). Deferred as medium-risk (binning/low-count merge
rules) and orthogonal to the P2 gate; the current behavior is honest and safe.

## Detail — Phase 3+ (remaining)

Tasks 13–19 are defined in `docs_v2/17_Implementation_Guide.md` (steps 13–19) and
`docs_v2/16_Engineering_Roadmap.md` (P3–P6). Next up is **P3 — failure injection**
(`engine/failure/` + the Failure Configurator UI). They will be broken down here
as each is picked up.

---

## Change history

| Date | Change |
|---|---|
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
