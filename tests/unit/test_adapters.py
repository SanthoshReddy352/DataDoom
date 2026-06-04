"""Framework adapters: pandas loader (core) + torch/tf/hf converters (optional)."""

from __future__ import annotations

import pandas as pd
import pytest

from datadoom.adapters import (
    load_dataframe,
    numeric_feature_columns,
    to_hf_dataset,
    to_torch_dataset,
)
from datadoom.engine import generate, parse_spec


def _spec_with_injected():
    return parse_spec(
        {
            "datadoom_version": "1",
            "name": "adapt",
            "rows": 200,
            "seed": 1,
            "features": {
                "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
                "flag": {"type": "boolean", "rate": 0.4},
                "label": {"type": "categorical", "categories": ["a", "b"]},
                "note": {"type": "text", "generator": "lorem"},
            },
            "failures": [{"type": "mcar", "columns": ["x"], "rate": 0.1}],
            "export": {"formats": ["csv"], "versions": ["clean", "injected"]},
        }
    )


def test_load_dataframe_clean_and_injected(tmp_path) -> None:
    generate(_spec_with_injected(), seed=1, out_dir=tmp_path)
    clean = load_dataframe(tmp_path)
    injected = load_dataframe(tmp_path, version="injected")
    assert list(clean.columns) == ["x", "flag", "label", "note"]
    assert len(clean) == 200 and len(injected) == 200
    # The injected variant has missing values in x (MCAR), the clean one does not.
    assert clean["x"].isna().sum() == 0
    assert injected["x"].isna().sum() > 0


def test_load_dataframe_missing_artifact_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_dataframe(tmp_path)  # nothing generated here


def test_numeric_feature_columns_selects_model_ready() -> None:
    df = pd.DataFrame(
        {"a": [1.0, 2.0], "b": [True, False], "c": ["x", "y"], "t": pd.to_datetime(["2020", "2021"])}
    )
    cols = numeric_feature_columns(df, exclude=["a"])
    assert cols == ["b"]  # numeric 'a' excluded; categorical 'c' + datetime 't' skipped


def test_to_torch_dataset(tmp_path) -> None:
    torch = pytest.importorskip("torch")
    generate(_spec_with_injected(), seed=1, out_dir=tmp_path)
    df = load_dataframe(tmp_path)
    ds = to_torch_dataset(df, target="flag")
    assert len(ds) == 200
    x0, y0 = ds[0]
    # features are the numeric/bool columns minus the target → just 'x'.
    assert x0.shape[-1] == 1
    assert isinstance(y0.item(), (int, float)) or y0.dtype == torch.float32


def test_to_hf_dataset(tmp_path) -> None:
    pytest.importorskip("datasets")
    generate(_spec_with_injected(), seed=1, out_dir=tmp_path)
    df = load_dataframe(tmp_path)
    ds = to_hf_dataset(df)
    assert ds.num_rows == 200
    assert set(["x", "flag", "label", "note"]).issubset(set(ds.column_names))


def test_framework_loader_without_backend_hints_extra(monkeypatch) -> None:
    # If a backend is missing, the converter raises an ImportError naming the extra.
    import builtins

    real_import = builtins.__import__

    def _blocked(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("no torch")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked)
    # importlib.import_module ultimately uses __import__; ensure the hint surfaces.
    df = pd.DataFrame({"x": [1.0, 2.0], "y": [0, 1]})
    with pytest.raises(ImportError) as e:
        to_torch_dataset(df, target="y")
    assert "datadoom[torch]" in str(e.value)
