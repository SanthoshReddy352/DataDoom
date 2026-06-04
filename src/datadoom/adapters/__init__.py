"""Framework adapters — load a generated DataDoom run into ML frameworks (18.4).

A run directory (the ``--out`` of ``datadoom run``) holds ``data.csv`` (and any
``data.injected.*`` / other formats). These helpers turn it into the in-memory
object each framework expects:

* :func:`load_dataframe` — a **pandas** ``DataFrame`` (no extra needed; pandas is
  a core dep). Auto-detects csv / parquet / json and the clean/injected variant.
* :func:`to_torch_dataset` — a ``torch.utils.data.TensorDataset`` (extra: ``torch``).
* :func:`to_tf_dataset` — a ``tf.data.Dataset`` (extra: ``tf``).
* :func:`to_hf_dataset` — a HuggingFace ``datasets.Dataset`` (extra: ``hf``).

The framework loaders **lazy-import** their backend and raise a clear install
hint if it is missing, so the core install stays light. This package depends only
on the engine (for nothing heavyweight) + pandas; the engine never imports it.
"""

from __future__ import annotations

from .frameworks import to_hf_dataset, to_tf_dataset, to_torch_dataset
from .loaders import load_dataframe, numeric_feature_columns

__all__ = [
    "load_dataframe",
    "numeric_feature_columns",
    "to_torch_dataset",
    "to_tf_dataset",
    "to_hf_dataset",
]
