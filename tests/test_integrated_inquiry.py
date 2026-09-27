from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import verdant_obligations.inquiry as inquiry_module
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
)
from verdant_obligations import (
    AttentionPortfolio,
    AttentionPortfolioPolicy,
    CounterfactualPatch,
    CounterfactualRuntime,
    DependencyGapInquiryCoordinator,
    DependencyGapPipeline,
    HypothesisOperator,
    IntegratedInquiryError,
    IntegratedInquiryPolicy,
    IntegratedInquiryTrace,
    MatchedCounterfactualObserver,
    MatchedCounterfactualPlans,
    OutcomeKind,
    StructuralTraceEffect,
    experiment_archive_bytes,
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


def _kernel() -> VerdantKernel:
    kernel = VerdantKernel(seed=7401, state_dim=16, run_label="integrated-inquiry")
    kernel.apply_experience(
        _experience(
            "integrated-dependency",
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
            "integrated-route",
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
            "integrated-grounding",
            labels=("grounded reading",),
            evidence_kind=EvidenceKind.OUTCOME,
        )
    )
    return kernel


def test_opt_in_path_links_detection_attention_hypotheses_and_simulation() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    before = kernel.fingerprint()

    result = DependencyGapInquiryCoordinator().run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:001",
    )

    assert not result.replayed
    assert kernel.fingerprint() != before
    assert result.trace.canonical_checkpoint_fingerprint == kernel.fingerprint()
    assert result.trace.simulation_ledger_fingerprint == runtime.ledger.fingerprint()
    assert len(result.detection.candidates) == 1
    assert len(result.attention.decision.allocations) == 1
    assert len(result.simulations) == len(result.plans) == len(result.trace.trials) == 3
    assert len(result.matched_pairs) == 1
    matched = result.matched_pairs[0]
    assert result.trace.matched_observations == (matched.observation,)
    assert matched.obligation_id == result.detection.mutations[0].obligation.kernel_id
    assert matched.hypothesis_id == matched.observation.hypothesis_ref
    assert matched.observation.effect == StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
    assert matched.observation.canonical_records_preserved
    assert matched.observation.baseline.result_refs == (matched.hypothesis_id,)
    assert matched.observation.treatment.result_refs == (matched.hypothesis_id,)
    assert len(runtime.ledger.state.reservations) == 5
    assert len(runtime.ledger.state.settlements) == 5
    assert {item.operator for item in result.hypotheses} == {
        HypothesisOperator.EVIDENCE_PATH_PROJECTION,
        HypothesisOperator.NULL_ARTIFACT,
        HypothesisOperator.DEFER_INSUFFICIENT_EVIDENCE,
    }

    outcomes = {
        outcome.outcome_id: outcome
        for hypothesis in result.hypotheses
        for outcome in hypothesis.outcomes
    }
    hypotheses = {item.hypothesis_id: item for item in result.hypotheses}
    trials_by_settlement = {
        item.settlement_id: item for item in result.trace.trials
    }
    assert {outcomes[item.outcome_id].kind for item in result.trace.trials} == {
        OutcomeKind.PATH_COMPLETES,
        OutcomeKind.PATH_STALLS,
        OutcomeKind.PATH_CONFLICTS,
    }
    for simulation in result.simulations:
        trial = trials_by_settlement[simulation.settlement.settlement_id]
        outcome = outcomes[trial.outcome_id]
        hypothesis = hypotheses[trial.hypothesis_id]
        assert outcome.hypothesis_id == hypothesis.hypothesis_id
        assert simulation.reservation.attention_decision_id == (
            result.attention.decision.decision_id
        )
        assert simulation.settlement.canonical_unchanged
        assert not simulation.settlement.canonical_commit_permitted
        assert not simulation.settlement.epistemic_authority_enabled
        assert set(simulation.settlement.result_refs) == {
            hypothesis.hypothesis_id,
            outcome.outcome_id,
            outcome.equivalence_signature,
        }

    completion_trial = next(
        item
        for item in result.trace.trials
        if outcomes[item.outcome_id].kind == OutcomeKind.PATH_COMPLETES
    )
    completion_hypothesis = hypotheses[completion_trial.hypothesis_id]
    assert completion_hypothesis.patches
    assert completion_hypothesis.patches[0].record_key not in kernel.state.relations

    bid = result.attention.decision.bids[0]
    assert bid.requested_budget == pytest.approx(0.05)
    assert set(bid.metric_provenance_refs) >= {
        result.detection.candidates[0].candidate_id,
        result.detection.mutations[0].event.event_id,
        result.partitions[0].partition_id,
        *(item.hypothesis_id for item in result.hypotheses),
    }
    assert not result.trace.canonical_simulation_leakage_detected
    assert not result.trace.canonical_resolution_permitted
    assert not result.trace.epistemic_authority_enabled


def test_trace_reconstructs_exactly_after_archive_reload(tmp_path: Path) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    coordinator = DependencyGapInquiryCoordinator()
    first = coordinator.run(
        kernel,
        runtime,
        source_event_key="integrated-inquiry:replay",
    )
    path = tmp_path / "integrated.vob"
    expected_archive = experiment_archive_bytes(kernel, runtime.ledger)
    save_experiment_archive(path, kernel, runtime.ledger)
    assert path.read_bytes() == expected_archive

    restored_kernel, restored_ledger = load_experiment_archive(path)
    restored_runtime = CounterfactualRuntime(ledger=restored_ledger)
    canonical_before = restored_kernel.fingerprint()
    simulation_before = restored_runtime.ledger.fingerprint()

    replay = DependencyGapInquiryCoordinator().run(
        restored_kernel,
        restored_runtime,
        source_event_key="integrated-inquiry:replay",
    )

    assert replay.replayed
    assert replay.trace == first.trace
    assert replay.plans == first.plans
    assert tuple(item.plans for item in replay.matched_pairs) == tuple(
        item.plans for item in first.matched_pairs
    )
    assert tuple(item.observation for item in replay.matched_pairs) == tuple(
        item.observation for item in first.matched_pairs
    )
    assert tuple(
        (item.baseline.reservation, item.treatment.reservation)
        for item in replay.matched_pairs
    ) == tuple(
        (item.baseline.reservation, item.treatment.reservation)
        for item in first.matched_pairs
    )
    assert tuple(
        (item.baseline.settlement, item.treatment.settlement)
        for item in replay.matched_pairs
    ) == tuple(
        (item.baseline.settlement, item.treatment.settlement)
        for item in first.matched_pairs
    )
    assert all(item.replayed for item in replay.matched_pairs)
    assert tuple(item.reservation for item in replay.simulations) == tuple(
        item.reservation for item in first.simulations
    )
    assert tuple(item.settlement for item in replay.simulations) == tuple(
        item.settlement for item in first.simulations
    )
    assert restored_kernel.fingerprint() == canonical_before
    assert restored_runtime.ledger.fingerprint() == simulation_before


def test_allocation_must_fund_matched_pair_and_one_labeled_arm() -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    attention = AttentionPortfolio(
        AttentionPortfolioPolicy(micro_probe_budget=0.02)
    )

    with pytest.raises(IntegratedInquiryError, match="matched control pair"):
        DependencyGapInquiryCoordinator(attention=attention).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:underfunded-match",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_matched_receipt_tamper_rejects_entire_staged_transaction() -> None:
    class TamperingObserver:
        def observe(self, *args, **kwargs):
            receipt = MatchedCounterfactualObserver().observe(*args, **kwargs)
            return receipt.model_copy(
                update={"canonical_records_preserved": False}
            )

    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(
        IntegratedInquiryError,
        match="Matched structural observation failed validation",
    ):
        DependencyGapInquiryCoordinator(
            matched_observer=TamperingObserver()
        ).run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:tampered-match",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_matched_plan_cannot_substitute_a_foreign_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_builder = inquiry_module.build_matched_counterfactual_plans

    def forged_builder(hypothesis, **kwargs):
        plans = real_builder(hypothesis, **kwargs)
        foreign_patch = CounterfactualPatch.upsert(
            "relations",
            "forged-foreign-relation",
            {"counterfactual": True, "forged": True},
        )
        return MatchedCounterfactualPlans(
            baseline=plans.baseline.model_copy(
                update={"patches": (foreign_patch,)}
            ),
            treatment=plans.treatment.model_copy(
                update={"patches": (foreign_patch,)}
            ),
        )

    monkeypatch.setattr(
        inquiry_module,
        "build_matched_counterfactual_plans",
        forged_builder,
    )
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="declared hypothesis"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:foreign-matched-patch",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_missing_projected_intervention_rejects_without_partial_writes() -> None:
    kernel = VerdantKernel(
        seed=7402,
        state_dim=16,
        run_label="integrated-inquiry-no-route",
    )
    kernel.apply_experience(
        _experience(
            "integrated-dependency-no-route",
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
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="patch-bearing"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:no-projected-path",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_unrelated_eligible_obligation_rejects_transaction_without_partial_writes() -> None:
    kernel = _kernel()
    DependencyGapPipeline().observe_gap(
        kernel,
        target_action_node="action:external",
        missing_input_signature="input:external",
        trigger_relation="requires",
        triggering_refs=("action:external", "input:external"),
        source_event_key="external-gap",
        context_snapshot_hash="external-context",
    )
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()

    with pytest.raises(IntegratedInquiryError, match="exactly the eligible"):
        DependencyGapInquiryCoordinator().run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:incomplete-set",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_detected_simulation_leak_is_not_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kernel = _kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    simulation_before = runtime.ledger.fingerprint()
    real_execute = CounterfactualRuntime.execute

    def leaking_execute(self, staged_kernel, **kwargs):
        result = real_execute(self, staged_kernel, **kwargs)
        staged_kernel.state.cycle += 1
        return result

    monkeypatch.setattr(CounterfactualRuntime, "execute", leaking_execute)
    coordinator = DependencyGapInquiryCoordinator(
        policy=IntegratedInquiryPolicy(maximum_simulations_per_obligation=1)
    )

    with pytest.raises(IntegratedInquiryError, match="changed canonical state"):
        coordinator.run(
            kernel,
            runtime,
            source_event_key="integrated-inquiry:leak",
        )

    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() == simulation_before


def test_rehashed_trace_cannot_drop_internal_provenance() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:tamper",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["detection_candidate_ids"] = ("dependency_gap_candidate_forged",)

    with pytest.raises(ValueError, match="lost its detector candidate"):
        IntegratedInquiryTrace.build(**payload)


def test_rehashed_trace_cannot_drop_matched_receipt() -> None:
    result = DependencyGapInquiryCoordinator().run(
        _kernel(),
        CounterfactualRuntime(),
        source_event_key="integrated-inquiry:drop-match",
    )
    payload = result.trace.model_dump(mode="python", exclude={"trace_id"})
    payload["matched_observations"] = ()

    with pytest.raises(ValueError):
        IntegratedInquiryTrace.build(**payload)
