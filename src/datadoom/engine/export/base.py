"""Exporter ABC (04 §8).

An exporter serializes a frame to a byte-stable file and returns its checksum
metadata. Byte-stability is essential: the same ``(spec_hash, seed)`` must yield
identical file bytes on the pinned path.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class ArtifactInfo:
    path: str
    format: str
    checksum_sha256: str
    size_bytes: int
    version: str = "clean"

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "format": self.format,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "version": self.version,
        }


class Exporter(ABC):
    format: str
    # File extension for the artifact (defaults to ``format`` when unset).
    extension: str = ""
    # Optional JSON-schema fragment for exporter options (09 §6); ``None`` for built-ins.
    param_schema: Mapping[str, object] | None = None

    @property
    def ext(self) -> str:
        return self.extension or self.format

    @abstractmethod
    def write(self, df: pd.DataFrame, path: str | Path) -> ArtifactInfo:
        """Write ``df`` to ``path`` deterministically and return its info."""
