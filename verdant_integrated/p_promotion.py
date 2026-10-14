"""Opt-in, bounded automatic P promotion through existing native eligibility/Council.

This scheduler is external *research policy*, not a learned Verdant policy.
It never changes structure thresholds or bypasses denied native authorization.
"""
from __future__ import annotations

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    StructureCandidateStatus,
    StructurePromotionDisposition,
    VerdantKernel,
)
from verdant_structures import VerdantStructurePipeline


def promote_eligible_p(kernel: VerdantKernel, *, maximum: int = 4) -> dict:
    """Promote up to N eligible P candidates at a predeclared section boundary.

    Never retries a refusal against altered policy; an unexpected native
    exception stops the study and requires normal stage-level recovery.
    """
    if type(maximum) is not int or maximum < 0 or maximum > 8:
        raise ValueError("Auto-P promotion cap must be an integer between 0 and 8")

    pipeline = VerdantStructurePipeline()
    governance = VerdantGovernancePipeline()
    semantic_before = (
        tuple(sorted(kernel.state.concepts)),
        tuple(sorted(kernel.state.relations)),
        tuple(sorted(kernel.state.claims)),
        tuple(sorted(kernel.state.contradictions)),
        tuple(sorted(kernel.state.evidence)),
    )
    eligible = sorted(
        (candidate for candidate in kernel.state.structure_candidates.values()
         if candidate.status == StructureCandidateStatus.ELIGIBLE),
        key=lambda candidate: (-candidate.occurrence_count, candidate.candidate_id),
    )
    promoted = []
    deferred = []
    considered = 0
    for candidate in eligible:
        if len(promoted) >= maximum:
            break
        considered += 1
        # Re-evaluate quality and current native-policy gates; stale quality or
        # status cannot serve as authorization.
        report = pipeline.inspect_promotion(kernel, candidate.candidate_id)
        if report.disposition != StructurePromotionDisposition.PROMOTE:
            deferred.append(dict(candidate_id=candidate.candidate_id,
                                 reason="native_eligibility",
                                 rejection_codes=list(report.rejection_codes)))
            continue
        proposal = pipeline.promotion_council_proposal(kernel, report, governance)
        decision_preview = governance.inspect(kernel, proposal)
        if proposal.operation not in decision_preview.authorized_operations:
            deferred.append(dict(candidate_id=candidate.candidate_id,
                                 reason="council_not_authorized",
                                 disposition=decision_preview.disposition.value,
                                 rationale_codes=list(decision_preview.rationale_codes)))
            continue
        # Use the same native path as the Workbench's manual Promote button.
        result = pipeline.promote(kernel, candidate.candidate_id, governance)
        if result.event.structure_id not in kernel.state.structures:
            raise RuntimeError("Native Council-authorized promotion did not persist")
        promoted.append(dict(candidate_id=candidate.candidate_id,
                             structure_id=result.event.structure_id,
                             council_decision_event_id=result.event.council_decision_event_id,
                             promotion_event_id=result.event.event_id))

    semantic_after = (
        tuple(sorted(kernel.state.concepts)),
        tuple(sorted(kernel.state.relations)),
        tuple(sorted(kernel.state.claims)),
        tuple(sorted(kernel.state.contradictions)),
        tuple(sorted(kernel.state.evidence)),
    )
    if semantic_after != semantic_before:
        raise RuntimeError("P promotion mutated canonical semantic identities")

    return dict(
        scheduler="bounded_section_end_native_p_promotion_v0.1",
        cap=maximum,
        eligible_at_boundary=len(eligible),
        considered=considered,
        promoted=promoted,
        deferred=deferred,
        not_considered_due_to_cap=max(0, len(eligible)-considered),
        native_quality_and_council_required=True,
        automatic_q_promotion=False,
        learned_promotion_policy=False,
    )
