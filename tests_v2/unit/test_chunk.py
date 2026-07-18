"""Unit tests for verdant.pipeline.chunk.CognitiveChunk."""

from __future__ import annotations

import pytest
from verdant.pipeline.chunk import CognitiveChunk, ProcessingStep


class TestSections:
    """Test section add/update/get."""

    def test_add_section(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_section("test_section", {"key": "value"})
        assert chunk.get_section_content("test_section") == {"key": "value"}

    def test_add_duplicate_raises(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_section("sec", {"a": 1})
        with pytest.raises(ValueError, match="already exists"):
            chunk.add_section("sec", {"b": 2})

    def test_update_section_creates(self) -> None:
        chunk = CognitiveChunk()
        chunk.update_section("new_sec", {"x": 42})
        assert chunk.get_section_content("new_sec") == {"x": 42}

    def test_update_section_overwrites(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_section("s", {"old": True})
        chunk.update_section("s", {"new": True})
        assert chunk.get_section_content("s") == {"new": True}

    def test_get_missing_returns_none(self) -> None:
        chunk = CognitiveChunk()
        assert chunk.get_section_content("nope") is None

    def test_get_all_sections(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_section("a", {"x": 1})
        chunk.add_section("b", {"y": 2})
        all_sec = chunk.get_all_sections()
        assert set(all_sec.keys()) == {"a", "b"}


class TestProcessingLog:
    """Test processing log."""

    def test_add_step(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_processing_step("BlockA", "process", {"detail": 1})
        log = chunk.get_processing_history()
        assert len(log) == 1
        assert log[0].processor == "BlockA"
        assert log[0].operation == "process"

    def test_filter_by_processor(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_processing_step("A", "step1")
        chunk.add_processing_step("B", "step2")
        chunk.add_processing_step("A", "step3")
        filtered = chunk.get_processing_history("A")
        assert len(filtered) == 2
        assert all(s.processor == "A" for s in filtered)

    def test_step_has_timestamp(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_processing_step("X", "op")
        assert chunk.processing_log[0].timestamp > 0


class TestCompactDict:
    """Test to_compact_dict output."""

    def test_produces_required_keys(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_section("sensory", {"input_text": "hello", "tokens": ["hello"]})
        chunk.add_processing_step("Sensory", "process")
        compact = chunk.to_compact_dict()
        assert "chunk_id" in compact
        assert "sections" in compact
        assert "processing_log" in compact

    def test_truncates_large_values(self) -> None:
        chunk = CognitiveChunk()
        big_list = list(range(100))
        chunk.add_section("big", {"data": big_list, "small": 42})
        compact = chunk.to_compact_dict()
        # Large list should be summarised
        assert isinstance(compact["sections"]["big"]["data"], str)
        # Small scalar kept
        assert compact["sections"]["big"]["small"] == 42

    def test_compact_log_is_lightweight(self) -> None:
        chunk = CognitiveChunk()
        chunk.add_processing_step("A", "op", {"heavy_detail": list(range(50))})
        compact = chunk.to_compact_dict()
        log_entry = compact["processing_log"][0]
        # Compact log should only have processor + operation
        assert set(log_entry.keys()) == {"processor", "operation"}
