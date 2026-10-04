from __future__ import annotations

import json
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    ObligationFamily,
    VerdantKernel,
)
from verdant_kernel.models import stable_id
from verdant_obligations import (
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_LENS_MISSING_REQUIREMENTS,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionCalibrationCriterionDeriver,
    ContradictionCalibrationDimensionCriterion,
    ContradictionDimensionCriterionDeclaration,
    ContradictionDimensionCriterionIntegrityError,
    ContradictionDimensionEvaluationDisposition,
    ContradictionDimensionEvaluationReceipt,
    ContradictionDimensionTrialRunner,
    ContradictionHypothesisProtocol,
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlIntegrityError,
    ContradictionLensTrialContext,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSplit,
    ContradictionObligationDetector,
    ContradictionProjectionCardinalityProfile,
    ContradictionResolutionRequirement,
    CounterfactualRuntime,
    EquivalenceLensSystem,
    LensEvidenceResult,
    LensOpcode,
    contradiction_dimension_sidecar_bytes,
    load_contradiction_dimension_sidecar,
    load_experiment_archive_bundle,
    save_contradiction_dimension_sidecar,
    save_experiment_archive,
)


def _claim(
    kernel: VerdantKernel,
    *,
    event_key: str,
    subject_label: str,
    polarity: ClaimPolarity,
    source: ClaimSourceClass,
) -> None:
    ClaimLearningPipeline().record_claim(
        kernel,
        event_key=event_key,
        native_description=f"Dimension-criterion evidence {event_key}.",
        subject_label=subject_label,
        predicate="has_property",
        object_label="open",
        polarity=polarity,
        source_class=source,
    )


def _prepared(
    seed: int,
    label: str,
    *,
    negated_source: ClaimSourceClass = ClaimSourceClass.HUMAN_TESTIMONY,
):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"contradiction-dimension-{label}-{seed}",
    )
    subject = f"door-{label}-{seed}"
    _claim(
        kernel,
        event_key=f"dimension-affirmed-{label}-{seed}",
        subject_label=subject,
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    _claim(
        kernel,
        event_key=f"dimension-negated-{label}-{seed}",
        subject_label=subject,
        polarity=ClaimPolarity.NEGATED,
        source=negated_source,
    )
    obligation = ContradictionObligationDetector().detect_and_record(
        kernel
    ).mutations[0].obligation
    latest = next(
        item
        for item in reversed(kernel.state.obligation_history)
        if item.obligation_id == obligation.kernel_id
    )
    allocation = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator=CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
                requested_budget=0.05,
                estimated_cost=0.05,
                expected_gain=0.55,
                uncertainty=0.85,
                urgency=0.50,
                novelty=0.75,
                metric_provenance_refs=latest.triggering_refs,
                generator_version=CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
            ),
        ),
        source_event_key=f"dimension-attention-{label}-{seed}",
    ).decision.allocations[0]
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    return kernel, obligation, allocation, bundle


def _lenses(kernel: VerdantKernel, bundle) -> EquivalenceLensSystem:
    lenses = EquivalenceLensSystem()
    definition = lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTIVATED_REFS,),
        provenance_refs=(bundle.evidence_receipt.receipt_id,),
    )
    binding = lenses.approve_binding(
        definition_id=definition.definition_id,
        obligation_family=ObligationFamily.CONTRADICTION,
        failure_tripwire_count=2,
        calibration_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"dimension-lens:approve:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
    )
    lenses.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"dimension-lens:evidence:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
        hypothesis_refs=tuple(item.hypothesis_id for item in bundle.hypotheses),
    )
    return lenses


def _pair_fixture(
    seed: int = 6801,
    *,
    held_out_negated_source: ClaimSourceClass = ClaimSourceClass.HUMAN_TESTIMONY,
):
    calibration = _prepared(seed, "calibration")
    held_out = _prepared(
        seed + 1,
        "held-out",
        negated_source=held_out_negated_source,
    )
    lenses = _lenses(calibration[0], calibration[3])
    pair = ContradictionLensTrialPairContext.build(
        calibration=ContradictionLensTrialContext.build(
            calibration[0],
            calibration[3],
            lenses,
            split=ContradictionLensTrialSplit.CALIBRATION,
            source_event_key=f"dimension-calibration:{seed}",
        ),
        held_out=ContradictionLensTrialContext.build(
            held_out[0],
            held_out[3],
            lenses,
            split=ContradictionLensTrialSplit.HELD_OUT,
            source_event_key=f"dimension-held-out:{seed + 1}",
        ),
    )
    declaration = ContradictionDimensionCriterionDeclaration.build(pair)
    return calibration, held_out, lenses, pair, declaration


def _execute(
    seed: int = 6801,
    *,
    held_out_negated_source: ClaimSourceClass = ClaimSourceClass.HUMAN_TESTIMONY,
):
    calibration, held_out, lenses, pair, declaration = _pair_fixture(
        seed,
        held_out_negated_source=held_out_negated_source,
    )
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    result = ContradictionDimensionTrialRunner().run(
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        calibration_bundle=calibration[3],
        held_out_bundle=held_out[3],
        pair_context=pair,
        criterion_declaration=declaration,
    )
    return (
        calibration,
        held_out,
        lenses,
        pair,
        declaration,
        calibration_runtime,
        held_out_runtime,
        result,
    )


def _rehash_declaration(payload: dict) -> dict:
    values = dict(payload)
    values["declaration_id"] = stable_id(
        "contradiction_dimension_criterion_declaration",
        {key: value for key, value in values.items() if key != "declaration_id"},
    )
    return values


def _rehash_criterion(payload: dict) -> dict:
    values = dict(payload)
    values["criterion_id"] = stable_id(
        "contradiction_calibration_dimension_criterion",
        {key: value for key, value in values.items() if key != "criterion_id"},
    )
    return values


def _rehash_evaluation(payload: dict) -> dict:
    values = dict(payload)
    values["receipt_id"] = stable_id(
        "contradiction_dimension_evaluation",
        {key: value for key, value in values.items() if key != "receipt_id"},
    )
    return values


def test_criterion_is_frozen_between_calibration_and_held_out_calls() -> None:
    calibration, held_out, lenses, pair, declaration = _pair_fixture()
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()

    class RecordingDeriver:
        def __init__(self) -> None:
            self.criterion = None
            self.delegate = ContradictionCalibrationCriterionDeriver()

        def derive(self, declared, observation):
            self.criterion = self.delegate.derive(declared, observation)
            return self.criterion

    deriver = RecordingDeriver()

    class SequencingRunner:
        def __init__(self) -> None:
            self.calls = 0
            self.delegate = ContradictionLensControlledProbeRunner()

        def run(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                assert deriver.criterion is not None
            return self.delegate.run(*args, **kwargs)

    result = ContradictionDimensionTrialRunner(
        controlled_runner=SequencingRunner(),
        criterion_deriver=deriver,
    ).run(
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        calibration_bundle=calibration[3],
        held_out_bundle=held_out[3],
        pair_context=pair,
        criterion_declaration=declaration,
    )

    assert result.criterion == deriver.criterion
    assert result.criterion.calibration_only_derivation
    assert not result.criterion.held_out_trace_consulted
    assert result.criterion.frozen_before_held_out_execution
    assert result.criterion.calibration_cardinalities == (1, 1)
    assert result.criterion.calibration_profile == (
        ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    )
    assert result.evaluation.held_out_cardinalities == (1, 1)
    assert result.evaluation.disposition == (
        ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH
    )
    assert result.evaluation.trace_local_dimension_outcome_match_observed
    assert not result.evaluation.explicit_valid_null_observed
    assert not result.evaluation.dimensional_separation_observed
    assert not result.evaluation.predictive_discrimination_observed
    assert not result.evaluation.resolution_trial_ready
    assert result.evaluation.missing_requirements == (
        CONTRADICTION_LENS_MISSING_REQUIREMENTS
    )
    assert {
        ContradictionResolutionRequirement.DIMENSIONAL_SEPARATION,
        ContradictionResolutionRequirement.PREDICTIVE_DISCRIMINATION,
        ContradictionResolutionRequirement.INDEPENDENT_HELD_OUT_REPLICATION,
        ContradictionResolutionRequirement.SOURCE_INDEPENDENCE,
    }.issubset(result.evaluation.missing_requirements)
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert len(held_out_runtime.ledger.state.settlements) == 2
    assert calibration[0].fingerprint() == (
        pair.calibration.canonical_checkpoint_fingerprint
    )
    assert held_out[0].fingerprint() == pair.held_out.canonical_checkpoint_fingerprint


def test_out_of_calibration_profile_is_an_explicit_valid_null() -> None:
    *_, result = _execute(
        6810,
        held_out_negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
    )

    assert result.criterion.calibration_profile == (
        ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    )
    assert result.evaluation.held_out_cardinalities == (2, 2)
    assert result.evaluation.held_out_profile == (
        ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES
    )
    valid_null = (
        ContradictionDimensionEvaluationDisposition.
        VALID_NULL_OUT_OF_CALIBRATION_PROFILE
    )
    assert result.evaluation.disposition == valid_null
    assert result.evaluation.explicit_valid_null_observed
    assert not result.evaluation.trace_local_dimension_outcome_match_observed
    assert not result.evaluation.trace_local_outcome_mismatch_observed
    assert not result.evaluation.predictive_discrimination_observed
    assert not result.evaluation.resolution_trial_ready


def test_calibration_only_deriver_rejects_held_out_observation() -> None:
    *_, result = _execute(6820)

    with pytest.raises(
        ContradictionDimensionCriterionIntegrityError,
        match="declared calibration",
    ):
        ContradictionCalibrationCriterionDeriver().derive(
            result.declaration,
            result.evaluation.held_out_observation,
        )


def test_fully_rehashed_grammar_evidence_and_authority_tamper_fail() -> None:
    *_, result = _execute(6830)

    declaration_payload = result.declaration.model_dump(mode="json")
    declaration_payload["admissible_profiles"] = list(
        reversed(declaration_payload["admissible_profiles"])
    )
    with pytest.raises(ValueError, match="changed its grammar"):
        ContradictionDimensionCriterionDeclaration.model_validate(
            _rehash_declaration(declaration_payload)
        )

    criterion_payload = result.criterion.model_dump(mode="json")
    criterion_payload["expected_functional_outcome"] = (
        "valid_null_shared_routing"
    )
    with pytest.raises(ValueError, match="altered trace evidence"):
        ContradictionCalibrationDimensionCriterion.model_validate(
            _rehash_criterion(criterion_payload)
        )

    evaluation_payload = result.evaluation.model_dump(mode="json")
    evaluation_payload["predictive_discrimination_observed"] = True
    with pytest.raises(ValueError, match="claim boundary"):
        ContradictionDimensionEvaluationReceipt.model_validate(
            _rehash_evaluation(evaluation_payload)
        )


def test_second_context_failure_rolls_back_both_ledgers_after_freeze() -> None:
    calibration, held_out, lenses, pair, declaration = _pair_fixture(6840)
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    simulation_before = (
        calibration_runtime.ledger.fingerprint(),
        held_out_runtime.ledger.fingerprint(),
    )
    canonical_before = (
        calibration[0].fingerprint(),
        held_out[0].fingerprint(),
    )
    lens_before = lenses.fingerprint()

    class FailSecondRun:
        def __init__(self) -> None:
            self.calls = 0
            self.delegate = ContradictionLensControlledProbeRunner()

        def run(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise ContradictionLensControlIntegrityError(
                    "injected post-criterion held-out failure"
                )
            return self.delegate.run(*args, **kwargs)

    with pytest.raises(
        ContradictionDimensionCriterionIntegrityError,
        match="injected post-criterion held-out failure",
    ):
        ContradictionDimensionTrialRunner(
            controlled_runner=FailSecondRun()
        ).run(
            calibration[0],
            calibration_runtime,
            held_out[0],
            held_out_runtime,
            lenses,
            calibration_bundle=calibration[3],
            held_out_bundle=held_out[3],
            pair_context=pair,
            criterion_declaration=declaration,
        )
    assert calibration_runtime.ledger.fingerprint() == simulation_before[0]
    assert held_out_runtime.ledger.fingerprint() == simulation_before[1]
    assert calibration[0].fingerprint() == canonical_before[0]
    assert held_out[0].fingerprint() == canonical_before[1]
    assert lenses.fingerprint() == lens_before


def test_completed_dimension_sidecar_is_deterministic_and_closes_ledgers(
    tmp_path: Path,
) -> None:
    (
        calibration,
        held_out,
        lenses,
        _,
        _,
        calibration_runtime,
        held_out_runtime,
        result,
    ) = _execute(6850)
    path = tmp_path / "dimension-criterion.vdc"
    save_contradiction_dimension_sidecar(
        path,
        result,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )
    loaded = load_contradiction_dimension_sidecar(
        path,
        calibration_kernel=calibration[0],
        held_out_kernel=held_out[0],
        lenses=lenses,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )
    assert loaded.criterion == result.criterion
    assert loaded.evaluation == result.evaluation
    assert path.read_bytes() == contradiction_dimension_sidecar_bytes(
        result,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )

    with pytest.raises(
        ContradictionDimensionCriterionIntegrityError,
        match="different simulation state",
    ):
        load_contradiction_dimension_sidecar(
            path,
            calibration_kernel=calibration[0],
            held_out_kernel=held_out[0],
            lenses=lenses,
            calibration_ledger=held_out_runtime.ledger,
            held_out_ledger=calibration_runtime.ledger,
        )

    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["evaluation"]["disposition"] = "trace_local_outcome_mismatch"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(
        ContradictionDimensionCriterionIntegrityError,
        match="Held-out dimension evaluation was altered|checksum mismatch",
    ):
        load_contradiction_dimension_sidecar(
            path,
            calibration_kernel=calibration[0],
            held_out_kernel=held_out[0],
            lenses=lenses,
            calibration_ledger=calibration_runtime.ledger,
            held_out_ledger=held_out_runtime.ledger,
        )


def test_dual_archive_replay_reconstructs_criterion_without_new_cost(
    tmp_path: Path,
) -> None:
    (
        calibration,
        held_out,
        lenses,
        _,
        _,
        calibration_runtime,
        held_out_runtime,
        first,
    ) = _execute(6860)
    calibration_archive = tmp_path / "calibration.vob"
    held_out_archive = tmp_path / "held-out.vob"
    sidecar = tmp_path / "dimension.vdc"
    save_experiment_archive(
        calibration_archive,
        calibration[0],
        calibration_runtime.ledger,
        lens_system=lenses,
    )
    save_experiment_archive(
        held_out_archive,
        held_out[0],
        held_out_runtime.ledger,
        lens_system=lenses,
    )
    save_contradiction_dimension_sidecar(
        sidecar,
        first,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )

    restored_calibration = load_experiment_archive_bundle(calibration_archive)
    restored_held_out = load_experiment_archive_bundle(held_out_archive)
    assert restored_calibration.lens_system is not None
    loaded = load_contradiction_dimension_sidecar(
        sidecar,
        calibration_kernel=restored_calibration.kernel,
        held_out_kernel=restored_held_out.kernel,
        lenses=restored_calibration.lens_system,
        calibration_ledger=restored_calibration.simulation_ledger,
        held_out_ledger=restored_held_out.simulation_ledger,
    )
    calibration_bundle = ContradictionHypothesisProtocol().generate(
        restored_calibration.kernel,
        obligation_id=calibration[3].obligation_id,
        attention_allocation_id=calibration[2].allocation_id,
    )
    held_out_bundle = ContradictionHypothesisProtocol().generate(
        restored_held_out.kernel,
        obligation_id=held_out[3].obligation_id,
        attention_allocation_id=held_out[2].allocation_id,
    )
    simulation_before = (
        restored_calibration.simulation_ledger.fingerprint(),
        restored_held_out.simulation_ledger.fingerprint(),
    )
    replay = ContradictionDimensionTrialRunner().run(
        restored_calibration.kernel,
        CounterfactualRuntime(restored_calibration.simulation_ledger),
        restored_held_out.kernel,
        CounterfactualRuntime(restored_held_out.simulation_ledger),
        restored_calibration.lens_system,
        calibration_bundle=calibration_bundle,
        held_out_bundle=held_out_bundle,
        pair_context=loaded.pair_context,
        criterion_declaration=loaded.declaration,
    )

    assert replay.replayed
    assert replay.criterion == first.criterion
    assert replay.evaluation == first.evaluation
    assert restored_calibration.simulation_ledger.fingerprint() == simulation_before[0]
    assert restored_held_out.simulation_ledger.fingerprint() == simulation_before[1]
