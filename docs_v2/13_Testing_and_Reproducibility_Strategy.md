# 13 — Testing & Reproducibility Strategy

> Reproducibility is DataDoom's headline guarantee, so it gets a first-class, *tested* strategy — not a slogan. Obeys `00_README_Index.md`. Math in `05`; determinism rules in `11 §6`.

---

## 1. Testing Philosophy

- **The guarantee must be executable.** "Same spec + seed → identical dataset" is a CI assertion, not marketing.
- **The pure engine is the most-tested layer.** It has no web/DB, so it's fast and exhaustively unit-testable.
- **Honesty is tested too.** We assert that compliance reporting behaves as documented and that we do *not* secretly refit distributions.
- **Plugins are tested by contract**, so the ecosystem stays deterministic.

---

## 2. Test Layers

| Layer | Location | What it covers |
|---|---|---|
| Unit | `tests/unit/` | each engine module: rng, dist, causal, failure, difficulty, export, spec validation |
| Determinism | `tests/determinism/` | same `(spec_hash, seed)` → identical checksums; namespace independence |
| Golden | `tests/golden/` | curated specs → expected checksums recorded per OS/Python |
| Plugin contract | `tests/plugin_contract/` | every registered plugin: interface completeness, schema validity, determinism |
| API | `tests/api/` | FastAPI routes, validation envelopes, WS event stream |
| E2E | `tests/e2e/` | spec → run → artifacts → report, via CLI and via API |
| Property-based | (hypothesis) | invariants over random valid specs |

---

## 3. The Reproducibility Guarantee — Precisely

**Claim (scoped):** On the **pinned path** — single-threaded BLAS, pinned numpy/scipy/sklearn versions, CPU — for identical `(spec_hash, seed)`, every produced artifact's SHA256 is identical, on the same OS/arch.

**We do NOT claim** bitwise identity across: thread counts, GPUs, different numpy/BLAS builds, or different CPU architectures (FP reductions differ). We *do* claim **statistical** reproducibility there (same distributions, same structure).

### 3.1 Determinism unit tests
- Run generation twice in-process with the same seed → assert array-equal frames and equal checksums.
- Add a feature/edge → assert *unrelated* features' streams are unchanged (namespace isolation, `05 §1.2`).
- Assert no banned calls in the data path (AST lint: no `random`, `np.random.` globals, `uuid4`, `time.time` under `engine/` data path).

### 3.2 Cross-OS / cross-Python repro matrix (CI)
`.github/workflows/repro-matrix.yml` runs golden specs on:
`{windows, macos, linux} × {py3.11, py3.12}` with the pinned dependency set.
- **Within the same (OS, py)**: assert checksums match the recorded golden value → **bitwise guarantee**.
- **Across OS/py**: assert **statistical** equivalence (distribution params within tolerance, identical causal structure, identical shapes) rather than bitwise — and record any cross-platform checksum drift as a known-tolerance note.
- A bitwise mismatch within a pinned (OS, py) cell **fails the build**.

### 3.3 Golden specs
- A small, diverse set of `*.datadoom.yaml` covering numeric/categorical/datetime, causal SEM, each failure mode, difficulty targeting.
- Expected checksums stored as `tests/golden/<spec>/<os>-<py>.sha256`.
- Regenerating goldens is a deliberate, reviewed action (`make goldens`), never automatic — so an accidental determinism break can't silently rewrite the baseline.

---

## 4. Statistical Correctness Tests

- **Distribution fit:** generate large `n`, assert empirical params within tolerance of target (mean/std/rate), and KS p-value distribution behaves correctly (≈5% rejection at α=0.05 across many seeds — proving we're *not* refitting).
- **Anti-overfit assertion:** explicitly test that compliance reporting does **not** modify parameters (run with a "would-fail" seed; assert params unchanged and the failure is *reported*, not corrected).
- **SEM correctness:** known linear DAG → assert recovered coefficients/correlations match the structural weights within noise tolerance; assert topological execution order.
- **Failure injection:** assert MCAR rate ≈ p; MAR/MNAR missingness correlates with driver as specified; leakage `into` has high MI with target; drift shifts params over index.
- **Difficulty calibration:** for each named tier, assert the achieved probe metric lands in the documented band across a sample of generated datasets (this is what *validates* the tier→band table in `05 §5.3`).

---

## 5. Plugin Contract Tests

Run automatically for built-ins and available via `datadoom plugin check`:
1. **Interface:** required methods present; `param_schema` is valid JSON-schema.
2. **Determinism:** call twice with the same injected seeded `rng` → identical output. (This is how we keep the ecosystem reproducible — a plugin that fails this can't ship.)
3. **RNG hygiene:** static check that the plugin uses only the injected `rng`.
4. **Schema/UI:** the declared schema renders to a valid form (validated against the UI renderer's contract).

---

## 6. API & E2E Tests

- **API:** every route's happy path + key error (422 with correct `locator`, 404, 409 idempotency). WS test asserts the canonical stage sequence and a terminal `completed`/`failed`.
- **E2E:** `datadoom run examples/fraud.datadoom.yaml --seed 42 --out tmp/` → assert artifacts exist, checksums match golden, `report.html` + `metadata.json` present, and `datadoom verify` passes.
- **CLI ↔ API parity:** the same spec produces the same checksums whether run via CLI, API, or `datadoom.generate()` (proves the single-pipeline invariant, `03 §10`).

---

## 7. Performance / Regression Budgets

- Benchmark: 50k×20 tabular < 10 s; 1M×20 streamed within RAM cap (`01 §8`, `12`).
- A CI perf job tracks throughput; a >25% regression flags the PR (warn, not hard-fail, to avoid noise on shared runners).

---

## 8. Coverage & Gates (CI must pass to merge)

1. Ruff lint + format clean.
2. mypy strict on `engine/` (and `store/api` typed).
3. `import-linter` layering (`10 §4`) passes.
4. Unit + determinism + plugin-contract + API tests green.
5. Repro matrix: bitwise within pinned cells; statistical across cells.
6. Frontend: `tsc --noEmit`, ESLint, component tests for graph/schema editors.
7. Coverage threshold on `engine/` (e.g. ≥ 90%).

---

## 9. Manual / Exploratory QA Checklist (per release)

- Fresh `pip install datadoom` in a clean venv on each OS → `datadoom` opens the app → create dataset → generate → export → `datadoom verify` round-trips.
- Offline test: disconnect network, confirm full local flow works.
- Plugin install test: `pip install` a sample plugin → it appears in the UI dropdowns.
- Upgrade test: open a DB/spec created by the previous release → Alembic auto-upgrade succeeds; old specs still validate.

---

## 10. Reproducibility Metric (tracked)

- `reproducibility_failure_rate` = bitwise mismatches / total pinned-cell repro checks, target **< 0.1%** (`01 §8`).
- Surfaced in the repro-matrix CI summary and the project README badge.
