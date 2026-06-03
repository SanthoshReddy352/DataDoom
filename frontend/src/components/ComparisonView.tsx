import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Card, Kicker, PullStat, Spinner } from "./ui";
import { Histogram } from "./Histogram";
import { FailureIcon } from "./FailureBadges";
import { api } from "@/lib/api";
import { FAILURE_META } from "@/lib/failures";
import { clsx } from "@/lib/clsx";
import type { FailureDiff, FailuresReport, Preview, Report, Spec } from "@/lib/types";

export function ComparisonView({
  runId,
  report,
  cleanPreview,
  spec,
}: {
  runId: string;
  report?: Report | null;
  cleanPreview?: Preview;
  spec?: Spec;
}) {
  const failures = report?.failures as FailuresReport | null | undefined;
  const injected = useQuery({
    queryKey: ["preview", runId, "injected"],
    queryFn: () => api.preview(runId, 200, "injected"),
    enabled: !!runId,
    retry: false,
  });

  if (!failures || failures.count === 0) {
    return (
      <Empty>
        This run injected no failures. Add corruptions in the Canvas → <strong>Failures</strong> view, then
        regenerate to compare the clean and injected datasets here.
      </Empty>
    );
  }

  const modes = failures.modes ?? [];

  return (
    <div className="space-y-6">
      <SummaryRow modes={modes} clean={cleanPreview} injected={injected.data} />

      {/* Realized effect per failure (authoritative — measured by the engine) */}
      <section>
        <Kicker>What each failure actually did</Kicker>
        <p className="mt-1 text-xs italic text-text-faint">
          Measured on the full generated dataset by the engine — not an estimate.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {modes.map((m) => (
            <ModeCard key={m.index} diff={m} />
          ))}
        </div>
      </section>

      {/* Distribution shift overlays for affected numeric columns */}
      <DistShiftSection modes={modes} clean={cleanPreview} injected={injected.data} spec={spec} />

      {/* Cell-level diff */}
      <section>
        <Kicker>Clean → injected, row by row</Kicker>
        {injected.isLoading ? (
          <Spinner className="mt-3" />
        ) : injected.data && cleanPreview ? (
          <DiffTable clean={cleanPreview} injected={injected.data} />
        ) : (
          <Empty>The injected variant wasn’t exported for this run.</Empty>
        )}
      </section>
    </div>
  );
}

// --- summary ------------------------------------------------------------------

function SummaryRow({
  modes,
  clean,
  injected,
}: {
  modes: FailureDiff[];
  clean?: Preview;
  injected?: Preview;
}) {
  const nulledCols = new Set<string>();
  let missingFrac = 0;
  for (const m of modes) {
    if (m.nullified_fraction) {
      for (const [c, frac] of Object.entries(m.nullified_fraction)) {
        nulledCols.add(c);
        missingFrac += frac;
      }
    }
    if (m.realized_rate != null && m.column) {
      nulledCols.add(m.column);
      missingFrac += m.realized_rate;
    }
  }
  const addedCols =
    clean && injected ? injected.columns.filter((c) => !clean.columns.includes(c)) : [];

  return (
    <Card className="flex flex-wrap items-center gap-x-10 gap-y-6 p-6">
      <PullStat value={modes.length} label="Failure modes" tone="primary" />
      <PullStat
        value={`${Math.round(missingFrac * 100)}%`}
        label="Cells made missing"
        tone={missingFrac > 0 ? "hazard" : "text"}
      />
      <PullStat value={nulledCols.size} label="Columns affected" />
      {addedCols.length > 0 && <PullStat value={`+${addedCols.length}`} label="Leakage columns" tone="warning" />}
      <p className="max-w-xs text-sm text-text-muted">
        Both variants share the same{" "}
        <span className="font-mono text-xs">(spec_hash, seed)</span> — the clean baseline is byte-identical
        to a run with no failures.
      </p>
    </Card>
  );
}

// --- per-mode card ------------------------------------------------------------

function pct(x?: number): string {
  return x == null ? "—" : `${(x * 100).toFixed(1)}%`;
}
function fixed(x?: number, d = 2): string {
  return x == null || !Number.isFinite(x) ? "—" : x.toFixed(d);
}

function ModeCard({ diff }: { diff: FailureDiff }) {
  const meta = FAILURE_META[diff.type];
  return (
    <Card className="p-4">
      <div className="flex items-center gap-2.5">
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control"
          style={{ color: meta.accent, background: `color-mix(in srgb, ${meta.accent} 14%, transparent)` }}
        >
          <FailureIcon type={diff.type} size={15} />
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{meta.label}</div>
          <div className="font-mono text-[11px] text-text-faint">
            #{diff.index + 1} · {diff.column ?? diff.into ?? (diff.nullified_fraction ? Object.keys(diff.nullified_fraction).join(", ") : "")}
          </div>
        </div>
      </div>
      <div className="mt-3">{renderEffect(diff, meta.accent)}</div>
    </Card>
  );
}

function Bar({ value, target, color }: { value: number; target?: number; color: string }) {
  return (
    <div className="relative mt-1 h-2 w-full overflow-hidden rounded-pill bg-surface-3">
      <div className="h-full rounded-pill" style={{ width: `${Math.min(100, value * 100)}%`, background: color }} />
      {target != null && (
        <span
          className="absolute top-[-2px] h-3 w-0.5 bg-text-faint"
          style={{ left: `${Math.min(100, target * 100)}%` }}
          title={`target ${pct(target)}`}
        />
      )}
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div className="font-mono text-base font-semibold tnum" style={color ? { color } : undefined}>
        {value}
      </div>
      <div className="kicker mt-0.5">{label}</div>
    </div>
  );
}

function renderEffect(d: FailureDiff, color: string) {
  switch (d.type) {
    case "mcar": {
      const fracs = Object.values(d.nullified_fraction ?? {});
      const avg = fracs.length ? fracs.reduce((a, b) => a + b, 0) / fracs.length : 0;
      return (
        <>
          <div className="flex items-baseline justify-between text-xs text-text-muted">
            <span>realized missing</span>
            <span className="font-mono font-semibold text-text">{pct(avg)}</span>
          </div>
          <Bar value={avg} target={d.rate} color={color} />
        </>
      );
    }
    case "mar":
    case "mnar":
      return (
        <>
          <div className="flex items-baseline justify-between text-xs text-text-muted">
            <span>realized missing {d.self_dependent ? "(self-driven)" : `← ${d.driver}`}</span>
            <span className="font-mono font-semibold text-text">{pct(d.realized_rate)}</span>
          </div>
          <Bar value={d.realized_rate ?? 0} target={d.target_rate} color={color} />
          <div className="mt-1 text-[11px] text-text-faint">target {pct(d.target_rate)}</div>
        </>
      );
    case "label_noise":
      return (
        <>
          <div className="flex items-baseline justify-between text-xs text-text-muted">
            <span>labels flipped</span>
            <span className="font-mono font-semibold text-text">{pct(d.flipped_fraction)}</span>
          </div>
          <Bar value={d.flipped_fraction ?? 0} target={d.rate} color={color} />
        </>
      );
    case "feature_noise":
      return (
        <div className="flex gap-6">
          <Stat label="noise σ" value={fixed(d.realized_noise_std)} color={color} />
          <Stat label="mean shift" value={fixed(d.realized_mean_shift)} />
        </div>
      );
    case "drift":
      return (
        <div className="flex items-end justify-between gap-3">
          <div className="flex gap-6">
            <Stat label="total shift" value={fixed(d.total_shift)} color={color} />
            <Stat label="2nd−1st half" value={fixed(d.mean_shift_second_vs_first_half)} />
          </div>
          <svg viewBox="0 0 40 16" className="h-5 w-12 shrink-0">
            <line x1="1" y1="15" x2="39" y2="2" stroke={color} strokeWidth="1.6" strokeLinecap="round" />
          </svg>
        </div>
      );
    case "covariate_shift":
      return (
        <div className="space-y-1 font-mono text-xs">
          <div className="flex justify-between">
            <span className="text-text-faint">mean</span>
            <span>
              {fixed(d.before?.mean)} <span className="text-text-faint">→</span>{" "}
              <span style={{ color }}>{fixed(d.after?.mean)}</span>
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-faint">std</span>
            <span>
              {fixed(d.before?.std)} <span className="text-text-faint">→</span>{" "}
              <span style={{ color }}>{fixed(d.after?.std)}</span>
            </span>
          </div>
        </div>
      );
    case "leakage": {
      const corr = d.realized_correlation ?? 0;
      return (
        <>
          <div className="flex items-baseline justify-between text-xs text-text-muted">
            <span>corr({d.into}, {d.target})</span>
            <span className="font-mono font-semibold" style={{ color }}>
              {fixed(corr, 3)}
            </span>
          </div>
          <Bar value={Math.abs(corr)} color={color} />
          <div className="mt-1 text-[11px] text-text-faint">a near-perfect proxy for the label</div>
        </>
      );
    }
    default:
      return null;
  }
}

// --- distribution shift overlays ----------------------------------------------

function columnValues(p: Preview | undefined, name: string): number[] {
  if (!p) return [];
  const idx = p.columns.indexOf(name);
  if (idx < 0) return [];
  return p.rows.map((r) => Number(r[idx])).filter((v) => Number.isFinite(v));
}

function DistShiftSection({
  modes,
  clean,
  injected,
  spec,
}: {
  modes: FailureDiff[];
  clean?: Preview;
  injected?: Preview;
  spec?: Spec;
}) {
  const cols = useMemo(() => {
    const set = new Set<string>();
    for (const m of modes) {
      if ((m.type === "drift" || m.type === "covariate_shift" || m.type === "feature_noise") && m.column) {
        const f = spec?.features?.[m.column];
        if (!spec || (f && f.type === "numeric")) set.add(m.column);
      }
    }
    return [...set];
  }, [modes, spec]);

  if (cols.length === 0 || !clean || !injected) return null;

  return (
    <section>
      <Kicker>Distribution shift</Kicker>
      <p className="mt-1 text-xs italic text-text-faint">
        Clean (grey) vs injected (violet) on a shared axis — the sampled preview rows.
      </p>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {cols.map((c) => (
          <Card key={c} className="p-4">
            <div className="text-sm font-medium">{c}</div>
            <div className="mt-2 grid grid-cols-2 gap-3">
              <Mini label="clean" values={columnValues(clean, c)} color="var(--text-faint)" />
              <Mini label="injected" values={columnValues(injected, c)} color="var(--primary)" />
            </div>
          </Card>
        ))}
      </div>
    </section>
  );
}

function Mini({ label, values, color }: { label: string; values: number[]; color: string }) {
  return (
    <div className="rounded-control border border-border bg-surface-2 p-2">
      <Histogram values={values} color={color} height={80} />
      <div className="kicker mt-1 text-center">{label}</div>
    </div>
  );
}

// --- cell-level diff table ----------------------------------------------------

type ChangeKind = "same" | "nullified" | "changed" | "added";

function DiffTable({ clean, injected }: { clean: Preview; injected: Preview }) {
  const [changedOnly, setChangedOnly] = useState(true);
  const cleanIdx = useMemo(
    () => Object.fromEntries(clean.columns.map((c, i) => [c, i])),
    [clean.columns],
  );

  function cellKind(col: string, r: number): ChangeKind {
    if (!(col in cleanIdx)) return "added";
    const cv = clean.rows[r]?.[cleanIdx[col]];
    const ji = injected.columns.indexOf(col);
    const jv = injected.rows[r]?.[ji];
    if ((jv == null || jv === "") && cv != null && cv !== "") return "nullified";
    if (String(cv) !== String(jv)) return "changed";
    return "same";
  }

  const n = Math.min(clean.rows.length, injected.rows.length);
  // A row "changed" only if an *existing* column was nullified or altered. A
  // planted (added) column is present in every row, so counting it would make
  // every row "changed" and the filter a no-op.
  const rowChanged = (r: number) =>
    clean.columns.some((c) => {
      const k = cellKind(c, r);
      return k === "nullified" || k === "changed";
    });
  const changedRows = useMemo(() => {
    const out: number[] = [];
    for (let r = 0; r < n; r++) if (rowChanged(r)) out.push(r);
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [n, clean, injected]);
  const rows = changedOnly ? changedRows : Array.from({ length: n }, (_, r) => r);

  const KIND_STYLE: Record<ChangeKind, string> = {
    same: "text-text-faint",
    nullified: "bg-hazard-tint text-hazard font-semibold",
    changed: "bg-warning-tint text-warning",
    added: "bg-primary-tint text-primary",
  };

  return (
    <Card className="mt-3 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-3 text-[11px]">
          <Legend swatch="bg-hazard" label="made missing" />
          <Legend swatch="bg-warning" label="value changed" />
          <Legend swatch="bg-primary" label="planted column" />
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-xs text-text-muted">
          <input
            type="checkbox"
            checked={changedOnly}
            onChange={(e) => setChangedOnly(e.target.checked)}
            className="h-3.5 w-3.5 accent-[var(--primary)]"
          />
          Changed rows only
          <span className="font-mono text-text-faint tnum">
            ({changedRows.length} of {n})
          </span>
        </label>
      </div>
      <div className="max-h-[460px] overflow-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-border bg-surface-2 text-left">
              <th className="px-2 py-2 font-mono text-[10px] text-text-faint">#</th>
              {injected.columns.map((c) => (
                <th
                  key={c}
                  className={clsx(
                    "px-3 py-2 font-mono text-[11px]",
                    c in cleanIdx ? "text-text-muted" : "text-primary",
                  )}
                >
                  {c}
                  {!(c in cleanIdx) && " ★"}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 120).map((r) => (
              <tr key={r} className="border-b border-border last:border-0">
                <td className="px-2 py-1.5 font-mono text-[10px] text-text-faint tnum">{r}</td>
                {injected.columns.map((c) => {
                  const kind = cellKind(c, r);
                  const ji = injected.columns.indexOf(c);
                  const jv = injected.rows[r]?.[ji];
                  const cv = c in cleanIdx ? clean.rows[r]?.[cleanIdx[c]] : undefined;
                  return (
                    <td
                      key={c}
                      title={kind === "changed" ? `clean: ${String(cv)}` : undefined}
                      className={clsx("px-3 py-1.5 font-mono tnum", KIND_STYLE[kind])}
                    >
                      {kind === "nullified" ? "∅" : jv == null || jv === "" ? "·" : String(jv)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && (
        <div className="px-4 py-6 text-center text-xs text-text-faint">
          {changedOnly && changedRows.length === 0
            ? "No nullified or altered cells in the sampled rows — this run only adds a planted column. Uncheck to see all rows."
            : "No rows to show."}
        </div>
      )}
    </Card>
  );
}

function Legend({ swatch, label }: { swatch: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-text-muted">
      <span className={clsx("h-2.5 w-2.5 rounded-[3px]", swatch)} />
      {label}
    </span>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-border p-10 text-center text-sm text-text-faint">
      {children}
    </div>
  );
}
