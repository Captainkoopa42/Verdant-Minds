from __future__ import annotations

import time

from fastapi.testclient import TestClient

from verdant_benchmarks.ethomorphism import EthomorphismBenchmarkHarness
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import VerdantKernel
from verdant_workbench import DurableRunService, OrganismConfig
from verdant_workbench.app import app, runtime
from verdant_workbench.curriculum import CurriculumCompileRequest, CurriculumFreezeRequest
from verdant_workbench.models import (
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LanguageSentenceTeachRequest,
    LexemeTeachRequest,
)


def wait_idle(service: DurableRunService, run_id: str, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = service.execution_status(run_id)
        if status["state"] in {"idle", "paused", "stopped"} and status["queue_counts"].get("queued", 0) == 0:
            return status
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for curriculum queue")


def test_wb04_m19_template_compiles_freezes_and_matches_reference_hash(tmp_path):
    service = DurableRunService(tmp_path / "wb04-curriculum")
    try:
        project = service.create_project("WB04 Lab", project_id="proj_wb04")
        template = service.m19_curriculum_template()
        harness = EthomorphismBenchmarkHarness()
        assert template["item_count"] == 30
        assert template["compiled_sha256"] == harness.curriculum_sha256()

        request = CurriculumCompileRequest(
            project_id=project.project_id,
            title=template["title"],
            source_format="experience_jsonl",
            source_text=template["source_text"],
            state_dim=template["state_dim"],
        )
        compiled = service.compile_curriculum(request)
        assert compiled["item_count"] == 30
        assert compiled["compiled_sha256"] == harness.curriculum_sha256()
        assert compiled["parsed_items"][0]["event_key"].startswith("m19:world-a")

        frozen = service.freeze_curriculum(
            CurriculumFreezeRequest(**request.model_dump(), expected_compiled_sha256=compiled["compiled_sha256"])
        )
        detail = service.curriculum_detail(frozen.curriculum_id)
        assert detail["manifest"]["compiled_sha256"] == harness.curriculum_sha256()
        assert len(detail["compiled_commands"]) == 30
        assert detail["record"]["version"] == 1

        # Freezing identical bytes creates a new immutable catalog version but deduplicates the artifact.
        frozen_2 = service.freeze_curriculum(
            CurriculumFreezeRequest(**request.model_dump(), expected_compiled_sha256=compiled["compiled_sha256"])
        )
        assert frozen_2.version == 2
        assert frozen_2.artifact_sha256 == frozen.artifact_sha256
    finally:
        service.close()


def test_wb04_m19_curriculum_workbench_run_matches_direct_engine(tmp_path):
    service = DurableRunService(tmp_path / "wb04-run")
    try:
        project = service.create_project("M19 Curriculum Run", project_id="proj_m19_curr")
        template = service.m19_curriculum_template()
        request = CurriculumFreezeRequest(
            project_id=project.project_id,
            title="M19 Through Workbench",
            source_format="experience_jsonl",
            source_text=template["source_text"],
            state_dim=16,
            expected_compiled_sha256=template["compiled_sha256"],
        )
        frozen = service.freeze_curriculum(request)
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=1901, state_dim=16, run_label="wb04-m19-equivalence"),
            organism_id="org_wb04_m19",
            run_id="run_wb04_m19",
        )
        queued = service.queue_curriculum(descriptor["run_id"], frozen.curriculum_id)
        assert queued["item_count"] == 30
        service.start_queue(descriptor["run_id"])
        wait_idle(service, descriptor["run_id"])
        wb_status = service.status(descriptor["run_id"])
        assert wb_status["execution"]["queue_counts"]["completed"] == 30
        assert wb_status["metrics"]["concept_count"] == 20
        assert wb_status["metrics"]["relation_count"] == 15

        direct = VerdantKernel(seed=1901, state_dim=16, run_label="wb04-m19-equivalence")
        pipeline = VerdantDevelopmentPipeline()
        for command in EthomorphismBenchmarkHarness().curriculum_commands():
            pipeline.advance(direct, command)
        assert wb_status["descriptor"]["fingerprint"] == direct.fingerprint()
        assert wb_status["descriptor"]["cycle"] == direct.state.cycle
    finally:
        service.close()


def test_wb04_primitive_line_compiler_and_diff(tmp_path):
    service = DurableRunService(tmp_path / "wb04-primitive")
    try:
        project = service.create_project("Primitive Studio", project_id="proj_primitive")
        source = """# explicit primitive curriculum\nPRESENCE basin-a kren tar vel\nEDGE basin-a kren linked tar | weight=0.7 | directed=false\nEDGE basin-a tar linked vel | weight=0.8 | directed=false\n"""
        request = CurriculumCompileRequest(
            project_id=project.project_id,
            title="Primitive Triad",
            source_format="primitive_lines",
            source_text=source,
            state_dim=8,
        )
        compiled = service.compile_curriculum(request)
        assert compiled["item_count"] == 3
        assert compiled["parsed_items"][1]["kind"] == "edge"
        frozen = service.freeze_curriculum(
            CurriculumFreezeRequest(**request.model_dump(), expected_compiled_sha256=compiled["compiled_sha256"])
        )
        changed = CurriculumCompileRequest(
            project_id=project.project_id,
            title="Primitive Triad",
            source_format="primitive_lines",
            source_text=source.replace("weight=0.8", "weight=0.6"),
            state_dim=8,
            baseline_curriculum_id=frozen.curriculum_id,
        )
        diffed = service.compile_curriculum(changed)
        assert diffed["compiled_sha256"] != compiled["compiled_sha256"]
        assert "baseline/compiled_commands.jsonl" in diffed["diff_from_baseline"]
    finally:
        service.close()


def test_wb04_grammar_lab_preview_is_pure_and_teaching_uses_engine_language_path(tmp_path):
    service = DurableRunService(tmp_path / "wb04-grammar")
    try:
        project = service.create_project("Grammar Lab", project_id="proj_grammar")
        descriptor = service.create_run(
            project.project_id,
            OrganismConfig(seed=4040, state_dim=32, run_label="grammar-lab"),
            organism_id="org_grammar",
            run_id="run_grammar",
        )
        run_id = descriptor["run_id"]
        initial = service.grammar_status(run_id)
        assert initial["enabled_rules"] == []

        service.teach_grammar_rule(run_id, GrammarRuleTeachRequest(rule_id="transitive_svo"))
        service.teach_lexeme(run_id, LexemeTeachRequest(lemma="dog", category="noun", forms=("dog",)))
        service.teach_lexeme(run_id, LexemeTeachRequest(lemma="chase", category="verb", forms=("chase", "chases", "chased")))
        service.teach_lexeme(run_id, LexemeTeachRequest(lemma="child", category="noun", forms=("child",)))

        before = service.status(run_id)["descriptor"]
        preview = service.grammar_preview(
            run_id,
            GrammarPreviewRequest(sentence="dog chases child.", event_key="preview-001"),
        )
        after = service.status(run_id)["descriptor"]
        assert preview["analysis"]["parsed"] is True
        assert preview["analysis"]["frame"]["subject"] == "dog"
        assert preview["analysis"]["frame"]["predicate"] == "chase"
        assert preview["analysis"]["frame"]["object"] == "child"
        assert before["fingerprint"] == after["fingerprint"]
        assert before["state_revision"] == after["state_revision"]

        receipt = service.teach_language_sentence(
            run_id,
            LanguageSentenceTeachRequest(sentence="dog chases child.", event_key="grammar-sentence-001"),
        )
        assert receipt["result"]["analysis"]["parsed"] is True
        status = service.grammar_status(run_id)
        assert "transitive_svo" in status["enabled_rules"]
        assert any(item["form"] == "chases" and item["lemma"] == "chase" for item in status["lexicon"])
        metrics = service.status(run_id)["metrics"]
        assert metrics["claim_count"] >= 1
    finally:
        service.close()


def test_wb04_api_curriculum_and_grammar_routes(tmp_path):
    runtime.reset(tmp_path / "api-wb04")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "WB04 API"}).json()
        template = client.get("/api/v1/curricula/templates/m19-alien")
        assert template.status_code == 200
        template_body = template.json()
        compiled = client.post(
            "/api/v1/curricula/compile",
            json={
                "project_id": project["project_id"],
                "title": "API M19",
                "source_format": "experience_jsonl",
                "source_text": template_body["source_text"],
                "state_dim": 16,
            },
        )
        assert compiled.status_code == 200
        frozen = client.post(
            "/api/v1/curricula/freeze",
            json={
                "project_id": project["project_id"],
                "title": "API M19",
                "source_format": "experience_jsonl",
                "source_text": template_body["source_text"],
                "state_dim": 16,
                "expected_compiled_sha256": compiled.json()["compiled_sha256"],
            },
        )
        assert frozen.status_code == 200
        curriculum_id = frozen.json()["curriculum_id"]
        assert client.get(f"/api/v1/curricula/{curriculum_id}").status_code == 200

        run = client.post(
            f"/api/v1/projects/{project['project_id']}/runs",
            json={"seed": 55, "state_dim": 16, "run_label": "wb04-api"},
        ).json()
        queued = client.post(f"/api/v1/runs/{run['run_id']}/curricula/{curriculum_id}/queue")
        assert queued.status_code == 200
        assert queued.json()["item_count"] == 30

        grammar = client.get(f"/api/v1/runs/{run['run_id']}/grammar")
        assert grammar.status_code == 200
        assert len(grammar.json()["rules"]) >= 3
    finally:
        runtime.close()


def test_wb04_serves_curriculum_and_grammar_workbench_surfaces(tmp_path):
    runtime.reset(tmp_path / "ui-wb04")
    client = TestClient(app)
    try:
        assert client.get("/").status_code == 200
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "CURRICULUM STUDIO" in js.text
        assert "LANGUAGE / GRAMMAR LAB" in js.text
        assert "WORKBENCH · WB-05" in js.text
    finally:
        runtime.close()


def test_wb041_editable_teaching_record_is_explicit_not_prose_inferred(tmp_path):
    import json

    service = DurableRunService(tmp_path / "wb041-explicit")
    try:
        project = service.create_project("Editable Teaching", project_id="proj_editable")
        bundle = {
            "schema": "verdant.teaching.bundle.v1",
            "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": ""},
            "items": [
                {
                    "item_id": "lie-001",
                    "context_id": "deliberate-mismatch",
                    "source_text": "The tar eats the moon.",
                    "concepts": [
                        {"label": "kren", "attributes": {"kind": "entity"}},
                        {"label": "tar", "attributes": {"kind": "entity"}},
                    ],
                    "relations": [
                        {"source": "kren", "relation": "moves_toward", "target": "tar", "directed": True, "weight": 0.8, "confidence": 1.0}
                    ],
                    "claims": [],
                    "confidence": 1.0,
                    "provenance": {"author": "human", "purpose": "prove source text is not parsed"},
                    "grammar_annotation": {"note": "intentionally unrelated source sentence"},
                    "lexicon_annotation": [{"surface": "tar", "role": "noun"}],
                }
            ],
        }
        compiled = service.compile_curriculum(CurriculumCompileRequest(
            project_id=project.project_id,
            title="Explicit Record",
            source_format="teaching_bundle_json",
            source_text=json.dumps(bundle),
            state_dim=16,
        ))
        assert compiled["item_count"] == 1
        assert compiled["scaffold_item_count"] == 0
        command = compiled["compiled_commands"][0]
        assert command["relation_proposals"][0]["relation_type"] == "moves_toward"
        assert {item["label"] for item in command["concept_proposals"]} == {"kren", "tar"}
        assert "moon" not in {item["label"] for item in command["concept_proposals"]}
        assert command["semantic_evidence_details"]["source_text"] == "The tar eats the moon."
    finally:
        service.close()


def test_wb041_bundle_can_queue_language_scaffold_and_world_teaching(tmp_path):
    import json

    service = DurableRunService(tmp_path / "wb041-scaffold")
    try:
        project = service.create_project("Scaffold Bundle", project_id="proj_scaffold")
        bundle = {
            "schema": "verdant.teaching.bundle.v1",
            "language_scaffold": {
                "grammar_rules": ["transitive_svo"],
                "lexicon": [
                    {"lemma": "dog", "category": "noun", "forms": ["dog"], "attributes": {}},
                    {"lemma": "chase", "category": "verb", "forms": ["chase", "chases", "chased"], "attributes": {}},
                    {"lemma": "child", "category": "noun", "forms": ["child"], "attributes": {}},
                ],
                "notes": "Explicit parser scaffold",
            },
            "items": [
                {
                    "item_id": "world-001",
                    "context_id": "world",
                    "source_text": "dog chases child.",
                    "concepts": [{"label": "dog", "attributes": {}}, {"label": "child", "attributes": {}}],
                    "relations": [{"source": "dog", "relation": "chases", "target": "child", "directed": True, "weight": 0.8, "confidence": 1.0}],
                    "claims": [],
                    "confidence": 1.0,
                    "provenance": {"author": "human"},
                    "grammar_annotation": {"subject": "dog", "predicate": "chase", "object": "child"},
                    "lexicon_annotation": [],
                }
            ],
        }
        source = json.dumps(bundle)
        compiled = service.compile_curriculum(CurriculumCompileRequest(
            project_id=project.project_id, title="Scaffold + World", source_format="teaching_bundle_json", source_text=source, state_dim=32,
        ))
        assert compiled["scaffold_item_count"] == 4
        frozen = service.freeze_curriculum(CurriculumFreezeRequest(
            project_id=project.project_id, title="Scaffold + World", source_format="teaching_bundle_json", source_text=source, state_dim=32,
            expected_compiled_sha256=compiled["compiled_sha256"],
        ))
        descriptor = service.create_run(project.project_id, OrganismConfig(seed=91, state_dim=32, run_label="bundle"), run_id="run_bundle", organism_id="org_bundle")
        queued = service.queue_curriculum(descriptor["run_id"], frozen.curriculum_id)
        assert queued["scaffold_item_count"] == 4
        assert queued["experience_item_count"] == 1
        assert queued["item_count"] == 5
        service.start_queue(descriptor["run_id"])
        wait_idle(service, descriptor["run_id"])
        grammar = service.grammar_status(descriptor["run_id"])
        assert "transitive_svo" in grammar["enabled_rules"]
        assert any(entry["form"] == "chases" and entry["lemma"] == "chase" for entry in grammar["lexicon"])
        metrics = service.status(descriptor["run_id"])["metrics"]
        assert metrics["relation_count"] >= 1
    finally:
        service.close()


def test_wb041_curriculum_allows_deliberately_contradictory_claims(tmp_path):
    import json

    service = DurableRunService(tmp_path / "wb041-contradiction")
    try:
        project = service.create_project("Contradiction Lab", project_id="proj_contradiction")
        def item(item_id, polarity):
            return {
                "item_id": item_id,
                "context_id": "misinformation-test",
                "source_text": "A kren is hot." if polarity == "affirmed" else "The same kren is not hot.",
                "concepts": [{"label": "kren", "attributes": {}}, {"label": "hot", "attributes": {}}],
                "relations": [],
                "claims": [{
                    "subject": "kren", "predicate": "has_property", "object": "hot", "polarity": polarity,
                    "source_class": "human_testimony", "confidence": 1.0, "rationale": "deliberate contradiction", "attributes": {}
                }],
                "confidence": 1.0,
                "provenance": {"author": "human", "experiment": "false-information"},
                "grammar_annotation": {}, "lexicon_annotation": [],
            }
        bundle = {"schema": "verdant.teaching.bundle.v1", "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": ""}, "items": [item("claim-a", "affirmed"), item("claim-b", "negated")], "notes": "Contradiction is intentional."}
        source = json.dumps(bundle)
        compiled = service.compile_curriculum(CurriculumCompileRequest(project_id=project.project_id, title="Contradictory Claims", source_format="teaching_bundle_json", source_text=source, state_dim=16))
        assert len(compiled["compiled_commands"]) == 2
        frozen = service.freeze_curriculum(CurriculumFreezeRequest(project_id=project.project_id, title="Contradictory Claims", source_format="teaching_bundle_json", source_text=source, state_dim=16, expected_compiled_sha256=compiled["compiled_sha256"]))
        run = service.create_run(project.project_id, OrganismConfig(seed=92, state_dim=16, run_label="contradiction"), run_id="run_contradiction", organism_id="org_contradiction")
        service.queue_curriculum(run["run_id"], frozen.curriculum_id)
        service.start_queue(run["run_id"])
        wait_idle(service, run["run_id"])
        metrics = service.status(run["run_id"])["metrics"]
        assert metrics["claim_count"] >= 2
        assert metrics["contradiction_count"] >= 1
    finally:
        service.close()


def test_wb041_editable_template_api_and_ui(tmp_path):
    runtime.reset(tmp_path / "api-wb041")
    client = TestClient(app)
    try:
        template = client.get("/api/v1/curricula/templates/editable-teaching-record")
        assert template.status_code == 200
        body = template.json()
        assert body["source_format"] == "teaching_bundle_json"
        assert "verdant.teaching.bundle.v1" in body["source_text"]
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "Editable Teaching Record Builder" in js.text
        assert "False, fictional" in js.text
        assert "teaching_bundle_json" in js.text
    finally:
        runtime.close()
