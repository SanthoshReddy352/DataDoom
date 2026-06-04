# Changelog

All notable changes to DataDoom are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/).

## 0.1.0

### Added

- **Phase 0 — Deterministic Core.** The headless, reproducible engine:
  - `engine.rng` — seeded `RNGFactory` with per-namespace key derivation
    (`sha256(spec_hash || seed || namespace)`); independent streams per feature.
  - `engine.spec` — Pydantic v2 spec models, canonical JSON serialization, and
    `spec_hash` (seed-excluded), plus cross-field validation with error locators.
  - `engine.dist` — built-in distributions (normal, lognormal, poisson, pareto,
    uniform, exponential) with samplers for categorical/boolean/datetime/text,
    and **honest** KS compliance reporting (no parameter refitting).
  - `engine.export` — byte-stable CSV writer, reproducible `metadata.json`, and
    SHA256 checksums.
  - `engine.pipeline` — the minimal intake → snapshot → seed → base generation →
    compliance → packaging slice, behind a single `generate()` entry point.
  - `datadoom` CLI — `run`, `validate`, and `verify`.
  - Determinism gate, first golden spec, and the reproducibility CI matrix.

- **Phase 1 — Server + web Canvas.** `store/` (SQLAlchemy + SQLite/WAL,
  repositories, local artifact store, Alembic migrations), `jobs/` (in-process
  worker + event hub with progress replay/cancel), `api/` (FastAPI app, REST
  routes, WebSocket + SSE, resource estimator), `datadoom serve`, and the React
  web Canvas (Dashboard, schema editor + Inspector, live generation tracker,
  Results, Export) bundled into the wheel.

- **Phase 2 — Causal engine.** `engine.causal` — a networkx DAG with a
  lexicographical topological SEM walk, structural functions (linear, logistic,
  polynomial, map, identity), per-node noise, and `do()` interventions; the
  `causal_truth` + mutual-information reports; and the web Graph view (React Flow).

- **Phase 3 — Failure injection.** `engine.failure` — eight mechanisms (MCAR,
  MAR, MNAR, label noise, feature noise, drift, covariate shift, leakage) applied
  to a copy while the clean baseline is preserved, with honest realized-effect
  diffs; the web Failure Configurator + clean-vs-injected Comparison.

- **Phase 4 — Difficulty targeting.** `engine.difficulty` — scikit-learn baseline
  probes (logreg/tree) and an adaptive bisection that calibrates a binary label to
  a target baseline-AUROC band (feature noise + label flips), reported honestly
  (achieved metric, iterations, knobs, trace); the web Difficulty view.

- **Phase 5 — Ecosystem.**
  - **Plugins** — five extension points (distribution, structural fn, failure
    mode, exporter, probe) discovered via entry points or `$DATADOOM_HOME/plugins`,
    with a scaffolder + contract checks (interface, schema, determinism, RNG
    hygiene); `datadoom plugin list/new/check` and a web Plugins gallery.
  - **Exporters** — byte-stable JSON and (optional) Parquet alongside CSV.
  - **Templates** — built-in domain starter specs + four hackathon challenges;
    `datadoom template list/show/use` and a web Templates gallery.
  - **Time-series** — additive `T(t)+S(t)+AR(p)+εₜ` feature type.
  - **Adapters** — `datadoom.adapters` loaders for pandas (core) and
    torch/tf/HF (optional extras).
  - **AI authoring** — `build_capabilities()` manifest via `datadoom
    spec-reference` / `GET /api/spec-reference`, plus the YAML + LLM authoring
    guides.

- **Enhancements.** Realistic seeded text providers (mimesis); latent features
  (`emit: false`); web Import-from-YAML; the Generation Overview dashboard;
  the per-column **Column Guide** (profile + failure attribution + ML advice);
  a locked resolved-spec artifact and an audit report bound into every bundle.

- **1.0 hardening (in progress).** Documentation site (mkdocs-material) with a
  GitHub Pages workflow; tag-driven release automation (PyPI via OIDC trusted
  publishing, keyless Sigstore build-provenance attestation, GitHub Releases);
  a runnable Docker server image published to GHCR.

### Notes

- Spec format is `datadoom_version: 1` and **additive** — older specs keep working.
- **Team mode** (Postgres/S3/Redis + auth) is deferred as a future addon.
