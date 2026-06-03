import { Card, Kicker, PullStat, TYPE_COLOR } from "./ui";
import type { Artifact, Preview, Report, RunSummary, Spec } from "@/lib/types";

/** Generation Overview — the at-a-glance "what did I just make" dashboard,
 * composed entirely from the reproducible metadata (spec + report + artifacts). */
export function OverviewView({
  spec,
  report,
  preview,
  run,
  artifacts,
}: {
  spec?: Spec;
  report?: Report | null;
  preview?: Preview;
  run?: RunSummary;
  artifacts?: Artifact[];
}) {
  const features = spec ? Object.entries(spec.features) : [];
  const rows = preview?.total ?? spec?.rows ?? 0;
  const cols = features.length;
  const score = report?.compliance_score ?? report?.distribution?.compliance_score ?? null;
  const failures = report?.failures ?? null;

  // Feature-type breakdown for the donut.
  const typeCounts = features.reduce<Record<string, number>>((acc, [, f]) => {
    acc[f.type] = (acc[f.type] ?? 0) + 1;
    return acc;
  }, {});
  const typeSlices = Object.entries(typeCounts).map(([type, count]) => ({
    label: type,
    count,
    color: TYPE_COLOR[type] ?? "var(--text-muted)",
  }));

  // Distribution family mix across numeric features.
  const distCounts = features.reduce<Record<string, number>>((acc, [, f]) => {
    if (f.type === "numeric") {
      const key = f.dist ?? "derived";
      acc[key] = (acc[key] ?? 0) + 1;
    }
    return acc;
  }, {});

  const derivedCount = report?.causal_truth?.edges?.length
    ? new Set(report.causal_truth.edges.map((e) => e.to)).size
    : 0;
  const edgeCount = report?.causal_truth?.edges?.length ?? 0;

  return (
    <div className="space-y-6">
      {/* Headline numerals */}
      <Card className="flex flex-wrap items-center gap-x-12 gap-y-6 p-6">
        <PullStat value={rows.toLocaleString()} label="Rows" />
        <PullStat value={cols} label="Columns" />
        <PullStat
          value={score != null ? `${Math.round(score * 100)}%` : "—"}
          label="Compliance"
          tone={score != null && score >= 0.8 ? "success" : score != null && score >= 0.5 ? "warning" : "hazard"}
        />
        {failures && failures.count > 0 && (
          <PullStat value={failures.count} label="Failure modes" tone="hazard" />
        )}
        {run && <PullStat value={run.seed} label="Seed" tone="primary" />}
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Feature-type composition */}
        <Card className="p-5">
          <Kicker>Column composition</Kicker>
          <div className="mt-4 flex items-center gap-6">
            <Donut slices={typeSlices} />
            <ul className="space-y-1.5 text-sm">
              {typeSlices.map((s) => (
                <li key={s.label} className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-[3px]" style={{ background: s.color }} />
                  <span className="capitalize text-text">{s.label}</span>
                  <span className="font-mono text-xs text-text-faint tnum">{s.count}</span>
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* Distribution family mix */}
        <Card className="p-5">
          <Kicker>Distribution families</Kicker>
          {Object.keys(distCounts).length === 0 ? (
            <p className="mt-4 text-sm text-text-muted">No sampled numeric features.</p>
          ) : (
            <BarList
              items={Object.entries(distCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([label, count]) => ({ label, count }))}
              color="var(--primary)"
            />
          )}
        </Card>
      </div>

      {/* Causal structure summary */}
      {edgeCount > 0 && (
        <Card className="flex flex-wrap items-center gap-x-12 gap-y-4 p-6">
          <div>
            <Kicker>Causal structure</Kicker>
            <p className="mt-1 max-w-md text-sm text-text-muted">
              This dataset carries a true generating graph — derived columns are computed from their
              parents, not sampled independently.
            </p>
          </div>
          <PullStat value={edgeCount} label="Edges" tone="primary" />
          <PullStat value={derivedCount} label="Derived cols" />
          {report?.causal_truth?.interventions &&
            Object.keys(report.causal_truth.interventions).length > 0 && (
              <PullStat value={Object.keys(report.causal_truth.interventions).length} label="Interventions" tone="warning" />
            )}
        </Card>
      )}

      {/* Failure-by-mode */}
      {failures && failures.count > 0 && (
        <Card className="p-5">
          <Kicker>Injected failures · by mode</Kicker>
          <BarList
            items={Object.entries(
              failures.modes.reduce<Record<string, number>>((acc, m) => {
                acc[m.type] = (acc[m.type] ?? 0) + 1;
                return acc;
              }, {}),
            )
              .sort((a, b) => b[1] - a[1])
              .map(([label, count]) => ({ label, count }))}
            color="var(--hazard)"
          />
        </Card>
      )}

      {/* Artifacts */}
      <Card className="overflow-hidden">
        <div className="border-b border-border px-4 py-2.5">
          <Kicker>Artifacts · reproducible bundle</Kicker>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-surface-2 text-left text-xs text-text-muted">
              <th className="px-4 py-2">File</th>
              <th className="px-4 py-2">Version</th>
              <th className="px-4 py-2">Size</th>
              <th className="px-4 py-2">SHA-256</th>
            </tr>
          </thead>
          <tbody className="font-mono text-xs tnum">
            {(artifacts ?? []).length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-3 text-center font-sans text-text-faint">
                  No artifacts recorded.
                </td>
              </tr>
            ) : (
              (artifacts ?? []).map((a) => (
                <tr key={a.artifact_id} className="border-b border-border last:border-0">
                  <td className="px-4 py-2">{a.format}</td>
                  <td className="px-4 py-2 font-sans">{a.version}{a.split ? ` · ${a.split}` : ""}</td>
                  <td className="px-4 py-2">{humanSize(a.size_bytes)}</td>
                  <td className="px-4 py-2 text-text-faint" title={a.checksum_sha256}>
                    {a.checksum_sha256.slice(0, 12)}…
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

/** A dependency-free SVG donut. */
function Donut({ slices }: { slices: { label: string; count: number; color: string }[] }) {
  const total = slices.reduce((a, s) => a + s.count, 0) || 1;
  const r = 42;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg width="110" height="110" viewBox="0 0 110 110" className="-rotate-90">
      <circle cx="55" cy="55" r={r} fill="none" stroke="var(--surface-2)" strokeWidth="14" />
      {slices.map((s) => {
        const frac = s.count / total;
        const dash = frac * c;
        const seg = (
          <circle
            key={s.label}
            cx="55"
            cy="55"
            r={r}
            fill="none"
            stroke={s.color}
            strokeWidth="14"
            strokeDasharray={`${dash} ${c - dash}`}
            strokeDashoffset={-offset}
          />
        );
        offset += dash;
        return seg;
      })}
    </svg>
  );
}

/** Horizontal labelled bars normalized to the largest count. */
function BarList({ items, color }: { items: { label: string; count: number }[]; color: string }) {
  const max = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className="mt-4 space-y-2.5">
      {items.map((i) => (
        <div key={i.label} className="flex items-center gap-3">
          <span className="w-28 truncate font-mono text-xs text-text-muted">{i.label}</span>
          <div className="h-3 flex-1 overflow-hidden rounded-pill bg-surface-2">
            <div
              className="h-full rounded-pill"
              style={{ width: `${(i.count / max) * 100}%`, background: color }}
            />
          </div>
          <span className="w-6 text-right font-mono text-xs text-text-faint tnum">{i.count}</span>
        </div>
      ))}
    </div>
  );
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
