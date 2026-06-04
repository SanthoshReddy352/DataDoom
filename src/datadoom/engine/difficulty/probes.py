"""Baseline probe models for difficulty calibration (05 §5.1, 17 step 15).

Difficulty is defined *operationally*: a dataset is "as hard as" the score a
standard baseline model achieves on it. A :class:`ProbeModel` trains a baseline
classifier on a seeded train split and reports the task metric on the holdout —
AUROC for binary classification. The probe never refits or "helps" the data; it
just measures how separable the label is from the features (honest statistics,
invariant #3).

scikit-learn powers the estimators. The probe metric drives the adaptive loop's
knob selection, so it sits on the determinism-critical path — every estimator is
either intrinsically deterministic (lbfgs logistic regression) or seeded
(decision tree, train/test split). Same `(spec_hash, seed)` on the pinned
environment → identical metric → identical calibrated bytes (invariant #6).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

# Object columns with more distinct values than this are treated as free-text /
# id-like and dropped from the probe design matrix (one-hot would explode).
_MAX_CATEGORY_CARDINALITY = 50
_TEST_SIZE = 0.3


@dataclass
class ProbeResult:
    """What a probe measured on one realized frame."""

    metric: float  # the task metric the band targets (AUROC for binary)
    metric_name: str  # "auroc"
    task: str  # "classification"
    linear_separability: float  # holdout accuracy of a linear probe (05 §5.4)
    class_balance: float  # fraction of the positive class
    n_features: int  # design-matrix width actually fed to the probe

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "metric_name": self.metric_name,
            "task": self.task,
            "linear_separability": self.linear_separability,
            "class_balance": self.class_balance,
            "n_features": self.n_features,
        }


class ProbeModel(ABC):
    """A baseline model whose holdout score *defines* the dataset's difficulty."""

    name: str
    # Optional JSON-schema fragment for probe options (09 §6); ``None`` for built-ins.
    param_schema: Mapping[str, Any] | None = None

    @abstractmethod
    def estimator(self, seed: int) -> Any:
        """Return a fresh scikit-learn classifier exposing ``predict_proba``."""


class LogRegProbe(ProbeModel):
    name = "logreg"

    def estimator(self, seed: int) -> Any:
        # lbfgs is deterministic given the data; no random_state needed.
        return LogisticRegression(max_iter=1000)


class TreeProbe(ProbeModel):
    name = "tree"

    def estimator(self, seed: int) -> Any:
        # Depth-capped so it stays a *baseline*, not a memorizer; seeded for repro.
        return DecisionTreeClassifier(max_depth=8, random_state=seed)


PROBES: dict[str, ProbeModel] = {p.name: p for p in (LogRegProbe(), TreeProbe())}


def _encode_label(series: pd.Series) -> tuple[np.ndarray, int]:
    """Map a classification label to 0/1 codes; return (codes, n_classes).

    The positive class is the lexicographically larger category (so booleans map
    True→1) — a stable convention so AUROC orientation is reproducible.
    """
    if pd.api.types.is_bool_dtype(series):
        return series.to_numpy().astype(int), 2
    codes, uniques = pd.factorize(series, sort=True)
    return codes.astype(int), len(uniques)


def _design_matrix(frame: pd.DataFrame, label: str) -> tuple[np.ndarray, list[str]]:
    """Build a numeric feature matrix from every column except the label.

    Numeric/boolean columns pass through (median-imputed); low-cardinality
    categoricals are one-hot encoded; datetimes become ordinals; free-text /
    high-cardinality columns are dropped (uninformative to a baseline probe).
    """
    parts: list[pd.DataFrame] = []
    for col in frame.columns:
        if col == label:
            continue
        s = frame[col]
        if pd.api.types.is_bool_dtype(s):
            parts.append(s.astype(float).to_frame(col))
        elif pd.api.types.is_numeric_dtype(s):
            filled = s.astype(float)
            median = filled.median()
            parts.append(filled.fillna(0.0 if pd.isna(median) else median).to_frame(col))
        elif pd.api.types.is_datetime64_any_dtype(s):
            parts.append(s.astype("int64").astype(float).to_frame(col))
        else:  # object / categorical
            if s.nunique(dropna=True) <= _MAX_CATEGORY_CARDINALITY:
                dummies = pd.get_dummies(s, prefix=col, dummy_na=False, dtype=float)
                if dummies.shape[1] > 0:
                    parts.append(dummies)
    if not parts:
        return np.empty((len(frame), 0), dtype=float), []
    design = pd.concat(parts, axis=1)
    return design.to_numpy(dtype=float), list(design.columns)


def evaluate(
    probe: ProbeModel,
    frame: pd.DataFrame,
    label: str,
    *,
    split_seed: int,
    est_seed: int,
) -> ProbeResult:
    """Train ``probe`` on a seeded split and score it on the holdout (05 §5.1).

    Binary classification only in v0.1: returns holdout AUROC. Degenerate cases
    (no usable features, a single realized class) score at chance (0.5) — honest
    "no signal" rather than a misleading number or a crash.
    """
    X, feat_names = _design_matrix(frame, label)
    y, _ = _encode_label(frame[label])
    n_features = X.shape[1]
    positive_rate = float(np.mean(y == 1)) if len(y) else 0.0

    classes = np.unique(y)
    if n_features == 0 or classes.size < 2:
        # Nothing to learn from, or label collapsed to one class → chance.
        return ProbeResult(0.5, "auroc", "classification", 0.5, positive_rate, n_features)

    # Stratify only when every class can appear on both sides of the split.
    counts = np.bincount(y)
    stratify = y if counts.min() >= 2 else None
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=_TEST_SIZE, random_state=split_seed, stratify=stratify
    )
    if np.unique(y_te).size < 2 or np.unique(y_tr).size < 2:
        return ProbeResult(0.5, "auroc", "classification", 0.5, positive_rate, n_features)

    scaler = StandardScaler().fit(X_tr)
    X_tr_s = scaler.transform(X_tr)
    X_te_s = scaler.transform(X_te)

    model = probe.estimator(est_seed)
    model.fit(X_tr_s, y_tr)
    proba = model.predict_proba(X_te_s)[:, 1]
    auroc = float(roc_auc_score(y_te, proba))

    # Linear-separability reference (05 §5.4): a plain logistic probe's holdout
    # accuracy, regardless of which probe scored the AUROC.
    linear = LogisticRegression(max_iter=1000).fit(X_tr_s, y_tr)
    lin_acc = float(accuracy_score(y_te, linear.predict(X_te_s)))

    return ProbeResult(auroc, "auroc", "classification", lin_acc, positive_rate, n_features)
