"""Public, stable contract surface for plugin authors (09 §4).

Import the base classes and the ``schema`` helper from here::

    from datadoom.plugin import Distribution, schema

    class WeibullDistribution(Distribution):
        name = "weibull"
        param_schema = schema({"k": {"type": "number", "minimum": 0}})
        def sample(self, rng, n, params): ...
        def cdf(self, x, params): ...

These names are re-exported from ``datadoom.plugins.contracts`` and stay stable
even as the engine's internal layout evolves.
"""

from __future__ import annotations

from datadoom.plugins.contracts import (
    Distribution,
    Exporter,
    FailureMode,
    ProbeModel,
    StructuralFn,
    schema,
)

__all__ = [
    "Distribution",
    "StructuralFn",
    "FailureMode",
    "Exporter",
    "ProbeModel",
    "schema",
]
