"""Templates endpoints (08 §10).

Full templates land in P5 (task 18); P1 ships the endpoints so the UI route is
coherent. Returns the empty set until the registry exists.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..schemas import TemplateSummary

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def list_templates() -> list[TemplateSummary]:
    return []
