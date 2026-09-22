"""Observer-only, pre-admission contextual access-pressure telemetry.

This is deliberately not Tg, not a truth judgement and not a control policy.
It inspects learned P membership against the incoming cue *before* the
developmental pipeline applies admission or temporary policy. No state writes.
"""
from __future__ import annotations

from typing import Iterable

from verdant_kernel import VerdantKernel


def inspect_access_pressure(
    kernel: VerdantKernel,
    cue_concept_ids: Iterable[str],
) -> dict[str, object]:
    """Describe structural competition using existing concept IDs only.

    A P with no overlap is not currently a recruitment candidate. An
    overlapping P with coverage < 0.5 is a weakly cued candidate; one with
    coverage >= 0.5 is strongly cued *structurally*, not semantically proven.

    This is a pre-admission *possibility count*, not the observed admitted P
    count. Workspace competition can reject candidates for other reasons.
    """

    cue = frozenset(cue_concept_ids)
    unknown = cue.difference(kernel.state.concepts)
    if unknown:
        raise ValueError("Access-pressure inspection requires existing concept IDs.")
    fingerprint_before = kernel.fingerprint()
    candidates: list[dict[str, object]] = []
    for structure in sorted(
        kernel.state.structures.values(),
        key=lambda item: item.structure_id,
    ):
        if not kernel.structure_is_available(structure.structure_id):
            continue
        members = set(structure.member_concept_ids)
        overlap = tuple(sorted(members.intersection(cue)))
        if not overlap:
            continue
        fraction = len(overlap) / len(members)
        candidates.append({
            "structure_id": structure.structure_id,
            "member_count": len(members),
            "trigger_count": len(overlap),
            "trigger_fraction": fraction,
            "trigger_concept_ids": list(overlap),
            "weak_context": fraction < 0.5,
        })
    weak = [candidate for candidate in candidates if candidate["weak_context"]]
    strong = [candidate for candidate in candidates if not candidate["weak_context"]]
    if kernel.fingerprint() != fingerprint_before:
        raise RuntimeError("Access-pressure inspection mutated canonical state.")
    return {
        "schema_id": "verdant.access_pressure_observation.v1",
        "behavioral_authority_enabled": False,
        "semantic_truth_judgement": False,
        "canonical_state_fingerprint": fingerprint_before,
        "cycle_before_experience": kernel.state.cycle,
        "cue_concept_ids": list(sorted(cue)),
        "available_overlapping_structures": len(candidates),
        "weak_context_candidate_count": len(weak),
        "supported_context_candidate_count": len(strong),
        "max_weak_trigger_fraction": max(
            (candidate["trigger_fraction"] for candidate in weak),
            default=None,
        ),
        "candidate_details": candidates,
    }
