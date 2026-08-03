from __future__ import annotations

from fastapi.testclient import TestClient

from verdant_workbench.app import app, runtime
from verdant_workbench.models import CommandEnvelope, OrganismConfig, TeachingRequest
from verdant_workbench.worker import EngineWorkerSupervisor


def test_isolated_worker_create_teach_snapshot_and_save(tmp_path):
    with EngineWorkerSupervisor.create(
        OrganismConfig(seed=33, state_dim=8, run_label="worker-test"),
        run_id="run_worker",
        organism_id="org_worker",
    ) as worker:
        descriptor = worker.request("descriptor")
        envelope = CommandEnvelope(
            command_id="cmd_worker_1",
            run_id="run_worker",
            organism_id="org_worker",
            command_type="TEACH",
            expected_state_revision=descriptor["state_revision"],
            actor="test",
        )
        request = TeachingRequest(context_id="worker", labels=("alpha", "beta"), event_key="worker-001")
        receipt = worker.request("teach", {"envelope": envelope.model_dump(mode="json"), "request": request.model_dump(mode="json")})
        assert receipt["state_revision_after"] > receipt["state_revision_before"]
        snapshot = worker.request("snapshot", {"scope": "summary"})
        assert snapshot["payload"]["metrics"]["concept_count"] == 2
        checkpoint = tmp_path / "worker.vdk"
        saved = worker.request("save", {"path": str(checkpoint)})
        assert checkpoint.exists()
        assert len(saved["checkpoint_sha256"]) == 64


def test_fastapi_health_and_minimal_run_lifecycle(tmp_path):
    runtime.reset(tmp_path / "api-home")
    client = TestClient(app)
    try:
        health = client.get("/health")
        assert health.status_code == 200
        created = client.post("/api/v1/runs", json={"seed": 44, "state_dim": 8, "run_label": "api-test"})
        assert created.status_code == 200
        descriptor = created.json()
        run_id = descriptor["run_id"]
        taught = client.post(
            f"/api/v1/runs/{run_id}/teach",
            json={
                "context_id": "api",
                "labels": ["one", "two"],
                "event_key": "api-001",
                "expected_state_revision": descriptor["state_revision"],
            },
        )
        assert taught.status_code == 200
        status = client.get(f"/api/v1/runs/{run_id}/status")
        assert status.status_code == 200
        assert status.json()["metrics"]["concept_count"] == 2
    finally:
        runtime.close()


def test_fastapi_project_checkpoint_close_reopen_and_branch(tmp_path):
    runtime.reset(tmp_path / "api-wb02")
    client = TestClient(app)
    try:
        project_response = client.post("/api/v1/projects", json={"name": "API Lab"})
        assert project_response.status_code == 200
        project_id = project_response.json()["project_id"]
        created = client.post(
            f"/api/v1/projects/{project_id}/runs",
            json={"seed": 88, "state_dim": 8, "run_label": "api-wb02"},
        )
        assert created.status_code == 200
        descriptor = created.json()
        run_id = descriptor["run_id"]
        taught = client.post(
            f"/api/v1/runs/{run_id}/teach",
            json={
                "context_id": "api",
                "labels": ["alpha", "beta"],
                "event_key": "api-wb02-001",
                "expected_state_revision": descriptor["state_revision"],
            },
        )
        assert taught.status_code == 200
        saved = client.post(f"/api/v1/runs/{run_id}/checkpoints", json={"label": "branch point"})
        assert saved.status_code == 200
        checkpoint_id = saved.json()["checkpoint_id"]
        assert client.post(f"/api/v1/runs/{run_id}/close").status_code == 200
        assert client.post(f"/api/v1/runs/{run_id}/reopen").status_code == 200
        branched = client.post(f"/api/v1/checkpoints/{checkpoint_id}/branch")
        assert branched.status_code == 200
        child_run = branched.json()["run_id"]
        ancestry = client.get(f"/api/v1/runs/{child_run}/ancestry")
        assert ancestry.status_code == 200
        assert [item["run_id"] for item in ancestry.json()] == [run_id, child_run]
        events = client.get(f"/api/v1/runs/{run_id}/events")
        assert events.status_code == 200
        assert events.json()
    finally:
        runtime.close()
