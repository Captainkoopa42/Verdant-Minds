"""Observer-only, pre-admission contextual access-pressure telemetry.

This is deliberately not Tg, not a truth judgement and not a control policy.
It inspects learned P membership against the incoming cue *before* the
developmental pipeline applies admission or temporary policy. No state writes.
"""
from __future__ import annotations

from typing import Iterable

from verdant_kernel import VerdantKernel
from verdant_kernel.models import normalize_label

from .models import (
    AccessPressureCandidate,
    AccessPressureMeasurementStatus,
    AccessPressureObservation,
)


def inspect_access_pressure(
    kernel: VerdantKernel,
    cue_concept_ids: Iterable[str],
    *,
    cue_labels: Iterable[str] = (),
    source_event_key: str = "",
) -> AccessPressureObservation:
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
    candidates: list[AccessPressureCandidate] = []
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
        candidates.append(AccessPressureCandidate(
            structure_id=structure.structure_id,
            member_count=len(members),
            trigger_count=len(overlap),
            trigger_fraction=fraction,
            trigger_concept_ids=overlap,
            weak_context=fraction < 0.5,
        ))
    weak = [candidate for candidate in candidates if candidate.weak_context]
    strong = [candidate for candidate in candidates if not candidate.weak_context]
    if kernel.fingerprint() != fingerprint_before:
        raise RuntimeError("Access-pressure inspection mutated canonical state.")
    return AccessPressureObservation(
        measurement_status=AccessPressureMeasurementStatus.COMPLETE,
        source_event_key=source_event_key,
        canonical_state_fingerprint=fingerprint_before,
        cycle_before_experience=kernel.state.cycle,
        cue_labels=tuple(sorted(set(cue_labels))),
        cue_concept_ids=tuple(sorted(cue)),
        available_overlapping_structures=len(candidates),
        weak_context_candidate_count=len(weak),
        supported_context_candidate_count=len(strong),
        max_weak_trigger_fraction=max(
            (candidate.trigger_fraction for candidate in weak),
            default=None,
        ),
        candidate_details=tuple(candidates),
    )


def inspect_labeled_access_pressure(
    kernel: VerdantKernel,
    cue_labels: Iterable[str],
    *,
    source_event_key: str = "",
) -> AccessPressureObservation:
    """Inspect a current cue without creating concepts to make it measurable.

    If any label is absent from the checkpoint, the returned record is marked
    incomplete and deliberately contains no partial candidate counts.
    """

    labels = tuple(sorted(set(label.strip() for label in cue_labels if label.strip())))
    by_label = {
        concept.normalized_label: concept_id
        for concept_id, concept in kernel.state.concepts.items()
    }
    known_ids: list[str] = []
    unknown: list[str] = []
    for label in labels:
        key = normalize_label(label)
        concept_id = by_label.get(key)
        if concept_id is None:
            unknown.append(label)
        else:
            known_ids.append(concept_id)
    if unknown:
        fingerprint = kernel.fingerprint()
        return AccessPressureObservation(
            measurement_status=AccessPressureMeasurementStatus.INCOMPLETE,
            source_event_key=source_event_key,
            canonical_state_fingerprint=fingerprint,
            cycle_before_experience=kernel.state.cycle,
            cue_labels=labels,
            cue_concept_ids=tuple(sorted(set(known_ids))),
            unknown_cue_labels=tuple(sorted(unknown)),
        )
    return inspect_access_pressure(
        kernel,
        known_ids,
        cue_labels=labels,
        source_event_key=source_event_key,
    )
