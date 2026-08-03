from __future__ import annotations

import hashlib

import pytest

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RefoldDisposition,
    RefoldingIntegrityError,
    RefoldingStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_refolding import VerdantRefoldingPipeline
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(event_key: str, labels: tuple[str, ...], *, context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="m18:controlled",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_refolding_test": True},
        metadata={"context_id": context},
    )


def challenge_evidence(kernel: VerdantKernel, event_key: str, *, context: str):
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=event_key,
            source_ref="m18:contradiction",
            modality="text",
            payload_sha256=digest(event_key),
            feature_vector=(0.0, 1.0, 0.0),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.OBSERVATION,
            semantic_evidence_details={
                "controlled_structural_contradiction": True,
                "semantic_mutation_permitted": False,
            },
            metadata={"context_id": context, "event_type": "structural_challenge"},
        )
    )
    return tuple(
        sorted(
            {
                result.observation_evidence_id,
                result.translation_evidence_id,
                *result.additional_evidence_ids,
            }
        )
    )


def labels(kernel: VerdantKernel, concept_ids) -> set[str]:
    return {kernel.state.concepts[item].normalized_label for item in concept_ids}


def concept_id(kernel: VerdantKernel, label: str) -> str:
    return next(
        item
        for item, concept in kernel.state.concepts.items()
        if concept.normalized_label == label
    )


def cultivate_and_promote(
    edges: tuple[tuple[str, str], ...],
    *,
    minimum_members: int,
    maximum_neighbors_per_seed: int,
    seed: int,
) -> tuple[VerdantKernel, str]:
    kernel = VerdantKernel(seed=seed, state_dim=16, run_label=f"m18-{seed}")
    kernel.update_plasticity_policy(
        decay_rate=0.0,
        learning_rate=0.50,
        maximum_degree=12,
        maximum_edge_node_ratio=6.0,
        strength_budget_per_concept=5.0,
    )
    kernel.update_structure_policy(
        minimum_members=minimum_members,
        maximum_members=minimum_members,
        maximum_neighbors_per_seed=maximum_neighbors_per_seed,
        minimum_member_association_strength=0.15,
        minimum_reconstructability=0.18,
        minimum_internal_cohesion=0.18,
        minimum_boundary_selectivity=0.50,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
    )
    development = VerdantDevelopmentPipeline()
    for repeat in range(5):
        for index, edge in enumerate(edges):
            development.advance(
                kernel,
                command(
                    f"learn-{seed}-{repeat}-{index}",
                    edge,
                    context=f"world-{repeat % 2}",
                ),
            )
    expected = {item for edge in edges for item in edge}
    candidate = max(
        (
            item
            for item in kernel.state.structure_candidates.values()
            if labels(kernel, item.member_concept_ids) == expected
        ),
        key=lambda item: item.occurrence_count,
    )
    structure_id = VerdantStructurePipeline().promote(
        kernel, candidate.candidate_id
    ).event.structure_id
    return kernel, structure_id


@pytest.fixture(scope="module")
def split_fixture():
    # One six-member fold built from two internally coherent triangles plus
    # three cross-links from a3 into the B triangle. Removing those cross-links
    # reveals two viable three-member components.
    edges = (
        ("a1", "a2"),
        ("a2", "a3"),
        ("a1", "a3"),
        ("b1", "b2"),
        ("b2", "b3"),
        ("b1", "b3"),
        ("a3", "b1"),
        ("a3", "b2"),
        ("a3", "b3"),
    )
    kernel, structure_id = cultivate_and_promote(
        edges, minimum_members=6, maximum_neighbors_per_seed=6, seed=1801
    )
    yield kernel.snapshot(), structure_id


def fresh_split(split_fixture):
    state, structure_id = split_fixture
    return VerdantKernel.from_state(state.model_copy(deep=True)), structure_id


def add_repeated_challenge(
    kernel: VerdantKernel,
    structure_id: str,
    pair: tuple[str, str],
    *,
    prefix: str,
    repeats: int = 2,
):
    pipeline = VerdantRefoldingPipeline()
    ids = tuple(sorted((concept_id(kernel, pair[0]), concept_id(kernel, pair[1]))))
    record = None
    for index in range(repeats):
        refs = challenge_evidence(kernel, f"{prefix}-{index}", context=f"challenge-{index}")
        record = pipeline.challenge(
            kernel,
            structure_id,
            ids,
            evidence_refs=refs,
            confidence=0.80,
        )
    return record


def test_single_contradiction_observation_does_not_force_refold(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    add_repeated_challenge(
        kernel, structure_id, ("a3", "b1"), prefix="single", repeats=1
    )
    report = VerdantRefoldingPipeline().inspect(kernel, structure_id)
    assert report.disposition == RefoldDisposition.STABLE
    assert "no_mature_structural_challenge" in report.rejection_codes
    assert kernel.structure_is_available(structure_id)


def test_recurrent_bridge_contradictions_split_fold_without_erasing_parent(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    for index, pair in enumerate((("a3", "b1"), ("a3", "b2"), ("a3", "b3"))):
        add_repeated_challenge(
            kernel, structure_id, pair, prefix=f"split-{index}", repeats=2
        )
    pipeline = VerdantRefoldingPipeline()
    report = pipeline.inspect(kernel, structure_id)
    assert report.disposition == RefoldDisposition.SPLIT
    assert len(report.proposals) == 2
    assert {frozenset(labels(kernel, item.member_concept_ids)) for item in report.proposals} == {
        frozenset({"a1", "a2", "a3"}),
        frozenset({"b1", "b2", "b3"}),
    }

    parent_before = kernel.state.structures[structure_id]
    event = pipeline.commit(kernel, report)
    assert kernel.state.structures[structure_id] == parent_before
    assert not kernel.structure_is_available(structure_id)
    assert len(event.produced_structure_ids) == 2
    for child_id in event.produced_structure_ids:
        child = kernel.state.structures[child_id]
        assert child.lineage_parent_structure_id == structure_id
        assert child.lineage_root_structure_id == structure_id
        assert child.revision_index == 1
        assert child.refold_basis_challenge_ids == report.challenge_ids
        assert child.quality_at_promotion.perturbation_survival > 0.0
        assert child.quality_at_promotion.contradiction_tolerance == 1.0


def test_split_children_become_causal_operands_while_parent_stays_dormant(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    for index, pair in enumerate((("a3", "b1"), ("a3", "b2"), ("a3", "b3"))):
        add_repeated_challenge(kernel, structure_id, pair, prefix=f"causal-{index}")
    event = VerdantRefoldingPipeline().refold(kernel, structure_id).event

    a1 = concept_id(kernel, "a1")
    report = VerdantCompilationPipeline().inspect(kernel, (a1,))
    assert report.structure_id in set(event.produced_structure_ids)
    assert labels(kernel, report.reconstructed_concept_ids) == {"a1", "a2", "a3"}
    assert structure_id not in set(event.produced_structure_ids)
    assert not kernel.structure_is_available(structure_id)


def test_connected_contradiction_produces_revision_not_split() -> None:
    kernel, structure_id = cultivate_and_promote(
        (("x1", "x2"), ("x2", "x3"), ("x1", "x3")),
        minimum_members=3,
        maximum_neighbors_per_seed=3,
        seed=1802,
    )
    add_repeated_challenge(kernel, structure_id, ("x1", "x3"), prefix="revise")
    pipeline = VerdantRefoldingPipeline()
    report = pipeline.inspect(kernel, structure_id)
    assert report.disposition == RefoldDisposition.REVISE
    assert len(report.proposals) == 1
    proposal = report.proposals[0]
    assert labels(kernel, proposal.member_concept_ids) == {"x1", "x2", "x3"}
    assert len(proposal.internal_edge_snapshots) == 2

    event = pipeline.commit(kernel, report)
    revised = kernel.state.structures[event.produced_structure_ids[0]]
    assert revised.lineage_parent_structure_id == structure_id
    assert revised.revision_index == 1
    assert len(revised.internal_edge_snapshots) == 2
    assert not kernel.structure_is_available(structure_id)
    assert kernel.structure_is_available(revised.structure_id)


def test_undersized_split_remains_unresolved_and_preserves_parent() -> None:
    kernel, structure_id = cultivate_and_promote(
        (("u1", "u2"), ("u2", "u3"), ("u1", "u3")),
        minimum_members=3,
        maximum_neighbors_per_seed=3,
        seed=1803,
    )
    add_repeated_challenge(kernel, structure_id, ("u1", "u2"), prefix="unres-a")
    add_repeated_challenge(kernel, structure_id, ("u1", "u3"), prefix="unres-b")
    pipeline = VerdantRefoldingPipeline()
    report = pipeline.inspect(kernel, structure_id)
    assert report.disposition == RefoldDisposition.UNRESOLVED
    assert not report.proposals
    event = pipeline.commit(kernel, report)
    assert event.produced_structure_ids == ()
    assert event.parent_ablated is False
    assert kernel.structure_is_available(structure_id)


def test_refold_inspection_is_pure_and_policy_change_makes_report_stale(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    for index, pair in enumerate((("a3", "b1"), ("a3", "b2"), ("a3", "b3"))):
        add_repeated_challenge(kernel, structure_id, pair, prefix=f"stale-{index}")
    pipeline = VerdantRefoldingPipeline()
    before = kernel.snapshot()
    report = pipeline.inspect(kernel, structure_id)
    assert kernel.snapshot() == before
    kernel.update_refolding_policy(minimum_combined_confidence=0.74)
    with pytest.raises(RefoldingStaleError):
        kernel.commit_structure_refold(report)


def test_structural_challenge_replay_is_idempotent_and_conflicting_reuse_is_rejected(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    pipeline = VerdantRefoldingPipeline()
    refs = challenge_evidence(kernel, "replay-challenge", context="replay")
    ids = tuple(sorted((concept_id(kernel, "a3"), concept_id(kernel, "b1"))))
    first = pipeline.challenge(
        kernel, structure_id, ids, evidence_refs=refs, confidence=0.8
    )
    cycle_after_first = kernel.state.cycle
    second = pipeline.challenge(
        kernel, structure_id, ids, evidence_refs=refs, confidence=0.8
    )
    assert first == second
    assert kernel.state.cycle == cycle_after_first
    with pytest.raises(RefoldingIntegrityError):
        pipeline.challenge(kernel, structure_id, ids, evidence_refs=refs, confidence=0.7)


def test_refolding_checkpoint_roundtrip_preserves_lineage(split_fixture, tmp_path) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    for index, pair in enumerate((("a3", "b1"), ("a3", "b2"), ("a3", "b3"))):
        add_repeated_challenge(kernel, structure_id, pair, prefix=f"checkpoint-{index}")
    VerdantRefoldingPipeline().refold(kernel, structure_id)

    path = tmp_path / "m18-refold.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.state.structural_challenges == kernel.state.structural_challenges
    assert restored.state.structure_refold_events == kernel.state.structure_refold_events
    assert restored.state.structures == kernel.state.structures
    assert restored.state.ablated_structure_ids == kernel.state.ablated_structure_ids
    assert restored.fingerprint() == kernel.fingerprint()


def test_refolding_does_not_install_semantic_truth(split_fixture) -> None:
    kernel, structure_id = fresh_split(split_fixture)
    before = (len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims))
    for index, pair in enumerate((("a3", "b1"), ("a3", "b2"), ("a3", "b3"))):
        add_repeated_challenge(kernel, structure_id, pair, prefix=f"firewall-{index}")
    after_challenge = (len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims))
    VerdantRefoldingPipeline().refold(kernel, structure_id)
    after_refold = (len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims))
    assert after_challenge == before
    assert after_refold == before
