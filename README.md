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

## Status

**Phases 0–5 complete; 1.0 hardening underway.** The deterministic engine, server +
web Canvas, causal engine, failure injection, difficulty targeting, the plugin system,
exporters, templates, time-series, framework adapters, and the AI spec-authoring
manifest all ship. Remaining for 1.0 is hardening (docs, release automation, the repro
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

```bash
# pull the published image (or `docker build -t datadoom:local .` from a clone)
docker run --rm -p 8000:8000 -v datadoom-data:/data \
  ghcr.io/santhoshreddy352/datadoom:latest
```

Open <http://localhost:8000>. The `-v datadoom-data:/data` volume persists your
datasets/runs across restarts; the server binds `0.0.0.0:8000` inside the container.

## Development

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"

ruff check src tests            # lint
lint-imports                    # architecture boundaries
mypy                            # type-check
pytest                          # test suite
```

## The reproducibility guarantee (scoped)

Given the same spec and seed, on the **pinned path** (single-threaded BLAS, pinned
library versions, CPU, same OS/arch), DataDoom produces a **bitwise-identical** dataset.
Across different OS/architectures we guarantee **statistical** — not bitwise —
equivalence (FP reductions differ). The cross-OS × cross-Python reproducibility matrix
enforces this in CI. See
[`docs_v2/13_Testing_and_Reproducibility_Strategy.md`](docs_v2/13_Testing_and_Reproducibility_Strategy.md).

## License

[Apache-2.0](LICENSE).
