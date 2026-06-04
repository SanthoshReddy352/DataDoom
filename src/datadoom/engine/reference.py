"""Machine-readable spec capabilities manifest (the AI-authoring contract).

`build_capabilities()` returns a JSON-serializable dict that enumerates **every**
knob a DataDoom spec accepts, with its exact valid values and constraints. It is
built from the **live engine registries** (distributions, structural functions,
failure modes, exporters, text providers, difficulty tiers) so it is always in
sync with the running build *and* automatically reflects any registered plugin.

The authoritative *names* come from the registries; richer per-item *annotations*
(parameter domains, failure-mode fields, prose) are curated here and merged in by
name. An item with no annotation (e.g. a third-party plugin distribution) still
appears, carrying whatever the engine ABC exposes (required params, schema).

This is what you feed an LLM/agent so it can emit a valid `*.datadoom.yaml`
without guessing. The CLI surfaces it via ``datadoom spec-reference`` and the API
via ``GET /api/spec-reference``.
"""

from __future__ import annotations

from typing import Any

from ..version import __version__

# --- curated annotations (merged onto registry-derived names by key) ----------------

_DIST_ANNOTATIONS: dict[str, dict[str, Any]] = {
    "normal": {
        "summary": "Symmetric bell curve over all real numbers.",
        "params": {"mean": "center (any real)", "std": "spread, must be > 0"},
    },
    "lognormal": {
        "summary": "Right-skewed, positive-only (income, prices). mu/sigma are of the underlying normal (log space).",
        "params": {"mu": "mean of ln(X) (any real)", "sigma": "std of ln(X), must be > 0"},
    },
    "uniform": {
        "summary": "Flat — every value in [low, high] equally likely.",
        "params": {"low": "lower bound", "high": "upper bound, must be > low"},
    },
    "exponential": {
        "summary": "Decaying, non-negative (waiting times). Mean == scale.",
        "params": {"scale": "mean of the distribution, must be > 0"},
    },
    "poisson": {
        "summary": "Discrete counts 0,1,2,… ; lam is the mean. Output is integer.",
        "params": {"lam": "mean count, must be > 0"},
        "discrete": True,
    },
    "pareto": {
        "summary": "Heavy-tailed power law; values are >= xm. Smaller alpha = heavier tail.",
        "params": {"alpha": "tail index, must be > 0", "xm": "minimum value (scale), must be > 0"},
    },
}

_FN_ANNOTATIONS: dict[str, dict[str, Any]] = {
    "linear": {
        "summary": "weight·parent + bias.",
        "fields": {"weight": "number (required)", "bias": "number (optional, default 0)"},
    },
    "logistic": {
        "summary": "1/(1+e^-(weight·parent+bias)) — squash a driver to 0..1; typically the last edge into a boolean target.",
        "fields": {"weight": "number (required)", "bias": "number (optional, default 0)"},
    },
    "polynomial": {
        "summary": "Σ coeffs[i]·parent^i — curved/non-linear effect.",
        "fields": {"coeffs": "non-empty list of numbers (required)"},
    },
    "map": {
        "summary": "Look up mapping[parent_category] — turns a categorical parent into a number. Must cover every category.",
        "fields": {"mapping": "object {category: number} covering all parent categories (required)"},
    },
    "identity": {"summary": "Pass the parent value through unchanged.", "fields": {}},
}

#: Failure modes: each is a list item under top-level ``failures`` with ``type`` + these fields.
_FAILURE_MODES: dict[str, dict[str, Any]] = {
    "mcar": {
        "category": "missingness",
        "summary": "Missing Completely At Random — blanks chosen independently of the data.",
        "fields": {
            "column": "feature name (or use 'columns')",
            "columns": "list of feature names (alternative to 'column')",
            "rate": "fraction in [0,1] to blank (required)",
        },
    },
    "mar": {
        "category": "missingness",
        "summary": "Missing At Random — blank probability depends on another observed column.",
        "fields": {
            "column": "feature to blank (required)",
            "driver": "observed numeric/boolean feature that drives missingness (required)",
            "rate": "expected fraction blanked, calibrated (required)",
            "strength": "driver skew, number (optional, default 2.0)",
        },
    },
    "mnar": {
        "category": "missingness",
        "summary": "Missing Not At Random — blank probability depends on the column's own value.",
        "fields": {
            "column": "feature to blank (required)",
            "driver": "optional numeric/boolean driver (defaults to the column itself)",
            "rate": "expected fraction blanked, calibrated (required)",
            "strength": "skew, number (optional, default 2.0)",
        },
    },
    "label_noise": {
        "category": "noise",
        "summary": "Flip a boolean / reassign a categorical label to a different class.",
        "fields": {
            "column": "boolean or categorical feature (required)",
            "rate": "fraction in [0,1] to corrupt (required)",
        },
    },
    "feature_noise": {
        "category": "noise",
        "summary": "Additive noise on a numeric column: x' = x + ε.",
        "fields": {
            "column": "numeric feature (required)",
            "dist": "noise distribution name (required, e.g. normal)",
            "params": "params for that distribution (e.g. {mean: 0, std: 1})",
        },
    },
    "drift": {
        "category": "shift",
        "summary": "Gradually shift a numeric column across the row index (concept drift).",
        "fields": {
            "column": "numeric feature (required)",
            "schedule": "object: {kind: linear|step, magnitude: number (total shift) OR rate: per-row slope, at: 0..1 (step only, default 0.5)}",
        },
    },
    "covariate_shift": {
        "category": "shift",
        "summary": "Affine-rescale a numeric column to a target mean/std.",
        "fields": {
            "column": "numeric feature (required)",
            "target": "object {mean?: number, std?: number} (at least one required)",
        },
    },
    "leakage": {
        "category": "leakage",
        "summary": "Plant a NEW column that is a near-perfect proxy for a target.",
        "fields": {
            "target": "numeric/boolean feature to leak (required)",
            "into": "new column name, must differ from target (required)",
            "noise": "proxy noise level relative to target spread (optional, default 0.05; smaller = stronger leak)",
        },
    },
}

_FEATURE_TYPES: dict[str, dict[str, Any]] = {
    "numeric": {
        "summary": "Numbers from a distribution, optionally clamped and/or rounded to int. Omit 'dist' to make it a causal-derived column.",
        "fields": {
            "dist": "distribution name (see 'distributions'); omit for a causal target",
            "params": "object of distribution parameters",
            "min": "lower clamp (optional)",
            "max": "upper clamp (optional)",
            "dtype": "'float' (default) or 'int' (rounds to whole numbers)",
        },
    },
    "categorical": {
        "summary": "One label per row from a fixed set.",
        "fields": {
            "categories": "non-empty list of strings (required)",
            "weights": "list of non-negative numbers, positionally matched; normalized (optional, default uniform)",
        },
    },
    "boolean": {
        "summary": "True/false column.",
        "fields": {"rate": "probability of true, in [0,1] (default 0.5)"},
    },
    "datetime": {
        "summary": "Timestamps drawn uniformly in a range.",
        "fields": {
            "start": "ISO date string, e.g. '2023-01-01' (required)",
            "end": "ISO date string >= start (required)",
            "granularity": "'second' | 'minute' | 'hour' | 'day' (default 'day')",
        },
    },
    "text": {
        "summary": "Strings: 'lorem' filler or a realistic provider (see 'text_generators'). Realistic providers are seeded/reproducible.",
        "fields": {
            "generator": "'lorem' (default) or a realistic provider key",
            "locale": "locale for realistic providers (default 'en')",
            "length": "object {min, max} word-count range — lorem only (default {min:5,max:30})",
        },
    },
    "timeseries": {
        "summary": "Ordered additive series Xt = trend + seasonality + AR(p) + noise over the row index. Row order is the time axis (preserved). May be a causal parent; never a causal target; not distribution-compliance assessed.",
        "fields": {
            "trend": "object {slope, intercept} — linear trend (optional)",
            "seasonality": "list of {amplitude, period (>0), phase} sinusoids, summed (optional)",
            "ar": "list of AR coefficients [phi1..phip]; sum(|phi|) must be < 1 (stationarity)",
            "noise_std": "sigma of Gaussian innovations, >= 0 (default 1.0)",
            "min": "lower clamp (optional)",
            "max": "upper clamp (optional)",
            "dtype": "'float' (default) or 'int'",
        },
    },
}

_SHARED_FEATURE_FIELDS = {
    "description": "free-text doc (optional)",
    "emit": "boolean; false = latent (computed/drives the SEM but NOT exported, and excluded from probe/compliance/correlation). Default true.",
}

_RULES = [
    "Top-level required keys: datadoom_version (always \"1\"), name (slug [A-Za-z0-9_-]+), rows (int >= 1), features.",
    "A causal-derived feature (numeric or boolean) is declared WITHOUT a 'dist'/'rate' and MUST be the 'to' of at least one causal edge.",
    "A feature cannot be both sampled (has dist) and a causal target.",
    "The causal graph must be acyclic. Only numeric/boolean features can be causal targets.",
    "'map' edges require a categorical parent and a mapping covering every category; other fns require a numeric/boolean/timeseries parent.",
    "A difficulty 'label' must be a boolean or 2-class categorical feature, and must not be latent (emit:false).",
    "difficulty.knobs ⊆ {noise, label_noise}. target is a named tier or {band:[a,b]}.",
    "Failures are an ordered list applied after the clean baseline is captured; export versions must include 'injected' to write the corrupted variant.",
    "A failure cannot reference a latent (emit:false) feature.",
    "export.splits ratios must sum to 1.0. export.formats must be known formats.",
    "time-series AR must satisfy sum(|coefficients|) < 1 (stationarity).",
    "Determinism: same (spec, seed) -> identical bytes. Seed is NOT part of the spec hash.",
]


def _distributions() -> list[dict[str, Any]]:
    from .dist.builtins import REGISTRY

    out: list[dict[str, Any]] = []
    for name in sorted(REGISTRY):
        dist = REGISTRY[name]
        entry: dict[str, Any] = {
            "name": name,
            "required_params": list(dist.required_params),
            "builtin": name in _DIST_ANNOTATIONS,
        }
        entry.update(_DIST_ANNOTATIONS.get(name, {}))
        if getattr(dist, "param_schema", None) is not None:
            entry["param_schema"] = dist.param_schema
        out.append(entry)
    return out


def _structural_fns() -> list[dict[str, Any]]:
    from .causal.functions import STRUCTURAL_FNS

    out: list[dict[str, Any]] = []
    for name in sorted(STRUCTURAL_FNS):
        entry: dict[str, Any] = {"name": name, "builtin": name in _FN_ANNOTATIONS}
        entry.update(_FN_ANNOTATIONS.get(name, {}))
        out.append(entry)
    return out


def _failure_modes() -> list[dict[str, Any]]:
    from .failure import FAILURE_MODES

    out: list[dict[str, Any]] = []
    for name in sorted(FAILURE_MODES):
        entry: dict[str, Any] = {"type": name, "builtin": name in _FAILURE_MODES}
        entry.update(_FAILURE_MODES.get(name, {}))
        out.append(entry)
    return out


def _difficulty() -> dict[str, Any]:
    from .difficulty import PROBES, TIER_BANDS

    return {
        "tiers": {name: list(band) for name, band in TIER_BANDS.items()},
        "probes": sorted(PROBES),
        "knobs": ["noise", "label_noise"],
        "target": "a named tier (e.g. 'advanced') or an explicit {band: [a, b]} of AUROC",
        "label": "the boolean / 2-class categorical column the baseline probe predicts",
        "max_iters": "calibration steps, int >= 1 (default 8)",
    }


def _exporters() -> dict[str, Any]:
    from .export import EXPORTERS

    return {
        "formats": sorted(EXPORTERS),
        "versions": ["clean", "injected"],
        "fields": {
            "formats": "list of output formats (default [csv]); parquet needs the optional extra",
            "versions": "subset of {clean, injected} (default [clean])",
            "splits": "object {name: ratio} whose ratios sum to 1.0 (optional)",
            "shuffle": "boolean (default true)",
            "metadata": "boolean — write metadata.json (default true)",
        },
    }


def _text_generators() -> dict[str, Any]:
    from .dist.providers import REALISTIC_GENERATORS

    return {
        "lorem": "filler words (uses 'length' {min,max})",
        "realistic": sorted(REALISTIC_GENERATORS),
    }


def build_capabilities() -> dict[str, Any]:
    """Return the full, JSON-serializable spec capabilities manifest."""
    return {
        "datadoom_version": "1",
        "package_version": __version__,
        "summary": (
            "DataDoom spec capabilities. A spec is a YAML/JSON document describing a "
            "reproducible synthetic dataset. Use the exact names/fields below; same "
            "(spec, seed) regenerates identical data."
        ),
        "top_level_keys": {
            "datadoom_version": 'required, always "1"',
            "name": "required, slug [A-Za-z0-9_-]+",
            "description": "optional string",
            "seed": "optional int (reproducibility; not part of the spec hash)",
            "rows": "required int >= 1",
            "features": "required object {name: feature} — see feature_types",
            "causal": "optional DAG {edges, noise, interventions}",
            "difficulty": "optional classification difficulty target",
            "failures": "optional ordered list of corruptions",
            "export": "optional output config",
            "meta": "optional free-form object (ignored by the engine)",
        },
        "shared_feature_fields": _SHARED_FEATURE_FIELDS,
        "feature_types": _FEATURE_TYPES,
        "distributions": _distributions(),
        "structural_fns": _structural_fns(),
        "causal": {
            "edges": "list of {from, to, fn, ...fn params} — see structural_fns",
            "noise": "object {derived_node: {dist: <name|none>, params: {...}}}",
            "interventions": "list of {do: {feature: value}} — fix a node to a constant",
        },
        "failure_modes": _failure_modes(),
        "difficulty": _difficulty(),
        "export": _exporters(),
        "text_generators": _text_generators(),
        "rules": _RULES,
    }
