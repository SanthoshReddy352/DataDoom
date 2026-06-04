"""End-to-end dataset audits: does a *generated* dataset match its spec?

These mirror, in permanent test form, the manual "generate then analyze" audit
we run on the examples. Unlike ``test_dist_correctness.py`` (which exercises the
samplers in isolation), these drive the **whole pipeline** on the shipped example
specs and assert every declared property holds in the realized frame:

* non-causal ``tabular-basic`` — each feature matches its requested distribution
  (moments, bounds, categorical weights, boolean rate, datetime range, text len),
  and KS-applicability is reported honestly (continuous/float/un-clamped only).
* causal ``causal-fraud`` — the structural equations are recovered from the data
  (OLS coefficients, noise scale, logistic calibration, correlation signs).

If a logic/arithmetic bug slipped into sampling, clamping, dtype casting, the SEM
walk, or compliance scoring, one of these end-to-end assertions fails.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from datadoom.engine import generate, load_spec

REPO = Path(__file__).resolve().parents[2]
TABULAR_BASIC = REPO / "examples" / "tabular-basic.datadoom.yaml"
CAUSAL_FRAUD = REPO / "examples" / "causal-fraud.datadoom.yaml"
SEED = 42


# --- non-causal (distribution-only) dataset -----------------------------------------


@pytest.fixture(scope="module")
def basic():
    return generate(load_spec(str(TABULAR_BASIC)), seed=SEED)


def test_basic_shape_and_columns(basic) -> None:
    df = basic.frame
    assert len(df) == 5000
    assert list(df.columns) == [
        "age", "income", "visits", "education", "is_member", "signup_date", "note"
    ]


def test_basic_age_normal_clamped_int(basic) -> None:
    age = basic.frame["age"].to_numpy()
    assert str(basic.frame["age"].dtype).startswith("int")  # dtype: int
    assert np.all(age == age.astype(np.int64))
    assert age.min() >= 18 and age.max() <= 90  # clamp [18, 90]
    # Clamp at 18 (~1.8σ) lifts the mean slightly and shrinks the std vs N(40,12).
    assert 39.0 <= age.mean() <= 42.0
    assert 10.0 <= age.std(ddof=1) <= 12.5


def test_basic_income_lognormal_moments(basic) -> None:
    # lognormal(mu=10.5, sigma=0.4): median=exp(mu), mean=exp(mu + sigma^2/2).
    income = basic.frame["income"].to_numpy()
    assert (income > 0).all()  # lognormal support is (0, inf)
    assert np.median(income) == pytest.approx(np.exp(10.5), rel=0.06)
    assert income.mean() == pytest.approx(np.exp(10.5 + 0.4**2 / 2), rel=0.08)


def test_basic_visits_poisson_mean_var(basic) -> None:
    visits = basic.frame["visits"].to_numpy()
    assert str(basic.frame["visits"].dtype).startswith("int")
    assert (visits >= 0).all()
    assert visits.mean() == pytest.approx(3.0, abs=0.2)   # lam = 3
    assert visits.var() == pytest.approx(3.0, abs=0.5)    # Poisson: mean == var


def test_basic_education_weighted_proportions(basic) -> None:
    edu = basic.frame["education"]
    n = len(edu)
    props = {c: (edu == c).sum() / n for c in ("hs", "college", "grad")}
    assert props["hs"] == pytest.approx(0.5, abs=0.03)
    assert props["college"] == pytest.approx(0.4, abs=0.03)
    assert props["grad"] == pytest.approx(0.1, abs=0.02)


def test_basic_is_member_boolean_rate(basic) -> None:
    member = basic.frame["is_member"]
    assert member.dtype == bool
    assert member.mean() == pytest.approx(0.3, abs=0.03)  # rate: 0.3


def test_basic_signup_date_within_bounds(basic) -> None:
    dates = pd.to_datetime(basic.frame["signup_date"])
    assert dates.min() >= pd.Timestamp("2023-01-01")
    assert dates.max() <= pd.Timestamp("2024-12-31")
    # Day granularity: no sub-day component.
    assert (dates.dt.normalize() == dates).all()


def test_basic_note_token_length(basic) -> None:
    counts = basic.frame["note"].map(lambda s: len(s.split()))
    assert counts.min() >= 5 and counts.max() <= 20  # length {min: 5, max: 20}


def test_basic_compliance_applicability_is_honest(basic) -> None:
    comp = basic.compliance
    by_name = {f.feature: f for f in comp.features}
    # Only features with a `dist` are assessed; derived/non-numeric are skipped.
    assert set(by_name) == {"age", "income", "visits"}
    # age (int + clamp) and visits (discrete poisson) are judged by a chi-square
    # GoF against the effective PMF; income (continuous lognormal, unclamped) by
    # KS. All three are assessable, and a correct generator passes each.
    assert by_name["age"].test == "chi2_gof" and by_name["age"].applicable is True
    assert by_name["visits"].test == "chi2_gof" and by_name["visits"].applicable is True
    assert by_name["income"].test == "ks" and by_name["income"].applicable is True
    assert by_name["age"].passed is True and by_name["visits"].passed is True
    d = comp.to_dict()
    assert d["assessed_features"] == 3 and d["applicable_features"] == 3
    # A correct generator lands at a full pass rate.
    assert comp.score == 1.0


def test_basic_is_reproducible() -> None:
    a = generate(load_spec(str(TABULAR_BASIC)), seed=SEED).frame
    b = generate(load_spec(str(TABULAR_BASIC)), seed=SEED).frame
    assert a.equals(b)


# --- causal dataset (end-to-end, on the shipped example) ----------------------------


@pytest.fixture(scope="module")
def fraud():
    return generate(load_spec(str(CAUSAL_FRAUD)), seed=SEED)


def test_fraud_income_recovers_structural_coefficients(fraud) -> None:
    # income = 800*age + 10000 + map(education) + N(0, 5000).
    df = fraud.frame
    age = df["age"].to_numpy(dtype=float)
    edu_contrib = df["education"].map({"hs": 0.0, "college": 15000.0, "grad": 40000.0}).to_numpy()
    income = df["income"].to_numpy()
    X = np.column_stack([np.ones(len(df)), age, edu_contrib])
    bias, age_w, edu_w = np.linalg.lstsq(X, income, rcond=None)[0]
    assert age_w == pytest.approx(800, abs=15)
    assert bias == pytest.approx(10000, abs=400)
    assert edu_w == pytest.approx(1.0, abs=0.05)
    resid = income - (10000 + 800 * age + edu_contrib)
    assert resid.std(ddof=1) == pytest.approx(5000, rel=0.05)  # noise scale


def test_fraud_is_fraud_logistic_calibration(fraud) -> None:
    # is_fraud ~ Bernoulli(sigmoid(-0.00002*income + 1.0)); empirical rate per
    # theoretical-probability bin should track the diagonal.
    df = fraud.frame
    income = df["income"].to_numpy()
    p = 1.0 / (1.0 + np.exp(-(-0.00002 * income + 1.0)))
    fraud_flag = df["is_fraud"].to_numpy().astype(float)
    assert fraud_flag.mean() == pytest.approx(p.mean(), abs=0.03)
    # corr(income, is_fraud) must be negative (logistic weight < 0).
    assert np.corrcoef(income, fraud_flag)[0, 1] < 0


def test_fraud_report_has_true_graph_and_mi(fraud) -> None:
    truth = fraud.report.causal_truth
    assert truth is not None
    edges = {(e["from"], e["to"]) for e in truth["edges"]}
    assert edges == {("age", "income"), ("education", "income"), ("income", "is_fraud")}
    order = truth["topological_order"]
    assert order.index("age") < order.index("income") < order.index("is_fraud")
    assert fraud.report.mutual_information is not None
