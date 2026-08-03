from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from verdant_benchmarks.ethomorphism import EthomorphismBenchmarkHarness
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import VerdantKernel
from verdant_workbench.curriculum import CurriculumCompileRequest, CurriculumFreezeRequest
from verdant_workbench.models import (
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LanguageSentenceTeachRequest,
    LexemeTeachRequest,
    OrganismConfig,
)
from verdant_workbench.run_service import DurableRunService


def wait_idle(service: DurableRunService, run_id: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = service.execution_status(run_id)
        if status["queue_counts"].get("queued", 0) == 0 and status["state"] in {"idle", "paused", "stopped"}:
            return
        time.sleep(0.05)
    raise TimeoutError("WB04 proof timed out waiting for curriculum execution")


def main() -> dict:
    with tempfile.TemporaryDirectory(prefix="verdant-wb04-proof-") as tmp:
        service = DurableRunService(Path(tmp) / "lab")
        try:
            project = service.create_project("WB04 Proof", project_id="proj_wb04_proof")
            template = service.m19_curriculum_template()
            compile_request = CurriculumCompileRequest(
                project_id=project.project_id,
                title="M19 Alien Worlds — WB04 Proof",
                source_format="experience_jsonl",
                source_text=template["source_text"],
                state_dim=16,
            )
            compiled = service.compile_curriculum(compile_request)
            frozen = service.freeze_curriculum(
                CurriculumFreezeRequest(
                    **compile_request.model_dump(),
                    expected_compiled_sha256=compiled["compiled_sha256"],
                )
            )
            run = service.create_run(
                project.project_id,
                OrganismConfig(seed=1901, state_dim=16, run_label="wb04-proof-m19"),
                organism_id="org_wb04_proof",
                run_id="run_wb04_proof",
            )
            queued = service.queue_curriculum(run["run_id"], frozen.curriculum_id)
            service.start_queue(run["run_id"])
            wait_idle(service, run["run_id"])
            status = service.status(run["run_id"])

            direct = VerdantKernel(seed=1901, state_dim=16, run_label="wb04-proof-m19")
            development = VerdantDevelopmentPipeline()
            for command in EthomorphismBenchmarkHarness().curriculum_commands():
                development.advance(direct, command)

            grammar_run = service.create_run(
                project.project_id,
                OrganismConfig(seed=4404, state_dim=32, run_label="wb04-proof-grammar"),
                organism_id="org_wb04_grammar_proof",
                run_id="run_wb04_grammar_proof",
            )
            grammar_id = grammar_run["run_id"]
            service.teach_grammar_rule(grammar_id, GrammarRuleTeachRequest(rule_id="transitive_svo"))
            service.teach_lexeme(grammar_id, LexemeTeachRequest(lemma="dog", category="noun", forms=("dog",)))
            service.teach_lexeme(grammar_id, LexemeTeachRequest(lemma="chase", category="verb", forms=("chase", "chases", "chased")))
            service.teach_lexeme(grammar_id, LexemeTeachRequest(lemma="child", category="noun", forms=("child",)))
            before = service.status(grammar_id)["descriptor"]
            preview = service.grammar_preview(grammar_id, GrammarPreviewRequest(sentence="dog chases child.", event_key="wb04-proof-preview"))
            after = service.status(grammar_id)["descriptor"]
            taught = service.teach_language_sentence(
                grammar_id,
                LanguageSentenceTeachRequest(sentence="dog chases child.", event_key="wb04-proof-sentence"),
            )
            grammar_status = service.grammar_status(grammar_id)

            checks = {
                "m19_template_count_30": template["item_count"] == 30,
                "m19_compiled_hash_matches_reference": compiled["compiled_sha256"] == template["compiled_sha256"],
                "frozen_hash_matches_reviewed_hash": frozen.compiled_sha256 == compiled["compiled_sha256"],
                "curriculum_queue_count_30": queued["item_count"] == 30,
                "curriculum_all_items_completed": status["execution"]["queue_counts"].get("completed") == 30,
                "workbench_matches_direct_fingerprint": status["descriptor"]["fingerprint"] == direct.fingerprint(),
                "m19_concepts_20": status["metrics"]["concept_count"] == 20,
                "m19_relations_15": status["metrics"]["relation_count"] == 15,
                "grammar_preview_parsed": bool(preview["analysis"]["parsed"]),
                "grammar_preview_pure_fingerprint": before["fingerprint"] == after["fingerprint"],
                "grammar_preview_pure_revision": before["state_revision"] == after["state_revision"],
                "grammar_sentence_committed": bool(taught["result"]["analysis"]["parsed"]),
                "grammar_rule_enabled": "transitive_svo" in grammar_status["enabled_rules"],
            }
            return {
                "schema": "verdant.workbench.wb04-proof.v1",
                "passed": all(checks.values()),
                "checks": checks,
                "curriculum": {
                    "reference_compiled_sha256": template["compiled_sha256"],
                    "compiled_sha256": compiled["compiled_sha256"],
                    "artifact_sha256": frozen.artifact_sha256,
                    "curriculum_id": frozen.curriculum_id,
                    "item_count": frozen.item_count,
                    "workbench_final_fingerprint": status["descriptor"]["fingerprint"],
                    "direct_final_fingerprint": direct.fingerprint(),
                    "concept_count": status["metrics"]["concept_count"],
                    "relation_count": status["metrics"]["relation_count"],
                },
                "grammar": {
                    "preview_analysis": preview["analysis"],
                    "preview_state_revision": preview["state_revision"],
                    "enabled_rules": grammar_status["enabled_rules"],
                    "lexicon_forms": grammar_status["lexicon"],
                },
            }
        finally:
            service.close()


if __name__ == "__main__":
    result = main()
    output_path = Path(__file__).resolve().parents[1] / "artifacts" / "wb04_curriculum_grammar_proof.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"\nproof_artifact={output_path}")
    if not result["passed"]:
        raise SystemExit(1)
