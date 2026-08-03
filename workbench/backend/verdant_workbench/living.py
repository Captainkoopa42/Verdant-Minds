from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Iterable


LIVING_FRAME_SCHEMA = "verdant.workbench.living-frame.v1"
LIVING_TIMELINE_SCHEMA = "verdant.workbench.living-timeline.v1"


class LivingExplorerError(RuntimeError):
    pass


def _dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if isinstance(model, dict):
        return dict(model)
    raise TypeError(f"Unsupported living explorer record: {type(model)!r}")


def _sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _latest(items: Iterable[Any], cycle: int, cycle_attr: str = "committed_cycle") -> Any | None:
    eligible = [item for item in items if int(getattr(item, cycle_attr)) <= cycle]
    if not eligible:
        return None
    return max(eligible, key=lambda item: (int(getattr(item, cycle_attr)), _event_identity(item)))


def _event_identity(item: Any) -> str:
    return str(
        getattr(item, "event_id", None)
        or getattr(item, "resonance_event_id", None)
        or getattr(item, "challenge_id", None)
        or ""
    )


def _availability_at(events: Iterable[Any], structure_id: str, cycle: int) -> bool:
    available = True
    related = [e for e in events if getattr(e, "committed_cycle", 0) <= cycle and (
        getattr(e, "structure_id", None) == structure_id or getattr(e, "layered_structure_id", None) == structure_id
    )]
    for event in sorted(related, key=lambda e: (e.committed_cycle, _event_identity(e))):
        action = getattr(event.action, "value", str(event.action)).lower()
        if action == "ablate":
            available = False
        elif action == "restore":
            available = True
    return available

def _p_availability_at(kernel, structure_id: str, cycle: int) -> bool:
    actions: list[tuple[int, str, str]] = []
    for event in kernel.state.structure_availability_events:
        if event.structure_id == structure_id and event.committed_cycle <= cycle:
            actions.append((event.committed_cycle, event.event_id, getattr(event.action, "value", str(event.action)).lower()))
    for event in kernel.state.structure_refold_events:
        if event.report.parent_structure_id == structure_id and event.parent_ablated and event.committed_cycle <= cycle:
            actions.append((event.committed_cycle, event.event_id, "ablate"))
    available = True
    for _cycle, _eid, action in sorted(actions):
        if action == "ablate":
            available = False
        elif action == "restore":
            available = True
    return available


def _latest_candidate_snapshots(kernel, cycle: int, *, hierarchy: bool = False) -> dict[str, Any]:
    events = kernel.state.hierarchy_observation_events if hierarchy else kernel.state.structure_observation_events
    result: dict[str, Any] = {}
    for event in sorted(events, key=lambda e: (e.committed_cycle, e.event_id)):
        if event.committed_cycle > cycle:
            break
        for candidate in event.report.proposed_candidates:
            result[candidate.candidate_id] = candidate
    return result


def _historical_associations(kernel, cycle: int) -> tuple[list[dict[str, Any]], dict[str, str]]:
    event = _latest(kernel.state.plasticity_events, cycle)
    if event is None:
        return [], {}
    change_by_id: dict[str, str] = {}
    for assessment in event.report.assessments:
        change_by_id[assessment.association_id] = getattr(assessment.disposition, "value", str(assessment.disposition))
    edges = []
    for assoc in event.report.proposed_associations:
        a, b = assoc.concept_ids
        edges.append({
            "id": assoc.association_id,
            "source": a,
            "target": b,
            "strength": assoc.strength,
            "exposure_count": assoc.exposure_count,
            "created_cycle": assoc.created_cycle,
            "updated_cycle": assoc.updated_cycle,
            "last_reinforced_cycle": assoc.last_reinforced_cycle,
            "change_at_frame": change_by_id.get(assoc.association_id),
        })
    return edges, change_by_id


def _workspace_at(kernel, cycle: int) -> dict[str, Any]:
    event = _latest(kernel.state.workspace_cycle_events, cycle)
    if event is None:
        return {
            "event_id": None,
            "active": [],
            "suppressed": [],
            "total_allocated_resource": 0.0,
            "resource_budget": float(kernel.state.workspace_policy.resource_budget),
        }
    active = []
    suppressed = []
    admitted = set(event.report.admitted_candidate_ids)
    suppressed_ids = set(event.report.suppressed_candidate_ids)
    for assessment in event.report.assessments:
        candidate = assessment.candidate
        view = {
            "candidate_id": assessment.candidate_id,
            "source_kind": getattr(candidate.source_kind, "value", str(candidate.source_kind)),
            "source_ref": candidate.source_ref,
            "label": candidate.label,
            "binding_refs": list(candidate.binding_refs),
            "evidence_refs": list(candidate.evidence_refs),
            "raw_score": assessment.raw_score,
            "effective_score": assessment.effective_score,
            "allocated_resource": assessment.allocated_resource,
            "signals": _dump(candidate.signals),
            "disposition": getattr(assessment.disposition, "value", str(assessment.disposition)),
        }
        if assessment.candidate_id in admitted:
            active.append(view)
        elif assessment.candidate_id in suppressed_ids:
            suppressed.append(view)
    return {
        "event_id": event.event_id,
        "committed_cycle": event.committed_cycle,
        "active": active,
        "suppressed": suppressed,
        "active_item_ids": list(event.active_item_ids),
        "broadcast_item_ids": list(event.broadcast_item_ids),
        "total_allocated_resource": event.report.total_allocated_resource,
        "resource_budget": event.report.resource_budget,
    }


def _resonance_at(kernel, cycle: int) -> dict[str, Any]:
    event = _latest(kernel.state.resonance_events, cycle)
    if event is None:
        return {"event_id": None, "candidates": []}
    return {
        "event_id": event.resonance_event_id,
        "committed_cycle": event.committed_cycle,
        "modality": event.query_report.modality,
        "candidates": [
            {
                "concept_id": c.concept_id,
                "score": c.score,
                "rank": c.rank,
                "profile_exposure_count": c.profile_exposure_count,
                "profile_evidence_count": c.profile_evidence_count,
            }
            for c in event.query_report.candidates
        ],
    }


def _event_markers(kernel, cycle: int) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []

    def add(kind: str, event_id: str, payload: dict[str, Any] | None = None):
        markers.append({"kind": kind, "event_id": event_id, "payload": payload or {}})

    for event in kernel.state.resonance_events:
        if event.committed_cycle == cycle:
            add("RESONANCE", event.resonance_event_id, {"candidate_count": len(event.query_report.candidates)})
    for event in kernel.state.workspace_cycle_events:
        if event.committed_cycle == cycle:
            add("WORKSPACE", event.event_id, {"active_count": len(event.active_item_ids), "suppressed_count": len(event.suppressed_candidate_ids)})
    for event in kernel.state.plasticity_events:
        if event.committed_cycle == cycle:
            add("PLASTICITY", event.event_id, {
                "created": list(event.report.created_association_ids),
                "reinforced": list(event.report.reinforced_association_ids),
                "decayed": list(event.report.decayed_association_ids),
                "pruned": list(event.report.pruned_association_ids),
            })
    for event in kernel.state.structure_observation_events:
        if event.committed_cycle == cycle:
            add("P_CANDIDATE", event.event_id, {"candidate_ids": list(event.active_candidate_ids)})
    for event in kernel.state.structure_promotion_events:
        if event.committed_cycle == cycle:
            add("P_PROMOTED", event.event_id, {"structure_id": event.structure_id, "candidate_id": event.report.candidate_id})
    for event in kernel.state.structure_availability_events:
        if event.committed_cycle == cycle:
            add("P_AVAILABILITY", event.event_id, {"structure_id": event.structure_id, "action": getattr(event.action, "value", str(event.action))})
    for event in kernel.state.compilation_probe_events:
        if event.committed_cycle == cycle:
            add("P_USED", event.event_id, {"structure_id": event.report.structure_id, "disposition": getattr(event.report.disposition, "value", str(event.report.disposition))})
    for event in kernel.state.structure_interaction_events:
        if event.committed_cycle == cycle:
            add("P_INTERACTION", event.event_id, {"source_structure_id": event.report.source_structure_id, "best_target_structure_id": event.report.best_target_structure_id})
    for event in kernel.state.hierarchy_observation_events:
        if event.committed_cycle == cycle:
            add("Q_CANDIDATE", event.event_id, {"candidate_ids": list(event.active_candidate_ids)})
    for event in kernel.state.hierarchy_promotion_events:
        if event.committed_cycle == cycle:
            add("Q_PROMOTED", event.event_id, {"layered_structure_id": event.layered_structure_id, "candidate_id": event.report.candidate_id})
    for event in kernel.state.layered_structure_availability_events:
        if event.committed_cycle == cycle:
            add("Q_AVAILABILITY", event.event_id, {"layered_structure_id": event.layered_structure_id, "action": getattr(event.action, "value", str(event.action))})
    for event in kernel.state.layered_probe_events:
        if event.committed_cycle == cycle:
            add("Q_USED", event.event_id, {"layered_structure_id": event.report.layered_structure_id, "query_structure_id": event.report.query_structure_id})
    for challenge in kernel.state.structural_challenges.values():
        for observation in challenge.observations:
            if observation.cycle == cycle:
                add("CHALLENGE", f"{challenge.challenge_id}:{observation.event_key}", {
                    "challenge_id": challenge.challenge_id,
                    "structure_id": challenge.structure_id,
                    "concept_ids": list(challenge.concept_ids),
                    "confidence": observation.confidence,
                })
    for event in kernel.state.structure_refold_events:
        if event.committed_cycle == cycle:
            add("REFOLD", event.event_id, {
                "parent_structure_id": event.report.parent_structure_id,
                "disposition": getattr(event.report.disposition, "value", str(event.report.disposition)),
                "produced_structure_ids": list(event.produced_structure_ids),
                "parent_ablated": event.parent_ablated,
            })
    markers.sort(key=lambda m: (m["kind"], m["event_id"]))
    return markers


def _interesting_cycles(kernel) -> list[int]:
    cycles = {0, int(kernel.state.cycle)}
    for concept in kernel.state.concepts.values():
        cycles.add(int(concept.created_cycle))
    for relation in kernel.state.relations.values():
        cycles.add(int(relation.created_cycle))
        cycles.add(int(relation.updated_cycle))
    for collection in (
        kernel.state.resonance_events,
        kernel.state.workspace_cycle_events,
        kernel.state.plasticity_events,
        kernel.state.structure_observation_events,
        kernel.state.structure_promotion_events,
        kernel.state.structure_availability_events,
        kernel.state.compilation_probe_events,
        kernel.state.structure_interaction_events,
        kernel.state.hierarchy_observation_events,
        kernel.state.hierarchy_promotion_events,
        kernel.state.layered_structure_availability_events,
        kernel.state.layered_probe_events,
        kernel.state.structure_refold_events,
    ):
        for event in collection:
            cycles.add(int(event.committed_cycle))
    for challenge in kernel.state.structural_challenges.values():
        for observation in challenge.observations:
            cycles.add(int(observation.cycle))
    return sorted(cycle for cycle in cycles if cycle >= 0)


def _downsample_cycles(cycles: list[int], max_frames: int, kernel) -> list[int]:
    if max_frames <= 0:
        raise LivingExplorerError("max_frames must be positive")
    if len(cycles) <= max_frames:
        return cycles
    milestone_cycles = set()
    for collection in (
        kernel.state.structure_promotion_events,
        kernel.state.structure_availability_events,
        kernel.state.structure_interaction_events,
        kernel.state.hierarchy_promotion_events,
        kernel.state.layered_structure_availability_events,
        kernel.state.layered_probe_events,
        kernel.state.structure_refold_events,
    ):
        milestone_cycles.update(int(e.committed_cycle) for e in collection)
    for challenge in kernel.state.structural_challenges.values():
        milestone_cycles.update(int(o.cycle) for o in challenge.observations)
    keep = {cycles[0], cycles[-1]} | milestone_cycles
    budget = max(0, max_frames - len(keep))
    remaining = [c for c in cycles if c not in keep]
    if budget and remaining:
        if budget >= len(remaining):
            keep.update(remaining)
        else:
            for i in range(budget):
                idx = round(i * (len(remaining) - 1) / max(1, budget - 1)) if budget > 1 else len(remaining) // 2
                keep.add(remaining[idx])
    selected = sorted(keep)
    if len(selected) > max_frames:
        # Milestone-heavy traces are never silently dropped; caller can request a larger cap.
        return selected
    return selected


def _apply_lod(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], workspace: dict[str, Any], p_structures: list[dict[str, Any]], *, max_nodes: int, max_edges: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if max_nodes <= 0 or max_edges <= 0:
        raise LivingExplorerError("LOD node/edge caps must be positive")
    all_node_ids = {n["id"] for n in nodes}
    priority: set[str] = set()
    for item in workspace.get("active", []):
        priority.update(item.get("binding_refs", []))
    for structure in p_structures:
        priority.update(structure.get("member_concept_ids", []))
    ranked_nodes = sorted(
        nodes,
        key=lambda n: (
            0 if n["id"] in priority else 1,
            -float(n.get("resonance_score", 0.0)),
            n.get("label", ""),
            n["id"],
        ),
    )
    kept_nodes = ranked_nodes[:max_nodes]
    kept_ids = {n["id"] for n in kept_nodes}
    eligible_edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids]
    kept_edges = sorted(eligible_edges, key=lambda e: (-float(e.get("strength", 0.0)), e["id"]))[:max_edges]
    lod = {
        "total_nodes": len(nodes),
        "rendered_nodes": len(kept_nodes),
        "omitted_nodes": len(nodes) - len(kept_nodes),
        "total_edges": len(edges),
        "rendered_edges": len(kept_edges),
        "omitted_edges": len(edges) - len(kept_edges),
        "max_nodes": max_nodes,
        "max_edges": max_edges,
        "priority_node_count": len(priority & all_node_ids),
    }
    return kept_nodes, kept_edges, lod


def living_frame(kernel, cycle: int | None = None, *, max_nodes: int = 240, max_edges: int = 500) -> dict[str, Any]:
    before = kernel.fingerprint()
    current_cycle = int(kernel.state.cycle)
    if cycle is None:
        cycle = current_cycle
    cycle = int(cycle)
    if cycle < 0 or cycle > current_cycle:
        raise LivingExplorerError(f"Cycle {cycle} is outside recorded history 0..{current_cycle}.")

    resonance = _resonance_at(kernel, cycle)
    resonance_scores = {item["concept_id"]: item["score"] for item in resonance["candidates"]}
    workspace = _workspace_at(kernel, cycle)
    active_binding_ids = {ref for item in workspace.get("active", []) for ref in item.get("binding_refs", [])}

    p_structures = []
    for structure in sorted(kernel.state.structures.values(), key=lambda s: (s.created_cycle, s.structure_id)):
        if structure.created_cycle > cycle:
            continue
        p_structures.append({
            "id": structure.structure_id,
            "opaque_name": structure.opaque_name,
            "created_cycle": structure.created_cycle,
            "available": _p_availability_at(kernel, structure.structure_id, cycle),
            "member_concept_ids": list(structure.member_concept_ids),
            "revision_index": structure.revision_index,
            "lineage_parent_structure_id": structure.lineage_parent_structure_id,
        })
    q_structures = []
    for structure in sorted(kernel.state.layered_structures.values(), key=lambda s: (s.created_cycle, s.layered_structure_id)):
        if structure.created_cycle > cycle:
            continue
        q_structures.append({
            "id": structure.layered_structure_id,
            "opaque_name": structure.opaque_name,
            "created_cycle": structure.created_cycle,
            "available": _availability_at(kernel.state.layered_structure_availability_events, structure.layered_structure_id, cycle),
            "member_structure_ids": list(structure.member_structure_ids),
            "depth": structure.depth,
        })

    membership: dict[str, list[str]] = defaultdict(list)
    for structure in p_structures:
        for cid in structure["member_concept_ids"]:
            membership[cid].append(structure["id"])

    nodes = []
    for concept in sorted(kernel.state.concepts.values(), key=lambda c: (c.created_cycle, c.normalized_label, c.concept_id)):
        if concept.created_cycle > cycle:
            continue
        nodes.append({
            "id": concept.concept_id,
            "label": concept.label,
            "created_cycle": concept.created_cycle,
            "resonance_score": float(resonance_scores.get(concept.concept_id, 0.0)),
            "workspace_active": concept.concept_id in active_binding_ids,
            "structure_ids": sorted(membership.get(concept.concept_id, [])),
        })

    edges, _changes = _historical_associations(kernel, cycle)
    nodes, edges, lod = _apply_lod(nodes, edges, workspace, p_structures, max_nodes=max_nodes, max_edges=max_edges)
    p_candidates = _latest_candidate_snapshots(kernel, cycle)
    q_candidates = _latest_candidate_snapshots(kernel, cycle, hierarchy=True)
    markers = _event_markers(kernel, cycle)

    frame_core = {
        "schema": LIVING_FRAME_SCHEMA,
        "cycle": cycle,
        "current_cycle": current_cycle,
        "is_live_head": cycle == current_cycle,
        "nodes": nodes,
        "plastic_edges": edges,
        "workspace": workspace,
        "resonance": resonance,
        "p_candidates": [
            {
                "id": c.candidate_id,
                "status": getattr(c.status, "value", str(c.status)),
                "occurrence_count": c.occurrence_count,
                "member_concept_ids": list(c.member_concept_ids),
                "quality": _dump(c.quality),
            }
            for c in sorted(p_candidates.values(), key=lambda c: (c.created_cycle, c.candidate_id))
        ],
        "p_structures": p_structures,
        "q_candidates": [
            {
                "id": c.candidate_id,
                "status": getattr(c.status, "value", str(c.status)),
                "occurrence_count": c.occurrence_count,
                "member_structure_ids": list(c.member_structure_ids),
                "quality": _dump(c.quality),
            }
            for c in sorted(q_candidates.values(), key=lambda c: (c.created_cycle, c.candidate_id))
        ],
        "q_structures": q_structures,
        "markers": markers,
        "lod": lod,
        "counts": {
            "concepts_recorded_through_cycle": sum(1 for c in kernel.state.concepts.values() if c.created_cycle <= cycle),
            "plastic_associations": len(edges),
            "workspace_active": len(workspace.get("active", [])),
            "p_candidates": len(p_candidates),
            "p_structures": len(p_structures),
            "q_candidates": len(q_candidates),
            "q_structures": len(q_structures),
        },
    }
    frame_core["frame_sha256"] = _sha(frame_core)
    after = kernel.fingerprint()
    if before != after:
        raise LivingExplorerError("Living Explorer projection mutated canonical engine state.")
    frame_core["canonical_fingerprint_before"] = before
    frame_core["canonical_fingerprint_after"] = after
    frame_core["mutated"] = False
    return frame_core


def living_timeline(kernel, *, max_frames: int = 240, max_nodes: int = 240, max_edges: int = 500, include_frames: bool = True) -> dict[str, Any]:
    before = kernel.fingerprint()
    cycles = _downsample_cycles(_interesting_cycles(kernel), max_frames, kernel)
    frames = [living_frame(kernel, cycle, max_nodes=max_nodes, max_edges=max_edges) for cycle in cycles] if include_frames else []
    index = []
    if include_frames:
        for idx, frame in enumerate(frames):
            index.append({
                "index": idx,
                "cycle": frame["cycle"],
                "frame_sha256": frame["frame_sha256"],
                "marker_kinds": [m["kind"] for m in frame["markers"]],
                "counts": frame["counts"],
                "lod": frame["lod"],
            })
    else:
        for idx, cycle in enumerate(cycles):
            markers = _event_markers(kernel, cycle)
            index.append({"index": idx, "cycle": cycle, "marker_kinds": [m["kind"] for m in markers]})
    after = kernel.fingerprint()
    if before != after:
        raise LivingExplorerError("Living Explorer timeline mutated canonical engine state.")
    result = {
        "schema": LIVING_TIMELINE_SCHEMA,
        "current_cycle": int(kernel.state.cycle),
        "frame_count": len(cycles),
        "cycles": cycles,
        "index": index,
        "frames": frames,
        "head_frame_sha256": frames[-1]["frame_sha256"] if frames else None,
        "canonical_fingerprint_before": before,
        "canonical_fingerprint_after": after,
        "mutated": False,
        "sampling": {
            "recorded_interesting_cycles": len(_interesting_cycles(kernel)),
            "returned_frames": len(cycles),
            "max_frames": max_frames,
            "max_nodes": max_nodes,
            "max_edges": max_edges,
        },
    }
    return result
