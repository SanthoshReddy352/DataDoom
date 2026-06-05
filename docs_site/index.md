---
title: DataDoom — reproducible synthetic data
template: home.html
hide:
  - navigation
  - toc
---

# DataDoom

**Local-first, open-source engine for controllable, reproducible synthetic data.**

Design a dataset the way you reason about it — distributions, causal structure,
difficulty, and failure modes — as a single spec file, and regenerate it
**identically, forever**, from `(spec_hash, seed)`.

> **North star:** a synthetic dataset should be as version-controllable,
> shareable, and reproducible as source code.

---

## Why DataDoom

- **Deterministic by construction.** All randomness flows through one seeded RNG.
  The same spec + seed produces byte-identical artifacts on a pinned path.
- **Honest statistics.** Distributions are sampled correctly and *fit is reported*
  (KS / chi-square goodness-of-fit, compliance score) — parameters are never
  refit to the realized sample.
- **You control the signal.** A causal DAG (SEM) defines the true relationships,
  difficulty targeting calibrates a baseline-model AUROC into a chosen band, and
  failure injection corrupts a copy (MCAR/MAR/MNAR, noise, drift, leakage…) while
  the clean baseline is preserved.
- **Two surfaces, one engine.** A CLI for automation and a web Canvas for design
  both call the exact same `engine.pipeline` — generation logic is never
  duplicated.
- **Extensible.** New distributions, structural functions, failure modes,
  exporters, and probes ship as plugins against the engine ABCs — no core change.

## Install

```bash
pip install datadoom              # engine + CLI
pip install "datadoom[server]"    # + web Canvas (datadoom serve)
pip install "datadoom[parquet]"   # + Parquet export
```

## Quickstart — CLI

```bash
# Generate a dataset from a spec (deterministic on the pinned path)
datadoom run examples/causal-fraud.datadoom.yaml --seed 42 --out ./out

# Prove reproducibility: regenerate and compare bytes
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42 --against ./out

# Start from a built-in domain template
datadoom template list
datadoom template use fraud-detection --out my.datadoom.yaml

# Machine-readable capabilities manifest (for AI/agent authoring)
datadoom spec-reference
```

## Quickstart — web Canvas

```bash
pip install "datadoom[server]"
datadoom serve         # opens the bundled web Canvas (no Node toolchain needed)
```

Create a dataset, edit the schema, wire a causal graph, configure difficulty and
failures, generate with a live progress tracker, then preview / compare / export.

## Where to go next

- **[YAML authoring guide](authoring.md)** — write your first spec, end to end.
- **[LLM / agent reference](llm-reference.md)** — the authoring contract for AI tools.
- **[Spec reference](spec-reference.md)** — the full spec surface + live manifest.
- **[Plugin system](plugins.md)** — extend the engine with your own components.
- **[Architecture](architecture.md)** — how determinism, layering, and the pipeline fit.
- **[Examples gallery](examples.md)** — runnable example specs and domain templates.

---

*DataDoom is Apache-2.0 licensed. The authoritative design lives in
[`docs_v2/`](https://github.com/SanthoshReddy352/datadoom/tree/main/docs_v2)
(start at `00_README_Index.md`).*
