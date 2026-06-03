"""Realistic text providers (names, emails, addresses, …) backed by *mimesis*.

The default ``text`` generator is ``lorem`` (see :func:`sample_text`), which emits
filler words. These providers make text *genuine-looking* — ``"Maria Alvarez"``
instead of ``"lorem ipsum dolor"`` — **without sacrificing determinism**, which is
DataDoom's headline guarantee (CLAUDE.md invariant #1).

How determinism is preserved
----------------------------
mimesis is a pure, offline library that draws from an *isolated*, seeded
``random.Random`` instance — it never touches global random state. We seed that
instance from the feature's own ``numpy`` generator (which is itself keyed by
``sha256(spec_hash || seed || namespace)``), so:

* the same ``(spec_hash, seed)`` reproduces byte-identical text, and
* each feature draws from an independent stream — adding one never perturbs
  another (invariant #1).

Byte-reproducibility holds *on the pinned path*: a different mimesis version may
emit different strings for the same seed, exactly like the numpy pin for numeric
draws (invariant #6). mimesis is therefore a pinned core dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np

from ..errors import SpecValidationError

if TYPE_CHECKING:
    from mimesis import Generic
    from mimesis.locales import Locale

# A curated provider catalog. Each entry maps a spec ``generator`` key to a
# callable that pulls one value from a seeded mimesis facade. Keep the keys
# stable: they are part of the spec surface (invariant #5, additive only).
_PROVIDERS: dict[str, Callable[[Generic], object]] = {
    # people
    "name": lambda g: g.person.full_name(),
    "first_name": lambda g: g.person.first_name(),
    "last_name": lambda g: g.person.last_name(),
    "email": lambda g: g.person.email(),
    "username": lambda g: g.person.username(),
    "phone": lambda g: g.person.phone_number(),
    "occupation": lambda g: g.person.occupation(),
    "title": lambda g: g.person.title(),
    "nationality": lambda g: g.person.nationality(),
    # places
    "address": lambda g: g.address.address(),
    "street": lambda g: g.address.street_name(),
    "city": lambda g: g.address.city(),
    "state": lambda g: g.address.state(),
    "country": lambda g: g.address.country(),
    "postal_code": lambda g: g.address.postal_code(),
    # business / finance
    "company": lambda g: g.finance.company(),
    "currency": lambda g: g.finance.currency_iso_code(),
    "price": lambda g: g.finance.price(),
    # internet
    "url": lambda g: g.internet.url(),
    "hostname": lambda g: g.internet.hostname(),
    "ipv4": lambda g: g.internet.ip_v4(),
    # generic text
    "word": lambda g: g.text.word(),
    "sentence": lambda g: g.text.sentence(),
    "color": lambda g: g.text.color(),
}

#: Generator keys served by mimesis (``lorem`` is handled by ``sample_text``).
REALISTIC_GENERATORS: frozenset[str] = frozenset(_PROVIDERS)


def is_realistic_generator(name: str) -> bool:
    """True if ``name`` is a mimesis-backed provider key."""
    return name in _PROVIDERS


def resolve_locale(locale: str, *, locator: str | None = None) -> "Locale":
    """Map a spec locale string (e.g. ``"en"``) to a mimesis ``Locale`` member."""
    from mimesis.locales import Locale

    try:
        return Locale(locale)
    except ValueError as exc:
        valid = sorted(loc.value for loc in Locale)
        raise SpecValidationError(
            f"unknown locale {locale!r} (known: {valid})", locator=locator
        ) from exc


def sample_provider(
    rng: np.random.Generator, n: int, generator: str, locale: str = "en"
) -> np.ndarray:
    """Draw ``n`` realistic values for ``generator``, seeded from ``rng``.

    The mimesis facade is seeded from a 32-bit integer pulled off the feature's
    own generator, so the output is reproducible and stream-independent.
    """
    provider = _PROVIDERS.get(generator)
    if provider is None:
        raise SpecValidationError(
            f"unknown text generator {generator!r} "
            f"(known: {sorted(REALISTIC_GENERATORS) + ['lorem']})"
        )

    from mimesis import Generic

    loc = resolve_locale(locale)
    seed = int(rng.integers(0, 2**32))
    facade = Generic(locale=loc, seed=seed)

    out = np.empty(n, dtype=object)
    for i in range(n):
        out[i] = str(provider(facade))
    return out
