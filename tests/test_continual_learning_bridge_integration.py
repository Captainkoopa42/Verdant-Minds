from unittest.mock import MagicMock

from usm import UnifiedSyntheticMind


def test_process_input_wires_memory_bridge_into_continual_learning_section():
    mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})

    bridge = mind.memory_bridge
    bridge.bidirectional_update = MagicMock(return_value={"ok": True})
    bridge.get_resonance_info = MagicMock(
        return_value={
            "top_patterns": [("memory_ethics_sync", 3)],
            "pattern_count": 1,
            "strongest_pattern": ("memory_ethics_sync", 3),
        }
    )
    bridge.detect_and_create_emergent_concepts = MagicMock(return_value=[])

    chunk = mind.process_input("Please summarize and reason about fairness tradeoffs.")

    continual_learning = chunk.get_section_content("continual_learning_section")
    assert isinstance(continual_learning, dict)
    assert "resonance_patterns" in continual_learning
    assert "emergent_concepts_created" in continual_learning
    assert isinstance(continual_learning["emergent_concepts_created"], int)

    resonance = continual_learning["resonance_patterns"]
    assert isinstance(resonance, dict)
    assert resonance.get("pattern_count") == 1

    bridge.bidirectional_update.assert_called_once()
