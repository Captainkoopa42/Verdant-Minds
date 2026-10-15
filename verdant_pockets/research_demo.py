"""Explicitly teacher-staged native Council-P/Q composition demonstration.

Generates three real promoted native P structures and a Council-promoted Q
inside a NEW disposable native kernel; then supplies individual typed
relations as external TEST-HARNESS testimony. The final cross-memory answer
is NEVER taught. This demo is NOT spontaneous rule learning and never
uses or changes the user's saved VDK.

Run: python -m verdant_pockets.research_demo --out research-demo.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_kernel import (
    EvidenceKind, ExperienceCommand, RelationStatus, VerdantKernel,
)
from verdant_development import VerdantDevelopmentPipeline
from verdant_structures import VerdantStructurePipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline

from .composition import CompositionQuery, inspect_composition, evaluate_control_arms
from .curriculum import grade_frozen_tasks
from .experiment import cultivate_pocket


def _experience(event: str, concept_labels: tuple[str, ...], context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event, source_ref="pocket-v2:teacher-controlled",
        modality="text",
        payload_sha256=hashlib.sha256((event + ":" + ":".join(concept_labels)).encode()).hexdigest(),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=concept_labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_teacher_primitive_only": True},
        metadata={"context_id": context},
    )


def make_native_teaching_corpus():
    kernel = VerdantKernel(seed=27182, state_dim=16, run_label="pocket-v2-teacher-only-demo")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=4, maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25,
        minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
    )
    kernel.update_hierarchy_policy(
        minimum_interaction_events=3,
        minimum_evidence_events=6,
        layered_probe_similarity=0.985,
    )
    family = []
    development = VerdantDevelopmentPipeline()
    for prefix in ("r", "s", "t"):
        edges = tuple((f"{prefix}{i}", f"{prefix}{i+1}") for i in range(1, 4))
        for repeat in range(2):
            for index, edge in enumerate(edges):
                development.advance(
                    kernel, _experience(
                        f"{prefix}-{repeat}-{index}", edge,
                        context=f"controlled-{prefix}-{repeat%2}",
                    ),
                )
        expected = {f"{prefix}{i}" for i in range(1, 5)}
        candidate = max((
            item for item in kernel.state.structure_candidates.values()
            if {kernel.state.concepts[c].normalized_label for c in item.member_concept_ids} == expected
        ), key=lambda item: item.occurrence_count)
        family.append(VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event.structure_id)

    interaction = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    for p_id in family:
        interaction.interact(kernel, p_id)
        hierarchy.observe(kernel)
    Q = next(
        item for item in kernel.state.hierarchy_candidates.values()
        if set(item.member_structure_ids) == set(family)
    )
    q_id = hierarchy.promote(kernel, Q.candidate_id).event.layered_structure_id
    names = {c.normalized_label: cid for cid, c in kernel.state.concepts.items()}
    primitive_relations = []
    for i, (prefix, p_id) in enumerate(zip("rst", family)):
        predicate = "precedes" if i < 2 else "supports"
        for j in range(1, 4):
            r = kernel.propose_relation(
                names[f"{prefix}{j}"], names[f"{prefix}{j+1}"], predicate,
                evidence_refs=kernel.state.structures[p_id].evidence_refs,
                directed=True, status=RelationStatus.SUPPORTED,
                confidence=0.85, weight=0.85,
            )
            primitive_relations.append(r.relation_id)
    bridge = kernel.propose_relation(
        names["r4"], names["s1"], "precedes",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs,
        directed=True, status=RelationStatus.SUPPORTED,
        confidence=0.85, weight=0.85,
    )
    primitive_relations.append(bridge.relation_id)
    return kernel, tuple(family), q_id, names, primitive_relations


def run_controlled_demo() -> dict:
    kernel, family, q_id, names, primitives = make_native_teaching_corpus()
    before = kernel.fingerprint()
    pocket = cultivate_pocket(kernel, family, q_id=q_id, rounds=1)
    direct = CompositionQuery(names["r1"], names["s4"], maximum_hops=9)
    main = inspect_composition(pocket, direct)
    controls = evaluate_control_arms(
        pocket, direct, wrong_ps=(family[0], family[2]),
    )
    tasks = [
        ("01_unprovided_full_chain", "r1", "s4", "precedes", True),
        ("02_unprovided_short_chain", "r3", "s2", "precedes", True),
        ("03_reversed", "s4", "r1", "precedes", False),
        ("04_wrong_family", "r1", "t4", "precedes", False),
        ("05_wrong_predicate", "r1", "s4", "supports", False),
        ("06_wrong_direction", "s1", "r4", "precedes", False),
    ]
    queries = [
        {"task_id": task_id, "source_concept_id": names[fr],
         "target_concept_id": names[to], "relation_type": predicate,
         "maximum_hops": 9}
        for task_id, fr, to, predicate, _ in tasks
    ]
    grades = {
        task_id: {"expected": "supported_composition" if positive else "abstain"}
        for task_id, _fr, _to, _predicate, positive in tasks
    }
    scored = grade_frozen_tasks(pocket, queries, grades)
    if kernel.fingerprint() != before:
        raise RuntimeError("Read-only demonstration changed the native source")
    output = {
        "schema": "verdant.cognitive_pocket_native_teacher_demo.v2",
        "source_canonical_fingerprint": before,
        "native_p_ids": list(family),
        "promoted_q_id": q_id,
        "external_primitive_testimony_count": len(primitives),
        "external_bridge_count": 1,
        "final_answer_never_taught": True,
        "transitivity_rule_externally_supplied": True,
        "direct_composition": main,
        "matched_controls": controls,
        "frozen_curriculum": scored,
        "no_native_canonical_result_written": True,
        "not_spontaneous_composition_rule_discovery": True,
        "not_a_saved_checkpoint_trial": True,
    }
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run_controlled_demo()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({
        "output": str(args.out),
        "native_p": len(result["native_p_ids"]),
        "council_q": result["promoted_q_id"],
        "composite_disposition": result["direct_composition"]["disposition"],
        "native_witness_relations": len(result["direct_composition"]["witness_native_relation_ids"]),
        "frozen_curriculum_grades": result["frozen_curriculum"]["confusion"],
        "no_original_vdk_touched": True,
    }, indent=2))


if __name__ == "__main__":
    main()
