"""Honest statistical compliance reporting (05 §2.2-2.3, §7).

We report how well the realized sample matches the *requested* distribution. We
deliberately do NOT refit parameters to the sample: the ~alpha fraction of
"failures" at significance alpha is expected sampling variance, not a defect.
Refitting would make the data match itself rather than the user's request.

**Two complementary tests, picked by feature shape.**

*Continuous, untransformed targets* → a one-sample **Kolmogorov-Smirnov** test
against the requested CDF. This is the right tool when the realized data really
is a clean draw from a continuous distribution (e.g. ``normal``/``lognormal``
with ``dtype: float`` and no clamping).

*Integer, discrete, or clamped targets* → a **chi-square goodness-of-fit** test
against the **effective** PMF (the distribution actually realized after the
transform). A KS test is invalid here: ``dtype: int`` discretizes a continuous
draw, a discrete distribution (poisson) lives on the integers, and ``min``/
``max`` clamping piles point masses at the bounds — so the realized data is no
longer a clean draw from the continuous CDF, and at large *n* a KS test rejects
on the *transform artifact*, not on any defect. The GoF test instead compares
binned counts to the effective PMF, where the end bins absorb the (possibly
clamped) tail mass:

* interior integer bin ``k``  → ``P = F(k + ½) − F(k − ½)``
* min bin                      → ``P = F(kmin + ½)``       (absorbs the lower tail)
* max bin                      → ``P = 1 − F(kmax − ½)``   (absorbs the upper tail)

For a discrete CDF the ``±½`` edges coincide with the integer steps, so the same
formula yields the exact PMF (``F(k) − F(k−1)``). Bins whose expected count falls
below :data:`MIN_EXPECTED_COUNT` are merged with a neighbour (Cochran's rule) so
the chi-square approximation holds. Degrees of freedom are ``bins − 1`` — we
subtract **nothing** for fitted parameters because the parameters come from the
spec, not from the data.

This turns the previous honest *abstention* (``applicable: False``, scored
``n/a``) into an actual validated pass/fail for the most common real-world
feature shapes — ages, counts, bounded scores — while never penalizing a correct
generator for a transform we deliberately applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from .base import Distribution
from .builtins import REGISTRY

DEFAULT_ALPHA = 0.05

# Distributions whose support is discrete: a continuous KS test does not apply.
DISCRETE_DISTS = {"poisson"}

# Cochran's rule of thumb: keep every chi-square cell's expected count at or
# above this by merging sparse bins, so the asymptotic distribution holds.
MIN_EXPECTED_COUNT = 5.0

# Number of interior bins for the clamped-continuous goodness-of-fit test.
_CONTINUOUS_INTERIOR_BINS = 24

# Guard: refuse to enumerate an absurd integer range (degenerate spec).
_MAX_INTEGER_BINS = 200_000


@dataclass
class FeatureCompliance:
    feature: str
    dist: str
    target_params: dict[str, float]
    empirical: dict[str, float]
    ks_statistic: float
    p_value: float
    passed: bool | None
    clamped_fraction: float = 0.0
    applicable: bool = True
    note: str | None = None
    # Which test produced ``p_value``/``passed``: "ks", "chi2_gof", or "none"
    # (the last meaning no valid test could be formed — an honest abstention).
    test: str = "ks"
    # Chi-square goodness-of-fit detail (only when ``test == "chi2_gof"``).
    gof: dict[str, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "dist": self.dist,
            "target_params": self.target_params,
            "empirical": self.empirical,
            "ks_statistic": self.ks_statistic,
            "p_value": self.p_value,
            "passed": self.passed,
            "clamped_fraction": self.clamped_fraction,
            "applicable": self.applicable,
            "note": self.note,
            "test": self.test,
            "gof": self.gof,
        }


@dataclass
class ComplianceReport:
    alpha: float
    features: list[FeatureCompliance] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Fraction of *assessable* features whose fit test passes.

        A feature is assessable when some valid test (KS for continuous targets,
        chi-square GoF for integer/discrete/clamped targets) could be run for it.
        Features that abstain (``applicable: False`` — no valid test could be
        formed) are excluded so a correct generator is never penalized. With no
        assessable features there is nothing to contradict, so the score is 1.0.
        """
        applicable = [f for f in self.features if f.applicable]
        if not applicable:
            return 1.0
        return sum(1 for f in applicable if f.passed) / len(applicable)

    def to_dict(self) -> dict[str, Any]:
        return {
            "alpha": self.alpha,
            "compliance_score": self.score,
            "applicable_features": sum(1 for f in self.features if f.applicable),
            "assessed_features": len(self.features),
            "features": [f.to_dict() for f in self.features],
        }


def _needs_gof(dist_name: str, dtype: str, clamped_fraction: float) -> tuple[bool, list[str]]:
    """Decide whether a continuous KS test is invalid here (→ use a GoF test).

    Returns ``(needs_gof, reasons)``; an empty ``reasons`` means KS is valid.
    """
    reasons: list[str] = []
    if dist_name in DISCRETE_DISTS:
        reasons.append("discrete distribution")
    if dtype == "int":
        reasons.append("integer discretization")
    if clamped_fraction > 0:
        reasons.append(f"clamping ({clamped_fraction:.1%})")
    return bool(reasons), reasons


def _merge_sparse_bins(
    expected_p: np.ndarray, observed: np.ndarray, n: int
) -> tuple[np.ndarray, np.ndarray]:
    """Greedily merge adjacent bins left-to-right until each expected count is at
    least :data:`MIN_EXPECTED_COUNT`. Any sparse remainder folds into the last
    closed group. Deterministic given the inputs.
    """
    groups_p: list[float] = []
    groups_o: list[float] = []
    cur_p = 0.0
    cur_o = 0.0
    for p, o in zip(expected_p.tolist(), observed.tolist()):
        cur_p += p
        cur_o += o
        if cur_p * n >= MIN_EXPECTED_COUNT:
            groups_p.append(cur_p)
            groups_o.append(cur_o)
            cur_p = 0.0
            cur_o = 0.0
    if cur_p > 0 or cur_o > 0:  # leftover sparse tail
        if groups_p:
            groups_p[-1] += cur_p
            groups_o[-1] += cur_o
        else:
            groups_p.append(cur_p)
            groups_o.append(cur_o)
    return np.asarray(groups_p, dtype=float), np.asarray(groups_o, dtype=float)


def _chi_square(expected_p: np.ndarray, observed: np.ndarray, n: int) -> dict[str, float] | None:
    """Run a chi-square GoF on already-binned (expected prob, observed count).

    Merges sparse bins, then computes ``Σ (O − E)² / E`` with ``dof = bins − 1``
    (no parameters were fit). Returns ``None`` when fewer than two bins survive
    (no testable signal) or the total expected mass is degenerate.
    """
    total_p = float(expected_p.sum())
    if total_p <= 0:
        return None
    expected_p = expected_p / total_p  # guard tiny float drift so Σp == 1
    merged_p, merged_o = _merge_sparse_bins(expected_p, observed, n)
    if merged_p.size < 2:
        return None
    expected_counts = merged_p * n
    statistic = float(np.sum((merged_o - expected_counts) ** 2 / expected_counts))
    dof = int(merged_p.size - 1)
    p_value = float(stats.chi2.sf(statistic, dof))
    return {"statistic": statistic, "dof": float(dof), "bins": float(merged_p.size), "p_value": p_value}


def _integer_gof(dist: Distribution, params: dict[str, float], data: np.ndarray, n: int) -> dict[str, float] | None:
    """GoF for an integer-valued target (int dtype or a discrete distribution)."""
    ints = np.rint(data).astype(np.int64)
    kmin = int(ints.min())
    kmax = int(ints.max())
    if kmax - kmin + 1 > _MAX_INTEGER_BINS:
        return None
    ks = np.arange(kmin, kmax + 1)
    observed = np.bincount(ints - kmin, minlength=ks.size).astype(float)
    upper = dist.cdf(ks + 0.5, params)  # F(k + ½)
    lower = dist.cdf(ks - 0.5, params)  # F(k − ½)
    expected_p = np.asarray(upper, dtype=float) - np.asarray(lower, dtype=float)
    expected_p[0] = float(upper[0])           # min bin absorbs the lower tail
    expected_p[-1] = 1.0 - float(lower[-1])   # max bin absorbs the upper tail
    expected_p = np.clip(expected_p, 0.0, None)
    return _chi_square(expected_p, observed, n)


def _clamped_continuous_gof(
    dist: Distribution,
    params: dict[str, float],
    data: np.ndarray,
    n: int,
    clamp_min: float | None,
    clamp_max: float | None,
) -> dict[str, float] | None:
    """GoF for a continuous (float) target whose only transform is clamping.

    Clamping turns ``[min, max]`` into point masses: ``P(min) = F(min)`` and
    ``P(max) = 1 − F(max)``. The open interior is split into equal-width bins.
    """
    bins_p: list[float] = []
    bins_o: list[float] = []

    interior_lo = clamp_min if clamp_min is not None else float(data.min())
    interior_hi = clamp_max if clamp_max is not None else float(data.max())
    if not interior_hi > interior_lo:
        return None

    if clamp_min is not None:  # lower point mass P(min) = F(min)
        bins_p.append(float(dist.cdf(np.asarray([clamp_min]), params)[0]))
        bins_o.append(float(np.count_nonzero(data <= clamp_min)))

    edges = np.linspace(interior_lo, interior_hi, _CONTINUOUS_INTERIOR_BINS + 1)
    cdf_edges = np.asarray(dist.cdf(edges, params), dtype=float)
    if clamp_min is None:
        cdf_edges[0] = 0.0   # bottom interior bin absorbs the open lower tail
    if clamp_max is None:
        cdf_edges[-1] = 1.0  # top interior bin absorbs the open upper tail
    # Strictly-interior data (exact bounds already counted as point masses).
    interior_mask = data > interior_lo
    if clamp_max is not None:
        interior_mask &= data < interior_hi
    interior_o = np.histogram(data[interior_mask], bins=edges)[0].astype(float)
    bins_p.extend(np.diff(cdf_edges).tolist())
    bins_o.extend(interior_o.tolist())

    if clamp_max is not None:  # upper point mass P(max) = 1 − F(max)
        bins_p.append(1.0 - float(dist.cdf(np.asarray([clamp_max]), params)[0]))
        bins_o.append(float(np.count_nonzero(data >= clamp_max)))

    expected_p = np.clip(np.asarray(bins_p, dtype=float), 0.0, None)
    observed = np.asarray(bins_o, dtype=float)
    return _chi_square(expected_p, observed, n)


def assess_numeric(
    feature: str,
    dist_name: str,
    params: dict[str, float],
    values: np.ndarray,
    clamped_fraction: float = 0.0,
    alpha: float = DEFAULT_ALPHA,
    dtype: str = "float",
    clamp_min: float | None = None,
    clamp_max: float | None = None,
) -> FeatureCompliance:
    """Assess a realized numeric sample against its requested distribution.

    Continuous untransformed targets are judged by KS; integer/discrete/clamped
    targets by a chi-square goodness-of-fit against the effective PMF. The KS
    statistic is always reported for transparency. See the module docstring.
    """
    dist = REGISTRY[dist_name]
    data = np.asarray(values, dtype=float)

    ks_stat, ks_p = stats.kstest(data, lambda x: dist.cdf(x, params))
    empirical = {
        "mean": float(np.mean(data)),
        "std": float(np.std(data, ddof=1)) if data.size > 1 else 0.0,
        "min": float(np.min(data)),
        "max": float(np.max(data)),
    }

    needs_gof, reasons = _needs_gof(dist_name, dtype, clamped_fraction)

    # Decide which test rules, then construct one FeatureCompliance.
    p_value = float(ks_p)
    passed: bool | None = bool(ks_p > alpha)
    applicable = True
    test = "ks"
    note: str | None = None
    gof: dict[str, float] | None = None

    if needs_gof:
        why = ", ".join(reasons)
        # KS is not a valid signal here — run a goodness-of-fit test against the
        # effective (discretized/clamped) PMF instead.
        if dtype == "int" or dist_name in DISCRETE_DISTS:
            gof = _integer_gof(dist, params, data, data.size)
        else:  # continuous float whose only transform is clamping
            gof = _clamped_continuous_gof(dist, params, data, data.size, clamp_min, clamp_max)
        if gof is None:
            # No valid test could be formed (near-constant / too few bins) —
            # abstain honestly rather than emit a meaningless verdict.
            passed = None
            applicable = False
            test = "none"
            note = (
                f"continuous KS not applicable ({why}); goodness-of-fit "
                "abstained (too few distinct values to bin)"
            )
        else:
            p_value = float(gof["p_value"])
            passed = bool(gof["p_value"] > alpha)
            test = "chi2_gof"
            note = (
                f"chi-square goodness-of-fit vs the effective PMF "
                f"({int(gof['bins'])} bins, dof {int(gof['dof'])}); "
                f"KS not applicable ({why})"
            )

    return FeatureCompliance(
        feature=feature,
        dist=dist_name,
        target_params=dict(params),
        empirical=empirical,
        ks_statistic=float(ks_stat),
        p_value=p_value,
        passed=passed,
        clamped_fraction=float(clamped_fraction),
        applicable=applicable,
        note=note,
        test=test,
        gof=gof,
    )
