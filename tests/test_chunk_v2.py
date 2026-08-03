from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cognitive_chunk_v2.archive import CognitiveChunkArchive
from cognitive_chunk_v2.models import (
    ClaimRecord,
    ClaimStatus,
    CognitiveChunkV2,
    Modality,
    ObservationRecord,
    TemporalSegmentRecord,
    TemporalTrack,
)
from cognitive_chunk_v2.permissions import ChunkWriter, WritePermissionError
from cognitive_chunk_v2.pipeline import ExperienceInput, PipelineOrchestrator


def test_text_round_trip(tmp_path: Path) -> None:
    orchestrator = PipelineOrchestrator()
    chunk, store = orchestrator.process(
        ExperienceInput.from_text("A remembered sentence.")
    )
    archive = tmp_path / "text_chunk.zip"
    orchestrator.save(archive, chunk, store)

    recall = orchestrator.recall(archive)
    assert recall.payload_integrity
    assert recall.feature_similarity > 0.999999
    assert recall.current_reinterpretation_similarity > 0.999999

    loaded, loaded_store = CognitiveChunkArchive.load(archive)
    assert len(loaded.processing_log) == 9
    assert loaded.sections["language_processing_section"][
        "canonical_representation"
    ] is False
    assert loaded_store.get_bytes(
        loaded.payloads[0].storage_path
    ) == b"A remembered sentence."


def test_observation_records_are_immutable() -> None:
    observation = ObservationRecord(
        payload_id="payload",
        source_id="sensor",
        measurement_type="received",
        data={"value": 1},
        confidence=1.0,
    )
    with pytest.raises(ValidationError):
        observation.confidence = 0.2


def test_write_authority_blocks_language_from_observations() -> None:
    chunk = CognitiveChunkV2()
    writer = ChunkWriter(chunk, "LanguageProcessing")
    with pytest.raises(WritePermissionError):
        writer.append("observations", None)


def test_merge_creates_contradiction() -> None:
    left = CognitiveChunkV2()
    right = CognitiveChunkV2()

    ChunkWriter(left, "ReasoningPlanning").append(
        "claims",
        ClaimRecord(
            scope="damage_state",
            value="intact",
            status=ClaimStatus.SUPPORTED,
            created_by="ReasoningPlanning",
            confidence=0.8,
        ),
    )
    ChunkWriter(right, "ReasoningPlanning").append(
        "claims",
        ClaimRecord(
            scope="damage_state",
            value="cracked",
            status=ClaimStatus.SUPPORTED,
            created_by="ReasoningPlanning",
            confidence=0.8,
        ),
    )

    left.merge_from(right)
    assert len(left.contradictions) == 1
    assert left.contradictions[0].scope == "damage_state"


def test_video_segment_contract_is_ready_but_not_implemented() -> None:
    segment = TemporalSegmentRecord(
        parent_payload_id="video_payload",
        start_ms=1000,
        end_ms=2500,
        track=TemporalTrack.AUDIO,
        selected_by="attention",
        selection_reason="speech event",
    )
    assert segment.track == TemporalTrack.AUDIO
    assert segment.end_ms > segment.start_ms
