"""Built-in domain templates (17 step 18, 09 §4.6).

A template is a curated, ready-to-run spec plus catalog metadata. The web gallery
and ``datadoom template`` surface them so a user can start from a realistic
domain dataset in one click. Templates are *data only* (no code); this module is
a thin loader that reads the bundled YAML via :mod:`importlib.resources`, so it
works the same from the source tree and an installed wheel.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml


@dataclass(frozen=True)
class TemplateMeta:
    """Catalog entry for one built-in template."""

    id: str
    name: str
    domain: str
    description: str
    tags: tuple[str, ...]
    filename: str
    features: tuple[str, ...] = ()  # showcased engine features (causal/failures/…)
    level: str = "starter"  # "starter" (learn one feature) | "hackathon" (full enterprise challenge)

    def to_summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "description": self.description,
            "tags": list(self.tags) + list(self.features),
            "level": self.level,
        }


CATALOG: tuple[TemplateMeta, ...] = (
    # ── Hackathon flagships ──────────────────────────────────────────────────
    # Enterprise-grade ML challenges: each composes a deep causal DAG, a latent
    # confounder, a stacked data-quality failure profile and (where applicable)
    # a calibrated difficulty band — a realistic dataset to build a model on,
    # carrying a `meta.challenge` brief (target / metric / split / gotchas).
    TemplateMeta(
        id="credit-default-challenge",
        name="Credit default (challenge)",
        domain="Finance",
        description=(
            "Consumer credit default. Demographics and employment drive income, which "
            "feeds a latent risk score behind the default label — calibrated to the "
            "'advanced' AUROC band, then corrupted with MNAR income, drifting debt-to-"
            "income, a leaked collections proxy and label noise. Train/test split included."
        ),
        tags=("credit-risk", "classification"),
        features=("causal", "latent", "difficulty", "failure-injection", "leakage"),
        filename="credit_default_challenge.datadoom.yaml",
        level="hackathon",
    ),
    TemplateMeta(
        id="clinical-deterioration",
        name="Clinical deterioration (challenge)",
        domain="Healthcare",
        description=(
            "ICU early-warning with a hidden confounder: a latent illness severity drives "
            "both the observed vitals (heart rate, lactate, BP) and the outcome, so the "
            "vitals are confounded proxies. Calibrated to 'advanced', with realistic "
            "MNAR/MAR/MCAR clinical missingness."
        ),
        tags=("clinical", "classification"),
        features=("causal", "latent", "confounder", "difficulty", "missingness"),
        filename="clinical_deterioration.datadoom.yaml",
        level="hackathon",
    ),
    TemplateMeta(
        id="predictive-maintenance",
        name="Predictive maintenance (challenge)",
        domain="Industrial IoT",
        description=(
            "Turbine maintenance on multi-sensor time-series (vibration, bearing temp, oil "
            "pressure) plus load and component grade, driving a latent wear index behind a "
            "maintenance label. The load regime drifts, gains sensor noise and drops "
            "readings; a leaked alarm proxy is planted. Sequential — preserve row order."
        ),
        tags=("predictive-maintenance", "classification"),
        features=("time-series", "causal", "latent", "drift", "leakage"),
        filename="predictive_maintenance.datadoom.yaml",
        level="hackathon",
    ),
    TemplateMeta(
        id="telecom-churn-challenge",
        name="Telecom churn (challenge)",
        domain="Telecom",
        description=(
            "Customer churn with realistic records: believable identity fields (name, "
            "email, city) sit beside the real signal — tenure, charges, support load, "
            "contract and usage feed a latent dissatisfaction score. Calibrated to the hard "
            "'kaggle' AUROC band, with MNAR usage and noisy labels. Drop the identifiers."
        ),
        tags=("churn", "classification"),
        features=("causal", "latent", "difficulty", "realistic-text", "missingness"),
        filename="telecom_churn_challenge.datadoom.yaml",
        level="hackathon",
    ),
    # ── Starter templates (learn one capability at a time) ───────────────────
    TemplateMeta(
        id="fraud-detection",
        name="Transaction fraud",
        domain="Finance",
        description=(
            "Customer age and card type drive monthly spend, which drives a fraud-risk "
            "label — then realistic data-quality failures (under-reported spend, random "
            "gaps, mislabels) corrupt a copy so you can study robustness."
        ),
        tags=("classification",),
        features=("causal", "failure-injection"),
        filename="fraud_detection.datadoom.yaml",
    ),
    TemplateMeta(
        id="customer-churn",
        name="Customer churn",
        domain="SaaS",
        description=(
            "Tenure, monthly charges and support load feed a latent satisfaction score "
            "behind a churn label, calibrated down to an 'intermediate' baseline-AUROC "
            "band so the dataset is hard in a measured, honest way."
        ),
        tags=("classification",),
        features=("difficulty", "latent", "causal"),
        filename="customer_churn.datadoom.yaml",
    ),
    TemplateMeta(
        id="hospital-readmission",
        name="Hospital readmission",
        domain="Healthcare",
        description=(
            "Patient age, diagnosis count, length of stay and prior admissions drive a "
            "latent severity score behind a 30-day readmission label — a clean causal "
            "starter with a hidden confounder in the true graph."
        ),
        tags=("classification",),
        features=("causal", "latent"),
        filename="hospital_readmission.datadoom.yaml",
    ),
    TemplateMeta(
        id="ecommerce-orders",
        name="E-commerce orders",
        domain="E-commerce",
        description=(
            "A fast orders table — lognormal order value, basket quantity, product "
            "category, channel, order date and a return flag. Distribution-only, so it "
            "generates instantly."
        ),
        tags=("tabular",),
        features=("distributions", "datetime"),
        filename="ecommerce_orders.datadoom.yaml",
    ),
    TemplateMeta(
        id="iot-sensors",
        name="IoT sensor readings",
        domain="IoT",
        description=(
            "Hourly multi-sensor telemetry — temperature, humidity, pressure and battery "
            "by device, with bounded distributions that stay physically plausible."
        ),
        tags=("tabular",),
        features=("numeric", "datetime"),
        filename="iot_sensors.datadoom.yaml",
    ),
    TemplateMeta(
        id="people-directory",
        name="People directory",
        domain="People",
        description=(
            "Believable identities — names, emails, phones, companies, job titles, "
            "cities and countries — via deterministic mimesis providers. Great for demos "
            "and UIs that need realistic-looking records."
        ),
        tags=("tabular",),
        features=("realistic-text", "datetime"),
        filename="people_directory.datadoom.yaml",
    ),
    TemplateMeta(
        id="marketing-ab-test",
        name="Marketing A/B test",
        domain="Marketing",
        description=(
            "A web experiment — 50/50 control vs. treatment, session engagement "
            "(exponential dwell, Poisson pageviews), conversion and revenue. "
            "Distribution-only and instant."
        ),
        tags=("experiment",),
        features=("distributions",),
        filename="ab_test.datadoom.yaml",
    ),
    TemplateMeta(
        id="insurance-claims",
        name="Insurance claims",
        domain="Insurance",
        description=(
            "Claims with a heavy-tailed (Pareto) claim amount — most small, a few very "
            "large — plus policyholder age, region, prior-claim count and a fraud flag."
        ),
        tags=("tabular",),
        features=("heavy-tail",),
        filename="insurance_claims.datadoom.yaml",
    ),
)

_BY_ID = {t.id: t for t in CATALOG}


def list_templates() -> list[TemplateMeta]:
    """Every built-in template, in catalog order."""
    return list(CATALOG)


def get_template(template_id: str) -> TemplateMeta | None:
    return _BY_ID.get(template_id)


def load_template_text(template_id: str) -> str:
    """The template's raw spec YAML (comments preserved — good for `template show`)."""
    meta = _BY_ID.get(template_id)
    if meta is None:
        raise KeyError(f"unknown template {template_id!r}")
    return (resources.files(__package__) / meta.filename).read_text(encoding="utf-8")


def load_template_body(template_id: str) -> dict[str, Any]:
    """Parse a template's spec YAML into a raw dict (not yet validated)."""
    body = yaml.safe_load(load_template_text(template_id))
    if not isinstance(body, dict):
        raise ValueError(f"template {template_id!r} did not parse to a mapping")
    return body
