"""Distributions + honest compliance reporting."""

from __future__ import annotations

from .base import Distribution
from .builtins import (
    REGISTRY,
    sample_boolean,
    sample_categorical,
    sample_datetime,
    sample_text,
)
from .compliance import ComplianceReport, FeatureCompliance, assess_numeric
from .providers import (
    REALISTIC_GENERATORS,
    is_realistic_generator,
    resolve_locale,
    sample_provider,
)

__all__ = [
    "Distribution",
    "REGISTRY",
    "ComplianceReport",
    "FeatureCompliance",
    "assess_numeric",
    "sample_boolean",
    "sample_categorical",
    "sample_datetime",
    "sample_text",
    "sample_provider",
    "is_realistic_generator",
    "resolve_locale",
    "REALISTIC_GENERATORS",
]
