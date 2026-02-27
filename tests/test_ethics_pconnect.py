#!/usr/bin/env python3

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.blocks.ethics_values_block import EthicsValuesBlock
from src.core.cognitive_chunk import CognitiveChunk


def test_ethics_pconnect_primary_score_fields_present():
    block = EthicsValuesBlock()
    chunk = CognitiveChunk()

    chunk.update_section("sensory_input_section", {"input_text": "Assess justice and autonomy tradeoffs"})
    chunk.update_section(
        "pattern_recognition_section",
        {
            "concepts": ["justice fairness", "autonomy consent", "transparency"],
            "sentiment_data": {"polarity": "neutral"},
        },
    )

    out = block.process_chunk(chunk)
    ethics = out.get_section_content("ethical_consideration_section")

    assert ethics is not None
    assert "overall_score" in ethics
    assert "heuristic_score" in ethics
    assert "mean_delta_e" in ethics
    assert "pair_count" in ethics

    assert 0.0 <= ethics["overall_score"] <= 1.0
    assert 0.0 <= ethics["mean_delta_e"] <= 2.0
    assert ethics["pair_count"] >= 1
