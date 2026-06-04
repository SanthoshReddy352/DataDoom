"""Per-column data profile — exploratory analysis the engine can do for you.

A synthetic dataset is special: the engine knows the ground truth of every column
— its declared type, how a derived column was generated, and exactly which
failure modes corrupted it and by how much. This module turns that into a
**per-column report card** so an engineer or student opening the Results screen
gets, at a glance, what each column is, its summary statistics, and — crucially —
*what's wrong with it and how to handle that when building an ML model*.

Pure engine code: deterministic pandas aggregation on the realized frame plus a
static advice lookup (:mod:`datadoom.engine.advice`). No randomness, no model
fitting — same ``(spec_hash, seed)`` → identical profile (invariant #6).

The profile is computed from the **clean** shipped frame (the canonical
artifact); when an **injected** variant exists, each column also carries its
post-corruption missing rate / moments so the realized impact of the failures is
visible next to the pristine baseline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from .advice import build_issue, severity_rank

if TYPE_CHECKING:
    from .spec.models import Spec

# Categorical columns with more distinct values than this are summarised by their
# top categories only (a full breakdown would be noise for the reader).
_TOP_CATEGORIES = 12
# A target whose minority class is below this share is flagged as imbalanced.
_IMBALANCE_MINORITY = 0.35


def _num(x: Any) -> float | None:
    """Coerce to a JSON-safe float, mapping NaN/inf to ``None``."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def _parents_of(spec: Spec, col: str) -> list[str]:
    """Causal parents (edge sources) feeding a derived column, in spec order."""
    if spec.causal is None:
        return []
    return [e.src for e in spec.causal.edges if e.dst == col]


def _derived_names(spec: Spec) -> set[str]:
    return set() if spec.causal is None else {e.dst for e in spec.causal.edges}


def _label_column(spec: Spec) -> str | None:
    """Best guess at the target column.

    Authoritative when a difficulty block names a ``label``; otherwise a
    best-effort heuristic: a boolean/categorical causal *sink* (a derived column
    that no other edge consumes) is almost always the prediction target. Returns
    ``None`` when the guess is ambiguous (zero or several candidates).
    """
    if spec.difficulty is not None and getattr(spec.difficulty, "label", None):
        return spec.difficulty.label
    if spec.causal is None:
        return None
    sources = {e.src for e in spec.causal.edges}
    candidates = [
        e.dst
        for e in spec.causal.edges
        if e.dst not in sources
        and (feat := spec.features.get(e.dst)) is not None
        and feat.type in ("boolean", "categorical")
    ]
    unique = list(dict.fromkeys(candidates))
    return unique[0] if len(unique) == 1 else None


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    """Summary statistics for a numeric column (NaN-aware, JSON-safe)."""
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    clean = values[np.isfinite(values)]
    if clean.size == 0:
        return {}
    q = np.quantile(clean, [0.25, 0.5, 0.75])
    return {
        "mean": _num(clean.mean()),
        "std": _num(clean.std()),
        "min": _num(clean.min()),
        "p25": _num(q[0]),
        "median": _num(q[1]),
        "p75": _num(q[2]),
        "max": _num(clean.max()),
        "skew": _num(pd.Series(clean).skew()) if clean.size > 2 else None,
    }


def _category_breakdown(series: pd.Series) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Top categories (value/count/pct) and an imbalance summary for a discrete column."""
    counts = series.dropna().value_counts()
    n = int(counts.sum())
    if n == 0:
        return [], None
    top = [
        {"value": _stringify(val), "count": int(c), "pct": c / n}
        for val, c in counts.head(_TOP_CATEGORIES).items()
    ]
    majority = int(counts.iloc[0])
    minority = int(counts.iloc[-1])
    imbalance = {
        "classes": int(counts.size),
        "majority_pct": majority / n,
        "minority_pct": minority / n,
        "ratio": majority / minority if minority else None,
    }
    return top, imbalance


def _stringify(val: Any) -> str:
    if isinstance(val, (bool, np.bool_)):
        return "true" if val else "false"
    return str(val)


def _failures_by_column(diffs: list[dict[str, Any]] | None) -> dict[str, list[dict[str, Any]]]:
    """Invert the per-mode failure diffs into a per-column list of (mode, magnitude).

    Each entry carries the realized magnitude (authoritative — the engine measured
    it) so :func:`datadoom.engine.advice.build_issue` can size severity and the UI
    can show the concrete effect.
    """
    out: dict[str, list[dict[str, Any]]] = {}

    def add(col: str, mode: str, magnitude: str, fraction: float | None, detail: dict[str, Any]) -> None:
        out.setdefault(col, []).append(
            {"mode": mode, "magnitude": magnitude, "fraction": fraction, "detail": detail}
        )

    for d in diffs or []:
        mode = str(d.get("type") or d.get("mechanism") or "")
        if mode == "mcar":
            for col, frac in (d.get("nullified_fraction") or {}).items():
                f = _num(frac) or 0.0
                add(col, "mcar", f"{f * 100:.1f}% of values missing", f, {"rate": f})
        elif mode in ("mar", "mnar"):
            col = str(d.get("column"))
            f = _num(d.get("realized_rate")) or 0.0
            detail = {"rate": f, "driver": d.get("driver"), "self_dependent": d.get("self_dependent")}
            add(col, mode, f"{f * 100:.1f}% of values missing", f, detail)
        elif mode == "label_noise":
            col = str(d.get("column"))
            f = _num(d.get("flipped_fraction")) or 0.0
            add(col, "label_noise", f"{f * 100:.1f}% of labels flipped", f, {"rate": f})
        elif mode == "feature_noise":
            col = str(d.get("column"))
            sd = _num(d.get("realized_noise_std"))
            add(
                col,
                "feature_noise",
                f"σ≈{sd:.3g} noise added" if sd is not None else "noise added",
                None,
                {"noise_std": sd, "mean_shift": _num(d.get("realized_mean_shift"))},
            )
        elif mode == "drift":
            col = str(d.get("column"))
            shift = _num(d.get("total_shift"))
            kind = d.get("kind", "linear")
            add(
                col,
                "drift",
                f"{shift:.3g} total {kind} shift" if shift is not None else f"{kind} drift",
                None,
                {"total_shift": shift, "kind": kind},
            )
        elif mode == "covariate_shift":
            col = str(d.get("column"))
            before, after = d.get("before") or {}, d.get("after") or {}
            bm, am = _num(before.get("mean")), _num(after.get("mean"))
            mag = f"mean {bm:.3g}→{am:.3g}" if bm is not None and am is not None else "distribution shifted"
            add(col, "covariate_shift", mag, None, {"before": before, "after": after})
        elif mode == "leakage":
            col = str(d.get("into"))
            corr = _num(d.get("realized_correlation"))
            mag = f"corr={corr:.3f} with {d.get('target')}" if corr is not None else "high-MI proxy"
            add(col, "leakage", mag, None, {"target": d.get("target"), "correlation": corr})
    return out


def _role(name: str, derived: set[str], label: str | None, planted: bool) -> str:
    """How the column functions for modelling: label / leakage proxy / derived / feature."""
    if planted:
        return "leakage_proxy"
    if name == label:
        return "label"
    if name in derived:
        return "derived"
    return "feature"


def _column_profile(
    name: str,
    *,
    spec: Spec,
    clean: pd.DataFrame,
    injected: pd.DataFrame | None,
    derived: set[str],
    label: str | None,
    col_failures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble the report card for a single column."""
    planted = name not in clean.columns  # e.g. a leakage proxy lives only in injected
    base = injected if planted and injected is not None else clean
    series = base[name]
    feat = spec.features.get(name)
    feature_type = feat.type if feat is not None else "synthetic"

    n = int(len(series))
    missing = int(series.isna().sum())
    profile: dict[str, Any] = {
        "name": name,
        "role": _role(name, derived, label, planted),
        "feature_type": feature_type,
        "dtype": str(series.dtype),
        "count": n,
        "missing": missing,
        "missing_pct": missing / n if n else 0.0,
        "unique": int(series.nunique(dropna=True)),
        "derived": name in derived,
        "parents": _parents_of(spec, name),
        "description": getattr(feat, "description", None),
    }

    if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
        profile["stats"] = _numeric_stats(series)
        profile["categories"] = None
        profile["imbalance"] = None
    else:
        top, imbalance = _category_breakdown(series)
        profile["stats"] = None
        profile["categories"] = top
        profile["imbalance"] = imbalance

    # Post-corruption snapshot: how the column actually looks in the injected variant.
    if injected is not None and name in injected.columns and not planted:
        inj = injected[name]
        inj_missing = int(inj.isna().sum())
        post: dict[str, Any] = {"missing_pct": inj_missing / n if n else 0.0}
        if pd.api.types.is_numeric_dtype(inj) and not pd.api.types.is_bool_dtype(inj):
            vals = pd.to_numeric(inj, errors="coerce").to_numpy(dtype=float)
            vals = vals[np.isfinite(vals)]
            if vals.size:
                post["mean"] = _num(vals.mean())
                post["std"] = _num(vals.std())
        profile["injected"] = post
    else:
        profile["injected"] = None

    # Issues: failure-mode corruptions + (for the label) class imbalance.
    issues = [
        build_issue(f["mode"], magnitude=f["magnitude"], fraction=f["fraction"], detail=f["detail"]).to_dict()
        for f in col_failures
    ]
    imbalance = profile.get("imbalance")
    if name == label and imbalance and imbalance["minority_pct"] < _IMBALANCE_MINORITY:
        ratio = imbalance.get("ratio")
        mag = (
            f"{imbalance['majority_pct'] * 100:.1f}% / {imbalance['minority_pct'] * 100:.1f}%"
            + (f" ({ratio:.1f}:1)" if ratio else "")
        )
        issues.append(
            build_issue("class_imbalance", magnitude=mag, fraction=None, detail=imbalance).to_dict()
        )
    issues.sort(key=lambda i: severity_rank(i["severity"]), reverse=True)
    profile["issues"] = issues
    return profile


def build_profile(
    spec: Spec,
    clean: pd.DataFrame,
    *,
    injected: pd.DataFrame | None = None,
    failure_diffs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the full per-column data profile for the Results screen.

    Returns a JSON-serialisable dict with a top-level ``summary`` and a
    ``columns`` list (one report card each). Columns appear in shipped order,
    with any injected-only columns (e.g. leakage proxies) appended.
    """
    derived = _derived_names(spec)
    label = _label_column(spec)
    by_col = _failures_by_column(failure_diffs)

    names: list[str] = list(clean.columns)
    if injected is not None:
        names += [c for c in injected.columns if c not in clean.columns]

    columns = [
        _column_profile(
            name,
            spec=spec,
            clean=clean,
            injected=injected,
            derived=derived,
            label=label,
            col_failures=by_col.get(name, []),
        )
        for name in names
    ]

    n_issue_cols = sum(1 for c in columns if c["issues"])
    severities = [i["severity"] for c in columns for i in c["issues"]]
    summary = {
        "n_rows": int(len(clean)),
        "n_columns": len(columns),
        "label": label,
        "columns_with_issues": n_issue_cols,
        "total_issues": len(severities),
        "critical_issues": sum(1 for s in severities if s == "critical"),
        "high_issues": sum(1 for s in severities if s == "high"),
    }
    return {"summary": summary, "columns": columns}
