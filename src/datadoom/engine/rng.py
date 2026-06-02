"""Seeded RNG factory — the determinism invariant (05 §1.2).

All randomness in the engine MUST flow through an :class:`RNGFactory`. No stdlib
``random``, ``uuid4``, ``time``, or ``np.random.*`` *global* calls are allowed in
the data path. Each logical stream gets its own independent generator keyed by
``namespace`` so that adding a feature never perturbs another's draws.

    key(ns) = SHA256(spec_hash || ":" || seed || ":" || ns)[:8] -> uint64
    RNG(ns) = numpy.random.Generator(PCG64(key(ns)))
"""

from __future__ import annotations

import hashlib

import numpy as np

# Stable namespace prefixes (documented in 05 §1.2). Helpers below build the
# full namespace string so call sites stay consistent.
NS_FEATURE = "feature"
NS_NOISE = "noise"
NS_FAILURE = "failure"
NS_PROBE = "probe"
NS_SHUFFLE = "shuffle"


def _derive_key(spec_hash: str, seed: int, namespace: str) -> int:
    """Derive a uint64 PCG64 key from (spec_hash, seed, namespace)."""
    payload = f"{spec_hash}:{seed}:{namespace}".encode()
    digest = hashlib.sha256(payload).digest()
    # First 8 bytes, big-endian, as an unsigned 64-bit integer.
    return int.from_bytes(digest[:8], byteorder="big", signed=False)


class RNGFactory:
    """Produces independent, deterministic generators per namespace.

    Two factories with identical ``(spec_hash, seed)`` yield identical draws for
    the same namespace, and different namespaces are statistically independent.
    """

    def __init__(self, spec_hash: str, seed: int) -> None:
        self.spec_hash = spec_hash
        self.seed = int(seed)

    def key(self, namespace: str) -> int:
        """Return the raw uint64 key for a namespace (used in determinism reports)."""
        return _derive_key(self.spec_hash, self.seed, namespace)

    def generator(self, namespace: str) -> np.random.Generator:
        """Return an independent ``numpy.random.Generator`` for ``namespace``."""
        return np.random.Generator(np.random.PCG64(self.key(namespace)))

    # Convenience namespace builders -------------------------------------------------

    def feature(self, name: str) -> np.random.Generator:
        return self.generator(f"{NS_FEATURE}:{name}")

    def noise(self, name: str) -> np.random.Generator:
        return self.generator(f"{NS_NOISE}:{name}")

    def failure(self, index: int) -> np.random.Generator:
        return self.generator(f"{NS_FAILURE}:{index}")

    def shuffle(self) -> np.random.Generator:
        return self.generator(NS_SHUFFLE)

    def key_digests(self, namespaces: list[str]) -> dict[str, str]:
        """Hex key digests for the determinism report section (06 §3.5)."""
        return {ns: format(self.key(ns), "016x") for ns in namespaces}
