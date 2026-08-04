from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from verdant_hierarchy.demo import run as run_hierarchy_demo
from verdant_workbench import CheckpointRecord, DurableRunService, OrganismConfig
from verdant_workbench.adapter import VerdantEngineAdapter
from verdant_workbench.app import app, runtime
from verdant_workbench.models import TeachingRequest


def cultivate_promoted_p(service: DurableRunService, run_id: str) -> str:
    for index in range(7):
        service.teach(
            run_id,
            TeachingRequest(
                context_id=f"context-{index % 2}",
                labels=("kren", "tar", "vel"),
                event_key=f"wb05-triad-{index}",
            ),
        )
    index = service.forensic_structures(run_id)
    eligible = [item for item in index["p_candidates"] if item["status"] == "eligible"]
    assert eligible
    service.promote_structure(run_id, eligible[0]["id"])
    promoted = service.forensic_structures(run_id)["p_structures"]
    assert len(promoted) == 1
    return promoted[0]["id"]


def test_wb05_p_inspector_traces_structure_to_candidate_evidence_governance_and_frozen_topology(tmp_path):
    service = DurableRunService(tmp_path / "wb05-forensics")
    try:
        project = service.create_project("WB05 Forensics", project_id="proj_wb05")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1414, state_dim=64, run_label="wb05-forensics"),
            organism_id="org_wb05",
            run_id="run_wb05",
        )
        sid = cultivate_promoted_p(service, descriptor["run_id"])
        detail = service.forensic_structure_detail(descriptor["run_id"], sid)

        assert detail["kind"] == "P"
        assert detail["record"]["structure_id"] == sid
        assert detail["candidate"]["candidate_id"] == detail["record"]["source_candidate_id"]
        assert len(detail["candidate_history"]) >= 4
        assert detail["promotion_event"]["structure_id"] == sid
        assert detail["council_decision"]["decision_event_id"] == detail["record"]["council_decision_event_id"]
        assert {item["display_label"] for item in detail["member_concepts"]} == {"kren", "tar", "vel"}
        assert len(detail["frozen_edges"]) == 3
        assert all(item["source_label"] and item["target_label"] for item in detail["frozen_edges"])
        assert len(detail["evidence"]) >= 7
        assert {item["event_key"] for item in detail["evidence"] if not item.get("missing")} >= {
            "wb05-triad-0", "wb05-triad-1"
        }
    finally:
        service.close()


def test_wb05_replay_formation_is_pure_canonical_history(tmp_path):
    service = DurableRunService(tmp_path / "wb05-replay")
    try:
        project = service.create_project("Replay Lab", project_id="proj_replay")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1414, state_dim=64, run_label="wb05-replay"),
            organism_id="org_replay",
            run_id="run_replay",
        )
        sid = cultivate_promoted_p(service, descriptor["run_id"])
        before = service.status(descriptor["run_id"])["descriptor"]
        replay = service.forensic_structure_replay(descriptor["run_id"], sid)
        after = service.status(descriptor["run_id"])["descriptor"]
        assert replay["frame_count"] >= 5
        assert replay["frames"][-1]["phase"] == "promotion"
        assert replay["mutated"] is False
        assert replay["fingerprint_before"] == replay["fingerprint_after"]
        assert before["fingerprint"] == after["fingerprint"]
        assert before["state_revision"] == after["state_revision"]
    finally:
        service.close()


def test_wb05_causal_compare_reproduces_p_ablation_and_restoration(tmp_path):
    service = DurableRunService(tmp_path / "wb05-causal")
    try:
        project = service.create_project("Causal Lab", project_id="proj_causal")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1414, state_dim=64, run_label="wb05-causal"),
            organism_id="org_causal",
            run_id="run_causal",
        )
        sid = cultivate_promoted_p(service, descriptor["run_id"])
        result = service.causal_compare_structure(descriptor["run_id"], sid, "kren")
        with_p = result["with_structure"]
        ablated = result["ablated"]
        restored = result["restored"]
        work = lambda item: item["cost"]["concepts_inspected"] + item["cost"]["associations_traversed"]
        assert with_p["structure_id"] == sid
        assert ablated["structure_id"] is None
        assert restored["structure_id"] == sid
        assert work(with_p) < work(ablated)
        assert work(restored) == work(with_p)
        assert set(with_p["reconstructed_concept_ids"]) == set(ablated["reconstructed_concept_ids"]) == set(restored["reconstructed_concept_ids"])
        assert result["available_after"] is True
        detail = service.forensic_structure_detail(descriptor["run_id"], sid)
        actions = [item["action"] for item in detail["availability_events"]]
        assert "ablate" in actions and "restore" in actions
        assert len(detail["uses"]) == 2  # only enabled/restored probes actually used P
    finally:
        service.close()


def test_wb05_q_inspector_and_replay_use_actual_hierarchy_records(tmp_path):
    output = tmp_path / "hierarchy-demo"
    summary = run_hierarchy_demo(output)
    adapter = VerdantEngineAdapter.load(
        output / "milestone_17_hierarchy_demo.vdk",
        run_id="run_q_forensic",
        organism_id="org_q_forensic",
    )
    index = adapter.forensic_list_structures()
    assert index["q_structures"]
    qid = summary["layered_structure_id"]
    detail = adapter.forensic_structure_detail(qid)
    assert detail["kind"] == "Q"
    assert detail["record"]["layered_structure_id"] == qid
    assert len(detail["member_structures"]) == 3
    assert detail["promotion_event"]["layered_structure_id"] == qid
    assert detail["council_decision"]["decision_event_id"] == detail["record"]["council_decision_event_id"]
    replay = adapter.forensic_structure_replay(qid)
    assert replay["mutated"] is False
    assert replay["frames"][-1]["phase"] == "promotion"
    graph = adapter.forensic_structure_graph(qid)
    assert graph["kind"] == "Q"
    assert len(graph["nodes"]) == 4
    assert len(graph["edges"]) == 3


def test_wb05_q_causal_lab_records_held_out_and_negative_controls(tmp_path):
    output = tmp_path / "hierarchy-causal-demo"
    summary = run_hierarchy_demo(output)
    checkpoint_path = output / "milestone_17_hierarchy_demo.vdk"
    loaded = VerdantEngineAdapter.load(
        checkpoint_path,
        run_id="run_q_causal",
        organism_id="org_q_causal",
    )
    descriptor = loaded.descriptor()

    service = DurableRunService(tmp_path / "q-causal-lab")
    try:
        project = service.create_project("Q Causal Lab", project_id="proj_q_causal")
        service.create_run(
            project.project_id,
            OrganismConfig(seed=1901, state_dim=16, run_label="q-import"),
            organism_id="org_q_causal",
            run_id="run_q_causal",
        )
        service.close_run("run_q_causal")
        artifact = service.artifacts.ingest_file(checkpoint_path)
        checkpoint = CheckpointRecord(
            checkpoint_id="ckpt_q_causal",
            run_id="run_q_causal",
            organism_id="org_q_causal",
            artifact_sha256=artifact.sha256,
            artifact_size_bytes=artifact.size_bytes,
            canonical_fingerprint=descriptor.fingerprint,
            state_revision=descriptor.state_revision,
            cycle=descriptor.cycle,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_checkpoint_id=None,
            label="controlled Q fixture",
        )
        service.repository.add_checkpoint(checkpoint)
        service.repository.update_run_head(
            "run_q_causal",
            state_revision=descriptor.state_revision,
            cycle=descriptor.cycle,
            fingerprint=descriptor.fingerprint,
            status="closed",
            head_checkpoint_id=checkpoint.checkpoint_id,
        )
        service.reopen_run("run_q_causal")

        qid = summary["layered_structure_id"]
        held_out = service.causal_compare_hierarchy(
            "run_q_causal",
            qid,
            summary["novel_query_structure_id"],
            expected_outcome="family_match",
        )
        assert held_out["query_scope"] == "held_out"
        assert held_out["passed"] is True
        assert held_out["with_q"]["layered_structure_id"] == qid
        assert held_out["q_ablated"]["layered_structure_id"] is None
        assert held_out["q_restored"]["layered_structure_id"] == qid
        assert held_out["with_q"]["cost"]["comparison_work"] < held_out[
            "q_ablated"
        ]["cost"]["comparison_work"]

        negative = service.causal_compare_hierarchy(
            "run_q_causal",
            qid,
            summary["unrelated_star_structure_id"],
            expected_outcome="negative_control",
        )
        assert negative["query_scope"] == "held_out"
        assert negative["passed"] is True
        assert negative["with_q"]["layered_structure_id"] is None
        assert negative["q_restored"]["layered_structure_id"] is None
        assert negative["available_after"] is True

        event_types = [
            event.event_type for event in service.events.read_run("run_q_causal")
        ]
        assert event_types.count("LAYERED_PROBE_COMMITTED") == 6
        assert event_types.count("LAYERED_STRUCTURE_AVAILABILITY_CHANGED") == 4
    finally:
        service.close()


def test_wb05_api_exposes_structure_inspection_graph_replay_and_interventions(tmp_path):
    runtime.reset(tmp_path / "api-wb05")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "WB05 API"}).json()
        run = client.post(
            f"/api/v1/projects/{project['project_id']}/runs",
            json={"seed": 1414, "state_dim": 64, "run_label": "wb05-api"},
        ).json()
        run_id = run["run_id"]
        revision = run["state_revision"]
        for index in range(7):
            response = client.post(
                f"/api/v1/runs/{run_id}/teach",
                json={
                    "context_id": f"context-{index % 2}",
                    "labels": ["kren", "tar", "vel"],
                    "event_key": f"wb05-api-{index}",
                    "expected_state_revision": revision,
                },
            )
            assert response.status_code == 200
            revision = response.json()["state_revision_after"]
        index = client.get(f"/api/v1/runs/{run_id}/structures")
        assert index.status_code == 200
        candidate = next(item for item in index.json()["p_candidates"] if item["status"] == "eligible")
        promoted = client.post(
            f"/api/v1/runs/{run_id}/structure-candidates/{candidate['id']}/promote",
            json={"expected_state_revision": revision},
        )
        assert promoted.status_code == 200
        sid = promoted.json()["result"]["structure_id"]
        assert client.get(f"/api/v1/runs/{run_id}/structures/{sid}").status_code == 200
        replay = client.get(f"/api/v1/runs/{run_id}/structures/{sid}/replay")
        assert replay.status_code == 200 and replay.json()["mutated"] is False
        graph = client.get(f"/api/v1/runs/{run_id}/structures/{sid}/graph")
        assert graph.status_code == 200 and len(graph.json()["nodes"]) == 3
        causal = client.post(f"/api/v1/runs/{run_id}/structures/{sid}/causal-compare", json={"cue_label": "kren"})
        assert causal.status_code == 200
        assert causal.json()["with_structure"]["structure_id"] == sid
        assert causal.json()["ablated"]["structure_id"] is None
    finally:
        runtime.close()


def test_wb05_serves_structures_and_explorer_surfaces(tmp_path):
    runtime.reset(tmp_path / "ui-wb05")
    client = TestClient(app)
    try:
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "STRUCTURES / FORENSIC INSPECTOR" in js.text
        assert "EXPLORER / FORENSIC TOPOLOGY" in js.text
        assert "Replay formation" in js.text
        assert "Causal ablation laboratory" in js.text
        assert "Q causal laboratory" in js.text
        assert "WB-05" in js.text
    finally:
        runtime.close()
