"""Time-series generation (05 §6): components, determinism, validation, audit."""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, load_spec, parse_spec
from datadoom.engine.errors import SpecValidationError
from datadoom.engine.rng import RNGFactory
from datadoom.engine.timeseries import Seasonality, Trend, generate_series


def _rng():
    return RNGFactory("h", 1).noise("series")


# --- component math ------------------------------------------------------------------


def test_pure_trend_is_exact_line() -> None:
    s = generate_series(_rng(), 100, trend=Trend(slope=2.0, intercept=5.0), noise_std=0.0)
    expected = 2.0 * np.arange(100) + 5.0
    assert np.allclose(s, expected)


def test_seasonality_is_periodic() -> None:
    s = generate_series(
        _rng(), 48, seasonality=[Seasonality(amplitude=3.0, period=24, phase=0.0)], noise_std=0.0
    )
    # One full period apart, the deterministic seasonal value repeats.
    assert np.allclose(s[:24], s[24:48], atol=1e-9)
    assert abs(s.max() - 3.0) < 1e-9 and abs(s.min() + 3.0) < 1e-9


def test_ar1_induces_positive_autocorrelation() -> None:
    s = generate_series(_rng(), 20_000, ar=[0.6], noise_std=1.0)
    lag1 = np.corrcoef(s[:-1], s[1:])[0, 1]
    # AR(1) with φ=0.6 has theoretical lag-1 autocorrelation = φ.
    assert abs(lag1 - 0.6) < 0.05


def test_noise_only_is_iid_gaussian() -> None:
    s = generate_series(_rng(), 50_000, noise_std=2.0)
    assert abs(float(np.std(s)) - 2.0) < 0.05
    assert abs(np.corrcoef(s[:-1], s[1:])[0, 1]) < 0.03  # no autocorrelation


def test_generate_series_is_deterministic() -> None:
    a = generate_series(_rng(), 500, trend=Trend(0.1, 1.0), ar=[0.4], noise_std=1.0)
    b = generate_series(_rng(), 500, trend=Trend(0.1, 1.0), ar=[0.4], noise_std=1.0)
    assert np.array_equal(a, b)


# --- validation ----------------------------------------------------------------------


def _ts_spec(**ts):
    return {
        "datadoom_version": "1",
        "name": "ts",
        "rows": 100,
        "seed": 1,
        "features": {"x": {"type": "timeseries", **ts}},
    }


def test_nonstationary_ar_rejected() -> None:
    # sum|φ| = 1.2 ≥ 1 → non-stationary; parse_spec runs cross-field validation.
    with pytest.raises(SpecValidationError) as e:
        parse_spec(_ts_spec(ar=[0.7, 0.5]))
    assert "ar" in (e.value.locator or "")


def test_stationary_ar_accepted() -> None:
    spec = parse_spec(_ts_spec(ar=[0.7, 0.2]))  # sum|φ| = 0.9 < 1
    result = generate(spec, seed=1)
    assert "x" in result.frame.columns and len(result.frame) == 100


def test_nonpositive_period_rejected() -> None:
    # period has gt=0 at the model layer; parse_spec surfaces it as SpecValidationError.
    with pytest.raises(SpecValidationError):
        parse_spec(_ts_spec(seasonality=[{"amplitude": 1.0, "period": 0}]))


def test_timeseries_min_max_clamp_and_int_dtype() -> None:
    spec = parse_spec(
        _ts_spec(trend={"slope": 1.0, "intercept": 0.0}, noise_std=0.0, min=5, max=20, dtype="int")
    )
    x = generate(spec, seed=1).frame["x"].to_numpy()
    assert x.min() >= 5 and x.max() <= 20
    assert str(spec.features["x"].dtype) == "int"
    assert np.all(x == x.astype(np.int64))


# --- pipeline / determinism ----------------------------------------------------------


def test_timeseries_feature_not_compliance_assessed() -> None:
    # A trended, autocorrelated series is not a clean distribution draw → no KS/GoF.
    spec = parse_spec(_ts_spec(trend={"slope": 0.1, "intercept": 0.0}, noise_std=1.0))
    comp = generate(spec, seed=1).compliance
    assert comp.features == []  # timeseries has no `dist`, so it is skipped


def test_timeseries_can_drive_a_causal_child() -> None:
    spec = load_spec("examples/timeseries-sensor.datadoom.yaml")
    result = generate(spec, seed=7)
    df = result.frame
    assert list(df.columns) == ["temperature", "reading"]
    # reading ≈ 1.8·temperature + 5 (+ small noise) — recover the slope.
    b = np.polyfit(df["temperature"], df["reading"], 1)
    assert abs(b[0] - 1.8) < 0.05 and abs(b[1] - 5.0) < 0.5


def test_timeseries_run_is_byte_reproducible(tmp_path) -> None:
    spec = load_spec("examples/timeseries-sensor.datadoom.yaml")
    a = generate(spec, seed=7, out_dir=tmp_path / "a").artifacts[0].checksum_sha256
    b = generate(spec, seed=7, out_dir=tmp_path / "b").artifacts[0].checksum_sha256
    assert a == b
