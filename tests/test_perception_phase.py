from __future__ import annotations

import cv2
import numpy as np
import pytest
from pathlib import Path

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_media import ImportOptions, VerdantMediaGateway
from verdant_objects import VerdantObjectPipeline
from verdant_perception import (
    PerceptualBindingReport,
    PerceptualIntegrityError,
    PerceptualStaleError,
    VerdantPerceptionPipeline,
)


def write_video(
    path: Path,
    *,
    frames: int = 10,
    fps: float = 5.0,
    occluded: set[int] | None = None,
    two_regions: bool = False,
    brightness: int = 220,
    size: int = 12,
) -> None:
    occluded = occluded or set()
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 64)
    )
    assert writer.isOpened()
    for index in range(frames):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        if index not in occluded:
            x = 4 + index * 4
            frame[18 : 18 + size, x : x + size] = brightness
        if two_regions:
            x2 = 48 - index * 3
            frame[38:48, x2 : x2 + 10] = 155
        writer.write(frame)
    writer.release()


def configured_kernel(seed: int, label: str) -> VerdantKernel:
    kernel = VerdantKernel(seed=seed, state_dim=64, run_label=label)
    kernel.update_sensory_policy(
        feature_change_threshold=1.0,
        maximum_event_gap_ns=300_000_000,
        minimum_modalities_per_group=1,
    )
    return kernel


def import_video(kernel: VerdantKernel, path: Path, output: Path):
    result = VerdantMediaGateway().import_path(
        kernel,
        path,
        output_dir=output,
        options=ImportOptions(video_fps=5.0, include_video_audio=False),
    )
    archive_paths = {
        result.sensory_result.archive.archive_id: result.sensory_result.archive_path
    }
    return result, archive_paths


def test_perceptual_inspection_is_pure(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1201, "perception-pure")
    result, archives = import_video(kernel, video, tmp_path / "out")
    before = kernel.snapshot()
    report = VerdantPerceptionPipeline().inspect(
        kernel, result.temporal_event_ids, archives
    )
    assert report.frames
    assert kernel.snapshot() == before


def test_moving_region_builds_one_persistent_unnamed_candidate(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video, frames=10)
    kernel = configured_kernel(1202, "perception-moving")
    result, archives = import_video(kernel, video, tmp_path / "out")
    bound = VerdantPerceptionPipeline().process(
        kernel, result.temporal_event_ids, archives
    )
    assert len(bound.report.frames) == 10
    assert all(len(frame.region_proposals) == 1 for frame in bound.report.frames)
    assert len(kernel.state.object_candidates) == 1
    candidate = next(iter(kernel.state.object_candidates.values()))
    assert candidate.visible_observation_count == 10
    assert candidate.persistence_count >= 8
    assert candidate.common_motion_count >= 8
    assert candidate.promoted_concept_id is None
    assert kernel.state.concepts == {}


def test_occlusion_and_reappearance_are_preserved(tmp_path: Path) -> None:
    video = tmp_path / "occlusion.mp4"
    write_video(video, frames=10, occluded={4, 5})
    kernel = configured_kernel(1203, "perception-occlusion")
    result, archives = import_video(kernel, video, tmp_path / "out")
    bound = VerdantPerceptionPipeline().process(
        kernel, result.temporal_event_ids, archives
    )
    candidate = next(iter(kernel.state.object_candidates.values()))
    assert candidate.occlusion_count == 1
    assert candidate.reappearance_count == 1
    assert len(bound.report.occlusion_bindings) == 1
    assert any(len(frame.region_proposals) == 0 for frame in bound.report.frames)


def test_two_lookalike_regions_remain_separate_candidates(tmp_path: Path) -> None:
    video = tmp_path / "two.mp4"
    write_video(video, frames=8, two_regions=True)
    kernel = configured_kernel(1204, "perception-two")
    result, archives = import_video(kernel, video, tmp_path / "out")
    VerdantPerceptionPipeline().process(kernel, result.temporal_event_ids, archives)
    assert len(kernel.state.object_candidates) == 2
    counts = sorted(item.visible_observation_count for item in kernel.state.object_candidates.values())
    assert counts == [8, 8]


def test_still_image_cannot_fake_temporal_objecthood(tmp_path: Path) -> None:
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    image[20:40, 18:38] = 220
    path = tmp_path / "still.png"
    cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    kernel = configured_kernel(1205, "perception-still")
    result = VerdantMediaGateway().import_path(kernel, path, output_dir=tmp_path / "out")
    archives = {
        result.sensory_result.archive.archive_id: result.sensory_result.archive_path
    }
    VerdantPerceptionPipeline().process(kernel, result.temporal_event_ids, archives)
    candidate = next(iter(kernel.state.object_candidates.values()))
    promotion = VerdantObjectPipeline().inspect_promotion(kernel, candidate.candidate_id)
    assert candidate.visible_observation_count == 1
    assert promotion.disposition.value == "defer"
    assert "insufficient_temporal_persistence" in promotion.rejection_codes
    assert "insufficient_recurrence" in promotion.rejection_codes


def test_perception_creates_no_concepts_relations_or_claims(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1206, "perception-semantic-boundary")
    result, archives = import_video(kernel, video, tmp_path / "out")
    VerdantPerceptionPipeline().process(kernel, result.temporal_event_ids, archives)
    assert kernel.state.concepts == {}
    assert kernel.state.relations == {}
    assert kernel.state.claims == {}
    assert kernel.state.contradictions == {}
    assert kernel.state.perceptual_binding_events[-1].semantic_mutation_permitted is False


def test_perceptual_report_becomes_stale_after_policy_change(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1207, "perception-stale")
    result, archives = import_video(kernel, video, tmp_path / "out")
    pipeline = VerdantPerceptionPipeline()
    report = pipeline.inspect(kernel, result.temporal_event_ids, archives)
    kernel.update_perceptual_policy(minimum_saliency_threshold=0.10)
    with pytest.raises(PerceptualStaleError):
        pipeline.commit(kernel, report, archives)


def test_tampered_perceptual_report_is_rejected(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1208, "perception-tamper")
    result, archives = import_video(kernel, video, tmp_path / "out")
    pipeline = VerdantPerceptionPipeline()
    report = pipeline.inspect(kernel, result.temporal_event_ids, archives)
    payload = report.model_dump(mode="json")
    payload["output_state_fingerprint"] = "0" * 64
    with pytest.raises((ValueError, PerceptualIntegrityError)):
        tampered = PerceptualBindingReport.model_validate(payload)
        pipeline.commit(kernel, tampered, archives)


def test_checkpoint_roundtrip_preserves_perceptual_lineage(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1209, "perception-checkpoint")
    result, archives = import_video(kernel, video, tmp_path / "out")
    VerdantPerceptionPipeline().process(kernel, result.temporal_event_ids, archives)
    checkpoint = tmp_path / "perception.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    assert restored.snapshot() == kernel.snapshot()
    assert restored.state.identity.schema_version == "1.0.0-alpha"
    assert len(restored.state.perceptual_binding_events) == 1


def test_perceptual_commit_is_atomic_when_archive_is_wrong(tmp_path: Path) -> None:
    video = tmp_path / "moving.mp4"
    write_video(video)
    kernel = configured_kernel(1210, "perception-atomic")
    result, archives = import_video(kernel, video, tmp_path / "out")
    pipeline = VerdantPerceptionPipeline()
    report = pipeline.inspect(kernel, result.temporal_event_ids, archives)
    before = kernel.snapshot()
    wrong = {next(iter(archives)): tmp_path / "missing.vsa.zip"}
    with pytest.raises((PerceptualIntegrityError, FileNotFoundError)):
        pipeline.commit(kernel, report, wrong)
    assert kernel.snapshot() == before


def test_two_native_clips_can_earn_council_governed_proto_object(tmp_path: Path) -> None:
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    write_video(first, frames=9, occluded={3, 4}, brightness=205, size=12)
    write_video(second, frames=7, brightness=210, size=13)
    kernel = configured_kernel(1211, "perception-native-promotion")
    kernel.update_object_policy(transformation_novelty_distance=0.01)
    gateway = VerdantMediaGateway()
    perception = VerdantPerceptionPipeline()
    archive_paths = {}
    for clip in (first, second):
        result = gateway.import_path(
            kernel,
            clip,
            output_dir=tmp_path / "out",
            options=ImportOptions(video_fps=5.0, include_video_audio=False),
        )
        archive_paths[result.sensory_result.archive.archive_id] = result.sensory_result.archive_path
        perception.process(kernel, result.temporal_event_ids, archive_paths)
    assert len(kernel.state.object_candidates) == 1
    candidate = next(iter(kernel.state.object_candidates.values()))
    assert len(candidate.episode_ids) == 2
    assert candidate.transformation_count >= 2
    assert candidate.reappearance_count >= 1
    promotion_report = VerdantObjectPipeline().inspect_promotion(kernel, candidate.candidate_id)
    assert promotion_report.disposition.value == "promote"
    promoted = VerdantObjectPipeline().promote(kernel, candidate.candidate_id)
    concept = kernel.state.concepts[promoted.promotion_event.concept_id]
    assert concept.attributes["concept_type"] == "earned_proto_object"
    assert concept.attributes["semantic_category_preinstalled"] is False
    assert concept.label.startswith("proto-object-")
