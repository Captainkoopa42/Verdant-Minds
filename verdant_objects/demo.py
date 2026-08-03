from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_kernel import (
    ExperienceCommand,
    ObjectObservationInput,
    ObjectObservationKind,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_objects import VerdantObjectPipeline


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
CHECKPOINT_PATH = ARTIFACT_DIR / "milestone_7_objects_demo.vdk"
SUMMARY_PATH = ARTIFACT_DIR / "milestone_7_objects_summary.json"
REPORTS_PATH = ARTIFACT_DIR / "milestone_7_object_reports.json"


def native_evidence(
    kernel: VerdantKernel,
    *,
    key: str,
    episode: str,
    frame: int,
    features: tuple[float, ...],
) -> str:
    payload = f"native:{episode}:{frame}:{features}"
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"native-sensor:{key}",
            modality="vision_native",
            payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
            feature_vector=features,
            semantic_evidence_details={
                "object_identity_label_supplied": False,
            },
            metadata={
                "episode": episode,
                "frame": frame,
                "semantic_category_preinstalled": False,
            },
        )
    )
    return result.observation_evidence_id


def visible(
    kernel: VerdantKernel,
    objects: VerdantObjectPipeline,
    reports: list[dict],
    *,
    key: str,
    episode: str,
    frame: int,
    appearance: tuple[float, ...],
    position: tuple[float, float],
    motion: tuple[float, float],
    common: bool = False,
):
    evidence = native_evidence(
        kernel,
        key=key,
        episode=episode,
        frame=frame,
        features=appearance,
    )
    result = objects.observe(
        kernel,
        ObjectObservationInput(
            episode_id=episode,
            frame_index=frame,
            evidence_ref=evidence,
            modality="vision_native",
            kind=ObjectObservationKind.VISIBLE,
            appearance_features=appearance,
            position=position,
            motion=motion,
            common_motion_supported=common,
            metadata={
                "human_object_label": None,
                "controlled_numeric_features": True,
            },
        ),
    )
    reports.append(result.report.model_dump(mode="json"))
    return result


def target_update(
    kernel: VerdantKernel,
    objects: VerdantObjectPipeline,
    reports: list[dict],
    *,
    key: str,
    episode: str,
    frame: int,
    candidate_id: str,
    kind: ObjectObservationKind,
):
    evidence = native_evidence(
        kernel,
        key=key,
        episode=episode,
        frame=frame,
        features=(0.0, 0.0, 0.0, 0.0),
    )
    result = objects.observe(
        kernel,
        ObjectObservationInput(
            episode_id=episode,
            frame_index=frame,
            evidence_ref=evidence,
            modality="vision_native",
            kind=kind,
            target_candidate_id=candidate_id,
            metadata={
                "visibility": "temporarily_absent",
            },
        ),
    )
    reports.append(result.report.model_dump(mode="json"))
    return result


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=707, state_dim=64, run_label="milestone-7-demo")
    objects = VerdantObjectPipeline()
    reports: list[dict] = []

    first = visible(
        kernel,
        objects,
        reports,
        key="a-e1-f0",
        episode="episode-1",
        frame=0,
        appearance=(0.20, 0.40, 0.60, 0.80),
        position=(0.0, 0.0),
        motion=(0.1, 0.0),
    )
    candidate_a = first.event.candidate_id

    visible(
        kernel,
        objects,
        reports,
        key="a-e1-f1",
        episode="episode-1",
        frame=1,
        appearance=(0.30, 0.35, 0.65, 0.75),
        position=(0.1, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        objects,
        reports,
        key="a-e1-f2",
        episode="episode-1",
        frame=2,
        appearance=(0.12, 0.48, 0.52, 0.88),
        position=(0.2, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    target_update(
        kernel,
        objects,
        reports,
        key="a-e1-f3-occluded",
        episode="episode-1",
        frame=3,
        candidate_id=candidate_a,
        kind=ObjectObservationKind.OCCLUSION,
    )
    visible(
        kernel,
        objects,
        reports,
        key="a-e1-f4-reappear",
        episode="episode-1",
        frame=4,
        appearance=(0.32, 0.32, 0.68, 0.72),
        position=(0.4, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        objects,
        reports,
        key="a-e2-f0",
        episode="episode-2",
        frame=0,
        appearance=(0.24, 0.38, 0.62, 0.78),
        position=(0.0, 0.2),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        objects,
        reports,
        key="a-e2-f1",
        episode="episode-2",
        frame=1,
        appearance=(0.14, 0.47, 0.53, 0.87),
        position=(0.1, 0.2),
        motion=(0.1, 0.0),
        common=True,
    )
    # Similar appearance, incompatible position and motion: a separate candidate.
    lookalike = visible(
        kernel,
        objects,
        reports,
        key="b-e2-f2",
        episode="episode-2",
        frame=2,
        appearance=(0.22, 0.39, 0.61, 0.79),
        position=(2.0, 0.2),
        motion=(-0.1, 0.0),
    )
    candidate_b = lookalike.event.candidate_id


    semantic_before = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    promotion_report = objects.inspect_promotion(kernel, candidate_a)
    promotion = objects.promote(kernel, candidate_a)
    semantic_after = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }

    save_checkpoint(CHECKPOINT_PATH, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(CHECKPOINT_PATH))
    exact_reload = restored.snapshot() == kernel.snapshot()

    a = kernel.state.object_candidates[candidate_a]
    b = kernel.state.object_candidates[candidate_b]
    concept = kernel.state.concepts[promotion.promotion_event.concept_id]
    summary = {
        "milestone": 7,
        "title": "Earned Proto-Object Formation",
        "llm_in_loop": False,
        "pretrained_vision_model_in_loop": False,
        "sensory_input": "controlled native numerical feature observations",
        "human_object_identity_labels_supplied": False,
        "metrics": kernel.metrics(),
        "candidate_a": {
            "candidate_id": candidate_a,
            "status": a.status.value,
            "visible_observation_count": a.visible_observation_count,
            "episode_count": len(a.episode_ids),
            "persistence_count": a.persistence_count,
            "transformation_count": a.transformation_count,
            "common_motion_count": a.common_motion_count,
            "occlusion_count": a.occlusion_count,
            "reappearance_count": a.reappearance_count,
            "support_score": a.support_score,
            "support_components": a.support_components.model_dump(mode="json"),
            "evidence_count": len(a.evidence_refs),
            "promoted_concept_id": a.promoted_concept_id,
        },
        "lookalike_candidate": {
            "candidate_id": candidate_b,
            "separate_from_a": candidate_b != candidate_a,
            "status": b.status.value,
            "visible_observation_count": b.visible_observation_count,
            "candidate_a_recorded_as_competitor": candidate_a in b.competing_candidate_ids,
        },
        "promotion": {
            "disposition": promotion_report.disposition.value,
            "rejection_codes": list(promotion_report.rejection_codes),
            "council_disposition": promotion.council_decision.report.disposition.value,
            "concept_id": concept.concept_id,
            "machine_generated_label": concept.label,
            "concept_type": concept.attributes["concept_type"],
            "semantic_category_preinstalled": concept.attributes[
                "semantic_category_preinstalled"
            ],
            "full_evidence_lineage_preserved": set(concept.evidence_refs) == set(a.evidence_refs),
        },
        "semantic_counts_before_promotion": semantic_before,
        "semantic_counts_after_promotion": semantic_after,
        "tracking_created_semantic_truth": semantic_before != {"concepts": 0, "relations": 0, "claims": 0},
        "exact_checkpoint_reload": exact_reload,
        "object_policy": kernel.state.object_policy.model_dump(mode="json"),
        "important_boundary": (
            "This milestone uses controlled numerical observations. It does not yet "
            "decode raw camera video or autonomously learn the sensory translator."
        ),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORTS_PATH.write_text(
        json.dumps(
            {
                "observation_reports": reports,
                "promotion_report": promotion_report.model_dump(mode="json"),
                "council_report": promotion.council_decision.report.model_dump(mode="json"),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
