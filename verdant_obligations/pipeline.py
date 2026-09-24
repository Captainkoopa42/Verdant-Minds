"""Experimental DependencyGap obligation substrate.

This module implements one deliberately narrow vertical slice: immutable
DependencyGap kernels, append-only canonical history, and a pure rebuildable
view.  It does not grant the scheduler automatic action authority and it does
not claim that a stall or a topological wake condition establishes meaning.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from verdant_kernel import VerdantKernel
from verdant_kernel.models import (
    ContradictionObligationKernel,
    DependencyCutEdge,
    DependencyGapObligationKernel,
    DependencyGapStallCertificate,
    DependencyGraphDelta,
    ExhaustedAttemptSignature,
    IdentityAmbiguityObligationKernel,
    ObligationAttempt,
    ObligationAuthority,
    ObligationBudgetState,
    ObligationEventType,
    ObligationFamily,
    ObligationHistoryEvent,
    ObligationStatus,
    PredictionFailureObligationKernel,
    PredicateOperator,
    ReopenCondition,
    ReopenPredicate,
    StallCauseExpression,
    TransitionRecord,
    canonical_json_bytes,
    stable_id,
)


DERIVATION_POLICY_VERSION = "dependency_gap_view_reducer_v0.1"
DETECTION_POLICY_VERSION = "dependency_gap_detector_contract_v0.1"


class ObligationIntegrityError(RuntimeError):
    pass


class ObligationTransitionError(ObligationIntegrityError):
    pass


class ObligationView(BaseModel):
    """Non-authoritative projection rebuilt solely from canonical history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    obligation_id: str
    family: ObligationFamily
    current_status: ObligationStatus
    budget_accounting: ObligationBudgetState
    exhausted_attempt_signatures: tuple[str, ...] = ()
    admissible_actions_blocked: tuple[str, ...] = ()
    active_stall_certificate: DependencyGapStallCertificate | None = None
    reopen_criteria: ReopenCondition | None = None
    last_event_id: str
    history_length: int = Field(ge=1)
    derivation_policy_version: str = DERIVATION_POLICY_VERSION

    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.model_dump(mode="json"))
        ).hexdigest()


@dataclass(frozen=True)
class ObligationMutationResult:
    obligation: (
        DependencyGapObligationKernel
        | ContradictionObligationKernel
        | PredictionFailureObligationKernel
        | IdentityAmbiguityObligationKernel
    )
    event: ObligationHistoryEvent
    replayed: bool = False


def _events_for(kernel: VerdantKernel, obligation_id: str) -> tuple[ObligationHistoryEvent, ...]:
    return tuple(
        event
        for event in kernel.state.obligation_history
        if event.obligation_id == obligation_id
    )


def derive_obligation_view(
    kernel: VerdantKernel,
    obligation_id: str,
) -> ObligationView:
    obligation = kernel.state.obligation_kernels.get(obligation_id)
    if obligation is None:
        raise ObligationIntegrityError("Unknown obligation kernel.")
    events = _events_for(kernel, obligation_id)
    if not events or events[0].event_type != ObligationEventType.CREATED:
        raise ObligationIntegrityError("Obligation history has no creation event.")

    status = ObligationStatus.OPEN
    active_stall: DependencyGapStallCertificate | None = None
    attempts: dict[str, ExhaustedAttemptSignature] = {}
    requested = granted = consumed = 0.0

    for event in events:
        if event.event_type == ObligationEventType.CREATED:
            status = ObligationStatus.OPEN
        elif event.event_type == ObligationEventType.RETRIGGERED:
            pass
        elif event.event_type == ObligationEventType.ATTEMPT_RECORDED:
            if status not in {
                ObligationStatus.OPEN,
                ObligationStatus.INVESTIGATING,
                ObligationStatus.REOPENED,
            }:
                raise ObligationTransitionError("Attempt recorded outside an active inquiry state.")
            if event.attempt is None:
                raise ObligationIntegrityError("Attempt event lost its typed attempt.")
            status = ObligationStatus.INVESTIGATING
            attempts[event.attempt.signature.signature_id] = event.attempt.signature
            requested += event.attempt.budget.requested
            granted += event.attempt.budget.granted
            consumed += event.attempt.budget.consumed
        elif event.event_type == ObligationEventType.STALLED:
            if status not in {ObligationStatus.OPEN, ObligationStatus.INVESTIGATING}:
                raise ObligationTransitionError("Stall recorded outside an investigable state.")
            active_stall = event.stall_certificate
            status = ObligationStatus.STALLED
        elif event.event_type == ObligationEventType.WAKE_CANDIDATE:
            if status == ObligationStatus.STALLED:
                status = ObligationStatus.MAY_WAKE
            elif status != ObligationStatus.MAY_WAKE:
                raise ObligationTransitionError("Wake candidate recorded outside a stalled state.")
        elif event.event_type == ObligationEventType.RECHECK_ALLOCATED:
            if status != ObligationStatus.MAY_WAKE:
                raise ObligationTransitionError("Recheck allocation requires MayWake.")
            status = ObligationStatus.RECHECK_PENDING
            requested += event.recheck_budget_granted or 0.0
            granted += event.recheck_budget_granted or 0.0
        elif event.event_type == ObligationEventType.RECHECK_NO_CHANGE:
            if status != ObligationStatus.RECHECK_PENDING:
                raise ObligationTransitionError("No-change recheck requires Recheck_Pending.")
            active_stall = event.stall_certificate
            consumed += event.recheck_budget_consumed or 0.0
            status = ObligationStatus.STALLED
        elif event.event_type == ObligationEventType.REOPENED:
            if status != ObligationStatus.RECHECK_PENDING:
                raise ObligationTransitionError("Reopening requires Recheck_Pending.")
            consumed += event.recheck_budget_consumed or 0.0
            active_stall = None
            status = ObligationStatus.REOPENED
        elif event.event_type == ObligationEventType.RESOLVED:
            if status not in {ObligationStatus.INVESTIGATING, ObligationStatus.REOPENED}:
                raise ObligationTransitionError("Resolution requires an active inquiry.")
            active_stall = None
            status = ObligationStatus.RESOLVED
        elif event.event_type == ObligationEventType.REVALIDATION_REQUIRED:
            if status != ObligationStatus.RESOLVED:
                raise ObligationTransitionError("Revalidation requires a resolved obligation.")
            status = ObligationStatus.REVALIDATION_REQUIRED

    if active_stall is not None:
        for signature in active_stall.exhausted_attempts:
            attempts[signature.signature_id] = signature
    exhausted = tuple(sorted(attempts))
    return ObligationView(
        obligation_id=obligation_id,
        family=obligation.family,
        current_status=status,
        budget_accounting=ObligationBudgetState(
            requested=requested,
            granted=granted,
            consumed=consumed,
        ),
        exhausted_attempt_signatures=exhausted,
        admissible_actions_blocked=exhausted,
        active_stall_certificate=active_stall,
        reopen_criteria=(active_stall.reopen_condition if active_stall else None),
        last_event_id=events[-1].event_id,
        history_length=len(events),
    )


def delta_crosses_dependency_cut(
    certificate: DependencyGapStallCertificate,
    delta: DependencyGraphDelta,
) -> bool:
    cut_edge_ids = {item.edge_id for item in certificate.dependency_cut_set}
    if any(item.edge_id in cut_edge_ids for item in delta.changed_edges):
        return True
    reachable = set(certificate.reachable_partition_refs)
    evidence = set(certificate.evidence_partition_refs)
    return any(
        (
            edge.source_node_ref in reachable
            and edge.target_node_ref in evidence
        )
        or (
            edge.source_node_ref in evidence
            and edge.target_node_ref in reachable
        )
        for edge in delta.changed_edges
    )


def evaluate_reopen_condition(
    condition: ReopenCondition,
    certificate: DependencyGapStallCertificate,
    delta: DependencyGraphDelta,
) -> bool:
    if condition.operator == PredicateOperator.ATOM:
        values = {
            ReopenPredicate.CROSSES_DEPENDENCY_CUT: delta_crosses_dependency_cut(
                certificate, delta
            ),
            ReopenPredicate.HAS_NEW_LINEAGE_ROOT: bool(
                set(delta.lineage_roots).difference(certificate.exhausted_lineage_roots)
            ),
            ReopenPredicate.HAS_NEW_EVALUATOR_VERSION: bool(
                set(delta.evaluator_versions).difference(
                    certificate.active_lens_and_policy_versions
                )
            ),
            ReopenPredicate.BUDGET_RENEWED: delta.budget_renewed,
        }
        return values[condition.predicate]
    results = tuple(
        evaluate_reopen_condition(item, certificate, delta)
        for item in condition.operands
    )
    if condition.operator == PredicateOperator.AND:
        return all(results)
    return any(results)


def _remaining_reopen_condition(
    condition: ReopenCondition,
    certificate: DependencyGapStallCertificate,
    delta: DependencyGraphDelta,
) -> ReopenCondition | None:
    """Return the unsatisfied remainder; ``None`` means the contract passed."""

    if condition.operator == PredicateOperator.ATOM:
        return None if evaluate_reopen_condition(condition, certificate, delta) else condition
    remaining = tuple(
        item
        for operand in condition.operands
        if (item := _remaining_reopen_condition(operand, certificate, delta)) is not None
    )
    if condition.operator == PredicateOperator.OR:
        if len(remaining) < len(condition.operands):
            return None
        return condition
    if not remaining:
        return None
    if len(remaining) == 1:
        return remaining[0]
    return ReopenCondition.all_of(*remaining)


def _has_reopen_signal(
    condition: ReopenCondition,
    certificate: DependencyGapStallCertificate,
    delta: DependencyGraphDelta,
) -> bool:
    if delta.audit_ping:
        return True
    if condition.operator == PredicateOperator.ATOM:
        return evaluate_reopen_condition(condition, certificate, delta)
    return any(
        _has_reopen_signal(item, certificate, delta)
        for item in condition.operands
    )


def _existing_source_event(
    kernel: VerdantKernel,
    obligation_id: str,
    source_event_key: str,
) -> ObligationHistoryEvent | None:
    return next(
        (
            event
            for event in _events_for(kernel, obligation_id)
            if event.source_event_key == source_event_key
        ),
        None,
    )


def _require_dependency_gap(
    obligation: (
        DependencyGapObligationKernel
        | ContradictionObligationKernel
        | PredictionFailureObligationKernel
        | IdentityAmbiguityObligationKernel
    ),
) -> DependencyGapObligationKernel:
    if not isinstance(obligation, DependencyGapObligationKernel):
        raise ObligationIntegrityError(
            "DependencyGap lifecycle operations cannot govern another family."
        )
    return obligation


def _commit(
    kernel: VerdantKernel,
    event: ObligationHistoryEvent,
    *,
    obligation: (
        DependencyGapObligationKernel
        | ContradictionObligationKernel
        | PredictionFailureObligationKernel
        | IdentityAmbiguityObligationKernel
        | None
    ) = None,
) -> ObligationHistoryEvent:
    state = kernel.snapshot()
    input_fingerprint = kernel.semantic_fingerprint()
    if event.cycle != state.cycle + 1 or event.committed_sequence != state.event_sequence + 1:
        raise ObligationIntegrityError("Obligation event was built against stale canonical state.")
    if obligation is not None:
        if obligation.kernel_id in state.obligation_kernels:
            raise ObligationIntegrityError("Obligation kernel already exists.")
        state.obligation_kernels[obligation.kernel_id] = obligation
    state.cycle = event.cycle
    state.event_sequence = event.committed_sequence
    state.obligation_history.append(event)
    output_fingerprint = state.fingerprint(include_transitions=False)
    transition = TransitionRecord(
        transition_id=stable_id(
            "transition",
            state.identity.kernel_id,
            state.event_sequence,
            f"obligation_{event.event_type.value}",
            event.payload_sha256,
            input_fingerprint,
            output_fingerprint,
        ),
        sequence=state.event_sequence,
        cycle=state.cycle,
        operation=f"obligation_{event.event_type.value}",
        command_hash=event.payload_sha256,
        input_fingerprint=input_fingerprint,
        output_fingerprint=output_fingerprint,
        input_refs=tuple(
            item
            for item in (event.previous_event_id, *event.basis_event_refs)
            if item is not None
        ),
        output_refs=(event.obligation_id, event.event_id),
    )
    state.transitions.append(transition)
    validated = VerdantKernel.from_state(state)
    kernel.state = validated.state
    return kernel.state.obligation_history[-1]


def record_detected_contradiction(
    kernel: VerdantKernel,
    *,
    obligation: ContradictionObligationKernel,
    triggering_refs: tuple[str, ...],
    source_event_key: str,
    context_snapshot_hash: str,
    source_lineage_roots: tuple[str, ...],
    policy_version: str,
) -> ObligationMutationResult:
    """Commit or retrigger one detector-authored contradiction anchor."""

    refs = tuple(sorted(set(triggering_refs)))
    roots = tuple(sorted(set(source_lineage_roots)))
    existing = kernel.state.obligation_kernels.get(obligation.kernel_id)
    if existing is not None and not isinstance(existing, ContradictionObligationKernel):
        raise ObligationIntegrityError("Contradiction identity collided with another family.")
    prior = _existing_source_event(kernel, obligation.kernel_id, source_event_key)
    if prior is not None:
        if (
            prior.triggering_refs != refs
            or prior.context_snapshot_hash != context_snapshot_hash
            or prior.source_lineage_roots != roots
            or prior.policy_version != policy_version
        ):
            raise ObligationIntegrityError(
                "Obligation source event key was reused with different evidence."
            )
        assert existing is not None
        return ObligationMutationResult(existing, prior, replayed=True)

    if existing is None:
        if obligation.creation_cycle != kernel.state.cycle + 1:
            raise ObligationIntegrityError("Contradiction obligation has a stale creation cycle.")
        event_type = ObligationEventType.CREATED
        previous = None
    else:
        event_type = ObligationEventType.RETRIGGERED
        previous = _events_for(kernel, obligation.kernel_id)[-1].event_id
    event = ObligationHistoryEvent.build(
        obligation_id=obligation.kernel_id,
        event_type=event_type,
        authority=ObligationAuthority.DETECTOR,
        source_event_key=source_event_key,
        cycle=kernel.state.cycle + 1,
        committed_sequence=kernel.state.event_sequence + 1,
        previous_event_id=previous,
        triggering_refs=refs,
        context_snapshot_hash=context_snapshot_hash,
        source_lineage_roots=roots,
        policy_version=policy_version,
    )
    committed = _commit(
        kernel,
        event,
        obligation=(obligation if existing is None else None),
    )
    return ObligationMutationResult(
        kernel.state.obligation_kernels[obligation.kernel_id], committed
    )


def record_detected_prediction_failure(
    kernel: VerdantKernel,
    *,
    obligation: PredictionFailureObligationKernel,
    triggering_refs: tuple[str, ...],
    source_event_key: str,
    context_snapshot_hash: str,
    source_lineage_roots: tuple[str, ...],
    policy_version: str,
) -> ObligationMutationResult:
    """Commit or replay one detector-authored prediction-failure anchor."""

    refs = tuple(sorted(set(triggering_refs)))
    roots = tuple(sorted(set(source_lineage_roots)))
    existing = kernel.state.obligation_kernels.get(obligation.kernel_id)
    if existing is not None and not isinstance(
        existing, PredictionFailureObligationKernel
    ):
        raise ObligationIntegrityError("Prediction identity collided with another family.")
    prior = _existing_source_event(kernel, obligation.kernel_id, source_event_key)
    if prior is not None:
        if (
            prior.triggering_refs != refs
            or prior.context_snapshot_hash != context_snapshot_hash
            or prior.source_lineage_roots != roots
            or prior.policy_version != policy_version
        ):
            raise ObligationIntegrityError(
                "Obligation source event key was reused with different evidence."
            )
        assert existing is not None
        return ObligationMutationResult(existing, prior, replayed=True)
    if existing is None:
        if obligation.creation_cycle != kernel.state.cycle + 1:
            raise ObligationIntegrityError("Prediction obligation has a stale creation cycle.")
        event_type = ObligationEventType.CREATED
        previous = None
    else:
        event_type = ObligationEventType.RETRIGGERED
        previous = _events_for(kernel, obligation.kernel_id)[-1].event_id
    event = ObligationHistoryEvent.build(
        obligation_id=obligation.kernel_id,
        event_type=event_type,
        authority=ObligationAuthority.DETECTOR,
        source_event_key=source_event_key,
        cycle=kernel.state.cycle + 1,
        committed_sequence=kernel.state.event_sequence + 1,
        previous_event_id=previous,
        triggering_refs=refs,
        context_snapshot_hash=context_snapshot_hash,
        source_lineage_roots=roots,
        policy_version=policy_version,
    )
    committed = _commit(
        kernel,
        event,
        obligation=(obligation if existing is None else None),
    )
    return ObligationMutationResult(
        kernel.state.obligation_kernels[obligation.kernel_id], committed
    )


def record_detected_identity_ambiguity(
    kernel: VerdantKernel,
    *,
    obligation: IdentityAmbiguityObligationKernel,
    triggering_refs: tuple[str, ...],
    source_event_key: str,
    context_snapshot_hash: str,
    source_lineage_roots: tuple[str, ...],
    policy_version: str,
) -> ObligationMutationResult:
    """Commit, retrigger, or replay one native identity ambiguity."""

    refs = tuple(sorted(set(triggering_refs)))
    roots = tuple(sorted(set(source_lineage_roots)))
    existing = kernel.state.obligation_kernels.get(obligation.kernel_id)
    if existing is not None and not isinstance(
        existing, IdentityAmbiguityObligationKernel
    ):
        raise ObligationIntegrityError("Identity ambiguity collided with another family.")
    prior = _existing_source_event(kernel, obligation.kernel_id, source_event_key)
    if prior is not None:
        if (
            prior.triggering_refs != refs
            or prior.context_snapshot_hash != context_snapshot_hash
            or prior.source_lineage_roots != roots
            or prior.policy_version != policy_version
        ):
            raise ObligationIntegrityError(
                "Obligation source event key was reused with different evidence."
            )
        assert existing is not None
        return ObligationMutationResult(existing, prior, replayed=True)
    if existing is None:
        if obligation.creation_cycle != kernel.state.cycle + 1:
            raise ObligationIntegrityError("Identity obligation has a stale creation cycle.")
        event_type = ObligationEventType.CREATED
        previous = None
    else:
        event_type = ObligationEventType.RETRIGGERED
        previous = _events_for(kernel, obligation.kernel_id)[-1].event_id
    event = ObligationHistoryEvent.build(
        obligation_id=obligation.kernel_id,
        event_type=event_type,
        authority=ObligationAuthority.DETECTOR,
        source_event_key=source_event_key,
        cycle=kernel.state.cycle + 1,
        committed_sequence=kernel.state.event_sequence + 1,
        previous_event_id=previous,
        triggering_refs=refs,
        context_snapshot_hash=context_snapshot_hash,
        source_lineage_roots=roots,
        policy_version=policy_version,
    )
    committed = _commit(
        kernel,
        event,
        obligation=(obligation if existing is None else None),
    )
    return ObligationMutationResult(
        kernel.state.obligation_kernels[obligation.kernel_id], committed
    )


class DependencyGapPipeline:
    """Explicit experimental authority boundary for DependencyGap history."""

    def observe_gap(
        self,
        kernel: VerdantKernel,
        *,
        target_action_node: str,
        missing_input_signature: str,
        trigger_relation: str,
        triggering_refs: tuple[str, ...],
        source_event_key: str,
        context_snapshot_hash: str,
        source_lineage_roots: tuple[str, ...] = (),
        scope_key: str | None = None,
        policy_version: str = DETECTION_POLICY_VERSION,
    ) -> ObligationMutationResult:
        refs = tuple(sorted(set(triggering_refs)))
        if not refs:
            raise ObligationIntegrityError("DependencyGap requires canonical triggering refs.")
        roots = tuple(sorted(set(source_lineage_roots)))
        scope = scope_key or stable_id(
            "dependency_gap_scope", target_action_node, missing_input_signature
        )
        obligation_id = stable_id(
            "obligation",
            "0.1",
            ObligationFamily.DEPENDENCY_GAP.value,
            target_action_node,
            missing_input_signature,
            trigger_relation,
            scope,
        )
        existing = kernel.state.obligation_kernels.get(obligation_id)
        prior = _existing_source_event(kernel, obligation_id, source_event_key)
        if prior is not None:
            if (
                prior.triggering_refs != refs
                or prior.context_snapshot_hash != context_snapshot_hash
                or prior.source_lineage_roots != roots
                or prior.policy_version != policy_version
            ):
                raise ObligationIntegrityError(
                    "Obligation source event key was reused with different evidence."
                )
            return ObligationMutationResult(existing, prior, replayed=True)

        cycle = kernel.state.cycle + 1
        sequence = kernel.state.event_sequence + 1
        if existing is None:
            obligation = DependencyGapObligationKernel(
                kernel_id=obligation_id,
                target_action_node=target_action_node,
                missing_input_signature=missing_input_signature,
                trigger_relation=trigger_relation,
                scope_key=scope,
                canonical_triggering_refs=refs,
                creation_cycle=cycle,
                policy_version=policy_version,
            )
            event_type = ObligationEventType.CREATED
            previous = None
        else:
            obligation = existing
            event_type = ObligationEventType.RETRIGGERED
            previous = _events_for(kernel, obligation_id)[-1].event_id
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=event_type,
            authority=ObligationAuthority.DETECTOR,
            source_event_key=source_event_key,
            cycle=cycle,
            committed_sequence=sequence,
            previous_event_id=previous,
            triggering_refs=refs,
            context_snapshot_hash=context_snapshot_hash,
            source_lineage_roots=roots,
            policy_version=policy_version,
        )
        committed = _commit(
            kernel,
            event,
            obligation=(obligation if existing is None else None),
        )
        return ObligationMutationResult(
            kernel.state.obligation_kernels[obligation_id],
            committed,
        )

    def record_attempt(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
        *,
        attempt: ObligationAttempt,
        source_event_key: str,
        policy_version: str,
    ) -> ObligationMutationResult:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        obligation = _require_dependency_gap(obligation)
        prior = _existing_source_event(kernel, obligation_id, source_event_key)
        if prior is not None:
            if prior.attempt != attempt or prior.policy_version != policy_version:
                raise ObligationIntegrityError("Attempt event key was reused with different data.")
            return ObligationMutationResult(obligation, prior, replayed=True)
        view = derive_obligation_view(kernel, obligation_id)
        if view.current_status not in {
            ObligationStatus.OPEN,
            ObligationStatus.INVESTIGATING,
            ObligationStatus.REOPENED,
        }:
            raise ObligationTransitionError("Cannot record an attempt in the current state.")
        previous = view.last_event_id
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=ObligationEventType.ATTEMPT_RECORDED,
            authority=ObligationAuthority.SCHEDULER,
            source_event_key=source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            previous_event_id=previous,
            attempt=attempt,
            basis_event_refs=(previous,),
            policy_version=policy_version,
        )
        return ObligationMutationResult(obligation, _commit(kernel, event))

    def stall(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
        *,
        source_event_key: str,
        stall_cause_expression: StallCauseExpression,
        bounded_subgraph_hash: str,
        reopen_condition: ReopenCondition,
        unresolved_evidence_frontier: tuple[str, ...] = (),
        reachable_partition_refs: tuple[str, ...] = (),
        evidence_partition_refs: tuple[str, ...] = (),
        dependency_cut_set: tuple[DependencyCutEdge, ...] = (),
        exhausted_lineage_roots: tuple[str, ...] = (),
        unavailable_input_operator_types: tuple[str, ...] = (),
        active_lens_and_policy_versions: tuple[str, ...] = (),
        governance_constraints: tuple[str, ...] = (),
        policy_version: str = DERIVATION_POLICY_VERSION,
    ) -> ObligationMutationResult:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        obligation = _require_dependency_gap(obligation)
        prior = _existing_source_event(kernel, obligation_id, source_event_key)
        if prior is not None:
            return ObligationMutationResult(obligation, prior, replayed=True)
        view = derive_obligation_view(kernel, obligation_id)
        if view.current_status not in {ObligationStatus.OPEN, ObligationStatus.INVESTIGATING}:
            raise ObligationTransitionError("Cannot stall an obligation in the current state.")
        history = _events_for(kernel, obligation_id)
        attempt_events = tuple(
            event for event in history
            if event.event_type == ObligationEventType.ATTEMPT_RECORDED
            and event.attempt is not None
        )
        basis = tuple(sorted(
            (event.event_id for event in attempt_events),
        )) or (view.last_event_id,)
        exhausted = tuple(sorted(
            (event.attempt.signature for event in attempt_events if event.attempt),
            key=lambda item: item.signature_id,
        ))
        certificate = DependencyGapStallCertificate.build(
            obligation_kernel_ref=obligation_id,
            cycle_issued=kernel.state.cycle + 1,
            stall_cause_expression=stall_cause_expression,
            unresolved_evidence_frontier=unresolved_evidence_frontier,
            bounded_subgraph_hash=bounded_subgraph_hash,
            reachable_partition_refs=reachable_partition_refs,
            evidence_partition_refs=evidence_partition_refs,
            dependency_cut_set=dependency_cut_set,
            exhausted_attempts=exhausted,
            exhausted_lineage_roots=exhausted_lineage_roots,
            unavailable_input_operator_types=unavailable_input_operator_types,
            active_lens_and_policy_versions=active_lens_and_policy_versions,
            governance_constraints=governance_constraints,
            budget_state_at_stall=view.budget_accounting,
            reopen_condition=reopen_condition,
            derivation_policy_version=policy_version,
            basis_event_refs=basis,
        )
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=ObligationEventType.STALLED,
            authority=ObligationAuthority.RESOLUTION_GOVERNOR,
            source_event_key=source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            previous_event_id=view.last_event_id,
            stall_certificate=certificate,
            basis_event_refs=basis,
            policy_version=policy_version,
        )
        return ObligationMutationResult(obligation, _commit(kernel, event))

    def note_delta(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
        delta: DependencyGraphDelta,
        *,
        policy_version: str = DERIVATION_POLICY_VERSION,
    ) -> ObligationMutationResult | None:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        obligation = _require_dependency_gap(obligation)
        prior = _existing_source_event(kernel, obligation_id, delta.source_event_key)
        if prior is not None:
            if prior.graph_delta != delta:
                raise ObligationIntegrityError("Graph-delta key was reused with different data.")
            return ObligationMutationResult(obligation, prior, replayed=True)
        view = derive_obligation_view(kernel, obligation_id)
        if view.current_status == ObligationStatus.MAY_WAKE:
            return None
        if view.current_status != ObligationStatus.STALLED:
            raise ObligationTransitionError("Only a stalled obligation can evaluate a wake delta.")
        certificate = view.active_stall_certificate
        if certificate is None:
            raise ObligationIntegrityError("Stalled obligation lost its certificate.")
        if not _has_reopen_signal(certificate.reopen_condition, certificate, delta):
            return None
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=ObligationEventType.WAKE_CANDIDATE,
            authority=ObligationAuthority.GRAPH_MONITOR,
            source_event_key=delta.source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            previous_event_id=view.last_event_id,
            graph_delta=delta,
            basis_event_refs=(view.last_event_id,),
            policy_version=policy_version,
        )
        return ObligationMutationResult(obligation, _commit(kernel, event))

    def allocate_recheck(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
        *,
        source_event_key: str,
        granted_budget: float,
        policy_version: str,
    ) -> ObligationMutationResult:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        obligation = _require_dependency_gap(obligation)
        prior = _existing_source_event(kernel, obligation_id, source_event_key)
        if prior is not None:
            if prior.recheck_budget_granted != granted_budget:
                raise ObligationIntegrityError("Recheck key was reused with another budget.")
            return ObligationMutationResult(obligation, prior, replayed=True)
        view = derive_obligation_view(kernel, obligation_id)
        if view.current_status != ObligationStatus.MAY_WAKE:
            raise ObligationTransitionError("Recheck allocation requires MayWake.")
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=ObligationEventType.RECHECK_ALLOCATED,
            authority=ObligationAuthority.SCHEDULER,
            source_event_key=source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            previous_event_id=view.last_event_id,
            recheck_budget_granted=granted_budget,
            basis_event_refs=(view.last_event_id,),
            policy_version=policy_version,
        )
        return ObligationMutationResult(obligation, _commit(kernel, event))

    def complete_recheck(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
        *,
        source_event_key: str,
        consumed_budget: float | None = None,
        policy_version: str = DERIVATION_POLICY_VERSION,
    ) -> ObligationMutationResult:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        obligation = _require_dependency_gap(obligation)
        prior = _existing_source_event(kernel, obligation_id, source_event_key)
        if prior is not None:
            if (
                consumed_budget is not None
                and prior.recheck_budget_consumed != consumed_budget
            ):
                raise ObligationIntegrityError(
                    "Recheck result key was reused with different consumption."
                )
            return ObligationMutationResult(obligation, prior, replayed=True)
        view = derive_obligation_view(kernel, obligation_id)
        if view.current_status != ObligationStatus.RECHECK_PENDING:
            raise ObligationTransitionError("Completing a recheck requires Recheck_Pending.")
        certificate = view.active_stall_certificate
        if certificate is None:
            raise ObligationIntegrityError("Recheck lost its active stall certificate.")
        wake = next(
            event for event in reversed(_events_for(kernel, obligation_id))
            if event.event_type == ObligationEventType.WAKE_CANDIDATE
        )
        if wake.graph_delta is None:
            raise ObligationIntegrityError("Wake event lost its graph delta.")
        allocation = next(
            event for event in reversed(_events_for(kernel, obligation_id))
            if event.event_type == ObligationEventType.RECHECK_ALLOCATED
        )
        granted = allocation.recheck_budget_granted or 0.0
        consumed = granted if consumed_budget is None else consumed_budget
        if consumed < 0.0 or consumed > granted + 1e-12:
            raise ObligationIntegrityError(
                "Recheck consumption must be within the granted simulation budget."
            )
        remaining_condition = _remaining_reopen_condition(
            certificate.reopen_condition,
            certificate,
            wake.graph_delta,
        )
        passed = remaining_condition is None
        if passed:
            event_type = ObligationEventType.REOPENED
            replacement = None
        else:
            event_type = ObligationEventType.RECHECK_NO_CHANGE
            replacement_budget = ObligationBudgetState(
                requested=view.budget_accounting.requested,
                granted=view.budget_accounting.granted,
                consumed=view.budget_accounting.consumed + consumed,
            )
            replacement = DependencyGapStallCertificate.build(
                obligation_kernel_ref=obligation_id,
                cycle_issued=kernel.state.cycle + 1,
                stall_cause_expression=certificate.stall_cause_expression,
                unresolved_evidence_frontier=certificate.unresolved_evidence_frontier,
                bounded_subgraph_hash=certificate.bounded_subgraph_hash,
                reachable_partition_refs=certificate.reachable_partition_refs,
                evidence_partition_refs=certificate.evidence_partition_refs,
                dependency_cut_set=certificate.dependency_cut_set,
                exhausted_attempts=certificate.exhausted_attempts,
                exhausted_lineage_roots=certificate.exhausted_lineage_roots,
                unavailable_input_operator_types=certificate.unavailable_input_operator_types,
                active_lens_and_policy_versions=certificate.active_lens_and_policy_versions,
                governance_constraints=certificate.governance_constraints,
                budget_state_at_stall=replacement_budget,
                reopen_condition=remaining_condition,
                derivation_policy_version=policy_version,
                basis_event_refs=(view.last_event_id,),
                supersedes_certificate_id=certificate.certificate_id,
            )
        event = ObligationHistoryEvent.build(
            obligation_id=obligation_id,
            event_type=event_type,
            authority=ObligationAuthority.RESOLUTION_GOVERNOR,
            source_event_key=source_event_key,
            cycle=kernel.state.cycle + 1,
            committed_sequence=kernel.state.event_sequence + 1,
            previous_event_id=view.last_event_id,
            stall_certificate=replacement,
            graph_delta=(wake.graph_delta if passed else None),
            recheck_budget_consumed=consumed,
            basis_event_refs=(view.last_event_id,),
            policy_version=policy_version,
        )
        return ObligationMutationResult(obligation, _commit(kernel, event))
