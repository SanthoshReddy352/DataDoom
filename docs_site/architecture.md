# Architecture

DataDoom is a pure, deterministic **engine** wrapped by thin surfaces. The
guarantees come from a handful of non-negotiable invariants enforced in CI.

## Layering

```
cli  →  api  →  jobs  →  engine  ←  plugins
                            ↑
                          store, adapters
```

- **`engine/`** is a clean, installable library: it imports *nothing* from the
  web/DB/CLI layers or any web framework. This is enforced by `import-linter`
  (the "engine stays framework-free" contract).
- Higher layers may import lower ones, never the reverse. `store`, `plugins`, and
  `adapters` sit beside the engine and depend only on it.

## The single pipeline

The CLI, the HTTP API, and `datadoom.generate()` **all** call
`engine.pipeline.generate()` — generation logic is never duplicated. The pipeline
is a fixed sequence of stages:

```
intake → snapshot → seed → base_generation → causal → difficulty
       → failure_injection → compliance → packaging
```

- `base_generation` samples root features; `causal` derives the rest via the SEM
  walk in topological order.
- `difficulty` calibrates the *clean* frame to a target baseline-AUROC band.
- `failure_injection` corrupts a **copy**, preserving the clean baseline.
- `compliance` reports fit honestly; `packaging` writes byte-stable artifacts.

## Determinism invariant

All randomness flows through `engine.rng`. The RNG key is:

```
sha256(spec_hash || ':' || seed || ':' || namespace)[:8] → uint64
```

No stdlib `random`, `uuid4`, `time`, or global `np.random.*` ever appears in the
data path. On the pinned path (pinned numpy/scikit-learn/mimesis), the same
`(spec_hash, seed)` yields **byte-identical** artifacts — proven by the
determinism gate and the cross-OS reproducibility matrix in CI.

## Reproducible artifacts

`metadata.json` and the data files carry no timestamps or ambient state. Every run
also ships a **locked resolved spec** (canonical body + baked-in seed) and an
**audit report**, all checksummed, so a dataset is as reproducible and
shareable as source code.

## Full design set

The authoritative architecture documents:

- **[03 — Technical Architecture](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/03_Technical_Architecture.md)**
- **[10 — File Structure](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/10_File_Structure.md)**
- **[13 — Testing & Reproducibility Strategy](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/13_Testing_and_Reproducibility_Strategy.md)**
