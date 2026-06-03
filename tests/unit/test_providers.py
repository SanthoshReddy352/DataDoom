"""Realistic text providers (mimesis-backed) — determinism + validation."""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.dist.providers import (
    REALISTIC_GENERATORS,
    is_realistic_generator,
    resolve_locale,
    sample_provider,
)
from datadoom.engine.errors import SpecValidationError
from datadoom.engine.rng import RNGFactory


def _rng(ns: str = "feature:x") -> np.random.Generator:
    return RNGFactory(spec_hash="deadbeef", seed=99).generator(ns)


@pytest.mark.parametrize("generator", sorted(REALISTIC_GENERATORS))
def test_every_provider_emits_strings(generator: str) -> None:
    out = sample_provider(_rng(), 8, generator)
    assert out.shape == (8,)
    assert all(isinstance(v, str) and v for v in out)


def test_same_seed_reproduces_values() -> None:
    a = sample_provider(_rng(), 16, "name")
    b = sample_provider(_rng(), 16, "name")
    assert list(a) == list(b)


def test_distinct_namespaces_diverge() -> None:
    a = sample_provider(_rng("feature:a"), 16, "name")
    b = sample_provider(_rng("feature:b"), 16, "name")
    assert list(a) != list(b)


def test_unknown_generator_raises() -> None:
    with pytest.raises(SpecValidationError, match="unknown text generator"):
        sample_provider(_rng(), 4, "not_a_provider")


def test_unknown_locale_raises() -> None:
    with pytest.raises(SpecValidationError, match="unknown locale"):
        resolve_locale("zz", locator="features.x.locale")


def test_locale_changes_output() -> None:
    en = sample_provider(_rng(), 16, "city", locale="en")
    de = sample_provider(_rng(), 16, "city", locale="de")
    assert list(en) != list(de)


def test_is_realistic_generator() -> None:
    assert is_realistic_generator("email")
    assert not is_realistic_generator("lorem")


SPEC = {
    "datadoom_version": "1",
    "name": "providers-test",
    "rows": 50,
    "features": {
        "full_name": {"type": "text", "generator": "name"},
        "email": {"type": "text", "generator": "email"},
        "note": {"type": "text", "generator": "lorem", "length": {"min": 3, "max": 6}},
    },
    "export": {"formats": ["csv"], "versions": ["clean"]},
}


def test_pipeline_produces_realistic_columns() -> None:
    spec = parse_spec(SPEC)
    frame = generate(spec, seed=7).frame
    # mimesis names contain a space; lorem filler is space-joined words too, so
    # assert on the email shape which is unambiguous.
    assert frame["email"].str.contains("@").all()
    assert frame["full_name"].str.contains(" ").all()


def test_pipeline_rejects_unknown_generator() -> None:
    bad = {**SPEC, "features": {"x": {"type": "text", "generator": "wizardry"}}}
    with pytest.raises(SpecValidationError, match="unknown text generator"):
        generate(parse_spec(bad), seed=1)
