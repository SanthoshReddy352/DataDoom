"""Meta endpoints (08 §11): health + version."""

from __future__ import annotations

import platform
import sys
from typing import Any

from fastapi import APIRouter

from datadoom.engine.reference import build_capabilities
from datadoom.version import __version__

from ..schemas import HealthResponse, VersionResponse

router = APIRouter(prefix="/api", tags=["meta"])

# The spec format version DataDoom currently authors/reads (independent of the
# HTTP API version, 08 §13).
DATADOOM_SPEC_VERSION = "1"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(
        version=__version__,
        datadoom_version=DATADOOM_SPEC_VERSION,
        python=platform.python_version(),
        platform=f"{platform.system()} {platform.release()} ({sys.platform})",
    )


@router.get("/spec-reference")
def spec_reference() -> dict[str, Any]:
    """Machine-readable spec capabilities manifest (for AI/tooling authoring).

    Built from the live registries, so plugin-registered capabilities are
    included. Mirrors the ``datadoom spec-reference`` CLI.
    """
    return build_capabilities()
