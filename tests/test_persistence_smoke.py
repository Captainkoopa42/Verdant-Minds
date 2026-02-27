import json

from usm import UnifiedSyntheticMind


def test_persistence_roundtrip(tmp_path):
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})

    mind.process_input("Hello")
    mind.process_input("What do you remember?")

    pre_size = len(mind.memory_web.memory_store)
    state_path = tmp_path / "state.json"
    mind.save_state(str(state_path))

    loaded = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    loaded.load_state(str(state_path))
    chunk = loaded.process_input("Continue")

    assert len(loaded.memory_web.memory_store) >= pre_size
    coherence = chunk.get_section_content("coherence_invariants_section")
    assert coherence is not None
    assert "violation_rate" in coherence

    with open(state_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert "memory_web" in saved
    assert "ecwf_core" in saved
    assert "entropy_history" in saved
