#!/usr/bin/env python3
"""
Unit Tests for CognitiveChunk Class

This module contains comprehensive unit tests for the CognitiveChunk class,
which is the core data structure for information processing in the Unified
Synthetic Mind cognitive architecture.

Test Coverage:
- Initialization and ID generation
- Section creation, update, and retrieval
- Processing log management
- Chunk merging operations
- Edge cases and error handling

Run with: pytest tests/test_cognitive_chunk.py -v
"""

import pytest
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "Verdant Source Codes" / "src"))

from core.CognitiveChunk import CognitiveChunk


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def empty_chunk():
    """
    Fixture that provides a fresh CognitiveChunk instance with auto-generated ID.

    Returns:
        CognitiveChunk: A new chunk with default initialization
    """
    return CognitiveChunk()


@pytest.fixture
def custom_chunk():
    """
    Fixture that provides a CognitiveChunk with a custom ID.

    Returns:
        CognitiveChunk: A new chunk with custom ID "test_chunk_001"
    """
    return CognitiveChunk(chunk_id="test_chunk_001")


@pytest.fixture
def populated_chunk():
    """
    Fixture that provides a CognitiveChunk pre-populated with sample data.

    Returns:
        CognitiveChunk: A chunk with multiple sections and processing logs
    """
    chunk = CognitiveChunk(chunk_id="populated_test")

    # Add sensory input section
    chunk.add_section("sensory_input", {
        "input_text": "What is artificial intelligence?",
        "tokens": ["What", "is", "artificial", "intelligence"],
        "complexity_score": 0.65
    })

    # Add memory section
    chunk.add_section("memory", {
        "retrieved_concepts": ["AI", "Machine Learning", "Neural Networks"],
        "activation_scores": [0.9, 0.7, 0.6]
    })

    # Add processing steps
    chunk.add_processing_step(
        processor_name="SensoryInput",
        operation="tokenize",
        details={"token_count": 4}
    )
    chunk.add_processing_step(
        processor_name="Memory",
        operation="retrieve",
        details={"concepts_found": 3}
    )

    return chunk


@pytest.fixture
def merge_source_chunk():
    """
    Fixture that provides a chunk to be used as merge source in merge tests.

    Returns:
        CognitiveChunk: A chunk with sections designed for merge testing
    """
    chunk = CognitiveChunk(chunk_id="merge_source")

    chunk.add_section("reasoning", {
        "inference_type": "deductive",
        "confidence": 0.85
    })

    chunk.add_section("memory", {
        "new_key": "new_value",
        "additional_concepts": ["Deep Learning"]
    })

    chunk.add_processing_step(
        processor_name="Reasoning",
        operation="infer",
        details={"steps": 5}
    )

    return chunk


# =============================================================================
# Initialization Tests
# =============================================================================

class TestInitialization:
    """Tests for CognitiveChunk initialization and basic properties."""

    def test_init_with_auto_id(self, empty_chunk):
        """
        Test that initialization without an ID generates a default chunk ID.

        The auto-generated ID should follow the format 'chunk_<timestamp>'.
        """
        assert empty_chunk.chunk_id is not None
        assert empty_chunk.chunk_id.startswith("chunk_")
        assert len(empty_chunk.chunk_id) > 6  # More than just "chunk_"

    def test_init_with_custom_id(self, custom_chunk):
        """
        Test that initialization with a custom ID uses that ID.

        Custom IDs should be preserved exactly as provided.
        """
        assert custom_chunk.chunk_id == "test_chunk_001"

    def test_init_sets_creation_time(self, empty_chunk):
        """
        Test that creation_time is set to a valid timestamp.

        The timestamp should be close to the current time (within 1 second).
        """
        current_time = time.time()
        assert abs(empty_chunk.creation_time - current_time) < 1.0
        assert isinstance(empty_chunk.creation_time, float)

    def test_init_creates_empty_sections_dict(self, empty_chunk):
        """
        Test that sections dictionary is initialized as empty.

        A new chunk should have no sections until they are added.
        """
        assert isinstance(empty_chunk.sections, dict)
        assert len(empty_chunk.sections) == 0

    def test_init_creates_empty_processing_log(self, empty_chunk):
        """
        Test that processing_log is initialized as an empty list.

        A new chunk should have no processing history.
        """
        assert isinstance(empty_chunk.processing_log, list)
        assert len(empty_chunk.processing_log) == 0

    def test_multiple_chunks_have_different_ids(self):
        """
        Test that auto-generated IDs are unique for different chunks.

        Note: Since IDs use int(time.time()), chunks created within the same
        second will have the same ID. This test ensures uniqueness by waiting
        1.1 seconds between creations.
        """
        chunk1 = CognitiveChunk()
        time.sleep(1.1)  # Wait for different second to ensure different timestamps
        chunk2 = CognitiveChunk()

        assert chunk1.chunk_id != chunk2.chunk_id


# =============================================================================
# Section Management Tests
# =============================================================================

class TestSectionManagement:
    """Tests for adding, updating, and retrieving sections."""

    def test_add_section_success(self, empty_chunk):
        """
        Test that add_section successfully adds a new section.

        After adding, the section should be retrievable with correct content.
        """
        content = {"key1": "value1", "key2": 42}
        empty_chunk.add_section("test_section", content)

        assert "test_section" in empty_chunk.sections
        assert empty_chunk.sections["test_section"] == content

    def test_add_section_duplicate_raises_error(self, empty_chunk):
        """
        Test that adding a duplicate section raises ValueError.

        The add_section method should prevent overwriting existing sections.
        """
        content1 = {"data": "first"}
        content2 = {"data": "second"}

        empty_chunk.add_section("duplicate", content1)

        with pytest.raises(ValueError) as exc_info:
            empty_chunk.add_section("duplicate", content2)

        assert "already exists" in str(exc_info.value)

    def test_add_multiple_sections(self, empty_chunk):
        """
        Test that multiple sections can be added to a chunk.

        All sections should be independently stored and retrievable.
        """
        empty_chunk.add_section("section1", {"data": 1})
        empty_chunk.add_section("section2", {"data": 2})
        empty_chunk.add_section("section3", {"data": 3})

        assert len(empty_chunk.sections) == 3
        assert empty_chunk.sections["section1"]["data"] == 1
        assert empty_chunk.sections["section2"]["data"] == 2
        assert empty_chunk.sections["section3"]["data"] == 3

    def test_update_section_existing(self, populated_chunk):
        """
        Test that update_section modifies an existing section.

        The old content should be completely replaced by the new content.
        """
        original_content = populated_chunk.get_section_content("sensory_input")
        assert original_content is not None

        new_content = {"input_text": "Updated text", "new_field": 123}
        populated_chunk.update_section("sensory_input", new_content)

        updated_content = populated_chunk.get_section_content("sensory_input")
        assert updated_content == new_content
        assert "complexity_score" not in updated_content  # Old key removed
        assert "new_field" in updated_content  # New key added

    def test_update_section_creates_if_not_exists(self, empty_chunk):
        """
        Test that update_section creates a section if it doesn't exist.

        Unlike add_section, update_section should work for new sections too.
        """
        content = {"created_by": "update"}
        empty_chunk.update_section("new_section", content)

        assert "new_section" in empty_chunk.sections
        assert empty_chunk.sections["new_section"] == content

    def test_get_section_content_existing(self, populated_chunk):
        """
        Test that get_section_content retrieves existing section correctly.

        Should return the exact dictionary stored in the section.
        """
        memory_content = populated_chunk.get_section_content("memory")

        assert memory_content is not None
        assert isinstance(memory_content, dict)
        assert "retrieved_concepts" in memory_content
        assert memory_content["retrieved_concepts"] == ["AI", "Machine Learning", "Neural Networks"]

    def test_get_section_content_nonexistent_returns_none(self, empty_chunk):
        """
        Test that get_section_content returns None for missing sections.

        This allows safe querying without raising exceptions.
        """
        result = empty_chunk.get_section_content("nonexistent_section")
        assert result is None

    def test_section_content_is_mutable(self, empty_chunk):
        """
        Test that section content can be modified through the returned reference.

        Note: This tests current behavior. In production, consider using
        deep copies to prevent unintended mutations.
        """
        content = {"mutable": "original"}
        empty_chunk.add_section("test", content)

        # Get reference and modify
        retrieved = empty_chunk.get_section_content("test")
        retrieved["mutable"] = "modified"

        # Verify modification persisted
        assert empty_chunk.sections["test"]["mutable"] == "modified"


# =============================================================================
# Processing Log Tests
# =============================================================================

class TestProcessingLog:
    """Tests for processing log management and history tracking."""

    def test_add_processing_step_success(self, empty_chunk):
        """
        Test that add_processing_step correctly adds a log entry.

        The entry should include all provided fields plus a timestamp.
        """
        before_time = time.time()

        empty_chunk.add_processing_step(
            processor_name="TestProcessor",
            operation="test_op",
            details={"param": "value"}
        )

        after_time = time.time()

        assert len(empty_chunk.processing_log) == 1

        log_entry = empty_chunk.processing_log[0]
        assert log_entry["processor"] == "TestProcessor"
        assert log_entry["operation"] == "test_op"
        assert log_entry["details"] == {"param": "value"}
        assert before_time <= log_entry["timestamp"] <= after_time

    def test_add_multiple_processing_steps(self, empty_chunk):
        """
        Test that multiple processing steps are logged in order.

        The log should maintain chronological order of operations.
        """
        empty_chunk.add_processing_step("Processor1", "op1", {})
        time.sleep(0.001)
        empty_chunk.add_processing_step("Processor2", "op2", {})
        time.sleep(0.001)
        empty_chunk.add_processing_step("Processor3", "op3", {})

        assert len(empty_chunk.processing_log) == 3

        # Verify chronological order
        timestamps = [step["timestamp"] for step in empty_chunk.processing_log]
        assert timestamps == sorted(timestamps)

    def test_get_processing_history_all(self, populated_chunk):
        """
        Test that get_processing_history without filter returns all entries.

        Should return complete log when no processor_name is specified.
        """
        history = populated_chunk.get_processing_history()

        assert len(history) == 2
        assert history[0]["processor"] == "SensoryInput"
        assert history[1]["processor"] == "Memory"

    def test_get_processing_history_filtered(self, populated_chunk):
        """
        Test that get_processing_history filters by processor_name.

        Should return only entries matching the specified processor.
        """
        # Add another entry from SensoryInput
        populated_chunk.add_processing_step(
            "SensoryInput",
            "validate",
            {"valid": True}
        )

        sensory_history = populated_chunk.get_processing_history("SensoryInput")

        assert len(sensory_history) == 2
        assert all(step["processor"] == "SensoryInput" for step in sensory_history)

    def test_get_processing_history_nonexistent_processor(self, populated_chunk):
        """
        Test that filtering by nonexistent processor returns empty list.

        Should gracefully handle processors that haven't logged anything.
        """
        history = populated_chunk.get_processing_history("NonexistentProcessor")

        assert isinstance(history, list)
        assert len(history) == 0

    def test_processing_log_details_structure(self, empty_chunk):
        """
        Test that complex details structures are preserved correctly.

        The details field should support nested dictionaries and lists.
        """
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "mixed": {"items": ["a", "b"]}
        }

        empty_chunk.add_processing_step(
            "ComplexProcessor",
            "complex_op",
            complex_details
        )

        log_entry = empty_chunk.processing_log[0]
        assert log_entry["details"] == complex_details
        assert log_entry["details"]["nested"]["key"] == "value"
        assert log_entry["details"]["list"] == [1, 2, 3]


# =============================================================================
# Merge Operations Tests
# =============================================================================

class TestMergeOperations:
    """Tests for merging chunks together."""

    def test_merge_chunk_adds_new_sections(self, populated_chunk, merge_source_chunk):
        """
        Test that merge_chunk adds sections from source that don't exist in target.

        New sections should be added completely.
        """
        # populated_chunk has: sensory_input, memory
        # merge_source_chunk has: reasoning, memory

        populated_chunk.merge_chunk(merge_source_chunk)

        # Reasoning section should be added
        assert "reasoning" in populated_chunk.sections
        assert populated_chunk.sections["reasoning"]["inference_type"] == "deductive"

    def test_merge_chunk_updates_existing_sections(self, populated_chunk, merge_source_chunk):
        """
        Test that merge_chunk adds non-overlapping keys to existing sections.

        For overlapping sections, only new keys should be added;
        existing keys should be preserved.
        """
        # Both chunks have "memory" section
        original_concepts = populated_chunk.sections["memory"]["retrieved_concepts"]

        populated_chunk.merge_chunk(merge_source_chunk)

        # Original keys should be preserved
        assert populated_chunk.sections["memory"]["retrieved_concepts"] == original_concepts

        # New keys from merge source should be added
        assert "new_key" in populated_chunk.sections["memory"]
        assert populated_chunk.sections["memory"]["new_key"] == "new_value"
        assert "additional_concepts" in populated_chunk.sections["memory"]

    def test_merge_chunk_extends_processing_log(self, populated_chunk, merge_source_chunk):
        """
        Test that merge_chunk extends the processing log.

        All processing entries from source should be appended to target's log.
        """
        original_log_length = len(populated_chunk.processing_log)
        source_log_length = len(merge_source_chunk.processing_log)

        populated_chunk.merge_chunk(merge_source_chunk)

        assert len(populated_chunk.processing_log) == original_log_length + source_log_length

        # Last entry should be from merge source
        assert populated_chunk.processing_log[-1]["processor"] == "Reasoning"

    def test_merge_empty_chunk(self, populated_chunk):
        """
        Test that merging an empty chunk doesn't affect the target.

        Should be a no-op when source chunk is empty.
        """
        empty = CognitiveChunk(chunk_id="empty")

        original_sections = dict(populated_chunk.sections)
        original_log_length = len(populated_chunk.processing_log)

        populated_chunk.merge_chunk(empty)

        assert populated_chunk.sections == original_sections
        assert len(populated_chunk.processing_log) == original_log_length

    def test_merge_into_empty_chunk(self, empty_chunk, merge_source_chunk):
        """
        Test that merging into an empty chunk copies all sections.

        Empty target should receive all sections from source.
        """
        empty_chunk.merge_chunk(merge_source_chunk)

        assert len(empty_chunk.sections) == len(merge_source_chunk.sections)
        assert "reasoning" in empty_chunk.sections
        assert "memory" in empty_chunk.sections

    def test_merge_preserves_chunk_identity(self, populated_chunk, merge_source_chunk):
        """
        Test that merge doesn't change the target chunk's ID or creation time.

        Metadata of the target chunk should remain unchanged.
        """
        original_id = populated_chunk.chunk_id
        original_time = populated_chunk.creation_time

        populated_chunk.merge_chunk(merge_source_chunk)

        assert populated_chunk.chunk_id == original_id
        assert populated_chunk.creation_time == original_time

    def test_merge_does_not_modify_source(self, populated_chunk, merge_source_chunk):
        """
        Test that merging doesn't modify the source chunk.

        Source chunk should remain unchanged after merge operation.
        """
        original_source_sections = dict(merge_source_chunk.sections)
        original_source_log = list(merge_source_chunk.processing_log)

        populated_chunk.merge_chunk(merge_source_chunk)

        assert merge_source_chunk.sections == original_source_sections
        assert merge_source_chunk.processing_log == original_source_log


# =============================================================================
# Edge Cases and Validation Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_section_with_empty_dict(self, empty_chunk):
        """
        Test that sections can contain empty dictionaries.

        Empty content should be valid for sections.
        """
        empty_chunk.add_section("empty_section", {})

        assert "empty_section" in empty_chunk.sections
        assert empty_chunk.sections["empty_section"] == {}

    def test_section_with_none_values(self, empty_chunk):
        """
        Test that section content can include None values.

        None is a valid value for dictionary keys.
        """
        content = {"key1": None, "key2": "value"}
        empty_chunk.add_section("section_with_none", content)

        retrieved = empty_chunk.get_section_content("section_with_none")
        assert retrieved["key1"] is None
        assert retrieved["key2"] == "value"

    def test_processing_step_with_empty_details(self, empty_chunk):
        """
        Test that processing steps can have empty details.

        Empty details dictionary should be allowed.
        """
        empty_chunk.add_processing_step("Processor", "operation", {})

        assert len(empty_chunk.processing_log) == 1
        assert empty_chunk.processing_log[0]["details"] == {}

    def test_chunk_id_with_special_characters(self):
        """
        Test that chunk IDs can contain special characters.

        Custom IDs should support various naming conventions.
        """
        special_ids = [
            "chunk-with-dashes",
            "chunk_with_underscores",
            "chunk.with.dots",
            "chunk:with:colons",
            "chunk/with/slashes"
        ]

        for chunk_id in special_ids:
            chunk = CognitiveChunk(chunk_id=chunk_id)
            assert chunk.chunk_id == chunk_id

    def test_very_long_section_content(self, empty_chunk):
        """
        Test that sections can handle large content dictionaries.

        Should support sections with many keys and large data.
        """
        large_content = {f"key_{i}": f"value_{i}" for i in range(1000)}
        empty_chunk.add_section("large_section", large_content)

        retrieved = empty_chunk.get_section_content("large_section")
        assert len(retrieved) == 1000
        assert retrieved["key_500"] == "value_500"

    def test_merge_with_deeply_nested_conflicts(self):
        """
        Test merge behavior with nested dictionary conflicts.

        Note: Current implementation doesn't deep-merge nested dicts.
        This test documents the expected behavior.
        """
        chunk1 = CognitiveChunk(chunk_id="chunk1")
        chunk1.add_section("section", {
            "nested": {"level1": {"level2": "original"}}
        })

        chunk2 = CognitiveChunk(chunk_id="chunk2")
        chunk2.add_section("section", {
            "nested": {"level1": {"level2": "new"}},
            "other_key": "value"
        })

        chunk1.merge_chunk(chunk2)

        # Original nested value should be preserved (no deep merge)
        assert chunk1.sections["section"]["nested"]["level1"]["level2"] == "original"

        # New top-level key should be added
        assert chunk1.sections["section"]["other_key"] == "value"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests simulating real usage patterns."""

    def test_full_pipeline_simulation(self):
        """
        Test a complete processing pipeline simulation.

        Simulates how a chunk might flow through multiple processing blocks.
        """
        # Create chunk with sensory input
        chunk = CognitiveChunk(chunk_id="pipeline_test")

        # Block 1: Sensory Input
        chunk.add_section("sensory_input", {
            "input_text": "Test query",
            "tokens": ["Test", "query"]
        })
        chunk.add_processing_step("SensoryInput", "process", {"tokens": 2})

        # Block 2: Memory
        chunk.update_section("memory", {
            "concepts": ["Concept1", "Concept2"]
        })
        chunk.add_processing_step("Memory", "retrieve", {"concepts_found": 2})

        # Block 3: Reasoning
        chunk.update_section("reasoning", {
            "inference": "deductive",
            "confidence": 0.8
        })
        chunk.add_processing_step("Reasoning", "infer", {"confidence": 0.8})

        # Block 4: Action Selection
        chunk.update_section("action", {
            "selected_action": "respond",
            "action_confidence": 0.9
        })
        chunk.add_processing_step("ActionSelection", "select", {"action": "respond"})

        # Verify complete pipeline
        assert len(chunk.sections) == 4
        assert len(chunk.processing_log) == 4

        # Verify all blocks logged in order
        processors = [step["processor"] for step in chunk.processing_log]
        assert processors == ["SensoryInput", "Memory", "Reasoning", "ActionSelection"]

    def test_chunk_reuse_and_update(self):
        """
        Test that chunks can be reused and updated across multiple interactions.

        Simulates updating a chunk with new information over time.
        """
        chunk = CognitiveChunk(chunk_id="reusable")

        # First interaction
        chunk.add_section("interaction_1", {"data": "first"})
        chunk.add_processing_step("Processor", "interaction_1", {})

        # Second interaction - update and add
        chunk.update_section("interaction_1", {"data": "updated"})
        chunk.add_section("interaction_2", {"data": "second"})
        chunk.add_processing_step("Processor", "interaction_2", {})

        # Third interaction
        chunk.add_section("interaction_3", {"data": "third"})
        chunk.add_processing_step("Processor", "interaction_3", {})

        assert len(chunk.sections) == 3
        assert len(chunk.processing_log) == 3
        assert chunk.sections["interaction_1"]["data"] == "updated"

    def test_parallel_chunk_processing(self):
        """
        Test creating and merging multiple chunks in parallel.

        Simulates parallel processing paths that converge.
        """
        # Main chunk
        main_chunk = CognitiveChunk(chunk_id="main")
        main_chunk.add_section("input", {"text": "query"})

        # Parallel path 1: Memory retrieval
        memory_chunk = CognitiveChunk(chunk_id="memory_path")
        memory_chunk.add_section("memory_results", {"concepts": ["A", "B"]})
        memory_chunk.add_processing_step("Memory", "retrieve", {})

        # Parallel path 2: Ethical evaluation
        ethics_chunk = CognitiveChunk(chunk_id="ethics_path")
        ethics_chunk.add_section("ethics_results", {"status": "approved"})
        ethics_chunk.add_processing_step("Ethics", "evaluate", {})

        # Merge parallel results back to main
        main_chunk.merge_chunk(memory_chunk)
        main_chunk.merge_chunk(ethics_chunk)

        # Verify merged results
        assert "input" in main_chunk.sections
        assert "memory_results" in main_chunk.sections
        assert "ethics_results" in main_chunk.sections
        assert len(main_chunk.processing_log) == 2


# =============================================================================
# Performance and Stress Tests
# =============================================================================

class TestPerformance:
    """Performance and stress tests for CognitiveChunk."""

    def test_many_sections_performance(self):
        """
        Test that chunk can handle many sections efficiently.

        Should be able to manage hundreds of sections without issues.
        """
        chunk = CognitiveChunk()

        # Add 500 sections
        for i in range(500):
            chunk.add_section(f"section_{i}", {"data": i})

        assert len(chunk.sections) == 500

        # Verify random access works
        assert chunk.get_section_content("section_250")["data"] == 250

    def test_large_processing_log(self):
        """
        Test that processing log can handle many entries.

        Should efficiently manage logs with thousands of entries.
        """
        chunk = CognitiveChunk()

        # Add 1000 processing steps
        for i in range(1000):
            chunk.add_processing_step(
                f"Processor_{i % 10}",
                "operation",
                {"step": i}
            )

        assert len(chunk.processing_log) == 1000

        # Test filtered retrieval
        processor_0_steps = chunk.get_processing_history("Processor_0")
        assert len(processor_0_steps) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
