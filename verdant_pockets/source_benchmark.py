"""Auditable v2.3 fixed-source scaling/overhead benchmark.

The same genuine Council-P/Q source memory and the same two corroborated
bridge observations are held constant. We add 0..64 independently *valid*
but SINGLE-LINEAGE distractor observation statements. Distractors do not
become proof edges, and the flat reference gets exactly the same admissible
corroborated edge view. This is NOT a neural efficiency demonstration.
"""
from __future__ import annotations

from itertools import permutations

from .composition import CompositionQuery
from .corroboration import attest, inspect_corroboration, new_provenance
from .evidence_retention import observation_from_testimony
from .experiment import PocketIntegrityError


LEVELS = (0, 8, 16, 32, 64)


def benchmark_scale(pocket: dict, names: dict, *, native_kernel=None) -> dict:
    registry={
        "bench-root-a":{"lineage_family":"bench-independent-family-a","description":"controlled attestation A"},
        "bench-root-b":{"lineage_family":"bench-independent-family-b","description":"controlled attestation B"},
        "bench-noise":{"lineage_family":"bench-copied-single-root","description":"controlled unrelated root"},
    }
    original=new_provenance(pocket,registry)
    for origin in ("bench-root-a","bench-root-b"):
        original=attest(pocket,original,observation_from_testimony(
            source=names["r4"],target=names["s1"],relation_type="precedes",
            source_ref=origin,
        ),source_id=origin)

    # 12 genuinely promoted native concepts; none of these unrelated
    # statements may be used without a second declared lineage.
    allowed=sorted(names)
    candidate_edges=[
        (a,b) for a,b in permutations(allowed,2)
        if (a,b) not in {("r4","s1"),("s1","r4"),("r1","s4")}
        and a[0]!=b[0]
    ]
    if len(candidate_edges)<64:
        raise PocketIntegrityError("Not enough unique held-out decoy concept pairs")
    growing=original
    reports=[]
    previous=0
    for n in LEVELS:
        for a,b in candidate_edges[previous:n]:
            growing=attest(pocket,growing,observation_from_testimony(
                source=names[a],target=names[b],relation_type="precedes",
                source_ref="bench-noise",
            ),source_id="bench-noise")
        previous=n
        result=inspect_corroboration(
            pocket,growing,
            CompositionQuery(names["r1"],names["s4"],maximum_hops=9),
            native_kernel=native_kernel,
        )
        if result["disposition"]!="supported_experimental_composition":
            raise PocketIntegrityError("Uncorroborated noise spoiled true corroborated claim")
        if result["flat_baseline"]["disposition"]!=result["disposition"]:
            raise PocketIntegrityError("Pocket and flat reference became inconsistent")
        if len(result["reconciliation"]["corroborated_claims"])!=1:
            raise PocketIntegrityError("An unrelated singleton distractor was laundered as independent")
        reports.append({
            "unrelated_attestations":n,
            "total_attestations":n+2,
            "eligible_experimental_bridges":1,
            "source_p_count":len(pocket["p_ids"]),
            "native_concept_count":len(pocket["concepts"]),
            "pocket_disposition":result["disposition"],
            "flat_disposition":result["flat_baseline"]["disposition"],
            "pocket_proof_edge_expansions":result["cost_accounting"]["pocket_edge_expansions"],
            "pocket_p_route_inspections":result["cost_accounting"]["p_route_relation_inspections"],
            "pocket_total_recorded_graph_work":(
                result["cost_accounting"]["pocket_edge_expansions"]+
                result["cost_accounting"]["p_route_relation_inspections"]
            ),
            "flat_proof_edge_expansions":result["cost_accounting"]["flat_edge_expansions"],
            "provenance_attestations_replayed":result["cost_accounting"]["attestation_records_replayed"],
            "registry_source_records":result["cost_accounting"]["source_lineage_registry_entries"],
        })
    return {
        "schema":"verdant.cognitive_pocket_provenance_scaling.v2.3",
        "source_pocket_id":pocket["pocket_id"],
        "levels":list(LEVELS),
        "results":reports,
        "same_native_source_every_level":True,
        "live_native_negative_relation_scan":native_kernel is not None,
        "distractors_eligible_without_corroboration":False,
        "equal_admissible_evidence_for_flat_and_pocket":True,
        "measured_wall_clock_speedup":False,
        "pocket_advantage_demonstrated":False,
        "source_count_held_constant":True,
        "description":"controlled scaling of uncorroborated distractor testimony, not large native P/Q graph scale",
    }
