import { Card, Kicker, PullStat } from "./ui";
import { TIERS } from "@/lib/difficulty";
import { clsx } from "@/lib/clsx";
import type { DifficultyReport } from "@/lib/types";

// AUROC lives in [0.5, 1.0] in practice (0.5 = chance, 1.0 = perfect), so the
// meter zooms to that range to make the tier bands legible.
const LO = 0.5;
const HI = 1.0;
const pos = (v: number) => `${(Math.min(HI, Math.max(LO, v)) - LO) / (HI - LO) * 100}%`;

/** A 0.5–1.0 AUROC axis showing the tier bands, a target band, and an optional marker. */
export function BandMeter({
  band,
  marker,
  met,
  showTiers = true,
}: {
  band: [number, number];
  marker?: number;
  met?: boolean;
  showTiers?: boolean;
}) {
  const [a, b] = band;
  const markerColor = met == null ? "var(--primary)" : met ? "var(--success)" : "var(--warning)";
  return (
    <div className="select-none">
      <div className="relative h-9 rounded-control border border-border bg-surface-2">
        {/* Tier bands as faint backdrop segments */}
        {showTiers &&
          TIERS.map((t) => (
            <div
              key={t.tier}
              title={`${t.label} · ${t.band[0]}–${t.band[1]}`}
              className="absolute inset-y-0 border-l border-border/60"
              style={{ left: pos(t.band[0]), width: `calc(${pos(t.band[1])} - ${pos(t.band[0])})` }}
            />
          ))}
        {/* Target band highlight */}
        <div
          className="absolute inset-y-0 rounded-[5px]"
          style={{
            left: pos(a),
            width: `calc(${pos(b)} - ${pos(a)})`,
            background: "color-mix(in srgb, var(--primary) 18%, transparent)",
            boxShadow: "inset 0 0 0 1.5px var(--primary)",
          }}
        />
        {/* Achieved marker */}
        {marker != null && (
          <div className="absolute inset-y-0" style={{ left: pos(marker) }}>
            <div className="absolute inset-y-0 w-0.5 -translate-x-1/2" style={{ background: markerColor }} />
            <div
              className="absolute -top-1.5 -translate-x-1/2 rounded-pill px-1.5 py-0.5 font-mono text-[10px] font-semibold text-white"
              style={{ background: markerColor }}
            >
              {marker.toFixed(3)}
            </div>
          </div>
        )}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-text-faint">
        <span>0.50</span>
        <span>0.75</span>
        <span>1.00 AUROC</span>
      </div>
    </div>
  );
}

function Stat({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="kicker">{label}</div>
      <div className={clsx("mt-0.5 text-lg font-semibold", mono && "font-mono tnum")}>{value}</div>
    </div>
  );
}

export function DifficultyView({ report }: { report: DifficultyReport | null | undefined }) {
  if (!report) {
    return (
      <div className="rounded-card border border-dashed border-border p-10 text-center text-text-faint">
        This run had no difficulty target. Enable difficulty targeting in the Canvas to calibrate the
        dataset to a baseline-AUROC band.
      </div>
    );
  }
  const [a, b] = report.target.band;
  const tierLabel = report.target.tier
    ? TIERS.find((t) => t.tier === report.target.tier)?.label ?? report.target.tier
    : "Custom band";
  const minDist = a <= report.achieved_metric && report.achieved_metric <= b
    ? 0
    : Math.min(Math.abs(report.achieved_metric - a), Math.abs(report.achieved_metric - b));

  return (
    <div className="space-y-4">
      {/* Headline: achieved vs target */}
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-10">
            <PullStat
              value={report.achieved_metric.toFixed(3)}
              label={`Achieved ${report.metric_name.toUpperCase()}`}
              tone={report.band_met ? "success" : "warning"}
            />
            <div>
              <div className="kicker">Target · {tierLabel}</div>
              <div className="mt-0.5 font-mono text-lg font-semibold tnum">
                {a.toFixed(2)} – {b.toFixed(2)}
              </div>
            </div>
          </div>
          <span
            className={clsx(
              "rounded-pill px-3 py-1 text-sm font-semibold",
              report.band_met ? "bg-success-tint text-success" : "bg-warning-tint text-warning",
            )}
          >
            {report.band_met ? "✓ in band" : `closest · Δ ${minDist.toFixed(3)}`}
          </span>
        </div>
        <div className="mt-5">
          <BandMeter band={report.target.band} marker={report.achieved_metric} met={report.band_met} />
        </div>
        {report.note && (
          <p className="mt-4 rounded-control border border-warning bg-warning-tint px-3 py-2 text-xs leading-relaxed text-warning">
            {report.note}
          </p>
        )}
      </Card>

      {/* What the loop did */}
      <Card className="p-5">
        <Kicker>How it got there</Kicker>
        <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <Stat label="Probe" value={report.probe} mono={false} />
          <Stat label="Iterations" value={String(report.iterations)} />
          <Stat label="Difficulty dial" value={report.dial.toFixed(3)} />
          <Stat label="Feature noise η" value={report.feature_noise.toFixed(3)} />
          <Stat label="Label flips ρ" value={`${Math.round(report.label_flip * 100)}%`} />
          <Stat label="Noise-to-signal η²" value={report.reference.noise_to_signal.toFixed(3)} />
          <Stat label="Linear separability" value={report.reference.linear_separability.toFixed(3)} />
          <Stat label="Class balance" value={`${Math.round(report.reference.class_balance * 100)}%`} />
        </div>
        {report.knobs_active.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            <span className="kicker mr-1">Active knobs</span>
            {report.knobs_active.map((k) => (
              <span key={k} className="rounded-pill border border-primary bg-primary-tint px-2 py-0.5 text-xs font-medium text-primary">
                {k}
              </span>
            ))}
          </div>
        )}
        <p className="mt-4 border-t border-border pt-3 text-xs italic leading-relaxed text-text-faint">
          Difficulty is empirical: the dataset is calibrated until a {report.probe} baseline scores in the
          target band on a held-out split. Feature noise blurs the numeric predictors (the authored causal
          graph is left intact); label flips are the deep-end lever. Achieved score is reported honestly,
          misses included.
        </p>
      </Card>

      {/* Bisection trace */}
      {report.trace.length > 1 && (
        <Card className="overflow-hidden">
          <div className="border-b border-border px-4 py-2.5">
            <Kicker>Adaptive search · dial → probe AUROC</Kicker>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2 text-left text-xs text-text-muted">
                <th className="px-4 py-2">Step</th>
                <th className="px-4 py-2">Dial</th>
                <th className="px-4 py-2">Probe AUROC</th>
                <th className="px-4 py-2">Verdict</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs tnum">
              {report.trace.map((t, i) => {
                const inBand = a <= t.metric && t.metric <= b;
                const verdict = inBand ? "in band" : t.metric > b ? "too easy" : "too hard";
                return (
                  <tr key={i} className="border-b border-border last:border-0">
                    <td className="px-4 py-1.5 text-text-faint">{i + 1}</td>
                    <td className="px-4 py-1.5">{t.dial.toFixed(3)}</td>
                    <td className="px-4 py-1.5">{t.metric.toFixed(3)}</td>
                    <td
                      className="px-4 py-1.5 font-sans"
                      style={{ color: inBand ? "var(--success)" : "var(--text-muted)" }}
                    >
                      {verdict}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
