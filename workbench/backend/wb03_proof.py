from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from verdant_workbench import DurableRunService, OrganismConfig, TeachingRequest


def wait_idle(service: DurableRunService, run_id: str, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if service.execution_status(run_id)["state"] == "idle":
            return
        time.sleep(0.05)
    raise RuntimeError("queue did not drain")


def main() -> dict:
    root = Path(tempfile.mkdtemp(prefix="verdant-wb03-proof-"))
    run_id = "run_wb03_proof"
    project_id = "proj_wb03_proof"
    organism_id = "org_wb03_proof"

    first = DurableRunService(root)
    project = first.create_project("WB03 Proof", project_id=project_id)
    created = first.create_run(
        project.project_id,
        OrganismConfig(seed=30303, state_dim=8, run_label="wb03-proof"),
        organism_id=organism_id,
        run_id=run_id,
    )
    initial = first.save_checkpoint(run_id, checkpoint_id="ckpt_wb03_initial", label="initial")
    for idx, labels in enumerate((("kren", "tar"), ("vel",), ("mip", "zog")), start=1):
        first.enqueue_teaching(
            run_id,
            TeachingRequest(context_id="proof-world", labels=labels, event_key=f"wb03-proof-{idx:03d}"),
        )
    queue_before_restart = first.list_queue(run_id)
    first.close()

    second = DurableRunService(root)
    reopened = second.reopen_run(run_id)
    queue_after_restart = second.list_queue(run_id)
    step = second.step_queue(run_id)
    after_step = second.status(run_id)
    second.start_queue(run_id)
    wait_idle(second, run_id)
    final_status = second.status(run_id)
    final = second.save_checkpoint(run_id, checkpoint_id="ckpt_wb03_final", label="after queue")
    branch = second.branch_from_checkpoint(final.checkpoint_id, new_run_id="run_wb03_branch")
    cursor, events = second.events.read_after(run_id, 0, limit=1000)
    event_types = [event.event_type for event in events]

    result = {
        "schema": "verdant.workbench.wb03.proof.v1",
        "root": str(root),
        "checks": {
            "queue_persisted_across_workbench_restart": [item["queue_item_id"] for item in queue_before_restart] == [item["queue_item_id"] for item in queue_after_restart],
            "single_step_processed_exactly_one_item": step["executed"] is True and after_step["execution"]["queue_counts"].get("completed", 0) == 1,
            "run_processed_remaining_queue": final_status["execution"]["queue_counts"].get("completed", 0) == 3,
            "three_teaching_items_created_five_concepts": final_status["metrics"]["concept_count"] == 5,
            "dirty_before_final_checkpoint": final_status["dirty"] is True,
            "final_checkpoint_matches_live_fingerprint": final.canonical_fingerprint == final_status["descriptor"]["fingerprint"],
            "branch_begins_at_exact_final_state": branch["fingerprint"] == final.canonical_fingerprint,
            "run_control_events_are_durable": all(t in event_types for t in ("RUN_STARTED", "RUN_QUEUE_CHANGED", "RUN_PAUSED", "CHECKPOINT_SAVED")),
            "cognitive_events_are_durable": event_types.count("EVIDENCE_ACCEPTED") == 3,
            "event_cursor_is_nonzero": cursor > 0,
        },
        "initial": {
            "fingerprint": initial.canonical_fingerprint,
            "checkpoint_sha256": initial.artifact_sha256,
            "state_revision": initial.state_revision,
        },
        "after_reopen": reopened,
        "after_step": {
            "concept_count": after_step["metrics"]["concept_count"],
            "queue_counts": after_step["execution"]["queue_counts"],
        },
        "final": {
            "fingerprint": final.canonical_fingerprint,
            "checkpoint_sha256": final.artifact_sha256,
            "state_revision": final.state_revision,
            "cycle": final.cycle,
            "queue_counts": final_status["execution"]["queue_counts"],
            "metrics": final_status["metrics"],
        },
        "branch": branch,
        "event_cursor": cursor,
        "event_count": len(events),
        "event_types": event_types,
    }
    second.close()
    return result


if __name__ == "__main__":
    data = main()
    print(json.dumps(data, indent=2, sort_keys=True))
