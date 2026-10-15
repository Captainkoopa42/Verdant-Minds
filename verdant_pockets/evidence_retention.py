"""Pocket v2.1: explicit evidence acquisition, scoped replay and retention.

No autonomous sensing, inferred observation truth, native relation creation or
ObligationKernel write. This implements only experimental source-attested
testimony recorded in a separate, hash-linked, create-only sidecar.

Do not call the retained proof "canonical": it is conditional upon a new
EXTERNAL experimental observation, not part of the native Verdant VDK.
"""
from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .composition import (
    ALLOWED_TRANSITIVE_RELATIONS, CompositionQuery, _admitted_edges,
    _concept_route, _load_source, _p_routes, inspect_composition,
)
from .experiment import PocketIntegrityError


SCHEMA = "verdant.cognitive_pocket_evidence_retention.v2.1"
POLICY = "controlled_external_testimony_explicit_transitivity_v2.1"


def _bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(obj: object) -> str:
    return sha256(_bytes(obj)).hexdigest()


def _source_anchor(pocket: dict) -> dict:
    _load_source(pocket)
    return {
        "pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "source_snapshot_sha256": _digest(pocket),
    }


def new_ledger(pocket: dict) -> dict:
    """Create an empty, source-anchored local journal; not a canonical record."""
    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "source": _source_anchor(pocket),
        "events": [],
        "head_hash": _digest(_source_anchor(pocket)),
        "no_native_writeback": True,
    }


def _check_observation(obs: dict, concept_ids: set[str]) -> None:
    expected = {
        "source", "target", "type", "directed", "evidence_kind",
        "source_ref", "observation_body", "observation_sha256",
    }
    if set(obs) != expected:
        raise PocketIntegrityError("Experimental observation fields are incomplete or excessive")
    if (obs["source"] not in concept_ids or obs["target"] not in concept_ids or
            obs["source"] == obs["target"]):
        raise PocketIntegrityError("Observation concept endpoints are not native P members")
    if obs["type"] not in ALLOWED_TRANSITIVE_RELATIONS:
        raise PocketIntegrityError("Observation predicate does not have a licensed composition rule")
    if obs["directed"] is not True:
        raise PocketIntegrityError("Observation must specify directed native concept endpoints")
    if obs["evidence_kind"] != "controlled_external_testimony":
        raise PocketIntegrityError("Only explicit controlled external testimony is admitted in v2.1")
    if not isinstance(obs["source_ref"], str) or not (4 <= len(obs["source_ref"]) <= 200):
        raise PocketIntegrityError("Observation requires an explicit bounded source reference")
    if not isinstance(obs["observation_body"], dict):
        raise PocketIntegrityError("Observation body must be a separate structured claim")
    if obs["observation_body"] != {
        "subject": obs["source"],
        "predicate": obs["type"],
        "object": obs["target"],
        "directed": True,
    }:
        raise PocketIntegrityError("Observation body does not match asserted typed relation")
    if obs["observation_sha256"] != _digest(obs["observation_body"]):
        raise PocketIntegrityError("Observation payload checksum mismatch")


def observation_from_testimony(
    *,
    source: str, target: str, relation_type: str, source_ref: str,
) -> dict:
    body = {
        "subject": source, "predicate": relation_type,
        "object": target, "directed": True,
    }
    return {
        "source": source, "target": target, "type": relation_type,
        "directed": True,
        "evidence_kind": "controlled_external_testimony",
        "source_ref": source_ref,
        "observation_body": body,
        "observation_sha256": _digest(body),
    }


def validate_ledger(ledger: dict, pocket: dict) -> None:
    """Verify source binding and deterministic event chain.

    Hash integrity detects accidental/casual tampering; it does not certify
    external observation truth or provide a digital signature.
    """
    if set(ledger) != {"schema", "policy", "source", "events", "head_hash", "no_native_writeback"}:
        raise PocketIntegrityError("Ledger metadata is invalid")
    if ledger["schema"] != SCHEMA or ledger["policy"] != POLICY or ledger["no_native_writeback"] is not True:
        raise PocketIntegrityError("Unknown or unauthorized evidence journal")
    if ledger["source"] != _source_anchor(pocket):
        raise PocketIntegrityError("Evidence journal is bound to a different native pocket checkpoint")
    concept_ids = {c["id"] for c in pocket["concepts"]}
    if not isinstance(ledger["events"], list) or len(ledger["events"]) > 16:
        raise PocketIntegrityError("Evidence journal exceeded bounded event count")
    prev = _digest(ledger["source"])
    seen = set()
    for index, event in enumerate(ledger["events"]):
        if set(event) != {"sequence", "prev_hash", "observation", "observation_id", "record_hash"}:
            raise PocketIntegrityError("Malformed journal event")
        obs = event["observation"]
        _check_observation(obs, concept_ids)
        eid = _digest(obs)
        if eid in seen:
            raise PocketIntegrityError("Duplicate experimental observation")
        seen.add(eid)
        unsigned = {k: v for k, v in event.items() if k != "record_hash"}
        if (event["sequence"] != index or event["prev_hash"] != prev
                or event["observation_id"] != eid or event["record_hash"] != _digest(unsigned)):
            raise PocketIntegrityError("Evidence history chain is broken")
        prev = event["record_hash"]
    if ledger["head_hash"] != prev:
        raise PocketIntegrityError("Evidence journal head hash mismatch")


def acquire_observation(pocket: dict, ledger: dict, observation: dict) -> dict:
    """Return a new journal state; caller can seal it as new separate file."""
    validate_ledger(ledger, pocket)
    _check_observation(observation, {c["id"] for c in pocket["concepts"]})
    if len(ledger["events"]) >= 16:
        raise PocketIntegrityError("Local evidence acquisition budget exceeded")
    receipt = deepcopy(ledger)
    event = {
        "sequence": len(receipt["events"]),
        "prev_hash": receipt["head_hash"],
        "observation": deepcopy(observation),
        "observation_id": _digest(observation),
    }
    event["record_hash"] = _digest(event)
    receipt["events"].append(event)
    receipt["head_hash"] = event["record_hash"]
    validate_ledger(receipt, pocket)
    return receipt


def gap_certificate(pocket: dict, query: CompositionQuery) -> dict:
    """Describe an unresolved query; NEVER guess the missing bridge itself."""
    original = inspect_composition(pocket, query)
    return {
        "query": query.as_dict(),
        "disposition": original["disposition"],
        "native_eligible_relations": original["metrics"].get("eligible_canonical_relation_count", 0),
        "native_route_candidates": original["metrics"].get("p_route_candidates", 0),
        "candidate_bridge_guessed": False,
        "hypothetical_analogies_count_as_evidence": False,
        "no_obligation_kernel_created": True,
    }


def _witness(
    pocket: dict, ledger: dict, query: CompositionQuery,
) -> tuple[list[dict], list[str], dict, str]:
    ps, concepts, native, _ = _load_source(pocket)
    native_base = _admitted_edges(native, query.relation_type)
    overlay = []
    for event in ledger["events"]:
        obs = event["observation"]
        if obs["type"] != query.relation_type:
            continue
        overlay.append({
            "id": "experimental_observation_" + event["observation_id"][:24],
            "source": obs["source"], "target": obs["target"],
            "type": obs["type"], "directed": True,
            "evidence_refs": [],
            "origin": "experimental_attestation_only",
            "observation_id": event["observation_id"],
        })
    # Do not trust a simulated bridge to manufacture a canonical native row.
    for r in native_base:
        r.setdefault("origin", "native_canonical")
    admitted = native_base + overlay
    source_owner = set(concepts[query.source_concept_id]["owner_p_ids"])
    target_owner = set(concepts[query.target_concept_id]["owner_p_ids"])
    routes, metrics = _p_routes(ps, concepts, admitted, query, source_owner, target_owner)
    metrics["native_eligible_relations"] = len(native_base)
    metrics["external_observations_eligible"] = len(overlay)
    metrics["edge_expansions"] = 0
    metrics["flat_edge_adjacency_size"] = len(admitted)
    if metrics["route_enumeration_truncated"]:
        # A positive witness may be proven using inspected routes; a negative
        # answer with truncated routes MUST be classified as inconclusive.
        truncated = True
    else:
        truncated = False
    for path in routes:
        witness, budgeted = _concept_route(
            admitted, concepts, set(path), query, metrics,
        )
        if budgeted:
            return [], [], metrics, "abstain_budget_exhausted"
        if not witness:
            continue
        if len(witness) < 2:
            return [], [], metrics, "abstain_direct_observation_not_composition"
        if not any(r.get("origin") == "experimental_attestation_only" for r in witness):
            # Caller should use v2 native composition for canonical-only proof.
            continue
        selected = list(path)
        contested = any(
            (r["source"], r["target"], r["type"]) ==
            (edge["source"], edge["target"], edge["type"])
            and r["status"] in ("rejected", "contradicted")
            for edge in witness for r in native
        )
        reverse_observation = any(
            x["source"] == y["target"] and x["target"] == y["source"] and x["type"] == y["type"]
            for x in overlay for y in overlay if x is not y
        )
        if contested or reverse_observation:
            return [], [], metrics, "abstain_contested_evidence"
        return witness, selected, metrics, "supported_experimental_composition"
    return [], [], metrics, ("abstain_route_budget_incomplete" if truncated
                             else "abstain_missing_supported_path")


def compose_with_evidence(pocket: dict, ledger: dict, query: CompositionQuery) -> dict:
    """Proof over native records + separately named EXTERNAL experimental data."""
    query.validate()
    validate_ledger(ledger, pocket)
    ps, concepts, native, _ = _load_source(pocket)
    if query.source_concept_id not in concepts or query.target_concept_id not in concepts:
        raise PocketIntegrityError("Unknown native source concept in query")
    if query.relation_type not in ALLOWED_TRANSITIVE_RELATIONS:
        status = "abstain_rule_not_licensed"
        witness, selected, metrics = [], [], {}
    elif query.source_concept_id == query.target_concept_id:
        status = "abstain_reflexive_query"
        witness, selected, metrics = [], [], {}
    else:
        witness, selected, metrics, status = _witness(pocket, ledger, query)
    result = {
        "schema": "verdant.cognitive_pocket_retained_composition.v2.1",
        "policy": POLICY,
        "source_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "journal_head_hash": ledger["head_hash"],
        "query": query.as_dict(),
        "disposition": status,
        "selected_p_ids": selected,
        "witness_native_relation_ids": [r["id"] for r in witness if r.get("origin") == "native_canonical"],
        "witness_canonical_evidence_refs": sorted({
            e for r in witness if r.get("origin") == "native_canonical"
            for e in r["evidence_refs"]
        }),
        "witness_external_observation_ids": [
            r["observation_id"] for r in witness
            if r.get("origin") == "experimental_attestation_only"
        ],
        "witness_path": ([query.source_concept_id] + [r["target"] for r in witness]) if witness else [],
        "witness_edge_origins": [r["origin"] for r in witness],
        "candidate_composite": ({
            "source": query.source_concept_id,
            "target": query.target_concept_id,
            "relation_type": query.relation_type,
            "status": "conditional_on_external_experimental_testimony",
            "native_canonical_claim_created": False,
            "external_ground_truth_independently_verified": False,
        } if status == "supported_experimental_composition" else None),
        "metrics": metrics,
        "no_canonical_writeback": True,
        "no_obligation_kernel_created": True,
        "rule_externally_declared_not_learned": True,
        "numeric_activity_not_used_as_evidence": True,
    }
    result["result_id"] = _digest(result)
    return result


def flat_graph_control(pocket: dict, ledger: dict, query: CompositionQuery) -> dict:
    """Flat canonical + experimental evidence BFS under the same typed rule.

    Counts inspected edges and expansions honestly; not a timing benchmark.
    """
    query.validate()
    validate_ledger(ledger, pocket)
    _ps, concepts, native, _ = _load_source(pocket)
    if query.source_concept_id not in concepts or query.target_concept_id not in concepts:
        raise PocketIntegrityError("Unknown concept")
    if query.relation_type not in ALLOWED_TRANSITIVE_RELATIONS:
        return {"disposition": "abstain_rule_not_licensed", "edge_expansions": 0, "witness": []}
    admitted = _admitted_edges(native, query.relation_type)
    # Unlike pocket routing, this searches the entire native concept graph.
    for event in ledger["events"]:
        obs = event["observation"]
        if obs["type"] == query.relation_type:
            admitted.append({
                "id": "experimental_observation_" + event["observation_id"][:24],
                "source": obs["source"], "target": obs["target"],
                "type": obs["type"], "origin": "experimental_attestation_only",
                "observation_id": event["observation_id"],
            })
    if query.source_concept_id == query.target_concept_id:
        return {"disposition": "abstain_reflexive_query", "edge_expansions": 0, "witness": []}
    graph: dict[str, list[dict]] = defaultdict(list)
    for edge in admitted:
        graph[edge["source"]].append(edge)
    for refs in graph.values():
        refs.sort(key=lambda r: r["id"])
    queue = deque([(query.source_concept_id, ())])
    seen = {query.source_concept_id}
    count = 0
    while queue:
        at, walked = queue.popleft()
        if len(walked) >= query.maximum_hops:
            continue
        for edge in graph[at]:
            count += 1
            if count > query.maximum_search_expansions:
                return {"disposition": "abstain_budget_exhausted", "edge_expansions": count, "witness": []}
            chain = (*walked, edge)
            if edge["target"] == query.target_concept_id:
                if len(chain) < 2:
                    return {"disposition": "abstain_direct_observation_not_composition",
                            "edge_expansions": count, "witness": []}
                if not any(x.get("origin") == "experimental_attestation_only" for x in chain):
                    return {"disposition": "native_only_proof_outside_acquisition_scope",
                            "edge_expansions": count, "witness": []}
                return {"disposition": "supported_experimental_composition",
                        "edge_expansions": count, "witness": [x["id"] for x in chain],
                        "eligible_edges": len(admitted)}
            if edge["target"] not in seen:
                seen.add(edge["target"])
                queue.append((edge["target"], chain))
    return {"disposition": "abstain_missing_supported_path", "edge_expansions": count,
            "witness": [], "eligible_edges": len(admitted)}


def save_ledger(path: Path, ledger: dict, pocket: dict) -> None:
    """Create-only sidecar; the file need not be in a native VDK directory."""
    validate_ledger(ledger, pocket)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(_bytes(ledger))


def load_ledger(path: Path, pocket: dict) -> dict:
    raw = Path(path).read_bytes()
    try:
        journal = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PocketIntegrityError("Unreadable evidence journal") from exc
    if raw != _bytes(journal):
        raise PocketIntegrityError("Evidence journal bytes not canonical")
    validate_ledger(journal, pocket)
    return journal
