"""Opt-in, read-only cognitive-pocket cultivation over genuine native P memories.

Inspired by V4 basin-local processing and mitosis, without reusing V4's
incompatible NetworkX state or creating canonical P/Q facts.

The pocket distinguishes three channels:
  native plastic association (local activity)
  native canonical relation (typed, evidenced; may cross structures)
  structural role analogy (non-factual hypothetical propagation ONLY)

Every trace and candidate is derived from an existing native kernel snapshot.
No canonical commit, obligation creation, Q nomination or resolution occurs.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations, permutations

from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import VerdantKernel
from verdant_kernel.models import canonical_json_bytes, stable_id


class PocketIntegrityError(ValueError):
    """Invalid sources or unsafe attempt to treat analogy as evidence."""


def _typed_rows(kernel: VerdantKernel, members: set[str]) -> list[dict]:
    # Current canonical records, not assertions about what P knew at promotion.
    rows = []
    for r in kernel.state.relations.values():
        if r.source_concept_id not in members or r.target_concept_id not in members:
            continue
        if not r.evidence_refs or any(e not in kernel.state.evidence for e in r.evidence_refs):
            raise PocketIntegrityError("Canonical relation has incomplete evidence closure")
        rows.append({
            "id": r.relation_id,
            "source": r.source_concept_id,
            "target": r.target_concept_id,
            "type": r.relation_type,
            "directed": r.directed,
            "status": r.status.value,
            "weight": r.weight,
            "evidence_refs": list(r.evidence_refs),
        })
    return sorted(rows, key=lambda row: row["id"])


def _role_grammar(members: tuple[str, ...], rows: list[dict]) -> tuple | None:
    """Canonical renaming-insensitive, type-variable grammar, not semantics."""
    if not rows:
        return None
    if len(members) > 8:
        return None
    best = None
    for order in permutations(range(len(members))):
        ren = dict(zip(sorted(members), order))
        typed = sorted(
            (
                (ren[r["source"]], ren[r["target"]]) if r["directed"] else
                tuple(sorted((ren[r["source"]], ren[r["target"]]))),
                r["type"], bool(r["directed"]),
            )
            for r in rows
        )
        role_ids = {}
        grammar = []
        for edge, typ, directed in typed:
            if typ not in role_ids:
                role_ids[typ] = len(role_ids)
            grammar.append((edge[0], edge[1], role_ids[typ], directed))
        key = tuple(grammar)
        if best is None or key < best:
            best = key
    return best


def cultivate_pocket(
    kernel: VerdantKernel,
    p_ids: tuple[str, ...] | list[str],
    *,
    q_id: str | None = None,
    rounds: int = 6,
    minimum_alignment: float = 0.90,
) -> dict:
    """Reconstructable read-only pocket using 2..8 actual available promoted Ps.

    This proof-of-concept runs deterministic activation *in a private numeric
    scratch map*. Hypothetical role links permit attention transfer but never
    create evidence, canonical edges, semantic equivalence or a resolved path.
    """
    if not 1 <= rounds <= 12:
        raise PocketIntegrityError("Pocket rounds must be between 1 and 12")
    if not 0.0 <= minimum_alignment <= 1.0:
        raise PocketIntegrityError("Invalid similarity threshold")
    ids = tuple(sorted(p_ids))
    if len(ids) != len(set(ids)) or not 2 <= len(ids) <= 8:
        raise PocketIntegrityError("Pocket needs 2..8 distinct native P structures")
    for sid in ids:
        if sid not in kernel.state.structures or not kernel.structure_is_available(sid):
            raise PocketIntegrityError("Every source must be an available, Council-promoted P")
    if q_id is not None:
        q = kernel.state.layered_structures.get(q_id)
        if q is None or not kernel.layered_structure_is_available(q_id):
            raise PocketIntegrityError("Q must be a genuine available promoted Q")
        if not set(ids).issubset(q.member_structure_ids):
            raise PocketIntegrityError("Q does not contain the requested P sources")

    before = kernel.fingerprint()
    ps = [kernel.state.structures[sid] for sid in ids]
    owners: dict[str, set[str]] = defaultdict(set)
    local_edges = {}
    p_records = []
    all_member_relations = {}
    for p in ps:
        members = tuple(sorted(p.member_concept_ids))
        for cid in members:
            if cid not in kernel.state.concepts:
                raise PocketIntegrityError("Dangling concept in promoted P")
            owners[cid].add(p.structure_id)
        rows = _typed_rows(kernel, set(members))
        for r in rows:
            all_member_relations[r["id"]] = r
        grammar = _role_grammar(members, rows)
        for edge in p.internal_edge_snapshots:
            a, b = edge.concept_ids
            if a not in members or b not in members:
                raise PocketIntegrityError("Broken plastic association snapshot")
            local_edges[tuple(sorted((a, b)))] = max(
                edge.strength, local_edges.get(tuple(sorted((a, b))), 0.0)
            )
        p_records.append({
            "id": p.structure_id,
            "created_cycle": p.created_cycle,
            "council_decision_id": p.council_decision_event_id,
            "members": list(members),
            "promotion_relation_ids": list(p.member_relation_ids),
            "current_canonical_relation_ids": [r["id"] for r in rows],
            "relation_grammar": [list(token) for token in grammar] if grammar is not None else None,
            "promotion_evidence_refs": list(p.evidence_refs),
        })

    # A genuine canonical *cross-P* relation is the only non-hypothetical
    # bridge. No shared label, native topology mapping, or Q membership is
    # allowed to create a new factual edge.
    all_nodes = set(owners)
    cross_relations = []
    for r in _typed_rows(kernel, all_nodes):
        if r["id"] in all_member_relations:
            continue
        # Hypothetical, contradicted or rejected canonical records are
        # visible in native memory but never an evidenced cross-pocket bridge.
        if r["status"] not in ("supported", "confirmed"):
            continue
        if not any(a != b for a in owners[r["source"]] for b in owners[r["target"]]):
            continue
        cross_relations.append(r)

    candidates = []
    hypothetical_edges = set()
    for left, right in combinations(ps, 2):
        score, mapping = VerdantStructureInteractionPipeline._symbolic_alignment(
            kernel, left, right
        )
        if score < minimum_alignment or not mapping:
            continue
        item = {
            "from_p": left.structure_id,
            "to_p": right.structure_id,
            "topology_score": round(float(score), 12),
            "mapped_roles": [list(pair) for pair in mapping],
            "status": "hypothetical_role_correspondence",
            "canonical_relation_asserted": False,
            "semantic_equivalence_asserted": False,
        }
        candidates.append(item)
        for a, b in mapping:
            if a != b:
                hypothetical_edges.add(tuple(sorted((a, b))))

    # A path through separate Ps is a factual path description ONLY where
    # both native relation edges already exist, and never a transitive claim.
    canonical_edges = [
        row for row in all_member_relations.values()
        if row["status"] in ("supported", "confirmed")
    ] + cross_relations
    walks = []
    for first, second in combinations(canonical_edges, 2):
        for a, b in ((first, second), (second, first)):
            if not a["directed"] or not b["directed"]:
                continue
            if a["target"] != b["source"]:
                continue
            # At least one actual cross-P relation or disjoint owning sources.
            cross = a["id"] in {r["id"] for r in cross_relations} or b["id"] in {r["id"] for r in cross_relations}
            if not cross:
                continue
            walks.append({
                "nodes": [a["source"], a["target"], b["target"]],
                "relation_ids": [a["id"], b["id"]],
                "evidence_refs": sorted(set(a["evidence_refs"] + b["evidence_refs"])),
                "status": "observed_canonical_two_edge_path",
                "derived_transitive_fact": False,
            })
    walks = sorted(walks, key=lambda w: (w["relation_ids"], w["nodes"]))[:64]

    # Deterministic local activation. Analogical channel is a *thought
    # experiment*, never counted as canonical signal or an observed relation.
    active = {cid: 0.0 for cid in sorted(all_nodes)}
    for p in ps:
        seed = min(p.member_concept_ids)
        active[seed] = 1.0
    rounds_trace = []
    for tick in range(1, rounds + 1):
        nxt = {cid: round(val * 0.70, 8) for cid, val in active.items()}
        for (a, b), weight in sorted(local_edges.items()):
            nxt[a] = min(1.0, max(nxt[a], active[b] * weight * 0.70))
            nxt[b] = min(1.0, max(nxt[b], active[a] * weight * 0.70))
        for r in cross_relations:
            if r["status"] not in ("supported", "confirmed"):
                continue
            a, b = r["source"], r["target"]
            nxt[b] = min(1.0, max(nxt[b], active[a] * r["weight"] * 0.45))
            if not r["directed"]:
                nxt[a] = min(1.0, max(nxt[a], active[b] * r["weight"] * 0.45))
        for a, b in sorted(hypothetical_edges):
            nxt[a] = min(1.0, max(nxt[a], active[b] * 0.08))
            nxt[b] = min(1.0, max(nxt[b], active[a] * 0.08))
        active = {cid: round(v, 8) for cid, v in sorted(nxt.items())}
        rounds_trace.append({
            "round": tick,
            "activation": active.copy(),
            "channel_counts": {
                "native_plastic": len(local_edges),
                "evidenced_cross_p": len(cross_relations),
                "hypothetical_analogy": len(hypothetical_edges),
            },
        })

    grammar_groups: dict[str, list[str]] = defaultdict(list)
    for p in p_records:
        grammar_groups[str(p["relation_grammar"])].append(p["id"])
    # The summary intentionally retains source IDs and does not discard any
    # exact types or evidence. No binary compression or learned ontology claim.
    summary = [
        {"grammar": None if key == "None" else key, "p_ids": sorted(v)}
        for key, v in sorted(grammar_groups.items())
    ]
    payload = {
        "schema": "verdant.cognitive_pocket.v0",
        "canonical_fingerprint": before,
        "canonical_cycle": kernel.state.cycle,
        "q_context_id": q_id,
        "p_ids": list(ids),
        "concepts": [
            {
                "id": cid,
                "label": kernel.state.concepts[cid].label,
                "owner_p_ids": sorted(owners[cid]),
                "evidence_refs": list(kernel.state.concepts[cid].evidence_refs),
            }
            for cid in sorted(all_nodes)
        ],
        "p_snapshots": p_records,
        "current_member_relations": sorted(all_member_relations.values(), key=lambda r: r["id"]),
        "evidenced_cross_p_relations": cross_relations,
        "native_plastic_edges": [
            {"nodes": list(k), "strength_at_p_promotion": v}
            for k, v in sorted(local_edges.items())
        ],
        "hypothetical_role_alignments": candidates,
        "evidenced_cross_p_walks": walks,
        "local_rounds": rounds_trace,
        "grammar_inventory": summary,
        "controls": {
            "canonical_edge_created": False,
            "q_or_p_promoted": False,
            "obligation_recorded": False,
            "simulation_budget_consumed": False,
            "epistemic_truth_asserted_from_analogy": False,
            "lossless_source_trace_retained": True,
            "actual_binary_compression_measured": False,
        },
    }
    payload["pocket_id"] = stable_id("cognitive_pocket", payload)
    if kernel.fingerprint() != before:
        raise PocketIntegrityError("Cultivation touched canonical native state")
    return payload
