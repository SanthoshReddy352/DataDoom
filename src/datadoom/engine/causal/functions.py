"""Structural functions for SEM edges (05 §3, 04 §5).

Each edge carries a structural function ``fn`` that maps a parent's values to a
numeric *contribution*. A derived node sums the contributions of its incoming
edges and adds node noise (see ``execute.py``). Functions are pure and operate
on numpy arrays so they stay deterministic on the pinned path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from ..errors import SpecValidationError
from ..spec.models import CausalEdge


def _as_float(parent: np.ndarray) -> np.ndarray:
    """Coerce a parent column to float (booleans → 0/1)."""
    return np.asarray(parent, dtype=float)


class StructuralFn(ABC):
    """ABC for an edge's structural function."""

    name: str

    @abstractmethod
    def contribution(self, parent: np.ndarray, edge: CausalEdge) -> np.ndarray:
        """Return this edge's additive contribution to the child node."""

    def validate(self, edge: CausalEdge, locator: str) -> None:
        """Check the edge carries the params this function needs."""
        return None


class Linear(StructuralFn):
    name = "linear"

    def contribution(self, parent, edge):
        bias = edge.bias or 0.0
        return edge.weight * _as_float(parent) + bias

    def validate(self, edge, locator):
        if edge.weight is None:
            raise SpecValidationError("linear edge requires 'weight'", locator=locator)


class Logistic(StructuralFn):
    name = "logistic"

    def contribution(self, parent, edge):
        bias = edge.bias or 0.0
        z = edge.weight * _as_float(parent) + bias
        return 1.0 / (1.0 + np.exp(-z))

    def validate(self, edge, locator):
        if edge.weight is None:
            raise SpecValidationError("logistic edge requires 'weight'", locator=locator)


class Polynomial(StructuralFn):
    name = "polynomial"

    def contribution(self, parent, edge):
        p = _as_float(parent)
        out = np.zeros_like(p)
        for i, c in enumerate(edge.coeffs or ()):
            out = out + c * (p**i)
        return out

    def validate(self, edge, locator):
        if not edge.coeffs:
            raise SpecValidationError(
                "polynomial edge requires a non-empty 'coeffs' list", locator=locator
            )


class Map(StructuralFn):
    name = "map"

    def contribution(self, parent, edge):
        mapping = edge.mapping or {}
        out = np.empty(len(parent), dtype=float)
        for i, v in enumerate(parent):
            key = str(v)
            if key not in mapping:
                raise SpecValidationError(
                    f"map edge has no mapping for category {key!r}",
                    locator=f"causal edge {edge.src}->{edge.dst}",
                )
            out[i] = mapping[key]
        return out

    def validate(self, edge, locator):
        if not edge.mapping:
            raise SpecValidationError(
                "map edge requires a non-empty 'mapping'", locator=locator
            )


class Identity(StructuralFn):
    name = "identity"

    def contribution(self, parent, edge):
        return _as_float(parent)


STRUCTURAL_FNS: dict[str, StructuralFn] = {
    fn.name: fn for fn in (Linear(), Logistic(), Polynomial(), Map(), Identity())
}
