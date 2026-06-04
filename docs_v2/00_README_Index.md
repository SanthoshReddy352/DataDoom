# DataDoom — Documentation Index (v2, Open Source)

> **DataDoom** is an open-source, local-first engine for **controllable, reproducible synthetic data**.
> You design a dataset — distributions, causal relationships, difficulty, failure modes — in a web Canvas, and regenerate it identically, forever, from a single spec file.
>
> **Primary surface:** the **web app**. The CLI is a launcher/automation surface, not the point of contact.
> **Distribution model:** `pip install datadoom` → `datadoom` → browser opens. Local-first, zero-config, works offline.

This `docs_v2/` set is the **authoritative design** for DataDoom. It supersedes the legacy `Docs/` set (HackForge AI), which described a contradictory SaaS/microservices product. See `../Docs/DataDoom_Critical_Analysis_and_Recommended_Architecture.md` for why the design changed.

---

## How to read these docs

**If you want the "what" (product):** 01 → 02
**If you want the "how" (engineering):** 03 → 04 → 05 → 06 → 07 → 08 → 09
**If you want to build it:** 10 → 11 → 16 → 17 → 18
**If you want to trust/contribute to it:** 12 → 13 → 14 → 15 → 19

---

## Document map

| # | Document | Purpose | Replaces in legacy `Docs/` |
|---|---|---|---|
| 00 | **README_Index** (this file) | Map + locked global decisions | — |
| 01 | **PRD** | Product requirements, scope, personas, success metrics | `PRD.md` |
| 02 | **User_Flow_Guide** | Website UX, screens, micro-interactions | `HackForge AI User Flow Guide.md` |
| 03 | **Technical_Architecture** | Modular-monolith architecture, pipeline, deployment | `Techincal_Architecture.md` |
| 04 | **DataDoom_Spec_Reference** | The spec file format — the heart of the project | *(new)* |
| 05 | **Mathematical_Algorithm_Definitions** | Honest math: determinism, distributions, SEM, failures, difficulty | `Mathematical_Algorithm_Definitions.md` |
| 06 | **Internal_Data_Models** | Domain entities / Pydantic models | `Internal_Data_Models.md` |
| 07 | **Database_Schema** | SQLite default schema (+ optional Postgres) | `DB_Schema&Indexing.md` |
| 08 | **API_Contract** | REST + WebSocket + OpenAPI outline | `Microservices_API_Contract.md`, `Open_API_Scheme.md` |
| 09 | **Plugin_System** | Extension API — the community growth engine | *(new)* |
| 10 | **File_Structure** | Monorepo layout | `File_Structure.md` |
| 11 | **Language_Technology_Specification** | Stack per module + rationale | `Language_Specification.md` |
| 12 | **Resource_Estimation_Model** | Local runtime/RAM/file-size estimation | `Cost_Estimation_Model.md` |
| 13 | **Testing_and_Reproducibility_Strategy** | The reproducibility guarantee + test matrix | *(new)* |
| 14 | **Security_and_Privacy** | Local-first threat model, honest posture | `Security_Compliance.md` |
| 15 | **Open_Source_Governance** | License, contributing, governance, releases | *(new)* |
| 16 | **Engineering_Roadmap** | Capability-ordered phases | `Engineering_Roadmap.md` |
| 17 | **Implementation_Guide** | Step-by-step build sequence | `Implementation_Guide.md` |
| 18 | **AI_Accelerated_Engineering_Playbook** | How to build this with an AI agent safely | `HackForge AI_ AI-Accelerated Engineering Playbook.md` |
| 19 | **Learning_Guide** | Onboarding/learning path for new contributors | `Learning_Guide.md` |
| 20 | **YAML_Authoring_Guide** | Beginner-friendly, end-to-end guide to writing a spec by hand | `20_YAML_Authoring_Guide.md` |
| 21 | **LLM_Spec_Authoring_Reference** | Terse authoring contract optimized for AI/agent spec generation | `21_LLM_Spec_Authoring_Reference.md` |
| 22 | **Release_and_Publishing_Runbook** | Operator steps to publish docs/PyPI/Docker/releases (Pages, OIDC, provenance) | `22_Release_and_Publishing_Runbook.md` |
| 23 | **Pushing_Changes_DCO_and_Versioning** | How to push to GitHub, sign off commits (DCO), bump versions, cut a release | `23_Pushing_Changes_DCO_and_Versioning.md` |

### Legacy docs intentionally **dropped** (SaaS/microservices-only, not part of DataDoom v2 core)
`Advanced_System_Documents.md`, `Kafka_Event_Contract.md`, `Portobuff_Definitions.md`, `Mulit_Tenant_Isolation.md`, `SLA_SLO_RateLimiting.md`, `Infrastructure_Summary.md` — their still-relevant fragments are folded into 03, 06, 07, 14, 15. Kafka, gRPC/Protobuf, multi-tenant RLS, SLA tiers, and dedicated infra are **out of the core** (may return later as optional editions/plugins).

---

## 🔒 Locked Global Design Decisions

Every document in this set MUST agree with the decisions below. If a doc contradicts this list, this list wins. Changing any of these is a project-level decision, not a per-doc one.

### Identity
- **Product name:** DataDoom
- **Package name (PyPI):** `datadoom` — verified **available** on PyPI/TestPyPI (2026-06-01); reserve it before 0.1.
- **CLI command:** `datadoom`
- **Spec file extension:** `*.datadoom.yaml` (YAML primary; JSON accepted)
- **GitHub home:** personal repo `github.com/SanthoshReddy352/datadoom` (currently named `Hack-Forge` → rename to `datadoom` before publishing). The org handle `datadoom` is taken by an inactive account; not used.
- **License:** **Apache-2.0** (default choice; permissive + patent grant). Contributions via **DCO** sign-off.

### Product shape
- **Primary surface:** local-first **web app** (Canvas). CLI = launcher + headless automation. Python library = embedding.
- **Single source of truth:** the **DataDoom Spec** file. UI edits the spec; engine executes the spec; git versions the spec.
- **Spec identity:** `spec_hash = sha256(canonical_json(spec without seed))`. An artifact is uniquely identified by `(spec_hash, seed)`.

### Tech stack (core)
- **Backend / engine:** Python **3.11+**, **FastAPI**, Pydantic v2.
- **Data libs:** NumPy, SciPy, pandas (Parquet via pyarrow), **networkx** (DAG), scikit-learn (probe models).
- **Jobs:** in-process async/thread worker pool **by default**; optional **RQ (Redis)** for team mode.
- **Realtime:** WebSocket (SSE fallback) streamed from the worker.
- **Storage (default):** **SQLite** (metadata) + **local filesystem** (artifacts). Zero external services.
- **Storage (optional team mode):** PostgreSQL + S3-compatible object storage.
- **Frontend:** React + TypeScript + **Vite**, **React Flow** (causal graph), Tailwind CSS, **Zustand** (state), TanStack Query (server state).
- **API contract:** OpenAPI **auto-generated** from FastAPI/Pydantic (not hand-written, no Protobuf).
- **Packaging:** PyPI wheel, `pipx`, Docker image; frontend bundled into the wheel.

### Engine invariants (non-negotiable)
1. **Determinism:** all randomness flows through the seeded RNG wrapper. No stdlib `random`, `uuid4`, `time`, or `np.random.*` global calls in the data path. RNG = `numpy.random.Generator(PCG64(derived_key))`, `derived_key = sha256(spec_hash || seed || namespace)`.
2. **Reproducibility guarantee scope:** `(spec_hash, seed) → bitwise-identical artifact` on the **pinned path** = single-threaded (`OMP_NUM_THREADS=1`), pinned library versions, CPU. We do **not** claim bitwise determinism across threads/GPUs/heterogeneous nodes.
3. **Honest statistics:** sample correctly from the requested distribution and **report** empirical fit (KS stat + p-value, compliance score). **No "KS auto-correction loop"** that refits parameters to the sample. Fitting to a *user-supplied real reference sample* is a separate opt-in feature.
4. **Difficulty = empirical target:** regenerate/adjust noise & imbalance until a held-out **probe model** lands in the requested metric band; report achieved metric. Named tiers map to validated bands.
5. **Immutable config snapshot:** a run executes against a frozen spec snapshot; editing creates a new draft/version.

### Canonical generation pipeline (referenced by all docs)
```
1. Intake & Validate        spec → schema/DAG/param validation
2. Snapshot & Hash          freeze spec, compute spec_hash
3. Seed Resolution          derive deterministic seed / RNG keys
4. Base Feature Generation  sample independent (root) features
5. Causal / SEM Execution   topological walk applying structural equations
6. Failure Injection        optional corruption transforms (clean baseline preserved)
7. Difficulty Calibration   optional adaptive loop toward target band
8. Compliance Reporting     KS / correlation / difficulty / failure reports
9. Packaging & Export       format conversion + splits + metadata + checksums
```

### Canonical domain entities (referenced by all docs)
`Dataset` (user-facing managed item) · `Spec` (immutable config snapshot + hash) · `GenerationRun` (one execution: status/seed/progress/logs) · `Artifact` (output file: uri/format/split/checksum/size) · `Report` (compliance/correlation/difficulty/failure sections) · `User` (**team mode only**; local mode = single implicit user) · `Plugin` (runtime-registered extension).

### Scope fences
- **In (v1 core):** tabular + time-series; deterministic engine; distributions; causal DAG/SEM; failure injection; difficulty targeting; reports; export adapters; web Canvas; CLI; Python API; plugin system; templates; local-first install.
- **Deferred (opt-in, post-v1):** graph/network data; richer time-series; team/server mode (Postgres/accounts/sharing); hosted edition.
- **Out (core):** GAN/VAE image synthesis; multi-modal image/text; SaaS billing/quotas/SLA; multi-region infra; Kafka; gRPC/Protobuf; multi-tenant RLS; any non-deterministic data-path code.

---

*Last structural update: see git history. All docs in this folder share the decisions above.*
