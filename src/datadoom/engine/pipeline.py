"""Minimal deterministic generation pipeline (03, 05, 17 step 5).

P0 implements the headless slice of the canonical 9-stage pipeline:

    intake -> snapshot -> seed -> base_generation -> compliance -> packaging

Causal, failure, and difficulty stages arrive in later phases. The single
entry point :func:`generate` is what the CLI, API, and ``datadoom.generate()``
all call — generation logic is never duplicated.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..version import __version__
from .dist import (
    REGISTRY,
    ComplianceReport,
    assess_numeric,
    sample_boolean,
    sample_categorical,
    sample_datetime,
    sample_provider,
    sample_text,
)
from .dist.compliance import DEFAULT_ALPHA
from .errors import SpecValidationError
from .export import EXPORTERS, ArtifactInfo, build_metadata, write_metadata
from .progress import ProgressEmitter
from .reports import ReportBundle, build_report
from .rng import RNGFactory
from .spec import Spec, validate_spec
from .spec.models import (
    BooleanFeature,
    CategoricalFeature,
    DatetimeFeature,
    NumericFeature,
    TextFeature,
)

STAGES = (
    "intake",
    "snapshot",
    "seed",
    "base_generation",
    "causal",
    "failure_injection",
    "compliance",
    "packaging",
)


@dataclass
class RunContext:
    spec: Spec
    spec_hash: str
    seed: int
    rng: RNGFactory
    frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    reports: dict[str, Any] = field(default_factory=dict)
    progress: ProgressEmitter = field(default_factory=ProgressEmitter)
    used_namespaces: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    spec_hash: str
    seed: int
    frame: pd.DataFrame
    compliance: ComplianceReport
    metadata: dict[str, Any]
    artifacts: list[ArtifactInfo]
    out_dir: str | None
    report: ReportBundle
    injected: pd.DataFrame | None = None


def resolve_seed(spec: Spec, seed_override: int | None) -> int:
    """Resolve the effective seed: override > spec.seed > fresh OS entropy.

    Seed generation is the one sanctioned use of OS entropy — it is NOT on the
    data path. The resolved seed is recorded so the run is reproducible after.
    Exposed so callers (e.g. the API) can persist the resolved seed at
    run-creation time and stay consistent with what the pipeline would pick.
    """
    if seed_override is not None:
        return int(seed_override)
    if spec.seed is not None:
        return int(spec.seed)
    return int.from_bytes(os.urandom(8), "big") & ((1 << 63) - 1)


def _derived_features(spec: Spec) -> set[str]:
    """Feature names produced by the causal layer (any edge destination)."""
    if spec.causal is None:
        return set()
    return {edge.dst for edge in spec.causal.edges}


def _sample_feature(name: str, feat: Any, ctx: RunContext) -> tuple[np.ndarray, float]:
    """Return (values, clamped_fraction) for one feature."""
    n = ctx.spec.rows
    rng = ctx.rng.feature(name)
    ctx.used_namespaces.append(f"feature:{name}")

    if isinstance(feat, NumericFeature):
        if feat.dist is None:
            raise SpecValidationError(
                f"feature {name!r} has no distribution; derived (causal) features "
                "require the causal engine, which arrives in a later phase",
                locator=f"features.{name}",
            )
        values = REGISTRY[feat.dist].sample(rng, n, feat.params)
        clamped_fraction = 0.0
        if feat.min is not None or feat.max is not None:
            lo = -np.inf if feat.min is None else feat.min
            hi = np.inf if feat.max is None else feat.max
            mask = (values < lo) | (values > hi)
            clamped_fraction = float(np.mean(mask)) if n else 0.0
            values = np.clip(values, lo, hi)
        if feat.dtype == "int":
            values = np.rint(values).astype("int64")
        return values, clamped_fraction

    if isinstance(feat, CategoricalFeature):
        return sample_categorical(rng, n, feat.categories, feat.weights), 0.0
    if isinstance(feat, BooleanFeature):
        return sample_boolean(rng, n, feat.rate), 0.0
    if isinstance(feat, DatetimeFeature):
        return sample_datetime(rng, n, feat.start, feat.end, feat.granularity), 0.0
    if isinstance(feat, TextFeature):
        if feat.generator == "lorem":
            return (
                sample_text(rng, n, feat.length.get("min", 5), feat.length.get("max", 30)),
                0.0,
            )
        return sample_provider(rng, n, feat.generator, feat.locale), 0.0
    raise SpecValidationError(f"unsupported feature type for {name!r}", locator=f"features.{name}")


def generate(
    spec: Spec,
    *,
    seed: int | None = None,
    out_dir: str | Path | None = None,
    progress: ProgressEmitter | None = None,
    alpha: float = DEFAULT_ALPHA,
) -> RunResult:
    """Execute the minimal pipeline and (optionally) write artifacts."""
    progress = progress or ProgressEmitter()

    # 1. intake & validate
    progress.emit("intake", 0, "validating spec")
    validate_spec(spec)

    # 2. snapshot & hash
    progress.emit("snapshot", 10, "hashing spec")
    spec_hash = spec.spec_hash()

    # 3. seed resolution
    resolved_seed = resolve_seed(spec, seed)
    rng = RNGFactory(spec_hash, resolved_seed)
    ctx = RunContext(spec=spec, spec_hash=spec_hash, seed=resolved_seed, rng=rng, progress=progress)
    progress.emit("seed", 20, f"seed={resolved_seed}")

    # 4. base feature generation — sample root (non-derived) features.
    # Causal targets are computed in the causal stage, not sampled here.
    progress.emit("base_generation", 30, "sampling features")
    derived = _derived_features(spec)
    columns: dict[str, np.ndarray] = {}
    clamp_fractions: dict[str, float] = {}
    for fname, feat in spec.features.items():
        if fname in derived:
            continue
        values, clamped = _sample_feature(fname, feat, ctx)
        columns[fname] = values
        clamp_fractions[fname] = clamped

    # 5. causal / SEM execution — fill derived columns in topological order.
    causal_dag = None
    if spec.causal is not None:
        progress.emit("causal", 55, "executing structural equations")
        from .causal import execute_causal

        causal_dag = execute_causal(ctx, columns)

    frame = pd.DataFrame(columns, columns=list(spec.features.keys()))
    ctx.frames["clean"] = frame

    # 6. failure injection — corrupt a copy; the clean baseline is preserved.
    injected: pd.DataFrame | None = None
    failure_diffs: list[dict[str, Any]] | None = None
    if spec.failures:
        progress.emit("failure_injection", 62, "injecting failures")
        from .failure import apply_failures

        injected, failure_diffs = apply_failures(ctx, frame)
        ctx.frames["injected"] = injected

    # 7. compliance (honest KS, no refit) — assessed on the clean baseline.
    progress.emit("compliance", 70, "assessing distribution fit")
    report = ComplianceReport(alpha=alpha)
    for fname, feat in spec.features.items():
        if isinstance(feat, NumericFeature) and feat.dist is not None:
            report.features.append(
                assess_numeric(
                    fname,
                    feat.dist,
                    feat.params,
                    frame[fname].to_numpy(),
                    clamped_fraction=clamp_fractions[fname],
                    alpha=alpha,
                    dtype=feat.dtype,
                )
            )
    ctx.reports["compliance"] = report

    # 8. packaging
    progress.emit("packaging", 90, "writing artifacts")
    determinism: dict[str, Any] = {
        "spec_hash": ctx.spec_hash,
        "seed": ctx.seed,
        "namespace_key_digests": ctx.rng.key_digests(sorted(set(ctx.used_namespaces))),
        "artifact_checksums": {},
    }
    artifacts: list[ArtifactInfo] = []
    metadata: dict[str, Any] = {}
    out_path: str | None = None
    if out_dir is not None:
        out_path = str(out_dir)
        artifacts, metadata, checksums = _package(
            ctx, frame, report, determinism, Path(out_dir), injected, failure_diffs
        )
        determinism["artifact_checksums"] = checksums

    report_bundle = build_report(
        compliance=report,
        frame=frame,
        determinism=determinism,
        causal=spec.causal,
        causal_dag=causal_dag,
        failures=failure_diffs,
    )

    progress.emit("packaging", 100, "done")
    return RunResult(
        spec_hash=spec_hash,
        seed=resolved_seed,
        frame=frame,
        compliance=report,
        metadata=metadata,
        artifacts=artifacts,
        out_dir=out_path,
        report=report_bundle,
        injected=injected,
    )


def _package(
    ctx: RunContext,
    frame: pd.DataFrame,
    report: ComplianceReport,
    determinism: dict[str, Any],
    out_dir: Path,
    injected: pd.DataFrame | None = None,
    failure_diffs: list[dict[str, Any]] | None = None,
) -> tuple[list[ArtifactInfo], dict[str, Any], dict[str, str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    exporter = EXPORTERS["csv"]

    data_path = out_dir / "data.csv"
    data_artifact = exporter.write(frame, data_path)
    # Store a path relative to out_dir so checksums/metadata are location-stable.
    data_artifact.path = data_path.name
    data_artifact.version = "clean"

    data_artifacts = [data_artifact]
    # The injected variant ships alongside the clean baseline when the spec asks
    # for it (and any failures actually ran).
    if injected is not None and "injected" in ctx.spec.export.versions:
        injected_path = out_dir / "data.injected.csv"
        injected_artifact = exporter.write(injected, injected_path)
        injected_artifact.path = injected_path.name
        injected_artifact.version = "injected"
        data_artifacts.append(injected_artifact)

    checksums = {a.path: a.checksum_sha256 for a in data_artifacts}
    determinism = {**determinism, "artifact_checksums": checksums}
    metadata = build_metadata(
        spec_body=ctx.spec.body(),
        spec_hash=ctx.spec_hash,
        seed=ctx.seed,
        rows=ctx.spec.rows,
        package_version=__version__,
        artifacts=data_artifacts,
        compliance=report.to_dict(),
        determinism=determinism,
        failures=failure_diffs,
    )
    meta_artifact = write_metadata(metadata, out_dir / "metadata.json")
    meta_artifact.path = "metadata.json"

    # The resolved spec (with seed) so the bundle is self-reproducing.
    resolved_spec = dict(ctx.spec.body())
    resolved_spec["seed"] = ctx.seed
    _write_resolved_spec(resolved_spec, out_dir / "spec.resolved.yaml")

    return [*data_artifacts, meta_artifact], metadata, checksums


def _write_resolved_spec(spec_body: dict[str, Any], path: Path) -> None:
    import yaml

    text = yaml.safe_dump(spec_body, sort_keys=True, default_flow_style=False)
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))
