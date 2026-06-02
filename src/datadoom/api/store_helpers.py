"""Thin helpers shared by routes: dataset loading + latest-run lookup.

Re-exports the store repositories so route modules import them from one place,
and centralizes the "404 if missing" and "latest run" patterns.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from datadoom.store import (
    ArtifactRepository,
    DatasetRepository,
    DatasetRow,
    GenerationRunRow,
    ReportRepository,
    RunRepository,
    SpecRepository,
)

from .errors import http_error

__all__ = [
    "DatasetRepository",
    "SpecRepository",
    "RunRepository",
    "ArtifactRepository",
    "ReportRepository",
    "load_dataset",
    "load_run",
    "latest_run_row",
]


def load_dataset(session: Session, dataset_id: str) -> DatasetRow:
    row = DatasetRepository(session).get(dataset_id)
    if row is None:
        raise http_error(404, "not_found", f"dataset {dataset_id} not found")
    return row


def load_run(session: Session, run_id: str) -> GenerationRunRow:
    row = RunRepository(session).get(run_id)
    if row is None:
        raise http_error(404, "not_found", f"run {run_id} not found")
    return row


def latest_run_row(runs: RunRepository, dataset: DatasetRow) -> GenerationRunRow | None:
    """Prefer the dataset's recorded latest run, else the most recent by time."""
    if dataset.latest_run_id:
        found = runs.get(dataset.latest_run_id)
        if found is not None:
            return found
    rows = runs.list_for_dataset(dataset.dataset_id)
    return rows[0] if rows else None
