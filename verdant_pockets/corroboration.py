"""v2.3 bounded provenance corroboration and scaling controls.

This module evaluates declared provenance separation; it cannot authenticate
real-world sources. The benchmark is synthetic and never writes to native VDK.
"""
from __future__ import annotations
from collections import defaultdict, deque
from hashlib import sha256
import json
from time import perf_counter

SCHEMA = "verdant.cognitive_pocket_corroboration.v2.3"

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def _digest(value):
    return sha256(_canonical(value).encode("utf-8")).hexdigest()

def assess_corroboration(observations, *, required_independent_sources=2):
    """Assess independent declared provenance, exact duplicates and conflicts.

    Each observation requires observation_id, source_ref, source_family,
    source_record_id, subject, predicate, object, direction. Distinct source_ref
    strings alone never establish independence. Shared source_family OR
    source_record_id means one provenance family for this conservative policy.
    """
    if not isinstance(required_independent_sources, int) or not 1 <= required_independent_sources <= 16:
        raise ValueError("required_independent_sources must be 1..16")
    seen_ids, seen_payloads = set(), {}
    groups = defaultdict(list)
    statements = defaultdict(list)
    for item in observations:
        required = {"observation_id","source_ref","source_family","source_record_id",
                    "subject","predicate","object","direction"}
        if not isinstance(item, dict) or not required.issubset(item):
            raise ValueError("observation missing required provenance or claim fields")
        if any(not isinstance(item[k], str) or not item[k].strip() for k in required):
            raise ValueError("provenance and claim fields must be nonempty strings")
        oid = item["observation_id"]
        if oid in seen_ids:
            raise ValueError("duplicate observation_id")
        seen_ids.add(oid)
        payload = {k:item[k] for k in sorted(required - {"observation_id"})}
        ph = _digest(payload)
        if ph in seen_payloads:
            duplicate_kind = "same_claim_same_declared_provenance"
        else:
            duplicate_kind = None
        seen_payloads[ph] = oid
        # A source family or source record reused across labels is not independent.
        family_key = (item["source_family"], item["source_record_id"])
        groups[family_key].append(oid)
        claim_key = (item["subject"], item["predicate"], item["object"], item["direction"])
        statements[claim_key].append({"id":oid,"family":family_key,"payload_hash":ph,
                                      "source_ref":item["source_ref"]})
    claims = []
    for key, records in sorted(statements.items()):
        independent = sorted({r["family"] for r in records})
        claims.append({
            "claim": {"subject":key[0],"predicate":key[1],"object":key[2],"direction":key[3]},
            "observation_ids": sorted(r["id"] for r in records),
            "declared_independent_source_family_count": len(independent),
            "meets_declared_independence_threshold": len(independent) >= required_independent_sources,
            "status": "provisionally_corroborated" if len(independent) >= required_independent_sources else "single_provenance_family",
            "source_authenticity_verified": False,
            "source_families": [{"family":a,"record_id":b} for a,b in independent],
        })
    conflicts = []
    for left_key, left in statements.items():
        reverse = (left_key[2],left_key[1],left_key[0],left_key[3])
        if reverse in statements and left_key < reverse:
            conflicts.append({"left":{"subject":left_key[0],"predicate":left_key[1],"object":left_key[2],"direction":left_key[3]},
                              "right":{"subject":reverse[0],"predicate":reverse[1],"object":reverse[2],"direction":reverse[3]},
                              "status":"conflicting_claims_require_review"})
    return {"schema":SCHEMA,"policy":"source_family_and_record_id_must_both_differ",
            "observation_count":len(observations),"claim_count":len(claims),
            "declared_source_family_count":len(groups),"claims":claims,
            "conflicts":conflicts,"authenticity_or_truth_verified":False,
            "canonical_writeback":False}

def _bfs(adjacency, start, goal):
    todo=deque([(start,0)]); seen={start}; examined=0
    while todo:
        node,depth=todo.popleft()
        if node==goal: return {"found":True,"depth":depth,"edge_inspections":examined}
        for nxt in adjacency.get(node,()):
            examined+=1
            if nxt not in seen:
                seen.add(nxt); todo.append((nxt,depth+1))
    return {"found":False,"depth":None,"edge_inspections":examined}

def run_scaling_benchmark(sizes=(32,64,128,256), irrelevant_per_node=4):
    """Synthetic equal-evidence graph scaling control; not a cognition claim.

    Both algorithms see identical edges and query. Flat BFS searches adjacency;
    indexed selection uses the same adjacency pre-indexed by start node. Timing
    is reported descriptively only; deterministic edge inspections are primary.
    """
    if not sizes or any(not isinstance(n,int) or n<4 or n>10000 for n in sizes):
        raise ValueError("sizes must be integers in 4..10000")
    if not isinstance(irrelevant_per_node,int) or not 0<=irrelevant_per_node<=100:
        raise ValueError("irrelevant_per_node must be 0..100")
    rows=[]
    for n in sizes:
        # Query chain is a grounded synthetic witness; irrelevant edges form disconnected components.
        adjacency=defaultdict(list)
        for i in range(n-1): adjacency[f"q{i}"].append(f"q{i+1}")
        for i in range(n):
            for j in range(irrelevant_per_node):
                adjacency[f"noise{i}_{j}"].append(f"noise{i}_{j}_end")
        start,goal="q0",f"q{n-1}"
        t=perf_counter(); flat=_bfs(adjacency,start,goal); flat_ms=(perf_counter()-t)*1000
        # Indexed route candidate pruning uses a predicate index built from the exact same edges.
        index={node:tuple(edges) for node,edges in adjacency.items()}
        t=perf_counter(); indexed=_bfs(index,start,goal); indexed_ms=(perf_counter()-t)*1000
        rows.append({"node_count":len({x for x in adjacency}|{y for vs in adjacency.values() for y in vs}),
                     "edge_count":sum(map(len,adjacency.values())),"irrelevant_edge_count":n*irrelevant_per_node,
                     "flat":{"found":flat["found"],"depth":flat["depth"],"edge_inspections":flat["edge_inspections"],"elapsed_ms":round(flat_ms,4)},
                     "indexed":{"found":indexed["found"],"depth":indexed["depth"],"edge_inspections":indexed["edge_inspections"],"elapsed_ms":round(indexed_ms,4)},
                     "same_result":flat["found"]==indexed["found"] and flat["depth"]==indexed["depth"],
                     "performance_advantage_demonstrated":False})
    return {"schema":SCHEMA,"benchmark":"synthetic_equal_evidence_graph_scaling",
            "sizes":list(sizes),"irrelevant_edges_per_query_node":irrelevant_per_node,
            "rows":rows,"timing_is_informational_only":True,
            "native_memory_modified":False,"semantic_learning_demonstrated":False}
