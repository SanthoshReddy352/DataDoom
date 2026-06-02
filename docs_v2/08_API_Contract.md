# 08 — API Contract (REST + WebSocket)

> Single FastAPI service. **OpenAPI is auto-generated** from Pydantic models — this doc is the human-readable contract, not a hand-maintained spec. No gRPC/Protobuf, no Kafka. Obeys `00_README_Index.md`.

---

## 1. Conventions

- Base path: `/api`. SPA served at `/`. OpenAPI JSON at `/api/openapi.json`; Swagger UI at `/api/docs`.
- **Auth:** none in local mode (a no-op dependency). Team mode injects a real auth dependency (bearer token) without changing route shapes.
- **IDs:** UUID strings. **Times:** ISO-8601 UTC. **Bodies:** JSON (spec uploads also accept `text/yaml`).
- **Errors:** consistent envelope:
  ```json
  { "error": { "code": "validation_error",
               "message": "std must be > 0",
               "locator": "features.age.params.std" } }
  ```
- **Async generation:** creating a run returns immediately with `202` and a `run_id`; progress streams over WebSocket.
- **Idempotency:** `POST /datasets/{id}/runs` accepts an `Idempotency-Key` header; repeated keys return the existing run.

---

## 2. Resource Overview

| Resource | Routes |
|---|---|
| Specs | validate, hash, estimate |
| Datasets | CRUD + list |
| Specs-of-dataset | create version, get, history |
| Runs | create (generate), get, list, cancel |
| Artifacts | list, download |
| Reports | get |
| Failure variant | create injected variant from a run |
| Templates | list, get |
| Plugins | list |
| Meta | health, version |

---

## 3. Spec Endpoints (stateless helpers)

```
POST /api/specs/validate
  body: spec (JSON or YAML)
  200:  { valid: true, spec_hash, warnings: [] }
  422:  { error: { code: "validation_error", message, locator } }

POST /api/specs/hash
  body: spec
  200:  { spec_hash }

POST /api/specs/estimate
  body: spec
  200:  { estimated_runtime_seconds, estimated_ram_mb, estimated_size_bytes,
          features, edges, gpu_required: false }      # see doc 12
```

---

## 4. Dataset Endpoints

```
GET  /api/datasets
  query: status?, q?, limit?, offset?
  200:  { items: [DatasetSummary], total }

POST /api/datasets
  body: { name, description?, spec? }     # spec optional; blank creates an empty draft
  201:  Dataset

GET  /api/datasets/{dataset_id}            -> Dataset (incl. current_spec, latest_run summary)
PATCH /api/datasets/{dataset_id}           body: { name?, description? } -> Dataset
DELETE /api/datasets/{dataset_id}          204  (cascades; removes artifact dir)

POST /api/datasets/{dataset_id}/duplicate  201 Dataset   (clones current spec into a new dataset)
```

`Dataset` shape:
```json
{ "dataset_id":"…","name":"…","description":"…","status":"draft",
  "current_spec": { "spec_id":"…","spec_hash":"…","version":3,"body":{…} },
  "latest_run": { "run_id":"…","status":"completed","compliance_score":0.98 } | null,
  "created_at":"…","updated_at":"…" }
```

---

## 5. Spec Versioning Endpoints

```
PUT  /api/datasets/{dataset_id}/spec        # save edits -> NEW immutable snapshot
  body: spec
  200:  { spec_id, spec_hash, version }      # creates version N+1, repoints current_spec

GET  /api/datasets/{dataset_id}/spec         -> current spec (body + hash + version)
GET  /api/datasets/{dataset_id}/spec/history -> [ { spec_id, version, spec_hash, created_at } ]
GET  /api/datasets/{dataset_id}/spec/{version} -> spec snapshot
```

> Editing never mutates a spec row (immutability invariant, `06 §5`).

---

## 6. Generation (Run) Endpoints

```
POST /api/datasets/{dataset_id}/runs
  headers: Idempotency-Key?
  body: { seed?: int }                       # seed override; else spec seed or generated
  202:  { run_id, status: "queued", ws: "/api/ws/runs/{run_id}" }

GET  /api/runs/{run_id}                       -> GenerationRun (status, stage, progress_pct, error?, metrics)
GET  /api/datasets/{dataset_id}/runs          -> [GenerationRun summaries]
POST /api/runs/{run_id}/cancel                -> { status: "cancelled" }  (cooperative)
```

`GenerationRun` shape:
```json
{ "run_id":"…","dataset_id":"…","spec_id":"…","seed":42,
  "status":"running","stage":"causal","progress_pct":55,
  "error":null,"metrics":{…},"started_at":"…","finished_at":null }
```

---

## 7. WebSocket — Live Progress

```
WS /api/ws/runs/{run_id}
```
Server → client event stream (one JSON object per message):
```json
{ "type":"stage",    "stage":"base_generation", "status":"running", "pct":40 }
{ "type":"log",      "level":"info", "message":"generated 50000 rows for 'age'" }
{ "type":"stage",    "stage":"base_generation", "status":"done", "pct":50 }
{ "type":"completed","run_id":"…","compliance_score":0.98,"report_id":"…" }
{ "type":"failed",   "stage":"causal","message":"…","traceback":"…" }
```
- Client may send `{ "type":"cancel" }`.
- **SSE fallback:** `GET /api/runs/{run_id}/events` streams the same events as `text/event-stream` for environments without WS.
- Late subscribers receive a replay of stage events so far, then live updates.

Canonical stages (match `00`/`03`): `intake`, `snapshot`, `seed`, `base_generation`, `causal`, `failure_injection`, `difficulty`, `compliance`, `packaging`.

---

## 8. Artifacts & Reports

```
GET  /api/runs/{run_id}/artifacts            -> [Artifact]   (version, split, format, size, checksum)
GET  /api/artifacts/{artifact_id}/download   -> file stream (Content-Disposition; checksum header)
GET  /api/runs/{run_id}/report               -> Report (all sections)
GET  /api/runs/{run_id}/preview              -> { columns, rows: [...] }  query: version, split, limit
GET  /api/runs/{run_id}/bundle               -> zip (artifacts + metadata.json + report.html + spec)
```

---

## 9. Failure Variant

```
POST /api/runs/{run_id}/inject
  body: { failures: [ Failure, ... ] }       # see 04 §7
  202:  { run_id, ws: "…" }                   # creates a new run producing the injected variant
                                              # (clean baseline reused from source run)
```

---

## 10. Templates & Plugins

```
GET /api/templates                 -> [ { id, name, domain, description, tags } ]
GET /api/templates/{id}            -> { spec, problem_statement, metric, preview_graph }
POST /api/templates/{id}/use       body: { name } -> 201 Dataset

GET /api/plugins                   -> [ { name, kind, version, schema, enabled } ]
```
The `schema` fragment lets the UI render plugin-contributed config natively (see `09_Plugin_System.md`).

---

## 11. Meta

```
GET /api/health    -> { status: "ok" }
GET /api/version   -> { version, datadoom_version, python, platform }
```

---

## 12. Status Codes

| Code | Meaning |
|---|---|
| 200 | OK |
| 201 | Created (dataset, template-use) |
| 202 | Accepted (run queued) |
| 204 | Deleted |
| 400 | Malformed request |
| 404 | Unknown resource |
| 409 | Conflict (duplicate name; idempotency replay returns the existing run with 200) |
| 422 | Spec validation error (with `locator`) |
| 500 | Unexpected server error (traceback logged, not leaked in prod mode) |

---

## 13. Versioning of the API itself

- API surface versioned by path prefix when a breaking change is unavoidable (`/api/v2/...`); v1 stays at `/api/...` for compatibility.
- The **spec format** version (`datadoom_version`) is independent of the HTTP API version.
- OpenAPI is the source of truth for exact schemas; this document is the intent.
