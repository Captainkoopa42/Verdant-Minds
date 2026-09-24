from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    GovernanceProposalKind,
    KernelInvariantError,
    ObligationEventType,
    ObligationFamily,
    PredictionFailureObligationKernel,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    PredictionFailureDetectionPolicy,
    PredictionFailureDetector,
    derive_obligation_view,
)


def _evidence(kernel: VerdantKernel, key: str, kind: EvidenceKind) -> tuple[str, ...]:
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"prediction-test:{key}",
            modality="controlled_test",
            payload_sha256=hashlib.sha256(key.encode()).hexdigest(),
            feature_vector=(0.1, 0.2),
            concept_labels=("test_system",),
            semantic_evidence_kind=kind,
            semantic_evidence_details={"controlled_key": key},
        )
    )
    return result.additional_evidence_ids


def _outcome(
    kernel: VerdantKernel,
    *,
    suffix: str = "one",
    expected_harm: float = 0.1,
    observed_harm: float = 0.8,
):
    governance = VerdantGovernancePipeline()
    observation = _evidence(kernel, f"observation-{suffix}", EvidenceKind.OBSERVATION)
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation=f"inspect_{suffix}",
        action_class=f"inspection_{suffix}",
        description=f"Controlled inspection {suffix}.",
        evidence_refs=observation,
        relevance=1.0,
        urgency=0.6,
        novelty=0.2,
        predicted_information_gain=1.0,
        harm_risk=expected_harm,
        reversibility=1.0,
    )
    decision = governance.commit(kernel, governance.inspect(kernel, proposal))
    physical = _evidence(kernel, f"outcome-{suffix}", EvidenceKind.OUTCOME)
    return governance.record_outcome(
        kernel,
        decision_event_id=decision.decision_event_id,
        evidence_refs=physical,
        succeeded=True,
        harm_score=observed_harm,
    )


def test_large_native_prediction_error_becomes_persistent_obligation() -> None:
    kernel = VerdantKernel(seed=6201, state_dim=16, run_label="prediction-anchor")
    outcome = _outcome(kernel)
    detector = PredictionFailureDetector()
    before = kernel.fingerprint()
    inspected, candidates = detector.inspect(kernel)
    assert kernel.fingerprint() == before
    assert inspected == (outcome.outcome_id,)
    assert len(candidates) == 1

    mutation = detector.detect_and_record(kernel).mutations[0]
    obligation = mutation.obligation
    assert isinstance(obligation, PredictionFailureObligationKernel)
    assert obligation.family == ObligationFamily.PREDICTION_FAILURE
    assert obligation.expected_value == 0.1
    assert obligation.observed_value == 0.8
    assert obligation.prediction_error == outcome.prediction_error
    assert {obligation.outcome_ref, obligation.prediction_source_ref}.issubset(
        obligation.canonical_triggering_refs
    )
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"


def test_unchanged_detection_replays_at_zero_canonical_cost() -> None:
    kernel = VerdantKernel(seed=6202, state_dim=16, run_label="prediction-replay")
    _outcome(kernel)
    detector = PredictionFailureDetector()
    first = detector.detect_and_record(kernel).mutations[0]
    cycle = kernel.state.cycle
    fingerprint = kernel.fingerprint()
    replay = detector.detect_and_record(kernel).mutations[0]
    assert replay.replayed
    assert replay.obligation.kernel_id == first.obligation.kernel_id
    assert kernel.state.cycle == cycle
    assert kernel.fingerprint() == fingerprint


def test_policy_revision_retriggers_same_failure_without_fragmenting_identity() -> None:
    kernel = VerdantKernel(seed=6203, state_dim=16, run_label="prediction-policy")
    _outcome(kernel)
    first = PredictionFailureDetector().detect_and_record(kernel).mutations[0]
    revised = PredictionFailureDetector(
        PredictionFailureDetectionPolicy(
            policy_version="prediction_failure_detector_test_v2",
            minimum_prediction_error=0.20,
        )
    ).detect_and_record(kernel).mutations[0]
    assert revised.obligation.kernel_id == first.obligation.kernel_id
    events = [
        item for item in kernel.state.obligation_history
        if item.obligation_id == first.obligation.kernel_id
    ]
    assert [item.event_type for item in events] == [
        ObligationEventType.CREATED,
        ObligationEventType.RETRIGGERED,
    ]


def test_below_threshold_outcome_is_inspected_but_not_promoted_to_obligation() -> None:
    kernel = VerdantKernel(seed=6204, state_dim=16, run_label="prediction-threshold")
    outcome = _outcome(kernel, expected_harm=0.20, observed_harm=0.30)
    report = PredictionFailureDetector().detect_and_record(kernel)
    assert report.inspected_outcome_ids == (outcome.outcome_id,)
    assert report.candidates == ()
    assert report.mutations == ()
    assert kernel.state.obligation_kernels == {}


def test_distinct_prediction_events_do_not_overmerge() -> None:
    kernel = VerdantKernel(seed=6205, state_dim=16, run_label="prediction-scope")
    _outcome(kernel, suffix="alpha")
    _outcome(kernel, suffix="beta")
    report = PredictionFailureDetector().detect_and_record(kernel)
    assert len(report.mutations) == 2
    assert len({item.obligation.kernel_id for item in report.mutations}) == 2
    assert len({item.obligation.scope_key for item in report.mutations}) == 2


def test_checkpoint_roundtrip_rebuilds_prediction_failure_view(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=6206, state_dim=16, run_label="prediction-checkpoint")
    _outcome(kernel)
    obligation = PredictionFailureDetector().detect_and_record(kernel).mutations[0].obligation
    expected = derive_obligation_view(kernel, obligation.kernel_id)
    checkpoint = tmp_path / "prediction-failure.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    assert restored.snapshot() == kernel.snapshot()
    assert derive_obligation_view(restored, obligation.kernel_id) == expected


def test_value_or_lineage_tampering_fails_closed() -> None:
    kernel = VerdantKernel(seed=6207, state_dim=16, run_label="prediction-tamper")
    _outcome(kernel)
    obligation = PredictionFailureDetector().detect_and_record(kernel).mutations[0].obligation
    state = kernel.snapshot()
    state.obligation_kernels[obligation.kernel_id] = obligation.model_copy(
        update={"observed_value": 0.7}
    )
    with pytest.raises(KernelInvariantError):
        VerdantKernel.from_state(state)

    native = VerdantKernel(seed=6217, state_dim=16, run_label="native-prediction-tamper")
    _outcome(native)
    native_tamper = native.snapshot()
    native_tamper.governance_outcomes[0] = native_tamper.governance_outcomes[0].model_copy(
        update={"prediction_error": 0.1}
    )
    with pytest.raises(KernelInvariantError, match="prediction error drift"):
        VerdantKernel.from_state(native_tamper)


def test_attention_allocation_does_not_resolve_prediction_failure() -> None:
    kernel = VerdantKernel(seed=6208, state_dim=16, run_label="prediction-attention")
    _outcome(kernel)
    obligation = PredictionFailureDetector().detect_and_record(kernel).mutations[0].obligation
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="bounded_prediction_probe",
                requested_budget=0.10,
                estimated_cost=0.05,
                expected_gain=0.6,
                uncertainty=0.7,
                urgency=0.5,
                novelty=0.6,
                generator_version="prediction-bid-test-v1",
            ),
        ),
        source_event_key="prediction-attention-001",
    ).decision
    assert decision.allocations[0].obligation_id == obligation.kernel_id
    assert not decision.epistemic_authority_enabled
    assert derive_obligation_view(kernel, obligation.kernel_id).current_status.value == "Open"
