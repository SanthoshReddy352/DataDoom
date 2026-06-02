# 15 — Open Source Governance

> How DataDoom is licensed, contributed to, decided upon, and released. Adoption is a feature; this doc makes the project *contributable*. Obeys `00_README_Index.md`.

---

## 1. License

- **Apache-2.0** for the core. Rationale: permissive (maximizes adoption, allows commercial use), includes an explicit **patent grant** (important for an algorithm-heavy project), and is GitHub/enterprise-friendly.
- **Contributor sign-off via DCO** (Developer Certificate of Origin) — `Signed-off-by` line on commits. Lightweight; no CLA paperwork barrier. (A CLA can be reconsidered only if a foundation donation ever requires it.)
- **Dependency license rule:** core depends only on permissive (BSD/MIT/Apache) packages (`11 §9`). Copyleft stays out of core; plugins carry their own license obligations.
- **Plugins & templates** may choose their own OSI license; the recommended default is Apache-2.0/MIT.

---

## 2. Repository Standards (ship in v0.1)

| File | Purpose |
|---|---|
| `LICENSE` | Apache-2.0 text |
| `README.md` | what/why, 5-min quickstart, badges (CI, repro rate, PyPI) |
| `CONTRIBUTING.md` | dev setup, DCO, branch/PR flow, test gates |
| `CODE_OF_CONDUCT.md` | Contributor Covenant |
| `SECURITY.md` | private disclosure channel + response expectations (`14 §4`) |
| `GOVERNANCE.md` | this model, summarized |
| `CHANGELOG.md` | Keep-a-Changelog format |
| `.github/ISSUE_TEMPLATE/` | bug / feature / plugin-idea templates |
| `.github/PULL_REQUEST_TEMPLATE.md` | checklist (tests, docs, DCO, layering) |
| `good first issue` / `help wanted` labels | onboarding path for new contributors |

---

## 3. Governance Model

DataDoom starts as a **BDFL-lite / maintainer-led** project and is designed to graduate to **meritocratic multi-maintainer** governance as the community grows.

### 3.1 Roles
- **Users** — file issues, request features, share specs/plugins.
- **Contributors** — submit PRs (code, docs, templates, plugins).
- **Maintainers** — review/merge, triage, cut releases, guard the architecture invariants (`00`, `03 §10`, `10 §4`).
- **Lead maintainer (initially the founder)** — final tie-breaker, roadmap steward; explicitly intends to delegate as trusted maintainers emerge.

### 3.2 Becoming a maintainer
Sustained, high-quality contribution + good review judgment → nominated by an existing maintainer → lazy-consensus approval among maintainers. Documented in `GOVERNANCE.md` so the path is transparent.

### 3.3 Decision-making
- **Lazy consensus** for most changes: a PR/proposal merges if no maintainer objects within a review window.
- **DDEP (DataDoom Enhancement Proposal)** for big changes: anything touching the **locked decisions** (`00`), the **spec format** (`04`), the **plugin API** (`09`), or the **determinism guarantee** (`05`/`13`). A short design doc, public discussion, maintainer sign-off, then implementation.
- Disagreements escalate to lead maintainer as last resort.

---

## 4. Contribution Workflow

1. Open/claim an issue (or a DDEP for large changes).
2. Fork → feature branch.
3. Dev setup: `pip install -e .[dev]`, `pre-commit install`, `cd frontend && npm ci`.
4. Make the change **with tests and docs**.
5. Pass local gates: Ruff, mypy, import-linter, pytest, `tsc`/ESLint (`13 §8`).
6. Commit with **DCO sign-off**; open PR using the template.
7. Maintainer review → CI green (incl. repro matrix) → merge (squash).
8. Anything user-facing updates `CHANGELOG.md` and the docs.

**Hard rules reviewers enforce** (the architecture must not erode):
- `engine/` stays framework-free; layering (`10 §4`) holds.
- All randomness via `engine.rng`; no banned calls.
- New optional capability prefers a **plugin** over a core branch (`09 §8`).
- Spec changes are additive within `datadoom_version: 1`.

---

## 5. Versioning & Compatibility

- **Package:** SemVer (`MAJOR.MINOR.PATCH`). Breaking API/behavior → MAJOR.
- **Spec format:** versioned independently by `datadoom_version`; additive-only within a major; breaking → bump + `datadoom migrate`.
- **Plugin API:** treated as public API; breaking changes are MAJOR and announced; plugins declare compatible ranges (`09 §7`).
- **Deprecation policy:** deprecate for ≥1 minor with warnings before removal.

---

## 6. Release Process

- Automated via `release.yml`: tag → build wheel (with bundled frontend) → run full CI incl. repro matrix → publish to PyPI with signed provenance (`14 §4`) → build Docker image → publish docs.
- **Release cadence:** time-boxed minors (e.g. ~monthly while pre-1.0), patches as needed.
- Each release: changelog entry, migration notes if any, updated docs, GitHub Release with notes.
- **Quality bar to release:** all CI gates green, repro matrix bitwise-clean in pinned cells, docs build clean, fresh-install smoke test on all OSes (`13 §9`).

---

## 7. Community Infrastructure

- **Docs site** (mkdocs-material) from `docs/` — quickstart, spec reference, plugin authoring, architecture, examples gallery.
- **Discussions / chat** (GitHub Discussions; optionally Discord/Matrix) for Q&A and design.
- **Community index** for plugins & templates (a curated list / simple registry page) so the ecosystem is discoverable.
- **Public roadmap** (GitHub Projects) tracking the phases in `16`.

---

## 8. Project Values

1. **Trust through transparency** — guarantees are tested and the tests are public.
2. **Welcoming** — good first issues, responsive reviews, clear paths to maintainership.
3. **Stable contracts** — the spec format and plugin API are promises, not moving targets.
4. **Scope discipline** — say no to scope creep that re-bloats the core; push it to plugins.
5. **No vendor lock-in** — local-first, open formats, no mandatory cloud.

---

## 9. Trademark / Naming (housekeeping)

- **Availability verified (2026-06-01):** PyPI `datadoom` is **free** (also TestPyPI). Reserve it (publish a placeholder `0.0.0` or claim on first release) before the 0.1 tag.
- **GitHub home:** the project lives at the **personal repo** `github.com/SanthoshReddy352/datadoom`. The existing repo is currently named `Hack-Forge` (remote `github.com/SanthoshReddy352/Hack-Forge.git`) and will be **renamed to `datadoom`** before publishing. GitHub auto-redirects the old name after rename, so existing clones keep working; still update the remote URL afterward (`git remote set-url origin …/datadoom.git`).
- The GitHub **org handle** `datadoom` is held by an inactive account (0 repos) and is **not** used; migrating to a dedicated org later is optional and non-blocking (GitHub redirects from the personal repo).
- The name/logo may be trademarked to protect the project's identity while keeping the code Apache-2.0; forks must rename per standard OSS trademark norms. (Decision deferred; flagged here so it isn't forgotten.)
