from __future__ import annotations

import json
import tempfile
from pathlib import Path

from verdant_hierarchy.demo import run as run_hierarchy_demo
from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.adapter import VerdantEngineAdapter
from verdant_workbench.models import TeachingRequest


def main() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_dir = repo_root / "workbench" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="verdant-wb05-proof-") as td:
        root = Path(td)
        service = DurableRunService(root / "workbench-home")
        try:
            project = service.create_project("WB05 proof", project_id="proj_wb05_proof")
            descriptor = service.create_run(
                project.project_id,
                OrganismConfig(seed=1414, state_dim=64, run_label="wb05-proof"),
                organism_id="org_wb05_proof",
                run_id="run_wb05_proof",
            )
            for index in range(7):
                service.teach(
                    descriptor["run_id"],
                    TeachingRequest(
                        context_id=f"context-{index % 2}",
                        labels=("kren", "tar", "vel"),
                        event_key=f"wb05-proof-{index}",
                    ),
                )
            index = service.forensic_structures(descriptor["run_id"])
            candidate = next(item for item in index["p_candidates"] if item["status"] == "eligible")
            promotion = service.promote_structure(descriptor["run_id"], candidate["id"])
            sid = promotion["result"]["structure_id"]
            detail = service.forensic_structure_detail(descriptor["run_id"], sid)
            before_replay = service.status(descriptor["run_id"])["descriptor"]
            replay = service.forensic_structure_replay(descriptor["run_id"], sid)
            after_replay = service.status(descriptor["run_id"])["descriptor"]
            graph = service.forensic_structure_graph(descriptor["run_id"], sid)
            causal = service.causal_compare_structure(descriptor["run_id"], sid, "kren")
        finally:
            service.close()

        hierarchy_dir = root / "hierarchy"
        h_summary = run_hierarchy_demo(hierarchy_dir)
        q_adapter = VerdantEngineAdapter.load(
            hierarchy_dir / "milestone_17_hierarchy_demo.vdk",
            run_id="run_wb05_q_proof",
            organism_id="org_wb05_q_proof",
        )
        qid = h_summary["layered_structure_id"]
        q_detail = q_adapter.forensic_structure_detail(qid)
        q_replay = q_adapter.forensic_structure_replay(qid)
        q_graph = q_adapter.forensic_structure_graph(qid)

    def work(item):
        cost = item["cost"]
        return int(cost["concepts_inspected"]) + int(cost["associations_traversed"])

    evidence_keys = sorted(
        item.get("event_key") for item in detail["evidence"]
        if item.get("event_key")
    )
    result = {
        "workbench_milestone": "WB-05",
        "name": "Structures + Forensic Explorer",
        "p_structure_id": sid,
        "p_candidate_id": candidate["id"],
        "p_candidate_history_frames": len(detail["candidate_history"]),
        "p_evidence_records": len(detail["evidence"]),
        "p_frozen_edges": len(detail["frozen_edges"]),
        "p_member_labels": sorted(item["display_label"] for item in detail["member_concepts"]),
        "p_evidence_event_keys": evidence_keys,
        "p_replay": {
            "frame_count": replay["frame_count"],
            "mutated": replay["mutated"],
            "fingerprint_before": replay["fingerprint_before"],
            "fingerprint_after": replay["fingerprint_after"],
            "live_fingerprint_before": before_replay["fingerprint"],
            "live_fingerprint_after": after_replay["fingerprint"],
        },
        "p_graph": {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])},
        "p_causal_ablation": {
            "cue_label": causal["cue_label"],
            "with_p_work": work(causal["with_structure"]),
            "ablated_work": work(causal["ablated"]),
            "restored_work": work(causal["restored"]),
            "with_p_structure_id": causal["with_structure"]["structure_id"],
            "ablated_structure_id": causal["ablated"]["structure_id"],
            "restored_structure_id": causal["restored"]["structure_id"],
            "available_after": causal["available_after"],
            "same_reconstruction": (
                set(causal["with_structure"]["reconstructed_concept_ids"])
                == set(causal["ablated"]["reconstructed_concept_ids"])
                == set(causal["restored"]["reconstructed_concept_ids"])
            ),
        },
        "q_structure_id": qid,
        "q_member_count": len(q_detail["member_structures"]),
        "q_evidence_records": len(q_detail["evidence"]),
        "q_replay_frames": q_replay["frame_count"],
        "q_replay_mutated": q_replay["mutated"],
        "q_graph": {"nodes": len(q_graph["nodes"]), "edges": len(q_graph["edges"])},
    }
    result["gates"] = {
        "p_traces_to_candidate_history": result["p_candidate_history_frames"] >= 4,
        "p_traces_to_exact_evidence": all(f"wb05-proof-{i}" in evidence_keys for i in range(7)),
        "p_traces_to_governance": detail["council_decision"].get("decision_event_id") == detail["record"]["council_decision_event_id"],
        "replay_is_non_mutating": not replay["mutated"] and before_replay["fingerprint"] == after_replay["fingerprint"],
        "graph_is_record_backed": len(graph["nodes"]) == 3 and len(graph["edges"]) == len(detail["frozen_edges"]),
        "p_ablation_removes_advantage": work(causal["with_structure"]) < work(causal["ablated"]),
        "p_restoration_restores_advantage": work(causal["restored"]) == work(causal["with_structure"]),
        "p_reconstruction_unchanged": result["p_causal_ablation"]["same_reconstruction"],
        "q_inspector_reads_real_hierarchy": len(q_detail["member_structures"]) == 3 and q_detail["promotion_event"] is not None,
        "q_replay_is_non_mutating": not q_replay["mutated"],
    }
    result["all_gates_pass"] = all(result["gates"].values())

    output = artifact_dir / "wb05_forensic_explorer_proof.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
