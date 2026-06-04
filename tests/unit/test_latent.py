"""Latent (hidden) features — ``emit: false`` (04 §4).

A latent feature is sampled / computed and may drive the SEM and the true causal
graph, but is **not shipped**: excluded from the output frame, the metadata
columns, compliance, and the difficulty probe. It models unobserved variables
(latent scores, hidden confounders). Adding the field must not change the hash of
a spec that doesn't use it.
"""

from __future__ import annotations

import numpy as np
import pytest

from datadoom.engine import generate, parse_spec
from datadoom.engine.errors import SpecValidationError


def _latent_label_spec(**difficulty):
    """A latent `score` drives a logistic boolean label from observable roots."""
    body = {
        "datadoom_version": "1",
        "name": "latent",
        "seed": 5,
        "rows": 3000,
        "features": {
            "x1": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "x2": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            "score": {"type": "numeric", "dtype": "float", "emit": False},
            "label": {"type": "boolean"},
        },
        "causal": {
            "edges": [
                {"from": "x1", "to": "score", "fn": "linear", "weight": 1.0},
                {"from": "x2", "to": "score", "fn": "linear", "weight": 1.0},
                {"from": "score", "to": "label", "fn": "logistic", "weight": 2.0, "bias": 0.0},
            ],
            "noise": {"score": {"dist": "none"}, "label": {"dist": "none"}},
        },
    }
    if difficulty:
        body["difficulty"] = {"label": "label", "probe": "logreg", **difficulty}
    return parse_spec(body)


def test_latent_excluded_from_output_but_drives_label() -> None:
    result = generate(_latent_label_spec(), seed=5)
    assert "score" not in result.frame.columns
    assert list(result.frame.columns) == ["x1", "x2", "label"]
    # The label still depends on the (hidden) score → correlated with x1+x2.
    s = result.frame["x1"].to_numpy() + result.frame["x2"].to_numpy()
    y = result.frame["label"].to_numpy().astype(float)
    assert abs(np.corrcoef(s, y)[0, 1]) > 0.3


def test_latent_present_in_true_causal_graph() -> None:
    truth = generate(_latent_label_spec(), seed=5).report.causal_truth
    assert "score" in (truth["nodes"] or [])  # the hidden node is in the truth
    assert any(e["from"] == "score" for e in truth["edges"])


def test_latent_excluded_from_compliance() -> None:
    # A latent *root* with a dist must not be assessed (it isn't shipped).
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "latent-root",
            "seed": 1,
            "rows": 2000,
            "features": {
                "hidden": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}, "emit": False},
                "obs": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}},
            },
        }
    )
    rep = generate(spec, seed=1).report
    assessed = {f["feature"] for f in rep.distribution["features"]}
    assert "hidden" not in assessed
    assert "obs" in assessed


def test_hidden_confounder_correlates_two_observables() -> None:
    # A hidden common cause makes two observed children correlate, with the
    # confounder itself absent from the data (classic latent confounding).
    spec = parse_spec(
        {
            "datadoom_version": "1",
            "name": "confounder",
            "seed": 3,
            "rows": 4000,
            "features": {
                "u": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}, "emit": False},
                "a": {"type": "numeric", "dtype": "float"},
                "b": {"type": "numeric", "dtype": "float"},
            },
            "causal": {
                "edges": [
                    {"from": "u", "to": "a", "fn": "linear", "weight": 1.0},
                    {"from": "u", "to": "b", "fn": "linear", "weight": 1.0},
                ],
                "noise": {"a": {"dist": "normal", "params": {"mean": 0, "std": 0.3}}, "b": {"dist": "normal", "params": {"mean": 0, "std": 0.3}}},
            },
        }
    )
    f = generate(spec, seed=3).frame
    assert "u" not in f.columns
    assert np.corrcoef(f["a"], f["b"])[0, 1] > 0.7  # confounded despite no edge a—b


def test_emit_field_is_hash_safe_when_unset() -> None:
    # A spec that doesn't set emit must not canonicalize the field (no hash drift).
    body = {
        "datadoom_version": "1",
        "name": "plain",
        "rows": 10,
        "features": {"x": {"type": "numeric", "dist": "normal", "params": {"mean": 0, "std": 1}}},
    }
    dumped = parse_spec(body).body()
    assert "emit" not in dumped["features"]["x"]
    # An explicit emit: false *is* canonicalized (it changes generation).
    body2 = {**body, "features": {"x": {**body["features"]["x"], "emit": False}}}
    assert parse_spec(body2).body()["features"]["x"]["emit"] is False
    assert parse_spec(body).spec_hash() != parse_spec(body2).spec_hash()


def test_validation_rejects_latent_difficulty_label() -> None:
    # Pointing difficulty at the latent score (not shipped) must be rejected.
    body = _latent_label_spec().body()
    body["difficulty"] = {"target": "kaggle", "label": "score", "probe": "logreg"}
    with pytest.raises(SpecValidationError, match="latent"):
        generate(parse_spec(body), seed=1)


def test_validation_rejects_failure_on_latent() -> None:
    body = _latent_label_spec().body()
    body["failures"] = [{"type": "feature_noise", "column": "score", "dist": "normal", "params": {"mean": 0, "std": 1}}]
    with pytest.raises(SpecValidationError, match="latent"):
        generate(parse_spec(body), seed=1)
