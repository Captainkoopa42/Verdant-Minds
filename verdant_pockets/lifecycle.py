"""Deterministic pocket daughter partitions, lossless codec, and sealed sidecar.

Pockets are experimental observations. Daughters are NOT canonical V4 mitosis
shards and have no independent epistemic, scheduling, or graph write authority.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import zlib

from .experiment import PocketIntegrityError
from .dynamics import paired_cohort
from .adaptation import local_cultivation
from .compression import pack_native_relations, validate_native_dictionary


def _bytes(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(obj: object) -> str:
    return hashlib.sha256(_bytes(obj)).hexdigest()


def daughter_partitions(pocket: dict, cohort: dict) -> dict:
    """A lossless division by observed typed-variable grammar, not arbitrary Q split.

    Repeated grammmar provides pocket-local partitions; all native source
    records stay in the complete parent pocket. Cross-partition links are
    pointers to existing synthetic links and carry NO semantic authority.
    """
    if cohort["source_pocket_id"] != pocket["pocket_id"]:
        raise PocketIntegrityError("Cohort and parent pocket differ")
    ps = {p["id"]: p for p in pocket["p_snapshots"]}
    concepts = {c["id"]: c for c in pocket["concepts"]}
    partitions = []
    seen = set()
    gram_groups: dict[str, list[str]] = {}
    for p in ps.values():
        gram = json.dumps(p["relation_grammar"], sort_keys=True, separators=(",", ":"))
        gram_groups.setdefault(gram, []).append(p["id"])
    for i, (gram, pids) in enumerate(sorted(gram_groups.items())):
        pids = sorted(pids)
        local = sorted({cid for pid in pids for cid in ps[pid]["members"]})
        if seen.intersection(pids):
            raise PocketIntegrityError("Daughter P membership overlaps unexpectedly")
        seen.update(pids)
        partitions.append({
            "daughter_id": f"daughter_{i:02d}_{_hash((pocket['pocket_id'], gram, pids))[:12]}",
            "parent_pocket_id": pocket["pocket_id"],
            "role_grammar": json.loads(gram),
            "p_ids": pids,
            "concept_ids": local,
            "native_relation_ids": sorted({
                row["id"] for row in pocket["current_member_relations"]
                if row["source"] in local and row["target"] in local
            }),
            "type": "experimental_read_only_subpocket",
            "source_evidence_preserved_in_parent": True,
        })
    if seen != set(ps):
        raise PocketIntegrityError("Daughter partition lost native source P")

    owner: dict[str, str] = {}
    for part in partitions:
        for cid in part["concept_ids"]:
            if cid in owner:
                # Shared canonical concept IDs require replicated shadows, not
                # destructive migration. No ambiguous reassignment in v1.
                raise PocketIntegrityError("Overlapping concept requires future shadow-routing protocol")
            owner[cid] = part["daughter_id"]
    if set(owner) != set(concepts):
        raise PocketIntegrityError("Daughter concept coverage mismatch")

    boundaries = {}
    for trial in cohort["trials"]:
        for e in trial["links"]:
            da, db = owner[e["source"]], owner[e["target"]]
            if da == db:
                continue
            identity = (
                da, db, e["source"], e["target"],
                e["kind"], e.get("relation_id"),
            )
            boundaries[identity] = {
                "source_daughter_id": da, "target_daughter_id": db,
                "source_concept_id": e["source"], "target_concept_id": e["target"],
                "kind": e["kind"], "native_relation_id": e.get("relation_id"),
                "hypothetical_only": e["kind"].startswith("hypothetical_"),
                "weight": e["strength"],
            }
    result = {
        "schema": "verdant.cognitive_pocket_daughters.v1",
        "parent_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "partition_rule": "native_relation_variable_grammar",
        "daughters": partitions,
        "boundary_links": [boundaries[k] for k in sorted(boundaries, key=str)],
        "coverage": {
            "p_exactly_once": True,
            "concept_exactly_once": True,
            "canonical_relation_ids_preserved_in_parent": True,
            "recombine_is_metadata_only": True,
        },
    }
    result["partition_id"] = _hash(result)
    return result


def compression_receipt(payload: dict) -> dict:
    """True byte compression and exact reconstruction, NOT learned cognition."""
    raw = _bytes(payload)
    compressed = zlib.compress(raw, level=9)
    restored = zlib.decompress(compressed)
    if restored != raw:
        raise PocketIntegrityError("Compression lost experimental evidence bytes")
    return {
        "codec": "zlib-9-over-canonical-json",
        "original_bytes": len(raw),
        "compressed_bytes": len(compressed),
        "reduction_fraction": round(1.0 - len(compressed) / max(1, len(raw)), 9),
        "original_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "lossless_exact_reconstruction": True,
        "learned_representation_compression": False,
        "semantic_reconstruction_demonstrated": False,
    }


def build_lifecycle(pocket: dict, *, rounds: int = 8, maximum_links_per_p: int = 2) -> dict:
    cohort = paired_cohort(pocket, rounds=rounds, maximum_links_per_p=maximum_links_per_p)
    daughters = daughter_partitions(pocket, cohort)
    dictionary = pack_native_relations(pocket)
    adaptation = local_cultivation(pocket, epochs=2, rounds=min(rounds, 8), maximum_links_per_p=maximum_links_per_p)
    # A separate receipt for every chronological session, chained to the
    # original certified pocket ID. Sequential replay is deterministic.
    history = []
    predecessor = pocket["pocket_id"]
    for trial in cohort["trials"]:
        record = {
            "sequence": len(history),
            "prev_hash": predecessor,
            "trial_id": _hash(trial),
            "source_p_id": trial["source_p_id"],
            "arm": trial["arm"],
            "final_non_source_active": trial["final_non_source_active"],
            "final_activation_sha256": _hash(trial["frames"][-1]["activation"]),
        }
        record["record_hash"] = _hash(record)
        history.append(record)
        predecessor = record["record_hash"]

    body = {
        "schema": "verdant.cognitive_pocket_lifecycle.v1",
        "parent_pocket": pocket,
        "matched_cohort": cohort,
        "experimental_daughters": daughters,
        "native_relation_dictionary": dictionary,
        "local_plasticity": adaptation,
        "history": history,
        "head_hash": predecessor,
        "limitations": {
            "no_canonical_writeback": True,
            "no_endogenous_scheduler": True,
            "no_evidence_of_new_semantic_understanding": True,
            "no_automatic_obligation_trigger": True,
            "numeric_local_activity_not_native_v4_budding": True,
        },
    }
    # Exclude the receipt itself from the compression measurement to avoid
    # self-referential hashing.
    body["compression"] = compression_receipt(body)
    body["lifecycle_id"] = _hash(body)
    return body


def validate_lifecycle(body: dict) -> None:
    if body.get("schema") != "verdant.cognitive_pocket_lifecycle.v1":
        raise PocketIntegrityError("Unknown lifecycle schema")
    expected = dict(body)
    claimed_id = expected.pop("lifecycle_id", None)
    if claimed_id != _hash(expected):
        raise PocketIntegrityError("Lifecycle checksum mismatch")
    uncompressed = dict(expected)
    receipt = uncompressed.pop("compression")
    if compression_receipt(uncompressed) != receipt:
        raise PocketIntegrityError("Lifecycle compression receipt mismatch")
    pocket = body["parent_pocket"]
    cohort = body["matched_cohort"]
    if cohort["source_pocket_id"] != pocket["pocket_id"]:
        raise PocketIntegrityError("Lifecycle mixed unrelated source pockets")
    if cohort["cohort_id"] != _hash({k:v for k,v in cohort.items() if k != "cohort_id"}):
        raise PocketIntegrityError("Lifecycle cohort checksum mismatch")
    # Re-evaluate daughter membership and all boundary references from trials.
    if body["experimental_daughters"] != daughter_partitions(pocket, cohort):
        raise PocketIntegrityError("Daughter partitions or boundary links changed")
    validate_native_dictionary(body["native_relation_dictionary"], pocket)
    adaptation = body["local_plasticity"]
    if adaptation != local_cultivation(
        pocket,
        epochs=adaptation["epochs"],
        rounds=adaptation["local_rounds_per_session"],
        rate=adaptation["rate"],
        maximum_links_per_p=adaptation["maximum_links_per_p"],
    ):
        raise PocketIntegrityError("Local plasticity changed under deterministic replay")
    predecessor = pocket["pocket_id"]
    if len(body["history"]) != len(cohort["trials"]):
        raise PocketIntegrityError("Lifecycle has missing trial history")
    for index, (event, trial) in enumerate(zip(body["history"], cohort["trials"])):
        record = dict(event)
        key = record.pop("record_hash", None)
        if (key != _hash(record) or
                record["sequence"] != index or
                record["prev_hash"] != predecessor or
                record["trial_id"] != _hash(trial) or
                record["final_activation_sha256"] != _hash(trial["frames"][-1]["activation"])):
            raise PocketIntegrityError("Pocket history chain failed replay")
        predecessor = key
    if predecessor != body["head_hash"]:
        raise PocketIntegrityError("History head mismatch")


def save_lifecycle(path: Path, body: dict) -> None:
    """Write a sealed sidecar, create-only, without overwriting an existing file.

    Temp and hard-link are on the same volume, ensuring an incomplete temp
    cannot be mistaken for a finalized path. No canonical VDK is touched.
    """
    validate_lifecycle(body)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _bytes(body)
    fd, temp_name = tempfile.mkstemp(prefix=".pocket-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError(str(path))
        os.link(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def load_lifecycle(path: Path) -> dict:
    raw = Path(path).read_bytes()
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PocketIntegrityError("Corrupt pocket lifecycle JSON") from exc
    if raw != _bytes(body):
        raise PocketIntegrityError("Lifecycle JSON is not canonical")
    validate_lifecycle(body)
    return body
