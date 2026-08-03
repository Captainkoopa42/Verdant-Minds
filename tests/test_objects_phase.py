from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    ObjectAuthorizationError,
    ObjectCandidateStatus,
    ObjectIntegrityError,
    ObjectObservationInput,
    ObjectObservationKind,
    ObjectPromotionDisposition,
    ObjectStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_objects import VerdantObjectPipeline


def sensory_evidence(
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
            payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),
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
    pipeline: VerdantObjectPipeline,
    *,
    key: str,
    episode: str,
    frame: int,
    appearance: tuple[float, ...],
    position: tuple[float, float],
    motion: tuple[float, float],
    common: bool = False,
):
    evidence = sensory_evidence(
        kernel,
        key=key,
        episode=episode,
        frame=frame,
        features=appearance,
    )
    return pipeline.observe(
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
            metadata={"human_object_label": None},
        ),
    )


def occlude(
    kernel: VerdantKernel,
    pipeline: VerdantObjectPipeline,
    *,
    key: str,
    episode: str,
    frame: int,
    candidate_id: str,
):
    evidence = sensory_evidence(
        kernel,
        key=key,
        episode=episode,
        frame=frame,
        features=(0.0, 0.0, 0.0, 0.0),
    )
    return pipeline.observe(
        kernel,
        ObjectObservationInput(
            episode_id=episode,
            frame_index=frame,
            evidence_ref=evidence,
            modality="vision_native",
            kind=ObjectObservationKind.OCCLUSION,
            target_candidate_id=candidate_id,
            metadata={"visibility": "temporarily_absent"},
        ),
    )




def build_eligible(seed: int = 707) -> tuple[VerdantKernel, VerdantObjectPipeline, str]:
    kernel = VerdantKernel(seed=seed, state_dim=64, run_label="object-tests")
    pipeline = VerdantObjectPipeline()
    first = visible(
        kernel,
        pipeline,
        key="e1-f0",
        episode="episode-1",
        frame=0,
        appearance=(0.20, 0.40, 0.60, 0.80),
        position=(0.0, 0.0),
        motion=(0.1, 0.0),
    )
    candidate_id = first.event.candidate_id
    visible(
        kernel,
        pipeline,
        key="e1-f1",
        episode="episode-1",
        frame=1,
        appearance=(0.30, 0.35, 0.65, 0.75),
        position=(0.1, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        pipeline,
        key="e1-f2",
        episode="episode-1",
        frame=2,
        appearance=(0.12, 0.48, 0.52, 0.88),
        position=(0.2, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    occlude(
        kernel,
        pipeline,
        key="e1-f3-occluded",
        episode="episode-1",
        frame=3,
        candidate_id=candidate_id,
    )
    visible(
        kernel,
        pipeline,
        key="e1-f4-reappear",
        episode="episode-1",
        frame=4,
        appearance=(0.32, 0.32, 0.68, 0.72),
        position=(0.4, 0.0),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        pipeline,
        key="e2-f0",
        episode="episode-2",
        frame=0,
        appearance=(0.24, 0.38, 0.62, 0.78),
        position=(0.0, 0.2),
        motion=(0.1, 0.0),
        common=True,
    )
    visible(
        kernel,
        pipeline,
        key="e2-f1",
        episode="episode-2",
        frame=1,
        appearance=(0.14, 0.47, 0.53, 0.87),
        position=(0.1, 0.2),
        motion=(0.1, 0.0),
        common=True,
    )
    return kernel, pipeline, candidate_id


def semantic_counts(kernel: VerdantKernel) -> tuple[int, ...]:
    return (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )


def test_tracking_preserves_native_evidence_without_creating_semantics() -> None:
    kernel = VerdantKernel(seed=701, state_dim=32, run_label="object-purity")
    pipeline = VerdantObjectPipeline()
    before = semantic_counts(kernel)
    result = visible(
        kernel,
        pipeline,
        key="first",
        episode="episode",
        frame=0,
        appearance=(0.2, 0.4, 0.6, 0.8),
        position=(0.0, 0.0),
        motion=(0.1, 0.0),
    )
    candidate = kernel.state.object_candidates[result.event.candidate_id]
    assert semantic_counts(kernel) == before
    assert candidate.evidence_refs == (result.report.observation.evidence_ref,)
    assert candidate.observation_ids == (result.event.observation_id,)
    assert result.event.semantic_mutation_permitted is False


def test_transformation_continuity_associates_one_candidate() -> None:
    kernel = VerdantKernel(seed=702, state_dim=32, run_label="transform")
    pipeline = VerdantObjectPipeline()
    first = visible(
        kernel, pipeline, key="f0", episode="e", frame=0,
        appearance=(0.2, 0.4, 0.6, 0.8), position=(0.0, 0.0), motion=(0.1, 0.0)
    )
    second = visible(
        kernel, pipeline, key="f1", episode="e", frame=1,
        appearance=(0.3, 0.35, 0.65, 0.75), position=(0.1, 0.0), motion=(0.1, 0.0), common=True
    )
    assert second.event.candidate_id == first.event.candidate_id
    candidate = kernel.state.object_candidates[first.event.candidate_id]
    assert candidate.visible_observation_count == 2
    assert candidate.persistence_count == 1
    assert candidate.transformation_count >= 1
    assert candidate.common_motion_count == 1


def test_similar_appearance_with_incompatible_motion_forms_separate_candidate() -> None:
    kernel = VerdantKernel(seed=703, state_dim=32, run_label="lookalike")
    pipeline = VerdantObjectPipeline()
    first = visible(
        kernel, pipeline, key="a0", episode="e", frame=0,
        appearance=(0.2, 0.4, 0.6, 0.8), position=(0.0, 0.0), motion=(0.1, 0.0)
    )
    second = visible(
        kernel, pipeline, key="b1", episode="e", frame=1,
        appearance=(0.22, 0.39, 0.61, 0.79), position=(2.0, 0.0), motion=(-0.1, 0.0)
    )
    assert second.event.candidate_id != first.event.candidate_id
    assert first.event.candidate_id in second.report.competing_candidate_ids
    assert len(kernel.state.object_candidates) == 2


def test_occlusion_and_reappearance_are_preserved_as_identity_evidence() -> None:
    kernel = VerdantKernel(seed=704, state_dim=32, run_label="occlusion")
    pipeline = VerdantObjectPipeline()
    first = visible(
        kernel, pipeline, key="f0", episode="e", frame=0,
        appearance=(0.2, 0.4, 0.6, 0.8), position=(0.0, 0.0), motion=(0.1, 0.0)
    )
    candidate_id = first.event.candidate_id
    occlude(kernel, pipeline, key="f1-occ", episode="e", frame=1, candidate_id=candidate_id)
    assert kernel.state.object_candidates[candidate_id].status == ObjectCandidateStatus.OCCLUDED
    reappeared = visible(
        kernel, pipeline, key="f2", episode="e", frame=2,
        appearance=(0.24, 0.38, 0.62, 0.78), position=(0.2, 0.0), motion=(0.1, 0.0)
    )
    assert reappeared.event.candidate_id == candidate_id
    candidate = kernel.state.object_candidates[candidate_id]
    assert candidate.occlusion_count == 1
    assert candidate.reappearance_count == 1


def test_repetition_alone_cannot_earn_objecthood() -> None:
    kernel = VerdantKernel(seed=705, state_dim=32, run_label="gating")
    pipeline = VerdantObjectPipeline()
    candidate_id = ""
    for frame in range(6):
        result = visible(
            kernel, pipeline, key=f"same-{frame}", episode="same", frame=frame,
            appearance=(0.2, 0.4, 0.6, 0.8), position=(frame * 0.1, 0.0), motion=(0.1, 0.0)
        )
        candidate_id = result.event.candidate_id
    report = pipeline.inspect_promotion(kernel, candidate_id)
    assert report.disposition == ObjectPromotionDisposition.DEFER
    assert "insufficient_recurrence" in report.rejection_codes
    assert "insufficient_transformation_continuity" in report.rejection_codes
    assert "insufficient_occlusion_reappearance" in report.rejection_codes


def test_full_temporal_history_becomes_eligible() -> None:
    kernel, pipeline, candidate_id = build_eligible()
    candidate = kernel.state.object_candidates[candidate_id]
    report = pipeline.inspect_promotion(kernel, candidate_id)
    assert candidate.status == ObjectCandidateStatus.ELIGIBLE
    assert candidate.visible_observation_count == 6
    assert len(candidate.episode_ids) == 2
    assert candidate.persistence_count >= 3
    assert candidate.transformation_count >= 2
    assert candidate.common_motion_count >= 2
    assert candidate.reappearance_count == 1
    assert report.disposition == ObjectPromotionDisposition.PROMOTE
    assert report.rejection_codes == ()
    assert report.evidence_refs == candidate.evidence_refs


def test_promotion_requires_council_authorization() -> None:
    kernel, pipeline, candidate_id = build_eligible(seed=708)
    report = pipeline.inspect_promotion(kernel, candidate_id)
    with pytest.raises(ObjectAuthorizationError):
        kernel.commit_object_promotion(
            report,
            council_decision_event_id="missing-decision",
        )


def test_governed_promotion_creates_one_machine_named_proto_object() -> None:
    kernel, pipeline, candidate_id = build_eligible(seed=709)
    before = semantic_counts(kernel)
    result = pipeline.promote(kernel, candidate_id)
    after = semantic_counts(kernel)
    concept = kernel.state.concepts[result.promotion_event.concept_id]
    candidate = kernel.state.object_candidates[candidate_id]
    assert after[0] == before[0] + 1
    assert after[1:] == before[1:]
    assert concept.label.startswith("proto-object-")
    assert concept.attributes["concept_type"] == "earned_proto_object"
    assert concept.attributes["semantic_category_preinstalled"] is False
    assert concept.attributes["object_candidate_id"] == candidate_id
    assert set(concept.evidence_refs) == set(candidate.evidence_refs)
    assert candidate.status == ObjectCandidateStatus.PROMOTED
    assert candidate.promoted_concept_id == concept.concept_id


def test_observation_inspection_is_pure_and_stale_report_is_rejected() -> None:
    kernel = VerdantKernel(seed=710, state_dim=32, run_label="stale-observation")
    pipeline = VerdantObjectPipeline()
    evidence = sensory_evidence(
        kernel, key="pending", episode="e", frame=0,
        features=(0.2, 0.4, 0.6, 0.8)
    )
    observation = ObjectObservationInput(
        episode_id="e", frame_index=0, evidence_ref=evidence,
        modality="vision_native", kind=ObjectObservationKind.VISIBLE,
        appearance_features=(0.2, 0.4, 0.6, 0.8),
        position=(0.0, 0.0), motion=(0.1, 0.0)
    )
    before = kernel.fingerprint()
    report = pipeline.inspect_observation(kernel, observation)
    assert kernel.fingerprint() == before
    visible(
        kernel, pipeline, key="other", episode="other", frame=0,
        appearance=(0.9, 0.1, 0.1, 0.1), position=(0.0, 1.0), motion=(0.0, 0.1)
    )
    with pytest.raises(ObjectStaleError):
        pipeline.commit_observation(kernel, report)


def test_tampered_promotion_report_is_rejected() -> None:
    kernel, pipeline, candidate_id = build_eligible(seed=711)
    report = pipeline.inspect_promotion(kernel, candidate_id)
    tampered = report.model_copy(update={"proposed_label": "human-supplied-cup"})
    with pytest.raises(ObjectIntegrityError):
        kernel.validate_object_promotion_report(tampered)


def test_exact_checkpoint_recovery_preserves_object_lineage(tmp_path: Path) -> None:
    kernel, pipeline, candidate_id = build_eligible(seed=712)
    pipeline.promote(kernel, candidate_id)
    path = tmp_path / "objects.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.snapshot() == kernel.snapshot()
    assert restored.object_structural_fingerprint() == kernel.object_structural_fingerprint()


def test_deterministic_replay_produces_identical_object_development() -> None:
    first, first_pipeline, first_id = build_eligible(seed=713)
    first_pipeline.promote(first, first_id)
    second, second_pipeline, second_id = build_eligible(seed=713)
    second_pipeline.promote(second, second_id)
    assert first_id == second_id
    assert first.snapshot() == second.snapshot()
