import json

from usm import UnifiedSyntheticMind


def test_persistence_roundtrip(tmp_path):
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})

    mind.process_input("Hello")
    mind.process_input("What do you remember?")

    # Seed persisted components with explicit non-default values for roundtrip checks
    mind.blocks["ContinualLearning"].adaptive_memory["roundtrip_concept"] = {
        "stability": 0.77,
        "retrieval_count": 3,
    }
    mind.blocks["ContinualLearning"].reinforcement_cycles = 42

    mind.system_learning.t_glass = 0.61
    mind.system_learning.phase_state = "rigid"
    mind.system_learning.learning_rates["memory"] = 0.08

    mind.three_kings_layer.forefront_king.decision_threshold = 0.83
    mind.three_kings_layer.forefront_king.working_memory = {"focus": 0.9}
    mind.three_kings_layer.ethics_king.ethical_sensitivity = 0.72
    mind.three_kings_layer.data_king.oversight_metrics["total_oversights"] = 99

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

    # New persistence coverage checks
    assert loaded.blocks["ContinualLearning"].adaptive_memory.get("roundtrip_concept", {}).get("stability") == 0.77
    assert loaded.blocks["ContinualLearning"].reinforcement_cycles >= 42

    assert 0.0 < loaded.system_learning.t_glass <= 1.0
    assert isinstance(loaded.system_learning.phase_state, str)
    assert loaded.system_learning.learning_rates["memory"] > 0

    assert loaded.three_kings_layer.forefront_king.decision_threshold >= 0.4
    assert "focus" in loaded.three_kings_layer.forefront_king.working_memory or loaded.three_kings_layer.forefront_king.working_memory
    assert 0.0 < loaded.three_kings_layer.ethics_king.ethical_sensitivity <= 1.0
    assert loaded.three_kings_layer.data_king.oversight_metrics.get("total_oversights", 0) >= 99

    with open(state_path, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert "memory_web" in saved
    assert "ecwf_core" in saved
    assert "entropy_history" in saved
    assert "continual_learning" in saved
    assert "system_learning" in saved
    assert "kings" in saved
    assert "data_king" in saved["kings"]
    assert "forefront_king" in saved["kings"]
    assert "ethics_king" in saved["kings"]

    assert saved["continual_learning"].get("reinforcement_cycles") == 42
    assert saved["system_learning"].get("t_glass") == 0.61
    assert saved["system_learning"].get("phase_state") == "rigid"
    assert saved["system_learning"].get("learning_rates", {}).get("memory") == 0.08
    assert saved["kings"]["forefront_king"].get("decision_threshold") == 0.83
    assert saved["kings"]["ethics_king"].get("ethical_sensitivity") == 0.72


def test_memory_web_save_load_preserves_emergent_concepts_and_counts(tmp_path):
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})

    mind.memory_web.add_thought("alpha", stability=0.7, metadata={"domain": "test"})
    mind.memory_web.add_thought("beta", stability=0.6, metadata={"domain": "test"})
    mind.memory_web.connect_thoughts("alpha", "beta", initial_weight=0.8)

    emergent_label = "Emergent_alpha_beta_123"
    mind.memory_web.add_thought(
        emergent_label,
        stability=0.55,
        metadata={"origin": "wave_emergence", "creation_time": 1.0, "magnitude": 0.42},
    )
    mind.memory_web.connect_thoughts(emergent_label, "alpha", initial_weight=0.6)

    mind.memory_bridge.concept_dimension_mapping[emergent_label] = [
        ("cognitive", 0, 0.9),
        ("ethical", 1, 0.7),
    ]
    mind.memory_bridge.resonance_patterns["alpha_x_beta"] = {
        "concepts": ["alpha", "beta"],
        "created_at": 1.0,
        "magnitude": 0.5,
    }

    before_count = len(mind.memory_web.memory_store)
    before_emergent = sorted(
        label
        for label, payload in mind.memory_web.memory_store.items()
        if (payload.get("metadata") or {}).get("origin") == "wave_emergence"
    )

    state_path = tmp_path / "memoryweb_roundtrip.json"
    mind.save_state(str(state_path))

    loaded = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    loaded.load_state(str(state_path))

    after_count = len(loaded.memory_web.memory_store)
    after_emergent = sorted(
        label
        for label, payload in loaded.memory_web.memory_store.items()
        if (payload.get("metadata") or {}).get("origin") == "wave_emergence"
    )

    assert after_count == before_count
    assert after_emergent == before_emergent
    assert "alpha_x_beta" in loaded.memory_bridge.resonance_patterns
    assert emergent_label in loaded.memory_bridge.concept_dimension_mapping
