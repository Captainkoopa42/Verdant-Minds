from __future__ import annotations

import hashlib

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualRuntime,
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    FunctionalAction,
    FunctionalConsequence,
    FunctionalPartitionIndex,
    HypothesisGenerationPolicy,
    HypothesisOperator,
    OutcomeKind,
    StructuralHypothesis,
    build_hypothesis_plan,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _experience(
    key: str,
    *,
    labels: tuple[str, ...] = (),
    relations: tuple[RelationProposal, ...] = (),
    evidence_kind: EvidenceKind | None = None,
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=key,
        source_ref=f"curriculum:{key}",
        modality="text",
        payload_sha256=_digest(key),
        feature_vector=tuple(index / 15.0 for index in range(16)),
        concept_labels=labels,
        relation_proposals=relations,
        semantic_evidence_kind=evidence_kind,
    )


def _path_kernel(*, relation_confidence: float = 0.9) -> tuple[VerdantKernel, str]:
    kernel = VerdantKernel(seed=5501, state_dim=16, run_label="hypothesis-paths")
    kernel.apply_experience(
        _experience(
            "dependency",
            relations=(
                RelationProposal(
                    source_label="stabilize loop",
                    target_label="pressure input",
                    relation_type="requires",
                    confidence=relation_confidence,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "route-a",
            relations=(
                RelationProposal(
                    source_label="pressure input",
                    target_label="sensor route a",
                    relation_type="routes_to",
                    confidence=relation_confidence,
                ),
                RelationProposal(
                    source_label="sensor route a",
                    target_label="canonical reading",
                    relation_type="routes_to",
                    confidence=relation_confidence,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "route-b",
            relations=(
                RelationProposal(
                    source_label="pressure input",
                    target_label="sensor route b",
                    relation_type="routes_to",
                    confidence=relation_confidence,
                ),
                RelationProposal(
                    source_label="sensor route b",
                    target_label="canonical reading",
                    relation_type="routes_to",
                    confidence=relation_confidence,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "grounded-reading",
            labels=("canonical reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    report = DependencyGapDetector().detect_and_record(kernel)
    assert len(report.mutations) == 1
    return kernel, report.mutations[0].obligation.kernel_id


def _projected(
    hypotheses: tuple[StructuralHypothesis, ...],
) -> tuple[StructuralHypothesis, ...]:
    return tuple(
        item
        for item in hypotheses
        if item.operator == HypothesisOperator.EVIDENCE_PATH_PROJECTION
    )


def test_generation_is_pure_deterministic_and_compositional() -> None:
    kernel, obligation_id = _path_kernel()
    generator = DependencyGapHypothesisGenerator()
    canonical_before = kernel.fingerprint()

    first = generator.generate(kernel, obligation_id)
    second = generator.generate(kernel, obligation_id)

    assert first == second
    assert kernel.fingerprint() == canonical_before
    projected = _projected(first)
    assert len(projected) == 2
    assert {item.operator for item in first} == {
        HypothesisOperator.EVIDENCE_PATH_PROJECTION,
        HypothesisOperator.NULL_ARTIFACT,
        HypothesisOperator.DEFER_INSUFFICIENT_EVIDENCE,
    }
    assert all(len(item.derivation_path_relation_ids) == 2 for item in projected)
    assert all(len(item.patches) == 1 for item in projected)
    assert all(
        {outcome.kind for outcome in item.outcomes}
        == {
            OutcomeKind.PATH_COMPLETES,
            OutcomeKind.PATH_STALLS,
            OutcomeKind.PATH_CONFLICTS,
        }
        for item in projected
    )
    canonical_refs = {
        *kernel.state.concepts,
        *kernel.state.relations,
        *kernel.state.evidence,
        *kernel.state.obligation_kernels,
    }
    assert all(set(item.provenance_refs).issubset(canonical_refs) for item in first)


def test_functional_partitions_collapse_cosmetic_path_variants() -> None:
    kernel, obligation_id = _path_kernel()
    hypotheses = DependencyGapHypothesisGenerator().generate(kernel, obligation_id)
    projected = _projected(hypotheses)

    success = [
        next(outcome for outcome in item.outcomes if outcome.kind == OutcomeKind.PATH_COMPLETES)
        for item in projected
    ]
    assert projected[0].hypothesis_id != projected[1].hypothesis_id
    assert success[0].equivalence_signature == success[1].equivalence_signature

    partition = FunctionalPartitionIndex.build(obligation_id, hypotheses)
    success_class = next(
        item
        for item in partition.equivalence_classes
        if item.equivalence_signature == success[0].equivalence_signature
    )
    assert set(success_class.member_outcome_ids) == {
        success[0].outcome_id,
        success[1].outcome_id,
    }
    assert success[1].outcome_id in partition.rejected_duplicate_outcome_ids


def test_equivalence_ignores_continuous_relation_weight_noise() -> None:
    low, low_obligation = _path_kernel(relation_confidence=0.3)
    high, high_obligation = _path_kernel(relation_confidence=0.95)
    generator = DependencyGapHypothesisGenerator()

    low_hypotheses = generator.generate(low, low_obligation)
    high_hypotheses = generator.generate(high, high_obligation)

    low_signatures = sorted(
        outcome.equivalence_signature
        for item in low_hypotheses
        for outcome in item.outcomes
    )
    high_signatures = sorted(
        outcome.equivalence_signature
        for item in high_hypotheses
        for outcome in item.outcomes
    )
    assert low_signatures == high_signatures

    consequence = FunctionalConsequence(
        action=FunctionalAction.DEFER_FOR_EVIDENCE,
        activated_canonical_refs=("concept:x",),
    )
    assert consequence.equivalence_signature() == FunctionalConsequence(
        action=FunctionalAction.DEFER_FOR_EVIDENCE,
        activated_canonical_refs=("concept:x",),
    ).equivalence_signature()


def test_bounds_and_directionality_prevent_unbounded_or_reverse_search() -> None:
    kernel, obligation_id = _path_kernel()
    shallow = DependencyGapHypothesisGenerator(
        HypothesisGenerationPolicy(maximum_path_depth=1)
    ).generate(kernel, obligation_id)
    assert _projected(shallow) == ()
    assert {item.operator for item in shallow} == {
        HypothesisOperator.NULL_ARTIFACT,
        HypothesisOperator.DEFER_INSUFFICIENT_EVIDENCE,
    }

    capped = DependencyGapHypothesisGenerator(
        HypothesisGenerationPolicy(maximum_projected_paths=1)
    ).generate(kernel, obligation_id)
    assert len(_projected(capped)) == 1


def test_preregistered_hypothesis_plan_executes_only_in_simulation() -> None:
    kernel, obligation_id = _path_kernel()
    hypothesis = _projected(
        DependencyGapHypothesisGenerator().generate(kernel, obligation_id)
    )[0]
    outcome = next(
        item for item in hypothesis.outcomes if item.kind == OutcomeKind.PATH_COMPLETES
    )
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation_id,
                action_operator=hypothesis.operator.value,
                requested_budget=0.05,
                estimated_cost=0.05,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.9,
                generator_version=hypothesis.grammar_version,
                metric_provenance_refs=hypothesis.provenance_refs,
            ),
        ),
        source_event_key="attention:hypothesis-dry-run",
    ).decision
    allocation = decision.allocations[0]
    canonical_before = kernel.fingerprint()
    plan = build_hypothesis_plan(
        hypothesis,
        outcome,
        source_event_key="simulation:hypothesis-dry-run",
        requested_budget=0.02,
        consumed_budget=0.01,
    )

    result = CounterfactualRuntime().execute(
        kernel,
        allocation_id=allocation.allocation_id,
        plan=plan,
    )

    assert kernel.fingerprint() == canonical_before
    assert result.settlement.canonical_unchanged
    assert result.settlement.applied_patch_ids == (hypothesis.patches[0].patch_id,)
    assert set(result.settlement.result_refs) == {
        hypothesis.hypothesis_id,
        outcome.outcome_id,
        outcome.equivalence_signature,
    }
    assert hypothesis.patches[0].record_key not in kernel.state.relations


def test_tampered_hypothesis_or_cross_hypothesis_outcome_is_rejected() -> None:
    kernel, obligation_id = _path_kernel()
    hypotheses = DependencyGapHypothesisGenerator().generate(kernel, obligation_id)
    projected = _projected(hypotheses)
    tampered = projected[0].model_copy(update={"operand_refs": ("fabricated",)})
    with pytest.raises(ValueError, match="identity checksum"):
        StructuralHypothesis.model_validate(tampered.model_dump(mode="json"))

    foreign_outcome = projected[1].outcomes[0]
    with pytest.raises(ValueError, match="does not belong"):
        build_hypothesis_plan(
            projected[0],
            foreign_outcome,
            source_event_key="simulation:foreign-outcome",
            requested_budget=0.01,
            consumed_budget=0.0,
        )
