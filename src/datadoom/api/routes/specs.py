"""Stateless spec helpers (08 §3): validate, hash, estimate.

These never touch the DB — they parse the posted spec through ``engine.spec``
(the single source of validation truth) and return derived facts.
"""

from __future__ import annotations

import yaml
from fastapi import APIRouter

from datadoom.engine import parse_spec
from datadoom.engine.errors import SpecValidationError

from ..estimate import estimate as estimate_spec
from ..schemas import (
    EstimateResponse,
    HashResponse,
    ParseResponse,
    ParseTextRequest,
    SpecBody,
    ValidateResponse,
)

router = APIRouter(prefix="/api/specs", tags=["specs"])


@router.post("/validate", response_model=ValidateResponse)
def validate(body: SpecBody) -> ValidateResponse:
    # parse_spec raises SpecValidationError -> 422 with locator (handled centrally).
    spec = parse_spec(body)
    return ValidateResponse(valid=True, spec_hash=spec.spec_hash(), warnings=[])


@router.post("/parse", response_model=ParseResponse)
def parse(body: ParseTextRequest) -> ParseResponse:
    """Parse raw YAML/JSON spec text → validated spec body (web 'New from YAML').

    YAML is parsed by the same PyYAML loader the CLI uses, then validated through
    the single ``engine.spec`` path, so the web import accepts exactly what
    ``datadoom run file.yaml`` would. Syntax and validation errors come back as a
    422 with a ``locator`` (handled centrally).
    """
    try:
        data = yaml.safe_load(body.text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        loc = f"line {mark.line + 1}" if mark is not None else None
        raise SpecValidationError(f"invalid YAML: {exc}", locator=loc) from exc
    if not isinstance(data, dict):
        raise SpecValidationError("spec must be a mapping at the top level (key: value …)")
    spec = parse_spec(data)
    return ParseResponse(valid=True, spec_hash=spec.spec_hash(), spec=spec.body())


@router.post("/hash", response_model=HashResponse)
def spec_hash(body: SpecBody) -> HashResponse:
    spec = parse_spec(body)
    return HashResponse(spec_hash=spec.spec_hash())


@router.post("/estimate", response_model=EstimateResponse)
def estimate(body: SpecBody) -> EstimateResponse:
    spec = parse_spec(body)
    est = estimate_spec(spec)
    return EstimateResponse(
        estimated_runtime_seconds=est.estimated_runtime_seconds,
        estimated_ram_mb=est.estimated_ram_mb,
        estimated_size_bytes=est.estimated_size_bytes,
        features=est.features,
        edges=est.edges,
        gpu_required=est.gpu_required,
    )
