from __future__ import annotations

import hashlib

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    RelationStatus,
    VerdantKernel,
)
from verdant_obligations import (
    DependencyGapDetectionPolicy,
    DependencyGapDetector,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _experience(
    key: str,
    *,
    labels: tuple[str, ...] = (),
    relations: tuple[RelationProposal, ...] = (),
    semantic_kind: EvidenceKind | None = None,
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=key,
        source_ref=f"curriculum:{key}",
        modality="text",
        payload_sha256=_digest(key),
        feature_vector=tuple(index / 15.0 for index in range(16)),
        concept_labels=labels,
        relation_proposals=relations,
        semantic_evidence_kind=semantic_kind,
    )


def _dependency_kernel(*, relation_type: str = "requires") -> VerdantKernel:
    kernel = VerdantKernel(seed=5201, state_dim=16, run_label="gap-detector")
    kernel.apply_experience(
        _experience(
            "dependency-contract",
            relations=(
                RelationProposal(
                    source_label="regulate pressure",
                    target_label="pressure reading",
                    relation_type=relation_type,
                    confidence=0.9,
                ),
            ),
        )
    )
    return kernel


def test_inspection_is_pure_and_detection_creates_native_obligation() -> None:
    kernel = _dependency_kernel()
    detector = DependencyGapDetector()
    before = kernel.fingerprint()
    inspected, candidates = detector.inspect(kernel)

    assert kernel.fingerprint() == before
    assert len(inspected) == 1
    assert len(candidates) == 1
    relation = next(iter(kernel.state.relations.values()))
    candidate = candidates[0]
    assert candidate.relation_id == relation.relation_id
    assert candidate.target_action_node == relation.source_concept_id
    assert candidate.missing_input_signature == relation.target_concept_id
    assert set(relation.evidence_refs).issubset(candidate.canonical_triggering_refs)

    report = detector.detect_and_record(kernel)
    assert report.created_or_retriggered_count == 1
    assert report.replayed_count == 0
    assert len(kernel.state.obligation_kernels) == 1
    obligation = next(iter(kernel.state.obligation_kernels.values()))
    assert obligation.target_action_node == relation.source_concept_id
    assert obligation.missing_input_signature == relation.target_concept_id
    assert obligation.trigger_relation == "requires"


def test_unchanged_detection_replays_without_a_canonical_write() -> None:
    kernel = _dependency_kernel()
    detector = DependencyGapDetector()
    first = detector.detect_and_record(kernel)
    fingerprint = kernel.fingerprint()
    cycle = kernel.state.cycle
    history_size = len(kernel.state.obligation_history)

    replay = detector.detect_and_record(kernel)

    assert first.created_or_retriggered_count == 1
    assert replay.created_or_retriggered_count == 0
    assert replay.replayed_count == 1
    assert kernel.fingerprint() == fingerprint
    assert kernel.state.cycle == cycle
    assert len(kernel.state.obligation_history) == history_size


def test_qualifying_input_evidence_prevents_false_gap_creation() -> None:
    kernel = _dependency_kernel()
    kernel.apply_experience(
        _experience(
            "physical-pressure-reading",
            labels=("pressure reading",),
            semantic_kind=EvidenceKind.OUTCOME,
        )
    )
    detector = DependencyGapDetector()
    before = kernel.fingerprint()

    report = detector.detect_and_record(kernel)

    assert len(report.inspected_relation_ids) == 1
    assert report.candidates == ()
    assert report.mutations == ()
    assert kernel.fingerprint() == before
    assert kernel.state.obligation_kernels == {}


def test_unrelated_or_ineligible_edges_do_not_create_obligations() -> None:
    unrelated = _dependency_kernel(relation_type="mentions")
    assert DependencyGapDetector().detect_and_record(unrelated).candidates == ()

    rejected = VerdantKernel(seed=5202, state_dim=16, run_label="rejected-gap")
    rejected.apply_experience(
        _experience(
            "rejected-contract",
            relations=(
                RelationProposal(
                    source_label="regulate pressure",
                    target_label="pressure reading",
                    relation_type="requires",
                    status=RelationStatus.REJECTED,
                ),
            ),
        )
    )
    assert DependencyGapDetector().detect_and_record(rejected).candidates == ()
    assert rejected.state.obligation_kernels == {}


def test_detector_grammar_is_explicit_versioned_and_order_constrained() -> None:
    custom = DependencyGapDetectionPolicy(
        policy_version="dependency-policy-test-v1",
        dependency_relation_types=("needs",),
    )
    kernel = _dependency_kernel(relation_type="needs")
    report = DependencyGapDetector(policy=custom).detect_and_record(kernel)
    assert len(report.candidates) == 1
    assert report.policy_version == "dependency-policy-test-v1"

    with pytest.raises(ValueError, match="sorted and unique"):
        DependencyGapDetectionPolicy(
            dependency_relation_types=("requires", "needs"),
        )


def test_new_nonqualifying_local_evidence_retriggers_same_obligation() -> None:
    kernel = _dependency_kernel()
    detector = DependencyGapDetector()
    first = detector.detect_and_record(kernel)
    obligation_id = first.mutations[0].obligation.kernel_id

    kernel.apply_experience(
        _experience(
            "additional-testimony",
            labels=("pressure reading",),
            semantic_kind=EvidenceKind.TESTIMONY,
        )
    )
    retrigger = detector.detect_and_record(kernel)

    assert retrigger.created_or_retriggered_count == 1
    assert retrigger.mutations[0].obligation.kernel_id == obligation_id
    assert [event.event_type.value for event in kernel.state.obligation_history] == [
        "Created",
        "Retriggered",
    ]

