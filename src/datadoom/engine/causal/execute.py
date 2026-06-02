"""SEM execution: topological walk applying structural equations (05 §3).

Runs after base (root) features are sampled. For each derived node in
topological order:

    v = Σ_e  fn_e(parent_e)  +  ε_v          (ε_v ~ noise[v] via RNG(noise:v))

Boolean children interpret the summed contribution as a probability and draw a
Bernoulli outcome from ``RNG(feature:v)`` (05 §3). Interventions ``do(X=x₀)``
fix a node to a constant and skip its equation; because the walk is topological,
descendants automatically see the intervened value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

from ..errors import SpecValidationError
from ..spec.models import BooleanFeature, NumericFeature
from .functions import STRUCTURAL_FNS
from .graph import CausalDag

if TYPE_CHECKING:  # avoid a runtime import cycle with pipeline
    from ..pipeline import RunContext


def resolve_interventions(interventions: list[dict[str, Any]]) -> dict[str, float]:
    """Flatten ``[{do: {X: x0}}, ...]`` into ``{X: x0}`` (last wins)."""
    fixed: dict[str, float] = {}
    for item in interventions:
        do = item.get("do", {})
        for node, value in do.items():
            fixed[node] = float(value)
    return fixed


def build_dag(ctx: RunContext) -> CausalDag:
    assert ctx.spec.causal is not None
    return CausalDag(ctx.spec.causal.edges, list(ctx.spec.features))


def execute_causal(ctx: RunContext, columns: dict[str, np.ndarray]) -> CausalDag:
    """Fill derived columns in-place; return the DAG (for the report's true graph)."""
    spec = ctx.spec
    assert spec.causal is not None
    n = spec.rows
    dag = build_dag(ctx)
    interventions = resolve_interventions(spec.causal.interventions)

    for node in dag.topological_order():
        if node in interventions:
            columns[node] = _materialize_constant(spec.features[node], interventions[node], n)
            continue
        in_edges = dag.in_edges(node)
        if not in_edges:
            continue  # root feature — already sampled in base_generation

        contrib = np.zeros(n, dtype=float)
        for edge in in_edges:
            fn = STRUCTURAL_FNS[edge.fn]
            contrib = contrib + fn.contribution(columns[edge.src], edge)

        eps = _draw_noise(ctx, node, n)
        if eps is not None:
            contrib = contrib + eps

        columns[node] = _finalize(ctx, node, spec.features[node], contrib)

    return dag


def _draw_noise(ctx: RunContext, node: str, n: int) -> np.ndarray | None:
    """Node noise ε_v from RNG(noise:v); ``None`` when noise is absent/``none``."""
    from ..dist.builtins import REGISTRY

    assert ctx.spec.causal is not None
    spec = ctx.spec.causal.noise.get(node)
    if spec is None:
        return None
    dist_name = spec.get("dist")
    if dist_name is None or dist_name == "none":
        return None
    dist = REGISTRY[dist_name]
    ctx.used_namespaces.append(f"noise:{node}")
    return dist.sample(ctx.rng.noise(node), n, spec.get("params", {}))


def _finalize(ctx: RunContext, node: str, feat: Any, contrib: np.ndarray) -> np.ndarray:
    if isinstance(feat, BooleanFeature):
        p = np.clip(contrib, 0.0, 1.0)
        ctx.used_namespaces.append(f"feature:{node}")
        return ctx.rng.feature(node).random(size=len(contrib)) < p
    if isinstance(feat, NumericFeature):
        values = contrib
        if feat.min is not None or feat.max is not None:
            lo = -np.inf if feat.min is None else feat.min
            hi = np.inf if feat.max is None else feat.max
            values = np.clip(values, lo, hi)
        if feat.dtype == "int":
            values = np.rint(values).astype("int64")
        return values
    raise SpecValidationError(
        f"feature {node!r} is a causal target but type {feat.type!r} cannot be derived "
        "(only numeric and boolean targets are supported)",
        locator=f"features.{node}",
    )


def _materialize_constant(feat: Any, value: float, n: int) -> np.ndarray:
    if isinstance(feat, BooleanFeature):
        return np.full(n, bool(value))
    if isinstance(feat, NumericFeature) and feat.dtype == "int":
        return np.full(n, int(round(value)), dtype="int64")
    return np.full(n, float(value))
