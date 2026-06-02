# 18 — AI-Accelerated Engineering Playbook

> How to build DataDoom with an AI coding agent **without** wrecking the architecture or the determinism guarantee. You are the **architect**; the AI is a **high-speed implementer**. Obeys `00_README_Index.md`.

---

## 1. Why this is easier than the legacy plan

The legacy playbook had to coordinate Go + Python + Kafka + gRPC + K8s across an AI's context window — a recipe for hallucinated infra and race conditions. DataDoom is **one Python package + one React app**, with **pure, testable engine modules** and a **hard, automatable correctness oracle** (reproducibility checksums). That makes it an almost ideal AI-build target: small surface, strong tests, fast feedback.

---

## 2. Rules of Engagement

1. **Contract-first, then code.** For each module, agree on the interface (ABC + types from `06`/`09`) before implementation. Don't ask "write the engine"; ask "implement `Distribution.sample` for `normal` to this signature, with these tests."
2. **One module per session.** Build `rng` → `spec` → `dist` → `export` → `pipeline` in separate, focused sessions. Long marathon sessions cause context drift and silent constraint loss.
3. **Tests before/with implementation (TDD).** Especially for the engine: ask for the determinism/statistical tests first, run them, feed failures back.
4. **Feed the agent only the relevant docs.** For `engine.dist`, provide `04 §4`, `05 §2`, `09 §4.1` — not all 20 docs. (Pointers, not dumps.)
5. **A `CLAUDE.md`/agent-rules file in the repo root** restates the non-negotiables (below) so every session inherits them.
6. **Review the full diff, not just the changed lines** — agents sometimes "helpfully" rewrite a nearby working function.

---

## 3. Repo-root agent rules (`CLAUDE.md`) — must include

```
- Engine purity: nothing in src/datadoom/engine/ may import fastapi, sqlalchemy,
  the api/, store/, or jobs/ packages. (import-linter enforces this.)
- Determinism: ALL randomness goes through engine.rng's injected Generator.
  NEVER use random, np.random.* globals, uuid4, time, or hashlib-for-randomness
  in the data path. No reliance on dict/set iteration order for sampling.
- Honest stats: sample from the requested distribution and REPORT KS/compliance.
  NEVER refit distribution parameters to the generated sample ("auto-correction").
- One pipeline: CLI, API, and datadoom.generate() all call engine.pipeline.
  Do not duplicate generation logic anywhere.
- Spec is additive within datadoom_version: 1. No breaking spec changes.
- Prefer a plugin (engine consumes ABCs) over a core special-case.
- Offline-first: no core code path may require network access.
- Tests required: stochastic code ships with a determinism test.
```

---

## 4. Per-Phase AI Workflow (maps to `17`)

### Engine modules (rng/spec/dist/causal/failure/difficulty/export)
- **Your job:** provide the relevant math (`05`) + spec (`04`) sections and the ABC signature; ask for pytest tests first.
- **AI's job:** implement the function + docstring; iterate on test failures you paste back.
- **🚨 Determinism Trap:** the agent *will* reach for `np.random.normal(...)` or `random.random()`. Audit every stochastic line; confirm it uses the injected `rng`. The determinism test is your safety net — keep it green.
- **🚨 Auto-correction Trap:** if you ask for "make the data pass the KS test," the agent may refit parameters. Don't. The test in `13 §4` (KS rejection ≈ α; params unchanged) guards this.

### Store / DB
- **Your job:** provide `06`/`07`; set up SQLite locally.
- **AI's job:** SQLAlchemy models + Alembic `0001_init` + repositories.
- **🚨 Trap:** agent may invent Postgres-only DDL (JSONB, RLS, partitioning). DataDoom core is **SQLite-portable**; reject PG-only constructs in core (`07 §4`).

### API
- **Your job:** provide `08`; remind it auth is a no-op dependency in local mode.
- **AI's job:** FastAPI routes mapped to Pydantic schemas; WS hub; SSE fallback.
- **🚨 Trap:** agent may add mutating spec endpoints (`PUT spec` that edits in place). Specs are **immutable**; edits create new versions (`06 §5`, `08 §5`).

### Frontend
- **Your job:** provide `02`; dictate state strategy (Zustand + TanStack Query).
- **AI's job:** Tailwind components, React Flow graph, WS client, schema-fragment form renderer.
- **🚨 Trap:** async state in the graph + WS can cause infinite `useEffect` re-render loops. Review effect dependencies; prefer derived state.

### Plugins
- **Your job:** provide `09`; insist plugins use the injected `rng`.
- **AI's job:** ABCs, loader (entry points + local dir), registry, `plugin new/check`, contract tests.
- **🚨 Trap:** the agent may auto-`pip install` a plugin referenced by a spec. **Never** — unknown plugin = validation error, not a code fetch (`14 §3.2`).

---

## 5. The "Do Not Trust" Checklist (keep on your desk)

- [ ] **Sycophancy:** if you propose breaking an invariant (e.g. "just import the DB into engine to save time"), the agent may agree. *You* hold the architecture line.
- [ ] **Silent rewrite:** re-read full diffs; watch for unrelated function rewrites.
- [ ] **Monolith temptation:** the agent likes one big `app.py`/`pipeline.py`. Enforce the module structure (`10`); import-linter is the automated backstop.
- [ ] **Library hallucination:** check new entries in `pyproject.toml`/`package.json` — real, maintained, permissively licensed (`11 §9`)?
- [ ] **Error dilution:** reject `except Exception: pass` and `log.fatal`; demand structured, located errors (`08 §1`).
- [ ] **Determinism drift:** any new stochastic code without a determinism test is incomplete.
- [ ] **Scope creep:** if the agent proposes Kafka/GPU/microservices "for scale," that's the legacy ghost — out of scope (`00`).

---

## 6. Leverage Points (where AI shines on this project)

- **Statistical/algorithm code** (`engine.dist`, `causal`, `failure`) — well-specified math (`05`) → fast, correct implementations with tests.
- **Boilerplate** — SQLAlchemy models, FastAPI routes, Pydantic schemas, Typer commands, React components.
- **Tests** — generating the determinism/statistical/property tests that *are* the guarantee.
- **Docs** — keeping the docs site in sync with code (the agent reads these docs as ground truth).

---

## 7. Verification Loop (every change)

```
1. Agent implements against the agreed interface + tests.
2. Run: ruff, mypy, import-linter, pytest (incl. determinism).
3. For stochastic code: run the repro test twice → identical checksums.
4. Review the FULL diff for invariant violations (§5).
5. Only then commit (with DCO sign-off).
```

The reproducibility checksum is the killer feature for AI-assisted development: **the correctness of the core is machine-checkable**, so the agent can iterate fast while the test suite prevents regressions in the one property that matters most.

---

## 8. Summary

DataDoom is a great AI-build target *because* the design is small, pure, and test-anchored. Use the agent to move fast on algorithms, boilerplate, and tests — but **own the architecture**: guard engine purity, determinism, honest statistics, the immutable spec, and the scope fences. The automated gates (import-linter + determinism matrix) turn those principles into walls the agent can't accidentally walk through.
