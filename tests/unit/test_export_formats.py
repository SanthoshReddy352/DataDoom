"""JSON + Parquet exporters and multi-format packaging (task 18.1).

CSV byte-stability is covered by ``test_export.py``; here we assert the new
formats are byte-stable + round-trip, the pipeline writes every requested format
per version, and validation rejects an unknown format.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.errors import SpecValidationError
from datadoom.engine.export import EXPORTERS, JsonExporter


@pytest.fixture
def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "i": np.array([1, 2, 3], dtype="int64"),
            "f": np.array([1.5, np.nan, 3.25], dtype="float64"),
            "b": np.array([True, False, True]),
            "s": ["x", "y", "z"],
            "t": pd.to_datetime(["2020-01-01", "2020-06-15", "2021-12-31"]),
        }
    )


def test_registry_has_new_formats() -> None:
    assert set(EXPORTERS) >= {"csv", "json", "parquet"}
    assert EXPORTERS["json"].ext == "json"
    assert EXPORTERS["parquet"].ext == "parquet"


def test_json_is_byte_stable_and_roundtrips(frame: pd.DataFrame, tmp_path: Path) -> None:
    exp = JsonExporter()
    a = exp.write(frame, tmp_path / "a.json")
    b = exp.write(frame, tmp_path / "b.json")
    assert a.checksum_sha256 == b.checksum_sha256  # byte-stable
    assert a.format == "json"

    back = pd.read_json(tmp_path / "a.json")
    assert list(back.columns) == list(frame.columns)
    assert len(back) == 3
    # NaN survives as null -> NaN; ints/bools/strings preserved.
    assert bool(pd.isna(back["f"].iloc[1]))
    assert back["i"].tolist() == [1, 2, 3]
    assert back["s"].tolist() == ["x", "y", "z"]


def test_parquet_is_byte_stable_and_roundtrips(frame: pd.DataFrame, tmp_path: Path) -> None:
    pytest.importorskip("pyarrow")
    exp = EXPORTERS["parquet"]
    a = exp.write(frame, tmp_path / "a.parquet")
    b = exp.write(frame, tmp_path / "b.parquet")
    assert a.checksum_sha256 == b.checksum_sha256
    back = pd.read_parquet(tmp_path / "a.parquet")
    assert list(back.columns) == list(frame.columns)
    assert back["i"].tolist() == [1, 2, 3]
    assert bool(pd.isna(back["f"].iloc[1]))


def test_pipeline_writes_all_formats() -> None:
    pytest.importorskip("pyarrow")
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "fmt",
            "rows": 200,
            "features": {"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}}},
            "export": {"formats": ["csv", "json", "parquet"]},
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = generate(spec, seed=3, out_dir=tmp)
        names = {a.path for a in result.artifacts}
        assert {"data.csv", "data.json", "data.parquet", "metadata.json"} <= names
        for n in ("data.csv", "data.json", "data.parquet"):
            assert (Path(tmp) / n).exists()
        # checksums recorded for every data file
        checks = result.metadata["determinism"]["artifact_checksums"]
        assert {"data.csv", "data.json", "data.parquet"} <= set(checks)


def test_injected_written_per_format() -> None:
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "fmtfail",
            "rows": 300,
            "features": {
                "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            },
            "failures": [{"type": "mcar", "column": "x", "rate": 0.2}],
            "export": {"formats": ["csv", "json"], "versions": ["clean", "injected"]},
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        result = generate(spec, seed=5, out_dir=tmp)
        names = {a.path for a in result.artifacts}
        assert {"data.csv", "data.json", "data.injected.csv", "data.injected.json"} <= names


def test_validation_rejects_unknown_format() -> None:
    with pytest.raises(SpecValidationError) as exc:
        parse_spec(
            {
                "datadoom_version": "1",
                "name": "bad",
                "rows": 10,
                "features": {"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}}},
                "export": {"formats": ["csv", "feather"]},
            }
        )
    assert exc.value.locator == "export.formats"
