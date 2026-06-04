"""Templates endpoints (08 §10).

Surfaces the built-in domain templates (17 step 18). The gallery lists them; the
detail endpoint returns the full spec so the Canvas can create a dataset from it
in one click (the existing create flow accepts a ``spec``).
"""

from __future__ import annotations

from fastapi import APIRouter

from datadoom.templates import get_template, list_templates, load_template_body

from ..errors import http_error
from ..schemas import TemplateDetail, TemplateSummary

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateSummary])
def list_all() -> list[TemplateSummary]:
    return [TemplateSummary(**t.to_summary()) for t in list_templates()]


@router.get("/{template_id}", response_model=TemplateDetail)
def get_one(template_id: str) -> TemplateDetail:
    meta = get_template(template_id)
    if meta is None:
        raise http_error(404, "not_found", f"template {template_id!r} not found")
    return TemplateDetail(**meta.to_summary(), spec=load_template_body(template_id))
