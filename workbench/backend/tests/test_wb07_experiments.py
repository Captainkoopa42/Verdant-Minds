from __future__ import annotations

import os

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService
from verdant_workbench.app import app, runtime
from verdant_workbench.experiments import (
    ExperimentAuthorRequest,
    ExperimentForkRequest,
    evaluate_assertions,
    read_experiment_package,
    run_ethomorphism_isolated,
    scientific_result_sha256,
)
from verdant_benchmarks import BenchmarkConfig


def _fake_result():
    summary = {
        "schema": "verdant.ethomorphism_benchmark.v1",
        "config": {"seed": 1901},
        "curriculum_sha256": "fake",
        "arms": {},
        "causal_controls": {},
        "refolding": {},
        "long_run_health": {},
        "headline_checks": {
            "same_external_curriculum_count_all_arms": True,
            "target_abstraction_not_taught": True,
            "d_forms_earned_structures": True,
            "d_forms_higher_order_q": True,
            "c_has_plasticity_without_promoted_folds": True,
            "all_arms_reconstruct_heldout_world": True,
            "d_uses_compiled_structure": True,
            "p_ablation_restoration_is_causal": True,
            "q_ablation_restoration_is_causal": True,
            "d_rejects_star_from_path_family": True,
            "refolding_preserves_lineage": True,
            "refolding_preserves_semantic_counts": True,
            "c_long_run_within_caps": True,
            "d_long_run_within_caps": True,
        },
    }
    return {
        "summary": summary,
        "scientific_result_sha256": scientific_result_sha256(summary),
        "worker_isolation": {"mode": "test", "arm_state_isolation": True},
    }


def test_wb07_freezes_self_contained_m19_experiment_package(tmp_path):
    service = DurableRunService(tmp_path / "freeze")
    try:
        project = service.create_project("Experiments", project_id="proj_exp")
        record = service.freeze_experiment(ExperimentAuthorRequest(project_id=project.project_id))
        assert service.artifacts.verify(record.artifact_sha256)
        manifest, package = read_experiment_package(service.experiment_artifact_path(record.experiment_id))
        assert manifest.curriculum_sha256 == "38ffb6c25056b7f0134e5f2dd923fe08b9cca05318a66f38e3c7582eb102ce4b"
        assert manifest.curriculum_event_count == 30
        assert len(package["commands"]) == 30
        assert len(manifest.arms) == 4
        assert manifest.expected_assertions
    finally:
        service.close()


def test_wb07_fork_preserves_parent_lineage_and_creates_new_immutable_artifact(tmp_path):
    service = DurableRunService(tmp_path / "fork")
    try:
        project = service.create_project("Experiments", project_id="proj_fork")
        parent = service.freeze_experiment(ExperimentAuthorRequest(project_id=project.project_id, title="Base"))
        child = service.fork_experiment(parent.experiment_id, ExperimentForkRequest(title="Forked", seed=1902))
        detail = service.experiment_detail(child.experiment_id)
        assert child.parent_experiment_id == parent.experiment_id
        assert detail["manifest"]["parent_experiment_id"] == parent.experiment_id
        assert detail["manifest"]["protocol_config"]["seed"] == 1902
        assert child.artifact_sha256 != parent.artifact_sha256
        assert service.artifacts.verify(parent.artifact_sha256)
    finally:
        service.close()


def test_wb07_assertions_are_explicit_and_machine_checkable():
    assertions = ExperimentAuthorRequest(project_id="p").expected_assertions
    assert assertions == ()
    from verdant_workbench.experiments import default_assertions
    result = evaluate_assertions(_fake_result()["summary"], default_assertions())
    assert result and all(item["passed"] for item in result)


def test_wb07_run_and_reproduction_verification_use_frozen_result_artifacts(tmp_path, monkeypatch):
    import verdant_workbench.run_service as run_service_module

    monkeypatch.setattr(run_service_module, "run_ethomorphism_isolated", lambda config: _fake_result())
    service = DurableRunService(tmp_path / "run")
    try:
        project = service.create_project("Experiments", project_id="proj_run")
        experiment = service.freeze_experiment(ExperimentAuthorRequest(project_id=project.project_id))
        xrun = service.start_experiment(experiment.experiment_id)
        finished = service.wait_experiment_run(xrun.experiment_run_id, timeout=10)
        assert finished.status == "completed"
        assert finished.result_artifact_sha256
        detail = service.experiment_run_detail(xrun.experiment_run_id)
        assert detail["verification"]["all_assertions_pass"] is True
        assert len(detail["assertions"]) == finished.assertions_total
        verified = service.verify_experiment_run(xrun.experiment_run_id)
        assert verified["reproduction_match"] is True
        assert verified["verified"] is True
        assert service.repository.get_experiment_run(xrun.experiment_run_id).verified == 1
    finally:
        service.close()


def test_wb07_protocol_runner_reports_explicit_process_and_arm_isolation(monkeypatch):
    import verdant_workbench.experiments as experiments
    fake_summary = _fake_result()["summary"]
    monkeypatch.setattr(experiments, "_run_protocol_process", lambda config: {
        "worker_pid": os.getpid() + 1000, "start_method": "test", "summary": fake_summary
    })
    result = experiments.run_ethomorphism_isolated(BenchmarkConfig())
    assert result["worker_isolation"]["arm_state_isolation"] is True
    assert result["worker_isolation"]["experiment_worker_pid"] != os.getpid()
    assert result["worker_isolation"]["arm_ids"] == [arm.value for arm in __import__("verdant_benchmarks").ArmName]


def test_wb07_api_exposes_template_freeze_fork_and_download(tmp_path):
    runtime.reset(tmp_path / "api")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "Experiment API"}).json()
        pid = project["project_id"]
        template = client.get(f"/api/v1/experiments/templates/ethomorphism-m19?project_id={pid}")
        assert template.status_code == 200
        assert template.json()["curriculum_event_count"] == 30
        frozen = client.post("/api/v1/experiments/freeze", json={"project_id": pid, "title": "Reference"})
        assert frozen.status_code == 200
        eid = frozen.json()["experiment_id"]
        detail = client.get(f"/api/v1/experiments/{eid}")
        assert detail.status_code == 200
        package = client.get(f"/api/v1/experiments/{eid}/package")
        assert package.status_code == 200
        assert package.content[:2] == b"PK"
        child = client.post(f"/api/v1/experiments/{eid}/fork", json={"title": "Reference Fork", "seed": 1902})
        assert child.status_code == 200
        assert child.json()["parent_experiment_id"] == eid
    finally:
        runtime.close()


def test_wb07_served_ui_exposes_experiment_manager_and_verification_controls(tmp_path):
    runtime.reset(tmp_path / "ui")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        css = client.get("/style.css")
        assert js.status_code == 200 and css.status_code == 200
        assert "EXPERIMENT MANAGER · WB-07" in js.text
        assert "RUN EXPERIMENT" in js.text
        assert "VERIFY BY REPRODUCTION" in js.text
        assert "DOWNLOAD VERIFICATION PACKAGE" in js.text
        assert "Experiment Manager" in css.text
    finally:
        runtime.close()
