"""The Phase 0 tooling gate: a trivial test that must pass in CI everywhere."""

from __future__ import annotations

import datadoom


def test_version_is_exposed() -> None:
    assert isinstance(datadoom.__version__, str)
    assert datadoom.__version__


def test_public_api_surface() -> None:
    for name in ("Spec", "generate", "load_spec", "parse_spec", "validate_spec"):
        assert hasattr(datadoom, name)
