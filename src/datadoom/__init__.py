"""DataDoom — local-first engine for reproducible synthetic data.

Public API:

    >>> import datadoom
    >>> spec = datadoom.load_spec("dataset.datadoom.yaml")
    >>> result = datadoom.generate(spec, seed=42)
    >>> result.frame.head()
"""

from __future__ import annotations

from .engine import Spec, generate, load_spec, parse_spec, validate_spec
from .version import __version__

__all__ = [
    "Spec",
    "generate",
    "load_spec",
    "parse_spec",
    "validate_spec",
    "__version__",
]
