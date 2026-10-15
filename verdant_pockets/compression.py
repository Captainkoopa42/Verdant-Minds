"""Lossless dictionary-coded native typed relation snapshots.

This IS experimentally measured compact encoding of repetitive record fields,
not learned semantic compression, not promoted P/Q and not replacement of the
canonical graph. Every typed edge and all evidence references reconstruct.
"""
from __future__ import annotations

import hashlib
import json

from .experiment import PocketIntegrityError


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()


def pack_native_relations(pocket: dict) -> dict:
    records = sorted(
        pocket["current_member_relations"] + pocket["evidenced_cross_p_relations"],
        key=lambda e: e["id"],
    )
    if len({r["id"] for r in records}) != len(records):
        raise PocketIntegrityError("Cannot compress duplicate native relation identities")
    ids = {c["id"] for c in pocket["concepts"]}
    if any(r["source"] not in ids or r["target"] not in ids or not r["evidence_refs"] for r in records):
        raise PocketIntegrityError("Canonical record is missing endpoint or evidence")
    concept_ids = sorted(ids)
    predicates = sorted({r["type"] for r in records})
    evidence = sorted({x for r in records for x in r["evidence_refs"]})
    statuses = sorted({r["status"] for r in records})
    cidx = {c: i for i, c in enumerate(concept_ids)}
    tidx = {t: i for i, t in enumerate(predicates)}
    eidx = {e: i for i, e in enumerate(evidence)}
    sidx = {s: i for i, s in enumerate(statuses)}

    output = {
        "schema": "verdant.pocket_dictionary_native_relations.v1",
        "source_pocket_id": pocket["pocket_id"],
        "concept_id_table": concept_ids,
        "relation_type_table": predicates,
        "evidence_id_table": evidence,
        "relation_status_table": statuses,
        "encoded_rows": [
            [
                r["id"],
                cidx[r["source"]], cidx[r["target"]],
                tidx[r["type"]], int(bool(r["directed"])),
                r["weight"], sidx[r["status"]],
                [eidx[ref] for ref in r["evidence_refs"]],
            ]
            for r in records
        ],
        "raw_records_sha256": _sha(records),
    }
    reconstructed = unpack_native_relations(output)
    if reconstructed != records:
        raise PocketIntegrityError("Lossless native record reconstruction failed")
    raw_count = len(_bytes(records))
    encoded_count = len(_bytes(output))
    output["receipt"] = {
        "uncompressed_native_records_bytes": raw_count,
        "dictionary_encoded_bytes": encoded_count,
        "reduction_fraction": round(1.0 - encoded_count / max(1, raw_count), 9),
        "reconstructed_native_records_sha256": _sha(reconstructed),
        "full_reconstruction": True,
        "type_and_evidence_retention": True,
        "is_learned_semantic_compression": False,
        "may_be_larger_for_small_graphs": True,
    }
    output["envelope_sha256"] = _sha(output)
    return output


def unpack_native_relations(packed: dict) -> list[dict]:
    if packed.get("schema") != "verdant.pocket_dictionary_native_relations.v1":
        raise PocketIntegrityError("Unknown pocket dictionary format")
    tables = (
        packed["concept_id_table"], packed["relation_type_table"],
        packed["evidence_id_table"], packed["relation_status_table"],
    )
    if any(len(set(table)) != len(table) or table != sorted(table) for table in tables):
        raise PocketIntegrityError("Invalid dictionary index table")
    cs, ts, es, ss = tables
    rows = []
    for row in packed["encoded_rows"]:
        if len(row) != 8:
            raise PocketIntegrityError("Invalid encoded relation field count")
        rid, src, dst, reltype, direct, weight, status, erefs = row
        try:
            if direct not in (0, 1):
                raise PocketIntegrityError("Invalid directed relationship marker")
            record = {
                "id": rid, "source": cs[src], "target": cs[dst],
                "type": ts[reltype], "directed": bool(direct),
                "weight": weight, "status": ss[status],
                "evidence_refs": [es[i] for i in erefs],
            }
        except (IndexError, TypeError) as exc:
            raise PocketIntegrityError("Out-of-range native dictionary pointer") from exc
        rows.append(record)
    if rows != sorted(rows, key=lambda e: e["id"]) or len({x["id"] for x in rows}) != len(rows):
        raise PocketIntegrityError("Native dictionary rows are not unique and canonical")
    if _sha(rows) != packed["raw_records_sha256"]:
        raise PocketIntegrityError("Encoded native relation records are not faithful")
    return rows


def validate_native_dictionary(packed: dict, pocket: dict) -> None:
    snapshot = dict(packed)
    envelope = snapshot.pop("envelope_sha256", None)
    if envelope != _sha(snapshot):
        raise PocketIntegrityError("Native dictionary envelope checksum mismatch")
    if packed["source_pocket_id"] != pocket["pocket_id"]:
        raise PocketIntegrityError("Native dictionary belongs to another pocket")
    if pack_native_relations(pocket) != packed:
        raise PocketIntegrityError("Dictionary does not reconstruct this source pocket")
