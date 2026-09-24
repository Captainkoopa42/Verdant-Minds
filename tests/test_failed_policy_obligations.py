from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDisposition,
    ExperienceCommand,
    FailedPolicyObligationKernel,
    GovernanceProposalKind,
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
    FailedPolicyDetectionPolicy,
    FailedPolicyDetector,
    derive_obligation_view,
)


def _kernel() -> tuple[VerdantKernel, str]:
    kernel = VerdantKernel(seed=6401, state_dim=16, run_label="failed-policy")
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key="policy-evidence",
            source_ref="policy-safety-sensor",
            modality="governance_test",
            payload_sha256=hashlib.sha256(b"policy-evidence").hexdigest(),
            feature_vector=(0.1, 0.2, 0.3),
        )
    )
    return kernel, result.observation_evidence_id


def _deny(
    kernel: VerdantKernel,
    evidence_ref: str,
    *,
    operation: str = "unsafe_actuation",
    action_class: str = "forceful_actuation",
) -> str:
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.ACT,
        operation=operation,
        action_class=action_class,
        description=f"Attempt {operation} under a high-risk test condition.",
        evidence_refs=(evidence_ref,),
        relevance=1.0,
        urgency=0.8,
        novelty=0.2,
        predicted_information_gain=0.3,
        harm_risk=0.95,
        reversibility=0.10,
        safe_alternatives=(f"inspect_before_{operation}",),
    )
    report = governance.inspect(kernel, proposal)
    assert report.disposition == CouncilDisposition.DENY
    assert operation in report.blocked_operations
    return governance.commit(kernel, report).decision_event_id


def _repeated_block() -> tuple[VerdantKernel, str, tuple[str, str]]:
    kernel, evidence = _kernel()
    decisions = (_deny(kernel, evidence), _deny(kernel, evidence))
    return kernel, evidence, decisions


def test_single_safety_denial_is_not_labeled_failed_policy() -> None:
    kernel, evidence = _kernel()
    decision = _deny(kernel, evidence)
    report = FailedPolicyDetector().detect_and_record(kernel)
    assert report.inspected_decision_ids == (decision,)
    assert report.candidates == ()
    assert report.mutations == ()


def test_repeated_governance_block_becomes_failed_policy_obligation() -> None:
    kernel, evidence, decisions = _repeated_block()
    detector = FailedPolicyDetector()
    before = kernel.fingerprint()
    inspected, candidates = detector.inspect(kernel)
    assert kernel.fingerprint() == before
    assert set(decisions) == set(inspected)
    assert len(candidates) == 1

    mutation = detector.detect_and_record(kernel).mutations[0]
    obligation = mutation.obligation
    assert isinstance(obligation, FailedPolicyObligationKernel)
    assert obligation.family == ObligationFamily.FAILED_POLICY
    assert obligation.blocked_decision_refs == tuple(sorted(decisions))
    assert evidence in obligation.canonical_triggering_refs
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"


def test_unchanged_failed_policy_detection_is_zero_cost_replay() -> None:
    kernel, _, _ = _repeated_block()
    detector = FailedPolicyDetector()
    first = detector.detect_and_record(kernel).mutations[0]
    cycle = kernel.state.cycle
    fingerprint = kernel.fingerprint()
    replay = detector.detect_and_record(kernel).mutations[0]
    assert replay.replayed
    assert replay.obligation.kernel_id == first.obligation.kernel_id
    assert kernel.state.cycle == cycle
    assert kernel.fingerprint() == fingerprint


def test_new_block_retriggers_same_scope_without_changing_safety_decisions() -> None:
    kernel, evidence, decisions = _repeated_block()
    first = FailedPolicyDetector().detect_and_record(kernel).mutations[0]
    third = _deny(kernel, evidence)
    second = FailedPolicyDetector().detect_and_record(kernel).mutations[0]
    assert second.obligation.kernel_id == first.obligation.kernel_id
    assert set(decisions + (third,)).issubset(second.event.triggering_refs)
    events = [
        event for event in kernel.state.obligation_history
        if event.obligation_id == first.obligation.kernel_id
    ]
    assert [event.event_type for event in events] == [
        ObligationEventType.CREATED,
        ObligationEventType.RETRIGGERED,
    ]
    assert all(
        event.report.disposition == CouncilDisposition.DENY
        for event in kernel.state.council_decisions
    )


def test_policy_revision_retriggers_same_failed_policy_question() -> None:
    kernel, _, _ = _repeated_block()
    first = FailedPolicyDetector().detect_and_record(kernel).mutations[0]
    revised = FailedPolicyDetector(
        FailedPolicyDetectionPolicy(
            policy_version="failed_policy_detector_test_v2",
            minimum_repeated_denials=2,
        )
    ).detect_and_record(kernel).mutations[0]
    assert revised.obligation.kernel_id == first.obligation.kernel_id
    assert not revised.replayed


def test_independent_governance_scopes_do_not_overmerge() -> None:
    kernel, evidence = _kernel()
    for operation, action_class in (
        ("unsafe_actuation", "forceful_actuation"),
        ("unsafe_release", "hazardous_release"),
    ):
        _deny(kernel, evidence, operation=operation, action_class=action_class)
        _deny(kernel, evidence, operation=operation, action_class=action_class)
    report = FailedPolicyDetector().detect_and_record(kernel)
    assert len(report.mutations) == 2
    assert len({item.obligation.kernel_id for item in report.mutations}) == 2


def test_checkpoint_roundtrip_rebuilds_failed_policy_view(tmp_path: Path) -> None:
    kernel, _, _ = _repeated_block()
    obligation = FailedPolicyDetector().detect_and_record(kernel).mutations[0].obligation
    expected = derive_obligation_view(kernel, obligation.kernel_id)
    checkpoint = tmp_path / "failed-policy.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    assert restored.snapshot() == kernel.snapshot()
    assert derive_obligation_view(restored, obligation.kernel_id) == expected


def test_missing_blocked_decision_fails_closed() -> None:
    kernel, _, _ = _repeated_block()
    obligation = FailedPolicyDetector().detect_and_record(kernel).mutations[0].obligation
    state = kernel.snapshot()
    state.council_decisions = [
        item for item in state.council_decisions
        if item.decision_event_id != obligation.blocked_decision_refs[0]
    ]
    with pytest.raises(KernelInvariantError, match="lost a blocked Council decision"):
        VerdantKernel.from_state(state)


def test_attention_allocation_cannot_change_policy_or_denials() -> None:
    kernel, _, _ = _repeated_block()
    obligation = FailedPolicyDetector().detect_and_record(kernel).mutations[0].obligation
    decisions_before = tuple(kernel.state.council_decisions)
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="bounded_policy_probe",
                requested_budget=0.10,
                estimated_cost=0.05,
                expected_gain=0.6,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.7,
                generator_version="failed-policy-bid-test-v1",
            ),
        ),
        source_event_key="failed-policy-attention-001",
    ).decision
    assert decision.allocations[0].obligation_id == obligation.kernel_id
    assert not decision.epistemic_authority_enabled
    assert tuple(kernel.state.council_decisions) == decisions_before
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"
