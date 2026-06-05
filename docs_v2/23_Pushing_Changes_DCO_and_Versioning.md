# 23 — Pushing Changes, DCO Sign-off & Versioning

> A practical, copy-pasteable guide for getting your changes onto GitHub the right
> way: how to sign off commits (DCO), how to push, how to bump the version, and how
> that turns into a release. Commands are shown for **PowerShell** (your shell) but
> are identical in bash unless noted. For the publishing side (PyPI / Docker / Pages)
> see [22_Release_and_Publishing_Runbook.md](22_Release_and_Publishing_Runbook.md).

---

## 0. TL;DR cheat sheet

```powershell
# one-time: point origin at the canonical repo name (yours still says Hack-Forge)
git remote set-url origin https://github.com/SanthoshReddy352/datadoom.git

# everyday change, on a branch (recommended)
git switch -c my-change            # new branch off main
git add -A                         # stage everything (or name specific files)
git commit -s -m "Describe the change"   # -s = DCO sign-off (REQUIRED)
git push -u origin my-change       # push the branch; open a PR on GitHub

# release a new version (after merging to main)
#   1) edit src/datadoom/version.py  -> bump __version__
#   2) move CHANGELOG [Unreleased] -> [X.Y.Z]
git commit -s -am "Release X.Y.Z"
git tag -a vX.Y.Z -m "DataDoom X.Y.Z"
git push origin main --tags        # the tag triggers the release workflow
```

> **`-s` goes on `git commit`, never on `git push`.** Pushing has no sign-off flag.
> The rule of thumb: **every commit** gets `-s`; **no** push command gets it.

---

## 1. One-time setup

### 1a. Git identity (already set for you ✅)

The DCO trailer is built from your git `user.name` / `user.email`, and the email
**must match a verified email on your GitHub account**. Verify:

```powershell
git config user.name      # -> SanthoshReddy352
git config user.email     # -> gsreddy1182006@gmail.com
```

If you ever need to set them (use `--global` for all repos, omit it for just this one):

```powershell
git config --global user.name  "SanthoshReddy352"
git config --global user.email "gsreddy1182006@gmail.com"
```

### 1b. Fix the remote URL (recommended)

Your clone's `origin` points at the **old** repo name and only works because GitHub
redirects it:

```powershell
git remote -v
# origin  https://github.com/SanthoshReddy352/Hack-Forge.git   <-- old name
```

The project's canonical name is **`datadoom`** (matches the README badges, the docs
site URL, the GHCR image, and the PyPI trusted-publisher config). Repoint it so you
don't rely on the redirect:

```powershell
git remote set-url origin https://github.com/SanthoshReddy352/datadoom.git
git remote -v        # confirm it now shows .../datadoom.git
```

---

## 2. The DCO sign-off (`-s`)

### What it is

This project uses the **Developer Certificate of Origin** instead of a CLA (see
[CONTRIBUTING.md](../CONTRIBUTING.md) §DCO). "Signing off" just means appending a
trailer to your commit message certifying you wrote the code / have the right to
contribute it. `git commit -s` adds it automatically:

```
Describe the change

Signed-off-by: SanthoshReddy352 <gsreddy1182006@gmail.com>
```

That line **is** the DCO sign-off — there is nothing else to "get". It's generated
from your git identity (§1a), which is why the identity has to be correct.

### `-s` (DCO) vs `-S` (GPG) — don't confuse them

| Flag | Meaning | Needed here? |
|---|---|---|
| `-s` (lowercase) | **DCO sign-off** — adds the `Signed-off-by:` text trailer | **Yes, every commit** |
| `-S` (uppercase) | **GPG/SSH cryptographic signature** — shows a "Verified" badge | Optional, only if you maintain a signing key |

You asked "should I use `-s` on all pushes?" — there is no `-s` on `push`. Use `-s`
on **every `git commit`**. (You can also sign tags cryptographically with
`git tag -s`, which is the *uppercase*-style signing — separate from the DCO.)

### If you forget to sign off

```powershell
# last commit only:
git commit --amend -s --no-edit

# a whole branch's commits (re-applies them with sign-off):
git rebase --signoff main
```

### Make it automatic (optional)

Add an alias so you don't forget the flag:

```powershell
git config --global alias.cs "commit -s"
# then: git cs -m "message"
```

---

## 3. Pushing your changes

### Option A — feature branch + Pull Request (recommended)

This is the convention in CLAUDE.md / CONTRIBUTING and keeps `main` clean.

```powershell
git switch -c short-descriptive-name      # branch off the current main
# ...make your edits...
git status                                # review what changed
git add -A                                # stage all changes
#   (or stage specific files: git add README.md src/datadoom/cli/main.py)
git commit -s -m "Concise summary of the change"
git push -u origin short-descriptive-name # first push sets upstream
```

Then on GitHub click **"Compare & pull request"**, fill the template, and merge when
CI is green. After merging, sync your local main:

```powershell
git switch main
git pull
```

### Option B — commit straight to `main` (solo, quick)

Fine for a solo maintainer, but you lose the PR/CI safety net before code lands.

```powershell
git add -A
git commit -s -m "Concise summary of the change"
git push origin main
```

### Before you push — run the gates

So CI doesn't fail after the fact:

```powershell
.\.venv\Scripts\Activate.ps1
ruff check src tests
lint-imports
mypy
pytest
```

---

## 4. Updating the version

The single source of truth is **`src/datadoom/version.py`**:

```python
__version__ = "0.1.0"
```

When to bump and to what (the project follows SemVer-ish + PEP 440):

| Change | New version | Notes |
|---|---|---|
| First public, install-ready release | `0.1.0` | Drops the `.dev` suffix. |
| Pre-release / testing | `0.1.0.dev1`, `0.1.0rc1` | `pip install datadoom` **skips** `.devN`/`rcN` unless they're the only versions or you pass `--pre`. |
| Backwards-compatible additions | bump **minor** (`0.2.0`) | New optional spec fields, new features. |
| Bug fixes only | bump **patch** (`0.1.1`) | |
| Breaking changes (post-1.0) | bump **major** (`2.0.0`) | |

Steps for a version bump:

```powershell
# 1) edit src/datadoom/version.py  -> set __version__
# 2) edit CHANGELOG.md  -> rename "## [Unreleased]" to "## [X.Y.Z]" (add a fresh
#    empty [Unreleased] above it)
git commit -s -am "Release X.Y.Z"
```

> **Why bumping matters:** PyPI versions are **immutable** — you can never re-upload
> the same version. If a release fails partway (e.g. the `400 File already exists`
> you saw), the fix is a **new** version, not a re-push of the old one. The publish
> step is also set to `skip-existing`, so re-running the *same* version now no-ops
> instead of erroring.

---

## 5. Cutting a release (tag → CI publishes)

A release is just a **`v*` git tag** on `main`. Pushing the tag triggers
`.github/workflows/release.yml`, which builds the wheel/sdist (with the bundled web
Canvas), smoke-tests it, signs build provenance, creates a GitHub Release, publishes
to **PyPI** (OIDC, no token), and pushes the **Docker image** to GHCR.

```powershell
# after the version-bump commit from §4 is on main:
git tag -a v0.1.0 -m "DataDoom 0.1.0"     # annotated tag
#   (or: git tag -s v0.1.0 -m "..."  to GPG-sign the tag, if you have a key)
git push origin main --tags
```

The **tag name** and the **package version** should match (tag `v0.1.0` ⇒
`__version__ = "0.1.0"`). One-time PyPI/GHCR/Pages enablement and the full release
checklist are in [22_Release_and_Publishing_Runbook.md](22_Release_and_Publishing_Runbook.md).

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| PR fails a DCO check / commit lacks sign-off | committed without `-s` | `git commit --amend -s --no-edit` (last) or `git rebase --signoff main` (branch), then `git push --force-with-lease` |
| `400 File already exists` on PyPI | re-publishing an existing version (immutable) | bump `version.py` to a new version (§4); `skip-existing` already prevents the hard failure |
| `git push` rejected (non-fast-forward) | remote has commits you don't | `git pull --rebase` then push |
| Push goes to `Hack-Forge` | stale remote URL | `git remote set-url origin .../datadoom.git` (§1b) |
| `datadoom serve` says it needs `[server]` after installing | stale local install | `pip install --upgrade --force-reinstall --no-cache-dir "datadoom[server]"` |

---

## Quick answers to the questions that prompted this doc

- **How do I push to GitHub?** §3 — branch + PR (recommended) or straight to `main`;
  always `git commit -s`, then `git push`.
- **How do I get the signed DCO?** §2 — it's the `Signed-off-by:` trailer that
  `git commit -s` adds from your git identity. Nothing to download; just use `-s`.
- **How do I update versions?** §4 — edit `src/datadoom/version.py`, update the
  CHANGELOG, commit. Bump for every PyPI release (versions are immutable).
- **Should I use `-s` on all pushes?** `-s` is a **commit** flag, not a push flag.
  Use it on **every commit**; `git push` never takes `-s`.
