"""Byte-stable CSV writer (17 step 4).

We render to a string with an explicit ``\\n`` line terminator and write raw
UTF-8 bytes ourselves, bypassing OS-specific newline translation so the output
is identical on Windows, macOS and Linux. Column order is fixed by the caller.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import ArtifactInfo, Exporter
from .checksums import sha256_bytes


class CsvExporter(Exporter):
    format = "csv"

    def write(self, df: pd.DataFrame, path: str | Path) -> ArtifactInfo:
        text = df.to_csv(index=False, lineterminator="\n")
        data = text.encode("utf-8")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Binary write => no newline translation; bytes are exactly `data`.
        with open(path, "wb") as fh:
            fh.write(data)
        return ArtifactInfo(
            path=str(path),
            format=self.format,
            checksum_sha256=sha256_bytes(data),
            size_bytes=len(data),
        )
