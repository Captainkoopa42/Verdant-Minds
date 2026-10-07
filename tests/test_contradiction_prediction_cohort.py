from __future__ import annotations

import inspect
import json
from dataclasses import replace
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
    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionDimensionCriterionDeclaration,
    ContradictionDurablePredictionCohortRunner,
    ContradictionHypothesisProtocol,
    ContradictionLensTrialContext,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSplit,
    ContradictionObligationDetector,
    ContradictionPredictionAuditDisposition,
    ContradictionPredictionCohortContextInput,
    ContradictionPredictionCohortDeclaration,
    ContradictionPredictionCohortFoldRule,
    ContradictionPredictionCohortIntegrityError,
    ContradictionPredictionCohortReceipt,
    ContradictionPredictionCohortResultEnvelope,
    ContradictionProjectionCardinalityProfile,
    CounterfactualRuntime,
    EquivalenceLensSystem,
    LensEvidenceResult,
    LensOpcode,
    contradiction_prediction_cohort_result_bytes,
    read_contradiction_prediction_cohort_result,
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
        native_description=f"Cohort evidence {event_key}.",
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
        run_label=f"contradiction-cohort-{label}-{seed}",
    )
    subject = f"door-{label}-{seed}"
    _claim(
        kernel,
        event_key=f"cohort-affirmed-{label}-{seed}",
        subject_label=subject,
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    _claim(
        kernel,
        event_key=f"cohort-negated-{label}-{seed}",
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
        source_event_key=f"cohort-attention-{label}-{seed}",
    ).decision.allocations[0]
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    return kernel, bundle


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
        source_event_key=f"cohort-lens:approve:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
    )
    lenses.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"cohort-lens:evidence:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
        hypothesis_refs=tuple(item.hypothesis_id for item in bundle.hypotheses),
    )
    return lenses


def _pair(
    seed: int,
    label: str,
    *,
    held_out_negated_source: ClaimSourceClass,
):
    calibration_kernel, calibration_bundle = _prepared(
        seed, f"{label}-calibration"
    )
    held_out_kernel, held_out_bundle = _prepared(
        seed + 1,
        f"{label}-held-out",
        negated_source=held_out_negated_source,
    )
    lenses = _lenses(calibration_kernel, calibration_bundle)
    pair = ContradictionLensTrialPairContext.build(
        calibration=ContradictionLensTrialContext.build(
            calibration_kernel,
            calibration_bundle,
            lenses,
            split=ContradictionLensTrialSplit.CALIBRATION,
            source_event_key=f"cohort-calibration:{label}:{seed}",
        ),
        held_out=ContradictionLensTrialContext.build(
            held_out_kernel,
            held_out_bundle,
            lenses,
            split=ContradictionLensTrialSplit.HELD_OUT,
            source_event_key=f"cohort-held-out:{label}:{seed + 1}",
        ),
    )
    return calibration_kernel, held_out_kernel, lenses, pair


def _input(
    root: Path,
    name: str,
    prepared,
    *,
    calibration_runtime: CounterfactualRuntime | None = None,
    held_out_runtime: CounterfactualRuntime | None = None,
) -> ContradictionPredictionCohortContextInput:
    calibration_kernel, held_out_kernel, lenses, pair = prepared
    return ContradictionPredictionCohortContextInput(
        positive_preregistration_path=root / f"{name}-positive.vop",
        control_preregistration_path=root / f"{name}-control.vop",
        stage_path=root / f"{name}.vcs",
        rule_path=root / f"{name}.vpr",
        audit_path=root / f"{name}.vpa",
        calibration_kernel=calibration_kernel,
        calibration_runtime=calibration_runtime or CounterfactualRuntime(),
        held_out_kernel=held_out_kernel,
        held_out_runtime=held_out_runtime or CounterfactualRuntime(),
        lenses=lenses,
        pair_context=pair,
        criterion_declaration=ContradictionDimensionCriterionDeclaration.build(pair),
    )


@pytest.fixture(scope="module")
def completed_cohort(tmp_path_factory):
    root = tmp_path_factory.mktemp("contradiction-cohort")
    singleton = _pair(
        7601,
        "singleton",
        held_out_negated_source=ClaimSourceClass.HUMAN_TESTIMONY,
    )
    multi = _pair(
        7701,
        "multi",
        held_out_negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    inputs = (
        _input(root, "singleton", singleton),
        _input(root, "multi", multi),
    )
    run = ContradictionDurablePredictionCohortRunner().run(
        root / "cohort.vcp",
        root / "cohort.vcr",
        inputs,
    )
    return root, inputs, run


def _rehash_receipt(payload: dict) -> dict:
    values = dict(payload)
    values["receipt_id"] = stable_id(
        "contradiction_prediction_cohort_receipt",
        {key: value for key, value in values.items() if key != "receipt_id"},
    )
    return values


def _rehash_rule(payload: dict) -> dict:
    values = dict(payload)
    values["rule_id"] = stable_id(
        "contradiction_prediction_cohort_fold_rule",
        {key: value for key, value in values.items() if key != "rule_id"},
    )
    return values


def test_two_actual_profiles_and_leave_one_context_out_falsification(
    completed_cohort,
) -> None:
    _, inputs, run = completed_cohort
    receipt = run.receipt
    assert run.preregistration_path.exists() and run.result_path.exists()
    assert not run.replayed
    assert set(receipt.actual_profiles) == set(
        CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
    )
    assert receipt.two_actual_profiles_verified
    assert receipt.evidence_partitions_disjoint
    assert receipt.untouched_controls_verified
    assert receipt.all_positive_outcomes_admission_gain
    assert receipt.all_controls_valid_null
    assert receipt.same_input_outcome_collision_observed
    assert receipt.preserved_v042_false_positive
    assert receipt.all_v042_audits_falsified
    assert receipt.bounded_rule_family_falsified
    assert all(
        not item.positive_match
        and item.control_match
        and not item.joint_discrimination_observed
        for item in receipt.fold_evaluations
    )
    assert all(
        not rule.control_consulted and not rule.evaluation_consulted
        for rule in receipt.fold_rules
    )
    assert not receipt.predictive_discrimination_observed
    assert not receipt.dimensional_separation_observed
    assert not receipt.resolution_trial_ready
    assert not receipt.canonical_commit_permitted
    assert all(
        item.calibration_runtime.ledger.state.settlements
        and item.held_out_runtime.ledger.state.settlements
        for item in inputs
    )
    singleton = next(
        audit
        for audit in run.result.source_audits
        if audit.receipt.positive_evaluation.held_out_profile
        == ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    )
    assert singleton.receipt.disposition == (
        ContradictionPredictionAuditDisposition.CARDINALITY_ONLY_FALSE_POSITIVE
    )
    assert singleton.receipt.valid_null_false_positive_observed


def test_rule_derivation_api_excludes_control_and_evaluation_inputs(
    completed_cohort,
) -> None:
    _, _, run = completed_cohort
    assert tuple(
        inspect.signature(ContradictionPredictionCohortFoldRule.build).parameters
    ) == ("declaration", "fold", "training_evaluation")
    payload = run.receipt.fold_rules[0].model_dump(mode="json")
    payload["control_consulted"] = True
    with pytest.raises(ValueError, match="claim boundary"):
        ContradictionPredictionCohortFoldRule.model_validate(_rehash_rule(payload))


def test_fully_rehashed_authority_tamper_fails(completed_cohort) -> None:
    _, _, run = completed_cohort
    payload = run.receipt.model_dump(mode="json")
    payload["predictive_discrimination_observed"] = True
    with pytest.raises(ValueError, match="claim boundary"):
        ContradictionPredictionCohortReceipt.model_validate(
            _rehash_receipt(payload)
        )


def test_completed_sidecar_tamper_is_rejected(
    completed_cohort,
    tmp_path: Path,
) -> None:
    _, _, run = completed_cohort
    path = tmp_path / "tampered.vcr"
    path.write_bytes(run.result_path.read_bytes())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_audit_sha256s"][0] = "0" * 64
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        ContradictionPredictionCohortIntegrityError,
        match="Invalid prediction-cohort result",
    ):
        read_contradiction_prediction_cohort_result(path)


def test_duplicate_context_is_rejected(completed_cohort) -> None:
    _, inputs, _ = completed_cohort
    item = inputs[0]
    with pytest.raises(ValueError, match="disjoint"):
        ContradictionPredictionCohortDeclaration.build(
            (
                (item.pair_context, item.held_out_kernel),
                (item.pair_context, item.held_out_kernel),
            )
        )


def test_completed_cohort_replays_without_new_simulation_cost(
    completed_cohort,
) -> None:
    _, inputs, first = completed_cohort
    replay_inputs = tuple(
        replace(
            item,
            calibration_runtime=CounterfactualRuntime(),
            held_out_runtime=CounterfactualRuntime(),
        )
        for item in inputs
    )
    before = first.result_path.read_bytes()
    replay = ContradictionDurablePredictionCohortRunner().run(
        first.preregistration_path,
        first.result_path,
        replay_inputs,
    )
    assert replay.replayed and replay.result == first.result
    assert first.result_path.read_bytes() == before
    assert all(run.replayed for run in replay.context_runs)
    assert all(
        replay_item.calibration_runtime.ledger.fingerprint()
        == original.calibration_runtime.ledger.fingerprint()
        and replay_item.held_out_runtime.ledger.fingerprint()
        == original.held_out_runtime.ledger.fingerprint()
        for replay_item, original in zip(replay_inputs, inputs, strict=True)
    )


def test_completed_result_cannot_backfill_missing_context_artifacts(
    completed_cohort,
    tmp_path: Path,
) -> None:
    _, original_inputs, completed = completed_cohort
    preregistration = tmp_path / "cohort.vcp"
    result = tmp_path / "cohort.vcr"
    preregistration.write_bytes(completed.preregistration_path.read_bytes())
    result.write_bytes(completed.result_path.read_bytes())
    inputs = tuple(
        replace(
            item,
            positive_preregistration_path=tmp_path / f"{index}-positive.vop",
            control_preregistration_path=tmp_path / f"{index}-control.vop",
            stage_path=tmp_path / f"{index}.vcs",
            rule_path=tmp_path / f"{index}.vpr",
            audit_path=tmp_path / f"{index}.vpa",
            calibration_runtime=CounterfactualRuntime(),
            held_out_runtime=CounterfactualRuntime(),
        )
        for index, item in enumerate(original_inputs)
    )
    with pytest.raises(
        ContradictionPredictionCohortIntegrityError,
        match="predates a required context artifact",
    ):
        ContradictionDurablePredictionCohortRunner().run(
            preregistration, result, inputs
        )


def test_preregistration_precedes_child_execution_and_failure_rolls_back(
    completed_cohort,
    tmp_path: Path,
) -> None:
    _, original_inputs, completed = completed_cohort
    inputs = tuple(
        replace(
            item,
            positive_preregistration_path=tmp_path / f"{index}-positive.vop",
            control_preregistration_path=tmp_path / f"{index}-control.vop",
            stage_path=tmp_path / f"{index}.vcs",
            rule_path=tmp_path / f"{index}.vpr",
            audit_path=tmp_path / f"{index}.vpa",
            calibration_runtime=CounterfactualRuntime(),
            held_out_runtime=CounterfactualRuntime(),
        )
        for index, item in enumerate(original_inputs)
    )
    preregistration = tmp_path / "cohort.vcp"
    result = tmp_path / "cohort.vcr"

    class FailSecondContext:
        def __init__(self) -> None:
            self.calls = 0

        def run(
            self,
            _positive,
            _control,
            _stage,
            _rule,
            _audit,
            _calibration_kernel,
            calibration_runtime,
            _held_out_kernel,
            held_out_runtime,
            _lenses,
            *,
            pair_context,
            criterion_declaration,
        ):
            del criterion_declaration
            assert preregistration.exists()
            self.calls += 1
            if self.calls == 2:
                raise ContradictionPredictionCohortIntegrityError(
                    "injected second-context failure"
                )
            source = next(
                run
                for run in completed.context_runs
                if run.stage.stage_receipt.pair_context == pair_context
            )
            calibration_runtime.ledger.state = source.calibration_ledger.snapshot()
            held_out_runtime.ledger.state = source.held_out_ledger.snapshot()
            return source

    with pytest.raises(
        ContradictionPredictionCohortIntegrityError,
        match="injected second-context failure",
    ):
        ContradictionDurablePredictionCohortRunner(
            prediction_runner=FailSecondContext()
        ).run(preregistration, result, inputs)
    assert preregistration.exists() and not result.exists()
    assert all(
        item.calibration_runtime.ledger.fingerprint()
        == CounterfactualRuntime().ledger.fingerprint()
        and item.held_out_runtime.ledger.fingerprint()
        == CounterfactualRuntime().ledger.fingerprint()
        for item in inputs
    )


def test_result_bytes_are_canonical_and_deterministic(completed_cohort) -> None:
    _, _, run = completed_cohort
    assert run.result_path.read_bytes() == (
        contradiction_prediction_cohort_result_bytes(run.result)
    )
    rebuilt = ContradictionPredictionCohortResultEnvelope.build(
        run.preregistration.declaration,
        run.result.source_audits,
    )
    assert rebuilt == run.result
