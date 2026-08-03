from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.curriculum import CurriculumCompileRequest, CurriculumFreezeRequest


def wait_idle(service: DurableRunService, run_id: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = service.execution_status(run_id)
        if status["state"] in {"idle", "paused", "stopped"} and status["queue_counts"].get("queued", 0) == 0:
            return
        time.sleep(0.05)
    raise RuntimeError("Timed out waiting for editable curriculum run")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    artifact_dir = repo_root / "workbench" / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    proof_root = artifact_dir / "wb041_proof_lab"
    if proof_root.exists():
        shutil.rmtree(proof_root)

    service = DurableRunService(proof_root)
    try:
        project = service.create_project("WB-04.1 Editable Teaching Proof", project_id="proj_wb041_proof")
        bundle = {
            "schema": "verdant.teaching.bundle.v1",
            "language_scaffold": {
                "grammar_rules": ["transitive_svo"],
                "lexicon": [
                    {"lemma": "kren", "category": "noun", "forms": ["kren"], "attributes": {}},
                    {"lemma": "move", "category": "verb", "forms": ["move", "moves", "moved"], "attributes": {}},
                    {"lemma": "tar", "category": "noun", "forms": ["tar"], "attributes": {}},
                ],
                "notes": "Explicit parser scaffold; authored rather than inferred.",
            },
            "items": [
                {
                    "item_id": "explicit-world-relation",
                    "context_id": "editor-proof",
                    "source_text": "This sentence deliberately does not describe the compiled relation.",
                    "concepts": [
                        {"label": "kren", "attributes": {"kind": "entity"}},
                        {"label": "tar", "attributes": {"kind": "entity"}},
                    ],
                    "relations": [
                        {"source": "kren", "relation": "moves_toward", "target": "tar", "directed": True, "weight": 0.8, "confidence": 1.0}
                    ],
                    "claims": [],
                    "confidence": 1.0,
                    "provenance": {"author": "human", "purpose": "explicit-record proof"},
                    "grammar_annotation": {"subject": "kren", "predicate": "move", "relation": "toward", "object": "tar"},
                    "lexicon_annotation": [
                        {"surface": "kren", "role": "noun"},
                        {"surface": "moves", "lemma": "move", "role": "verb"},
                        {"surface": "toward", "role": "relation"},
                        {"surface": "tar", "role": "noun"},
                    ],
                },
                {
                    "item_id": "claim-hot",
                    "context_id": "contradiction-proof",
                    "source_text": "A kren is hot.",
                    "concepts": [{"label": "kren", "attributes": {}}, {"label": "hot", "attributes": {}}],
                    "relations": [],
                    "claims": [{
                        "subject": "kren", "predicate": "has_property", "object": "hot", "polarity": "affirmed",
                        "source_class": "human_testimony", "confidence": 1.0, "rationale": "deliberate claim A", "attributes": {}
                    }],
                    "confidence": 1.0,
                    "provenance": {"author": "human", "experiment": "contradictory-teaching"},
                    "grammar_annotation": {}, "lexicon_annotation": [],
                },
                {
                    "item_id": "claim-not-hot",
                    "context_id": "contradiction-proof",
                    "source_text": "The same kren is not hot.",
                    "concepts": [{"label": "kren", "attributes": {}}, {"label": "hot", "attributes": {}}],
                    "relations": [],
                    "claims": [{
                        "subject": "kren", "predicate": "has_property", "object": "hot", "polarity": "negated",
                        "source_class": "human_testimony", "confidence": 1.0, "rationale": "deliberate claim B", "attributes": {}
                    }],
                    "confidence": 1.0,
                    "provenance": {"author": "human", "experiment": "contradictory-teaching"},
                    "grammar_annotation": {}, "lexicon_annotation": [],
                },
            ],
            "notes": "Workbench validates schema and provenance, not truth.",
        }
        source = json.dumps(bundle, indent=2)
        request = CurriculumCompileRequest(
            project_id=project.project_id,
            title="WB-04.1 Editable Teaching Example",
            source_format="teaching_bundle_json",
            source_text=source,
            state_dim=32,
        )
        compiled = service.compile_curriculum(request)
        frozen = service.freeze_curriculum(CurriculumFreezeRequest(
            **request.model_dump(), expected_compiled_sha256=compiled["compiled_sha256"]
        ))
        package_path = service.artifacts.resolve(frozen.artifact_sha256, verify=True)
        example_path = artifact_dir / "wb041_editable_teaching_example.vcurr"
        shutil.copy2(package_path, example_path)

        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=4041, state_dim=32, run_label="wb041-proof"),
            organism_id="org_wb041_proof",
            run_id="run_wb041_proof",
        )
        queued = service.queue_curriculum(descriptor["run_id"], frozen.curriculum_id)
        service.start_queue(descriptor["run_id"])
        wait_idle(service, descriptor["run_id"])
        status = service.status(descriptor["run_id"])
        grammar = service.grammar_status(descriptor["run_id"])
        detail = service.curriculum_detail(frozen.curriculum_id)

        first_command = detail["compiled_commands"][0]
        concept_labels = sorted(item["label"] for item in first_command["concept_proposals"])
        relation_type = first_command["relation_proposals"][0]["relation_type"]
        source_text = first_command["semantic_evidence_details"]["source_text"]

        gates = {
            "editable_bundle_compiled": compiled["source_format"] == "teaching_bundle_json",
            "source_sentence_not_used_as_hidden_semantic_parser": relation_type == "moves_toward" and concept_labels == ["kren", "tar"] and "does not describe" in source_text,
            "language_scaffold_queued_before_experiences": queued["scaffold_item_count"] == 4 and queued["experience_item_count"] == 3,
            "grammar_rule_installed": "transitive_svo" in grammar["enabled_rules"],
            "lexicon_installed": any(x["form"] == "moves" and x["lemma"] == "move" for x in grammar["lexicon"]),
            "contradictory_claims_accepted": status["metrics"]["claim_count"] >= 2 and status["metrics"]["contradiction_count"] >= 1,
            "frozen_package_roundtrips_scaffold": detail["language_scaffold"] == compiled["language_scaffold"],
        }
        proof = {
            "schema": "verdant.workbench.wb041.proof.v1",
            "title": "WB-04.1 Editable Teaching Records Proof",
            "compiled_sha256": compiled["compiled_sha256"],
            "source_sha256": compiled["source_sha256"],
            "curriculum_id": frozen.curriculum_id,
            "curriculum_artifact_sha256": frozen.artifact_sha256,
            "experience_item_count": compiled["item_count"],
            "scaffold_item_count": compiled["scaffold_item_count"],
            "queued_item_count": queued["item_count"],
            "final_cycle": status["descriptor"]["cycle"],
            "final_state_revision": status["descriptor"]["state_revision"],
            "final_fingerprint": status["descriptor"]["fingerprint"],
            "claim_count": status["metrics"]["claim_count"],
            "contradiction_count": status["metrics"]["contradiction_count"],
            "enabled_grammar_rules": grammar["enabled_rules"],
            "gates": gates,
            "all_gates_pass": all(gates.values()),
            "example_curriculum": str(example_path.relative_to(repo_root)),
        }
        output = artifact_dir / "wb041_editable_teaching_proof.json"
        output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(proof, indent=2))
        if not proof["all_gates_pass"]:
            raise SystemExit(1)
    finally:
        service.close()


if __name__ == "__main__":
    main()
