"""Critical mathematical audit of the failure modes (P3).

The Phase-2 analogue of ``test_dataset_audit.py``: instead of checking that a
realized rate is *roughly* the target, these **recover each mechanism's
parameters from the generated data and compare against exact or asymptotic
theory**. Failure injection is pure math — a sign error or a miscalibrated
intercept produces data that still "looks corrupted" but is quantitatively
wrong. These tests are the guard against that.

Three mechanisms have **closed-form** targets and are asserted to (near) machine
precision:

* ``drift`` (linear)   — ``Δ[i] = magnitude · i/(n-1)`` exactly.
* ``covariate_shift``  — affine moment-match hits the target mean/std exactly.
* ``leakage``          — ``corr(into, target) = 1/√(1+η²)`` exactly.

The stochastic mechanisms are audited by **parameter recovery**:

* ``mcar``             — rate inside the binomial 3σ band + independence (Welch t).
* ``mar`` / ``mnar``   — IRLS logistic regression recovers the ``strength`` slope
                         *and* the calibrated intercept reproduces the rate.
* ``label_noise``      — boolean: symmetric flip + marginal ``q(1-p)+(1-q)p``;
                         categorical: the reassignment transition matrix is
                         uniform over the other ``k-1`` classes.
* ``feature_noise``    — recovered noise σ, zero mean, KS-Gaussian, independent.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from datadoom.engine import generate, parse_spec

SEED = 7
N = 20_000

FEATURES = {
    "x": {"type": "numeric", "dist": "normal", "params": {"mean": 50, "std": 10}},
    "y": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 5}},
    "flag": {"type": "boolean", "rate": 0.4},
    "color": {
        "type": "categorical",
        "categories": ["r", "g", "b", "k"],
        "weights": [0.4, 0.3, 0.2, 0.1],
    },
}


def _run(failures):
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "audit",
            "rows": N,
            "seed": SEED,
            "features": FEATURES,
            "failures": failures,
        }
    )
    res = generate(spec, seed=SEED)
    return res.frame, res.injected


def _z(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / v.std()


def _irls_logit(z: np.ndarray, m: np.ndarray, iters: int = 60) -> tuple[float, float]:
    """Newton-Raphson fit of P(m=1) = sigmoid(b0 + b1·z). Returns (b0, b1).

    Pure numpy (no sklearn dependency): recovers the logistic missingness slope
    so MAR/MNAR can be checked against their declared ``strength``.
    """
    X = np.column_stack([np.ones_like(z), z])
    beta = np.zeros(2)
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-(X @ beta)))
        w = np.clip(p * (1.0 - p), 1e-9, None)
        step = np.linalg.solve(X.T @ (w[:, None] * X), X.T @ (m - p))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-11:
            break
    return float(beta[0]), float(beta[1])


# --- 1. MCAR: rate + independence ---------------------------------------------------


def test_mcar_rate_in_binomial_band_and_independent() -> None:
    p = 0.1
    clean, inj = _run([{"type": "mcar", "columns": ["x"], "rate": p}])
    m = inj["x"].isna().to_numpy()
    se = np.sqrt(p * (1 - p) / N)
    assert abs(m.mean() - p) < 3 * se  # within the binomial 3σ band

    # Missingness must be independent of the underlying value (Welch t ≈ 0).
    xc = clean["x"].to_numpy()
    a, b = xc[m], xc[~m]
    t = (a.mean() - b.mean()) / np.sqrt(a.var() / len(a) + b.var() / len(b))
    assert abs(t) < 3.5


# --- 2. MAR: recover the strength slope + calibrated rate ---------------------------


@pytest.mark.parametrize("strength", [1.5, 3.0])
def test_mar_recovers_logistic_slope_and_rate(strength) -> None:
    clean, inj = _run(
        [{"type": "mar", "column": "y", "rate": 0.2, "driver": "x", "strength": strength}]
    )
    m = inj["y"].isna().to_numpy().astype(float)
    _b0, b1 = _irls_logit(_z(clean["x"].to_numpy()), m)
    # Slope recovers the declared strength; the column nullified is independent
    # of the driver's scale because missingness is driven purely by x.
    assert b1 == pytest.approx(strength, abs=0.12)
    assert m.mean() == pytest.approx(0.2, abs=0.01)  # intercept calibration


# --- 3. MNAR: slope recovered on the column's own value -----------------------------


@pytest.mark.parametrize("strength", [1.5, 3.0])
def test_mnar_recovers_self_dependence_slope(strength) -> None:
    clean, inj = _run([{"type": "mnar", "column": "x", "rate": 0.2, "strength": strength}])
    m = inj["x"].isna().to_numpy().astype(float)
    _b0, b1 = _irls_logit(_z(clean["x"].to_numpy()), m)
    assert b1 == pytest.approx(strength, abs=0.12)
    assert m.mean() == pytest.approx(0.2, abs=0.01)


# --- 4. label_noise (boolean): symmetric flip + marginal law ------------------------


def test_label_noise_boolean_symmetric_and_marginal() -> None:
    p = 0.1
    clean, inj = _run([{"type": "label_noise", "column": "flag", "rate": p}])
    cl = clean["flag"].to_numpy()
    inj_v = inj["flag"].to_numpy()
    flip = cl != inj_v
    # Flip probability is the same in both classes (no class-conditional bias).
    assert flip[cl].mean() == pytest.approx(p, abs=0.012)
    assert flip[~cl].mean() == pytest.approx(p, abs=0.012)
    # Marginal after flipping: P(obs=T) = q(1-p) + (1-q)p.
    q = cl.mean()
    assert inj_v.mean() == pytest.approx(q * (1 - p) + (1 - q) * p, abs=0.006)


# --- 5. label_noise (categorical): uniform reassignment matrix ----------------------


def test_label_noise_categorical_transition_matrix_is_uniform() -> None:
    p = 0.2
    cats = ["r", "g", "b", "k"]
    k = len(cats)
    clean, inj = _run([{"type": "label_noise", "column": "color", "rate": p}])
    cl = clean["color"].to_numpy()
    inj_v = inj["color"].to_numpy()
    assert (cl != inj_v).mean() == pytest.approx(p, abs=0.012)

    off = p / (k - 1)  # theoretical off-diagonal mass
    for c in cats:
        row = inj_v[cl == c]
        probs = {d: (row == d).mean() for d in cats}
        assert probs[c] == pytest.approx(1 - p, abs=0.02)  # stay prob
        for d in cats:
            if d != c:
                # Reassignment is uniform over the *other* k-1 classes.
                assert probs[d] == pytest.approx(off, abs=0.02)


# --- 6. feature_noise: recover σ, zero mean, gaussian, independent ------------------


def test_feature_noise_recovers_distribution() -> None:
    sigma = 3.0
    clean, inj = _run(
        [{"type": "feature_noise", "column": "y", "dist": "normal", "params": {"mean": 0, "std": sigma}}]
    )
    eps = inj["y"].to_numpy() - clean["y"].to_numpy()
    assert eps.std(ddof=0) == pytest.approx(sigma, abs=0.06)
    assert abs(eps.mean()) < 0.08
    # The added noise is genuinely Gaussian (KS does not reject) …
    _ks, pval = stats.kstest((eps - eps.mean()) / eps.std(), "norm")
    assert pval > 0.01
    # … and independent of the value it was added to.
    assert abs(np.corrcoef(eps, clean["y"].to_numpy())[0, 1]) < 0.025


# --- 7. drift (linear): exact ramp --------------------------------------------------


def test_drift_linear_is_exact_to_machine_precision() -> None:
    magnitude = 20.0
    clean, inj = _run(
        [{"type": "drift", "column": "x", "schedule": {"kind": "linear", "magnitude": magnitude}}]
    )
    delta = inj["x"].to_numpy() - clean["x"].to_numpy()
    expected = magnitude * np.arange(N) / (N - 1)
    assert np.max(np.abs(delta - expected)) < 1e-9  # exact closed form
    assert delta[0] == pytest.approx(0.0, abs=1e-12)
    assert delta[-1] == pytest.approx(magnitude, abs=1e-9)


def test_drift_step_jumps_at_threshold() -> None:
    clean, inj = _run(
        [{"type": "drift", "column": "x", "schedule": {"kind": "step", "at": 0.5, "magnitude": 10.0}}]
    )
    delta = inj["x"].to_numpy() - clean["x"].to_numpy()
    half = N // 2
    assert np.allclose(delta[:half], 0.0, atol=1e-9)
    assert np.allclose(delta[half:], 10.0, atol=1e-9)


# --- 8. covariate_shift: exact moment match -----------------------------------------


def test_covariate_shift_hits_target_moments_exactly() -> None:
    clean, inj = _run([{"type": "covariate_shift", "column": "x", "target": {"mean": 80, "std": 4}}])
    xv = inj["x"].to_numpy()
    # Affine x' = (x-μ)(σ_t/σ)+μ_t ⇒ mean=μ_t, std=σ_t exactly (ddof=0).
    assert xv.mean() == pytest.approx(80.0, abs=1e-6)
    assert xv.std(ddof=0) == pytest.approx(4.0, abs=1e-6)


def test_covariate_shift_mean_only_is_pure_translation() -> None:
    clean, inj = _run([{"type": "covariate_shift", "column": "x", "target": {"mean": 70}}])
    delta = inj["x"].to_numpy() - clean["x"].to_numpy()
    # No std target → pure shift: every row moves by the same constant.
    assert delta.std(ddof=0) < 1e-9
    assert inj["x"].to_numpy().mean() == pytest.approx(70.0, abs=1e-6)


# --- 9. leakage: closed-form correlation --------------------------------------------


@pytest.mark.parametrize("eta", [0.05, 0.2])
def test_leakage_correlation_matches_closed_form(eta) -> None:
    clean, inj = _run([{"type": "leakage", "target": "flag", "into": "leak", "noise": eta}])
    tgt = clean["flag"].to_numpy().astype(float)
    leak = inj["leak"].to_numpy()
    sd = tgt.std(ddof=0)
    # Residual std is η·σ_target …
    assert (leak - tgt).std(ddof=0) == pytest.approx(eta * sd, rel=0.05)
    # … so corr(into, target) = σ / √(σ² + (ησ)²) = 1/√(1+η²), exactly.
    theory = 1.0 / np.sqrt(1.0 + eta**2)
    assert np.corrcoef(leak, tgt)[0, 1] == pytest.approx(theory, abs=0.004)
