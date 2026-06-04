# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this project is

**DataDoom** is a local-first, open-source engine for **controllable, reproducible
synthetic data**: you design a dataset (distributions, causal structure,
difficulty, failure modes) as a single spec file and regenerate it identically,
forever, from `(spec_hash, seed)`. Primary surface (later) is a web Canvas; the
CLI is the launcher/automation surface.

- **Authoritative design:** `docs_v2/` (start at `docs_v2/00_README_Index.md`,
  which holds the **locked global decisions** every other doc obeys). The legacy
  `Docs/` set is superseded — do not build from it.
- **Current state:** see **[status.md](status.md)**. Phases 0–4 are complete:
  deterministic core, server + web Canvas, the causal engine (`engine/causal/`),
  the failure-injection engine (`engine/failure/`), and difficulty targeting
  (`engine/difficulty/`) — each with its web surface. **Phase 5 is underway:** the
  **plugin system** (`plugins/`, task 17) and **exporters + templates** (task
  18.1/18.2) ship — JSON/Parquet exporters, built-in domain templates, the
  `datadoom plugin`/`template` CLIs, and web Plugins/Templates galleries. Remaining
  in task 18: time-series (`engine/timeseries.py`) + framework adapters; then task
  19 (1.0 hardening).

## Project docs you must keep updated

These three files are living documents — update them as part of the same change
that alters behavior, **not** as an afterthought:

1. **[status.md](status.md)** — implementation tracker. When you start/finish a
   task, flip its status. When a task needs breaking down, add subtasks
   (`5` → `5.1`, `5.2`, …) and a row per subtask, and append a Change-history
   entry. The Master Log table is the at-a-glance view.
2. **[testing_guide.md](testing_guide.md)** — the manual testing guide the user
   runs by hand. Every test is labelled with **what it tests, which files, the
   command, and the expected output**. When behavior changes or a feature lands,
   add/adjust the matching labelled test and its expected output.
3. **CLAUDE.md** (this file) — keep commands, layout, and invariants current.

## Repository layout

```
src/datadoom/
  engine/            # PURE engine — no web/DB/framework imports
    rng.py           # seeded RNGFactory (the determinism invariant)
    spec/            # Pydantic models, canonical hashing, validation
    dist/            # Distribution ABC, builtins, KS compliance
    causal/          # DAG (networkx) + StructuralFn + SEM execution + interventions
    failure/         # MCAR/MAR/MNAR, noise, drift, covariate-shift, leakage
    difficulty/      # scikit-learn probes + adaptive bisection to a target band
    timeseries.py    # additive Xₜ = T(t)+S(t)+AR(p)+εₜ (05 §6); TimeseriesFeature
    export/          # Exporter ABC + byte-stable CSV/JSON/Parquet, metadata, checksums
    reference.py     # build_capabilities() — machine-readable spec manifest (AI authoring)
    pipeline.py      # the single generate() entry point (RunContext)
    reports.py       # report bundle: compliance, correlation, MI, causal_truth
    progress.py errors.py
  plugins/           # registry + loader + scaffolder (engine ← plugins; never the reverse)
    contracts.py     # re-exports the engine ABCs as `datadoom.plugin` + schema()
    registry.py loader.py scaffold.py
  plugin.py          # public author shim: `from datadoom.plugin import Distribution, schema`
  adapters/          # consumer loaders: pandas (core) + torch/tf/hf (optional extras)
  templates/         # built-in domain starter specs (*.datadoom.yaml) + catalog/loader
  cli/main.py        # Typer CLI: run|validate|verify|version|spec-reference | plugin{…} | template{…}
  version.py __init__.py   # public API: Spec, generate, load_spec, parse_spec, validate_spec, build_capabilities
tests/{unit,determinism,golden,api,plugin_contract}
examples/            # *.datadoom.yaml sample specs
docs_v2/             # authoritative design (numbered 00–21)
```

Phase 1 packages (`store/`, `jobs/`, `api/`, `frontend/`, `webdist/`), the
`plugins/` system (task 17), `templates/` (task 18.2), and `adapters/` (task 18.4)
are in place. **Phase 5 is complete** (plugins, exporters, templates, time-series,
adapters, AI spec-authoring manifest); see `docs_v2/20`/`21` for authoring guides.

## Engine invariants (non-negotiable — reviewers enforce)

1. **Determinism:** all randomness flows through `engine.rng`. No stdlib
   `random`, `uuid4`, `time`, or global `np.random.*` in the data path. RNG key =
   `sha256(spec_hash || ':' || seed || ':' || namespace)[:8] → uint64`.
2. **Engine purity / layering:** `engine/` imports nothing from `api/store/jobs/
   cli` or web frameworks. Enforced by `lint-imports` (contracts in
   `pyproject.toml`). Layer order: `cli → api → jobs → engine ← plugins`.
3. **Honest statistics:** sample correctly from the requested distribution and
   **report** fit (KS stat + p-value, compliance score). **Never** refit
   parameters to the realized sample.
4. **One pipeline:** CLI, API, and `datadoom.generate()` all call
   `engine.pipeline` — never duplicate generation logic.
5. **Spec is additive** within `datadoom_version: 1` (only add optional fields).
6. **Reproducible artifacts:** `metadata.json` and CSV carry no timestamps/ambient
   state; the same `(spec_hash, seed)` → identical bytes on the pinned path.

## Dev environment

Use the **project-local virtual environment** in `.venv/` (Python 3.11, matching
CI's lowest supported version). Do **not** install into a global interpreter.

```powershell
python -m venv .venv                  # one-time (use a full python path if PATH python lacks pip)
.\.venv\Scripts\Activate.ps1          # each session
python -m pip install -e ".[dev]"     # install datadoom + dev tools
```

Once activated, `datadoom`, `pytest`, `ruff`, `mypy`, and `lint-imports` are on
PATH. (If `python` on PATH lacks `pip`/`venv`, create the venv once with a full
interpreter path, then activate — everything after activation uses the venv.)

> History: an earlier setup used a global 3.14 interpreter, where mypy hit an
> `INTERNAL ERROR` on whole-package runs. In the clean `.venv` (3.11), `mypy` runs
> the whole package cleanly — always use the venv.

## Commands (venv activated)

```powershell
ruff check src tests        # lint
lint-imports                # architecture boundaries (5 contracts)
mypy                        # type-check (whole package)
pytest                      # 297 tests (unit + determinism + api + plugin_contract)
datadoom run examples/causal-fraud.datadoom.yaml --seed 42 --out .tmp_run
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42
datadoom run examples/timeseries-sensor.datadoom.yaml --seed 7 --out .tmp_ts   # time-series
datadoom spec-reference     # machine-readable capabilities manifest (AI authoring)
datadoom plugin list        # core built-ins + discovered plugins
datadoom plugin new distribution weibull   # scaffold a plugin package
datadoom plugin check ./datadoom-plugin-weibull   # run the contract checks
datadoom template list      # built-in domain templates
datadoom template use fraud-detection --out my.datadoom.yaml   # start from one
```

> Parquet export needs the optional extra: `pip install -e ".[parquet]"` (pyarrow).
> Without it, CSV/JSON still work; a parquet run errors with an install hint.
> Framework adapters (`datadoom.adapters`: pandas core; torch/tf/hf optional) load a
> generated run into ML frameworks — `pip install -e ".[torch]"` etc. for those.
> Authoring guides: `docs_v2/20` (beginners) and `docs_v2/21` (for AI/agents); the
> live capabilities manifest is `datadoom spec-reference` / `GET /api/spec-reference`.

Full manual procedures with expected outputs are in
**[testing_guide.md](testing_guide.md)**.

## Workflow conventions

- Branch off `main`; commit with **DCO sign-off** (`git commit -s`). Commit/push
  only when the user asks.
- New stochastic behavior ships with a **determinism test**. New behavior ships
  with tests + an updated `testing_guide.md` entry.
- Prefer a **plugin** over a core special-case for anything third-party-able.
- Keep it offline: no core path requires network.
- After finishing a task, update **status.md** (status + change history) and
  **testing_guide.md** (if behavior/commands changed).
