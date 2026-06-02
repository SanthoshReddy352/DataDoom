# 02 — User Flow & Micro-Interactions Guide

> The website is DataDoom's **primary point of contact**. This document specifies the screens, flows, and interactions. Obeys `00_README_Index.md`.

---

## 1. Design Philosophy

- **Local-first & instant.** The app runs on `localhost`; no spinners waiting on a remote cloud. Generation feedback is real-time over WebSocket.
- **The Canvas edits a spec.** Every action maps to a field in the DataDoom Spec (`04_DataDoom_Spec_Reference.md`). The UI is a structured editor; the spec is the truth. "View Spec" is always one click away.
- **Transparent, not magical.** Users see the pipeline stages, the seed, the compliance numbers, and the diff between clean and corrupted data. Trust is the product.
- **Developer aesthetic.** Dark mode by default, keyboard-navigable, monospace where it helps (seeds, hashes, logs).
- **Honest language.** We say "compliance score" and "achieved difficulty," never "guaranteed perfect distribution."

---

## 2. Information Architecture

```
/                     Landing (first run) → redirects to /datasets once onboarded
/datasets             Dashboard: list of datasets
/datasets/:id         Canvas: schema + graph editor for a dataset's draft spec
/datasets/:id/run/:runId   Generation tracker (live) → Results
/templates            Template gallery
/plugins              Installed plugins browser
/settings             Local settings (theme, default seed behavior, storage path)
```

Local mode requires **no authentication**. Team mode (opt-in, post-v1) adds `/login` and a workspace switcher.

---

## 3. Phase 1 — First Run & Onboarding

### 3.1 Launch
User runs `datadoom` in a terminal → server starts → browser opens at `http://localhost:8000`.

- **First-run screen:** a brief, dismissible welcome with three cards: *Create Blank Dataset*, *Start from Template*, *Open a Spec File*.
- **Micro-interactions:** an embedded read-only terminal auto-types a sample `.datadoom.yaml` to teach the spec format. Hovering a CTA scales 1.03× with a soft glow.
- **No login** in local mode. A subtle status chip shows `● local` and the storage path.

### 3.2 Open a Spec File
Drag-and-drop or file-pick a `*.datadoom.yaml`. The app validates it (calls `POST /api/specs/validate`), shows a green check or inline errors, and opens it in the Canvas as a new draft.

---

## 4. Phase 2 — Dashboard

- **Layout:** left sidebar (Datasets, Templates, Plugins, Settings); main area = grid of **Dataset Cards**.
- **Dataset Card:** name, created/updated, status badge, row count, feature count, last run's compliance score.
- **Status badges:** `Draft` (grey), `Running` (pulsing blue dot), `Completed` (green check), `Failed` (red triangle).
- **Empty state:** illustrated empty lab with *Create Blank Dataset* and *Use a Template*.
- **Card hover:** elevates with shadow; reveals quick actions — **Open**, **Duplicate**, **Regenerate (same seed)**, **Export**, **Delete**.
- **Micro-interactions:** deleting prompts a confirm; duplicating animates a card clone sliding into place.

---

## 5. Phase 3 — Dataset Initialization

Triggered by *Create Dataset*. A modal collects the minimum to start:

- **Name** (required, auto-focused).
- **Description** (optional).
- **Row count** (slider + input, e.g. 1k–1M). A live **Estimated file size / RAM / runtime** readout updates as the slider moves (from `12_Resource_Estimation_Model.md`, computed client-side from a baseline + `GET /api/estimate`).
- **Difficulty target** (dropdown: Beginner / Intermediate / Advanced / Kaggle / Custom band).
- **Seed** (optional; tooltip: "Leave blank for a recorded deterministic seed").

Submit → transitions into the **Canvas**.

---

## 6. Phase 4 — The Canvas (Core Workspace)

Three regions: **Top Toolbar**, **Main Area** (Table ⇄ Graph toggle), **Right Inspector**.

### 6.1 Top Toolbar
- View toggle: **Table** / **Graph**.
- **Seed** input (masked toggle), **Validate**, **Estimate Run**, **View Spec** (opens read-only YAML drawer), **Generate** (primary CTA).
- A small `unsaved changes` indicator; autosave to the draft spec every change.

### 6.2 Table View (Schema Builder)
A smart spreadsheet that defines **schema, not data**.

- **Add column:** `+` at the header row inserts `feature_N`.
- **Rename:** double-click header → inline text input → Enter saves.
- **Type chip per column:** numeric / categorical / boolean / datetime / text.
- **Reorder:** drag column headers horizontally.
- **Select:** clicking a column highlights it and loads its properties in the Right Inspector.
- **Micro-interactions:** invalid params (e.g. negative variance) turn the cell border red with a tooltip; a column with a causal parent shows a small link glyph.

### 6.3 Right Inspector (contextual to selected column)
- **Numeric:** distribution dropdown (Normal, LogNormal, Poisson, Pareto, Uniform, …), parameter inputs (mean/variance/min/max/…), live mini-histogram preview (sampled client-side with a fixed preview seed).
- **Categorical:** dynamic category list + interactive class-weight pie/bars (for imbalance).
- **Boolean:** base rate slider.
- **Datetime:** range + granularity + optional seasonality hint.
- **Relationships:** "Add dependency" → choose parent columns + structural function (linear / logistic / mapping / polynomial / custom-plugin) + weight/params + noise σ.
- **Validation feedback:** inline, immediate, per-field.

### 6.4 Graph View (Causal Visualizer)
- **React Flow** canvas: columns = nodes, dependencies = directed edges.
- **Create edge:** drag from a node handle to another → opens the structural-function editor.
- **Cycle detection:** an edge that would create a cycle flashes red and is rejected with a toast: *"Causal loops (cycles) are not permitted."*
- **Node badge:** shows distribution type; root nodes vs. derived nodes visually distinct.
- **Layout:** auto-layout button (topological left-to-right) + free drag.
- **Intervention mode (advanced):** toggle a node to `do(X=x)`; incoming edges visually detach; used for counterfactual generation.

---

## 7. Phase 5 — Pre-Flight & Generation

### 7.1 Validation & Estimation
*Estimate Run* (or *Generate*, which auto-validates) slides down a panel:

- **Validation:** DAG acyclicity, parameter validity, type/distribution compatibility, missing targets.
- **Estimate:** estimated runtime, RAM, output file size, number of features/edges. (No cost/credits/GPU — local CPU model.)
- On success the **Generate** button unlocks and pulses.

### 7.2 Generation Tracker (real-time)
The Canvas fades; a centered **Event Tracker** appears, listing the canonical pipeline stages (from `00`):

```
Intake & Validate → Snapshot & Hash → Seed → Base Generation
→ Causal/SEM → Failure Injection* → Difficulty Calibration* → Compliance → Packaging
(* shown only if enabled)
```

- **Live streaming:** WebSocket checks off stages; the current stage spins.
- **Console drawer:** expandable raw logs (`[INFO] generated 50,000 rows for 'age'`).
- **Cancel** button (cooperative cancellation).
- **Completion:** subtle success flash + **View Results**.
- **Failure:** the failed stage turns red; the console auto-expands to the error; a **Retry** / **Edit Spec** choice appears.

---

## 8. Phase 6 — Results & Evaluation

Tabs: **Data Preview · Schema Summary · Distributions · Correlation Matrix · Evaluation Report**.

- **Data Preview:** paginated grid, first N rows; column headers show type + distribution.
- **Distributions:** per-feature histogram with target overlay; KS stat + p-value chip (honest reporting).
- **Correlation Matrix:** heatmap; hovering a cell shows the exact coefficient.
- **Evaluation Report:** **Compliance Score** (e.g. 98%), per-feature Target vs. Actual, **achieved difficulty** vs. target band + the probe model used, **true causal graph** rendered as ground truth.
- **Header chips:** `seed`, `spec_hash` (click to copy), reproducibility note ("Regenerate from this spec+seed for identical data").

### 8.1 Failure Injection Fork
A call-out at the bottom of the report: *"Stress-test your model. Inject failures?"* → **Keep Clean Only** / **Create Failure-Injected Variant**.

### 8.2 Failure Injection Configurator
- Split screen: clean stats left, injection tools right.
- Accordions: Missingness (MCAR/MAR/MNAR with rate + driver columns), Noise (feature/label), Drift, Covariate Shift, Leakage.
- **Live diff preview:** adjusting a slider updates an "expected impact" visual on the left (e.g. data-retention bar dropping, class balance shifting).
- *Inject* runs a mini Event Tracker; the clean baseline is always preserved.

### 8.3 Comparison View
Side-by-side Clean vs. Injected, highlighting concrete changes ("`income` now 12% null (MNAR, driver=education)", "`is_fraud` label flipped on 3% of rows").

---

## 9. Phase 7 — Export & Lifecycle

### 9.1 Export Modal
- **Version:** Clean / Injected / Both.
- **Format:** CSV / Parquet / JSON (plugins add more).
- **Splits:** train/test/hidden toggles + ratios.
- **Include:** metadata bundle (`spec.datadoom.yaml`, `metadata.json`, `report.html`) checkbox.
- **Download Spec:** always available — the shareable, reproducible artifact.
- Download shows a progress circle on the button; files are written locally and offered for download.

### 9.2 Dashboard Post-Actions
- **Regenerate (same seed):** queues an identical run.
- **Edit as New Version:** clones the spec into a new draft (respects immutable-snapshot rule).
- **Open Spec in editor:** reveals the on-disk file path.

---

## 10. Cross-Cutting UX Rules

- **Keyboard:** `g` table/graph toggle, `v` validate, `⌘/Ctrl+Enter` generate, `?` shortcuts overlay.
- **Errors are actionable:** every error names the field/node and offers a fix or a doc link.
- **Spec drawer everywhere:** the read-only YAML is always reachable so power users learn the format.
- **No dark patterns:** destructive actions confirm; nothing phones home; no hidden network calls (local mode is offline-capable).
- **Plugin awareness:** when a plugin contributes a distribution/failure/exporter, it appears natively in the relevant dropdowns (its declared schema fragment is auto-rendered — see `09_Plugin_System.md`).

---

## 11. Templates Gallery (`/templates`)

- Cards per domain (Financial Fraud, E-commerce Churn, Healthcare Readmission, …).
- Click → slide-over previewing the schema nodes + causal graph + the generated problem statement and metric.
- **Use Template** clones its spec into a new draft dataset.
- Community templates (installed via plugins) appear here tagged `community`.
