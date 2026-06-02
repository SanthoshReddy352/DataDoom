"""Stateless spec helpers (08 §3): validate, hash, estimate.

These never touch the DB — they parse the posted spec through ``engine.spec``
(the single source of validation truth) and return derived facts.
"""

from __future__ import annotations

from fastapi import APIRouter

from datadoom.engine import parse_spec

from ..estimate import estimate as estimate_spec
from ..schemas import EstimateResponse, HashResponse, SpecBody, ValidateResponse

router = APIRouter(prefix="/api/specs", tags=["specs"])


@router.post("/validate", response_model=ValidateResponse)
def validate(body: SpecBody) -> ValidateResponse:
    # parse_spec raises SpecValidationError -> 422 with locator (handled centrally).
    spec = parse_spec(body)
    return ValidateResponse(valid=True, spec_hash=spec.spec_hash(), warnings=[])


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
