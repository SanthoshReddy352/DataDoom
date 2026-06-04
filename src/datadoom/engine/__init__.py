"""The pure DataDoom engine — no web/DB/framework imports.

This package is an independently installable library: spec parsing, the seeded
RNG, distributions, export and the deterministic pipeline.
"""

from __future__ import annotations

from .errors import (
    DataDoomError,
    DistributionError,
    ReproducibilityError,
    SpecValidationError,
)
from .pipeline import RunContext, RunResult, generate, resolve_seed
from .reference import build_capabilities
from .reports import ReportBundle, build_report
from .rng import RNGFactory
from .spec import Spec, load_spec, parse_spec, validate_spec

__all__ = [
    "generate",
    "resolve_seed",
    "RunContext",
    "RunResult",
    "ReportBundle",
    "build_report",
    "build_capabilities",
    "RNGFactory",
    "Spec",
    "load_spec",
    "parse_spec",
    "validate_spec",
    "DataDoomError",
    "SpecValidationError",
    "DistributionError",
    "ReproducibilityError",
]
