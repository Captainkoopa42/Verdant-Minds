from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from verdant_workbench import DurableRunService, OrganismConfig, TeachingRequest


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    proof_path = repo_root / "artifacts" / "wb02_persistence_branch_proof.json"
    proof_path.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="verdant-wb02-proof-"))
    try:
        service = DurableRunService(temp_root)
        project = service.create_project("WB02 Proof", project_id="proj_wb02_proof")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1901, state_dim=16, run_label="wb02-proof"),
            organism_id="org_wb02_proof",
            run_id="run_wb02_root",
        )
        sequence = [
            ("world-a", ("kren", "tar"), "wb02-proof-001"),
            ("world-a", ("tar", "vel"), "wb02-proof-002"),
            ("world-b", ("kren", "tar"), "wb02-proof-003"),
            ("world-b", ("tar", "vel"), "wb02-proof-004"),
        ]
        for index, (context, labels, event_key) in enumerate(sequence, start=1):
            current = service.status("run_wb02_root")["descriptor"]
            service.teach(
                "run_wb02_root",
                TeachingRequest(context_id=context, labels=labels, event_key=event_key),
                expected_state_revision=current["state_revision"],
                command_id=f"cmd_wb02_proof_{index:03d}",
            )
        checkpoint = service.save_checkpoint(
            "run_wb02_root", label="root branch point", checkpoint_id="ckpt_wb02_root"
        )
        root_artifact_bytes = service.checkpoint_path(checkpoint.checkpoint_id).read_bytes()
        event_ids_before = [event.event_id for event in service.events.read_run("run_wb02_root")]
        service.close_run("run_wb02_root")
        service.close()

        reopened = DurableRunService(temp_root)
        reopened_descriptor = reopened.reopen_run("run_wb02_root")
        reopen_matches = reopened_descriptor["fingerprint"] == checkpoint.canonical_fingerprint
        root_bytes_after_reopen = reopened.checkpoint_path("ckpt_wb02_root").read_bytes()
        root_bytes_match = root_bytes_after_reopen == root_artifact_bytes
        events_after = [event.event_id for event in reopened.events.read_run("run_wb02_root")]
        event_ledger_match = events_after == event_ids_before

        child_descriptor = reopened.branch_from_checkpoint("ckpt_wb02_root", new_run_id="run_wb02_child")
        child_starts_equal = child_descriptor["fingerprint"] == checkpoint.canonical_fingerprint
        ancestry = reopened.ancestry("run_wb02_child")
        reopened.teach(
            "run_wb02_child",
            TeachingRequest(context_id="child", labels=("mip",), event_key="wb02-child-001"),
            expected_state_revision=child_descriptor["state_revision"],
            command_id="cmd_wb02_child_001",
        )
        child_checkpoint = reopened.save_checkpoint(
            "run_wb02_child", label="child diverged", checkpoint_id="ckpt_wb02_child"
        )
        parent_unchanged = reopened.checkpoint_path("ckpt_wb02_root").read_bytes() == root_artifact_bytes
        child_diverged = child_checkpoint.canonical_fingerprint != checkpoint.canonical_fingerprint
        event_index_count = len(reopened.repository.list_event_index("run_wb02_root"))
        reopened.close()

        proof = {
            "schema": "verdant.workbench.wb02-proof.v1",
            "project_id": project.project_id,
            "root_run_id": "run_wb02_root",
            "root_checkpoint_id": checkpoint.checkpoint_id,
            "root_checkpoint_sha256": checkpoint.artifact_sha256,
            "root_canonical_fingerprint": checkpoint.canonical_fingerprint,
            "root_state_revision": checkpoint.state_revision,
            "root_cycle": checkpoint.cycle,
            "root_event_count": len(event_ids_before),
            "root_event_index_count_after_reopen": event_index_count,
            "reopen_fingerprint_matches": reopen_matches,
            "checkpoint_bytes_preserved": root_bytes_match,
            "event_ledger_preserved": event_ledger_match,
            "child_run_id": "run_wb02_child",
            "child_started_from_exact_parent_state": child_starts_equal,
            "child_checkpoint_id": child_checkpoint.checkpoint_id,
            "child_checkpoint_sha256": child_checkpoint.artifact_sha256,
            "child_canonical_fingerprint": child_checkpoint.canonical_fingerprint,
            "child_diverged_after_new_experience": child_diverged,
            "parent_checkpoint_immutable_after_branch": parent_unchanged,
            "ancestry": [item["run_id"] for item in ancestry],
            "all_exit_checks_passed": all([
                reopen_matches,
                root_bytes_match,
                event_ledger_match,
                child_starts_equal,
                child_diverged,
                parent_unchanged,
                [item["run_id"] for item in ancestry] == ["run_wb02_root", "run_wb02_child"],
                event_index_count == len(event_ids_before),
            ]),
        }
        proof_path.write_text(json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(proof, indent=2, sort_keys=True))
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
