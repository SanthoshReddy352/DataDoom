"""RNG determinism + namespace independence (05 §1.2)."""

from __future__ import annotations

import numpy as np

from datadoom.engine.rng import RNGFactory


def test_same_inputs_identical_draws() -> None:
    a = RNGFactory("hash", 7).feature("age").random(10)
    b = RNGFactory("hash", 7).feature("age").random(10)
    assert np.array_equal(a, b)


def test_different_seed_differs() -> None:
    a = RNGFactory("hash", 1).feature("age").random(10)
    b = RNGFactory("hash", 2).feature("age").random(10)
    assert not np.array_equal(a, b)


def test_namespaces_are_independent() -> None:
    f = RNGFactory("hash", 7)
    a = f.feature("age").random(20)
    b = f.feature("income").random(20)
    assert not np.array_equal(a, b)


def test_adding_a_namespace_does_not_perturb_others() -> None:
    # Drawing 'income' must not change what 'age' produces — generators are
    # independent, so order of creation is irrelevant.
    f1 = RNGFactory("hash", 7)
    age_only = f1.feature("age").random(15)

    f2 = RNGFactory("hash", 7)
    f2.feature("income").random(15)  # create another namespace first
    age_after = f2.feature("age").random(15)

    assert np.array_equal(age_only, age_after)


def test_key_digest_is_stable_hex() -> None:
    digests = RNGFactory("hash", 7).key_digests(["feature:age"])
    assert set(digests) == {"feature:age"}
    assert len(digests["feature:age"]) == 16
