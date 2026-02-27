#!/usr/bin/env python3

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.core.system import UnifiedSystem
from src.core.cognitive_chunk import CognitiveChunk


def test_update_glass_transition_temp_uses_semantic_entropy_bounds():
    system = UnifiedSystem(config={"initialize_knowledge": False})
    chunk = CognitiveChunk()

    chunk.update_section("sensory_input_section", {"tokens": ["a", "b"], "ambiguity_score": 0.1})
    chunk.update_section("memory_section", {"retrieved_concepts": ["x"], "novelty_score": 0.2})
    chunk.update_section("ethical_consideration_section", {"mean_delta_e": 1.6})
    chunk.update_section("wave_function_section", {"entropy": 0.72})

    system._update_glass_transition_temp(chunk)

    tg = system.metrics.get("glass_transition_temp")
    assert tg is not None
    assert 0.1 <= tg <= 0.9
