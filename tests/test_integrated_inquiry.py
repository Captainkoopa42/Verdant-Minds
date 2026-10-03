from __future__ import annotations

import hashlib
import json
import os
import select
import signal
import threading
from pathlib import Path

import pytest

import verdant_obligations.inquiry as inquiry_module
from verdant_kernel import (
    CouncilDisposition,
    EvidenceKind,
    ExperienceCommand,
    ObligationFamily,
    RelationProposal,
    WorkspaceDisposition,
    WorkspaceSourceKind,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes
from verdant_obligations import (
    AttentionPortfolio,
    AttentionPortfolioPolicy,
    ControlledOperationalTrialObserver,
    CounterfactualPatch,
    CounterfactualRuntime,
    DependencyGapInquiryCoordinator,
    DependencyGapPipeline,
    EquivalenceLensSystem,
    GROUNDED_TRACE_REQUIREMENTS,
    HypothesisOperator,
    IntegratedInquiryError,
    IntegratedInquiryPolicy,
    IntegratedInquiryReceiptIntegrityError,
    IntegratedInquiryTrace,
    IntegratedInquiryTrialControlRequest,
    LensOpcode,
    MatchedCounterfactualObserver,
    MatchedCounterfactualPlans,
    MatchedOutgoingActionObservation,
    MatchedWorkspaceAdmissionObservation,
    MISSING_OPERATIONAL_REQUIREMENTS,
    NativeWorkspaceAdmissionObserver,
    NativeOutgoingActionObserver,
    NativeOutgoingActionProbePolicy,
    OutcomeKind,
    OperationalProbeDisposition,
    OutgoingActionDisposition,
    OutgoingActionEffect,
    OutgoingActionProbeIntegrityError,
    OverlayAccessEffect,
    OverlayOperationalProbe,
    ResolutionEvidenceRequirement,
    SimulationLedger,
    StructuralTraceEffect,
    TraceResolutionEvidenceDeriver,
    TraceResolutionEvidenceIntegrityError,
    TraceResolutionEvidenceReceipt,
    WorkspaceAdmissionEffect,
    WorkspaceAdmissionProbeIntegrityError,
    append_integrated_inquiry_receipt_history,
    experiment_archive_bytes,
    integrated_inquiry_receipt_bytes,
    integrated_inquiry_receipt_history_bytes,
    load_experiment_archive,
    load_experiment_archive_bundle,
    load_integrated_inquiry_receipt,
    load_integrated_inquiry_receipt_history_entry,
    read_integrated_inquiry_receipt_history,
    save_experiment_archive,
    save_integrated_inquiry_receipt,
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


def _kernel() -> VerdantKernel:
    kernel = VerdantKernel(seed=7401, state_dim=16, run_label="integrated-inquiry")
    kernel.apply_experience(
        _experience(
            "integrated-dependency",
            relations=(
                RelationProposal(
                    source_label="stabilize loop",
                    target_label="pressure input",
                    relation_type="requires",
                    confidence=0.9,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "integrated-route",
            relations=(
                RelationProposal(
                    source_label="pressure input",
                    target_label="grounded reading",
                    relation_type="routes_to",
                    confidence=0.9,
                ),
            ),
        )
    )
    kernel.apply_experience(
        _experience(
            "integrated-grounding",
            labels=("grounded reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    return kernel


def _lenses(kernel: VerdantKernel) -> EquivalenceLensSystem:
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(
            LensOpcode.SELECT_ACTION,
            LensOpcode.SELECT_ACTIVATED_REFS,
            LensOpcode.SELECT_EDGE_ENDPOINTS,
            LensOpcode.SELECT_EDGE_TYPES,
        ),
        provenance_refs=("integrated-controls:matched-suite",),
    )
    lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=(
            "integrated-controls:calibration",
            "integrated-controls:held-out",
        ),
        source_event_key="lens:integrated-controls:v0.28",
        cycle=kernel.state.cycle,
    )
    return lenses


def _trial_controls(
    lenses: EquivalenceLensSystem,
    *,
    slot_budget: int = 2,
) -> IntegratedInquiryTrialControlRequest:
    return IntegratedInquiryTrialControlRequest.build(
        lenses,
        calibration_seed=101,
        held_out_seed=211,
        horizon=4,
        slot_budget=slot_budget,
    )


def test_opt_in_path_links_detection_attention_hypotheses_and_simulation() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    before = kernel.fingerprint()

    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:001",
    )

    assert not result.replayed
    assert kernel.fingerprint() != before
    assert result.trace.canonical_checkpoint_fingerprint == kernel.fingerprint()
    assert result.trace.simulation_ledger_fingerprint == runtime.ledger.fingerprint()
    assert len(result.detection.candidates) == 1
    assert len(result.attention.decision.allocations) == 1
    assert len(result.simulations) == len(result.plans) == len(result.trace.trials) == 3
    assert len(result.matched_pairs) == 1
    matched = result.matched_pairs[0]
    assert result.trace.matched_observations == (matched.observation,)
    assert result.trace.operational_probe_observations == (
        matched.operational_observation,
    )
    assert result.trace.resolution_evidence_receipts == (
        matched.resolution_evidence,
    )
    assert matched.obligation_id == result.detection.mutations[0].obligation.kernel_id
    assert matched.hypothesis_id == matched.observation.hypothesis_ref
    assert matched.observation.effect == StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
    assert matched.observation.canonical_records_preserved
    assert matched.observation.baseline.result_refs == (matched.hypothesis_id,)
    assert matched.observation.treatment.result_refs == (matched.hypothesis_id,)
    operational = matched.operational_observation
    assert operational.effect == OverlayAccessEffect.ACCESS_GAIN
    assert (
        operational.baseline.disposition
        == OperationalProbeDisposition.NO_QUALIFYING_ACCESS_PATH
    )
    assert operational.baseline.retrieved_evidence_refs == ()
    assert (
        operational.treatment.disposition
        == OperationalProbeDisposition.CANONICAL_EVIDENCE_RETRIEVED
    )
    assert operational.treatment.retrieved_evidence_refs
    assert all(
        ref in kernel.state.evidence
        for ref in operational.treatment.retrieved_evidence_refs
    )
    assert not operational.treatment.workspace_admission_observed
    assert not operational.treatment.outgoing_action_observed
    assert not operational.treatment.canonical_dependency_path_established
    assert len(runtime.ledger.state.reservations) == 5
    assert len(runtime.ledger.state.settlements) == 5
    assert {item.operator for item in result.hypotheses} == {
        HypothesisOperator.EVIDENCE_PATH_PROJECTION,
        HypothesisOperator.NULL_ARTIFACT,
        HypothesisOperator.DEFER_INSUFFICIENT_EVIDENCE,
    }

    outcomes = {
        outcome.outcome_id: outcome
        for hypothesis in result.hypotheses
        for outcome in hypothesis.outcomes
    }
    hypotheses = {item.hypothesis_id: item for item in result.hypotheses}
    trials_by_settlement = {
        item.settlement_id: item for item in result.trace.trials
    }
    assert {outcomes[item.outcome_id].kind for item in result.trace.trials} == {
        OutcomeKind.PATH_COMPLETES,
        OutcomeKind.PATH_STALLS,
        OutcomeKind.PATH_CONFLICTS,
    }
    for simulation in result.simulations:
        trial = trials_by_settlement[simulation.settlement.settlement_id]
        outcome = outcomes[trial.outcome_id]
        hypothesis = hypotheses[trial.hypothesis_id]
        assert outcome.hypothesis_id == hypothesis.hypothesis_id
        assert simulation.reservation.attention_decision_id == (
            result.attention.decision.decision_id
        )
        assert simulation.settlement.canonical_unchanged
        assert not simulation.settlement.canonical_commit_permitted
        assert not simulation.settlement.epistemic_authority_enabled
        assert set(simulation.settlement.result_refs) == {
            hypothesis.hypothesis_id,
            outcome.outcome_id,
            outcome.equivalence_signature,
        }

    completion_trial = next(
        item
        for item in result.trace.trials
        if outcomes[item.outcome_id].kind == OutcomeKind.PATH_COMPLETES
    )
    completion_hypothesis = hypotheses[completion_trial.hypothesis_id]
    assert completion_hypothesis.patches
    assert completion_hypothesis.patches[0].record_key not in kernel.state.relations
    assert operational.treatment.traversed_relation_refs == (
        completion_hypothesis.patches[0].record_key,
    )

    coverage = matched.resolution_evidence
    assert coverage.matched_observation_ref == matched.observation.observation_id
    assert coverage.matched_operational_probe_ref == operational.match_id
    assert coverage.candidate_path_relation_refs == (
        completion_hypothesis.derivation_path_relation_ids
    )
    assert coverage.structural_added_refs == matched.observation.added_record_refs
    assert coverage.grounded_requirements == GROUNDED_TRACE_REQUIREMENTS
    assert coverage.missing_requirements == MISSING_OPERATIONAL_REQUIREMENTS
    assert {
        ResolutionEvidenceRequirement.OVERLAY_RETRIEVAL_OBSERVATION,
        ResolutionEvidenceRequirement.OVERLAY_PATH_OBSERVATION,
    }.issubset(coverage.grounded_requirements)
    assert {
        ResolutionEvidenceRequirement.RETRIEVED_REFS,
        ResolutionEvidenceRequirement.ADMITTED_REFS,
        ResolutionEvidenceRequirement.OUTGOING_ACTION,
        ResolutionEvidenceRequirement.EXECUTED_DEPENDENCY_PATH,
        ResolutionEvidenceRequirement.HELD_OUT_REPLICATION,
    }.issubset(coverage.missing_requirements)
    assert not coverage.resolution_trial_ready
    assert coverage.simulated_only
    assert not coverage.observed_outcome_authority_enabled
    assert not coverage.resolution_authority_enabled
    assert not coverage.canonical_commit_permitted

    bid = result.attention.decision.bids[0]
    assert bid.requested_budget == pytest.approx(0.05)
    assert set(bid.metric_provenance_refs) >= {
        result.detection.candidates[0].candidate_id,
        result.detection.mutations[0].event.event_id,
        result.partitions[0].partition_id,
        *(item.hypothesis_id for item in result.hypotheses),
    }
    assert not result.trace.canonical_simulation_leakage_detected
    assert not result.trace.canonical_resolution_permitted
    assert not result.trace.epistemic_authority_enabled


def test_controlled_opt_in_path_funds_and_traces_both_predeclared_pairs() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses)
    canonical_before = kernel.fingerprint()
    lens_before = lenses.fingerprint()

    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:controlled",
        lenses=lenses,
        trial_controls=controls,
    )

    assert not result.replayed
    assert kernel.fingerprint() != canonical_before
    assert lenses.fingerprint() == lens_before
    assert result.trace.trial_control_request == controls
    assert len(result.matched_pairs) == 2
    assert len(result.trace.controlled_trial_observations) == 2
    assert len(result.held_out_replications) == 1
    assert result.trace.held_out_replication_receipts == (
        result.held_out_replications[0],
    )
    assert len(result.trace.workspace_admission_observations) == 2
    assert len(result.held_out_workspace_admission_replications) == 1
    assert result.trace.held_out_workspace_admission_receipts == (
        result.held_out_workspace_admission_replications[0],
    )
    assert len(result.trace.outgoing_action_observations) == 2
    assert len(result.held_out_outgoing_action_replications) == 1
    assert result.trace.held_out_outgoing_action_receipts == (
        result.held_out_outgoing_action_replications[0],
    )
    assert len(runtime.ledger.state.reservations) == 5
    assert len(runtime.ledger.state.settlements) == 5
    assert len(result.simulations) == 1

    allocation = result.attention.decision.allocations[0]
    bid = result.attention.decision.bids[0]
    assert bid.requested_budget == pytest.approx(0.07)
    assert allocation.granted_budget == pytest.approx(0.05)
    assert controls.request_id in bid.metric_provenance_refs
    assert controls.lens_binding_id in bid.metric_provenance_refs
    assert controls.lens_definition_id in bid.metric_provenance_refs
    assert controls.lens_state_fingerprint in bid.metric_provenance_refs

    controlled = tuple(
        item.controlled_observation for item in result.matched_pairs
    )
    assert all(item is not None for item in controlled)
    assert {item.context.split for item in controlled if item is not None} == {
        item.context.split for item in result.held_out_replications[0].trials
    }
    assert {
        item.context.seed for item in controlled if item is not None
    } == {101, 211}
    assert all(
        pair.context is not None
        and pair.context.context_id in pair.baseline.settlement.result_refs
        and pair.context.context_id in pair.treatment.settlement.result_refs
        and pair.baseline.reservation.allocation_id == allocation.allocation_id
        and pair.treatment.reservation.allocation_id == allocation.allocation_id
        and pair.resolution_evidence.missing_requirements
        == MISSING_OPERATIONAL_REQUIREMENTS
        for pair in result.matched_pairs
    )
    workspace_observations = tuple(
        item.workspace_admission_observation for item in result.matched_pairs
    )
    assert all(item is not None for item in workspace_observations)
    for pair in result.matched_pairs:
        workspace = pair.workspace_admission_observation
        assert workspace is not None
        assert workspace.effect == WorkspaceAdmissionEffect.ADMISSION_GAIN
        assert workspace.baseline.submitted_retrieved_evidence_refs == ()
        assert workspace.baseline.admitted_retrieved_evidence_refs == ()
        assert workspace.treatment.submitted_retrieved_evidence_refs == (
            pair.operational_observation.treatment.retrieved_evidence_refs
        )
        assert workspace.treatment.admitted_retrieved_evidence_refs
        assert workspace.treatment.native_workspace_pipeline_executed
        assert workspace.treatment.workspace_event.report == (
            workspace.treatment.admission_report
        )
        assert not workspace.treatment.workspace_event.semantic_mutation_permitted
        assert workspace.treatment.shadow_execution_only
        assert not workspace.treatment.canonical_workspace_mutated
        assert not workspace.treatment.outgoing_action_observed
        assert not workspace.treatment.canonical_dependency_path_established
        action = pair.outgoing_action_observation
        assert action is not None
        assert action.workspace_admission == workspace
        assert action.effect == OutgoingActionEffect.ACTION_GAIN
        assert (
            action.baseline.action_disposition
            == OutgoingActionDisposition.NO_ADMITTED_EVIDENCE
        )
        treatment_action = action.treatment
        assert (
            treatment_action.action_disposition
            == OutgoingActionDisposition.AUTHORIZED_AND_ADMITTED
        )
        assert treatment_action.council_report is not None
        assert treatment_action.council_decision is not None
        assert treatment_action.action_workspace_report is not None
        assert treatment_action.action_workspace_event is not None
        assert treatment_action.council_report.disposition == CouncilDisposition.APPROVE
        assert treatment_action.operation in (
            treatment_action.council_report.authorized_operations
        )
        action_assessment = next(
            item
            for item in treatment_action.action_workspace_report.assessments
            if item.candidate.metadata.get("outgoing_action_probe_version")
        )
        assert action_assessment.disposition == WorkspaceDisposition.ADMIT
        assert (
            action_assessment.candidate.source_kind
            == WorkspaceSourceKind.AUTHORIZED_ACTION
        )
        assert action_assessment.candidate.source_ref == (
            treatment_action.council_decision.decision_event_id
        )
        assert action_assessment.candidate.operation == treatment_action.operation
        assert treatment_action.outgoing_action_signature_observed
        assert not treatment_action.external_action_executed
        assert not treatment_action.canonical_dependency_path_established
    replication = result.held_out_replications[0]
    assert replication.seeds == (101, 211)
    assert replication.declared_seed_replay_observed
    assert not replication.stochastic_generalization_established
    assert not replication.native_workspace_admission_observed
    assert not replication.outgoing_action_observed
    assert not replication.canonical_dependency_path_established
    assert not replication.resolution_authority_enabled
    assert not replication.canonical_commit_permitted
    workspace_replication = result.held_out_workspace_admission_replications[0]
    assert workspace_replication.operational_replication_ref == replication.receipt_id
    assert workspace_replication.seeds == (101, 211)
    assert workspace_replication.declared_seed_replay_observed
    assert workspace_replication.native_workspace_admission_observed
    assert workspace_replication.declared_slot_budget_enforced
    assert not workspace_replication.canonical_workspace_commit_performed
    assert not workspace_replication.outgoing_action_observed
    assert not workspace_replication.canonical_dependency_path_established
    action_replication = result.held_out_outgoing_action_replications[0]
    assert action_replication.operational_replication_ref == replication.receipt_id
    assert action_replication.workspace_replication_ref == (
        workspace_replication.receipt_id
    )
    assert action_replication.seeds == (101, 211)
    assert action_replication.native_outgoing_action_signature_observed
    assert not action_replication.external_action_executed
    assert not action_replication.canonical_dependency_path_established
    assert len(kernel.state.workspace_items) == 0
    assert len(kernel.state.workspace_cycle_events) == 0
    assert len(kernel.state.council_decisions) == 0
    assert not result.trace.canonical_simulation_leakage_detected
    assert not result.trace.canonical_resolution_permitted
    assert not result.trace.epistemic_authority_enabled


def test_controlled_trace_reconstructs_exactly_after_archive_reload(
    tmp_path: Path,
) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses)
    coordinator = DependencyGapInquiryCoordinator()
    first = coordinator.run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:controlled-replay",
        lenses=lenses,
        trial_controls=controls,
    )
    path = tmp_path / "integrated-controlled.vob"
    save_experiment_archive(
        path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
    )
    bundle = load_experiment_archive_bundle(path)
    assert bundle.lens_system is not None
    restored_runtime = CounterfactualRuntime(bundle.simulation_ledger)
    restored_controls = _trial_controls(bundle.lens_system)
    assert restored_controls == controls
    canonical_before = bundle.kernel.fingerprint()
    simulation_before = restored_runtime.ledger.fingerprint()

    replay = coordinator.run(
        bundle.kernel,
        restored_runtime,
        source_event_key="integrated-inquiry:controlled-replay",
        lenses=bundle.lens_system,
        trial_controls=restored_controls,
    )

    assert replay.replayed
    assert replay.trace == first.trace
    assert tuple(item.plans for item in replay.matched_pairs) == tuple(
        item.plans for item in first.matched_pairs
    )
    assert tuple(item.observation for item in replay.matched_pairs) == tuple(
        item.observation for item in first.matched_pairs
    )
    assert tuple(
        item.controlled_observation for item in replay.matched_pairs
    ) == tuple(item.controlled_observation for item in first.matched_pairs)
    assert replay.held_out_replications == first.held_out_replications
    assert tuple(
        item.workspace_admission_observation for item in replay.matched_pairs
    ) == tuple(
        item.workspace_admission_observation for item in first.matched_pairs
    )
    assert (
        replay.held_out_workspace_admission_replications
        == first.held_out_workspace_admission_replications
    )
    assert tuple(
        item.outgoing_action_observation for item in replay.matched_pairs
    ) == tuple(
        item.outgoing_action_observation for item in first.matched_pairs
    )
    assert (
        replay.held_out_outgoing_action_replications
        == first.held_out_outgoing_action_replications
    )
    assert all(item.replayed for item in replay.matched_pairs)
    assert bundle.kernel.fingerprint() == canonical_before
    assert restored_runtime.ledger.fingerprint() == simulation_before
    assert len(bundle.kernel.state.workspace_items) == 0
    assert len(bundle.kernel.state.workspace_cycle_events) == 0
    assert len(bundle.kernel.state.council_decisions) == 0


def test_trace_reconstructs_exactly_after_archive_reload(tmp_path: Path) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    coordinator = DependencyGapInquiryCoordinator()
    first = coordinator.run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:replay",
    )
    path = tmp_path / "integrated.vob"
    expected_archive = experiment_archive_bytes(kernel, runtime.ledger)
    save_experiment_archive(path, kernel, runtime.ledger)
    assert path.read_bytes() == expected_archive

    restored_kernel, restored_ledger = load_experiment_archive(path)
    restored_runtime = CounterfactualRuntime(ledger=restored_ledger)
    canonical_before = restored_kernel.fingerprint()
    simulation_before = restored_runtime.ledger.fingerprint()

    replay = DependencyGapInquiryCoordinator().run(
        restored_kernel,
        restored_runtime,
        source_event_key="integrated-inquiry:replay",
    )

    assert replay.replayed
    assert replay.trace == first.trace
    assert replay.plans == first.plans
    assert tuple(item.plans for item in replay.matched_pairs) == tuple(
        item.plans for item in first.matched_pairs
    )
    assert tuple(item.observation for item in replay.matched_pairs) == tuple(
        item.observation for item in first.matched_pairs
    )
    assert tuple(
        item.operational_observation for item in replay.matched_pairs
    ) == tuple(item.operational_observation for item in first.matched_pairs)
    assert tuple(item.resolution_evidence for item in replay.matched_pairs) == tuple(
        item.resolution_evidence for item in first.matched_pairs
    )
    assert tuple(
        (item.baseline.reservation, item.treatment.reservation)
        for item in replay.matched_pairs
    ) == tuple(
        (item.baseline.reservation, item.treatment.reservation)
        for item in first.matched_pairs
    )
    assert tuple(
        (item.baseline.settlement, item.treatment.settlement)
        for item in replay.matched_pairs
    ) == tuple(
        (item.baseline.settlement, item.treatment.settlement)
        for item in first.matched_pairs
    )
    assert all(item.replayed for item in replay.matched_pairs)
    assert tuple(item.reservation for item in replay.simulations) == tuple(
        item.reservation for item in first.simulations
    )
    assert tuple(item.settlement for item in replay.simulations) == tuple(
        item.settlement for item in first.simulations
    )
    assert restored_kernel.fingerprint() == canonical_before
    assert restored_runtime.ledger.fingerprint() == simulation_before


def test_allocation_must_fund_matched_pair_and_one_labeled_arm() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    attention = AttentionPortfolio(
        AttentionPortfolioPolicy(micro_probe_budget=0.02)
    )

    with pytest.raises(IntegratedInquiryError, match="matched control pair"):
        DependencyGapInquiryCoordinator(attention=attention).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:underfunded-match",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_controlled_allocation_must_fund_two_pairs_and_one_labeled_arm() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    attention = AttentionPortfolio(
        AttentionPortfolioPolicy(
            micro_probe_budget=0.04,
            maximum_grant=0.04,
        )
    )

    with pytest.raises(IntegratedInquiryError, match="matched control pair"):
        DependencyGapInquiryCoordinator(attention=attention).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:controlled-underfunded",
            lenses=lenses,
            trial_controls=controls,
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


@pytest.mark.parametrize(
    ("change", "message"),
    (
        ({"held_out_seed": 101}, "distinct"),
        ({"lens_state_fingerprint": "0" * 64}, "checksum"),
        ({"counterfactual_arm_count": 2}, "exactly two"),
        ({"canonical_commit_permitted": True}, "claim boundary"),
    ),
)
def test_controlled_request_tampering_fails_before_partial_publication(
    change: dict[str, object],
    message: str,
) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    forged = _trial_controls(lenses).model_copy(update=change)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(IntegratedInquiryError, match=message):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:controlled-forged-request",
            lenses=lenses,
            trial_controls=forged,
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_controlled_request_rejects_post_declaration_lens_replacement() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses)
    replacement = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=("integrated-controls:replacement",),
    )
    lenses.approve_binding(
        definition_id=replacement.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("integrated-controls:replacement-calibration",),
        source_event_key="lens:integrated-controls:replacement",
        cycle=kernel.state.cycle,
    )
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="active Lens state"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:changed-lens",
            lenses=lenses,
            trial_controls=controls,
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_controlled_observation_tamper_rejects_entire_transaction() -> None:
    class TamperingControlledObserver:
        def observe(self, *args, **kwargs):
            observation = ControlledOperationalTrialObserver().observe(
                *args, **kwargs
            )
            return observation.model_copy(
                update={"canonical_commit_permitted": True}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="Controlled matched observation failed validation",
    ):
        DependencyGapInquiryCoordinator(
            controlled_trial_observer=TamperingControlledObserver()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:controlled-tamper",
            lenses=lenses,
            trial_controls=controls,
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_matched_receipt_tamper_rejects_entire_staged_transaction() -> None:
    class TamperingObserver:
        def observe(self, *args, **kwargs):
            receipt = MatchedCounterfactualObserver().observe(*args, **kwargs)
            return receipt.model_copy(
                update={"canonical_records_preserved": False}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="Matched structural observation failed validation",
    ):
        DependencyGapInquiryCoordinator(
            matched_observer=TamperingObserver()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:tampered-match",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_matched_plan_cannot_substitute_a_foreign_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_builder = inquiry_module.build_matched_counterfactual_plans

    def forged_builder(hypothesis, **kwargs):
        plans = real_builder(hypothesis, **kwargs)
        foreign_patch = CounterfactualPatch.upsert(
            "relations",
            "forged-foreign-relation",
            {"counterfactual": True, "forged": True},
        )
        return MatchedCounterfactualPlans(
            baseline=plans.baseline.model_copy(
                update={"patches": (foreign_patch,)}
            ),
            treatment=plans.treatment.model_copy(
                update={"patches": (foreign_patch,)}
            ),
        )

    monkeypatch.setattr(
        inquiry_module,
        "build_matched_counterfactual_plans",
        forged_builder,
    )
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="declared hypothesis"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:foreign-matched-patch",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_missing_projected_intervention_rejects_without_partial_writes() -> None:
    kernel = VerdantKernel(
        seed=7402,
        state_dim=16,
        run_label="integrated-inquiry-no-route",
    )
    kernel.apply_experience(
        _experience(
            "integrated-dependency-no-route",
            relations=(
                RelationProposal(
                    source_label="stabilize loop",
                    target_label="pressure input",
                    relation_type="requires",
                    confidence=0.9,
                ),
            ),
        )
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="patch-bearing"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:no-projected-path",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_unrelated_eligible_obligation_rejects_transaction_without_partial_writes() -> None:
    kernel = _kernel()
    DependencyGapPipeline().observe_gap(
        kernel,
        target_action_node="action:external",
        missing_input_signature="input:external",
        trigger_relation="requires",
        triggering_refs=("action:external", "input:external"),
        source_event_key="external-gap",
        context_snapshot_hash="external-context",
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="exactly the eligible"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:incomplete-set",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_detected_simulation_leak_is_not_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    real_execute = CounterfactualRuntime.execute

    def leaking_execute(self, staged_kernel, **kwargs):
        result = real_execute(self, staged_kernel, **kwargs)
        staged_kernel.state.cycle += 1
        return result

    monkeypatch.setattr(CounterfactualRuntime, "execute", leaking_execute)
    coordinator = DependencyGapInquiryCoordinator(
        policy=IntegratedInquiryPolicy(maximum_simulations_per_obligation=1)
    )

    with pytest.raises(IntegratedInquiryError, match="changed canonical state"):
        coordinator.run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:leak",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_rehashed_trace_cannot_drop_internal_provenance() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:tamper",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["detection_candidate_ids"] = ("dependency_gap_candidate_forged",)

    with pytest.raises(ValueError, match="lost its detector candidate"):
        IntegratedInquiryTrace.build(**payload)


def test_rehashed_trace_cannot_drop_matched_receipt() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:drop-match",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["matched_observations"] = ()

    with pytest.raises(ValueError):
        IntegratedInquiryTrace.build(**payload)


def test_rehashed_trace_cannot_drop_resolution_coverage_receipt() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:drop-resolution-coverage",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["resolution_evidence_receipts"] = ()

    with pytest.raises(ValueError):
        IntegratedInquiryTrace.build(**payload)


def test_resolution_coverage_rejects_foreign_simulation_ledger() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:foreign-resolution-ledger",
    )
    pair = result.matched_pairs[0]
    hypothesis = next(
        item for item in result.hypotheses if item.hypothesis_id == pair.hypothesis_id
    )

    with pytest.raises(TraceResolutionEvidenceIntegrityError):
        TraceResolutionEvidenceDeriver().derive(
            kernel,
            SimulationLedger(),
            obligation_event_ref=pair.resolution_evidence.obligation_event_ref,
            hypothesis=hypothesis,
            plans=pair.plans,
            baseline_result=pair.baseline,
            treatment_result=pair.treatment,
            observation=pair.observation,
            operational_observation=pair.operational_observation,
        )


def test_resolution_coverage_cannot_claim_readiness_or_hide_missing_fields() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:resolution-coverage-authority",
    )
    receipt = result.matched_pairs[0].resolution_evidence
    ready_payload = receipt.model_dump(mode="python")
    ready_payload["resolution_trial_ready"] = True
    with pytest.raises(ValueError, match="cannot claim"):
        TraceResolutionEvidenceReceipt.model_validate(ready_payload)

    hidden_payload = receipt.model_dump(mode="python")
    hidden_payload["missing_requirements"] = ()
    with pytest.raises(ValueError, match="Missing operational"):
        TraceResolutionEvidenceReceipt.model_validate(hidden_payload)

    false_gain = receipt.model_dump(mode="python")
    false_gain["overlay_newly_retrieved_evidence_refs"] = ()
    with pytest.raises(ValueError, match="access gain"):
        TraceResolutionEvidenceReceipt.model_validate(false_gain)


def test_rehashed_trace_cannot_drop_operational_probe() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:drop-operational-probe",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["operational_probe_observations"] = ()

    with pytest.raises(ValueError):
        IntegratedInquiryTrace.build(**payload)


@pytest.mark.parametrize(
    "field",
    (
        "controlled_trial_observations",
        "held_out_replication_receipts",
        "workspace_admission_observations",
        "held_out_workspace_admission_receipts",
        "outgoing_action_observations",
        "held_out_outgoing_action_receipts",
    ),
)
def test_rehashed_controlled_trace_cannot_drop_control_evidence(
    field: str,
) -> None:
    kernel = _kernel()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:drop-controlled-evidence",
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload[field] = ()

    with pytest.raises(ValueError):
        IntegratedInquiryTrace.build(**payload)


def test_native_workspace_slot_cap_suppresses_excess_retrieved_evidence() -> None:
    kernel = _kernel()
    kernel.apply_experience(
        _experience(
            "integrated-grounding-second",
            labels=("grounded reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(lenses, slot_budget=1)
    canonical_workspace_before = (
        dict(kernel.state.workspace_items),
        tuple(kernel.state.workspace_cycle_events),
        kernel.state.workspace_policy,
    )

    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:workspace-slot-cap",
        lenses=lenses,
        trial_controls=controls,
    )

    assert len(result.matched_pairs) == 2
    for pair in result.matched_pairs:
        workspace = pair.workspace_admission_observation
        assert workspace is not None
        treatment = workspace.treatment
        assert len(treatment.submitted_retrieved_evidence_refs) == 2
        assert len(treatment.admitted_retrieved_evidence_refs) == 1
        assert len(treatment.suppressed_retrieved_evidence_refs) == 1
        assert treatment.declared_slot_budget == 1
        assert len(treatment.workspace_event.active_item_ids) == 1
        assert treatment.declared_slot_budget_enforced
        action = pair.outgoing_action_observation
        assert action is not None
        assert action.treatment.action_workspace_event is not None
        assert len(action.treatment.action_workspace_event.active_item_ids) == 1
        assert action.treatment.outgoing_action_signature_observed
    assert (
        dict(kernel.state.workspace_items),
        tuple(kernel.state.workspace_cycle_events),
        kernel.state.workspace_policy,
    ) == canonical_workspace_before


def test_workspace_observer_tamper_rejects_entire_staged_transaction() -> None:
    class TamperingWorkspaceObserver:
        def observe(self, *args, **kwargs):
            observation = NativeWorkspaceAdmissionObserver().observe(
                *args, **kwargs
            )
            return observation.model_copy(
                update={"canonical_commit_permitted": True}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="Native workspace-admission observation failed validation",
    ):
        DependencyGapInquiryCoordinator(
            workspace_admission_observer=TamperingWorkspaceObserver()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:workspace-tamper",
            lenses=lenses,
            trial_controls=_trial_controls(lenses),
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_workspace_observer_cannot_relax_canonical_slot_policy() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    controls = _trial_controls(
        lenses,
        slot_budget=kernel.state.workspace_policy.max_active_items + 1,
    )
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="cannot relax canonical policy",
    ):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:workspace-relaxed-cap",
            lenses=lenses,
            trial_controls=controls,
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_workspace_receipt_rehash_cannot_claim_canonical_authority() -> None:
    kernel = _kernel()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:workspace-authority",
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    receipt = result.matched_pairs[0].workspace_admission_observation
    assert receipt is not None
    payload = receipt.model_dump(mode="python")
    payload["canonical_commit_permitted"] = True

    with pytest.raises(ValueError, match="authority boundary"):
        MatchedWorkspaceAdmissionObservation.model_validate(payload)


def test_workspace_observer_rejects_foreign_simulation_ledger() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:workspace-foreign-ledger",
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    pair = result.matched_pairs[0]
    assert pair.context is not None
    assert pair.controlled_observation is not None
    hypothesis = next(
        item for item in result.hypotheses if item.hypothesis_id == pair.hypothesis_id
    )
    canonical_before = kernel.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        WorkspaceAdmissionProbeIntegrityError,
        match="foreign or altered simulation record",
    ):
        NativeWorkspaceAdmissionObserver().observe(
            kernel,
            SimulationLedger(),
            lenses,
            context=pair.context,
            hypothesis=hypothesis,
            baseline_plan=pair.plans.baseline,
            baseline_result=pair.baseline,
            treatment_plan=pair.plans.treatment,
            treatment_result=pair.treatment,
            controlled_observation=pair.controlled_observation,
        )

    assert kernel.fingerprint() == canonical_before
    assert lenses.fingerprint() == lens_before


def test_outgoing_action_observer_tamper_rejects_entire_staged_transaction() -> None:
    class TamperingActionObserver:
        def observe(self, *args, **kwargs):
            observation = NativeOutgoingActionObserver().observe(*args, **kwargs)
            return observation.model_copy(
                update={"canonical_commit_permitted": True}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="Native outgoing-action observation failed validation",
    ):
        DependencyGapInquiryCoordinator(
            outgoing_action_observer=TamperingActionObserver()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:action-tamper",
            lenses=lenses,
            trial_controls=_trial_controls(lenses),
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_outgoing_action_policy_substitution_is_recomputed_and_rejected() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()
    substituted = NativeOutgoingActionObserver(
        NativeOutgoingActionProbePolicy(urgency=0.60)
    )

    with pytest.raises(
        IntegratedInquiryError,
        match="Outgoing-action observer disagrees",
    ):
        DependencyGapInquiryCoordinator(
            outgoing_action_observer=substituted
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:action-policy-substitution",
            lenses=lenses,
            trial_controls=_trial_controls(lenses),
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before
    assert lenses.fingerprint() == lens_before


def test_outgoing_action_receipt_cannot_claim_execution_or_authority() -> None:
    kernel = _kernel()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:action-authority",
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    receipt = result.matched_pairs[0].outgoing_action_observation
    assert receipt is not None

    for field in (
        "external_action_executed",
        "canonical_dependency_path_established",
        "observed_outcome_authority_enabled",
        "resolution_authority_enabled",
        "canonical_commit_permitted",
    ):
        payload = receipt.model_dump(mode="python")
        payload[field] = True
        with pytest.raises(ValueError, match="authority boundary"):
            MatchedOutgoingActionObservation.model_validate(payload)


def test_outgoing_action_observer_rejects_foreign_simulation_ledger() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:action-foreign-ledger",
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    pair = result.matched_pairs[0]
    assert pair.context is not None
    assert pair.controlled_observation is not None
    assert pair.workspace_admission_observation is not None
    hypothesis = next(
        item for item in result.hypotheses if item.hypothesis_id == pair.hypothesis_id
    )
    canonical_before = kernel.fingerprint()
    lens_before = lenses.fingerprint()

    with pytest.raises(OutgoingActionProbeIntegrityError):
        NativeOutgoingActionObserver().observe(
            kernel,
            SimulationLedger(),
            lenses,
            context=pair.context,
            hypothesis=hypothesis,
            baseline_plan=pair.plans.baseline,
            baseline_result=pair.baseline,
            treatment_plan=pair.plans.treatment,
            treatment_result=pair.treatment,
            controlled_observation=pair.controlled_observation,
            workspace_observation=pair.workspace_admission_observation,
        )

    assert kernel.fingerprint() == canonical_before
    assert lenses.fingerprint() == lens_before


def test_tampered_operational_probe_rejects_staged_transaction() -> None:
    class TamperingOperationalProbe:
        def observe(self, *args, **kwargs):
            observation = OverlayOperationalProbe().observe(*args, **kwargs)
            return observation.model_copy(
                update={"canonical_commit_permitted": True}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="Operational probe"):
        DependencyGapInquiryCoordinator(
            operational_probe=TamperingOperationalProbe()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:tampered-operational-probe",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def _controlled_receipt_experiment(
    source_event_key: str,
) -> tuple[
    VerdantKernel,
    CounterfactualRuntime,
    EquivalenceLensSystem,
    object,
]:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    lenses = _lenses(kernel)
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key=source_event_key,
        lenses=lenses,
        trial_controls=_trial_controls(lenses),
    )
    return kernel, runtime, lenses, result


def test_integrated_receipt_sidecar_round_trips_against_exact_vob_pair(
    tmp_path: Path,
) -> None:
    kernel, runtime, lenses, result = _controlled_receipt_experiment(
        "integrated-inquiry:durable-receipt"
    )
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    lens_before = lenses.fingerprint()
    expected = integrated_inquiry_receipt_bytes(
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )
    assert expected == integrated_inquiry_receipt_bytes(
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )

    archive_path = tmp_path / "controlled.vob"
    receipt_path = tmp_path / "controlled.viq"
    save_experiment_archive(
        archive_path,
        kernel,
        runtime.ledger,
        lens_system=lenses,
    )
    receipt_digest = save_integrated_inquiry_receipt(
        receipt_path,
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )
    assert receipt_path.read_bytes() == expected
    assert receipt_digest == hashlib.sha256(expected).hexdigest()

    bundle = load_experiment_archive_bundle(archive_path)
    assert bundle.lens_system is not None
    restored = load_integrated_inquiry_receipt(
        receipt_path,
        kernel=bundle.kernel,
        simulation_ledger=bundle.simulation_ledger,
        lens_system=bundle.lens_system,
    )
    assert restored == result.trace
    assert restored.outgoing_action_observations
    assert restored.held_out_outgoing_action_receipts
    assert bundle.kernel.fingerprint() == canonical_before
    assert bundle.simulation_ledger.fingerprint() == simulation_before
    assert bundle.lens_system.fingerprint() == lens_before
    assert len(bundle.simulation_ledger.state.reservations) == 5
    assert len(bundle.simulation_ledger.state.settlements) == 5


def test_integrated_receipt_rejects_rehashed_authority_and_missing_evidence(
    tmp_path: Path,
) -> None:
    kernel, runtime, lenses, result = _controlled_receipt_experiment(
        "integrated-inquiry:durable-tamper"
    )
    path = tmp_path / "tampered.viq"
    data = integrated_inquiry_receipt_bytes(
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )

    authority = json.loads(data)
    authority["trace"]["outgoing_action_observations"][0]["treatment"][
        "external_action_executed"
    ] = True
    authority["trace_sha256"] = hashlib.sha256(
        canonical_json_bytes(authority["trace"])
    ).hexdigest()
    path.write_bytes(canonical_json_bytes(authority))
    with pytest.raises(
        IntegratedInquiryReceiptIntegrityError,
        match="Invalid integrated inquiry receipt",
    ):
        load_integrated_inquiry_receipt(
            path,
            kernel=kernel,
            simulation_ledger=runtime.ledger,
            lens_system=lenses,
        )

    missing = json.loads(data)
    missing["trace"]["outgoing_action_observations"] = []
    missing["trace_sha256"] = hashlib.sha256(
        canonical_json_bytes(missing["trace"])
    ).hexdigest()
    path.write_bytes(canonical_json_bytes(missing))
    with pytest.raises(
        IntegratedInquiryReceiptIntegrityError,
        match="Invalid integrated inquiry receipt",
    ):
        load_integrated_inquiry_receipt(
            path,
            kernel=kernel,
            simulation_ledger=runtime.ledger,
            lens_system=lenses,
        )


def test_integrated_receipt_rejects_foreign_sidecar_pairing(tmp_path: Path) -> None:
    kernel, runtime, lenses, result = _controlled_receipt_experiment(
        "integrated-inquiry:durable-foreign"
    )
    path = tmp_path / "paired.viq"
    save_integrated_inquiry_receipt(
        path,
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )

    foreign_kernel = VerdantKernel(
        seed=7499,
        state_dim=16,
        run_label="foreign-integrated-receipt",
    )
    for kwargs in (
        {
            "kernel": foreign_kernel,
            "simulation_ledger": runtime.ledger,
            "lens_system": lenses,
        },
        {
            "kernel": kernel,
            "simulation_ledger": SimulationLedger(),
            "lens_system": lenses,
        },
        {
            "kernel": kernel,
            "simulation_ledger": runtime.ledger,
            "lens_system": EquivalenceLensSystem(),
        },
    ):
        with pytest.raises(
            IntegratedInquiryReceiptIntegrityError,
            match="pairing mismatch",
        ):
            load_integrated_inquiry_receipt(path, **kwargs)


def test_integrated_receipt_rejects_uncontrolled_pre_v030_trace() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:durable-incomplete",
    )
    lenses = _lenses(kernel)

    with pytest.raises(
        IntegratedInquiryReceiptIntegrityError,
        match="predeclared controlled-trial lineage",
    ):
        integrated_inquiry_receipt_bytes(
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )


def test_integrated_receipt_atomic_replace_preserves_prior_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    kernel, runtime, lenses, result = _controlled_receipt_experiment(
        "integrated-inquiry:durable-atomic"
    )
    path = tmp_path / "atomic.viq"
    save_integrated_inquiry_receipt(
        path,
        kernel,
        runtime.ledger,
        lenses,
        result.trace,
    )
    before = path.read_bytes()

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("injected receipt replace failure")

    monkeypatch.setattr(
        "verdant_obligations.inquiry_receipts.os.replace",
        fail_replace,
    )
    with pytest.raises(OSError, match="injected receipt replace failure"):
        save_integrated_inquiry_receipt(
            path,
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
    assert path.read_bytes() == before
    assert list(tmp_path.glob(".atomic.viq.*.tmp")) == []


requires_posix_history = pytest.mark.skipif(
    os.name != "posix",
    reason="receipt-history writer arbitration requires POSIX flock",
)
requires_posix_history_fork = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "fork"),
    reason="controlled receipt-history process tests require POSIX fork",
)


def _receipt_digest(kernel, runtime, lenses, result) -> str:
    return hashlib.sha256(
        integrated_inquiry_receipt_bytes(
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
    ).hexdigest()


@requires_posix_history
def test_integrated_receipt_history_is_cumulative_idempotent_and_exactly_paired(
    tmp_path: Path,
) -> None:
    first = _controlled_receipt_experiment("integrated-history:first")
    second = _controlled_receipt_experiment("integrated-history:second")
    path = tmp_path / "inquiries.viqh"
    fingerprints = tuple(
        (
            kernel.fingerprint(),
            runtime.ledger.fingerprint(),
            lenses.fingerprint(),
        )
        for kernel, runtime, lenses, _ in (first, second)
    )

    receipt_ids = tuple(
        append_integrated_inquiry_receipt_history(
            path,
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
        for kernel, runtime, lenses, result in (first, second)
    )
    assert receipt_ids == tuple(
        _receipt_digest(*experiment) for experiment in (first, second)
    )
    assert append_integrated_inquiry_receipt_history(
        path,
        first[0],
        first[1].ledger,
        first[2],
        first[3].trace,
    ) == receipt_ids[0]

    history = read_integrated_inquiry_receipt_history(path)
    assert path.read_bytes() == integrated_inquiry_receipt_history_bytes(history)
    assert tuple(item.sequence for item in history.entries) == (1, 2)
    assert tuple(item.receipt_sha256 for item in history.entries) == receipt_ids
    assert history.entries[0].previous_entry_sha256 == "0" * 64
    assert history.entries[1].previous_entry_sha256 != "0" * 64
    assert len(history.entries) == 2

    for receipt_id, experiment in zip(receipt_ids, (first, second), strict=True):
        kernel, runtime, lenses, result = experiment
        reservations = len(runtime.ledger.state.reservations)
        settlements = len(runtime.ledger.state.settlements)
        restored = load_integrated_inquiry_receipt_history_entry(
            path,
            receipt_id,
            kernel=kernel,
            simulation_ledger=runtime.ledger,
            lens_system=lenses,
        )
        assert restored == result.trace
        assert len(runtime.ledger.state.reservations) == reservations
        assert len(runtime.ledger.state.settlements) == settlements

    with pytest.raises(
        IntegratedInquiryReceiptIntegrityError,
        match="pairing mismatch",
    ):
        load_integrated_inquiry_receipt_history_entry(
            path,
            receipt_ids[0],
            kernel=second[0],
            simulation_ledger=second[1].ledger,
            lens_system=second[2],
        )
    assert tuple(
        (
            kernel.fingerprint(),
            runtime.ledger.fingerprint(),
            lenses.fingerprint(),
        )
        for kernel, runtime, lenses, _ in (first, second)
    ) == fingerprints


@requires_posix_history
def test_integrated_receipt_history_rejects_reorder_truncation_and_rehashed_authority(
    tmp_path: Path,
) -> None:
    experiments = (
        _controlled_receipt_experiment("integrated-history:tamper:first"),
        _controlled_receipt_experiment("integrated-history:tamper:second"),
    )
    path = tmp_path / "tampered.viqh"
    for kernel, runtime, lenses, result in experiments:
        append_integrated_inquiry_receipt_history(
            path,
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
    original = path.read_bytes()

    reordered = json.loads(original)
    reordered["entries"] = list(reversed(reordered["entries"]))
    path.write_bytes(canonical_json_bytes(reordered))
    with pytest.raises(IntegratedInquiryReceiptIntegrityError):
        read_integrated_inquiry_receipt_history(path)

    truncated = json.loads(original)
    truncated["entries"] = truncated["entries"][:-1]
    path.write_bytes(canonical_json_bytes(truncated))
    with pytest.raises(IntegratedInquiryReceiptIntegrityError):
        read_integrated_inquiry_receipt_history(path)

    authority = json.loads(original)
    authority["entries"][0]["receipt"]["trace"][
        "outgoing_action_observations"
    ][0]["treatment"]["external_action_executed"] = True
    receipt = authority["entries"][0]["receipt"]
    receipt["trace_sha256"] = hashlib.sha256(
        canonical_json_bytes(receipt["trace"])
    ).hexdigest()
    authority["entries"][0]["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(receipt)
    ).hexdigest()
    previous = "0" * 64
    for entry in authority["entries"]:
        entry["previous_entry_sha256"] = previous
        previous = hashlib.sha256(canonical_json_bytes(entry)).hexdigest()
    authority["head_sha256"] = previous
    path.write_bytes(canonical_json_bytes(authority))
    with pytest.raises(
        IntegratedInquiryReceiptIntegrityError,
        match="Invalid integrated inquiry receipt history",
    ):
        read_integrated_inquiry_receipt_history(path)


def _read_history_writer_marker(file_descriptor: int) -> None:
    readable, _, _ = select.select([file_descriptor], [], [], 10.0)
    if not readable:
        pytest.fail("child receipt-history writer did not reach its gate")
    marker = os.read(file_descriptor, 1)
    if marker != b"R":
        pytest.fail(f"child receipt-history writer failed before its gate: {marker!r}")


def _phase_paused_history_writer(
    path: Path,
    experiment,
    phase: str,
    ready_file_descriptor: int,
) -> None:
    import verdant_obligations.inquiry_receipts as receipt_module

    try:
        if phase == "before_replace":

            def pause_before_replace(_source: Path, _target: Path) -> None:
                os.write(ready_file_descriptor, b"R")
                while True:
                    signal.pause()

            receipt_module.os.replace = pause_before_replace
        elif phase == "after_replace":
            real_fsync = receipt_module.os.fsync
            fsync_count = 0

            def pause_before_directory_sync(file_descriptor: int) -> None:
                nonlocal fsync_count
                fsync_count += 1
                if fsync_count == 2:
                    os.write(ready_file_descriptor, b"R")
                    while True:
                        signal.pause()
                real_fsync(file_descriptor)

            receipt_module.os.fsync = pause_before_directory_sync
        else:  # pragma: no cover - helper misuse
            raise AssertionError(f"unknown receipt-history phase: {phase}")

        kernel, runtime, lenses, result = experiment
        append_integrated_inquiry_receipt_history(
            path,
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
    except BaseException:
        try:
            os.write(ready_file_descriptor, b"E")
        finally:
            os._exit(2)
    os._exit(3)


def _kill_history_writer_at_phase(path: Path, experiment, phase: str) -> None:
    ready_read, ready_write = os.pipe()
    process_id = os.fork()
    if process_id == 0:
        os.close(ready_read)
        _phase_paused_history_writer(path, experiment, phase, ready_write)

    os.close(ready_write)
    reaped = False
    try:
        _read_history_writer_marker(ready_read)
        os.kill(process_id, signal.SIGKILL)
        _, status = os.waitpid(process_id, 0)
        reaped = True
        assert os.WIFSIGNALED(status)
        assert os.WTERMSIG(status) == signal.SIGKILL
    finally:
        os.close(ready_read)
        if not reaped:
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(process_id, 0)


@requires_posix_history_fork
def test_integrated_receipt_history_process_kill_exposes_complete_prefix(
    tmp_path: Path,
) -> None:
    for phase, candidate_visible in (
        ("before_replace", False),
        ("after_replace", True),
    ):
        directory = tmp_path / phase
        directory.mkdir()
        path = directory / "inquiries.viqh"
        expected_path = directory / "expected.viqh"
        initial = _controlled_receipt_experiment(f"history-kill:{phase}:initial")
        candidate = _controlled_receipt_experiment(f"history-kill:{phase}:candidate")
        later = _controlled_receipt_experiment(f"history-kill:{phase}:later")

        initial_id = append_integrated_inquiry_receipt_history(
            path,
            initial[0],
            initial[1].ledger,
            initial[2],
            initial[3].trace,
        )
        append_integrated_inquiry_receipt_history(
            expected_path,
            initial[0],
            initial[1].ledger,
            initial[2],
            initial[3].trace,
        )
        candidate_id = append_integrated_inquiry_receipt_history(
            expected_path,
            candidate[0],
            candidate[1].ledger,
            candidate[2],
            candidate[3].trace,
        )
        initial_bytes = path.read_bytes()
        candidate_bytes = expected_path.read_bytes()

        _kill_history_writer_at_phase(path, candidate, phase)

        assert path.read_bytes() == (
            candidate_bytes if candidate_visible else initial_bytes
        )
        history = read_integrated_inquiry_receipt_history(path)
        assert tuple(item.receipt_sha256 for item in history.entries) == (
            (initial_id, candidate_id) if candidate_visible else (initial_id,)
        )
        temporary_paths = list(directory.glob(".inquiries.viqh.*.tmp"))
        if candidate_visible:
            assert temporary_paths == []
        else:
            assert len(temporary_paths) == 1
            assert temporary_paths[0].read_bytes() == candidate_bytes

        later_id = append_integrated_inquiry_receipt_history(
            path,
            later[0],
            later[1].ledger,
            later[2],
            later[3].trace,
        )
        final_history = read_integrated_inquiry_receipt_history(path)
        expected_ids = (
            (initial_id, candidate_id, later_id)
            if candidate_visible
            else (initial_id, later_id)
        )
        assert tuple(
            item.receipt_sha256 for item in final_history.entries
        ) == expected_ids
        assert list(directory.glob(".inquiries.viqh.*.tmp")) == []


def _gated_history_writer(
    path: Path,
    experiment,
    ready_file_descriptor: int,
    go_file_descriptor: int,
) -> None:
    try:
        os.write(ready_file_descriptor, b"R")
        if os.read(go_file_descriptor, 1) != b"G":
            raise RuntimeError("parent did not release receipt-history writer")
        kernel, runtime, lenses, result = experiment
        append_integrated_inquiry_receipt_history(
            path,
            kernel,
            runtime.ledger,
            lenses,
            result.trace,
        )
    except BaseException:
        os._exit(2)
    os._exit(0)


@requires_posix_history_fork
def test_integrated_receipt_history_concurrent_writers_retain_every_receipt(
    tmp_path: Path,
) -> None:
    path = tmp_path / "concurrent.viqh"
    initial = _controlled_receipt_experiment("history-concurrent:initial")
    initial_id = append_integrated_inquiry_receipt_history(
        path,
        initial[0],
        initial[1].ledger,
        initial[2],
        initial[3].trace,
    )
    experiments = tuple(
        _controlled_receipt_experiment(f"history-concurrent:{index}")
        for index in range(6)
    )
    expected_ids = {
        _receipt_digest(*experiment) for experiment in experiments
    }
    children: list[tuple[int, int, int]] = []
    for experiment in experiments:
        ready_read, ready_write = os.pipe()
        go_read, go_write = os.pipe()
        process_id = os.fork()
        if process_id == 0:
            os.close(ready_read)
            os.close(go_write)
            _gated_history_writer(
                path,
                experiment,
                ready_write,
                go_read,
            )
        os.close(ready_write)
        os.close(go_read)
        children.append((process_id, ready_read, go_write))

    observed: list[tuple[str, ...]] = []
    reader_errors: list[BaseException] = []
    stop_reader = threading.Event()

    def sample_history() -> None:
        try:
            while not stop_reader.is_set():
                history = read_integrated_inquiry_receipt_history(path)
                observed.append(
                    tuple(item.receipt_sha256 for item in history.entries)
                )
        except BaseException as error:  # pragma: no cover - diagnostic guard
            reader_errors.append(error)

    reader: threading.Thread | None = None
    reaped_processes: set[int] = set()
    try:
        for _, ready_read, _ in children:
            _read_history_writer_marker(ready_read)
            os.close(ready_read)
        reader = threading.Thread(target=sample_history, daemon=True)
        reader.start()
        for _, _, go_write in children:
            os.write(go_write, b"G")
            os.close(go_write)
        for process_id, _, _ in children:
            _, status = os.waitpid(process_id, 0)
            reaped_processes.add(process_id)
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == 0
        children.clear()
    finally:
        stop_reader.set()
        if reader is not None:
            reader.join(timeout=5.0)
            assert not reader.is_alive()
        for process_id, ready_read, go_write in children:
            for file_descriptor in (ready_read, go_write):
                try:
                    os.close(file_descriptor)
                except OSError:
                    pass
            if process_id not in reaped_processes:
                try:
                    os.kill(process_id, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(process_id, 0)

    final_history = read_integrated_inquiry_receipt_history(path)
    final_ids = tuple(item.receipt_sha256 for item in final_history.entries)
    assert reader_errors == []
    assert observed
    assert final_ids[0] == initial_id
    assert set(final_ids[1:]) == expected_ids
    assert len(final_ids) == 7
    assert all(
        snapshot == final_ids[: len(snapshot)]
        and len(snapshot) == len(set(snapshot))
        for snapshot in observed
    )
    assert list(tmp_path.glob(".concurrent.viqh.*.tmp")) == []
    for experiment in experiments:
        receipt_id = _receipt_digest(*experiment)
        restored = load_integrated_inquiry_receipt_history_entry(
            path,
            receipt_id,
            kernel=experiment[0],
            simulation_ledger=experiment[1].ledger,
            lens_system=experiment[2],
        )
        assert restored == experiment[3].trace
