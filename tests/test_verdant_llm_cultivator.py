import json
import urllib.error
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

    def load_state(self, path):
        return None


def test_cultivation_context_included_in_llm_payload(monkeypatch, tmp_path):
    captured = {}

    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "anthropic")
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
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--model", "test-model", "--fresh"])

    cultivator.main()

    payload = json.loads(captured["telemetry_payload"])
    assert "cultivation_context" in payload
    context = payload["cultivation_context"]
    assert context["cycle_number"] == 1
    assert context["memoryweb_size"] >= 1


def test_rate_limited_provider_falls_back_without_crashing(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "anthropic,local_fallback")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.2, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    def raise_429(**kwargs):
        raise urllib.error.HTTPError(url="https://api.anthropic.com/v1/messages", code=429, msg="rate", hdrs=None, fp=None)

    monkeypatch.setattr(cultivator, "_anthropic_next_input", raise_429)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    cycle_logs = sorted((tmp_path / "outputs").glob("cultivation_cycles_*.jsonl"))
    assert cycle_logs
    record = json.loads(cycle_logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["provider_used"] == "local_fallback"
    assert record["next_input"]


def test_perturbation_interval_and_bank_selection():
    bank, reason, flip = cultivator._select_perturbation_bank(
        last_cycle_emergent=0,
        fce_history=[0.5, 0.49, 0.48, 0.47, 0.46, 0.45],
        phase="Flexible",
        flexible_streak=10,
        cycle_number=10,
        last_perturbation_cycle=0,
        phase_changed_since_last_perturbation=False,
        perturbation_interval=15,
        rigid_next_for_flexible=True,
    )
    assert bank == "chaotic"
    assert reason == "fce_declining_5_cycles"
    assert flip is True

    bank, reason, flip = cultivator._select_perturbation_bank(
        last_cycle_emergent=0,
        fce_history=[0.5, 0.5, 0.5],
        phase="Flexible",
        flexible_streak=15,
        cycle_number=15,
        last_perturbation_cycle=0,
        phase_changed_since_last_perturbation=False,
        perturbation_interval=15,
        rigid_next_for_flexible=True,
    )
    assert bank == "rigid"
    assert reason == "flexible_streak_interval"
    assert flip is False
