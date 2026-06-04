import { Gauge, Sparkles, Trash2 } from "lucide-react";
import { Button, Card, Kicker } from "./ui";
import { BandMeter } from "./DifficultyView";
import {
  ALL_KNOBS,
  KNOB_META,
  PROBES,
  TIERS,
  bandOf,
  defaultDifficulty,
  isTier,
  labelableColumns,
  validateDifficultyClient,
} from "@/lib/difficulty";
import { clsx } from "@/lib/clsx";
import type { Difficulty, DifficultyKnob, Spec } from "@/lib/types";

export function DifficultyConfigurator({
  spec,
  onChange,
}: {
  spec: Spec;
  onChange: (d: Difficulty | null) => void;
}) {
  const labels = labelableColumns(spec);
  const d = spec.difficulty ?? null;

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto max-w-2xl px-6 py-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-control bg-primary-tint text-primary">
            <Gauge size={18} />
          </span>
          <div>
            <h2 className="font-display text-xl font-semibold leading-tight">Difficulty targeting</h2>
            <p className="text-xs text-text-muted">
              Calibrate the dataset to a baseline-model AUROC band — empirical, not a guess.
            </p>
          </div>
        </div>

        {labels.length === 0 ? (
          <Card className="mt-5 border-dashed p-6 text-sm text-text-muted">
            Difficulty needs a <strong>binary label</strong> — a boolean column, or a categorical with
            exactly two categories. Add one in the <strong>Table</strong> view, then return here.
          </Card>
        ) : d == null ? (
          <Card className="mt-5 flex flex-col items-start gap-3 border-dashed p-6">
            <p className="text-sm text-text-muted">
              Off — the dataset ships at its natural difficulty. Turn it on to tune how hard the label is
              to predict.
            </p>
            <Button variant="primary" onClick={() => onChange(defaultDifficulty(spec))}>
              <Sparkles size={15} /> Enable difficulty targeting
            </Button>
          </Card>
        ) : (
          <Editor spec={spec} d={d} labels={labels} onChange={onChange} />
        )}
      </div>
    </div>
  );
}

function Editor({
  spec,
  d,
  labels,
  onChange,
}: {
  spec: Spec;
  d: Difficulty;
  labels: string[];
  onChange: (d: Difficulty | null) => void;
}) {
  const set = (patch: Partial<Difficulty>) => onChange({ ...d, ...patch });
  const custom = !isTier(d.target);
  const band = bandOf(d.target);
  const error = validateDifficultyClient(d, spec);

  return (
    <div className="mt-5 space-y-5">
      {/* Target */}
      <section>
        <Kicker>Target band</Kicker>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {TIERS.map((t) => {
            const on = !custom && d.target === t.tier;
            return (
              <button
                key={t.tier}
                onClick={() => set({ target: t.tier })}
                className={clsx(
                  "ring-focus rounded-control border px-3 py-2.5 text-left transition-colors",
                  on ? "border-primary bg-primary-tint" : "border-border hover:border-border-strong",
                )}
              >
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-semibold">{t.label}</span>
                  <span className="font-mono text-[11px] text-text-muted tnum">
                    {t.band[0].toFixed(2)}–{t.band[1].toFixed(2)}
                  </span>
                </div>
                <p className="mt-0.5 text-[11px] leading-snug text-text-faint">{t.blurb}</p>
              </button>
            );
          })}
          <button
            onClick={() => set({ target: custom ? d.target : { metric: "auroc", band } })}
            className={clsx(
              "ring-focus col-span-2 rounded-control border px-3 py-2 text-left text-sm font-medium transition-colors",
              custom ? "border-primary bg-primary-tint text-primary" : "border-border text-text-muted hover:text-text",
            )}
          >
            Custom band…
          </button>
        </div>

        {custom && (
          <div className="mt-2 grid grid-cols-2 gap-2">
            <label className="block">
              <span className="text-xs font-medium text-text-muted">Low AUROC</span>
              <NumInput value={band[0]} onChange={(v) => set({ target: { metric: "auroc", band: [v, band[1]] } })} />
            </label>
            <label className="block">
              <span className="text-xs font-medium text-text-muted">High AUROC</span>
              <NumInput value={band[1]} onChange={(v) => set({ target: { metric: "auroc", band: [band[0], v] } })} />
            </label>
          </div>
        )}

        <div className="mt-3">
          <BandMeter band={band} />
        </div>
      </section>

      {/* Label + probe */}
      <section className="grid grid-cols-2 gap-3">
        <label className="block">
          <Kicker>Label to predict</Kicker>
          <Select value={d.label} options={labels} onChange={(label) => set({ label })} />
        </label>
        <label className="block">
          <Kicker>Baseline probe</Kicker>
          <Select value={d.probe} options={PROBES.map((p) => p.value)} onChange={(probe) => set({ probe: probe as Difficulty["probe"] })} />
        </label>
      </section>

      {/* Knobs */}
      <section>
        <Kicker>Difficulty knobs</Kicker>
        <p className="mt-1 text-[11px] text-text-faint">
          Composed into one bisection dial: feature noise first, label flips as the deep end.
        </p>
        <div className="mt-2 space-y-2">
          {ALL_KNOBS.map((k) => {
            const on = d.knobs.includes(k);
            return (
              <button
                key={k}
                onClick={() => toggleKnob(d, k, set)}
                className={clsx(
                  "ring-focus flex w-full items-start gap-2.5 rounded-control border px-3 py-2.5 text-left transition-colors",
                  on ? "border-primary bg-primary-tint" : "border-border hover:border-border-strong",
                )}
              >
                <span
                  className={clsx(
                    "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-[5px] border",
                    on ? "border-primary bg-primary text-white" : "border-border-strong",
                  )}
                >
                  {on && <span className="text-[10px] leading-none">✓</span>}
                </span>
                <span>
                  <span className="text-sm font-medium">{KNOB_META[k].label}</span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-text-faint">{KNOB_META[k].blurb}</span>
                </span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Iterations */}
      <section className="grid grid-cols-2 gap-3">
        <label className="block">
          <Kicker>Max iterations</Kicker>
          <NumInput value={d.max_iters} step={1} onChange={(v) => set({ max_iters: Math.max(1, Math.round(v)) })} />
        </label>
      </section>

      {error && (
        <div className="rounded-control border border-warning bg-warning-tint px-3 py-2 text-xs text-warning">
          {error}
        </div>
      )}

      <p className="rounded-control border border-border bg-surface-2 px-3 py-2.5 text-[11px] leading-relaxed text-text-faint">
        The clean baseline is captured first; calibration bakes feature-observation noise (and label flips
        if needed) into the shipped dataset and reports the achieved AUROC honestly — including when a band
        can't be reached. Causal structure you authored is preserved.
      </p>

      <button
        onClick={() => onChange(null)}
        className="ring-focus inline-flex items-center gap-1.5 rounded-control px-2 py-1.5 text-xs font-medium text-text-faint transition-colors hover:bg-hazard-tint hover:text-hazard"
      >
        <Trash2 size={14} /> Disable difficulty targeting
      </button>
    </div>
  );
}

function toggleKnob(d: Difficulty, k: DifficultyKnob, set: (p: Partial<Difficulty>) => void) {
  const has = d.knobs.includes(k);
  // Keep canonical order (noise before label_noise) so the spec hash is stable.
  const next = ALL_KNOBS.filter((x) => (x === k ? !has : d.knobs.includes(x)));
  set({ knobs: next });
}

// --- small form primitives (mirroring FailureInspector) -----------------------

function NumInput({ value, onChange, step }: { value: number | undefined; onChange: (n: number) => void; step?: number }) {
  return (
    <input
      type="number"
      step={step ?? 0.01}
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
      className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
    />
  );
}

function Select({ value, options, onChange }: { value: string; options: string[]; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
