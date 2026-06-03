import { Trash2 } from "lucide-react";
import { Kicker } from "./ui";
import { FailureIcon } from "./FailureBadges";
import {
  FAILURE_META,
  columnKinds,
  impactEstimate,
  leakTarget,
  shiftTarget,
  validateFailureClient,
} from "@/lib/failures";
import { DIST_PARAMS, NUMERIC_DISTS } from "@/lib/specDefaults";
import { clsx } from "@/lib/clsx";
import type { Failure, Spec } from "@/lib/types";

export function FailureInspector({
  failure,
  index,
  spec,
  onChange,
  onDelete,
}: {
  failure: Failure;
  index: number;
  spec: Spec;
  onChange: (f: Failure) => void;
  onDelete: () => void;
}) {
  const meta = FAILURE_META[failure.type];
  const k = columnKinds(spec);
  const impact = impactEstimate(failure, spec.rows);
  const error = validateFailureClient(failure, spec);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <Kicker>Failure step {index + 1}</Kicker>
        <div className="mt-1.5 flex items-center gap-2.5">
          <span
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control"
            style={{ color: meta.accent, background: `color-mix(in srgb, ${meta.accent} 14%, transparent)` }}
          >
            <FailureIcon type={failure.type} size={16} />
          </span>
          <div className="min-w-0">
            <div className="truncate font-display text-lg font-semibold leading-tight">{meta.label}</div>
            <div className="text-[11px] font-medium" style={{ color: meta.accent }}>
              {meta.category}
            </div>
          </div>
        </div>
        <p className="mt-2.5 text-xs leading-relaxed text-text-muted">{meta.blurb}</p>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        <Controls failure={failure} kinds={k} onChange={onChange} />

        {/* Live impact estimate */}
        <div className="mt-4 rounded-control border border-border bg-surface-2 p-3">
          <div className="flex items-center justify-between">
            <Kicker>Estimated impact</Kicker>
            {impact.metric && (
              <span
                className="rounded-pill px-2 py-0.5 font-mono text-[11px] font-semibold"
                style={{ color: meta.accent, background: `color-mix(in srgb, ${meta.accent} 12%, transparent)` }}
              >
                {impact.metric}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-xs leading-relaxed text-text-muted">{impact.line}</p>
          <p className="mt-2 border-t border-border pt-2 font-mono text-[10.5px] leading-relaxed text-text-faint">
            {meta.math}
          </p>
        </div>

        {error && (
          <div className="mt-3 rounded-control border border-warning bg-warning-tint px-3 py-2 text-xs text-warning">
            {error}
          </div>
        )}
      </div>

      <div className="border-t border-border p-4">
        <button
          onClick={onDelete}
          className="ring-focus inline-flex items-center gap-1.5 rounded-control px-2 py-1.5 text-xs font-medium text-text-faint transition-colors hover:bg-hazard-tint hover:text-hazard"
        >
          <Trash2 size={14} /> Remove step
        </button>
      </div>
    </div>
  );
}

// --- form primitives ----------------------------------------------------------

function Row({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="mb-3 block">
      <span className="text-xs font-medium text-text-muted">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[11px] text-text-faint">{hint}</span>}
    </label>
  );
}

function NumInput({
  value,
  onChange,
  placeholder,
  step,
}: {
  value: number | undefined;
  onChange: (n: number | undefined) => void;
  placeholder?: string;
  step?: number;
}) {
  return (
    <input
      type="number"
      step={step}
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value === "" ? undefined : Number(e.target.value))}
      className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
    />
  );
}

function Select({
  value,
  options,
  onChange,
  placeholder,
}: {
  value: string | undefined;
  options: string[];
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value)}
      className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (n: number) => void;
}) {
  return (
    <Row label={label}>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 w-full accent-[var(--primary)]"
      />
    </Row>
  );
}

function ColumnChips({
  selected,
  options,
  onToggle,
}: {
  selected: string[];
  options: string[];
  onToggle: (name: string) => void;
}) {
  if (options.length === 0) return <p className="mt-1 text-xs text-text-faint">No columns available.</p>;
  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {options.map((c) => {
        const on = selected.includes(c);
        return (
          <button
            key={c}
            onClick={() => onToggle(c)}
            className={clsx(
              "ring-focus rounded-pill border px-2.5 py-1 text-xs font-medium transition-colors",
              on
                ? "border-primary bg-primary-tint text-primary"
                : "border-border text-text-muted hover:border-border-strong hover:text-text",
            )}
          >
            {c}
          </button>
        );
      })}
    </div>
  );
}

// --- per-type controls --------------------------------------------------------

function Controls({
  failure: f,
  kinds: k,
  onChange,
}: {
  failure: Failure;
  kinds: ReturnType<typeof columnKinds>;
  onChange: (f: Failure) => void;
}) {
  const ratePct = `${Math.round((f.rate ?? 0) * 100)}%`;

  switch (f.type) {
    case "mcar":
      return (
        <>
          <Row label="Columns to blank">
            <ColumnChips
              selected={f.columns ?? []}
              options={k.all}
              onToggle={(name) => {
                const set = new Set(f.columns ?? []);
                set.has(name) ? set.delete(name) : set.add(name);
                onChange({ ...f, columns: k.all.filter((c) => set.has(c)) });
              }}
            />
          </Row>
          <Slider label={`Missing rate · ${ratePct}`} value={f.rate ?? 0} min={0} max={1} step={0.01} onChange={(rate) => onChange({ ...f, rate })} />
        </>
      );

    case "mar":
      return (
        <>
          <Row label="Column to make missing">
            <Select value={f.column} options={k.all} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <Row label="Driver (observed)" hint="Missingness rises with this column. Must be numeric or boolean.">
            <Select value={f.driver} options={k.numericOrBool} onChange={(driver) => onChange({ ...f, driver })} placeholder="Select a driver" />
          </Row>
          <Slider label={`Missing rate · ${ratePct}`} value={f.rate ?? 0} min={0} max={1} step={0.01} onChange={(rate) => onChange({ ...f, rate })} />
          <Slider label={`Dependence strength · ${(f.strength ?? 2).toFixed(1)}`} value={f.strength ?? 2} min={0} max={6} step={0.5} onChange={(strength) => onChange({ ...f, strength })} />
        </>
      );

    case "mnar":
      return (
        <>
          <Row label="Column (drives its own missingness)">
            <Select value={f.column} options={k.numericOrBool} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <Slider label={`Missing rate · ${ratePct}`} value={f.rate ?? 0} min={0} max={1} step={0.01} onChange={(rate) => onChange({ ...f, rate })} />
          <Slider label={`Dependence strength · ${(f.strength ?? 2).toFixed(1)}`} value={f.strength ?? 2} min={0} max={6} step={0.5} onChange={(strength) => onChange({ ...f, strength })} />
        </>
      );

    case "label_noise":
      return (
        <>
          <Row label="Label column" hint="Boolean or categorical.">
            <Select value={f.column} options={k.labelable} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <Slider label={`Flip rate · ${ratePct}`} value={f.rate ?? 0} min={0} max={1} step={0.01} onChange={(rate) => onChange({ ...f, rate })} />
        </>
      );

    case "feature_noise": {
      const params = f.params ?? {};
      return (
        <>
          <Row label="Numeric column">
            <Select value={f.column} options={k.numeric} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <Row label="Noise distribution">
            <Select
              value={f.dist}
              options={NUMERIC_DISTS}
              onChange={(dist) => onChange({ ...f, dist, params: DIST_PARAMS[dist] })}
            />
          </Row>
          <div className="grid grid-cols-2 gap-2">
            {Object.keys(params).map((key) => (
              <Row key={key} label={key}>
                <NumInput value={params[key]} onChange={(n) => onChange({ ...f, params: { ...params, [key]: n ?? 0 } })} />
              </Row>
            ))}
          </div>
        </>
      );
    }

    case "drift": {
      const sched = f.schedule ?? { kind: "linear" };
      return (
        <>
          <Row label="Numeric column">
            <Select value={f.column} options={k.numeric} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <Row label="Schedule">
            <div className="mt-1 inline-flex rounded-control border border-border p-0.5">
              {(["linear", "step"] as const).map((kind) => (
                <button
                  key={kind}
                  onClick={() => onChange({ ...f, schedule: { ...sched, kind } })}
                  className={clsx(
                    "ring-focus rounded-[7px] px-3 py-1 text-xs capitalize",
                    (sched.kind ?? "linear") === kind ? "bg-primary-tint text-primary" : "text-text-muted",
                  )}
                >
                  {kind}
                </button>
              ))}
            </div>
          </Row>
          <Row label="Total shift (magnitude)" hint="Amount added by the last row.">
            <NumInput value={sched.magnitude} onChange={(n) => onChange({ ...f, schedule: { ...sched, magnitude: n } })} />
          </Row>
          {(sched.kind ?? "linear") === "step" && (
            <Row label="Step at (fraction of rows)">
              <NumInput value={sched.at ?? 0.5} step={0.05} onChange={(n) => onChange({ ...f, schedule: { ...sched, at: n } })} />
            </Row>
          )}
        </>
      );
    }

    case "covariate_shift": {
      const t = shiftTarget(f);
      return (
        <>
          <Row label="Numeric column">
            <Select value={f.column} options={k.numeric} onChange={(column) => onChange({ ...f, column })} placeholder="Select a column" />
          </Row>
          <div className="grid grid-cols-2 gap-2">
            <Row label="target mean">
              <NumInput value={t.mean} placeholder="—" onChange={(n) => onChange({ ...f, target: { ...t, mean: n } })} />
            </Row>
            <Row label="target std" hint="optional">
              <NumInput value={t.std} placeholder="keep" onChange={(n) => onChange({ ...f, target: { ...t, std: n } })} />
            </Row>
          </div>
        </>
      );
    }

    case "leakage": {
      const eta = f.noise ?? 0.05;
      const corr = 1 / Math.sqrt(1 + eta * eta);
      return (
        <>
          <Row label="Target to leak" hint="Numeric or boolean label.">
            <Select value={leakTarget(f)} options={k.numericOrBool} onChange={(target) => onChange({ ...f, target })} placeholder="Select a target" />
          </Row>
          <Row label="Planted column name">
            <input
              value={f.into ?? ""}
              onChange={(e) => onChange({ ...f, into: e.target.value })}
              spellCheck={false}
              placeholder="leak"
              className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
            />
          </Row>
          <Slider label={`Proxy noise · ${eta.toFixed(2)} → corr ${corr.toFixed(3)}`} value={eta} min={0.01} max={0.5} step={0.01} onChange={(noise) => onChange({ ...f, noise })} />
        </>
      );
    }
  }
}
