from __future__ import annotations

import hashlib

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    StructureInteractionDisposition,
    StructureInteractionStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(event_key: str, labels: tuple[str, ...], *, context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="interaction:controlled",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_structure_interaction_test": True},
        metadata={"context_id": context},
    )


def labels_for_candidate(kernel: VerdantKernel, candidate) -> set[str]:
    return {
        kernel.state.concepts[item].normalized_label
        for item in candidate.member_concept_ids
    }


def cultivate_and_promote(
    kernel: VerdantKernel,
    prefix: str,
    edges: tuple[tuple[str, str], ...],
) -> str:
    development = VerdantDevelopmentPipeline()
    for repeat in range(4):
        for index, edge in enumerate(edges):
            development.advance(
                kernel,
                command(
                    f"{prefix}-{repeat}-{index}",
                    edge,
                    context=f"{prefix}-context-{repeat % 2}",
                ),
            )
    expected = {label for edge in edges for label in edge}
    candidate = max(
        (
            item
            for item in kernel.state.structure_candidates.values()
            if labels_for_candidate(kernel, item) == expected
        ),
        key=lambda item: item.occurrence_count,
    )
    return VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event.structure_id


@pytest.fixture(scope="module")
def interaction_fixture():
    kernel = VerdantKernel(seed=1601, state_dim=32, run_label="interaction-fixture")
    # M16 is about comparing already-earned structures, not about decay timing.
    # Freezing local decay makes the two isomorphic training histories directly
    # comparable while their absolute symbols remain disjoint.
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.25)
    kernel.update_structure_policy(
        minimum_members=4,
        maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_reconstructability=0.35,
        minimum_internal_cohesion=0.30,
        minimum_recurrence_events=3,
        minimum_evidence_events=3,
    )
    path_a = cultivate_and_promote(
        kernel,
        "world-a",
        (("a1", "a2"), ("a2", "a3"), ("a3", "a4")),
    )
    path_b = cultivate_and_promote(
        kernel,
        "world-b",
        (("b1", "b2"), ("b2", "b3"), ("b3", "b4")),
    )
    star_c = cultivate_and_promote(
        kernel,
        "world-c",
        (("c1", "c2"), ("c1", "c3"), ("c1", "c4")),
    )
    return kernel.snapshot(), path_a, path_b, star_c


def fresh(interaction_fixture):
    state, a, b, c = interaction_fixture
    return VerdantKernel.from_state(state.model_copy(deep=True)), a, b, c


def test_field_retrieval_finds_symbolically_disjoint_isomorphic_structure(interaction_fixture) -> None:
    kernel, path_a, path_b, star_c = fresh(interaction_fixture)
    pipeline = VerdantStructureInteractionPipeline()
    report = pipeline.inspect(kernel, path_a)

    by_target = {item.target_structure_id: item for item in report.candidates}
    assert report.best_target_structure_id == path_b
    assert by_target[path_b].disposition == StructureInteractionDisposition.VERIFIED_ALIGNMENT
    assert by_target[path_b].field_similarity > by_target[star_c].field_similarity
    assert by_target[path_b].symbolic_similarity >= kernel.state.structure_interaction_policy.minimum_symbolic_similarity
    assert set(kernel.state.structures[path_a].member_concept_ids).isdisjoint(
        kernel.state.structures[path_b].member_concept_ids
    )


def test_structure_sensitive_field_signature_ignores_surface_symbols(interaction_fixture) -> None:
    kernel, path_a, path_b, _ = fresh(interaction_fixture)
    pipeline = VerdantStructureInteractionPipeline()
    left = pipeline.signature(kernel, path_a)
    right = pipeline.signature(kernel, path_b)

    assert left.structure_id != right.structure_id
    # Surface IDs/names are absent from the encoder.  Small differences in
    # learned edge strengths are allowed, while relationally isomorphic forms
    # should still land almost on top of one another in the interaction field.
    assert left.feature_values[:2] == right.feature_values[:2]
    assert pipeline._field_similarity(left, right) > 0.999


def test_field_candidate_is_not_accepted_without_symbolic_verification(interaction_fixture) -> None:
    kernel, path_a, _, star_c = fresh(interaction_fixture)
    report = VerdantStructureInteractionPipeline().inspect(kernel, path_a)
    control = next(item for item in report.candidates if item.target_structure_id == star_c)

    # Path and star share size/edge count, so the continuous retrieval stage is
    # deliberately permissive enough to notice the star.  Exact symbolic
    # unfolding must still reject the analogy.
    assert control.field_similarity >= kernel.state.structure_interaction_policy.minimum_field_similarity
    assert control.symbolic_similarity < kernel.state.structure_interaction_policy.minimum_symbolic_similarity
    assert control.disposition == StructureInteractionDisposition.FIELD_ONLY


def test_verified_alignment_returns_one_to_one_role_mapping(interaction_fixture) -> None:
    kernel, path_a, path_b, _ = fresh(interaction_fixture)
    report = VerdantStructureInteractionPipeline().inspect(kernel, path_a)
    match = next(item for item in report.candidates if item.target_structure_id == path_b)

    assert len(match.member_mapping) == 4
    assert {a for a, _ in match.member_mapping} == set(kernel.state.structures[path_a].member_concept_ids)
    assert {b for _, b in match.member_mapping} == set(kernel.state.structures[path_b].member_concept_ids)


def test_interaction_inspection_is_pure_and_policy_change_makes_report_stale(interaction_fixture) -> None:
    kernel, path_a, _, _ = fresh(interaction_fixture)
    pipeline = VerdantStructureInteractionPipeline()
    before = kernel.snapshot()
    report = pipeline.inspect(kernel, path_a)
    assert kernel.snapshot() == before

    kernel.update_structure_interaction_policy(
        minimum_symbolic_similarity=kernel.state.structure_interaction_policy.minimum_symbolic_similarity - 0.01
    )
    with pytest.raises(StructureInteractionStaleError):
        pipeline.commit(kernel, report)


def test_ablated_target_is_excluded_from_field_retrieval(interaction_fixture) -> None:
    kernel, path_a, path_b, _ = fresh(interaction_fixture)
    from verdant_compilation import VerdantCompilationPipeline

    VerdantCompilationPipeline.ablate(kernel, path_b, "M16 retrieval ablation control")
    report = VerdantStructureInteractionPipeline().inspect(kernel, path_a)
    assert all(item.target_structure_id != path_b for item in report.candidates)
    assert report.best_target_structure_id is None


def test_interaction_event_checkpoint_roundtrip(interaction_fixture, tmp_path) -> None:
    kernel, path_a, path_b, _ = fresh(interaction_fixture)
    result = VerdantStructureInteractionPipeline().interact(kernel, path_a)
    assert result.report.best_target_structure_id == path_b

    path = tmp_path / "interaction.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.state.structure_interaction_events == kernel.state.structure_interaction_events
    assert restored.fingerprint() == kernel.fingerprint()


def test_structure_interaction_does_not_mutate_semantic_truth(interaction_fixture) -> None:
    kernel, path_a, _, _ = fresh(interaction_fixture)
    before = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    VerdantStructureInteractionPipeline().interact(kernel, path_a)
    after = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    assert after == before
