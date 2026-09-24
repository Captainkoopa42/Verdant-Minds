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
    DependencyGapDetector,
    DiagnosticConclusion,
    DiagnosticEngine,
    DiagnosticIntegrityError,
    DiagnosticLedgerState,
    DiagnosticPolicy,
    DiagnosticProbeFinding,
    DiagnosticProbeKind,
    DiagnosticProbeObservation,
    DiagnosticRecursionError,
    DiagnosticResult,
    DiagnosticTriggerKind,
    EquivalenceLensSystem,
    InquiryFailureEvidence,
    LensOpcode,
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DiagnosticFixture:
    kernel: VerdantKernel
    runtime: CounterfactualRuntime
    lenses: EquivalenceLensSystem
    engine: DiagnosticEngine
    diagnostic_id: str
    allocation_id: str


def _fixture(*, valid_null: bool = False, policy: DiagnosticPolicy | None = None):
    kernel = VerdantKernel(seed=5801, state_dim=16, run_label="diagnostic-obligation")
    kernel.apply_experience(
        ExperienceCommand(
            event_key="diagnostic-dependency",
            source_ref="curriculum:diagnostic",
            modality="text",
            payload_sha256=_digest("diagnostic-dependency"),
            feature_vector=tuple(index / 15.0 for index in range(16)),
            relation_proposals=(
                RelationProposal(
                    source_label="diagnostic action",
                    target_label="missing diagnostic input",
                    relation_type="requires",
                ),
            ),
        )
    )
    obligation = DependencyGapDetector().detect_and_record(kernel).mutations[0].obligation
    hypothesis_ref = "hypothesis:diagnostic-candidate"
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION, LensOpcode.SELECT_ACTIVATED_REFS),
        provenance_refs=("diagnostic:primitive-control",),
    )
    binding = lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("diagnostic:calibration",),
        source_event_key="lens:diagnostic",
        cycle=kernel.state.cycle,
    )
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="diagnostic_test_inquiry",
                requested_budget=0.20,
                estimated_cost=0.10,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.7,
                metric_provenance_refs=(hypothesis_ref,),
                generator_version="diagnostic-test-generator-v1",
            ),
        ),
        source_event_key="attention:diagnostic",
    ).decision
    allocation = decision.allocations[0]
    runtime = CounterfactualRuntime()
    failed = runtime.execute(
        kernel,
        allocation_id=allocation.allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key="simulation:diagnostic:trigger",
            operator_version="inquiry-under-diagnosis-v1",
            requested_budget=0.01,
            consumed_budget=0.005,
            result_refs=(hypothesis_ref,),
        ),
    ).settlement
    trigger = InquiryFailureEvidence.build(
        trigger_kind=DiagnosticTriggerKind.INQUIRY_FAILURE,
        attention_decision_id=decision.decision_id,
        failed_settlement_id=failed.settlement_id,
        obligation_id=obligation.kernel_id,
        lens_binding_id=binding.binding_id,
        lens_definition_id=definition.definition_id,
        hypothesis_ref=hypothesis_ref,
        completed_within_predicted_cost=True,
        graph_traversal_valid=True,
        action_executed=valid_null,
        explanatory_gain_observed=False,
        evidence_refs=tuple(sorted((
            decision.decision_id,
            failed.settlement_id,
            binding.binding_id,
            definition.definition_id,
            hypothesis_ref,
        ))),
    )
    engine = DiagnosticEngine(policy=policy)
    diagnostic = engine.open(
        kernel,
        trigger=trigger,
        simulation_ledger=runtime.ledger,
        lens_system=lenses,
        source_event_key="diagnostic:open",
    )
    return DiagnosticFixture(
        kernel=kernel,
        runtime=runtime,
        lenses=lenses,
        engine=engine,
        diagnostic_id=diagnostic.diagnostic_id,
        allocation_id=allocation.allocation_id,
    )


def _probe(
    fixture: DiagnosticFixture,
    kind: DiagnosticProbeKind,
    finding: DiagnosticProbeFinding,
    suffix: str,
) -> DiagnosticProbeObservation:
    basis_ref = f"diagnostic:basis:{suffix}"
    settlement = fixture.runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=CounterfactualPlan.build(
            source_event_key=f"simulation:diagnostic:probe:{suffix}",
            operator_version=f"diagnostic-{kind.value}-v1",
            requested_budget=0.01,
            consumed_budget=0.005,
            result_refs=(fixture.diagnostic_id, basis_ref),
        ),
    ).settlement
    return DiagnosticProbeObservation.build(
        diagnostic_id=fixture.diagnostic_id,
        kind=kind,
        finding=finding,
        simulation_settlement_id=settlement.settlement_id,
        basis_refs=(basis_ref,),
    )


def _conclude(fixture: DiagnosticFixture, probes=(), key="diagnostic:conclude"):
    return fixture.engine.conclude(
        diagnostic_id=fixture.diagnostic_id,
        probes=probes,
        simulation_ledger=fixture.runtime.ledger,
        source_event_key=key,
    )


def test_valid_null_terminates_without_component_attribution_or_mutation() -> None:
    fixture = _fixture(valid_null=True)
    kernel_before = fixture.kernel.fingerprint()
    simulation_before = fixture.runtime.ledger.fingerprint()
    lens_before = fixture.lenses.fingerprint()

    result = _conclude(fixture)

    assert result.conclusion == DiagnosticConclusion.VALID_NULL
    assert result.attributed_component_refs == ()
    assert result.terminal and not result.may_spawn_diagnostic
    assert not result.epistemic_authority_enabled
    assert fixture.kernel.fingerprint() == kernel_before
    assert fixture.runtime.ledger.fingerprint() == simulation_before
    assert fixture.lenses.fingerprint() == lens_before


@pytest.mark.parametrize(
    ("finding", "expected"),
    (
        (
            DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT,
            DiagnosticConclusion.LENS_OVER_SMOOTHING,
        ),
        (
            DiagnosticProbeFinding.LENS_SPLIT_EQUIVALENT,
            DiagnosticConclusion.LENS_HYPER_DISCRIMINATION,
        ),
    ),
)
def test_primitive_baseline_isolates_lens_defects(finding, expected) -> None:
    fixture = _fixture()
    probe = _probe(fixture, DiagnosticProbeKind.PRIMITIVE_BASELINE, finding, "lens")

    result = _conclude(fixture, (probe,))

    assert result.conclusion == expected
    assert result.attributed_component_refs == (
        fixture.engine.state.obligations[0].trigger.lens_definition_id,
    )


def test_adjacent_context_recovery_attributes_binding_miscalibration() -> None:
    fixture = _fixture()
    probe = _probe(
        fixture,
        DiagnosticProbeKind.ADJACENT_CONTEXT,
        DiagnosticProbeFinding.RECOVERED,
        "binding",
    )
    result = _conclude(fixture, (probe,))
    assert result.conclusion == DiagnosticConclusion.BINDING_MISCALIBRATION
    assert result.attributed_component_refs == (
        fixture.engine.state.obligations[0].trigger.lens_binding_id,
    )


def test_invalid_topology_attributes_generator_fault() -> None:
    fixture = _fixture()
    probe = _probe(
        fixture,
        DiagnosticProbeKind.GENERATOR_COHERENCE,
        DiagnosticProbeFinding.TOPOLOGY_INVALID,
        "generator",
    )
    result = _conclude(fixture, (probe,))
    assert result.conclusion == DiagnosticConclusion.GENERATOR_FAULT
    assert result.attributed_component_refs == (
        fixture.engine.state.obligations[0].trigger.hypothesis_ref,
    )


@pytest.mark.parametrize(
    "finding",
    (DiagnosticProbeFinding.COST_EXCEEDED, DiagnosticProbeFinding.GAIN_IMPOSSIBLE),
)
def test_cost_ablation_attributes_scheduler_misalignment(finding) -> None:
    fixture = _fixture()
    probe = _probe(
        fixture,
        DiagnosticProbeKind.COST_CALIBRATION,
        finding,
        finding.value,
    )
    result = _conclude(fixture, (probe,))
    assert result.conclusion == DiagnosticConclusion.SCHEDULER_MISALIGNMENT
    assert result.attributed_component_refs == (
        fixture.engine.state.obligations[0].trigger.attention_decision_id,
    )


def test_multiple_component_signals_end_as_interaction_suspected() -> None:
    fixture = _fixture()
    probes = (
        _probe(
            fixture,
            DiagnosticProbeKind.PRIMITIVE_BASELINE,
            DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT,
            "interaction-lens",
        ),
        _probe(
            fixture,
            DiagnosticProbeKind.GENERATOR_COHERENCE,
            DiagnosticProbeFinding.TOPOLOGY_INVALID,
            "interaction-generator",
        ),
    )

    result = _conclude(fixture, probes)

    assert result.conclusion == DiagnosticConclusion.INTERACTION_SUSPECTED
    assert len(result.attributed_component_refs) == 2


def test_unisolated_failure_terminates_inconclusive() -> None:
    fixture = _fixture()
    probes = (
        _probe(
            fixture,
            DiagnosticProbeKind.PRIMITIVE_BASELINE,
            DiagnosticProbeFinding.AGREED,
            "agreed",
        ),
        _probe(
            fixture,
            DiagnosticProbeKind.GENERATOR_COHERENCE,
            DiagnosticProbeFinding.TOPOLOGY_VALID,
            "valid",
        ),
    )
    assert _conclude(fixture, probes).conclusion == DiagnosticConclusion.INCONCLUSIVE


def test_terminal_result_cannot_spawn_recursive_diagnostic() -> None:
    fixture = _fixture()
    result = _conclude(fixture)

    with pytest.raises(DiagnosticRecursionError):
        fixture.engine.open_from_diagnostic_result(result)
    with pytest.raises(ValidationError):
        DiagnosticResult.model_validate(
            {**result.model_dump(mode="json"), "may_spawn_diagnostic": True}
        )


def test_probe_kind_mismatch_and_resource_overruns_fail_closed() -> None:
    with pytest.raises(ValidationError):
        DiagnosticProbeObservation.build(
            diagnostic_id="diagnostic:test",
            kind=DiagnosticProbeKind.GENERATOR_COHERENCE,
            finding=DiagnosticProbeFinding.COST_EXCEEDED,
            simulation_settlement_id="settlement:test",
            basis_refs=("basis:test",),
        )

    fixture = _fixture(policy=DiagnosticPolicy(maximum_probes=1))
    probes = (
        _probe(
            fixture,
            DiagnosticProbeKind.PRIMITIVE_BASELINE,
            DiagnosticProbeFinding.AGREED,
            "cap-a",
        ),
        _probe(
            fixture,
            DiagnosticProbeKind.ADJACENT_CONTEXT,
            DiagnosticProbeFinding.NOT_RECOVERED,
            "cap-b",
        ),
    )
    with pytest.raises(DiagnosticIntegrityError, match="probe cap"):
        _conclude(fixture, probes)

    budget_fixture = _fixture(
        policy=DiagnosticPolicy(maximum_simulation_budget=0.004)
    )
    costly = _probe(
        budget_fixture,
        DiagnosticProbeKind.COST_CALIBRATION,
        DiagnosticProbeFinding.COST_EXCEEDED,
        "budget",
    )
    with pytest.raises(DiagnosticIntegrityError, match="budget exceeded"):
        _conclude(budget_fixture, (costly,))


def test_replay_snapshot_and_tamper_checks_are_deterministic() -> None:
    fixture = _fixture()
    probe = _probe(
        fixture,
        DiagnosticProbeKind.PRIMITIVE_BASELINE,
        DiagnosticProbeFinding.AGREED,
        "replay",
    )
    first = _conclude(fixture, (probe,))
    second = _conclude(fixture, (probe,))
    restored = DiagnosticEngine.from_snapshot(fixture.engine.snapshot())

    assert first == second
    assert restored.fingerprint() == fixture.engine.fingerprint()

    payload = fixture.engine.snapshot()
    payload["results"][0]["conclusion"] = DiagnosticConclusion.GENERATOR_FAULT.value
    with pytest.raises(ValidationError):
        DiagnosticLedgerState.model_validate(payload)


def test_open_replay_is_stable_and_changed_request_is_rejected() -> None:
    fixture = _fixture()
    original = fixture.engine.state.obligations[0]

    replay = fixture.engine.open(
        fixture.kernel,
        trigger=original.trigger,
        simulation_ledger=fixture.runtime.ledger,
        lens_system=fixture.lenses,
        source_event_key=original.source_event_key,
    )
    assert replay == original
    assert len(fixture.engine.state.obligations) == 1

    changed_values = original.trigger.model_dump(mode="python", exclude={"evidence_id"})
    changed_values["action_executed"] = not original.trigger.action_executed
    changed = InquiryFailureEvidence.build(**changed_values)
    with pytest.raises(DiagnosticIntegrityError, match="changed request"):
        fixture.engine.open(
            fixture.kernel,
            trigger=changed,
            simulation_ledger=fixture.runtime.ledger,
            lens_system=fixture.lenses,
            source_event_key=original.source_event_key,
        )


def test_trigger_and_probe_require_complete_causal_lineage() -> None:
    fixture = _fixture()
    trigger = fixture.engine.state.obligations[0].trigger
    successful_values = trigger.model_dump(mode="python", exclude={"evidence_id"})
    successful_values.update(
        action_executed=True,
        explanatory_gain_observed=True,
    )
    with pytest.raises(ValidationError, match="successful inquiry"):
        InquiryFailureEvidence.build(**successful_values)

    incomplete_values = trigger.model_dump(mode="python", exclude={"evidence_id"})
    incomplete_values["evidence_refs"] = tuple(
        ref for ref in trigger.evidence_refs if ref != trigger.lens_binding_id
    )
    incomplete = InquiryFailureEvidence.build(**incomplete_values)
    second_engine = DiagnosticEngine()
    with pytest.raises(DiagnosticIntegrityError, match="omits required"):
        second_engine.open(
            fixture.kernel,
            trigger=incomplete,
            simulation_ledger=fixture.runtime.ledger,
            lens_system=fixture.lenses,
            source_event_key="diagnostic:incomplete-trigger",
        )

    valid_probe = _probe(
        fixture,
        DiagnosticProbeKind.PRIMITIVE_BASELINE,
        DiagnosticProbeFinding.AGREED,
        "lineage",
    )
    forged_probe = DiagnosticProbeObservation.build(
        diagnostic_id=fixture.diagnostic_id,
        kind=valid_probe.kind,
        finding=valid_probe.finding,
        simulation_settlement_id=valid_probe.simulation_settlement_id,
        basis_refs=("diagnostic:basis:invented",),
    )
    with pytest.raises(DiagnosticIntegrityError, match="declared simulation lineage"):
        _conclude(fixture, (forged_probe,))
