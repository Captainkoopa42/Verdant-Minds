from __future__ import annotations

import hashlib
import json
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
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION,
    PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR,
    PREDICTION_FAILURE_TRIAL_ARM_ORDER,
    PREDICTION_FAILURE_TRIAL_DISPOSITION_PRECEDENCE,
    PREDICTION_FAILURE_TRIAL_ERROR_FORMULA,
    PREDICTION_FAILURE_TRIAL_OBSERVED_VALUE_SOURCE,
    PREDICTION_FAILURE_TRIAL_PLAN_VERSION,
    PREDICTION_FAILURE_RISK_OPERATOR_VERSION,
    PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION,
    PREDICTION_FAILURE_TRIAL_TARGET_DELTA_FORMULA,
    PREDICTION_FAILURE_TRIAL_TRACE_VALUE_FIELD,
    PREDICTION_FAILURE_TRIAL_VALID_NULL_DELTA_FORMULA,
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
    PredictionFailureSimulationInputProjection,
    PredictionFailureGovernanceRiskOperator,
    PredictionFailureRiskProjection,
    PredictionFailureRiskSource,
    PredictionFailureRiskReceiptRecorder,
    PredictionFailureRiskReceiptIntegrityError,
    PredictionFailureTrialArm,
    PredictionFailureTrialArmDeclaration,
    PredictionFailureTrialDeclaration,
    PredictionFailureTrialOutcomePolicy,
    PredictionFailureTrialPlanBundle,
    PredictionFailureTrialPlanIntegrityError,
    PredictionFailureTrialPlanMaterializer,
    PredictionFailureTrialPreregistrationIntegrityError,
    PredictionFailureTrialPreregistrar,
    PredictionFailureTrialSimulationPlan,
    load_prediction_failure_trial_plan,
    load_prediction_failure_risk_receipt,
    load_prediction_failure_trial_preregistration,
    prediction_failure_trial_plan_bytes,
    prediction_failure_risk_receipt_bytes,
    prediction_failure_trial_preregistration_bytes,
    read_prediction_failure_trial_plan,
    read_prediction_failure_risk_receipt,
    save_prediction_failure_risk_receipt,
    read_prediction_failure_trial_preregistration,
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


def _outcome(kernel: VerdantKernel, *, suffix: str = "one", declared_harm_risk: float = 0.1):
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
        harm_risk=declared_harm_risk,
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


def _trial_bundle(seed: int):
    kernel, obligation, allocation, _, _, _ = _prepared(seed=seed)
    bundle = PredictionFailureHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    return kernel, bundle


def test_trial_preregistration_freezes_matched_design_without_execution(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7101)
    before = kernel.fingerprint()
    path = tmp_path / "prediction-failure-trial.vfp"

    envelope = PredictionFailureTrialPreregistrar().register(
        path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )

    declaration = envelope.declaration
    policy = declaration.outcome_policy
    assert kernel.fingerprint() == before
    assert declaration.canonical_fingerprint == before
    assert declaration.hypothesis_bundle == bundle
    assert tuple(item.arm for item in declaration.arms) == (
        PREDICTION_FAILURE_TRIAL_ARM_ORDER
    )
    assert tuple(
        (
            item.target_present,
            item.target_ablation_requested,
            item.no_op_control,
        )
        for item in declaration.arms
    ) == (
        (True, False, False),
        (False, True, False),
        (True, False, True),
    )
    assert {item.shared_design_seed for item in declaration.arms} == {
        declaration.shared_design_seed
    }
    assert {item.matched_control_signature for item in declaration.arms} == {
        declaration.matched_control_signature
    }
    assert {item.requested_budget for item in declaration.arms} == {0.015}
    assert policy.total_budget == 0.045
    assert policy.total_budget <= bundle.evidence_receipt.authorized_budget
    assert policy.trace_value_field == PREDICTION_FAILURE_TRIAL_TRACE_VALUE_FIELD
    assert (
        policy.observed_value_source
        == PREDICTION_FAILURE_TRIAL_OBSERVED_VALUE_SOURCE
    )
    assert policy.error_formula == PREDICTION_FAILURE_TRIAL_ERROR_FORMULA
    assert (
        policy.target_delta_formula
        == PREDICTION_FAILURE_TRIAL_TARGET_DELTA_FORMULA
    )
    assert (
        policy.valid_null_delta_formula
        == PREDICTION_FAILURE_TRIAL_VALID_NULL_DELTA_FORMULA
    )
    assert (
        policy.disposition_precedence
        == PREDICTION_FAILURE_TRIAL_DISPOSITION_PRECEDENCE
    )
    assert set(bundle.evidence_receipt.protected_evidence_refs).issubset(
        declaration.held_constant_refs
    )
    assert {item.hypothesis_id for item in bundle.hypotheses}.issubset(
        declaration.held_constant_refs
    )
    assert not declaration.runner_implemented
    assert not declaration.execution_plans_materialized
    assert not declaration.trial_executed
    assert not declaration.traces_observed
    assert not declaration.outcomes_observed
    assert not declaration.target_specific_effect_observed
    assert not declaration.causal_attribution_enabled
    assert not declaration.resolution_authority_enabled
    assert not declaration.promotion_authority_enabled
    assert not declaration.policy_rewrite_authority_enabled
    assert not declaration.canonical_commit_permitted
    assert path.read_bytes() == (
        prediction_failure_trial_preregistration_bytes(envelope)
    )


def test_trial_preregistration_checkpoint_replay_is_exact_and_idempotent(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7102)
    checkpoint = tmp_path / "prediction-failure-trial.vdk"
    path = tmp_path / "prediction-failure-trial.vfp"
    save_checkpoint(checkpoint, kernel.snapshot())
    registrar = PredictionFailureTrialPreregistrar()
    expected = registrar.register(
        path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    first_bytes = path.read_bytes()

    assert registrar.register(
        path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    ) == expected
    assert path.read_bytes() == first_bytes

    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(
        reversed(tuple(state.obligation_kernels.items()))
    )
    restored = VerdantKernel.from_state(state)
    assert restored.fingerprint() == kernel.fingerprint()
    assert load_prediction_failure_trial_preregistration(
        path,
        kernel=restored,
    ) == expected
    assert PredictionFailureTrialDeclaration.build(
        kernel=restored,
        hypothesis_bundle=bundle,
    ) == expected.declaration


def test_trial_preregistration_rejects_foreign_and_stale_checkpoints(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7103)
    path = tmp_path / "prediction-failure-trial.vfp"
    PredictionFailureTrialPreregistrar().register(
        path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    foreign, _ = _trial_bundle(7104)
    with pytest.raises(
        PredictionFailureTrialPreregistrationIntegrityError,
        match="another canonical checkpoint",
    ):
        load_prediction_failure_trial_preregistration(path, kernel=foreign)

    PredictionFailureDetector(
        PredictionFailureDetectionPolicy(
            policy_version="prediction_failure_trial_retrigger_v2",
            minimum_prediction_error=0.2,
        )
    ).detect_and_record(kernel)
    with pytest.raises(
        PredictionFailureTrialPreregistrationIntegrityError,
        match="another canonical checkpoint",
    ):
        load_prediction_failure_trial_preregistration(path, kernel=kernel)


def test_trial_preregistration_rejects_foreign_bundle_before_write(
    tmp_path: Path,
) -> None:
    kernel, _ = _trial_bundle(7105)
    _, foreign_bundle = _trial_bundle(7106)
    path = tmp_path / "foreign-bundle.vfp"

    with pytest.raises(PredictionFailureTrialPreregistrationIntegrityError):
        PredictionFailureTrialPreregistrar().register(
            path,
            kernel=kernel,
            hypothesis_bundle=foreign_bundle,
        )
    assert not path.exists()


def test_trial_preregistration_path_is_first_committer_wins(
    tmp_path: Path,
) -> None:
    first_kernel, first_bundle = _trial_bundle(7107)
    second_kernel, second_bundle = _trial_bundle(7108)
    path = tmp_path / "immutable.vfp"
    registrar = PredictionFailureTrialPreregistrar()
    first = registrar.register(
        path,
        kernel=first_kernel,
        hypothesis_bundle=first_bundle,
    )
    first_bytes = path.read_bytes()

    with pytest.raises(
        PredictionFailureTrialPreregistrationIntegrityError,
        match="different evidence",
    ):
        registrar.register(
            path,
            kernel=second_kernel,
            hypothesis_bundle=second_bundle,
        )
    assert path.read_bytes() == first_bytes
    assert load_prediction_failure_trial_preregistration(
        path,
        kernel=first_kernel,
    ) == first


def test_trial_preregistration_tamper_and_noncanonical_bytes_fail(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7109)
    canonical_path = tmp_path / "canonical.vfp"
    envelope = PredictionFailureTrialPreregistrar().register(
        canonical_path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    data = prediction_failure_trial_preregistration_bytes(envelope)

    changed = bytearray(data)
    changed[-2] ^= 1
    tampered_path = tmp_path / "tampered.vfp"
    tampered_path.write_bytes(changed)
    with pytest.raises(PredictionFailureTrialPreregistrationIntegrityError):
        read_prediction_failure_trial_preregistration(tampered_path)

    noncanonical_path = tmp_path / "noncanonical.vfp"
    noncanonical_path.write_bytes(data + b"\n")
    with pytest.raises(
        PredictionFailureTrialPreregistrationIntegrityError,
        match="not canonical",
    ):
        read_prediction_failure_trial_preregistration(noncanonical_path)


def test_trial_preregistration_fully_rehashed_authority_forgery_fails(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7110)
    source = tmp_path / "source.vfp"
    envelope = PredictionFailureTrialPreregistrar().register(
        source,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    payload = json.loads(
        prediction_failure_trial_preregistration_bytes(envelope)
    )
    declaration = payload["declaration"]
    declaration["trial_executed"] = True
    declaration["declaration_id"] = stable_id(
        "prediction_failure_trial_declaration",
        {
            key: value
            for key, value in declaration.items()
            if key != "declaration_id"
        },
    )
    payload["declaration_sha256"] = hashlib.sha256(
        canonical_json_bytes(declaration)
    ).hexdigest()
    forged = tmp_path / "authority-forgery.vfp"
    forged.write_bytes(canonical_json_bytes(payload))

    with pytest.raises(PredictionFailureTrialPreregistrationIntegrityError):
        read_prediction_failure_trial_preregistration(forged)


def test_trial_preregistration_fully_rehashed_evidence_suppression_fails(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7111)
    envelope = PredictionFailureTrialPreregistrar().register(
        tmp_path / "evidence-source.vfp",
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    declaration = envelope.declaration
    payload = declaration.model_dump(mode="json")
    suppressed_ref = bundle.evidence_receipt.protected_evidence_refs[0]
    held_refs = tuple(
        item
        for item in declaration.held_constant_refs
        if item != suppressed_ref
    )
    held_sha = hashlib.sha256(canonical_json_bytes(held_refs)).hexdigest()
    signature = stable_id(
        "prediction_failure_trial_matched_control",
        PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION,
        declaration.canonical_kernel_id,
        declaration.canonical_fingerprint,
        bundle.bundle_id,
        declaration.target_ref,
        held_sha,
        declaration.shared_design_seed,
        declaration.outcome_policy_sha256,
    )
    arms = tuple(
        PredictionFailureTrialArmDeclaration.build(
            arm=item.arm,
            target_ref=declaration.target_ref,
            shared_design_seed=declaration.shared_design_seed,
            requested_budget=declaration.outcome_policy.per_arm_budget,
            held_constant_ref_set_sha256=held_sha,
            matched_control_signature=signature,
        )
        for item in declaration.arms
    )
    payload["held_constant_refs"] = held_refs
    payload["held_constant_ref_set_sha256"] = held_sha
    payload["matched_control_signature"] = signature
    payload["arms"] = [item.model_dump(mode="json") for item in arms]
    payload["arm_refs"] = [item.arm_id for item in arms]
    payload["declaration_id"] = stable_id(
        "prediction_failure_trial_declaration",
        {
            key: value
            for key, value in payload.items()
            if key != "declaration_id"
        },
    )

    with pytest.raises(ValueError, match="changed its frozen design"):
        PredictionFailureTrialDeclaration.model_validate(payload)


def test_trial_preregistration_models_reject_policy_and_arm_drift(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="crossed its fixed grammar"):
        PredictionFailureTrialOutcomePolicy(
            target_error_change_threshold=0.10
        )

    kernel, bundle = _trial_bundle(7112)
    envelope = PredictionFailureTrialPreregistrar().register(
        tmp_path / "model-source.vfp",
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    valid_null = next(
        item
        for item in envelope.declaration.arms
        if item.arm == PredictionFailureTrialArm.VALID_NULL
    )
    payload = valid_null.model_dump(mode="json")
    payload["target_present"] = False
    payload["arm_id"] = stable_id(
        "prediction_failure_trial_arm",
        {key: value for key, value in payload.items() if key != "arm_id"},
    )
    with pytest.raises(ValueError, match="crossed its pre-execution boundary"):
        PredictionFailureTrialArmDeclaration.model_validate(payload)


def test_trial_preregistration_checks_size_before_json_parse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import verdant_obligations.prediction_failure_trial_preregistration as module

    path = tmp_path / "oversized.vfp"
    path.write_bytes(b"not-json-but-too-large")
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(
        PredictionFailureTrialPreregistrationIntegrityError,
        match="exceeds its size limit",
    ):
        read_prediction_failure_trial_preregistration(path)


def _trial_plan_fixture(tmp_path: Path, seed: int, stem: str = "trial"):
    kernel, bundle = _trial_bundle(seed)
    preregistration_path = tmp_path / f"{stem}.vfp"
    plan_path = tmp_path / f"{stem}.vpp"
    preregistration = PredictionFailureTrialPreregistrar().register(
        preregistration_path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    plan_envelope = PredictionFailureTrialPlanMaterializer().materialize(
        plan_path,
        kernel=kernel,
        preregistration_path=preregistration_path,
    )
    return (
        kernel,
        bundle,
        preregistration_path,
        preregistration,
        plan_path,
        plan_envelope,
    )


def _risk_receipt_fixture(tmp_path: Path, seed: int, stem: str = "receipt"):
    kernel, bundle, prereg_path, _, plan_path, _ = _trial_plan_fixture(
        tmp_path, seed, stem,
    )
    path = tmp_path / f"{stem}.vfr"
    envelope = PredictionFailureRiskReceiptRecorder().record(
        path, kernel=kernel, plan_path=plan_path,
        preregistration_path=prereg_path,
    )
    return kernel, bundle, prereg_path, plan_path, path, envelope


def _rehash_risk_receipt(payload: dict) -> bytes:
    receipt = payload["receipt"]
    evaluation = receipt["evaluation"]
    for projection in evaluation["projections"]:
        projection["projection_id"] = stable_id(
            "prediction_failure_risk_projection",
            {k: v for k, v in projection.items() if k != "projection_id"},
        )
    evaluation["evaluation_id"] = stable_id(
        "prediction_failure_risk_evaluation",
        {k: v for k, v in evaluation.items() if k != "evaluation_id"},
    )
    receipt["receipt_id"] = stable_id(
        "prediction_failure_risk_receipt",
        {k: v for k, v in receipt.items() if k != "receipt_id"},
    )
    payload["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(receipt)
    ).hexdigest()
    return canonical_json_bytes(payload)


def test_risk_receipt_checkpoint_replay_preserves_abstention_and_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from verdant_obligations import CounterfactualRuntime

    kernel, bundle, prereg_path, _, plan_path, plan = _trial_plan_fixture(
        tmp_path, 7401,
    )
    before = kernel.fingerprint()
    original_inputs = (prereg_path.read_bytes(), plan_path.read_bytes())
    checkpoint = tmp_path / "receipt.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    original_checkpoint = checkpoint.read_bytes()

    def forbidden_runtime(*args, **kwargs):
        raise AssertionError("Risk receipt must not instantiate a simulation runtime")

    monkeypatch.setattr(CounterfactualRuntime, "__init__", forbidden_runtime)
    path = tmp_path / "receipt.vfr"
    recorder = PredictionFailureRiskReceiptRecorder()
    envelope = recorder.record(
        path, kernel=kernel, plan_path=plan_path,
        preregistration_path=prereg_path,
    )
    receipt = envelope.receipt
    assert receipt.plan_bundle_ref == plan.plan_bundle.plan_bundle_id
    assert receipt.plan_sha256 == hashlib.sha256(original_inputs[1]).hexdigest()
    assert receipt.preregistration_sha256 == hashlib.sha256(original_inputs[0]).hexdigest()
    assert receipt.evaluation == PredictionFailureGovernanceRiskOperator().evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path,
    )
    ablation = receipt.evaluation.projections[1]
    assert ablation.predicted_harm_score is None
    assert ablation.source == PredictionFailureRiskSource.INSUFFICIENT_EVIDENCE
    assert bundle.evidence_receipt.outcome_ref not in ablation.supporting_refs
    assert not receipt.matched_trial_executed
    assert not receipt.simulation_trace_observed
    assert not receipt.trial_result_observed
    assert not receipt.canonical_commit_permitted
    data = path.read_bytes()
    assert data == prediction_failure_risk_receipt_bytes(envelope)
    assert read_prediction_failure_risk_receipt(path) == envelope

    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(reversed(tuple(state.obligation_kernels.items())))
    restored = VerdantKernel.from_state(state)
    assert load_prediction_failure_risk_receipt(
        path, kernel=restored, plan_path=plan_path,
        preregistration_path=prereg_path,
    ) == envelope
    assert recorder.record(
        path, kernel=restored, plan_path=plan_path,
        preregistration_path=prereg_path,
    ) == envelope
    assert path.read_bytes() == data
    assert kernel.fingerprint() == restored.fingerprint() == before
    save_checkpoint(checkpoint, kernel.snapshot())
    assert checkpoint.read_bytes() == original_checkpoint
    assert (prereg_path.read_bytes(), plan_path.read_bytes()) == original_inputs


def test_risk_receipt_preserves_distinct_prior_outcome_support(tmp_path: Path) -> None:
    kernel, _, prior, target, prereg_path, plan_path, evaluation = _risk_prior_fixture(
        tmp_path, 7402,
    )
    path = tmp_path / "prior.vfr"
    envelope = PredictionFailureRiskReceiptRecorder().record(
        path, kernel=kernel, plan_path=plan_path,
        preregistration_path=prereg_path,
    )
    assert envelope.receipt.evaluation == evaluation
    assert all(
        p.predicted_harm_score == prior.learned_risk_after
        and prior.outcome_id in p.supporting_refs
        and target.outcome_id not in p.supporting_refs
        and not set(target.evidence_refs).intersection(p.supporting_refs)
        for p in envelope.receipt.evaluation.projections
    )
    assert load_prediction_failure_risk_receipt(
        path, kernel=kernel, plan_path=plan_path,
        preregistration_path=prereg_path,
    ) == envelope


def test_risk_receipt_rejects_foreign_stale_and_substituted_inputs(tmp_path: Path) -> None:
    kernel, _, prereg_path, plan_path, path, envelope = _risk_receipt_fixture(
        tmp_path, 7403, "first",
    )
    foreign, _, foreign_prereg, foreign_plan, _, _ = _risk_receipt_fixture(
        tmp_path, 7404, "foreign",
    )
    original = path.read_bytes()
    for context, plan, prereg in (
        (foreign, plan_path, prereg_path),
        (kernel, foreign_plan, foreign_prereg),
        (kernel, plan_path, foreign_prereg),
        (kernel, foreign_plan, prereg_path),
        (kernel, plan_path, tmp_path / "missing.vfp"),
    ):
        with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
            load_prediction_failure_risk_receipt(
                path, kernel=context, plan_path=plan,
                preregistration_path=prereg,
            )
        unpublished = tmp_path / "unpublished.vfr"
        with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
            save_prediction_failure_risk_receipt(
                unpublished, envelope, kernel=context, plan_path=plan,
                preregistration_path=prereg,
            )
        assert not unpublished.exists()
    _evidence(kernel, "stale-risk-receipt", EvidenceKind.OBSERVATION)
    before = kernel.fingerprint()
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
        load_prediction_failure_risk_receipt(
            path, kernel=kernel, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    assert path.read_bytes() == original
    assert kernel.fingerprint() == before


def test_risk_receipt_path_is_immutable_and_separate_from_inputs(tmp_path: Path) -> None:
    kernel, _, prereg_path, plan_path, path, _ = _risk_receipt_fixture(
        tmp_path, 7405, "first",
    )
    foreign, _, foreign_prereg, _, foreign_plan, _ = _trial_plan_fixture(
        tmp_path, 7406, "foreign",
    )
    original = path.read_bytes()
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
        PredictionFailureRiskReceiptRecorder().record(
            path, kernel=foreign, plan_path=foreign_plan,
            preregistration_path=foreign_prereg,
        )
    assert path.read_bytes() == original
    for occupied in (plan_path, prereg_path):
        before = occupied.read_bytes()
        with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="separate"):
            PredictionFailureRiskReceiptRecorder().record(
                occupied, kernel=kernel, plan_path=plan_path,
                preregistration_path=prereg_path,
            )
        assert occupied.read_bytes() == before


@pytest.mark.parametrize("attack", (
    "score", "suppress_support", "inject_target_outcome", "synthetic_ablation",
    "swap_plan_refs", "input_digest",
))
def test_risk_receipt_rehashed_output_forgery_needs_exact_provenance(
    tmp_path: Path, attack: str,
) -> None:
    kernel, bundle, prereg_path, plan_path, path, envelope = _risk_receipt_fixture(
        tmp_path, 7407,
    )
    payload = envelope.model_dump(mode="json")
    projections = payload["receipt"]["evaluation"]["projections"]
    if attack == "score":
        projections[0]["predicted_harm_score"] = 0.9
    elif attack == "suppress_support":
        projections[0]["supporting_refs"] = projections[0]["supporting_refs"][1:]
    elif attack == "inject_target_outcome":
        projections[0]["supporting_refs"] = sorted(set(
            (*projections[0]["supporting_refs"], bundle.evidence_receipt.outcome_ref)
        ))
    elif attack == "synthetic_ablation":
        projections[1]["source"] = PredictionFailureRiskSource.PRIOR_OUTCOME_LEARNING.value
        projections[1]["predicted_harm_score"] = 0.0
        projections[1]["reason"] = None
    elif attack == "swap_plan_refs":
        projections[0]["plan_ref"], projections[2]["plan_ref"] = (
            projections[2]["plan_ref"], projections[0]["plan_ref"]
        )
    else:
        payload["receipt"]["plan_sha256"] = "0" * 64
    forged = tmp_path / "forged.vfr"
    forged.write_bytes(_rehash_risk_receipt(payload))
    # These forgeries are locally self-consistent; only exact input replay
    # establishes whether the operator really produced the declared output.
    untrusted = read_prediction_failure_risk_receipt(forged)
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="provenance"):
        load_prediction_failure_risk_receipt(
            forged, kernel=kernel, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    unpublished = tmp_path / "unpublished.vfr"
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="provenance"):
        save_prediction_failure_risk_receipt(
            unpublished, untrusted, kernel=kernel, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    assert not unpublished.exists()
    assert path.read_bytes() == prediction_failure_risk_receipt_bytes(envelope)


def test_risk_receipt_rehashed_authority_and_claims_fail_closed(tmp_path: Path) -> None:
    _, _, _, _, _, envelope = _risk_receipt_fixture(tmp_path, 7408)
    receipt_flags = (
        "matched_trial_executed", "simulation_trace_observed", "trial_result_observed",
        "causal_attribution_enabled", "resolution_authority_enabled",
        "promotion_authority_enabled", "policy_rewrite_authority_enabled",
        "canonical_commit_permitted",
    )
    for level, flags in (
        ("receipt", receipt_flags),
        ("evaluation", ("matched_trial_executed", "result_observed",
                        "resolution_authority_enabled", "canonical_commit_permitted")),
        ("projection", ("simulation_trace_observed", "trial_result_observed",
                        "canonical_commit_permitted")),
    ):
        for flag in flags:
            payload = envelope.model_dump(mode="json")
            target = payload["receipt"]
            if level != "receipt":
                target = target["evaluation"]
            if level == "projection":
                target = target["projections"][0]
            target[flag] = True
            path = tmp_path / "authority.vfr"
            path.write_bytes(_rehash_risk_receipt(payload))
            with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
                read_prediction_failure_risk_receipt(path)


def test_risk_receipt_rejects_byte_noncanonical_and_oversized_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import verdant_obligations.prediction_failure_risk_sidecar as module

    _, _, _, _, path, envelope = _risk_receipt_fixture(tmp_path, 7409)
    for data in (
        path.read_bytes()[:-1] + b"!",
        b" " + path.read_bytes(),
        json.dumps(envelope.model_dump(mode="json"), indent=2).encode(),
    ):
        invalid = tmp_path / "invalid.vfr"
        invalid.write_bytes(data)
        with pytest.raises(PredictionFailureRiskReceiptIntegrityError):
            read_prediction_failure_risk_receipt(invalid)
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="size limit"):
        read_prediction_failure_risk_receipt(path)
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="size limit"):
        prediction_failure_risk_receipt_bytes(envelope)


def test_risk_receipt_atomic_replace_failure_publishes_nothing_and_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    import verdant_obligations.prediction_failure_trial_plans as module

    kernel, _, prereg_path, _, plan_path, _ = _trial_plan_fixture(tmp_path, 7410)
    before = kernel.fingerprint()
    original_inputs = (plan_path.read_bytes(), prereg_path.read_bytes())
    path = tmp_path / "recover.vfr"
    replace = module.os.replace

    def fail_replace(*args, **kwargs):
        raise OSError("injected risk receipt replacement failure")

    monkeypatch.setattr(module.os, "replace", fail_replace)
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="injected"):
        PredictionFailureRiskReceiptRecorder().record(
            path, kernel=kernel, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    assert not path.exists()
    assert not tuple(tmp_path.glob(".recover.vfr.*.tmp"))
    assert kernel.fingerprint() == before
    assert (plan_path.read_bytes(), prereg_path.read_bytes()) == original_inputs
    monkeypatch.setattr(module.os, "replace", replace)
    envelope = PredictionFailureRiskReceiptRecorder().record(
        path, kernel=kernel, plan_path=plan_path,
        preregistration_path=prereg_path,
    )
    assert load_prediction_failure_risk_receipt(
        path, kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path,
    ) == envelope


def test_risk_receipt_detects_input_drift_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _, prereg_path, _, plan_path, _ = _trial_plan_fixture(tmp_path, 7411)
    before = kernel.fingerprint()
    evaluate = PredictionFailureGovernanceRiskOperator.evaluate

    def alter_input(self, **kwargs):
        result = evaluate(self, **kwargs)
        plan_path.write_bytes(plan_path.read_bytes() + b" ")
        return result

    monkeypatch.setattr(PredictionFailureGovernanceRiskOperator, "evaluate", alter_input)
    path = tmp_path / "drift.vfr"
    with pytest.raises(PredictionFailureRiskReceiptIntegrityError, match="inputs changed"):
        PredictionFailureRiskReceiptRecorder().record(
            path, kernel=kernel, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    assert not path.exists()
    assert kernel.fingerprint() == before


def test_risk_projection_abstains_without_predecision_support(
    tmp_path: Path,
) -> None:
    kernel, bundle, prereg_path, _, plan_path, _ = _trial_plan_fixture(
        tmp_path, 7301
    )
    checkpoint = tmp_path / "risk.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    original = kernel.fingerprint()
    plan_bytes = plan_path.read_bytes()
    prereg_bytes = prereg_path.read_bytes()
    operator = PredictionFailureGovernanceRiskOperator()

    result = operator.evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path
    )
    by_arm = {item.arm: item for item in result.projections}
    assert result.operator_version == PREDICTION_FAILURE_RISK_OPERATOR_VERSION
    assert by_arm[PredictionFailureTrialArm.BASELINE].predicted_harm_score == 0.1
    assert by_arm[PredictionFailureTrialArm.VALID_NULL].predicted_harm_score == 0.1
    ablation = by_arm[PredictionFailureTrialArm.TARGET_ABLATION]
    assert ablation.source == PredictionFailureRiskSource.INSUFFICIENT_EVIDENCE
    assert ablation.predicted_harm_score is None
    assert ablation.reason == "no_predecision_action_class_outcome"
    assert bundle.evidence_receipt.outcome_ref not in ablation.supporting_refs
    assert not result.matched_trial_executed
    assert not result.result_observed
    assert not result.canonical_commit_permitted
    assert all(not item.simulation_trace_observed for item in result.projections)
    assert kernel.fingerprint() == original
    assert plan_path.read_bytes() == plan_bytes
    assert prereg_path.read_bytes() == prereg_bytes

    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(reversed(tuple(state.obligation_kernels.items())))
    restored = VerdantKernel.from_state(state)
    assert operator.evaluate(
        kernel=restored, plan_path=plan_path,
        preregistration_path=prereg_path,
    ) == result


def _risk_prior_fixture(tmp_path: Path, seed: int = 7302, *,
                        prior_harm_score: float = 0.8, declared_harm_risk: float = 0.1):
    kernel = VerdantKernel(
        seed=seed, state_dim=16, run_label="prediction-failure-risk-prior"
    )
    governance = VerdantGovernancePipeline()
    prior_proposal = governance.propose(
        kernel, proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_risk_prior", action_class="inspection_one",
        description="Controlled prior inspection.",
        evidence_refs=_evidence(kernel, "risk-prior", EvidenceKind.OBSERVATION),
        relevance=1.0, urgency=0.6, novelty=0.2,
        predicted_information_gain=1.0, harm_risk=0.1, reversibility=1.0,
    )
    prior_decision = governance.commit(
        kernel, governance.inspect(kernel, prior_proposal)
    )
    prior_outcome = governance.record_outcome(
        kernel, decision_event_id=prior_decision.decision_event_id,
        evidence_refs=_evidence(kernel, "risk-prior-outcome", EvidenceKind.OUTCOME),
        succeeded=True, harm_score=prior_harm_score,
    )
    assert prior_outcome.learned_risk_after == pytest.approx(prior_harm_score * 0.8)
    target_outcome, target_decision, target_proposal = _outcome(
        kernel, declared_harm_risk=declared_harm_risk,
    )
    assert target_proposal.action_class == prior_proposal.action_class
    assert prior_outcome.cycle < target_proposal.created_cycle
    report = PredictionFailureDetector().detect_and_record(kernel)
    obligation = next(
        item.obligation for item in report.mutations
        if item.obligation.prediction_source_ref == target_decision.decision_event_id
    )
    allocation = _authorize(
        kernel, tuple(item.obligation.kernel_id for item in report.mutations),
        source_event_key="prediction-failure-risk-prior-attention",
    )[obligation.kernel_id]
    bundle = PredictionFailureHypothesisProtocol().generate(
        kernel, obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    prereg_path = tmp_path / "prior.vfp"
    plan_path = tmp_path / "prior.vpp"
    PredictionFailureTrialPreregistrar().register(
        prereg_path, kernel=kernel, hypothesis_bundle=bundle,
    )
    PredictionFailureTrialPlanMaterializer().materialize(
        plan_path, kernel=kernel, preregistration_path=prereg_path,
    )
    result = PredictionFailureGovernanceRiskOperator().evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path,
    )
    return kernel, bundle, prior_outcome, target_outcome, prereg_path, plan_path, result


def test_risk_projection_uses_only_earlier_physical_learning(
    tmp_path: Path,
) -> None:
    _, _, prior_outcome, target_outcome, _, _, result = _risk_prior_fixture(tmp_path)
    by_arm = {item.arm: item for item in result.projections}
    assert {item.predicted_harm_score for item in result.projections} == {
        prior_outcome.learned_risk_after
    }
    assert (
        by_arm[PredictionFailureTrialArm.TARGET_ABLATION].source
        == PredictionFailureRiskSource.PRIOR_OUTCOME_LEARNING
    )
    assert all(prior_outcome.outcome_id in item.supporting_refs for item in result.projections)
    assert all(target_outcome.outcome_id not in item.supporting_refs for item in result.projections)
    assert all(target_outcome.evidence_refs[0] not in item.supporting_refs for item in result.projections)
    assert not result.matched_trial_executed


def test_risk_projection_rejects_foreign_and_tampered_plan(
    tmp_path: Path,
) -> None:
    kernel, _, prereg_path, _, plan_path, _ = _trial_plan_fixture(
        tmp_path, 7303, "first"
    )
    foreign, _, foreign_prereg, _, foreign_plan, _ = _trial_plan_fixture(
        tmp_path, 7304, "foreign"
    )
    operator = PredictionFailureGovernanceRiskOperator()
    expected = operator.evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path,
    )
    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        operator.evaluate(
            kernel=foreign, plan_path=plan_path,
            preregistration_path=prereg_path,
        )
    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        operator.evaluate(
            kernel=kernel, plan_path=foreign_plan,
            preregistration_path=foreign_prereg,
        )
    tampered = tmp_path / "tampered.vpp"
    data = bytearray(plan_path.read_bytes())
    data[-2] ^= 1
    tampered.write_bytes(data)
    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        operator.evaluate(
            kernel=kernel, plan_path=tampered,
            preregistration_path=prereg_path,
        )
    assert operator.evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=prereg_path,
    ) == expected


def test_risk_projection_rejects_forged_score_and_authority() -> None:
    projection = PredictionFailureRiskProjection.build(
        plan_ref="controlled-plan", arm=PredictionFailureTrialArm.TARGET_ABLATION,
        source=PredictionFailureRiskSource.INSUFFICIENT_EVIDENCE,
        score=None, supporting_refs=("native-council-report",),
        reason="no_predecision_action_class_outcome",
    )
    forged = projection.model_dump(mode="json")
    forged["predicted_harm_score"] = 0.8
    with pytest.raises(ValueError, match="boundary"):
        PredictionFailureRiskProjection.model_validate(forged)
    forged = projection.model_dump(mode="json")
    forged["canonical_commit_permitted"] = True
    with pytest.raises(ValueError, match="boundary"):
        PredictionFailureRiskProjection.model_validate(forged)


def test_trial_plan_materializes_typed_target_absence_without_execution(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7201)
    preregistration_path = tmp_path / "typed-target.vfp"
    plan_path = tmp_path / "typed-target.vpp"
    before = kernel.fingerprint()
    preregistration = PredictionFailureTrialPreregistrar().register(
        preregistration_path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    preregistration_bytes = preregistration_path.read_bytes()

    envelope = PredictionFailureTrialPlanMaterializer().materialize(
        plan_path,
        kernel=kernel,
        preregistration_path=preregistration_path,
    )

    package = envelope.plan_bundle
    plans = {item.arm: item for item in package.plans}
    baseline = plans[PredictionFailureTrialArm.BASELINE]
    ablation = plans[PredictionFailureTrialArm.TARGET_ABLATION]
    valid_null = plans[PredictionFailureTrialArm.VALID_NULL]
    assert kernel.fingerprint() == before
    assert preregistration_path.read_bytes() == preregistration_bytes
    assert package.preregistration == preregistration
    assert tuple(item.arm for item in package.plans) == (
        PREDICTION_FAILURE_TRIAL_ARM_ORDER
    )
    assert baseline.input_projection.declared_harm_risk == 0.1
    assert ablation.input_projection.declared_harm_risk is None
    assert valid_null.input_projection.declared_harm_risk == 0.1
    assert not ablation.input_projection.missing_target_default_permitted
    assert {
        item.input_projection.non_target_input_sha256
        for item in package.plans
    } == {package.non_target_input_sha256}
    assert {item.requested_budget for item in package.plans} == {0.015}
    assert package.total_requested_budget == 0.045
    assert package.total_requested_budget <= (
        bundle.evidence_receipt.authorized_budget
    )
    for plan in package.plans:
        assert set(bundle.evidence_receipt.protected_evidence_refs).issubset(
            plan.result_refs
        )
        assert plan.input_projection.simulation_only
        assert plan.dedicated_pristine_simulation_ledger_required
        assert not plan.native_overlay_patches_permitted
        assert not plan.counterfactual_runtime_plan_materialized
        assert plan.prediction_operator_ref is None
        assert not plan.runtime_execution_authorized
        assert not plan.trace_observed
        assert not plan.predicted_harm_observed
        assert not plan.result_observed
        assert not plan.canonical_commit_permitted
    assert package.prediction_operator_required
    assert not package.prediction_operator_materialized
    assert not package.counterfactual_runtime_plans_materialized
    assert not package.runner_implemented
    assert not package.plans_executed
    assert not package.target_specific_effect_observed
    assert not package.causal_attribution_enabled
    assert not package.resolution_authority_enabled
    assert not package.promotion_authority_enabled
    assert not package.policy_rewrite_authority_enabled
    assert not package.canonical_commit_permitted
    assert plan_path.read_bytes() == prediction_failure_trial_plan_bytes(
        envelope
    )


def test_trial_plan_checkpoint_replay_is_exact_and_idempotent(
    tmp_path: Path,
) -> None:
    kernel, bundle = _trial_bundle(7202)
    checkpoint = tmp_path / "trial-plan.vdk"
    preregistration_path = tmp_path / "trial-plan.vfp"
    plan_path = tmp_path / "trial-plan.vpp"
    save_checkpoint(checkpoint, kernel.snapshot())
    PredictionFailureTrialPreregistrar().register(
        preregistration_path,
        kernel=kernel,
        hypothesis_bundle=bundle,
    )
    materializer = PredictionFailureTrialPlanMaterializer()
    expected = materializer.materialize(
        plan_path,
        kernel=kernel,
        preregistration_path=preregistration_path,
    )
    first_bytes = plan_path.read_bytes()
    assert materializer.materialize(
        plan_path,
        kernel=kernel,
        preregistration_path=preregistration_path,
    ) == expected
    assert plan_path.read_bytes() == first_bytes

    state = load_checkpoint(checkpoint)
    state.evidence = dict(reversed(tuple(state.evidence.items())))
    state.obligation_kernels = dict(
        reversed(tuple(state.obligation_kernels.items()))
    )
    restored = VerdantKernel.from_state(state)
    assert restored.fingerprint() == kernel.fingerprint()
    assert load_prediction_failure_trial_plan(
        plan_path,
        kernel=restored,
        preregistration_path=preregistration_path,
    ) == expected


def test_trial_plan_rejects_foreign_and_stale_checkpoints(
    tmp_path: Path,
) -> None:
    kernel, _, preregistration_path, _, plan_path, _ = _trial_plan_fixture(
        tmp_path,
        7203,
    )
    foreign, _ = _trial_bundle(7204)
    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="exact durable preregistration",
    ):
        load_prediction_failure_trial_plan(
            plan_path,
            kernel=foreign,
            preregistration_path=preregistration_path,
        )

    PredictionFailureDetector(
        PredictionFailureDetectionPolicy(
            policy_version="prediction_failure_plan_retrigger_v2",
            minimum_prediction_error=0.2,
        )
    ).detect_and_record(kernel)
    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="exact durable preregistration",
    ):
        load_prediction_failure_trial_plan(
            plan_path,
            kernel=kernel,
            preregistration_path=preregistration_path,
        )


def test_trial_plan_rejects_substituted_preregistration(
    tmp_path: Path,
) -> None:
    _, _, _, _, first_plan_path, _ = _trial_plan_fixture(
        tmp_path,
        7205,
        "first",
    )
    second_kernel, _, second_preregistration_path, _, _, _ = (
        _trial_plan_fixture(tmp_path, 7206, "second")
    )

    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="another preregistration",
    ):
        load_prediction_failure_trial_plan(
            first_plan_path,
            kernel=second_kernel,
            preregistration_path=second_preregistration_path,
        )


def test_trial_plan_foreign_preregistration_publishes_no_plan(
    tmp_path: Path,
) -> None:
    kernel, _ = _trial_bundle(7207)
    foreign_kernel, foreign_bundle = _trial_bundle(7208)
    foreign_preregistration_path = tmp_path / "foreign.vfp"
    PredictionFailureTrialPreregistrar().register(
        foreign_preregistration_path,
        kernel=foreign_kernel,
        hypothesis_bundle=foreign_bundle,
    )
    plan_path = tmp_path / "must-not-exist.vpp"

    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        PredictionFailureTrialPlanMaterializer().materialize(
            plan_path,
            kernel=kernel,
            preregistration_path=foreign_preregistration_path,
        )
    assert not plan_path.exists()


def test_trial_plan_path_is_first_committer_wins(tmp_path: Path) -> None:
    first = _trial_plan_fixture(tmp_path, 7209, "first-writer")
    first_kernel, _, first_preregistration_path, _, first_plan_path, envelope = (
        first
    )
    first_bytes = first_plan_path.read_bytes()
    second_kernel, second_bundle = _trial_bundle(7210)
    second_preregistration_path = tmp_path / "second-writer.vfp"
    PredictionFailureTrialPreregistrar().register(
        second_preregistration_path,
        kernel=second_kernel,
        hypothesis_bundle=second_bundle,
    )

    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="different evidence",
    ):
        PredictionFailureTrialPlanMaterializer().materialize(
            first_plan_path,
            kernel=second_kernel,
            preregistration_path=second_preregistration_path,
        )
    assert first_plan_path.read_bytes() == first_bytes
    assert load_prediction_failure_trial_plan(
        first_plan_path,
        kernel=first_kernel,
        preregistration_path=first_preregistration_path,
    ) == envelope


def test_trial_plan_tamper_and_noncanonical_bytes_fail(tmp_path: Path) -> None:
    _, _, _, _, _, envelope = _trial_plan_fixture(tmp_path, 7211)
    data = prediction_failure_trial_plan_bytes(envelope)
    changed = bytearray(data)
    changed[-2] ^= 1
    tampered_path = tmp_path / "tampered.vpp"
    tampered_path.write_bytes(changed)
    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        read_prediction_failure_trial_plan(tampered_path)

    noncanonical_path = tmp_path / "noncanonical.vpp"
    noncanonical_path.write_bytes(data + b"\n")
    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="not canonical",
    ):
        read_prediction_failure_trial_plan(noncanonical_path)


def test_trial_plan_fully_rehashed_authority_forgery_fails(
    tmp_path: Path,
) -> None:
    _, _, _, _, _, envelope = _trial_plan_fixture(tmp_path, 7212)
    payload = json.loads(prediction_failure_trial_plan_bytes(envelope))
    package = payload["plan_bundle"]
    package["plans_executed"] = True
    package["plan_bundle_id"] = stable_id(
        "prediction_failure_trial_plan_bundle",
        {
            key: value
            for key, value in package.items()
            if key != "plan_bundle_id"
        },
    )
    payload["plan_bundle_sha256"] = hashlib.sha256(
        canonical_json_bytes(package)
    ).hexdigest()
    path = tmp_path / "authority-forgery.vpp"
    path.write_bytes(canonical_json_bytes(payload))

    with pytest.raises(PredictionFailureTrialPlanIntegrityError):
        read_prediction_failure_trial_plan(path)


def test_trial_plan_rejects_target_default_and_cross_arm_input_drift(
    tmp_path: Path,
) -> None:
    kernel, _, _, _, _, envelope = _trial_plan_fixture(tmp_path, 7213)
    package = envelope.plan_bundle
    ablation = next(
        item
        for item in package.plans
        if item.arm == PredictionFailureTrialArm.TARGET_ABLATION
    )
    target_payload = ablation.input_projection.model_dump(mode="json")
    target_payload["declared_harm_risk"] = 0.0
    target_payload["projection_id"] = stable_id(
        "prediction_failure_simulation_input",
        {
            key: value
            for key, value in target_payload.items()
            if key != "projection_id"
        },
    )
    with pytest.raises(ValueError, match="simulation-only boundary"):
        PredictionFailureSimulationInputProjection.model_validate(
            target_payload
        )

    baseline_index = next(
        index
        for index, item in enumerate(package.plans)
        if item.arm == PredictionFailureTrialArm.BASELINE
    )
    baseline = package.plans[baseline_index]
    projection_payload = baseline.input_projection.model_dump(mode="json")
    projection_payload["novelty"] = 0.9
    proposal = next(
        item.report.proposal
        for item in kernel.state.council_decisions
        if item.report.proposal.proposal_id == package.canonical_proposal_ref
    )
    non_target = proposal.model_dump(mode="json")
    non_target.pop("proposal_id")
    non_target.pop("harm_risk")
    non_target["novelty"] = 0.9
    projection_payload["non_target_input_sha256"] = hashlib.sha256(
        canonical_json_bytes(non_target)
    ).hexdigest()
    projection_payload["projection_id"] = stable_id(
        "prediction_failure_simulation_input",
        {
            key: value
            for key, value in projection_payload.items()
            if key != "projection_id"
        },
    )
    changed_projection = (
        PredictionFailureSimulationInputProjection.model_validate(
            projection_payload
        )
    )
    changed_plan = PredictionFailureTrialSimulationPlan.build(
        preregistration=package.preregistration,
        arm=package.preregistration.declaration.arms[baseline_index],
        projection=changed_projection,
    )
    package_payload = package.model_dump(mode="json")
    package_payload["plans"][baseline_index] = changed_plan.model_dump(
        mode="json"
    )
    package_payload["plan_refs"][baseline_index] = changed_plan.plan_id
    package_payload["plan_bundle_id"] = stable_id(
        "prediction_failure_trial_plan_bundle",
        {
            key: value
            for key, value in package_payload.items()
            if key != "plan_bundle_id"
        },
    )
    with pytest.raises(ValueError, match="matched-control constant"):
        PredictionFailureTrialPlanBundle.model_validate(package_payload)


def test_trial_plan_checks_size_before_json_parse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import verdant_obligations.prediction_failure_trial_plans as module

    path = tmp_path / "oversized.vpp"
    path.write_bytes(b"not-json-but-too-large")
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(
        PredictionFailureTrialPlanIntegrityError,
        match="exceeds its size limit",
    ):
        read_prediction_failure_trial_plan(path)
