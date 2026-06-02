# 11 — Language & Technology Specification

> The exact stack, per area, with rationale and the constraints each choice must honor. Obeys `00_README_Index.md`. This replaces the legacy "maximum optimization / enterprise" stack (Go + Kafka + gRPC + Terraform), which was wrong for a local-first OSS tool.

---

## 1. Guiding Constraints

Every technology choice is judged against:
1. **Installability** — must `pip install` cleanly on Win/macOS/Linux, Python 3.11+, no system services required.
2. **Determinism** — must not introduce nondeterminism into the data path.
3. **Single-language core** — minimize languages so contributors can be productive everywhere. (Python backend, TypeScript frontend — that's it.)
4. **Dependency hygiene** — few, well-maintained, permissively-licensed dependencies; heavy/optional ones gated as extras.

---

## 2. Language Mapping

| Area | Language | Version |
|---|---|---|
| Engine, server, CLI | **Python** | 3.11+ |
| Frontend | **TypeScript / React** | TS 5.x, React 18 |
| Build glue / CI | Bash + GitHub Actions YAML | — |
| Docs | Markdown (mkdocs-material) | — |
| Specs (user-facing) | YAML / JSON | spec `datadoom_version: 1` |

No Go. No gRPC/Protobuf. No Kafka/Avro. No Terraform/Helm in core.

---

## 3. Backend Stack

| Concern | Choice | Rationale | Determinism constraint |
|---|---|---|---|
| Web framework | **FastAPI** | async, Pydantic-native, auto OpenAPI, great DX | none (control plane) |
| Validation/models | **Pydantic v2** | spec validation + API schemas in one system | strict types prevent silent coercion |
| ASGI server | **uvicorn** | simple, fast, bundled launch | — |
| Numerics | **NumPy** | the sampling core | **pin version**; `PCG64` generators only |
| Stats | **SciPy** | distributions, KS test | pin version; use `Generator`, not legacy `RandomState` |
| DataFrames | **pandas** (+ **pyarrow** for Parquet) | ubiquitous, Parquet/CSV IO | deterministic IO; stable column order |
| Graphs | **networkx** | DAG build, cycle detection, topo sort | deterministic node/edge ordering (sort before iterate) |
| ML probes | **scikit-learn** | logreg/tree baselines for difficulty | seed every estimator via injected rng |
| ORM | **SQLAlchemy 2.x** | SQLite+Postgres portability | — |
| Migrations | **Alembic** | versioned schema, auto-upgrade on launch | — |
| Jobs (default) | **in-process** asyncio + `concurrent.futures` pool | zero infra | single-threaded BLAS on pinned path |
| Jobs (team, optional) | **RQ** + Redis | simple, Pythonic queue | same pipeline code |
| CLI | **Typer** | ergonomic, type-hint based | — |
| Config | **pydantic-settings** + TOML | layered config | — |
| Hashing | `hashlib` (SHA256) | spec_hash, checksums, RNG keys | stable canonical serialization |

### 3.1 Optional extras (gated, not core deps)
```
datadoom[postgres]   -> psycopg
datadoom[redis]      -> rq, redis
datadoom[s3]         -> boto3 / s3fs
datadoom[polars]     -> polars adapter
```
Heavy/optional capabilities (e.g. GPU/GAN generators) are **separate plugin packages**, never core dependencies (`09 §8`).

---

## 4. Frontend Stack

| Concern | Choice | Rationale |
|---|---|---|
| Framework | **React 18 + TypeScript** | mainstream, contributor-friendly |
| Bundler | **Vite** | fast dev, simple static build → bundled into wheel |
| Causal graph | **React Flow** | node/edge canvas, the graph builder |
| Styling | **Tailwind CSS** | fast, consistent, dark-mode default |
| Local/UI state | **Zustand** | minimal boilerplate |
| Server state | **TanStack Query** | caching, async status for REST |
| Realtime | native **WebSocket** (SSE fallback) | live generation tracker |
| Charts | **visx** or **Recharts** | histograms, correlation heatmap |
| Forms from schema | small **JSON-schema → form** renderer | renders plugin `param_schema` automatically |
| API client | generated from `/api/openapi.json` | types stay in sync with backend |

No server-side rendering, no Next.js — it's a static SPA served by FastAPI.

---

## 5. Why Python-Only Core (vs. the legacy Go split)

The legacy design split a Go "control plane" from a Python "compute plane" over gRPC. For DataDoom that split is pure cost:
- "Create experiment" and "generate data" are the **same logical action** at our scale — a network hop and a second language buy nothing.
- The valuable code (sampling, SEM, failure injection, probes) is **inherently Python** (NumPy/SciPy/sklearn). Keeping the control plane in Python means one language, one toolchain, one debugging story, and contributors who can work across the whole stack.
- Performance: tabular generation is NumPy-vectorized C under the hood; Python orchestration overhead is negligible relative to the array math.

If a genuine hotspot ever appears, the fix is a targeted native extension (Cython/Rust via PyO3) **inside** the engine module — not a second service.

---

## 6. Determinism-Sensitive Technology Rules

These are mandatory (see `05`, `13`):
1. RNG = `numpy.random.Generator(PCG64(key))` only; **never** legacy `np.random.*` globals or Python `random`.
2. Pinned path runs with single-threaded BLAS (`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`).
3. NumPy/SciPy/scikit-learn versions are **pinned** (lower+upper bounds) for releases; the repro matrix tests across the pinned set.
4. Any iteration over `dict`/`set`/graph nodes that feeds sampling must be **sorted** first.
5. Parquet/CSV writers configured for stable column order and no embedded timestamps that would change checksums.

---

## 7. Tooling & Quality Gates

| Purpose | Tool |
|---|---|
| Lint/format (Py) | **Ruff** (lint + format) |
| Type check (Py) | **mypy** (strict on `engine/`) |
| Architecture lint | **import-linter** (enforces `10 §4` layering) |
| Tests | **pytest** (+ coverage) |
| Lint/format (TS) | **ESLint + Prettier** |
| Type check (TS) | `tsc --noEmit` |
| Pre-commit | **pre-commit** hooks for the above |
| CI | **GitHub Actions** (lint, type, test, repro matrix, build wheel) |

---

## 8. Platform Support Matrix

| | Windows | macOS | Linux |
|---|---|---|---|
| Python | 3.11, 3.12 | 3.11, 3.12 | 3.11, 3.12 |
| Install | `pip`/`pipx` | `pip`/`pipx`/brew(pipx) | `pip`/`pipx` |
| Bitwise repro tested | ✅ CI | ✅ CI | ✅ CI |

Docker image provided for a uniform self-host/runtime environment.

---

## 9. Dependency Licensing

Core dependencies must be permissively licensed (BSD/MIT/Apache) to keep DataDoom cleanly **Apache-2.0**. Copyleft (GPL/AGPL) dependencies are not allowed in the core; if a plugin needs one, the plugin carries that license obligation, not the core.
