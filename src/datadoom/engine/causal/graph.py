"""Causal DAG construction & deterministic traversal (05 §3, 17 step 11).

Wraps a ``networkx.DiGraph`` built from the spec's causal edges. The engine is
pure, so graph operations are deterministic: nodes iterate in **sorted** order
and the topological walk is **lexicographical**, so the SEM execution order is a
function of the spec alone (never of dict/hash iteration order).
"""

from __future__ import annotations

import networkx as nx

from ..errors import SpecValidationError
from ..spec.models import CausalEdge


class CausalDag:
    """A validated causal DAG over the spec's feature names.

    Cycle detection is defensive — ``validate_spec`` already rejects cycles, but
    constructing the graph re-checks so the engine never executes a bad walk.
    """

    def __init__(self, edges: list[CausalEdge], feature_names: list[str]) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()
        self._graph.add_nodes_from(sorted(feature_names))
        # Author order is preserved per destination so summation order (and thus
        # floating-point results) is a stable function of the spec.
        self._in_edges: dict[str, list[CausalEdge]] = {n: [] for n in feature_names}
        for edge in edges:
            self._graph.add_edge(edge.src, edge.dst)
            self._in_edges[edge.dst].append(edge)
        if not nx.is_directed_acyclic_graph(self._graph):
            raise SpecValidationError("causal graph is not acyclic", locator="causal.edges")

    def topological_order(self) -> list[str]:
        """Deterministic topological order (lexicographical tie-breaking)."""
        return list(nx.lexicographical_topological_sort(self._graph))

    def in_edges(self, node: str) -> list[CausalEdge]:
        """Incoming edges for ``node`` in author order (empty for roots)."""
        return self._in_edges.get(node, [])

    def parents(self, node: str) -> list[str]:
        """Sorted parent feature names of ``node``."""
        return sorted(self._graph.predecessors(node))

    def is_derived(self, node: str) -> bool:
        """True if ``node`` has at least one incoming edge (computed, not sampled)."""
        return bool(self._in_edges.get(node))

    def derived_nodes(self) -> set[str]:
        """All nodes that are causal targets (have ≥1 incoming edge)."""
        return {n for n, e in self._in_edges.items() if e}
