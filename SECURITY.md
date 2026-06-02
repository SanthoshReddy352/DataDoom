# Security Policy

DataDoom is **local-first and offline-capable**: no telemetry, no mandatory
network access, no data leaves your machine. The threat model is documented in
[`docs_v2/14_Security_and_Privacy.md`](docs_v2/14_Security_and_Privacy.md).

## Reporting a vulnerability

Please report security issues **privately** rather than opening a public issue:

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on the
  repository, or
- email the maintainer at the address listed on the GitHub profile.

Include a description, reproduction steps, and impact. We aim to acknowledge
within a few days and to coordinate a fix and disclosure timeline with you.

## Scope notes

- Loading a spec executes **no arbitrary code**; specs are declarative data.
- Third-party **plugins** run with full process privileges — install only
  plugins you trust, same as any Python package.
