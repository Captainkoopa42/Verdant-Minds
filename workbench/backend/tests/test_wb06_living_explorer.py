from __future__ import annotations

from fastapi.testclient import TestClient

from verdant_hierarchy.demo import run as run_hierarchy_demo
from verdant_refolding.demo import run_demo as run_refolding_demo
from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.adapter import VerdantEngineAdapter
from verdant_workbench.app import app, runtime
from verdant_workbench.models import ProbeRequest, TeachingRequest


def cultivate_promoted_p(service: DurableRunService, run_id: str) -> str:
    for index in range(7):
        service.teach(
            run_id,
            TeachingRequest(
                context_id=f"living-{index % 2}",
                labels=("kren", "tar", "vel"),
                event_key=f"wb06-living-{index}",
            ),
        )
    index = service.forensic_structures(run_id)
    eligible = [item for item in index["p_candidates"] if item["status"] == "eligible"]
    assert eligible
    result = service.promote_structure(run_id, eligible[0]["id"])
    sid = result["result"]["structure_id"]
    service.probe(run_id, ProbeRequest(cue_labels=("kren",)))
    return sid


def test_wb06_timeline_is_non_mutating_and_head_matches_live_projection(tmp_path):
    service = DurableRunService(tmp_path / "living")
    try:
        project = service.create_project("Living", project_id="proj_living")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=606, state_dim=64, run_label="living"),
            organism_id="org_living",
            run_id="run_living",
        )
        cultivate_promoted_p(service, descriptor["run_id"])
        before = service.status(descriptor["run_id"])["descriptor"]
        timeline = service.living_explorer_timeline(descriptor["run_id"], max_frames=160)
        head = service.living_explorer_frame(descriptor["run_id"])
        after = service.status(descriptor["run_id"])["descriptor"]
        assert timeline["mutated"] is False
        assert head["mutated"] is False
        assert before["fingerprint"] == after["fingerprint"]
        assert timeline["head_frame_sha256"] == head["frame_sha256"]
        assert timeline["frames"][-1]["frame_sha256"] == head["frame_sha256"]
    finally:
        service.close()


def test_wb06_frames_expose_real_workspace_plasticity_candidate_promotion_and_use(tmp_path):
    service = DurableRunService(tmp_path / "layers")
    try:
        project = service.create_project("Layers", project_id="proj_layers")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=607, state_dim=64, run_label="layers"),
            organism_id="org_layers",
            run_id="run_layers",
        )
        sid = cultivate_promoted_p(service, descriptor["run_id"])
        timeline = service.living_explorer_timeline(descriptor["run_id"], max_frames=180)
        marker_kinds = [m["kind"] for frame in timeline["frames"] for m in frame["markers"]]
        assert "WORKSPACE" in marker_kinds
        assert "PLASTICITY" in marker_kinds
        assert "P_CANDIDATE" in marker_kinds
        assert "P_PROMOTED" in marker_kinds
        assert "P_USED" in marker_kinds
        head = timeline["frames"][-1]
        assert head["workspace"]["active"]
        assert head["plastic_edges"]
        assert any(item["id"] == sid for item in head["p_structures"])
        assert all(edge["strength"] > 0 for edge in head["plastic_edges"])
    finally:
        service.close()


def test_wb06_level_of_detail_reports_omissions_instead_of_hiding_them(tmp_path):
    service = DurableRunService(tmp_path / "lod")
    try:
        project = service.create_project("LOD", project_id="proj_lod")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=608, state_dim=32, run_label="lod"),
            organism_id="org_lod",
            run_id="run_lod",
        )
        for i in range(3):
            service.teach(descriptor["run_id"], TeachingRequest(context_id="lod", labels=(f"n{i}a", f"n{i}b", f"n{i}c"), event_key=f"lod-{i}"))
        frame = service.living_explorer_frame(descriptor["run_id"], max_nodes=3, max_edges=2)
        assert frame["lod"]["rendered_nodes"] <= 3
        assert frame["lod"]["rendered_edges"] <= 2
        assert frame["lod"]["total_nodes"] >= frame["lod"]["rendered_nodes"]
        assert frame["lod"]["omitted_nodes"] == frame["lod"]["total_nodes"] - frame["lod"]["rendered_nodes"]
    finally:
        service.close()


def test_wb06_q_promotion_is_visible_from_actual_engine_records(tmp_path):
    hdir = tmp_path / "hierarchy"
    h_summary = run_hierarchy_demo(hdir)
    h_adapter = VerdantEngineAdapter.load(hdir / "milestone_17_hierarchy_demo.vdk", run_id="run_q_living", organism_id="org_q_living")
    h_timeline = h_adapter.living_explorer_timeline(max_frames=240)
    assert any(m["kind"] == "Q_PROMOTED" for f in h_timeline["frames"] for m in f["markers"])
    assert any(q["id"] == h_summary["layered_structure_id"] for q in h_timeline["frames"][-1]["q_structures"])


def test_wb06_refold_is_visible_from_actual_engine_records(tmp_path):
    rdir = tmp_path / "refold"
    r_summary = run_refolding_demo(rdir)
    r_adapter = VerdantEngineAdapter.load(rdir / "milestone_18_refolding_demo.vdk", run_id="run_r_living", organism_id="org_r_living")
    r_timeline = r_adapter.living_explorer_timeline(max_frames=320)
    refold_markers = [m for f in r_timeline["frames"] for m in f["markers"] if m["kind"] == "REFOLD"]
    assert refold_markers
    assert refold_markers[-1]["payload"]["parent_structure_id"] == r_summary["parent"]["structure_id"]
    head = r_timeline["frames"][-1]
    parent = next(p for p in head["p_structures"] if p["id"] == r_summary["parent"]["structure_id"])
    assert parent["available"] is False
    assert len([p for p in head["p_structures"] if p["lineage_parent_structure_id"] == parent["id"]]) == 2

def test_wb06_api_exposes_frame_and_timeline(tmp_path):
    runtime.reset(tmp_path / "api")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "WB06 API"}).json()
        run = client.post(f"/api/v1/projects/{project['project_id']}/runs", json={"seed": 609, "state_dim": 32, "run_label": "wb06-api"}).json()
        run_id = run["run_id"]
        revision = run["state_revision"]
        for i in range(2):
            response = client.post(f"/api/v1/runs/{run_id}/teach", json={"context_id": "api", "labels": ["a", "b", "c"], "event_key": f"api-{i}", "expected_state_revision": revision})
            assert response.status_code == 200
            revision = response.json()["state_revision_after"]
        frame = client.get(f"/api/v1/runs/{run_id}/explorer/frame")
        timeline = client.get(f"/api/v1/runs/{run_id}/explorer/timeline?max_frames=80")
        assert frame.status_code == 200
        assert timeline.status_code == 200
        assert frame.json()["schema"] == "verdant.workbench.living-frame.v1"
        assert timeline.json()["schema"] == "verdant.workbench.living-timeline.v1"
        assert timeline.json()["head_frame_sha256"] == frame.json()["frame_sha256"]
    finally:
        runtime.close()


def test_wb06_served_ui_is_living_record_backed_canvas(tmp_path):
    runtime.reset(tmp_path / "ui")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        css = client.get("/style.css")
        assert js.status_code == 200 and css.status_code == 200
        assert "EXPLORER / LIVING VIEW · WB-06" in js.text
        assert "livingCanvas" in js.text
        assert "PLAY RECORDING" in js.text
        assert "layout: deterministic display projection" in js.text
        assert "frame_sha256" in js.text
        assert "Living Explorer" in css.text
    finally:
        runtime.close()
