# DataDoom — Manual Testing Guide

> This is the document **you** use to exercise the application by hand and see how
> it behaves. Each test says **what it checks**, **which files it exercises**, the
> **command to run**, and the **expected output**.
>
> Keep this file in sync with the code — update it whenever behavior changes or a
> new capability lands. Current coverage: **Phase 0 (deterministic core)**.
>
> **Last updated:** 2026-06-02

---

## 0. Setup (read once)

The project uses a **local virtual environment** in `.venv/` (Python 3.11, matching
CI). Create it once, then **activate it** at the start of each testing session so
`datadoom`, `pytest`, `ruff`, `mypy`, and `lint-imports` are all on your `PATH`.

### One-time: create the venv and install

In **PowerShell**, from the project root:

```powershell
cd "D:\Hack Forge"
python -m venv .venv                       # create .venv (Python 3.11)
.\.venv\Scripts\Activate.ps1               # activate it
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"          # install datadoom + dev tools (editable)
```

> If `python` on your PATH lacks `pip`/`venv`, create the venv with a full
> interpreter path once, e.g.
> `& "C:\Users\santh\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m venv .venv`,
> then activate as above — everything after activation uses the venv.

### Every session: activate

```powershell
cd "D:\Hack Forge"
.\.venv\Scripts\Activate.ps1
```

Your prompt should now be prefixed with `(.venv)`. Sanity check:

```powershell
python -c "import datadoom, sys; print(datadoom.__version__, 'on py', sys.version.split()[0])"
```

**Expected:** `0.1.0.dev0 on py 3.11.15`

> All commands below assume the venv is **activated**. If you'd rather not activate,
> prefix each command with `.\.venv\Scripts\` (e.g. `.\.venv\Scripts\pytest`).
> To leave the venv: `deactivate`.

---

## 1. Test catalogue

Tests are grouped:

- **Group A — Quality gates** (lint / architecture / types)
- **Group B — Automated test suite** (pytest, per area)
- **Group C — CLI behavior** (validate / run / verify by hand)
- **Group D — Determinism proof** (the headline guarantee)
- **Group E — Honest statistics** (observe, don't auto-correct)
- **Group F — Artifact inspection** (what the engine writes)
- **Group G — Correctness tests** (TH.1–TH.8, implemented)
- **Group H — Server & web (Phase 1)** (store / API / WebSocket, by hand)
- **Group I — Web Canvas (Phase 1)** (the browser app + theme toggling)
- **Group J — Causal engine (Phase 2)** (DAG/SEM + interventions + true graph)
- **Group K — End-to-end dataset audit** (generate → analyze the realized frame)
- **Group L — Web Graph view (Phase 2)** (React Flow causal editor + Results graph)

---

## Group A — Quality gates

### A1 — Lint (Ruff)
- **What it tests:** code style / common bugs across the package and tests.
- **Files under test:** `src/`, `tests/`.
- **Run:**
  ```powershell
  ruff check src tests
  ```
- **Expected:** `All checks passed!`

### A2 — Architecture boundaries (import-linter)
- **What it tests:** the engine stays framework-free and layering holds
  (`engine/` never imports `api`/`store`/`jobs`/`cli` or FastAPI/SQLAlchemy).
- **Files under test:** all of `src/datadoom/`; contracts in `pyproject.toml`
  (`[tool.importlinter]`).
- **Run:**
  ```powershell
  lint-imports
  ```
- **Expected:** ends with
  ```
  engine stays framework-free KEPT
  layered architecture KEPT
  store depends only on engine KEPT
  Contracts: 3 kept, 0 broken.
  ```

### A3 — Type check (mypy)
- **What it tests:** static types, strict-ish on `engine/`.
- **Files under test:** `src/datadoom/` (whole package).
- **Run:**
  ```powershell
  mypy
  ```
- **Expected:** `Success: no issues found in 56 source files`

---

## Group B — Automated test suite (pytest)

### B0 — Run everything
- **What it tests:** the entire suite (123 tests: Phase 0 engine + Phase 1
  store/api + Phase 2 causal engine + end-to-end dataset audits).
- **Run:**
  ```powershell
  pytest
  ```
- **Expected:** `123 passed` (a few may `skip` only if golden checksum is unknown
  for your numpy — see B8). Phase-1 tests need the server extra installed
  (`pip install -e ".[dev]"` already includes it).

The rows below let you run and understand each area on its own.

### B1 — Version & public API
- **What it tests:** package version is exposed; public API surface exists.
- **Files under test:** `src/datadoom/__init__.py`, `version.py`.
- **Run:** `pytest tests/unit/test_version.py -v`
- **Expected:** `2 passed`.

### B2 — Seeded RNG
- **What it tests:** identical inputs → identical draws; different namespaces are
  independent; **adding a namespace doesn't perturb others**.
- **Files under test:** `src/datadoom/engine/rng.py`.
- **Run:** `pytest tests/unit/test_rng.py -v`
- **Expected:** `5 passed`.

### B3 — Spec hashing & canonicalization
- **What it tests:** hash **excludes seed**; integral floats normalize (`40` ≡
  `40.0`); key order doesn't matter; object hash == body hash.
- **Files under test:** `src/datadoom/engine/spec/hashing.py`, `models.py`.
- **Run:** `pytest tests/unit/test_hashing.py -v`
- **Expected:** `6 passed` (includes TH.6 discrimination: a param change and a
  category reorder each move the hash).

### B4 — Spec validation
- **What it tests:** valid specs parse; each invalid case raises
  `SpecValidationError` with the right **locator** (unknown dist, bad `std`,
  weights length, `min>max`, causal cycle, dangling refs, sampled-and-derived
  conflict, split sums, difficulty label, failure refs/rate).
- **Files under test:** `src/datadoom/engine/spec/validate.py`, `models.py`.
- **Run:** `pytest tests/unit/test_spec_validate.py -v`
- **Expected:** `15 passed` (includes TH.7: a valid multi-node DAG is accepted; a
  self-loop `a→a` is rejected as a cycle).

### B5 — Distributions & honest compliance
- **What it tests:** empirical params within tolerance; uniform respects bounds;
  KS rejection rate stays near α when params are correct (proves **no refit**);
  KS **rejects** when params are wrong; compliance score aggregates.
- **Files under test:** `src/datadoom/engine/dist/{builtins,compliance}.py`.
- **Run:** `pytest tests/unit/test_dist.py -v`
- **Expected:** `5 passed`.

### B6 — Export byte-stability
- **What it tests:** CSV bytes are identical across writes; LF newlines (no CRLF);
  column order preserved; checksum stable.
- **Files under test:** `src/datadoom/engine/export/`.
- **Run:** `pytest tests/unit/test_export.py -v`
- **Expected:** `3 passed`.

### B7 — Pipeline behavior
- **What it tests:** clamping is recorded; no clamp → 0 fraction; `dtype: int`
  yields integral column; derived feature without causal engine raises; column
  order matches spec.
- **Files under test:** `src/datadoom/engine/pipeline.py`.
- **Run:** `pytest tests/unit/test_pipeline.py -v`
- **Expected:** `5 passed`.

### B8 — Determinism gate (the guarantee)
- **What it tests:** two runs of the same spec+seed produce identical frames and
  identical CSV bytes/checksums; `spec_hash` excludes seed; different seeds change
  data; golden checksum matches the pinned value for your numpy.
- **Files under test:** `src/datadoom/engine/pipeline.py`, `export/`, golden spec.
- **Run:** `pytest tests/determinism -v`
- **Expected:** `5 passed`. (`test_golden_checksum_pinned` **skips** with an
  instruction if your numpy version isn't recorded in
  `tests/golden/checksums.json` — that is expected on a new numpy, not a failure.)

### B9 — Distribution correctness (TH.1–TH.5)
- **What it tests:** samplers produce the right *distribution*, not just numbers —
  lognormal/poisson/pareto/exponential moments & support; cdf↔sampler KS
  agreement; categorical weight fidelity; boolean rate; datetime bounds &
  granularity; text token length. (See Group G for the per-check detail.)
- **Files under test:** `src/datadoom/engine/dist/{builtins,compliance}.py`.
- **Run:** `pytest tests/unit/test_dist_correctness.py -v`
- **Expected:** `16 passed`.

### B10 — Metadata integrity (TH.8)
- **What it tests:** in a written bundle, `metadata.json`'s recorded `data.csv`
  checksum equals the file's actual SHA256, `spec_hash` matches the run, and
  `spec.resolved.yaml` carries the resolved seed.
- **Files under test:** `src/datadoom/engine/pipeline.py`, `export/metadata.py`.
- **Run:** `pytest tests/unit/test_metadata.py -v`
- **Expected:** `3 passed`.

> Hashing discrimination (TH.6) and DAG acceptance (TH.7) ship as additions to
> B3 (`test_hashing.py`) and B4 (`test_spec_validate.py`) respectively.

---

## Group C — CLI behavior (run these by hand)

All use the example spec `examples/tabular-basic.datadoom.yaml`. With the venv
activated, the `datadoom` command is on your PATH.

### C1 — `validate` a good spec
- **What it tests:** spec parsing + cross-field validation succeed and print the
  spec hash.
- **Files under test:** `cli/main.py`, `engine/spec/`.
- **Run:**
  ```powershell
  datadoom validate examples/tabular-basic.datadoom.yaml
  ```
- **Expected:**
  ```
  OK  spec_hash=121975c21442f475cb692232de8c7c2f9d75336a71df302262697409d2ed5a2a
  ```
  > `spec_hash` is a pure hash of the spec text — it is **the same on every
  > machine/OS/Python**. If you edit the spec, it changes.

### C2 — `validate` catches a bad spec
- **What it tests:** validation fails with a clear, located message and a non-zero
  exit code.
- **Files under test:** `engine/spec/validate.py`, `cli/main.py`.
- **Setup:** make a broken copy (unknown distribution). This array form avoids
  here-string indentation pitfalls:
  ```powershell
  Set-Content -Encoding utf8 .\broken.datadoom.yaml @(
    'datadoom_version: "1"',
    'name: broken',
    'rows: 10',
    'features:',
    '  x: { type: numeric, dist: wat, params: {} }'
  )
  datadoom validate .\broken.datadoom.yaml
  ```
- **Expected:** red text
  `INVALID: features.x.dist: unknown distribution 'wat'` and exit code 1.
  Clean up: `Remove-Item .\broken.datadoom.yaml`

### C3 — `run` generates a dataset
- **What it tests:** the full pipeline writes artifacts and prints a summary.
- **Files under test:** `engine/pipeline.py`, `engine/export/`, `cli/main.py`.
- **Run:**
  ```powershell
  datadoom run examples/tabular-basic.datadoom.yaml --seed 7 --out .tmp_run
  ```
- **Expected (shape):**
  ```
  spec_hash       121975c2...d2ed5a2a
  seed            7
  rows            5000
  compliance      1.000 (1 KS-assessed, 2 n/a)
  artifact        data.csv  sha256=6a044e7344421...…
  artifact        metadata.json  sha256=...
  written to .tmp_run
  ```
  > Of the 3 numeric features only `income` (continuous lognormal, unclamped) gets
  > a valid continuous KS test, and it passes → `compliance 1.000`. `age` (clamped
  > to 18–90 *and* int) and `visits` (discrete Poisson) are reported as **n/a** —
  > a continuous KS test isn't valid for transformed/discrete data, so they're
  > excluded from the score rather than falsely failed (their empirical moments
  > still match the request). Nothing is auto-corrected. See Group E.

### C4 — `verify` self-check (reproducibility)
- **What it tests:** generating twice with the same seed yields the **same
  checksum**.
- **Files under test:** `cli/main.py` (`verify`), `engine/pipeline.py`.
- **Run:**
  ```powershell
  datadoom verify examples/tabular-basic.datadoom.yaml --seed 7
  ```
- **Expected:** green
  ```
  OK  reproducible (spec_hash=121975c2..., seed=7)
      sha256=<64 hex chars>
  ```

### C5 — `verify --against` a saved run
- **What it tests:** a fresh run matches a previously saved bundle's recorded
  checksum (round-trip).
- **Files under test:** `cli/main.py`, `engine/export/metadata.py`.
- **Run (after C3 produced `.tmp_run`):**
  ```powershell
  datadoom verify examples/tabular-basic.datadoom.yaml --seed 7 --against .tmp_run
  ```
- **Expected:** `OK  reproducible (...)`. If you regenerate `.tmp_run` with a
  **different** seed first, expect a red `MISMATCH` and exit 1.

---

## Group D — Determinism proof (manual)

### D1 — Two runs, byte-for-byte identical
- **What it tests:** the headline guarantee, by hand.
- **Run:**
  ```powershell
  datadoom run examples/tabular-basic.datadoom.yaml --seed 1 --out .run_a
  datadoom run examples/tabular-basic.datadoom.yaml --seed 1 --out .run_b
  (Get-FileHash .run_a\data.csv).Hash -eq (Get-FileHash .run_b\data.csv).Hash
  ```
- **Expected:** `True`. Cleanup: `Remove-Item -Recurse .run_a, .run_b`

### D2 — Different seed → different data
- **Run:**
  ```powershell
  datadoom run examples/tabular-basic.datadoom.yaml --seed 1 --out .run_a
  datadoom run examples/tabular-basic.datadoom.yaml --seed 2 --out .run_b
  (Get-FileHash .run_a\data.csv).Hash -eq (Get-FileHash .run_b\data.csv).Hash
  ```
- **Expected:** `False`. Cleanup as above.

> **Cross-machine note:** `spec_hash` is identical everywhere. The **data
> checksum** is only guaranteed identical on the *pinned path* (same numpy/scipy,
> single-threaded BLAS). A different numpy version may produce a different — but
> still internally reproducible — checksum. That is by design (`docs_v2/05 §1.3`).

---

## Group E — Honest statistics (observe behavior)

### E1 — Compliance reports fit, never fakes it
- **What it tests:** the engine **reports** distribution fit and does not refit
  parameters to the sample; and that a continuous KS test only counts where it is
  statistically valid (continuous dist + float dtype + no clamp).
- **Run:**
  ```powershell
  datadoom run examples/tabular-basic.datadoom.yaml --seed 7 --out .tmp_run
  python -c "import json; d=json.load(open('.tmp_run/metadata.json')); c=d['compliance']; print('score', round(c['compliance_score'],3), '| applicable', c['applicable_features'], 'of', c['assessed_features']); [print(' ', f['feature'], f['dist'], 'p=%.3f'%f['p_value'], (('pass' if f['passed'] else 'FAIL') if f['applicable'] else 'n/a'), 'clamped=%.2f'%f['clamped_fraction']) for f in c['features']]"
  ```
- **Expected (values vary slightly):**
  ```
  score 1.0 | applicable 1 of 3
    age normal p=0.000 n/a clamped=0.03
    income lognormal p=0.156 pass clamped=0.00
    visits poisson p=0.000 n/a clamped=0.00
  ```
  `age` is **n/a** (clamped ~3% of a normal *and* cast to int — both transforms
  break the continuous-KS null), and `visits` is **n/a** (Poisson is discrete).
  Their realized data still matches the request — eyeball `empirical` mean/std in
  the metadata — but a continuous KS test isn't a valid pass/fail for them, so they
  are reported with `applicable:false` and excluded from the score rather than
  falsely failed. Only `income` (continuous lognormal, unclamped) is KS-scored.
  This is **honest** and avoids the false-negative where a correct generator
  scores 0.

---

## Group F — Artifact inspection

### F1 — What a run writes
- **What it tests:** the output bundle layout.
- **Run:**
  ```powershell
  Get-ChildItem .tmp_run
  ```
- **Expected files:**
  | File | Purpose |
  |---|---|
  | `data.csv` | the generated clean dataset (5000 rows) |
  | `metadata.json` | spec, `spec_hash`, seed, compliance, namespace key digests, checksums (no timestamps → reproducible) |
  | `spec.resolved.yaml` | the exact spec used, with the resolved `seed` baked in |

### F2 — Peek at the data
- **Run:**
  ```powershell
  Get-Content .tmp_run\data.csv -TotalCount 3
  ```
- **Expected:** a header `age,income,visits,education,is_member,signup_date,note`
  followed by data rows. Cleanup: `Remove-Item -Recurse .tmp_run`

---

## Group G — Correctness tests (✅ implemented)

> These close gaps where a *logic/arithmetic* bug could pass the structural
> suite (tracked as task **TH** in [status.md](status.md)). All are now
> implemented and pass; the detail below documents what each one checks. Run
> them via B9/B10 above (and the TH.6/TH.7 additions in B3/B4).

### G1 — Distribution statistical correctness (TH.1)
- **What it tests:** that `lognormal`, `poisson`, `pareto`, `exponential`
  produce the right *distribution*, not just "some numbers":
  - `lognormal(mu,sigma)`: empirical median ≈ `exp(mu)`, mean ≈ `exp(mu+sigma²/2)`.
  - `poisson(lam)`: mean ≈ var ≈ `lam`; output integral.
  - `pareto(alpha,xm)`: all samples **≥ xm** (support), mean ≈ `alpha·xm/(alpha-1)`
    for `alpha>2` — guards the `(pareto(α)+1)·xm` formula.
  - `exponential(scale)`: all samples **≥ 0**, mean ≈ `scale`.
  - Each distribution **passes** KS on correct params (proves `cdf` matches the
    sampler — a wrong `cdf` would be caught).
- **Files under test:** `src/datadoom/engine/dist/builtins.py`, `compliance.py`.
- **Test file:** `tests/unit/test_dist_correctness.py`.

### G2 — Categorical weight fidelity (TH.2)
- **What it tests:** `weights:[0.6,0.3,0.1]` yields ~60/30/10; no weights →
  ~uniform; unnormalized weights (e.g. `[3,1]`) normalize to 0.75/0.25.
- **Files under test:** `src/datadoom/engine/dist/builtins.py` (`sample_categorical`).
- **Test file:** `tests/unit/test_dist_correctness.py`.

### G3 — Boolean rate fidelity (TH.3)
- **What it tests:** `rate=0.3` → empirical P(true) ≈ 0.3.
- **Files under test:** `sample_boolean`.
- **Test file:** `tests/unit/test_dist_correctness.py`.

### G4 — Datetime bounds & granularity (TH.4)
- **What it tests:** all values within `[start,end]`; `granularity: day`
  yields whole-day values; correct `datetime64` dtype. (Guards the `astype`
  datetime refactor.)
- **Files under test:** `sample_datetime`.
- **Test file:** `tests/unit/test_dist_correctness.py`.

### G5 — Text length (TH.5)
- **What it tests:** each generated string has a token count within
  `[min,max]`.
- **Files under test:** `sample_text`.
- **Test file:** `tests/unit/test_dist_correctness.py`.

### G5b — Realistic text providers (mimesis)
- **What it tests:** `generator:` keys other than `lorem` (name, email,
  address, company, occupation, …) emit genuine-looking strings via *mimesis*,
  seeded from the feature's own RNG so the same `(spec_hash, seed)` reproduces
  byte-identical text; an unknown `generator` or `locale` is rejected at
  validation; a non-`en` `locale` changes the output.
- **Files under test:** `src/datadoom/engine/dist/providers.py`,
  `pipeline.py`, `spec/validate.py`.
- **Test file:** `tests/unit/test_providers.py`;
  `examples/people-realistic.datadoom.yaml` is also in the determinism gate
  (`tests/determinism/test_determinism.py`).
- **Command:**
  ```powershell
  datadoom run examples/people-realistic.datadoom.yaml --seed 42 --out .tmp_people
  datadoom verify examples/people-realistic.datadoom.yaml --seed 42
  ```
- **Expected:** `data.csv` has real-looking `full_name`/`email`/`company`
  values, the `german_city` column holds German place names (locale `de`), and
  `verify` reports the run is reproducible (identical checksum on the pinned
  mimesis version).

### G6 — Hashing discrimination (TH.6)
- **What it tests:** changing a param value → **different** `spec_hash`;
  reordering `categories` (semantic array order) → **different** hash. (Today all
  hash tests assert *equality* only; a degenerate hash would pass them.)
- **Files under test:** `src/datadoom/engine/spec/hashing.py`, `models.py`.
- **Test file:** `tests/unit/test_hashing.py` (additions).

### G7 — Causal DAG acceptance (TH.7)
- **What it tests:** a valid multi-node DAG (`a→b→c`, `a→c`) is **accepted**;
  a self-loop `a→a` is **rejected** as a cycle. (Today only cycle *rejection* is
  tested — a detector that wrongly rejects valid graphs would pass.)
- **Files under test:** `src/datadoom/engine/spec/validate.py`.
- **Test file:** `tests/unit/test_spec_validate.py` (additions).

### G8 — Metadata integrity (TH.8)
- **What it tests:** in a written bundle, `metadata.json`'s recorded
  `data.csv` checksum **equals** the actual file SHA256; `spec_hash` matches the
  result; `spec.resolved.yaml` carries the resolved `seed`.
- **Files under test:** `src/datadoom/engine/pipeline.py`, `export/metadata.py`.
- **Test file:** `tests/unit/test_metadata.py` (new).

---

## Group H — Server & web (Phase 1)

> Needs the server extra (already in `[dev]`). These exercise `store/`, `jobs/`,
> and `api/` — the persistence DB, the in-process worker, and the REST/WebSocket
> surface — without a browser.

### H0 — Upgrade an existing database schema
- **What it tests:** if you encounter `sqlite3.OperationalError: no such column: reports.mutual_information`
  (or similar missing-column errors), the DB has pending Alembic migrations that need applying.
- **Run:**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  python -c "from datadoom.store.db import init_database; from datadoom.config import load_config; cfg = load_config(); init_database(cfg.db_url)"
  ```
  Or simply restart the server (`datadoom serve`), which calls `alembic upgrade head` automatically.
- **Expected:** the database is upgraded to the latest schema. Verify with:
  ```powershell
  python -c "import sqlite3; c = sqlite3.connect(str(load_config().db_path)); r = c.execute('SELECT * from alembic_version').fetchall(); print('Current:', r); c.close()"
  ```
  The version should show the latest revision hash.

### H1 — Store: CRUD, immutability, cascade
- **What it tests:** dataset CRUD; **spec immutability** (edit → new version,
  current repointed); **cascade delete** (removing a dataset deletes its specs,
  runs, artifacts, reports); the Alembic `0001_init` migration produces the same
  tables the ORM declares.
- **Files under test:** `src/datadoom/store/*`, `store/migrations/versions/0001_init.py`.
- **Test file:** `tests/unit/test_store.py`.
- **Run:** `pytest tests/unit/test_store.py -v`
- **Expected:** `5 passed`.

### H2 — API: routes, errors, run lifecycle, WS
- **What it tests:** happy paths for specs/datasets/runs/results; `422` with a
  `locator` on a bad spec; `409` on a duplicate name; `Idempotency-Key` replay
  (second create returns `200` + the same run); a run generates artifacts + report;
  **same `(spec, seed)` → identical CSV checksum** over the API; the WebSocket
  streams `stage` events through to `completed`.
- **Files under test:** `src/datadoom/api/*`, `jobs/*`.
- **Test file:** `tests/api/test_api.py`.
- **Run:** `pytest tests/api -v`
- **Expected:** all pass (12 tests).

### H3 — Launch the server by hand
- **What it tests:** `datadoom serve` boots, opens/upgrades the SQLite DB under
  `$DATADOOM_HOME`, and serves the API.
- **Run (a scratch home so you don't touch real data):**
  ```powershell
  $env:DATADOOM_HOME = "$env:TEMP\datadoom-manual"
  datadoom serve
  ```
- **Expected:** prints `DataDoom serving on http://127.0.0.1:8000 (data: …)`.
  In another shell:
  ```powershell
  curl http://127.0.0.1:8000/api/health      # {"status":"ok"}
  curl http://127.0.0.1:8000/api/version     # version + datadoom_version "1"
  ```
  Swagger UI is at `http://127.0.0.1:8000/api/docs`. Stop with Ctrl+C.

### H4 — End-to-end over HTTP (curl)
- **What it tests:** create → generate → poll → preview, all over REST.
- **Run (server from H3 still up):**
  ```powershell
  $spec = '{"datadoom_version":"1","name":"h4","rows":500,"features":{"age":{"type":"numeric","dist":"normal","params":{"mean":40,"std":10}},"amt":{"type":"numeric","dist":"normal","params":{"mean":100,"std":25}}}}'
  $ds   = curl -s -X POST http://127.0.0.1:8000/api/datasets -H "Content-Type: application/json" -d "{`"name`":`"h4`",`"spec`":$spec}"
  ```
- **Expected:** the dataset JSON includes `"status":"draft"` and a
  `current_spec.version: 1`. POST `…/datasets/{id}/runs` returns `202` + a
  `run_id`; GET `…/runs/{id}` flips to `completed`; `…/runs/{id}/preview`
  returns columns + rows; `…/runs/{id}/report` has a non-null `compliance_score`
  and a `correlation` matrix (two numeric features).

---

## Group I — Web Canvas (Phase 1)

> The bundled SPA. Build it once, then `datadoom serve` ships it; no Node needed
> by end users. (For UI development, `cd frontend && npm run dev` proxies to :8000.)

### I1 — Build the frontend into the wheel
- **What it tests:** the SPA compiles into `src/datadoom/webdist/`.
- **Run:**
  ```powershell
  cd frontend; npm install; npm run build; cd ..
  ```
- **Expected:** `vite build` succeeds and writes `src/datadoom/webdist/index.html`
  + `assets/`. `datadoom serve` then serves the app at `http://127.0.0.1:8000/`.

### I2 — The MVP loop in the browser  (P1 exit gate)
- **What it tests:** create a dataset → edit the schema in the Canvas → Generate →
  watch the live tracker → view Results → Export — all in-browser, < 5 min.
- **Steps:** open `http://127.0.0.1:8000/`; "Create Dataset" (name + rows); in the
  Canvas add/edit columns (pick distributions, watch the live preview histogram);
  press **Generate**; the Tracker streams stages to **completed**; "View Results"
  shows Data Preview, Distributions (with honest KS chips), Correlation, and the
  Evaluation report (compliance pull-stat + determinism); "Export" downloads the
  bundle (data.csv + metadata.json + resolved spec).
- **Expected:** the whole loop works without a page reload; the seed and spec_hash
  are visible and copyable; regenerating with the same seed reproduces the data.

### I3 — Theme toggling (Paper / Ink / System)
- **What it tests:** the first-class editorial theme system.
- **Steps:** use the top-bar toggle to switch **Paper → Ink → System**; press
  **`t`** anywhere (outside a text field) to flip Paper↔Ink; reload the page.
- **Expected:** the whole app (light "Paper" default, dark "Ink") recolors
  smoothly with no flash on reload; the choice persists; "System" follows the OS
  setting; reduced-motion users get no transition flash.

---

## Group J — Causal engine (Phase 2)

The causal stage runs between `base_generation` and `compliance`: root features
are sampled, then derived (causal-target) features are computed by the SEM walk
in topological order. See `examples/causal-fraud.datadoom.yaml`.

### J0 — Causal unit tests
- **What it tests:** SEM execution, structural fns, interventions, validation,
  the true-graph + MI report sections. **Files:** `src/datadoom/engine/causal/*`,
  `tests/unit/test_causal.py`.
- **Run:**
  ```powershell
  pytest tests/unit/test_causal.py -q
  ```
- **Expected:** `22 passed`.

### J1 — Generate from a causal spec
- **What it tests:** `age→income→is_fraud` (+`education→income`) end-to-end; roots
  sampled, derived columns computed. **File:** `examples/causal-fraud.datadoom.yaml`.
- **Run:**
  ```powershell
  datadoom run examples/causal-fraud.datadoom.yaml --seed 42 --out .tmp_causal
  ```
- **Expected:** `rows 5000`, `compliance 1.000 (0 KS-assessed, 1 n/a)`. `age` is a
  realistic clamped integer, so a continuous KS test does not apply to it (see
  Group E / E2); `income`/`is_fraud` are derived (not KS-assessed). Two artifacts
  written.

### J2 — Inspect the derived structure  (P2 engine gate)
- **What it tests:** the SEM actually wired the features — income tracks age, and
  is_fraud is a Bernoulli of the logistic of income.
- **Run:**
  ```powershell
  python -c "import pandas as pd; d=pd.read_csv('.tmp_causal/data.csv'); print('corr age~income', round(d['age'].corr(d['income']),3)); print('is_fraud rate', round(d['is_fraud'].mean(),3))"
  ```
- **Expected:** a clearly positive `age~income` correlation (≈0.5–0.6) and an
  `is_fraud` rate in (0,1) — neither all-True nor all-False.

### J3 — True graph + mutual-information report
- **What it tests:** the report carries `causal_truth` (edges with params + topo
  order) and a `mutual_information` matrix (05 §7).
- **Run:**
  ```powershell
  python -c "from datadoom.engine import load_spec, generate; r=generate(load_spec('examples/causal-fraud.datadoom.yaml'), seed=42); print('edges', [(e['from'],e['to'],e['fn']) for e in r.report.causal_truth['edges']]); print('topo', r.report.causal_truth['topological_order']); print('MI cols', r.report.mutual_information['columns'])"
  ```
- **Expected:** the three authored edges print; the topo order has `age`/`education`
  before `income` before `is_fraud`; the MI matrix lists the discretizable columns.

### J4 — Interventions detach edges
- **What it tests:** `do(X=x₀)` fixes a node to a constant and reports its incoming
  edges as `active: false` (05 §3.1).
- **Run:**
  ```powershell
  python -c "from datadoom.engine import generate, parse_spec; s=parse_spec({'datadoom_version':'1','name':'iv','rows':1000,'seed':1,'features':{'x':{'type':'numeric','dist':'normal','params':{'mean':0,'std':1}},'y':{'type':'numeric'}},'causal':{'edges':[{'from':'x','to':'y','fn':'linear','weight':5}],'interventions':[{'do':{'y':9}}]}}); r=generate(s,seed=1); print('y unique', set(r.frame['y'])); print('edge active', r.report.causal_truth['edges'][0]['active'])"
  ```
- **Expected:** `y unique {9.0}` (detached from x, fixed) and `edge active False`.

### J5 — Cycle rejection
- **What it tests:** a cyclic graph is rejected at validation with a locator.
- **Run:**
  ```powershell
  python -c "from datadoom.engine import parse_spec; parse_spec({'datadoom_version':'1','name':'c','rows':10,'features':{'a':{'type':'numeric'},'b':{'type':'numeric'}},'causal':{'edges':[{'from':'a','to':'b','fn':'identity'},{'from':'b','to':'a','fn':'identity'}]}})"
  ```
- **Expected:** a `SpecValidationError` mentioning "acyclic".

> Cleanup: `Remove-Item -Recurse -Force .tmp_causal`.

---

## Group K — End-to-end dataset audit

These prove the **whole pipeline** produces data that matches the spec — not just
that the samplers work in isolation (Group G) but that a *generated* dataset's
realized columns carry the requested distributions and dependencies. Automated in
`tests/unit/test_dataset_audit.py`.

### K0 — Run the audit suite
- **What it tests:** generate from both shipped examples and assert every declared
  property holds in the realized frame.
- **Run:**
  ```powershell
  pytest tests/unit/test_dataset_audit.py -q
  ```
- **Expected:** `13 passed`.

### K1 — Audit the non-causal dataset by hand
- **What it tests:** for `tabular-basic`, each feature matches its requested
  distribution — moments, bounds, categorical weights, boolean rate, datetime
  range, text length — and KS-applicability is honest.
- **Run:**
  ```powershell
  python -c "from datadoom.engine import load_spec, generate; import numpy as np, pandas as pd; r=generate(load_spec('examples/tabular-basic.datadoom.yaml'), seed=42); d=r.frame; print('age   mean=%.2f std=%.2f min=%d max=%d int=%s'%(d['age'].mean(), d['age'].std(), d['age'].min(), d['age'].max(), str(d['age'].dtype))); print('income median=%.0f (target %.0f)  mean=%.0f (target %.0f)'%(d['income'].median(), np.exp(10.5), d['income'].mean(), np.exp(10.5+0.4**2/2))); print('visits mean=%.2f var=%.2f (lam=3)'%(d['visits'].mean(), d['visits'].var())); print('edu   '+str({c: round((d['education']==c).mean(),3) for c in ['hs','college','grad']})+' (target .5/.4/.1)'); print('member rate=%.3f (target .3)'%d['is_member'].mean()); print('note  tokens %d..%d (target 5..20)'%(d['note'].map(lambda s: len(s.split())).min(), d['note'].map(lambda s: len(s.split())).max())); print('compliance %.3f  applicable=%d of %d'%(r.compliance.score, r.compliance.to_dict()['applicable_features'], r.compliance.to_dict()['assessed_features']))"
  ```
- **Expected (values vary slightly):** `age` mean ≈ 40, bounds within 18..90, int
  dtype; `income` median ≈ 36315 and mean ≈ 39340; `visits` mean ≈ var ≈ 3; the
  education split ≈ .5/.4/.1; member rate ≈ .3; note tokens within 5..20; and
  `compliance` with `applicable = 1 of 3` (only the continuous, unclamped `income`
  is KS-scored — `age`/`visits` abstain honestly).

### K2 — Audit the causal dataset by hand
- **What it tests:** the structural equations are recovered from the generated
  data (OLS coefficients + noise scale + logistic calibration).
- **Run:**
  ```powershell
  python -c "from datadoom.engine import load_spec, generate; import numpy as np; r=generate(load_spec('examples/causal-fraud.datadoom.yaml'), seed=42); d=r.frame; age=d['age'].to_numpy(float); edu=d['education'].map({'hs':0.,'college':15000.,'grad':40000.}).to_numpy(); inc=d['income'].to_numpy(); X=np.column_stack([np.ones(len(d)),age,edu]); b,aw,ew=np.linalg.lstsq(X,inc,rcond=None)[0]; print('OLS  age_w=%.1f (800)  bias=%.0f (10000)  edu_w=%.3f (1.0)'%(aw,b,ew)); print('noise std=%.0f (5000)'%(inc-(10000+800*age+edu)).std()); fr=d['is_fraud'].to_numpy(float); p=1/(1+np.exp(-(-0.00002*inc+1.0))); print('fraud rate=%.3f  theory=%.3f  corr(income,fraud)=%.3f (neg)'%(fr.mean(),p.mean(),np.corrcoef(inc,fr)[0,1]))"
  ```
- **Expected:** `age_w` ≈ 800, `bias` ≈ 10000, `edu_w` ≈ 1.0, noise std ≈ 5000,
  fraud rate ≈ theory, and `corr(income, fraud)` **negative** (the logistic
  weight is negative). The declared dependencies match the realized data.

---

## Group L — Web Graph view (Phase 2)

The Canvas gains a **Graph** view (React Flow) for authoring the causal DAG, and
Results gains a read-only true-graph + MI heatmap. Build the SPA first (Group I,
**I1**: `npm install && npm run build` in `frontend/`), then `datadoom serve` and
open `http://127.0.0.1:8000/`.

### L1 — Author a causal graph in the browser  (P2 exit gate)
- **What it tests:** drag-to-connect edges, the structural-fn editor, derived
  features, and generation through the SEM.
- **Steps:** open a dataset with ≥2 columns (e.g. `age` numeric + an empty
  `income` numeric); switch the toolbar toggle to **Graph**; drag from `age`'s
  right handle to `income` — an edge appears and `income` becomes **derived**
  (its `dist` is dropped). Click the edge → pick `linear`, set weight/bias. Add
  `education` (categorical) → `income` and pick `map` (a row per category). Press
  **Generate**.
- **Expected:** the edge is created; `income` shows as *derived*; the run
  completes; **Results → Causal Graph** renders the true DAG with edge labels.

### L2 — Live cycle rejection
- **What it tests:** the editor refuses to create a cycle.
- **Steps:** with `a → b` present, drag from `b` back to `a`.
- **Expected:** no edge is added; a hazard toast appears: "b → a would create a
  cycle — rejected." A self-connection is likewise rejected.

### L3 — Intervention toggle
- **What it tests:** `do(X=x₀)` from the UI.
- **Steps:** click a derived node; tick **Fix this node to a constant**; set a
  value; Generate; open **Results → Causal Graph**.
- **Expected:** the node is badged `do()`, its incoming edges render **dashed**
  (detached), and the realized column is constant at the chosen value.

### L4 — Results: true graph + correlation/MI
- **What it tests:** the read-only ground-truth graph and both heatmaps.
- **Steps:** from a completed causal run, open **Results**; visit **Causal Graph**
  and **Correlation & MI**.
- **Expected:** the DAG shows every authored edge (fn + weight) in topological
  layout; the **Correlation** heatmap (signed) and **Mutual information** heatmap
  (magnitude, diagonal = entropy) both render. On the **Distributions**/**Evaluation**
  tabs, integer/discrete/clamped features read **n/a** (not "review"), and the
  compliance card notes `N of M applicable`.

---

## Group M — Failure injection (Phase 3)

The pipeline gains a `failure_injection` stage: the clean baseline is captured,
then the spec's ordered `failures` corrupt a *copy* (each from `RNG(failure:i)`).
The clean variant is always preserved; the injected variant ships as
`data.injected.csv` when `export.versions` includes `injected`. Automated in
`tests/unit/test_failure.py`.

### M0 — Run the failure unit tests
- **What it tests:** every mode's behavior (rate accuracy, MAR/MNAR
  driver/value dependence, label flip-to-different-class, feature-noise std,
  drift schedule, covariate moment-match, leakage correlation), the
  clean-baseline guarantee, injected determinism, and per-mode validation.
- **Run:**
  ```powershell
  pytest tests/unit/test_failure.py -q
  ```
- **Expected:** `26 passed`.

### M0b — Critical mathematical audit (parameter recovery)
- **What it tests:** the math, not just the shape. Generates at n=20k and
  **recovers each mechanism's parameters from the realized frame** vs exact or
  asymptotic theory — the P3 analogue of `test_dataset_audit.py`:
  MAR/MNAR logistic-slope recovery (IRLS) + calibrated rate; categorical
  reassignment is a *uniform* transition matrix (off-diagonal = p/(k−1)); boolean
  flip is class-symmetric with marginal `q(1−p)+(1−q)p`; feature-noise ε is
  KS-Gaussian with the right σ and independent of x; **drift** is an exact linear
  ramp (≈1e-14); **covariate_shift** hits the target mean/std to 1e-6; **leakage**
  correlation equals the closed form `1/√(1+η²)`.
- **Run:**
  ```powershell
  pytest tests/unit/test_failure_audit.py -q
  ```
- **Expected:** `14 passed`. A sign error, a miscalibrated intercept, or a biased
  reassignment would fail here even though the loose checks in **M0** still pass.

### M1 — Generate clean + injected variants  (P3 engine gate)
- **What it tests:** the end-to-end stage writes both variants; the clean
  baseline carries no injected missingness; the injected variant does.
- **Run:**
  ```powershell
  datadoom run examples/failure-fraud.datadoom.yaml --seed 42 --out .tmp_fail
  ```
- **Expected:** three artifacts listed — `data.csv` (clean), `data.injected.csv`,
  and `metadata.json` — and `written to .tmp_fail`. The clean `data.csv` has no
  blank cells; `data.injected.csv` has blanks in `income`/`age`, a flipped share
  of `is_fraud`, and an extra `fraud_score` leakage column not present in the
  clean file.

### M2 — Inspect the realized failure effects
- **What it tests:** each mode's diff summary matches what landed in the frame.
- **Run:**
  ```powershell
  python -c "from datadoom.engine import load_spec, generate; r=generate(load_spec('examples/failure-fraud.datadoom.yaml'), seed=42); c,i=r.frame,r.injected; print('clean NaN total      =', int(c.isna().sum().sum())); print('injected income NaN  = %.3f'%i['income'].isna().mean()); print('injected age NaN     = %.3f'%i['age'].isna().mean()); print('is_fraud flipped     = %.3f'%(c['is_fraud'].to_numpy()!=i['is_fraud'].to_numpy()).mean()); print('leakage corr (inj)   = %.3f'%__import__('numpy').corrcoef(i['fraud_score'], i['is_fraud'].to_numpy(float))[0,1]); [print(' diff:', m['type'], {k:v for k,v in m.items() if k in ('realized_rate','flipped_fraction','realized_noise_std','total_shift','realized_correlation')}) for m in r.report.failures['modes']]"
  ```
- **Expected:** clean NaN total `0`; injected `income` NaN ≈ 0.12 and `age` NaN
  ≈ 0.05; `is_fraud` flipped ≈ 0.03; leakage correlation ≈ 0.99 against the
  **injected** label (the proxy is planted *after* label noise, so it tracks the
  already-corrupted label); and each diff summary's realized stat ≈ its requested
  knob.

### M3 — Both variants are byte-stable
- **What it tests:** the injected corruption is reproducible on the pinned path.
- **Run:**
  ```powershell
  datadoom verify examples/failure-fraud.datadoom.yaml --seed 42
  pytest "tests/determinism/test_determinism.py::test_injected_variant_is_byte_stable" -q
  ```
- **Expected:** `OK reproducible` (clean `data.csv` checksum) and `1 passed`
  (`data.injected.csv` identical across two runs).

### M4 — Validation rejects malformed failures
- **What it tests:** unknown types and per-mode field/type/reference errors are
  caught with a precise `locator`.
- **Run:**
  ```powershell
  python -c "from datadoom.engine import parse_spec; from datadoom.engine.errors import SpecValidationError; bad={'datadoom_version':'1','name':'bad','rows':10,'features':{'c':{'type':'categorical','categories':['a','b']}},'failures':[{'type':'label_noise','column':'c','rate':2.0}]}
  try:
      parse_spec(bad)
  except SpecValidationError as e:
      print('raised:', type(e).__name__, '->', e.locator)"
  ```
- **Expected:** `raised: SpecValidationError -> failures[0].rate` (rate out of
  `[0,1]`). The 12 parametrized cases in **M0** cover the rest — unknown type
  (`failures[0].type`), wrong column type, bad driver, missing schedule kind,
  empty covariate target, and `into == target`.

---

## Group N — Web Failure Configurator + Comparison (Phase 3)

The Canvas gains a third **Failures** view to author the corruption pipeline, and
Results gains a **Comparison** tab. Build the SPA first (Group I, **I1**:
`npm install && npm run build` in `frontend/`), then `datadoom serve` and open
`http://127.0.0.1:8000/`.

### N1 — Author a failure pipeline  (P3 exit gate)
- **What it tests:** adding/ordering/configuring failures and generating both
  variants.
- **Steps:** open a dataset with a numeric and a boolean column (e.g. `x` numeric
  + `flag` boolean). Switch the toolbar toggle to **Failures**. Click **Add
  failure** → pick **MNAR** (Missingness); in the inspector set its column to `x`
  and the rate slider to ~20%. Add **Label noise** on `flag`, then **Target
  leakage** with target `flag` → planted column `leak`. Reorder with the ↑/↓
  handles. Confirm the **Export the corrupted variant** toggle is on. Press
  **Generate**.
- **Expected:** each step shows a live impact chip (e.g. MNAR `≈… rows`, leakage
  `corr ≈ 0.999`); the green banner promises the clean baseline is preserved; the
  Failures tab shows a count badge; the run completes.

### N2 — Inspector controls & live impact
- **What it tests:** the type-aware controls and the honest estimate.
- **Steps:** select each failure step and exercise its controls — sliders
  (rate/strength/noise), column/driver selects, the drift schedule, covariate
  target moments, MCAR multi-column chips.
- **Expected:** the **Estimated impact** card updates as you tune; the math line
  matches the mechanism (e.g. leakage shows `corr = 1/√(1+noise²)`); an invalid
  config (e.g. no column picked) shows an inline amber warning and a ⚠ on the card.

### N3 — Comparison tab: realized effects
- **What it tests:** the authoritative per-mode diffs from the run report.
- **Steps:** from the completed run, open **Results → Comparison**.
- **Expected:** summary pull-stats (failure modes, % cells missing, columns
  affected, +leakage columns); one card per failure showing its **realized**
  effect (MNAR missing-rate bar vs target, label flip %, leakage correlation
  gauge, drift total-shift + ramp, covariate before→after moments). These are
  measured by the engine, not estimates.

### N4 — Comparison tab: clean vs injected diff
- **What it tests:** the cell-level and distribution comparison.
- **Steps:** scroll the Comparison tab; toggle **Changed rows only**.
- **Expected:** distribution overlays (clean grey vs injected violet) for any
  drifted/shifted/noised numeric column; a diff table where nullified cells show
  **∅** (red), changed values are amber (hover shows the clean value), and the
  planted leakage column (★) is violet. The clean **Data Preview** tab still shows
  the uncorrupted data.

---

## Group O — Web Generation Overview + realistic generators (Enhancement)

### O1 — Generation Overview dashboard
- **What it tests:** the **Overview** tab (the new default on the Results page)
  renders the at-a-glance summary from the run's metadata.
- **Files under test:** `frontend/src/components/OverviewView.tsx`,
  `pages/Results.tsx`.
- **Steps:** open any completed run's Results; the **Overview** tab is selected
  first.
- **Expected:** headline numerals (rows, columns, compliance %, seed; plus
  *Failure modes* when failures were injected); a **donut** of column-type
  composition with a colour legend; a **distribution-families** bar list; an
  **artifacts** table (format / version / human-readable size / short SHA-256).
  For a causal run, a **causal-structure** card (edges / derived cols /
  interventions); for a failure run, a **failure-by-mode** bar list.

### O2 — Author a realistic text column
- **What it tests:** the Canvas Inspector can author mimesis-backed text
  columns, and the locale control appears only for realistic generators.
- **Files under test:** `frontend/src/components/Inspector.tsx`,
  `lib/types.ts`, `lib/summary.ts`.
- **Steps:** in the Canvas, add/select a **text** column; in the Inspector open
  the **Generator** dropdown and pick e.g. `email` (People group). Generate.
- **Expected:** picking a non-`lorem` generator swaps the *min/max tokens*
  inputs for a **Locale** select; `lorem` shows the token inputs. The generated
  `email` column holds genuine-looking addresses, and re-running the same
  spec + seed reproduces identical values (see **G5b** for the engine guarantee).

---

## Appendix — One-shot "is everything healthy?" sweep

With the venv activated:

```powershell
cd "D:\Hack Forge"
.\.venv\Scripts\Activate.ps1

ruff check src tests        # A1  -> All checks passed!
lint-imports               # A2  -> 3 kept, 0 broken
mypy                       # A3  -> Success: no issues found in 67 source files
pytest                     # B0  -> 198 passed
datadoom verify examples/tabular-basic.datadoom.yaml --seed 7      # C4 -> OK reproducible
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42      # J1 -> OK reproducible
datadoom verify examples/failure-fraud.datadoom.yaml --seed 42     # M3 -> OK reproducible
datadoom verify examples/people-realistic.datadoom.yaml --seed 42  # G5b -> OK reproducible
```

If all are green, Phase 0, the Phase-1 server/web tests, the Phase-2 causal
engine, **and** the Phase-3 failure engine are healthy. For the in-browser P1
exit gate, build the SPA (I1) and walk the loop (I2–I3); for the P2 engine gate,
run Group **J**; for the P3 engine gate, run Group **M**.
