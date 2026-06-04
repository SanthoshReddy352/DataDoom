# DataDoom

**Local-first, open-source engine for controllable, reproducible synthetic data.**

[![CI](https://github.com/SanthoshReddy352/datadoom/actions/workflows/ci.yml/badge.svg)](https://github.com/SanthoshReddy352/datadoom/actions/workflows/ci.yml)
[![Reproducibility Matrix](https://github.com/SanthoshReddy352/datadoom/actions/workflows/repro-matrix.yml/badge.svg)](https://github.com/SanthoshReddy352/datadoom/actions/workflows/repro-matrix.yml)
[![Docs](https://github.com/SanthoshReddy352/datadoom/actions/workflows/docs.yml/badge.svg)](https://santhoshreddy352.github.io/datadoom/)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Design the dataset the way you reason about it — distributions, causal relationships,
difficulty, and failure modes — and regenerate it identically, forever, from a single spec file.

> **North star:** a synthetic dataset should be as version-controllable, shareable, and
> reproducible as source code.

📖 **Docs:** <https://santhoshreddy352.github.io/datadoom/> · authoritative design in
[`docs_v2/`](docs_v2/) (start at [`docs_v2/00_README_Index.md`](docs_v2/00_README_Index.md)).

## Why DataDoom

Synthetic data usually forces a trade-off: it's either **realistic but a black box**
(you can't say what relationships or flaws it contains) or **controllable but
throwaway** (you can't regenerate the exact same dataset tomorrow). That makes it hard
to teach with, benchmark against, file a bug against, or share.

**The goal:** make a dataset something you *design* and *version-control like source
code*. You declare its structure — distributions, causal relationships, difficulty,
and data-quality failures — in one spec file, and DataDoom regenerates it
**byte-for-byte identically** from `(spec_hash, seed)`, while honestly reporting how
well the realized data matches what you asked for. No network, no telemetry, no
account: everything runs locally.

**Good for:** ML teaching & reproducible benchmarks · testing data pipelines on known
edge cases · sharing a dataset's *recipe* instead of PII · hackathon / challenge
datasets with a known ground truth.

## What it does

- **Deterministic by construction** — one seeded RNG underpins everything; the same
  spec + seed yields a bitwise-identical dataset on the pinned path.
- **Honest statistics** — distributions are sampled correctly and their fit is
  *reported* (KS / chi-square goodness-of-fit, compliance score); parameters are never
  refit to flatter the sample.
- **Causal structure** — a DAG of structural equations (linear/logistic/polynomial/…)
  with per-node noise and `do()` interventions, plus a true-graph + mutual-information
  report.
- **Failure injection** — eight mechanisms (MCAR/MAR/MNAR, label & feature noise,
  drift, covariate shift, leakage) corrupt a *copy* while the clean baseline is kept,
  with realized-effect diffs.
- **Difficulty targeting** — calibrate a binary label to a chosen baseline-model AUROC
  band, reported with the achieved metric, knobs, and bisection trace.
- **Rich feature types** — numeric/categorical/boolean/datetime, realistic seeded text
  (names, emails, addresses), additive time-series, and latent (hidden) features.
- **Extensible** — distributions, structural functions, failure modes, exporters, and
  probes all ship as plugins against the engine ABCs, with zero core changes.
- **Built to consume** — export CSV / JSON / Parquet, load a run straight into
  pandas / PyTorch / TensorFlow / HuggingFace, and start from built-in domain templates
  (including ready-made hackathon challenges).
- **Two surfaces, one engine** — a CLI for automation and a web Canvas for design both
  call the exact same pipeline, so results never diverge.

## Status

**Phases 0–5 complete; 1.0 hardening underway.** Everything in *What it does* above
ships today. Remaining for 1.0 is hardening (docs site, release automation, the repro
matrix); see [`status.md`](status.md). Optional team mode is a deferred future addon.

## Install

```bash
pip install datadoom              # engine + CLI
pip install "datadoom[server]"    # + web Canvas (datadoom serve)
pip install "datadoom[parquet]"   # + Parquet export
```

## Quickstart

```bash
# generate a dataset from a spec
datadoom run examples/causal-fraud.datadoom.yaml --seed 42 --out out/

# validate a spec
datadoom validate examples/causal-fraud.datadoom.yaml

# verify a run reproduces bitwise from spec + seed
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42 --against out/

# start from a built-in domain template
datadoom template use fraud-detection --out my.datadoom.yaml
```

## Web UI (Canvas)

The web Canvas — design schemas, wire causal graphs, configure difficulty/failures,
generate with a live tracker, preview/compare/export — ships **prebuilt inside the
package** (no Node toolchain needed). There are two ways to run it.

### Option A — pip + `datadoom serve`

```bash
pip install "datadoom[server]"   # the [server] extra adds FastAPI/uvicorn
datadoom serve                   # serves the API + Canvas on http://127.0.0.1:8000
```

Then open <http://127.0.0.1:8000> in your browser. `datadoom serve` is what starts
the UI — installing the package alone does not run a server.

> **Hitting `The web server needs extra deps … pip install 'datadoom[server]'`
> even after installing it?** You almost certainly have an older `datadoom` already
> installed, so pip reports "already satisfied" and never pulls the `[server]`
> dependencies. Force a clean reinstall:
> ```bash
> pip install --upgrade --force-reinstall --no-cache-dir "datadoom[server]"
> ```

### Option B — Docker (UI starts automatically)

The image's entrypoint **is** `datadoom serve`, so the Canvas comes up as soon as
the container runs — you do **not** run any extra command.

**Build and run from a clone (works today):**

```bash
docker build -t datadoom:local .
docker run --rm -p 8000:8000 -v datadoom-data:/data datadoom:local
```

**Or pull the published image** (available after a tagged release pushes it to
GHCR — see [`docs_v2/22`](docs_v2/22_Release_and_Publishing_Runbook.md) §3):

```bash
docker run --rm -p 8000:8000 -v datadoom-data:/data ghcr.io/santhoshreddy352/datadoom:latest
```

> Each `docker run` is a **single line** on purpose — it works in PowerShell, CMD,
> and bash alike. A `\` line-continuation is bash-only and breaks in PowerShell.

Open <http://localhost:8000>. The `-v datadoom-data:/data` volume persists your
datasets/runs across restarts; the server binds `0.0.0.0:8000` inside the container.

## Development

Clone the repo (or **fork** it first on GitHub and clone your fork if you intend to
open a pull request), then set up a project-local virtual environment:

```bash
# clone (use your fork's URL if you forked)
git clone https://github.com/SanthoshReddy352/datadoom.git
cd datadoom

# project-local venv (Python 3.11 matches CI's lowest supported version)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -e ".[dev]"         # editable install + dev tools

ruff check src tests            # lint
lint-imports                    # architecture boundaries
mypy                            # type-check
pytest                          # test suite
```

Contributions are welcome — please commit with DCO sign-off (`git commit -s`) and run
the gates above before opening a PR. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## The reproducibility guarantee (scoped)

Given the same spec and seed, on the **pinned path** (single-threaded BLAS, pinned
library versions, CPU, same OS/arch), DataDoom produces a **bitwise-identical** dataset.
Across different OS/architectures we guarantee **statistical** — not bitwise —
equivalence (FP reductions differ). The cross-OS × cross-Python reproducibility matrix
enforces this in CI. See
[`docs_v2/13_Testing_and_Reproducibility_Strategy.md`](docs_v2/13_Testing_and_Reproducibility_Strategy.md).

## License

[Apache-2.0](LICENSE).
