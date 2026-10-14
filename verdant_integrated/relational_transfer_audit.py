"""Read-only relational Q transfer audit over a native checkpoint.

No teaching, promotions, canonical state changes, source-file edits or Q
ablation. Output measurements reflect retrospective final-checkpoint state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_hierarchy.relational_abstraction import RelationalAbstractionProbe
from verdant_kernel import VerdantKernel, load_checkpoint


def audit_checkpoint(checkpoint: str | Path, *, max_queries: int = 12) -> dict:
    if not 1 <= max_queries <= 100:
        raise ValueError("max_queries must be from 1 to 100")
    p = Path(checkpoint)
    original_bytes = p.read_bytes()
    kernel = VerdantKernel.from_state(load_checkpoint(p))
    original_fingerprint = kernel.fingerprint()
    observer = RelationalAbstractionProbe()

    rows = []
    for sid in sorted(kernel.state.structures)[:max_queries]:
        if not kernel.structure_is_available(sid):
            continue
        report = observer.inspect(kernel, sid)
        before_query_q = sum(
            q.created_cycle < kernel.state.structures[sid].created_cycle
            for q in kernel.state.layered_structures.values()
        )
        ref = report["exhaustive"]
        keyed = report["p_keyed"]
        q = report["q_overlay"]
        rows.append(dict(
            query_p=sid,
            query_created_cycle=report["query_created_cycle"],
            native_q_older_than_query=before_query_q,
            q_overlay_groups=q["q_groups"],
            q_ids=q["q_ids_used"],
            exactly_identical_verdicts=report["all_verdicts_identical"],
            exact_typed_matches=len(ref["accepted_ids"]),
            rejected_pairs=ref["rejected_count"],
            abstained_pairs=len(ref["abstained_ids"]),
            exhaustive_exact_verifications=ref["exact_verifications"],
            p_keyed_exact_verifications=keyed["exact_verifications"],
            q_overlay_exact_verifications=q["exact_verifications"],
            p_keyed_key_comparisons=keyed["key_comparisons"],
            q_overlay_key_comparisons=q["key_comparisons"],
            q_overlay_member_candidates_in_current_final_state=q["q_groups"],
            q_overlay_decreases_key_checks_vs_p_only=(
                q["key_comparisons"] < keyed["key_comparisons"]
            ),
            note="Final checkpoint state only; later Q/P may leak into retrospective query",
        ))

    if p.read_bytes() != original_bytes or kernel.fingerprint() != original_fingerprint:
        raise RuntimeError("Relational-transfer audit mutated checkpoint or native state")
    return dict(
        native_checkpoint_sha256=hashlib.sha256(original_bytes).hexdigest(),
        native_fingerprint=original_fingerprint,
        promoted_p=len(kernel.state.structures),
        promoted_q=len(kernel.state.layered_structures),
        report="exact typed-role Q overlay versus P-only keyed and exhaustive controls",
        strict_typed_role_threshold=1.0,
        query_count=len(rows),
        all_query_verdicts_preserved=all(x["exactly_identical_verdicts"] for x in rows),
        runtime_speedup_claimed=False,
        counting_index_build_or_cache_cost_in_query=False,
        time_isolated_prospective_trial=False,
        independent_semantic_truth_test=False,
        native_state_mutated=False,
        checkpoint_modified=False,
        queries=rows,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("--max-queries", type=int, default=12)
    args = parser.parse_args(argv)
    print(json.dumps(audit_checkpoint(
        args.checkpoint, max_queries=args.max_queries
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
