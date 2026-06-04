# Examples gallery

Two ways to start: **example specs** (hand-written, in the repo) and **built-in
templates** (shipped with the package, one command to instantiate).

## Example specs

Runnable specs in [`examples/`](https://github.com/SanthoshReddy352/datadoom/tree/main/examples).
Each is part of the determinism gate, so every one regenerates byte-identically.

| Spec | Demonstrates |
|---|---|
| [`tabular-basic`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/tabular-basic.datadoom.yaml) | Plain distribution-only tabular data — the smallest useful spec. |
| [`causal-fraud`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/causal-fraud.datadoom.yaml) | A causal DAG (`age → income → is_fraud`, `education → income`) with a logistic target. |
| [`failure-fraud`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/failure-fraud.datadoom.yaml) | The fraud DAG plus six stacked failure modes; ships clean + injected variants. |
| [`difficulty-credit`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/difficulty-credit.datadoom.yaml) | A credit-default label calibrated to the `advanced` difficulty band, with a latent score. |
| [`people-realistic`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/people-realistic.datadoom.yaml) | Realistic-but-seeded text fields (names, emails, addresses) via mimesis providers. |
| [`timeseries-sensor`](https://github.com/SanthoshReddy352/datadoom/blob/main/examples/timeseries-sensor.datadoom.yaml) | An additive time-series feature: trend + seasonality + AR(p) + noise. |

Run any of them:

```bash
datadoom run examples/causal-fraud.datadoom.yaml --seed 42 --out ./out
datadoom verify examples/causal-fraud.datadoom.yaml --seed 42 --against ./out
```

## Built-in templates

Start from a curated domain spec with one command (or one click in the web
Templates gallery):

```bash
datadoom template list                # all templates
datadoom template list --level hackathon
datadoom template use fraud-detection --out my.datadoom.yaml
```

### Hackathon challenges

Enterprise-grade ML challenges built by composition — deep causal DAGs, latent
confounders, mixed feature types, stacked data-quality failures, and calibrated
difficulty bands. Each carries a `meta.challenge` brief.

| Template | Domain | Highlights |
|---|---|---|
| `credit-default-challenge` | Finance | Deep DAG → latent risk score → default; `advanced` band; MNAR/MAR/drift/leakage/label-noise. |
| `clinical-deterioration` | Healthcare | Hidden-confounder design — latent severity drives vitals *and* outcome; `advanced` band. |
| `predictive-maintenance` | Industrial IoT | Three additive time-series sensors → latent wear → label; drift/noise/MCAR/leakage. |
| `telecom-churn-challenge` | Telecom | Realistic-text identity + latent dissatisfaction → churn; hard `kaggle` band; MNAR. |

### Starter templates

| Template | Domain | Highlights |
|---|---|---|
| `fraud-detection` | Finance | Causal structure + failure injection. |
| `customer-churn` | SaaS | Difficulty targeting + a latent feature. |
| `hospital-readmission` | Healthcare | Causal structure + a latent feature. |
| `ecommerce-orders` | E-commerce | Quick distribution-only table. |
| `iot-sensors` | IoT | Sensor readings. |
| `people-directory` | People | Realistic text via mimesis providers. |
| `marketing-ab-test` | Marketing | A/B test design. |
| `insurance-claims` | Insurance | A Pareto heavy-tailed claim amount. |
