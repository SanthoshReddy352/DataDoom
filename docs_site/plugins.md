# Plugin system

DataDoom is extended by **plugins**: a plugin is a small class implementing one of
the engine's ABCs, discovered at startup and inserted into the engine's own lookup
tables — so it works in the CLI, the API, and the web Canvas with **no core
change**. The dependency points one way only: `engine ← plugins` (the engine never
imports plugins), enforced by an import-linter contract.

## Five extension points

| Kind | ABC (`from datadoom.plugin import …`) | Keyed on |
|---|---|---|
| Distribution | `Distribution` | `name` |
| Structural function | `StructuralFn` | `name` |
| Failure mode | `FailureMode` | `name` |
| Exporter | `Exporter` | `format` |
| Difficulty probe | `ProbeModel` | `name` |

Each ABC carries an optional `param_schema` so the web UI can render controls for
your plugin's parameters automatically.

## Scaffold → check → use

```bash
datadoom plugin list                          # built-ins + discovered plugins
datadoom plugin new distribution weibull      # scaffold a datadoom-plugin-weibull package
datadoom plugin check ./datadoom-plugin-weibull   # run the contract checks
```

The contract checks verify the interface, the param schema, **determinism**, and
run a static **RNG-hygiene** scan (no stdlib `random`/`uuid4`/`time`/global
`np.random.*` in the data path — all randomness must flow through the injected
`rng`).

## Discovery

Plugins are found via two mechanisms:

1. **Entry points** in the `datadoom.plugins` group (installed packages).
2. **Local files** in `$DATADOOM_HOME/plugins/*.py`.

Broken or duplicate plugins fail loudly at load time rather than silently.

## Full guide

The complete plugin authoring guide (ABC contracts, schema format, packaging) is
in the authoritative design set:

- **[09 — Plugin System](https://github.com/SanthoshReddy352/datadoom/blob/main/docs_v2/09_Plugin_System.md)**
