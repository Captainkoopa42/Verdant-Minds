from __future__ import annotations

import pytest

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    CounterfactualLeakError,
    CounterfactualOverlay,
    CounterfactualPatch,
    CounterfactualPlan,
    CounterfactualRuntime,
    DependencyGapPipeline,
    SimulationDisposition,
    SimulationIntegrityError,
    SimulationLedger,
)


def _allocated_kernel() -> tuple[VerdantKernel, str, str]:
    kernel = VerdantKernel(seed=5401, state_dim=16, run_label="counterfactual")
    obligation = DependencyGapPipeline().observe_gap(
        kernel,
        target_action_node="action:stabilize-loop",
        missing_input_signature="input:pressure-reading",
        trigger_relation="requires",
        triggering_refs=("action:stabilize-loop", "input:pressure-reading"),
        source_event_key="gap:counterfactual",
        context_snapshot_hash="context:counterfactual",
    ).obligation
    decision = AttentionPortfolio().decide(
        kernel,
        (
            AttentionBidInput(
                obligation_id=obligation.kernel_id,
                action_operator="bounded_counterfactual_probe",
                requested_budget=0.05,
                estimated_cost=0.05,
                expected_gain=0.7,
                uncertainty=0.8,
                urgency=0.6,
                novelty=0.9,
                generator_version="test-generator-v1",
            ),
        ),
        source_event_key="attention:counterfactual",
    ).decision
    assert len(decision.allocations) == 1
    return kernel, obligation.kernel_id, decision.allocations[0].allocation_id


def _plan(
    key: str,
    *,
    requested: float = 0.02,
    consumed: float = 0.01,
    disposition: SimulationDisposition = SimulationDisposition.DISCARDED,
    apply_patch_count: int | None = None,
    value: int = 1,
) -> CounterfactualPlan:
    return CounterfactualPlan.build(
        source_event_key=key,
        operator_version="test-overlay-operator-v1",
        requested_budget=requested,
        consumed_budget=consumed,
        patches=(
            CounterfactualPatch.upsert(
                "concepts",
                f"hypothesis:{key}",
                {"hypothetical": True, "value": value},
            ),
            CounterfactualPatch.delete(
                "obligation_kernels",
                "never-delete-canonical",
            ),
        ),
        apply_patch_count=apply_patch_count,
        disposition=disposition,
        termination_code=(
            None if disposition == SimulationDisposition.DISCARDED
            else f"injected_{disposition.value}"
        ),
        result_refs=(f"result:{key}",),
    )


def test_overlay_is_read_through_copy_on_write() -> None:
    kernel, obligation_id, _ = _allocated_kernel()
    before = kernel.fingerprint()
    overlay = CounterfactualOverlay(kernel)

    canonical_record = overlay.read("obligation_kernels", obligation_id)
    assert canonical_record is not None
    canonical_record["target_action_node"] = "tampered-return-value"
    assert kernel.state.obligation_kernels[obligation_id].target_action_node == (
        "action:stabilize-loop"
    )

    replacement = CounterfactualPatch.upsert(
        "obligation_kernels",
        obligation_id,
        {"counterfactual_replacement": True},
    )
    overlay.apply(replacement)
    overlay.apply(CounterfactualPatch.delete("obligation_kernels", obligation_id))

    assert overlay.read("obligation_kernels", obligation_id) is None
    assert obligation_id in kernel.state.obligation_kernels
    assert kernel.fingerprint() == before
    assert overlay.fingerprint() != before

    with pytest.raises(ValueError, match="collection is not authorized"):
        CounterfactualPatch.upsert(
            "transitions",
            "hypothesis:forbidden",
            {"would_escape_overlay_boundary": True},
        )


def test_runtime_uses_canonical_allocation_but_only_simulation_ledger_changes() -> None:
    kernel, _, allocation_id = _allocated_kernel()
    runtime = CounterfactualRuntime()
    canonical_before = kernel.fingerprint()
    ledger_before = runtime.ledger.fingerprint()

    result = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=_plan("simulation:isolated"),
    )

    assert not result.replayed
    assert kernel.fingerprint() == canonical_before
    assert runtime.ledger.fingerprint() != ledger_before
    assert result.settlement.canonical_unchanged
    assert not result.settlement.canonical_commit_permitted
    assert not result.settlement.epistemic_authority_enabled
    assert len(result.settlement.applied_patch_ids) == 2
    assert "hypothesis:simulation:isolated" not in kernel.state.concepts

    ledger_fingerprint = runtime.ledger.fingerprint()
    with pytest.raises(SimulationIntegrityError, match="attention allocation"):
        runtime.execute(
            kernel,
            allocation_id="allocation:missing",
            plan=_plan("simulation:no-allocation"),
        )
    assert runtime.ledger.fingerprint() == ledger_fingerprint
    assert kernel.fingerprint() == canonical_before

    decision, allocation = runtime._allocation(kernel, allocation_id)
    forged = allocation.model_copy(update={"granted_budget": 1.0})
    with pytest.raises(SimulationIntegrityError, match="non-canonical attention allocation"):
        runtime.ledger.reserve(
            kernel=kernel,
            decision=decision,
            allocation=forged,
            plan=_plan("simulation:forged-allocation"),
        )


def test_simulation_replay_is_zero_cost_and_changed_request_is_rejected() -> None:
    kernel, _, allocation_id = _allocated_kernel()
    runtime = CounterfactualRuntime()
    plan = _plan("simulation:replay")
    first = runtime.execute(kernel, allocation_id=allocation_id, plan=plan)
    ledger_fingerprint = runtime.ledger.fingerprint()

    replay = runtime.execute(kernel, allocation_id=allocation_id, plan=plan)

    assert replay.replayed
    assert replay.reservation == first.reservation
    assert replay.settlement == first.settlement
    assert runtime.ledger.fingerprint() == ledger_fingerprint

    with pytest.raises(SimulationIntegrityError, match="different request"):
        runtime.execute(
            kernel,
            allocation_id=allocation_id,
            plan=_plan("simulation:replay", value=2),
        )
    assert runtime.ledger.fingerprint() == ledger_fingerprint


def test_budget_is_cumulative_and_survives_separate_ledger_reload() -> None:
    kernel, _, allocation_id = _allocated_kernel()
    runtime = CounterfactualRuntime()
    runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=_plan("simulation:budget-a", requested=0.04, consumed=0.03),
    )
    ledger_before_rejection = runtime.ledger.fingerprint()

    with pytest.raises(ValueError, match="exceeds an attention allocation"):
        runtime.execute(
            kernel,
            allocation_id=allocation_id,
            plan=_plan("simulation:budget-too-large", requested=0.03, consumed=0.01),
        )
    assert runtime.ledger.fingerprint() == ledger_before_rejection

    runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=_plan("simulation:budget-b", requested=0.02, consumed=0.02),
    )
    restored = SimulationLedger.from_state(runtime.ledger.snapshot())

    assert restored.snapshot() == runtime.ledger.snapshot()
    assert restored.fingerprint() == runtime.ledger.fingerprint()
    assert sum(item.consumed_budget for item in restored.state.settlements) == pytest.approx(
        0.05
    )


def test_cancelled_and_failed_runs_charge_only_declared_consumption() -> None:
    kernel, _, allocation_id = _allocated_kernel()
    runtime = CounterfactualRuntime()
    cancelled = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=_plan(
            "simulation:cancelled",
            requested=0.02,
            consumed=0.01,
            disposition=SimulationDisposition.CANCELLED,
            apply_patch_count=0,
        ),
    )
    failed = runtime.execute(
        kernel,
        allocation_id=allocation_id,
        plan=_plan(
            "simulation:failed",
            requested=0.04,
            consumed=0.02,
            disposition=SimulationDisposition.FAILED,
            apply_patch_count=1,
        ),
    )

    assert cancelled.settlement.disposition == SimulationDisposition.CANCELLED
    assert cancelled.settlement.applied_patch_ids == ()
    assert failed.settlement.disposition == SimulationDisposition.FAILED
    assert len(failed.settlement.applied_patch_ids) == 1
    assert sum(
        item.consumed_budget for item in runtime.ledger.state.settlements
    ) == pytest.approx(0.03)


def test_leak_detection_refuses_settlement_after_canonical_mutation() -> None:
    kernel, _, allocation_id = _allocated_kernel()
    runtime = CounterfactualRuntime()
    decision, allocation = runtime._allocation(kernel, allocation_id)
    plan = _plan("simulation:leak-check", apply_patch_count=1)
    reservation, _ = runtime.ledger.reserve(
        kernel=kernel,
        decision=decision,
        allocation=allocation,
        plan=plan,
    )
    overlay = CounterfactualOverlay(kernel)
    overlay.apply(plan.patches[0])

    DependencyGapPipeline().observe_gap(
        kernel,
        target_action_node="action:external-mutation",
        missing_input_signature="input:external-mutation",
        trigger_relation="requires",
        triggering_refs=("action:external-mutation", "input:external-mutation"),
        source_event_key="gap:external-mutation",
        context_snapshot_hash="context:external-mutation",
    )

    with pytest.raises(CounterfactualLeakError, match="Canonical state changed"):
        runtime.ledger.settle(
            reservation=reservation,
            plan=plan,
            overlay=overlay,
            kernel=kernel,
        )
    assert runtime.ledger.state.settlements == ()


def test_paired_checkpoints_keep_future_canonical_behavior_identical(tmp_path) -> None:
    source, _, allocation_id = _allocated_kernel()
    checkpoint = tmp_path / "counterfactual-paired.vdk"
    save_checkpoint(checkpoint, source.snapshot())
    control = VerdantKernel.from_state(load_checkpoint(checkpoint))
    simulated = VerdantKernel.from_state(load_checkpoint(checkpoint))
    runtime = CounterfactualRuntime()

    assert control.fingerprint() == simulated.fingerprint()
    for index in range(100):
        disposition = (
            SimulationDisposition.FAILED
            if index % 11 == 0
            else SimulationDisposition.CANCELLED
            if index % 7 == 0
            else SimulationDisposition.DISCARDED
        )
        runtime.execute(
            simulated,
            allocation_id=allocation_id,
            plan=_plan(
                f"simulation:paired:{index:03d}",
                requested=0.0005,
                consumed=0.0001,
                disposition=disposition,
                apply_patch_count=index % 3 if disposition != SimulationDisposition.DISCARDED else 2,
                value=index,
            ),
        )

    assert simulated.fingerprint() == control.fingerprint()
    assert len(runtime.ledger.state.settlements) == 100
    assert sum(
        item.consumed_budget for item in runtime.ledger.state.settlements
    ) == pytest.approx(0.01)

    for kernel in (control, simulated):
        DependencyGapPipeline().observe_gap(
            kernel,
            target_action_node="action:future-identical",
            missing_input_signature="input:future-identical",
            trigger_relation="requires",
            triggering_refs=("action:future-identical", "input:future-identical"),
            source_event_key="gap:future-identical",
            context_snapshot_hash="context:future-identical",
        )

    assert simulated.fingerprint() == control.fingerprint()
    assert simulated.state.obligation_history == control.state.obligation_history
