"""Dataset CRUD + spec versioning (08 §4-5).

Editing a spec never mutates a row — it creates a new immutable version and
repoints ``current_spec_id`` (the immutability invariant, 06 §5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from datadoom.engine import parse_spec

from .. import serializers
from ..deps import get_session, get_state
from ..errors import http_error
from ..schemas import (
    CreateDatasetRequest,
    Dataset,
    DatasetList,
    SaveSpecResponse,
    SpecBody,
    SpecDetail,
    SpecSummary,
    UpdateDatasetRequest,
)
from ..state import AppState
from ..store_helpers import (
    DatasetRepository,
    RunRepository,
    SpecRepository,
    latest_run_row,
    load_dataset,
)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=DatasetList)
def list_datasets(
    status: str | None = None,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    s: Session = Depends(get_session),
) -> DatasetList:
    rows, total = DatasetRepository(s).list(status=status, q=q, limit=limit, offset=offset)
    specs = SpecRepository(s)
    runs = RunRepository(s)
    items = [
        serializers.dataset_summary(r, specs.current(r), latest_run_row(runs, r))
        for r in rows
    ]
    return DatasetList(items=items, total=total)


@router.post("", response_model=Dataset, status_code=201)
def create_dataset(
    req: CreateDatasetRequest, s: Session = Depends(get_session)
) -> Dataset:
    datasets = DatasetRepository(s)
    if datasets.get_by_name(req.name) is not None:
        raise http_error(409, "conflict", f"a dataset named {req.name!r} already exists")

    row = datasets.create(name=req.name, description=req.description)
    current_spec = None
    if req.spec is not None:
        spec = parse_spec(req.spec)  # raises 422 with locator on invalid
        current_spec = SpecRepository(s).create_version(
            row, spec.body(), spec.spec_hash(), spec.datadoom_version
        )
    return serializers.dataset(row, current_spec, None)


@router.get("/{dataset_id}", response_model=Dataset)
def get_dataset(dataset_id: str, s: Session = Depends(get_session)) -> Dataset:
    row = load_dataset(s, dataset_id)
    current_spec = SpecRepository(s).current(row)
    latest = latest_run_row(RunRepository(s), row)
    return serializers.dataset(row, current_spec, latest)


@router.patch("/{dataset_id}", response_model=Dataset)
def update_dataset(
    dataset_id: str, req: UpdateDatasetRequest, s: Session = Depends(get_session)
) -> Dataset:
    datasets = DatasetRepository(s)
    row = load_dataset(s, dataset_id)
    if (
        req.name is not None
        and req.name != row.name
        and datasets.get_by_name(req.name) is not None
    ):
        raise http_error(409, "conflict", f"a dataset named {req.name!r} already exists")
    datasets.update(row, name=req.name, description=req.description)
    current_spec = SpecRepository(s).current(row)
    latest = latest_run_row(RunRepository(s), row)
    return serializers.dataset(row, current_spec, latest)


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: str,
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> Response:
    row = load_dataset(s, dataset_id)
    DatasetRepository(s).delete(row)  # ORM cascade -> specs/runs/artifacts/reports
    state.artifacts.remove_dataset(dataset_id)  # removes the artifact directory
    return Response(status_code=204)


@router.post("/{dataset_id}/duplicate", response_model=Dataset, status_code=201)
def duplicate_dataset(dataset_id: str, s: Session = Depends(get_session)) -> Dataset:
    datasets = DatasetRepository(s)
    specs = SpecRepository(s)
    src = load_dataset(s, dataset_id)
    src_spec = specs.current(src)

    new_name = _unique_copy_name(datasets, src.name)
    clone = datasets.create(name=new_name, description=src.description)
    new_spec = None
    if src_spec is not None:
        new_spec = specs.create_version(
            clone, dict(src_spec.body), src_spec.spec_hash, src_spec.datadoom_version
        )
    return serializers.dataset(clone, new_spec, None)


# --- spec versioning ----------------------------------------------------------
@router.put("/{dataset_id}/spec", response_model=SaveSpecResponse)
def save_spec(
    dataset_id: str, body: SpecBody, s: Session = Depends(get_session)
) -> SaveSpecResponse:
    row = load_dataset(s, dataset_id)
    spec = parse_spec(body)  # 422 with locator on invalid
    new_spec = SpecRepository(s).create_version(
        row, spec.body(), spec.spec_hash(), spec.datadoom_version
    )
    # A fresh edit returns the dataset to a draft state (a new run regenerates it).
    if row.status in {"completed", "failed"}:
        DatasetRepository(s).set_status(row, "draft")
    return SaveSpecResponse(
        spec_id=new_spec.spec_id, spec_hash=new_spec.spec_hash, version=new_spec.version
    )


@router.get("/{dataset_id}/spec", response_model=SpecDetail)
def get_current_spec(dataset_id: str, s: Session = Depends(get_session)) -> SpecDetail:
    row = load_dataset(s, dataset_id)
    spec = SpecRepository(s).current(row)
    if spec is None:
        raise http_error(404, "not_found", "dataset has no spec yet")
    return serializers.spec_detail(spec)


@router.get("/{dataset_id}/spec/history", response_model=list[SpecSummary])
def spec_history(dataset_id: str, s: Session = Depends(get_session)) -> list[SpecSummary]:
    load_dataset(s, dataset_id)
    return [serializers.spec_summary(r) for r in SpecRepository(s).history(dataset_id)]


@router.get("/{dataset_id}/spec/{version}", response_model=SpecDetail)
def get_spec_version(
    dataset_id: str, version: int, s: Session = Depends(get_session)
) -> SpecDetail:
    load_dataset(s, dataset_id)
    spec = SpecRepository(s).by_version(dataset_id, version)
    if spec is None:
        raise http_error(404, "not_found", f"no spec version {version}")
    return serializers.spec_detail(spec)


def _unique_copy_name(datasets: DatasetRepository, base: str) -> str:
    candidate = f"{base}-copy"
    i = 2
    while datasets.get_by_name(candidate) is not None:
        candidate = f"{base}-copy-{i}"
        i += 1
    return candidate
