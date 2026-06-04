"""Byte-stable JSON writer (17 step 18, 09 §8).

Emits a records array (``[{col: value, …}, …]``) in stable column order, with no
timestamps/ambient state, so the same ``(spec_hash, seed)`` yields identical bytes
on the pinned path (invariant #6). Values are normalized so the output round-trips
through ``pandas.read_json(orient="records")``: numpy scalars become Python
scalars, ``NaN``/``NaT`` become ``null``, and datetimes become ISO-8601 strings.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .base import ArtifactInfo, Exporter
from .checksums import sha256_bytes


def _normalize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, np.floating):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return None if pd.isna(value) else value.isoformat()
    if value is pd.NaT:
        return None
    if isinstance(value, np.datetime64):
        ts = pd.Timestamp(value)
        return None if pd.isna(ts) else ts.isoformat()
    return value


class JsonExporter(Exporter):
    format = "json"

    def write(self, df: pd.DataFrame, path: str | Path) -> ArtifactInfo:
        columns = list(df.columns)
        records = [
            {col: _normalize(val) for col, val in zip(columns, row, strict=True)}
            for row in df.itertuples(index=False, name=None)
        ]
        # Compact + sorted-by-column-order; LF newlines only (json never emits CRLF).
        text = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
        data = text.encode("utf-8")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
        return ArtifactInfo(
            path=str(path),
            format=self.format,
            checksum_sha256=sha256_bytes(data),
            size_bytes=len(data),
        )
