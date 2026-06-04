"""ML-handling advice for the issues a column carries (exploratory guidance).

DataDoom knows *exactly* what it did to every column — which failure mode hit it,
the realized magnitude, and (for derived columns) how it was generated. This
module turns that ground truth into **actionable guidance for the engineer or
student who will model the data**: for each issue, a plain-language explanation,
the single best handling approach, and a short menu of concrete techniques.

This is static knowledge keyed on ``(mechanism, column type)`` plus the realized
magnitude — no randomness, no model fitting. It exists so the Results screen can
answer "what should I focus on, and how do I deal with it?" without the user
having to recognise an MNAR pattern from a histogram themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Severity ranks the urgency of an issue for someone building a model on the data.
# "critical" = will silently break the model (leakage); "high" = caps achievable
# performance or biases estimates if mishandled; "medium"/"low" = handle with care.
Severity = str  # "critical" | "high" | "medium" | "low"
_SEVERITY_RANK = {"critical": 3, "high": 2, "medium": 1, "low": 0}


@dataclass
class Issue:
    """One thing about a column an ML engineer should know and handle."""

    mode: str  # the failure mechanism ("mnar", "leakage", …) or "class_imbalance"
    title: str  # short headline ("Missing not at random")
    severity: Severity
    magnitude: str  # human-readable realized effect ("12.0% of values missing")
    explanation: str  # what the issue is, in plain language
    recommendation: str  # the single best way to handle it
    techniques: list[str] = field(default_factory=list)  # concrete options
    detail: dict[str, Any] = field(default_factory=dict)  # raw numbers for the UI

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "title": self.title,
            "severity": self.severity,
            "magnitude": self.magnitude,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "techniques": self.techniques,
            "detail": self.detail,
        }


# --- the knowledge base --------------------------------------------------------------
# Each entry is the fixed guidance for a mechanism. ``base_severity`` is escalated
# by realized magnitude in the builders below where it makes sense.

_GUIDE: dict[str, dict[str, Any]] = {
    "mcar": {
        "title": "Missing completely at random",
        "base_severity": "low",
        "explanation": (
            "Values are missing independently of every column, including their own "
            "value. This is the most benign kind of missingness: the observed rows "
            "stay a fair, unbiased sample of the data."
        ),
        "recommendation": (
            "Simple imputation is unbiased here. Use the median (numeric) or mode "
            "(categorical), or drop rows if the rate is small (<5%)."
        ),
        "techniques": [
            "Median/mean imputation for numeric columns",
            "Mode (most-frequent) imputation for categoricals",
            "Listwise row deletion — unbiased under MCAR when the rate is low",
        ],
    },
    "mar": {
        "title": "Missing at random",
        "base_severity": "medium",
        "explanation": (
            "Whether a value is missing depends on *other observed* columns, not on "
            "the missing value itself. Naive mean/median imputation biases the column "
            "because it ignores those drivers; conditioning on them fixes it."
        ),
        "recommendation": (
            "Use conditional, model-based imputation that learns from the observed "
            "drivers (e.g. IterativeImputer / MICE or KNN), not a global mean."
        ),
        "techniques": [
            "IterativeImputer (MICE) — regresses the column on the others",
            "KNN imputation on the correlated features",
            "Add a binary missingness-indicator feature alongside the imputed value",
            "Avoid plain mean/median imputation — it biases under MAR",
        ],
    },
    "mnar": {
        "title": "Missing not at random",
        "base_severity": "high",
        "explanation": (
            "Whether a value is missing depends on the *unobserved value itself* "
            "(e.g. high earners hide income). No imputation is unbiased without "
            "modelling the missingness mechanism — the missing rows are a skewed "
            "sample, so filling them in from the observed rows distorts the column."
        ),
        "recommendation": (
            "Treat missingness as informative: add an explicit missing-indicator "
            "feature (it is often predictive on its own) and avoid pretending the "
            "data is MCAR/MAR. Consider selection / pattern-mixture models."
        ),
        "techniques": [
            "Add a binary 'is-missing' indicator — frequently predictive itself",
            "Pattern-mixture or selection models for the missingness mechanism",
            "Domain-informed bounds instead of point imputation",
            "Run a sensitivity analysis over plausible imputed values",
        ],
    },
    "label_noise": {
        "title": "Label noise",
        "base_severity": "high",
        "explanation": (
            "A fraction of the target labels are wrong. This caps the accuracy any "
            "model can honestly reach and, with high-capacity models, gets memorised "
            "as if it were signal — hurting generalisation."
        ),
        "recommendation": (
            "Train with noise-robust losses and strong regularisation, and use "
            "confident-learning tools to find and prune likely-mislabelled rows."
        ),
        "techniques": [
            "Confident learning (e.g. cleanlab) to flag mislabelled rows",
            "Noise-robust losses (label smoothing, symmetric / MAE loss)",
            "Early stopping and regularisation to resist memorising errors",
            "Ensemble disagreement to surface suspect labels",
        ],
    },
    "feature_noise": {
        "title": "Feature measurement noise",
        "base_severity": "medium",
        "explanation": (
            "Additive measurement noise was injected into this feature, lowering its "
            "signal-to-noise ratio. Linear models will attenuate its coefficient "
            "(regression dilution); the feature looks weaker than it truly is."
        ),
        "recommendation": (
            "Prefer noise-tolerant models and regularisation; aggregate or smooth if "
            "repeated measurements exist for the same entity."
        ),
        "techniques": [
            "L2 regularisation to stabilise the attenuated coefficient",
            "Tree ensembles — more tolerant of feature noise than linear models",
            "Aggregate/denoise if multiple readings per entity are available",
            "Robust scaling so the noise does not dominate distance metrics",
        ],
    },
    "drift": {
        "title": "Distribution drift over row order",
        "base_severity": "medium",
        "explanation": (
            "This feature's distribution shifts across the dataset index (its "
            "early rows differ from its late rows). A random train/test split leaks "
            "the late regime into training and overstates real-world performance."
        ),
        "recommendation": (
            "Split by row/time order rather than randomly, and validate on the later "
            "regime. Detrend the feature or add the time index as a feature."
        ),
        "techniques": [
            "Time-ordered train/test split (do not shuffle)",
            "Detrend / difference the feature to remove the systematic shift",
            "Add the row index or timestamp as an explicit feature",
            "Rolling or periodic retraining for a deployed model",
        ],
    },
    "covariate_shift": {
        "title": "Covariate shift",
        "base_severity": "medium",
        "explanation": (
            "This feature's marginal distribution was moved away from the original "
            "(train ≠ deployment distribution) while its relationship to the label is "
            "preserved. Models tuned on the original distribution mis-calibrate."
        ),
        "recommendation": (
            "Re-weight training rows by the density ratio (importance weighting), or "
            "re-standardise using deployment statistics, and validate on the shifted "
            "distribution."
        ),
        "techniques": [
            "Importance weighting via density-ratio estimation",
            "Domain-adaptation methods",
            "Re-standardise the feature using deployment-time statistics",
            "Validate explicitly on the shifted distribution",
        ],
    },
    "leakage": {
        "title": "Target leakage",
        "base_severity": "critical",
        "explanation": (
            "This column is a near-perfect proxy for the target that would NOT be "
            "available at prediction time. It inflates offline metrics to look great "
            "and then collapses in production. This is leakage, not signal."
        ),
        "recommendation": (
            "Drop this column before training. If a single feature gives suspiciously "
            "high accuracy/AUROC, treat it as leakage until proven otherwise."
        ),
        "techniques": [
            "Remove the leaking column from the feature set",
            "Audit all features for ones derived from the target",
            "Be suspicious of any single feature with near-perfect predictive power",
        ],
    },
    "class_imbalance": {
        "title": "Class imbalance",
        "base_severity": "medium",
        "explanation": (
            "The target classes are far from balanced. A model can score high "
            "accuracy by predicting the majority class while being useless on the "
            "minority class that usually matters most."
        ),
        "recommendation": (
            "Stop using raw accuracy — evaluate with PR-AUC / F1 / recall on the "
            "minority class, and rebalance via class weights or resampling."
        ),
        "techniques": [
            "Class weights (e.g. class_weight='balanced')",
            "Resampling: SMOTE / oversample minority or undersample majority",
            "Stratified train/test splitting and cross-validation",
            "Evaluate with PR-AUC, F1, recall — not accuracy",
            "Tune the decision threshold rather than defaulting to 0.5",
        ],
    },
}


def _escalate(base: Severity, fraction: float | None) -> Severity:
    """Bump severity up one tier when a corruption rate is large."""
    if fraction is None:
        return base
    if fraction >= 0.30:
        return _bump(base, 2)
    if fraction >= 0.15:
        return _bump(base, 1)
    return base


def _bump(sev: Severity, by: int) -> Severity:
    rank = min(3, _SEVERITY_RANK.get(sev, 1) + by)
    for name, value in _SEVERITY_RANK.items():
        if value == rank:
            return name
    return sev


def build_issue(
    mode: str, *, magnitude: str, fraction: float | None = None, detail: dict[str, Any] | None = None
) -> Issue:
    """Assemble the guidance :class:`Issue` for a mechanism + realized magnitude.

    ``fraction`` (a corruption rate in [0, 1]) escalates the base severity for
    rate-like mechanisms; pass ``None`` for mechanisms where rate is irrelevant.
    Unknown mechanisms fall back to a generic medium-severity entry so a new
    plugin failure mode still renders coherently.
    """
    guide = _GUIDE.get(mode)
    if guide is None:
        return Issue(
            mode=mode,
            title=mode.replace("_", " ").title(),
            severity="medium",
            magnitude=magnitude,
            explanation=f"Column was modified by the {mode!r} mechanism.",
            recommendation="Inspect the realized effect and handle accordingly.",
            techniques=[],
            detail=detail or {},
        )
    return Issue(
        mode=mode,
        title=guide["title"],
        severity=_escalate(guide["base_severity"], fraction),
        magnitude=magnitude,
        explanation=guide["explanation"],
        recommendation=guide["recommendation"],
        techniques=list(guide["techniques"]),
        detail=detail or {},
    )


def severity_rank(sev: Severity) -> int:
    """Numeric rank for sorting issues by urgency (higher = more urgent)."""
    return _SEVERITY_RANK.get(sev, 1)
