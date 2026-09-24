from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from verdant_kernel import ExperienceCommand, ObligationFamily, RelationProposal, VerdantKernel
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualPlan,
    CounterfactualRuntime,
    CouncilInterventionCandidate,
    CouncilInterventionIntegrityError,
    CouncilInterventionLedgerState,
    CouncilLeastRegretTournament,
    CouncilTournamentDecision,
    CouncilTournamentDisposition,
    DependencyGapDetector,
    DiagnosticConclusion,
    DiagnosticEngine,
    DiagnosticLedgerState,
    DiagnosticProbeFinding,
    DiagnosticProbeKind,
    DiagnosticProbeObservation,
    DiagnosticResult,
    DiagnosticTriggerKind,
    EpistemicPreservationObservation,
    EquivalenceLensSystem,
    InquiryFailureEvidence,
    InterventionKind,
    LensOpcode,
    OrthogonalFingerprintObservation,
    SimulationDisposition,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CouncilFixture:
    kernel: VerdantKernel
    runtime: CounterfactualRuntime
    lenses: EquivalenceLensSystem
    diagnostics: DiagnosticEngine
    diagnostic_result_id: str
    allocation_id: str
    obligation_id: str
    candidates: tuple[CouncilInterventionCandidate, ...]
    evaluations: tuple[EpistemicPreservationObservation, ...]


def _simulation(
    kernel: VerdantKernel,
    runtime: CounterfactualRuntime,
    allocation_id: str,
    key: str,
    *result_refs: str,
):
    return runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key=f"simulation:{key}",
            operator_version=f"{key}-v1",
            requested_budget=0.008,
            consumed_budget=0.003,
            result_refs=result_refs,
        ),
    ).settlement


def _fixture() -> CouncilFixture:
    kernel = VerdantKernel(seed=5901, state_dim=16, run_label="least-regret-council")
    kernel.apply_experience(
        ExperienceCommand(
            event_key="council-dependency",
            source_ref="curriculum:council",
            modality="text",
            payload_sha256=_digest("council-dependency"),
            feature_vector=tuple(index / 15.0 for index in range(16)),
            relation_proposals=(
                RelationProposal(
                    source_label="council action",
                    target_label="missing council input",
                    relation_type="requires",
                ),
            ),
        )
    )
    obligation = DependencyGapDetector().detect_and_record(kernel).mutations[0].obligation
    hypothesis_ref = "hypothesis:council-interaction"
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION, LensOpcode.SELECT_ACTIVATED_REFS),
        provenance_refs=("council:lens-control",),
    )
    binding = lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("council:calibration",),
        source_event_key="lens:council",
        cycle=kernel.state.cycle,
    )
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="council_test_inquiry",
                requested_budget=0.20,
                estimated_cost=0.10,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.6,
                novelty=0.7,
                metric_provenance_refs=(hypothesis_ref,),
                generator_version="council-test-generator-v1",
            ),
        ),
        source_event_key="attention:council",
    ).decision
    allocation = decision.allocations[0]
    runtime = CounterfactualRuntime()
    trigger_settlement = _simulation(
        kernel,
        runtime,
        allocation.allocation_id,
        "council-trigger",
        hypothesis_ref,
    )
    trigger = InquiryFailureEvidence.build(
        trigger_kind=DiagnosticTriggerKind.INQUIRY_FAILURE,
        attention_decision_id=decision.decision_id,
        failed_settlement_id=trigger_settlement.settlement_id,
        obligation_id=obligation.kernel_id,
        lens_binding_id=binding.binding_id,
        lens_definition_id=definition.definition_id,
        hypothesis_ref=hypothesis_ref,
        completed_within_predicted_cost=True,
        graph_traversal_valid=True,
        action_executed=False,
        explanatory_gain_observed=False,
        evidence_refs=tuple(sorted((
            decision.decision_id,
            trigger_settlement.settlement_id,
            binding.binding_id,
            definition.definition_id,
            hypothesis_ref,
        ))),
    )
    diagnostics = DiagnosticEngine()
    diagnostic = diagnostics.open(
        kernel,
        trigger=trigger,
        simulation_ledger=runtime.ledger,
        lens_system=lenses,
        source_event_key="diagnostic:council-open",
    )

    def diagnostic_probe(kind, finding, suffix, basis):
        settlement = _simulation(
            kernel,
            runtime,
            allocation.allocation_id,
            f"council-diagnostic-{suffix}",
            diagnostic.diagnostic_id,
            basis,
        )
        return DiagnosticProbeObservation.build(
            diagnostic_id=diagnostic.diagnostic_id,
            kind=kind,
            finding=finding,
            simulation_settlement_id=settlement.settlement_id,
            basis_refs=(basis,),
        )

    probes = (
        diagnostic_probe(
            DiagnosticProbeKind.PRIMITIVE_BASELINE,
            DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT,
            "lens",
            "diagnostic:basis:lens",
        ),
        diagnostic_probe(
            DiagnosticProbeKind.COST_CALIBRATION,
            DiagnosticProbeFinding.COST_EXCEEDED,
            "scheduler",
            "diagnostic:basis:scheduler",
        ),
    )
    result = diagnostics.conclude(
        diagnostic_id=diagnostic.diagnostic_id,
        probes=probes,
        simulation_ledger=runtime.ledger,
        source_event_key="diagnostic:council-conclude",
    )
    assert result.conclusion == DiagnosticConclusion.INTERACTION_SUSPECTED
    candidates = (
        CouncilInterventionCandidate.build(
            diagnostic_result_id=result.result_id,
            kind=InterventionKind.DEMOTE_LENS,
            target_component_refs=(definition.definition_id,),
            proposed_variant_ref="variant:lens-demotion",
            basis_refs=(result.result_id, "intervention:basis:lens"),
        ),
        CouncilInterventionCandidate.build(
            diagnostic_result_id=result.result_id,
            kind=InterventionKind.ADJUST_ATTENTION_POLICY,
            target_component_refs=(decision.decision_id,),
            proposed_variant_ref="variant:attention-adjustment",
            basis_refs=(result.result_id, "intervention:basis:attention"),
        ),
        CouncilInterventionCandidate.build(
            diagnostic_result_id=result.result_id,
            kind=InterventionKind.COORDINATED_SUBSTITUTION,
            target_component_refs=(definition.definition_id, decision.decision_id),
            proposed_variant_ref="variant:coordinated",
            basis_refs=(result.result_id, "intervention:basis:coordinated"),
        ),
    )
    checkpoint = kernel.fingerprint()
    vectors = (
        ((obligation.kernel_id,), 10, 10, 10),
        ((), 30, 30, 30),
        ((obligation.kernel_id,), 20, 20, 20),
    )
    evaluations = []
    for index, (candidate, vector) in enumerate(zip(candidates, vectors, strict=True)):
        basis = f"preservation:basis:{index}"
        settlement = _simulation(
            kernel,
            runtime,
            allocation.allocation_id,
            f"council-intervention-{index}",
            candidate.candidate_id,
            basis,
        )
        fingerprint = _digest(f"orthogonal:{index}")
        evaluations.append(EpistemicPreservationObservation.build(
            candidate_id=candidate.candidate_id,
            simulation_settlement_id=settlement.settlement_id,
            checkpoint_fingerprint=checkpoint,
            repair_restored=True,
            would_reopen_obligation_ids=vector[0],
            wave_state_deviation_ppm=vector[1],
            c_memory_deviation_units=vector[2],
            tg_observer_deviation_ppm=vector[3],
            orthogonal_fingerprints=(OrthogonalFingerprintObservation(
                context_ref="orthogonal:context:stable-suite",
                before_fingerprint=fingerprint,
                after_fingerprint=fingerprint,
            ),),
            basis_refs=(basis,),
        ))
    return CouncilFixture(
        kernel=kernel,
        runtime=runtime,
        lenses=lenses,
        diagnostics=diagnostics,
        diagnostic_result_id=result.result_id,
        allocation_id=allocation.allocation_id,
        obligation_id=obligation.kernel_id,
        candidates=candidates,
        evaluations=tuple(evaluations),
    )


def _replace_evaluation(evaluation, **updates):
    values = evaluation.model_dump(mode="python", exclude={"evaluation_id"})
    values.update(updates)
    return EpistemicPreservationObservation.build(**values)


def _decide(fixture: CouncilFixture, **updates):
    values = {
        "diagnostic_result_id": fixture.diagnostic_result_id,
        "candidates": fixture.candidates,
        "evaluations": fixture.evaluations,
        "diagnostics": fixture.diagnostics,
        "simulation_ledger": fixture.runtime.ledger,
        "lens_system": fixture.lenses,
        "source_event_key": "council:tournament",
    }
    values.update(updates)
    tournament = values.pop("tournament", CouncilLeastRegretTournament())
    return tournament, tournament.decide(fixture.kernel, **values)


def test_pareto_tournament_uses_minimax_regret_and_does_not_apply_edit() -> None:
    fixture = _fixture()
    kernel_before = fixture.kernel.fingerprint()
    simulation_before = fixture.runtime.ledger.fingerprint()
    lens_before = fixture.lenses.fingerprint()
    diagnostic_before = fixture.diagnostics.fingerprint()

    _, decision = _decide(fixture)

    assert decision.disposition == CouncilTournamentDisposition.RECOMMEND
    assert decision.selected_candidate_id == fixture.candidates[0].candidate_id
    assert set(decision.pareto_frontier_candidate_ids) == {
        fixture.candidates[0].candidate_id,
        fixture.candidates[1].candidate_id,
    }
    dominated = next(
        item for item in decision.assessments
        if item.candidate_id == fixture.candidates[2].candidate_id
    )
    assert dominated.exclusion_codes == ("pareto_dominated",)
    assert not decision.intervention_authority_enabled
    assert fixture.kernel.fingerprint() == kernel_before
    assert fixture.runtime.ledger.fingerprint() == simulation_before
    assert fixture.lenses.fingerprint() == lens_before
    assert fixture.diagnostics.fingerprint() == diagnostic_before


def test_component_footprint_is_only_a_preservation_tiebreaker() -> None:
    fixture = _fixture()
    first, second, _ = fixture.evaluations
    tied_second = _replace_evaluation(
        second,
        would_reopen_obligation_ids=first.would_reopen_obligation_ids,
        wave_state_deviation_ppm=first.wave_state_deviation_ppm,
        c_memory_deviation_units=first.c_memory_deviation_units,
        tg_observer_deviation_ppm=first.tg_observer_deviation_ppm,
    )
    candidates = (fixture.candidates[2], fixture.candidates[1])
    evaluations = (fixture.evaluations[2], tied_second)
    coordinated_tied = _replace_evaluation(
        evaluations[0],
        would_reopen_obligation_ids=tied_second.would_reopen_obligation_ids,
        wave_state_deviation_ppm=tied_second.wave_state_deviation_ppm,
        c_memory_deviation_units=tied_second.c_memory_deviation_units,
        tg_observer_deviation_ppm=tied_second.tg_observer_deviation_ppm,
    )

    _, decision = _decide(
        fixture,
        candidates=candidates,
        evaluations=(coordinated_tied, tied_second),
    )

    assert decision.selected_candidate_id == fixture.candidates[1].candidate_id


def test_high_blast_radius_is_a_cost_not_a_permanent_veto() -> None:
    fixture = _fixture()
    lens_eval, attention_eval, _ = fixture.evaluations
    high_blast_low_ripple = _replace_evaluation(
        lens_eval,
        wave_state_deviation_ppm=0,
        c_memory_deviation_units=0,
        tg_observer_deviation_ppm=0,
    )
    low_blast_high_ripple = _replace_evaluation(
        attention_eval,
        wave_state_deviation_ppm=100,
        c_memory_deviation_units=100,
        tg_observer_deviation_ppm=100,
    )

    _, decision = _decide(
        fixture,
        candidates=fixture.candidates[:2],
        evaluations=(high_blast_low_ripple, low_blast_high_ripple),
    )

    assert decision.selected_candidate_id == fixture.candidates[0].candidate_id


def test_orthogonal_corruption_and_failed_repair_are_hard_exclusions() -> None:
    fixture = _fixture()
    first, second, _ = fixture.evaluations
    unstable = first.orthogonal_fingerprints[0].model_copy(
        update={"after_fingerprint": _digest("corrupted")}
    )
    corrupted = _replace_evaluation(first, orthogonal_fingerprints=(unstable,))
    failed = _replace_evaluation(second, repair_restored=False)

    _, decision = _decide(
        fixture,
        candidates=fixture.candidates[:2],
        evaluations=(corrupted, failed),
    )

    assert decision.disposition == CouncilTournamentDisposition.ABSTAIN
    assert decision.selected_candidate_id is None
    codes = {item.candidate_id: item.exclusion_codes for item in decision.assessments}
    assert "orthogonal_fingerprint_changed" in codes[fixture.candidates[0].candidate_id]
    assert "repair_not_restored" in codes[fixture.candidates[1].candidate_id]


def test_missing_simulation_lineage_is_excluded() -> None:
    fixture = _fixture()
    first, second, _ = fixture.evaluations
    forged = _replace_evaluation(first, basis_refs=("preservation:basis:invented",))

    _, decision = _decide(
        fixture,
        candidates=fixture.candidates[:2],
        evaluations=(forged, second),
    )

    assessment = next(
        item for item in decision.assessments
        if item.candidate_id == fixture.candidates[0].candidate_id
    )
    assert "simulation_lineage_missing" in assessment.exclusion_codes
    assert decision.selected_candidate_id == fixture.candidates[1].candidate_id


def test_candidates_must_share_the_same_orthogonal_validation_suite() -> None:
    fixture = _fixture()
    second = fixture.evaluations[1]
    observation = second.orthogonal_fingerprints[0]
    mismatched = _replace_evaluation(
        second,
        orthogonal_fingerprints=(OrthogonalFingerprintObservation(
            context_ref="orthogonal:context:different-suite",
            before_fingerprint=observation.before_fingerprint,
            after_fingerprint=observation.after_fingerprint,
        ),),
    )

    with pytest.raises(CouncilInterventionIntegrityError, match="validation suite"):
        _decide(
            fixture,
            candidates=fixture.candidates[:2],
            evaluations=(fixture.evaluations[0], mismatched),
        )


def test_cancelled_counterfactual_cannot_support_an_intervention() -> None:
    fixture = _fixture()
    candidate = fixture.candidates[0]
    basis = "preservation:basis:cancelled"
    settlement = fixture.runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key="simulation:council-intervention-cancelled",
            operator_version="cancelled-intervention-v1",
            requested_budget=0.008,
            consumed_budget=0.003,
            disposition=SimulationDisposition.CANCELLED,
            termination_code="bounded_cancel",
            result_refs=(candidate.candidate_id, basis),
        ),
    ).settlement
    original = fixture.evaluations[0]
    cancelled = EpistemicPreservationObservation.build(
        **{
            **original.model_dump(mode="python", exclude={"evaluation_id"}),
            "simulation_settlement_id": settlement.settlement_id,
            "basis_refs": (basis,),
        }
    )

    _, decision = _decide(
        fixture,
        candidates=fixture.candidates[:2],
        evaluations=(cancelled, fixture.evaluations[1]),
    )

    assessment = next(
        item for item in decision.assessments
        if item.candidate_id == candidate.candidate_id
    )
    assert "simulation_unverified" in assessment.exclusion_codes


def test_unknown_component_and_incomplete_candidate_set_fail_closed() -> None:
    fixture = _fixture()
    unknown = CouncilInterventionCandidate.build(
        diagnostic_result_id=fixture.diagnostic_result_id,
        kind=InterventionKind.REVISE_GENERATOR,
        target_component_refs=("component:invented",),
        proposed_variant_ref="variant:invented",
        basis_refs=(fixture.diagnostic_result_id,),
    )
    with pytest.raises(CouncilInterventionIntegrityError, match="exactly one"):
        _decide(
            fixture,
            candidates=(unknown, fixture.candidates[0]),
            evaluations=(fixture.evaluations[0],),
        )

    unknown_eval = _replace_evaluation(
        fixture.evaluations[1], candidate_id=unknown.candidate_id
    )
    with pytest.raises(CouncilInterventionIntegrityError, match="unknown causal"):
        _decide(
            fixture,
            candidates=(unknown, fixture.candidates[0]),
            evaluations=(unknown_eval, fixture.evaluations[0]),
        )

    mistyped = CouncilInterventionCandidate.build(
        diagnostic_result_id=fixture.diagnostic_result_id,
        kind=InterventionKind.DEMOTE_LENS,
        target_component_refs=(
            fixture.diagnostics.state.obligations[0].trigger.attention_decision_id,
        ),
        proposed_variant_ref="variant:mistyped",
        basis_refs=(fixture.diagnostic_result_id,),
    )
    mistyped_eval = _replace_evaluation(
        fixture.evaluations[1], candidate_id=mistyped.candidate_id
    )
    with pytest.raises(CouncilInterventionIntegrityError, match="kind does not match"):
        _decide(
            fixture,
            candidates=(mistyped, fixture.candidates[0]),
            evaluations=(mistyped_eval, fixture.evaluations[0]),
        )


def test_null_or_inconclusive_diagnostic_cannot_open_tournament() -> None:
    fixture = _fixture()
    original = fixture.diagnostics.state.results[0]
    null_result = DiagnosticResult.build(
        source_event_key="diagnostic:null-result",
        sequence=2,
        diagnostic_id=original.diagnostic_id,
        conclusion=DiagnosticConclusion.VALID_NULL,
        consumed_simulation_budget=0.0,
    )
    diagnostics = DiagnosticEngine(
        state=DiagnosticLedgerState(
            obligations=fixture.diagnostics.state.obligations,
            results=(null_result,),
        )
    )
    with pytest.raises(CouncilInterventionIntegrityError, match="cannot authorize"):
        _decide(
            fixture,
            diagnostic_result_id=null_result.result_id,
            diagnostics=diagnostics,
        )


def test_replay_snapshot_and_tamper_detection_are_deterministic() -> None:
    fixture = _fixture()
    tournament, first = _decide(fixture)
    _, second = _decide(fixture, tournament=tournament)
    restored = CouncilLeastRegretTournament.from_snapshot(tournament.snapshot())

    assert first == second
    assert restored.fingerprint() == tournament.fingerprint()

    payload = tournament.snapshot()
    payload["decisions"][0]["selected_candidate_id"] = fixture.candidates[2].candidate_id
    with pytest.raises(ValidationError):
        CouncilInterventionLedgerState.model_validate(payload)


def test_changed_replay_and_authority_tampering_are_rejected() -> None:
    fixture = _fixture()
    tournament, decision = _decide(fixture)
    original = fixture.evaluations[0].orthogonal_fingerprints[0]
    changed_context = OrthogonalFingerprintObservation(
        context_ref=original.context_ref,
        before_fingerprint=_digest("changed-but-stable"),
        after_fingerprint=_digest("changed-but-stable"),
    )
    changed = _replace_evaluation(
        fixture.evaluations[0], orthogonal_fingerprints=(changed_context,)
    )
    with pytest.raises(CouncilInterventionIntegrityError, match="changed evidence"):
        _decide(
            fixture,
            tournament=tournament,
            evaluations=(changed, *fixture.evaluations[1:]),
        )

    with pytest.raises(ValidationError):
        CouncilTournamentDecision.model_validate(
            {
                **decision.model_dump(mode="json"),
                "intervention_authority_enabled": True,
            }
        )

    values = decision.model_dump(mode="python", exclude={"decision_id"})
    values["selected_candidate_id"] = fixture.candidates[1].candidate_id
    with pytest.raises(ValidationError, match="least-regret ordering"):
        CouncilTournamentDecision.build(**values)
