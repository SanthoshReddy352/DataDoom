"""Export is byte-stable and checksums are reproducible."""

from __future__ import annotations

import pandas as pd

from datadoom.engine.export import CsvExporter, sha256_file


def test_csv_is_byte_stable_across_writes(tmp_path) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    p1 = tmp_path / "one.csv"
    p2 = tmp_path / "two.csv"
    i1 = CsvExporter().write(df, p1)
    i2 = CsvExporter().write(df, p2)
    assert i1.checksum_sha256 == i2.checksum_sha256
    assert sha256_file(p1) == i1.checksum_sha256


def test_csv_uses_lf_newlines(tmp_path) -> None:
    df = pd.DataFrame({"a": [1, 2]})
    p = tmp_path / "x.csv"
    CsvExporter().write(df, p)
    raw = p.read_bytes()
    assert b"\r\n" not in raw
    assert raw == b"a\n1\n2\n"


def test_column_order_preserved(tmp_path) -> None:
    df = pd.DataFrame({"z": [1], "a": [2], "m": [3]})
    p = tmp_path / "x.csv"
    CsvExporter().write(df, p)
    header = p.read_bytes().split(b"\n")[0]
    assert header == b"z,a,m"
