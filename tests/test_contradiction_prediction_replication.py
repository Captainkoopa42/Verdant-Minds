from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    ObligationFamily,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id
from verdant_obligations import (
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES,
    CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT,
    CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionHypothesisProtocol,
    ContradictionLensTrialContext,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSplit,
    ContradictionObligationDetector,
    ContradictionPredictionReplicationContext,
    ContradictionPredictionReplicationContextInput,
    ContradictionPredictionReplicationDeclaration,
    ContradictionPredictionReplicationIntegrityError,
    ContradictionPredictionReplicationPreregistrar,
    ContradictionPredictionReplicationPreregistrationEnvelope,
    ContradictionPredictionReplicationTraceRole,
    EquivalenceLensSystem,
    LensEvidenceResult,
    LensOpcode,
    contradiction_prediction_replication_preregistration_bytes,
    read_contradiction_prediction_replication_preregistration,
    save_contradiction_prediction_replication_preregistration,
)
from verdant_structures import VerdantStructurePipeline


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
        native_description=f"Replication evidence {event_key}.",
        subject_label=subject_label,
        predicate="has_property",
        object_label="open",
        polarity=polarity,
        source_class=source,
    )


def _background_command(index: int, label: str) -> ExperienceCommand:
    event_key = f"replication-background-{label}-{index}"
    return ExperienceCommand(
        event_key=event_key,
        source_ref="contradiction-replication:controlled-background",
        modality="text",
        payload_sha256=hashlib.sha256(event_key.encode("utf-8")).hexdigest(),
        feature_vector=(1.0, *([0.0] * 15)),
        concept_labels=(
            f"replication-{label}-a",
            f"replication-{label}-b",
            f"replication-{label}-c",
        ),
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={
            "controlled_replication_background": True,
            "context_id": f"replication-{label}-{index % 2}",
        },
        metadata={"context_id": f"replication-{label}-{index % 2}"},
    )


def _promote_background_structure(kernel: VerdantKernel, label: str) -> None:
    development = VerdantDevelopmentPipeline()
    for index in range(6):
        development.advance(kernel, _background_command(index, label))
    candidates = tuple(kernel.state.structure_candidates.values())
    assert len(candidates) == 1
    VerdantStructurePipeline().promote(kernel, candidates[0].candidate_id)
    assert len(kernel.state.structures) == 1


def _prepared(
    seed: int,
    label: str,
    *,
    negated_source: ClaimSourceClass,
    background_structure: bool = False,
):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"contradiction-replication-{label}-{seed}",
    )
    subject = f"door-{label}-{seed}"
    _claim(
        kernel,
        event_key=f"replication-affirmed-{label}-{seed}",
        subject_label=subject,
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    _claim(
        kernel,
        event_key=f"replication-negated-{label}-{seed}",
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
        source_event_key=f"replication-attention-{label}-{seed}",
    ).decision.allocations[0]
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    if background_structure:
        _promote_background_structure(kernel, f"{label}-{seed}")
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
        source_event_key=f"replication-lens:approve:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
    )
    lenses.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"replication-lens:evidence:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
        hypothesis_refs=tuple(item.hypothesis_id for item in bundle.hypotheses),
    )
    return lenses


def _input(
    seed: int,
    label: str,
    *,
    held_out_negated_source: ClaimSourceClass,
    trace_role: ContradictionPredictionReplicationTraceRole,
) -> ContradictionPredictionReplicationContextInput:
    calibration_kernel, calibration_bundle = _prepared(
        seed,
        f"{label}-calibration",
        negated_source=ClaimSourceClass.HUMAN_TESTIMONY,
    )
    held_out_kernel, held_out_bundle = _prepared(
        seed + 1,
        f"{label}-held-out",
        negated_source=held_out_negated_source,
        background_structure=(
            trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
        ),
    )
    lenses = _lenses(calibration_kernel, calibration_bundle)
    pair = ContradictionLensTrialPairContext.build(
        calibration=ContradictionLensTrialContext.build(
            calibration_kernel,
            calibration_bundle,
            lenses,
            split=ContradictionLensTrialSplit.CALIBRATION,
            source_event_key=f"replication-calibration:{label}:{seed}",
        ),
        held_out=ContradictionLensTrialContext.build(
            held_out_kernel,
            held_out_bundle,
            lenses,
            split=ContradictionLensTrialSplit.HELD_OUT,
            source_event_key=f"replication-held-out:{label}:{seed + 1}",
        ),
    )
    return ContradictionPredictionReplicationContextInput(
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        pair_context=pair,
        trace_role=trace_role,
    )


@pytest.fixture(scope="module")
def replication_inputs():
    low = ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL
    high = ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
    return (
        _input(
            9101,
            "singleton-low",
            held_out_negated_source=ClaimSourceClass.HUMAN_TESTIMONY,
            trace_role=low,
        ),
        _input(
            9201,
            "singleton-high",
            held_out_negated_source=ClaimSourceClass.HUMAN_TESTIMONY,
            trace_role=high,
        ),
        _input(
            9301,
            "multi-low",
            held_out_negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
            trace_role=low,
        ),
        _input(
            9401,
            "multi-high",
            held_out_negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
            trace_role=high,
        ),
    )


@pytest.fixture(scope="module")
def preregistered_replication(tmp_path_factory, replication_inputs):
    root = tmp_path_factory.mktemp("contradiction-replication")
    path = root / "replication.vrp"
    before = tuple(
        (
            item.calibration_kernel.fingerprint(),
            item.held_out_kernel.fingerprint(),
            item.lenses.fingerprint(),
        )
        for item in replication_inputs
    )
    envelope = ContradictionPredictionReplicationPreregistrar().register(
        path, replication_inputs
    )
    return path, replication_inputs, before, envelope


def _declared_contexts(replication_inputs):
    return tuple(
        ContradictionPredictionReplicationContext.build(
            item.pair_context,
            item.calibration_kernel,
            item.held_out_kernel,
            item.lenses,
            trace_role=item.trace_role,
        )
        for item in replication_inputs
    )


def test_four_context_native_trace_plan_is_frozen_before_execution(
    preregistered_replication,
) -> None:
    path, _, _, envelope = preregistered_replication
    declaration = envelope.declaration
    assert path.exists()
    assert len(declaration.contexts) == CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT
    assert declaration.required_profiles == (
        CONTRADICTION_PREDICTION_COHORT_REQUIRED_PROFILES
    )
    assert declaration.outcome_policy.trace_field == (
        CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD
    )
    assert declaration.outcome_policy.minimum_admission_score == 0.35
    assert not declaration.outcome_policy.threshold_variation_permitted
    assert len(declaration.folds) == 2
    for profile in declaration.required_profiles:
        contexts = tuple(
            item for item in declaration.contexts if item.expected_profile == profile
        )
        assert len(contexts) == 2
        assert {item.trace_role for item in contexts} == set(
            ContradictionPredictionReplicationTraceRole
        )
        low = next(
            item
            for item in contexts
            if item.trace_role
            == ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL
        )
        high = next(
            item
            for item in contexts
            if item.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
        )
        assert low.canonical_preexisting_structure_count == 0
        assert low.declared_baseline_after_structure_count == 0
        assert low.declared_treatment_after_structure_count == 1
        assert not low.background_structure_refs
        assert high.canonical_preexisting_structure_count == 1
        assert high.declared_baseline_after_structure_count == 1
        assert high.declared_treatment_after_structure_count == 2
        assert len(high.background_structure_refs) == 1
        assert high.background_evidence_refs
        assert len(high.background_council_decision_refs) == 1
        assert len(high.background_promotion_event_refs) == 1
    assert not declaration.replication_executed
    assert not declaration.outcomes_observed
    assert not declaration.predictive_discrimination_observed
    assert not declaration.dimensional_separation_observed
    assert not declaration.authority_enabled
    assert not declaration.canonical_commit_permitted


def test_preregistration_is_pure_and_has_no_simulation_or_result_artifacts(
    preregistered_replication,
) -> None:
    path, inputs, before, _ = preregistered_replication
    after = tuple(
        (
            item.calibration_kernel.fingerprint(),
            item.held_out_kernel.fingerprint(),
            item.lenses.fingerprint(),
        )
        for item in inputs
    )
    assert after == before
    assert not tuple(path.parent.glob("*.vrr"))
    assert not tuple(path.parent.glob("*.vpa"))
    assert not tuple(path.parent.glob("*.vcs"))


def test_context_order_does_not_change_canonical_preregistration(
    preregistered_replication,
) -> None:
    _, inputs, _, envelope = preregistered_replication
    reversed_declaration = ContradictionPredictionReplicationDeclaration.build(
        tuple(reversed(_declared_contexts(inputs)))
    )
    reversed_envelope = (
        ContradictionPredictionReplicationPreregistrationEnvelope.build(
            reversed_declaration
        )
    )
    assert reversed_envelope == envelope
    assert contradiction_prediction_replication_preregistration_bytes(
        reversed_envelope
    ) == contradiction_prediction_replication_preregistration_bytes(envelope)


def test_wrong_trace_role_and_foreign_lens_fail_before_publication(
    tmp_path: Path,
    replication_inputs,
) -> None:
    high = replication_inputs[1]
    wrong_role = replace(
        high,
        trace_role=ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL,
    )
    path = tmp_path / "wrong-role.vrp"
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="trace role disagrees",
    ):
        ContradictionPredictionReplicationPreregistrar().register(
            path,
            (replication_inputs[0], wrong_role, *replication_inputs[2:]),
        )
    assert not path.exists()

    low = replication_inputs[0]
    foreign_lens = replace(low, lenses=replication_inputs[2].lenses)
    path = tmp_path / "foreign-lens.vrp"
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="foreign Lens",
    ):
        ContradictionPredictionReplicationPreregistrar().register(
            path, (foreign_lens, *replication_inputs[1:])
        )
    assert not path.exists()


def test_duplicate_canonical_context_is_rejected_before_publication(
    tmp_path: Path,
    replication_inputs,
) -> None:
    path = tmp_path / "duplicate.vrp"
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="distinct canonical kernels",
    ):
        ContradictionPredictionReplicationPreregistrar().register(
            path,
            (*replication_inputs[:3], replication_inputs[0]),
        )
    assert not path.exists()


def test_fully_rehashed_background_evidence_reuse_is_rejected(
    replication_inputs,
) -> None:
    contexts = list(_declared_contexts(replication_inputs))
    high_indexes = [
        index
        for index, item in enumerate(contexts)
        if item.trace_role
        == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
    ]
    source = contexts[high_indexes[0]]
    target = contexts[high_indexes[1]]
    payload = target.model_dump(mode="json")
    payload["background_evidence_refs"] = list(source.background_evidence_refs)
    payload["context_id"] = stable_id(
        "contradiction_prediction_replication_context",
        {key: value for key, value in payload.items() if key != "context_id"},
    )
    contexts[high_indexes[1]] = ContradictionPredictionReplicationContext.model_validate(
        payload
    )
    with pytest.raises(ValueError, match="reuse protected evidence"):
        ContradictionPredictionReplicationDeclaration.build(contexts)


def test_fully_rehashed_authority_forgery_is_rejected(
    tmp_path: Path,
    preregistered_replication,
) -> None:
    _, _, _, envelope = preregistered_replication
    payload = json.loads(
        contradiction_prediction_replication_preregistration_bytes(envelope)
    )
    declaration = payload["declaration"]
    declaration["authority_enabled"] = True
    declaration["declaration_id"] = stable_id(
        "contradiction_prediction_replication_declaration",
        {
            key: value
            for key, value in declaration.items()
            if key != "declaration_id"
        },
    )
    payload["declaration_sha256"] = hashlib.sha256(
        canonical_json_bytes(declaration)
    ).hexdigest()
    path = tmp_path / "authority-forgery.vrp"
    path.write_bytes(canonical_json_bytes(payload))
    with pytest.raises(ContradictionPredictionReplicationIntegrityError):
        read_contradiction_prediction_replication_preregistration(path)


def test_sidecar_tamper_and_noncanonical_bytes_are_rejected(
    tmp_path: Path,
    preregistered_replication,
) -> None:
    _, _, _, envelope = preregistered_replication
    data = contradiction_prediction_replication_preregistration_bytes(envelope)
    changed = bytearray(data)
    changed[-2] ^= 1
    path = tmp_path / "digest-tamper.vrp"
    path.write_bytes(changed)
    with pytest.raises(ContradictionPredictionReplicationIntegrityError):
        read_contradiction_prediction_replication_preregistration(path)

    path = tmp_path / "noncanonical.vrp"
    path.write_bytes(data + b"\n")
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="not canonical",
    ):
        read_contradiction_prediction_replication_preregistration(path)


def test_immutable_path_is_idempotent_but_never_overwritten(
    tmp_path: Path,
    preregistered_replication,
) -> None:
    _, _, _, envelope = preregistered_replication
    path = tmp_path / "immutable.vrp"
    declaration_id = save_contradiction_prediction_replication_preregistration(
        path, envelope
    )
    first = path.read_bytes()
    assert save_contradiction_prediction_replication_preregistration(
        path, envelope
    ) == declaration_id
    assert path.read_bytes() == first

    path.write_bytes(b"occupied-by-different-evidence")
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="different evidence",
    ):
        save_contradiction_prediction_replication_preregistration(path, envelope)
    assert path.read_bytes() == b"occupied-by-different-evidence"


def test_sidecar_size_is_checked_before_json_parse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import verdant_obligations.contradiction_prediction_replication as module

    path = tmp_path / "oversized.vrp"
    path.write_bytes(b"not-json-but-too-large")
    monkeypatch.setattr(module, "_MAX_SIDECAR_BYTES", 4)
    with pytest.raises(
        ContradictionPredictionReplicationIntegrityError,
        match="exceeds its size limit",
    ):
        read_contradiction_prediction_replication_preregistration(path)
