from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.blocks.language_processing_block import LanguageProcessingBlock
from src.core.cognitive_chunk import CognitiveChunk


def test_wave_state_modulates_language_response_structure():
    block = LanguageProcessingBlock(memory_bridge=None)
    chunk = CognitiveChunk()

    chunk.update_section("action_selection_section", {
        "selected_action": "answer_query",
        "action_confidence": 0.85,
        "action_parameters": {}
    })
    chunk.update_section("reasoning_section", {
        "reasoning_plan": [
            {"type": "analysis", "description": "Observation", "content": ["Signal variance is high."]},
            {"type": "conclusion_formation", "description": "Conclusion", "content": ["A cautious synthesis is warranted."]}
        ]
    })
    chunk.update_section("memory_section", {
        "retrieved_concepts": ["policy", "risk", "tradeoff"],
        "activated_concepts": {"policy": 0.7}
    })
    chunk.update_section("ethics_king_section", {
        "evaluation": {
            "status": "acceptable",
            "principle_scores": {"Non-Maleficence": 0.9, "Justice": 0.7}
        }
    })
    chunk.update_section("sensory_input_section", {"input_text": "How should I proceed?"})
    chunk.update_section("wave_function_section", {
        "magnitude": 0.4,
        "phase": 2.8,
        "entropy": 0.82,
        "cognitive_dimensions": [0.1, 0.8, 0.2, 0.7, 0.3],
        "ethical_dimensions": [0.9, 0.1, 0.2, 0.3, 0.4]
    })

    out = block.process_chunk(chunk)
    lang = out.get_section_content("language_processing_section")

    assert isinstance(lang, dict)
    assert "wave_response_parameters" in lang
    assert lang.get("interference_signature") == "divergent"

    params = lang["wave_response_parameters"]
    assert params.get("dominant_cognitive_dims") == [1, 3]
    assert params.get("dominant_ethical_dims") == [0, 4]

    response = lang.get("generated_response", "")
    assert "Both X and Y can be true here" in response
    assert "potential harms" in response
