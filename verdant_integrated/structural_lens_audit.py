"""Read-only P relation-discrimination and Q-cost audit of an existing native VDK.

No teaching, no Council operation, no Q ablation, no output-file modification.
Report retrospective cross-sectional costs, NOT measured wall-clock speed or
prospective held-out correctness. Native Q remains topology-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path

from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction.relation_lens import RelationAwareLens
from verdant_kernel import VerdantKernel, load_checkpoint


def audit_checkpoint(path: str | Path, *, max_pairs: int = 66) -> dict:
    if not 1 <= max_pairs <= 200:
        raise ValueError("max_pairs must be within 1..200")
    path = Path(path)
    initial_bytes = path.read_bytes()
    kernel = VerdantKernel.from_state(load_checkpoint(path))
    original = kernel.fingerprint()
    lens = RelationAwareLens()
    groups = []
    counts = Counter()
    for left, right in list(combinations(sorted(kernel.state.structures), 2))[:max_pairs]:
        result = lens.inspect(kernel, left, right)
        counts["total_pairs"] += 1
        counts["native_topology_accept" if result["baseline_accept"] else "native_topology_reject"] += 1
        counts["typed_" + result["verdict"]] += 1
        if result["baseline_accept"] and result["verdict"] == "reject":
            counts["baseline_positive_typed_negative"] += 1
        groups.append({
            "source_p": left, "target_p": right,
            "baseline_topology_score": result["baseline_topology_score"],
            "baseline_accept": result["baseline_accept"],
            "typed_f1": result["typed_f1"],
            "verdict": result["verdict"],
            "reason": result["reason"],
            "source_relation_count": result["source_relation_count"],
            "target_relation_count": result["target_relation_count"],
        })

    native_q = VerdantHierarchyPipeline()
    retrospective = []
    for sid, structure in sorted(kernel.state.structures.items()):
        earlier = [
            q for q in kernel.state.layered_structures.values()
            if q.created_cycle < structure.created_cycle
            and sid not in q.member_structure_ids
        ]
        if not earlier:
            continue
        report = native_q.inspect_probe(kernel, sid)
        chosen = kernel.state.layered_structures.get(report.layered_structure_id)
        chosen_earlier = chosen is not None and chosen.created_cycle < structure.created_cycle
        retrospective.append(dict(
            query_p=sid, query_p_created_cycle=structure.created_cycle,
            earlier_q_available=len(earlier), selected_q=report.layered_structure_id,
            selected_q_predates_query=chosen_earlier,
            disposition=report.disposition.value,
            native_q_comparison_work=report.cost.comparison_work,
            native_baseline_comparison_work=report.baseline_cost.comparison_work,
            native_q_less_work=(
                chosen_earlier
                and report.cost.comparison_work < report.baseline_cost.comparison_work
            ),
            compressed_matched_members=report.cost.matched_members,
            native_baseline_matched_members=report.baseline_cost.matched_members,
            # Retrospective full checkpoint includes later Ps/possibly later Qs.
            prospective_temporal_isolation=False,
            execution_time_benchmark=False,
        ))

    if kernel.fingerprint() != original or path.read_bytes() != initial_bytes:
        raise RuntimeError("Structural discrimination audit changed the native checkpoint")
    return dict(
        checkpoint_sha256=hashlib.sha256(initial_bytes).hexdigest(),
        canonical_fingerprint=original,
        native_p=len(kernel.state.structures),
        native_q=len(kernel.state.layered_structures),
        relation_lens="current_canonical_member_relations_exact_types_and_directions",
        promotion_or_native_hierarchy_mutation=False,
        synthetic_ground_truth_not_inferred_from_checkpoint=True,
        pair_sampling="lexical_p_id_order_first_n_pairs_no_probability_claim",
        pairs_available=len(kernel.state.structures)*(len(kernel.state.structures)-1)//2,
        pair_counts=dict(sorted(counts.items())),
        pair_details=groups,
        native_retrospective_q_work=retrospective,
        audit_only=True,
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("--max-pairs", type=int, default=66)
    args = parser.parse_args(argv)
    print(json.dumps(audit_checkpoint(args.checkpoint, max_pairs=args.max_pairs),
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
