"""Artifacts, preview, report, and bundle download (08 §8).

These power the Results screen: list output files, stream a download (with the
reproducibility checksum in a header), preview the first rows, fetch the full
report, or download a zip bundle (artifacts + metadata + spec).
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from .. import serializers
from ..deps import get_session, get_state
from ..errors import http_error
from ..schemas import Artifact, PreviewResponse, Report
from ..state import AppState
from ..store_helpers import (
    ArtifactRepository,
    ReportRepository,
    SpecRepository,
    load_run,
)

router = APIRouter(prefix="/api", tags=["artifacts"])


@router.get("/runs/{run_id}/artifacts", response_model=list[Artifact])
def list_artifacts(run_id: str, s: Session = Depends(get_session)) -> list[Artifact]:
    load_run(s, run_id)
    return [serializers.artifact(a) for a in ArtifactRepository(s).list_for_run(run_id)]


@router.get("/artifacts/{artifact_id}/download")
def download_artifact(
    artifact_id: str,
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> FileResponse:
    art = ArtifactRepository(s).get(artifact_id)
    if art is None:
        raise http_error(404, "not_found", f"artifact {artifact_id} not found")
    path = state.artifacts.open_uri(art.storage_uri)
    if not path.exists():
        raise http_error(404, "not_found", "artifact file is missing on disk")
    return FileResponse(
        path,
        filename=path.name,
        headers={"X-Checksum-SHA256": art.checksum_sha256},
    )


@router.get("/runs/{run_id}/report", response_model=Report)
def get_report(run_id: str, s: Session = Depends(get_session)) -> Report:
    load_run(s, run_id)
    rep = ReportRepository(s).get_for_run(run_id)
    if rep is None:
        raise http_error(404, "not_found", "no report (run not completed)")
    return serializers.report(rep)


@router.get("/runs/{run_id}/preview", response_model=PreviewResponse)
def preview(
    run_id: str,
    version: str = "clean",
    split: str = "full",
    limit: int = Query(100, ge=1, le=5000),
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> PreviewResponse:
    run = load_run(s, run_id)
    arts = ArtifactRepository(s).list_for_run(run_id)
    target = next(
        (
            a
            for a in arts
            if a.format == "csv" and a.version == version and (a.split or "full") == split
        ),
        None,
    )
    if target is None:
        raise http_error(404, "not_found", "no matching data artifact to preview")

    path = state.artifacts.open_uri(target.storage_uri)
    if not path.exists():
        raise http_error(404, "not_found", "artifact file is missing on disk")

    frame = pd.read_csv(path, nrows=limit)
    spec_row = SpecRepository(s).get(run.spec_id)
    total = (spec_row.body.get("rows") if spec_row else None) or len(frame)
    rows = frame.where(pd.notna(frame), None).values.tolist()
    return PreviewResponse(columns=list(frame.columns), rows=rows, total=int(total))


@router.get("/runs/{run_id}/bundle")
def bundle(
    run_id: str,
    s: Session = Depends(get_session),
    state: AppState = Depends(get_state),
) -> StreamingResponse:
    run = load_run(s, run_id)
    run_dir: Path = state.artifacts.run_dir(run.dataset_id, run_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(run_dir.glob("*")):
            if f.is_file():
                zf.write(f, arcname=f.name)
    buf.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{run_id}.zip"'}
    return StreamingResponse(buf, media_type="application/zip", headers=headers)
