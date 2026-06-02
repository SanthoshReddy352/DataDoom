"""Resource estimator (doc 12) — heuristic runtime / RAM / output-size guess.

Local-first means **no cost, no GPU, no quotas** — we estimate only so the UI can
warn before a heavy run. Pure function of the spec + fixed calibration constants,
so it is deterministic and reproducible (doc 12 §9). Never blocks a run.
"""

from __future__ import annotations

from dataclasses import dataclass

from datadoom.engine import Spec

# Per-cell byte estimates by type (doc 12 §3).
_BYTES_NUMERIC = 8
_BYTES_BOOL = 1
_BYTES_DATETIME = 19  # ISO-8601 string in CSV
_CSV_FORMAT_FACTOR = 1.2

# Calibrated throughput constants (rows/sec-ish) — reference-laptop defaults (doc 12 §6).
_KAPPA_SAMPLE = 4_000_000.0  # vectorized sampling cells/sec
_KAPPA_IO = 80_000_000.0  # bytes/sec write
_T_FIXED = 0.15  # process/setup overhead seconds


@dataclass
class Estimate:
    estimated_runtime_seconds: float
    estimated_ram_mb: float
    estimated_size_bytes: int
    features: int
    edges: int
    gpu_required: bool = False


def _avg_bytes(feat) -> float:  # noqa: ANN001 — duck-typed over the feature union
    t = feat.type
    if t == "numeric":
        return _BYTES_NUMERIC
    if t == "boolean":
        return _BYTES_BOOL
    if t == "datetime":
        return _BYTES_DATETIME
    if t == "categorical":
        labels = feat.categories or [""]
        return sum(len(c) for c in labels) / len(labels) + 1
    if t == "text":
        length = getattr(feat, "length", {}) or {}
        avg_tokens = (length.get("min", 5) + length.get("max", 30)) / 2
        return avg_tokens * 5  # ~5 bytes/token incl. spaces
    return _BYTES_NUMERIC


def estimate(spec: Spec) -> Estimate:
    n = spec.rows
    feats = list(spec.features.values())
    f = len(feats)
    edges = len(spec.causal.edges) if spec.causal else 0

    bytes_per_row = sum(_avg_bytes(ft) for ft in feats)
    versions = len(spec.export.versions) or 1
    formats = len(spec.export.formats) or 1
    size_clean = n * bytes_per_row * _CSV_FORMAT_FACTOR
    size_total = int(size_clean * versions * formats)

    f_num = sum(1 for ft in feats if ft.type == "numeric")
    t_base = (n * max(f_num, 1)) / _KAPPA_SAMPLE
    t_io = size_total / _KAPPA_IO
    runtime = round(_T_FIXED + t_base + t_io, 3)

    # One float64 working frame, with clean (+possible injected) copies (doc 12 §4).
    frame_multiplier = 2 + (1 if "injected" in spec.export.versions else 0)
    ram_mb = round((n * max(f, 1) * 8 * frame_multiplier) / (1024 * 1024), 2)

    return Estimate(
        estimated_runtime_seconds=runtime,
        estimated_ram_mb=ram_mb,
        estimated_size_bytes=size_total,
        features=f,
        edges=edges,
        gpu_required=False,
    )
