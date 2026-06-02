# DataDoom

**Local-first, open-source engine for controllable, reproducible synthetic data.**

Design the dataset the way you reason about it — distributions, causal relationships,
difficulty, and failure modes — and regenerate it identically, forever, from a single spec file.

> **North star:** a synthetic dataset should be as version-controllable, shareable, and
> reproducible as source code.

This repository is in early development. The authoritative design lives in [`docs_v2/`](docs_v2/)
(start at [`docs_v2/00_README_Index.md`](docs_v2/00_README_Index.md)).

## Status

**Phase 0 — deterministic engine (in progress).** Headless tabular generation with a
seeded RNG, distribution sampling, honest statistical compliance reporting, CSV export,
and a CLI. The web Canvas comes in a later phase.

## Quickstart (development)

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev]"

# generate a dataset from a spec
datadoom run examples/iris_like.datadoom.yaml --seed 42 --out out/

# validate a spec
datadoom validate examples/iris_like.datadoom.yaml

# verify a generated file reproduces from spec + seed
datadoom verify examples/iris_like.datadoom.yaml --against out/data.csv --seed 42
```

## The reproducibility guarantee (scoped)

Given the same spec and seed, on the **pinned path** (single-threaded, pinned library
versions, CPU), DataDoom produces a **bitwise-identical** dataset. See
[`docs_v2/13_Testing_and_Reproducibility_Strategy.md`](docs_v2/13_Testing_and_Reproducibility_Strategy.md).

## License

[Apache-2.0](LICENSE).
