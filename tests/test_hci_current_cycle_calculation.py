#!/usr/bin/env python3
"""Tests for current-cycle housed contradiction index (HCI) calculation."""

import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

from src.core.system import UnifiedSystem
from src.core.CognitiveChunk import CognitiveChunk


def _make_system():
    config = {
        "cognitive_dimensions": 3,
        "ethical_dimensions": 3,
        "wave_facets": 5,
        "bridge_influence_factor": 0.3,
        "initialize_knowledge": False,
        "log_level": "WARNING",
    }
    with patch.dict("sys.modules", {"tensorflow": MagicMock(), "torch": MagicMock()}):
        return UnifiedSystem(seed=42, config=config)


def test_hci_positive_when_principle_scores_have_spread():
    system = _make_system()
    chunk = CognitiveChunk()
    chunk.update_section("wave_function_section", {"entropy": 0.4, "magnitude": 0.8, "phase": 0.2})
    chunk.update_section("memory_section", {"activated_concepts": {"a": 0.7}, "novelty_score": 0.0})
    chunk.update_section(
        "ethics_king_section",
        {
            "evaluation": {
                "overall_score": 0.5,
                "principle_scores": {"NonMaleficence": 0.2, "Justice": 0.9},
            }
        },
    )
    chunk.update_section("ethical_consideration_section", {"mean_delta_e": 0.0})

    coherence = system._compute_coherence_invariants(chunk)
    hci = coherence["housed_contradiction_index"]

    assert math.isfinite(hci)
    assert hci > 0.0


def test_hci_zero_when_no_activation_and_no_principle_spread():
    system = _make_system()
    chunk = CognitiveChunk()
    chunk.update_section("wave_function_section", {"entropy": 0.9, "magnitude": 0.9, "phase": 0.1})
    chunk.update_section("memory_section", {"activated_concepts": {}, "novelty_score": 0.0})
    chunk.update_section("ethics_king_section", {"evaluation": {"overall_score": 0.5, "principle_scores": {}}})
    chunk.update_section("ethical_consideration_section", {"mean_delta_e": 0.0})

    coherence = system._compute_coherence_invariants(chunk)
    assert coherence["housed_contradiction_index"] == 0.0
