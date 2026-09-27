from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    ObligationFamily,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    ControlledOperationalTrialObservation,
    ControlledOperationalTrialObserver,
    CounterfactualPatch,
    CounterfactualRuntime,
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    EquivalenceLensSystem,
    HeldOutOperationalReplicationObserver,
    HeldOutOperationalReplicationReceipt,
    LensOpcode,
    OperationalTrialContext,
    OperationalTrialControlIntegrityError,
    OperationalTrialSplit,
    OverlayAccessEffect,
    SimulationLedger,
    StructuralHypothesis,
    build_matched_counterfactual_plans,
    build_operational_trial_context,
    load_experiment_archive_bundle,
    save_experiment_archive,
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


@dataclass(frozen=True)
class TrialFixture:
    kernel: VerdantKernel
    hypothesis: StructuralHypothesis
    allocation_id: str
    lenses: EquivalenceLensSystem


@dataclass(frozen=True)
class ExecutedTrial:
    context: OperationalTrialContext
    baseline_plan: object
    treatment_plan: object
    baseline_result: object
    treatment_result: object
    observation: ControlledOperationalTrialObservation


def _fixture() -> TrialFixture:
    kernel = VerdantKernel(seed=7701, state_dim=16, run_label="trial-controls")
    kernel.apply_experience(
        _experience(
            "trial-control-dependency",
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
            "trial-control-route",
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
            "trial-control-grounding",
            labels=("grounded reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    obligation = DependencyGapDetector().detect_and_record(kernel).mutations[0].obligation
    hypothesis = next(
        item
        for item in DependencyGapHypothesisGenerator().generate(
            kernel, obligation.kernel_id
        )
        if item.patches
    )
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(
            LensOpcode.SELECT_ACTION,
            LensOpcode.SELECT_ACTIVATED_REFS,
            LensOpcode.SELECT_EDGE_ENDPOINTS,
            LensOpcode.SELECT_EDGE_TYPES,
        ),
        provenance_refs=("trial-controls:matched-suite",),
    )
    lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("trial-controls:calibration-a", "trial-controls:held-out-a"),
        source_event_key="lens:trial-controls:v0.27",
        cycle=kernel.state.cycle,
    )
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="controlled_operational_replication",
                requested_budget=0.10,
                estimated_cost=0.04,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.8,
                metric_provenance_refs=hypothesis.provenance_refs,
                generator_version=hypothesis.grammar_version,
            ),
        ),
        source_event_key="attention:trial-controls:v0.27",
    ).decision
    return TrialFixture(
        kernel=kernel,
        hypothesis=hypothesis,
        allocation_id=decision.allocations[0].allocation_id,
        lenses=lenses,
    )


def _context(
    fixture: TrialFixture,
    *,
    split: OperationalTrialSplit,
    seed: int,
    horizon: int = 4,
    slot_budget: int = 2,
) -> OperationalTrialContext:
    return build_operational_trial_context(
        fixture.kernel,
        fixture.lenses,
        hypothesis=fixture.hypothesis,
        split=split,
        seed=seed,
        horizon=horizon,
        slot_budget=slot_budget,
    )


def _execute(
    fixture: TrialFixture,
    runtime: CounterfactualRuntime,
    context: OperationalTrialContext,
) -> ExecutedTrial:
    plans = build_matched_counterfactual_plans(
        fixture.hypothesis,
        source_event_key=(
            f"operational-trial:{context.split.value}:{context.seed}"
        ),
        requested_budget=0.02,
        consumed_budget=0.01,
        additional_result_refs=(context.context_id,),
    )
    baseline = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.baseline,
    )
    treatment = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.treatment,
    )
    observation = ControlledOperationalTrialObserver().observe(
        fixture.kernel,
        runtime.ledger,
        fixture.lenses,
        context=context,
        hypothesis=fixture.hypothesis,
        baseline_plan=plans.baseline,
        baseline_result=baseline,
        treatment_plan=plans.treatment,
        treatment_result=treatment,
    )
    return ExecutedTrial(
        context=context,
        baseline_plan=plans.baseline,
        treatment_plan=plans.treatment,
        baseline_result=baseline,
        treatment_result=treatment,
        observation=observation,
    )


def _replicated_fixture():
    fixture = _fixture()
    runtime = CounterfactualRuntime()
    calibration = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.CALIBRATION,
            seed=11,
        ),
    )
    held_out = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.HELD_OUT,
            seed=29,
        ),
    )
    receipt = HeldOutOperationalReplicationObserver().observe(
        (held_out.observation, calibration.observation)
    )
    return fixture, runtime, calibration, held_out, receipt


def test_predeclared_controls_replicate_without_crossing_authority() -> None:
    fixture = _fixture()
    runtime = CounterfactualRuntime()
    canonical_before = fixture.kernel.fingerprint()
    lens_before = fixture.lenses.fingerprint()
    calibration = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.CALIBRATION,
            seed=11,
        ),
    )
    held_out = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.HELD_OUT,
            seed=29,
        ),
    )

    receipt = HeldOutOperationalReplicationObserver().observe(
        (held_out.observation, calibration.observation)
    )

    assert receipt.seeds == (11, 29)
    assert receipt.calibration_trial_ref == calibration.observation.observation_id
    assert receipt.held_out_trial_refs == (held_out.observation.observation_id,)
    assert receipt.declared_seed_replay_observed
    assert not receipt.stochastic_generalization_established
    assert not receipt.native_workspace_admission_observed
    assert not receipt.outgoing_action_observed
    assert not receipt.canonical_dependency_path_established
    assert not receipt.resolution_authority_enabled
    assert not receipt.canonical_commit_permitted
    assert all(
        trial.operational_observation.effect == OverlayAccessEffect.ACCESS_GAIN
        for trial in receipt.trials
    )
    assert all(
        trial.context.context_id
        in trial.structural_observation.baseline.result_refs
        and trial.context.context_id
        in trial.structural_observation.treatment.result_refs
        for trial in receipt.trials
    )
    assert fixture.kernel.fingerprint() == canonical_before
    assert fixture.lenses.fingerprint() == lens_before
    assert HeldOutOperationalReplicationReceipt.model_validate(
        receipt.model_dump(mode="json")
    ) == receipt


def test_control_context_must_be_committed_before_both_arms() -> None:
    fixture = _fixture()
    context = _context(
        fixture,
        split=OperationalTrialSplit.CALIBRATION,
        seed=11,
    )
    plans = build_matched_counterfactual_plans(
        fixture.hypothesis,
        source_event_key="operational-trial:missing-context",
        requested_budget=0.02,
        consumed_budget=0.01,
    )
    runtime = CounterfactualRuntime()
    baseline = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.baseline,
    )
    treatment = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.treatment,
    )

    with pytest.raises(
        OperationalTrialControlIntegrityError,
        match="not committed before execution",
    ):
        ControlledOperationalTrialObserver().observe(
            fixture.kernel,
            runtime.ledger,
            fixture.lenses,
            context=context,
            hypothesis=fixture.hypothesis,
            baseline_plan=plans.baseline,
            baseline_result=baseline,
            treatment_plan=plans.treatment,
            treatment_result=treatment,
        )


def test_control_and_hypothesis_tampering_fail_closed() -> None:
    fixture = _fixture()
    runtime = CounterfactualRuntime()
    executed = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.CALIBRATION,
            seed=11,
        ),
    )
    forged_context = executed.context.model_copy(update={"seed": 12})
    with pytest.raises(
        OperationalTrialControlIntegrityError,
        match="checksum mismatch",
    ):
        ControlledOperationalTrialObserver().observe(
            fixture.kernel,
            runtime.ledger,
            fixture.lenses,
            context=forged_context,
            hypothesis=fixture.hypothesis,
            baseline_plan=executed.baseline_plan,
            baseline_result=executed.baseline_result,
            treatment_plan=executed.treatment_plan,
            treatment_result=executed.treatment_result,
        )

    patch = fixture.hypothesis.patches[0]
    changed = CounterfactualPatch.upsert(
        patch.collection,
        "counterfactual:unregistered-trial-patch",
        patch.value or {},
    )
    forged_hypothesis = fixture.hypothesis.model_copy(
        update={"patches": (changed,)}
    )
    with pytest.raises(
        OperationalTrialControlIntegrityError,
        match="checksum mismatch",
    ):
        ControlledOperationalTrialObserver().observe(
            fixture.kernel,
            runtime.ledger,
            fixture.lenses,
            context=executed.context,
            hypothesis=forged_hypothesis,
            baseline_plan=executed.baseline_plan,
            baseline_result=executed.baseline_result,
            treatment_plan=executed.treatment_plan,
            treatment_result=executed.treatment_result,
        )


def test_active_lens_change_invalidates_predeclared_context() -> None:
    fixture = _fixture()
    runtime = CounterfactualRuntime()
    context = _context(
        fixture,
        split=OperationalTrialSplit.CALIBRATION,
        seed=11,
    )
    plans = build_matched_counterfactual_plans(
        fixture.hypothesis,
        source_event_key="operational-trial:lens-change",
        requested_budget=0.02,
        consumed_budget=0.01,
        additional_result_refs=(context.context_id,),
    )
    baseline = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.baseline,
    )
    treatment = runtime.execute(
        fixture.kernel,
        allocation_id=fixture.allocation_id,
        plan=plans.treatment,
    )
    replacement = fixture.lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=("trial-controls:replacement",),
    )
    fixture.lenses.approve_binding(
        definition_id=replacement.definition_id,
        obligation_family=ObligationFamily.DEPENDENCY_GAP,
        failure_tripwire_count=3,
        calibration_refs=("trial-controls:replacement-a",),
        source_event_key="lens:trial-controls:replacement",
        cycle=fixture.kernel.state.cycle,
    )

    with pytest.raises(
        OperationalTrialControlIntegrityError,
        match="does not match current state",
    ):
        ControlledOperationalTrialObserver().observe(
            fixture.kernel,
            runtime.ledger,
            fixture.lenses,
            context=context,
            hypothesis=fixture.hypothesis,
            baseline_plan=plans.baseline,
            baseline_result=baseline,
            treatment_plan=plans.treatment,
            treatment_result=treatment,
        )


@pytest.mark.parametrize(
    ("held_out_seed", "held_out_horizon", "held_out_slots", "message"),
    (
        (11, 4, 2, "distinct seeds"),
        (29, 3, 2, "not matched"),
        (29, 4, 3, "not matched"),
    ),
)
def test_replication_rejects_seed_reuse_and_mismatched_controls(
    held_out_seed: int,
    held_out_horizon: int,
    held_out_slots: int,
    message: str,
) -> None:
    fixture = _fixture()
    runtime = CounterfactualRuntime()
    calibration = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.CALIBRATION,
            seed=11,
        ),
    )
    held_out = _execute(
        fixture,
        runtime,
        _context(
            fixture,
            split=OperationalTrialSplit.HELD_OUT,
            seed=held_out_seed,
            horizon=held_out_horizon,
            slot_budget=held_out_slots,
        ),
    )

    with pytest.raises(OperationalTrialControlIntegrityError, match=message):
        HeldOutOperationalReplicationObserver().observe(
            (calibration.observation, held_out.observation)
        )


def test_foreign_ledger_and_authority_forgery_fail_closed() -> None:
    fixture, runtime, calibration, held_out, _ = _replicated_fixture()
    with pytest.raises(OperationalTrialControlIntegrityError):
        ControlledOperationalTrialObserver().observe(
            fixture.kernel,
            SimulationLedger(),
            fixture.lenses,
            context=calibration.context,
            hypothesis=fixture.hypothesis,
            baseline_plan=calibration.baseline_plan,
            baseline_result=calibration.baseline_result,
            treatment_plan=calibration.treatment_plan,
            treatment_result=calibration.treatment_result,
        )

    forged = calibration.observation.model_copy(
        update={"resolution_authority_enabled": True}
    )
    with pytest.raises(
        OperationalTrialControlIntegrityError,
        match="authority boundary",
    ):
        HeldOutOperationalReplicationObserver().observe(
            (forged, held_out.observation)
        )
    assert runtime.ledger.state.settlements


def test_controlled_replication_replays_exactly_after_archive_reload(
    tmp_path: Path,
) -> None:
    fixture, runtime, calibration, held_out, first = _replicated_fixture()
    archive = tmp_path / "controlled-operational-replication.vob"
    save_experiment_archive(
        archive,
        fixture.kernel,
        runtime.ledger,
        lens_system=fixture.lenses,
    )
    bundle = load_experiment_archive_bundle(archive)
    assert bundle.lens_system is not None
    restored_hypothesis = next(
        item
        for item in DependencyGapHypothesisGenerator().generate(
            bundle.kernel, fixture.hypothesis.obligation_id
        )
        if item.hypothesis_id == fixture.hypothesis.hypothesis_id
    )
    restored_fixture = TrialFixture(
        kernel=bundle.kernel,
        hypothesis=restored_hypothesis,
        allocation_id=fixture.allocation_id,
        lenses=bundle.lens_system,
    )
    restored_runtime = CounterfactualRuntime(bundle.simulation_ledger)
    replayed = []
    for original in (calibration, held_out):
        rebuilt_context = _context(
            restored_fixture,
            split=original.context.split,
            seed=original.context.seed,
            horizon=original.context.horizon,
            slot_budget=original.context.slot_budget,
        )
        assert rebuilt_context == original.context
        replayed.append(
            _execute(restored_fixture, restored_runtime, rebuilt_context)
        )
    second = HeldOutOperationalReplicationObserver().observe(
        tuple(item.observation for item in replayed)
    )

    assert second == first
    assert all(item.baseline_result.replayed for item in replayed)
    assert all(item.treatment_result.replayed for item in replayed)
    assert restored_runtime.ledger.fingerprint() == runtime.ledger.fingerprint()
