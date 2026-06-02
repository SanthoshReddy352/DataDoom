# Governance

This is a summary; the full model lives in
[`docs_v2/15_Open_Source_Governance.md`](docs_v2/15_Open_Source_Governance.md).

DataDoom starts **maintainer-led (BDFL-lite)** and is designed to graduate to
**meritocratic multi-maintainer** governance as the community grows.

## Roles

- **Users** — file issues, request features, share specs/plugins.
- **Contributors** — submit PRs (code, docs, templates, plugins).
- **Maintainers** — review/merge, triage, cut releases, and guard the
  architecture invariants (determinism, engine purity, layering, honest stats).
- **Lead maintainer** (initially the founder) — final tie-breaker and roadmap
  steward, intending to delegate as trusted maintainers emerge.

## Becoming a maintainer

Sustained, high-quality contribution plus good review judgment → nominated by an
existing maintainer → lazy-consensus approval among maintainers.

## Decision-making

- **Lazy consensus** for most changes: merges if no maintainer objects within the
  review window.
- **DataDoom Enhancement Proposal (DDEP)** for big changes — anything touching the
  locked global decisions, the spec format, the plugin API, or the determinism
  guarantee. A short design doc, public discussion, maintainer sign-off, then
  implementation.
- Disagreements escalate to the lead maintainer as a last resort.
