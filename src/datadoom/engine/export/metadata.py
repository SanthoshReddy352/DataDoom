"""Deterministic ``metadata.json`` writer (04 §8, 06 §3.5).

The metadata document is intentionally free of timestamps or other ambient state
so that it is itself reproducible: the same ``(spec_hash, seed)`` produces an
identical metadata file. Human-facing run timestamps live in the persistence
layer, not in the reproducible artifact bundle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import ArtifactInfo
from .checksums import sha256_bytes


def build_metadata(
    *,
    spec_body: dict[str, Any],
    spec_hash: str,
    seed: int,
    rows: int,
    package_version: str,
    artifacts: list[ArtifactInfo],
    compliance: dict[str, Any],
    determinism: dict[str, Any],
    failures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "datadoom_package_version": package_version,
        "spec_hash": spec_hash,
        "seed": seed,
        "rows": rows,
        "spec": spec_body,
        "artifacts": [a.to_dict() for a in artifacts],
        "compliance": compliance,
        "determinism": determinism,
    }
    if failures is not None:
        metadata["failures"] = failures
    return metadata


def write_metadata(metadata: dict[str, Any], path: str | Path) -> ArtifactInfo:
    text = json.dumps(metadata, sort_keys=True, indent=2, ensure_ascii=False)
    data = (text + "\n").encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return ArtifactInfo(
        path=str(path),
        format="json",
        checksum_sha256=sha256_bytes(data),
        size_bytes=len(data),
    )
