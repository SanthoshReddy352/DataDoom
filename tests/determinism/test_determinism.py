"""The P0 reproducibility gate: same (spec_hash, seed) -> identical bytes.

These are the tests that must stay green to protect the headline guarantee.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datadoom.engine import generate, load_spec

REPO = Path(__file__).resolve().parents[2]
GOLDEN_SPEC = REPO / "tests" / "golden" / "fraud_numeric.datadoom.yaml"
EXAMPLE_SPEC = REPO / "examples" / "tabular-basic.datadoom.yaml"
CAUSAL_SPEC = REPO / "examples" / "causal-fraud.datadoom.yaml"
FAILURE_SPEC = REPO / "examples" / "failure-fraud.datadoom.yaml"
PEOPLE_SPEC = REPO / "examples" / "people-realistic.datadoom.yaml"
DIFFICULTY_SPEC = REPO / "examples" / "difficulty-credit.datadoom.yaml"
TIMESERIES_SPEC = REPO / "examples" / "timeseries-sensor.datadoom.yaml"
CHECKSUMS = REPO / "tests" / "golden" / "checksums.json"


@pytest.mark.parametrize(
    "spec_path",
    [
        GOLDEN_SPEC,
        EXAMPLE_SPEC,
        CAUSAL_SPEC,
        FAILURE_SPEC,
        PEOPLE_SPEC,
        DIFFICULTY_SPEC,
        TIMESERIES_SPEC,
    ],
)
def test_two_runs_identical(tmp_path, spec_path) -> None:
    spec = load_spec(str(spec_path))
    r1 = generate(spec, seed=99, out_dir=tmp_path / "a")
    r2 = generate(spec, seed=99, out_dir=tmp_path / "b")

    # Frames are equal value-for-value.
    pd.testing.assert_frame_equal(r1.frame, r2.frame)
    # And the serialized bytes are bitwise-identical.
    a = (tmp_path / "a" / "data.csv").read_bytes()
    b = (tmp_path / "b" / "data.csv").read_bytes()
    assert a == b
    assert r1.artifacts[0].checksum_sha256 == r2.artifacts[0].checksum_sha256


def test_injected_variant_is_byte_stable(tmp_path) -> None:
    """The injected corruption is itself reproducible on the pinned path."""
    spec = load_spec(str(FAILURE_SPEC))
    generate(spec, seed=99, out_dir=tmp_path / "a")
    generate(spec, seed=99, out_dir=tmp_path / "b")
    a = (tmp_path / "a" / "data.injected.csv").read_bytes()
    b = (tmp_path / "b" / "data.injected.csv").read_bytes()
    assert a == b


def test_spec_hash_excludes_seed(tmp_path) -> None:
    spec = load_spec(str(GOLDEN_SPEC))
    h1 = generate(spec, seed=1).spec_hash
    h2 = generate(spec, seed=2).spec_hash
    assert h1 == h2


def test_different_seed_changes_data() -> None:
    spec = load_spec(str(GOLDEN_SPEC))
    a = generate(spec, seed=1).frame["age"].to_numpy()
    b = generate(spec, seed=2).frame["age"].to_numpy()
    assert not np.array_equal(a, b)


def golden_checksum_key() -> str:
    """The (OS, arch, numpy) cell a golden checksum is recorded against.

    Doc 13 scopes the **bitwise** guarantee to a single OS/arch on the pinned
    dependency set — FP reductions can differ across BLAS builds / architectures —
    so the golden checksum is keyed per platform, not globally per numpy version.
    """
    return f"{platform.system()}-{platform.machine()}-numpy-{np.__version__}"


def test_golden_checksum_pinned(tmp_path) -> None:
    """Within a pinned cell (OS + arch + numpy), the golden checksum must hold.

    The reference file is keyed per platform so a cell with no recorded value
    skips with an instruction (and CI prints the value to record) rather than
    failing spuriously or — worse — silently passing a cross-platform mismatch.
    """
    spec = load_spec(str(GOLDEN_SPEC))
    result = generate(spec, seed=12345, out_dir=tmp_path)
    checksum = result.artifacts[0].checksum_sha256

    refs = json.loads(CHECKSUMS.read_text(encoding="utf-8")) if CHECKSUMS.exists() else {}
    key = golden_checksum_key()
    if key not in refs:
        pytest.skip(
            f"no pinned golden checksum for '{key}'. Record it by adding "
            f'"{key}": "{checksum}" to {CHECKSUMS.name} '
            "(the repro-matrix CI prints this value per cell)."
        )
    assert checksum == refs[key], f"golden checksum drift for {key}"
