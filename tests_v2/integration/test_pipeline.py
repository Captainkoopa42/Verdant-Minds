"""Integration tests for the full pipeline."""

from __future__ import annotations

import pytest
from verdant_v2.system import VerdantConfig, VerdantSystem


@pytest.fixture
def system() -> VerdantSystem:
    return VerdantSystem(VerdantConfig(seed=42))


class TestProcessInput:
    """Verify process_input runs through all 9 blocks."""

    def test_returns_chunk(self, system: VerdantSystem) -> None:
        chunk = system.process_input("What is the nature of consciousness?")
        assert chunk is not None
        assert chunk.chunk_id

    def test_all_nine_block_sections_populated(self, system: VerdantSystem) -> None:
        chunk = system.process_input("How do ethics and identity relate?")
        expected_sections = [
            "sensory_input_section",
            "pattern_recognition_section",
            "memory_section",
            "wave_function_section",
            "internal_communication_section",
            "reasoning_section",
            "ethical_consideration_section",
            "action_selection_section",
            "language_processing_section",
            "continual_learning_section",
        ]
        for sec_name in expected_sections:
            content = chunk.get_section_content(sec_name)
            assert content is not None, f"Section '{sec_name}' missing"
            assert len(content) > 0, f"Section '{sec_name}' empty"

    def test_processing_log_shows_all_blocks(self, system: VerdantSystem) -> None:
        chunk = system.process_input("Testing the pipeline")
        log = chunk.get_processing_history()
        processors = [step.processor for step in log]
        # All 9 blocks should be represented
        expected_blocks = [
            "SensoryInput",
            "PatternRecognition",
            "MemoryStorage",
            "InternalCommunication",
            "ReasoningPlanning",
            "EthicsValues",
            "ActionSelection",
            "LanguageProcessing",
            "ContinualLearning",
        ]
        for block in expected_blocks:
            assert block in processors, f"Block '{block}' missing from processing log"

    def test_processing_log_order(self, system: VerdantSystem) -> None:
        chunk = system.process_input("Test ordering")
        log = chunk.get_processing_history()
        # Extract first occurrence of each block
        block_order = []
        seen = set()
        for step in log:
            if step.processor not in seen and step.processor in {
                "SensoryInput", "PatternRecognition", "MemoryStorage",
                "InternalCommunication", "ReasoningPlanning", "EthicsValues",
                "ActionSelection", "LanguageProcessing", "ContinualLearning",
            }:
                block_order.append(step.processor)
                seen.add(step.processor)
        expected_order = [
            "SensoryInput", "PatternRecognition", "MemoryStorage",
            "InternalCommunication", "ReasoningPlanning", "EthicsValues",
            "ActionSelection", "LanguageProcessing", "ContinualLearning",
        ]
        assert block_order == expected_order

    def test_coherence_invariants_computed(self, system: VerdantSystem) -> None:
        chunk = system.process_input("Test coherence")
        coherence = chunk.get_section_content("coherence_invariants_section")
        assert coherence is not None
        assert "triangle_valid_at_alpha1" in coherence
        assert "housed_contradiction_index" in coherence
        assert "triple_pqr" in coherence

    def test_governance_sections_present(self, system: VerdantSystem) -> None:
        chunk = system.process_input("Test governance")
        # DataKing hooks in after InternalCommunication
        assert chunk.get_section_content("data_king_section") is not None
        # EthicsKing hooks in after EthicsValues
        assert chunk.get_section_content("ethics_king_section") is not None
        # ForefrontKing hooks in after ActionSelection
        assert chunk.get_section_content("forefront_king_section") is not None
        # Council hooks in after ActionSelection
        assert chunk.get_section_content("three_kings_layer_section") is not None

    def test_language_response_generated(self, system: VerdantSystem) -> None:
        chunk = system.process_input("What is justice?")
        lang = chunk.get_section_content("language_processing_section")
        assert lang is not None
        assert isinstance(lang.get("generated_response"), str)
        assert len(lang["generated_response"]) > 0

    def test_wave_function_section_has_values(self, system: VerdantSystem) -> None:
        chunk = system.process_input("Test wave")
        wave = chunk.get_section_content("wave_function_section")
        assert wave is not None
        assert "entropy" in wave
        assert "magnitude" in wave
        assert "phase" in wave
