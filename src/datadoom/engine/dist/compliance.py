"""Honest statistical compliance reporting (05 §2.2-2.3, §7).

We report how well the realized sample matches the *requested* distribution via
a Kolmogorov-Smirnov test. We deliberately do NOT refit parameters to the
sample: the ~alpha fraction of KS "failures" at significance alpha is expected
sampling variance, not a defect. Refitting would make the data match itself
rather than the user's request.

**KS applicability.** A one-sample KS test is only valid for a *continuous*,
*untransformed* target. When a feature is integer (``dtype: int`` discretizes a
continuous draw), drawn from a discrete distribution (e.g. poisson), or
``min``/``max``-clamped (truncation introduces point masses at the bounds), the
realized data is no longer a clean draw from the continuous CDF, so the KS
p-value is not a meaningful pass/fail signal — at large *n* it rejects on the
transform artifact, not on any defect. For those features we still compute and
report the KS statistic and the empirical moments (which *do* track the target),
but mark the result ``applicable: False`` and exclude it from the compliance
score. This avoids the false-negative where a correct generator scores 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy import stats

from .builtins import REGISTRY

DEFAULT_ALPHA = 0.05

# Distributions whose support is discrete: a continuous KS test does not apply.
DISCRETE_DISTS = {"poisson"}


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
        }


@dataclass
class ComplianceReport:
    alpha: float
    features: list[FeatureCompliance] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Fraction of *KS-applicable* features whose p-value exceeds alpha.

        Features where a continuous KS test does not apply (integer/discrete/
        clamped — see module docstring) are excluded so a correct generator is
        never penalized for a transform we deliberately applied. With no
        applicable features there is nothing to contradict, so the score is 1.0.
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


def _ks_applicability(dist_name: str, dtype: str, clamped_fraction: float) -> tuple[bool, str | None]:
    """Decide whether a continuous KS test is a valid compliance signal here."""
    reasons: list[str] = []
    if dist_name in DISCRETE_DISTS:
        reasons.append("discrete distribution")
    if dtype == "int":
        reasons.append("integer discretization")
    if clamped_fraction > 0:
        reasons.append(f"clamping ({clamped_fraction:.1%})")
    if not reasons:
        return True, None
    return False, (
        "continuous KS not applicable (" + ", ".join(reasons) + "); "
        "compare empirical vs target moments instead"
    )


def assess_numeric(
    feature: str,
    dist_name: str,
    params: dict[str, float],
    values: np.ndarray,
    clamped_fraction: float = 0.0,
    alpha: float = DEFAULT_ALPHA,
    dtype: str = "float",
) -> FeatureCompliance:
    """Assess a realized numeric sample against its requested distribution.

    A one-sample KS test is computed for transparency in all cases, but it only
    counts toward the compliance score when it is statistically valid (continuous
    distribution, float dtype, no clamping). See the module docstring.
    """
    dist = REGISTRY[dist_name]
    data = np.asarray(values, dtype=float)

    ks_stat, p_value = stats.kstest(data, lambda x: dist.cdf(x, params))
    applicable, note = _ks_applicability(dist_name, dtype, clamped_fraction)

    empirical = {
        "mean": float(np.mean(data)),
        "std": float(np.std(data, ddof=1)) if data.size > 1 else 0.0,
        "min": float(np.min(data)),
        "max": float(np.max(data)),
    }
    return FeatureCompliance(
        feature=feature,
        dist=dist_name,
        target_params=dict(params),
        empirical=empirical,
        ks_statistic=float(ks_stat),
        p_value=float(p_value),
        passed=bool(p_value > alpha) if applicable else None,
        clamped_fraction=float(clamped_fraction),
        applicable=applicable,
        note=note,
    )
