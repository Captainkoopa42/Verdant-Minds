from __future__ import annotations

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.app import app, runtime


def test_structure_index_exposes_live_promotion_policy(tmp_path):
    service = DurableRunService(tmp_path / "candidate-gates")
    try:
        project = service.create_project("Candidate Gates", project_id="proj_candidate_gates")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=4201, state_dim=128, run_label="candidate-gates"),
            organism_id="org_candidate_gates",
            run_id="run_candidate_gates",
        )
        index = service.forensic_structures(descriptor["run_id"])
        policy = index["p_promotion_policy"]
        assert policy["minimum_recurrence_events"] == 4
        assert policy["minimum_reconstructability"] == 0.50
        assert policy["minimum_boundary_selectivity"] == 0.65
        assert policy["minimum_internal_cohesion"] == 0.38
        assert policy["minimum_evidence_events"] == 4
        assert policy["minimum_contexts"] == 2
    finally:
        service.close()


def test_served_structure_ui_shows_gates_and_disables_premature_promotion(tmp_path):
    runtime.reset(tmp_path / "candidate-gate-ui")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "candidatePromotionGates" in js.text
        assert "Not yet eligible" in js.text
        assert "Internal cohesion" in js.text
        assert "engine eligibility gates" in js.text
        assert "p_promotion_policy" in js.text
    finally:
        runtime.close()
