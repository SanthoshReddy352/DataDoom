# 06 — Internal Data Models

> Domain entities and their Pydantic/ORM shapes. Obeys `00_README_Index.md`. Persistence DDL in `07_Database_Schema.md`; spec shapes in `04`.

There are **two model families**:
1. **Spec models** — Pydantic v2 models that mirror the spec file (validation + the engine's in-memory config). Pure, no DB.
2. **Persistence models** — entities stored in the metadata DB (Dataset, Spec snapshot, GenerationRun, Artifact, Report, optionally User).

---

## 1. Spec Models (Pydantic, engine-side)

These live in `engine/spec/` and are the parsed, validated form of `04`.

```python
# engine/spec/models.py  (illustrative)
from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional, Union

class NumericFeature(BaseModel):
    type: Literal["numeric"]
    dist: Optional[str] = None          # None => derived via causal
    params: dict[str, float] = {}
    min: Optional[float] = None
    max: Optional[float] = None
    dtype: Literal["int", "float"] = "float"
    description: Optional[str] = None

class CategoricalFeature(BaseModel):
    type: Literal["categorical"]
    categories: list[str]
    weights: Optional[list[float]] = None

class BooleanFeature(BaseModel):
    type: Literal["boolean"]
    rate: float = 0.5

class DatetimeFeature(BaseModel):
    type: Literal["datetime"]
    start: str; end: str
    granularity: Literal["second","minute","hour","day"] = "day"
    dist: str = "uniform"

class TextFeature(BaseModel):
    type: Literal["text"]
    generator: str = "lorem"
    length: dict[str, int] = {"min": 5, "max": 30}

Feature = Union[NumericFeature, CategoricalFeature, BooleanFeature, DatetimeFeature, TextFeature]

class CausalEdge(BaseModel):
    src: str = Field(alias="from")
    dst: str = Field(alias="to")
    fn: str                              # linear|logistic|polynomial|map|identity|<plugin>
    weight: Optional[float] = None
    bias: Optional[float] = None
    coeffs: Optional[list[float]] = None
    mapping: Optional[dict[str, float]] = None

class CausalGraph(BaseModel):
    edges: list[CausalEdge] = []
    noise: dict[str, dict] = {}          # node -> {dist, params} | {dist: none}
    interventions: list[dict] = []

class Difficulty(BaseModel):
    target: Union[str, dict]             # tier name OR {task, metric, band:[a,b]}
    label: str
    probe: str = "logreg"
    max_iters: int = 8
    knobs: list[str] = ["noise", "imbalance"]

class Failure(BaseModel):
    type: str                            # mcar|mar|mnar|label_noise|feature_noise|drift|covariate_shift|leakage|<plugin>
    # remaining fields are type-specific and validated by the FailureMode plugin/handler
    model_config = {"extra": "allow"}

class ExportSpec(BaseModel):
    formats: list[str] = ["csv"]
    versions: list[Literal["clean","injected"]] = ["clean"]
    splits: Optional[dict[str, float]] = None
    shuffle: bool = True
    metadata: bool = True

class Spec(BaseModel):
    datadoom_version: str
    name: str
    description: Optional[str] = None
    seed: Optional[int] = None
    rows: int = Field(ge=1)
    features: dict[str, Feature]
    causal: Optional[CausalGraph] = None
    difficulty: Optional[Difficulty] = None
    failures: list[Failure] = []
    export: ExportSpec = ExportSpec()
    meta: dict = {}

    # cross-field validation: acyclicity, references, derived vs sampled, etc. (see 04 §9)
    @model_validator(mode="after")
    def _validate(self): ...
```

Key derived/computed (not authored):
- `Spec.spec_hash()` → canonical-JSON SHA256 with `seed` excluded (see `05 §1`).
- `Spec.canonical()` → canonical JSON string.

---

## 2. RunContext (engine-side, transient)

The in-memory state threaded through the pipeline (not persisted directly):

```python
class RunContext:
    spec: Spec                  # frozen snapshot
    spec_hash: str
    seed: int                   # resolved (generated if absent)
    rng: RNGFactory             # engine.rng — per-namespace generators
    frames: dict[str, "DataFrame"]   # clean, injected, splits
    reports: ReportBundle
    progress: ProgressEmitter   # publishes stage events to the WS hub
    cancelled: bool
```

---

## 3. Persistence Entities

> Local mode: no `User`; a single implicit owner. Team mode (opt-in) adds `User` + `owner_id` FKs. All entities use UUID string PKs and UTC timestamps.

### 3.1 Dataset (user-facing managed item)
| field | type | notes |
|---|---|---|
| `dataset_id` | UUID PK | |
| `name` | text | unique per owner |
| `description` | text? | |
| `current_spec_id` | FK → Spec | the editable draft snapshot |
| `status` | enum | draft / running / completed / failed |
| `latest_run_id` | FK → GenerationRun? | |
| `owner_id` | FK → User? | team mode only |
| `created_at` / `updated_at` | timestamp | |

### 3.2 Spec (immutable snapshot)
| field | type | notes |
|---|---|---|
| `spec_id` | UUID PK | |
| `dataset_id` | FK → Dataset | |
| `spec_hash` | text | SHA256 (seed-excluded) |
| `body` | JSON | canonicalized spec document |
| `datadoom_version` | text | |
| `version` | int | monotonic per dataset (edit = new snapshot) |
| `created_at` | timestamp | |

Immutability: a Spec row is **never updated**. "Edit" creates a new Spec (new `version`) and repoints `Dataset.current_spec_id`.

### 3.3 GenerationRun (one execution)
| field | type | notes |
|---|---|---|
| `run_id` | UUID PK | |
| `dataset_id` | FK | |
| `spec_id` | FK | the snapshot executed |
| `seed` | bigint | resolved seed |
| `status` | enum | queued / running / completed / failed / cancelled |
| `stage` | text | current/last pipeline stage |
| `progress_pct` | int | 0–100 |
| `error` | JSON? | message + traceback + stage on failure |
| `metrics` | JSON | per-stage durations, peak RAM est, throughput |
| `started_at` / `finished_at` | timestamp? | |
| `created_at` | timestamp | |

### 3.4 Artifact (output file)
| field | type | notes |
|---|---|---|
| `artifact_id` | UUID PK | |
| `run_id` | FK | |
| `version` | enum | clean / injected |
| `split` | enum? | train / test / hidden_test / full |
| `format` | text | csv / parquet / json / plugin |
| `storage_uri` | text | local path or s3:// |
| `checksum_sha256` | text | bitwise-repro anchor |
| `size_bytes` | bigint | |
| `created_at` | timestamp | |

### 3.5 Report (evaluation outputs)
One row per run, sectioned JSON (or normalized sub-tables if needed later):
| field | type | notes |
|---|---|---|
| `report_id` | UUID PK | |
| `run_id` | FK | |
| `compliance_score` | float | overall |
| `distribution` | JSON | per-feature target/empirical/KS/p-value/clamp |
| `correlation` | JSON | Pearson + MI matrices |
| `causal_truth` | JSON | the true graph G |
| `difficulty` | JSON | target band, achieved metric, probe, iters |
| `failures` | JSON | per-failure diff summaries |
| `determinism` | JSON | spec_hash, seed, namespace key digests, checksums |
| `created_at` | timestamp | |

### 3.6 User (team mode only)
| field | type | notes |
|---|---|---|
| `user_id` | UUID PK | |
| `email` | text | |
| `role` | enum | admin / member / viewer |
| `auth_provider` | text | |
| `created_at` | timestamp | |

### 3.7 Plugin (runtime registry; optional persistence)
Plugins are discovered at runtime (entry points + local dir). We may persist a lightweight record for the UI:
| field | type | notes |
|---|---|---|
| `name` | text PK | |
| `kind` | enum | distribution / structural_fn / failure_mode / exporter / template / probe_model |
| `version` | text | |
| `schema` | JSON | UI-render schema fragment |
| `enabled` | bool | |

---

## 4. Entity Relationships

```
User (team only) 1───* Dataset 1───* Spec (immutable snapshots)
                                 │
                                 └───* GenerationRun ─1──* Artifact
                                              │
                                              └─1──1 Report
```

- A Dataset has many Spec snapshots (version history) and many runs.
- A run references exactly one Spec snapshot and produces many Artifacts + one Report.

---

## 5. Invariants

1. Spec rows are immutable; edits create new versions.
2. `(spec_hash, seed)` is the reproducibility key; the same pair must always yield equal Artifact checksums on the pinned path.
3. A run is artifact-transactional: either all its Artifacts + Report are committed, or none.
4. Engine spec models (`§1`) and the persisted `Spec.body` agree byte-for-byte after canonicalization.
5. No multi-tenant fields are required in local mode; `owner_id`/`User` are nullable/absent until team mode.
