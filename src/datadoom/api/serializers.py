"""ORM row -> API schema converters (keeps route bodies thin)."""

from __future__ import annotations

from typing import Any

from datadoom.store import (
    ArtifactRow,
    DatasetRow,
    GenerationRunRow,
    ReportRow,
    SpecRow,
)

from . import schemas


def spec_summary(row: SpecRow) -> schemas.SpecSummary:
    return schemas.SpecSummary(
        spec_id=row.spec_id,
        spec_hash=row.spec_hash,
        version=row.version,
        datadoom_version=row.datadoom_version,
        created_at=row.created_at,
    )


def spec_detail(row: SpecRow) -> schemas.SpecDetail:
    return schemas.SpecDetail(
        spec_id=row.spec_id,
        spec_hash=row.spec_hash,
        version=row.version,
        datadoom_version=row.datadoom_version,
        created_at=row.created_at,
        body=dict(row.body),
    )


def run_summary(row: GenerationRunRow) -> schemas.RunSummary:
    compliance = None
    if row.metrics:
        compliance = row.metrics.get("compliance_score")
    return schemas.RunSummary(
        run_id=row.run_id,
        dataset_id=row.dataset_id,
        spec_id=row.spec_id,
        spec_hash=row.spec.spec_hash if row.spec is not None else None,
        name=row.name,
        seed=row.seed,
        status=row.status,
        stage=row.stage,
        progress_pct=row.progress_pct,
        compliance_score=compliance,
        error=row.error,
        metrics=row.metrics,
        started_at=row.started_at,
        finished_at=row.finished_at,
        created_at=row.created_at,
    )


def latest_run(row: GenerationRunRow | None) -> schemas.LatestRun | None:
    if row is None:
        return None
    compliance = row.metrics.get("compliance_score") if row.metrics else None
    return schemas.LatestRun(
        run_id=row.run_id, status=row.status, compliance_score=compliance
    )


def _spec_stats(body: dict[str, Any] | None) -> tuple[int | None, int | None]:
    if not body:
        return None, None
    rows = body.get("rows")
    features = body.get("features")
    return rows, (len(features) if isinstance(features, dict) else None)


def dataset_summary(
    row: DatasetRow, current_spec: SpecRow | None, latest: GenerationRunRow | None
) -> schemas.DatasetSummary:
    rows, features = _spec_stats(current_spec.body if current_spec else None)
    compliance = latest.metrics.get("compliance_score") if latest and latest.metrics else None
    return schemas.DatasetSummary(
        dataset_id=row.dataset_id,
        name=row.name,
        description=row.description,
        status=row.status,
        rows=rows,
        features=features,
        compliance_score=compliance,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def dataset(
    row: DatasetRow, current_spec: SpecRow | None, latest: GenerationRunRow | None
) -> schemas.Dataset:
    return schemas.Dataset(
        dataset_id=row.dataset_id,
        name=row.name,
        description=row.description,
        status=row.status,
        current_spec=spec_detail(current_spec) if current_spec else None,
        latest_run=latest_run(latest),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def artifact(row: ArtifactRow) -> schemas.Artifact:
    # The real on-disk filename is the basename of the storage URI — the
    # authoritative name (data.csv, data.injected.csv, metadata.json, …) so the
    # UI never has to guess clean-vs-injected from version/format.
    filename = row.storage_uri.replace("\\", "/").rsplit("/", 1)[-1]
    return schemas.Artifact(
        artifact_id=row.artifact_id,
        run_id=row.run_id,
        version=row.version,
        split=row.split,
        format=row.format,
        filename=filename,
        size_bytes=row.size_bytes,
        checksum_sha256=row.checksum_sha256,
        created_at=row.created_at,
    )


def report(row: ReportRow) -> schemas.Report:
    return schemas.Report(
        report_id=row.report_id,
        run_id=row.run_id,
        compliance_score=row.compliance_score,
        distribution=row.distribution,
        correlation=row.correlation,
        mutual_information=row.mutual_information,
        causal_truth=row.causal_truth,
        difficulty=row.difficulty,
        failures=row.failures,
        profile=row.profile,
        determinism=row.determinism,
    )
