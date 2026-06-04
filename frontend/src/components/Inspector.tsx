import { Check, ChevronDown, Plus, Trash2, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Kicker, Menu, MenuItem } from "./ui";
import { clsx } from "@/lib/clsx";
import { Histogram } from "./Histogram";
import { DIST_PARAMS, NUMERIC_DISTS } from "@/lib/specDefaults";
import { previewNumeric } from "@/lib/sampling";
import type { Feature } from "@/lib/types";
import { TEXT_GENERATORS, TEXT_LOCALES } from "@/lib/types";

const FEATURE_TYPES: Feature["type"][] = ["numeric", "categorical", "boolean", "datetime", "text", "timeseries"];

export function Inspector({
  name,
  feature,
  siblingNames,
  onChange,
  onRename,
  onChangeType,
  onDelete,
  locatorError,
}: {
  name: string;
  feature: Feature;
  siblingNames: string[];
  onChange: (f: Feature) => void;
  onRename: (next: string) => void;
  onChangeType: (t: Feature["type"]) => void;
  onDelete: () => void;
  locatorError?: string | null;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border p-4">
        <Kicker>Column inspector</Kicker>
        <NameEditor name={name} siblingNames={siblingNames} onRename={onRename} />
        <div className="mt-3 flex flex-wrap gap-1">
          {FEATURE_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => onChangeType(t)}
              className={
                "ring-focus rounded-pill px-2.5 py-1 text-[11px] font-medium capitalize transition-colors " +
                (feature.type === t
                  ? "bg-primary-tint text-primary"
                  : "text-text-faint hover:bg-surface-2 hover:text-text")
              }
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-4">
        {feature.type === "numeric" && <NumericControls f={feature} onChange={onChange} />}
        {feature.type === "categorical" && <CategoricalControls f={feature} onChange={onChange} />}
        {feature.type === "boolean" && <BooleanControls f={feature} onChange={onChange} />}
        {feature.type === "datetime" && <DatetimeControls f={feature} onChange={onChange} />}
        {feature.type === "text" && <TextControls f={feature} onChange={onChange} />}
        {feature.type === "timeseries" && <TimeseriesControls f={feature} onChange={onChange} />}

        {locatorError && (
          <div className="mt-4 rounded-control border border-hazard bg-hazard-tint px-3 py-2 text-xs text-hazard">
            {locatorError}
          </div>
        )}

        <LatentToggle feature={feature} onChange={onChange} />
      </div>

      <div className="border-t border-border p-4">
        <button
          onClick={onDelete}
          className="ring-focus inline-flex items-center gap-1.5 rounded-control px-2 py-1.5 text-xs font-medium text-text-faint transition-colors hover:bg-hazard-tint hover:text-hazard"
        >
          <Trash2 size={14} /> Delete column
        </button>
      </div>
    </div>
  );
}

/** Local-draft name editor: commits on blur/Enter, validates non-empty + unique. */
function NameEditor({
  name,
  siblingNames,
  onRename,
}: {
  name: string;
  siblingNames: string[];
  onRename: (next: string) => void;
}) {
  const [draft, setDraft] = useState(name);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setDraft(name);
    setErr(null);
  }, [name]);

  function commit() {
    const next = draft.trim();
    if (next === name) {
      setErr(null);
      return;
    }
    if (!next) {
      setErr("Name can't be empty");
      setDraft(name);
      return;
    }
    if (siblingNames.includes(next)) {
      setErr("A column with that name already exists");
      return;
    }
    setErr(null);
    onRename(next);
  }

  return (
    <div className="mt-1.5">
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") (e.target as HTMLInputElement).blur();
          if (e.key === "Escape") {
            setDraft(name);
            setErr(null);
            (e.target as HTMLInputElement).blur();
          }
        }}
        spellCheck={false}
        className="ring-focus w-full rounded-control bg-transparent font-display text-xl font-semibold tracking-tight outline-none focus:bg-surface-2 focus:px-2 focus:py-1"
      />
      {err && <p className="mt-1 text-xs text-hazard">{err}</p>}
    </div>
  );
}

/** Latent (`emit: false`) toggle — applies to any feature type. */
function LatentToggle({ feature, onChange }: { feature: Feature; onChange: (f: Feature) => void }) {
  const latent = feature.emit === false;
  return (
    <label className="mt-5 flex cursor-pointer items-start gap-2.5 rounded-control border border-border bg-surface-2 px-3 py-2.5">
      <input
        type="checkbox"
        checked={latent}
        onChange={(e) => onChange({ ...feature, emit: e.target.checked ? false : undefined })}
        className="mt-0.5 h-4 w-4 accent-[var(--primary)]"
      />
      <span className="text-xs">
        <span className="font-medium text-text">Latent (not exported)</span>
        <span className="mt-0.5 block leading-snug text-text-faint">
          Drives sampling / the causal graph but is <strong>not shipped</strong> — excluded from the data,
          the difficulty probe, and compliance. Use for hidden confounders or a latent score behind a label.
        </span>
      </span>
    </label>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-3 block">
      <span className="text-xs font-medium text-text-muted">{label}</span>
      {children}
    </label>
  );
}

function NumInput({ value, onChange }: { value: number | undefined; onChange: (n: number) => void }) {
  return (
    <input
      type="number"
      value={value ?? ""}
      onChange={(e) => onChange(Number(e.target.value))}
      className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
    />
  );
}

function NumericControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "numeric" }>;
  onChange: (f: Feature) => void;
}) {
  const isDerived = f.dist == null;
  const dist = f.dist ?? "normal";
  const params = f.params ?? {};
  const preview = previewNumeric(dist, params);

  if (isDerived) {
    return (
      <>
        <div className="rounded-control border border-dashed border-border bg-surface-2 p-3 text-sm text-text-muted">
          This column is <strong className="text-text">derived</strong> — its values come from its
          parents in the causal graph, not a sampled distribution. Edit its structural function in the
          Graph view, or detach its parents to make it samplable again.
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2">
          <Row label="min (clamp)">
            <NumInput value={f.min ?? undefined} onChange={(n) => onChange({ ...f, min: n })} />
          </Row>
          <Row label="max (clamp)">
            <NumInput value={f.max ?? undefined} onChange={(n) => onChange({ ...f, max: n })} />
          </Row>
        </div>
      </>
    );
  }

  return (
    <>
      <Row label="Distribution">
        <select
          value={dist}
          onChange={(e) => onChange({ ...f, dist: e.target.value, params: DIST_PARAMS[e.target.value] })}
          className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
        >
          {NUMERIC_DISTS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </Row>

      <div className="mb-3 rounded-control border border-border bg-surface-2 p-2">
        <Histogram values={preview} />
        <div className="kicker mt-1 text-center">preview · client-sampled</div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {Object.keys(params).map((k) => (
          <Row key={k} label={k}>
            <NumInput value={params[k]} onChange={(n) => onChange({ ...f, params: { ...params, [k]: n } })} />
          </Row>
        ))}
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        <Row label="min (clamp)">
          <NumInput value={f.min ?? undefined} onChange={(n) => onChange({ ...f, min: n })} />
        </Row>
        <Row label="max (clamp)">
          <NumInput value={f.max ?? undefined} onChange={(n) => onChange({ ...f, max: n })} />
        </Row>
      </div>

      <Row label="dtype">
        <div className="mt-1 inline-flex rounded-control border border-border p-0.5">
          {(["float", "int"] as const).map((d) => (
            <button
              key={d}
              onClick={() => onChange({ ...f, dtype: d })}
              className={
                "ring-focus rounded-[7px] px-3 py-1 text-xs " +
                ((f.dtype ?? "float") === d ? "bg-primary-tint text-primary" : "text-text-muted")
              }
            >
              {d}
            </button>
          ))}
        </div>
      </Row>
    </>
  );
}

function CategoricalControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "categorical" }>;
  onChange: (f: Feature) => void;
}) {
  const cats = f.categories ?? [];
  const weights = f.weights ?? cats.map(() => 1);
  const total = weights.reduce((a, b) => a + b, 0) || 1;
  return (
    <>
      <Kicker>Categories &amp; weights</Kicker>
      <div className="mt-2 space-y-1.5">
        {cats.map((c, i) => (
          <div key={i} className="flex items-center gap-2">
            <input
              value={c}
              onChange={(e) => {
                const next = [...cats];
                next[i] = e.target.value;
                onChange({ ...f, categories: next });
              }}
              className="ring-focus flex-1 rounded-control border border-border bg-surface-2 px-2 py-1 text-sm outline-none focus:border-primary"
            />
            <input
              type="number"
              value={weights[i]}
              onChange={(e) => {
                const next = [...weights];
                next[i] = Number(e.target.value);
                onChange({ ...f, weights: next });
              }}
              className="ring-focus w-16 rounded-control border border-border bg-surface-2 px-2 py-1 font-mono text-xs outline-none focus:border-primary"
            />
            <span className="w-10 text-right font-mono text-[11px] text-text-faint tnum">
              {Math.round((weights[i] / total) * 100)}%
            </span>
            <button
              onClick={() =>
                onChange({
                  ...f,
                  categories: cats.filter((_, j) => j !== i),
                  weights: weights.filter((_, j) => j !== i),
                })
              }
              className="ring-focus rounded text-text-faint hover:text-hazard"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange({ ...f, categories: [...cats, `cat_${cats.length + 1}`], weights: [...weights, 1] })}
        className="ring-focus mt-2 inline-flex items-center gap-1 rounded text-xs font-medium text-primary hover:underline"
      >
        <Plus size={13} /> Add category
      </button>
      <div className="mt-3 flex h-2 overflow-hidden rounded-pill">
        {weights.map((w, i) => (
          <div
            key={i}
            style={{
              width: `${(w / total) * 100}%`,
              background: ["var(--primary)", "var(--info)", "var(--warning)", "var(--success)", "var(--hazard)"][i % 5],
            }}
          />
        ))}
      </div>
    </>
  );
}

function BooleanControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "boolean" }>;
  onChange: (f: Feature) => void;
}) {
  return (
    <Row label={`Base rate · P(true) = ${(f.rate ?? 0.5).toFixed(2)}`}>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={f.rate ?? 0.5}
        onChange={(e) => onChange({ ...f, rate: Number(e.target.value) })}
        className="mt-2 w-full accent-[var(--primary)]"
      />
    </Row>
  );
}

function DatetimeControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "datetime" }>;
  onChange: (f: Feature) => void;
}) {
  return (
    <>
      <Row label="start">
        <input
          value={f.start ?? ""}
          onChange={(e) => onChange({ ...f, start: e.target.value })}
          placeholder="2020-01-01"
          className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
        />
      </Row>
      <Row label="end">
        <input
          value={f.end ?? ""}
          onChange={(e) => onChange({ ...f, end: e.target.value })}
          placeholder="2024-12-31"
          className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 font-mono text-sm outline-none focus:border-primary"
        />
      </Row>
      <Row label="granularity">
        <select
          value={f.granularity ?? "day"}
          onChange={(e) => onChange({ ...f, granularity: e.target.value as never })}
          className="ring-focus mt-1 w-full rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-sm outline-none focus:border-primary"
        >
          {["second", "minute", "hour", "day"].map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
      </Row>
    </>
  );
}

function TextControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "text" }>;
  onChange: (f: Feature) => void;
}) {
  const gen = f.generator ?? "lorem";
  const len = f.length ?? { min: 5, max: 30 };

  return (
    <>
      <Row label="Generator">
        <MenuSelect value={gen} groups={TEXT_GENERATORS} onChange={(v) => onChange({ ...f, generator: v })} />
      </Row>

      {gen === "lorem" ? (
        <div className="mt-2 grid grid-cols-2 gap-2">
          <Row label="min tokens">
            <NumInput value={len.min} onChange={(n) => onChange({ ...f, length: { ...len, min: n } })} />
          </Row>
          <Row label="max tokens">
            <NumInput value={len.max} onChange={(n) => onChange({ ...f, length: { ...len, max: n } })} />
          </Row>
        </div>
      ) : (
        <Row label="Locale">
          <MenuSelect value={f.locale ?? "en"} groups={[{ keys: TEXT_LOCALES }]} onChange={(v) => onChange({ ...f, locale: v })} />
        </Row>
      )}

      <p className="mt-3 text-xs italic text-text-faint">
        Realistic generators emit genuine-looking values (names, emails, addresses…) via mimesis, seeded
        from this column's stream — so the same spec + seed still reproduces byte-identical data.
      </p>
    </>
  );
}

function TimeseriesControls({
  f,
  onChange,
}: {
  f: Extract<Feature, { type: "timeseries" }>;
  onChange: (f: Feature) => void;
}) {
  const trend = f.trend ?? { slope: 0, intercept: 0 };
  const seasons = f.seasonality ?? [];
  const ar = f.ar ?? [];
  const arSum = ar.reduce((a, b) => a + Math.abs(b), 0);

  return (
    <>
      <p className="mb-3 text-xs italic text-text-faint">
        An ordered series <span className="not-italic font-mono">Xt = trend + Σ seasonality + AR(p) + noise</span>{" "}
        over the row index — row order is the time axis. May be a causal parent; never a target.
      </p>

      <Kicker>Trend</Kicker>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <Row label="slope (per row)">
          <NumInput value={trend.slope} onChange={(n) => onChange({ ...f, trend: { ...trend, slope: n } })} />
        </Row>
        <Row label="intercept">
          <NumInput value={trend.intercept} onChange={(n) => onChange({ ...f, trend: { ...trend, intercept: n } })} />
        </Row>
      </div>

      <Kicker>Seasonality</Kicker>
      <div className="mt-2 space-y-2">
        {seasons.map((s, i) => (
          <div key={i} className="rounded-control border border-border bg-surface-2 p-2">
            <div className="grid grid-cols-3 gap-2">
              <Row label="amplitude">
                <NumInput
                  value={s.amplitude}
                  onChange={(n) => {
                    const next = [...seasons];
                    next[i] = { ...s, amplitude: n };
                    onChange({ ...f, seasonality: next });
                  }}
                />
              </Row>
              <Row label="period">
                <NumInput
                  value={s.period}
                  onChange={(n) => {
                    const next = [...seasons];
                    next[i] = { ...s, period: n };
                    onChange({ ...f, seasonality: next });
                  }}
                />
              </Row>
              <Row label="phase">
                <NumInput
                  value={s.phase ?? 0}
                  onChange={(n) => {
                    const next = [...seasons];
                    next[i] = { ...s, phase: n };
                    onChange({ ...f, seasonality: next });
                  }}
                />
              </Row>
            </div>
            <button
              onClick={() => onChange({ ...f, seasonality: seasons.filter((_, j) => j !== i) })}
              className="ring-focus inline-flex items-center gap-1 text-[11px] text-text-faint hover:text-hazard"
            >
              <X size={12} /> remove season
            </button>
          </div>
        ))}
      </div>
      <button
        onClick={() => onChange({ ...f, seasonality: [...seasons, { amplitude: 1, period: 24, phase: 0 }] })}
        className="ring-focus mt-2 inline-flex items-center gap-1 rounded text-xs font-medium text-primary hover:underline"
      >
        <Plus size={13} /> Add season
      </button>

      <div className="mt-4">
        <Kicker>Autoregression (AR)</Kicker>
        <div className="mt-2 space-y-1.5">
          {ar.map((c, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-10 font-mono text-[11px] text-text-faint">φ{i + 1}</span>
              <input
                type="number"
                value={c}
                onChange={(e) => {
                  const next = [...ar];
                  next[i] = Number(e.target.value);
                  onChange({ ...f, ar: next });
                }}
                className="ring-focus flex-1 rounded-control border border-border bg-surface-2 px-2 py-1 font-mono text-xs outline-none focus:border-primary"
              />
              <button
                onClick={() => onChange({ ...f, ar: ar.filter((_, j) => j !== i) })}
                className="ring-focus rounded text-text-faint hover:text-hazard"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
        <button
          onClick={() => onChange({ ...f, ar: [...ar, 0.3] })}
          className="ring-focus mt-2 inline-flex items-center gap-1 rounded text-xs font-medium text-primary hover:underline"
        >
          <Plus size={13} /> Add AR term
        </button>
        {ar.length > 0 && (
          <p className={"mt-1.5 text-[11px] " + (arSum < 1 ? "text-text-faint" : "text-hazard")}>
            Σ|φ| = {arSum.toFixed(2)} {arSum < 1 ? "(stationary ✓)" : "(must be < 1)"}
          </p>
        )}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <Row label="noise σ">
          <NumInput value={f.noise_std ?? 1} onChange={(n) => onChange({ ...f, noise_std: n })} />
        </Row>
        <Row label="dtype">
          <div className="mt-1 inline-flex rounded-control border border-border p-0.5">
            {(["float", "int"] as const).map((d) => (
              <button
                key={d}
                onClick={() => onChange({ ...f, dtype: d })}
                className={
                  "ring-focus rounded-[7px] px-3 py-1 text-xs " +
                  ((f.dtype ?? "float") === d ? "bg-primary-tint text-primary" : "text-text-muted")
                }
              >
                {d}
              </button>
            ))}
          </div>
        </Row>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Row label="min (clamp)">
          <NumInput value={f.min ?? undefined} onChange={(n) => onChange({ ...f, min: n })} />
        </Row>
        <Row label="max (clamp)">
          <NumInput value={f.max ?? undefined} onChange={(n) => onChange({ ...f, max: n })} />
        </Row>
      </div>
    </>
  );
}

/** A select-like control backed by the portal `Menu` so the option list is
 * viewport-clamped — a native <select> popup spills off-screen in the
 * right-edge inspector. Groups with a `group` label render a header. */
function MenuSelect({
  value,
  groups,
  onChange,
}: {
  value: string;
  groups: { group?: string; keys: readonly string[] }[];
  onChange: (v: string) => void;
}) {
  return (
    <Menu
      align="right"
      fullWidth
      trigger={({ open, toggle }) => (
        <button
          type="button"
          onClick={toggle}
          className="ring-focus mt-1 flex w-full items-center justify-between rounded-control border border-border bg-surface-2 px-2.5 py-1.5 text-left text-sm outline-none focus:border-primary"
        >
          <span className="truncate">{value}</span>
          <ChevronDown
            size={14}
            className={clsx("ml-2 shrink-0 text-text-faint transition-transform", open && "rotate-180")}
          />
        </button>
      )}
    >
      {(close) => (
        <div className="w-[240px] max-w-[calc(100vw-1rem)]">
          {groups.map((g, gi) => (
            <div key={g.group ?? gi} className="mb-1 last:mb-0">
              {g.group && (
                <div className="px-2.5 pb-1 pt-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-faint">
                  {g.group}
                </div>
              )}
              {g.keys.map((k) => (
                <MenuItem
                  key={k}
                  onClick={() => {
                    onChange(k);
                    close();
                  }}
                  icon={<Check size={14} className={clsx("text-primary", k !== value && "opacity-0")} />}
                >
                  <span className="truncate">{k}</span>
                </MenuItem>
              ))}
            </div>
          ))}
        </div>
      )}
    </Menu>
  );
}
