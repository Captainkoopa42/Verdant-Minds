"""Read-only v2 composition task on an existing native Q/P checkpoint.

Existing native canonical relations are the ONLY evidence. No new bridge
testimony, grade label, hidden answer or native relation is injected.

Usage:
  python -m verdant_pockets.composition_cli SOURCE.vdk --q-index 1 \
     --source-label first_event --target-label target_point --out result.json

This original 12-P/2-Q corpus lacks canonical cross-P relation evidence,
so *abstention* is expected; a positive score here would be suspicious.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_kernel import VerdantKernel, load_checkpoint

from .composition import CompositionQuery, inspect_composition
from .experiment import PocketIntegrityError, cultivate_pocket


def inspect_native_task(
    checkpoint: Path, output: Path, *,
    q_index: int, source_label: str, target_label: str,
    relation_type: str = "precedes",
) -> dict:
    if checkpoint.resolve() == output.resolve():
        raise PocketIntegrityError("Cannot replace native VDK with a derived report")
    if not checkpoint.is_file():
        raise PocketIntegrityError("Source native VDK is missing")
    original_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    kernel = VerdantKernel.from_state(load_checkpoint(checkpoint))
    before = kernel.fingerprint()
    qs = sorted((
        q for q in kernel.state.layered_structures.values()
        if kernel.layered_structure_is_available(q.layered_structure_id)
    ), key=lambda q: (q.created_cycle, q.layered_structure_id))
    if not 0 <= q_index < len(qs):
        raise PocketIntegrityError(f"Available native Q index 0..{len(qs)-1} required")
    q = qs[q_index]
    pocket = cultivate_pocket(kernel, q.member_structure_ids, q_id=q.layered_structure_id, rounds=1)
    labels = {}
    for c in pocket["concepts"]:
        labels.setdefault(c["label"].casefold(), []).append(c["id"])

    def resolve(label: str) -> str:
        ids = labels.get(label.casefold(), [])
        if len(ids) != 1:
            raise PocketIntegrityError(f"Query label {label!r} missing or ambiguous inside this Q")
        return ids[0]

    query = CompositionQuery(resolve(source_label), resolve(target_label), relation_type=relation_type)
    result = inspect_composition(pocket, query)
    if kernel.fingerprint() != before or hashlib.sha256(checkpoint.read_bytes()).hexdigest() != original_hash:
        raise PocketIntegrityError("Original native VDK changed during task inspection")
    payload = {
        "schema": "verdant.cognitive_pocket_native_composition_export.v2",
        "source_checkpoint_sha256": original_hash,
        "source_canonical_fingerprint": before,
        "source_q_id": q.layered_structure_id,
        "source_labels": {"from": source_label, "to": target_label},
        "experiment": result,
        "native_memory_unchanged": True,
        "teacher_testimony_added": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
    return {
        "result": result["disposition"],
        "selected_p_ids": result["selected_p_ids"],
        "native_relation_witness_count": len(result["witness_native_relation_ids"]),
        "original_memory_unchanged": True,
        "output_path": str(output),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--q-index", type=int, default=1)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--target-label", required=True)
    parser.add_argument("--predicate", default="precedes")
    args = parser.parse_args(argv)
    print(json.dumps(inspect_native_task(
        args.checkpoint, args.out, q_index=args.q_index,
        source_label=args.source_label, target_label=args.target_label,
        relation_type=args.predicate,
    ), indent=2))


if __name__ == "__main__":
    main()
