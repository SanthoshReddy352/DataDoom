"""Spec parsing, validation, canonicalization and hashing."""

from __future__ import annotations

from typing import Any

import yaml

from ..errors import SpecValidationError
from .hashing import canonical_json, spec_hash
from .models import Spec
from .validate import validate_spec

__all__ = [
    "Spec",
    "validate_spec",
    "canonical_json",
    "spec_hash",
    "load_spec",
    "parse_spec",
]


def parse_spec(data: dict[str, Any]) -> Spec:
    """Parse a raw dict into a validated :class:`Spec` (shape + cross-field)."""
    from pydantic import ValidationError

    try:
        spec = Spec.model_validate(data)
    except ValidationError as exc:
        # Surface the first error with a dotted locator the UI/CLI can use.
        first = exc.errors()[0]
        locator = ".".join(str(p) for p in first["loc"])
        raise SpecValidationError(first["msg"], locator=locator) from exc
    validate_spec(spec)
    return spec


def load_spec(path: str) -> Spec:
    """Load and validate a spec from a YAML (or JSON) file."""
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SpecValidationError("spec file must be a mapping at the top level")
    return parse_spec(data)
