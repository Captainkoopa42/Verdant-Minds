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
    PredictionFailureTrialArm,
    PredictionFailureTrialArmDeclaration,
    PredictionFailureTrialDeclaration,
    PredictionFailureTrialOutcomePolicy,
    PredictionFailureTrialPreregistrationIntegrityError,
    PredictionFailureTrialPreregistrar,
    load_prediction_failure_trial_preregistration,
    prediction_failure_trial_preregistration_bytes,
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
