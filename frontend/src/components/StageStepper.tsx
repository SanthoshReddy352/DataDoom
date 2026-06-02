import { Check, Circle, Loader2, X } from "lucide-react";
import { clsx } from "@/lib/clsx";

export type StageStatus = "pending" | "running" | "done" | "failed" | "skipped";

// Canonical pipeline stages (08 §7). Optional stages (causal / failure /
// difficulty) are marked — in P1 the engine runs the headless subset, so they
// render as "not in this spec" rather than pending forever.
export const STAGES: { key: string; label: string; optional?: boolean }[] = [
  { key: "intake", label: "Intake & Validate" },
  { key: "snapshot", label: "Snapshot & Hash" },
  { key: "seed", label: "Seed" },
  { key: "base_generation", label: "Base Generation" },
  { key: "causal", label: "Causal / SEM", optional: true },
  { key: "failure_injection", label: "Failure Injection", optional: true },
  { key: "difficulty", label: "Difficulty Calibration", optional: true },
  { key: "compliance", label: "Compliance" },
  { key: "packaging", label: "Packaging" },
];

export function StageStepper({ statuses }: { statuses: Record<string, StageStatus> }) {
  return (
    <ol className="space-y-1">
      {STAGES.map((s) => {
        const st = statuses[s.key] ?? (s.optional ? "skipped" : "pending");
        return (
          <li
            key={s.key}
            className={clsx(
              "flex items-center gap-3 rounded-control px-3 py-2",
              st === "running" && "bg-primary-tint",
              st === "failed" && "bg-hazard-tint",
            )}
          >
            <StageIcon status={st} />
            <span
              className={clsx(
                "text-sm",
                st === "done" && "text-text",
                st === "running" && "font-medium text-primary",
                st === "failed" && "font-medium text-hazard",
                (st === "pending" || st === "skipped") && "text-text-faint",
              )}
            >
              {s.label}
            </span>
            {st === "skipped" && (
              <span className="kicker ml-auto">not in this spec</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function StageIcon({ status }: { status: StageStatus }) {
  if (status === "done") return <Check size={16} className="text-success" />;
  if (status === "running") return <Loader2 size={16} className="animate-spin text-primary" />;
  if (status === "failed") return <X size={16} className="text-hazard" />;
  return <Circle size={16} className="text-text-faint/40" />;
}
