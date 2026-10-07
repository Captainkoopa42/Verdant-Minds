from __future__ import annotations

import hashlib
import json
import os
import signal
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    ObligationFamily,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    CONTRADICTION_CALIBRATION_STAGE_VERSION,
    CONTRADICTION_DOWNSTREAM_TRACE_FIELD,
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_LENS_MISSING_REQUIREMENTS,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionCalibrationCriterionDeriver,
    ContradictionCalibrationDimensionCriterion,
    ContradictionCalibrationStageIntegrityError,
    ContradictionDownstreamOutcomeDisposition,
    ContradictionDownstreamOutcomeIntegrityError,
    ContradictionDownstreamOutcomeObserver,
    ContradictionDownstreamOutcomePolicy,
    ContradictionDurableDimensionTrialRunner,
    ContradictionDurableDownstreamOutcomeRunner,
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
    load_contradiction_calibration_stage_sidecar,
    read_contradiction_downstream_result,
    load_contradiction_dimension_sidecar,
    load_experiment_archive_bundle,
    save_contradiction_dimension_sidecar,
    save_experiment_archive,
    read_contradiction_calibration_stage_sidecar,
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


requires_posix_stage = pytest.mark.skipif(
    os.name != "posix",
    reason="calibration-stage writer arbitration requires POSIX flock",
)
requires_posix_stage_fork = pytest.mark.skipif(
    os.name != "posix" or not hasattr(os, "fork"),
    reason="controlled calibration-stage process tests require POSIX fork",
)


def _prepared_stage(path: Path, seed: int = 6900):
    calibration, held_out, lenses, pair, declaration = _pair_fixture(seed)
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    runner = ContradictionDurableDimensionTrialRunner()
    stage = runner.prepare_and_persist(
        path,
        calibration[0],
        calibration_runtime,
        held_out[0],
        lenses,
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
        runner,
        stage,
    )


@requires_posix_stage
def test_calibration_stage_is_durable_before_held_out_and_resumes_exactly(
    tmp_path: Path,
) -> None:
    path = tmp_path / "calibration-stage.vcs"
    (
        calibration,
        held_out,
        lenses,
        pair,
        _,
        calibration_runtime,
        held_out_runtime,
        runner,
        stage,
    ) = _prepared_stage(path)

    receipt = stage.envelope.stage_receipt
    assert receipt.stage_version == CONTRADICTION_CALIBRATION_STAGE_VERSION
    assert receipt.pair_context == pair
    assert receipt.calibration_only
    assert receipt.matched_controls_unchanged
    assert receipt.complete_calibration_ledger_embedded
    assert not receipt.held_out_execution_started
    assert not receipt.held_out_trace_consulted
    assert not receipt.predictive_discrimination_observed
    assert not receipt.resolution_trial_ready
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert held_out_runtime.ledger.state.settlements == ()
    assert "held_out_observation" not in type(receipt).model_fields
    assert read_contradiction_calibration_stage_sidecar(path) == stage.envelope

    before_resume = path.read_bytes()
    result = runner.resume_from_stage(
        path,
        calibration[0],
        held_out[0],
        held_out_runtime,
        lenses,
    )

    assert path.read_bytes() == before_resume
    assert result.criterion == receipt.criterion
    assert result.replication_receipt.pair_context == pair
    assert result.evaluation.criterion == receipt.criterion
    assert result.evaluation.disposition == (
        ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH
    )
    assert not result.evaluation.predictive_discrimination_observed
    assert not result.evaluation.resolution_trial_ready
    assert result.calibration_ledger.fingerprint() == (
        receipt.calibration_simulation_fingerprint
    )
    assert len(held_out_runtime.ledger.state.settlements) == 2
    assert calibration[0].fingerprint() == (
        pair.calibration.canonical_checkpoint_fingerprint
    )
    assert held_out[0].fingerprint() == (
        pair.held_out.canonical_checkpoint_fingerprint
    )


def _paused_stage_writer(
    path: Path,
    fixture,
    phase: str,
    ready_file_descriptor: int,
) -> None:
    import verdant_obligations.contradiction_calibration_stage as stage_module

    calibration, held_out, lenses, pair, declaration = fixture
    real_replace = stage_module.os.replace

    def pause_replace(source, destination):
        if phase == "before_replace":
            os.write(ready_file_descriptor, b"B")
            while True:
                signal.pause()
        real_replace(source, destination)
        if phase == "after_replace":
            os.write(ready_file_descriptor, b"A")
            while True:
                signal.pause()

    stage_module.os.replace = pause_replace
    try:
        ContradictionDurableDimensionTrialRunner().prepare_and_persist(
            path,
            calibration[0],
            CounterfactualRuntime(),
            held_out[0],
            lenses,
            pair_context=pair,
            criterion_declaration=declaration,
        )
    finally:
        os._exit(3)


def _kill_stage_writer(path: Path, fixture, phase: str) -> None:
    ready_read, ready_write = os.pipe()
    process_id = os.fork()
    if process_id == 0:
        os.close(ready_read)
        _paused_stage_writer(path, fixture, phase, ready_write)
    os.close(ready_write)
    try:
        marker = os.read(ready_read, 1)
        assert marker == (b"B" if phase == "before_replace" else b"A")
        os.kill(process_id, signal.SIGKILL)
        _, status = os.waitpid(process_id, 0)
        assert os.WIFSIGNALED(status)
        assert os.WTERMSIG(status) == signal.SIGKILL
    finally:
        os.close(ready_read)
        try:
            os.kill(process_id, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(process_id, 0)
        except ChildProcessError:
            pass


@requires_posix_stage_fork
def test_process_death_handoff_and_stale_temporary_recovery(
    tmp_path: Path,
) -> None:
    before_path = tmp_path / "before-replace.vcs"
    before_fixture = _pair_fixture(6910)
    _kill_stage_writer(before_path, before_fixture, "before_replace")
    assert not before_path.exists()
    assert len(list(tmp_path.glob(".before-replace.vcs.*.tmp"))) == 1

    before_runtime = CounterfactualRuntime()
    ContradictionDurableDimensionTrialRunner().prepare_and_persist(
        before_path,
        before_fixture[0][0],
        before_runtime,
        before_fixture[1][0],
        before_fixture[2],
        pair_context=before_fixture[3],
        criterion_declaration=before_fixture[4],
    )
    assert before_path.exists()
    assert list(tmp_path.glob(".before-replace.vcs.*.tmp")) == []
    assert len(before_runtime.ledger.state.settlements) == 2

    after_path = tmp_path / "after-replace.vcs"
    after_fixture = _pair_fixture(6920)
    _kill_stage_writer(after_path, after_fixture, "after_replace")
    assert after_path.exists()
    assert list(tmp_path.glob(".after-replace.vcs.*.tmp")) == []
    loaded = load_contradiction_calibration_stage_sidecar(
        after_path,
        calibration_kernel=after_fixture[0][0],
        held_out_kernel=after_fixture[1][0],
        lenses=after_fixture[2],
    )
    held_out_runtime = CounterfactualRuntime()
    resumed = ContradictionDurableDimensionTrialRunner().resume_from_stage(
        after_path,
        after_fixture[0][0],
        after_fixture[1][0],
        held_out_runtime,
        after_fixture[2],
    )
    assert resumed.criterion == loaded.stage_receipt.criterion
    assert len(resumed.calibration_ledger.state.settlements) == 2
    assert len(held_out_runtime.ledger.state.settlements) == 2


def _gated_stage_writer(
    path: Path,
    fixture,
    ready_file_descriptor: int,
    go_file_descriptor: int,
    result_file_descriptor: int,
) -> None:
    calibration, held_out, lenses, pair, declaration = fixture
    os.write(ready_file_descriptor, b"R")
    if os.read(go_file_descriptor, 1) != b"G":
        os._exit(4)
    try:
        stage = ContradictionDurableDimensionTrialRunner().prepare_and_persist(
            path,
            calibration[0],
            CounterfactualRuntime(),
            held_out[0],
            lenses,
            pair_context=pair,
            criterion_declaration=declaration,
        )
        result = f"S:{stage.envelope.stage_receipt.pair_context_ref}".encode()
    except ContradictionCalibrationStageIntegrityError:
        result = b"C"
    except Exception as exc:  # pragma: no cover - diagnostic child payload.
        result = f"E:{type(exc).__name__}:{exc}".encode()
    os.write(result_file_descriptor, result)
    os._exit(0)


@requires_posix_stage_fork
def test_concurrent_foreign_writers_are_first_committer_wins(
    tmp_path: Path,
) -> None:
    path = tmp_path / "arbitrated-stage.vcs"
    fixtures = (_pair_fixture(6930), _pair_fixture(6940))
    children = []
    for fixture in fixtures:
        ready_read, ready_write = os.pipe()
        go_read, go_write = os.pipe()
        result_read, result_write = os.pipe()
        process_id = os.fork()
        if process_id == 0:
            os.close(ready_read)
            os.close(go_write)
            os.close(result_read)
            _gated_stage_writer(
                path,
                fixture,
                ready_write,
                go_read,
                result_write,
            )
        os.close(ready_write)
        os.close(go_read)
        os.close(result_write)
        children.append(
            (process_id, ready_read, go_write, result_read)
        )

    try:
        for _, ready_read, _, _ in children:
            assert os.read(ready_read, 1) == b"R"
        for _, _, go_write, _ in children:
            os.write(go_write, b"G")
        statuses = []
        for process_id, _, _, _ in children:
            _, status = os.waitpid(process_id, 0)
            statuses.append(status)
        assert all(
            os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
            for status in statuses
        )
        results = [
            os.read(result_read, 4096).decode()
            for _, _, _, result_read in children
        ]
    finally:
        for process_id, ready_read, go_write, result_read in children:
            for descriptor in (ready_read, go_write, result_read):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            try:
                os.kill(process_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(process_id, 0)
            except ChildProcessError:
                pass

    successes = [item for item in results if item.startswith("S:")]
    assert len(successes) == 1
    assert results.count("C") == 1
    winning_pair_ref = successes[0].split(":", 1)[1]
    winning_fixture = next(
        fixture for fixture in fixtures if fixture[3].pair_id == winning_pair_ref
    )
    loaded = load_contradiction_calibration_stage_sidecar(
        path,
        calibration_kernel=winning_fixture[0][0],
        held_out_kernel=winning_fixture[1][0],
        lenses=winning_fixture[2],
    )
    assert loaded.stage_receipt.pair_context_ref == winning_pair_ref
    assert list(tmp_path.glob(".arbitrated-stage.vcs.*.tmp")) == []


@requires_posix_stage
def test_stage_rejects_crossed_context_and_fully_rehashed_authority_tamper(
    tmp_path: Path,
) -> None:
    path = tmp_path / "tamper-stage.vcs"
    calibration, held_out, lenses, *_ = _prepared_stage(path, 6950)

    with pytest.raises(
        ContradictionCalibrationStageIntegrityError,
        match="different protected state|stale or substituted",
    ):
        load_contradiction_calibration_stage_sidecar(
            path,
            calibration_kernel=held_out[0],
            held_out_kernel=calibration[0],
            lenses=lenses,
        )

    payload = json.loads(path.read_text(encoding="utf-8"))
    receipt = payload["stage_receipt"]
    receipt["resolution_authority_enabled"] = True
    receipt["stage_receipt_id"] = stable_id(
        "contradiction_calibration_stage_receipt",
        {
            key: value
            for key, value in receipt.items()
            if key != "stage_receipt_id"
        },
    )
    payload["stage_receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(receipt)
    ).hexdigest()
    path.write_bytes(canonical_json_bytes(payload))

    with pytest.raises(
        ContradictionCalibrationStageIntegrityError,
        match="Invalid Contradiction calibration-stage sidecar",
    ):
        read_contradiction_calibration_stage_sidecar(path)


@requires_posix_stage
def test_failed_resume_rolls_back_and_nonpristine_held_out_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "resume-rollback.vcs"
    (
        calibration,
        held_out,
        lenses,
        _,
        _,
        _,
        held_out_runtime,
        runner,
        _,
    ) = _prepared_stage(path, 6960)
    stage_bytes = path.read_bytes()
    held_out_before = held_out_runtime.ledger.fingerprint()

    class FailHeldOutRun:
        def run(self, *args, **kwargs):
            raise ContradictionLensControlIntegrityError(
                "injected held-out resume failure"
            )

    with pytest.raises(
        ContradictionCalibrationStageIntegrityError,
        match="injected held-out resume failure",
    ):
        ContradictionDurableDimensionTrialRunner(
            controlled_runner=FailHeldOutRun()
        ).resume_from_stage(
            path,
            calibration[0],
            held_out[0],
            held_out_runtime,
            lenses,
        )
    assert held_out_runtime.ledger.fingerprint() == held_out_before
    assert path.read_bytes() == stage_bytes

    runner.resume_from_stage(
        path,
        calibration[0],
        held_out[0],
        held_out_runtime,
        lenses,
    )
    with pytest.raises(
        ContradictionCalibrationStageIntegrityError,
        match="pristine preregistered ledger",
    ):
        runner.resume_from_stage(
            path,
            calibration[0],
            held_out[0],
            held_out_runtime,
            lenses,
        )


@requires_posix_stage
def test_same_stage_write_is_idempotent_but_foreign_stage_cannot_replace_it(
    tmp_path: Path,
) -> None:
    path = tmp_path / "immutable-stage.vcs"
    first = _pair_fixture(6970)
    runner = ContradictionDurableDimensionTrialRunner()
    original = runner.prepare_and_persist(
        path,
        first[0][0],
        CounterfactualRuntime(),
        first[1][0],
        first[2],
        pair_context=first[3],
        criterion_declaration=first[4],
    )
    first_bytes = path.read_bytes()
    replay = runner.prepare_and_persist(
        path,
        first[0][0],
        CounterfactualRuntime(),
        first[1][0],
        first[2],
        pair_context=first[3],
        criterion_declaration=first[4],
    )
    assert replay.envelope == original.envelope
    assert path.read_bytes() == first_bytes

    foreign = _pair_fixture(6980)
    with pytest.raises(
        ContradictionCalibrationStageIntegrityError,
        match="already committed a different receipt",
    ):
        runner.prepare_and_persist(
            path,
            foreign[0][0],
            CounterfactualRuntime(),
            foreign[1][0],
            foreign[2],
            pair_context=foreign[3],
            criterion_declaration=foreign[4],
        )
    assert path.read_bytes() == first_bytes


def _downstream_paths(tmp_path: Path, label: str = "outcome"):
    return (
        tmp_path / f"{label}.vop",
        tmp_path / f"{label}.vcs",
        tmp_path / f"{label}.vor",
    )


def _execute_downstream(
    tmp_path: Path,
    *,
    seed: int = 6990,
    policy: ContradictionDownstreamOutcomePolicy | None = None,
    runner: ContradictionDurableDownstreamOutcomeRunner | None = None,
):
    calibration, held_out, lenses, pair, declaration = _pair_fixture(seed)
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    paths = _downstream_paths(tmp_path, str(seed))
    result = (runner or ContradictionDurableDownstreamOutcomeRunner()).run(
        *paths,
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        pair_context=pair,
        criterion_declaration=declaration,
        outcome_policy=policy,
    )
    return (
        calibration,
        held_out,
        lenses,
        pair,
        declaration,
        calibration_runtime,
        held_out_runtime,
        paths,
        result,
    )


@requires_posix_stage
def test_downstream_outcome_is_preregistered_and_uses_count_only_native_trace(
    tmp_path: Path,
) -> None:
    pre_path, _, result_path = _downstream_paths(tmp_path, "6990")
    stage_saw_preregistration: list[bool] = []

    class OrderingRunner(ContradictionDurableDimensionTrialRunner):
        def prepare_and_persist(self, *args, **kwargs):
            stage_saw_preregistration.append(
                pre_path.exists() and not result_path.exists()
            )
            return super().prepare_and_persist(*args, **kwargs)

    fixture = _pair_fixture(6990)
    canonical_before = (fixture[0][0].fingerprint(), fixture[1][0].fingerprint())
    lens_before = fixture[2].fingerprint()
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    paths = _downstream_paths(tmp_path, "6990")
    outcome = ContradictionDurableDownstreamOutcomeRunner(
        dimension_runner=OrderingRunner()
    ).run(
        *paths,
        fixture[0][0],
        calibration_runtime,
        fixture[1][0],
        held_out_runtime,
        fixture[2],
        pair_context=fixture[3],
        criterion_declaration=fixture[4],
    )

    receipt = outcome.receipt
    assert stage_saw_preregistration == [True]
    assert all(path.exists() for path in paths)
    assert receipt.disposition == (
        ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
    )
    assert receipt.baseline.trace_added_structure_count == 0
    assert receipt.treatment.trace_added_structure_count == 1
    assert receipt.baseline.trace_field == CONTRADICTION_DOWNSTREAM_TRACE_FIELD
    assert receipt.treatment.trace_field == CONTRADICTION_DOWNSTREAM_TRACE_FIELD
    assert receipt.baseline.raw_score == pytest.approx(0.24)
    assert receipt.baseline.effective_score == pytest.approx(0.232)
    assert not receipt.baseline.admitted
    assert receipt.treatment.raw_score == pytest.approx(0.38)
    assert receipt.treatment.effective_score == pytest.approx(0.372)
    assert receipt.treatment.admitted
    assert receipt.baseline.candidate_control_signature == (
        receipt.treatment.candidate_control_signature
    )
    assert receipt.baseline.source_contradiction_ref == (
        receipt.treatment.source_contradiction_ref
    )
    assert receipt.baseline.source_claim_refs == receipt.treatment.source_claim_refs
    assert receipt.baseline.source_evidence_refs == (
        receipt.treatment.source_evidence_refs
    )
    assert receipt.baseline.candidate.evidence_refs == receipt.source_evidence_refs
    assert receipt.treatment.candidate.evidence_refs == receipt.source_evidence_refs
    assert not receipt.baseline.trace_record_identities_consulted
    assert not receipt.treatment.trace_record_identities_consulted
    assert not receipt.baseline.lens_projections_consulted
    assert not receipt.treatment.functional_disposition_consulted
    assert receipt.outcome_derived_from_actual_experiment_traces
    assert receipt.identical_matched_workspace_controls_verified
    assert receipt.evidence_preserved and receipt.anti_suppression_verified
    assert not receipt.predictive_discrimination_observed
    assert not receipt.dimensional_separation_observed
    assert not receipt.external_outcome_observed
    assert not receipt.resolution_trial_ready
    assert not receipt.resolution_authority_enabled
    assert not receipt.policy_rewrite_authority_enabled
    assert not receipt.canonical_commit_permitted
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert len(held_out_runtime.ledger.state.settlements) == 2
    assert (fixture[0][0].fingerprint(), fixture[1][0].fingerprint()) == (
        canonical_before
    )
    assert fixture[2].fingerprint() == lens_before


@requires_posix_stage
def test_downstream_outcome_retains_an_explicit_native_valid_null(
    tmp_path: Path,
) -> None:
    *_, result = _execute_downstream(
        tmp_path,
        seed=7000,
        policy=ContradictionDownstreamOutcomePolicy(
            minimum_admission_score=0.0
        ),
    )
    receipt = result.receipt
    assert receipt.disposition == ContradictionDownstreamOutcomeDisposition.VALID_NULL
    assert receipt.baseline.admitted
    assert receipt.treatment.admitted
    assert receipt.baseline.trace_added_structure_count == 0
    assert receipt.treatment.trace_added_structure_count == 1
    assert receipt.baseline.candidate_control_signature == (
        receipt.treatment.candidate_control_signature
    )
    assert receipt.explicit_valid_null_supported
    assert not receipt.predictive_discrimination_observed


@requires_posix_stage
def test_downstream_observer_failure_publishes_no_held_out_state_or_result(
    tmp_path: Path,
) -> None:
    paths = _downstream_paths(tmp_path, "7010")
    fixture = _pair_fixture(7010)
    canonical_before = (fixture[0][0].fingerprint(), fixture[1][0].fingerprint())
    lens_before = fixture[2].fingerprint()
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()

    class FailingObserver(ContradictionDownstreamOutcomeObserver):
        def observe(self, *args, **kwargs):
            raise ContradictionDownstreamOutcomeIntegrityError(
                "injected downstream observer failure"
            )

    with pytest.raises(
        ContradictionDownstreamOutcomeIntegrityError,
        match="injected downstream observer failure",
    ):
        ContradictionDurableDownstreamOutcomeRunner(
            observer=FailingObserver()
        ).run(
            *paths,
            fixture[0][0],
            calibration_runtime,
            fixture[1][0],
            held_out_runtime,
            fixture[2],
            pair_context=fixture[3],
            criterion_declaration=fixture[4],
        )
    assert paths[0].exists()
    assert paths[1].exists()
    assert not paths[2].exists()
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert held_out_runtime.ledger.state.settlements == ()
    assert (fixture[0][0].fingerprint(), fixture[1][0].fingerprint()) == (
        canonical_before
    )
    assert fixture[2].fingerprint() == lens_before


@requires_posix_stage
def test_downstream_outcome_rejects_a_foreign_simulation_ledger(
    tmp_path: Path,
) -> None:
    _, held_out, _, _, _, _, _, _, completed = _execute_downstream(
        tmp_path, seed=7020
    )
    receipt = completed.receipt
    foreign = completed.calibration_ledger
    foreign_before = foreign.fingerprint()
    canonical_before = held_out[0].fingerprint()
    with pytest.raises(
        ContradictionDownstreamOutcomeIntegrityError,
        match="ledger|settlement|observation|simulation",
    ):
        ContradictionDownstreamOutcomeObserver().observe(
            held_out[0],
            foreign,
            declaration=receipt.declaration,
            preregistration_sha256=receipt.preregistration_sha256,
            calibration_stage_sha256=receipt.calibration_stage_sha256,
            calibration_stage_receipt_ref=receipt.calibration_stage_receipt_ref,
            held_out_observation=receipt.held_out_observation,
        )
    assert foreign.fingerprint() == foreign_before
    assert held_out[0].fingerprint() == canonical_before


@requires_posix_stage
def test_downstream_result_rejects_fully_rehashed_authority_tamper(
    tmp_path: Path,
) -> None:
    *_, paths, _ = _execute_downstream(tmp_path, seed=7030)
    result_path = paths[2]
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    receipt = payload["receipt"]
    receipt["predictive_discrimination_observed"] = True
    receipt["receipt_id"] = stable_id(
        "contradiction_downstream_outcome_receipt",
        {key: value for key, value in receipt.items() if key != "receipt_id"},
    )
    payload["receipt_sha256"] = hashlib.sha256(
        canonical_json_bytes(receipt)
    ).hexdigest()
    result_path.write_bytes(canonical_json_bytes(payload))
    with pytest.raises(
        ContradictionDownstreamOutcomeIntegrityError,
        match="Invalid downstream result",
    ):
        read_contradiction_downstream_result(result_path)


@requires_posix_stage
def test_completed_downstream_sidecar_replays_without_new_simulation_cost(
    tmp_path: Path,
) -> None:
    (
        calibration,
        held_out,
        lenses,
        pair,
        declaration,
        _,
        _,
        paths,
        first,
    ) = _execute_downstream(tmp_path, seed=7040)
    before = tuple(path.read_bytes() for path in paths)

    class NoExecutionRunner:
        def prepare_and_persist(self, *args, **kwargs):
            raise AssertionError("completed replay reran calibration")

        def resume_from_stage(self, *args, **kwargs):
            raise AssertionError("completed replay reran held-out simulation")

    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    replay = ContradictionDurableDownstreamOutcomeRunner(
        dimension_runner=NoExecutionRunner()
    ).run(
        *paths,
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        pair_context=pair,
        criterion_declaration=declaration,
    )
    assert replay.replayed
    assert replay.receipt == first.receipt
    assert tuple(path.read_bytes() for path in paths) == before
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert len(held_out_runtime.ledger.state.settlements) == 2


@requires_posix_stage
def test_calibration_stage_cannot_precede_downstream_preregistration(
    tmp_path: Path,
) -> None:
    pre_path, stage_path, result_path = _downstream_paths(tmp_path, "7050")
    calibration, held_out, lenses, pair, declaration = _pair_fixture(7050)
    ContradictionDurableDimensionTrialRunner().prepare_and_persist(
        stage_path,
        calibration[0],
        CounterfactualRuntime(),
        held_out[0],
        lenses,
        pair_context=pair,
        criterion_declaration=declaration,
    )
    stage_bytes = stage_path.read_bytes()
    held_out_runtime = CounterfactualRuntime()
    with pytest.raises(
        ContradictionDownstreamOutcomeIntegrityError,
        match="predates downstream preregistration",
    ):
        ContradictionDurableDownstreamOutcomeRunner().run(
            pre_path,
            stage_path,
            result_path,
            calibration[0],
            CounterfactualRuntime(),
            held_out[0],
            held_out_runtime,
            lenses,
            pair_context=pair,
            criterion_declaration=declaration,
        )
    assert not pre_path.exists()
    assert not result_path.exists()
    assert stage_path.read_bytes() == stage_bytes
    assert held_out_runtime.ledger.state.settlements == ()
