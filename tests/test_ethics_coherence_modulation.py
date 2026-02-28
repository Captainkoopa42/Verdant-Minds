from pathlib import Path
import sys

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.kings.ethics_king import EthicsKing
from src.core.cognitive_chunk import CognitiveChunk


def test_ethics_king_increases_caution_under_coherence_strain():
    king = EthicsKing()
    chunk = CognitiveChunk()

    chunk.update_section("ethical_consideration_section", {"concerns": []})
    chunk.update_section("language_processing_section", {"generated_response": "Initial response."})
    chunk.update_section("action_selection_section", {"selected_action": "answer_query"})
    chunk.update_section("coherence_invariants_section", {
        "housed_contradiction_index": 0.9,
        "triangle_valid_at_alpha1": False,
        "violation_rate": 0.5,
    })

    out = king.oversee_processing(chunk)
    ethics_section = out.get_section_content("ethics_king_section")
    evaluation = ethics_section.get("evaluation", {})
    coherence_influence = ethics_section.get("coherence_influence", {})

    assert evaluation.get("overall_score", 1.0) < 0.8
    assert "coherence_tension" in evaluation.get("concerns", [])
    assert coherence_influence.get("contradiction_index") == 0.9
    assert coherence_influence.get("triangle_valid") is False
    assert coherence_influence.get("score_adjustment") == -0.1
    assert "coherence_tension" in coherence_influence.get("concerns_added", [])
