# DataDoom — Frontend Design Prompts (for Claude Design)

> Copy-paste prompts to design the DataDoom web app. **Run Prompt 0 first** to
> establish the design system, then the per-screen prompts. Each per-screen prompt
> is self-contained but assumes Prompt 0's tokens/components — if the tool loses
> context, re-paste the **Design System Recap** block (end of Prompt 0).
>
> Phase tags map to the roadmap: **[P1]** build now (MVP), **[P2–P5]** later
> screens included so the design system is coherent from day one.
>
> Source UX truth: `docs_v2/02_User_Flow_Guide.md`; product: `docs_v2/01_PRD.md`;
> spec/report data shapes: `docs_v2/04`, `06`. These prompts encode that truth so
> you can paste them without the docs.

---

## Aesthetic direction — "The Lab Journal" (editorial / magazine)

DataDoom is a precise scientific instrument, presented like a **beautifully
typeset science journal**. The visual language is **editorial / magazine**:
confident serif headlines, generous whitespace, a strong typographic hierarchy,
hairline rules, eyebrow/kicker labels, oversized tabular numerals for key stats,
and restrained spot colour. It should feel calm, literate, and exact — the
opposite of a noisy "dashboard". The data itself (seeds, hashes, params, logs)
speaks in monospace — the instrument's voice inside the prose.

**Theme toggling is a first-class feature.** Two equally-considered themes:

- **Paper** (light, the **default**) — warm off-white stock, near-black ink.
- **Ink** (dark) — warm near-black, paper-white text.

Plus a **System** option. The toggle is always visible in the top bar; the
choice persists; **every component, state, and screen must be designed in BOTH
themes**. The "doom" in DataDoom is never decorative — it appears only as a
reserved hazard/ember accent on failure-injection and destructive moments.

---

## Locked technical stack (state this to the tool; do not substitute)

- **React 18 + TypeScript + Vite**, **Tailwind CSS**, **Zustand** (UI state),
  **TanStack Query** (server state).
- **shadcn/ui** (Radix primitives) as the base component kit; **lucide-react**
  icons; **Sonner** toasts; **Framer Motion** for micro-interactions.
- **React Flow** (+ `dagre`) for the causal graph; **TanStack Table** for the
  schema spreadsheet; **Glide Data Grid** for the data preview; **Recharts/Tremor**
  for histograms & bars; **Nivo** for the correlation heatmap; **CodeMirror 6**
  for the read-only YAML spec drawer.
- **Fonts (editorial trio):** a high-contrast **serif** for display/headlines
  (**Fraunces**, optical-size variable; alt **Newsreader**), a clean **grotesque
  sans** for UI controls/labels (**Geist Sans**; alt **Inter**), and a
  **monospace** for all data — seeds, hashes, params, logs, code (**Geist Mono**;
  alt **JetBrains Mono**). Long-form prose/descriptions may use a serif text face
  (**Newsreader**) for a true magazine read. Self-host the fonts (offline).
- API client generated from the FastAPI OpenAPI schema; realtime via WebSocket
  (SSE fallback). No external/CDN calls at runtime — the app is **offline-capable**.

---

# Prompt 0 — Foundation & Design System

```
You are designing the design system and application shell for DataDoom, a
local-first, open-source desktop-class web app (runs at http://localhost:8000,
served by a Python server; no cloud, no login). Output a cohesive design system
plus the app shell. Stack: React + TypeScript + Vite + Tailwind CSS, shadcn/ui
(Radix) components, lucide-react icons, Framer Motion, Sonner toasts.

PRODUCT CONTEXT
DataDoom is a "controllable experimental data laboratory." Users design a dataset
the way they reason about it — distributions, causal relationships, difficulty,
and failure modes — and regenerate it identically, forever, from a single spec
file. It is NOT a row generator or a prompt wrapper. The center of gravity is a
human-readable spec file; the UI is a structured editor for that spec. Four
signature capabilities: (1) strict seed reproducibility, (2) user-authored causal
DAG/SEM, (3) ML-difficulty targeting, (4) systematic failure-mode injection.

PERSONAS: ML engineers/data scientists, hackathon organizers, educators/students,
library authors. Technical, comfortable with terminals, value transparency.

AESTHETIC — "THE LAB JOURNAL" (editorial / magazine; non-negotiable)
Design DataDoom as a beautifully typeset science journal: confident SERIF
headlines, generous margins and whitespace, a strong typographic hierarchy,
hairline rules as dividers, small-caps "eyebrow"/kicker labels above titles,
oversized tabular numerals for key stats (a compliance score reads like a
magazine pull-stat), and restraint with colour. Editorial devices to use:
kickers, drop-of-emphasis lead sentences, pull-quotes for the honest/trust
statements, figure-style captions in small serif italic, and a clear baseline
rhythm. The result should feel literate, calm, and exact — not a busy dashboard.

DESIGN PHILOSOPHY (non-negotiable)
- Local-first & instant: no cloud spinners; generation feedback is real-time.
- Transparent, not magical: always show the seed, spec hash, pipeline stages,
  compliance numbers, and clean-vs-corrupted diffs. Trust is the product.
- Honest language: "compliance score", "achieved difficulty" — never "guaranteed
  perfect distribution". No dark patterns; destructive actions confirm.
- Keyboard-navigable; monospace for seeds/hashes/logs/params (the instrument's
  voice woven through the editorial prose).
- "The Canvas edits a spec": a read-only YAML "View Spec" drawer is reachable from
  everywhere so power users learn the format.

THEME TOGGLING (first-class — design BOTH themes for everything)
Two equally-polished themes, switchable from a persistent top-bar toggle, plus a
"System" option; the choice persists (localStorage) and cross-fades smoothly
(respect prefers-reduced-motion):
- "Paper" (LIGHT, the DEFAULT): warm paper stock, near-black ink.
- "Ink" (DARK): warm near-black, paper-white text.
Deliver every token, component, and state in both themes. Both must pass WCAG-AA.

COLOR PALETTE — "Paper & Ink" (encode as CSS custom properties in OKLCH; ship a
:root [Paper] set and a [data-theme="ink"] set). Warm neutrals, reserved accents.

  PAPER (light, default):
    --bg            #FBFAF7   warm paper (app canvas)
    --surface-1     #FFFFFF   panels / cards (raised off the paper)
    --surface-2     #F4F2EC   insets, inputs, table zebra
    --surface-3     #EAE7DD   hover/active fill
    --border        #E2DED3   hairline rules / dividers
    --border-strong #C8C2B2   focused/active outlines
    --text          #1A1916   ink (primary)
    --text-muted    #6B6862   secondary
    --text-faint    #9A958A   tertiary / placeholders / captions

  INK (dark):
    --bg            #100F0C   warm near-black
    --surface-1     #1A1813   panels / cards
    --surface-2     #232017
    --surface-3     #2D2A1F
    --border        #322E22
    --border-strong #4A4534
    --text          #ECE8DF   warm paper-white
    --text-muted    #ADA694
    --text-faint    #79735F

  ACCENTS (shared hues; tune lightness per theme; each needs hover + a ~12% tint
  surface for badges). Use accents as editorial spot colour — sparingly:
    --primary       Plasma Violet   brand, primary CTAs, active nav, focus ring
                    Paper #5B43E6   ·  Ink #8E72FF
    --hazard        Ember           FAILURE INJECTION, destructive, drift/corruption ONLY
                    Paper #C8402A   ·  Ink #FF5C38
    --success       Signal Green    pass/compliant/completed
                    Paper #2E7D43   ·  Ink #3FB950
    --warning       Amber           caution / near-threshold
                    Paper #B7791F   ·  Ink #E3B341
    --info          Cyan            neutral data / info chips
                    Paper #0E7C8B   ·  Ink #39D3E0
  Data-viz categorical sequence (charts/nodes): violet, cyan, amber, green,
    ember, magenta #C026D3/#E879F9, teal #0D9488/#2DD4BF (pick the per-theme tone).
  Use hazard sparingly — it must read as a warning whenever it appears.

TYPOGRAPHY (editorial trio)
- Display / headlines: a high-contrast SERIF — Fraunces (optical-size variable;
  alt Newsreader). Page titles are large serif; use a small-caps letterspaced
  eyebrow/kicker above them.
- UI sans (controls, labels, nav, table headers): Geist Sans (alt Inter).
- Prose / long descriptions / captions: a serif text face (Newsreader) for the
  magazine read; captions in small italic.
- Mono (seeds, spec_hash, file paths, log lines, numeric params, code):
  Geist Mono (alt JetBrains Mono). Tabular-nums for ALL metrics.
- Type scale (editorial, roomy): 12/13 micro & captions, 14/15 body, 16/18
  section, 22/28 page titles (serif), 40/56 hero & pull-stats (serif).
  Tight leading for data, comfortable for prose.

SHAPE / SPACING / ELEVATION (paper-like, low chrome)
- Radius: 4–6px controls, 8–10px cards, 14px modals. Borders are 1px HAIRLINES
  (--border) used as editorial rules; lean on rules + whitespace, not big shadows.
- Spacing on a 4px grid with generous outer margins (the "page margins" of a
  magazine). Establish a clear baseline rhythm.
- Elevation: light, soft shadows in Paper; in Ink rely on surface steps + borders.
  One restrained focus glow on the primary CTA.
- Motion: 150–200ms ease-out for hovers; spring for card/clone movement; a brief
  success "flash" on completion; a smooth theme cross-fade. Respect
  prefers-reduced-motion (no theme flash, no parallax).

APP SHELL (deliver this layout)
- Left SIDEBAR (collapsible, ~240px): editorial masthead — the "DataDoom" wordmark
  set in the display serif + a tiny mono version chip; nav items (sans, with
  icons) — Datasets, Templates, Plugins, Settings. Active item: --primary
  left-rule + faint tint. Keep it airy.
- TOP BAR: a kicker + contextual page title/breadcrumb on the left (serif title);
  right side: a STATUS CHIP "● local" (success dot) with the storage path on
  hover, the THEME TOGGLE (Paper/Ink + System; sun/moon or a labeled segmented
  control), and a "?" shortcuts button. A hairline rule separates the bar.
- COMMAND PALETTE (Cmd/Ctrl+K): fuzzy actions (new dataset, open spec, toggle
  theme, go to…).
- GLOBAL SPEC DRAWER: a right-side slide-over showing the current dataset's spec
  as read-only, syntax-highlighted YAML (CodeMirror), with a copy button; opens
  via a persistent "View Spec" affordance and the shortcut.
- SHORTCUTS OVERLAY ("?"): g = table/graph toggle, v = validate,
  Cmd/Ctrl+Enter = generate, Cmd/Ctrl+K = command palette, t = toggle theme.
- TOASTS via Sonner (bottom-right). ERROR pattern: every error names the
  field/node (a "locator") and offers a fix or doc link.

SHARED COMPONENTS to define (in BOTH themes): Button (primary/secondary/ghost/
destructive), Input/NumberInput, Select/Combobox, Slider, Switch, Tabs,
Dialog/Modal, Drawer, Accordion, Card ("journal entry"), Badge/StatusBadge,
Tooltip, Toast, Table primitives, EmptyState, Kicker/Eyebrow label, PullStat
(oversized serif numeral + caption), KbdKey, CopyableHash (mono + copy icon),
MiniSparkline/MiniHistogram, ThemeToggle, and a StageStepper (generation tracker).

STATES: design empty, loading (skeletons, not spinners where possible), error,
and success for every surface, IN BOTH THEMES. Keyboard focus rings everywhere
(2px --primary).

DELIVERABLES: token sheet (CSS variables for Paper + Ink), an editorial
typography specimen (serif headlines, kickers, pull-stats, mono data, captions),
the full component inventory above in both themes, the assembled app shell
(sidebar + top bar with the theme toggle + an empty content area), and a
"kitchen sink" screen shown once in Paper and once in Ink.
```

**Design System Recap (re-paste into later prompts if needed):**

```
DataDoom = local-first synthetic-data lab, styled as an EDITORIAL / MAGAZINE
science journal ("The Lab Journal"): serif headlines (Fraunces), sans UI (Geist
Sans), mono data (Geist Mono), kickers, hairline rules, pull-stats, generous
whitespace. Spec-as-truth; transparent/honest. THEME TOGGLING is first-class —
design everything in BOTH "Paper" (light, DEFAULT: bg #FBFAF7, surfaces #FFFFFF/
#F4F2EC, ink text #1A1916) and "Ink" (dark: bg #100F0C, surfaces #1A1813/#232017,
text #ECE8DF), persistent top-bar toggle + System, WCAG-AA both. Accents are
reserved spot colour: Plasma Violet primary (Paper #5B43E6 / Ink #8E72FF), Ember
hazard for failure/destructive ONLY (Paper #C8402A / Ink #FF5C38), success/
warning/info green/amber/cyan. Radius 4–6/8–10/14, 4px grid, hairline borders,
reduced-motion aware. Stack: React+TS+Vite, Tailwind, shadcn/ui, lucide, Framer
Motion, Sonner. Shell = airy left sidebar (Datasets/Templates/Plugins/Settings) +
top bar with "● local" chip + THEME TOGGLE + global read-only YAML spec drawer +
Cmd/Ctrl+K palette.
```

---

# Prompt 1 — First-Run / Onboarding  [P1]

```
Design DataDoom's first-run / landing screen (route "/", redirects to /datasets
once onboarded). Use the DataDoom design system ("The Lab Journal", editorial;
Paper light default + Ink dark; show both).

CONTEXT: The user just ran `datadoom` in a terminal; the browser opened. No login.
This is a brief, dismissible welcome that teaches the spec format and offers three
ways in. Treat it like a magazine COVER / contents page: a confident serif
masthead, a kicker, generous margins.

LAYOUT
- Editorial hero: a small-caps kicker ("A controllable data laboratory"), then the
  "DataDoom" wordmark in the display serif, and a serif lead line as a pull-quote:
  "Design a dataset. Regenerate it identically, forever." A subtle "● local"
  status chip with the storage path. The theme toggle is visible.
- Three primary CTA CARDS in a row (journal entries):
  1) "Create Blank Dataset" (primary, Plasma Violet)
  2) "Start from a Template"
  3) "Open a Spec File" (drag-and-drop zone + file picker for *.datadoom.yaml)
- A teaching element: an embedded READ-ONLY TERMINAL/listing panel (mono, with a
  paper-tinted or ink surface depending on theme) that auto-types a short sample
  `.datadoom.yaml` (datadoom_version, name, rows, a couple of features) to
  demonstrate the format. A blinking caret; loops gently.

INTERACTIONS
- CTA hover: subtle lift (1.02) + a soft Plasma-Violet focus glow; keep it quiet.
- "Open a Spec File": on drop, show validating → green check or inline error list
  (each error names the field via a "locator" like `features.age.params`). Valid
  file opens in the Canvas as a new draft.
- Dismiss "x" persists the choice (don't show welcome again).

STATES: idle, dragging-over (dropzone highlighted with --primary dashed rule),
validating, valid, invalid (ember, listed errors). Show the hero once in Paper and
once in Ink.
DELIVERABLE: the full first-run screen (Paper + Ink) + the drag-over and
invalid-file states.
```

---

# Prompt 2 — Dashboard + Create Dataset modal  [P1]

```
Design the DataDoom Dashboard (route "/datasets") and the Create Dataset modal.
Use the DataDoom design system (editorial; both themes).

DASHBOARD LAYOUT (a magazine "contents" page of datasets)
- Left sidebar (from the shell) with Datasets active.
- Main area: an editorial header — kicker ("Your laboratory") + a large serif
  "Datasets" title — with a primary "Create Dataset" button and a search/filter
  input on the right, separated from the grid by a hairline rule. Below: a
  responsive GRID of Dataset Cards with generous gutters.

DATASET CARD (a journal entry): dataset name in the display serif (prominent),
created/updated (relative, muted, small), a STATUS BADGE, and a row of metrics in
MONO tabular-nums — row count, feature count, and the last run's COMPLIANCE SCORE
rendered as a small PullStat (e.g. "98%"; "—" if never run).
- STATUS BADGES: Draft (neutral ink), Running (pulsing --primary dot), Completed
  (Signal-Green check), Failed (Ember triangle).
- CARD HOVER: gentle lift + --border-strong rule; reveal a quick-action row —
  Open, Duplicate, Regenerate (same seed), Export, Delete. Delete confirms;
  Duplicate animates a card clone sliding into place (Framer Motion).
- EMPTY STATE: an editorial "empty page" — a kicker, a serif line "Nothing in the
  lab yet", and two CTAs ("Create Blank Dataset", "Use a Template").

CREATE DATASET MODAL (shadcn Dialog) collects the minimum to start:
- Name (required, auto-focused, slug-friendly; live-validate the pattern).
- Description (optional).
- Row count: a slider + linked number input (1k–1M, log scale). As it moves, show
  a LIVE readout of Estimated file size / RAM / runtime (client-side estimate;
  label it "estimate"). Numbers in mono tabular-nums.
- Difficulty target: dropdown — Beginner / Intermediate / Advanced / Kaggle /
  Custom band (Custom reveals two metric-band inputs).
- Seed (optional; helper: "Leave blank for a recorded deterministic seed").
- Submit transitions into the Canvas.

STATES: loading (card skeletons), empty, populated, hover, delete-confirm — in
both themes.
DELIVERABLE: dashboard (populated + empty), a card in hover state, and the modal
(show the dashboard in Paper and Ink).
```

---

# Prompt 3 — Canvas: Table View + Inspector  [P1] (core workspace)

```
Design DataDoom's Canvas in TABLE VIEW with the contextual right Inspector
(route "/datasets/:id"). This is the core workspace. Use the design system
(editorial; both themes). TanStack Table for the schema grid; Recharts/Tremor for
the mini-histogram.

IMPORTANT MENTAL MODEL: the Table View defines SCHEMA, not data. Each column is a
feature in the spec. Every control maps to a spec field. Keep the workspace calm
and literate — editorial spacing, hairline rules, mono for all numeric params.

THREE REGIONS
1) TOP TOOLBAR: view toggle [Table | Graph]; a masked Seed input (eye toggle, mono);
   buttons: Validate (v), Estimate Run, View Spec (opens the YAML drawer), and a
   primary "Generate" CTA (Cmd/Ctrl+Enter). A small "unsaved changes • autosaved"
   indicator (the draft spec autosaves on every edit). Theme toggle remains in the
   top bar.
2) MAIN AREA — SCHEMA TABLE (a smart spreadsheet of columns = features):
   - Header row with a "+" to add a column (inserts feature_N).
   - Each column header: editable name in sans (double-click → inline input →
     Enter), a TYPE CHIP (numeric / categorical / boolean / datetime / text,
     colour-coded from the data-viz sequence), and a small "link" glyph if the
     column has a causal parent.
   - Drag column headers to reorder. Click a column to select it (highlight) and
     load it in the Inspector.
   - Show a few representative preview cells per column (mono; sampled client-side
     with a fixed preview seed) so the schema feels alive — caption it clearly as a
     preview, not the dataset.
   - Invalid params turn the column rule Ember with a tooltip naming the issue.
3) RIGHT INSPECTOR (contextual to the selected column). An editorial panel: a
   kicker with the feature name, controls per type, inline per-field validation:
   - NUMERIC: distribution dropdown (Normal, LogNormal, Poisson, Pareto, Uniform,
     Exponential, …+plugins); parameter inputs that change with the distribution
     (mean/std, mu/sigma, lam, alpha/xm, low/high, scale; mono); optional min/max
     clamp; int/float dtype toggle; a LIVE MINI-HISTOGRAM preview (client-sampled,
     fixed seed) that updates as params change.
   - CATEGORICAL: an editable category list (add/remove/reorder) + an interactive
     class-weight editor shown as bars/pie (for imbalance); weights normalize.
   - BOOLEAN: a base-rate slider (P(true)).
   - DATETIME: start/end range pickers + granularity (second/minute/hour/day).
   - TEXT: generator (lorem/…) + token length min/max.
   - RELATIONSHIPS (all types): "Add dependency" → pick parent column(s) +
     structural function (linear / logistic / polynomial / mapping / custom) +
     weight/params + noise σ. (This writes into the causal graph.)

INTERACTIONS: selecting a column smoothly swaps the Inspector; param edits live-
update the mini-histogram; everything is keyboard reachable; "g" toggles to Graph;
"t" toggles theme.
STATES: empty schema (one starter column + an editorial hint), a numeric column
selected (with histogram), a categorical column selected (weights), an
invalid-param state — in both themes.
DELIVERABLE: the Canvas table view with the toolbar, a populated schema, and the
Inspector in numeric + categorical states (show the workspace in Paper and Ink).
```

---

# Prompt 4 — Canvas: Graph View (Causal Visualizer)  [P2]

```
Design DataDoom's Canvas GRAPH VIEW — a causal DAG editor (same route, toggled
from Table view with "g"). Use the design system (editorial; both themes) and
React Flow (+ dagre auto-layout).

CONTEXT: columns = nodes, dependencies = directed edges (structural equations).
The graph must be acyclic; cycles are rejected.

CANVAS
- React Flow canvas on the --bg with a subtle dot grid (faint in both themes).
  Top-left: the same view toggle [Table | Graph]; top-right: "Auto-layout"
  (topological left→right), zoom/fit controls, and an "Intervention mode" toggle.
- NODES: a card per feature (editorial: feature name in the display serif, a small
  TYPE/DISTRIBUTION badge, mono detail, connection handles). Visually distinguish
  ROOT (sampled) nodes from DERIVED nodes (derived nodes get a Plasma-Violet accent
  ring; roots are neutral ink). Selected node syncs with the right Inspector.
- EDGES: directed, with an arrowhead; label shows the structural function in mono
  (e.g. "linear ·w=800"). Use smooth-step edges; hairline weight.

INTERACTIONS
- Create edge: drag from a node handle to another → opens a STRUCTURAL-FUNCTION
  EDITOR popover (function dropdown: linear / logistic / polynomial / map /
  identity / plugin; weight/bias/coeffs/mapping fields as appropriate; noise σ).
- CYCLE DETECTION: an edge that would create a cycle flashes Ember and is
  rejected with a Sonner toast: "Causal loops (cycles) are not permitted."
- INTERVENTION MODE: toggling lets the user set do(X = x) on a node; its incoming
  edges visually detach (dimmed/dashed) to show the counterfactual cut.
DELIVERABLE: the graph editor with ~5 nodes and a few edges (one labeled), the
structural-function editor popover, and the cycle-rejected toast state (both themes).
```

---

# Prompt 5 — Pre-Flight + Generation Tracker (real-time)  [P1]

```
Design DataDoom's Pre-Flight panel and the real-time Generation Tracker
(route "/datasets/:id/run/:runId"). Use the design system (editorial; both themes).
Build a StageStepper component; updates arrive over WebSocket.

PART A — PRE-FLIGHT (slides down when "Estimate Run" or "Generate" is pressed)
- VALIDATION summary: DAG acyclicity, parameter validity, type/distribution
  compatibility, missing targets — each a pass/fail line (Signal-Green check or
  Ember issue naming the field/node).
- ESTIMATE: estimated runtime, RAM, output file size, #features, #edges, rendered
  as small PullStats in mono tabular-nums; clearly captioned "estimate" (local CPU
  model — NO cost/credits/GPU).
- On success the primary "Generate" button unlocks and gently pulses.

PART B — GENERATION TRACKER (the Canvas fades; a centered, editorial tracker appears)
- A kicker ("Generating") + the dataset name in the display serif, with the seed
  and spec_hash as mono chips beneath.
- A vertical STAGE STEPPER listing the canonical pipeline stages:
  Intake & Validate → Snapshot & Hash → Seed → Base Generation → Causal/SEM →
  Failure Injection* → Difficulty Calibration* → Compliance → Packaging
  (* shown only if that stage is enabled by the spec).
- Live streaming: completed stages get a Signal-Green check; the current stage
  shows a spinner/progress; pending stages are muted. Show overall % progress in
  mono.
- CONSOLE DRAWER: an expandable MONO log panel streaming lines like
  "[INFO] generated 50,000 rows for 'age'". Auto-scroll; toggle to expand.
- A "Cancel" button (cooperative cancellation; confirm).
- COMPLETION: a subtle success flash + a primary "View Results" button.
- FAILURE: the failed stage turns Ember; the console auto-expands to the error;
  offer "Retry" and "Edit Spec".
DELIVERABLE: the pre-flight panel (success), the tracker mid-run (one stage
spinning, console open), the completed state, and the failed state (both themes).
```

---

# Prompt 6 — Results & Evaluation  [P1]

```
Design DataDoom's Results & Evaluation screen (after a run completes). Use the
design system (editorial; both themes). Charts: Recharts/Tremor for histograms;
Nivo for the correlation heatmap; Glide Data Grid for the data preview. Treat this
like the MAGAZINE FEATURE SPREAD — the payoff — with a strong editorial layout.

HEADER: a kicker ("Evaluation") + dataset name + run in the display serif, plus
CHIPS for `seed` and `spec_hash` (mono, click to copy) and a reproducibility
PULL-QUOTE: "Regenerate from this spec + seed for identical data." A primary
"Export" button.

TABS:
1) DATA PREVIEW: a fast, virtualized grid (Glide Data Grid) of the first N rows;
   column headers show the feature type + distribution. Pagination/row count (mono).
2) SCHEMA SUMMARY: a compact editorial list/table of features with type,
   distribution, and key params (mono).
3) DISTRIBUTIONS: a grid of per-feature cards; each card = a histogram of the
   generated values with the TARGET distribution overlaid, plus an honest
   "KS D=… p=…" chip and a pass/near/fail colour (Green/Amber/Ember). Caption that
   occasional non-pass is expected sampling variance / clamping, not a defect.
4) CORRELATION MATRIX: a Nivo heatmap (use the data-viz palette tuned per theme);
   hovering a cell shows the exact coefficient. Include a toggle between Pearson
   correlation and mutual information if present.
5) EVALUATION REPORT: the trust payload, laid out like a feature article —
   - COMPLIANCE SCORE as a big serif PULL-STAT (e.g. 98%) + per-feature
     Target vs Actual table (mono).
   - ACHIEVED DIFFICULTY vs target band, plus the probe model used and iterations.
   - TRUE CAUSAL GRAPH rendered as ground truth (a small read-only React Flow or
     static DAG) — this is a key differentiator; give it a prominent figure block
     with a caption.

FAILURE-INJECTION FORK: a call-out card at the bottom of the report:
"Stress-test your model. Inject failures?" → buttons "Keep Clean Only" /
"Create Failure-Injected Variant" (the latter uses the Ember accent).
DELIVERABLE: the Results screen across all five tabs (Distributions and the
Evaluation Report are the priority), plus the header chips and the fork call-out
(show the spread in both Paper and Ink).
```

---

# Prompt 7 — Failure Injection Configurator + Comparison  [P3]

```
Design DataDoom's Failure Injection Configurator and the Clean-vs-Injected
Comparison view. Use the design system (editorial; both themes). The Ember/hazard
accent LEADS here — this is the "doom" surface — but stay precise and scientific,
not gimmicky. Editorially, treat it as the "errata / corruption" section.

CONFIGURATOR (split screen)
- LEFT: live "clean" stats (retention bar, class balance, key distributions; mono).
- RIGHT: failure tools as ACCORDIONS, each with sliders/inputs:
  - Missingness: MCAR / MAR / MNAR — rate + driver column(s).
  - Noise: feature noise / label noise — rate + params.
  - Drift: concept drift over index/time — schedule.
  - Covariate Shift: target distribution shift.
  - Leakage: plant a leaky proxy for the target.
  Failures are an ORDERED list (they apply in sequence); allow reordering.
- LIVE DIFF PREVIEW: adjusting any slider updates an "expected impact" visual on
  the LEFT (e.g. the data-retention bar dropping, class balance shifting). Make
  cause→effect obvious and immediate.
- A primary "Inject" runs a mini generation tracker; the CLEAN baseline is ALWAYS
  preserved alongside the injected variant.

COMPARISON VIEW (side-by-side Clean vs Injected)
- Highlight concrete changes in plain editorial language, e.g.:
  "`income` now 12% null (MNAR, driver=education)",
  "`is_fraud` label flipped on 3% of rows".
- Per-column before/after mini-charts; a summary of total cells changed (mono).
DELIVERABLE: the configurator with two accordions open and a live diff on the
left, plus the comparison view (both themes).
```

---

# Prompt 8 — Difficulty selector + evaluation report  [P4]

```
Design DataDoom's Difficulty targeting controls and its evaluation readout. Use
the design system (editorial; both themes). (These can live in the Create modal /
Canvas toolbar and in the Results > Evaluation tab.)

SELECTOR
- A segmented control / dropdown of tiers: Beginner, Intermediate, Advanced,
  Kaggle, plus "Custom band". Show each tier's documented metric band (e.g. AUROC
  range) as a helper caption. Custom reveals task + metric + [low, high] band inputs.
- A "label" picker (which feature the probe predicts) and a probe selector
  (logreg / tree / plugin).

EVALUATION READOUT (honest)
- A horizontal band visual: the TARGET band as a shaded range, with a marker for
  the ACHIEVED metric. Green if inside the band, Amber if close, Ember if missed.
- Show: achieved metric, target band, probe model used, and iterations taken
  (mono). If the band wasn't met within max_iters, say so plainly (no silent
  failure).
DELIVERABLE: the selector (Kaggle + Custom states) and the achieved-vs-target
band readout (hit and missed states) — both themes.
```

---

# Prompt 9 — Export modal  [P1]

```
Design DataDoom's Export modal (shadcn Dialog). Use the design system (editorial;
both themes).

CONTROLS
- VERSION: Clean / Injected / Both (Injected disabled if no injected variant).
- FORMAT: CSV / Parquet / JSON (note plugins can add more).
- SPLITS: toggles + ratio inputs for train / test / hidden_test; show that ratios
  must sum to 1.0 (live validate).
- INCLUDE: a "metadata bundle" checkbox (spec.datadoom.yaml, metadata.json,
  report.html).
- "Download Spec" is ALWAYS available and visually emphasized (editorial emphasis —
  it's the shareable, reproducible artifact, the product's soul).
- Primary "Export" button shows a progress circle while files are written locally,
  then offers the download(s).
STATES: default, splits-invalid (sum≠1.0), exporting (progress), done — both themes.
DELIVERABLE: the modal in default and exporting states (Paper + Ink).
```

---

# Prompt 10 — Templates Gallery  [P5]

```
Design DataDoom's Templates Gallery (route "/templates"). Use the design system
(editorial; both themes). Treat it like a magazine's "collections" page.

- A grid of TEMPLATE CARDS per domain: Financial Fraud, E-commerce Churn,
  Healthcare Readmission, etc. Each card: title in the display serif, a one-line
  problem description (serif prose), a domain icon, tags, and a "community" tag for
  plugin-provided templates.
- Click a card → a SLIDE-OVER preview showing: the schema features, a small
  read-only causal graph, and the generated problem statement + metric.
- A primary "Use Template" clones the template's spec into a new draft dataset and
  opens the Canvas.
STATES: gallery, hover, slide-over preview, empty (no templates installed) — both
themes.
DELIVERABLE: the gallery + the slide-over preview (Paper + Ink).
```

---

# Prompt 11 — Plugins Browser  [P5]

```
Design DataDoom's Plugins browser (route "/plugins"). Use the design system
(editorial; both themes).

- A list/grid of installed plugins. Each row: name (display serif), KIND badge
  (distribution / structural_fn / failure_mode / exporter / template / probe_model),
  version (mono), an enabled toggle, and a short description (serif prose).
- A detail panel shows the plugin's declared parameter schema (rendered as a
  read-only form preview, since the UI auto-renders plugin schemas elsewhere).
- An empty state explaining that plugins are discovered from installed Python
  packages and a local plugins directory (offline; no marketplace fetch).
DELIVERABLE: the plugins list with mixed kinds + a detail panel + empty state
(both themes).
```

---

# Prompt 12 — Settings  [P1-lite]

```
Design DataDoom's Settings (route "/settings"). Use the design system (editorial;
both themes). Keep it minimal and local-first.

SECTIONS (editorial list with kickers + hairline rules)
- Appearance: THEME — Paper (light, default) / Ink (dark) / System — as the
  primary control here, with a live preview swatch of each; plus an optional
  "reduce motion" note that respects the OS setting.
- Generation defaults: default seed behavior (record a deterministic seed vs.
  prompt each time), default difficulty tier.
- Storage: the local storage path (read-only, mono, with a "reveal in file
  manager" affordance) and a "garbage-collect old runs" action (confirm).
- About: version (mono), links to docs/spec reference, and a clear pull-quote
  statement: "No telemetry — runs fully offline."
DELIVERABLE: the settings screen with the sections above, shown in Paper and Ink
(the Appearance/theme section is the priority).
```

---

## Appendix A — Data shapes the UI binds to (so screens look real)

- **Spec** (the edited document): `datadoom_version`, `name`, `description?`,
  `seed?`, `rows`, `features{ name -> feature }`, `causal?`, `difficulty?`,
  `failures[]`, `export`, `meta`.
- **Feature** by `type`:
  - numeric: `dist`, `params{}`, `min?`, `max?`, `dtype(int|float)`
  - categorical: `categories[]`, `weights[]?`
  - boolean: `rate`
  - datetime: `start`, `end`, `granularity`, `dist`
  - text: `generator`, `length{min,max}`
- **Causal**: `edges[]` of `{from, to, fn, weight?, bias?, coeffs?, mapping?}`,
  `noise{ node -> {dist, params} }`, `interventions[]`.
- **Difficulty**: `target (tier | {task,metric,band:[a,b]})`, `label`, `probe`,
  `max_iters`, `knobs[]`.
- **Failure** item: `{ type, ...type-specific (column/columns, rate, driver,
  target, into, schedule, dist, params) }`.
- **Report** (Results screen): `compliance_score`, per-feature
  `{target_params, empirical, ks_statistic, p_value, passed, clamped_fraction}`,
  `correlation` (Pearson + MI matrices), `causal_truth` (the true DAG),
  `difficulty` (target band, achieved, probe, iterations), `failures` (diff
  summaries), `determinism` (spec_hash, seed, namespace key digests, checksums).
- **Generation stages** (tracker): Intake & Validate, Snapshot & Hash, Seed,
  Base Generation, Causal/SEM, Failure Injection, Difficulty Calibration,
  Compliance, Packaging.
- **Status values**: dataset = Draft / Running / Completed / Failed; run =
  queued / running / completed / failed / cancelled.

> These shapes are now served by the Phase-1 API. The frontend generates its
> client from `/api/openapi.json`; live progress arrives on
> `/api/ws/runs/{run_id}` (SSE fallback `/api/runs/{run_id}/events`). In P1 the
> Report fills `compliance_score`, `distribution`, `correlation`, and
> `determinism`; `causal_truth`/`difficulty`/`failures` arrive in P2–P4 (design
> their empty/"not yet computed" states now so the layout is stable).

## Appendix B — Build order (matches the roadmap)

1. Prompt 0 (design system, BOTH themes) → 2. Prompt 1 (first run) →
3. Prompt 2 (dashboard) → 4. Prompt 3 (Canvas Table + Inspector) →
5. Prompt 5 (tracker) → 6. Prompt 6 (results) → 7. Prompt 9 (export). That set is
the **P1 MVP**. Then Prompt 4 (graph, P2), 7 (failures, P3), 8 (difficulty, P4),
10/11 (templates/plugins, P5), 12 (settings, anytime).

## Appendix C — References (component & design guidance)

- shadcn/ui (base components): https://www.shadcn.io/ and
  https://designrevision.com/blog/shadcn-ui-guide
- Editorial / magazine typography & systems (Fraunces, Newsreader, scale & rhythm):
  https://fonts.google.com/specimen/Fraunces ,
  https://fonts.google.com/specimen/Newsreader ,
  https://practicaltypography.com/
- React UI library landscape 2026:
  https://www.untitledui.com/blog/react-component-libraries
- React Flow (causal graph) + dagre layout: https://reactflow.dev/ ,
  https://reactflow.dev/examples , https://reactflow.dev/examples/layout/dagre
- Data grids (TanStack Table / Glide / react-data-grid):
  https://tanstack.com/table/latest ,
  https://www.pkgpulse.com/guides/tanstack-table-vs-ag-grid-vs-react-data-grid-2026
- Charts (Recharts/Tremor for histograms, Nivo for heatmaps):
  https://www.pkgpulse.com/guides/recharts-v3-vs-tremor-vs-nivo-react-charting-2026 ,
  https://www.tremor.so/
- Light/dark theming & OKLCH tokens (both themes from one token set):
  https://evilmartians.com/chronicles/exploring-the-oklch-ecosystem-and-its-tools ,
  https://web.dev/articles/building-a-color-scheme
```
