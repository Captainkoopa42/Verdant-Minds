from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from verdant_workbench import DurableRunService
from verdant_workbench.experiments import ExperimentAuthorRequest, ExperimentForkRequest, read_experiment_package

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / ".wb07-proof-lab"
ARTIFACTS = ROOT / "workbench" / "artifacts"
PROOF = ARTIFACTS / "wb07_experiment_manager_proof.json"
SOURCE_EXPORT = ARTIFACTS / "wb07_m19_reference_experiment.vexp"
RESULT_EXPORT = ARTIFACTS / "wb07_m19_verification_package.vexp"


def main() -> int:
    if LAB.exists():
        shutil.rmtree(LAB)
    LAB.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    service = DurableRunService(LAB)
    project = service.create_project("WB-07 Proof", project_id="proj_wb07_proof")
    template = service.experiment_template(project.project_id)
    experiment = service.freeze_experiment(
        ExperimentAuthorRequest(project_id=project.project_id, title="M19 Reference Verification")
    )
    source_path = service.experiment_artifact_path(experiment.experiment_id)
    shutil.copy2(source_path, SOURCE_EXPORT)
    manifest, embedded = read_experiment_package(source_path)

    started = service.start_experiment(experiment.experiment_id)
    finished = service.wait_experiment_run(started.experiment_run_id, timeout=180.0)
    if finished.status != "completed":
        raise RuntimeError(f"Reference experiment failed: {finished.error_message}")
    first_detail = service.experiment_run_detail(started.experiment_run_id)

    verification = service.verify_experiment_run(started.experiment_run_id)
    verified_record = service.repository.get_experiment_run(started.experiment_run_id)
    result_path = service.experiment_run_artifact_path(started.experiment_run_id)
    shutil.copy2(result_path, RESULT_EXPORT)

    fork = service.fork_experiment(
        experiment.experiment_id,
        ExperimentForkRequest(title="M19 Seed 1902 Fork", seed=1902),
    )
    fork_detail = service.experiment_detail(fork.experiment_id)

    summary = first_detail["summary"]
    d = summary["arms"]["D_full_earned_folds"]
    causal = summary["causal_controls"]
    gates = {
        "reference_curriculum_hash_locked": manifest.curriculum_sha256 == "38ffb6c25056b7f0134e5f2dd923fe08b9cca05318a66f38e3c7582eb102ce4b",
        "reference_curriculum_self_contained_30_events": len(embedded["commands"]) == 30 == manifest.curriculum_event_count,
        "all_reference_headline_checks_pass": all(summary["headline_checks"].values()),
        "all_manifest_assertions_pass": all(item["passed"] for item in first_detail["assertions"]),
        "experiment_runs_outside_workbench_process": first_detail["worker_isolation"]["experiment_worker_pid"] != os.getpid(),
        "arms_use_independent_canonical_state": first_detail["worker_isolation"]["arm_state_isolation"] is True,
        "p_causal_result_preserved": causal["with_structure_work"] == 1 and causal["ablated_work"] == 7 and causal["restored_work"] == 1,
        "q_causal_result_preserved": causal["with_q_work"] == 3 and causal["q_ablated_work"] == 8 and causal["q_restored_work"] == 3,
        "d_compiled_local_work_preserved": d["local_reconstruction_work"] == 1 and d["local_structure_used"] is True,
        "reproduction_hash_matches": verification["reproduction_match"] is True,
        "experiment_marked_verified": verification["verified"] is True and verified_record.verified == 1,
        "fork_preserves_parent_lineage": fork.parent_experiment_id == experiment.experiment_id and fork_detail["manifest"]["parent_experiment_id"] == experiment.experiment_id,
        "fork_is_new_immutable_artifact": fork.artifact_sha256 != experiment.artifact_sha256,
        "source_package_integrity_verified": service.artifacts.verify(experiment.artifact_sha256),
        "result_package_integrity_verified": service.artifacts.verify(verified_record.result_artifact_sha256),
    }
    payload = {
        "schema": "verdant.workbench.wb07-proof.v1",
        "experiment_id": experiment.experiment_id,
        "experiment_run_id": started.experiment_run_id,
        "source_experiment_sha256": experiment.artifact_sha256,
        "scientific_result_sha256": finished.scientific_result_sha256,
        "reproduced_scientific_result_sha256": verification["reproduced_scientific_result_sha256"],
        "worker_isolation": first_detail["worker_isolation"],
        "curriculum_sha256": manifest.curriculum_sha256,
        "curriculum_event_count": manifest.curriculum_event_count,
        "arm_metrics": summary["arms"],
        "causal_controls": causal,
        "refolding": summary["refolding"],
        "assertions": first_detail["assertions"],
        "fork": fork.__dict__,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "exports": {
            "source_experiment": str(SOURCE_EXPORT),
            "verification_package": str(RESULT_EXPORT),
        },
    }
    PROOF.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "all_gates_pass": payload["all_gates_pass"],
        "scientific_result_sha256": payload["scientific_result_sha256"],
        "reproduction_match": verification["reproduction_match"],
        "source": str(SOURCE_EXPORT),
        "result": str(RESULT_EXPORT),
        "proof": str(PROOF),
    }, indent=2), flush=True)
    service.close()
    # multiprocessing's resource tracker can remain alive after a completed
    # fork-based laboratory run in some constrained CI containers. The proof
    # artifacts are fully flushed above; force a clean proof-script exit only.
    os._exit(0)


if __name__ == "__main__":
    raise SystemExit(main())
