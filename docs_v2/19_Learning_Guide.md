# 19 — Learning Guide

> Onboarding for new contributors (and your future self). The fastest path from "I cloned the repo" to "I shipped a change." Obeys `00_README_Index.md`.

---

## 1. Who This Is For

- **New contributors** who want to fix a bug, add a distribution, or build UI.
- **Plugin authors** extending DataDoom without touching core.
- **You, six months from now**, re-orienting on the project.

You don't need to be an expert in all of: statistics, causal inference, FastAPI, and React. Pick a track (§5) and learn the rest as needed.

---

## 2. The 30-Minute Mental Model

Read these, in order, for the big picture:
1. `00_README_Index.md` — the locked decisions + canonical pipeline/entities. **Most important.**
2. `01_PRD.md` §1–§5 — what we're building and why open source.
3. `03_Technical_Architecture.md` §1–§4 — the modular monolith + the 9-stage pipeline.
4. `04_DataDoom_Spec_Reference.md` §1–§5 — the spec is the center of gravity; everything serializes to/from it.

If you remember only three things:
- **The spec + seed determine the dataset, reproducibly.**
- **The engine is pure** (no web/DB) and the **pipeline** is the only way to make data.
- **We report honest statistics** — we never fake distribution compliance.

---

## 3. Set Up Your Dev Environment

```bash
git clone <repo> && cd datadoom
python -m venv .venv && . .venv/bin/activate     # (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"
pre-commit install
cd frontend && npm ci && npm run build && cd ..   # builds the bundled UI
datadoom                                           # launches the app at http://localhost:8000
```

Run the gates so you know green looks like green:
```bash
ruff check . && mypy src/datadoom/engine && pytest -q
lint-imports                                       # import-linter (architecture layering)
```

Generate something headless to see determinism:
```bash
datadoom run examples/fraud.datadoom.yaml --seed 42 --out /tmp/d1
datadoom run examples/fraud.datadoom.yaml --seed 42 --out /tmp/d2
datadoom verify examples/fraud.datadoom.yaml --against /tmp/d1/clean/full.csv
# checksums of /tmp/d1 and /tmp/d2 match → that's the guarantee.
```

---

## 4. Concept Primer (just enough theory)

- **Seeded determinism** — we derive every random stream from `sha256(spec_hash + seed + namespace)` so the same inputs always reproduce the same data. (`05 §1`)
- **Distributions & KS test** — we sample from a distribution and *check* the fit with a Kolmogorov–Smirnov test. The KS test **reports**; it does not "fix" anything. (`05 §2`)
- **Causal DAG / SEM** — features form a directed acyclic graph; each derived feature = a function of its parents + noise, computed in topological order. This is what makes the data *structured*, not just random columns. (`05 §3`)
- **Failure injection** — controlled corruption (missingness MCAR/MAR/MNAR, noise, drift, leakage) to stress-test ML pipelines, always alongside a clean baseline. (`05 §4`)
- **Difficulty targeting** — we train a small "probe" model and tune noise/imbalance until its score lands in a target band; difficulty is *measured*, not asserted. (`05 §5`)

New to causal inference? You only need: "edges mean "depends on," no cycles, compute parents before children." The math is in `05` when you want depth.

---

## 5. Pick a Track

### Track A — Engine / algorithms (Python, NumPy, stats)
- Read: `05`, `04 §4–§7`, `13 §3–§4`.
- Good first issues: add a built-in distribution; improve a compliance report; add a failure mode.
- Golden rule: use the injected `rng`; write a determinism test (`13 §5`). Run `pytest tests/determinism`.

### Track B — Backend / API (Python, FastAPI, SQLAlchemy)
- Read: `06`, `07`, `08`, `03 §3`.
- Good first issues: a new endpoint; better validation errors with `locator`; SSE fallback polish.
- Golden rule: keep `engine/` framework-free; specs are immutable (edits = new version).

### Track C — Frontend (React, TypeScript, React Flow)
- Read: `02`, `08 §7` (WS), `09 §6` (plugin schema rendering).
- Good first issues: inspector controls for a feature type; correlation heatmap; live diff preview.
- Golden rule: watch `useEffect` deps around the graph + WebSocket to avoid render loops (`18 §4`).

### Track D — Plugins (extend without touching core)
- Read: `09` end-to-end.
- Start: `datadoom plugin new --kind distribution my_dist` → implement `sample` with the injected `rng` → `datadoom plugin check ./`.
- Publish as `datadoom-plugin-*`; it auto-appears in the UI.

---

## 6. Make Your First Change (worked example: add the Weibull distribution)

1. `engine/dist/builtins.py`: add a `WeibullDistribution(Distribution)` with `param_schema`, `validate`, `sample` (using `rng.weibull`), `cdf`.
2. Register it among built-ins.
3. `tests/unit/test_dist.py`: assert empirical params ≈ target; KS p-value sane.
4. `tests/determinism`: same seed → identical samples.
5. The UI picks it up automatically (schema-rendered dropdown).
6. `ruff` + `mypy` + `pytest` green → commit with `Signed-off-by` → PR using the template.

That's the whole loop: **interface → implementation → tests → green → PR.**

---

## 7. Where Things Live (quick map)

| I want to change… | Go to |
|---|---|
| how randomness is seeded | `engine/rng.py` (`05 §1`) |
| the spec fields | `engine/spec/` + update `04` |
| a distribution | `engine/dist/builtins.py` (`09 §4.1`) |
| causal/structural functions | `engine/causal/functions.py` |
| a failure mode | `engine/failure/builtins.py` |
| difficulty/probes | `engine/difficulty/` |
| export format | `engine/export/` or a plugin |
| an API route | `api/routes/` (`08`) |
| DB schema | `store/models.py` + Alembic (`07`) |
| a UI screen | `frontend/src/pages|components/` (`02`) |
| build/packaging | `pyproject.toml`, `10 §3` |

---

## 8. Glossary

- **Spec** — the declarative `*.datadoom.yaml` that fully determines a dataset.
- **spec_hash** — SHA256 of the canonical spec (seed excluded); identity of a configuration.
- **Seed** — integer fixing all randomness; `(spec_hash, seed)` → reproducible artifact.
- **RunContext** — in-memory state threaded through the pipeline.
- **Pipeline** — the 9 canonical stages; the only way to produce an artifact.
- **Artifact** — an output file (clean/injected × split × format) with a checksum.
- **Probe model** — a small baseline model used to *measure* difficulty.
- **Pinned path** — single-threaded, version-pinned CPU execution where the bitwise guarantee holds.
- **DDEP** — DataDoom Enhancement Proposal, for changes to locked decisions / spec / plugin API (`15 §3.3`).

---

## 9. Getting Help & Contributing Back

- Read `15_Open_Source_Governance.md` for the contribution flow (DCO sign-off, PR template, gates).
- Ask in GitHub Discussions; tag issues `good first issue`/`help wanted` to find starter work.
- Improving these docs **is** a contribution — if something here confused you, fix it for the next person.
