import { histogram } from "@/lib/sampling";

// Lightweight SVG histogram (no chart library) — used for the live preview and
// the Results distribution cards. `overlay` draws a comparison line (target pdf).
export function Histogram({
  values,
  height = 120,
  color = "var(--primary)",
}: {
  values: number[];
  height?: number;
  color?: string;
}) {
  const bins = histogram(values, 28);
  const max = Math.max(1, ...bins.map((b) => b.count));
  const w = 100;
  const bw = w / bins.length;
  return (
    <svg viewBox={`0 0 ${w} ${height}`} preserveAspectRatio="none" className="h-[120px] w-full">
      {bins.map((b, i) => {
        const h = (b.count / max) * (height - 4);
        return (
          <rect
            key={i}
            x={i * bw + 0.4}
            y={height - h}
            width={bw - 0.8}
            height={h}
            rx={0.6}
            fill={color}
            opacity={0.85}
          />
        );
      })}
    </svg>
  );
}
