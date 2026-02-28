import json
from pathlib import Path

import scripts.verdant_llm_cultivator as cultivator


class _FakeMind:
    def __init__(self, config=None):
        self.config = config or {}
        self.memory_web = type("MemoryWeb", (), {"memory_store": {"identity": {}}})()

    def process_input(self, text):
        self.memory_web.memory_store[text] = {}
        return {"input": text}

    def save_state(self, path, include_ecwf_past_states=False):
        Path(path).write_text("{}", encoding="utf-8")



def test_cultivation_context_included_in_llm_payload(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.1, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    def fake_next_input(**kwargs):
        captured["telemetry_payload"] = kwargs["telemetry_payload"]
        return "What does memory retain when identity shifts?"

    monkeypatch.setattr(cultivator, "_anthropic_next_input", fake_next_input)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--model", "test-model"])

    cultivator.main()

    payload = json.loads(captured["telemetry_payload"])
    assert "cultivation_context" in payload

    context = payload["cultivation_context"]
    assert context["cycle_number"] == 1
    assert context["memoryweb_size"] >= 1
    assert isinstance(context["fce_last_5"], list)
    assert isinstance(context["fce_growing"], bool)
    assert isinstance(context["cycles_without_growth"], int)
    assert isinstance(context["forbidden_recent_domains"], list)
