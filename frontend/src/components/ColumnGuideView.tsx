import { useMemo, useState } from "react";
import { AlertTriangle, Lightbulb, ShieldAlert } from "lucide-react";
import { Card, Kicker, PullStat } from "@/components/ui";
import { clsx } from "@/lib/clsx";
import type { ColumnIssue, ColumnProfile, IssueSeverity, ProfileReport } from "@/lib/types";

const SEVERITY: Record<IssueSeverity, { label: string; cls: string; bar: string; rank: number }> = {
  critical: { label: "Critical", cls: "text-hazard bg-hazard-tint", bar: "var(--hazard)", rank: 3 },
  high: { label: "High", cls: "text-hazard bg-hazard-tint", bar: "var(--hazard)", rank: 2 },
  medium: { label: "Medium", cls: "text-warning bg-warning-tint", bar: "var(--warning)", rank: 1 },
  low: { label: "Low", cls: "text-text-muted bg-surface-2", bar: "var(--text-faint)", rank: 0 },
};

const ROLE: Record<ColumnProfile["role"], { label: string; cls: string }> = {
  label: { label: "target", cls: "text-primary bg-primary-tint" },
  derived: { label: "derived", cls: "text-info bg-info-tint" },
  leakage_proxy: { label: "leakage", cls: "text-hazard bg-hazard-tint" },
  feature: { label: "feature", cls: "text-text-muted bg-surface-2" },
};

const fmt = (n: number | null | undefined): string =>
  n == null || !Number.isFinite(n)
    ? "—"
    : Math.abs(n) >= 1e5 || (Math.abs(n) < 1e-3 && n !== 0)
      ? n.toExponential(2)
      : Number.isInteger(n)
        ? String(n)
        : n.toFixed(3);

const pct = (n: number): string => `${(n * 100).toFixed(1)}%`;

export function ColumnGuideView({ profile }: { profile?: ProfileReport | null }) {
  const [onlyIssues, setOnlyIssues] = useState(false);
  const cols = useMemo(() => {
    const c = profile?.columns ?? [];
    return onlyIssues ? c.filter((x) => x.issues.length > 0) : c;
  }, [profile, onlyIssues]);

  if (!profile || profile.columns.length === 0) {
    return (
      <div className="rounded-card border border-dashed border-border p-10 text-center text-text-faint">
        No column profile is available for this run.
      </div>
    );
  }
  const s = profile.summary;

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-center gap-x-10 gap-y-4">
          <PullStat value={s.n_columns} label="Columns" />
          <PullStat
            value={s.columns_with_issues}
            label="With issues"
            tone={s.columns_with_issues ? "warning" : "success"}
          />
          {s.critical_issues > 0 && <PullStat value={s.critical_issues} label="Critical" tone="hazard" />}
          {s.high_issues > 0 && <PullStat value={s.high_issues} label="High severity" tone="hazard" />}
          <div className="max-w-sm text-sm text-text-muted">
            A per-column field guide for modelling this data: type, summary statistics, and — where the
            engine injected a data-quality issue — what it is and how to handle it.
            {s.label && (
              <span className="mt-1 block font-mono text-xs text-text-faint">
                detected target: <span className="text-primary">{s.label}</span>
              </span>
            )}
          </div>
        </div>
        {s.total_issues > 0 && (
          <label className="mt-4 flex w-fit cursor-pointer items-center gap-2 text-xs text-text-muted">
            <input
              type="checkbox"
              checked={onlyIssues}
              onChange={(e) => setOnlyIssues(e.target.checked)}
              className="accent-primary"
            />
            Show only columns with issues
          </label>
        )}
      </Card>

      {cols.map((col) => (
        <ColumnCard key={col.name} col={col} />
      ))}
    </div>
  );
}

function ColumnCard({ col }: { col: ColumnProfile }) {
  const role = ROLE[col.role];
  const topSeverity = col.issues.reduce<IssueSeverity | null>(
    (acc, i) => (acc == null || SEVERITY[i.severity].rank > SEVERITY[acc].rank ? i.severity : acc),
    null,
  );
  return (
    <Card className="overflow-hidden">
      <div
        className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3"
        style={topSeverity ? { boxShadow: `inset 3px 0 0 ${SEVERITY[topSeverity].bar}` } : undefined}
      >
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="font-display text-lg font-semibold">{col.name}</span>
          <Chip className={role.cls}>{role.label}</Chip>
          <Chip className="bg-surface-2 text-text-muted">{col.feature_type}</Chip>
          <span className="font-mono text-[11px] text-text-faint">{col.dtype}</span>
          {col.parents.length > 0 && (
            <span className="font-mono text-[11px] text-text-faint">← {col.parents.join(", ")}</span>
          )}
        </div>
        {col.issues.length > 0 && (
          <span className="text-xs font-medium text-text-muted">
            {col.issues.length} issue{col.issues.length > 1 ? "s" : ""}
          </span>
        )}
      </div>

      <div className="px-5 py-4">
        {col.description && <p className="mb-3 text-sm italic text-text-muted">{col.description}</p>}
        <StatsRow col={col} />
        {col.stats == null && col.categories && col.categories.length > 0 && (
          <CategoryBars col={col} />
        )}
        {col.issues.length > 0 && (
          <div className="mt-4 space-y-3">
            {col.issues.map((issue, i) => (
              <IssueBlock key={`${issue.mode}-${i}`} issue={issue} />
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function StatsRow({ col }: { col: ColumnProfile }) {
  const cells: { label: string; value: string }[] = [
    { label: "rows", value: String(col.count) },
    { label: "missing", value: pct(col.missing_pct) },
    { label: "unique", value: String(col.unique) },
  ];
  if (col.stats) {
    cells.push(
      { label: "mean", value: fmt(col.stats.mean) },
      { label: "std", value: fmt(col.stats.std) },
      { label: "min", value: fmt(col.stats.min) },
      { label: "median", value: fmt(col.stats.median) },
      { label: "max", value: fmt(col.stats.max) },
    );
    if (col.stats.skew != null) cells.push({ label: "skew", value: fmt(col.stats.skew) });
  }
  if (col.imbalance) {
    cells.push({
      label: "balance",
      value: `${pct(col.imbalance.majority_pct)} / ${pct(col.imbalance.minority_pct)}`,
    });
  }
  if (col.injected) {
    cells.push({ label: "missing (injected)", value: pct(col.injected.missing_pct) });
    if (col.injected.mean != null) cells.push({ label: "mean (injected)", value: fmt(col.injected.mean) });
  }
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3 md:grid-cols-4">
      {cells.map((c) => (
        <div key={c.label} className="flex items-baseline justify-between gap-2 border-b border-border/60 pb-1">
          <span className="kicker">{c.label}</span>
          <span className="font-mono text-sm text-text tnum">{c.value}</span>
        </div>
      ))}
    </div>
  );
}

function CategoryBars({ col }: { col: ColumnProfile }) {
  const cats = col.categories ?? [];
  const max = Math.max(...cats.map((c) => c.pct), 0.0001);
  return (
    <div className="mt-4 space-y-1.5">
      <Kicker>Class distribution</Kicker>
      {cats.map((c) => (
        <div key={c.value} className="flex items-center gap-2">
          <span className="w-28 truncate font-mono text-xs text-text-muted" title={c.value}>
            {c.value}
          </span>
          <div className="h-3 flex-1 overflow-hidden rounded-pill bg-surface-2">
            <div
              className="h-full rounded-pill bg-primary"
              style={{ width: `${Math.max(2, (c.pct / max) * 100)}%` }}
            />
          </div>
          <span className="w-12 text-right font-mono text-xs text-text-muted tnum">{pct(c.pct)}</span>
        </div>
      ))}
    </div>
  );
}

function IssueBlock({ issue }: { issue: ColumnIssue }) {
  const sev = SEVERITY[issue.severity];
  const Icon = issue.severity === "critical" ? ShieldAlert : AlertTriangle;
  return (
    <div className="rounded-control border border-border bg-surface-2/40 p-3.5">
      <div className="flex flex-wrap items-center gap-2">
        <Icon size={15} style={{ color: sev.bar }} />
        <span className="font-medium text-text">{issue.title}</span>
        <Chip className={sev.cls}>{sev.label}</Chip>
        <span className="font-mono text-xs text-text-muted">{issue.magnitude}</span>
      </div>
      <p className="mt-2 text-sm text-text-muted">{issue.explanation}</p>
      <div className="mt-2.5 flex gap-2 rounded-control bg-primary-tint/50 p-2.5">
        <Lightbulb size={15} className="mt-0.5 shrink-0 text-primary" />
        <p className="text-sm text-text">
          <span className="font-medium">How to handle it: </span>
          {issue.recommendation}
        </p>
      </div>
      {issue.techniques.length > 0 && (
        <ul className="mt-2.5 space-y-1 pl-1">
          {issue.techniques.map((t) => (
            <li key={t} className="flex gap-2 text-xs text-text-muted">
              <span className="text-text-faint">•</span>
              {t}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Chip({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={clsx("rounded-pill px-2 py-0.5 text-[11px] font-semibold", className)}>{children}</span>
  );
}
