from __future__ import annotations

import pytest

from verdant_kernel import (
    DependencyCutEdge,
    DependencyGraphDelta,
    ExhaustedAttemptSignature,
    KernelInvariantError,
    ObligationAttempt,
    ObligationAttemptAttribution,
    ObligationBudgetState,
    ObligationStatus,
    ReopenCondition,
    ReopenPredicate,
    StallCause,
    StallCauseExpression,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_obligations import DependencyGapPipeline, derive_obligation_view


def _created(kernel: VerdantKernel, pipeline: DependencyGapPipeline):
    return pipeline.observe_gap(
        kernel,
        target_action_node="action:regulate-pressure",
        missing_input_signature="PressureReading",
        trigger_relation="requires",
        triggering_refs=("action:regulate-pressure", "type:PressureReading"),
        source_event_key="gap-detected-001",
        context_snapshot_hash="context-a",
        source_lineage_roots=("sensor-lineage-a",),
    )


def _attempt() -> ObligationAttempt:
    signature = ExhaustedAttemptSignature.build(
        projection_hash="projection-pressure-v1",
        equivalence_lens_version="dependency-lens-v0",
        horizon=2,
        operator_version="isomorphic-projection-v0",
        admissibility_policy_version="admissibility-v0",
        outcome_hash="outcome-null-a",
    )
    return ObligationAttempt.build(
        action_operator="isomorphic_projection",
        target_lens="dependency-lens-v0",
        signature=signature,
        budget=ObligationBudgetState(requested=1.0, granted=0.5, consumed=0.5),
        result_attribution=ObligationAttemptAttribution.VALID_NULL,
    )


def _stall(
    kernel: VerdantKernel,
    pipeline: DependencyGapPipeline,
    obligation_id: str,
    *,
    condition: ReopenCondition | None = None,
    exhausted_roots: tuple[str, ...] = ("sensor-lineage-a",),
):
    pipeline.record_attempt(
        kernel,
        obligation_id,
        attempt=_attempt(),
        source_event_key="attempt-001",
        policy_version="attention-portfolio-v0",
    )
    cut = DependencyCutEdge.build(
        "action:regulate-pressure",
        "requires",
        "evidence:pressure-reading",
    )
    condition = condition or ReopenCondition.atom(
        ReopenPredicate.CROSSES_DEPENDENCY_CUT
    )
    return pipeline.stall(
        kernel,
        obligation_id,
        source_event_key="stall-001",
        stall_cause_expression=StallCauseExpression.atom(
            StallCause.ALL_ATTEMPTS_EQUIVALENT
        ),
        bounded_subgraph_hash="bounded-pressure-subgraph-v1",
        reopen_condition=condition,
        unresolved_evidence_frontier=("action:regulate-pressure",),
        reachable_partition_refs=("action:regulate-pressure",),
        evidence_partition_refs=("evidence:pressure-reading",),
        dependency_cut_set=(cut,),
        exhausted_lineage_roots=exhausted_roots,
        active_lens_and_policy_versions=(
            "attention-portfolio-v0",
            "dependency-lens-v0",
        ),
    )


def test_obligation_identity_deduplicates_replay_and_accumulates_retriggers():
    kernel = VerdantKernel(seed=5101, state_dim=16, run_label="obligation-identity")
    pipeline = DependencyGapPipeline()
    first = _created(kernel, pipeline)
    fingerprint = kernel.fingerprint()

    replay = _created(kernel, pipeline)
    retrigger = pipeline.observe_gap(
        kernel,
        target_action_node="action:regulate-pressure",
        missing_input_signature="PressureReading",
        trigger_relation="requires",
        triggering_refs=("action:regulate-pressure", "type:PressureReading"),
        source_event_key="gap-detected-002",
        context_snapshot_hash="context-b",
        source_lineage_roots=("sensor-lineage-a",),
    )

    assert replay.replayed
    assert kernel.fingerprint() != fingerprint
    assert retrigger.obligation.kernel_id == first.obligation.kernel_id
    assert len(kernel.state.obligation_kernels) == 1
    assert [item.event_type.value for item in kernel.state.obligation_history] == [
        "Created",
        "Retriggered",
    ]


def test_tripartite_view_rebuilds_identically_after_checkpoint(tmp_path):
    kernel = VerdantKernel(seed=5102, state_dim=16, run_label="obligation-checkpoint")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    _stall(kernel, pipeline, obligation_id)
    before = derive_obligation_view(kernel, obligation_id)

    checkpoint = tmp_path / "obligation.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))
    after = derive_obligation_view(restored, obligation_id)

    assert before == after
    assert before.fingerprint() == after.fingerprint()
    assert after.current_status == ObligationStatus.STALLED
    assert after.active_stall_certificate is not None
    assert "obligation_view" not in restored.state.model_fields_set
    assert restored.fingerprint() == kernel.fingerprint()


def test_irrelevant_delta_costs_no_canonical_cycle_but_remote_cut_crossing_wakes():
    kernel = VerdantKernel(seed=5103, state_dim=16, run_label="obligation-wake")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    _stall(kernel, pipeline, obligation_id)
    cycle = kernel.state.cycle
    fingerprint = kernel.fingerprint()

    irrelevant = DependencyGraphDelta.build(
        "graph-delta-irrelevant",
        changed_edges=(DependencyCutEdge.build("remote:x", "links", "remote:y"),),
    )
    assert pipeline.note_delta(kernel, obligation_id, irrelevant) is None
    assert kernel.state.cycle == cycle
    assert kernel.fingerprint() == fingerprint

    remote_but_causal = DependencyGraphDelta.build(
        "graph-delta-causal",
        changed_edges=(DependencyCutEdge.build(
            "action:regulate-pressure",
            "new-bridge",
            "evidence:pressure-reading",
        ),),
    )
    pipeline.note_delta(kernel, obligation_id, remote_but_causal)
    assert derive_obligation_view(kernel, obligation_id).current_status == ObligationStatus.MAY_WAKE


def test_wake_storm_collapses_to_one_canonical_wake_event():
    kernel = VerdantKernel(seed=5104, state_dim=16, run_label="obligation-storm")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    _stall(kernel, pipeline, obligation_id)
    edge = DependencyCutEdge.build(
        "action:regulate-pressure", "requires", "evidence:pressure-reading"
    )
    first = DependencyGraphDelta.build("storm-00000", changed_edges=(edge,))
    assert pipeline.note_delta(kernel, obligation_id, first) is not None
    cycle = kernel.state.cycle
    history_size = len(kernel.state.obligation_history)

    for index in range(1, 500):
        delta = DependencyGraphDelta.build(
            f"storm-{index:05d}",
            changed_edges=(edge,),
        )
        assert pipeline.note_delta(kernel, obligation_id, delta) is None

    assert kernel.state.cycle == cycle
    assert len(kernel.state.obligation_history) == history_size


def test_multicausal_stall_supersedes_only_the_satisfied_reopen_condition():
    kernel = VerdantKernel(seed=5105, state_dim=16, run_label="obligation-multicausal")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    condition = ReopenCondition.all_of(
        ReopenCondition.atom(ReopenPredicate.CROSSES_DEPENDENCY_CUT),
        ReopenCondition.atom(ReopenPredicate.HAS_NEW_LINEAGE_ROOT),
    )
    _stall(kernel, pipeline, obligation_id, condition=condition)
    original = derive_obligation_view(kernel, obligation_id).active_stall_certificate
    assert original is not None

    cut_only = DependencyGraphDelta.build(
        "multi-cut-only",
        changed_edges=(DependencyCutEdge.build(
            "action:regulate-pressure", "requires", "evidence:pressure-reading"
        ),),
        lineage_roots=("sensor-lineage-a",),
    )
    pipeline.note_delta(kernel, obligation_id, cut_only)
    pipeline.allocate_recheck(
        kernel,
        obligation_id,
        source_event_key="multi-allocate-1",
        granted_budget=0.1,
        policy_version="attention-portfolio-v0",
    )
    pipeline.complete_recheck(
        kernel,
        obligation_id,
        source_event_key="multi-result-1",
    )
    stalled = derive_obligation_view(kernel, obligation_id)
    assert stalled.current_status == ObligationStatus.STALLED
    assert stalled.active_stall_certificate is not None
    assert stalled.active_stall_certificate.supersedes_certificate_id == original.certificate_id
    assert stalled.reopen_criteria == ReopenCondition.atom(
        ReopenPredicate.HAS_NEW_LINEAGE_ROOT
    )

    new_root = DependencyGraphDelta.build(
        "multi-new-root",
        lineage_roots=("sensor-lineage-b",),
    )
    pipeline.note_delta(kernel, obligation_id, new_root)
    pipeline.allocate_recheck(
        kernel,
        obligation_id,
        source_event_key="multi-allocate-2",
        granted_budget=0.1,
        policy_version="attention-portfolio-v0",
    )
    pipeline.complete_recheck(
        kernel,
        obligation_id,
        source_event_key="multi-result-2",
    )
    assert derive_obligation_view(kernel, obligation_id).current_status == ObligationStatus.REOPENED
    final_view = derive_obligation_view(kernel, obligation_id)
    assert final_view.active_stall_certificate is None
    assert final_view.reopen_criteria is None
    assert final_view.budget_accounting.requested == pytest.approx(1.2)
    assert final_view.budget_accounting.granted == pytest.approx(0.7)
    assert final_view.budget_accounting.consumed == pytest.approx(0.7)


def test_source_laundering_and_budget_only_novelty_do_not_wake():
    kernel = VerdantKernel(seed=5106, state_dim=16, run_label="obligation-source")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    condition = ReopenCondition.atom(ReopenPredicate.HAS_NEW_LINEAGE_ROOT)
    _stall(kernel, pipeline, obligation_id, condition=condition)
    fingerprint = kernel.fingerprint()

    laundered = DependencyGraphDelta.build(
        "laundered-source",
        lineage_roots=("sensor-lineage-a",),
    )
    renewed_budget = DependencyGraphDelta.build(
        "budget-only",
        budget_renewed=True,
    )
    assert pipeline.note_delta(kernel, obligation_id, laundered) is None
    assert pipeline.note_delta(kernel, obligation_id, renewed_budget) is None
    assert kernel.fingerprint() == fingerprint


def test_audit_ping_only_wakes_and_requires_an_independent_evaluator_change():
    kernel = VerdantKernel(seed=5108, state_dim=16, run_label="obligation-audit")
    pipeline = DependencyGapPipeline()
    obligation_id = _created(kernel, pipeline).obligation.kernel_id
    condition = ReopenCondition.atom(
        ReopenPredicate.HAS_NEW_EVALUATOR_VERSION
    )
    _stall(kernel, pipeline, obligation_id, condition=condition)

    audit_only = DependencyGraphDelta.build(
        "audit-without-version-change",
        audit_ping=True,
    )
    pipeline.note_delta(kernel, obligation_id, audit_only)
    pipeline.allocate_recheck(
        kernel,
        obligation_id,
        source_event_key="audit-allocate-1",
        granted_budget=0.05,
        policy_version="attention-portfolio-v0",
    )
    pipeline.complete_recheck(
        kernel,
        obligation_id,
        source_event_key="audit-result-1",
    )
    assert derive_obligation_view(kernel, obligation_id).current_status == ObligationStatus.STALLED

    upgraded = DependencyGraphDelta.build(
        "audit-with-version-change",
        evaluator_versions=("dependency-lens-v1",),
        audit_ping=True,
    )
    pipeline.note_delta(kernel, obligation_id, upgraded)
    pipeline.allocate_recheck(
        kernel,
        obligation_id,
        source_event_key="audit-allocate-2",
        granted_budget=0.05,
        policy_version="attention-portfolio-v0",
    )
    pipeline.complete_recheck(
        kernel,
        obligation_id,
        source_event_key="audit-result-2",
    )
    assert derive_obligation_view(kernel, obligation_id).current_status == ObligationStatus.REOPENED


def test_payload_tampering_breaks_canonical_history_validation():
    kernel = VerdantKernel(seed=5107, state_dim=16, run_label="obligation-tamper")
    pipeline = DependencyGapPipeline()
    _created(kernel, pipeline)
    tampered = kernel.snapshot()
    tampered.obligation_history[0] = tampered.obligation_history[0].model_copy(
        update={"policy_version": "silently-rewritten-policy"}
    )

    with pytest.raises(KernelInvariantError, match="checksum validation"):
        VerdantKernel.from_state(tampered)
