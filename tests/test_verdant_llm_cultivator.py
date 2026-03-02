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


def test_groq_error_falls_back_without_crashing(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "groq,local_fallback")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.2, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    def raise_groq_error(*args, **kwargs):
        raise RuntimeError("Groq API error: synthetic test failure")

    monkeypatch.setattr(cultivator, "groq_next_input", raise_groq_error)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    cycle_logs = sorted((tmp_path / "outputs").glob("cultivation_cycles_*.jsonl"))
    assert cycle_logs
    record = json.loads(cycle_logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["provider_used"] == "local_fallback"
    assert record["provider_error"] and "groq:" in record["provider_error"]
    assert record["next_input"]



def test_groq_rate_limit_wait_and_retry_once(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "groq,local_fallback")
    monkeypatch.setenv("VERDANT_MAX_RATE_LIMIT_SLEEP", "180")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.2, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    calls = {"count": 0}

    def fake_groq_next_input(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise cultivator.GroqRateLimitError("Groq API rate limited (429): retry after 2.5 seconds")
        return "Recovered after waiting"

    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(cultivator, "groq_next_input", fake_groq_next_input)
    monkeypatch.setattr(cultivator.time, "sleep", fake_sleep)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    assert calls["count"] == 2
    assert slept and slept[0] == 2.5

    cycle_logs = sorted((tmp_path / "outputs").glob("cultivation_cycles_*.jsonl"))
    assert cycle_logs
    record = json.loads(cycle_logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["provider_used"] == "groq"
    assert record["provider_error"] is None
    assert record["next_input"] == "Recovered after waiting"



def test_mistral_provider_returns_text(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "mistral,local_fallback")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.1, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "Probe identity from a memory paradox."}}]
            }).encode("utf-8")

    def fake_urlopen(req, timeout=60):
        assert req.full_url == "https://api.mistral.ai/v1/chat/completions"
        return _FakeResponse()

    monkeypatch.setattr(cultivator.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    cycle_logs = sorted((tmp_path / "outputs").glob("cultivation_cycles_*.jsonl"))
    assert cycle_logs
    record = json.loads(cycle_logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1])
    assert record["provider_used"] == "mistral"
    assert record["next_input"] == "Probe identity from a memory paradox."


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


def test_budget_mode_trims_prompt_and_uses_env_groq_call_args(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "groq")
    monkeypatch.setenv("VERDANT_BUDGET_MODE", "1")
    monkeypatch.setenv("VERDANT_MAX_PROMPT_CHARS", "200")
    monkeypatch.setenv("GROQ_MAX_TOKENS", "42")
    monkeypatch.setenv("GROQ_TEMPERATURE", "0.13")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.55, "details": "x" * 800},
            "coherence_invariants": {"housed_contradiction_index": 0.2, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0, "blob": "y" * 800},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    captured = {}

    def fake_groq_next_input(prompt, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return "Budget-safe prompt"

    monkeypatch.setattr(cultivator, "groq_next_input", fake_groq_next_input)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    stdout = capsys.readouterr().out
    cycle_logs = sorted((tmp_path / "outputs").glob("cultivation_cycles_*.jsonl"))
    assert cycle_logs
    record = json.loads(cycle_logs[-1].read_text(encoding="utf-8").strip().splitlines()[-1])

    assert captured["kwargs"]["max_tokens"] == 42
    assert captured["kwargs"]["temperature"] == 0.13
    assert len(captured["prompt"]) <= 200
    assert "seed_topic=" in captured["prompt"]
    assert "phase=" in captured["prompt"]
    assert "FCE=" in captured["prompt"]
    assert "Return only the next input prompt (one sentence)." in captured["prompt"]
    assert "event=prompt_trim" in stdout or (record.get("prompt_chars") is not None and record["prompt_chars"] <= 200)
    assert record["groq_max_tokens"] == 42
    assert record["groq_temperature"] == 0.13
    assert record["prompt_chars"] <= 200


def test_cycle_sleep_flag_calls_sleep(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "local_fallback")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.1, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(cultivator.time, "sleep", fake_sleep)
    monkeypatch.setattr(
        "sys.argv",
        ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation", "--cycle-sleep", "0.25"],
    )

    cultivator.main()

    assert slept == [0.25]


def test_cycle_sleep_env_default_calls_sleep(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "local_fallback")
    monkeypatch.setenv("VERDANT_CYCLE_SLEEP", "0.4")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Flexible", "T_cog": 0.5},
            "coherence_invariants": {"housed_contradiction_index": 0.1, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 0},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    slept = []

    def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(cultivator.time, "sleep", fake_sleep)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    assert slept == [0.4]


def test_mistral_tutor_contract_includes_curriculum_targets(monkeypatch, tmp_path):
    monkeypatch.setattr(cultivator, "project_root", tmp_path)
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setenv("VERDANT_PROVIDER_CHAIN", "mistral")
    monkeypatch.setenv("VERDANT_HCI_TARGET_LOW", "0.40")
    monkeypatch.setenv("VERDANT_HCI_TARGET_HIGH", "0.49")
    monkeypatch.setattr(cultivator, "UnifiedSyntheticMind", _FakeMind)

    def fake_build_telemetry(mind, chunk):
        return {
            "thermodynamic_state": {"phase": "Chaotic", "T_cog": 0.61},
            "coherence_invariants": {"housed_contradiction_index": 0.47, "triangle_valid_at_alpha1": True},
            "memory_topology": {"emergent_concepts_created": 1},
        }

    monkeypatch.setattr(cultivator, "build_telemetry", fake_build_telemetry)

    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"choices": [{"message": {"content": "Create a paradox from identity and ethics that resists resolution."}}]}).encode("utf-8")

    def fake_urlopen(req, timeout=60):
        body = json.loads(req.data.decode("utf-8"))
        captured["system_prompt"] = body["messages"][0]["content"]
        return _FakeResponse()

    monkeypatch.setattr(cultivator.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("sys.argv", ["verdant_llm_cultivator.py", "--cycles", "1", "--fresh", "--no-perturbation"])

    cultivator.main()

    prompt = captured["system_prompt"]
    assert "phase=Chaotic" in prompt
    assert "FCE=0.610" in prompt
    assert "HCI=0.470" in prompt
    assert "hci_target_low=0.40" in prompt
    assert "hci_target_high=0.49" in prompt
    assert "Return ONLY the next prompt as a single sentence" in prompt


def test_mistral_tutor_contract_mode_specific_050_constraints():
    key_metrics = {
        "phase": "Flexible",
        "FCE": 0.52,
        "housed_contradiction_index": 0.46,
    }

    approach_contract = cultivator._build_mistral_tutor_contract(
        key_metrics=key_metrics,
        hci_trend="flat",
        curriculum={
            "mode": "approach",
            "hci_target_low": 0.40,
            "hci_target_high": 0.49,
            "cross_interval": 10,
            "repeat_penalty": True,
            "multi_domain": True,
        },
        last_prompt="Test last prompt",
        recent_prompts=["Prompt A", "Prompt B"],
        hci_below_target_streak=0,
        crossed_above_050_recently=False,
        max_pressure_active=False,
    )
    assert "do not exceed 0.50" in approach_contract.lower()

    cross_contract = cultivator._build_mistral_tutor_contract(
        key_metrics=key_metrics,
        hci_trend="up",
        curriculum={
            "mode": "cross",
            "hci_target_low": 0.40,
            "hci_target_high": 0.49,
            "cross_interval": 7,
            "repeat_penalty": True,
            "multi_domain": True,
        },
        last_prompt="Test last prompt",
        recent_prompts=["Prompt A", "Prompt B"],
        hci_below_target_streak=0,
        crossed_above_050_recently=False,
        max_pressure_active=False,
    )
    assert "do not exceed" not in cross_contract.lower()
    assert "above 0.50" in cross_contract


def test_mistral_tutor_contract_max_pressure_instructions_present_when_active():
    key_metrics = {
        "phase": "Flexible",
        "FCE": 0.48,
        "housed_contradiction_index": 0.45,
    }

    contract = cultivator._build_mistral_tutor_contract(
        key_metrics=key_metrics,
        hci_trend="flat",
        curriculum={
            "mode": "cross",
            "hci_target_low": 0.40,
            "hci_target_high": 0.49,
            "cross_interval": 10,
            "repeat_penalty": True,
            "multi_domain": True,
        },
        last_prompt="Prior contradiction prompt",
        recent_prompts=["Prompt 1", "Prompt 2"],
        hci_below_target_streak=0,
        crossed_above_050_recently=False,
        max_pressure_active=True,
    )

    assert "MAXIMUM PRESSURE MODE (ACTIVE)" in contract
    assert "THIRD conflicting principle" in contract
    assert '"X is true AND X is false because Y"' in contract
    assert "Your magnitude is low — intensify the conflict" in contract
    assert "Forbidden starts" in contract
