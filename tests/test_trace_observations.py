from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualPatch,
    CounterfactualPlan,
    CounterfactualRunResult,
    CounterfactualRuntime,
    DependencyGapDetector,
    DependencyGapHypothesisGenerator,
    MatchedCounterfactualObserver,
    SimulationDisposition,
    StructuralTraceEffect,
    TraceObservationIntegrityError,
    build_matched_counterfactual_plans,
    load_experiment_archive,
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


def _fixture():
    kernel = VerdantKernel(seed=7501, state_dim=16, run_label="trace-observer")
    kernel.apply_experience(
        _experience(
            "trace-dependency",
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
            "trace-route",
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
            "trace-grounding",
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
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="matched_trace_observation",
                requested_budget=0.05,
                estimated_cost=0.02,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.5,
                novelty=0.8,
                metric_provenance_refs=hypothesis.provenance_refs,
                generator_version=hypothesis.grammar_version,
            ),
        ),
        source_event_key="attention:matched-trace-observation",
    ).decision
    return kernel, hypothesis, decision.allocations[0].allocation_id


def _execute_projected_pair(kernel, hypothesis, allocation_id, runtime, *, key):
    plans = build_matched_counterfactual_plans(
        hypothesis,
        source_event_key=key,
        requested_budget=0.02,
        consumed_budget=0.01,
    )
    baseline = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=plans.baseline,
    )
    treatment = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=plans.treatment,
    )
    observation = MatchedCounterfactualObserver().observe(
        kernel,
        runtime.ledger,
        hypothesis_ref=hypothesis.hypothesis_id,
        baseline_plan=plans.baseline,
        baseline_result=baseline,
        treatment_plan=plans.treatment,
        treatment_result=treatment,
    )
    return plans, baseline, treatment, observation


def _manual_pair(
    *,
    key: str,
    hypothesis_ref: str,
    patch: CounterfactualPatch,
):
    common = {
        "operator_version": "matched-trace-adversarial-v1",
        "requested_budget": 0.02,
        "consumed_budget": 0.01,
        "patches": (patch,),
        "disposition": SimulationDisposition.DISCARDED,
        "result_refs": (hypothesis_ref,),
    }
    return (
        CounterfactualPlan.build(
            source_event_key=f"{key}:baseline",
            apply_patch_count=0,
            **common,
        ),
        CounterfactualPlan.build(
            source_event_key=f"{key}:treatment",
            apply_patch_count=1,
            **common,
        ),
    )


def test_matched_actual_traces_derive_additive_effect_without_outcome_label() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()

    _, baseline, treatment, observation = _execute_projected_pair(
        kernel,
        hypothesis,
        allocation_id,
        runtime,
        key="matched-trace:additive",
    )

    assert kernel.fingerprint() == canonical_before
    assert baseline.trace.match_signature == treatment.trace.match_signature
    assert all(
        item.before_sha256 == item.after_sha256
        for item in baseline.trace.collection_deltas
    )
    assert observation.effect == StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
    assert observation.added_record_refs == (
        f"relations:{hypothesis.patches[0].record_key}",
    )
    assert observation.canonical_records_preserved
    assert observation.baseline.result_refs == (hypothesis.hypothesis_id,)
    assert observation.treatment.result_refs == (hypothesis.hypothesis_id,)
    assert not observation.observed_outcome_authority_enabled
    assert not observation.resolution_authority_enabled
    assert not observation.canonical_commit_permitted


def test_matched_trace_observation_replays_exactly_after_archive_reload(
    tmp_path: Path,
) -> None:
    kernel, hypothesis, allocation_id = _fixture()
    runtime = CounterfactualRuntime()
    plans, _, _, first = _execute_projected_pair(
        kernel,
        hypothesis,
        allocation_id,
        runtime,
        key="matched-trace:archive-replay",
    )
    path = tmp_path / "matched-trace.vob"
    save_experiment_archive(path, kernel, runtime.ledger)

    restored_kernel, restored_ledger = load_experiment_archive(path)
    restored_runtime = CounterfactualRuntime(restored_ledger)
    restored_hypothesis = next(
        item
        for item in DependencyGapHypothesisGenerator().generate(
            restored_kernel, hypothesis.obligation_id
        )
        if item.patches
    )
    restored_plans = build_matched_counterfactual_plans(
        restored_hypothesis,
        source_event_key="matched-trace:archive-replay",
        requested_budget=0.02,
        consumed_budget=0.01,
    )
    assert restored_hypothesis == hypothesis
    assert restored_plans == plans
    canonical_before = restored_kernel.fingerprint()
    ledger_before = restored_runtime.ledger.fingerprint()
    baseline = restored_runtime.execute(
        restored_kernel,
        allocation_id=allocation_id,
        plan=restored_plans.baseline,
    )
    treatment = restored_runtime.execute(
        restored_kernel,
        allocation_id=allocation_id,
        plan=restored_plans.treatment,
    )
    replay = MatchedCounterfactualObserver().observe(
        restored_kernel,
        restored_runtime.ledger,
        hypothesis_ref=restored_hypothesis.hypothesis_id,
        baseline_plan=restored_plans.baseline,
        baseline_result=baseline,
        treatment_plan=restored_plans.treatment,
        treatment_result=treatment,
    )

    assert baseline.replayed and treatment.replayed
    assert replay == first
    assert restored_kernel.fingerprint() == canonical_before
    assert restored_runtime.ledger.fingerprint() == ledger_before


def test_mismatched_actual_controls_are_rejected() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    runtime = CounterfactualRuntime()
    plans = build_matched_counterfactual_plans(
        hypothesis,
        source_event_key="matched-trace:mismatch",
        requested_budget=0.02,
        consumed_budget=0.01,
    )
    mismatched_treatment = CounterfactualPlan.build(
        source_event_key=plans.treatment.source_event_key,
        operator_version=plans.treatment.operator_version,
        requested_budget=plans.treatment.requested_budget,
        consumed_budget=0.009,
        patches=plans.treatment.patches,
        apply_patch_count=plans.treatment.apply_patch_count,
        disposition=plans.treatment.disposition,
        result_refs=plans.treatment.result_refs,
    )
    baseline = runtime.execute(
        kernel, allocation_id=allocation_id, plan=plans.baseline
    )
    treatment = runtime.execute(
        kernel, allocation_id=allocation_id, plan=mismatched_treatment
    )

    with pytest.raises(TraceObservationIntegrityError, match="controls differ"):
        MatchedCounterfactualObserver().observe(
            kernel,
            runtime.ledger,
            hypothesis_ref=hypothesis.hypothesis_id,
            baseline_plan=plans.baseline,
            baseline_result=baseline,
            treatment_plan=mismatched_treatment,
            treatment_result=treatment,
        )


def test_rehashed_or_replaced_runtime_trace_is_recomputed_from_ledger() -> None:
    kernel, hypothesis, allocation_id = _fixture()
    runtime = CounterfactualRuntime()
    plans = build_matched_counterfactual_plans(
        hypothesis,
        source_event_key="matched-trace:tamper",
        requested_budget=0.02,
        consumed_budget=0.01,
    )
    baseline = runtime.execute(
        kernel, allocation_id=allocation_id, plan=plans.baseline
    )
    treatment = runtime.execute(
        kernel, allocation_id=allocation_id, plan=plans.treatment
    )
    tampered_trace = treatment.trace.model_copy(
        update={"result_refs": ("forged-result",)}
    )
    tampered_result = replace(treatment, trace=tampered_trace)

    with pytest.raises(TraceObservationIntegrityError, match="actual ledger records"):
        MatchedCounterfactualObserver().observe(
            kernel,
            runtime.ledger,
            hypothesis_ref=hypothesis.hypothesis_id,
            baseline_plan=plans.baseline,
            baseline_result=baseline,
            treatment_plan=plans.treatment,
            treatment_result=tampered_result,
        )


@pytest.mark.parametrize("same_value", [False, True])
def test_trace_derived_preservation_distinguishes_mutation_from_valid_null(
    same_value: bool,
) -> None:
    kernel, _, allocation_id = _fixture()
    runtime = CounterfactualRuntime()
    relation = next(iter(kernel.state.relations.values()))
    patch = (
        CounterfactualPatch.upsert(
            "relations",
            relation.relation_id,
            relation.model_dump(mode="json"),
        )
        if same_value
        else CounterfactualPatch.delete("relations", relation.relation_id)
    )
    hypothesis_ref = f"matched-trace:{'null' if same_value else 'mutation'}"
    baseline_plan, treatment_plan = _manual_pair(
        key=hypothesis_ref,
        hypothesis_ref=hypothesis_ref,
        patch=patch,
    )
    canonical_before = kernel.fingerprint()
    baseline = runtime.execute(
        kernel, allocation_id=allocation_id, plan=baseline_plan
    )
    treatment = runtime.execute(
        kernel, allocation_id=allocation_id, plan=treatment_plan
    )
    observation = MatchedCounterfactualObserver().observe(
        kernel,
        runtime.ledger,
        hypothesis_ref=hypothesis_ref,
        baseline_plan=baseline_plan,
        baseline_result=baseline,
        treatment_plan=treatment_plan,
        treatment_result=treatment,
    )

    assert kernel.fingerprint() == canonical_before
    if same_value:
        assert observation.effect == StructuralTraceEffect.NO_STRUCTURAL_EFFECT
        assert observation.canonical_records_preserved
        assert not observation.added_record_refs
        assert not observation.removed_record_refs
        assert not observation.changed_record_refs
    else:
        assert observation.effect == StructuralTraceEffect.CANONICAL_RECORD_MUTATION
        assert not observation.canonical_records_preserved
        assert observation.removed_record_refs == (
            f"relations:{relation.relation_id}",
        )
