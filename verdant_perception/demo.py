from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from PIL import Image

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_media import ImportOptions, VerdantMediaGateway
from verdant_objects import VerdantObjectPipeline
from verdant_perception import VerdantPerceptionPipeline


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
MEDIA_DIR = ARTIFACTS / "milestone_11_user_media"
CHECKPOINT = ARTIFACTS / "milestone_11_media_perception_demo.vdk"
SUMMARY = ARTIFACTS / "milestone_11_media_perception_summary.json"
REPORTS = ARTIFACTS / "milestone_11_media_perception_reports.json"
RUN_PACKAGE = ARTIFACTS / "milestone_11_demo_run.vrun.zip"


def make_image(path: Path) -> None:
    frame = np.zeros((72, 96, 3), dtype=np.uint8)
    frame[20:50, 30:64] = (215, 215, 215)
    Image.fromarray(frame).save(path)


def make_audio(path: Path) -> None:
    rate = 8000
    time = np.arange(rate, dtype=np.float64) / rate
    wave = 0.28 * np.sin(2 * np.pi * 330 * time)
    wave += 0.12 * np.sin(2 * np.pi * 660 * time)
    sf.write(path, wave.astype(np.float32), rate, subtype="PCM_16")


def make_video(
    path: Path,
    *,
    frames: int,
    brightness: int,
    size: int,
    occluded: set[int] | None = None,
) -> None:
    occluded = occluded or set()
    writer = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 5.0, (96, 72)
    )
    if not writer.isOpened():
        raise RuntimeError("OpenCV could not create the demonstration MP4.")
    for index in range(frames):
        frame = np.zeros((72, 96, 3), dtype=np.uint8)
        if index not in occluded:
            x = 6 + index * 6
            value = min(250, brightness + (index % 3) * 4)
            frame[24 : 24 + size, x : x + size] = value
        writer.write(frame)
    writer.release()


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    image_path = MEDIA_DIR / "chosen_image.png"
    audio_path = MEDIA_DIR / "chosen_audio.wav"
    clip_one = MEDIA_DIR / "chosen_clip_one.mp4"
    clip_two = MEDIA_DIR / "chosen_clip_two.mp4"
    unknown = MEDIA_DIR / "chosen_unknown.bin"
    make_image(image_path)
    make_audio(audio_path)
    make_video(clip_one, frames=9, brightness=205, size=14, occluded={3, 4})
    make_video(clip_two, frames=7, brightness=210, size=15)
    unknown.write_bytes(b"user selected opaque file\x00\x01\xff")

    kernel = VerdantKernel(seed=1111, state_dim=64, run_label="milestone-11-demo")
    kernel.update_sensory_policy(
        feature_change_threshold=1.0,
        maximum_event_gap_ns=300_000_000,
        minimum_modalities_per_group=1,
    )
    kernel.update_object_policy(transformation_novelty_distance=0.01)
    gateway = VerdantMediaGateway()
    perception = VerdantPerceptionPipeline()
    options = ImportOptions(video_fps=5.0, include_video_audio=False)

    import_results = []
    perceptual_reports = []
    archive_paths = {}
    for path in (image_path, audio_path, clip_one, clip_two, unknown):
        result = gateway.import_path(
            kernel,
            path,
            output_dir=ARTIFACTS / "milestone_11_imported",
            options=options,
        )
        import_results.append(result)
        if result.sensory_result is None:
            continue
        archive_paths[result.sensory_result.archive.archive_id] = result.sensory_result.archive_path
        if any(item.modality.value == "vision" for item in result.sensory_result.samples):
            bound = perception.process(
                kernel,
                result.temporal_event_ids,
                archive_paths,
            )
            perceptual_reports.append(bound.report)

    # The still image creates its own insufficient candidate. The two clips form
    # a second candidate with recurrence, transformation, occlusion, and reappearance.
    candidates = sorted(
        kernel.state.object_candidates.values(),
        key=lambda item: (-item.visible_observation_count, item.candidate_id),
    )
    developed = candidates[0]
    object_pipeline = VerdantObjectPipeline()
    promotion_report = object_pipeline.inspect_promotion(kernel, developed.candidate_id)
    promotion = object_pipeline.promote(kernel, developed.candidate_id)
    promoted_concept = kernel.state.concepts[promotion.promotion_event.concept_id]

    checkpoint_sha256 = save_checkpoint(CHECKPOINT, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(CHECKPOINT))
    exact_reload = restored.snapshot() == kernel.snapshot()

    companions = []
    for result in import_results:
        companions.append(result.media_archive.archive_path)
        if result.sensory_archive_path is not None:
            companions.append(result.sensory_archive_path)
    run_package = gateway.write_run_package(
        kernel,
        RUN_PACKAGE,
        companion_paths=companions,
        metadata={"milestone": 11, "user_media_demo": True},
    )
    inspected = gateway.load_run(RUN_PACKAGE, mode="inspect")
    branch = gateway.load_run(
        RUN_PACKAGE,
        mode="branch",
        branch_label="milestone-11-demo-branch",
    )

    summary = {
        "milestone": 11,
        "title": "User Media Import and Native Perceptual Binding",
        "llm_in_loop": False,
        "pretrained_detector_in_loop": False,
        "user_file_gateway": {
            "source_files": [str(path) for path in (image_path, audio_path, clip_one, clip_two, unknown)],
            "import_count": len(import_results),
            "translated_count": sum(item.translated for item in import_results),
            "archive_only_or_unsupported_count": sum(not item.translated for item in import_results),
            "media_import_archives": [str(item.media_archive.archive_path) for item in import_results],
            "sensory_archives": [
                str(item.sensory_archive_path)
                for item in import_results
                if item.sensory_archive_path is not None
            ],
        },
        "native_media": {
            "sensory_sample_count": len(kernel.state.sensory_samples),
            "temporal_event_count": len(kernel.state.temporal_events),
            "vision_sample_count": sum(item.modality.value == "vision" for item in kernel.state.sensory_samples.values()),
            "audio_sample_count": sum(item.modality.value == "audio" for item in kernel.state.sensory_samples.values()),
        },
        "perception": {
            "binding_event_count": len(kernel.state.perceptual_binding_events),
            "frame_count": sum(len(item.frames) for item in perceptual_reports),
            "region_count": sum(
                len(frame.region_proposals)
                for report in perceptual_reports
                for frame in report.frames
            ),
            "object_candidate_count": len(kernel.state.object_candidates),
            "developed_candidate": {
                "candidate_id": developed.candidate_id,
                "visible_observation_count": developed.visible_observation_count,
                "episode_count": len(developed.episode_ids),
                "persistence_count": developed.persistence_count,
                "transformation_count": developed.transformation_count,
                "common_motion_count": developed.common_motion_count,
                "occlusion_count": developed.occlusion_count,
                "reappearance_count": developed.reappearance_count,
                "support_score": developed.support_score,
            },
        },
        "promotion": {
            "disposition": promotion_report.disposition.value,
            "rejection_codes": list(promotion_report.rejection_codes),
            "council_disposition": promotion.council_decision.report.disposition.value,
            "concept_id": promoted_concept.concept_id,
            "machine_generated_label": promoted_concept.label,
            "semantic_category_preinstalled": promoted_concept.attributes["semantic_category_preinstalled"],
        },
        "semantic_boundary": {
            "concepts_after_tracking_before_promotion": 0,
            "concepts_after_governed_promotion": len(kernel.state.concepts),
            "relations": len(kernel.state.relations),
            "claims": len(kernel.state.claims),
            "contradictions": len(kernel.state.contradictions),
        },
        "persistence": {
            "checkpoint": str(CHECKPOINT),
            "checkpoint_sha256": checkpoint_sha256,
            "exact_checkpoint_reload": exact_reload,
            "run_package": str(RUN_PACKAGE),
            "run_package_id": run_package.package_id,
            "run_package_inspection_matches": inspected.inspection.state == kernel.snapshot(),
            "branch_preserves_historical_kernel_id": branch.kernel.state.identity.kernel_id == kernel.state.identity.kernel_id,
            "branch_id": branch.kernel.state.lineage.branch_id,
            "branch_label": branch.kernel.state.lineage.branch_label,
            "branch_generation": branch.kernel.state.lineage.generation,
        },
        "metrics": kernel.metrics(),
        "important_boundaries": [
            "Original user files are preserved before decoding.",
            "Decoded samples are stored separately from original files.",
            "Unsupported files are preserved without fabricated interpretation.",
            "A still image cannot provide invented motion or persistence.",
            "Perceptual regions remain nonsemantic until the existing Council-authorized objecthood path promotes a candidate.",
        ],
    }
    reports = {
        "imports": [
            {
                "source_path": str(item.source_path),
                "media_kind": item.media_kind,
                "mime_type": item.mime_type,
                "media_archive": {
                    "import_id": item.media_archive.import_id,
                    "path": str(item.media_archive.archive_path),
                    "source_sha256": item.media_archive.source_sha256,
                    "archive_sha256": item.media_archive.archive_sha256,
                },
                "translated": item.translated,
                "translation_status": item.translation_status,
                "sensory_archive_path": str(item.sensory_archive_path) if item.sensory_archive_path else None,
                "temporal_event_ids": list(item.temporal_event_ids),
                "metadata": item.metadata,
                "notes": list(item.notes),
            }
            for item in import_results
        ],
        "perceptual_reports": [item.model_dump(mode="json") for item in perceptual_reports],
        "promotion_report": promotion_report.model_dump(mode="json"),
        "council_report": promotion.council_decision.report.model_dump(mode="json"),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORTS.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
