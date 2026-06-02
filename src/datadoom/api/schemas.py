"""Request/response models — the typed surface FastAPI turns into OpenAPI.

The frontend generates its API client from ``/api/openapi.json``, so these
shapes ARE the contract (doc 08). Spec bodies travel as open ``dict`` payloads
(the authoritative validation lives in ``engine.spec``); these models describe
the persistence/metadata envelope around them.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

SpecBody = dict[str, Any]


# --- errors -------------------------------------------------------------------
class ErrorDetail(BaseModel):
    code: str
    message: str
    locator: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# --- specs (stateless helpers) ------------------------------------------------
class ValidateResponse(BaseModel):
    valid: bool = True
    spec_hash: str
    warnings: list[str] = Field(default_factory=list)


class HashResponse(BaseModel):
    spec_hash: str


class EstimateResponse(BaseModel):
    estimated_runtime_seconds: float
    estimated_ram_mb: float
    estimated_size_bytes: int
    features: int
    edges: int
    gpu_required: bool = False


# --- specs of a dataset -------------------------------------------------------
class SpecSummary(BaseModel):
    spec_id: str
    spec_hash: str
    version: int
    datadoom_version: str
    created_at: str


class SpecDetail(SpecSummary):
    body: SpecBody


class SaveSpecResponse(BaseModel):
    spec_id: str
    spec_hash: str
    version: int


# --- runs ---------------------------------------------------------------------
class RunSummary(BaseModel):
    run_id: str
    dataset_id: str
    spec_id: str
    name: str | None = None
    seed: int
    status: str
    stage: str | None = None
    progress_pct: int = 0
    compliance_score: float | None = None
    error: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str


class CreateRunRequest(BaseModel):
    seed: int | None = None
    name: str | None = None


class UpdateRunRequest(BaseModel):
    name: str


class CreateRunResponse(BaseModel):
    run_id: str
    status: str
    seed: int
    ws: str


class CancelResponse(BaseModel):
    status: str


# --- datasets -----------------------------------------------------------------
class LatestRun(BaseModel):
    run_id: str
    status: str
    compliance_score: float | None = None


class DatasetSummary(BaseModel):
    dataset_id: str
    name: str
    description: str | None = None
    status: str
    rows: int | None = None
    features: int | None = None
    compliance_score: float | None = None
    created_at: str
    updated_at: str


class DatasetList(BaseModel):
    items: list[DatasetSummary]
    total: int


class Dataset(BaseModel):
    dataset_id: str
    name: str
    description: str | None = None
    status: str
    current_spec: SpecDetail | None = None
    latest_run: LatestRun | None = None
    created_at: str
    updated_at: str


class CreateDatasetRequest(BaseModel):
    name: str
    description: str | None = None
    spec: SpecBody | None = None


class UpdateDatasetRequest(BaseModel):
    name: str | None = None
    description: str | None = None


# --- artifacts & reports ------------------------------------------------------
class Artifact(BaseModel):
    artifact_id: str
    run_id: str
    version: str
    split: str | None = None
    format: str
    size_bytes: int
    checksum_sha256: str
    created_at: str


class Report(BaseModel):
    report_id: str
    run_id: str
    compliance_score: float | None = None
    distribution: dict[str, Any] | None = None
    correlation: dict[str, Any] | None = None
    mutual_information: dict[str, Any] | None = None
    causal_truth: dict[str, Any] | None = None
    difficulty: dict[str, Any] | None = None
    failures: dict[str, Any] | None = None
    determinism: dict[str, Any] | None = None


class PreviewResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    total: int


# --- templates & plugins & meta ----------------------------------------------
class TemplateSummary(BaseModel):
    id: str
    name: str
    domain: str
    description: str
    tags: list[str] = Field(default_factory=list)


class PluginInfo(BaseModel):
    name: str
    kind: str
    version: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    enabled: bool = True


class HealthResponse(BaseModel):
    status: str = "ok"


class VersionResponse(BaseModel):
    version: str
    datadoom_version: str
    python: str
    platform: str
