from __future__ import annotations

import time

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService, OrganismConfig, TeachingRequest
from verdant_workbench.app import app, runtime


def wait_until(predicate, timeout=8.0, interval=0.05):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError("Timed out waiting for Workbench run condition")


def test_wb03_queue_step_run_dirty_checkpoint_and_cursor_events(tmp_path):
    service = DurableRunService(tmp_path / "wb03-lab")
    try:
        project = service.create_project("WB03 Lab", project_id="proj_wb03")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=303, state_dim=8, run_label="wb03"),
            organism_id="org_wb03",
            run_id="run_wb03",
        )
        assert service.status("run_wb03")["dirty"] is True

        first = service.enqueue_teaching("run_wb03", TeachingRequest(context_id="world-a", labels=("kren", "tar"), event_key="wb03-001"))
        second = service.enqueue_teaching("run_wb03", TeachingRequest(context_id="world-a", labels=("vel",), event_key="wb03-002"))
        assert first.sequence_no == 1
        assert second.sequence_no == 2
        assert service.execution_status("run_wb03")["queue_counts"]["queued"] == 2

        stepped = service.step_queue("run_wb03")
        assert stepped["executed"] is True
        queue = service.list_queue("run_wb03")
        assert [item["status"] for item in queue] == ["completed", "queued"]
        assert service.status("run_wb03")["metrics"]["concept_count"] == 2

        service.start_queue("run_wb03")
        wait_until(lambda: service.execution_status("run_wb03")["state"] == "idle")
        queue = service.list_queue("run_wb03")
        assert [item["status"] for item in queue] == ["completed", "completed"]
        assert service.status("run_wb03")["metrics"]["concept_count"] == 3
        assert service.status("run_wb03")["dirty"] is True

        checkpoint = service.save_checkpoint("run_wb03", label="wb03 head")
        status = service.status("run_wb03")
        assert status["dirty"] is False
        assert status["head_checkpoint_id"] == checkpoint.checkpoint_id

        cursor, events = service.events.read_after("run_wb03", 0, limit=500)
        assert cursor > 0
        event_types = [item.event_type for item in events]
        assert "RUN_QUEUE_CHANGED" in event_types
        assert "EVIDENCE_ACCEPTED" in event_types
        assert "CHECKPOINT_SAVED" in event_types
        cursor_2, later = service.events.read_after("run_wb03", cursor, limit=500)
        assert cursor_2 == cursor
        assert later == []
    finally:
        service.close()


def test_wb03_fastapi_queue_controls_and_websocket_event_stream(tmp_path):
    runtime.reset(tmp_path / "api-wb03")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "Live Lab"}).json()
        descriptor = client.post(
            f"/api/v1/projects/{project['project_id']}/runs",
            json={"seed": 404, "state_dim": 8, "run_label": "live-console"},
        ).json()
        run_id = descriptor["run_id"]

        queued = client.post(
            f"/api/v1/runs/{run_id}/queue/teach",
            json={"context_id": "live", "labels": ["alpha", "beta"]},
        )
        assert queued.status_code == 200
        assert queued.json()["status"] == "queued"

        with client.websocket_connect(f"/api/v1/runs/{run_id}/events?cursor=0") as ws:
            first = ws.receive_json()
            assert first["kind"] in {"events", "status"}
            # Pull until we observe the already-persisted queue event.
            observed = []
            for _ in range(5):
                msg = first if not observed and first.get("kind") == "events" else ws.receive_json()
                if msg.get("kind") == "events":
                    observed.extend(item["event_type"] for item in msg["events"])
                if "RUN_QUEUE_CHANGED" in observed:
                    break
            assert "RUN_QUEUE_CHANGED" in observed

        stepped = client.post(f"/api/v1/runs/{run_id}/step")
        assert stepped.status_code == 200
        assert stepped.json()["executed"] is True
        status = client.get(f"/api/v1/runs/{run_id}/status").json()
        assert status["metrics"]["concept_count"] == 2
        assert status["execution"]["queue_counts"]["completed"] == 1
        assert status["dirty"] is True

        saved = client.post(f"/api/v1/runs/{run_id}/checkpoints", json={"label": "live-head"})
        assert saved.status_code == 200
        assert client.get(f"/api/v1/runs/{run_id}/status").json()["dirty"] is False

        listing = client.get(f"/api/v1/runs/{run_id}/events?cursor=0&limit=100")
        assert listing.status_code == 200
        assert listing.json()["cursor"] > 0
        assert any(item["event_type"] == "EVIDENCE_ACCEPTED" for item in listing.json()["events"])
    finally:
        runtime.close()


def test_wb03_serves_zero_dependency_console_build(tmp_path):
    runtime.reset(tmp_path / "ui-wb03")
    client = TestClient(app)
    try:
        response = client.get("/")
        assert response.status_code == 200
        assert "Verdant Workbench" in response.text
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "LIVE CULTIVATION" in js.text
        assert "const API='/api/v1'" in js.text
    finally:
        runtime.close()
