"""Cross-field spec validation (04 §9).

Pydantic handles shape/type. This module enforces semantic rules that span
multiple parts of the spec — references, acyclicity, derived-vs-sampled
consistency — raising :class:`SpecValidationError` with a ``locator`` pointing
at the offending control.
"""

from __future__ import annotations

from ..errors import SpecValidationError
from .models import (
    BooleanFeature,
    CategoricalFeature,
    NumericFeature,
    Spec,
    TextFeature,
    TimeseriesFeature,
)

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
    from ..dist.providers import is_realistic_generator, resolve_locale

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
        elif isinstance(feat, TextFeature):
            if feat.generator != "lorem" and not is_realistic_generator(feat.generator):
                raise SpecValidationError(
                    f"unknown text generator {feat.generator!r}", locator=f"{loc}.generator"
                )
            resolve_locale(feat.locale, locator=f"{loc}.locale")
        elif isinstance(feat, TimeseriesFeature):
            if feat.min is not None and feat.max is not None and feat.min > feat.max:
                raise SpecValidationError("min > max", locator=loc)
            # AR stationarity: Σ|φᵢ| < 1 is a conservative sufficient condition that
            # keeps the recursion bounded (a true unit-root/explosive series drifts
            # without bound and isn't reproducibly meaningful). Reject otherwise.
            if feat.ar and sum(abs(c) for c in feat.ar) >= 1.0:
                raise SpecValidationError(
                    "time-series AR is non-stationary: sum(|ar coefficients|) must be "
                    f"< 1 (got {sum(abs(c) for c in feat.ar):.3f})",
                    locator=f"{loc}.ar",
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
        elif not isinstance(parent, (NumericFeature, BooleanFeature, TimeseriesFeature)):
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
    # Lazy imports keep the difficulty layer optional at module load time.
    from ..difficulty import PROBES, TIER_BANDS
    from ..difficulty.knobs import ACTIVE_KNOBS

    cfg = spec.difficulty

    # The probe predicts the label; it must be a declared, classification-able
    # feature. v0.1 calibrates binary-classification AUROC only.
    label_feat = spec.features.get(cfg.label)
    if label_feat is None:
        raise SpecValidationError(
            f"difficulty.label {cfg.label!r} is not a declared feature",
            locator="difficulty.label",
        )
    if label_feat.emit is False:
        raise SpecValidationError(
            f"difficulty.label {cfg.label!r} is latent (emit: false) and is not shipped; "
            "the probe can only predict an observable label",
            locator="difficulty.label",
        )
    if isinstance(label_feat, BooleanFeature):
        pass
    elif isinstance(label_feat, CategoricalFeature):
        if len(label_feat.categories) != 2:
            raise SpecValidationError(
                f"difficulty.label {cfg.label!r} is categorical with "
                f"{len(label_feat.categories)} classes; v0.1 calibrates binary "
                "classification only (use a boolean or 2-class categorical label)",
                locator="difficulty.label",
            )
    else:
        raise SpecValidationError(
            f"difficulty.label {cfg.label!r} has type {label_feat.type!r}; v0.1 "
            "supports binary-classification targets only (boolean or 2-class "
            "categorical)",
            locator="difficulty.label",
        )

    if cfg.probe not in PROBES:
        raise SpecValidationError(
            f"unknown difficulty probe {cfg.probe!r} (known: {sorted(PROBES)})",
            locator="difficulty.probe",
        )

    # Target is either a named tier or an explicit band dict.
    if isinstance(cfg.target, str):
        if cfg.target not in TIER_BANDS:
            raise SpecValidationError(
                f"unknown difficulty tier {cfg.target!r} (known: {sorted(TIER_BANDS)})",
                locator="difficulty.target",
            )
    elif isinstance(cfg.target, dict):
        band = cfg.target.get("band")
        if not (isinstance(band, (list, tuple)) and len(band) == 2):
            raise SpecValidationError(
                "difficulty.target must name a tier or carry a 'band': [lo, hi]",
                locator="difficulty.target.band",
            )
        lo, hi = float(band[0]), float(band[1])
        if not (0.0 <= lo <= hi <= 1.0):
            raise SpecValidationError(
                f"difficulty band must satisfy 0 <= lo <= hi <= 1 (got [{lo}, {hi}])",
                locator="difficulty.target.band",
            )
        metric = cfg.target.get("metric", "auroc")
        if metric != "auroc":
            raise SpecValidationError(
                f"unsupported difficulty metric {metric!r}; v0.1 supports 'auroc'",
                locator="difficulty.target.metric",
            )
    else:
        raise SpecValidationError(
            "difficulty.target must be a tier name or an explicit-band object",
            locator="difficulty.target",
        )

    # Only the actively-implemented knobs are accepted — no silently-ignored
    # config. `causal` shrink and `imbalance` are planned (see status.md backlog).
    unknown = [k for k in cfg.knobs if k not in ACTIVE_KNOBS]
    if unknown:
        raise SpecValidationError(
            f"unsupported difficulty knob(s) {unknown}; v0.1 implements "
            f"{list(ACTIVE_KNOBS)} (causal shrink and imbalance are planned)",
            locator="difficulty.knobs",
        )


def _check_failures(spec: Spec) -> None:
    # Lazy import keeps the failure layer optional at module load time.
    from ..failure.modes import FAILURE_MODES

    latent = spec.latent_names()
    for i, failure in enumerate(spec.failures):
        loc = f"failures[{i}]"
        mode = FAILURE_MODES.get(failure.type)
        if mode is None:
            raise SpecValidationError(
                f"unknown failure type {failure.type!r} "
                f"(known: {sorted(FAILURE_MODES)})",
                locator=f"{loc}.type",
            )
        params = failure.model_dump()
        params.pop("type", None)
        mode.validate(params, spec.features, loc)
        # Failures corrupt the *shipped* frame; a latent column was already
        # dropped, so referencing one would fail at runtime — reject it early.
        for val in (*params.values(),):
            refs = val if isinstance(val, list) else [val]
            for ref in refs:
                if isinstance(ref, str) and ref in latent:
                    raise SpecValidationError(
                        f"failure references latent feature {ref!r} (emit: false), "
                        "which is not shipped and cannot be corrupted",
                        locator=loc,
                    )


def _check_export(spec: Spec) -> None:
    from ..export import EXPORTERS

    for fmt in spec.export.formats:
        if fmt not in EXPORTERS:
            known = ", ".join(sorted(EXPORTERS))
            raise SpecValidationError(
                f"unknown export format {fmt!r}; known formats: {known}",
                locator="export.formats",
            )

    splits = spec.export.splits
    if splits is not None:
        total = sum(splits.values())
        if abs(total - 1.0) > 1e-9:
            raise SpecValidationError(
                f"export.splits ratios must sum to 1.0 (got {total})", locator="export.splits"
            )
