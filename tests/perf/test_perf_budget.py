"""Performance budgets — generous wall-clock smoke checks.

These are NOT in the default suite (deselected by the `-m 'not perf'` addopts);
run them with ``pytest -m perf``. The budgets are intentionally loose so they
flag a real regression (an accidental O(n^2) loop, a per-row Python hot path)
rather than normal CI jitter. Determinism env (single-thread BLAS) is assumed.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from datadoom.engine import generate, load_spec

REPO = Path(__file__).resolve().parents[2]

# A moderately complex shipped spec (causal DAG + logistic target) is a better
# stress than a flat table — it exercises the SEM walk too.
CAUSAL_SPEC = REPO / "examples" / "causal-fraud.datadoom.yaml"

ROWS = 50_000
# Budgets sized for a slow shared CI runner with a wide safety margin; a healthy
# laptop completes this in a small fraction of the budget.
WALL_BUDGET_S = 45.0
MIN_ROWS_PER_S = 2_000


@pytest.mark.perf
def test_generate_50k_rows_within_budget(tmp_path) -> None:
    spec = load_spec(str(CAUSAL_SPEC)).model_copy(update={"rows": ROWS})

    start = time.perf_counter()
    result = generate(spec, seed=7, out_dir=tmp_path)
    elapsed = time.perf_counter() - start

    assert len(result.frame) == ROWS
    assert elapsed < WALL_BUDGET_S, (
        f"generation of {ROWS} rows took {elapsed:.1f}s "
        f"(budget {WALL_BUDGET_S:.0f}s) — possible performance regression"
    )
    throughput = ROWS / elapsed
    assert throughput > MIN_ROWS_PER_S, (
        f"throughput {throughput:.0f} rows/s below floor {MIN_ROWS_PER_S} rows/s"
    )
