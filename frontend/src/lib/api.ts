import type {
  Artifact,
  Dataset,
  DatasetSummary,
  Estimate,
  Preview,
  Report,
  RunSummary,
  Spec,
  SpecDetail,
} from "./types";

export class ApiError extends Error {
  code: string;
  locator?: string | null;
  status: number;
  constructor(status: number, code: string, message: string, locator?: string | null) {
    super(message);
    this.status = status;
    this.code = code;
    this.locator = locator;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const env = data?.error ?? {};
    throw new ApiError(res.status, env.code ?? "error", env.message ?? res.statusText, env.locator);
  }
  return data as T;
}

export const api = {
  // meta
  version: () => request<{ version: string; datadoom_version: string }>("/version"),

  // specs
  validate: (spec: Spec) =>
    request<{ valid: boolean; spec_hash: string; warnings: string[] }>("/specs/validate", {
      method: "POST",
      body: JSON.stringify(spec),
    }),
  estimate: (spec: Spec) =>
    request<Estimate>("/specs/estimate", { method: "POST", body: JSON.stringify(spec) }),

  // datasets
  listDatasets: (q?: string) =>
    request<{ items: DatasetSummary[]; total: number }>(
      `/datasets${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  getDataset: (id: string) => request<Dataset>(`/datasets/${id}`),
  createDataset: (body: { name: string; description?: string; spec?: Spec }) =>
    request<Dataset>("/datasets", { method: "POST", body: JSON.stringify(body) }),
  deleteDataset: (id: string) => request<void>(`/datasets/${id}`, { method: "DELETE" }),
  duplicateDataset: (id: string) =>
    request<Dataset>(`/datasets/${id}/duplicate`, { method: "POST" }),
  updateDataset: (id: string, body: { name?: string; description?: string | null }) =>
    request<Dataset>(`/datasets/${id}`, { method: "PATCH", body: JSON.stringify(body) }),

  // runs for a dataset (generation history)
  listRuns: (datasetId: string) => request<RunSummary[]>(`/datasets/${datasetId}/runs`),

  // spec versioning
  saveSpec: (id: string, spec: Spec) =>
    request<{ spec_id: string; spec_hash: string; version: number }>(`/datasets/${id}/spec`, {
      method: "PUT",
      body: JSON.stringify(spec),
    }),
  getSpec: (id: string) => request<SpecDetail>(`/datasets/${id}/spec`),

  // runs
  createRun: (datasetId: string, opts?: { seed?: number; name?: string }) =>
    request<{ run_id: string; status: string; seed: number; ws: string }>(
      `/datasets/${datasetId}/runs`,
      { method: "POST", body: JSON.stringify({ seed: opts?.seed ?? null, name: opts?.name ?? null }) },
    ),
  getRun: (runId: string) => request<RunSummary>(`/runs/${runId}`),
  renameRun: (runId: string, name: string) =>
    request<RunSummary>(`/runs/${runId}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  deleteRun: (runId: string) => request<void>(`/runs/${runId}`, { method: "DELETE" }),
  cancelRun: (runId: string) =>
    request<{ status: string }>(`/runs/${runId}/cancel`, { method: "POST" }),

  // results
  artifacts: (runId: string) => request<Artifact[]>(`/runs/${runId}/artifacts`),
  report: (runId: string) => request<Report>(`/runs/${runId}/report`),
  preview: (runId: string, limit = 50) =>
    request<Preview>(`/runs/${runId}/preview?limit=${limit}`),

  downloadUrl: (artifactId: string) => `/api/artifacts/${artifactId}/download`,
  bundleUrl: (runId: string) => `/api/runs/${runId}/bundle`,
};
