from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel
from verdant_kernel.models import stable_id
from verdant_obligations import (
    CONTRADICTION_GROUNDED_REQUIREMENTS,
    CONTRADICTION_HYPOTHESIS_PROTOCOL_VERSION,
    CONTRADICTION_MISSING_REQUIREMENTS,
    CONTRADICTION_PROVENANCE_ACTION_OPERATOR,
    AttentionBidInput,
    AttentionPortfolio,
    ContradictionHypothesisProtocol,
    ContradictionObligationDetector,
    ContradictionProvenanceDisposition,
    ContradictionProvenanceObservation,
    ContradictionProvenanceProbe,
    ContradictionProvenanceProbeIntegrityError,
    ContradictionProvenanceProbeObserver,
    ContradictionProvenanceProbeRunner,
    ContradictionResolutionEvidenceDeriver,
    ContradictionResolutionEvidenceIntegrityError,
    ContradictionResolutionEvidenceReceipt,
    ContradictionResolutionRequirement,
    CounterfactualPatch,
    CounterfactualPlan,
    CounterfactualRuntime,
    SimulationDisposition,
    SimulationIntegrityError,
    load_experiment_archive,
    save_experiment_archive,
)


def _rehash_resolution_evidence(payload: dict) -> dict:
    values = dict(payload)
    values["receipt_id"] = stable_id(
        "contradiction_resolution_evidence_receipt",
        {key: value for key, value in values.items() if key != "receipt_id"},
    )
    return values


def _claim(
    kernel: VerdantKernel,
    *,
    event_key: str,
    polarity: ClaimPolarity,
    source: ClaimSourceClass,
    subject: str = "door",
) -> None:
    ClaimLearningPipeline().record_claim(
        kernel,
        event_key=event_key,
        native_description=f"Controlled evidence {event_key}.",
        subject_label=subject,
        predicate="has_property",
        object_label="open",
        polarity=polarity,
        source_class=source,
    )


def _prepared(
    *,
    seed: int,
    affirmed_sources: tuple[ClaimSourceClass, ...] = (
        ClaimSourceClass.DIRECT_OBSERVATION,
    ),
    negated_sources: tuple[ClaimSourceClass, ...] = (
        ClaimSourceClass.HUMAN_TESTIMONY,
    ),
):
    kernel = VerdantKernel(
        seed=seed,
        state_dim=16,
        run_label=f"contradiction-probe-{seed}",
    )
    for index, source in enumerate(affirmed_sources):
        _claim(
            kernel,
            event_key=f"door-affirmed-{index}",
            polarity=ClaimPolarity.AFFIRMED,
            source=source,
        )
    for index, source in enumerate(negated_sources):
        _claim(
            kernel,
            event_key=f"door-negated-{index}",
            polarity=ClaimPolarity.NEGATED,
            source=source,
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
        source_event_key=f"contradiction-probe-attention-{seed}",
    ).decision.allocations[0]
    bundle = ContradictionHypothesisProtocol().generate(
        kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    return kernel, obligation, allocation, bundle


def test_matched_probe_derives_distinct_partition_from_real_traces() -> None:
    kernel, obligation, allocation, bundle = _prepared(seed=6401)
    runtime = CounterfactualRuntime()
    before = kernel.fingerprint()

    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:distinct",
    )

    assert kernel.fingerprint() == before
    assert run.observation.disposition == (
        ContradictionProvenanceDisposition.DISTINCT_SOURCE_PARTITION
    )
    assert run.observation.protected_claim_refs == obligation.claim_refs
    assert run.observation.protected_evidence_refs == (
        bundle.evidence_receipt.protected_evidence_refs
    )
    assert run.observation.matched_observation.added_record_refs == (
        f"structures:{run.probe.projection_id}",
    )
    assert len(runtime.ledger.state.reservations) == 2
    assert len(runtime.ledger.state.settlements) == 2
    assert sum(
        item.consumed_budget for item in runtime.ledger.state.settlements
    ) == pytest.approx(allocation.granted_budget)
    projection = run.probe.treatment_plan.patches[0].value
    assert projection is not None
    assert projection["evidence_receipt"] == (
        bundle.evidence_receipt.model_dump(mode="json")
    )
    assert set(projection["hypothesis_refs"]) == {
        item.hypothesis_id for item in bundle.hypotheses
    }
    assert not run.observation.truth_selection_authority_enabled
    assert not run.observation.observed_outcome_authority_enabled
    assert not run.observation.resolution_authority_enabled
    assert not run.observation.canonical_commit_permitted
    coverage = run.resolution_evidence
    assert coverage.hypothesis_bundle == bundle
    assert coverage.provenance_observation == run.observation
    assert coverage.grounded_requirements == CONTRADICTION_GROUNDED_REQUIREMENTS
    assert coverage.missing_requirements == CONTRADICTION_MISSING_REQUIREMENTS
    assert coverage.structural_added_refs == (
        f"structures:{run.probe.projection_id}",
    )
    assert not coverage.resolution_trial_ready
    assert not coverage.truth_selection_authority_enabled
    assert not coverage.observed_outcome_authority_enabled
    assert not coverage.resolution_authority_enabled
    assert not coverage.canonical_commit_permitted


@pytest.mark.parametrize(
    ("affirmed_sources", "negated_sources", "expected"),
    (
        (
            (ClaimSourceClass.DIRECT_OBSERVATION,),
            (ClaimSourceClass.DIRECT_OBSERVATION,),
            ContradictionProvenanceDisposition.VALID_NULL_SHARED_SOURCES,
        ),
        (
            (
                ClaimSourceClass.DIRECT_OBSERVATION,
                ClaimSourceClass.EXTERNAL_TESTIMONY,
            ),
            (ClaimSourceClass.DIRECT_OBSERVATION,),
            ContradictionProvenanceDisposition.INCONCLUSIVE_OVERLAPPING_SOURCES,
        ),
    ),
)
def test_probe_keeps_valid_null_and_overlap_inconclusive(
    affirmed_sources: tuple[ClaimSourceClass, ...],
    negated_sources: tuple[ClaimSourceClass, ...],
    expected: ContradictionProvenanceDisposition,
) -> None:
    seed = 6402 if len(affirmed_sources) == 1 else 6403
    kernel, _, _, bundle = _prepared(
        seed=seed,
        affirmed_sources=affirmed_sources,
        negated_sources=negated_sources,
    )
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        CounterfactualRuntime(),
        bundle=bundle,
        source_event_key=f"contradiction-probe:{expected.value}",
    )

    assert run.observation.disposition == expected
    assert run.observation.evidence_preserved
    assert run.resolution_evidence.provenance_disposition == expected
    assert not run.resolution_evidence.resolution_trial_ready
    if expected == ContradictionProvenanceDisposition.VALID_NULL_SHARED_SOURCES:
        assert not run.observation.symmetric_difference_source_roots
    else:
        assert run.observation.shared_support_source_roots
        assert run.observation.symmetric_difference_source_roots


def test_archive_replay_rebuilds_identical_probe_and_observation(
    tmp_path: Path,
) -> None:
    kernel, obligation, allocation, bundle = _prepared(seed=6404)
    runtime = CounterfactualRuntime()
    runner = ContradictionProvenanceProbeRunner()
    first = runner.run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:archive-replay",
    )
    path = tmp_path / "contradiction-probe.vob"
    save_experiment_archive(path, kernel, runtime.ledger)

    restored_kernel, restored_ledger = load_experiment_archive(path)
    restored_bundle = ContradictionHypothesisProtocol().generate(
        restored_kernel,
        obligation_id=obligation.kernel_id,
        attention_allocation_id=allocation.allocation_id,
    )
    restored_runtime = CounterfactualRuntime(restored_ledger)
    canonical_before = restored_kernel.fingerprint()
    ledger_before = restored_ledger.fingerprint()
    replay = runner.run(
        restored_kernel,
        restored_runtime,
        bundle=restored_bundle,
        source_event_key="contradiction-probe:archive-replay",
    )

    assert replay.replayed
    assert replay.probe == first.probe
    assert replay.observation == first.observation
    assert replay.resolution_evidence == first.resolution_evidence
    assert restored_kernel.fingerprint() == canonical_before
    assert restored_ledger.fingerprint() == ledger_before


def test_coverage_deriver_reconstructs_exact_receipt_without_mutation() -> None:
    kernel, _, _, bundle = _prepared(seed=6412)
    runtime = CounterfactualRuntime()
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:coverage-derive",
    )
    canonical_before = kernel.fingerprint()
    ledger_before = runtime.ledger.fingerprint()

    rebuilt = ContradictionResolutionEvidenceDeriver().derive(
        kernel,
        runtime.ledger,
        hypothesis_bundle=bundle,
        baseline_result=run.baseline,
        treatment_result=run.treatment,
        provenance_observation=run.observation,
    )

    assert rebuilt == run.resolution_evidence
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == ledger_before


def test_coverage_deriver_rejects_foreign_simulation_ledger() -> None:
    kernel, _, _, bundle = _prepared(seed=6413)
    runtime = CounterfactualRuntime()
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:coverage-foreign-ledger",
    )
    foreign = CounterfactualRuntime().ledger
    foreign_before = foreign.fingerprint()

    with pytest.raises(
        ContradictionResolutionEvidenceIntegrityError,
        match="foreign or altered simulation record",
    ):
        ContradictionResolutionEvidenceDeriver().derive(
            kernel,
            foreign,
            hypothesis_bundle=bundle,
            baseline_result=run.baseline,
            treatment_result=run.treatment,
            provenance_observation=run.observation,
        )
    assert foreign.fingerprint() == foreign_before


def test_coverage_deriver_rejects_mismatched_bundle_and_observation() -> None:
    kernel, _, _, bundle = _prepared(seed=6414)
    runtime = CounterfactualRuntime()
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:coverage-mismatch",
    )
    _, _, _, foreign_bundle = _prepared(seed=6415)
    canonical_before = kernel.fingerprint()
    ledger_before = runtime.ledger.fingerprint()

    with pytest.raises(ContradictionResolutionEvidenceIntegrityError):
        ContradictionResolutionEvidenceDeriver().derive(
            kernel,
            runtime.ledger,
            hypothesis_bundle=foreign_bundle,
            baseline_result=run.baseline,
            treatment_result=run.treatment,
            provenance_observation=run.observation,
        )
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == ledger_before


def test_fully_rehashed_coverage_cannot_suppress_protected_evidence() -> None:
    kernel, _, _, bundle = _prepared(seed=6416)
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        CounterfactualRuntime(),
        bundle=bundle,
        source_event_key="contradiction-probe:coverage-suppression",
    )
    payload = run.resolution_evidence.model_dump(mode="json")
    payload["protected_evidence_refs"] = payload["protected_evidence_refs"][:-1]

    with pytest.raises(ValueError, match="suppressed or altered"):
        ContradictionResolutionEvidenceReceipt.model_validate(
            _rehash_resolution_evidence(payload)
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    (
        ("missing_requirements", (), "missing coverage was hidden or altered"),
        (
            "resolution_trial_ready",
            True,
            "cannot claim truth, outcome, or resolution",
        ),
        (
            "resolution_authority_enabled",
            True,
            "cannot claim truth, outcome, or resolution",
        ),
    ),
)
def test_fully_rehashed_coverage_cannot_hide_gaps_or_grant_authority(
    field: str,
    value: object,
    match: str,
) -> None:
    kernel, _, _, bundle = _prepared(seed=6417)
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        CounterfactualRuntime(),
        bundle=bundle,
        source_event_key="contradiction-probe:coverage-authority",
    )
    payload = run.resolution_evidence.model_dump(mode="json")
    payload[field] = value

    with pytest.raises(ValueError, match=match):
        ContradictionResolutionEvidenceReceipt.model_validate(
            _rehash_resolution_evidence(payload)
        )


def test_coverage_accounts_for_every_requirement_exactly_once() -> None:
    covered = set(CONTRADICTION_GROUNDED_REQUIREMENTS)
    missing = set(CONTRADICTION_MISSING_REQUIREMENTS)

    assert covered.isdisjoint(missing)
    assert covered | missing == set(ContradictionResolutionRequirement)


def test_observer_rejects_replaced_runtime_trace() -> None:
    kernel, _, _, bundle = _prepared(seed=6405)
    runtime = CounterfactualRuntime()
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:trace-tamper",
    )
    forged_trace = run.treatment.trace.model_copy(
        update={"result_refs": ("forged-result",)}
    )
    forged_result = replace(run.treatment, trace=forged_trace)
    before = runtime.ledger.fingerprint()

    with pytest.raises(
        ContradictionProvenanceProbeIntegrityError,
        match="actual ledger records",
    ):
        ContradictionProvenanceProbeObserver().observe(
            kernel,
            runtime.ledger,
            bundle=bundle,
            probe=run.probe,
            baseline_result=run.baseline,
            treatment_result=forged_result,
        )
    assert runtime.ledger.fingerprint() == before


def test_observer_rejects_foreign_simulation_ledger() -> None:
    kernel, _, _, bundle = _prepared(seed=6411)
    runtime = CounterfactualRuntime()
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        runtime,
        bundle=bundle,
        source_event_key="contradiction-probe:foreign-ledger",
    )
    foreign = CounterfactualRuntime().ledger
    foreign_before = foreign.fingerprint()

    with pytest.raises(
        ContradictionProvenanceProbeIntegrityError,
        match="foreign or altered simulation record",
    ):
        ContradictionProvenanceProbeObserver().observe(
            kernel,
            foreign,
            bundle=bundle,
            probe=run.probe,
            baseline_result=run.baseline,
            treatment_result=run.treatment,
        )
    assert foreign.fingerprint() == foreign_before


def test_fully_rehashed_projection_cannot_suppress_receipt_evidence() -> None:
    kernel, _, _, bundle = _prepared(seed=6406)
    probe = ContradictionProvenanceProbe.build(
        bundle, source_event_key="contradiction-probe:suppression"
    )
    value = dict(probe.treatment_plan.patches[0].value or {})
    value["protected_evidence_refs"] = value["protected_evidence_refs"][:-1]
    forged_patch = CounterfactualPatch.upsert(
        "structures", probe.projection_id, value
    )
    plan = probe.treatment_plan
    forged_treatment = CounterfactualPlan.build(
        source_event_key=plan.source_event_key,
        operator_version=plan.operator_version,
        requested_budget=plan.requested_budget,
        consumed_budget=plan.consumed_budget,
        patches=(forged_patch,),
        apply_patch_count=1,
        disposition=plan.disposition,
        result_refs=plan.result_refs,
    )
    payload = probe.model_dump(mode="json")
    payload["treatment_plan"] = forged_treatment.model_dump(mode="json")

    with pytest.raises(ValueError, match="lost exact probe controls"):
        ContradictionProvenanceProbe.model_validate(payload)
    assert kernel.state.structures.get(probe.projection_id) is None


def test_stale_bundle_fails_before_any_simulation_is_published() -> None:
    kernel, _, _, bundle = _prepared(seed=6407)
    _claim(
        kernel,
        event_key="door-affirmed-new-source",
        polarity=ClaimPolarity.AFFIRMED,
        source=ClaimSourceClass.EXTERNAL_TESTIMONY,
    )
    ContradictionObligationDetector().detect_and_record(kernel)
    runtime = CounterfactualRuntime()
    before = runtime.ledger.fingerprint()

    with pytest.raises(
        ContradictionProvenanceProbeIntegrityError,
        match="stale relative to contradiction history",
    ):
        ContradictionProvenanceProbeRunner().run(
            kernel,
            runtime,
            bundle=bundle,
            source_event_key="contradiction-probe:stale",
        )
    assert runtime.ledger.fingerprint() == before


def test_second_arm_failure_rolls_back_staged_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel, _, _, bundle = _prepared(seed=6408)
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    ledger_before = runtime.ledger.fingerprint()
    original_execute = CounterfactualRuntime.execute
    calls = 0

    def fail_second(self, candidate_kernel, *, allocation_id, plan):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise SimulationIntegrityError("injected treatment failure")
        return original_execute(
            self,
            candidate_kernel,
            allocation_id=allocation_id,
            plan=plan,
        )

    monkeypatch.setattr(CounterfactualRuntime, "execute", fail_second)
    with pytest.raises(
        ContradictionProvenanceProbeIntegrityError,
        match="injected treatment failure",
    ):
        ContradictionProvenanceProbeRunner().run(
            kernel,
            runtime,
            bundle=bundle,
            source_event_key="contradiction-probe:atomic-failure",
        )
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == ledger_before


def test_partial_budget_exhaustion_cannot_publish_one_probe_arm() -> None:
    kernel, _, allocation, bundle = _prepared(seed=6409)
    runtime = CounterfactualRuntime()
    preexisting = CounterfactualPlan.build(
        source_event_key="contradiction-probe:preexisting",
        operator_version="preexisting_simulation_v1",
        requested_budget=0.01,
        consumed_budget=0.01,
        patches=(),
        apply_patch_count=0,
        disposition=SimulationDisposition.DISCARDED,
        result_refs=("preexisting",),
    )
    runtime.execute(
        kernel,
        allocation_id=allocation.allocation_id,
        plan=preexisting,
    )
    before = runtime.ledger.fingerprint()

    with pytest.raises(
        ContradictionProvenanceProbeIntegrityError,
        match="exceeds an attention allocation",
    ):
        ContradictionProvenanceProbeRunner().run(
            kernel,
            runtime,
            bundle=bundle,
            source_event_key="contradiction-probe:budget-rollback",
        )
    assert runtime.ledger.fingerprint() == before


def test_observation_authority_tampering_is_rejected() -> None:
    kernel, _, _, bundle = _prepared(seed=6410)
    run = ContradictionProvenanceProbeRunner().run(
        kernel,
        CounterfactualRuntime(),
        bundle=bundle,
        source_event_key="contradiction-probe:authority",
    )
    payload = run.observation.model_dump(mode="json")
    payload["truth_selection_authority_enabled"] = True

    with pytest.raises(ValueError, match="authority boundary"):
        ContradictionProvenanceObservation.model_validate(payload)
