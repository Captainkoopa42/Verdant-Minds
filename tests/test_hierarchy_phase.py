from __future__ import annotations

import hashlib
import gc

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    HierarchyCandidateStatus,
    HierarchyStaleError,
    LayeredProbeDisposition,
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
        source_ref="hierarchy:controlled",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_hierarchy_test": True},
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
    for repeat in range(2):
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
def hierarchy_fixture():
    kernel = VerdantKernel(seed=1701, state_dim=16, run_label="hierarchy-fixture")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=4,
        maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25,
        minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
    )
    kernel.update_hierarchy_policy(
        minimum_interaction_events=3,
        minimum_evidence_events=6,
        layered_probe_similarity=0.985,
    )

    family = []
    for prefix in ("world-a", "world-b", "world-c"):
        letter = prefix[-1]
        family.append(
            cultivate_and_promote(
                kernel,
                prefix,
                ((f"{letter}1", f"{letter}2"), (f"{letter}2", f"{letter}3"), (f"{letter}3", f"{letter}4")),
            )
        )

    interaction = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    observations = []
    for structure_id in family:
        interaction.interact(kernel, structure_id)
        observations.append(hierarchy.observe(kernel))

    candidate = next(
        item for item in kernel.state.hierarchy_candidates.values()
        if set(item.member_structure_ids) == set(family)
    )
    layered = hierarchy.promote(kernel, candidate.candidate_id).event.layered_structure_id

    # These are deliberately created *after* Q has been earned. They are not
    # constituents of the higher-order object.
    star = cultivate_and_promote(
        kernel,
        "world-star",
        (("s1", "s2"), ("s1", "s3"), ("s1", "s4")),
    )
    novel_path = cultivate_and_promote(
        kernel,
        "world-d",
        (("d1", "d2"), ("d2", "d3"), ("d3", "d4")),
    )
    payload = (kernel.snapshot(), tuple(family), layered, star, novel_path, tuple(observations))
    yield payload
    del payload
    gc.collect()


def fresh(hierarchy_fixture):
    state, family, layered, star, novel, observations = hierarchy_fixture
    return (
        VerdantKernel.from_state(state.model_copy(deep=True)),
        family,
        layered,
        star,
        novel,
        observations,
    )


def test_higher_order_candidate_is_built_from_earned_structures(hierarchy_fixture) -> None:
    kernel, family, layered, _star, _novel, observations = fresh(hierarchy_fixture)
    assert observations[0] is not None
    first_candidate = observations[0].report.proposed_candidates[0]
    assert first_candidate.status == HierarchyCandidateStatus.TRACKING

    final_candidate = kernel.state.hierarchy_candidates[
        kernel.state.layered_structures[layered].source_candidate_id
    ]
    assert final_candidate.status == HierarchyCandidateStatus.PROMOTED
    assert set(final_candidate.member_structure_ids) == set(family)
    assert final_candidate.quality.pair_coverage == pytest.approx(1.0)
    assert final_candidate.quality.alignment_cohesion >= 0.99
    assert final_candidate.quality.prototype_cohesion >= 0.99


def test_layered_promotion_is_opaque_and_does_not_create_semantic_truth(hierarchy_fixture) -> None:
    kernel, family, layered, _star, _novel, _observations = fresh(hierarchy_fixture)
    record = kernel.state.layered_structures[layered]
    assert record.opaque_name.startswith("Q_")
    assert record.depth == 2
    assert record.semantic_label_preinstalled is False
    assert set(record.member_structure_ids) == set(family)
    # The controlled worlds contain only taught primitive concepts; layered
    # promotion itself adds no canonical semantic relation or claim.
    assert len(kernel.state.relations) == 0
    assert len(kernel.state.claims) == 0


def test_novel_structure_uses_layered_operand_and_reduces_comparison_work(hierarchy_fixture) -> None:
    kernel, family, layered, _star, novel, _observations = fresh(hierarchy_fixture)
    report = VerdantHierarchyPipeline().inspect_probe(kernel, novel)
    assert report.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
    assert report.layered_structure_id == layered
    assert set(report.matched_structure_ids) == set(family)
    assert report.cost.comparison_work < report.baseline_cost.comparison_work
    assert report.compression_gain > 0.0


def test_layered_ablation_removes_gain_and_restoration_returns_it(hierarchy_fixture) -> None:
    kernel, family, layered, _star, novel, _observations = fresh(hierarchy_fixture)
    hierarchy = VerdantHierarchyPipeline()

    with_q = hierarchy.inspect_probe(kernel, novel)
    hierarchy.ablate(kernel, layered, "M17 causal ablation control")
    without_q = hierarchy.inspect_probe(kernel, novel)
    hierarchy.restore(kernel, layered, "M17 causal restoration control")
    restored = hierarchy.inspect_probe(kernel, novel)

    assert with_q.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
    assert without_q.disposition == LayeredProbeDisposition.FALLBACK_MEMBER_SCAN
    assert restored.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
    assert set(with_q.matched_structure_ids) == set(without_q.matched_structure_ids) == set(restored.matched_structure_ids) == set(family)
    assert with_q.cost.comparison_work < without_q.cost.comparison_work
    assert without_q.compression_gain == 0.0
    assert restored.cost.comparison_work == with_q.cost.comparison_work
    assert restored.compression_gain == pytest.approx(with_q.compression_gain)


def test_symbolically_different_control_does_not_false_match_layered_family(hierarchy_fixture) -> None:
    kernel, _family, layered, star, _novel, _observations = fresh(hierarchy_fixture)
    report = VerdantHierarchyPipeline().inspect_probe(kernel, star)
    assert not (
        report.disposition == LayeredProbeDisposition.USE_LAYERED_STRUCTURE
        and report.layered_structure_id == layered
    )
    assert report.matched_structure_ids == ()


def test_hierarchy_inspection_is_pure_and_policy_change_makes_report_stale(hierarchy_fixture) -> None:
    kernel, family, _layered, _star, _novel, _observations = fresh(hierarchy_fixture)
    # Add a fresh verified interaction so there is a new observation report.
    VerdantStructureInteractionPipeline().interact(kernel, family[0])
    pipeline = VerdantHierarchyPipeline()
    before = kernel.snapshot()
    report = pipeline.inspect_observation(kernel)
    assert report is not None
    assert kernel.snapshot() == before

    kernel.update_hierarchy_policy(
        minimum_alignment_cohesion=kernel.state.hierarchy_policy.minimum_alignment_cohesion - 0.01
    )
    with pytest.raises(HierarchyStaleError):
        kernel.commit_hierarchy_observation(report)


def test_layered_probe_checkpoint_roundtrip(hierarchy_fixture, tmp_path) -> None:
    kernel, _family, _layered, _star, novel, _observations = fresh(hierarchy_fixture)
    result = VerdantHierarchyPipeline().probe(kernel, novel)
    assert result.event is not None

    path = tmp_path / "hierarchy.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.state.layered_structures == kernel.state.layered_structures
    assert restored.state.layered_probe_events == kernel.state.layered_probe_events
    assert restored.fingerprint() == kernel.fingerprint()


def test_layered_probe_does_not_mutate_semantic_truth(hierarchy_fixture) -> None:
    kernel, _family, _layered, _star, novel, _observations = fresh(hierarchy_fixture)
    before = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    VerdantHierarchyPipeline().probe(kernel, novel)
    after = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    assert after == before
