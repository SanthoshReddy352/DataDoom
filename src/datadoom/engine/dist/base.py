"""Distribution ABC (05 §2).

A :class:`Distribution` knows how to *sample* from a target ``D(theta)`` using an
injected RNG, *validate* its parameters, and expose its theoretical *cdf* so the
compliance layer can run a KS test. Sampling is correct by construction — we
never refit parameters to the realized sample (05 §2.3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping

import numpy as np

from ..errors import SpecValidationError


class Distribution(ABC):
    name: str
    required_params: tuple[str, ...] = ()
    # Optional JSON-schema fragment for the feature `params`. Built-ins leave this
    # ``None`` (the Canvas renders their native controls); plugins declare one so
    # the UI can render config controls with no frontend work (09 §6).
    param_schema: Mapping[str, object] | None = None

    @abstractmethod
    def sample(self, rng: np.random.Generator, n: int, params: Mapping[str, float]) -> np.ndarray:
        """Draw ``n`` samples from the target distribution."""

    @abstractmethod
    def cdf(self, x: np.ndarray, params: Mapping[str, float]) -> np.ndarray:
        """Theoretical CDF F(x; params) — used for KS reporting."""

    def validate(self, params: Mapping[str, float], locator: str | None = None) -> None:
        """Check required params are present and satisfy domain constraints."""
        missing = [p for p in self.required_params if p not in params]
        if missing:
            raise SpecValidationError(
                f"distribution {self.name!r} missing params: {missing}", locator=locator
            )
        self._validate_domain(params, locator)

    def _validate_domain(self, params: Mapping[str, float], locator: str | None) -> None:
        """Override for per-distribution constraints (e.g. std > 0)."""
        return None
