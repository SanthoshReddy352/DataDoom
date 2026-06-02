"""The P0 reproducibility gate: same (spec_hash, seed) -> identical bytes.

These are the tests that must stay green to protect the headline guarantee.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datadoom.engine import generate, load_spec

REPO = Path(__file__).resolve().parents[2]
GOLDEN_SPEC = REPO / "tests" / "golden" / "fraud_numeric.datadoom.yaml"
EXAMPLE_SPEC = REPO / "examples" / "tabular-basic.datadoom.yaml"
CAUSAL_SPEC = REPO / "examples" / "causal-fraud.datadoom.yaml"
CHECKSUMS = REPO / "tests" / "golden" / "checksums.json"


@pytest.mark.parametrize("spec_path", [GOLDEN_SPEC, EXAMPLE_SPEC, CAUSAL_SPEC])
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


def test_golden_checksum_pinned(tmp_path) -> None:
    """Within a pinned cell (numpy version), the golden checksum must hold.

    The reference file is keyed by numpy version so a different pinned cell does
    not produce a false failure; if the running numpy is not yet recorded, the
    test skips with an instruction rather than failing spuriously.
    """
    spec = load_spec(str(GOLDEN_SPEC))
    result = generate(spec, seed=12345, out_dir=tmp_path)
    checksum = result.artifacts[0].checksum_sha256

    refs = json.loads(CHECKSUMS.read_text(encoding="utf-8")) if CHECKSUMS.exists() else {}
    key = f"numpy-{np.__version__}"
    if key not in refs:
        pytest.skip(f"no pinned golden checksum for {key}; add it to {CHECKSUMS.name}")
    assert checksum == refs[key], f"golden checksum drift for {key}"
