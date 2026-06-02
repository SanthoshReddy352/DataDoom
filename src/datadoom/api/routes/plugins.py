"""Plugins endpoint (08 §10).

The runtime plugin registry lands in P5 (task 17); P1 ships the endpoint so the
UI's plugin browser route is coherent. Returns the empty set until then.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import PluginInfo

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginInfo])
def list_plugins() -> list[PluginInfo]:
    return []
