"""Opt-in generic folding: an earned structure becomes one operand, by the same rule, at any depth.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited. This is a
first slice of the Generalized Recursive Scaling proposal, not the whole of it: there is no
saturation policy, no split, and no learned proposal generator here.

One rule, no level classes
    * REIFY  When a structure is promoted through the ordinary Council path, a concept is
             created for it with ``kernel.ensure_concept`` (the same call object promotion
             uses), carrying ``source_structure_id``. That concept is the fold's handle.
    * USE    When an experience contains every member of an available fold, the workspace's
             current-evidence binding is routed through the handle instead of the members,
             repeatedly, until nothing more folds. Evidence, concepts, relations, the field
             write and resonance profiles are untouched: only what attention binds changes.
    * FOLD   Handles bond with whatever they are held in mind with, and the unchanged
             structure observer and promotion gates decide whether those bonds have earned
             a structure. A structure made of handles is a deeper fold. Nothing in the code
             knows what depth it is working at; depth is measured afterwards.
    * A handle never bonds with its own contents (it is them).
    * Ablate a fold and it stops being recognised, so every fold that needs it stops being
      recognised too; restore it and they return. No state is rewritten to do this.
"""
from __future__ import annotations

from sidecar_surprise import SurpriseDevelopmentPipeline
from verdant_kernel.models import WorkspaceSourceKind

__all__ = ["FoldingDevelopmentPipeline", "folding_plasticity", "reify", "promote_and_reify", "fold_table", "chunk",
           "unfold", "depth_of"]

FOLD_TYPE = "earned_fold"


def fold_table(kernel, *, available_only: bool = True) -> dict[str, tuple[str, frozenset[str]]]:
    """handle concept id -> (structure id, member concept ids), derived from canonical state."""
    table = {}
    for concept_id, concept in kernel.state.concepts.items():
        structure_id = concept.attributes.get("source_structure_id")
        if concept.attributes.get("concept_type") != FOLD_TYPE or structure_id not in kernel.state.structures:
            continue
        if available_only and not kernel.structure_is_available(structure_id):
            continue
        table[concept_id] = (structure_id, frozenset(kernel.state.structures[structure_id].member_concept_ids))
    return table


def reify(kernel, structure_id: str) -> str:
    structure = kernel.state.structures[structure_id]
    concept = kernel.ensure_concept(structure.opaque_name, evidence_refs=structure.evidence_refs,
                                    attributes={"concept_type": FOLD_TYPE, "source_structure_id": structure_id,
                                                "semantic_label_preinstalled": False})
    return concept.concept_id


def promote_and_reify(kernel, structures, candidate_id: str) -> str:
    result = structures.promote(kernel, candidate_id)
    return reify(kernel, result.event.structure_id)


def chunk(kernel, concept_ids) -> tuple[frozenset[str], int]:
    """Route a set of concepts through every available fold it fully contains. Returns (set, folds used)."""
    current = set(concept_ids); table = fold_table(kernel); used = 0; changed = True
    while changed:
        changed = False
        for handle, (_sid, members) in sorted(table.items(), key=lambda item: (-len(item[1][1]), item[0])):
            if handle not in current and members and members <= current:
                current = (current - members) | {handle}; used += 1; changed = True
    return frozenset(current), used


def unfold(kernel, concept_ids, *, available_only: bool = False) -> frozenset[str]:
    """Everything a set of concepts stands for once every handle is opened."""
    table = fold_table(kernel, available_only=available_only); out: set[str] = set(); stack = list(concept_ids)
    while stack:
        concept_id = stack.pop()
        if concept_id in table:
            stack.extend(table[concept_id][1])
        else:
            out.add(concept_id)
    return frozenset(out)


def depth_of(kernel, structure_id: str) -> int:
    table = {sid: handle for handle, (sid, _m) in fold_table(kernel, available_only=False).items()}
    by_handle = fold_table(kernel, available_only=False)

    def depth(sid: str) -> int:
        members = kernel.state.structures[sid].member_concept_ids
        return 1 + max((depth(by_handle[m][0]) for m in members if m in by_handle), default=0)
    return depth(structure_id)


class FoldingDevelopmentPipeline(SurpriseDevelopmentPipeline):
    """The heartbeat with measured surprise, whose current-evidence binding is routed through earned folds."""

    def __init__(self, **stages) -> None:
        super().__init__(**stages); self.fold_log: list[tuple[str, int, int, int]] = []

    def _workspace_candidates(self, kernel, experience, resonance_event):
        candidates = list(super()._workspace_candidates(kernel, experience, resonance_event))
        for i, candidate in enumerate(candidates):
            if candidate.source_kind != WorkspaceSourceKind.CURRENT_EVIDENCE:
                continue
            routed, used = chunk(kernel, candidate.binding_refs)
            self.fold_log.append((experience.event_key, len(candidate.binding_refs), len(routed), used))
            if used:
                candidates[i] = candidate.model_copy(update={
                    "binding_refs": tuple(sorted(routed)),
                    "metadata": {**candidate.metadata, "routed_through_folds": used,
                                 "bound_before_folding": len(candidate.binding_refs)}})
        return tuple(candidates)


def folding_plasticity(base):
    """Plasticity stage derived from ``base`` in which a handle never bonds with its own contents."""

    class FoldingPlasticity(base):
        def _candidate_pairs(self, kernel, activation, evidence_by_concept, current_evidence_concepts):
            pairs = super()._candidate_pairs(kernel, activation, evidence_by_concept, current_evidence_concepts)
            table = fold_table(kernel, available_only=False)
            if not table:
                return pairs
            contents = {handle: unfold(kernel, [handle]) | _inner_handles(table, handle) for handle in table}
            return {key: value for key, value in pairs.items()
                    if not (value[0][0] in contents.get(value[0][1], ()) or value[0][1] in contents.get(value[0][0], ()))}

    FoldingPlasticity.__name__ = f"Folding{base.__name__}"
    return FoldingPlasticity


def _inner_handles(table, handle) -> frozenset[str]:
    out: set[str] = set(); stack = [m for m in table[handle][1] if m in table]
    while stack:
        inner = stack.pop(); out.add(inner); stack.extend(m for m in table[inner][1] if m in table)
    return frozenset(out)
