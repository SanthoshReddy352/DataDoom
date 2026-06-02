## What & why

<!-- A short description of the change and the motivation. Link the issue/DDEP. -->

## Checklist

- [ ] Tests added/updated (unit, and determinism tests for any stochastic code)
- [ ] Docs updated if user-facing (`docs_v2/` and/or `CHANGELOG.md`)
- [ ] Local gates pass: `ruff check`, `mypy`, `lint-imports`, `pytest`
- [ ] Architecture upheld: `engine/` stays framework-free; all randomness via `engine.rng`
- [ ] Spec changes are additive within `datadoom_version: 1`
- [ ] Commits are DCO **signed off** (`git commit -s`)
