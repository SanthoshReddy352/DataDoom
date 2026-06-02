# Contributing to DataDoom

Thanks for helping build a trustworthy, reproducible synthetic-data engine.
The authoritative design lives in [`docs_v2/`](docs_v2/); please skim
[`docs_v2/00_README_Index.md`](docs_v2/00_README_Index.md) before a non-trivial change.

## Dev setup

```bash
python -m pip install -e ".[dev]"
pre-commit install        # optional but recommended
```

Run the local gates before opening a PR:

```bash
ruff check src tests      # lint
mypy                      # type-check (strict on engine/)
lint-imports              # architectural layering
pytest                    # unit + determinism gates
```

## Branch & PR flow

1. Open or claim an issue (a **DDEP** for changes touching the locked decisions,
   the spec format, the plugin API, or the determinism guarantee).
2. Fork → feature branch off `main`.
3. Make the change **with tests and docs**.
4. Pass all local gates above.
5. Commit with a **DCO sign-off** (`git commit -s`) and open a PR using the template.
6. A maintainer reviews; CI (including the reproducibility matrix) must be green; merge is squash.

## Developer Certificate of Origin (DCO)

We use the [DCO](https://developercertificate.org/) instead of a CLA. Sign off
every commit:

```bash
git commit -s -m "your message"
```

This adds a `Signed-off-by: Your Name <you@example.com>` line certifying you have
the right to submit the contribution under the project's license.

## Hard rules reviewers enforce

These protect the architecture and must not erode:

- `engine/` stays **framework-free**; the layering in `docs_v2/10 §4` holds
  (enforced by `lint-imports`).
- **All randomness flows through `engine.rng`** — no stdlib `random`, `uuid4`,
  `time`, or global `np.random.*` in the data path.
- **Honest statistics** — sample correctly and *report* fit; never refit
  parameters to the realized sample.
- New optional capability prefers a **plugin** over a core branch.
- Spec changes are **additive only** within `datadoom_version: 1`.

## License

By contributing you agree your contributions are licensed under
[Apache-2.0](LICENSE).
