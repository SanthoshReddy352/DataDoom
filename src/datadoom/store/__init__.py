"""Persistence layer — metadata DB (SQLAlchemy/SQLite) + artifact storage.

`store/` sits beside the engine: it persists engine outputs but imports nothing
from `jobs`, `api`, or `cli` (enforced by import-linter). The rest of the app
talks to it only through the repositories and the :class:`ArtifactStore`.
"""

from __future__ import annotations

from .artifacts import ArtifactStore, LocalArtifactStore
from .db import Database, init_database, utcnow_iso
from .models import (
    ArtifactRow,
    Base,
    DatasetRow,
    GenerationRunRow,
    PluginRow,
    ReportRow,
    SpecRow,
)
from .repositories import (
    ArtifactRepository,
    DatasetRepository,
    ReportRepository,
    RunRepository,
    SpecRepository,
)

__all__ = [
    "Database",
    "init_database",
    "utcnow_iso",
    "Base",
    "DatasetRow",
    "SpecRow",
    "GenerationRunRow",
    "ArtifactRow",
    "ReportRow",
    "PluginRow",
    "DatasetRepository",
    "SpecRepository",
    "RunRepository",
    "ArtifactRepository",
    "ReportRepository",
    "ArtifactStore",
    "LocalArtifactStore",
]
