"""API route modules (doc 08). Each exposes an ``APIRouter`` named ``router``."""

from __future__ import annotations

from . import artifacts, datasets, meta, plugins, runs, specs, templates

__all__ = ["artifacts", "datasets", "meta", "plugins", "runs", "specs", "templates"]
