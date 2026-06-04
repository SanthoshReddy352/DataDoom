import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { Button, Card, CopyableHash, Kicker, PullStat, Spinner } from "@/components/ui";
import { Histogram } from "@/components/Histogram";
import { CausalGraphView } from "@/components/CausalGraphView";
import { ComparisonView } from "@/components/ComparisonView";
import { OverviewView } from "@/components/OverviewView";
import { ColumnGuideView } from "@/components/ColumnGuideView";
import { DifficultyView } from "@/components/DifficultyView";
import { GenerationsPanel } from "@/components/GenerationsPanel";
import { ExportModal } from "@/components/ExportModal";
import { api } from "@/lib/api";
import { clsx } from "@/lib/clsx";
import { recoverSCM } from "@/lib/audit";
import { useChrome } from "@/store/chrome";
import type { FailuresReport, FeatureCompliance, MatrixReport, Preview, Report, Spec } from "@/lib/types";

const ALL_TABS = [
  "Overview",
  "Data Preview",
  "Column Guide",
  "Distributions",
  "Correlation & MI",
  "Causal Graph",
  "Difficulty",
  "Comparison",
  "Generations",
  "Evaluation",
] as const;
type Tab = (typeof ALL_TABS)[number];

export function Results() {
  const { id, runId } = useParams<{ id: string; runId: string }>();
  const [tab, setTab] = useState<Tab>("Overview");
  const [exporting, setExporting] = useState(false);
  const setCrumbs = useChrome((s) => s.setCrumbs);

  const run = useQuery({ queryKey: ["run", runId], queryFn: () => api.getRun(runId!), enabled: !!runId });
  const report = useQuery({ queryKey: ["report", runId], queryFn: () => api.report(runId!), enabled: !!runId });
  const preview = useQuery({ queryKey: ["preview", runId], queryFn: () => api.preview(runId!, 200), enabled: !!runId });
  const artifacts = useQuery({ queryKey: ["artifacts", runId], queryFn: () => api.artifacts(runId!), enabled: !!runId });
  const datasetId = id ?? run.data?.dataset_id;
  const spec = useQuery({ queryKey: ["spec", datasetId], queryFn: () => api.getSpec(datasetId!), enabled: !!datasetId });

  useEffect(() => {
    setCrumbs([{ label: "Datasets", to: "/datasets" }, ...(spec.data ? [{ label: spec.data.body.name, to: `/datasets/${datasetId}` }] : []), { label: "Results" }]);
  }, [setCrumbs, spec.data, datasetId]);

  if (run.isLoading || report.isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const score = report.data?.compliance_score ?? null;
  const hasFailures = !!(report.data?.failures as FailuresReport | null | undefined)?.count;
  const hasDifficulty = !!report.data?.difficulty;
  const tabs = ALL_TABS.filter(
    (t) => (t !== "Comparison" || hasFailures) && (t !== "Difficulty" || hasDifficulty),
  );

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-8 py-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Kicker>Run report</Kicker>
            <h1 className="mt-1.5 font-display text-[36px] font-semibold leading-none tracking-tight">Results</h1>
            <div className="mt-3 flex flex-wrap gap-2.5">
              {run.data && <CopyableHash label="seed" value={run.data.seed} />}
              {report.data?.determinism && <CopyableHash label="spec_hash" value={report.data.determinism.spec_hash} />}
            </div>
            <p className="mt-3 max-w-md border-l-2 border-primary pl-3 text-sm italic text-text-muted">
              Regenerate from this spec + seed for byte-identical data.
            </p>
          </div>
          <Button variant="primary" onClick={() => setExporting(true)}>
            <Download size={15} /> Export
          </Button>
        </div>

        <div className="mt-7 flex flex-wrap gap-x-1 gap-y-0 border-b border-border">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={clsx(
                "ring-focus inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
                tab === t ? "border-primary text-text" : "border-transparent text-text-muted hover:text-text",
              )}
            >
              {t}
              {t === "Comparison" && (
                <span className="rounded-pill bg-primary-tint px-1.5 text-[10px] font-semibold text-primary tnum">
                  {(report.data?.failures as FailuresReport | null | undefined)?.count}
                </span>
              )}
              {t === "Column Guide" && !!report.data?.profile?.summary.total_issues && (
                <span className="rounded-pill bg-warning-tint px-1.5 text-[10px] font-semibold text-warning tnum">
                  {report.data.profile.summary.total_issues}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="mt-6 animate-fade-in">
          {tab === "Overview" && (
            <OverviewView
              spec={spec.data?.body}
              report={report.data}
              preview={preview.data}
              run={run.data}
              artifacts={artifacts.data ?? []}
            />
          )}
          {tab === "Data Preview" && <PreviewTab data={preview.data} loading={preview.isLoading} />}
          {tab === "Column Guide" && <ColumnGuideView profile={report.data?.profile} />}
          {tab === "Distributions" && <DistributionsTab report={report.data} preview={preview.data} />}
          {tab === "Correlation & MI" && <CorrelationTab report={report.data} />}
          {tab === "Causal Graph" && <CausalGraphTab report={report.data} spec={spec.data?.body} datasetId={datasetId} runId={runId} />}
          {tab === "Difficulty" && <DifficultyView report={report.data?.difficulty} />}
          {tab === "Comparison" && runId && (
            <ComparisonView runId={runId} report={report.data} cleanPreview={preview.data} spec={spec.data?.body} />
          )}
          {tab === "Generations" && <GenerationsPanel datasetId={datasetId} currentRunId={runId} />}
          {tab === "Evaluation" && <EvaluationTab report={report.data} preview={preview.data} score={score} />}
        </div>
      </div>

      {runId && (
        <ExportModal open={exporting} onClose={() => setExporting(false)} runId={runId} artifacts={artifacts.data ?? []} />
      )}
    </div>
  );
}

function PreviewTab({ data, loading }: { data?: Preview; loading: boolean }) {
  if (loading || !data) return <Spinner />;
  return (
    <Card className="overflow-auto">
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <span className="kicker">First {data.rows.length} of {data.total.toLocaleString()} rows</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-surface-2 text-left">
            {data.columns.map((c) => (
              <th key={c} className="px-3 py-2 font-mono text-xs text-text-muted">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.slice(0, 100).map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-1.5 font-mono text-xs text-text-muted tnum">{String(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

function numericColumn(preview: Preview | undefined, name: string): number[] {
  if (!preview) return [];
  const idx = preview.columns.indexOf(name);
  if (idx < 0) return [];
  return preview.rows.map((r) => Number(r[idx])).filter((v) => Number.isFinite(v));
}

function isApplicable(c: FeatureCompliance): boolean {
  return c.applicable ?? true;
}
function ksTone(c: FeatureCompliance): "success" | "warning" | "hazard" | "muted" {
  if (!isApplicable(c)) return "muted";
  if (c.passed) return "success";
  return c.p_value > 0.01 ? "warning" : "hazard";
}
const TONE_COLOR: Record<"success" | "warning" | "hazard" | "muted", string> = {
  success: "var(--success)",
  warning: "var(--warning)",
  hazard: "var(--hazard)",
  muted: "var(--text-faint)",
};

function DistributionsTab({ report, preview }: { report?: Report | null; preview?: Preview }) {
  const feats = report?.distribution?.features ?? [];
  if (feats.length === 0) return <Empty>No numeric features to assess.</Empty>;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {feats.map((c) => {
        const tone = ksTone(c);
        const color = TONE_COLOR[tone];
        const applicable = isApplicable(c);
        const verdict = !applicable ? "n/a" : c.passed ? "pass" : "review";
        return (
          <Card key={c.feature} className="p-4">
            <div className="flex items-center justify-between">
              <div className="font-display text-lg font-semibold">{c.feature}</div>
              <span className="font-mono text-[11px]" style={{ color }}>{c.dist}</span>
            </div>
            <div className="mt-2">
              <Histogram values={numericColumn(preview, c.feature)} color={color} />
            </div>
            <div className="mt-2 flex items-center justify-between font-mono text-xs text-text-muted">
              <span title="Which test decided the verdict">
                {c.test === "chi2_gof"
                  ? `χ² ${c.gof ? `${c.gof.bins}b` : "GoF"}`
                  : c.test === "none"
                    ? "abstain"
                    : `KS D=${c.ks_statistic.toFixed(3)}`}
              </span>
              <span>p={c.p_value.toFixed(3)}</span>
              <span style={{ color }} title={c.note ?? undefined}>{verdict}</span>
            </div>
            {c.note && <p className="mt-1.5 text-[11px] italic text-text-faint">{c.note}</p>}
          </Card>
        );
      })}
      <p className="col-span-full text-xs italic text-text-faint">
        Continuous, un-clamped features are judged by a Kolmogorov–Smirnov test against the
        requested CDF. Integer, discrete (e.g. poisson), and clamped features are judged by a
        chi-square <span className="not-italic font-mono">goodness-of-fit</span> against the
        effective PMF (boundary bins absorb the clamped tail). A feature only shows{" "}
        <span className="not-italic font-mono">n/a</span> when no valid test can be formed. We
        report fit honestly and never refit to the sample.
      </p>
    </div>
  );
}

function Heatmap({ matrix, diverging, normalize }: { matrix: MatrixReport; diverging: boolean; normalize?: number }) {
  const cellColor = (v: number | null) => {
    if (v == null) return "var(--surface-2)";
    if (diverging) {
      const hue = v >= 0 ? "91, 67, 230" : "200, 64, 42";
      return `rgba(${hue}, ${Math.min(1, Math.abs(v)).toFixed(2)})`;
    }
    const mag = normalize ? Math.min(1, v / normalize) : Math.min(1, v);
    return `rgba(91, 67, 230, ${mag.toFixed(2)})`;
  };
  return (
    <table className="mt-3 border-collapse" style={{ tableLayout: "fixed" }}>
      <thead>
        <tr>
          <th className="w-28" />
          {matrix.columns.map((c) => (
            <th
              key={c}
              title={c}
              className="w-14 max-w-[56px] break-words px-1 pb-2 align-bottom font-mono text-[10px] leading-tight text-text-faint"
            >
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {matrix.matrix.map((row, i) => (
          <tr key={i}>
            <td
              title={matrix.columns[i]}
              className="w-28 max-w-[112px] break-words pr-2 text-right align-middle font-mono text-[10px] leading-tight text-text-faint"
            >
              {matrix.columns[i]}
            </td>
            {row.map((v, j) => (
              <td key={j} className="p-0.5">
                <div
                  title={v == null ? "—" : v.toFixed(3)}
                  className="flex h-11 w-14 items-center justify-center rounded-[4px] font-mono text-[10px]"
                  style={{
                    background: cellColor(v),
                    color:
                      v != null && Math.abs(diverging ? v : normalize ? v / normalize : v) > 0.5
                        ? "#fff"
                        : "var(--text-muted)",
                  }}
                >
                  {v == null ? "—" : v.toFixed(2)}
                </div>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CorrelationTab({ report }: { report?: Report | null }) {
  const corr = report?.correlation;
  const mi = report?.mutual_information;
  if (!corr && !mi) return <Empty>Correlation needs at least two numeric features.</Empty>;
  const miMax = mi
    ? Math.max(0.0001, ...mi.matrix.flatMap((row, i) => row.map((v, j) => (i === j || v == null ? 0 : v))))
    : 1;
  return (
    <div className="space-y-4">
      {corr && (
        <Card className="overflow-auto p-4">
          <Kicker>Pearson correlation</Kicker>
          <Heatmap matrix={corr} diverging />
        </Card>
      )}
      {mi && (
        <Card className="overflow-auto p-4">
          <Kicker>Mutual information · {mi.units ?? "nats"}</Kicker>
          <p className="mt-1 text-xs italic text-text-faint">
            Captures non-linear dependence too; the diagonal is each column's entropy H(X).
          </p>
          <Heatmap matrix={mi} diverging={false} normalize={miMax} />
        </Card>
      )}
    </div>
  );
}

function empiricalMap(report?: Report | null): Record<string, { mean?: number; std?: number }> {
  const out: Record<string, { mean?: number; std?: number }> = {};
  for (const c of report?.distribution?.features ?? []) {
    out[c.feature] = { mean: c.empirical.mean, std: c.empirical.std };
  }
  return out;
}

function CausalGraphTab({ report, spec, datasetId, runId }: { report?: Report | null; spec?: Spec; datasetId?: string; runId?: string }) {
  const truth = report?.causal_truth;
  if (!truth || truth.edges.length === 0) {
    return <Empty>This dataset has no causal structure — features are sampled independently.</Empty>;
  }
  const interventions = Object.entries(truth.interventions ?? {});
  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="border-b border-border px-4 py-2.5">
          <Kicker>True generating graph · every column's settings & structural equations</Kicker>
        </div>
        <CausalGraphView truth={truth} spec={spec} datasetId={datasetId} runId={runId} empirical={empiricalMap(report)} />
      </Card>
      {interventions.length > 0 && (
        <Card className="p-4">
          <Kicker>Interventions · do()</Kicker>
          <div className="mt-2 flex flex-wrap gap-2 font-mono text-xs">
            {interventions.map(([k, v]) => (
              <span key={k} className="rounded-control border border-primary bg-primary-tint px-2 py-1 text-primary">
                do({k} = {v})
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs italic text-text-faint">
            Intervened nodes are fixed to a constant; their incoming edges (dashed) are detached.
          </p>
        </Card>
      )}
    </div>
  );
}

function EvaluationTab({ report, preview, score }: { report?: Report | null; preview?: Preview; score: number | null }) {
  const feats = report?.distribution?.features ?? [];
  const recoveries = useMemo(() => recoverSCM(report?.causal_truth, preview), [report?.causal_truth, preview]);

  return (
    <div className="space-y-6">
      <Card className="flex flex-wrap items-center gap-10 p-6">
        <PullStat
          value={score != null ? `${Math.round(score * 100)}%` : "—"}
          label="Compliance score"
          tone={score != null && score >= 0.8 ? "success" : score != null && score >= 0.5 ? "warning" : "hazard"}
        />
        <div className="max-w-sm text-sm text-text-muted">
          The fraction of <em>KS-applicable</em> features (continuous, float, un-clamped) whose realized
          sample is statistically consistent (KS, α=0.05) with the requested distribution. Integer,
          discrete, and clamped features abstain (n/a) and are judged by their moments.
          {report?.distribution?.applicable_features != null && (
            <span className="mt-1 block font-mono text-xs text-text-faint">
              {report.distribution.applicable_features} of {report.distribution.assessed_features} assessed features KS-applicable
            </span>
          )}
        </div>
      </Card>

      {/* SCM recovery — the transparency analytic */}
      {recoveries.length > 0 && (
        <Card className="overflow-hidden">
          <div className="border-b border-border px-4 py-2.5">
            <Kicker>Structural recovery · can a regression read back our equations?</Kicker>
            <p className="mt-1 text-xs italic text-text-faint">
              For each derived column we fit <span className="font-mono not-italic">target ~ parents</span> (OLS) on the
              realized sample and compare the recovered slope to the declared structural weight. Honest generation lands
              recovered ≈ declared.
            </p>
          </div>
          <div className="divide-y divide-border">
            {recoveries.map((rec) => (
              <div key={rec.target} className="px-4 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="font-display text-base font-semibold">{rec.target}</div>
                  {rec.note ? (
                    <span className="text-xs italic text-text-faint">{rec.note}</span>
                  ) : (
                    <div className="flex gap-4 font-mono text-xs text-text-muted">
                      <span>R²={rec.r2.toFixed(3)}</span>
                      <span>resid σ={rec.residualStd.toFixed(3)}</span>
                      <span>n={rec.n}</span>
                    </div>
                  )}
                </div>
                {!rec.note && (
                  <table className="mt-2 w-full text-xs">
                    <thead>
                      <tr className="text-left text-text-faint">
                        <th className="py-1 font-medium">term</th>
                        <th className="py-1 font-medium">recovered</th>
                        <th className="py-1 font-medium">declared</th>
                        <th className="py-1 font-medium">Δ</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono tnum">
                      <tr className="border-t border-border">
                        <td className="py-1 text-text-muted">intercept</td>
                        <td className="py-1">{rec.intercept.toFixed(3)}</td>
                        <td className="py-1 text-text-faint">—</td>
                        <td className="py-1 text-text-faint">—</td>
                      </tr>
                      {rec.terms.map((t) => {
                        const delta = t.truth != null ? Math.abs(t.recovered - t.truth) : null;
                        return (
                          <tr key={t.parent} className="border-t border-border">
                            <td className="py-1 text-text-muted">{t.parent}</td>
                            <td className="py-1">{t.recovered.toFixed(3)}</td>
                            <td className="py-1 text-text-faint">{t.truth != null ? t.truth.toFixed(3) : "—"}</td>
                            <td
                              className="py-1"
                              style={{ color: delta != null ? (delta < 0.15 ? "var(--success)" : delta < 0.4 ? "var(--warning)" : "var(--hazard)") : undefined }}
                            >
                              {delta != null ? delta.toFixed(3) : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {feats.length > 0 && (
        <Card className="overflow-hidden">
          <div className="border-b border-border px-4 py-2.5"><Kicker>Target vs actual</Kicker></div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2 text-left text-xs text-text-muted">
                <th className="px-4 py-2">Feature</th>
                <th className="px-4 py-2">Distribution</th>
                <th className="px-4 py-2">Empirical mean</th>
                <th className="px-4 py-2">Empirical std</th>
                <th className="px-4 py-2">Clamped</th>
                <th className="px-4 py-2">Fit p</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs tnum">
              {feats.map((c) => {
                const applicable = isApplicable(c);
                return (
                  <tr key={c.feature} className="border-b border-border last:border-0">
                    <td className="px-4 py-2 font-sans text-sm">{c.feature}</td>
                    <td className="px-4 py-2">{c.dist}</td>
                    <td className="px-4 py-2">{c.empirical.mean?.toFixed(3)}</td>
                    <td className="px-4 py-2">{c.empirical.std?.toFixed(3)}</td>
                    <td className="px-4 py-2">{(c.clamped_fraction * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2" title={c.note ?? undefined} style={{ color: TONE_COLOR[ksTone(c)] }}>
                      {applicable ? c.p_value.toFixed(3) : "n/a"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card className="p-5">
          <Kicker>Achieved difficulty</Kicker>
          {report?.difficulty ? (
            <div className="mt-2 text-sm text-text-muted">
              <span className="font-mono text-lg font-semibold text-text tnum">
                {report.difficulty.achieved_metric.toFixed(3)}
              </span>{" "}
              {report.difficulty.metric_name.toUpperCase()} vs target{" "}
              {report.difficulty.target.band[0].toFixed(2)}–{report.difficulty.target.band[1].toFixed(2)}
              <span
                className={clsx(
                  "ml-2 rounded-pill px-2 py-0.5 text-xs font-semibold",
                  report.difficulty.band_met ? "bg-success-tint text-success" : "bg-warning-tint text-warning",
                )}
              >
                {report.difficulty.band_met ? "in band" : "closest"}
              </span>
              <p className="mt-1.5 text-xs text-text-faint">See the Difficulty tab for the full calibration trace.</p>
            </div>
          ) : (
            <p className="mt-2 text-sm text-text-muted">
              No difficulty target was set for this run. Enable difficulty targeting in the Canvas to
              calibrate to a baseline-AUROC band.
            </p>
          )}
        </Card>
        {report?.determinism && (
          <Card className="p-5">
            <Kicker>Determinism</Kicker>
            <div className="mt-3 space-y-2 font-mono text-xs text-text-muted">
              <div>seed: {report.determinism.seed}</div>
              {Object.entries(report.determinism.artifact_checksums).map(([f, sum]) => (
                <div key={f} className="truncate">
                  {f}: <span className="text-text-faint">{sum}</span>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-border p-10 text-center text-text-faint">
      {children}
    </div>
  );
}
