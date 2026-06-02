// Client-side PREVIEW sampling only — a fixed-seed approximation so the Inspector
// histogram feels alive as params change. This is NOT the engine; the real,
// reproducible data comes from the server. Labelled as a preview in the UI.

function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gauss(rng: () => number) {
  let u = 0;
  let v = 0;
  while (u === 0) u = rng();
  while (v === 0) v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

export function previewNumeric(
  dist: string,
  params: Record<string, number>,
  n = 2000,
): number[] {
  const rng = mulberry32(1234567);
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    let x = 0;
    switch (dist) {
      case "normal":
        x = (params.mean ?? 0) + (params.std ?? 1) * gauss(rng);
        break;
      case "lognormal":
        x = Math.exp((params.mu ?? 0) + (params.sigma ?? 1) * gauss(rng));
        break;
      case "uniform":
        x = (params.low ?? 0) + ((params.high ?? 1) - (params.low ?? 0)) * rng();
        break;
      case "exponential":
        x = -(params.scale ?? 1) * Math.log(1 - rng());
        break;
      case "poisson": {
        const L = Math.exp(-(params.lam ?? 3));
        let k = 0;
        let p = 1;
        do {
          k++;
          p *= rng();
        } while (p > L);
        x = k - 1;
        break;
      }
      case "pareto":
        x = ((params.xm ?? 1) * 1) / Math.pow(1 - rng(), 1 / (params.alpha ?? 3));
        break;
      default:
        x = gauss(rng);
    }
    out.push(x);
  }
  return out;
}

export function histogram(values: number[], bins = 28): { x: number; count: number }[] {
  if (values.length === 0) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const buckets = new Array(bins).fill(0);
  for (const v of values) {
    const idx = Math.min(bins - 1, Math.floor(((v - min) / span) * bins));
    buckets[idx]++;
  }
  return buckets.map((count, i) => ({ x: min + (i / bins) * span, count }));
}
