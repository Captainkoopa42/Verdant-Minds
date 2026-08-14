from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from verdant_kernel import (
    HierarchyCandidateStatus,
    StructureCandidateStatus,
    VerdantKernel,
    WorkspaceSourceKind,
)


class InterventionTier(str, Enum):
    LOGICAL_AVAILABILITY = "logical_availability"
    DESTRUCTIVE_P = "destructive_p"
    DESTRUCTIVE_Q = "destructive_q"
    SUPPORT_SCRAMBLE = "support_scramble"


@dataclass(frozen=True)
class LesionManifest:
    schema_id: str
    tier: InterventionTier
    source_fingerprint: str
    fork_fingerprint: str
    target_id: str
    target_snapshot_sha256: str
    source_candidate_id: str
    removed_ids: tuple[str, ...]
    preserved_primitive_counts: dict[str, int]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ForkedLesion:
    kernel: VerdantKernel
    manifest: LesionManifest


def _sha(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _primitive_counts(kernel: VerdantKernel) -> dict[str, int]:
    return {
        "evidence": len(kernel.state.evidence),
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
        "contradictions": len(kernel.state.contradictions),
        "plasticity_associations": len(kernel.state.plasticity_associations),
    }


def _assert_primitives_preserved(source: VerdantKernel, fork: VerdantKernel) -> None:
    for name in ("evidence", "concepts", "relations", "claims", "contradictions", "plasticity_associations"):
        if getattr(source.state, name) != getattr(fork.state, name):
            raise RuntimeError(f"Destructive intervention mutated primitive substrate: {name}")


def fork_destructive_p_lesion(source: VerdantKernel, structure_id: str) -> ForkedLesion:
    """Clone *source* and remove one operational P record without a restore path.

    Primitive evidence, canonical semantics, ECWF state, and plastic associations
    are preserved exactly.  Derived records that would otherwise retain a live
    referential dependency on the removed P are pruned from the experimental
    fork.  The source StructureCandidate is reset to ELIGIBLE so normal V5
    observation/governance can re-derive and re-promote the operand.

    Refold-lineage parents are intentionally rejected in EU01 rather than
    silently deleting historical descendants.
    """

    if structure_id not in source.state.structures:
        raise KeyError(f"Unknown P structure {structure_id!r}.")
    target = source.state.structures[structure_id]
    if any(
        item.lineage_parent_structure_id == structure_id
        or item.lineage_root_structure_id == structure_id
        for sid, item in source.state.structures.items()
        if sid != structure_id
    ):
        raise ValueError("EU01 destructive P lesion does not delete a refolding lineage parent.")

    source_fingerprint = source.fingerprint()
    primitive_before = _primitive_counts(source)
    state = source.snapshot()
    removed: set[str] = {structure_id}

    # Remove active uses and histories whose kernel invariants require the P.
    state.structures.pop(structure_id)
    state.ablated_structure_ids = tuple(
        item for item in state.ablated_structure_ids if item != structure_id
    )
    state.structure_promotion_events = [
        item for item in state.structure_promotion_events if item.structure_id != structure_id
    ]
    state.structure_availability_events = [
        item for item in state.structure_availability_events if item.structure_id != structure_id
    ]
    state.compilation_probe_events = [
        item for item in state.compilation_probe_events if item.report.structure_id != structure_id
    ]
    state.workspace_items = {
        key: item
        for key, item in state.workspace_items.items()
        if not (
            item.source_kind == WorkspaceSourceKind.EARNED_STRUCTURE
            and item.source_ref == structure_id
        )
    }
    state.structural_challenges = {
        key: item
        for key, item in state.structural_challenges.items()
        if item.structure_id != structure_id
    }
    state.structure_refold_events = [
        item
        for item in state.structure_refold_events
        if item.report.parent_structure_id != structure_id
        and structure_id not in item.produced_structure_ids
    ]

    candidate = state.structure_candidates[target.source_candidate_id]
    state.structure_candidates[target.source_candidate_id] = candidate.model_copy(
        update={
            "status": StructureCandidateStatus.ELIGIBLE,
            "promoted_structure_id": None,
            "updated_cycle": max(candidate.updated_cycle, state.cycle),
        }
    )

    # Any interaction whose source/target was the lesioned P is no longer a
    # valid current higher-order observation in the fork.
    kept_interactions = []
    for event in state.structure_interaction_events:
        refs = {event.report.source_structure_id}
        refs.update(item.target_structure_id for item in event.report.candidates)
        if structure_id in refs:
            removed.add(event.event_id)
        else:
            kept_interactions.append(event)
    state.structure_interaction_events = kept_interactions
    kept_interaction_ids = {item.event_id for item in kept_interactions}

    # Remove current hierarchy candidates that depended on the missing P or on
    # interactions pruned above. Their historical observation snapshots remain
    # audit history, but they are no longer active candidate state.
    removed_hierarchy_candidates: set[str] = set()
    for candidate_id, item in list(state.hierarchy_candidates.items()):
        if (
            structure_id in item.member_structure_ids
            or any(ref not in kept_interaction_ids for ref in item.interaction_event_ids)
        ):
            removed_hierarchy_candidates.add(candidate_id)
            removed.add(candidate_id)
            state.hierarchy_candidates.pop(candidate_id)

    removed_q: set[str] = set()
    for layered_id, item in list(state.layered_structures.items()):
        if structure_id in item.member_structure_ids or item.source_candidate_id in removed_hierarchy_candidates:
            removed_q.add(layered_id)
            removed.add(layered_id)
            state.layered_structures.pop(layered_id)
    state.hierarchy_promotion_events = [
        item for item in state.hierarchy_promotion_events if item.layered_structure_id not in removed_q
    ]
    state.ablated_layered_structure_ids = tuple(
        item for item in state.ablated_layered_structure_ids if item not in removed_q
    )
    state.layered_structure_availability_events = [
        item for item in state.layered_structure_availability_events if item.layered_structure_id not in removed_q
    ]
    state.layered_probe_events = [
        item
        for item in state.layered_probe_events
        if item.report.query_structure_id != structure_id
        and item.report.layered_structure_id not in removed_q
        and structure_id not in item.report.matched_structure_ids
    ]
    state.hierarchy_observation_events = [
        item
        for item in state.hierarchy_observation_events
        if item.report.latest_interaction_event_id in kept_interaction_ids
    ]

    fork = VerdantKernel.from_state(state)
    _assert_primitives_preserved(source, fork)
    if source.fingerprint() != source_fingerprint:
        raise RuntimeError("Source kernel changed while constructing P lesion fork.")

    return ForkedLesion(
        kernel=fork,
        manifest=LesionManifest(
            schema_id="verdant.destructive_lesion.v1",
            tier=InterventionTier.DESTRUCTIVE_P,
            source_fingerprint=source_fingerprint,
            fork_fingerprint=fork.fingerprint(),
            target_id=structure_id,
            target_snapshot_sha256=_sha(target.model_dump(mode="json")),
            source_candidate_id=target.source_candidate_id,
            removed_ids=tuple(sorted(removed)),
            preserved_primitive_counts=primitive_before,
            notes=(
                "No restoration API is used by this intervention.",
                "Primitive semantic/evidence/plastic substrate is byte-equivalent at model level.",
                "Re-promotion may deterministically reproduce the same stable structure ID.",
            ),
        ),
    )


def fork_destructive_q_lesion(source: VerdantKernel, layered_structure_id: str) -> ForkedLesion:
    """Clone *source* and remove one Q while preserving all lower-level P state."""

    if layered_structure_id not in source.state.layered_structures:
        raise KeyError(f"Unknown Q structure {layered_structure_id!r}.")
    target = source.state.layered_structures[layered_structure_id]
    source_fingerprint = source.fingerprint()
    primitive_before = _primitive_counts(source)
    state = source.snapshot()

    state.layered_structures.pop(layered_structure_id)
    state.ablated_layered_structure_ids = tuple(
        item for item in state.ablated_layered_structure_ids if item != layered_structure_id
    )
    state.hierarchy_promotion_events = [
        item
        for item in state.hierarchy_promotion_events
        if item.layered_structure_id != layered_structure_id
    ]
    state.layered_structure_availability_events = [
        item
        for item in state.layered_structure_availability_events
        if item.layered_structure_id != layered_structure_id
    ]
    state.layered_probe_events = [
        item
        for item in state.layered_probe_events
        if item.report.layered_structure_id != layered_structure_id
    ]
    candidate = state.hierarchy_candidates[target.source_candidate_id]
    state.hierarchy_candidates[target.source_candidate_id] = candidate.model_copy(
        update={
            "status": HierarchyCandidateStatus.ELIGIBLE,
            "promoted_layered_structure_id": None,
            "updated_cycle": max(candidate.updated_cycle, state.cycle),
        }
    )

    fork = VerdantKernel.from_state(state)
    _assert_primitives_preserved(source, fork)
    # Q lesions must preserve every lower-level earned P exactly.
    if fork.state.structures != source.state.structures:
        raise RuntimeError("Q lesion mutated lower-level P structures.")
    if source.fingerprint() != source_fingerprint:
        raise RuntimeError("Source kernel changed while constructing Q lesion fork.")

    return ForkedLesion(
        kernel=fork,
        manifest=LesionManifest(
            schema_id="verdant.destructive_lesion.v1",
            tier=InterventionTier.DESTRUCTIVE_Q,
            source_fingerprint=source_fingerprint,
            fork_fingerprint=fork.fingerprint(),
            target_id=layered_structure_id,
            target_snapshot_sha256=_sha(target.model_dump(mode="json")),
            source_candidate_id=target.source_candidate_id,
            removed_ids=(layered_structure_id,),
            preserved_primitive_counts=primitive_before,
            notes=(
                "No restoration API is used by this intervention.",
                "All lower-level P operands are preserved exactly.",
                "Re-promotion may deterministically reproduce the same stable Q ID.",
            ),
        ),
    )
