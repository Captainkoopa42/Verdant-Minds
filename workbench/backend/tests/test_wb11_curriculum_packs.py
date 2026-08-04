from __future__ import annotations

import json

from fastapi.testclient import TestClient

from verdant_workbench import DurableRunService
from verdant_workbench.app import app, runtime
from verdant_workbench.curriculum import CurriculumPackCompileRequest, CurriculumPackFreezeRequest


def make_pack(state_dim: int = 16) -> str:
    return json.dumps({
        "schema": "verdant.curriculum.pack.v1",
        "title": "WB11 Foundations",
        "description": "two-section pack",
        "state_dim": state_dim,
        "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": "pack"},
        "sections": [
            {
                "section_id": "physics",
                "title": "Physics",
                "enabled": True,
                "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": "physics"},
                "items": [
                    {
                        "item_id": "physics-001",
                        "context_id": "physics",
                        "source_text": "Gravity links mass and falling.",
                        "concepts": [{"label": "gravity"}, {"label": "mass"}, {"label": "falling"}],
                        "relations": [
                            {"source": "gravity", "relation": "linked", "target": "mass", "directed": True, "weight": 0.8, "confidence": 1.0},
                            {"source": "gravity", "relation": "linked", "target": "falling", "directed": True, "weight": 0.8, "confidence": 1.0},
                        ],
                        "claims": [],
                        "confidence": 1.0,
                        "provenance": {"author": "test"},
                        "grammar_annotation": {},
                        "lexicon_annotation": [],
                    }
                ],
                "tests": [{"test_id": "probe-physics", "cue_labels": ["gravity", "mass"], "notes": "post-run probe"}],
            },
            {
                "section_id": "ecology",
                "title": "Ecology",
                "enabled": True,
                "items": [
                    {
                        "item_id": "ecology-001",
                        "context_id": "ecology",
                        "source_text": "Sunlight supports plant energy.",
                        "concepts": [{"label": "sunlight"}, {"label": "plant"}, {"label": "energy"}],
                        "relations": [
                            {"source": "sunlight", "relation": "linked", "target": "energy", "directed": True, "weight": 0.9, "confidence": 1.0}
                        ],
                        "claims": [],
                        "confidence": 1.0,
                        "provenance": {"author": "test"},
                        "grammar_annotation": {},
                        "lexicon_annotation": [],
                    }
                ],
                "tests": [],
            },
        ],
        "notes": "WB11 test pack",
    })


def test_wb11_pack_compiles_selected_sections_through_teaching_bundle(tmp_path):
    service = DurableRunService(tmp_path / "pack")
    try:
        project = service.create_project("Pack Lab", project_id="proj_pack")
        result = service.compile_curriculum_pack(CurriculumPackCompileRequest(
            project_id=project.project_id,
            pack_text=make_pack(),
            selected_section_ids=("physics",),
        ))
        assert result["pack"]["schema"] == "verdant.curriculum.pack.v1"
        assert [x["section_id"] for x in result["selected_sections"]] == ["physics"]
        assert result["curriculum"]["source_format"] == "teaching_bundle_json"
        assert result["curriculum"]["item_count"] == 1
        assert result["tests"][0]["test_id"] == "probe-physics"
        bundle = json.loads(result["bundle_source_text"])
        assert bundle["schema"] == "verdant.teaching.bundle.v1"
        assert bundle["items"][0]["provenance"]["curriculum_pack"]["section_id"] == "physics"
        assert bundle["items"][0]["source_text"] == "Gravity links mass and falling."
    finally:
        service.close()


def test_wb11_pack_freeze_is_normal_vcurr_and_section_selection_changes_hash(tmp_path):
    service = DurableRunService(tmp_path / "freeze")
    try:
        project = service.create_project("Pack Freeze", project_id="proj_pack_freeze")
        physics = service.compile_curriculum_pack(CurriculumPackCompileRequest(
            project_id=project.project_id, pack_text=make_pack(), selected_section_ids=("physics",)
        ))
        both = service.compile_curriculum_pack(CurriculumPackCompileRequest(
            project_id=project.project_id, pack_text=make_pack(), selected_section_ids=("physics", "ecology")
        ))
        assert physics["curriculum"]["compiled_sha256"] != both["curriculum"]["compiled_sha256"]
        frozen = service.freeze_curriculum_pack(CurriculumPackFreezeRequest(
            project_id=project.project_id,
            pack_text=make_pack(),
            selected_section_ids=("physics", "ecology"),
            expected_compiled_sha256=both["curriculum"]["compiled_sha256"],
        ))
        detail = service.curriculum_detail(frozen.curriculum_id)
        assert detail["record"]["item_count"] == 2
        assert detail["record"]["source_format"] == "teaching_bundle_json"
        assert len(detail["compiled_commands"]) == 2
    finally:
        service.close()


def test_wb11_pack_api_and_browser_surface(tmp_path):
    runtime.reset(tmp_path / "api")
    client = TestClient(app)
    try:
        project = client.post("/api/v1/projects", json={"name": "Pack API"}).json()
        body = {"project_id": project["project_id"], "pack_text": make_pack(), "selected_section_ids": ["physics"]}
        compiled = client.post("/api/v1/curricula/packs/compile", json=body)
        assert compiled.status_code == 200
        assert compiled.json()["curriculum"]["item_count"] == 1
        frozen = client.post("/api/v1/curricula/packs/freeze", json={**body, "expected_compiled_sha256": compiled.json()["curriculum"]["compiled_sha256"]})
        assert frozen.status_code == 200
        js = client.get("/app.js")
        assert js.status_code == 200
        assert "verdant.curriculum.pack.v1" in js.text
        assert "Curriculum Packs" in js.text
        assert "Run selected + probes" in js.text
        assert "Observe Q candidates" in js.text
        assert "/hierarchy/observe" in js.text
        assert "data-action=\"observe-hierarchy\"" in js.text
        assert "structureSelectionRequest" in js.text
        assert "state.structureDetail=null" in js.text
        assert "Loading selected structure" in js.text
        assert "function editorHasFocus()" in js.text
        assert "function patchLiveDOM()" in js.text
        assert "function backgroundRender(force=false)" in js.text
        assert "background traffic only" in js.text
        background = js.text.split("function backgroundRender(force=false)", 1)[1].split("async function req", 1)[0]
        assert "render();" not in background
        assert 'data-live=\"queue\"' in js.text
        assert 'data-live=\"events\"' in js.text
    finally:
        runtime.close()
