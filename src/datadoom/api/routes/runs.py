"""Generation run endpoints (08 §6, §9).

Creating a run returns ``202`` immediately with a resolved seed and a WebSocket
path; the worker executes it asynchronously and streams progress. Repeated
``Idempotency-Key`` headers return the existing run (``200``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.orm import Session

from datadoom.engine import parse_spec, resolve_seed

from .. import serializers
from ..deps import get_session, get_state
from ..errors import http_error
from ..schemas import (
    CancelResponse,
    CreateRunRequest,
    CreateRunResponse,
    RunSummary,
    UpdateRunRequest,
)
from ..state import AppState
from ..store_helpers import (
    RunRepository,
    SpecRepository,
    load_dataset,
    load_run,
)

router = APIRouter(prefix="/api", tags=["runs"])


def _ws_path(run_id: str) -> str:
    return f"/api/ws/runs/{run_id}"


@router.post("/datasets/{dataset_id}/runs", response_model=CreateRunResponse, status_code=202)
def create_run(
    dataset_id: str,
    req: CreateRunRequest,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> CreateRunResponse:
    dataset = load_dataset(s, dataset_id)
    spec_row = SpecRepository(s).current(dataset)
    if spec_row is None:
        raise http_error(400, "bad_request", "dataset has no spec to generate from")

    # Idempotency replay (08 §1): same key -> the existing run, 200.
    if idempotency_key is not None:
        existing_id = state.idempotency.get((dataset_id, idempotency_key))
        if existing_id is not None:
            existing = RunRepository(s).get(existing_id)
            if existing is not None:
                response.status_code = 200
                return CreateRunResponse(
                    run_id=existing.run_id,
                    status=existing.status,
                    seed=existing.seed,
                    ws=_ws_path(existing.run_id),
                )

    spec = parse_spec(dict(spec_row.body))
    seed = resolve_seed(spec, req.seed)
    name = req.name.strip() if req.name and req.name.strip() else None
    run = RunRepository(s).create(dataset.dataset_id, spec_row.spec_id, seed, name=name)
    run_id = run.run_id
    if idempotency_key is not None:
        state.idempotency[(dataset_id, idempotency_key)] = run_id

    # Commit the queued row before handing off to the worker thread so it is
    # visible when the worker opens its own session (the request's own context
    # manager will no-op commit again at the end).
    s.commit()
    state.worker.submit(run_id)

    return CreateRunResponse(run_id=run_id, status="queued", seed=seed, ws=_ws_path(run_id))


@router.get("/runs/{run_id}", response_model=RunSummary)
def get_run(run_id: str, s: Session = Depends(get_session)) -> RunSummary:
    return serializers.run_summary(load_run(s, run_id))


@router.get("/datasets/{dataset_id}/runs", response_model=list[RunSummary])
def list_runs(dataset_id: str, s: Session = Depends(get_session)) -> list[RunSummary]:
    load_dataset(s, dataset_id)
    rows = RunRepository(s).list_for_dataset(dataset_id)
    return [serializers.run_summary(r) for r in rows]


@router.patch("/runs/{run_id}", response_model=RunSummary)
def update_run(
    run_id: str, req: UpdateRunRequest, s: Session = Depends(get_session)
) -> RunSummary:
    run = load_run(s, run_id)
    name = req.name.strip()
    if not name:
        raise http_error(422, "validation_error", "a generation name is required")
    RunRepository(s).set_name(run, name)
    return serializers.run_summary(run)


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(
    run_id: str,
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> Response:
    run = load_run(s, run_id)
    if run.status in {"queued", "running"}:
        raise http_error(409, "conflict", "cancel the run before deleting it")
    dataset_id = run.dataset_id
    RunRepository(s).delete(run)  # ORM cascade -> artifacts/report rows
    state.artifacts.remove_run(dataset_id, run_id)  # remove the run's files
    return Response(status_code=204)


@router.post("/runs/{run_id}/cancel", response_model=CancelResponse)
def cancel_run(
    run_id: str,
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> CancelResponse:
    run = load_run(s, run_id)
    if run.status in {"completed", "failed", "cancelled"}:
        return CancelResponse(status=run.status)
    # Cooperative: flag the run; the worker aborts at the next stage boundary.
    state.hub.request_cancel(run_id)
    return CancelResponse(status="cancelling")


@router.post("/runs/{run_id}/inject", status_code=501)
def inject_failures(run_id: str, s: Session = Depends(get_session)) -> Response:
    """Failure-injected variant (08 §9). The failure engine lands in P3 (task 13)."""
    load_run(s, run_id)
    raise http_error(
        501, "not_implemented", "failure injection arrives in Phase 3 (engine/failure)"
    )
