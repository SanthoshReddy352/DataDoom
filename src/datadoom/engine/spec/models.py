"""Pydantic v2 spec models — the parsed, validated form of doc 04.

These are pure (no DB/framework imports). Shape/type validation happens here;
cross-entity semantic checks (acyclicity, references) live in ``validate.py``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .hashing import canonical_json, spec_hash

FEATURE_NAME_PATTERN = r"^[A-Za-z_][A-Za-z0-9_]*$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Feature definitions (04 §4) -----------------------------------------------------


class _FeatureBase(_Model):
    """Fields shared by every feature type.

    ``emit=False`` marks a **latent** feature: it is sampled / computed and may
    drive the causal SEM (and appears in the true causal graph), but it is **not
    shipped** — excluded from the output CSV, the difficulty probe, compliance,
    and correlation/MI. It models hidden variables (unobserved confounders, a
    latent score that generates an observed label). The default is ``None`` ==
    emitted; only an explicit ``False`` is canonicalized, so adding the field
    never changes the hash of an existing spec (invariant #5/#6).
    """

    description: str | None = None
    emit: bool | None = None


class NumericFeature(_FeatureBase):
    type: Literal["numeric"]
    dist: str | None = None  # None => derived via causal
    params: dict[str, float] = Field(default_factory=dict)
    min: float | None = None
    max: float | None = None
    dtype: Literal["int", "float"] = "float"


class CategoricalFeature(_FeatureBase):
    type: Literal["categorical"]
    categories: list[str] = Field(min_length=1)
    weights: list[float] | None = None

    @field_validator("weights")
    @classmethod
    def _weights_nonneg(cls, v: list[float] | None) -> list[float] | None:
        if v is not None and any(w < 0 for w in v):
            raise ValueError("categorical weights must be non-negative")
        return v


class BooleanFeature(_FeatureBase):
    type: Literal["boolean"]
    rate: float = 0.5

    @field_validator("rate")
    @classmethod
    def _rate_in_unit(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("boolean rate must be in [0, 1]")
        return v


class DatetimeFeature(_FeatureBase):
    type: Literal["datetime"]
    start: str
    end: str
    granularity: Literal["second", "minute", "hour", "day"] = "day"
    dist: str = "uniform"


class TextFeature(_FeatureBase):
    type: Literal["text"]
    # "lorem" emits filler words; any realistic provider key (name, email,
    # address, company, …) is served by mimesis. See dist/providers.py.
    generator: str = "lorem"
    locale: str = "en"
    length: dict[str, int] = Field(default_factory=lambda: {"min": 5, "max": 30})


class TrendSpec(_Model):
    """Linear trend ``slope·t + intercept`` over the row index."""

    slope: float = 0.0
    intercept: float = 0.0


class SeasonalitySpec(_Model):
    """One sinusoidal season ``amplitude·sin(2π·t/period + phase)``."""

    amplitude: float
    period: float = Field(gt=0.0)
    phase: float = 0.0


class TimeseriesFeature(_FeatureBase):
    """An ordered series ``Xₜ = T(t) + S(t) + AR(p) + εₜ`` (05 §6).

    Generated over the row index (row order is preserved end-to-end). It is a
    *root* feature — it may be a causal **parent** but is never a causal target,
    and it is not assessed by distribution compliance (KS/GoF don't apply to a
    trended, autocorrelated series).
    """

    type: Literal["timeseries"]
    trend: TrendSpec | None = None
    seasonality: list[SeasonalitySpec] = Field(default_factory=list)
    ar: list[float] = Field(default_factory=list)  # AR coefficients φ₁…φ_p
    noise_std: float = Field(default=1.0, ge=0.0)  # σ of εₜ ~ N(0, σ²)
    min: float | None = None
    max: float | None = None
    dtype: Literal["int", "float"] = "float"


Feature = Annotated[
    NumericFeature
    | CategoricalFeature
    | BooleanFeature
    | DatetimeFeature
    | TextFeature
    | TimeseriesFeature,
    Field(discriminator="type"),
]


# --- Causal graph (04 §5) ------------------------------------------------------------


class CausalEdge(_Model):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    src: str = Field(alias="from")
    dst: str = Field(alias="to")
    fn: str  # linear | logistic | polynomial | map | identity | <plugin>
    weight: float | None = None
    bias: float | None = None
    coeffs: list[float] | None = None
    mapping: dict[str, float] | None = None


class CausalGraph(_Model):
    edges: list[CausalEdge] = Field(default_factory=list)
    noise: dict[str, dict[str, Any]] = Field(default_factory=dict)
    interventions: list[dict[str, Any]] = Field(default_factory=list)


# --- Difficulty / failures / export (04 §6-8) ----------------------------------------


class Difficulty(_Model):
    target: str | dict[str, Any]
    label: str
    probe: str = "logreg"
    max_iters: int = Field(default=8, ge=1)
    # Lean-default knobs: feature-observation noise (primary) + label flips
    # (deep end). `causal` shrink / `imbalance` are planned (status.md backlog).
    knobs: list[str] = Field(default_factory=lambda: ["noise", "label_noise"])


class Failure(BaseModel):
    # type-specific fields are validated by the FailureMode handler (P3).
    model_config = ConfigDict(extra="allow")

    type: str


ExportVersion = Literal["clean", "injected"]


def _default_versions() -> list[ExportVersion]:
    return ["clean"]


class ExportSpec(_Model):
    formats: list[str] = Field(default_factory=lambda: ["csv"])
    versions: list[ExportVersion] = Field(default_factory=_default_versions)
    splits: dict[str, float] | None = None
    shuffle: bool = True
    metadata: bool = True


# --- Top-level spec (04 §2) ----------------------------------------------------------


class Spec(_Model):
    datadoom_version: str
    name: str
    description: str | None = None
    seed: int | None = None
    rows: int = Field(ge=1)
    features: dict[str, Feature]
    causal: CausalGraph | None = None
    difficulty: Difficulty | None = None
    failures: list[Failure] = Field(default_factory=list)
    export: ExportSpec = Field(default_factory=ExportSpec)
    meta: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_slug(cls, v: str) -> str:
        import re

        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("name must be slug-friendly ([A-Za-z0-9_-]+)")
        return v

    # --- Canonical form & identity (05 §1) -------------------------------------------

    def body(self) -> dict[str, Any]:
        """Serializable spec document (aliases applied, None fields dropped)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def canonical(self) -> str:
        """Canonical JSON string (seed excluded) used for hashing."""
        return canonical_json(self.body())

    def spec_hash(self) -> str:
        """sha256 of the canonical, seed-excluded spec."""
        return spec_hash(self.body())

    def latent_names(self) -> set[str]:
        """Feature names marked ``emit: false`` (computed but not shipped)."""
        return {name for name, feat in self.features.items() if feat.emit is False}

    def emitted_names(self) -> list[str]:
        """Feature names that are shipped, in spec order."""
        return [name for name, feat in self.features.items() if feat.emit is not False]
