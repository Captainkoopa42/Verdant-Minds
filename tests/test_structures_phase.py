from __future__ import annotations

import hashlib

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    StructureCandidateStatus,
    StructurePromotionDisposition,
    StructureStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
    event_key: str,
    labels: tuple[str, ...],
    *,
    context: str,
    feature: tuple[float, ...] = (1.0, 0.0, 0.0),
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="structure:controlled",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=feature,
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_structure_test": True},
        metadata={"context_id": context},
    )


def cultivate_triad(kernel: VerdantKernel, count: int = 6) -> None:
    development = VerdantDevelopmentPipeline()
    for index in range(count):
        development.advance(
            kernel,
            command(
                f"triad-{index}",
                ("kren", "tar", "vel"),
                context=f"context-{index % 2}",
            ),
        )


def only_candidate(kernel: VerdantKernel):
    assert len(kernel.state.structure_candidates) == 1
    return next(iter(kernel.state.structure_candidates.values()))


def test_developmental_history_forms_unlabeled_structure_candidate() -> None:
    kernel = VerdantKernel(seed=1401, state_dim=48, run_label="structure-formation")
    cultivate_triad(kernel, 5)
    candidate = only_candidate(kernel)

    labels = {
        kernel.state.concepts[item].normalized_label
        for item in candidate.member_concept_ids
    }
    assert labels == {"kren", "tar", "vel"}
    assert candidate.occurrence_count >= kernel.state.structure_policy.minimum_recurrence_events
    assert candidate.status == StructureCandidateStatus.ELIGIBLE
    assert candidate.quality.reconstructability >= kernel.state.structure_policy.minimum_reconstructability
    assert candidate.quality.boundary_selectivity == pytest.approx(1.0)
    assert candidate.quality.evidence_diversity == pytest.approx(1.0)
    assert candidate.quality.cross_context_stability == pytest.approx(1.0)
    assert len(kernel.state.relations) == 0
    assert len(kernel.state.structures) == 0


def test_candidate_cannot_promote_before_independent_gates_are_met() -> None:
    kernel = VerdantKernel(seed=1402, state_dim=48, run_label="structure-gates")
    cultivate_triad(kernel, 3)
    candidate = only_candidate(kernel)
    pipeline = VerdantStructurePipeline()
    report = pipeline.inspect_promotion(kernel, candidate.candidate_id)

    assert report.disposition == StructurePromotionDisposition.DEFER
    assert "insufficient_recurrence" in report.rejection_codes


def test_candidate_promotion_creates_opaque_operand_without_semantic_truth() -> None:
    kernel = VerdantKernel(seed=1403, state_dim=48, run_label="structure-promotion")
    cultivate_triad(kernel, 6)
    candidate = only_candidate(kernel)
    before_semantics = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
    )

    result = VerdantStructurePipeline().promote(kernel, candidate.candidate_id)
    structure = kernel.state.structures[result.event.structure_id]

    assert structure.opaque_name.startswith("P_")
    assert structure.semantic_label_preinstalled is False
    assert structure.member_concept_ids == candidate.member_concept_ids
    assert structure.evidence_refs == candidate.evidence_refs
    assert structure.field_prototype_sha256 == candidate.field_prototype_sha256
    assert before_semantics == (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
    )
    assert kernel.state.structure_candidates[candidate.candidate_id].status == StructureCandidateStatus.PROMOTED


def test_structure_inspection_is_pure_and_stale_report_is_rejected() -> None:
    kernel = VerdantKernel(seed=1404, state_dim=48, run_label="structure-stale")
    development = VerdantDevelopmentPipeline()
    for index in range(2):
        development.advance(
            kernel,
            command(f"triad-{index}", ("a", "b", "c"), context=f"ctx-{index}"),
        )
    # The second cycle is sufficient for the plastic strength threshold and
    # the automatic observer has already committed once. Inspecting again is pure.
    pipeline = VerdantStructurePipeline()
    before = kernel.snapshot()
    report = pipeline.inspect(kernel)
    assert report is not None
    assert kernel.snapshot() == before

    kernel.update_structure_policy(
        minimum_boundary_selectivity=min(
            1.0, kernel.state.structure_policy.minimum_boundary_selectivity + 0.01
        )
    )
    with pytest.raises(StructureStaleError):
        pipeline.commit(kernel, report)


def test_candidate_identity_depends_on_structure_not_run_or_partition_metadata() -> None:
    left = VerdantKernel(seed=1405, state_dim=48, run_label="structure-identity-left")
    right = VerdantKernel(seed=9999, state_dim=48, run_label="structure-identity-right")
    cultivate_triad(left, 5)
    cultivate_triad(right, 5)

    left_candidate = only_candidate(left)
    right_candidate = only_candidate(right)
    assert left_candidate.member_concept_ids == right_candidate.member_concept_ids
    assert left_candidate.candidate_id == right_candidate.candidate_id


def test_checkpoint_round_trip_preserves_candidates_and_promoted_structures(tmp_path) -> None:
    kernel = VerdantKernel(seed=1406, state_dim=48, run_label="structure-checkpoint")
    cultivate_triad(kernel, 6)
    candidate = only_candidate(kernel)
    VerdantStructurePipeline().promote(kernel, candidate.candidate_id)

    path = tmp_path / "structures.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.state.structure_candidates == kernel.state.structure_candidates
    assert restored.state.structures == kernel.state.structures
    assert restored.state.structure_observation_events == kernel.state.structure_observation_events
    assert restored.state.structure_promotion_events == kernel.state.structure_promotion_events
    assert restored.fingerprint() == kernel.fingerprint()


def test_boundary_contamination_blocks_promotion() -> None:
    kernel = VerdantKernel(seed=1407, state_dim=48, run_label="structure-boundary")
    kernel.update_structure_policy(
        maximum_members=3,
        maximum_neighbors_per_seed=2,
        minimum_boundary_selectivity=0.90,
    )
    development = VerdantDevelopmentPipeline()
    # First establish the internal triad strongly enough to keep it as the
    # local top-2 neighborhood for each seed.
    for index in range(7):
        development.advance(
            kernel,
            command(f"core-{index}", ("a", "b", "c"), context=f"core-{index % 2}"),
        )
    # Add several external traces, creating meaningful boundary pressure while
    # retaining the same 3-member candidate.
    for index, outsider in enumerate(("x", "y", "z")):
        for repeat in range(2):
            development.advance(
                kernel,
                command(
                    f"boundary-{index}-{repeat}",
                    ("a", outsider),
                    context=f"boundary-{index}",
                    feature=(0.0, 1.0, 0.0),
                ),
            )
    # Re-observe the core after boundary traces exist.
    development.advance(
        kernel,
        command("core-final", ("a", "b", "c"), context="core-final"),
    )
    core_ids = tuple(
        sorted(
            concept_id
            for concept_id, concept in kernel.state.concepts.items()
            if concept.normalized_label in {"a", "b", "c"}
        )
    )
    candidate = next(
        item for item in kernel.state.structure_candidates.values()
        if item.member_concept_ids == core_ids
    )
    report = VerdantStructurePipeline().inspect_promotion(kernel, candidate.candidate_id)

    assert candidate.quality.boundary_selectivity < 0.90
    assert report.disposition == StructurePromotionDisposition.DEFER
    assert "boundary_selectivity_below_threshold" in report.rejection_codes


def test_multiple_evidence_records_from_one_context_do_not_fake_cross_context_stability() -> None:
    kernel = VerdantKernel(seed=1408, state_dim=48, run_label="structure-context-gate")
    development = VerdantDevelopmentPipeline()
    for index in range(7):
        development.advance(
            kernel,
            command(
                f"same-context-{index}",
                ("kren", "tar", "vel"),
                context="only-one-context",
            ),
        )
    candidate = only_candidate(kernel)
    report = VerdantStructurePipeline().inspect_promotion(kernel, candidate.candidate_id)

    assert candidate.quality.cross_context_stability == pytest.approx(0.5)
    assert report.disposition == StructurePromotionDisposition.DEFER
    assert "insufficient_cross_context_stability" in report.rejection_codes
