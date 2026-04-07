"""Unit tests for verdant.governance."""

from __future__ import annotations

import pytest
from verdant.governance.data_king import DataKing
from verdant.governance.ethics_king import EthicsKing
from verdant.governance.forefront_king import ForefrontKing
from verdant.governance.council import ThreeKingsCouncil
from verdant.pipeline.chunk import CognitiveChunk


def _make_chunk(**sections) -> CognitiveChunk:
    chunk = CognitiveChunk()
    for name, content in sections.items():
        chunk.update_section(name, content)
    return chunk


class TestDataKing:
    """DataKing modifies chunk with quality info."""

    def test_adds_data_king_section(self) -> None:
        chunk = _make_chunk(
            sensory_input_section={"input_text": "test input", "token_count": 5},
            pattern_recognition_section={"concepts": ["a", "b"], "concept_count": 2, "question_confidence": 0.5},
            memory_section={"activated_concepts": {"a": 0.5}},
        )
        dk = DataKing()
        result = dk.oversee(chunk)
        sec = result.get_section_content("data_king_section")
        assert sec is not None
        assert "quality_score" in sec
        assert "novelty_score" in sec

    def test_processing_step_recorded(self) -> None:
        chunk = _make_chunk(
            sensory_input_section={"input_text": "x", "token_count": 1},
            pattern_recognition_section={"concepts": [], "concept_count": 0},
            memory_section={},
        )
        dk = DataKing()
        result = dk.oversee(chunk)
        steps = result.get_processing_history("DataKing")
        assert len(steps) == 1


class TestEthicsKing:
    """EthicsKing applies ethical oversight."""

    def test_adds_ethics_king_section(self) -> None:
        chunk = _make_chunk(
            ethical_consideration_section={
                "overall_score": 0.8,
                "principle_scores": {"Non-Maleficence": 0.9, "Beneficence": 0.8},
                "concerns": [],
            },
            coherence_invariants_section={
                "triangle_valid_at_alpha1": True,
                "violation_rate": 0.0,
                "housed_contradiction_index": 0.0,
            },
            language_processing_section={"generated_response": "test"},
        )
        ek = EthicsKing()
        result = ek.oversee(chunk)
        sec = result.get_section_content("ethics_king_section")
        assert sec is not None
        assert "evaluation" in sec
        assert sec["evaluation"]["status"] in ("excellent", "good", "acceptable", "review_needed")

    def test_coherence_strain_modulates_score(self) -> None:
        chunk = _make_chunk(
            ethical_consideration_section={
                "overall_score": 0.7,
                "principle_scores": {},
                "concerns": [],
            },
            coherence_invariants_section={
                "triangle_valid_at_alpha1": False,
                "violation_rate": 0.5,
                "housed_contradiction_index": 0.8,
            },
            language_processing_section={"generated_response": "test"},
        )
        ek = EthicsKing()
        result = ek.oversee(chunk)
        evaluation = result.get_section_content("ethics_king_section")["evaluation"]
        # With HCI > 0.6, score gets -0.1 penalty
        assert evaluation["overall_score"] < 1.0
        # Triangle invalid → coherence_tension concern added
        assert any(c["type"] == "coherence_tension" for c in evaluation["concerns"])


class TestForefrontKing:
    """ForefrontKing manages cognitive load and decision threshold."""

    def test_adds_forefront_section(self) -> None:
        chunk = _make_chunk(
            internal_communication_section={"integrated_context": {"primary_concepts": ["a"]}},
            reasoning_section={"confidence_score": 0.6, "inferences": {}},
            action_selection_section={"selected_action": "answer_query", "action_confidence": 0.7},
            pattern_recognition_section={"concepts": ["a"]},
            coherence_invariants_section={},
            processing_metrics_section={"glass_transition_temp": 0.5},
        )
        fk = ForefrontKing()
        result = fk.oversee(chunk)
        sec = result.get_section_content("forefront_king_section")
        assert sec is not None
        assert "cognitive_load" in sec
        assert "decision_threshold" in sec
        assert "phase_state" in sec

    def test_phase_dependent_threshold(self) -> None:
        # Rigid phase (low T_g) should have higher threshold
        chunk_rigid = _make_chunk(
            internal_communication_section={"integrated_context": {}},
            reasoning_section={"confidence_score": 0.5, "inferences": {}},
            action_selection_section={"selected_action": "answer_query", "action_confidence": 0.7},
            pattern_recognition_section={"concepts": []},
            coherence_invariants_section={},
            processing_metrics_section={"glass_transition_temp": 0.2},
        )
        chunk_chaotic = _make_chunk(
            internal_communication_section={"integrated_context": {}},
            reasoning_section={"confidence_score": 0.5, "inferences": {}},
            action_selection_section={"selected_action": "answer_query", "action_confidence": 0.7},
            pattern_recognition_section={"concepts": []},
            coherence_invariants_section={},
            processing_metrics_section={"glass_transition_temp": 0.8},
        )
        fk = ForefrontKing()
        fk.oversee(chunk_rigid)
        rigid_threshold = fk.decision_threshold

        fk2 = ForefrontKing()
        fk2.oversee(chunk_chaotic)
        chaotic_threshold = fk2.decision_threshold

        assert rigid_threshold > chaotic_threshold


class TestCouncil:
    """ThreeKingsCouncil coordinates and detects conflicts."""

    def test_detects_action_override_conflict(self) -> None:
        chunk = _make_chunk(
            action_selection_section={"selected_action": "defer_decision", "action_confidence": 0.5},
            data_king_section={"assessment_confidence": 0.5},
            forefront_king_section={"cognitive_load": 0.5},
            ethics_king_section={"evaluation": {"overall_score": 0.5, "status": "good", "concerns": []}},
        )
        dk = DataKing()
        fk = ForefrontKing()
        ek = EthicsKing()
        council = ThreeKingsCouncil(dk, fk, ek)

        # Simulate prior action being different
        conflicts = council._detect_conflicts(chunk, "answer_query")
        assert any(c["type"] == "action_override" for c in conflicts)

    def test_writes_council_section(self) -> None:
        chunk = _make_chunk(
            action_selection_section={"selected_action": "answer_query", "action_confidence": 0.7},
            data_king_section={"assessment_confidence": 0.7, "quality_score": 0.7},
            forefront_king_section={"cognitive_load": 0.4},
            ethics_king_section={"evaluation": {"overall_score": 0.8, "status": "good", "concerns": []}},
        )
        dk = DataKing()
        fk = ForefrontKing()
        ek = EthicsKing()
        council = ThreeKingsCouncil(dk, fk, ek)
        result = council.oversee(chunk)
        sec = result.get_section_content("three_kings_layer_section")
        assert sec is not None
        assert "conflicts" in sec
        assert "criticality" in sec

    def test_king_state_serialisation(self) -> None:
        dk = DataKing()
        state = dk.to_state_dict()
        dk2 = DataKing()
        dk2.from_state_dict(state)
        assert dk2.quality_threshold == dk.quality_threshold
