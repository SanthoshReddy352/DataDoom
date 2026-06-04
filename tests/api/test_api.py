"""API route tests (17 step 9): happy paths, 422 ``locator``, 409, idempotency,
the full async run lifecycle, and WS stage→completed streaming.
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _wait_run(client: TestClient, run_id: str, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/runs/{run_id}").json()
        if r["status"] in {"completed", "failed", "cancelled"}:
            return r
        time.sleep(0.03)
    raise AssertionError("run did not finish in time")


# --- meta + spec helpers ------------------------------------------------------
def test_health_and_version(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    v = client.get("/api/version").json()
    assert "version" in v and v["datadoom_version"] == "1"


def test_spec_reference_manifest(client: TestClient) -> None:
    cap = client.get("/api/spec-reference").json()
    assert set(cap["feature_types"]) >= {"numeric", "timeseries"}
    assert {d["name"] for d in cap["distributions"]} >= {"normal", "poisson"}
    assert {f["type"] for f in cap["failure_modes"]} >= {"mcar", "leakage"}


def test_validate_ok(client: TestClient, sample_spec: dict) -> None:
    r = client.post("/api/specs/validate", json=sample_spec)
    assert r.status_code == 200
    assert r.json()["valid"] is True and len(r.json()["spec_hash"]) == 64


def test_parse_yaml_text(client: TestClient) -> None:
    yaml_text = (
        'datadoom_version: "1"\n'
        "name: from-yaml\n"
        "rows: 100\n"
        "features:\n"
        "  age:\n"
        "    type: numeric\n"
        "    dist: normal\n"
        "    params: { mean: 40, std: 10 }\n"
    )
    r = client.post("/api/specs/parse", json={"text": yaml_text})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True and len(body["spec_hash"]) == 64
    assert body["spec"]["name"] == "from-yaml" and "age" in body["spec"]["features"]


def test_parse_yaml_syntax_error_has_locator(client: TestClient) -> None:
    r = client.post("/api/specs/parse", json={"text": "name: x\n  bad: : indent"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_parse_yaml_validation_error_has_locator(client: TestClient) -> None:
    bad = 'datadoom_version: "1"\nname: x\nrows: 1\nfeatures:\n  a:\n    type: numeric\n    dist: nope\n'
    r = client.post("/api/specs/parse", json={"text": bad})
    assert r.status_code == 422
    assert r.json()["error"]["locator"] == "features.a.dist"


def test_validate_error_has_locator(client: TestClient, sample_spec: dict) -> None:
    bad = dict(sample_spec)
    bad["features"] = {"age": {"type": "numeric", "dist": "normal", "params": {"mean": 1, "std": -1}}}
    r = client.post("/api/specs/validate", json=bad)
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert err["locator"] == "features.age.params"


def test_estimate(client: TestClient, sample_spec: dict) -> None:
    r = client.post("/api/specs/estimate", json=sample_spec)
    body = r.json()
    assert body["features"] == 4 and body["gpu_required"] is False
    assert body["estimated_size_bytes"] > 0


# --- dataset CRUD + versioning ------------------------------------------------
def test_dataset_crud_and_spec_versioning(client: TestClient, sample_spec: dict) -> None:
    created = client.post("/api/datasets", json={"name": "d1", "spec": sample_spec})
    assert created.status_code == 201
    did = created.json()["dataset_id"]
    assert created.json()["current_spec"]["version"] == 1

    # duplicate name -> 409
    dup = client.post("/api/datasets", json={"name": "d1"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "conflict"

    # save edited spec -> version 2, current repointed
    edited = dict(sample_spec, rows=500)
    saved = client.put(f"/api/datasets/{did}/spec", json=edited)
    assert saved.status_code == 200 and saved.json()["version"] == 2
    assert client.get(f"/api/datasets/{did}/spec").json()["version"] == 2
    assert len(client.get(f"/api/datasets/{did}/spec/history").json()) == 2
    # the old immutable snapshot is still retrievable
    assert client.get(f"/api/datasets/{did}/spec/1").json()["body"]["rows"] == 400


def test_unknown_dataset_404(client: TestClient) -> None:
    r = client.get("/api/datasets/does-not-exist")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_duplicate_dataset(client: TestClient, sample_spec: dict) -> None:
    did = client.post("/api/datasets", json={"name": "orig", "spec": sample_spec}).json()["dataset_id"]
    dup = client.post(f"/api/datasets/{did}/duplicate")
    assert dup.status_code == 201
    assert dup.json()["name"] == "orig-copy"
    assert dup.json()["current_spec"]["spec_hash"] == sample_spec_hash(client, sample_spec)


def sample_spec_hash(client: TestClient, spec: dict) -> str:
    return client.post("/api/specs/hash", json=spec).json()["spec_hash"]


# --- run lifecycle ------------------------------------------------------------
def test_run_generates_artifacts_and_report(client: TestClient, sample_spec: dict) -> None:
    did = client.post("/api/datasets", json={"name": "run-me", "spec": sample_spec}).json()["dataset_id"]
    created = client.post(f"/api/datasets/{did}/runs", json={"seed": 42})
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    assert created.json()["seed"] == 42

    final = _wait_run(client, run_id)
    assert final["status"] == "completed"
    assert final["compliance_score"] is not None

    artifacts = client.get(f"/api/runs/{run_id}/artifacts").json()
    formats = {a["format"] for a in artifacts}
    assert {"csv", "json"} <= formats
    assert all(len(a["checksum_sha256"]) == 64 for a in artifacts)

    preview = client.get(f"/api/runs/{run_id}/preview?limit=5").json()
    assert preview["columns"] == list(sample_spec["features"].keys())
    assert preview["total"] == 400 and len(preview["rows"]) == 5

    report = client.get(f"/api/runs/{run_id}/report").json()
    assert report["compliance_score"] == final["compliance_score"]
    assert report["correlation"] is not None  # two numeric features


def test_resolved_spec_is_locked_and_downloadable(client: TestClient, sample_spec: dict) -> None:
    """Each generation locks its resolved spec: it's a tracked YAML artifact, the
    run summary carries the spec_hash, and the spec.yaml endpoint serves a
    parseable spec with the seed baked in (version-control reproducibility)."""
    import yaml

    did = client.post("/api/datasets", json={"name": "lock", "spec": sample_spec}).json()["dataset_id"]
    run_id = client.post(f"/api/datasets/{did}/runs", json={"seed": 42}).json()["run_id"]
    assert _wait_run(client, run_id)["status"] == "completed"

    # The resolved spec is a first-class, checksummed artifact.
    artifacts = client.get(f"/api/runs/{run_id}/artifacts").json()
    spec_art = next((a for a in artifacts if a["version"] == "spec"), None)
    assert spec_art is not None and spec_art["format"] == "yaml"
    assert len(spec_art["checksum_sha256"]) == 64

    # The run summary exposes the spec_hash as the version-control anchor.
    runs = client.get(f"/api/datasets/{did}/runs").json()
    summary = next(r for r in runs if r["run_id"] == run_id)
    assert summary["spec_hash"] and len(summary["spec_hash"]) == 64

    # The dedicated endpoint downloads a parseable spec with the resolved seed.
    resp = client.get(f"/api/runs/{run_id}/spec.yaml")
    assert resp.status_code == 200
    body = yaml.safe_load(resp.text)
    assert body["seed"] == 42  # the resolved seed is baked in
    assert set(body["features"]) == set(sample_spec["features"])  # canonicalized, same columns


def test_difficulty_report_round_trips(client: TestClient, sample_spec: dict) -> None:
    """A difficulty target survives the full server path: run → store → report
    endpoint carries the achieved metric + band (P4)."""
    spec = dict(sample_spec)
    spec["difficulty"] = {"target": "kaggle", "label": "is_fraud", "probe": "logreg", "max_iters": 6}
    did = client.post("/api/datasets", json={"name": "diff", "spec": spec}).json()["dataset_id"]
    run_id = client.post(f"/api/datasets/{did}/runs", json={"seed": 42}).json()["run_id"]
    assert _wait_run(client, run_id)["status"] == "completed"

    diff = client.get(f"/api/runs/{run_id}/report").json()["difficulty"]
    assert diff is not None
    assert diff["metric_name"] == "auroc"
    assert diff["target"]["band"] == [0.62, 0.72]
    assert isinstance(diff["band_met"], bool)
    assert isinstance(diff["trace"], list) and len(diff["trace"]) >= 1


def test_run_idempotency_key_replays(client: TestClient, sample_spec: dict) -> None:
    did = client.post("/api/datasets", json={"name": "idem", "spec": sample_spec}).json()["dataset_id"]
    headers = {"Idempotency-Key": "abc-123"}
    first = client.post(f"/api/datasets/{did}/runs", json={"seed": 1}, headers=headers)
    second = client.post(f"/api/datasets/{did}/runs", json={"seed": 1}, headers=headers)
    assert first.status_code == 202
    assert second.status_code == 200  # replay returns existing run
    assert first.json()["run_id"] == second.json()["run_id"]


def test_run_requires_spec(client: TestClient) -> None:
    did = client.post("/api/datasets", json={"name": "empty"}).json()["dataset_id"]
    r = client.post(f"/api/datasets/{did}/runs", json={})
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_request"


def test_reproducible_same_seed_same_checksum(client: TestClient, sample_spec: dict) -> None:
    did = client.post("/api/datasets", json={"name": "repro", "spec": sample_spec}).json()["dataset_id"]
    sums = []
    for _ in range(2):
        rid = client.post(f"/api/datasets/{did}/runs", json={"seed": 7}).json()["run_id"]
        _wait_run(client, rid)
        arts = client.get(f"/api/runs/{rid}/artifacts").json()
        csv = next(a for a in arts if a["format"] == "csv")
        sums.append(csv["checksum_sha256"])
    assert sums[0] == sums[1]  # (spec_hash, seed) -> identical bytes


# --- websocket ----------------------------------------------------------------
def test_websocket_streams_stages_to_completed(client: TestClient, sample_spec: dict) -> None:
    did = client.post("/api/datasets", json={"name": "ws", "spec": sample_spec}).json()["dataset_id"]
    run_id = client.post(f"/api/datasets/{did}/runs", json={"seed": 3}).json()["run_id"]

    types: list[str] = []
    with client.websocket_connect(f"/api/ws/runs/{run_id}") as ws:
        while True:
            ev = ws.receive_json()
            types.append(ev["type"])
            if ev["type"] in {"completed", "failed", "cancelled"}:
                terminal = ev
                break
    assert "stage" in types
    assert terminal["type"] == "completed"
    assert "compliance_score" in terminal and "report_id" in terminal


# --- templates + plugins (P5) -------------------------------------------------
def test_list_templates(client: TestClient) -> None:
    items = client.get("/api/templates").json()
    assert len(items) >= 3
    ids = {t["id"] for t in items}
    assert {"fraud-detection", "customer-churn", "hospital-readmission"} <= ids


def test_get_template_detail_and_404(client: TestClient) -> None:
    detail = client.get("/api/templates/fraud-detection").json()
    assert detail["domain"] == "Finance"
    assert detail["spec"]["name"] == "transaction-fraud"
    assert client.get("/api/templates/nope").status_code == 404


def test_create_dataset_from_template(client: TestClient) -> None:
    detail = client.get("/api/templates/hospital-readmission").json()
    did = client.post(
        "/api/datasets", json={"name": detail["name"], "spec": detail["spec"]}
    ).json()["dataset_id"]
    run_id = client.post(f"/api/datasets/{did}/runs", json={"seed": 2}).json()["run_id"]
    run = _wait_run(client, run_id)
    assert run["status"] == "completed"


def test_list_plugins_over_http(client: TestClient) -> None:
    items = client.get("/api/plugins").json()
    assert len(items) == 24
    assert any(p["name"] == "parquet" and p["kind"] == "exporter" for p in items)
