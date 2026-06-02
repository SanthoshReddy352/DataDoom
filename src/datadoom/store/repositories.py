"""Repositories — the only way the app reads/writes metadata rows.

Each repository wraps a live :class:`~sqlalchemy.orm.Session`. They enforce the
domain invariants from doc 06 §5 — most importantly **spec immutability**: an
edit never updates a spec row, it creates a new version and repoints the
dataset's ``current_spec_id``.

UUID PKs are generated here with ``uuid4``. This is the persistence layer, NOT
the engine data path, so the determinism ban on ``uuid4`` does not apply (DB
identity has no bearing on reproducible artifact bytes).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db import utcnow_iso
from .models import (
    ArtifactRow,
    DatasetRow,
    GenerationRunRow,
    ReportRow,
    SpecRow,
)


def _uid() -> str:
    return str(uuid.uuid4())


class DatasetRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(
        self, name: str, description: str | None = None, owner_id: str | None = None
    ) -> DatasetRow:
        now = utcnow_iso()
        row = DatasetRow(
            dataset_id=_uid(),
            name=name,
            description=description,
            status="draft",
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
        )
        self.s.add(row)
        self.s.flush()
        return row

    def get(self, dataset_id: str) -> DatasetRow | None:
        return self.s.get(DatasetRow, dataset_id)

    def get_by_name(self, name: str, owner_id: str | None = None) -> DatasetRow | None:
        stmt = select(DatasetRow).where(
            DatasetRow.name == name, DatasetRow.owner_id.is_(owner_id)
        )
        return self.s.scalars(stmt).first()

    def list(
        self,
        status: str | None = None,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DatasetRow], int]:
        stmt = select(DatasetRow)
        count_stmt = select(func.count()).select_from(DatasetRow)
        if status:
            stmt = stmt.where(DatasetRow.status == status)
            count_stmt = count_stmt.where(DatasetRow.status == status)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(DatasetRow.name.like(like))
            count_stmt = count_stmt.where(DatasetRow.name.like(like))
        total = self.s.scalar(count_stmt) or 0
        stmt = stmt.order_by(DatasetRow.updated_at.desc()).limit(limit).offset(offset)
        return list(self.s.scalars(stmt).all()), int(total)

    def touch(self, row: DatasetRow) -> None:
        row.updated_at = utcnow_iso()

    def update(
        self, row: DatasetRow, name: str | None = None, description: str | None = None
    ) -> DatasetRow:
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        self.touch(row)
        return row

    def set_status(self, row: DatasetRow, status: str) -> None:
        row.status = status
        self.touch(row)

    def delete(self, row: DatasetRow) -> None:
        # ORM cascade removes specs/runs/artifacts/reports rows.
        self.s.delete(row)


class SpecRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create_version(
        self,
        dataset: DatasetRow,
        body: dict[str, Any],
        spec_hash: str,
        datadoom_version: str,
    ) -> SpecRow:
        """Create the next immutable spec snapshot and repoint the dataset."""
        next_version = (
            self.s.scalar(
                select(func.coalesce(func.max(SpecRow.version), 0)).where(
                    SpecRow.dataset_id == dataset.dataset_id
                )
            )
            or 0
        ) + 1
        row = SpecRow(
            spec_id=_uid(),
            dataset_id=dataset.dataset_id,
            spec_hash=spec_hash,
            body=body,
            datadoom_version=datadoom_version,
            version=next_version,
            created_at=utcnow_iso(),
        )
        self.s.add(row)
        self.s.flush()
        dataset.current_spec_id = row.spec_id
        dataset.updated_at = utcnow_iso()
        return row

    def get(self, spec_id: str) -> SpecRow | None:
        return self.s.get(SpecRow, spec_id)

    def current(self, dataset: DatasetRow) -> SpecRow | None:
        if dataset.current_spec_id is None:
            return None
        return self.s.get(SpecRow, dataset.current_spec_id)

    def history(self, dataset_id: str) -> list[SpecRow]:
        stmt = (
            select(SpecRow)
            .where(SpecRow.dataset_id == dataset_id)
            .order_by(SpecRow.version.desc())
        )
        return list(self.s.scalars(stmt).all())

    def by_version(self, dataset_id: str, version: int) -> SpecRow | None:
        stmt = select(SpecRow).where(
            SpecRow.dataset_id == dataset_id, SpecRow.version == version
        )
        return self.s.scalars(stmt).first()


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def create(
        self, dataset_id: str, spec_id: str, seed: int, name: str | None = None
    ) -> GenerationRunRow:
        row = GenerationRunRow(
            run_id=_uid(),
            dataset_id=dataset_id,
            spec_id=spec_id,
            name=name,
            seed=seed,
            status="queued",
            progress_pct=0,
            created_at=utcnow_iso(),
        )
        self.s.add(row)
        self.s.flush()
        return row

    def get(self, run_id: str) -> GenerationRunRow | None:
        return self.s.get(GenerationRunRow, run_id)

    def set_name(self, row: GenerationRunRow, name: str) -> GenerationRunRow:
        row.name = name
        return row

    def delete(self, row: GenerationRunRow) -> None:
        # Clear the dataset's recorded latest-run pointer if it referenced this run
        # (it's a soft reference, so the cascade won't touch it).
        dataset = self.s.get(DatasetRow, row.dataset_id)
        if dataset is not None and dataset.latest_run_id == row.run_id:
            dataset.latest_run_id = None
        # ORM cascade removes artifact/report rows.
        self.s.delete(row)

    def list_for_dataset(self, dataset_id: str) -> list[GenerationRunRow]:
        stmt = (
            select(GenerationRunRow)
            .where(GenerationRunRow.dataset_id == dataset_id)
            .order_by(GenerationRunRow.created_at.desc())
        )
        return list(self.s.scalars(stmt).all())

    def find_repro(self, spec_id: str, seed: int) -> GenerationRunRow | None:
        stmt = (
            select(GenerationRunRow)
            .where(GenerationRunRow.spec_id == spec_id, GenerationRunRow.seed == seed)
            .order_by(GenerationRunRow.created_at.desc())
        )
        return self.s.scalars(stmt).first()


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(
        self,
        run_id: str,
        version: str,
        fmt: str,
        storage_uri: str,
        checksum_sha256: str,
        size_bytes: int,
        split: str | None = None,
    ) -> ArtifactRow:
        row = ArtifactRow(
            artifact_id=_uid(),
            run_id=run_id,
            version=version,
            split=split,
            format=fmt,
            storage_uri=storage_uri,
            checksum_sha256=checksum_sha256,
            size_bytes=size_bytes,
            created_at=utcnow_iso(),
        )
        self.s.add(row)
        self.s.flush()
        return row

    def get(self, artifact_id: str) -> ArtifactRow | None:
        return self.s.get(ArtifactRow, artifact_id)

    def list_for_run(self, run_id: str) -> list[ArtifactRow]:
        stmt = select(ArtifactRow).where(ArtifactRow.run_id == run_id)
        return list(self.s.scalars(stmt).all())


class ReportRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def upsert(self, run_id: str, sections: dict[str, Any]) -> ReportRow:
        existing = self.get_for_run(run_id)
        if existing is None:
            existing = ReportRow(report_id=_uid(), run_id=run_id, created_at=utcnow_iso())
            self.s.add(existing)
        existing.compliance_score = sections.get("compliance_score")
        existing.distribution = sections.get("distribution")
        existing.correlation = sections.get("correlation")
        existing.mutual_information = sections.get("mutual_information")
        existing.causal_truth = sections.get("causal_truth")
        existing.difficulty = sections.get("difficulty")
        existing.failures = sections.get("failures")
        existing.determinism = sections.get("determinism")
        self.s.flush()
        return existing

    def get_for_run(self, run_id: str) -> ReportRow | None:
        stmt = select(ReportRow).where(ReportRow.run_id == run_id)
        return self.s.scalars(stmt).first()
