"""Cross-field spec validation (04 §9).

Pydantic handles shape/type. This module enforces semantic rules that span
multiple parts of the spec — references, acyclicity, derived-vs-sampled
consistency — raising :class:`SpecValidationError` with a ``locator`` pointing
at the offending control.
"""

from __future__ import annotations

from ..errors import SpecValidationError
from .models import BooleanFeature, CategoricalFeature, NumericFeature, Spec

SUPPORTED_SPEC_VERSIONS = {"1"}


def validate_spec(spec: Spec) -> None:
    """Run all cross-field checks. Raises on the first violation."""
    _check_version(spec)
    _check_features(spec)
    _check_causal(spec)
    _check_difficulty(spec)
    _check_failures(spec)
    _check_export(spec)


def _check_version(spec: Spec) -> None:
    if spec.datadoom_version not in SUPPORTED_SPEC_VERSIONS:
        raise SpecValidationError(
            f"unsupported datadoom_version {spec.datadoom_version!r} "
            f"(supported: {sorted(SUPPORTED_SPEC_VERSIONS)})",
            locator="datadoom_version",
        )


def _check_features(spec: Spec) -> None:
    # Lazy import to keep the dist layer optional at module load time.
    from ..dist.builtins import REGISTRY

    derived = _derived_names(spec)
    for name, feat in spec.features.items():
        loc = f"features.{name}"
        if isinstance(feat, NumericFeature):
            if feat.min is not None and feat.max is not None and feat.min > feat.max:
                raise SpecValidationError("min > max", locator=loc)
            if feat.dist is not None:
                dist = REGISTRY.get(feat.dist)
                if dist is None:
                    raise SpecValidationError(
                        f"unknown distribution {feat.dist!r}", locator=f"{loc}.dist"
                    )
                dist.validate(feat.params, locator=f"{loc}.params")
            elif name not in derived:
                # No dist and not produced by the causal layer → unsamplable.
                raise SpecValidationError(
                    f"numeric feature {name!r} has no 'dist' and is not a causal target "
                    "(it cannot be sampled or derived)",
                    locator=loc,
                )
        elif isinstance(feat, CategoricalFeature):
            if feat.weights is not None and len(feat.weights) != len(feat.categories):
                raise SpecValidationError(
                    "weights length must match categories length", locator=f"{loc}.weights"
                )


def _derived_names(spec: Spec) -> set[str]:
    if spec.causal is None:
        return set()
    return {edge.dst for edge in spec.causal.edges}


def _check_causal(spec: Spec) -> None:
    if spec.causal is None:
        return
    # Lazy imports keep the dist/causal layers optional at module load time.
    from ..causal.functions import STRUCTURAL_FNS
    from ..dist.builtins import REGISTRY

    feature_names = set(spec.features)
    targets: set[str] = set()
    adjacency: dict[str, list[str]] = {n: [] for n in feature_names}

    for i, edge in enumerate(spec.causal.edges):
        loc = f"causal.edges[{i}]"
        if edge.src not in feature_names:
            raise SpecValidationError(f"unknown 'from' feature {edge.src!r}", locator=loc)
        if edge.dst not in feature_names:
            raise SpecValidationError(f"unknown 'to' feature {edge.dst!r}", locator=loc)
        fn = STRUCTURAL_FNS.get(edge.fn)
        if fn is None:
            raise SpecValidationError(
                f"unknown structural function {edge.fn!r}", locator=f"{loc}.fn"
            )
        fn.validate(edge, locator=loc)
        # The structural function must be compatible with the parent's type, or
        # execution would hit a raw coercion error. `map` consumes a categorical
        # parent; the numeric fns need a numeric/boolean (float-coercible) parent.
        parent = spec.features[edge.src]
        if edge.fn == "map":
            if not isinstance(parent, CategoricalFeature):
                raise SpecValidationError(
                    f"map edge requires a categorical 'from' feature; {edge.src!r} is "
                    f"type {parent.type!r}",
                    locator=f"{loc}.fn",
                )
            missing = [c for c in parent.categories if c not in (edge.mapping or {})]
            if missing:
                raise SpecValidationError(
                    f"map edge is missing mappings for categories {missing}",
                    locator=f"{loc}.mapping",
                )
        elif not isinstance(parent, (NumericFeature, BooleanFeature)):
            raise SpecValidationError(
                f"{edge.fn!r} edge requires a numeric/boolean 'from' feature; {edge.src!r} "
                f"is type {parent.type!r} (use fn 'map' for categorical parents)",
                locator=f"{loc}.fn",
            )
        adjacency[edge.src].append(edge.dst)
        targets.add(edge.dst)

    for name in targets:
        feat = spec.features[name]
        # A feature that is both directly sampled and a causal target is ambiguous.
        if isinstance(feat, NumericFeature) and feat.dist is not None:
            raise SpecValidationError(
                f"feature {name!r} is both sampled (has dist) and derived (causal target)",
                locator=f"features.{name}",
            )
        # Only numeric/boolean targets can be derived by the SEM.
        if not isinstance(feat, (NumericFeature, BooleanFeature)):
            raise SpecValidationError(
                f"causal target {name!r} has type {feat.type!r}; only numeric and boolean "
                "features can be derived",
                locator=f"features.{name}",
            )

    # Per-node noise must reference a known distribution (or be 'none').
    for node, noise in spec.causal.noise.items():
        loc = f"causal.noise.{node}"
        if node not in feature_names:
            raise SpecValidationError(f"noise references unknown feature {node!r}", locator=loc)
        dist_name = noise.get("dist")
        if dist_name not in (None, "none") and dist_name not in REGISTRY:
            raise SpecValidationError(
                f"unknown noise distribution {dist_name!r}", locator=f"{loc}.dist"
            )

    # Interventions must reference real features.
    for i, item in enumerate(spec.causal.interventions):
        do = item.get("do", {})
        for node in do:
            if node not in feature_names:
                raise SpecValidationError(
                    f"intervention references unknown feature {node!r}",
                    locator=f"causal.interventions[{i}].do",
                )

    _reject_cycles(adjacency)


def _reject_cycles(adjacency: dict[str, list[str]]) -> None:
    """Kahn's algorithm; if not all nodes are emitted, a cycle exists."""
    indegree = {n: 0 for n in adjacency}
    for _, children in sorted(adjacency.items()):
        for child in children:
            indegree[child] += 1
    queue = sorted(n for n, d in indegree.items() if d == 0)
    emitted = 0
    while queue:
        node = queue.pop(0)
        emitted += 1
        for child in sorted(adjacency[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
        queue.sort()
    if emitted != len(adjacency):
        raise SpecValidationError("causal graph is not acyclic", locator="causal.edges")


def _check_difficulty(spec: Spec) -> None:
    if spec.difficulty is None:
        return
    if spec.difficulty.label not in spec.features:
        raise SpecValidationError(
            f"difficulty.label {spec.difficulty.label!r} is not a declared feature",
            locator="difficulty.label",
        )


def _check_failures(spec: Spec) -> None:
    feature_names = set(spec.features)
    for i, failure in enumerate(spec.failures):
        loc = f"failures[{i}]"
        data = failure.model_dump()
        rate = data.get("rate")
        if rate is not None and not 0.0 <= float(rate) <= 1.0:
            raise SpecValidationError("rate must be in [0, 1]", locator=f"{loc}.rate")
        for key in ("column", "driver", "target", "into"):
            ref = data.get(key)
            if isinstance(ref, str) and ref not in feature_names:
                raise SpecValidationError(
                    f"{key} {ref!r} is not a declared feature", locator=f"{loc}.{key}"
                )
        cols = data.get("columns")
        if isinstance(cols, list):
            for ref in cols:
                if ref not in feature_names:
                    raise SpecValidationError(
                        f"column {ref!r} is not a declared feature", locator=f"{loc}.columns"
                    )


def _check_export(spec: Spec) -> None:
    splits = spec.export.splits
    if splits is not None:
        total = sum(splits.values())
        if abs(total - 1.0) > 1e-9:
            raise SpecValidationError(
                f"export.splits ratios must sum to 1.0 (got {total})", locator="export.splits"
            )
