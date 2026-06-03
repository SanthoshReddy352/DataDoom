"""Report assembly (03 §4 stage 8, 06 §3.5, 05 §7).

Builds the sectioned ``Report`` payload the Results screen and the ``reports``
table bind to. Pure engine code — no DB/web imports. The sections the engine can
honestly produce are populated:

* ``compliance_score`` / ``distribution`` — from the KS compliance pass.
* ``correlation`` — Pearson matrix over numeric columns (cheap, honest).
* ``mutual_information`` — pairwise MI (nats) over discretized columns (05 §7).
* ``causal_truth`` — the true generating DAG + interventions (P2).
* ``determinism`` — spec_hash, seed, per-namespace key digests, checksums.

``difficulty`` (P4) and ``failures`` (P3) stay ``None`` until those engines land;
the schema is stable so the UI is coherent from day one.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from .causal.execute import resolve_interventions
from .dist import ComplianceReport

if TYPE_CHECKING:
    from .causal.graph import CausalDag
    from .spec.models import CausalGraph

# Columns with more distinct values than this are treated as free-text / id-like
# and excluded from the mutual-information matrix (binning would be meaningless).
_MI_MAX_CARDINALITY = 50
_MI_NUMERIC_BINS = 10


@dataclass
class ReportBundle:
    compliance_score: float
    distribution: dict[str, Any]
    correlation: dict[str, Any] | None = None
    mutual_information: dict[str, Any] | None = None
    causal_truth: dict[str, Any] | None = None
    difficulty: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None
    determinism: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def correlation_pearson(frame: pd.DataFrame) -> dict[str, Any] | None:
    """Pearson correlation over numeric columns, JSON-serializable.

    Returns ``None`` when fewer than two numeric columns exist (a matrix would
    be degenerate). NaNs (e.g. a constant column) are rendered as ``None``.
    """
    numeric = frame.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return None
    corr = numeric.corr(method="pearson")
    matrix = [[None if pd.isna(v) else float(v) for v in row] for row in corr.to_numpy()]
    return {"method": "pearson", "columns": list(corr.columns), "matrix": matrix}


def _discretize(series: pd.Series) -> np.ndarray | None:
    """Map a column to integer codes for MI; ``None`` if it isn't usable.

    Numeric/datetime columns are quantile-binned; low-cardinality
    categorical/boolean columns are factorized; free-text/id-like columns
    (cardinality above the cap) are skipped.
    """
    nunique = series.nunique(dropna=True)
    if nunique < 2:
        return None
    if pd.api.types.is_bool_dtype(series) or pd.api.types.is_object_dtype(series) or isinstance(
        series.dtype, pd.CategoricalDtype
    ):
        if nunique > _MI_MAX_CARDINALITY:
            return None
        return pd.factorize(series, sort=True)[0]
    values = series
    if pd.api.types.is_datetime64_any_dtype(series):
        values = series.astype("int64")
    if pd.api.types.is_numeric_dtype(values):
        bins = min(_MI_NUMERIC_BINS, int(nunique))
        codes = pd.qcut(values, q=bins, duplicates="drop").cat.codes
        return codes.to_numpy() if codes.nunique() >= 2 else None
    return None


def _mutual_information(a: np.ndarray, b: np.ndarray) -> float:
    """MI in nats between two integer-code arrays via the joint histogram."""
    contingency = pd.crosstab(a, b).to_numpy(dtype=float)
    n = contingency.sum()
    if n == 0:
        return 0.0
    pxy = contingency / n
    px = pxy.sum(axis=1, keepdims=True)
    py = pxy.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = pxy * (np.log(pxy) - np.log(px) - np.log(py))
    return float(np.nansum(np.where(pxy > 0, terms, 0.0)))


def mutual_information_matrix(frame: pd.DataFrame) -> dict[str, Any] | None:
    """Pairwise mutual information (nats) over discretizable columns (05 §7).

    Returns ``None`` when fewer than two columns are usable. The diagonal is the
    column's entropy ``H(X) = I(X;X)``. Symmetric by construction.
    """
    codes: dict[str, np.ndarray] = {}
    for col in frame.columns:
        disc = _discretize(frame[col])
        if disc is not None:
            codes[col] = disc
    cols = list(codes)
    if len(cols) < 2:
        return None
    size = len(cols)
    matrix = [[0.0] * size for _ in range(size)]
    for i in range(size):
        for j in range(i, size):
            mi = _mutual_information(codes[cols[i]], codes[cols[j]])
            matrix[i][j] = mi
            matrix[j][i] = mi
    return {"method": "histogram", "units": "nats", "columns": cols, "matrix": matrix}


def causal_truth(
    causal: CausalGraph | None, dag: CausalDag | None
) -> dict[str, Any] | None:
    """The true generating graph: edges (with params), interventions, topo order.

    Edges whose destination is intervened are reported ``active: false`` — an
    intervention ``do(X)`` detaches X's incoming edges (05 §3.1).
    """
    if causal is None:
        return None
    interventions = resolve_interventions(causal.interventions)
    edges: list[dict[str, Any]] = []
    for e in causal.edges:
        edge: dict[str, Any] = {"from": e.src, "to": e.dst, "fn": e.fn}
        for key, val in (
            ("weight", e.weight),
            ("bias", e.bias),
            ("coeffs", e.coeffs),
            ("mapping", e.mapping),
        ):
            if val is not None:
                edge[key] = val
        edge["active"] = e.dst not in interventions
        edges.append(edge)
    return {
        "nodes": dag.topological_order() if dag is not None else None,
        "edges": edges,
        "interventions": interventions,
        "topological_order": dag.topological_order() if dag is not None else None,
    }


def failures_section(diffs: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Wrap the per-mode failure diffs into the report's ``failures`` section.

    ``None`` when no failures were injected, so the UI can tell "no corruption"
    apart from "corruption with empty effect".
    """
    if not diffs:
        return None
    return {"count": len(diffs), "modes": diffs}


def build_report(
    *,
    compliance: ComplianceReport,
    frame: pd.DataFrame,
    determinism: dict[str, Any],
    causal: CausalGraph | None = None,
    causal_dag: CausalDag | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> ReportBundle:
    """Assemble the report bundle from the realized frame and compliance pass."""
    return ReportBundle(
        compliance_score=compliance.score,
        distribution=compliance.to_dict(),
        correlation=correlation_pearson(frame),
        mutual_information=mutual_information_matrix(frame),
        causal_truth=causal_truth(causal, causal_dag),
        failures=failures_section(failures),
        determinism=determinism,
    )
