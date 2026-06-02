"""Canonicalization + spec hashing (05 §1.1)."""

from __future__ import annotations

from datadoom.engine.spec import parse_spec
from datadoom.engine.spec.hashing import canonical_json, spec_hash

BASE = {
    "datadoom_version": "1",
    "name": "h",
    "rows": 10,
    "features": {"x": {"type": "numeric", "dist": "normal", "params": {"mean": 1, "std": 2}}},
}


def test_hash_excludes_seed() -> None:
    a = spec_hash({**BASE, "seed": 1})
    b = spec_hash({**BASE, "seed": 999})
    assert a == b


def test_integral_floats_normalize() -> None:
    a = spec_hash({**BASE, "features": {"x": {"type": "numeric", "dist": "normal",
                                              "params": {"mean": 40, "std": 2}}}})
    b = spec_hash({**BASE, "features": {"x": {"type": "numeric", "dist": "normal",
                                              "params": {"mean": 40.0, "std": 2.0}}}})
    assert a == b


def test_canonical_is_key_order_independent() -> None:
    a = canonical_json({"b": 1, "a": 2})
    b = canonical_json({"a": 2, "b": 1})
    assert a == b == '{"a":2,"b":1}'


def test_spec_object_hash_matches_body_hash() -> None:
    spec = parse_spec({**BASE, "seed": 5})
    assert spec.spec_hash() == spec_hash(spec.body())


# --- TH.6 hash discrimination (a change must move the hash) ---------------------------


def test_param_change_changes_hash() -> None:
    a = spec_hash({**BASE, "features": {"x": {"type": "numeric", "dist": "normal",
                                              "params": {"mean": 1, "std": 2}}}})
    b = spec_hash({**BASE, "features": {"x": {"type": "numeric", "dist": "normal",
                                              "params": {"mean": 1, "std": 3}}}})
    assert a != b


def test_category_reorder_changes_hash() -> None:
    # Category order is semantic, so reordering must yield a different hash.
    cat = {
        **BASE,
        "features": {"c": {"type": "categorical", "categories": ["a", "b", "c"]}},
    }
    reordered = {
        **BASE,
        "features": {"c": {"type": "categorical", "categories": ["b", "a", "c"]}},
    }
    assert spec_hash(cat) != spec_hash(reordered)
