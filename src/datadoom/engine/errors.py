"""Engine-level exceptions.

These are framework-free and carry a ``locator`` so the UI/CLI can point the
user at the offending control (a feature name, an edge, a list index).
"""

from __future__ import annotations


class DataDoomError(Exception):
    """Base class for all engine errors."""


class SpecValidationError(DataDoomError):
    """A spec failed structural or cross-field validation.

    ``locator`` identifies *where* the problem is (e.g. ``features.age.params``,
    ``causal.edges[2]``) so a caller can highlight it.
    """

    def __init__(self, message: str, locator: str | None = None) -> None:
        self.locator = locator
        self.message = message
        super().__init__(f"{locator}: {message}" if locator else message)


class DistributionError(DataDoomError):
    """An unknown distribution or invalid distribution parameters."""


class ReproducibilityError(DataDoomError):
    """A determinism/verification check failed (checksum mismatch)."""
