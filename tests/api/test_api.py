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


def test_validate_ok(client: TestClient, sample_spec: dict) -> None:
    r = client.post("/api/specs/validate", json=sample_spec)
    assert r.status_code == 200
    assert r.json()["valid"] is True and len(r.json()["spec_hash"]) == 64


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
