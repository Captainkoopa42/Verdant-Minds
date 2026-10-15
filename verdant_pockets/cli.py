"""Read-only native VDK cognitive-pocket cultivation export.

Usage:
    python -m verdant_pockets.cli original.vdk --q-index 0 --out pocket.json

Never overwrites an existing output, never mutates a VDK, runs NO curriculum,
and makes no semantic/canonical/obligation promotion claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_kernel import VerdantKernel, load_checkpoint

from .experiment import PocketIntegrityError, cultivate_pocket


def export_pocket(checkpoint: Path, out: Path, *, q_index: int, rounds: int) -> dict:
    original = checkpoint.read_bytes()
    if checkpoint.resolve() == out.resolve():
        raise PocketIntegrityError("Cannot overwrite a native checkpoint")
    kernel = VerdantKernel.from_state(load_checkpoint(checkpoint))
    before = kernel.fingerprint()
    available_q = sorted(
        (
            q for q in kernel.state.layered_structures.values()
            if kernel.layered_structure_is_available(q.layered_structure_id)
        ),
        key=lambda q: (q.created_cycle, q.layered_structure_id),
    )
    if not 0 <= q_index < len(available_q):
        raise PocketIntegrityError(
            f"No native available Q at index {q_index}; found {len(available_q)}"
        )
    q = available_q[q_index]
    pocket = cultivate_pocket(
        kernel, q.member_structure_ids,
        q_id=q.layered_structure_id, rounds=rounds,
    )
    if hashlib.sha256(checkpoint.read_bytes()).digest() != hashlib.sha256(original).digest():
        raise PocketIntegrityError("Source VDK bytes changed during cultivation")
    if kernel.fingerprint() != before:
        raise PocketIntegrityError("Source kernel fingerprint changed")
    result = {
        "schema": "verdant.cognitive_pocket_export.v0",
        "source_checkpoint_sha256": hashlib.sha256(original).hexdigest(),
        "source_checkpoint_fingerprint": before,
        "source_q_index": q_index,
        "pocket": pocket,
        "no_canonical_changes": True,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8")
    # Exclusive create. Atomic crash durability is explicitly NOT claimed.
    with out.open("xb") as file:
        file.write(payload)
    return {
        "source_sha256": result["source_checkpoint_sha256"],
        "q_id": q.layered_structure_id,
        "pocket_id": pocket["pocket_id"],
        "p_count": len(pocket["p_snapshots"]),
        "concept_count": len(pocket["concepts"]),
        "typed_member_relation_count": len(pocket["current_member_relations"]),
        "native_cross_p_relation_count": len(pocket["evidenced_cross_p_relations"]),
        "hypothetical_role_alignment_count": len(pocket["hypothetical_role_alignments"]),
        "canonical_two_edge_cross_p_walks": len(pocket["evidenced_cross_p_walks"]),
        "grammars": len(pocket["grammar_inventory"]),
        "rounds": len(pocket["local_rounds"]),
        "output_path": str(out),
        "original_vdk_unchanged": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, help="Existing native VDK; strictly read-only")
    parser.add_argument("--q-index", type=int, default=0, help="0 first promoted Q; 1 second, etc.")
    parser.add_argument("--rounds", type=int, default=6)
    parser.add_argument("--out", type=Path, required=True, help="New, unoccupied JSON path")
    args = parser.parse_args(argv)
    print(json.dumps(export_pocket(
        args.checkpoint, args.out, q_index=args.q_index, rounds=args.rounds,
    ), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
