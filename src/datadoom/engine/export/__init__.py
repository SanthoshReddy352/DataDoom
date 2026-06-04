"""Export adapters + metadata + checksums."""

from __future__ import annotations

from .base import ArtifactInfo, Exporter
from .checksums import sha256_bytes, sha256_file
from .csv_exporter import CsvExporter
from .json_exporter import JsonExporter
from .metadata import build_metadata, write_metadata
from .parquet_exporter import ParquetExporter

EXPORTERS: dict[str, Exporter] = {
    e.format: e for e in (CsvExporter(), JsonExporter(), ParquetExporter())
}

__all__ = [
    "ArtifactInfo",
    "Exporter",
    "CsvExporter",
    "JsonExporter",
    "ParquetExporter",
    "EXPORTERS",
    "sha256_bytes",
    "sha256_file",
    "build_metadata",
    "write_metadata",
]
