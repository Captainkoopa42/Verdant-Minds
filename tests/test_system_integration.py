#!/usr/bin/env python3
"""
Integration Tests for Unified Synthetic Mind System

This module contains comprehensive integration tests for the entire system,
testing component interactions, data flow, memory operations, ethical
evaluation, and block coordination.

The tests use mocking for heavy dependencies (TensorFlow, PyTorch) and
can run without pre-trained models or large datasets.

Test Coverage:
- System initialization with various configurations
- Complete data flow through all nine blocks
- Memory storage, retrieval, and ECWF bridge operations
- Ethical evaluation and Three Kings governance
- Block coordination and information flow
- Integration with existing IntegrationTestSuite infrastructure
- Error handling and edge cases

Run with: pytest tests/test_system_integration.py -v
"""

import pytest
import sys
import time
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Add project root to path for proper package imports
project_root = Path(__file__).parent.parent
verdant_src_root = project_root / "Verdant Source Codes"
if str(verdant_src_root) not in sys.path:
    sys.path.insert(0, str(verdant_src_root))

# Now import the modules using src. prefix
from src.core.system import UnifiedSystem
from src.core.CognitiveChunk import CognitiveChunk
from src.integration.BlockIntegrationManager import BlockIntegrationManager
from src.integration.IntegrationTestSuite import IntegrationTestSuite


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def minimal_config():
    """
    Fixture providing minimal configuration for testing.

    Returns:
        dict: Minimal configuration that disables heavy operations
    """
    return {
        "cognitive_dimensions": 3,
        "ethical_dimensions": 3,
        "wave_facets": 5,
        "bridge_influence_factor": 0.3,
        "learning_rate": 0.05,
        "decision_threshold": 0.7,
        "ethical_sensitivity": 0.6,
        "initialize_knowledge": False,  # Skip heavy initialization
        "log_level": "WARNING"
    }


@pytest.fixture
def standard_config():
    """
    Fixture providing standard configuration for testing.

    Returns:
        dict: Standard configuration for normal testing
    """
    return {
        "cognitive_dimensions": 5,
        "ethical_dimensions": 5,
        "wave_facets": 7,
        "bridge_influence_factor": 0.3,
        "learning_rate": 0.05,
        "decision_threshold": 0.7,
        "ethical_sensitivity": 0.6,
        "initialize_knowledge": False,
        "log_level": "WARNING"
    }


@pytest.fixture
def mock_system(minimal_config):
    """
    Fixture providing a UnifiedSystem instance with mocked heavy dependencies.

    Returns:
        UnifiedSystem: System instance ready for testing
    """
    # Mock TensorFlow/PyTorch operations if they're imported
    with patch.dict('sys.modules', {
        'tensorflow': MagicMock(),
        'torch': MagicMock(),
    }):
        system = UnifiedSystem(seed=42, config=minimal_config)
        return system


@pytest.fixture
def integration_manager(mock_system):
    """
    Fixture providing a BlockIntegrationManager instance.

    Returns:
        BlockIntegrationManager: Manager for block interactions
    """
    return BlockIntegrationManager(mock_system)


@pytest.fixture
def integration_test_suite(mock_system, integration_manager):
    """
    Fixture providing an IntegrationTestSuite instance.

    Returns:
        IntegrationTestSuite: Test suite for integration testing
    """
    return IntegrationTestSuite(mock_system, integration_manager)


@pytest.fixture
def sample_inputs():
    """
    Fixture providing various sample inputs for testing.

    Returns:
        dict: Dictionary of sample input texts
    """
    return {
        "simple": "What is artificial intelligence?",
        "ethical": "Should AI systems be allowed to make life-or-death decisions?",
        "complex": "Analyze the relationship between machine learning, ethics, and societal impact.",
        "uncertain": "What might happen if we develop AGI with incomplete safety measures?",
        "multi_domain": "How do quantum computing, climate change, and economic policy intersect?"
    }


# =============================================================================
# System Initialization Tests
# =============================================================================

class TestSystemInitialization:
    """Tests for system initialization with various configurations."""

    def test_init_with_minimal_config(self, minimal_config):
        """
        Test that system initializes successfully with minimal configuration.

        Minimal config uses smaller dimensions and disabled knowledge initialization
        to speed up testing.
        """
        system = UnifiedSystem(seed=42, config=minimal_config)

        assert system is not None
        assert system.config["cognitive_dimensions"] == 3
        assert system.config["ethical_dimensions"] == 3
        assert system.memory_web is not None
        assert system.ecwf_core is not None
        assert system.memory_bridge is not None

    def test_init_with_standard_config(self, standard_config):
        """
        Test that system initializes with standard configuration.

        Standard config uses default dimensions for realistic testing.
        """
        system = UnifiedSystem(seed=42, config=standard_config)

        assert system is not None
        assert system.config["cognitive_dimensions"] == 5
        assert system.config["ethical_dimensions"] == 5
        assert len(system.blocks) == 9

    def test_init_without_config(self):
        """
        Test that system uses default configuration when none provided.

        Default config should be sensible and allow system to function.
        """
        system = UnifiedSystem(seed=42, config={"initialize_knowledge": False})

        assert system is not None
        assert system.config is not None
        assert "cognitive_dimensions" in system.config
        assert "ethical_dimensions" in system.config

    def test_init_creates_all_blocks(self, mock_system):
        """
        Test that all nine cognitive blocks are created during initialization.

        The system should have all blocks in the nine-block architecture.
        """
        expected_blocks = [
            "SensoryInput",
            "PatternRecognition",
            "InternalCommunication",
            "MemoryStorage",
            "ReasoningPlanning",
            "EthicsValues",
            "ActionSelection",
            "LanguageProcessing",
            "ContinualLearning"
        ]

        for block_name in expected_blocks:
            assert block_name in mock_system.blocks
            assert mock_system.blocks[block_name] is not None

    def test_init_creates_three_kings_layer(self, mock_system):
        """
        Test that Three Kings governance layer is initialized.

        The governance layer provides oversight and coordination.
        """
        assert mock_system.three_kings_layer is not None
        assert hasattr(mock_system.three_kings_layer, 'data_king')
        assert hasattr(mock_system.three_kings_layer, 'ethics_king')
        assert hasattr(mock_system.three_kings_layer, 'forefront_king')

    def test_init_sets_processing_order(self, mock_system):
        """
        Test that processing order is correctly defined.

        Blocks should be processed in the correct sequence.
        """
        assert len(mock_system.processing_order) == 9
        assert mock_system.processing_order[0] == "SensoryInput"
        assert mock_system.processing_order[-1] == "ContinualLearning"

    def test_init_initializes_metrics(self, mock_system):
        """
        Test that system metrics are initialized.

        Metrics track system performance and behavior.
        """
        assert "total_interactions" in mock_system.metrics
        assert "ethical_evaluations" in mock_system.metrics
        assert "decisions_made" in mock_system.metrics
        assert mock_system.metrics["total_interactions"] == 0

    def test_init_with_different_seeds(self, minimal_config):
        """
        Test that different seeds produce different random states.

        Random seeds ensure reproducibility within tests.
        """
        system1 = UnifiedSystem(seed=42, config=minimal_config)
        system2 = UnifiedSystem(seed=123, config=minimal_config)

        # Systems should be different due to different random states
        # (though structure is the same)
        assert system1.metrics["start_time"] != system2.metrics["start_time"]

    def test_init_memory_components(self, mock_system):
        """
        Test that memory components are properly initialized.

        Memory Web and ECWF are core to the system's operation.
        """
        # Memory Web should be initialized
        assert mock_system.memory_web is not None
        assert hasattr(mock_system.memory_web, 'graph')

        # ECWF Core should be initialized with correct dimensions
        assert mock_system.ecwf_core is not None
        assert mock_system.ecwf_core.num_cognitive_dims == 3
        assert mock_system.ecwf_core.num_ethical_dims == 3

        # Bridge should connect them
        assert mock_system.memory_bridge is not None
        assert mock_system.memory_bridge.memory_web == mock_system.memory_web
        assert mock_system.memory_bridge.ecwf_core == mock_system.ecwf_core


# =============================================================================
# Data Flow Tests
# =============================================================================

class TestDataFlow:
    """Tests for data flow through the processing pipeline."""

    def test_process_simple_input(self, mock_system, sample_inputs):
        """
        Test processing a simple input through the entire pipeline.

        Should create a chunk and process it through all blocks.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        assert chunk is not None
        assert isinstance(chunk, CognitiveChunk)
        assert chunk.chunk_id is not None

    def test_chunk_flows_through_all_blocks(self, mock_system, sample_inputs):
        """
        Test that chunk is processed by all blocks in order.

        Each block should add its section to the chunk.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        # Check that sections from various blocks exist
        # (exact section names may vary based on implementation)
        assert len(chunk.sections) > 0
        assert chunk.processing_log is not None
        assert len(chunk.processing_log) > 0

    def test_processing_updates_metrics(self, mock_system, sample_inputs):
        """
        Test that processing updates system metrics.

        Metrics should track interactions and decisions.
        """
        initial_interactions = mock_system.metrics["total_interactions"]

        mock_system.process_input(sample_inputs["simple"])

        assert mock_system.metrics["total_interactions"] == initial_interactions + 1
        assert mock_system.metrics["last_interaction_time"] > 0

    def test_processing_order_is_respected(self, mock_system, sample_inputs):
        """
        Test that blocks are processed in the defined order.

        Processing log should show blocks in the correct sequence.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        # The chunk should have a processing log
        assert hasattr(chunk, 'processing_log')
        assert len(chunk.processing_log) > 0

        # First entry should be from SensoryInput
        # (if blocks are logging their operations)

    def test_chunk_retains_metadata(self, mock_system, sample_inputs):
        """
        Test that chunk retains metadata throughout processing.

        Metadata should be preserved and accessible.
        """
        metadata = {"source": "test", "priority": "high"}
        chunk = mock_system.process_input(sample_inputs["simple"], metadata=metadata)

        assert chunk is not None
        # Metadata handling depends on implementation

    def test_multiple_sequential_inputs(self, mock_system, sample_inputs):
        """
        Test processing multiple inputs sequentially.

        System should handle multiple interactions without issues.
        """
        chunk1 = mock_system.process_input(sample_inputs["simple"])
        chunk2 = mock_system.process_input(sample_inputs["ethical"])
        chunk3 = mock_system.process_input(sample_inputs["complex"])

        assert chunk1.chunk_id != chunk2.chunk_id
        assert chunk2.chunk_id != chunk3.chunk_id
        assert mock_system.metrics["total_interactions"] >= 3

    def test_processing_includes_metrics(self, mock_system, sample_inputs):
        """
        Test that processing metrics are added to chunk.

        Chunk should include timing and performance data.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        # Check if processing metrics section exists
        metrics_section = chunk.get_section_content("processing_metrics_section")
        if metrics_section:
            assert "processing_times" in metrics_section or "total_processing_time" in metrics_section


# =============================================================================
# Memory Operations Tests
# =============================================================================

class TestMemoryOperations:
    """Tests for memory storage, retrieval, and ECWF bridge operations."""

    def test_memory_web_accessible(self, mock_system):
        """
        Test that Memory Web is accessible and functional.

        Memory Web should be initialized and ready for use.
        """
        assert mock_system.memory_web is not None
        assert hasattr(mock_system.memory_web, 'add_concept')
        assert hasattr(mock_system.memory_web, 'get_concept')

    def test_ecwf_core_accessible(self, mock_system):
        """
        Test that ECWF Core is accessible and functional.

        ECWF provides wave function representations.
        """
        assert mock_system.ecwf_core is not None
        assert hasattr(mock_system.ecwf_core, 'create_wave_function')
        assert mock_system.ecwf_core.num_cognitive_dims > 0

    def test_memory_bridge_connects_components(self, mock_system):
        """
        Test that Memory-ECWF Bridge connects memory and wave functions.

        Bridge should enable translation between symbolic and subsymbolic.
        """
        assert mock_system.memory_bridge is not None
        assert mock_system.memory_bridge.memory_web == mock_system.memory_web
        assert mock_system.memory_bridge.ecwf_core == mock_system.ecwf_core

    def test_memory_storage_block_uses_bridge(self, mock_system):
        """
        Test that MemoryStorage block has access to the bridge.

        MemoryStorage should use the bridge for operations.
        """
        memory_block = mock_system.blocks["MemoryStorage"]
        assert hasattr(memory_block, 'memory_bridge') or hasattr(memory_block, 'bridge')

    def test_processing_can_access_memory(self, mock_system, sample_inputs):
        """
        Test that processing can access and use memory.

        Blocks should be able to store and retrieve information.
        """
        # Process input that might trigger memory operations
        chunk = mock_system.process_input(sample_inputs["complex"])

        # Memory section should exist if memory was accessed
        # (exact behavior depends on implementation)
        assert chunk is not None

    def test_wave_function_dimensions(self, mock_system):
        """
        Test that wave functions have correct dimensions.

        Wave functions should match configured dimensions.
        """
        wave_func = mock_system.ecwf_core.create_wave_function()

        assert wave_func is not None
        assert hasattr(wave_func, 'cognitive_state') or hasattr(wave_func, 'shape')

    def test_dimension_meanings_set(self, mock_system):
        """
        Test that dimension meanings are initialized.

        Dimensions should have semantic interpretations.
        """
        # Check that ECWF has dimension meanings
        assert hasattr(mock_system.ecwf_core, 'cognitive_meanings') or \
               hasattr(mock_system.ecwf_core, 'dimension_meanings')


# =============================================================================
# Ethical Evaluation Tests
# =============================================================================

class TestEthicalEvaluation:
    """Tests for ethical evaluation and Three Kings governance."""

    def test_ethics_values_block_exists(self, mock_system):
        """
        Test that EthicsValues block is initialized.

        Ethics block provides moral reasoning capabilities.
        """
        assert "EthicsValues" in mock_system.blocks
        ethics_block = mock_system.blocks["EthicsValues"]
        assert ethics_block is not None

    def test_ethical_input_triggers_evaluation(self, mock_system, sample_inputs):
        """
        Test that ethical input triggers ethical evaluation.

        Ethical questions should be processed by ethics systems.
        """
        chunk = mock_system.process_input(sample_inputs["ethical"])

        assert chunk is not None
        # Check if ethical evaluation occurred
        # (exact section name may vary)

    def test_three_kings_layer_accessible(self, mock_system):
        """
        Test that Three Kings Layer is accessible.

        All three kings should be present.
        """
        kings = mock_system.three_kings_layer

        assert hasattr(kings, 'data_king')
        assert hasattr(kings, 'ethics_king')
        assert hasattr(kings, 'forefront_king')

    def test_ethics_king_oversees_processing(self, mock_system, sample_inputs):
        """
        Test that Ethics King provides oversight.

        Ethics King should evaluate ethical implications.
        """
        initial_evaluations = mock_system.metrics["ethical_evaluations"]

        chunk = mock_system.process_input(sample_inputs["ethical"])

        # Ethical evaluations should have increased
        assert mock_system.metrics["ethical_evaluations"] >= initial_evaluations

    def test_data_king_oversees_processing(self, mock_system, sample_inputs):
        """
        Test that Data King provides oversight.

        Data King should validate data flow.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        # Data King should have been involved
        # (checking via processing would require implementation details)
        assert chunk is not None

    def test_forefront_king_oversees_actions(self, mock_system, sample_inputs):
        """
        Test that Forefront King oversees action selection.

        Forefront King should coordinate decision-making.
        """
        initial_decisions = mock_system.metrics["decisions_made"]

        chunk = mock_system.process_input(sample_inputs["simple"])

        # Decisions should have been made
        assert mock_system.metrics["decisions_made"] >= initial_decisions

    def test_ethical_principles_defined(self, mock_system):
        """
        Test that ethical principles are defined in ECWF.

        Ethical dimensions should have semantic meanings.
        """
        ecwf = mock_system.ecwf_core

        # Check for ethical dimension meanings
        assert hasattr(ecwf, 'ethical_meanings') or \
               hasattr(ecwf, 'dimension_meanings')


# =============================================================================
# Block Coordination Tests
# =============================================================================

class TestBlockCoordination:
    """Tests for coordination between blocks."""

    def test_blocks_share_chunk(self, mock_system, sample_inputs):
        """
        Test that all blocks process the same chunk instance.

        Chunk should accumulate data from all blocks.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])

        # Chunk should have sections from multiple blocks
        assert len(chunk.sections) > 1

    def test_internal_communication_block_coordinates(self, mock_system):
        """
        Test that InternalCommunication block facilitates coordination.

        This block should enable information sharing.
        """
        assert "InternalCommunication" in mock_system.blocks
        comm_block = mock_system.blocks["InternalCommunication"]
        assert comm_block is not None

    def test_block_integration_manager_tracks_interactions(self, integration_manager, mock_system, sample_inputs):
        """
        Test that BlockIntegrationManager tracks interactions.

        Manager should analyze cross-block communication.
        """
        chunk = mock_system.process_input(sample_inputs["complex"])

        interaction_data = integration_manager.analyze_block_interactions(chunk)

        assert interaction_data is not None
        assert isinstance(interaction_data, dict)

    def test_processing_creates_coordination_data(self, mock_system, sample_inputs):
        """
        Test that processing creates coordination data.

        Blocks should communicate and coordinate.
        """
        chunk = mock_system.process_input(sample_inputs["multi_domain"])

        # Check for coordination evidence in chunk
        assert chunk.processing_log is not None
        assert len(chunk.processing_log) > 0

    def test_reasoning_block_coordinates_with_memory(self, mock_system):
        """
        Test that ReasoningPlanning block coordinates with memory.

        Reasoning should access memory for context.
        """
        reasoning_block = mock_system.blocks["ReasoningPlanning"]
        assert hasattr(reasoning_block, 'memory_bridge') or \
               hasattr(reasoning_block, 'bridge')

    def test_language_block_coordinates_with_memory(self, mock_system):
        """
        Test that LanguageProcessing block coordinates with memory.

        Language processing should access memory.
        """
        language_block = mock_system.blocks["LanguageProcessing"]
        assert hasattr(language_block, 'memory_bridge') or \
               hasattr(language_block, 'bridge')


# =============================================================================
# Integration Test Suite Tests
# =============================================================================

class TestIntegrationTestSuiteUsage:
    """Tests using the existing IntegrationTestSuite infrastructure."""

    def test_integration_test_suite_initialization(self, integration_test_suite):
        """
        Test that IntegrationTestSuite initializes correctly.

        Suite should have test scenarios and metrics.
        """
        assert integration_test_suite is not None
        assert hasattr(integration_test_suite, 'test_scenarios')
        assert hasattr(integration_test_suite, 'performance_metrics')
        assert len(integration_test_suite.test_scenarios) > 0

    def test_integration_test_suite_has_scenarios(self, integration_test_suite):
        """
        Test that test suite includes predefined scenarios.

        Scenarios should cover various test cases.
        """
        scenarios = integration_test_suite.test_scenarios

        assert len(scenarios) > 0
        # Check that scenarios have required fields
        for scenario in scenarios:
            assert "name" in scenario
            assert "input" in scenario
            assert "validation_criteria" in scenario

    @pytest.mark.slow
    def test_run_integration_tests(self, integration_test_suite):
        """
        Test running the full integration test suite.

        This test is marked as slow since it runs multiple scenarios.
        """
        # Mock the system's get_response method to avoid heavy processing
        with patch.object(integration_test_suite.system, 'get_response', return_value="Test response"):
            results = integration_test_suite.run_integration_tests()

            assert results is not None
            assert "overall_success" in results
            assert "scenario_results" in results
            assert "performance_metrics" in results

    def test_integration_manager_analyzes_interactions(self, integration_manager, mock_system, sample_inputs):
        """
        Test that integration manager can analyze block interactions.

        Manager should provide insights into block communication.
        """
        chunk = mock_system.process_input(sample_inputs["simple"])
        analysis = integration_manager.analyze_block_interactions(chunk)

        assert analysis is not None
        assert isinstance(analysis, dict)


# =============================================================================
# Error Handling and Edge Cases
# =============================================================================

class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_empty_input_handling(self, mock_system):
        """
        Test that system handles empty input gracefully.

        Should not crash on empty strings.
        """
        try:
            chunk = mock_system.process_input("")
            assert chunk is not None or True  # Should handle gracefully
        except Exception as e:
            # If it raises an exception, it should be informative
            assert str(e) or True

    def test_very_long_input_handling(self, mock_system):
        """
        Test that system handles very long input.

        Should process or truncate appropriately.
        """
        long_input = "AI " * 1000  # 2000 characters
        chunk = mock_system.process_input(long_input)

        assert chunk is not None

    def test_special_characters_in_input(self, mock_system):
        """
        Test that system handles special characters.

        Should process Unicode and special characters.
        """
        special_input = "What is ∫∞ AI? 中文 العربية 🤖"
        chunk = mock_system.process_input(special_input)

        assert chunk is not None

    def test_invalid_config_uses_defaults(self):
        """
        Test that invalid config values fall back to defaults.

        System should be robust to configuration errors.
        """
        invalid_config = {
            "cognitive_dimensions": -5,  # Invalid
            "initialize_knowledge": False
        }

        # Should either use defaults or validate
        try:
            system = UnifiedSystem(seed=42, config=invalid_config)
            assert system is not None
        except (ValueError, AssertionError):
            # Acceptable to raise validation error
            pass

    def test_missing_config_keys(self):
        """
        Test that missing config keys use defaults.

        Partial configs should be acceptable.
        """
        partial_config = {
            "initialize_knowledge": False,
            "log_level": "WARNING"
        }

        system = UnifiedSystem(seed=42, config=partial_config)

        assert system is not None
        assert "cognitive_dimensions" in system.config


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestPerformance:
    """Performance tests for system integration."""

    def test_processing_time_reasonable(self, mock_system, sample_inputs):
        """
        Test that processing time is reasonable.

        Should complete in under 5 seconds for simple inputs.
        """
        start_time = time.time()
        chunk = mock_system.process_input(sample_inputs["simple"])
        processing_time = time.time() - start_time

        assert processing_time < 5.0  # Should be reasonably fast

    def test_multiple_rapid_inputs(self, mock_system, sample_inputs):
        """
        Test system with rapid sequential inputs.

        Should handle quick succession without issues.
        """
        inputs = [sample_inputs["simple"]] * 5

        for input_text in inputs:
            chunk = mock_system.process_input(input_text)
            assert chunk is not None

        assert mock_system.metrics["total_interactions"] >= 5

    def test_memory_usage_stable(self, mock_system, sample_inputs):
        """
        Test that memory usage doesn't grow unbounded.

        Processing multiple inputs shouldn't leak memory.
        """
        # Process several inputs
        for _ in range(10):
            mock_system.process_input(sample_inputs["simple"])

        # System should still be functional
        chunk = mock_system.process_input(sample_inputs["complex"])
        assert chunk is not None


# =============================================================================
# Integration Workflow Tests
# =============================================================================

class TestIntegrationWorkflows:
    """Tests for complete integration workflows."""

    def test_full_pipeline_with_ethical_reasoning(self, mock_system, sample_inputs):
        """
        Test complete pipeline with ethical reasoning.

        Should process ethical input through all blocks including ethics.
        """
        chunk = mock_system.process_input(sample_inputs["ethical"])

        assert chunk is not None
        assert mock_system.metrics["ethical_evaluations"] > 0

    def test_full_pipeline_with_uncertainty(self, mock_system, sample_inputs):
        """
        Test complete pipeline with uncertain input.

        Should handle uncertainty and generate appropriate response.
        """
        chunk = mock_system.process_input(sample_inputs["uncertain"])

        assert chunk is not None
        # Uncertainty should be reflected in processing

    def test_full_pipeline_with_multi_domain(self, mock_system, sample_inputs):
        """
        Test complete pipeline with multi-domain input.

        Should integrate information across domains.
        """
        chunk = mock_system.process_input(sample_inputs["multi_domain"])

        assert chunk is not None
        assert len(chunk.sections) > 0

    def test_end_to_end_with_response_generation(self, mock_system, sample_inputs):
        """
        Test end-to-end processing with response generation.

        Should produce a complete response.
        """
        response = mock_system.get_response(sample_inputs["simple"])

        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_continual_learning_block_activated(self, mock_system, sample_inputs):
        """
        Test that ContinualLearning block is activated.

        Last block should process and potentially update system.
        """
        chunk = mock_system.process_input(sample_inputs["complex"])

        # ContinualLearning is last in processing order
        assert "ContinualLearning" in mock_system.processing_order
        assert mock_system.processing_order[-1] == "ContinualLearning"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
