from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from verdant_kernel import (
    NativeModality,
    SensoryIntegrityError,
    SensoryStaleError,
    TemporalBoundaryReason,
    TemporalEventAssemblyReport,
    VerdantKernel,
    WorkspaceCandidateInput,
    WorkspaceIntegrityError,
    WorkspaceSignals,
    WorkspaceSourceKind,
    load_checkpoint,
    save_checkpoint,
)
from verdant_sensory import (
    NativeSamplePacket,
    SensoryArchiveIntegrityError,
    VerdantSensoryPipeline,
    verify_archive,
)
from verdant_workspace import VerdantWorkspacePipeline


def vision_payload(offset: int, *, inverse: bool = False) -> bytes:
    frame = np.zeros((16, 16), dtype=np.uint8)
    frame[4:10, offset : offset + 5] = 220
    frame += np.arange(16, dtype=np.uint8)[None, :] * 2
    if inverse:
        frame = 255 - frame
    return frame.tobytes()


def audio_payload(frequency: float, *, amplitude: float = 0.4) -> bytes:
    rate = 8000
    time = np.arange(160, dtype=np.float64) / rate
    wave = np.sin(2.0 * np.pi * frequency * time) * amplitude
    pcm = np.asarray(np.clip(wave, -1.0, 1.0) * 32767.0, dtype="<i2")
    return pcm.tobytes()





def packets(*, change_only: bool = False, modalities: int = 2) -> tuple[NativeSamplePacket, ...]:
    if modalities not in (1, 2):
        raise ValueError("The active sensory test fixture supports vision and audio only.")
    base = 1_000_000_000
    group_times = (
        [0, 80_000_000, 160_000_000, 240_000_000, 320_000_000, 400_000_000]
        if change_only
        else [0, 80_000_000, 160_000_000, 520_000_000, 600_000_000, 680_000_000]
    )
    result: list[NativeSamplePacket] = []
    for sequence, relative in enumerate(group_times):
        changed = change_only and sequence >= 3
        result.append(
            NativeSamplePacket(
                stream_id="camera-main",
                sequence_number=sequence,
                timestamp_ns=base + relative,
                modality=NativeModality.VISION,
                media_type="application/x-raw-gray8",
                payload=vision_payload((sequence % 4) + 1, inverse=changed),
                shape=(16, 16),
            )
        )
        if modalities == 2:
            result.append(
                NativeSamplePacket(
                    stream_id="audio-main",
                    sequence_number=sequence,
                    timestamp_ns=base + relative + 10_000_000,
                    modality=NativeModality.AUDIO,
                    media_type="audio/L16",
                    payload=audio_payload(240.0 if not changed else 760.0),
                    sample_rate_hz=8000,
                )
            )
    return tuple(result)

def build_batch(tmp_path: Path, *, seed: int = 1001, change_only: bool = False, modalities: int = 2):
    kernel = VerdantKernel(seed=seed, state_dim=64, run_label=f"sensory-{seed}")
    pipeline = VerdantSensoryPipeline()
    result = pipeline.ingest_batch(
        kernel,
        packets(change_only=change_only, modalities=modalities),
        batch_key="controlled-native-stream",
        archive_path=tmp_path / "native_stream.vsa.zip",
    )
    return kernel, pipeline, result


def test_native_archive_preserves_exact_payload_bytes(tmp_path: Path) -> None:
    supplied = packets()
    kernel, _, result = build_batch(tmp_path)
    verified = verify_archive(result.archive_path)
    assert verified.archive_sha256 == result.archive.archive_sha256
    assert verified.sample_ids == result.archive.sample_ids
    assert len(kernel.state.sensory_archives) == 1
    assert len(result.samples) == len(supplied)


def test_native_archive_tampering_is_detected(tmp_path: Path) -> None:
    _, _, result = build_batch(tmp_path)
    damaged = tmp_path / "damaged.vsa.zip"
    with zipfile.ZipFile(result.archive_path, "r") as source:
        members = {name: source.read(name) for name in source.namelist()}
    payload_name = next(name for name in members if name.startswith("samples/"))
    payload = bytearray(members[payload_name])
    payload[0] ^= 0x01
    members[payload_name] = bytes(payload)
    with zipfile.ZipFile(damaged, "w", compression=zipfile.ZIP_STORED) as target:
        for name, data in members.items():
            target.writestr(name, data)
    with pytest.raises(SensoryArchiveIntegrityError):
        verify_archive(damaged)


def test_nonsemantic_translation_creates_no_concepts_claims_or_relations(tmp_path: Path) -> None:
    kernel, _, result = build_batch(tmp_path)
    assert len(result.samples) == 12
    assert kernel.state.concepts == {}
    assert kernel.state.relations == {}
    assert kernel.state.claims == {}
    assert kernel.state.contradictions == {}
    assert all(item.metadata["semantic_categories_supplied"] is False for item in result.samples)


def test_two_modalities_synchronize_with_exact_skew(tmp_path: Path) -> None:
    kernel, _, _ = build_batch(tmp_path)
    groups = sorted(kernel.state.synchronization_groups.values(), key=lambda item: item.anchor_timestamp_ns)
    assert len(groups) == 6
    assert all(group.complete for group in groups)
    assert all(len(group.modalities) == 2 for group in groups)
    assert all(group.maximum_skew_ns == 10_000_000 for group in groups)


def test_time_gap_creates_two_temporal_events(tmp_path: Path) -> None:
    kernel, _, _ = build_batch(tmp_path)
    events = sorted(kernel.state.temporal_events.values(), key=lambda item: item.start_timestamp_ns)
    assert len(events) == 2
    assert events[0].boundary_reason == TemporalBoundaryReason.TIME_GAP
    assert events[1].boundary_reason == TemporalBoundaryReason.STREAM_END
    assert all(len(event.synchronization_group_ids) == 3 for event in events)


def test_feature_change_can_create_event_boundary_without_time_gap(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1002, state_dim=64, run_label="feature-boundary")
    kernel.update_sensory_policy(feature_change_threshold=0.05)
    result = VerdantSensoryPipeline().ingest_batch(
        kernel,
        packets(change_only=True),
        batch_key="change-only",
        archive_path=tmp_path / "change.vsa.zip",
    )
    events = sorted(kernel.state.temporal_events.values(), key=lambda item: item.start_timestamp_ns)
    assert len(events) >= 2
    assert any(event.boundary_reason == TemporalBoundaryReason.FEATURE_CHANGE for event in events[:-1])
    assert result.assembly_event.semantic_mutation_permitted is False


def test_sample_evidence_points_to_exact_native_payload(tmp_path: Path) -> None:
    kernel, _, result = build_batch(tmp_path)
    sample = result.samples[0]
    evidence = kernel.state.evidence[sample.observation_evidence_id]
    assert evidence.payload_sha256 == sample.payload_sha256
    assert evidence.source_ref == f"sensory://{sample.archive_id}/{sample.archive_member_path}"
    assert sample.payload_sha256 == hashlib.sha256(packets()[0].payload).hexdigest()


def test_temporal_inspection_is_pure(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1003, state_dim=64, run_label="pure-sensory-inspection")
    pipeline = VerdantSensoryPipeline()
    ingestion = pipeline.ingest_samples(
        kernel,
        packets(),
        batch_key="pure-inspection",
        archive_path=tmp_path / "pure.vsa.zip",
    )
    before = kernel.snapshot()
    report = pipeline.inspect_temporal_events(kernel, tuple(item.sample_id for item in ingestion.samples))
    assert report.proposed_events
    assert kernel.snapshot() == before


def test_temporal_report_becomes_stale_after_policy_change(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1004, state_dim=64, run_label="stale-sensory")
    pipeline = VerdantSensoryPipeline()
    ingestion = pipeline.ingest_samples(
        kernel,
        packets(),
        batch_key="stale-inspection",
        archive_path=tmp_path / "stale.vsa.zip",
    )
    report = pipeline.inspect_temporal_events(kernel, tuple(item.sample_id for item in ingestion.samples))
    kernel.update_sensory_policy(feature_change_threshold=0.3)
    with pytest.raises(SensoryStaleError):
        pipeline.commit_temporal_events(kernel, report)


def test_tampered_temporal_report_is_rejected(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1005, state_dim=64, run_label="tampered-sensory")
    pipeline = VerdantSensoryPipeline()
    ingestion = pipeline.ingest_samples(
        kernel,
        packets(),
        batch_key="tampered-inspection",
        archive_path=tmp_path / "tampered.vsa.zip",
    )
    report = pipeline.inspect_temporal_events(kernel, tuple(item.sample_id for item in ingestion.samples))
    tampered = report.model_copy(update={"operation": "assemble_temporal_events:tampered"})
    with pytest.raises(SensoryIntegrityError):
        pipeline.commit_temporal_events(kernel, tampered)


def test_stream_sequence_rollback_is_rejected(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1006, state_dim=64, run_label="sensory-sequence")
    pipeline = VerdantSensoryPipeline()
    first = packets()[:3]
    pipeline.ingest_samples(
        kernel,
        first,
        batch_key="first-stream",
        archive_path=tmp_path / "first.vsa.zip",
    )
    rollback = (
        NativeSamplePacket(
            stream_id="camera-main",
            sequence_number=0,
            timestamp_ns=2_000_000_000,
            modality=NativeModality.VISION,
            media_type="application/x-raw-gray8",
            payload=vision_payload(2),
            shape=(16, 16),
        ),
    )
    before = kernel.snapshot()
    with pytest.raises(SensoryIntegrityError):
        pipeline.ingest_samples(
            kernel,
            rollback,
            batch_key="rollback-stream",
            archive_path=tmp_path / "rollback.vsa.zip",
        )
    assert kernel.snapshot() == before
    assert not (tmp_path / "rollback.vsa.zip").exists()


def test_temporal_event_can_enter_workspace_with_native_lineage(tmp_path: Path) -> None:
    kernel, _, _ = build_batch(tmp_path)
    event = sorted(kernel.state.temporal_events.values(), key=lambda item: item.start_timestamp_ns)[-1]
    candidate = WorkspaceCandidateInput(
        source_kind=WorkspaceSourceKind.TEMPORAL_EVENT,
        source_ref=event.event_id,
        label="latest synchronized native event",
        evidence_refs=event.evidence_refs,
        resource_request=0.30,
        persistence_cycles=2,
        signals=WorkspaceSignals(
            evidence_grounding=1.0,
            relevance=0.9,
            prediction_error=0.4,
            novelty=0.7,
        ),
    )
    result = VerdantWorkspacePipeline().run_cycle(kernel, (candidate,))
    assert result.event.active_item_ids
    active = next(iter(kernel.state.workspace_items.values()))
    assert active.source_kind == WorkspaceSourceKind.TEMPORAL_EVENT
    assert active.source_ref == event.event_id


def test_workspace_rejects_temporal_event_with_unrelated_evidence(tmp_path: Path) -> None:
    kernel, _, _ = build_batch(tmp_path)
    events = sorted(kernel.state.temporal_events.values(), key=lambda item: item.start_timestamp_ns)
    first, second = events
    candidate = WorkspaceCandidateInput(
        source_kind=WorkspaceSourceKind.TEMPORAL_EVENT,
        source_ref=first.event_id,
        label="forged temporal lineage",
        evidence_refs=(second.evidence_refs[0],),
        resource_request=0.20,
        signals=WorkspaceSignals(evidence_grounding=1.0, relevance=1.0),
    )
    with pytest.raises(WorkspaceIntegrityError):
        VerdantWorkspacePipeline().inspect(kernel, (candidate,))


def test_checkpoint_roundtrip_preserves_native_event_memory(tmp_path: Path) -> None:
    kernel, _, _ = build_batch(tmp_path)
    checkpoint = tmp_path / "sensory.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    assert restored.snapshot() == kernel.snapshot()
    assert restored.state.identity.schema_version == "1.0.0-alpha"


def test_deterministic_replay_produces_identical_kernel_state(tmp_path: Path) -> None:
    left = VerdantKernel(seed=1007, state_dim=64, run_label="sensory-replay")
    right = VerdantKernel(seed=1007, state_dim=64, run_label="sensory-replay")
    pipeline = VerdantSensoryPipeline()
    pipeline.ingest_batch(
        left,
        packets(),
        batch_key="replay-batch",
        archive_path=tmp_path / "left.vsa.zip",
    )
    pipeline.ingest_batch(
        right,
        packets(),
        batch_key="replay-batch",
        archive_path=tmp_path / "right.vsa.zip",
    )
    assert left.snapshot() == right.snapshot()
    assert (tmp_path / "left.vsa.zip").read_bytes() == (tmp_path / "right.vsa.zip").read_bytes()


def test_incomplete_multimodal_group_is_preserved_not_invented(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=1008, state_dim=64, run_label="incomplete-group")
    kernel.update_sensory_policy(minimum_modalities_per_group=2)
    VerdantSensoryPipeline().ingest_batch(
        kernel,
        packets(modalities=1),
        batch_key="two-modalities",
        archive_path=tmp_path / "two-modalities.vsa.zip",
    )
    assert kernel.state.synchronization_groups
    assert all(not item.complete for item in kernel.state.synchronization_groups.values())
    assert all(len(item.modalities) == 1 for item in kernel.state.synchronization_groups.values())


def test_samples_cannot_be_assembled_into_two_events(tmp_path: Path) -> None:
    kernel, pipeline, result = build_batch(tmp_path)
    sample_ids = tuple(item.sample_id for item in result.samples)
    with pytest.raises(SensoryIntegrityError):
        pipeline.inspect_temporal_events(kernel, sample_ids)
