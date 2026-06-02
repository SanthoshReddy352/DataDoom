# 17 — Implementation Guide

> Concrete, ordered build sequence. Follow it top-to-bottom; each step is small, testable, and leaves the tree green. Obeys `00_README_Index.md`. Phase intent in `16`; layout in `10`.

---

## Phase 0 — Repo & Tooling

### 0.1 Initialize
- `git init`; create the monorepo layout from `10 §2` (`src/datadoom/...`, `frontend/`, `tests/`, `docs/`).
- `pyproject.toml` (hatchling): metadata, deps (`11 §3`), `[project.scripts] datadoom = "datadoom.cli.main:app"`, dev extras.
- Add `LICENSE` (Apache-2.0), `README.md`, governance files (`15 §2`).

### 0.2 Quality gates first
- Configure **Ruff**, **mypy** (strict on `engine/`), **import-linter** rules (`10 §4`), **pytest**, **pre-commit**.
- `.github/workflows/ci.yml`: lint → type → import-lint → tests on `{win,mac,linux} × {3.11,3.12}`.
- Make CI green on an empty skeleton before writing features.

> 🚦 Gate: a trivial `test_version` passes in CI on all platforms.

---

## Phase 0 (engine) — Deterministic Core

Build the pure engine **bottom-up**, each module fully tested before the next.

### 1. `engine/rng.py`
- `RNGFactory(spec_hash: str, seed: int)`; `.generator(namespace) -> np.random.Generator(PCG64(key))`; key = `sha256(spec_hash||':'||seed||':'||ns)` → uint64 (`05 §1.2`).
- Test: same inputs → identical draws; different namespaces → independent; adding a namespace doesn't perturb others.

### 2. `engine/spec/`
- Pydantic models (`06 §1`) for the spec (`04`).
- `hashing.py`: canonical JSON (sorted keys, normalized numbers, **seed excluded**) → `spec_hash` (`05 §1.1`).
- `validate.py`: structural rules + cross-field (acyclicity stub, references, derived-vs-sampled) (`04 §9`).
- Test: valid specs parse; each invalid case raises with the right `locator`; canonicalization is stable; hash excludes seed.

### 3. `engine/dist/`
- `base.Distribution` ABC (`sample`, `validate`, `cdf`).
- `builtins.py`: normal, lognormal, poisson, pareto, uniform, exponential, bernoulli, categorical, datetime, lorem-text.
- `compliance.py`: KS stat + p-value, empirical params, compliance score. **No refitting** (`05 §2.3`).
- Test: empirical params within tolerance; KS rejection ≈ α across seeds (proves no refit); clamping recorded.

### 4. `engine/export/`
- `Exporter` ABC + CSV writer (stable column order); `metadata.json` (spec, spec_hash, seed, summaries, checksums); SHA256 per file.
- Test: byte-stable CSV; checksum stable across runs.

### 5. `engine/pipeline.py` (minimal) + `RunContext`
- Stages: intake → snapshot → seed → base_generation → compliance → packaging. `ProgressEmitter` is a no-op sink for now.
- Test (determinism): two in-process runs, same seed → equal frames & checksums.

### 6. `cli/main.py` (Typer)
- `datadoom run spec.yaml --seed N --out dir`, `datadoom validate`, `datadoom verify --against`.
- Add first **golden specs** + `tests/golden` checksums; wire the **repro-matrix** workflow.

> 🚦 Gate (P0 exit): `datadoom run` produces a checksummed CSV; `datadoom verify` round-trips; repro CI bitwise-green on each pinned cell.

---

## Phase 1 — Server + Web Canvas MVP

### 7. `store/`
- SQLAlchemy models (`06`/`07`), SQLite engine (WAL, FK on), repositories, Alembic `0001_init`, auto-`upgrade head` on startup.
- `artifacts.py`: local FS `ArtifactStore`.
- Test: CRUD; spec immutability (edit → new version); cascade delete.

### 8. `jobs/worker.py`
- In-process async + thread-pool worker; runs `engine.pipeline`; `progress.py` publishes events to a WS hub. Cooperative cancel.

### 9. `api/`
- `app.py` (factory, static SPA mount, OpenAPI), `deps.py` (no-op auth local), `ws.py` (hub + SSE fallback), routes from `08`.
- Test: route happy paths + 422 `locator` + 409 idempotency; WS emits canonical stages → `completed`.

### 10. `frontend/` scaffold
- Vite + React + TS + Tailwind + Zustand + TanStack Query; generate API client from `/api/openapi.json`.
- Pages: **Dashboard**, **Canvas (Table view + Inspector)**, **Generation Tracker (WS)**, **Results (preview + distributions)**, **Export**.
- Build → copy to `src/datadoom/webdist/`; verify `datadoom` serves it (`10 §3`).

> 🚦 Gate (P1 exit): fresh env → `datadoom` → create dataset → generate 50k rows → preview → export CSV, all in-browser, < 5 min.

---

## Phase 2 — Causal Engine

### 11. `engine/causal/`
- `graph.py` (networkx build, **sorted** iteration, cycle detection, topo sort); `functions.py` (`StructuralFn` ABC + builtins); `execute.py` (SEM walk with per-node noise via `RNG(noise:v)`); interventions.
- Extend pipeline with the `causal` stage; reports add correlation/MI + true graph.
- Test: coefficient recovery on known DAGs; cycle rejection; intervention detaches edges.

### 12. Frontend Graph view
- React Flow nodes/edges; edge creation → structural-fn editor; live cycle rejection toast; intervention toggle; auto-layout (topological).
- Results: render true causal graph + correlation heatmap.

> 🚦 Gate: author `age→income→is_fraud`, generate, inspect true graph + correlations.

---

## Phase 3 — Failure Injection

### 13. `engine/failure/`
- `FailureMode` ABC + builtins (MCAR/MAR/MNAR, label/feature noise, drift, covariate_shift, leakage); each returns `(df, diff_summary)`, clean baseline preserved.
- Pipeline `failure_injection` stage; `POST /api/runs/{id}/inject`.
- Test: rate accuracy, driver correlation, leakage MI, drift schedule.

### 14. Frontend Failure Configurator + Comparison
- Accordions/sliders; **live diff preview** (client estimate of impact); Comparison view (clean vs injected highlights).

> 🚦 Gate: inject MNAR + label noise; see diff + comparison; clean variant still available.

---

## Phase 4 — Difficulty Targeting

### 15. `engine/difficulty/`
- `ProbeModel` ABC + logreg/tree; `calibrate.py` adaptive loop (bisection on knobs); achieved-metric reporting.
- **Validate** tier→band mapping (`05 §5.3`) with a calibration test (`13 §4`).
- Pipeline `difficulty` stage.

### 16. Frontend difficulty UI + evaluation report
- Tier/band selector; report shows target vs achieved + probe + iterations.

> 🚦 Gate: `target: kaggle` lands baseline AUROC in band, reported honestly.

---

## Phase 5 — Ecosystem

### 17. `plugins/`
- `contracts.py` (re-export ABCs as `datadoom.plugin`); `loader.py` (entry points + local dir); `registry.py` (validate, register, conflict-fail).
- Register core built-ins via the registry; `GET /api/plugins`; UI renders `param_schema` into forms.
- `datadoom plugin new/check`; plugin contract tests (`13 §5`).

### 18. Exporters + Templates + Time-series
- Parquet/JSON exporters + pandas/PyTorch/TF/HF adapters.
- `templates/` built-ins + gallery + `templates/use`.
- `engine/timeseries.py` (`05 §6`).

> 🚦 Gate: install a sample plugin → appears in UI; start from a template in one click; export Parquet.

---

## Phase 6 — Maturity / 1.0

### 19. Hardening
- Full repro matrix green + badge; perf budgets enforced; accessibility pass.
- Docs site (mkdocs) published; examples gallery.
- Release automation + signed releases + Docker image.
- Optional team mode: Postgres/S3/Redis backends behind config flags + auth dependency + `owner_id` scoping.

> 🚦 Gate (1.0): all CI gates green, repro bitwise-clean in pinned cells, docs complete, fresh-install smoke on all OSes.

---

## Cross-Cutting Implementation Rules

1. **Engine purity:** never import FastAPI/SQLAlchemy inside `engine/`. import-linter enforces it.
2. **One pipeline:** CLI, API, and `datadoom.generate()` all call `engine.pipeline` — never duplicate generation logic.
3. **RNG discipline:** every stochastic line uses an injected `rng`. Add an AST/grep check to CI for banned calls.
4. **Tests precede merge:** new behavior ships with unit + (if stochastic) determinism tests.
5. **Spec is additive:** within `datadoom_version: 1`, only add optional fields.
6. **Prefer plugins:** if a capability could be third-party, implement it against the plugin ABCs, not as a core special case.
7. **Keep it offline:** no core code path requires network.
