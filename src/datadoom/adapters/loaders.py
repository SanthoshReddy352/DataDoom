"""Read generated run artifacts into a pandas DataFrame."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Preferred read order: CSV is the canonical artifact, then parquet, then json.
_READERS: list[tuple[str, str]] = [("csv", "csv"), ("parquet", "parquet"), ("json", "json")]


def _read(path: Path, kind: str) -> pd.DataFrame:
    if kind == "csv":
        return pd.read_csv(path)
    if kind == "parquet":
        return pd.read_parquet(path)
    return pd.read_json(path, orient="records")


def load_dataframe(
    run_dir: str | Path,
    *,
    version: str = "clean",
    split: str | None = None,
) -> pd.DataFrame:
    """Load a generated dataset variant into a pandas ``DataFrame``.

    Args:
        run_dir: the run output directory (``datadoom run --out <dir>``).
        version: ``"clean"`` (default) or ``"injected"`` (the corrupted variant).
        split: optional split name (e.g. ``"train"``) if split files were written.

    Returns:
        The dataset as a ``DataFrame``, columns in spec order.

    Raises:
        FileNotFoundError: if no matching data artifact exists in ``run_dir``.
    """
    base = Path(run_dir)
    stem = "data" if version == "clean" else "data.injected"
    if split:
        stem = f"{stem}.{split}"

    for ext, kind in _READERS:
        candidate = base / f"{stem}.{ext}"
        if candidate.exists():
            return _read(candidate, kind)

    tried = ", ".join(f"{stem}.{ext}" for ext, _ in _READERS)
    raise FileNotFoundError(
        f"no data artifact for version={version!r}"
        + (f", split={split!r}" if split else "")
        + f" in {base} (looked for: {tried})"
    )


def numeric_feature_columns(df: pd.DataFrame, *, exclude: list[str] | None = None) -> list[str]:
    """Return the numeric/boolean columns of ``df`` (model-ready features).

    Categorical/text/datetime columns are skipped — encode them yourself if you
    need them. Pass ``exclude`` to drop e.g. the target column.
    """
    drop = set(exclude or [])
    cols: list[str] = []
    for name in df.columns:
        if name in drop:
            continue
        s = df[name]
        if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
            cols.append(name)
    return cols
