// Per-dataset *view* layout (column widths, pan/zoom, graph node positions &
// sizes). This is presentation state only — deliberately kept OUT of the spec so
// it never affects spec_hash or reproducibility. Persisted to localStorage so a
// resized column / arranged graph survives reloads.

const PREFIX = "datadoom-layout";

export function loadLayout<T>(datasetId: string | undefined, key: string, fallback: T): T {
  if (!datasetId) return fallback;
  try {
    const raw = localStorage.getItem(`${PREFIX}:${datasetId}:${key}`);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function saveLayout(datasetId: string | undefined, key: string, value: unknown): void {
  if (!datasetId) return;
  try {
    localStorage.setItem(`${PREFIX}:${datasetId}:${key}`, JSON.stringify(value));
  } catch {
    /* ignore quota / disabled storage */
  }
}
