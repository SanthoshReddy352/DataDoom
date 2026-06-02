"""Canonical serialization & spec hashing (05 §1.1).

The spec hash is the identity of a dataset's *design*. It must be stable across
machines and runs, so we define a strict canonical JSON form:

- object keys sorted lexicographically,
- no insignificant whitespace,
- numbers normalized (integral floats collapse to ints; shortest float repr),
- arrays preserve author order (order is semantic),
- the ``seed`` field is excluded (seed is not part of the design identity).

    spec_hash = SHA256(canonical_json(spec_without_seed))   # hex
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _normalize(value: Any) -> Any:
    """Recursively normalize numbers and drop nothing else.

    Integral floats (``1.0``) become ints (``1``) so that a value authored as an
    int and one authored as a float-but-whole hash identically.
    """
    if isinstance(value, bool):
        # bool is a subclass of int — keep it as-is (True/False -> JSON booleans).
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return value
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def canonical_json(spec_body: dict[str, Any]) -> str:
    """Return the canonical JSON string for a spec dict (``seed`` removed)."""
    body = {k: v for k, v in spec_body.items() if k != "seed"}
    normalized = _normalize(body)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def spec_hash(spec_body: dict[str, Any]) -> str:
    """Compute the hex SHA256 of the canonical (seed-excluded) spec."""
    return hashlib.sha256(canonical_json(spec_body).encode("utf-8")).hexdigest()
