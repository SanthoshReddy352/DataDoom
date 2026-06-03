import {
  AlertTriangle,
  Droplets,
  Eraser,
  EyeOff,
  MoveHorizontal,
  Shuffle,
  TrendingUp,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { FAILURE_META, columnFailureChips } from "@/lib/failures";
import { clsx } from "@/lib/clsx";
import type { Failure, FailureType } from "@/lib/types";

const ICONS: Record<FailureType, LucideIcon> = {
  mcar: Eraser,
  mar: Droplets,
  mnar: EyeOff,
  label_noise: Shuffle,
  feature_noise: Waves,
  drift: TrendingUp,
  covariate_shift: MoveHorizontal,
  leakage: AlertTriangle,
};

export function FailureIcon({ type, size = 15 }: { type: FailureType; size?: number }) {
  const Icon = ICONS[type];
  return <Icon size={size} />;
}

/** Compact chips for the failures touching a column — used in Table/Graph views. */
export function FailureBadges({
  failures,
  column,
  className,
  compact,
}: {
  failures: Failure[] | undefined;
  column: string;
  className?: string;
  /** Icon-only chips (for tight spots like graph nodes). */
  compact?: boolean;
}) {
  const chips = columnFailureChips(failures, column);
  if (chips.length === 0) return null;
  return (
    <div className={clsx("flex flex-wrap gap-1", className)}>
      {chips.map((c, i) => {
        const accent = FAILURE_META[c.type].accent;
        return (
          <span
            key={i}
            title={`${FAILURE_META[c.type].label} · ${c.text}`}
            className={clsx(
              "inline-flex items-center gap-1 rounded-pill px-1.5 py-0.5 text-[10px] font-medium leading-tight",
              c.secondary && "opacity-70",
            )}
            style={{ color: accent, background: `color-mix(in srgb, ${accent} 13%, transparent)` }}
          >
            <FailureIcon type={c.type} size={11} />
            {!compact && <span className="whitespace-nowrap">{c.text}</span>}
          </span>
        );
      })}
    </div>
  );
}
