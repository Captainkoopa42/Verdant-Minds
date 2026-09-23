from __future__ import annotations

import pytest

from verdant_kernel import KernelInvariantError, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_obligations import (
    AttentionBidInput,
    AttentionPortfolio,
    AttentionPortfolioPolicy,
    DependencyGapPipeline,
    ObligationIntegrityError,
)


def _obligations(count: int = 3) -> tuple[VerdantKernel, tuple[str, ...]]:
    kernel = VerdantKernel(seed=5301, state_dim=16, run_label="attention-portfolio")
    pipeline = DependencyGapPipeline()
    ids = []
    for index in range(count):
        result = pipeline.observe_gap(
            kernel,
            target_action_node=f"action:{index}",
            missing_input_signature=f"input:{index}",
            trigger_relation="requires",
            triggering_refs=(f"action:{index}", f"input:{index}"),
            source_event_key=f"gap:{index}",
            context_snapshot_hash=f"context:{index}",
        )
        ids.append(result.obligation.kernel_id)
    return kernel, tuple(ids)


def _bids(ids: tuple[str, ...]) -> tuple[AttentionBidInput, ...]:
    metrics = (
        # Strong and cheap: should be on the Pareto frontier.
        (0.9, 0.8, 0.8, 0.7, 0.10),
        # Strictly dominated by the first bid.
        (0.3, 0.2, 0.2, 0.1, 0.20),
        # High uncertainty/novelty preserves a second frontier direction.
        (0.5, 1.0, 0.4, 1.0, 0.15),
    )
    return tuple(
        AttentionBidInput(
            obligation_id=obligation_id,
            action_operator="bounded_micro_probe",
            requested_budget=0.20,
            estimated_cost=cost,
            expected_gain=gain,
            uncertainty=uncertainty,
            urgency=urgency,
            novelty=novelty,
            generator_version="test-bid-generator-v1",
        )
        for obligation_id, (gain, uncertainty, urgency, novelty, cost)
        in zip(ids, metrics, strict=True)
    )


def test_portfolio_records_frontier_exploration_deferral_and_budget() -> None:
    kernel, ids = _obligations()
    portfolio = AttentionPortfolio()
    before = kernel.fingerprint()

    result = portfolio.decide(kernel, _bids(ids), source_event_key="attention:001")
    decision = result.decision

    assert not result.replayed
    assert kernel.fingerprint() != before
    assert kernel.state.obligation_attention_decisions == [decision]
    assert decision.epistemic_authority_enabled is False
    assert len(decision.pareto_frontier_bid_ids) == 2
    dominated = next(
        bid for bid in decision.bids if bid.obligation_id == ids[1]
    )
    assert dominated.bid_id not in decision.pareto_frontier_bid_ids
    assert any(
        allocation.bid_id == dominated.bid_id
        and allocation.lane.value == "exploration"
        for allocation in decision.allocations
    )
    assert sum(item.granted_budget for item in decision.allocations) <= 0.50
    assert set(decision.deferred_bid_ids) == {
        item.bid_id for item in decision.bids
    } - {item.bid_id for item in decision.allocations}


def test_every_eligible_obligation_requires_an_explicit_bid() -> None:
    kernel, ids = _obligations()
    with pytest.raises(ObligationIntegrityError, match="cover every eligible"):
        AttentionPortfolio().decide(
            kernel,
            _bids(ids)[:-1],
            source_event_key="attention:incomplete",
        )
    assert kernel.state.obligation_attention_decisions == []


def test_decision_replay_is_a_zero_cost_canonical_noop() -> None:
    kernel, ids = _obligations()
    portfolio = AttentionPortfolio()
    first = portfolio.decide(kernel, _bids(ids), source_event_key="attention:replay")
    fingerprint = kernel.fingerprint()
    cycle = kernel.state.cycle

    replay = portfolio.decide(kernel, _bids(ids), source_event_key="attention:replay")

    assert replay.replayed
    assert replay.decision == first.decision
    assert kernel.fingerprint() == fingerprint
    assert kernel.state.cycle == cycle
    assert len(kernel.state.obligation_attention_decisions) == 1


def test_reused_decision_key_with_changed_metrics_is_rejected() -> None:
    kernel, ids = _obligations()
    portfolio = AttentionPortfolio()
    portfolio.decide(kernel, _bids(ids), source_event_key="attention:conflict")
    changed = list(_bids(ids))
    changed[0] = changed[0].model_copy(update={"expected_gain": 0.1})

    with pytest.raises(ObligationIntegrityError, match="different request"):
        portfolio.decide(
            kernel,
            tuple(changed),
            source_event_key="attention:conflict",
        )


def test_starvation_lane_rotates_micro_probes_under_tiny_budget() -> None:
    kernel, ids = _obligations()
    portfolio = AttentionPortfolio(
        AttentionPortfolioPolicy(
            total_budget=0.05,
            exploration_fraction=1.0,
            micro_probe_budget=0.05,
            maximum_grant=0.05,
            starvation_cycles=1,
            cooldown_cycles=1,
            maximum_allocations=1,
        )
    )
    selected = []
    for index in range(3):
        result = portfolio.decide(
            kernel,
            _bids(ids),
            source_event_key=f"attention:rotation:{index}",
        )
        assert len(result.decision.allocations) == 1
        selected.append(result.decision.allocations[0].obligation_id)

    assert set(selected) == set(ids)
    assert all(
        decision.allocations[0].lane.value == "starvation"
        for decision in kernel.state.obligation_attention_decisions
    )


def test_attention_history_survives_checkpoint_and_tampering_is_detected(tmp_path) -> None:
    kernel, ids = _obligations()
    decision = AttentionPortfolio().decide(
        kernel,
        _bids(ids),
        source_event_key="attention:checkpoint",
    ).decision
    checkpoint = tmp_path / "attention.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(checkpoint))

    assert restored.fingerprint() == kernel.fingerprint()
    assert restored.state.obligation_attention_decisions == [decision]

    tampered = kernel.snapshot()
    tampered.obligation_attention_decisions[0] = decision.model_copy(
        update={"payload_sha256": "0" * 64}
    )
    with pytest.raises(KernelInvariantError, match="canonical transition"):
        VerdantKernel.from_state(tampered)
