"""Opt-in bounded Q formation from genuinely promoted P interactions.

External research scheduler, NOT a self-learned Verdant executive. Runs
exactly the native Workbench interaction -> hierarchy observation -> Council-
gated Q promotion operations. Only uses P created by the native P pipeline.
"""
from __future__ import annotations

from verdant_governance import VerdantGovernancePipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    HierarchyCandidateStatus, HierarchyPromotionDisposition, VerdantKernel,
)


def _semantic_ids(kernel: VerdantKernel) -> tuple:
    state = kernel.state
    return tuple(
        tuple(sorted(records))
        for records in (
            state.concepts, state.relations, state.claims,
            state.contradictions, state.evidence,
        )
    )


def advance_q_from_new_p(
    kernel: VerdantKernel,
    *,
    newly_promoted_p_ids: tuple[str, ...],
    maximum_interactions: int = 4,
    maximum_q_promotions: int = 2,
) -> dict:
    """At section end interact new native Ps, observe hierarchy, promote Q if earned.

    Each source P is examined at most once over its lifetime in this policy;
    when a later P emerges it is inspected against the accumulated pool.
    Every actual native interaction has an immediately following native
    hierarchy observation attempt. No synthetic recurrence is added by
    replaying old sources on every curriculum section.
    """
    for name, value, bound in (
        ("maximum_interactions", maximum_interactions, 4),
        ("maximum_q_promotions", maximum_q_promotions, 4),
    ):
        if type(value) is not int or not 0 <= value <= bound:
            raise ValueError(f"{name} must be an integer between 0 and {bound}")
    if len(newly_promoted_p_ids) != len(set(newly_promoted_p_ids)):
        raise ValueError("Newly promoted P identities must be distinct")
    if len(newly_promoted_p_ids) > maximum_interactions:
        raise ValueError("New P batch exceeds the declared interaction cap")
    if any(
        sid not in kernel.state.structures or not kernel.structure_is_available(sid)
        for sid in newly_promoted_p_ids
    ):
        raise ValueError("Q input must refer to current available native P structures")

    before = _semantic_ids(kernel)
    interaction = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    governance = VerdantGovernancePipeline()
    prior_sources = {
        event.report.source_structure_id
        for event in kernel.state.structure_interaction_events
    }

    interactions = []
    observations = []
    deferred = []
    promoted = []

    # Wait for at least three independently earned Ps, the native Q minimum.
    # This ensures three Ps promoted across separate sections still receive
    # three distinct native interaction inspections, not only the newest one.
    # Each P source is processed ONCE under this protocol; never manufacture
    # recurrence by replaying an old source on every curriculum boundary.
    available_ids = sorted(
        sid for sid in kernel.state.structures
        if kernel.structure_is_available(sid)
    )
    available_count = len(available_ids)
    pending_sources = [
        sid for sid in available_ids if sid not in prior_sources
    ] if available_count >= 3 else []
    for sid in pending_sources[:maximum_interactions]:
        result = interaction.interact(kernel, sid)
        interactions.append(dict(
            source_structure_id=sid,
            event_id=result.event.event_id,
            verified_alignments=sum(
                c.disposition.value == "verified_alignment"
                for c in result.report.candidates
            ),
            candidate_targets=len(result.report.candidates),
        ))
        observed = hierarchy.observe(kernel)
        if observed is not None:
            observations.append(dict(
                event_id=observed.event.event_id,
                candidate_ids=list(observed.report.observed_candidate_ids),
                latest_interaction_event_id=result.event.event_id,
            ))

    eligible = sorted(
        (
            candidate for candidate in kernel.state.hierarchy_candidates.values()
            if candidate.status == HierarchyCandidateStatus.ELIGIBLE
        ),
        key=lambda c: (-c.occurrence_count, c.candidate_id),
    )
    considered = 0
    for candidate in eligible:
        if len(promoted) >= maximum_q_promotions:
            break
        considered += 1
        report = hierarchy.inspect_promotion(kernel, candidate.candidate_id)
        if report.disposition != HierarchyPromotionDisposition.PROMOTE:
            deferred.append(dict(
                candidate_id=candidate.candidate_id,
                reason="native_q_eligibility",
                rejection_codes=list(report.rejection_codes),
            ))
            continue
        proposal = hierarchy.promotion_council_proposal(
            kernel, report, governance
        )
        decision_preview = governance.inspect(kernel, proposal)
        if proposal.operation not in decision_preview.authorized_operations:
            deferred.append(dict(
                candidate_id=candidate.candidate_id,
                reason="council_not_authorized",
                rationale_codes=list(decision_preview.rationale_codes),
                disposition=decision_preview.disposition.value,
            ))
            continue
        result = hierarchy.promote(kernel, candidate.candidate_id, governance)
        if result.event.layered_structure_id not in kernel.state.layered_structures:
            raise RuntimeError("Council-authorized Q was not installed")
        promoted.append(dict(
            candidate_id=candidate.candidate_id,
            layered_structure_id=result.event.layered_structure_id,
            council_decision_event_id=result.event.council_decision_event_id,
            promotion_event_id=result.event.event_id,
        ))

    if _semantic_ids(kernel) != before:
        raise RuntimeError("P interactions and Q promotion changed canonical semantics")

    return dict(
        scheduler="bounded_section_end_native_q_v0.1",
        interaction_cap=maximum_interactions,
        q_promotion_cap=maximum_q_promotions,
        native_p_sources=list(sorted(newly_promoted_p_ids)),
        native_p_available=available_count,
        pending_unseen_p_sources=len(pending_sources),
        unprocessed_sources_due_to_interaction_cap=max(0, len(pending_sources)-len(interactions)),
        interactions=interactions,
        hierarchy_observations=observations,
        eligible_q_at_boundary=len(eligible),
        considered=considered,
        promoted=promoted,
        deferred=deferred,
        not_considered_due_to_cap=max(0, len(eligible)-considered),
        native_verified_alignment_required=True,
        native_council_authorization_required=True,
        learned_q_scheduling_policy=False,
    )
