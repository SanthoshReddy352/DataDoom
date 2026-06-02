"""Export adapters + metadata + checksums."""

from __future__ import annotations

from .base import ArtifactInfo, Exporter
from .checksums import sha256_bytes, sha256_file
from .csv_exporter import CsvExporter
from .metadata import build_metadata, write_metadata

EXPORTERS = {e.format: e for e in (CsvExporter(),)}

__all__ = [
    "ArtifactInfo",
    "Exporter",
    "CsvExporter",
    "EXPORTERS",
    "sha256_bytes",
    "sha256_file",
    "build_metadata",
    "write_metadata",
]
