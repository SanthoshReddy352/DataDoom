# 12 — Resource Estimation Model (Local)

> Replaces the legacy cloud **Cost** model. DataDoom is local-first: there is **no billing, no GPU rates, no egress cost**. We estimate **runtime, RAM, and output size** so the UI can warn before a heavy run. Obeys `00_README_Index.md`.

---

## 1. Purpose & Scope

The estimator answers three questions *before* a run, shown in the Canvas pre-flight panel (`02 §7.1`):
1. **How long** will this take? (`estimated_runtime_seconds`)
2. **How much RAM**? (`estimated_ram_mb`)
3. **How big** is the output? (`estimated_size_bytes`)

It is a **heuristic, config-driven** estimate (no actual execution), deterministic given a spec, exposed via `POST /api/specs/estimate` (`08 §3`). It must never *block* a run — only warn (e.g. "this may use ~6 GB RAM").

**Out of scope:** dollar cost, credits, quotas, GPU allocation, multi-region rate optimization — all SaaS artifacts removed from the product.

---

## 2. Inputs

From the spec:
- `n` = `rows`
- `f` = number of features
- `f_num` = numeric feature count, `f_cat`, `f_dt`, `f_text`
- `|E|` = causal edge count
- `D` = max DAG depth
- `k_fail` = number of failure injections
- `diff` = difficulty enabled? `iters_max`, probe type
- `formats`, `versions`, `splits` (affect output size & write time)

Plus machine calibration constants (measured per platform, stored in config; see §6).

---

## 3. Output Size Model

Per-cell byte estimate by type:
| type | avg bytes/value (Parquet/CSV) |
|---|---|
| numeric int | 8 |
| numeric float | 8 |
| categorical | ~ avg label length (CSV) / dictionary-encoded (Parquet) |
| boolean | 1 |
| datetime | 8 |
| text | avg token length × tokens |

```
bytes_per_row ≈ Σ_features avg_bytes(type)
size_clean    ≈ n × bytes_per_row × format_factor
size_total    ≈ size_clean × (#versions) × (#formats) × split_overhead
```
`format_factor`: CSV ≈ 1.0–1.5 (text expansion), Parquet ≈ 0.2–0.6 (compression). `split_overhead ≈ 1.0` (splits partition the same rows, not duplicate them; `both versions` doubles).

---

## 4. RAM Model

Generation holds frames in memory (clean + possibly injected) plus working buffers:
```
ram_base   ≈ n × f × 8 bytes            # one float64 working frame
ram_peak   ≈ ram_base × frame_multiplier
frame_multiplier ≈ 2 (clean) + 1 (injected if requested) + probe_overhead
probe_overhead: if difficulty enabled, + sklearn model footprint (≈ small, but train copies X)
```
Above a configurable threshold (`ram_peak > stream_threshold`), the engine switches to the **chunked/streaming path** for base generation, capping resident memory; the estimate then reports the capped figure with a "(streamed)" note.

---

## 5. Runtime Model

Decompose by pipeline stage (complexities from `05 §9`):
```
t_base    ≈ (n × f_num) / κ_sample            # vectorized sampling
t_causal  ≈ (n × (f + |E|)) / κ_sem
t_failure ≈ (n × k_fail) / κ_fail
t_diff    ≈ iters_used × train_cost(probe, n, f) / κ_probe     # dominant when enabled
t_ks      ≈ (f_num × n log n) / κ_ks
t_io      ≈ size_total / κ_io
t_total   ≈ t_base + t_causal + t_failure + t_diff + t_ks + t_io + t_fixed
```
- `κ_*` are empirically calibrated throughput constants (rows/sec-ish) per machine.
- `t_fixed` covers process/setup overhead.
- Difficulty `iters_used` is unknown a priori; estimate uses a midpoint (e.g. `min(3, max_iters)`) and labels it an upper-ish guess.

---

## 6. Calibration

- Ship **default** `κ_*` constants measured on a reference laptop (documented).
- On first run (or via `datadoom calibrate`), optionally run a tiny micro-benchmark to fit machine-specific `κ_*`, stored in `$DATADOOM_HOME/config.toml`. Purely local; improves estimate accuracy.
- After each real run, record actuals into `GenerationRun.metrics` (`06 §3.3`); a lightweight EWMA refines `κ_*` over time (post-run reconciliation, local only).

```
κ_new = (1 − λ) κ_old + λ κ_observed     # λ small, e.g. 0.2
```

---

## 7. Client-Side Live Estimate

For the **row-count slider** live readout (`02 §5`), the UI computes a cheap approximation client-side using `bytes_per_row` and cached `κ_*` (fetched once), so dragging the slider updates instantly without round-trips. The authoritative estimate comes from `POST /api/specs/estimate` on demand (Estimate Run / Generate).

---

## 8. Warnings & Guardrails

The estimate drives **non-blocking** warnings:
| Condition | UI behavior |
|---|---|
| `ram_peak > 0.7 × system_RAM` | yellow warning + suggest fewer rows / streaming |
| `estimated_runtime > 60 s` | inform; offer to reduce rows or disable difficulty loop |
| `size_total > free_disk` | block with a clear message (can't write the output) |
| difficulty enabled on large `n` | note that the probe loop dominates runtime |

Users are never charged or quota-limited; they are **informed** so local runs don't surprise them.

---

## 9. Determinism of the Estimate

Given a spec (and fixed `κ_*`), the estimate is a pure function — deterministic and reproducible. It depends only on config and calibration constants, never on the data values.

---

## 10. Mapping to Other Docs

| Concern | Doc |
|---|---|
| `POST /api/specs/estimate` contract | `08 §3` |
| complexity orders feeding `κ` model | `05 §9` |
| `metrics` persistence for reconciliation | `06 §3.3`, `07` |
| streaming path threshold | `03 §3.4`, `11 §3` |
| pre-flight UI | `02 §7.1` |
