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
  compliance      1.000 (3 assessed)
  artifact        data.csv  sha256=6a044e7344421...…
  artifact        metadata.json  sha256=...
  written to .tmp_run
  ```
  > All 3 numeric features are assessed and pass → `compliance 1.000`. `income`
  > (continuous lognormal, unclamped) gets a continuous **KS** test; `age` (clamped
  > to 18–90 *and* int) and `visits` (discrete Poisson) get a chi-square
  > **goodness-of-fit** against their effective PMF — valid for transformed/discrete
  > data where a continuous KS would not be. Nothing is auto-corrected (fit is
  > reported, never refit). See Group E.

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
  parameters to the sample; it picks the *valid* test per feature shape — a
  continuous **KS** test for continuous/float/un-clamped features, and a
  chi-square **goodness-of-fit** against the effective PMF for integer, discrete,
  or clamped features (which would break the continuous-KS null).
- **Run:**
  ```powershell
  datadoom run examples/tabular-basic.datadoom.yaml --seed 7 --out .tmp_run
  python -c "import json; d=json.load(open('.tmp_run/metadata.json')); c=d['compliance']; print('score', round(c['compliance_score'],3), '| applicable', c['applicable_features'], 'of', c['assessed_features']); [print(' ', f['feature'], f['dist'], f['test'], 'p=%.3f'%f['p_value'], (('pass' if f['passed'] else 'FAIL') if f['applicable'] else 'n/a'), 'clamped=%.2f'%f['clamped_fraction']) for f in c['features']]"
  ```
- **Expected (values vary slightly):**
  ```
  score 1.0 | applicable 3 of 3
    age normal chi2_gof p=0.954 pass clamped=0.04
    income lognormal ks p=0.158 pass clamped=0.00
    visits poisson chi2_gof p=0.284 pass clamped=0.00
  ```
  `age` (clamped ~4% of a normal *and* cast to int) and `visits` (discrete
  Poisson) are judged by a **chi-square GoF** against the effective PMF — the
  boundary bins absorb the clamped tail — so a correct generator now earns a real
  **pass** instead of abstaining (`n/a`). `income` (continuous lognormal,
  unclamped) is judged by **KS**. The fit is reported honestly and never refit. A
  feature only shows `n/a` (`test: none`) when no valid test can be formed (e.g. a
  near-constant column).
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
  | `data.csv` | the generated clean dataset |
  | `data.injected.csv` | the same data **with failure modes applied** (only when failures + the `injected` export version are configured) |
  | `metadata.json` | spec, `spec_hash`, seed, compliance, namespace key digests, checksums (no timestamps → reproducible) |
  | `spec.resolved.yaml` | the exact spec used, with the resolved `seed` baked in |
  | `audit_report.md` | human-readable audit: compliance, the column guide (stats + data-quality issues + ML advice), injected failures, causal truth, difficulty, and checksums (deterministic, timestamp-free) |

  All of these are tracked artifacts (`GET /api/runs/{id}/artifacts` lists them with
  a `filename` + `version` of `clean`/`injected`/`spec`/`audit`) and are bound into
  the bundle zip. In the web **Export** dialog the injected file is clearly named
  `data.injected.csv` (never a second `data.csv`) and the audit report leads.

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

### H5 — Each generation locks its resolved spec (reproducibility)

- **What it tests:** every run captures the exact spec + resolved seed as a
  tracked, downloadable YAML artifact. Files: `engine/pipeline.py`,
  `api/routes/artifacts.py`, `api/serializers.py`, `components/GenerationsPanel.tsx`.
- **Tests:** `pytest tests/api/test_api.py::test_resolved_spec_is_locked_and_downloadable -q`
- **Run (manual, server up):** generate a dataset, then
  `curl http://127.0.0.1:8000/api/runs/<run_id>/spec.yaml`
- **Expected:** the artifacts list (`…/runs/{id}/artifacts`) includes an entry with
  `version: "spec"`, `format: "yaml"`, and a 64-char checksum; the run summary
  carries a `spec_hash`; `…/runs/{id}/spec.yaml` downloads a parseable spec with
  `seed:` baked in (regenerating from it is byte-identical). In the browser, each
  generation card shows a **🔒 spec `<hash>`** chip and a **Spec YAML** button.

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
- **Expected:** `rows 5000`, `compliance 1.000 (1 assessed)`. `age` is a realistic
  clamped integer, so it is judged by a chi-square **goodness-of-fit** against its
  effective PMF (not a continuous KS) and passes (see Group E / E2); `income`/
  `is_fraud` are derived (no `dist`, so not assessed). Two artifacts written.

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
  `compliance` with `applicable = 3 of 3` (`income` via KS; `age`/`visits` via a
  chi-square goodness-of-fit against their effective PMF — all three pass).

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
  tabs, integer/discrete/clamped features show a **χ²** chip (chi-square GoF) with
  a real pass/fail and **Fit p** value — not "n/a" — and the compliance card notes
  `N of M applicable`. A feature reads **n/a** only when no valid test can be formed.

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

## Group P — Difficulty targeting (Phase 4)

The pipeline gains a `difficulty` stage (… → causal → **difficulty** →
failure_injection → compliance → packaging): a baseline **probe** (scikit-learn
`logreg`/`tree`) measures how separable the label is, and an adaptive bisection
turns a single "difficulty dial" — **feature-observation noise** first, then
**label flips** — until the probe's holdout AUROC lands in the target band. The
calibrated frame is the shipped clean baseline. Automated in
`tests/unit/test_difficulty.py` + `test_difficulty_audit.py`.

### P0 — Run the difficulty unit tests
- **What it tests:** the probe (high on a separable label, ≈0.5 on noise, no
  crash on a constant label), tier→band mapping, **dial monotonicity** + nested
  label flips, the loop landing intermediate/advanced/kaggle in band, honest-miss
  reporting, determinism, and validation (non-binary label, unknown probe/tier,
  rejected knob, bad band).
- **Run:**
  ```powershell
  pytest tests/unit/test_difficulty.py -q
  ```
- **Expected:** `18 passed`.

### P0b — Critical audit (the report is honest about the shipped data)
- **What it tests:** an **independent** probe (split seeds the loop never used)
  reproduces the reported AUROC on the data on disk; feature-noise variance
  matches the closed form `Var = σ²(1+η²)` and `noise_to_signal = η²` (05 §5.4);
  **every named tier** lands a fresh baseline in its band (05 §5.3 / 13 §4); a
  harder tier needs more noise.
- **Run:**
  ```powershell
  pytest tests/unit/test_difficulty_audit.py -q
  ```
- **Expected:** `8 passed`.

### P1 — Calibrate a dataset to a band  (P4 engine gate)
- **What it tests:** the end-to-end stage tunes a strong label down into the
  target band and reports it honestly.
- **Run:**
  ```powershell
  datadoom run examples/difficulty-credit.datadoom.yaml --seed 17 --out .tmp_diff
  python -c "from datadoom.engine import load_spec, generate; d=generate(load_spec('examples/difficulty-credit.datadoom.yaml'), seed=17).difficulty; print('band', d['target']['band'], 'achieved %.3f'%d['achieved_metric'], 'met', d['band_met'], 'eta %.2f'%d['feature_noise'], 'rho %.2f'%d['label_flip'], 'iters', d['iterations'])"
  ```
- **Expected:** the run writes `data.csv` + `metadata.json`; the probe lands in
  the **advanced** band `[0.72, 0.80]` with `met True`, a non-zero feature-noise
  η, and a handful of iterations. (Clean, the label is ~0.9 AUROC — the loop adds
  noise to bring it down.)

### P2 — The calibration is byte-stable
- **What it tests:** the same `(spec_hash, seed)` reproduces the calibrated bytes
  (the probe is on the determinism path, so this guards the scikit-learn pin).
- **Run:**
  ```powershell
  datadoom verify examples/difficulty-credit.datadoom.yaml --seed 17
  ```
- **Expected:** `OK reproducible` — identical `data.csv` checksum across runs.

### P3 — Honest miss (no silent failure)
- **What it tests:** when the clean label is already harder than the band and
  there's no easing knob, the engine ships the pristine data and **flags** it.
- **Run:**
  ```powershell
  python -c "from datadoom.engine import parse_spec, generate; b={'datadoom_version':'1','name':'weak','seed':1,'rows':3000,'features':{'x':{'type':'numeric','dist':'normal','params':{'mean':0,'std':1}},'y':{'type':'boolean','rate':0.5}},'difficulty':{'target':'beginner','label':'y','probe':'logreg'}}; d=generate(parse_spec(b), seed=1).difficulty; print('met', d['band_met'], '| dial', d['dial'], '|', d['note'])"
  ```
- **Expected:** `met False | dial 0.0 |` followed by a note that the clean data is
  already harder than the band, so the pristine dataset is shipped as-is.

## Group Q — Web Difficulty UI (Phase 4)

### Q1 — Configure a difficulty target
- **What it tests:** the Canvas **Difficulty** view authors the `difficulty`
  block.
- **Files under test:** `frontend/src/components/DifficultyConfigurator.tsx`,
  `lib/difficulty.ts`, `pages/Canvas.tsx`.
- **Steps:** open a dataset with a binary label (boolean or 2-class categorical);
  in the Canvas toolbar pick the **Difficulty** tab; click **Enable difficulty
  targeting**; choose a tier (e.g. *Advanced*), confirm the label/probe, leave
  both knobs on; Generate.
- **Expected:** the tab shows an "enabled" dot once configured; the **band meter**
  previews the chosen AUROC band; if the dataset has *no* binary label the view
  shows a guidance message instead of the editor. The spec drawer now carries a
  `difficulty:` block.

### Q2 — Read the difficulty report
- **What it tests:** the Results **Difficulty** tab renders the achieved-vs-target
  calibration.
- **Files under test:** `frontend/src/components/DifficultyView.tsx`,
  `pages/Results.tsx`.
- **Steps:** open the completed run's Results; select the **Difficulty** tab
  (present only when the run had a target).
- **Expected:** an **achieved AUROC** headline + target band with an *in band* /
  *closest* badge; a `BandMeter` (0.5–1.0, tier bands + a marker at the achieved
  score); a stat row (probe, iterations, dial, feature-noise η, label-flip ρ,
  noise-to-signal, linear separability, class balance); the **active knobs**; and
  a **bisection trace** table (dial → probe AUROC → verdict). A miss shows the
  honest note. The **Evaluation** tab's "Achieved difficulty" card mirrors the
  headline.

### Q3 — Import a dataset from YAML
- **What it tests:** the web **Import from YAML** flow parses + validates raw
  spec text through the same engine path as the CLI, then creates the dataset.
- **Files under test:** `src/datadoom/api/routes/specs.py` (`/api/specs/parse`),
  `frontend/src/pages/Dashboard.tsx` (`ImportYamlModal`), `lib/api.ts`.
- **Steps:** on the Datasets page click **From YAML**; paste a spec (or upload /
  drag a `.yaml` file — try `examples/difficulty-credit.datadoom.yaml`); click
  **Validate**, then **Import & open Canvas**; Generate.
- **Expected:** **Validate** shows `✓ Valid · <spec_hash>…`; a malformed spec
  shows `✗ <message> @ <locator>` (e.g. a bad distribution → `features.a.dist`).
  Import lands on the Canvas with the spec loaded; Generate runs it normally.

## Group R — Latent features (`emit: false`)

A feature marked `emit: false` is **latent**: it drives sampling / the SEM and
appears in the true causal graph, but is *not shipped* (excluded from the CSV,
the difficulty probe, compliance, and correlation/MI). Automated in
`tests/unit/test_latent.py`.

### R0 — Run the latent unit tests
- **What it tests:** a latent column is excluded from the output but still drives
  its label; it stays in `causal_truth`; it's excluded from compliance; a hidden
  confounder correlates two observed children; the `emit` field is hash-safe when
  unset; and validation rejects a latent difficulty-label or a failure that
  targets a latent.
- **Run:**
  ```powershell
  pytest tests/unit/test_latent.py -q
  ```
- **Expected:** `7 passed`.

### R1 — Latent column is computed but not shipped
- **What it tests:** the credit example's `risk_score` (a latent that combines
  the drivers into the label's logit) drives `defaulted` yet never appears in the
  data — so the probe predicts from genuine observables, no redundant proxy.
- **Run:**
  ```powershell
  datadoom run examples/difficulty-credit.datadoom.yaml --seed 17 --out .tmp_lat
  python -c "import pandas as pd; print('columns:', list(pd.read_csv('.tmp_lat/data.csv').columns))"
  python -c "from datadoom.engine import load_spec, generate; ct=generate(load_spec('examples/difficulty-credit.datadoom.yaml'), seed=17).report.causal_truth; print('risk_score in true graph:', 'risk_score' in ct['nodes'])"
  ```
- **Expected:** the CSV columns are `income, debt_ratio, inquiries, defaulted`
  (**no** `risk_score`), but `risk_score in true graph: True` — the hidden node is
  still documented in the causal truth. (Clean up `.tmp_lat` after.)

### R2 — Author a latent in the Canvas
- **What it tests:** the Inspector can mark a column latent, and the UI reflects it.
- **Files under test:** `frontend/src/components/Inspector.tsx`,
  `components/TableCanvas.tsx`, `lib/difficulty.ts`.
- **Steps:** in the Canvas, select a column and toggle **Latent (not exported)**.
- **Expected:** a `latent` badge appears on the Table card; the column no longer
  offers as a Difficulty **label**; the spec drawer shows `emit: false`; and after
  generating, the column is absent from the data preview.

---

## Group S — Plugin system (Phase 5, task 17)

A plugin is a small class implementing one of the engine ABCs (re-exported as
`datadoom.plugin`). It is discovered at startup — from a Python entry point
(`datadoom.plugins` group) or a local `$DATADOOM_HOME/plugins/*.py` — and inserted
into the engine's own lookup tables, so it works in the CLI, the API, and the web
UI with **no core change**. The engine never imports `plugins/` (enforced by the
4th import-linter contract). Automated in `tests/plugin_contract/test_plugins.py`.

### S0 — Run the plugin contract tests
- **What it tests:** the 24 built-ins register with the right kind and pass the
  contract; a registered plugin distribution flows through a real run; local-dir
  and entry-point discovery; conflict-fail; and the checker catches a
  non-deterministic / RNG-impure / bad-schema plugin; scaffold→check for all 5 kinds.
- **Files under test:** `src/datadoom/plugins/` (`contracts.py`, `registry.py`,
  `loader.py`, `scaffold.py`), `src/datadoom/plugin.py`.
- **Run:**
  ```powershell
  pytest tests/plugin_contract -q
  ```
- **Expected:** `16 passed`.

### S1 — List the registry (built-ins are plugins too)
- **What it tests:** the registry seeds every core capability.
- **Run:**
  ```powershell
  datadoom plugin list
  ```
- **Expected:** a table of capabilities ending with `24 capabilities` — 6
  distributions, 5 structural functions, 8 failure modes, 3 exporters (csv/json/
  parquet), 2 probe models, each tagged `[core]`.

### S2 — Scaffold a plugin and check it
- **What it tests:** `datadoom plugin new` writes a working `datadoom-plugin-*`
  package, and `datadoom plugin check` runs the contract (interface, schema,
  determinism, RNG hygiene) green on the freshly scaffolded stub.
- **Run:**
  ```powershell
  datadoom plugin new distribution weibull --dir .tmp_plugins
  datadoom plugin check .tmp_plugins/datadoom-plugin-weibull/src/datadoom_plugin_weibull/__init__.py
  ```
- **Expected:** `created …\datadoom-plugin-weibull`, then a report with
  `[PASS]` on `interface`, `schema`, `determinism`, `rng_hygiene` and
  `OK  1 plugin(s) pass the contract`. (Clean up `.tmp_plugins` after.)

### S3 — A local plugin is usable in a run (zero engine change)
- **What it tests:** a `.py` dropped in `$DATADOOM_HOME/plugins/` is discovered and
  a spec can reference its distribution by name.
- **Run (PowerShell):**
  ```powershell
  $env:DATADOOM_HOME = "$PWD\.tmp_home"
  New-Item -ItemType Directory -Force "$env:DATADOOM_HOME\plugins" | Out-Null
  Copy-Item .tmp_plugins/datadoom-plugin-weibull/src/datadoom_plugin_weibull/__init__.py "$env:DATADOOM_HOME\plugins\weibull.py"
  datadoom plugin list   # weibull now shows tagged [local]
  ```
- **Expected:** `weibull` appears in the list tagged `[local]`; authoring a numeric
  feature with `dist: weibull` then `datadoom run` succeeds. (Reset `DATADOOM_HOME`
  and remove `.tmp_home` after.)

### S4 — The web Plugins gallery + `GET /api/plugins`
- **What it tests:** the API serves the live registry and the Canvas renders it.
- **Files under test:** `api/routes/plugins.py`, `frontend/src/pages/Plugins.tsx`,
  `frontend/src/lib/schemaForm.tsx`.
- **Steps:** `datadoom serve`, open **Plugins** in the sidebar.
- **Expected:** capabilities grouped by kind (Distributions / Structural functions /
  Failure modes / Exporters / Probe models) with `core` badges; a third-party plugin
  shows a `plugin · local`/`entrypoint` badge and its `param_schema` rendered as
  form controls. `GET /api/plugins` returns the same set as JSON.

---

## Group T — Exporters + Templates (Phase 5, task 18.1/18.2)

CSV/JSON/Parquet exporters and built-in domain templates. Automated in
`tests/unit/test_export_formats.py`, `tests/unit/test_templates.py`, and `tests/api`.

### T0 — Run the exporter + template tests
- **What it tests:** JSON/Parquet are byte-stable + round-trip; the pipeline writes
  every requested format per version; unknown formats are rejected; and all 3
  templates parse/validate/generate (latents excluded).
- **Run:**
  ```powershell
  pytest tests/unit/test_export_formats.py tests/unit/test_templates.py -q
  ```
- **Expected:** `17 passed`.

### T1 — Export JSON + Parquet from the engine (P5 gate: export Parquet)
- **What it tests:** a multi-format run writes `data.csv` + `data.json` +
  `data.parquet`, each byte-stable on the pinned path.
- **Files under test:** `engine/export/{json,parquet}_exporter.py`, `engine/pipeline.py`.
- **Run (PowerShell):**
  ```powershell
  pip install -e ".[parquet]"   # one-time: pyarrow for the parquet format
  datadoom template use fraud-detection --out .tmp_fraud.datadoom.yaml
  # edit export.formats to [csv, json, parquet], or rely on the web Generate modal
  ```
- **Expected:** with `export.formats: [csv, json, parquet]`, the run dir holds all
  three `data.*` files; re-running with the same seed reproduces identical bytes
  for each. Without the parquet extra, a parquet run errors with an install hint
  (CSV/JSON still work).

### T2 — Start from a template (P5 gate: template in one click)
- **What it tests:** the built-in templates are listed and a dataset can be created
  from one.
- **Run:**
  ```powershell
  datadoom template list                 # 8 templates
  datadoom template show customer-churn   # prints the spec YAML
  datadoom template use customer-churn --out .tmp_churn.datadoom.yaml
  datadoom run .tmp_churn.datadoom.yaml --seed 1 --out .tmp_run
  ```
- **Expected:** `8 templates`; `template show` prints valid YAML; `template use`
  writes the file; the run completes (the latent `satisfaction` is **not** in
  `data.csv`). (Clean up the `.tmp_*` files after.)

### T3 — Web: Templates gallery + output formats
- **What it tests:** the gallery creates a dataset in one click, and the Generate
  modal offers output formats.
- **Files under test:** `frontend/src/pages/Templates.tsx`, `pages/Canvas.tsx`
  (Generate modal), `components/ExportModal.tsx`.
- **Steps:** `datadoom serve` → **Templates** → **Use this template** (opens the
  Canvas as a new dataset) → **Generate** → tick **JSON**/**Parquet** → generate →
  Results **Export** lists each `data.<format>` for download.
- **Expected:** the dataset opens pre-populated; CSV is locked-on in the formats
  list; after generating, the chosen formats appear as downloadable artifacts.

---

## Group U — Time-series + adapters + AI manifest (Phase 5, task 18.3/18.4/18.5)

### U0 — Run the new Phase-5 tests
- **What it tests:** time-series generation/validation, framework adapters, and the
  capabilities manifest.
- **Files under test:** `engine/timeseries.py`, `adapters/`, `engine/reference.py`.
- **Run:** `pytest tests/unit/test_timeseries.py tests/unit/test_adapters.py tests/unit/test_reference.py -q`
- **Expected:** all pass (torch/HF converter tests **skip** if those extras aren't
  installed — that's expected).

### U1 — Generate + audit a time-series (05 §6)
- **What it tests:** the additive `Xₜ = T(t)+S(t)+AR(p)+εₜ`; row order is the time
  axis; a time-series can drive a causal child. **File:** `examples/timeseries-sensor.datadoom.yaml`.
- **Run:**
  ```powershell
  datadoom run examples/timeseries-sensor.datadoom.yaml --seed 7 --out .tmp_ts
  python -c "import pandas as pd, numpy as np; d=pd.read_csv('.tmp_ts/data.csv'); t=np.arange(len(d)); A=np.vstack([t,np.ones_like(t)]).T; s,b=np.linalg.lstsq(A,d['temperature'].to_numpy(),rcond=None)[0]; print('trend slope=%.4f (target 0.002)'%s); print('reading~temp slope=%.3f (target 1.8)'%np.polyfit(d['temperature'],d['reading'],1)[0])"
  ```
- **Expected:** `cols ['temperature','reading']`; recovered trend slope ≈ 0.002;
  `reading` vs `temperature` slope ≈ 1.8 (the linear causal child). Run
  `datadoom verify examples/timeseries-sensor.datadoom.yaml --seed 7` → reproducible.

### U2 — Load a run into pandas / a framework (adapters)
- **What it tests:** `datadoom.adapters` reads a generated run; framework converters
  exist (torch/tf/hf behind optional extras). **Files:** `adapters/loaders.py`,
  `adapters/frameworks.py`.
- **Run:**
  ```powershell
  datadoom run examples/failure-fraud.datadoom.yaml --seed 42 --out .tmp_run
  python -c "from datadoom.adapters import load_dataframe, numeric_feature_columns as nfc; c=load_dataframe('.tmp_run'); inj=load_dataframe('.tmp_run', version='injected'); print('clean nulls', int(c.isna().sum().sum()), '| injected nulls', int(inj.isna().sum().sum())); print('model cols', nfc(c, exclude=['is_fraud']))"
  ```
- **Expected:** the clean frame has 0 nulls, the injected frame has > 0 (the
  failures); `numeric_feature_columns` lists the numeric/bool columns minus the
  target. `to_torch_dataset`/`to_tf_dataset`/`to_hf_dataset` raise an actionable
  `pip install 'datadoom[…]'` hint if the backend is absent.

### U3 — AI spec-authoring manifest
- **What it tests:** the machine-readable capabilities manifest the LLM doc points
  at, built from the live registries. **Files:** `engine/reference.py`, CLI/API.
- **Run:**
  ```powershell
  datadoom spec-reference | python -c "import sys,json; d=json.load(sys.stdin); print('feature_types', list(d['feature_types'])); print('distributions', [x['name'] for x in d['distributions']]); print('failures', [x['type'] for x in d['failure_modes']]); print('tiers', list(d['difficulty']['tiers']))"
  ```
- **Expected:** `feature_types` includes `timeseries`; all 6 distributions, 8
  failure modes, and 4 difficulty tiers listed. `GET /api/spec-reference` returns the
  same JSON. (Installed plugins appear automatically.) See
  `docs_v2/21_LLM_Spec_Authoring_Reference.md` for the AI authoring contract and
  `docs_v2/20_YAML_Authoring_Guide.md` for the beginner walkthrough.

---

## Group V — Hackathon mode (Phase 5, task 18.6)

> Four enterprise-grade challenge templates surfaced under a `level: hackathon`
> facet. Data-only/additive — they exercise the engine by composition (deep causal
> DAG + latent confounder + stacked failures + calibrated difficulty), not new
> features.

### V0 — List the hackathon pack
- **What it tests:** the `level` catalog facet + the CLI `--level` filter.
- **Files under test:** `templates/__init__.py`, `cli/main.py`.
- **Run:** `datadoom template list --level hackathon`
- **Expected:** the four flagships only —
  `credit-default-challenge` (Finance), `clinical-deterioration` (Healthcare),
  `predictive-maintenance` (Industrial IoT), `telecom-churn-challenge` (Telecom) —
  each tagged `[hackathon]`; trailer `4 templates`. `datadoom template list` (no
  flag) shows all 12 (8 starters + 4 flagships); `--level starter` shows the 8.

### V1 — Validate + run + verify every flagship
- **What it tests:** each challenge parses, validates, generates, and is
  byte-reproducible (the determinism contract) with its clean **and** injected
  variants. **Files:** `templates/*.datadoom.yaml`.
- **Run:**
  ```powershell
  foreach ($t in "credit-default-challenge","clinical-deterioration","predictive-maintenance","telecom-churn-challenge") {
    datadoom template use $t --out "$t.datadoom.yaml"
    datadoom validate "$t.datadoom.yaml"
    datadoom verify   "$t.datadoom.yaml" --seed 1
  }
  ```
- **Expected:** every `validate` prints `OK  spec_hash=…`; every `verify` prints
  `OK  reproducible (…)`. (Compliance legitimately reads low on the
  difficulty-calibrated ones — predictor blurring is intended, see Group P.)

### V2 — Confirm realistic labels + difficulty bands met
- **What it tests:** the SEM produces non-degenerate, realistic **minority-class**
  labels and the difficulty stage lands each calibrated label in its target AUROC
  band. **Files:** `engine/difficulty/`, the templates.
- **Run:**
  ```powershell
  python -c "import datadoom as dd; [print(f'{f:26} pos={(lambda c: int(c.sum())/len(c))(dd.generate(dd.load_spec(p),seed=1).frame[L]):.1%}', (lambda d: f\"{d['target']['tier']} achieved={d['achieved_metric']:.3f} met={d['band_met']}\" if d else 'no-difficulty')(dd.generate(dd.load_spec(p),seed=1).difficulty)) for f,p,L in [('credit','src/datadoom/templates/credit_default_challenge.datadoom.yaml','defaulted'),('clinical','src/datadoom/templates/clinical_deterioration.datadoom.yaml','deterioration'),('maint','src/datadoom/templates/predictive_maintenance.datadoom.yaml','needs_maintenance'),('telecom','src/datadoom/templates/telecom_churn_challenge.datadoom.yaml','churned')]]"
  ```
- **Expected:** positive rates ≈ credit 33% / clinical 33% / maintenance 29% /
  telecom 26% (realistic minorities, not 50/50 or degenerate); credit & clinical
  `advanced met=True` (≈0.74–0.77), telecom `kaggle met=True` (≈0.64), maintenance
  `no-difficulty` (it showcases time-series + drift + leakage instead).

### V3 — Inspect the enterprise composition (one example)
- **What it tests:** the deep causal DAG + latent confounder + stacked failures are
  really present. **File:** `credit_default_challenge.datadoom.yaml`.
- **Run:** `datadoom run src/datadoom/templates/credit_default_challenge.datadoom.yaml --seed 1 --out .tmp_hack`
- **Expected:** `data.csv` has **no** `risk_score` column (it's latent, `emit:false`)
  but the causal report (`metadata.json` is clean; the true graph shows in the web
  Results **Causal Graph** tab) carries the `…→annual_income→risk_score→defaulted`
  chain; `data.injected.csv` additionally has a planted `collections_flag`
  (leakage) and NaNs in `annual_income`/`debt_to_income`. The `meta.challenge`
  block (problem statement, metric, gotchas) rides along in the spec.

### V4 — Web gallery
- **What it tests:** the gallery leads with hackathon challenges, badges them, and
  filters by level. **Files:** `frontend/src/pages/Templates.tsx`, `lib/types.ts`.
- **Run:** `datadoom serve` → open **Templates**.
- **Expected:** the four flagships sort first, each with a Trophy **Hackathon**
  badge; the **All / Hackathon / Starter** filter narrows the grid; "Use this
  template" creates a dataset and opens it in the Canvas (Table/Graph/Failures/
  Difficulty views all populated from the challenge spec).

---

## Group W — Column Guide (per-column profile + ML advice)

> "Data exploration made simple." For every column the engine reports its type,
> summary statistics, causal parents, the failure modes that hit it (with realized
> magnitude), and — for each issue — how to handle it when building a model.
> Files: `engine/profile.py`, `engine/advice.py`, `engine/reports.py`,
> `components/ColumnGuideView.tsx`, `pages/Results.tsx`.

### W0 — Run the profile/advice unit tests

- **Tests:** roles, stats, failure attribution, class imbalance, advice, determinism.
- **Run:** `pytest tests/unit/test_profile.py -q`
- **Expected:** all green. The suite asserts each failure mode is attributed to the
  right column, leakage is **critical** ("drop before training"), the post-injection
  missing rate matches the realized rate, and two runs at the same seed produce a
  byte-identical profile.

### W1 — Read the profile from the engine

- **What it tests:** the report bundle carries a `profile` section end-to-end.
- **Run:**
  ```powershell
  python -c "from datadoom import load_spec, generate; p = generate(load_spec('examples/failure-fraud.datadoom.yaml'), seed=42).report.profile; import json; print(json.dumps(p['summary'], indent=2)); [print(c['name'], c['role'], [i['mode'] for i in c['issues']]) for c in p['columns']]"
  ```
- **Expected:** summary shows `label: is_fraud`, `critical_issues: 1`; `income` →
  derived with `[mnar, drift]`, `age` → `[feature_noise, mcar]`, `is_fraud` →
  `[label_noise]`, `fraud_score` → `leakage_proxy` with `[leakage]`,
  `education` → no issues.

### W2 — Read the Column Guide in the browser

- **What it tests:** the web surface.
- **Run:** `datadoom serve` → run the `failure-fraud` spec → open **Results → Column Guide**.
- **Expected:** a summary banner (Columns / With issues / Critical), then one card per
  column. Cards with issues show a coloured edge + severity badge; each issue card
  has the realized magnitude, a plain-language explanation, a highlighted **"How to
  handle it"** recommendation, and a list of concrete ML techniques. The tab shows a
  warning-coloured issue-count badge.

---

## Group X — Documentation site (Phase 6, task 19.1)

> The public docs site is built with mkdocs-material from `docs_site/`, whose
> pages **embed** the authoritative `docs_v2/` sources (single source of truth)
> via the include-markdown plugin. Files: `mkdocs.yml`, `docs_site/*.md`,
> `.github/workflows/docs.yml`, operator runbook `docs_v2/22_Release_and_Publishing_Runbook.md`.

### X0 — Install the docs tooling

- **What it tests:** the `docs` optional-dependency group resolves.
- **Run:** `pip install -e ".[docs]"`
- **Expected:** installs `mkdocs`, `mkdocs-material`, and
  `mkdocs-include-markdown-plugin` with no errors.

### X1 — Strict build (what CI runs)

- **What it tests:** every page renders and every internal link resolves.
- **Run:** `mkdocs build --strict`
- **Expected:** `Documentation built in …` and **exit code 0** with **no
  WARNING/INFO anchor lines**. (A GitHub-compatible `toc` slugify in `mkdocs.yml`
  makes the embedded `docs_v2/` anchors resolve; the Material 2.0 banner is the
  only console notice.)

### X2 — Local preview

- **What it tests:** the site looks right and the embedded guides appear in full.
- **Run:** `mkdocs serve` → open `http://127.0.0.1:8000`.
- **Expected:** Home (quickstart), **Authoring** (the full doc 20 inline),
  **LLM / agent reference** (the full doc 21 inline), Spec reference, Plugins,
  Architecture, and an Examples gallery listing the six example specs + the
  12 templates. The Paper/Ink palette toggle works.

### X3 — Publish (operator, GitHub) — *manual, not run here*

- **What it tests:** GitHub Pages goes live.
- **Run:** follow `docs_v2/22_Release_and_Publishing_Runbook.md` §1 — merge to
  `main` (the Docs workflow `gh-deploy`s), then **Settings → Pages → Deploy from
  branch: `gh-pages` / root**.
- **Expected:** the site is live at `https://<owner>.github.io/datadoom/`.

---

## Group Y — Release artifacts + Docker (Phase 6, task 19.2)

> Tag-driven release automation and a runnable server image. Files:
> `.github/workflows/release.yml`, `Dockerfile`, `.dockerignore`,
> `pyproject.toml` (`[tool.hatch.build]` artifacts), operator steps in
> `docs_v2/22_Release_and_Publishing_Runbook.md`.

### Y0 — Build the distributions

- **What it tests:** sdist + wheel build, and that the **web Canvas + templates
  ship inside both** (the wheel is built from the sdist, so the sdist must carry
  the gitignored `webdist/`).
- **Run:**
  ```powershell
  pip install build twine
  python -m build
  python -m twine check dist/*
  ```
- **Expected:** `Successfully built datadoom-….tar.gz and …-py3-none-any.whl`;
  `twine check` → both **PASSED**. Confirm the Canvas is bundled:
  ```powershell
  python -c "import zipfile,glob; n=zipfile.ZipFile(glob.glob('dist/*.whl')[0]).namelist(); print('webdist:', any(x.endswith('webdist/index.html') for x in n)); print('templates:', sum(1 for x in n if x.endswith('.yaml') and 'templates' in x))"
  ```
  → `webdist: True`, `templates: 12`.

### Y1 — Smoke-test the built wheel (clean venv)

- **What it tests:** the published wheel installs and runs standalone — exactly
  what the release workflow asserts.
- **Run:**
  ```powershell
  python -m venv .tmp_smoke
  .\.tmp_smoke\Scripts\python.exe -m pip install (Get-ChildItem dist\*.whl).FullName
  .\.tmp_smoke\Scripts\datadoom.exe version
  .\.tmp_smoke\Scripts\datadoom.exe run examples/tabular-basic.datadoom.yaml --seed 7 --out .tmp_smoke_run
  .\.tmp_smoke\Scripts\python.exe -c "import importlib.resources as r; print((r.files('datadoom')/'webdist'/'index.html').is_file())"
  ```
- **Expected:** version prints, the run writes artifacts, and the Canvas check
  prints `True`. (Clean up: `Remove-Item -Recurse -Force .tmp_smoke, .tmp_smoke_run`.)

### Y2 — Docker image build + run

- **What it tests:** the multi-stage image (Node builds the Canvas, slim Python
  runtime) builds and serves.
- **Run:** (needs a running Docker daemon)
  ```bash
  docker build -t datadoom:local .
  docker run --rm datadoom:local datadoom version
  docker run --rm -p 8000:8000 -v datadoom-data:/data datadoom:local
  ```
- **Expected:** the build completes; `datadoom version` prints; the server
  reports `DataDoom serving on http://0.0.0.0:8000` and the Canvas loads at
  `http://localhost:8000`.

### Y3 — Publish (operator) — *manual, not run here*

- Follow `docs_v2/22_Release_and_Publishing_Runbook.md` §2–4: register the PyPI
  Trusted Publisher + `pypi` GitHub Environment, then
  `git tag -s vX.Y.Z && git push origin main --tags`.
- **Expected:** the Release workflow goes green; PyPI + GHCR show the new version;
  `gh attestation verify dist/*.whl --owner SanthoshReddy352` passes.

---

## Group Z — Reproducibility hardening, perf budget, accessibility (Phase 6, task 19.3)

> Files: `.github/workflows/repro-matrix.yml`, `tests/determinism/test_determinism.py`,
> `tests/golden/checksums.json`, `tests/perf/test_perf_budget.py`,
> `pyproject.toml` (`perf` marker), `README.md`, and the frontend shared
> primitives (`Modal.tsx`, `Toaster.tsx`, `Layout.tsx`, `ui.tsx`).

### Z0 — Platform-keyed golden checksum

- **What it tests:** the bitwise golden gate **asserts** on a recorded platform
  and **skips with instructions** on an unrecorded one (honest per doc 13:
  bitwise within an OS/arch, statistical across).
- **Run:** `pytest tests/determinism -v`
- **Expected:** all green. On Windows/AMD64 + numpy 2.4.6,
  `test_golden_checksum_pinned` **asserts** against
  `Windows-AMD64-numpy-2.4.6`. On another platform it **skips** printing the exact
  `"<platform>-numpy-<ver>": "<sha>"` line to add to `tests/golden/checksums.json`.
  The CI repro matrix pins numpy and prints this value per cell in the job summary.

### Z1 — Perf budget (opt-in, non-gating)

- **What it tests:** generation throughput hasn't regressed (catches an accidental
  per-row hot path), without adding flakiness to the default suite.
- **Run:** `pytest -m perf -v`
- **Expected:** `test_generate_50k_rows_within_budget` passes (50k-row causal
  generate well under the 45 s / 2000 rows-per-s budget). A plain `pytest` run
  **deselects** it (`… 1 deselected`).

### Z2 — Accessibility (manual, in the browser)

- **What it tests:** keyboard and screen-reader basics on the shared UI.
- **Run:** `datadoom serve`, then with the keyboard only:
  - Press **Tab** on any page → the first stop is a visible **"Skip to content"**
    link that jumps focus to the main region.
  - Open any modal (e.g. Create dataset) → focus moves into the dialog, **Tab
    cycles within it** (never reaches the page behind), **Esc** closes it, and
    focus **returns** to the trigger. Confirm dialogs focus the confirm button.
  - Trigger a toast → it's announced (a screen reader reads it); its dismiss
    button is reachable and labelled.
  - Icon-only buttons (row "More actions", undo/redo, sidebar collapse) expose a
    name (hover title / `aria-label`); the sidebar nav, breadcrumb, and main are
    labelled landmarks.
- **Expected:** all the above hold; no keyboard trap outside modals.

---

## Appendix — One-shot "is everything healthy?" sweep

With the venv activated:

```powershell
cd "D:\Hack Forge"
.\.venv\Scripts\Activate.ps1

ruff check src tests        # A1  -> All checks passed!
lint-imports               # A2  -> 5 kept, 0 broken
mypy                       # A3  -> Success: no issues found in 89 source files
pytest                     # B0  -> 322 passed, 2 skipped (torch/hf), 1 deselected (perf)
datadoom plugin list                                               # S1 -> 24 capabilities
datadoom template list                                             # T2 -> 8 templates
datadoom spec-reference > $null                                    # U3 -> manifest emits
datadoom verify examples/tabular-basic.datadoom.yaml --seed 7      # C4 -> OK reproducible
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42      # J1 -> OK reproducible
datadoom verify examples/failure-fraud.datadoom.yaml --seed 42     # M3 -> OK reproducible
datadoom verify examples/people-realistic.datadoom.yaml --seed 42  # G5b -> OK reproducible
datadoom verify examples/difficulty-credit.datadoom.yaml --seed 17 # P2 -> OK reproducible
datadoom verify examples/timeseries-sensor.datadoom.yaml --seed 7  # U1 -> OK reproducible
```

If all are green, Phase 0, the Phase-1 server/web tests, the Phase-2 causal
engine, the Phase-3 failure engine, the Phase-4 difficulty engine, **and all of
Phase 5** (plugins, exporters + templates, time-series, framework adapters, and the
AI spec-authoring manifest) are healthy. For the in-browser P1 exit gate, build the
SPA (I1) and walk the loop (I2–I3); for the P2 engine gate, run Group **J**; for the
P3 engine gate, run Group **M**; for the P4 engine gate, run Group **P**; for the
plugin gate, run Group **S**; for the templates + Parquet gate, run Group **T**; for
time-series / adapters / the AI manifest, run Group **U**.
