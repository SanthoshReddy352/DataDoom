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
    TimeseriesFeature,
)
from .timeseries import Seasonality, Trend, generate_series

STAGES = (
    "intake",
    "snapshot",
    "seed",
    "base_generation",
    "causal",
    "difficulty",
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
    difficulty: dict[str, Any] | None = None


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


def _clamp_and_cast(
    values: np.ndarray, lo: float | None, hi: float | None, dtype: str, n: int
) -> tuple[np.ndarray, float]:
    """Apply optional ``min``/``max`` clamping and int rounding; report clamped fraction."""
    clamped_fraction = 0.0
    if lo is not None or hi is not None:
        low = -np.inf if lo is None else lo
        high = np.inf if hi is None else hi
        mask = (values < low) | (values > high)
        clamped_fraction = float(np.mean(mask)) if n else 0.0
        values = np.clip(values, low, high)
    if dtype == "int":
        values = np.rint(values).astype("int64")
    return values, clamped_fraction


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
        return _clamp_and_cast(values, feat.min, feat.max, feat.dtype, n)

    if isinstance(feat, TimeseriesFeature):
        # εₜ flows through the noise namespace (05 §6: RNG(noise:<series>)).
        ts_rng = ctx.rng.noise(name)
        ctx.used_namespaces[-1] = f"noise:{name}"  # replace the feature:<name> we appended
        series = generate_series(
            ts_rng,
            n,
            trend=Trend(feat.trend.slope, feat.trend.intercept) if feat.trend else None,
            seasonality=[Seasonality(s.amplitude, s.period, s.phase) for s in feat.seasonality],
            ar=feat.ar,
            noise_std=feat.noise_std,
        )
        return _clamp_and_cast(series, feat.min, feat.max, feat.dtype, n)

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

    # 5a. latent features (emit: false) drove sampling / the SEM and remain in the
    # true causal graph, but are NOT shipped — drop them before difficulty,
    # failures, compliance, and packaging so nothing downstream (incl. the probe)
    # can see a hidden variable.
    latent = spec.latent_names()
    if latent:
        frame = frame.drop(columns=[c for c in latent if c in frame.columns])
    ctx.frames["clean"] = frame

    # 5b. difficulty calibration — tune the dataset to a target baseline-metric
    # band (feature-observation noise / label flips), baked into the clean frame.
    difficulty_report: dict[str, Any] | None = None
    if spec.difficulty is not None:
        progress.emit("difficulty", 58, "calibrating difficulty")
        from .difficulty import calibrate_difficulty

        diff_result, frame = calibrate_difficulty(ctx, frame)
        difficulty_report = diff_result.to_dict()
        ctx.frames["clean"] = frame  # the calibrated frame is the shipped baseline

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
        if feat.emit is False:
            continue  # latent — not shipped, so nothing to assess
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
                    clamp_min=feat.min,
                    clamp_max=feat.max,
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
        spec=spec,
        causal=spec.causal,
        causal_dag=causal_dag,
        failures=failure_diffs,
        injected=injected,
        difficulty=difficulty_report,
    )

    # Bind a human-readable audit report (compliance + column guide + failures +
    # determinism) into the bundle so a download is self-describing. Registered as
    # a tracked artifact but kept out of the metadata checksum map (like the spec).
    if out_dir is not None:
        from .audit import render_audit_markdown

        audit_md = render_audit_markdown(spec, report_bundle, package_version=__version__)
        artifacts.append(_write_audit_report(audit_md, Path(out_dir) / "audit_report.md"))

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
        difficulty=difficulty_report,
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

    # Each requested format gets a file per shipped version. CSV stays first so it
    # remains the canonical preview/determinism artifact (`data.csv`); other formats
    # ship alongside it (09 §8).
    formats = ctx.spec.export.formats or ["csv"]
    want_injected = injected is not None and "injected" in ctx.spec.export.versions
    variants: list[tuple[str, pd.DataFrame]] = [("clean", frame)]
    if want_injected:
        variants.append(("injected", injected))

    data_artifacts: list[ArtifactInfo] = []
    for fmt in formats:
        exporter = EXPORTERS[fmt]
        for version, variant in variants:
            stem = "data" if version == "clean" else "data.injected"
            name = f"{stem}.{exporter.ext}"
            artifact = exporter.write(variant, out_dir / name)
            # Store a path relative to out_dir so checksums/metadata are location-stable.
            artifact.path = name
            artifact.version = version
            data_artifacts.append(artifact)

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

    # The resolved spec (with seed) so the bundle is self-reproducing. It is
    # registered as a tracked, checksummed artifact (version "spec") — the locked,
    # version-controllable record of exactly what produced this run — but kept OUT
    # of the metadata determinism checksum map (that map is for data files only),
    # so ``metadata.json`` stays byte-identical across runs.
    resolved_spec = dict(ctx.spec.body())
    resolved_spec["seed"] = ctx.seed
    spec_artifact = _write_resolved_spec(resolved_spec, out_dir / "spec.resolved.yaml")

    return [*data_artifacts, meta_artifact, spec_artifact], metadata, checksums


def _write_audit_report(markdown: str, path: Path) -> ArtifactInfo:
    """Write the audit report and return its tracked-artifact info (version 'audit')."""
    from .export import sha256_bytes

    data = markdown.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(data)
    return ArtifactInfo(
        path=path.name,
        format="md",
        checksum_sha256=sha256_bytes(data),
        size_bytes=len(data),
        version="audit",
    )


def _write_resolved_spec(spec_body: dict[str, Any], path: Path) -> ArtifactInfo:
    import yaml

    from .export import sha256_bytes

    text = yaml.safe_dump(spec_body, sort_keys=True, default_flow_style=False)
    data = text.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(data)
    return ArtifactInfo(
        path=path.name,
        format="yaml",
        checksum_sha256=sha256_bytes(data),
        size_bytes=len(data),
        version="spec",
    )
