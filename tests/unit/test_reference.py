"""The spec capabilities manifest (AI-authoring contract) is complete + serializable."""

from __future__ import annotations

import json

from datadoom.engine import build_capabilities


def test_manifest_is_json_serializable_and_complete() -> None:
    cap = build_capabilities()
    # Round-trips through JSON (what tooling/LLMs consume).
    assert json.loads(json.dumps(cap)) == cap

    for key in (
        "top_level_keys",
        "feature_types",
        "distributions",
        "structural_fns",
        "failure_modes",
        "difficulty",
        "export",
        "text_generators",
        "rules",
    ):
        assert key in cap


def test_manifest_lists_every_builtin_capability() -> None:
    cap = build_capabilities()
    dists = {d["name"] for d in cap["distributions"]}
    assert {"normal", "lognormal", "uniform", "exponential", "poisson", "pareto"} <= dists

    fns = {f["name"] for f in cap["structural_fns"]}
    assert {"linear", "logistic", "polynomial", "map", "identity"} <= fns

    failures = {f["type"] for f in cap["failure_modes"]}
    assert {
        "mcar", "mar", "mnar", "label_noise",
        "feature_noise", "drift", "covariate_shift", "leakage",
    } <= failures

    assert set(cap["feature_types"]) == {
        "numeric", "categorical", "boolean", "datetime", "text", "timeseries"
    }
    assert set(cap["difficulty"]["tiers"]) == {"beginner", "intermediate", "advanced", "kaggle"}
    assert "csv" in cap["export"]["formats"]


def test_distributions_carry_required_params() -> None:
    cap = build_capabilities()
    by_name = {d["name"]: d for d in cap["distributions"]}
    assert by_name["normal"]["required_params"] == ["mean", "std"]
    assert by_name["poisson"]["required_params"] == ["lam"]
    assert by_name["pareto"]["required_params"] == ["alpha", "xm"]


def test_manifest_reflects_registered_plugins() -> None:
    # A plugin-registered distribution must surface in the manifest (built from
    # the live registry), proving the contract stays authoritative.
    from datadoom.engine.dist.base import Distribution
    from datadoom.engine.dist.builtins import REGISTRY

    class _Tri(Distribution):
        name = "tri_test_only"
        required_params = ("a",)

        def sample(self, rng, n, params):  # pragma: no cover - not exercised
            return rng.random(n)

        def cdf(self, x, params):  # pragma: no cover - not exercised
            return x

    REGISTRY["tri_test_only"] = _Tri()
    try:
        names = {d["name"] for d in build_capabilities()["distributions"]}
        assert "tri_test_only" in names
    finally:
        del REGISTRY["tri_test_only"]
