from __future__ import annotations

import json
import shutil
from pathlib import Path

from verdant_workbench.models import OrganismConfig, TeachingRequest
from verdant_workbench.repository import WorkbenchRepository
from verdant_workbench.run_service import DurableRunService


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    out = root / "workbench" / "artifacts" / "wb09_workbench_1_0_proof.json"
    home = root / "workbench" / "artifacts" / "_wb09_proof_home"
    if home.exists():
        shutil.rmtree(home)
    service = DurableRunService(home)
    try:
        project = service.create_project("WB09 Proof", project_id="proj_wb09_proof")
        desc = service.create_run(project.project_id, OrganismConfig(seed=909, state_dim=8, run_label="wb09-proof"))
        run_id = desc["run_id"]
        service.teach(run_id, TeachingRequest(context_id="proof", labels=("a", "b", "c")))
        plugin_result = service.invoke_metric_plugin("example_metric", run_id)
        checkpoint = service.save_checkpoint(run_id, label="WB09 proof checkpoint")
        integrity_before = service.integrity_scan()
        plugin_list = service.list_plugins()
    finally:
        service.close()

    # Simulate stale active metadata left by a process crash; canonical checkpoint remains intact.
    repo = WorkbenchRepository(home / "workbench.db")
    try:
        repo.set_run_status(run_id, "active")
    finally:
        repo.close()
    recovered = DurableRunService(home)
    try:
        integrity_after = recovered.integrity_scan()
        recovered_run = recovered.repository.get_run(run_id)
        proof = {
            "schema": "verdant.workbench.wb09-proof.v1",
            "plugin": {
                "plugin_id": plugin_result["plugin_id"],
                "kind": plugin_result["kind"],
                "input_sha256": plugin_result["input_sha256"],
                "output_sha256": plugin_result["output_sha256"],
                "metric": plugin_result["output"],
                "discovered_plugin_count": len(plugin_list),
            },
            "checkpoint": {
                "checkpoint_id": checkpoint.checkpoint_id,
                "artifact_sha256": checkpoint.artifact_sha256,
                "canonical_fingerprint": checkpoint.canonical_fingerprint,
            },
            "integrity_before_restart": integrity_before,
            "integrity_after_restart": integrity_after,
            "crash_recovery": {
                "recovered_stale_runs": recovered.recovered_stale_runs,
                "run_status_after_recovery": recovered_run.status,
            },
        }
        proof["all_gates_pass"] = all([
            plugin_result["kind"] == "metric",
            plugin_result["output"].get("metric_id") == "relation_per_concept",
            integrity_before["all_ok"],
            integrity_after["all_ok"],
            recovered.recovered_stale_runs == 1,
            recovered_run.status == "closed",
        ])
        out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(proof, indent=2, sort_keys=True))
    finally:
        recovered.close()


if __name__ == "__main__":
    main()
