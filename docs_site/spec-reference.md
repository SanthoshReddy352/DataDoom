# Spec reference

A DataDoom spec is a single YAML (or JSON) file with `datadoom_version: 1`. It is
**additive**: within version `1`, only new optional fields are ever introduced, so
older specs keep working.

## The live manifest is authoritative

The spec surface is exposed as a machine-readable manifest built from the engine's
**live registries** — so every built-in *and every installed plugin* appears:

```bash
datadoom spec-reference          # CLI: full capability manifest as JSON
```

```text
GET /api/spec-reference          # same manifest over HTTP (when running the server)
```

The manifest enumerates every distribution, structural function, failure mode,
difficulty tier, feature type, exporter, and text provider, plus the hard
validation rules. Prefer it over any static list when building tooling.

## Top-level shape

| Key | Purpose |
|---|---|
| `datadoom_version` | Spec format version (`1`). |
| `name` | Human label for the dataset. |
| `rows` | Number of rows to generate. |
| `seed` | Default seed (overridable on the CLI / API). |
| `features` | The columns — a discriminated union by `type` (numeric, categorical, boolean, datetime, text, timeseries). |
| `causal` | Optional DAG of structural equations over the features. |
| `difficulty` | Optional baseline-AUROC targeting for a binary label. |
| `failures` | Optional ordered list of corruption mechanisms (applied to a copy). |
| `export` | Output `formats` (csv/json/parquet) and `versions` (clean/injected). |

## Full surface

The complete, prose spec reference (every field, type, and constraint) lives in
the authoritative design set:

- **[04 — Spec Reference](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/04_DataDoom_Spec_Reference.md)**
- **[05 — Mathematical / Algorithm Definitions](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/05_Mathematical_Algorithm_Definitions.md)**

For a guided, example-driven walkthrough, start with the **[YAML authoring
guide](authoring.md)**; for the AI-authoring contract, see the
**[LLM reference](llm-reference.md)**.
