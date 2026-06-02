"""Artifact storage adapters (03 §3.6, 06 §3.4).

Local filesystem by default: ``<artifacts_dir>/<dataset_id>/<run_id>/...``.
The interface keeps the rest of the app storage-agnostic so an S3 adapter can
drop in for team mode without touching callers.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class ArtifactStore(ABC):
    """Where a run's output files live. URIs are opaque to the caller."""

    @abstractmethod
    def run_dir(self, dataset_id: str, run_id: str) -> Path:
        """Return (creating if needed) the directory for a run's artifacts."""

    @abstractmethod
    def to_uri(self, path: Path) -> str:
        """Stable storage URI recorded in the Artifact row."""

    @abstractmethod
    def open_uri(self, uri: str) -> Path:
        """Resolve a stored URI back to a readable local path (for downloads)."""

    @abstractmethod
    def remove_dataset(self, dataset_id: str) -> None:
        """Delete all artifacts for a dataset (cascade delete)."""

    @abstractmethod
    def remove_run(self, dataset_id: str, run_id: str) -> None:
        """Delete all artifacts for a single run."""


class LocalArtifactStore(ArtifactStore):
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def run_dir(self, dataset_id: str, run_id: str) -> Path:
        d = self.root / dataset_id / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def to_uri(self, path: Path) -> str:
        # Record paths relative to the artifact root so the DB stays portable if
        # the root moves; downloads resolve back through `open_uri`.
        rel = Path(path).resolve().relative_to(self.root.resolve())
        return f"file:{rel.as_posix()}"

    def open_uri(self, uri: str) -> Path:
        if uri.startswith("file:"):
            return (self.root / uri[len("file:") :]).resolve()
        return Path(uri)

    def remove_dataset(self, dataset_id: str) -> None:
        d = self.root / dataset_id
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    def remove_run(self, dataset_id: str, run_id: str) -> None:
        d = self.root / dataset_id / run_id
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
