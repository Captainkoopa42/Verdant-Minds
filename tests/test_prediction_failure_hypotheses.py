from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    GovernanceProposalKind,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_obligations import (
    PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION,
    PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    PredictionFailureAblationComponent,
    PredictionFailureAblationTarget,
    PredictionFailureDetectionPolicy,
    PredictionFailureDetector,
    PredictionFailureEvidenceReceipt,
    PredictionFailureHypothesis,
    PredictionFailureHypothesisBundle,
    PredictionFailureHypothesisIntegrityError,
    PredictionFailureHypothesisKind,
    PredictionFailureHypothesisProtocol,
)


def _evidence(kernel: VerdantKernel, key: str, kind: EvidenceKind) -> tuple[str, ...]:
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"prediction-hypothesis:{key}",
            modality="controlled_test",
            payload_sha256=hashlib.sha256(key.encode()).hexdigest(),
            feature_vector=(0.1, 0.2),
            concept_labels=("test_system",),
            semantic_evidence_kind=kind,
            semantic_evidence_details={"controlled_key": key},
        )
    )
    return result.additional_evidence_ids


def _outcome(kernel: VerdantKernel, *, suffix: str = "one"):
    governance = VerdantGovernancePipeline()
    forecast_evidence = _evidence(
        kernel, f"observation-{suffix}", EvidenceKind.OBSERVATION
    )
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation=f"inspect_{suffix}",
        action_class=f"inspection_{suffix}",
        description=f"Controlled inspection {suffix}.",
        evidence_refs=forecast_evidence,
        relevance=1.0,
        urgency=0.6,
        novelty=0.2,
        predicted_information_gain=1.0,
        harm_risk=0.1,
        reversibility=1.0,
    )
    decision = governance.commit(kernel, governance.inspect(kernel, proposal))
    outcome_evidence = _evidence(kernel, f"outcome-{suffix}", EvidenceKind.OUTCOME)
    outcome = governance.record_outcome(
        kernel,
        decision_event_id=decision.decision_event_id,
        evidence_refs=outcome_evidence,
        succeeded=True,
        harm_score=0.8,
    )
    return outcome, decision, proposal


def _authorize(
    kernel: VerdantKernel,
    obligation_ids: tuple[str, ...],
    *,
    action_operator: str = PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR,
    generator_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION,
    requested_budget: float = 0.05,
    include_forecast_evidence: bool = True,
    source_event_key: str = "prediction-failure-hypothesis-attention",
):
    inputs = []
    for obligation_id in sorted(obligation_ids):
        obligation = kernel.state.obligation_kernels[obligation_id]
        event = next(
            item
            for item in reversed(kernel.state.obligation_history)
            if item.obligation_id == obligation_id
        )
        decision = next(
            item
            for item in kernel.state.council_decisions
            if item.decision_event_id == obligation.prediction_source_ref
        )
        provenance = set(event.triggering_refs)
        if include_forecast_evidence:
            provenance.update(decision.report.proposal.evidence_refs)
        inputs.append(
            AttentionBidInput(
                obligation_id=obligation_id,
                action_operator=action_operator,
                requested_budget=requested_budget,
                estimated_cost=requested_budget,
                expected_gain=0.55,
                uncertainty=0.85,
                urgency=0.50,
                novelty=0.75,
                metric_provenance_refs=tuple(sorted(provenance)),
                generator_version=generator_version,
            )
        )
    decision = AttentionPortfolio().decide(
        kernel,
        tuple(inputs),
        source_event_key=source_event_key,
    ).decision
    return {item.obligation_id: item for item in decision.allocations}


def _prepared(
    *,
    seed: int = 7001,
    action_operator: str = PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR,
    generator_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION,
    requested_budget: float = 0.05,
    include_forecast_evidence: bool = True,
):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"prediction-failure-hypothesis-{seed}",
    )
    outcome, decision, proposal = _outcome(kernel)
    obligation = PredictionFailureDetector().detect_and_record(
        kernel
    ).mutations[0].obligation
    allocation = _authorize(
        kernel,
        (obligation.kernel_id,),
        action_operator=action_operator,
        generator_version=generator_version,
        requested_budget=requested_budget,
        include_forecast_evidence=include_forecast_evidence,
        source_event_key=f"prediction-failure-hypothesis-attention-{seed}",
    )[obligation.kernel_id]
    return kernel, obligation, allocation, outcome, decision, proposal


def test_protocol_preserves_native_lineage_and_mandatory_alternatives() -> None:
    kernel, obligation, allocation, outcome, decision, proposal = _prepared()
    protocol = PredictionFailureHypothesisProtocol()
    before = kernel.fingerprint()

    bundle = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )

    assert kernel.fingerprint() == before
    assert protocol.validate(kernel, bundle) == bundle
    receipt = bundle.evidence_receipt
    assert receipt.outcome_ref == outcome.outcome_id
    assert receipt.prediction_source_ref == decision.decision_event_id
    assert receipt.proposal_ref == proposal.proposal_id
    assert receipt.forecast_basis_evidence_refs == proposal.evidence_refs
    assert receipt.decision_evidence_refs == decision.evidence_refs
    assert receipt.outcome_evidence_refs == outcome.evidence_refs
    assert receipt.protected_evidence_refs == tuple(
        sorted(set(decision.evidence_refs).union(outcome.evidence_refs))
    )
    assert receipt.ablation_target.component == (
        PredictionFailureAblationComponent.DECLARED_HARM_RISK
    )
    assert receipt.ablation_target.declared_value == proposal.harm_risk
    assert {item.kind for item in bundle.hypotheses} == set(
        PredictionFailureHypothesisKind
    )
    assert bundle.selected_hypothesis_ref is None
    assert not bundle.matched_trial_executed
    assert not bundle.ablation_outcome_observed
    assert not bundle.causal_attribution_enabled
    assert not bundle.resolution_authority_enabled
    assert not bundle.canonical_commit_permitted
    for hypothesis in bundle.hypotheses:
        assert hypothesis.matched_trial_required
        assert not hypothesis.selected
        assert hypothesis.protected_evidence_refs == receipt.protected_evidence_refs
        assert hypothesis.ablation_target_ref == receipt.ablation_target.target_id


def test_prediction_and_outcome_source_partitions_remain_visible() -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(seed=7002)
    receipt = PredictionFailureHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    ).evidence_receipt

    assert receipt.shared_evidence_refs == ()
    assert receipt.shared_source_roots == ()
    assert receipt.forecast_basis_source_roots == (
        "prediction-hypothesis:observation-one:observation",
    )
    assert receipt.outcome_source_roots == (
        "prediction-hypothesis:outcome-one:outcome",
    )


def test_checkpoint_and_mapping_order_replay_exact_bundle(tmp_path: Path) -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(seed=7003)
    protocol = PredictionFailureHypothesisProtocol()
    expected = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    checkpoint = tmp_path / "prediction-failure-hypothesis.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(
        reversed(tuple(state.obligation_kernels.items()))
    )
    restored = VerdantKernel.from_state(state)

    assert protocol.generate(
        restored,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    ) == expected
    assert PredictionFailureHypothesisBundle.model_validate(
        expected.model_dump(mode="json")
    ) == expected


@pytest.mark.parametrize(
    ("action_operator", "generator_version"),
    (
        ("generic_probe", PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION),
        (
            PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR,
            "foreign-generator-v1",
        ),
    ),
)
def test_wrong_attention_authorization_fails_closed(
    action_operator: str,
    generator_version: str,
) -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(
        seed=7004 if action_operator == "generic_probe" else 7005,
        action_operator=action_operator,
        generator_version=generator_version,
    )
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="does not authorize",
    ):
        PredictionFailureHypothesisProtocol().generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id=allocation.allocation_id,
        )


def test_unknown_underfunded_and_evidence_suppressing_allocations_fail() -> None:
    kernel, obligation, _, _, _, _ = _prepared(seed=7006)
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="one canonical Attention allocation",
    ):
        PredictionFailureHypothesisProtocol().generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id="forged-allocation",
        )

    small, small_obligation, small_allocation, _, _, _ = _prepared(
        seed=7007,
        requested_budget=0.01,
    )
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="below the PredictionFailure protocol minimum",
    ):
        PredictionFailureHypothesisProtocol().generate(
            small,
            obligation_id=small_obligation.kernel_id,
            attention_allocation_id=small_allocation.allocation_id,
        )

    suppressed, suppressed_obligation, suppressed_allocation, _, _, _ = _prepared(
        seed=7008,
        include_forecast_evidence=False,
    )
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="suppressed PredictionFailure triggering or forecast evidence",
    ):
        PredictionFailureHypothesisProtocol().generate(
            suppressed,
            obligation_id=suppressed_obligation.kernel_id,
            attention_allocation_id=suppressed_allocation.allocation_id,
        )


def test_retrigger_invalidates_stale_attention_basis() -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(seed=7009)
    protocol = PredictionFailureHypothesisProtocol()
    protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    retrigger = PredictionFailureDetector(
        PredictionFailureDetectionPolicy(
            policy_version="prediction_failure_detector_retrigger_v2",
            minimum_prediction_error=0.2,
        )
    ).detect_and_record(kernel).mutations[0]
    assert not retrigger.replayed

    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="stale relative to PredictionFailure history",
    ):
        protocol.generate(
            kernel,
            obligation_id=obligation.kernel_id,
            attention_allocation_id=allocation.allocation_id,
        )


def test_foreign_obligation_allocation_cannot_cross_contaminate_bundle() -> None:
    kernel = VerdantKernel(
        seed=7010,
        state_dim=16,
        run_label="prediction-failure-hypothesis-cross-scope",
    )
    _outcome(kernel, suffix="alpha")
    _outcome(kernel, suffix="beta")
    obligations = tuple(
        item.obligation
        for item in PredictionFailureDetector().detect_and_record(kernel).mutations
    )
    allocations = _authorize(
        kernel,
        tuple(item.kernel_id for item in obligations),
        source_event_key="prediction-failure-cross-scope-attention",
    )
    first, second = obligations
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="belongs to another obligation",
    ):
        PredictionFailureHypothesisProtocol().generate(
            kernel,
            obligation_id=first.kernel_id,
            attention_allocation_id=allocations[second.kernel_id].allocation_id,
        )


def test_models_reject_evidence_suppression_missing_arms_and_authority() -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(seed=7011)
    bundle = PredictionFailureHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    receipt_payload = bundle.evidence_receipt.model_dump(
        mode="json", exclude={"receipt_id"}
    )
    receipt_payload["ablation_target"] = bundle.evidence_receipt.ablation_target
    receipt_payload["protected_evidence_refs"] = receipt_payload[
        "protected_evidence_refs"
    ][:-1]
    with pytest.raises(ValueError, match="suppressed canonical evidence"):
        PredictionFailureEvidenceReceipt.build(**receipt_payload)

    bundle_payload = bundle.model_dump(mode="json")
    bundle_payload["hypotheses"] = bundle_payload["hypotheses"][:-1]
    with pytest.raises(ValueError):
        PredictionFailureHypothesisBundle.model_validate(bundle_payload)

    target_payload = bundle.evidence_receipt.ablation_target.model_dump(
        mode="json", exclude={"target_id"}
    )
    target_payload["causal_target_asserted"] = True
    with pytest.raises(ValueError, match="cannot claim execution or cause"):
        PredictionFailureAblationTarget.build(**target_payload)

    hypothesis = bundle.hypotheses[0]
    hypothesis_payload = hypothesis.model_dump(
        mode="json", exclude={"hypothesis_id"}
    )
    hypothesis_payload["selected"] = True
    with pytest.raises(ValueError, match="cannot carry authority"):
        PredictionFailureHypothesis.build(**hypothesis_payload)


def test_fully_rehashed_context_forgery_fails_canonical_validation() -> None:
    kernel, obligation, allocation, _, _, _ = _prepared(seed=7012)
    protocol = PredictionFailureHypothesisProtocol()
    bundle = protocol.generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    receipt_payload = bundle.evidence_receipt.model_dump(
        mode="json", exclude={"receipt_id"}
    )
    receipt_payload["ablation_target"] = bundle.evidence_receipt.ablation_target
    forged_context = "0" * 64
    receipt_payload["context_snapshot_sha256"] = forged_context
    forged_receipt = PredictionFailureEvidenceReceipt.build(**receipt_payload)
    forged_provenance = tuple(
        sorted(
            {
                obligation.kernel_id,
                bundle.obligation_event_ref,
                bundle.attention_decision_ref,
                bundle.attention_bid_ref,
                bundle.attention_allocation_ref,
                forged_receipt.receipt_id,
                forged_receipt.outcome_ref,
                forged_receipt.prediction_source_ref,
                forged_receipt.proposal_ref,
                forged_receipt.council_report_ref,
                forged_receipt.ablation_target.target_id,
                *forged_receipt.protected_evidence_refs,
            }
        )
    )
    forged_hypotheses = tuple(
        PredictionFailureHypothesis.build(
            obligation_id=obligation.kernel_id,
            outcome_ref=forged_receipt.outcome_ref,
            kind=kind,
            ablation_target_ref=forged_receipt.ablation_target.target_id,
            evidence_receipt_ref=forged_receipt.receipt_id,
            protected_evidence_refs=forged_receipt.protected_evidence_refs,
            provenance_refs=forged_provenance,
        )
        for kind in PredictionFailureHypothesisKind
    )
    forged_bundle = PredictionFailureHypothesisBundle.build(
        obligation_id=obligation.kernel_id,
        obligation_event_ref=bundle.obligation_event_ref,
        attention_decision_ref=bundle.attention_decision_ref,
        attention_bid_ref=bundle.attention_bid_ref,
        attention_allocation_ref=bundle.attention_allocation_ref,
        context_snapshot_sha256=forged_context,
        evidence_receipt=forged_receipt,
        hypotheses=forged_hypotheses,
    )
    assert forged_bundle.bundle_id != bundle.bundle_id
    with pytest.raises(
        PredictionFailureHypothesisIntegrityError,
        match="does not match canonical provenance",
    ):
        protocol.validate(kernel, forged_bundle)
