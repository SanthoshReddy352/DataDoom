"""Parquet writer (17 step 18, 09 §8).

Parquet is a columnar format ML tooling consumes directly (pandas/Polars/Spark,
``datasets``). ``pyarrow`` is an **optional** dependency (``pip install
datadoom[parquet]``) — it's a large wheel and the core stays light — so the import
is deferred to ``write`` with an actionable error if it is missing. Within a
pinned environment the same ``(spec_hash, seed)`` yields identical bytes; the only
embedded ambient value is pyarrow's constant ``created_by`` build string.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..errors import DataDoomError
from .base import ArtifactInfo, Exporter
from .checksums import sha256_file


class ParquetExporter(Exporter):
    format = "parquet"

    def write(self, df: pd.DataFrame, path: str | Path) -> ArtifactInfo:
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise DataDoomError(  # noqa: TRY003
                "the 'parquet' export format needs pyarrow; install it with "
                "`pip install datadoom[parquet]`"
            ) from exc

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pandas(df, preserve_index=False)
        # Fixed options so the bytes are reproducible on the pinned path.
        pq.write_table(table, path, compression="snappy", version="2.6")
        return ArtifactInfo(
            path=str(path),
            format=self.format,
            checksum_sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
        )
