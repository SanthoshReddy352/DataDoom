# 14 — Security & Privacy

> Honest, proportional posture for a **local-first, open-source** tool. Replaces the legacy enterprise "SOC2/mTLS/KMS/multi-tenant RLS" doc, most of which does not apply to software a user runs on their own machine. Obeys `00_README_Index.md`.

---

## 1. Threat Model (be precise about what we defend)

DataDoom's default deployment is **a local app on the user's own machine**, generating **synthetic** data. That fundamentally shapes the threat model:

| Asset | In local mode | In team mode (opt-in) |
|---|---|---|
| User's specs & artifacts | on the user's disk | on a shared server/object store |
| Network exposure | binds `localhost` only | exposed; needs TLS + auth |
| Sensitive data | usually none (data is synthetic) | possibly real reference samples |
| Multi-user trust | single user (the owner) | multiple users, roles |

**Primary risks we actually address:**
1. **Untrusted spec/plugin/template files** (a spec or plugin downloaded from the internet).
2. **Accidental network exposure** of the local server.
3. **Supply-chain integrity** of the `datadoom` package and its plugins.
4. **Privacy** — DataDoom must not phone home.

**Explicitly not in scope for the core:** multi-tenant isolation, SOC2/GDPR compliance pipelines, KMS-managed encryption, mTLS service mesh — these were SaaS-platform artifacts. A future hosted edition would own those; the OSS core does not pretend to.

---

## 2. Local-First Security Defaults

- **Bind to `127.0.0.1` by default.** The server is not reachable from the network unless the user explicitly sets `--host 0.0.0.0` (which prints a warning).
- **No authentication in local mode** — it's the user's own machine; adding mandatory auth would be friction theater. (Team mode adds real auth; see §5.)
- **No outbound network calls** in core functionality. Generation, validation, export, reporting all work fully offline.
- **Data never leaves the machine** in local mode. There is no cloud component to leak to.

---

## 3. Untrusted Input: Specs, Templates, Plugins

### 3.1 Specs & templates (data)
- Specs are **declarative data**, parsed by Pydantic with strict validation (`04 §9`). A spec cannot execute arbitrary code — it selects from registered distributions/fns/failures by name and supplies validated parameters.
- YAML is parsed with a **safe loader** (no arbitrary object construction / no `!!python/object`).
- Templates are specs + metadata — same safety as specs.
- Opening a malicious spec is therefore bounded to "generate a weird/large dataset," mitigated by the resource estimator's guardrails (`12 §8`).

### 3.2 Plugins (code) — the real risk
- **Plugins are arbitrary Python and run in-process with full user privileges. DataDoom does NOT sandbox them.** Installing a plugin is exactly as trusting as `pip install <anything>`.
- Mitigations:
  - The UI clearly **labels** third-party vs. core plugins.
  - Plugins are **never auto-installed** from a spec. A spec that references an unknown plugin fails validation with "plugin `X` not installed" — it does **not** fetch/run code.
  - Docs state plainly: *only install plugins you trust.* (`09 §7`)
  - Core ships a curated, reviewed built-in set; community plugins are opt-in installs.
- Future (deferred): optional plugin sandboxing/subprocess isolation if demand warrants — not promised in v1.

---

## 4. Supply-Chain Integrity

- **Signed releases:** wheels/sdists published to PyPI with provenance (PEP 740 / Sigstore attestations via the release workflow).
- **Pinned, reviewed dependencies:** core deps are few, permissively licensed (`11 §9`), and version-pinned for releases; Dependabot/renovate monitors CVEs.
- **Reproducible build of the frontend bundle** is verified in CI (`10 §3`) so the shipped `webdist/` matches the source.
- **SECURITY.md** documents a private disclosure channel and response SLA for vulnerabilities.

---

## 5. Team / Server Mode (opt-in) Security

When a user deliberately runs DataDoom as a shared server (`03 §6.2`), these become required (and documented in the deploy guide, not assumed by core):
- **TLS** via a reverse proxy (Caddy/nginx); never serve plaintext beyond localhost.
- **Authentication:** bearer-token / OAuth via the pluggable `api/deps.py` auth dependency.
- **Authorization:** app-level `owner_id` scoping (a user sees only their datasets); roles `admin/member/viewer`. (App-level scoping, **not** Postgres RLS, in core.)
- **Secrets** (DB URL, S3 keys, Redis) via environment variables, never committed.
- **Encryption at rest** is delegated to the chosen storage (e.g. S3 SSE, disk encryption) — DataDoom does not implement its own crypto.

---

## 6. Privacy

- **No telemetry by default.** DataDoom collects and transmits nothing.
- Any future analytics/update-check is **strictly opt-in**, off unless the user enables it, and documented exactly (what, where, why).
- **Synthetic data is the point** — DataDoom generates fake data, so it's a privacy-preserving alternative to using real data. The one case touching real data is the opt-in *reference fitting* feature (`05 §2.3`): the reference sample stays local and is used only to fit parameters; it is never uploaded.
- `metadata.json` records `spec_hash`, `seed`, and config — not raw external data. Authors should avoid putting secrets in `meta` free-form fields (documented).

---

## 7. Safe Defaults Summary

| Setting | Default | Rationale |
|---|---|---|
| Bind host | `127.0.0.1` | no accidental network exposure |
| Auth | off (local) / required (server) | friction-free local; safe shared |
| Telemetry | off | privacy by default |
| YAML loader | safe | no code execution via specs |
| Plugin install | manual, trusted only | plugins are code |
| Outbound network | none in core | offline-capable, no phone-home |
| Dependency licenses | permissive only (core) | keeps Apache-2.0 clean |

---

## 8. Responsible Use

DataDoom generates synthetic data for legitimate engineering, research, and education. The failure-injection and difficulty features are for **robustness testing**, not for fabricating data to misrepresent real-world results. This expectation is stated in the README and docs; misuse (e.g. passing synthetic data off as real measurements) is the user's responsibility.
