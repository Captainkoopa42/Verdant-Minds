from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService
from verdant_workbench.app import app, runtime
from verdant_workbench.models import OrganismConfig, TeachingRequest
from verdant_workbench.plugins import PluginError, PluginManager


def test_wb09_bundled_metric_plugin_is_hash_verified_and_out_of_process(tmp_path):
    service = DurableRunService(tmp_path / "plugins")
    try:
        plugins = service.list_plugins()
        manifest = next(item["manifest"] for item in plugins if item.get("valid") and item["manifest"]["plugin_id"] == "example_metric")
        assert manifest["kind"] == "metric"
        # Invoke manager directly with controlled metrics to prove the data-only contract.
        result = service.plugins.invoke("example_metric", {"metrics": {"concept_count": 4, "relation_count": 3}}, required_kind="metric")
        assert result.output["metric_id"] == "relation_per_concept"
        assert result.output["value"] == 0.75
        assert len(result.input_sha256) == 64 and len(result.output_sha256) == 64
    finally:
        service.close()


def test_wb09_plugin_code_hash_tamper_is_rejected(tmp_path):
    root = tmp_path / "plugins"
    plug = root / "tamper"
    plug.mkdir(parents=True)
    script = plug / "metric.py"
    script.write_text('import json,sys; json.dump({"ok": True}, sys.stdout)\n', encoding="utf-8")
    manifest = {
        "schema": "verdant.plugin.manifest.v1", "plugin_id": "tamper", "name": "Tamper", "version": "1",
        "api_version": "verdant.workbench.plugin.v1", "kind": "metric", "entrypoint": ["python", "metric.py"],
        "permissions": ["read_metrics"], "description": "", "timeout_seconds": 1.0,
        "code_sha256": "0" * 64,
    }
    (plug / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    manager = PluginManager(root)
    with pytest.raises(PluginError, match="code hash mismatch"):
        manager.load_manifest("tamper")


def test_wb09_plugin_path_escape_and_unsupported_permissions_are_rejected(tmp_path):
    root = tmp_path / "plugins"
    plug = root / "badperm"
    plug.mkdir(parents=True)
    script = plug / "metric.py"
    script.write_text('print("{}")\n', encoding="utf-8")
    digest = hashlib.sha256(script.read_bytes()).hexdigest()
    manifest = {
        "schema": "verdant.plugin.manifest.v1", "plugin_id": "badperm", "name": "Bad", "version": "1",
        "api_version": "verdant.workbench.plugin.v1", "kind": "metric", "entrypoint": ["python", "metric.py"],
        "permissions": ["mutate_kernel"], "description": "", "timeout_seconds": 1.0, "code_sha256": digest,
    }
    (plug / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")
    manager = PluginManager(root)
    with pytest.raises(PluginError, match="Unsupported plugin permissions"):
        manager.load_manifest("badperm")


def test_wb09_integrity_scan_detects_artifact_corruption(tmp_path):
    service = DurableRunService(tmp_path / "integrity")
    try:
        project = service.create_project("Integrity", project_id="proj_integrity")
        desc = service.create_run(project.project_id, OrganismConfig(seed=7, state_dim=8))
        run_id = desc["run_id"]
        service.teach(run_id, TeachingRequest(context_id="x", labels=("kren", "tar")))
        cp = service.save_checkpoint(run_id)
        assert service.integrity_scan()["all_ok"] is True
        path = service.artifacts.resolve(cp.artifact_sha256, verify=False)
        path.write_bytes(path.read_bytes() + b"tamper")
        scan = service.integrity_scan()
        assert scan["all_ok"] is False
        row = next(item for item in scan["checkpoints"] if item["checkpoint_id"] == cp.checkpoint_id)
        assert row["ok"] is False
    finally:
        service.close()


def test_wb09_api_exposes_plugins_diagnostics_and_integrity(tmp_path):
    runtime.reset(tmp_path / "api")
    client = TestClient(app)
    try:
        plugins = client.get("/api/v1/plugins")
        assert plugins.status_code == 200
        assert any(item.get("valid") and item["manifest"]["plugin_id"] == "example_metric" for item in plugins.json())
        diag = client.get("/api/v1/engineering/diagnostics")
        assert diag.status_code == 200
        assert diag.json()["workbench_version"] == "1.0.1"
        integrity = client.get("/api/v1/engineering/integrity")
        assert integrity.status_code == 200
        assert integrity.json()["all_ok"] is True
    finally:
        runtime.close()


def test_wb09_startup_recovers_stale_active_run_metadata(tmp_path):
    from verdant_workbench.repository import WorkbenchRepository
    service = DurableRunService(tmp_path / "recovery")
    try:
        project = service.create_project("Recovery", project_id="proj_recovery")
        desc = service.create_run(project.project_id, OrganismConfig(seed=9, state_dim=8))
        run_id = desc["run_id"]
    finally:
        service.close()
    # Simulate a process crash residue by forcing the persisted row back to active.
    repo = WorkbenchRepository(tmp_path / "recovery" / "workbench.db")
    try:
        repo.set_run_status(run_id, "active")
    finally:
        repo.close()
    recovered = DurableRunService(tmp_path / "recovery")
    try:
        assert recovered.recovered_stale_runs == 1
        assert recovered.repository.get_run(run_id).status == "closed"
    finally:
        recovered.close()


def test_wb09_served_ui_exposes_connections_and_engineering_surfaces(tmp_path):
    runtime.reset(tmp_path / "ui")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "PROVIDER CONNECTIONS · WB-08" in js.text
        assert "ENGINEERING · WB-09 / WORKBENCH 1.0" in js.text
        assert "CAPTURE IMMUTABLY" in js.text
        assert "RUN EXAMPLE METRIC ON ACTIVE ORGANISM" in js.text
    finally:
        runtime.close()


def test_wb09_metric_plugin_api_operates_on_live_run_without_kernel_access(tmp_path):
    runtime.reset(tmp_path / "plugin-api")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name":"Plugin API"}).json()
        run = client.post(f"/api/v1/projects/{project['project_id']}/runs", json={"seed":17,"state_dim":8,"run_label":"plugin-test"})
        assert run.status_code == 200, run.text
        run_id = run.json()["run_id"]
        taught = client.post(f"/api/v1/runs/{run_id}/teach", json={"context_id":"p","labels":["a","b","c"]})
        assert taught.status_code == 200, taught.text
        metric = client.post(f"/api/v1/plugins/example_metric/metric/{run_id}")
        assert metric.status_code == 200, metric.text
        body = metric.json()
        assert body["kind"] == "metric"
        assert body["output"]["metric_id"] == "relation_per_concept"
    finally:
        runtime.close()
