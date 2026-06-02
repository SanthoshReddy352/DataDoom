"""DataDoom HTTP API (FastAPI). Thin layer over ``jobs`` + ``store`` + ``engine``.

``create_app()`` is the entry point; ``datadoom serve`` (CLI) runs it under
uvicorn.
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
