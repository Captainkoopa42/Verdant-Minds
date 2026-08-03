from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService
from verdant_workbench.app import app, runtime
from verdant_workbench.experiments import ExperimentAuthorRequest, read_experiment_package
from verdant_workbench.release_identity import RELEASE_ID, source_build_identity


def test_release_identity_is_exact_and_content_hashed():
    identity = source_build_identity()
    assert identity["release_id"] == RELEASE_ID == "verdant-minds-v5-workbench-1.0.1"
    for key in ("engine_source_sha256", "workbench_source_sha256", "dependency_lock_sha256"):
        assert re.fullmatch(r"[0-9a-f]{64}", identity[key])


def test_new_experiment_manifest_locks_exact_source_build(tmp_path):
    service = DurableRunService(tmp_path / "lab")
    try:
        project = service.create_project("Build Identity", project_id="proj_build_identity")
        record = service.freeze_experiment(ExperimentAuthorRequest(project_id=project.project_id, title="Build-locked M19"))
        path = service.artifacts.resolve(record.artifact_sha256, verify=True)
        manifest, _ = read_experiment_package(path)
        current = source_build_identity()
        assert manifest.release_id == current["release_id"]
        assert manifest.engine_source_sha256 == current["engine_source_sha256"]
        assert manifest.workbench_source_sha256 == current["workbench_source_sha256"]
        assert manifest.dependency_lock_sha256 == current["dependency_lock_sha256"]
    finally:
        service.close()


def test_release_ui_has_first_class_evidence_and_timeline_surfaces(tmp_path):
    runtime.reset(tmp_path / "ui")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "EVIDENCE / KNOWLEDGE INSPECTOR · 1.0.1" in js.text
        assert "TIMELINE / BRANCH HISTORY · 1.0.1" in js.text
        assert "WORKBENCH 1.0.1 · V5" in js.text
    finally:
        runtime.close()


def test_diagnostics_exposes_release_build_identity(tmp_path):
    runtime.reset(tmp_path / "diag")
    client = TestClient(app)
    try:
        body = client.get("/api/v1/engineering/diagnostics").json()
        assert body["workbench_version"] == "1.0.1"
        assert body["build_identity"]["release_id"] == RELEASE_ID
        assert len(body["build_identity"]["engine_source_sha256"]) == 64
        assert len(body["build_identity"]["workbench_source_sha256"]) == 64
    finally:
        runtime.close()


def test_build_locked_experiment_rejects_mismatched_runtime(monkeypatch, tmp_path):
    service = DurableRunService(tmp_path / "locked")
    try:
        project = service.create_project("Build Lock", project_id="proj_build_lock")
        exp = service.freeze_experiment(ExperimentAuthorRequest(project_id=project.project_id, title="Locked"))
        real = source_build_identity()
        bad = dict(real)
        bad["engine_source_sha256"] = "0" * 64
        monkeypatch.setattr("verdant_workbench.run_service.source_build_identity", lambda: bad)
        run = service.start_experiment(exp.experiment_id)
        finished = service.wait_experiment_run(run.experiment_run_id, timeout=5.0)
        assert finished.status == "failed"
        assert "build identity mismatch" in (finished.error_message or "").lower()
    finally:
        service.close()
