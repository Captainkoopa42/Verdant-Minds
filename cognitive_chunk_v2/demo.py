from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .archive import CognitiveChunkArchive
from .models import (
    ClaimRecord,
    ClaimStatus,
    CognitiveChunkV2,
    Modality,
    TemporalSegmentRecord,
    TemporalTrack,
)
from .permissions import ChunkWriter, WritePermissionError
from .pipeline import ExperienceInput, PipelineOrchestrator


OUT = Path("/mnt/data")
PACKAGE_OUT = OUT / "cognitive_chunk_v2_results"
PACKAGE_OUT.mkdir(exist_ok=True)


def main() -> None:
    image_path = OUT / "247d9e9d-4198-456e-96c8-07421de8a1f9.png"
    audio_path = OUT / "audio_experience_original.wav"

    experiences = [
        ExperienceInput.from_text(
            "The cup moved downward, grip pressure fell, and a corrective motion restored stability.",
            source_id="plumbing_text_test",
        ),
        ExperienceInput.from_file(
            image_path,
            Modality.IMAGE,
            source_id="plumbing_image_test",
            media_type="image/png",
        ),
        ExperienceInput.from_file(
            audio_path,
            Modality.AUDIO,
            source_id="plumbing_audio_test",
            media_type="audio/wav",
        ),
    ]

    orchestrator = PipelineOrchestrator()
    rows = []
    archive_paths = []

    for experience in experiences:
        orchestrator.substrate.reset()
        chunk, store = orchestrator.process(experience)
        archive_path = (
            PACKAGE_OUT
            / f"{experience.modality.value}_cognitive_chunk_v2.zip"
        )
        orchestrator.save(archive_path, chunk, store)
        recall = orchestrator.recall(archive_path)

        loaded_chunk, loaded_store = CognitiveChunkArchive.load(archive_path)
        rows.append(
            {
                "modality": experience.modality.value,
                "archive_bytes": archive_path.stat().st_size,
                "payload_bytes": loaded_chunk.payloads[0].byte_length,
                "payload_integrity": recall.payload_integrity,
                "feature_similarity": recall.feature_similarity,
                "current_reinterpretation_similarity": (
                    recall.current_reinterpretation_similarity
                ),
                "historical_replay_similarity": (
                    recall.historical_replay_similarity
                ),
                "hybrid_similarity": recall.hybrid_similarity,
                "processing_events": len(loaded_chunk.processing_log),
                "claims": len(loaded_chunk.claims),
                "cognitive_effects": len(loaded_chunk.cognitive_effects),
                "resource_count": len(loaded_store.resources),
                "section_count": len(loaded_chunk.sections),
            }
        )
        archive_paths.append(archive_path)

    results = pd.DataFrame(rows)
    results.to_csv(
        PACKAGE_OUT / "multimodal_plumbing_results.csv",
        index=False,
    )

    # Permission test.
    permission_blocked = False
    permission_message = ""
    protected_chunk = CognitiveChunkV2()
    try:
        ChunkWriter(
            protected_chunk,
            "LanguageProcessing",
        ).append(
            "observations",
            None,
        )
    except WritePermissionError as error:
        permission_blocked = True
        permission_message = str(error)

    # Contradiction-producing merge test.
    left = CognitiveChunkV2()
    right = CognitiveChunkV2()
    ChunkWriter(left, "ReasoningPlanning").append(
        "claims",
        ClaimRecord(
            scope="damage_state",
            value="intact",
            status=ClaimStatus.SUPPORTED,
            created_by="ReasoningPlanning",
            confidence=0.76,
        ),
    )
    ChunkWriter(right, "ReasoningPlanning").append(
        "claims",
        ClaimRecord(
            scope="damage_state",
            value="cracked",
            status=ClaimStatus.SUPPORTED,
            created_by="ReasoningPlanning",
            confidence=0.71,
        ),
    )
    left.merge_from(right)

    # Future-video schema test only.
    future_video_segment = TemporalSegmentRecord(
        parent_payload_id="future_video_payload",
        start_ms=12_000,
        end_ms=14_500,
        track=TemporalTrack.AUDIOVISUAL,
        selected_by="FutureVideoAttentionPolicy",
        selection_reason="high novelty and causal relevance",
        constraint_tags=["duration<=3000ms", "budgeted_storage"],
    )
    serialized_video_contract = json.loads(
        future_video_segment.model_dump_json()
    )

    diagnostics = {
        "permission_test": {
            "unauthorized_observation_write_blocked": permission_blocked,
            "message": permission_message,
        },
        "merge_test": {
            "claims_after_merge": len(left.claims),
            "contradictions_after_merge": len(left.contradictions),
            "contradiction_scope": (
                left.contradictions[0].scope
                if left.contradictions
                else None
            ),
        },
        "video_ready_contract_test": serialized_video_contract,
        "archives": [str(path) for path in archive_paths],
    }
    (
        PACKAGE_OUT / "plumbing_diagnostics.json"
    ).write_text(
        json.dumps(diagnostics, indent=2),
        encoding="utf-8",
    )

    print(results.to_string(index=False))
    print()
    print(json.dumps(diagnostics, indent=2))


if __name__ == "__main__":
    main()
