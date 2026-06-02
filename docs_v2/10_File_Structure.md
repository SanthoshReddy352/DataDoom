# 10 — File Structure (Repository Layout)

> A single **monorepo**. Python package `datadoom` (engine + server + CLI) with the React frontend built and bundled into the wheel. Obeys `00_README_Index.md`.

---

## 1. Why a Monorepo (not polyrepo)

The legacy plan used many repos (contracts, control-plane, compute-plane, ml-engines, infra, client). That suited a microservices org; it does not suit a modular monolith built by a small team + contributors. One repo means: one version, one CI, atomic cross-cutting changes, one place to contribute. The frontend lives in the same repo and is compiled into static assets shipped inside the Python wheel.

---

## 2. Top-Level Layout

```
datadoom/                          # repo root
├── pyproject.toml                 # package metadata, deps, entry points, build (hatchling)
├── README.md
├── LICENSE                        # Apache-2.0
├── CHANGELOG.md
├── CONTRIBUTING.md  CODE_OF_CONDUCT.md  SECURITY.md  GOVERNANCE.md
├── .github/                       # CI workflows, issue/PR templates
│   └── workflows/{ci.yml,release.yml,repro-matrix.yml}
├── docs/                          # docs site source (mkdocs-material) — mirrors docs_v2 content
├── examples/                      # example *.datadoom.yaml specs
│
├── src/
│   └── datadoom/                  # THE Python package (import datadoom)
│       ├── __init__.py            # public API: Spec, generate, __version__
│       ├── version.py
│       │
│       ├── engine/                # PURE engine — no web/DB/framework imports
│       │   ├── spec/              # parse, validate, canonicalize, hash (Pydantic models)
│       │   │   ├── models.py
│       │   │   ├── validate.py
│       │   │   └── hashing.py
│       │   ├── rng.py             # seeded RNG factory (the determinism invariant)
│       │   ├── dist/              # distributions + KS/compliance reporting
│       │   │   ├── base.py        # Distribution ABC
│       │   │   ├── builtins.py
│       │   │   └── compliance.py
│       │   ├── causal/            # DAG build, cycle detect, topo sort, SEM, interventions
│       │   │   ├── graph.py
│       │   │   ├── functions.py   # StructuralFn ABC + builtins
│       │   │   └── execute.py
│       │   ├── failure/           # MCAR/MAR/MNAR, noise, drift, shift, leakage
│       │   │   ├── base.py        # FailureMode ABC
│       │   │   └── builtins.py
│       │   ├── difficulty/        # probe models + adaptive loop
│       │   │   ├── probes.py      # ProbeModel ABC + logreg/tree
│       │   │   └── calibrate.py
│       │   ├── timeseries.py
│       │   ├── export/            # Exporter ABC + csv/parquet/json + metadata + checksums
│       │   ├── reports.py         # ReportBundle assembly
│       │   ├── pipeline.py        # the 9-stage orchestrator (RunContext)
│       │   └── errors.py
│       │
│       ├── plugins/               # plugin registry + loader + scaffolder
│       │   ├── registry.py
│       │   ├── loader.py          # entry points + local dir discovery
│       │   └── contracts.py       # re-exports ABCs for plugin authors (datadoom.plugin)
│       │
│       ├── store/                 # persistence adapters
│       │   ├── db.py              # SQLAlchemy engine/session (SQLite default / PG opt)
│       │   ├── models.py          # ORM models (mirror doc 06/07)
│       │   ├── repositories.py    # Dataset/Run/Artifact/Report repos
│       │   ├── artifacts.py       # ArtifactStore: local FS / S3 adapters
│       │   └── migrations/        # Alembic
│       │       ├── env.py
│       │       └── versions/0001_init.py
│       │
│       ├── jobs/                  # worker abstraction
│       │   ├── worker.py          # in-process async/thread pool (default)
│       │   ├── rq_backend.py      # optional Redis/RQ backend (team mode)
│       │   └── progress.py        # ProgressEmitter -> WS hub
│       │
│       ├── api/                   # FastAPI app
│       │   ├── app.py             # app factory, static SPA mount, OpenAPI
│       │   ├── deps.py            # auth (no-op local / real team), DB session
│       │   ├── ws.py              # WebSocket hub + SSE fallback
│       │   ├── schemas.py         # request/response Pydantic models
│       │   └── routes/{datasets.py,specs.py,runs.py,artifacts.py,
│       │              reports.py,templates.py,plugins.py,meta.py}
│       │
│       ├── cli/                   # Typer-based CLI (launcher + automation)
│       │   └── main.py            # datadoom [run|validate|verify|plugins|gc|...]
│       │
│       ├── templates/             # built-in domain templates (*.datadoom.yaml + meta)
│       ├── config.py              # layered config (defaults/file/env/flags)
│       └── webdist/               # ← compiled frontend assets, bundled into the wheel
│
├── frontend/                      # React + TS source (NOT shipped as source in the wheel)
│   ├── package.json  vite.config.ts  tsconfig.json  tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx  App.tsx
│       ├── api/                   # generated client from /api/openapi.json + hooks
│       ├── store/                 # Zustand stores
│       ├── pages/{Dashboard,Canvas,Results,Templates,Plugins,Settings}.tsx
│       ├── components/
│       │   ├── schema/            # table/schema builder
│       │   ├── graph/             # React Flow causal canvas
│       │   ├── inspector/         # contextual right panel
│       │   ├── failure/           # injection configurator + live diff
│       │   ├── tracker/           # live generation tracker (WS)
│       │   └── reports/           # charts, correlation heatmap, compliance
│       └── lib/                   # ws client, schema-fragment renderer (plugin UI)
│
└── tests/
    ├── unit/                      # per-module engine tests
    ├── determinism/               # repro tests (same seed -> same checksum)
    ├── plugin_contract/           # plugin determinism/interface tests
    ├── api/                       # FastAPI route tests
    ├── e2e/                       # spec -> generate -> artifact end-to-end
    └── golden/                    # golden specs + expected checksums per OS/py
```

---

## 3. Build & Packaging Flow

1. `cd frontend && npm ci && npm run build` → emits static assets.
2. Build step copies `frontend/dist/*` → `src/datadoom/webdist/`.
3. `python -m build` (hatchling) produces a wheel that **includes** `webdist/` as package data.
4. `pip install datadoom` → `datadoom` serves the SPA from `webdist/` — no Node required by end users.

CI enforces that `webdist/` is built from the current `frontend/` (no stale bundles shipped).

---

## 4. Module Dependency Rules (enforced in review / import-linter)

```
cli  ───▶ api ───▶ jobs ───▶ engine ◀─── plugins
                     │         ▲
                     └─▶ store │ (engine never imports store/api/jobs)
```

- `engine/` imports **nothing** from `api/`, `store/`, `jobs/`, `cli/`. It is a clean, installable library.
- `store/` knows the DB; nothing in `engine/` touches the DB.
- `api/` and `cli/` are thin; the real work is `engine.pipeline` driven by `jobs`.
- `plugins/` provides ABCs (`datadoom.plugin`) that `engine` consumes via the registry; plugins depend only on those ABCs.

A CI lint (e.g. `import-linter`) fails the build if these layers are violated — protecting the architecture from the "monolith temptation" drift.

---

## 5. Key Entry Points (`pyproject.toml`)

```toml
[project.scripts]
datadoom = "datadoom.cli.main:app"

[project.entry-points."datadoom.plugins"]   # core built-ins registered here too
# third-party plugins add their own under this group

[tool.hatch.build.targets.wheel]
packages = ["src/datadoom"]
artifacts = ["src/datadoom/webdist/**"]
```

---

## 6. What's intentionally absent

- No `hackforge-contracts/`, `-control-plane/`, `-compute-plane/`, `-infra/` repos.
- No `.proto`, no Avro schemas, no Kafka config, no Helm/Terraform in core (`infra/` for a self-host deployment may live in `deploy/` as optional examples, not as a requirement).
- No separate frontend deployment — it's bundled.
