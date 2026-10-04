from __future__ import annotations

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
    ContradictionHypothesisProtocol,
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlIntegrityError,
    ContradictionLensHeldOutReplicationReceipt,
    ContradictionLensHeldOutTrialRunner,
    ContradictionLensReplicationDisposition,
    ContradictionLensTrialContext,
    ContradictionLensTrialIntegrityError,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSplit,
    ContradictionObligationDetector,
    ContradictionResolutionRequirement,
    CounterfactualRuntime,
    EquivalenceLensSystem,
    LensEvidenceResult,
    LensOpcode,
    contradiction_lens_trial_sidecar_bytes,
    load_contradiction_lens_trial_sidecar,
    load_experiment_archive_bundle,
    save_contradiction_lens_trial_sidecar,
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
        native_description=f"Held-out Contradiction evidence {event_key}.",
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
        run_label=f"contradiction-held-out-{label}-{seed}",
    )
    subject = f"door-{label}-{seed}"
    _claim(
        kernel,
        event_key=f"held-out-affirmed-{label}-{seed}",
        subject_label=subject,
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    _claim(
        kernel,
        event_key=f"held-out-negated-{label}-{seed}",
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
        source_event_key=f"held-out-attention-{label}-{seed}",
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
        source_event_key=f"held-out-lens:approve:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
    )
    lenses.record_evidence(
        binding_id=binding.binding_id,
        result=LensEvidenceResult.VALID_NULL,
        independent_consequence_refs=(bundle.evidence_receipt.receipt_id,),
        source_event_key=f"held-out-lens:evidence:{bundle.bundle_id}",
        cycle=kernel.state.cycle,
        hypothesis_refs=tuple(item.hypothesis_id for item in bundle.hypotheses),
    )
    return lenses


def _pair_fixture(seed: int = 6601):
    calibration = _prepared(seed, "calibration")
    held_out = _prepared(seed + 1, "held-out")
    lenses = _lenses(calibration[0], calibration[3])
    calibration_context = ContradictionLensTrialContext.build(
        calibration[0],
        calibration[3],
        lenses,
        split=ContradictionLensTrialSplit.CALIBRATION,
        source_event_key=f"contradiction-calibration:{seed}",
    )
    held_out_context = ContradictionLensTrialContext.build(
        held_out[0],
        held_out[3],
        lenses,
        split=ContradictionLensTrialSplit.HELD_OUT,
        source_event_key=f"contradiction-held-out:{seed + 1}",
    )
    pair = ContradictionLensTrialPairContext.build(
        calibration=calibration_context,
        held_out=held_out_context,
    )
    return calibration, held_out, lenses, pair


def _execute(seed: int = 6601):
    calibration, held_out, lenses, pair = _pair_fixture(seed)
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    result = ContradictionLensHeldOutTrialRunner().run(
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        calibration_bundle=calibration[3],
        held_out_bundle=held_out[3],
        pair_context=pair,
    )
    return (
        calibration,
        held_out,
        lenses,
        pair,
        calibration_runtime,
        held_out_runtime,
        result,
    )


def _rehash_context(payload: dict) -> dict:
    values = dict(payload)
    values["context_id"] = stable_id(
        "contradiction_lens_trial_context",
        {key: value for key, value in values.items() if key != "context_id"},
    )
    return values


def _rehash_pair(payload: dict) -> dict:
    values = dict(payload)
    values["pair_id"] = stable_id(
        "contradiction_lens_trial_pair_context",
        {key: value for key, value in values.items() if key != "pair_id"},
    )
    return values


def _rehash_receipt(payload: dict) -> dict:
    values = dict(payload)
    values["receipt_id"] = stable_id(
        "contradiction_lens_held_out_replication",
        {key: value for key, value in values.items() if key != "receipt_id"},
    )
    return values


def test_independent_contexts_replicate_only_internal_structural_effect() -> None:
    (
        calibration,
        held_out,
        lenses,
        pair,
        calibration_runtime,
        held_out_runtime,
        result,
    ) = _execute()

    assert pair.calibration.canonical_checkpoint_fingerprint != (
        pair.held_out.canonical_checkpoint_fingerprint
    )
    assert set(pair.calibration.claim_refs).isdisjoint(pair.held_out.claim_refs)
    assert set(pair.calibration.protected_evidence_refs).isdisjoint(
        pair.held_out.protected_evidence_refs
    )
    assert pair.calibration.source_root_universe == pair.held_out.source_root_universe
    assert pair.calibration.lens_fingerprint == pair.held_out.lens_fingerprint
    assert pair.lens_fingerprint == lenses.fingerprint()
    assert len(calibration_runtime.ledger.state.settlements) == 2
    assert len(held_out_runtime.ledger.state.settlements) == 2
    assert result.receipt.structural_effect_replicated
    assert result.receipt.disposition == (
        ContradictionLensReplicationDisposition.STRUCTURAL_EFFECT_REPLICATED
    )
    assert result.receipt.deterministic_internal_replication_only
    assert not result.receipt.independent_held_out_replication_observed
    assert not result.receipt.predictive_discrimination_observed
    assert not result.receipt.source_independence_observed
    assert not result.receipt.dimensional_separation_observed
    assert not result.receipt.resolution_trial_ready
    assert result.receipt.missing_requirements == (
        CONTRADICTION_LENS_MISSING_REQUIREMENTS
    )
    assert {
        ContradictionResolutionRequirement.DIMENSIONAL_SEPARATION,
        ContradictionResolutionRequirement.INDEPENDENT_HELD_OUT_REPLICATION,
        ContradictionResolutionRequirement.PREDICTIVE_DISCRIMINATION,
        ContradictionResolutionRequirement.SOURCE_INDEPENDENCE,
    }.issubset(result.receipt.missing_requirements)
    assert calibration[0].fingerprint() == (
        pair.calibration.canonical_checkpoint_fingerprint
    )
    assert held_out[0].fingerprint() == pair.held_out.canonical_checkpoint_fingerprint


def test_independent_context_can_return_explicit_divergent_structural_null() -> None:
    calibration = _prepared(6605, "calibration-divergent")
    held_out = _prepared(
        6606,
        "held-out-divergent",
        negated_source=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    lenses = _lenses(calibration[0], calibration[3])
    pair = ContradictionLensTrialPairContext.build(
        calibration=ContradictionLensTrialContext.build(
            calibration[0],
            calibration[3],
            lenses,
            split=ContradictionLensTrialSplit.CALIBRATION,
            source_event_key="divergent:calibration",
        ),
        held_out=ContradictionLensTrialContext.build(
            held_out[0],
            held_out[3],
            lenses,
            split=ContradictionLensTrialSplit.HELD_OUT,
            source_event_key="divergent:held-out",
        ),
    )
    result = ContradictionLensHeldOutTrialRunner().run(
        calibration[0],
        CounterfactualRuntime(),
        held_out[0],
        CounterfactualRuntime(),
        lenses,
        calibration_bundle=calibration[3],
        held_out_bundle=held_out[3],
        pair_context=pair,
    )

    assert not result.receipt.structural_effect_replicated
    assert result.receipt.disposition == (
        ContradictionLensReplicationDisposition.VALID_NULL_DIVERGENT_EFFECT
    )
    assert not result.receipt.independent_held_out_replication_observed
    assert not result.receipt.resolution_trial_ready


def test_same_canonical_context_cannot_masquerade_as_held_out() -> None:
    calibration, _, lenses, _ = _pair_fixture(6610)
    first = ContradictionLensTrialContext.build(
        calibration[0],
        calibration[3],
        lenses,
        split=ContradictionLensTrialSplit.CALIBRATION,
        source_event_key="same-context:calibration",
    )
    renamed = ContradictionLensTrialContext.build(
        calibration[0],
        calibration[3],
        lenses,
        split=ContradictionLensTrialSplit.HELD_OUT,
        source_event_key="same-context:held-out",
    )

    with pytest.raises(ValueError, match="not canonically independent"):
        ContradictionLensTrialPairContext.build(
            calibration=first,
            held_out=renamed,
        )


def test_held_out_context_requires_exact_calibration_lens_lineage() -> None:
    calibration, held_out, lenses, pair = _pair_fixture(6620)
    replacement_lenses = _lenses(held_out[0], held_out[3])
    replacement = ContradictionLensTrialContext.build(
        held_out[0],
        held_out[3],
        replacement_lenses,
        split=ContradictionLensTrialSplit.HELD_OUT,
        source_event_key="mismatched-lens:held-out",
    )

    assert lenses.fingerprint() == pair.lens_fingerprint
    assert replacement_lenses.fingerprint() != lenses.fingerprint()
    with pytest.raises(ValueError, match="identical Lens lineage"):
        ContradictionLensTrialPairContext.build(
            calibration=pair.calibration,
            held_out=replacement,
        )


def test_sidecar_change_after_preregistration_fails_without_publication() -> None:
    calibration, held_out, lenses, pair = _pair_fixture(6630)
    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    simulation_before = (
        calibration_runtime.ledger.fingerprint(),
        held_out_runtime.ledger.fingerprint(),
    )
    lenses.register_definition(
        operators=(LensOpcode.SELECT_ACTION,),
        provenance_refs=("post-preregistration-definition",),
    )
    lens_before = lenses.fingerprint()

    with pytest.raises(
        ContradictionLensTrialIntegrityError,
        match="stale or substituted",
    ):
        ContradictionLensHeldOutTrialRunner().run(
            calibration[0],
            calibration_runtime,
            held_out[0],
            held_out_runtime,
            lenses,
            calibration_bundle=calibration[3],
            held_out_bundle=held_out[3],
            pair_context=pair,
        )
    assert calibration_runtime.ledger.fingerprint() == simulation_before[0]
    assert held_out_runtime.ledger.fingerprint() == simulation_before[1]
    assert lenses.fingerprint() == lens_before


def test_second_context_failure_rolls_back_both_simulation_ledgers() -> None:
    calibration, held_out, lenses, pair = _pair_fixture(6640)
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

    class FailSecondControlledRun:
        def __init__(self) -> None:
            self.calls = 0
            self.delegate = ContradictionLensControlledProbeRunner()

        def run(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise ContradictionLensControlIntegrityError(
                    "injected held-out observer failure"
                )
            return self.delegate.run(*args, **kwargs)

    with pytest.raises(
        ContradictionLensTrialIntegrityError,
        match="injected held-out observer failure",
    ):
        ContradictionLensHeldOutTrialRunner(
            controlled_runner=FailSecondControlledRun()
        ).run(
            calibration[0],
            calibration_runtime,
            held_out[0],
            held_out_runtime,
            lenses,
            calibration_bundle=calibration[3],
            held_out_bundle=held_out[3],
            pair_context=pair,
        )
    assert calibration_runtime.ledger.fingerprint() == simulation_before[0]
    assert held_out_runtime.ledger.fingerprint() == simulation_before[1]
    assert calibration[0].fingerprint() == canonical_before[0]
    assert held_out[0].fingerprint() == canonical_before[1]
    assert lenses.fingerprint() == lens_before


def test_fully_rehashed_context_overlap_and_authority_tamper_fail_closed() -> None:
    _, _, _, pair, _, _, result = _execute(6650)
    pair_payload = pair.model_dump(mode="json")
    held_out_payload = dict(pair_payload["held_out"])
    held_out_payload["canonical_checkpoint_fingerprint"] = (
        pair.calibration.canonical_checkpoint_fingerprint
    )
    pair_payload["held_out"] = _rehash_context(held_out_payload)

    with pytest.raises(ValueError, match="not canonically independent"):
        ContradictionLensTrialPairContext.model_validate(_rehash_pair(pair_payload))

    receipt_payload = result.receipt.model_dump(mode="json")
    receipt_payload["predictive_discrimination_observed"] = True
    with pytest.raises(ValueError, match="claim boundary"):
        ContradictionLensHeldOutReplicationReceipt.model_validate(
            _rehash_receipt(receipt_payload)
        )


def test_preregistration_and_completed_receipt_are_durable_sidecars(
    tmp_path: Path,
) -> None:
    calibration, held_out, lenses, pair = _pair_fixture(6660)
    preregistration = tmp_path / "contradiction-preregistration.vct"
    save_contradiction_lens_trial_sidecar(preregistration, pair)
    loaded_preregistration = load_contradiction_lens_trial_sidecar(
        preregistration,
        calibration_kernel=calibration[0],
        held_out_kernel=held_out[0],
        lenses=lenses,
    )
    assert loaded_preregistration.pair_context == pair
    assert loaded_preregistration.receipt is None
    assert preregistration.read_bytes() == contradiction_lens_trial_sidecar_bytes(
        pair
    )

    calibration_runtime = CounterfactualRuntime()
    held_out_runtime = CounterfactualRuntime()
    result = ContradictionLensHeldOutTrialRunner().run(
        calibration[0],
        calibration_runtime,
        held_out[0],
        held_out_runtime,
        lenses,
        calibration_bundle=calibration[3],
        held_out_bundle=held_out[3],
        pair_context=pair,
    )
    completed = tmp_path / "contradiction-completed.vct"
    save_contradiction_lens_trial_sidecar(
        completed,
        pair,
        receipt=result.receipt,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )
    loaded = load_contradiction_lens_trial_sidecar(
        completed,
        calibration_kernel=calibration[0],
        held_out_kernel=held_out[0],
        lenses=lenses,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )
    assert loaded.receipt == result.receipt
    assert completed.read_bytes() == contradiction_lens_trial_sidecar_bytes(
        pair,
        receipt=result.receipt,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )

    with pytest.raises(
        ContradictionLensTrialIntegrityError,
        match="different simulation state",
    ):
        load_contradiction_lens_trial_sidecar(
            completed,
            calibration_kernel=calibration[0],
            held_out_kernel=held_out[0],
            lenses=lenses,
            calibration_ledger=held_out_runtime.ledger,
            held_out_ledger=calibration_runtime.ledger,
        )


def test_dual_archive_replay_reconstructs_exact_pair_and_receipt(
    tmp_path: Path,
) -> None:
    (
        calibration,
        held_out,
        lenses,
        pair,
        calibration_runtime,
        held_out_runtime,
        first,
    ) = _execute(6670)
    calibration_archive = tmp_path / "calibration.vob"
    held_out_archive = tmp_path / "held-out.vob"
    sidecar = tmp_path / "pair.vct"
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
    save_contradiction_lens_trial_sidecar(
        sidecar,
        pair,
        receipt=first.receipt,
        calibration_ledger=calibration_runtime.ledger,
        held_out_ledger=held_out_runtime.ledger,
    )

    restored_calibration = load_experiment_archive_bundle(calibration_archive)
    restored_held_out = load_experiment_archive_bundle(held_out_archive)
    assert restored_calibration.lens_system is not None
    assert restored_held_out.lens_system is not None
    assert (
        restored_calibration.lens_system.fingerprint()
        == restored_held_out.lens_system.fingerprint()
        == lenses.fingerprint()
    )
    loaded = load_contradiction_lens_trial_sidecar(
        sidecar,
        calibration_kernel=restored_calibration.kernel,
        held_out_kernel=restored_held_out.kernel,
        lenses=restored_calibration.lens_system,
        calibration_ledger=restored_calibration.simulation_ledger,
        held_out_ledger=restored_held_out.simulation_ledger,
    )
    assert loaded.receipt == first.receipt
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
    replay = ContradictionLensHeldOutTrialRunner().run(
        restored_calibration.kernel,
        CounterfactualRuntime(restored_calibration.simulation_ledger),
        restored_held_out.kernel,
        CounterfactualRuntime(restored_held_out.simulation_ledger),
        restored_calibration.lens_system,
        calibration_bundle=calibration_bundle,
        held_out_bundle=held_out_bundle,
        pair_context=loaded.pair_context,
    )

    assert replay.replayed
    assert replay.receipt == first.receipt
    assert restored_calibration.simulation_ledger.fingerprint() == simulation_before[0]
    assert restored_held_out.simulation_ledger.fingerprint() == simulation_before[1]
