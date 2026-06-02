# 03 — Technical Architecture

> Modular monolith, Python-first, local-first. Obeys `00_README_Index.md`. Rationale: `../Docs/DataDoom_Critical_Analysis_and_Recommended_Architecture.md`.

---

## 1. Architecture Philosophy

DataDoom is **one application**, not a distributed system. The guiding rule:

> Clean module boundaries *inside* one codebase, deployed as one process. Distribute later only if measured load forces it.

Properties we optimize for:
- **Deterministic** (reproducibility is the headline guarantee).
- **Installable & local-first** (zero external services by default).
- **Modular & extensible** (plugins, clean engine boundaries).
- **Debuggable** (a generation runs start-to-finish in one observable process).

Explicitly **rejected** (and why): microservices, Kafka, gRPC/Protobuf, Go control plane, day-one Kubernetes, multi-region, multi-tenant RLS — they add operational cost and failure modes with zero benefit at DataDoom's actual workload (seconds-to-minutes single-machine jobs).

---

## 2. High-Level View

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser (SPA)                         │
│   React + TS + Vite · React Flow · Tailwind · Zustand         │
└───────────────▲───────────────────────────▲──────────────────┘
                │ REST (OpenAPI)             │ WebSocket (progress/logs)
┌───────────────┴───────────────────────────┴──────────────────┐
│                    DataDoom Server (FastAPI)                   │
│  api/        routes, validation, OpenAPI, WS hub               │
│  jobs/       worker pool (in-process default · RQ optional)    │
│  ┌──────────────────────  engine/  ───────────────────────┐   │
│  │ rng · dist · causal · failure · difficulty · export     │   │
│  │ spec (parse/validate/hash) · pipeline (orchestrator)    │   │
│  └─────────────────────────────────────────────────────────┘  │
│  plugins/    runtime registry (entry points + local dir)       │
│  store/      metadata DB + artifact storage adapters           │
└───────────────▲───────────────────────────▲──────────────────┘
                │                            │
        ┌───────┴────────┐          ┌────────┴─────────┐
        │ SQLite (default)│          │ Local FS (default)│
        │ Postgres (team) │          │ S3-compat (team)  │
        └─────────────────┘          └──────────────────┘
```

The **frontend is bundled into the Python wheel** and served as static files by FastAPI, so `pip install datadoom && datadoom` yields a working app with no separate frontend deploy.

---

## 3. Layers

### 3.1 Client (Web App)
- SPA served by the backend at `/`. Talks REST for CRUD/commands, WebSocket for live run progress.
- State: Zustand (UI/local), TanStack Query (server cache). React Flow for the causal graph.
- Detail: `02_User_Flow_Guide.md`.

### 3.2 API Layer (`api/`)
- FastAPI app. Pydantic v2 request/response models → **OpenAPI auto-generated**.
- Responsibilities: routing, request validation, auth (no-op in local mode; pluggable for team mode), WebSocket hub for progress fan-out, static-file serving for the SPA.
- Detail: `08_API_Contract.md`.

### 3.3 Job Layer (`jobs/`)
- Default: **in-process worker pool** (asyncio + a thread/process pool for CPU-bound generation). A run is a coroutine that drives the pipeline and publishes progress events to the WebSocket hub.
- Optional **team mode:** RQ (Redis) workers for concurrency across processes; same pipeline code, different dispatch.
- Cooperative cancellation; per-run status persisted in `GenerationRun`.

### 3.4 Engine (`engine/`) — the core value
Pure, side-effect-light Python modules. **No web, DB, or framework imports here** — the engine is usable as a library (`import datadoom`).

| Module | Responsibility |
|---|---|
| `engine.spec` | Parse/validate spec, build immutable snapshot, compute `spec_hash`. |
| `engine.rng` | Seeded RNG wrapper; key derivation; the determinism invariant. |
| `engine.dist` | Distribution sampling + compliance reporting (KS, fit). |
| `engine.causal` | DAG build (networkx), cycle detection, topo sort, SEM execution, interventions. |
| `engine.failure` | MCAR/MAR/MNAR, noise, drift, covariate shift, leakage. |
| `engine.difficulty` | Probe models + adaptive calibration loop. |
| `engine.export` | Format conversion, splits, metadata, checksums. |
| `engine.pipeline` | Orchestrates the 9 canonical stages; emits progress events. |
| `engine.plugins` | Registry/loader; injects plugin-contributed capabilities into the above. |

### 3.5 Plugin Layer (`plugins/`)
- Runtime registry populated from (a) Python entry points (`datadoom.plugins`) and (b) a local plugins directory.
- Plugin types: Distribution, StructuralFn, FailureMode, Exporter, Template, ProbeModel.
- Each plugin declares a JSON-schema fragment so the **web UI renders its config automatically**.
- Detail: `09_Plugin_System.md`.

### 3.6 Storage (`store/`)
- **Metadata store:** SQLite by default (file in the DataDoom home dir); Postgres optional (team mode). Accessed via SQLAlchemy + Alembic migrations.
- **Artifact store:** local filesystem by default (`<home>/artifacts/<dataset>/<run>/...`); S3-compatible optional.
- Adapter interfaces (`MetadataStore`, `ArtifactStore`) keep the rest of the app storage-agnostic.
- Detail: `06_Internal_Data_Models.md`, `07_Database_Schema.md`.

---

## 4. The Generation Pipeline (canonical)

Implemented in `engine.pipeline`; the same code path for web, CLI, and library.

```
1. Intake & Validate    spec → schema/DAG/param validation (engine.spec + engine.causal)
2. Snapshot & Hash      freeze spec, compute spec_hash
3. Seed Resolution      derive RNG keys: sha256(spec_hash || seed || namespace)
4. Base Generation      sample root/independent features (engine.dist)
5. Causal / SEM         topo walk; v = f(parents(v)) + ε  (engine.causal)
6. Failure Injection*   apply transforms; preserve clean baseline (engine.failure)
7. Difficulty Calib.*   adaptive loop toward target band (engine.difficulty)
8. Compliance Report    KS / correlation / difficulty / failure reports (engine.dist + reports)
9. Packaging & Export   formats + splits + metadata + checksums (engine.export)
        (* optional stages, present only if the spec requests them)
```

Each stage publishes a progress event (`stage`, `status`, `pct`, `log line`) to the WebSocket hub. Stages are pure functions over an in-memory `RunContext` (frozen spec, RNG, intermediate frames), which makes the whole pipeline unit-testable and deterministic.

---

## 5. Determinism Architecture

The single most important architectural property. (Math in `05`, testing in `13`.)

- **Single RNG source:** `engine.rng.RNGFactory(spec_hash, seed)` yields independent `numpy.random.Generator(PCG64(key))` streams per namespace (per feature, per failure mode, per probe). Key = `sha256(spec_hash || seed || namespace)`.
- **Banned in the data path:** stdlib `random`, `uuid4`, `time`, `np.random.*` globals, set/dict iteration order dependence, unpinned thread counts.
- **Pinned execution path:** generation runs with `OMP_NUM_THREADS=1`/single-threaded BLAS and pinned numpy/scipy versions when the bitwise guarantee is in force.
- **Verification:** `datadoom verify spec.yaml --against artifact` recomputes and compares checksums; CI runs a cross-OS reproducibility matrix.

---

## 6. Deployment Topologies

### 6.1 Local (default, the product)
- One process: `datadoom` → uvicorn serving FastAPI + bundled SPA; in-process workers; SQLite + local FS.
- No network egress required. Data never leaves the machine.

### 6.2 Self-hosted single server (small team, opt-in)
- Same image, configured with Postgres + S3 + Redis (RQ workers) via env vars.
- Optional reverse proxy (Caddy/nginx) for TLS. Optional auth provider.

### 6.3 Docker
- `docker run -p 8000:8000 -v ./data:/data datadoom/datadoom` → local-equivalent with a mounted data volume.

> Kubernetes/multi-region are **not** part of core. If ever needed, the modular boundaries (engine vs jobs vs store) allow lifting the worker out — driven by metrics, not by design speculation.

---

## 7. Configuration

- Single config resolved from: defaults → config file (`<home>/config.toml`) → environment variables → CLI flags.
- Key settings: `storage.metadata` (sqlite|postgres), `storage.artifacts` (local|s3), `jobs.backend` (inproc|rq), `server.host/port`, `determinism.pinned` (bool), `telemetry.enabled` (default false).
- DataDoom home: `$DATADOOM_HOME` or platform default (`~/.datadoom`).

---

## 8. Observability (proportional, not enterprise)

- **Structured logging** (JSON option) via standard logging; per-run correlation id.
- **Local run metrics** captured into the `Report`/`GenerationRun` (durations per stage, peak RAM estimate, row throughput).
- Optional Prometheus endpoint **only** in self-hosted server mode (off by default).
- **No ELK/Grafana stack requirement.** No tracing infra in core.

---

## 9. Error Handling & Failure Semantics

- Validation errors (stage 1) are returned synchronously to the UI with field/node locators.
- Runtime errors fail the run, mark the failed stage, persist the traceback to the run log, and surface it in the tracker.
- Generation is **transactional at the artifact level**: a run either produces a complete, checksummed artifact set or none (no partial artifacts committed to the store).
- Cancellation is cooperative; partial work is discarded.

---

## 10. Architecture Invariants (enforced in review)

1. `engine/` imports **no** web/DB/framework code (keeps the library clean & testable).
2. All randomness goes through `engine.rng`.
3. The pipeline is the **only** way to produce an artifact (web, CLI, library all call it).
4. Storage is accessed only through `store/` adapters.
5. New capabilities that could be third-party (a distribution, a format) are added as **plugins**, not core branches, unless they're foundational.
6. Nothing in core requires a network connection.
