"""Bounded, accountable attention allocation for active obligations.

Attention is executive allocation, not epistemic authority.  The portfolio
records every eligible obligation, the explicit metric bid supplied for it,
the Pareto frontier, protected exploration spending, and every deferral.  It
does not execute a hypothesis, resolve an obligation, or alter graph meaning.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    ObligationAttentionAllocation,
    ObligationAttentionBid,
    ObligationAttentionDecisionRecord,
    ObligationAttentionLane,
    ObligationStatus,
    VerdantKernel,
)
from verdant_kernel.models import TransitionRecord, canonical_json_bytes, stable_id

from .pipeline import ObligationIntegrityError, derive_obligation_view


ATTENTION_PORTFOLIO_POLICY_VERSION = "obligation_attention_portfolio_v0.3"


class AttentionPortfolioPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = ATTENTION_PORTFOLIO_POLICY_VERSION
    total_budget: float = Field(default=0.50, gt=0.0)
    exploration_fraction: float = Field(default=0.20, gt=0.0, le=1.0)
    micro_probe_budget: float = Field(default=0.05, gt=0.0)
    maximum_grant: float = Field(default=0.20, gt=0.0)
    starvation_cycles: int = Field(default=8, ge=1)
    cooldown_cycles: int = Field(default=1, ge=0)
    maximum_allocations: int = Field(default=8, ge=1)

    @model_validator(mode="after")
    def validate_policy(self) -> "AttentionPortfolioPolicy":
        if not self.policy_version.strip():
            raise ValueError("Attention policy version cannot be empty.")
        if self.micro_probe_budget > self.maximum_grant + 1e-12:
            raise ValueError("Micro-probe budget cannot exceed the maximum grant.")
        if self.exploration_reserve + 1e-12 < self.micro_probe_budget:
            raise ValueError("Exploration reserve must fund at least one micro-probe.")
        return self

    @property
    def exploration_reserve(self) -> float:
        return self.total_budget * self.exploration_fraction


class AttentionBidInput(BaseModel):
    """Explicit metric proposal; v0.3 does not claim these metrics are learned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    obligation_id: str
    action_operator: str
    requested_budget: float = Field(gt=0.0)
    estimated_cost: float = Field(gt=0.0)
    expected_gain: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    metric_provenance_refs: tuple[str, ...] = ()
    generator_version: str

    @model_validator(mode="after")
    def validate_input(self) -> "AttentionBidInput":
        if not all(
            value.strip()
            for value in (
                self.obligation_id,
                self.action_operator,
                self.generator_version,
            )
        ):
            raise ValueError("Attention bid input identifiers cannot be empty.")
        if tuple(sorted(set(self.metric_provenance_refs))) != self.metric_provenance_refs:
            raise ValueError("Metric provenance refs must be sorted and unique.")
        return self


@dataclass(frozen=True)
class AttentionPortfolioResult:
    decision: ObligationAttentionDecisionRecord
    replayed: bool = False


def _dominates(left: ObligationAttentionBid, right: ObligationAttentionBid) -> bool:
    no_worse = (
        left.expected_gain >= right.expected_gain
        and left.uncertainty >= right.uncertainty
        and left.urgency >= right.urgency
        and left.novelty >= right.novelty
        and left.estimated_cost <= right.estimated_cost
    )
    strictly_better = (
        left.expected_gain > right.expected_gain
        or left.uncertainty > right.uncertainty
        or left.urgency > right.urgency
        or left.novelty > right.novelty
        or left.estimated_cost < right.estimated_cost
    )
    return no_worse and strictly_better


class AttentionPortfolio:
    ELIGIBLE_STATUSES = frozenset(
        {
            ObligationStatus.OPEN,
            ObligationStatus.INVESTIGATING,
            ObligationStatus.MAY_WAKE,
            ObligationStatus.REOPENED,
        }
    )

    def __init__(self, policy: AttentionPortfolioPolicy | None = None) -> None:
        self.policy = policy or AttentionPortfolioPolicy()

    @staticmethod
    def _request_sha256(
        inputs: tuple[AttentionBidInput, ...],
        policy: AttentionPortfolioPolicy,
    ) -> str:
        payload = {
            "policy": policy.model_dump(mode="json"),
            "bids": tuple(item.model_dump(mode="json") for item in inputs),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def _eligible_views(self, kernel: VerdantKernel):
        views = {
            obligation_id: derive_obligation_view(kernel, obligation_id)
            for obligation_id in sorted(kernel.state.obligation_kernels)
        }
        return {
            obligation_id: view
            for obligation_id, view in views.items()
            if view.current_status in self.ELIGIBLE_STATUSES
        }

    @staticmethod
    def _selection_history(kernel: VerdantKernel):
        counts: dict[str, int] = {}
        last_cycle: dict[str, int] = {}
        for decision in kernel.state.obligation_attention_decisions:
            for allocation in decision.allocations:
                counts[allocation.obligation_id] = (
                    counts.get(allocation.obligation_id, 0) + 1
                )
                last_cycle[allocation.obligation_id] = decision.cycle
        return counts, last_cycle

    def _build_bids(
        self,
        kernel: VerdantKernel,
        inputs: tuple[AttentionBidInput, ...],
    ) -> tuple[ObligationAttentionBid, ...]:
        eligible = self._eligible_views(kernel)
        by_obligation = {item.obligation_id: item for item in inputs}
        if len(by_obligation) != len(inputs):
            raise ObligationIntegrityError("Each obligation may submit only one attention bid.")
        if set(by_obligation) != set(eligible):
            missing = tuple(sorted(set(eligible) - set(by_obligation)))
            extra = tuple(sorted(set(by_obligation) - set(eligible)))
            raise ObligationIntegrityError(
                f"Attention bids must cover every eligible obligation; missing={missing}, extra={extra}."
            )
        bids = []
        for obligation_id in sorted(eligible):
            item = by_obligation[obligation_id]
            basis = eligible[obligation_id].last_event_id
            bids.append(
                ObligationAttentionBid.build(
                    obligation_id=obligation_id,
                    basis_event_id=basis,
                    action_operator=item.action_operator,
                    requested_budget=item.requested_budget,
                    estimated_cost=item.estimated_cost,
                    expected_gain=item.expected_gain,
                    uncertainty=item.uncertainty,
                    urgency=item.urgency,
                    novelty=item.novelty,
                    metric_provenance_refs=tuple(
                        sorted({basis, *item.metric_provenance_refs})
                    ),
                    generator_version=item.generator_version,
                )
            )
        return tuple(sorted(bids, key=lambda item: item.bid_id))

    @staticmethod
    def _frontier(bids: tuple[ObligationAttentionBid, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                bid.bid_id
                for bid in bids
                if not any(
                    other.bid_id != bid.bid_id and _dominates(other, bid)
                    for other in bids
                )
            )
        )

    def _allocations(
        self,
        kernel: VerdantKernel,
        bids: tuple[ObligationAttentionBid, ...],
        frontier_ids: tuple[str, ...],
    ) -> tuple[ObligationAttentionAllocation, ...]:
        counts, last_cycle = self._selection_history(kernel)
        frontier = set(frontier_ids)
        creation_cycle = {
            item.kernel_id: item.creation_cycle
            for item in kernel.state.obligation_kernels.values()
        }
        age = {
            bid.obligation_id: max(
                0,
                kernel.state.cycle
                - last_cycle.get(
                    bid.obligation_id,
                    creation_cycle[bid.obligation_id],
                ),
            )
            for bid in bids
        }
        selected: set[str] = set()
        allocations: list[ObligationAttentionAllocation] = []
        reserve_remaining = self.policy.exploration_reserve
        exploit_remaining = self.policy.total_budget - self.policy.exploration_reserve

        def grant(
            bid: ObligationAttentionBid,
            *,
            lane: ObligationAttentionLane,
            available: float,
            micro: bool,
            reason: str,
        ) -> float:
            if bid.bid_id in selected or len(allocations) >= self.policy.maximum_allocations:
                return 0.0
            target = (
                min(bid.requested_budget, self.policy.micro_probe_budget)
                if micro
                else min(bid.requested_budget, self.policy.maximum_grant)
            )
            if available + 1e-12 < target:
                return 0.0
            allocation = ObligationAttentionAllocation.build(
                bid_id=bid.bid_id,
                obligation_id=bid.obligation_id,
                granted_budget=target,
                lane=lane,
                frontier_member=bid.bid_id in frontier,
                starvation_age=age[bid.obligation_id],
                reason=reason,
            )
            allocations.append(allocation)
            selected.add(bid.bid_id)
            return target

        starved = sorted(
            (
                bid for bid in bids
                if age[bid.obligation_id] >= self.policy.starvation_cycles
            ),
            key=lambda bid: (
                -age[bid.obligation_id],
                counts.get(bid.obligation_id, 0),
                bid.bid_id,
            ),
        )
        for bid in starved:
            spent = grant(
                bid,
                lane=ObligationAttentionLane.STARVATION,
                available=reserve_remaining,
                micro=True,
                reason="bounded non-starvation micro-probe",
            )
            reserve_remaining -= spent

        exploratory = sorted(
            (bid for bid in bids if bid.bid_id not in selected),
            key=lambda bid: (
                bid.bid_id in frontier,
                counts.get(bid.obligation_id, 0),
                -bid.uncertainty,
                -bid.novelty,
                bid.bid_id,
            ),
        )
        for bid in exploratory:
            last = last_cycle.get(bid.obligation_id)
            if last is not None and kernel.state.cycle - last <= self.policy.cooldown_cycles:
                continue
            spent = grant(
                bid,
                lane=ObligationAttentionLane.EXPLORATION,
                available=reserve_remaining,
                micro=True,
                reason="protected exploration reserve",
            )
            reserve_remaining -= spent

        exploit = sorted(
            (
                bid for bid in bids
                if bid.bid_id in frontier and bid.bid_id not in selected
            ),
            key=lambda bid: (
                -bid.expected_gain,
                bid.estimated_cost,
                -bid.urgency,
                -bid.uncertainty,
                bid.bid_id,
            ),
        )
        for bid in exploit:
            last = last_cycle.get(bid.obligation_id)
            if last is not None and kernel.state.cycle - last <= self.policy.cooldown_cycles:
                continue
            spent = grant(
                bid,
                lane=ObligationAttentionLane.EXPLOITATION,
                available=exploit_remaining,
                micro=False,
                reason="Pareto-frontier competitive allocation",
            )
            exploit_remaining -= spent

        return tuple(sorted(allocations, key=lambda item: item.allocation_id))

    def decide(
        self,
        kernel: VerdantKernel,
        bid_inputs: tuple[AttentionBidInput, ...],
        *,
        source_event_key: str,
    ) -> AttentionPortfolioResult:
        inputs = tuple(sorted(bid_inputs, key=lambda item: item.obligation_id))
        request_sha256 = self._request_sha256(inputs, self.policy)
        prior = next(
            (
                item for item in kernel.state.obligation_attention_decisions
                if item.source_event_key == source_event_key
            ),
            None,
        )
        if prior is not None:
            if (
                prior.request_sha256 != request_sha256
                or prior.policy_version != self.policy.policy_version
            ):
                raise ObligationIntegrityError(
                    "Attention source event key was reused with a different request."
                )
            return AttentionPortfolioResult(prior, replayed=True)
        if not source_event_key.strip():
            raise ObligationIntegrityError("Attention decision requires a source event key.")

        bids = self._build_bids(kernel, inputs)
        if not bids:
            raise ObligationIntegrityError("Attention portfolio has no eligible obligations.")
        frontier = self._frontier(bids)
        allocations = self._allocations(kernel, bids, frontier)
        allocated = {item.bid_id for item in allocations}
        input_fingerprint = kernel.semantic_fingerprint()
        decision = ObligationAttentionDecisionRecord.build(
            source_event_key=source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            policy_version=self.policy.policy_version,
            request_sha256=request_sha256,
            input_fingerprint=input_fingerprint,
            total_budget=self.policy.total_budget,
            exploration_reserve=self.policy.exploration_reserve,
            eligible_obligation_ids=tuple(sorted(item.obligation_id for item in bids)),
            pareto_frontier_bid_ids=frontier,
            bids=bids,
            allocations=allocations,
            deferred_bid_ids=tuple(
                sorted(item.bid_id for item in bids if item.bid_id not in allocated)
            ),
        )

        state = kernel.snapshot()
        state.cycle = decision.cycle
        state.event_sequence = decision.committed_sequence
        state.obligation_attention_decisions.append(decision)
        output_fingerprint = state.fingerprint(include_transitions=False)
        transition = TransitionRecord(
            transition_id=stable_id(
                "transition",
                state.identity.kernel_id,
                state.event_sequence,
                "obligation_attention_decision",
                decision.payload_sha256,
                input_fingerprint,
                output_fingerprint,
            ),
            sequence=state.event_sequence,
            cycle=state.cycle,
            operation="obligation_attention_decision",
            command_hash=decision.payload_sha256,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            input_refs=tuple(
                sorted(
                    {
                        *(bid.basis_event_id for bid in bids),
                        *(ref for bid in bids for ref in bid.metric_provenance_refs),
                    }
                )
            ),
            output_refs=(
                decision.decision_id,
                *(item.allocation_id for item in allocations),
            ),
        )
        state.transitions.append(transition)
        validated = VerdantKernel.from_state(state)
        kernel.state = validated.state
        return AttentionPortfolioResult(
            kernel.state.obligation_attention_decisions[-1]
        )
