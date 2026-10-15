"""Selective, evidenced, read-only relational composition over genuine native P/Q.

Cognitive Pocket v2, phase 1. This is deliberately NOT free-form inference.
Only a preregistered transitivity rule can compose canonical SUPPORTED or
CONFIRMED directed same-predicate edges. P selection is bounded by native
cross-P topology; neither labels nor hypothetical analogies create bridges.

No truth or new relations are written to the native kernel. A successful
result is an independently checkable, reconstructed witness for a declared
rule; not autonomous discovery, semantic understanding or compression.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
import json
from typing import Any

from verdant_kernel.models import stable_id

from .experiment import PocketIntegrityError


RULE_POLICY_VERSION = "cognitive_pocket_explicit_transitive_rule_v2.0"
# Explicit external policies. In particular: supports, bounded_by, requires,
# differs_from, and unknown relation predicates are NOT assumed transitive.
ALLOWED_TRANSITIVE_RELATIONS = frozenset({"precedes"})


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class CompositionQuery:
    source_concept_id: str
    target_concept_id: str
    relation_type: str = "precedes"
    maximum_member_ps: int = 3
    maximum_hops: int = 12
    maximum_candidate_routes: int = 32
    maximum_search_expansions: int = 128

    def validate(self) -> None:
        if not self.source_concept_id or not self.target_concept_id:
            raise PocketIntegrityError("Query endpoints are required")
        if not self.relation_type or len(self.relation_type) > 96:
            raise PocketIntegrityError("Invalid exact relation predicate")
        if not 2 <= self.maximum_member_ps <= 8:
            raise PocketIntegrityError("Member-P budget must be 2..8")
        if not 2 <= self.maximum_hops <= 32:
            raise PocketIntegrityError("Path depth budget must be 2..32")
        if not 1 <= self.maximum_candidate_routes <= 64:
            raise PocketIntegrityError("Route budget must be 1..64")
        if not 1 <= self.maximum_search_expansions <= 1024:
            raise PocketIntegrityError("Expansion budget must be 1..1024")

    def as_dict(self) -> dict:
        return {
            "source_concept_id": self.source_concept_id,
            "target_concept_id": self.target_concept_id,
            "relation_type": self.relation_type,
            "maximum_member_ps": self.maximum_member_ps,
            "maximum_hops": self.maximum_hops,
            "maximum_candidate_routes": self.maximum_candidate_routes,
            "maximum_search_expansions": self.maximum_search_expansions,
        }


def _load_source(pocket: dict) -> tuple[dict, dict, list[dict], dict]:
    if pocket.get("schema") != "verdant.cognitive_pocket.v0":
        raise PocketIntegrityError("Requires read-only native Council-P pocket v0 schema")
    if not isinstance(pocket.get("pocket_id"), str):
        raise PocketIntegrityError("Missing source pocket id")
    to_hash = {k: v for k, v in pocket.items() if k != "pocket_id"}
    if pocket["pocket_id"] != stable_id("cognitive_pocket", to_hash):
        raise PocketIntegrityError("Source pocket content identity is stale or altered")
    p_records = {p["id"]: p for p in pocket["p_snapshots"]}
    concepts = {c["id"]: c for c in pocket["concepts"]}
    if (len(p_records) != len(pocket["p_snapshots"]) or
            set(p_records) != set(pocket["p_ids"]) or
            len(concepts) != len(pocket["concepts"])):
        raise PocketIntegrityError("Unstable or duplicated native P/concept references")
    if not 2 <= len(p_records) <= 8:
        raise PocketIntegrityError("Invalid native P count")
    for c in concepts.values():
        if not c["owner_p_ids"] or not set(c["owner_p_ids"]).issubset(p_records):
            raise PocketIntegrityError("Concept membership escaped native P source")
    for p in p_records.values():
        for cid in p["members"]:
            if cid not in concepts or p["id"] not in concepts[cid]["owner_p_ids"]:
                raise PocketIntegrityError("Missing native P/concept membership")
    records = pocket["current_member_relations"] + pocket["evidenced_cross_p_relations"]
    if len({r["id"] for r in records}) != len(records):
        raise PocketIntegrityError("Duplicate canonical relation ID")
    for r in records:
        if r["source"] not in concepts or r["target"] not in concepts:
            raise PocketIntegrityError("Canonical relation escapes pocket source scope")
        if (not r["evidence_refs"] or
                len(r["evidence_refs"]) != len(set(r["evidence_refs"]))):
            raise PocketIntegrityError("Canonical typed edge evidence closure invalid")
    return p_records, concepts, records, pocket


def _admitted_edges(rows: list[dict], relation_type: str) -> list[dict]:
    return sorted(
        (r for r in rows
         if r["directed"] is True
         and r["status"] in ("supported", "confirmed")
         and r["type"] == relation_type),
        key=lambda r: r["id"],
    )


def _p_routes(p_ids: dict, concepts: dict, rows: list[dict],
              query: CompositionQuery, source_owners: set[str],
              target_owners: set[str]) -> tuple[list[tuple[str, ...]], dict]:
    """P graph routing only sees typed native cross-P edges, not answers."""
    adjacency: dict[str, set[str]] = defaultdict(set)
    inspected = 0
    for r in rows:
        inspected += 1
        src_ps = set(concepts[r["source"]]["owner_p_ids"])
        dst_ps = set(concepts[r["target"]]["owner_p_ids"])
        for a in src_ps:
            for b in dst_ps:
                if a != b:
                    adjacency[a].add(b)
    routes = []
    frontier = deque((sid,) for sid in sorted(source_owners))
    while frontier and len(routes) < query.maximum_candidate_routes:
        path = frontier.popleft()
        tail = path[-1]
        if tail in target_owners and len(path) >= 2:
            routes.append(path)
            continue
        if len(path) >= query.maximum_member_ps:
            continue
        for next_sid in sorted(adjacency[tail]):
            if next_sid not in path:
                frontier.append(path + (next_sid,))
    exhausted_routes = bool(frontier)
    return routes, {
        "p_graph_cross_edge_records_inspected": inspected,
        "p_route_candidates": len(routes),
        "route_enumeration_truncated": exhausted_routes,
    }


def _concept_route(edges: list[dict], concepts: dict, allowed_ps: set[str],
                   query: CompositionQuery, counter: dict) -> tuple[list[dict], bool]:
    """Traverse exact directed canonical edges without interpreting labels."""
    allowed_nodes = {
        cid for cid, c in concepts.items()
        if set(c["owner_p_ids"]).intersection(allowed_ps)
    }
    adj: dict[str, list[dict]] = defaultdict(list)
    for r in edges:
        if r["source"] in allowed_nodes and r["target"] in allowed_nodes:
            adj[r["source"]].append(r)
    for v in adj.values():
        v.sort(key=lambda r: r["id"])
    queue = deque([(query.source_concept_id, ())])
    seen_depth = {query.source_concept_id: 0}
    while queue:
        current, path = queue.popleft()
        if len(path) >= query.maximum_hops:
            continue
        for r in adj[current]:
            counter["edge_expansions"] += 1
            if counter["edge_expansions"] > query.maximum_search_expansions:
                return [], True
            nxt = r["target"]
            extended = (*path, r)
            if nxt == query.target_concept_id:
                return list(extended), False
            if (nxt not in seen_depth or len(extended) < seen_depth[nxt]):
                seen_depth[nxt] = len(extended)
                queue.append((nxt, extended))
    return [], False


def _report(pocket: dict, query: CompositionQuery, disposition: str, *,
            selected: list[str] | None = None,
            witness: list[dict] | None = None,
            metrics: dict | None = None,
            excluded_p_ids: list[str] | None = None) -> dict:
    selected, witness = selected or [], witness or []
    ids = [r["id"] for r in witness]
    evidence = sorted({ref for r in witness for ref in r["evidence_refs"]})
    path = ([query.source_concept_id] +
            [r["target"] for r in witness]) if witness else []
    out = {
        "schema": "verdant.cognitive_pocket_composition.v2",
        "source_pocket_id": pocket["pocket_id"],
        "source_canonical_fingerprint": pocket["canonical_fingerprint"],
        "policy_version": RULE_POLICY_VERSION,
        "rule": {
            "predicate": query.relation_type,
            "transitivity_externally_declared": query.relation_type in ALLOWED_TRANSITIVE_RELATIONS,
            "learnt_by_verdant": False,
        },
        "query": query.as_dict(),
        "disposition": disposition,
        "selected_p_ids": selected,
        "excluded_p_ids": excluded_p_ids or [],
        "witness_concept_path": path,
        "witness_native_relation_ids": ids,
        "witness_canonical_evidence_refs": evidence,
        "candidate_composite": ({
            "source": query.source_concept_id,
            "target": query.target_concept_id,
            "relation_type": query.relation_type,
            "status": "experimental_derived_rule_consequence_only",
            "native_canonical_relation_created": False,
        } if disposition == "supported_composition" else None),
        "metrics": metrics or {},
        "no_obligation_recorded": True,
        "no_canonical_writeback": True,
        "hypothetical_analogy_evidence_used": False,
        "not_autonomously_discovered_rule": True,
    }
    out["evaluation_id"] = _digest(out)
    return out


def inspect_composition(
    pocket: dict,
    query: CompositionQuery,
    *,
    eligible_p_ids: tuple[str, ...] | None = None,
) -> dict:
    """Batched P routing plus exact canonical path verification, never writes.

    Missing witnesses, wrong predicates, reversed bridges and unsupported
    relation statuses are abstentions, never fabricated falsity. The supplied
    query endpoints are legitimate task inputs, NOT precomputed answers.
    """
    query.validate()
    ps, concepts, rows, _ = _load_source(pocket)
    if query.source_concept_id not in concepts or query.target_concept_id not in concepts:
        raise PocketIntegrityError("Query concepts are not original native memory members")
    if query.source_concept_id == query.target_concept_id:
        return _report(pocket, query, "abstain_reflexive_query")
    restriction = set(eligible_p_ids) if eligible_p_ids is not None else set(ps)
    if not restriction or not restriction.issubset(ps) or len(restriction) < 2:
        raise PocketIntegrityError("Candidate P restrictions require 2+ native source Ps")
    excluded = sorted(set(ps) - restriction)
    if query.relation_type not in ALLOWED_TRANSITIVE_RELATIONS:
        return _report(pocket, query, "abstain_rule_not_licensed",
                       excluded_p_ids=excluded)
    source_owners = set(concepts[query.source_concept_id]["owner_p_ids"]) & restriction
    target_owners = set(concepts[query.target_concept_id]["owner_p_ids"]) & restriction
    if not source_owners or not target_owners:
        return _report(pocket, query, "abstain_missing_relevant_p",
                       excluded_p_ids=excluded)

    edges = _admitted_edges(rows, query.relation_type)
    routes, metrics = _p_routes(ps, concepts, edges, query,
                               source_owners, target_owners)
    # A complete, witnessed relation chain is required before claiming a
    # derived conclusion. Admitted member-only paths cannot bridge islands.
    metrics["eligible_canonical_relation_count"] = len(edges)
    metrics["edge_expansions"] = 0
    metrics["all_native_relation_count"] = len(rows)
    for route in routes:
        witness, timed_out = _concept_route(edges, concepts, set(route),
                                            query, metrics)
        if timed_out:
            return _report(pocket, query, "abstain_budget_exhausted",
                           metrics=metrics, excluded_p_ids=excluded)
        if not witness:
            continue
        # A witness must actually use an eligible confirmed cross-P edge and
        # include at least two actual native P members.
        cross_ids = {r["id"] for r in pocket["evidenced_cross_p_relations"]}
        if not any(r["id"] in cross_ids for r in witness):
            continue
        traversed = [query.source_concept_id] + [r["target"] for r in witness]
        if len(set(traversed)) != len(traversed):
            raise PocketIntegrityError("Cyclic witness prohibited")
        # Do not infer when native memory contains a direct status-marked
        # contradiction against ANY used proof edge.
        contested = any(
            r["source"] == edge["source"] and r["target"] == edge["target"]
            and r["type"] == edge["type"]
            and r["status"] == "contradicted"
            for edge in witness for r in rows
        )
        if contested:
            return _report(pocket, query, "abstain_contested_evidence",
                           metrics=metrics, excluded_p_ids=excluded)
        return _report(pocket, query, "supported_composition",
                       selected=list(route), witness=witness,
                       metrics=metrics, excluded_p_ids=excluded)
    return _report(pocket, query, "abstain_missing_supported_path",
                   metrics=metrics, excluded_p_ids=excluded)


def evaluate_control_arms(pocket: dict, query: CompositionQuery,
                          *, wrong_ps: tuple[str, ...]) -> dict:
    """Matched counterfactual pocket snapshots with no canonical mutation.

    Wrong-P restriction, no cross-P bridge, reversed native bridge,
    mismatched predicate, and arbitrary hypothetical alignment metadata.
    Every arm holds the same query, rule and search budget.
    """
    _load_source(pocket)
    baseline = inspect_composition(pocket, query)
    if len(wrong_ps) < 2:
        raise PocketIntegrityError("Wrong-P control must preserve a >=2 P budget")

    def variant(name: str, edit) -> dict:
        p = json.loads(json.dumps(pocket))
        edit(p)
        p.pop("pocket_id")
        p["pocket_id"] = stable_id("cognitive_pocket", p)
        out = inspect_composition(p, query)
        return {"arm": name, "disposition": out["disposition"],
                "witness_ids": out["witness_native_relation_ids"],
                "metrics": out["metrics"],
                "numeric_success": out["disposition"] == "supported_composition",
                "synthetic_pocket_not_canonical": True}

    # A controlled synthetic view whose cross-P edge is removed, not an
    # intervention upon kernel memory or its underlying native checkpoint.
    no_bridge = variant(
        "without_cross_p_relations",
        lambda p: p.__setitem__("evidenced_cross_p_relations", []),
    )
    def reverse(p):
        for r in p["evidenced_cross_p_relations"]:
            if r["directed"]:
                r["source"], r["target"] = r["target"], r["source"]
    reverse_arm = variant("reverse_all_cross_p_relations", reverse)
    # Hypothetical role mappings cannot enter the canonical witness path.
    def scrambled_analogy(p):
        for r in p["hypothetical_role_alignments"]:
            r["mapped_roles"] = list(reversed(r["mapped_roles"]))
    analogy = variant("reverse_analogy_metadata", scrambled_analogy)
    mismatch = variant(
        "cross_bridge_predicate_mismatch",
        lambda p: [r.__setitem__("type", "unrelated") for r in p["evidenced_cross_p_relations"]],
    )
    wrong = inspect_composition(pocket, query, eligible_p_ids=wrong_ps)
    out = {
        "schema": "verdant.cognitive_pocket_composition_controls.v2",
        "source_pocket_id": pocket["pocket_id"],
        "query": query.as_dict(),
        "parent_source_fingerprint": pocket["canonical_fingerprint"],
        "baseline": baseline,
        "controls": [no_bridge, reverse_arm, analogy, mismatch, {
            "arm": "wrong_p_restriction",
            "disposition": wrong["disposition"],
            "witness_ids": wrong["witness_native_relation_ids"],
            "metrics": wrong["metrics"],
            "numeric_success": wrong["disposition"] == "supported_composition",
            "synthetic_pocket_not_canonical": True,
        }],
        "canonical_writeback": False,
        "is_composition_independent_of_analogy": (
            analogy["numeric_success"] == (baseline["disposition"] == "supported_composition")
        ),
        "externally_supplied_rule_and_bridge_not_endogenous": True,
    }
    out["controls_id"] = _digest(out)
    return out
