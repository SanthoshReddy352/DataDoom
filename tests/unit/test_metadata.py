"""Metadata integrity of a written bundle (status.md task TH.8).

A run that writes artifacts must produce a `metadata.json` whose recorded
checksum actually matches the bytes on disk, whose `spec_hash` matches the run,
and a `spec.resolved.yaml` that bakes in the resolved seed so the bundle is
self-reproducing.
"""

from __future__ import annotations

import json

import yaml

from datadoom.engine import generate, parse_spec
from datadoom.engine.export.checksums import sha256_file


def _spec():
    return parse_spec(
        {
            "datadoom_version": "1",
            "name": "meta",
            "rows": 200,
            "features": {
                "x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            },
        }
    )


def test_recorded_checksum_matches_file(tmp_path) -> None:
    out = tmp_path / "bundle"
    generate(_spec(), seed=7, out_dir=out)

    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    recorded = meta["determinism"]["artifact_checksums"]["data.csv"]
    assert recorded == sha256_file(out / "data.csv")
    # The artifacts list carries the same checksum for data.csv.
    csv_artifact = next(a for a in meta["artifacts"] if a["path"] == "data.csv")
    assert csv_artifact["checksum_sha256"] == recorded


def test_metadata_spec_hash_matches_run(tmp_path) -> None:
    out = tmp_path / "bundle"
    result = generate(_spec(), seed=7, out_dir=out)

    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert meta["spec_hash"] == result.spec_hash
    assert meta["determinism"]["spec_hash"] == result.spec_hash


def test_resolved_spec_carries_resolved_seed(tmp_path) -> None:
    out = tmp_path / "bundle"
    result = generate(_spec(), seed=7, out_dir=out)

    resolved = yaml.safe_load((out / "spec.resolved.yaml").read_text(encoding="utf-8"))
    assert resolved["seed"] == result.seed == 7
