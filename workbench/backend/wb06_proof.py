from __future__ import annotations

import json
import tempfile
from pathlib import Path

from verdant_hierarchy.demo import run as run_hierarchy_demo
from verdant_refolding.demo import run_demo as run_refolding_demo
from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.adapter import VerdantEngineAdapter
from verdant_workbench.models import ProbeRequest, TeachingRequest


def marker_kinds(timeline: dict) -> list[str]:
    return [marker["kind"] for frame in timeline["frames"] for marker in frame["markers"]]


def main() -> dict:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_dir = repo_root / "workbench" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="verdant-wb06-proof-") as td:
        root = Path(td)
        service = DurableRunService(root / "workbench-home")
        try:
            project = service.create_project("WB06 proof", project_id="proj_wb06_proof")
            descriptor = service.create_run(
                project.project_id,
                OrganismConfig(seed=606, state_dim=64, run_label="wb06-proof"),
                organism_id="org_wb06_proof",
                run_id="run_wb06_proof",
            )
            for index in range(7):
                service.teach(
                    descriptor["run_id"],
                    TeachingRequest(
                        context_id=f"context-{index % 2}",
                        labels=("kren", "tar", "vel"),
                        event_key=f"wb06-proof-{index}",
                    ),
                )
            structure_index = service.forensic_structures(descriptor["run_id"])
            candidate = next(item for item in structure_index["p_candidates"] if item["status"] == "eligible")
            promotion = service.promote_structure(descriptor["run_id"], candidate["id"])
            p_id = promotion["result"]["structure_id"]
            service.probe(descriptor["run_id"], ProbeRequest(cue_labels=("kren",)))

            before = service.status(descriptor["run_id"])["descriptor"]
            timeline = service.living_explorer_timeline(descriptor["run_id"], max_frames=180)
            head = service.living_explorer_frame(descriptor["run_id"])
            lod = service.living_explorer_frame(descriptor["run_id"], max_nodes=2, max_edges=1)
            after = service.status(descriptor["run_id"])["descriptor"]
        finally:
            service.close()

        hierarchy_dir = root / "hierarchy"
        hierarchy_summary = run_hierarchy_demo(hierarchy_dir)
        hierarchy_adapter = VerdantEngineAdapter.load(
            hierarchy_dir / "milestone_17_hierarchy_demo.vdk",
            run_id="run_wb06_q",
            organism_id="org_wb06_q",
        )
        q_timeline = hierarchy_adapter.living_explorer_timeline(max_frames=240)

        refold_dir = root / "refold"
        refold_summary = run_refolding_demo(refold_dir)
        refold_adapter = VerdantEngineAdapter.load(
            refold_dir / "milestone_18_refolding_demo.vdk",
            run_id="run_wb06_refold",
            organism_id="org_wb06_refold",
        )
        refold_timeline = refold_adapter.living_explorer_timeline(max_frames=320)

    p_markers = marker_kinds(timeline)
    q_markers = marker_kinds(q_timeline)
    refold_markers = [m for f in refold_timeline["frames"] for m in f["markers"] if m["kind"] == "REFOLD"]
    refold_head = refold_timeline["frames"][-1]
    refold_parent_id = refold_summary["parent"]["structure_id"]
    refold_parent = next(p for p in refold_head["p_structures"] if p["id"] == refold_parent_id)
    refold_children = [p for p in refold_head["p_structures"] if p["lineage_parent_structure_id"] == refold_parent_id]

    result = {
        "workbench_milestone": "WB-06",
        "name": "Living Explorer",
        "p_structure_id": p_id,
        "p_timeline": {
            "frame_count": timeline["frame_count"],
            "head_frame_sha256": timeline["head_frame_sha256"],
            "head_direct_sha256": head["frame_sha256"],
            "canonical_fingerprint_before": before["fingerprint"],
            "canonical_fingerprint_after": after["fingerprint"],
            "head_counts": head["counts"],
            "marker_kinds": sorted(set(p_markers)),
            "workspace_active": len(head["workspace"]["active"]),
            "plastic_edge_count": len(head["plastic_edges"]),
        },
        "lod_probe": lod["lod"],
        "q_timeline": {
            "layered_structure_id": hierarchy_summary["layered_structure_id"],
            "frame_count": q_timeline["frame_count"],
            "q_promoted_visible": "Q_PROMOTED" in q_markers,
            "q_count_at_head": len(q_timeline["frames"][-1]["q_structures"]),
        },
        "refold_timeline": {
            "parent_structure_id": refold_parent_id,
            "frame_count": refold_timeline["frame_count"],
            "refold_marker_count": len(refold_markers),
            "parent_available_at_head": refold_parent["available"],
            "child_count_at_head": len(refold_children),
        },
    }
    result["gates"] = {
        "timeline_projection_is_non_mutating": (
            not timeline["mutated"]
            and before["fingerprint"] == after["fingerprint"]
            and head["canonical_fingerprint_before"] == head["canonical_fingerprint_after"]
        ),
        "live_head_equals_replay_head": timeline["head_frame_sha256"] == head["frame_sha256"],
        "workspace_layer_is_recorded": "WORKSPACE" in p_markers and len(head["workspace"]["active"]) > 0,
        "plasticity_layer_is_recorded": "PLASTICITY" in p_markers and len(head["plastic_edges"]) > 0,
        "p_development_is_visible": all(kind in p_markers for kind in ("P_CANDIDATE", "P_PROMOTED", "P_USED")),
        "q_promotion_is_visible": "Q_PROMOTED" in q_markers and result["q_timeline"]["q_count_at_head"] >= 1,
        "refolding_is_visible": len(refold_markers) >= 1 and not refold_parent["available"] and len(refold_children) == 2,
        "lod_reports_omission": lod["lod"]["rendered_nodes"] <= 2 and lod["lod"]["omitted_nodes"] >= 1,
    }
    result["all_gates_pass"] = all(result["gates"].values())

    output = artifact_dir / "wb06_living_explorer_proof.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    main()
