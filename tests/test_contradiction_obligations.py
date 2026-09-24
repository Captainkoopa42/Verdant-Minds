from __future__ import annotations

from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    ContradictionObligationKernel,
    KernelInvariantError,
    ObligationEventType,
    ObligationFamily,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionObligationDetector,
    DependencyGapPipeline,
    ObligationIntegrityError,
    derive_obligation_view,
)


def _claim(
    kernel: VerdantKernel,
    *,
    event_key: str,
    subject: str,
    obj: str,
    polarity: ClaimPolarity,
    source: ClaimSourceClass = ClaimSourceClass.DIRECT_OBSERVATION,
) -> None:
    ClaimLearningPipeline().record_claim(
        kernel,
        event_key=event_key,
        native_description=f"Controlled evidence {event_key}.",
        subject_label=subject,
        predicate="has_property",
        object_label=obj,
        polarity=polarity,
        source_class=source,
    )


def _contradict(kernel: VerdantKernel, stem: str = "door") -> None:
    _claim(
        kernel,
        event_key=f"{stem}-affirmed",
        subject=stem,
        obj="open",
        polarity=ClaimPolarity.AFFIRMED,
    )
    _claim(
        kernel,
        event_key=f"{stem}-negated",
        subject=stem,
        obj="open",
        polarity=ClaimPolarity.NEGATED,
    )


def test_native_contradiction_becomes_one_persistent_obligation() -> None:
    kernel = VerdantKernel(seed=6101, state_dim=16, run_label="contradiction-anchor")
    _contradict(kernel)
    detector = ContradictionObligationDetector()
    before = kernel.fingerprint()

    inspected, candidates = detector.inspect(kernel)
    assert kernel.fingerprint() == before
    assert inspected == tuple(kernel.state.contradictions)
    assert len(candidates) == 1

    report = detector.detect_and_record(kernel)
    assert report.created_or_retriggered_count == 1
    obligation = report.mutations[0].obligation
    contradiction = next(iter(kernel.state.contradictions.values()))
    assert isinstance(obligation, ContradictionObligationKernel)
    assert obligation.family == ObligationFamily.CONTRADICTION
    assert obligation.claim_refs == tuple(sorted(contradiction.claim_ids))
    assert set(obligation.claim_refs).issubset(obligation.canonical_triggering_refs)
    assert contradiction.contradiction_id in obligation.canonical_triggering_refs
    assert derive_obligation_view(kernel, obligation.kernel_id).family == ObligationFamily.CONTRADICTION


def test_detector_replay_is_noop_but_new_evidence_retriggers_same_anchor() -> None:
    kernel = VerdantKernel(seed=6102, state_dim=16, run_label="contradiction-retrigger")
    _contradict(kernel)
    detector = ContradictionObligationDetector()
    first = detector.detect_and_record(kernel).mutations[0]
    cycle = kernel.state.cycle
    fingerprint = kernel.fingerprint()

    replay = detector.detect_and_record(kernel).mutations[0]
    assert replay.replayed
    assert kernel.state.cycle == cycle
    assert kernel.fingerprint() == fingerprint

    _claim(
        kernel,
        event_key="door-affirmed-independent",
        subject="door",
        obj="open",
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.HUMAN_TESTIMONY,
    )
    retrigger = detector.detect_and_record(kernel).mutations[0]
    assert not retrigger.replayed
    assert retrigger.obligation.kernel_id == first.obligation.kernel_id
    events = [
        item for item in kernel.state.obligation_history
        if item.obligation_id == first.obligation.kernel_id
    ]
    assert [item.event_type for item in events] == [
        ObligationEventType.CREATED,
        ObligationEventType.RETRIGGERED,
    ]


def test_distinct_claim_keys_do_not_overmerge() -> None:
    kernel = VerdantKernel(seed=6103, state_dim=16, run_label="contradiction-scope")
    _contradict(kernel, "door")
    _contradict(kernel, "window")
    report = ContradictionObligationDetector().detect_and_record(kernel)
    assert len(report.mutations) == 2
    assert len(kernel.state.obligation_kernels) == 2
    assert len({item.obligation.scope_key for item in report.mutations}) == 2


def test_obligation_preserves_native_evidence_and_claims() -> None:
    kernel = VerdantKernel(seed=6104, state_dim=16, run_label="contradiction-evidence")
    _contradict(kernel)
    mutation = ContradictionObligationDetector().detect_and_record(kernel).mutations[0]
    contradiction = next(iter(kernel.state.contradictions.values()))
    creation = mutation.event
    assert set(contradiction.evidence_refs).issubset(creation.triggering_refs)
    assert set(contradiction.claim_ids).issubset(creation.triggering_refs)
    assert contradiction.contradiction_id in creation.triggering_refs


def test_checkpoint_roundtrip_rebuilds_contradiction_view(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=6105, state_dim=16, run_label="contradiction-checkpoint")
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(kernel).mutations[0].obligation
    expected_view = derive_obligation_view(kernel, obligation.kernel_id)
    path = tmp_path / "contradiction.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.snapshot() == kernel.snapshot()
    assert derive_obligation_view(restored, obligation.kernel_id) == expected_view


def test_missing_canonical_claim_invalidates_checkpoint_state() -> None:
    kernel = VerdantKernel(seed=6106, state_dim=16, run_label="contradiction-tamper")
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(kernel).mutations[0].obligation
    state = kernel.snapshot()
    del state.claims[obligation.claim_refs[0]]
    with pytest.raises(KernelInvariantError):
        VerdantKernel.from_state(state)


def test_empty_claim_state_produces_no_obligation() -> None:
    kernel = VerdantKernel(seed=6107, state_dim=16, run_label="no-contradiction")
    report = ContradictionObligationDetector().detect_and_record(kernel)
    assert report.inspected_contradiction_ids == ()
    assert report.candidates == ()
    assert report.mutations == ()
    assert kernel.state.obligation_kernels == {}


def test_dependency_gap_lifecycle_cannot_govern_contradiction_family() -> None:
    kernel = VerdantKernel(seed=6108, state_dim=16, run_label="family-boundary")
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(kernel).mutations[0].obligation
    with pytest.raises(ObligationIntegrityError, match="another family"):
        DependencyGapPipeline().stall(
            kernel,
            obligation.kernel_id,
            source_event_key="invalid-cross-family-stall",
            stall_cause_expression={"operator": "Atom", "cause": "MissingNode"},
            bounded_subgraph_hash="not-applicable",
            reopen_condition={"operator": "Atom", "predicate": "CrossesDependencyCut"},
        )


def test_attention_portfolio_can_allocate_without_resolving_contradiction() -> None:
    kernel = VerdantKernel(seed=6109, state_dim=16, run_label="contradiction-attention")
    _contradict(kernel)
    obligation = ContradictionObligationDetector().detect_and_record(kernel).mutations[0].obligation
    result = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="bounded_contradiction_probe",
                requested_budget=0.10,
                estimated_cost=0.05,
                expected_gain=0.5,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.7,
                generator_version="contradiction-bid-test-v1",
            ),
        ),
        source_event_key="contradiction-attention-001",
    )
    assert result.decision.allocations[0].obligation_id == obligation.kernel_id
    assert result.decision.epistemic_authority_enabled is False
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"
