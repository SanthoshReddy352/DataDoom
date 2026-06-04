# 22 — Release & Publishing Runbook

> **Audience:** the maintainer/operator (you). This is the step-by-step for the
> publishing actions that **cannot** be automated from inside the repo because they
> need account-level access (GitHub Pages, PyPI, a container registry) or a tagged
> commit. The repo ships the *automation* (CI workflows, Dockerfile, packaging
> metadata); this doc is how you *flip the switches* to make it live.
>
> Status of each section is marked: **🟢 ready** (the workflow/file exists in the
> repo — just enable it) or **🟡 pending** (lands with a later Task-19 deliverable;
> listed here so the full picture is in one place).

## Conventions

- Default branch: `main`. Releases are cut from a `v*` git tag.
- Version source of truth: `src/datadoom/version.py` (read by hatchling).
- Never commit secrets. All publishing below uses **keyless OIDC** (GitHub →
  PyPI / Sigstore) or GitHub-managed tokens — there are **no long-lived secrets**
  to store for the core flow.

---

## 1. Documentation site → GitHub Pages 🟢 ready

The site is built by [`.github/workflows/docs.yml`](../.github/workflows/docs.yml)
with `mkdocs build --strict`, and on a push to `main` it publishes via
`mkdocs gh-deploy` (which pushes the rendered site to a `gh-pages` branch).

**One-time enablement (you):**

1. Push this branch to `main` (or merge the PR). The Docs workflow runs and, on
   `main`, creates/updates the **`gh-pages`** branch.
2. In GitHub: **Settings → Pages → Build and deployment**:
   - **Source:** *Deploy from a branch*
   - **Branch:** `gh-pages` / `/ (root)` → **Save**.
3. Wait ~1 min. The site is live at
   `https://<owner>.github.io/datadoom/` (matches `site_url` in `mkdocs.yml` —
   currently `https://santhoshreddy352.github.io/datadoom/`). Update `site_url`
   and the `repo_url` in `mkdocs.yml` if the org/repo name differs.

**Local preview (no account needed):**

```bash
pip install -e ".[docs]"
mkdocs serve          # live-reload at http://127.0.0.1:8000
mkdocs build --strict # what CI runs
```

> The deep design docs in `docs_v2/` stay the single source of truth: the site
> pages in `docs_site/` *embed* them via the include-markdown plugin. Edit the
> `docs_v2/` source, not a copy.

---

## 2. PyPI release (`pip install datadoom`) 🟢 ready

The release workflow [`.github/workflows/release.yml`](../.github/workflows/release.yml)
is tag-triggered: publishing is **tokenless** via PyPI Trusted Publishing (OIDC).

**One-time setup (you), before the first release:**

1. Create the project on PyPI (and ideally TestPyPI first). Reserve the name
   `datadoom` if available.
2. On PyPI: **Your projects → datadoom → Settings → Publishing → Add a trusted
   publisher (GitHub Actions)**:
   - **Owner:** `SanthoshReddy352`  ·  **Repository:** `datadoom`
   - **Workflow filename:** `release.yml`
   - **Environment:** `pypi` (match the environment named in the workflow).
3. In GitHub: **Settings → Environments → New environment → `pypi`** (optionally add
   required reviewers so a human approves each publish).

**Cutting a release (you), each time:**

1. Bump the version in `src/datadoom/version.py` (e.g. `0.1.0`), update
   `CHANGELOG.md` (move *Unreleased* → the new version), commit with sign-off:
   ```bash
   git commit -s -m "Release 0.1.0"
   ```
2. Tag and push:
   ```bash
   git tag -s v0.1.0 -m "DataDoom 0.1.0"   # -s if you sign tags; -a otherwise
   git push origin main --tags
   ```
3. The release workflow builds the sdist+wheel, smoke-tests the wheel, attaches
   build **provenance** (see §4), creates the GitHub Release, and publishes to
   PyPI via OIDC. No token needed.

**Manual fallback (if not yet automated):**

```bash
pip install build twine
python -m build                 # -> dist/*.whl, dist/*.tar.gz
python -m twine check dist/*
python -m twine upload dist/*   # prompts for a PyPI API token
```

---

## 3. Docker image 🟢 ready

The [`Dockerfile`](../Dockerfile) builds a runnable server image: a Node stage
compiles the web Canvas, then a slim Python runtime stage installs the package, so
the **final image carries no Node toolchain**. The release workflow builds and
pushes it to GHCR on a `v*` tag; CI builds it on every PR (non-gating).

**Build & run locally (you):**

```bash
docker build -t datadoom:local .
docker run --rm -p 8000:8000 datadoom:local     # datadoom serve on :8000
```

**Publish to GitHub Container Registry (GHCR):**

1. The release workflow can build and push on a `v*` tag using the built-in
   `GITHUB_TOKEN` with `packages: write` — no extra secret.
2. After the first push, make the package public if desired:
   **GitHub → your profile/org → Packages → datadoom → Package settings →
   Change visibility**.
3. Pull: `docker pull ghcr.io/santhoshreddy352/datadoom:0.1.0`.

> Docker Hub is optional and *does* need stored credentials
> (`DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` repo secrets). Prefer GHCR for the
> tokenless path.

---

## 4. Signed releases / build provenance 🟢 ready

The "signed releases" requirement is met **keylessly** — you do not manage any
signing key:

- **Build provenance attestation** via `actions/attest-build-provenance` on the
  release workflow signs the wheel/sdist with a short-lived Sigstore identity tied
  to the GitHub OIDC token. Verify with the GitHub CLI:
  ```bash
  gh attestation verify dist/datadoom-0.1.0-py3-none-any.whl --owner SanthoshReddy352
  ```
- **PyPI** records attestations automatically for Trusted-Publisher uploads.
- *(Optional)* GPG-signed git tags (`git tag -s`) if you maintain a GPG key; add
  the public key to your GitHub account so the tag shows **Verified**.

There is intentionally **no private key checked into or required by the repo**.

---

## 5. Reproducibility & CI badges 🟡 pending (Task 19 — deliverable C)

The README badges (CI status, reproducibility matrix) point at the existing
workflows and need no setup beyond the workflows running at least once on `main`.
The repro matrix pins numpy in its CI cells so the golden-checksum gate actually
asserts (rather than skips); see
[13_Testing_and_Reproducibility_Strategy.md](13_Testing_and_Reproducibility_Strategy.md).
No operator action required — the badges resolve once the workflows have run.

---

## 6. Team mode — deferred (future addon)

Optional **team mode** (Postgres + S3 + Redis/RQ + auth + `owner_id` scoping, all
opt-in behind config flags) is **explicitly out of scope** for the 1.0 hardening
pass and is parked as a **future addon**. The design intent is captured in
[16_Engineering_Roadmap.md](16_Engineering_Roadmap.md) (P6 / Post-1.0) and
[17_Implementation_Guide.md](17_Implementation_Guide.md) (Task 19). Nothing in the
current local-first path depends on it; do **not** treat its absence as a gap.

---

## Pre-release checklist

- [ ] `ruff check src tests`, `mypy`, `lint-imports`, `pytest` all green.
- [ ] Repro matrix green on the pinned cells (golden checksum asserts, not skips).
- [ ] `mkdocs build --strict` green; site preview looks right.
- [ ] `CHANGELOG.md` updated; *Unreleased* → the new version.
- [ ] `src/datadoom/version.py` bumped.
- [ ] Tag signed/annotated and pushed; release workflow green; PyPI + GHCR show the
      new version; `gh attestation verify` passes.
