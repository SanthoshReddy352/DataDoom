# Changelog

All notable changes to DataDoom are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
