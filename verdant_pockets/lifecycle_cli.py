"""Opt-in end-to-end pocket lifecycle from native VDK, with no VDK writes.

Run:
 python -m verdant_pockets.lifecycle_cli original.vdk --q-index 0 --out my-pocket.vcpl
 python -m verdant_pockets.lifecycle_cli --verify my-pocket.vcpl

Each run reconstructs genuine Council-promoted P/Q; localized stimuli,
matched controls, numeric daughter partitions, sealed event lineage, lossless
byte compression, and a read-only canonical obligation handoff. No curriculum.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_kernel import VerdantKernel, load_checkpoint

from .experiment import PocketIntegrityError, cultivate_pocket
from .lifecycle import build_lifecycle, save_lifecycle, load_lifecycle
from .obligations import inspect_obligation_handoff


def _summary(lifecycle: dict, handoff: dict) -> dict:
    cohort = lifecycle["matched_cohort"]
    return {
        "lifecycle_id": lifecycle["lifecycle_id"],
        "canonical_fingerprint": lifecycle["parent_pocket"]["canonical_fingerprint"],
        "original_p_count": len(lifecycle["parent_pocket"]["p_ids"]),
        "concept_count": len(lifecycle["parent_pocket"]["concepts"]),
        "source_count": len(cohort["source_p_ids"]),
        "trial_count": len(cohort["trials"]),
        "numeric_role_gain_sources": sorted({
            e["source_p_id"] for e in cohort["effects"]
            if e["arm"] == "role_aligned" and e["measurable_effect"]
        }),
        "experimental_daughter_count": len(lifecycle["experimental_daughters"]["daughters"]),
        "compression_reduction_fraction": lifecycle["compression"]["reduction_fraction"],
        "compression_kind": "zlib_bytes_only_not_structural_learning",
        "native_obligation_candidates": len(handoff["candidate_obligations"]),
        "canonical_memory_modified": False,
        "semantic_composition_demonstrated": False,
    }


def run_native(
    checkpoint: Path, out: Path, *,
    q_index: int = 0, rounds: int = 8, maximum_links_per_p: int = 2,
) -> dict:
    if checkpoint.resolve() == out.resolve():
        raise PocketIntegrityError("Output cannot overwrite the original checkpoint")
    original = checkpoint.read_bytes()
    original_sha = hashlib.sha256(original).hexdigest()
    kernel = VerdantKernel.from_state(load_checkpoint(checkpoint))
    fingerprint = kernel.fingerprint()
    q_options = sorted((
        q for q in kernel.state.layered_structures.values()
        if kernel.layered_structure_is_available(q.layered_structure_id)
    ), key=lambda q: (q.created_cycle, q.layered_structure_id))
    if not 0 <= q_index < len(q_options):
        raise PocketIntegrityError(f"No eligible Q at index {q_index}, found {len(q_options)}")
    q = q_options[q_index]
    pocket = cultivate_pocket(
        kernel, q.member_structure_ids, q_id=q.layered_structure_id,
        rounds=1,  # legacy preview is not used for scientific matched trials
    )
    handoff = inspect_obligation_handoff(kernel, pocket)
    lifecycle = build_lifecycle(
        pocket, rounds=rounds, maximum_links_per_p=maximum_links_per_p
    )
    if kernel.fingerprint() != fingerprint:
        raise PocketIntegrityError("Native kernel changed during lifecycle")
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != original_sha:
        raise PocketIntegrityError("Source checkpoint changed during lifecycle")
    save_lifecycle(out, lifecycle)
    summary = _summary(lifecycle, handoff)
    summary.update({
        "source_checkpoint_sha256": original_sha,
        "output": str(out),
        "no_native_vdk_changes": True,
        "obligation_handoff": handoff,
    })
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="?", help="Source native VDK, read-only")
    parser.add_argument("--q-index", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--max-links", type=int, default=2)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--verify", type=Path, help="Verify a sealed lifecycle without native VDK access")
    args = parser.parse_args(argv)
    if args.verify is not None:
        lifecycle = load_lifecycle(args.verify)
        print(json.dumps({
            "verified": True, "lifecycle_id": lifecycle["lifecycle_id"],
            "history_records": len(lifecycle["history"]),
            "compression_exact": lifecycle["compression"]["lossless_exact_reconstruction"],
            "canonical_fingerprint": lifecycle["parent_pocket"]["canonical_fingerprint"],
        }, indent=2))
        return
    if args.checkpoint is None or args.out is None:
        parser.error("Provide a source checkpoint and --out, or --verify")
    print(json.dumps(run_native(
        args.checkpoint, args.out,
        q_index=args.q_index, rounds=args.rounds,
        maximum_links_per_p=args.max_links,
    ), indent=2))


if __name__ == "__main__":
    main()
