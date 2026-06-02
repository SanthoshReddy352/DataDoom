# 07 — Database Schema

> **SQLite by default** (zero-config, local-first), **PostgreSQL optional** for team mode. SQLAlchemy models + Alembic migrations. Entities defined in `06_Internal_Data_Models.md`. Obeys `00_README_Index.md`.

---

## 1. Principles

1. **SQLite is the default and must work with zero setup.** A single file at `$DATADOOM_HOME/datadoom.db`.
2. **Portable DDL.** Use types/constructs that work on both SQLite and Postgres; avoid Postgres-only features in core (no RLS, no hash partitioning — those were SaaS artifacts).
3. **JSON columns** store spec bodies and report sections (SQLite `JSON1`, Postgres `JSONB`).
4. **UUIDs as TEXT** (portable) — 36-char string PKs.
5. **Timestamps as TEXT (ISO-8601 UTC)** on SQLite / `TIMESTAMPTZ` on Postgres; the ORM abstracts this.
6. **Migrations via Alembic** from day one, so the on-disk DB upgrades cleanly across releases.

---

## 2. Core Tables (portable DDL — SQLite dialect shown)

```sql
-- datasets ------------------------------------------------------------
CREATE TABLE datasets (
  dataset_id      TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  description     TEXT,
  current_spec_id TEXT REFERENCES specs(spec_id),
  status          TEXT NOT NULL DEFAULT 'draft',   -- draft|running|completed|failed
  latest_run_id   TEXT,                              -- FK added after runs exists
  owner_id        TEXT,                              -- NULL in local mode (team mode FK)
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);
CREATE UNIQUE INDEX ux_datasets_owner_name ON datasets(owner_id, name);
CREATE INDEX ix_datasets_status ON datasets(status);

-- specs (immutable snapshots) ----------------------------------------
CREATE TABLE specs (
  spec_id          TEXT PRIMARY KEY,
  dataset_id       TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
  spec_hash        TEXT NOT NULL,                    -- sha256(canonical, seed excluded)
  body             TEXT NOT NULL,                    -- canonical JSON (JSONB on PG)
  datadoom_version TEXT NOT NULL,
  version          INTEGER NOT NULL,                 -- monotonic per dataset
  created_at       TEXT NOT NULL
);
CREATE INDEX ix_specs_dataset ON specs(dataset_id);
CREATE INDEX ix_specs_hash    ON specs(spec_hash);
CREATE UNIQUE INDEX ux_specs_dataset_version ON specs(dataset_id, version);

-- generation_runs ----------------------------------------------------
CREATE TABLE generation_runs (
  run_id       TEXT PRIMARY KEY,
  dataset_id   TEXT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
  spec_id      TEXT NOT NULL REFERENCES specs(spec_id),
  seed         INTEGER NOT NULL,
  status       TEXT NOT NULL DEFAULT 'queued',       -- queued|running|completed|failed|cancelled
  stage        TEXT,
  progress_pct INTEGER NOT NULL DEFAULT 0,
  error        TEXT,                                  -- JSON {message,traceback,stage}
  metrics      TEXT,                                  -- JSON per-stage durations etc.
  started_at   TEXT,
  finished_at  TEXT,
  created_at   TEXT NOT NULL
);
CREATE INDEX ix_runs_dataset ON generation_runs(dataset_id);
CREATE INDEX ix_runs_status  ON generation_runs(status);
CREATE INDEX ix_runs_repro   ON generation_runs(spec_id, seed);

-- artifacts ----------------------------------------------------------
CREATE TABLE artifacts (
  artifact_id     TEXT PRIMARY KEY,
  run_id          TEXT NOT NULL REFERENCES generation_runs(run_id) ON DELETE CASCADE,
  version         TEXT NOT NULL,                      -- clean|injected
  split           TEXT,                               -- train|test|hidden_test|full
  format          TEXT NOT NULL,                      -- csv|parquet|json|<plugin>
  storage_uri     TEXT NOT NULL,
  checksum_sha256 TEXT NOT NULL,
  size_bytes      INTEGER NOT NULL,
  created_at      TEXT NOT NULL
);
CREATE INDEX ix_artifacts_run ON artifacts(run_id);

-- reports ------------------------------------------------------------
CREATE TABLE reports (
  report_id        TEXT PRIMARY KEY,
  run_id           TEXT NOT NULL UNIQUE REFERENCES generation_runs(run_id) ON DELETE CASCADE,
  compliance_score REAL,
  distribution     TEXT,   -- JSON
  correlation      TEXT,   -- JSON
  causal_truth     TEXT,   -- JSON
  difficulty       TEXT,   -- JSON
  failures         TEXT,   -- JSON
  determinism      TEXT,   -- JSON
  created_at       TEXT NOT NULL
);

-- plugins (optional cache of runtime registry) -----------------------
CREATE TABLE plugins (
  name     TEXT PRIMARY KEY,
  kind     TEXT NOT NULL,    -- distribution|structural_fn|failure_mode|exporter|template|probe_model
  version  TEXT,
  schema   TEXT,             -- JSON UI-render fragment
  enabled  INTEGER NOT NULL DEFAULT 1
);
```

### Team-mode-only table (created only when team mode is enabled)
```sql
CREATE TABLE users (
  user_id       TEXT PRIMARY KEY,
  email         TEXT NOT NULL UNIQUE,
  role          TEXT NOT NULL DEFAULT 'member',  -- admin|member|viewer
  auth_provider TEXT,
  created_at    TEXT NOT NULL
);
-- then: datasets.owner_id REFERENCES users(user_id)
```

---

## 3. Indexing Rationale

| Index | Query it serves |
|---|---|
| `ix_datasets_status` | dashboard filtering by status |
| `ux_datasets_owner_name` | unique dataset names per owner |
| `ix_specs_dataset`, `ux_specs_dataset_version` | version history; latest version lookup |
| `ix_specs_hash` | "have we generated this exact spec before?" / cache reuse |
| `ix_runs_repro (spec_id, seed)` | reproducibility lookup; "Regenerate (same seed)" |
| `ix_runs_status` | dashboard "running/failed" views |
| `ix_artifacts_run` | results page artifact listing |

Indexes are deliberately modest — local datasets number in the hundreds/thousands, not millions. No partitioning (a SaaS-scale artifact, explicitly out of scope).

---

## 4. SQLite ↔ Postgres Differences (handled by ORM)

| Concern | SQLite (default) | Postgres (team) |
|---|---|---|
| JSON | `TEXT` + `JSON1` functions | `JSONB` |
| UUID | `TEXT` | `TEXT` (or native `uuid`) |
| Timestamp | `TEXT` ISO-8601 UTC | `TIMESTAMPTZ` |
| Concurrency | WAL mode; single-writer | full MVCC |
| FK enforcement | `PRAGMA foreign_keys=ON` | default on |

SQLite pragmas set on connect: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`.

---

## 5. Migrations

- **Alembic** with a linear migration history checked into the repo.
- `0001_init` creates the core tables above (no `users`).
- Team-mode migrations are additive and gated (applied only when team mode configured).
- On `datadoom` startup, run `alembic upgrade head` against the local DB automatically (idempotent) so users never run migrations manually.

---

## 6. Data Lifecycle & Retention

- **No automatic deletion** in local mode (it's the user's disk; never delete their data silently).
- Deleting a Dataset cascades to its Specs, Runs, Artifacts, Reports (DB rows) and removes its artifact directory (with confirmation in the UI).
- "Regenerate (same seed)" creates a **new** run/artifacts; prior runs are retained for comparison unless pruned by the user.
- Optional `datadoom gc` command prunes orphaned artifact files not referenced by any Artifact row.

---

## 7. What's intentionally NOT here

- **Row-Level Security / multi-tenant policies** — not needed locally; team mode uses app-level `owner_id` scoping, not DB RLS, in core.
- **Hash partitioning / sharding** — SaaS-scale concern, out of scope.
- **Billing/quota/usage tables** — not part of the OSS core.
- **Audit-log tables** — local mode logs to files; team mode may add an append-only `audit` table later (deferred).
