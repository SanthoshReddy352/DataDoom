"""Plugins endpoint (08 §10).

Returns the live plugin registry — core built-ins plus anything discovered from
entry points or the local plugins directory at startup (09 §3). The Canvas reads
each entry's ``schema`` fragment to render config controls for third-party
capabilities with no frontend changes (09 §6).
"""

from __future__ import annotations

from fastapi import APIRouter

from datadoom.plugins import get_registry

from ..schemas import PluginInfo

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginInfo])
def list_plugins() -> list[PluginInfo]:
    return [PluginInfo(**record.to_info()) for record in get_registry().records()]
