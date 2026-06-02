import type { CausalTruth, Preview } from "./types";

/**
 * Structural recovery audit — the transparency analytic. For each derived target
 * whose incoming edges are linear/identity over numeric/boolean parents, we run
 * an ordinary-least-squares regression (target ~ parents) on the realized sample
 * and read the coefficients back. If generation was honest, the recovered slopes
 * should land near the structural weights we declared. This is the in-app version
 * of auditing a CSV with statsmodels' OLS.
 */
export interface RecoveredTerm {
  parent: string;
  recovered: number;
  truth: number | null; // declared structural weight, when comparable
}
export interface Recovery {
  target: string;
  terms: RecoveredTerm[];
  intercept: number;
  residualStd: number;
  r2: number;
  n: number;
  note?: string;
}

const LINEARISH = new Set(["linear", "identity"]);

function columnValues(preview: Preview, name: string): number[] {
  const idx = preview.columns.indexOf(name);
  if (idx < 0) return [];
  return preview.rows.map((r) => {
    const v = r[idx];
    if (typeof v === "boolean") return v ? 1 : 0;
    if (v === "true") return 1;
    if (v === "false") return 0;
    return Number(v);
  });
}

/** Solve (XᵀX + εI) β = Xᵀy via Gaussian elimination. X includes an intercept col. */
function solveOLS(X: number[][], y: number[]): number[] | null {
  const p = X[0]?.length ?? 0;
  if (p === 0) return null;
  const XtX: number[][] = Array.from({ length: p }, () => new Array(p).fill(0));
  const Xty = new Array(p).fill(0);
  for (let r = 0; r < X.length; r++) {
    for (let i = 0; i < p; i++) {
      Xty[i] += X[r][i] * y[r];
      for (let j = 0; j < p; j++) XtX[i][j] += X[r][i] * X[r][j];
    }
  }
  for (let i = 0; i < p; i++) XtX[i][i] += 1e-8; // ridge for stability
  // augmented elimination
  const A = XtX.map((row, i) => [...row, Xty[i]]);
  for (let col = 0; col < p; col++) {
    let piv = col;
    for (let r = col + 1; r < p; r++) if (Math.abs(A[r][col]) > Math.abs(A[piv][col])) piv = r;
    if (Math.abs(A[piv][col]) < 1e-12) return null;
    [A[col], A[piv]] = [A[piv], A[col]];
    const d = A[col][col];
    for (let j = col; j <= p; j++) A[col][j] /= d;
    for (let r = 0; r < p; r++) {
      if (r === col) continue;
      const f = A[r][col];
      for (let j = col; j <= p; j++) A[r][j] -= f * A[col][j];
    }
  }
  return A.map((row) => row[p]);
}

export function recoverSCM(truth: CausalTruth | null | undefined, preview: Preview | undefined): Recovery[] {
  if (!truth || !preview) return [];
  const byTarget = new Map<string, CausalTruth["edges"]>();
  for (const e of truth.edges) {
    if (!e.active) continue;
    if (!byTarget.has(e.to)) byTarget.set(e.to, []);
    byTarget.get(e.to)!.push(e);
  }

  const out: Recovery[] = [];
  for (const [target, edges] of byTarget) {
    const parents = edges.map((e) => e.from);
    const linearish = edges.every((e) => LINEARISH.has(e.fn));
    const y = columnValues(preview, target);
    const parentCols = parents.map((p) => columnValues(preview, p));
    const ok =
      y.length > parents.length + 2 &&
      y.every(Number.isFinite) &&
      parentCols.every((c) => c.length === y.length && c.every(Number.isFinite));

    if (!ok) continue;
    if (!linearish) {
      out.push({
        target,
        terms: parents.map((p) => ({ parent: p, recovered: NaN, truth: null })),
        intercept: NaN,
        residualStd: NaN,
        r2: NaN,
        n: y.length,
        note: "non-linear / categorical structure — not OLS-recoverable",
      });
      continue;
    }

    const X = y.map((_, r) => [1, ...parentCols.map((c) => c[r])]);
    const beta = solveOLS(X, y);
    if (!beta) continue;

    const intercept = beta[0];
    const slopes = beta.slice(1);
    // residuals + R²
    const mean = y.reduce((a, b) => a + b, 0) / y.length;
    let ssRes = 0;
    let ssTot = 0;
    for (let r = 0; r < y.length; r++) {
      const pred = intercept + slopes.reduce((acc, s, i) => acc + s * parentCols[i][r], 0);
      ssRes += (y[r] - pred) ** 2;
      ssTot += (y[r] - mean) ** 2;
    }
    out.push({
      target,
      terms: parents.map((p, i) => ({
        parent: p,
        recovered: slopes[i],
        truth: edges[i].fn === "identity" ? 1 : edges[i].weight ?? null,
      })),
      intercept,
      residualStd: Math.sqrt(ssRes / Math.max(1, y.length - slopes.length - 1)),
      r2: ssTot > 0 ? 1 - ssRes / ssTot : 1,
      n: y.length,
    });
  }
  return out;
}
