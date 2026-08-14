from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_kernel import HierarchyCandidateStatus, StructureCandidateStatus, VerdantKernel
from verdant_structures import VerdantStructurePipeline

from .interventions import ForkedLesion, InterventionTier


class RecoveryClassification(str, Enum):
    NO_RECOVERY = "no_recovery"
    REDERIVED_SAME_ID = "rederived_same_id"
    REEARNED_NEW_ID = "reearned_new_id"


@dataclass(frozen=True)
class RecoveryResult:
    classification: RecoveryClassification
    tier: InterventionTier
    removed_id: str
    recovered_id: str | None
    promotion_event_id: str | None
    used_restore_operation: bool
    notes: tuple[str, ...] = ()


def governed_rederive_p(lesion: ForkedLesion) -> RecoveryResult:
    """Use only the normal P eligibility/governance/promotion path after lesion.

    This is an *external experimental driver*, not autonomous self-repair.  It
    never calls the availability restoration API and never reinserts the saved
    target snapshot.
    """

    if lesion.manifest.tier != InterventionTier.DESTRUCTIVE_P:
        raise ValueError("P recovery requires a destructive-P lesion manifest.")
    kernel = lesion.kernel
    candidate = kernel.state.structure_candidates.get(lesion.manifest.source_candidate_id)
    if candidate is None or candidate.status != StructureCandidateStatus.ELIGIBLE:
        return RecoveryResult(
            RecoveryClassification.NO_RECOVERY,
            lesion.manifest.tier,
            lesion.manifest.target_id,
            None,
            None,
            False,
            ("Source candidate is not currently eligible for native governance promotion.",),
        )
    event = VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event
    recovered_id = event.structure_id
    classification = (
        RecoveryClassification.REDERIVED_SAME_ID
        if recovered_id == lesion.manifest.target_id
        else RecoveryClassification.REEARNED_NEW_ID
    )
    return RecoveryResult(
        classification,
        lesion.manifest.tier,
        lesion.manifest.target_id,
        recovered_id,
        event.event_id,
        False,
        ("Promotion was re-executed through normal V5 governance; no restore operation was used.",),
    )


def governed_rederive_q(lesion: ForkedLesion) -> RecoveryResult:
    """Use only the normal Q eligibility/governance/promotion path after lesion."""

    if lesion.manifest.tier != InterventionTier.DESTRUCTIVE_Q:
        raise ValueError("Q recovery requires a destructive-Q lesion manifest.")
    kernel = lesion.kernel
    candidate = kernel.state.hierarchy_candidates.get(lesion.manifest.source_candidate_id)
    if candidate is None or candidate.status != HierarchyCandidateStatus.ELIGIBLE:
        return RecoveryResult(
            RecoveryClassification.NO_RECOVERY,
            lesion.manifest.tier,
            lesion.manifest.target_id,
            None,
            None,
            False,
            ("Source hierarchy candidate is not currently eligible for native governance promotion.",),
        )
    event = VerdantHierarchyPipeline().promote(kernel, candidate.candidate_id).event
    recovered_id = event.layered_structure_id
    classification = (
        RecoveryClassification.REDERIVED_SAME_ID
        if recovered_id == lesion.manifest.target_id
        else RecoveryClassification.REEARNED_NEW_ID
    )
    return RecoveryResult(
        classification,
        lesion.manifest.tier,
        lesion.manifest.target_id,
        recovered_id,
        event.event_id,
        False,
        ("Promotion was re-executed through normal V5 governance; no restore operation was used.",),
    )
