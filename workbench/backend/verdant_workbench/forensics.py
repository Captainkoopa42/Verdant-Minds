from __future__ import annotations

from typing import Any


class ForensicNotFoundError(KeyError):
    pass


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json") if hasattr(model, "model_dump") else dict(model)


def _concept_view(kernel, concept_id: str) -> dict[str, Any]:
    concept = kernel.state.concepts.get(concept_id)
    if concept is None:
        return {"concept_id": concept_id, "missing": True, "label": concept_id}
    data = _dump(concept)
    data["display_label"] = concept.label
    data["evidence"] = [
        _dump(kernel.state.evidence[ref])
        for ref in concept.evidence_refs
        if ref in kernel.state.evidence
    ]
    return data


def _evidence_views(kernel, refs) -> list[dict[str, Any]]:
    result = []
    for ref in sorted(set(refs)):
        item = kernel.state.evidence.get(ref)
        if item is not None:
            result.append(_dump(item))
        else:
            result.append({"evidence_id": ref, "missing": True})
    return result


def _council_view(kernel, decision_id: str | None) -> dict[str, Any] | None:
    if not decision_id:
        return None
    for event in kernel.state.council_decisions:
        if event.decision_event_id == decision_id:
            return _dump(event)
    return {"decision_event_id": decision_id, "missing": True}


def _p_history(kernel, candidate_id: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for event in kernel.state.structure_observation_events:
        snapshots = [
            item for item in event.report.proposed_candidates
            if item.candidate_id == candidate_id
        ]
        if not snapshots:
            continue
        snapshot = snapshots[0]
        history.append({
            "phase": "candidate_observation",
            "cycle": event.committed_cycle,
            "native_event_id": event.event_id,
            "native_report_id": event.report.report_id,
            "candidate": _dump(snapshot),
            "evidence_refs": list(snapshot.evidence_refs),
            "workspace_event_ids": list(snapshot.workspace_event_ids),
        })
    history.sort(key=lambda item: (item["cycle"], item["native_event_id"]))
    return history


def _q_history(kernel, candidate_id: str) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for event in kernel.state.hierarchy_observation_events:
        snapshots = [
            item for item in event.report.proposed_candidates
            if item.candidate_id == candidate_id
        ]
        if not snapshots:
            continue
        snapshot = snapshots[0]
        history.append({
            "phase": "hierarchy_candidate_observation",
            "cycle": event.committed_cycle,
            "native_event_id": event.event_id,
            "native_report_id": event.report.report_id,
            "candidate": _dump(snapshot),
            "evidence_refs": list(snapshot.evidence_refs),
            "interaction_event_ids": list(snapshot.interaction_event_ids),
        })
    history.sort(key=lambda item: (item["cycle"], item["native_event_id"]))
    return history


def list_structures(kernel) -> dict[str, Any]:
    p = []
    for structure in sorted(kernel.state.structures.values(), key=lambda item: (item.created_cycle, item.structure_id)):
        p.append({
            "kind": "P",
            "id": structure.structure_id,
            "opaque_name": structure.opaque_name,
            "created_cycle": structure.created_cycle,
            "available": kernel.structure_is_available(structure.structure_id),
            "member_count": len(structure.member_concept_ids),
            "member_labels": [kernel.state.concepts[cid].label for cid in structure.member_concept_ids],
            "source_candidate_id": structure.source_candidate_id,
            "revision_index": structure.revision_index,
            "lineage_parent_structure_id": structure.lineage_parent_structure_id,
            "lineage_root_structure_id": structure.lineage_root_structure_id or structure.structure_id,
            "quality": _dump(structure.quality_at_promotion),
        })
    q = []
    for structure in sorted(kernel.state.layered_structures.values(), key=lambda item: (item.created_cycle, item.layered_structure_id)):
        q.append({
            "kind": "Q",
            "id": structure.layered_structure_id,
            "opaque_name": structure.opaque_name,
            "created_cycle": structure.created_cycle,
            "available": kernel.layered_structure_is_available(structure.layered_structure_id),
            "member_count": len(structure.member_structure_ids),
            "member_structure_ids": list(structure.member_structure_ids),
            "source_candidate_id": structure.source_candidate_id,
            "depth": structure.depth,
            "quality": _dump(structure.quality_at_promotion),
        })
    candidates = [
        {
            "kind": "P_CANDIDATE",
            "id": item.candidate_id,
            "status": item.status.value,
            "occurrence_count": item.occurrence_count,
            "created_cycle": item.created_cycle,
            "updated_cycle": item.updated_cycle,
            "member_count": len(item.member_concept_ids),
            "member_labels": [kernel.state.concepts[cid].label for cid in item.member_concept_ids],
            "quality": _dump(item.quality),
            "promoted_structure_id": item.promoted_structure_id,
        }
        for item in sorted(kernel.state.structure_candidates.values(), key=lambda item: (item.created_cycle, item.candidate_id))
    ]
    hierarchy_candidates = [
        {
            "kind": "Q_CANDIDATE",
            "id": item.candidate_id,
            "status": item.status.value,
            "occurrence_count": item.occurrence_count,
            "created_cycle": item.created_cycle,
            "updated_cycle": item.updated_cycle,
            "member_count": len(item.member_structure_ids),
            "member_structure_ids": list(item.member_structure_ids),
            "quality": _dump(item.quality),
            "promoted_layered_structure_id": item.promoted_layered_structure_id,
        }
        for item in sorted(kernel.state.hierarchy_candidates.values(), key=lambda item: (item.created_cycle, item.candidate_id))
    ]
    return {
        "cycle": kernel.state.cycle,
        "state_revision": kernel.state.event_sequence,
        "fingerprint": kernel.fingerprint(),
        "p_structures": p,
        "q_structures": q,
        "p_candidates": candidates,
        "q_candidates": hierarchy_candidates,
    }


def p_detail(kernel, structure_id: str) -> dict[str, Any]:
    structure = kernel.state.structures.get(structure_id)
    if structure is None:
        raise ForensicNotFoundError(structure_id)
    candidate = kernel.state.structure_candidates.get(structure.source_candidate_id)
    promotion = next((e for e in kernel.state.structure_promotion_events if e.structure_id == structure_id), None)
    refold_creation = next((e for e in kernel.state.structure_refold_events if structure_id in e.produced_structure_ids), None)
    uses = [
        _dump(e) for e in kernel.state.compilation_probe_events
        if e.report.structure_id == structure_id
    ]
    interactions = []
    for event in kernel.state.structure_interaction_events:
        report = event.report
        if report.source_structure_id == structure_id or any(c.target_structure_id == structure_id for c in report.candidates):
            interactions.append(_dump(event))
    challenges = [
        _dump(item) for item in kernel.state.structural_challenges.values()
        if item.structure_id == structure_id
    ]
    refolds = [
        _dump(e) for e in kernel.state.structure_refold_events
        if e.report.parent_structure_id == structure_id or structure_id in e.produced_structure_ids
    ]
    availability = [
        _dump(e) for e in kernel.state.structure_availability_events
        if e.structure_id == structure_id
    ]
    member_concepts = [_concept_view(kernel, cid) for cid in structure.member_concept_ids]
    edges = []
    for edge in structure.internal_edge_snapshots:
        a, b = edge.concept_ids
        edges.append({
            **_dump(edge),
            "source_label": kernel.state.concepts[a].label,
            "target_label": kernel.state.concepts[b].label,
        })
    evidence_refs = set(structure.evidence_refs)
    if candidate is not None:
        evidence_refs.update(candidate.evidence_refs)
    evidence = _evidence_views(kernel, evidence_refs)
    children = [
        item.structure_id for item in kernel.state.structures.values()
        if item.lineage_parent_structure_id == structure_id
    ]
    return {
        "kind": "P",
        "id": structure_id,
        "available": kernel.structure_is_available(structure_id),
        "record": _dump(structure),
        "candidate": None if candidate is None else _dump(candidate),
        "candidate_history": _p_history(kernel, structure.source_candidate_id),
        "promotion_event": None if promotion is None else _dump(promotion),
        "refold_creation_event": None if refold_creation is None else _dump(refold_creation),
        "council_decision": _council_view(kernel, structure.council_decision_event_id),
        "member_concepts": member_concepts,
        "frozen_edges": edges,
        "evidence": evidence,
        "uses": uses,
        "interactions": interactions,
        "availability_events": availability,
        "challenges": challenges,
        "refolds": refolds,
        "lineage": {
            "parent": structure.lineage_parent_structure_id,
            "root": structure.lineage_root_structure_id or structure.structure_id,
            "revision_index": structure.revision_index,
            "children": sorted(children),
            "refold_basis_challenge_ids": list(structure.refold_basis_challenge_ids),
        },
    }


def q_detail(kernel, structure_id: str) -> dict[str, Any]:
    structure = kernel.state.layered_structures.get(structure_id)
    if structure is None:
        raise ForensicNotFoundError(structure_id)
    candidate = kernel.state.hierarchy_candidates.get(structure.source_candidate_id)
    promotion = next((e for e in kernel.state.hierarchy_promotion_events if e.layered_structure_id == structure_id), None)
    availability = [
        _dump(e) for e in kernel.state.layered_structure_availability_events
        if e.layered_structure_id == structure_id
    ]
    uses = [
        _dump(e) for e in kernel.state.layered_probe_events
        if e.report.layered_structure_id == structure_id
    ]
    members = []
    for sid in structure.member_structure_ids:
        member = kernel.state.structures.get(sid)
        if member is None:
            members.append({"structure_id": sid, "missing": True})
        else:
            members.append({
                "structure_id": sid,
                "opaque_name": member.opaque_name,
                "available": kernel.structure_is_available(sid),
                "member_labels": [kernel.state.concepts[cid].label for cid in member.member_concept_ids],
                "created_cycle": member.created_cycle,
            })
    evidence_refs = set(structure.evidence_refs)
    if candidate is not None:
        evidence_refs.update(candidate.evidence_refs)
    return {
        "kind": "Q",
        "id": structure_id,
        "available": kernel.layered_structure_is_available(structure_id),
        "record": _dump(structure),
        "candidate": None if candidate is None else _dump(candidate),
        "candidate_history": _q_history(kernel, structure.source_candidate_id),
        "promotion_event": None if promotion is None else _dump(promotion),
        "council_decision": _council_view(kernel, structure.council_decision_event_id),
        "member_structures": members,
        "evidence": _evidence_views(kernel, evidence_refs),
        "availability_events": availability,
        "uses": uses,
    }


def detail(kernel, structure_id: str) -> dict[str, Any]:
    if structure_id in kernel.state.structures:
        return p_detail(kernel, structure_id)
    if structure_id in kernel.state.layered_structures:
        return q_detail(kernel, structure_id)
    raise ForensicNotFoundError(structure_id)


def replay(kernel, structure_id: str) -> dict[str, Any]:
    before = kernel.fingerprint()
    if structure_id in kernel.state.structures:
        structure = kernel.state.structures[structure_id]
        frames = _p_history(kernel, structure.source_candidate_id)
        promotion = next((e for e in kernel.state.structure_promotion_events if e.structure_id == structure_id), None)
        if promotion is not None:
            frames.append({
                "phase": "promotion",
                "cycle": promotion.committed_cycle,
                "native_event_id": promotion.event_id,
                "native_report_id": promotion.report.report_id,
                "promotion": _dump(promotion),
                "evidence_refs": list(promotion.report.evidence_refs),
            })
        refold = next((e for e in kernel.state.structure_refold_events if structure_id in e.produced_structure_ids), None)
        if refold is not None:
            frames.append({
                "phase": "refold_creation",
                "cycle": refold.committed_cycle,
                "native_event_id": refold.event_id,
                "native_report_id": refold.report.report_id,
                "refold": _dump(refold),
                "evidence_refs": list(refold.report.evidence_refs),
            })
        kind = "P"
    elif structure_id in kernel.state.layered_structures:
        structure = kernel.state.layered_structures[structure_id]
        frames = _q_history(kernel, structure.source_candidate_id)
        promotion = next((e for e in kernel.state.hierarchy_promotion_events if e.layered_structure_id == structure_id), None)
        if promotion is not None:
            frames.append({
                "phase": "promotion",
                "cycle": promotion.committed_cycle,
                "native_event_id": promotion.event_id,
                "native_report_id": promotion.report.report_id,
                "promotion": _dump(promotion),
                "evidence_refs": list(promotion.report.evidence_refs),
            })
        kind = "Q"
    else:
        raise ForensicNotFoundError(structure_id)
    frames.sort(key=lambda item: (item["cycle"], item["native_event_id"]))
    after = kernel.fingerprint()
    if after != before:
        raise RuntimeError("Forensic replay inspection mutated canonical engine state.")
    refs = sorted({ref for frame in frames for ref in frame.get("evidence_refs", [])})
    return {
        "kind": kind,
        "structure_id": structure_id,
        "frame_count": len(frames),
        "frames": frames,
        "evidence": _evidence_views(kernel, refs),
        "fingerprint_before": before,
        "fingerprint_after": after,
        "mutated": before != after,
    }


def graph(kernel, structure_id: str) -> dict[str, Any]:
    if structure_id in kernel.state.structures:
        structure = kernel.state.structures[structure_id]
        nodes = [
            {"id": cid, "kind": "concept", "label": kernel.state.concepts[cid].label}
            for cid in structure.member_concept_ids
        ]
        edges = [
            {
                "id": edge.association_id,
                "source": edge.concept_ids[0],
                "target": edge.concept_ids[1],
                "kind": "frozen_association",
                "weight": edge.strength,
            }
            for edge in structure.internal_edge_snapshots
        ]
        return {"structure_id": structure_id, "kind": "P", "nodes": nodes, "edges": edges}
    if structure_id in kernel.state.layered_structures:
        structure = kernel.state.layered_structures[structure_id]
        nodes = []
        edges = []
        center = {"id": structure_id, "kind": "Q", "label": structure.opaque_name}
        nodes.append(center)
        for sid in structure.member_structure_ids:
            member = kernel.state.structures.get(sid)
            nodes.append({"id": sid, "kind": "P", "label": member.opaque_name if member else sid})
            edges.append({"id": f"{structure_id}:{sid}", "source": structure_id, "target": sid, "kind": "hierarchy_member", "weight": 1.0})
        return {"structure_id": structure_id, "kind": "Q", "nodes": nodes, "edges": edges}
    raise ForensicNotFoundError(structure_id)
