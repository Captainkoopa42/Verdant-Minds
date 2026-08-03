from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from verdant_kernel import (
    NativeModality,
    VerdantKernel,
    WorkspaceCandidateInput,
    WorkspaceSignals,
    WorkspaceSourceKind,
    load_checkpoint,
    save_checkpoint,
)
from verdant_workspace import VerdantWorkspacePipeline

from .archive import verify_archive
from .pipeline import NativeSamplePacket, VerdantSensoryPipeline


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
ARCHIVE_PATH = ARTIFACT_DIR / "milestone_10_native_stream.vsa.zip"
CHECKPOINT_PATH = ARTIFACT_DIR / "milestone_10_sensory_demo.vdk"
SUMMARY_PATH = ARTIFACT_DIR / "milestone_10_sensory_summary.json"
REPORTS_PATH = ARTIFACT_DIR / "milestone_10_sensory_reports.json"


def _vision_frame(index: int, changed: bool) -> bytes:
    frame = np.zeros((24, 32), dtype=np.uint8)
    frame += np.arange(32, dtype=np.uint8)[None, :]
    left = 3 + index
    frame[8:17, left : left + 7] = 210
    if changed:
        frame[2:9, 21:29] = 245
        frame[8:17, left : left + 7] = 45
    return frame.tobytes()


def _audio_packet(frequency: float, amplitude: float) -> bytes:
    rate = 8000
    t = np.arange(240, dtype=np.float64) / rate
    wave = np.sin(2.0 * np.pi * frequency * t) * amplitude
    return np.asarray(np.clip(wave, -1.0, 1.0) * 32767.0, dtype="<i2").tobytes()




def make_packets() -> tuple[NativeSamplePacket, ...]:
    base = 10_000_000_000
    group_times = [0, 80_000_000, 160_000_000, 240_000_000, 620_000_000, 700_000_000, 780_000_000, 860_000_000]
    packets: list[NativeSamplePacket] = []
    for sequence, relative in enumerate(group_times):
        changed = sequence >= 4
        packets.append(
            NativeSamplePacket(
                stream_id="camera-main",
                sequence_number=sequence,
                timestamp_ns=base + relative,
                modality=NativeModality.VISION,
                media_type="application/x-raw-gray8",
                payload=_vision_frame(sequence % 4, changed),
                shape=(24, 32),
                metadata={
                    "native_camera_frame": True,
                    "human_object_labels": False,
                },
            )
        )
        packets.append(
            NativeSamplePacket(
                stream_id="microphone-main",
                sequence_number=sequence,
                timestamp_ns=base + relative + 4_000_000,
                modality=NativeModality.AUDIO,
                media_type="audio/pcm;format=s16le",
                payload=_audio_packet(240.0 if not changed else 920.0, 0.25 if not changed else 0.55),
                shape=(240,),
                sample_rate_hz=8000,
                channel_names=("mono",),
                metadata={"native_pcm": True, "speech_recognition_used": False},
            )
        )
    return tuple(packets)


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=1010, state_dim=128, run_label="milestone-10-native-sensory")
    pipeline = VerdantSensoryPipeline()
    result = pipeline.ingest_batch(
        kernel,
        make_packets(),
        batch_key="milestone-10-controlled-native-stream",
        archive_path=ARCHIVE_PATH,
    )
    verified_archive = verify_archive(ARCHIVE_PATH)

    events = sorted(kernel.state.temporal_events.values(), key=lambda item: item.start_timestamp_ns)
    current_event = events[-1]
    workspace_candidate = WorkspaceCandidateInput(
        source_kind=WorkspaceSourceKind.TEMPORAL_EVENT,
        source_ref=current_event.event_id,
        label="latest synchronized native sensory event",
        evidence_refs=current_event.evidence_refs,
        resource_request=0.38,
        persistence_cycles=2,
        signals=WorkspaceSignals(
            evidence_grounding=1.0,
            relevance=0.95,
            prediction_error=min(1.0, current_event.maximum_change_score + 0.35),
            novelty=0.80,
        ),
        binding_refs=current_event.synchronization_group_ids,
        metadata={
            "native_payload_replay_available": True,
            "semantic_categories_supplied": False,
        },
    )
    workspace_result = VerdantWorkspacePipeline().run_cycle(kernel, (workspace_candidate,))

    save_checkpoint(CHECKPOINT_PATH, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(CHECKPOINT_PATH))
    exact_reload = restored.snapshot() == kernel.snapshot()

    modality_counts = {
        modality.value: sum(sample.modality == modality for sample in result.samples)
        for modality in NativeModality
    }
    translator_examples = {}
    for modality in NativeModality:
        sample = next(item for item in result.samples if item.modality == modality)
        translator_examples[modality.value] = {
            "sample_id": sample.sample_id,
            "payload_sha256": sample.payload_sha256,
            "payload_nbytes": sample.payload_nbytes,
            "feature_vector": sample.feature_vector,
            "signature_length": len(sample.native_signature),
            "delta_score": sample.delta_score,
            "translation_kind": sample.metadata["translation_kind"],
            "semantic_categories_supplied": sample.metadata["semantic_categories_supplied"],
        }

    summary = {
        "milestone": 10,
        "title": "Native Sensory Translation and Temporal Event Memory",
        "schema_version": kernel.state.identity.schema_version,
        "archive": {
            "archive_id": result.archive.archive_id,
            "archive_sha256": result.archive.archive_sha256,
            "verified_sha256": verified_archive.archive_sha256,
            "manifest_sha256": result.archive.manifest_sha256,
            "sample_count": len(result.archive.sample_ids),
            "native_payloads_preserved": True,
        },
        "sensory": {
            "sample_count": len(result.samples),
            "modality_counts": modality_counts,
            "synchronization_group_count": len(kernel.state.synchronization_groups),
            "complete_group_count": sum(item.complete for item in kernel.state.synchronization_groups.values()),
            "maximum_observed_clock_skew_ns": max(item.maximum_skew_ns for item in kernel.state.synchronization_groups.values()),
            "temporal_event_count": len(events),
            "event_boundaries": [item.boundary_reason.value for item in events],
            "translator_examples": translator_examples,
        },
        "events": [
            {
                "event_id": item.event_id,
                "start_timestamp_ns": item.start_timestamp_ns,
                "end_timestamp_ns": item.end_timestamp_ns,
                "sample_count": len(item.sample_ids),
                "group_count": len(item.synchronization_group_ids),
                "modalities": [modality.value for modality in item.modalities],
                "maximum_change_score": item.maximum_change_score,
                "boundary_reason": item.boundary_reason.value,
                "evidence_count": len(item.evidence_refs),
                "archive_ids": item.archive_ids,
            }
            for item in events
        ],
        "workspace": {
            "active_item_ids": workspace_result.event.active_item_ids,
            "broadcast_item_ids": workspace_result.event.broadcast_item_ids,
            "temporal_event_admitted": any(
                item.source_kind == WorkspaceSourceKind.TEMPORAL_EVENT
                for item in kernel.state.workspace_items.values()
            ),
            "allocated_resource": sum(item.allocated_resource for item in kernel.state.workspace_items.values()),
        },
        "semantic_boundary": {
            "concept_count": len(kernel.state.concepts),
            "relation_count": len(kernel.state.relations),
            "claim_count": len(kernel.state.claims),
            "contradiction_count": len(kernel.state.contradictions),
            "semantic_categories_supplied": False,
        },
        "kernel_metrics": kernel.metrics(),
        "exact_checkpoint_reload": exact_reload,
    }
    reports = {
        "archive_record": result.archive.model_dump(mode="json"),
        "sample_records": [item.model_dump(mode="json") for item in result.samples],
        "temporal_event_report": result.report.model_dump(mode="json"),
        "temporal_event_assembly": result.assembly_event.model_dump(mode="json"),
        "workspace_report": workspace_result.report.model_dump(mode="json"),
        "workspace_event": workspace_result.event.model_dump(mode="json"),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORTS_PATH.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
