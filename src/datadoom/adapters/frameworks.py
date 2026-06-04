"""Convert a pandas DataFrame into torch / tensorflow / HuggingFace datasets.

Each converter lazy-imports its backend so the core install stays light; a
missing backend raises an actionable install hint naming the right extra.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from .loaders import numeric_feature_columns

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


def _require(module: str, extra: str) -> Any:
    try:
        return import_module(module)
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(
            f"{module!r} is required for this adapter. Install it with: "
            f"pip install 'datadoom[{extra}]'"
        ) from exc


def _feature_matrix(
    df: pd.DataFrame, feature_columns: list[str] | None, target: str | None
) -> tuple[list[str], np.ndarray]:
    cols = feature_columns or numeric_feature_columns(df, exclude=[target] if target else None)
    if not cols:
        raise ValueError(
            "no numeric/boolean feature columns found; pass feature_columns explicitly "
            "or encode categorical/text columns first"
        )
    x = df[cols].to_numpy(dtype="float32")
    return cols, x


def to_torch_dataset(
    df: pd.DataFrame,
    *,
    target: str | None = None,
    feature_columns: list[str] | None = None,
) -> Any:
    """Build a ``torch.utils.data.TensorDataset`` from ``df`` (extra: ``torch``).

    Features are the numeric/boolean columns (or ``feature_columns``); if
    ``target`` is given it becomes the second tensor.
    """
    torch = _require("torch", "torch")
    _, x = _feature_matrix(df, feature_columns, target)
    x_t = torch.as_tensor(x)
    if target is None:
        return torch.utils.data.TensorDataset(x_t)
    y = df[target].to_numpy()
    y_t = torch.as_tensor(y.astype("float32") if y.dtype != object else y)
    return torch.utils.data.TensorDataset(x_t, y_t)


def to_tf_dataset(
    df: pd.DataFrame,
    *,
    target: str | None = None,
    feature_columns: list[str] | None = None,
    batch_size: int | None = None,
) -> Any:
    """Build a ``tf.data.Dataset`` from ``df`` (extra: ``tf``).

    Yields feature rows, or ``(features, label)`` pairs when ``target`` is set.
    Optionally batched.
    """
    tf = _require("tensorflow", "tf")
    _, x = _feature_matrix(df, feature_columns, target)
    if target is None:
        ds = tf.data.Dataset.from_tensor_slices(x)
    else:
        ds = tf.data.Dataset.from_tensor_slices((x, df[target].to_numpy()))
    if batch_size:
        ds = ds.batch(batch_size)
    return ds


def to_hf_dataset(df: pd.DataFrame) -> Any:
    """Build a HuggingFace ``datasets.Dataset`` from ``df`` (extra: ``hf``).

    Keeps every column (including categorical/text) — HF datasets are schema-rich.
    """
    datasets = _require("datasets", "hf")
    return datasets.Dataset.from_pandas(df, preserve_index=False)
