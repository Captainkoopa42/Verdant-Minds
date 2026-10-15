"""Cognitive Pocket v2.3: declaration-grounded lineage and conditional corroboration.

Distinct *declared provenance families* are required for an experimental
bridge to become admissible. Copies and derived testimonies inherit their
ancestor family, so multiple citations from a single origin do not count as
corroboration. A reverse claim quarantines both directions conservatively.

CRUCIAL: A source manifest is experimental input, NOT a cryptographic proof
of external identity or genuine independence. Source-authenticated learning
requires a separately trusted acquisition boundary. No native writeback.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .composition import CompositionQuery, _load_source
from .evidence_retention import (
    _check_observation, acquire_observation, compose_with_evidence,
    flat_graph_control, new_ledger, observation_from_testimony,
)
from .experiment import PocketIntegrityError
from .reconciliation import validate_revision, _hash as _v22_hash


SCHEMA = "verdant.cognitive_pocket_provenance.v2.3"
POLICY = "declared_ancestry_two_family_corrob_reverse_dispute_v2.3"
MAX_EVENTS = 128
MAX_SOURCES = 64
MAX_MATERIALIZED_CLAIMS = 16


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value):
    return sha256(_bytes(value)).hexdigest()


def _anchor(pocket):
    _load_source(pocket)
    return {
        "source_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "snapshot_sha256": _hash(pocket),
    }


def new_provenance(pocket, source_manifest: dict):
    """Freeze an externally staged manifest of lineage families.

    One family = one original information-generating event, regardless of how
    many publication outlets, witnesses, or relays repeat that event.
    The manifest is not independently authenticated in this experiment.
    """
    if not isinstance(source_manifest, dict) or not 1 <= len(source_manifest) <= MAX_SOURCES:
        raise PocketIntegrityError("Manifest must register 1..64 declared sources")
    seen = set()
    for sid, record in source_manifest.items():
        if not isinstance(sid, str) or not 4 <= len(sid) <= 120:
            raise PocketIntegrityError("Invalid registered source identity")
        if not isinstance(record, dict) or set(record) != {"lineage_family", "description"}:
            raise PocketIntegrityError("Each source must declare one root lineage family and description")
        if not all(isinstance(record[k], str) and 4 <= len(record[k]) <= 160
                   for k in ("lineage_family", "description")):
            raise PocketIntegrityError("Malformed external lineage declaration")
        seen.add(record["lineage_family"])
    origin = _anchor(pocket)
    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "source": origin,
        "registered_sources": deepcopy(source_manifest),
        "registered_manifest_sha256": _hash(source_manifest),
        "events": [],
        "head_hash": _hash({"source": origin, "manifest_sha256": _hash(source_manifest)}),
        "native_writeback": False,
        "obligation_writeback": False,
    }


def _replay(journal, pocket):
    if set(journal) != {
        "schema", "policy", "source", "registered_sources",
        "registered_manifest_sha256", "events", "head_hash",
        "native_writeback", "obligation_writeback",
    }:
        raise PocketIntegrityError("Provenance journal schema mismatch")
    if (journal["schema"] != SCHEMA or journal["policy"] != POLICY or
            journal["native_writeback"] is not False or
            journal["obligation_writeback"] is not False):
        raise PocketIntegrityError("Unrecognized or unauthorized provenance journal")
    anchor = _anchor(pocket)
    if journal["source"] != anchor:
        raise PocketIntegrityError("Provenance source pocket/fingerprint mismatch")
    manifest = journal["registered_sources"]
    if not isinstance(manifest, dict) or not 1 <= len(manifest) <= MAX_SOURCES:
        raise PocketIntegrityError("Invalid registered manifest")
    if journal["registered_manifest_sha256"] != _hash(manifest):
        raise PocketIntegrityError("Manifest digest changed")
    # Verify manifest structural restrictions even for loaded sidecars.
    for sid, item in manifest.items():
        if (not isinstance(sid, str) or not 4 <= len(sid) <= 120 or
                not isinstance(item, dict) or set(item) != {"lineage_family","description"} or
                not all(isinstance(item[k],str) and 4 <= len(item[k]) <= 160 for k in ("lineage_family","description"))):
            raise PocketIntegrityError("Malformed registered source entry")
    events = journal["events"]
    if not isinstance(events,list) or len(events) > MAX_EVENTS:
        raise PocketIntegrityError("Provenance event budget exceeded")
    prev = _hash({"source": anchor, "manifest_sha256": _hash(manifest)})
    concepts = {c["id"] for c in pocket["concepts"]}
    records = {}
    withdrawn = set()
    for i, event in enumerate(events):
        if not isinstance(event,dict) or set(event) != {
            "sequence", "prev_hash", "operation", "payload", "record_hash"
        }:
            raise PocketIntegrityError("Malformed provenance event")
        unsigned = {k:v for k,v in event.items() if k != "record_hash"}
        if (event["sequence"] != i or event["prev_hash"] != prev or
                event["record_hash"] != _hash(unsigned)):
            raise PocketIntegrityError("Provenance event hash chain invalid")
        operation, payload = event["operation"], event["payload"]
        if operation == "attest":
            if not isinstance(payload,dict) or set(payload) != {
                "observation", "source_id", "derived_from"
            }:
                raise PocketIntegrityError("Malformed attestation fields")
            obs = payload["observation"]
            _check_observation(obs,concepts)
            sid, parent = payload["source_id"], payload["derived_from"]
            if sid not in manifest or obs["source_ref"] != sid:
                raise PocketIntegrityError("Attestation source not registered or mismatched")
            if parent is not None:
                if parent not in records or parent in withdrawn:
                    raise PocketIntegrityError("Derived citation must reference earlier nonwithdrawn attestation")
                # Derived copies can't change underlying statement or acquire
                # a newly 'independent' family by claiming another source.
                other = records[parent]["observation"]
                if (obs["source"],obs["target"],obs["type"]) != (
                        other["source"],other["target"],other["type"]):
                    raise PocketIntegrityError("Derived citation changed parent claim")
                lineage = records[parent]["lineage_family"]
            else:
                lineage = manifest[sid]["lineage_family"]
            oid = _hash(obs)
            if oid in records:
                raise PocketIntegrityError("Repeated attestation identity")
            records[oid] = {
                "observation": obs, "source_id": sid,
                "lineage_family": lineage,
                "derived_from": parent,
            }
        elif operation == "withdraw":
            if not isinstance(payload,dict) or set(payload) != {
                "observation_id", "source_id", "reason"
            }:
                raise PocketIntegrityError("Malformed withdrawal")
            oid, sid = payload["observation_id"], payload["source_id"]
            if oid not in records or oid in withdrawn:
                raise PocketIntegrityError("Withdrawing unknown/withdrawn observation")
            if sid != records[oid]["source_id"]:
                raise PocketIntegrityError("Withdrawal source does not match attestation source")
            reason = payload["reason"]
            if not isinstance(reason,str) or not 4 <= len(reason) <= 160:
                raise PocketIntegrityError("Missing bounded withdrawal reason")
            withdrawn.add(oid)
        else:
            raise PocketIntegrityError("Unauthorized provenance event type")
        prev = event["record_hash"]
    if journal["head_hash"] != prev:
        raise PocketIntegrityError("Provenance journal head mismatch")
    return records, withdrawn


def validate_provenance(journal,pocket):
    _replay(journal,pocket)


def _append(pocket,journal,op,payload):
    _replay(journal,pocket)
    if len(journal["events"]) >= MAX_EVENTS:
        raise PocketIntegrityError("Provenance event history full")
    new=deepcopy(journal)
    event={
        "sequence":len(new["events"]),
        "prev_hash":new["head_hash"],
        "operation":op,
        "payload":deepcopy(payload),
    }
    event["record_hash"]=_hash(event)
    new["events"].append(event)
    new["head_hash"]=event["record_hash"]
    _replay(new,pocket)
    return new


def attest(pocket,journal,observation,*,source_id,derived_from=None):
    """Append one controlled testimony. A derived citation inherits lineage."""
    return _append(pocket,journal,"attest",{
        "observation":observation,
        "source_id":source_id,
        "derived_from":derived_from,
    })


def withdraw(pocket,journal,observation_id,*,source_id,reason):
    """Keep the original testimony but remove this attestation from eligibility."""
    return _append(pocket,journal,"withdraw",{
        "observation_id":observation_id,
        "source_id":source_id,
        "reason":reason,
    })


def status_snapshot(pocket,journal,*,native_kernel=None):
    records, withdrawn = _replay(journal,pocket)
    native = _load_source(pocket)[2]
    native_forward = {
        (r["source"],r["target"],r["type"])
        for r in native if r["directed"] and r["status"] in ("supported","confirmed")
    }
    native_contradicted = {
        (r["source"],r["target"],r["type"])
        for r in native if r["directed"] and r["status"] == "contradicted"
    }
    # v0 pockets deliberately excluded unsupported native cross-P relations
    # from the evidence-backed export. Inspect a live verified source kernel
    # explicitly when the caller needs negative cross-P evidence. Never add
    # these contradicted rows to a proof edge view.
    if native_kernel is not None:
        if native_kernel.fingerprint() != pocket["canonical_fingerprint"]:
            raise PocketIntegrityError("Native conflict inspection kernel differs from source checkpoint")
        members = {c["id"] for c in pocket["concepts"]}
        for row in native_kernel.state.relations.values():
            if (row.source_concept_id in members and
                row.target_concept_id in members and
                row.directed and row.status.value == "contradicted"):
                if not row.evidence_refs or any(
                    ref not in native_kernel.state.evidence for ref in row.evidence_refs
                ):
                    raise PocketIntegrityError("Contradicted native relation evidence closure incomplete")
                native_contradicted.add((
                    row.source_concept_id,row.target_concept_id,row.relation_type
                ))

    grouped = defaultdict(list)
    for oid,item in records.items():
        if oid not in withdrawn:
            o=item["observation"]
            grouped[(o["source"],o["target"],o["type"])].append(oid)

    by_id={}
    for oid,item in records.items():
        o=item["observation"]
        if oid in withdrawn:
            kind="withdrawn"
        elif (o["target"],o["source"],o["type"]) in grouped or (
            o["target"],o["source"],o["type"]) in native_forward or (
            o["source"],o["target"],o["type"]) in native_contradicted:
            kind="disputed_quarantined"
        else:
            families={records[x]["lineage_family"] for x in grouped[
                (o["source"],o["target"],o["type"])
            ]}
            kind=("corroborated_experimental" if len(families)>=2
                  else "provisional_single_lineage")
        by_id[oid]=kind

    eligible_keys={}
    for key, ids in sorted(grouped.items()):
        candidates=sorted(oid for oid in ids if by_id[oid]=="corroborated_experimental")
        if not candidates:
            continue
        groups=sorted({records[oid]["lineage_family"] for oid in candidates})
        eligible_keys[key]={"observation_ids":candidates, "lineage_families":groups}
    return {
        "schema":"verdant.cognitive_pocket_provenance_state.v2.3",
        "source_pocket_id":pocket["pocket_id"],
        "journal_head_hash":journal["head_hash"],
        "attestation_count":len(records),
        "withdrawn_count":len(withdrawn),
        "counts":{k:sum(status==k for status in by_id.values()) for k in (
            "corroborated_experimental","provisional_single_lineage",
            "disputed_quarantined","withdrawn"
        )},
        "status_by_observation_id":{oid:by_id[oid] for oid in sorted(by_id)},
        "corroborated_claims": [
            {"source":key[0],"target":key[1],"type":key[2],**metadata}
            for key,metadata in eligible_keys.items()
        ],
        "source_authenticity_verified":False,
        "complete_native_conflict_source_inspected":native_kernel is not None,
        "lineage_independence_external_declaration_only":True,
        "no_canonical_writeback":True,
    }


def _admitted_v21(pocket,journal,*,native_kernel=None):
    state=status_snapshot(pocket,journal,native_kernel=native_kernel)
    if len(state["corroborated_claims"])>MAX_MATERIALIZED_CLAIMS:
        raise PocketIntegrityError("Corroborated claim graph exceeds bounded v2.1 view")
    view=new_ledger(pocket)
    attestation_map={}
    for claim in state["corroborated_claims"]:
        obs=observation_from_testimony(
            source=claim["source"],target=claim["target"],
            relation_type=claim["type"],
            source_ref="controlled:corroborated-claim:"+_hash(
                (claim["source"],claim["target"],claim["type"])
            )[:24],
        )
        view=acquire_observation(pocket,view,obs)
        new_oid=view["events"][-1]["observation_id"]
        attestation_map[new_oid]={
            "supporting_observation_ids":claim["observation_ids"],
            "lineage_families":claim["lineage_families"],
        }
    return view,state,attestation_map


def inspect_corroboration(pocket,journal,query,*,native_kernel=None):
    """Conditionally answer only using 2+ declared lineage groups per bridge."""
    query.validate()
    view, state, evidence = _admitted_v21(pocket,journal,native_kernel=native_kernel)
    proof=compose_with_evidence(pocket,view,query)
    flat=flat_graph_control(pocket,view,query)
    if flat["disposition"]!=proof["disposition"]:
        raise PocketIntegrityError("Corroborated pocket and flat graph disagree")
    used=proof["witness_external_observation_ids"]
    why=[evidence[k] for k in used]
    state_reason = "none"
    if proof["disposition"]!="supported_experimental_composition":
        if state["counts"]["disputed_quarantined"]:
            state_reason="at_least_one_disputed_testimony_exists"
        elif state["counts"]["provisional_single_lineage"]:
            state_reason="no_eligible_2_lineage_proof"
        elif state["counts"]["withdrawn"]:
            state_reason="some_testimony_withdrawn"
    result={
        "schema":"verdant.cognitive_pocket_corroborated_proof.v2.3",
        "source_pocket_id":pocket["pocket_id"],
        "journal_head_hash":journal["head_hash"],
        "query":query.as_dict(),
        "disposition":proof["disposition"],
        "non_support_reason":state_reason,
        "proof":proof,
        "flat_baseline":flat,
        "support_lineage_provenance":why,
        "synthetic_materialized_observations":used,
        "reconciliation":state,
        "cost_accounting":{
            "p_route_relation_inspections":proof["metrics"].get("p_graph_cross_edge_records_inspected",0),
            "pocket_edge_expansions":proof["metrics"].get("edge_expansions",0),
            "flat_edge_expansions":flat.get("edge_expansions",0),
            "attestation_records_replayed":state["attestation_count"],
            "source_lineage_registry_entries":len(journal["registered_sources"]),
            "not_a_wall_clock_benchmark":True,
        },
        "corroboration_not_source_authentication":True,
        "native_negative_relations_considered_from_live_source":native_kernel is not None,
        "no_native_writeback":True,
        "no_obligation_writeback":True,
    }
    result["evaluation_id"]=_hash(result)
    return result


def save_provenance(path,journal,pocket):
    validate_provenance(journal,pocket)
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as stream:
        stream.write(_bytes(journal))


def load_provenance(path,pocket):
    raw=Path(path).read_bytes()
    try:
        value=json.loads(raw)
    except (ValueError,UnicodeDecodeError) as exc:
        raise PocketIntegrityError("Corrupt provenance journal") from exc
    if _bytes(value)!=raw:
        raise PocketIntegrityError("Non-canonical provenance sidecar")
    validate_provenance(value,pocket)
    return value


def migrate_v22(pocket,old_journal,source_map,manifest):
    """Import v2.2 testimony under explicit external lineage declarations.

    Requires a *complete* mapping for each old observation source_ref. Does
    not auto-award independence just because source strings are different.
    """
    validate_revision(old_journal,pocket)
    new=new_provenance(pocket,manifest)
    for event in old_journal["events"]:
        payload=event["payload"]
        if event["operation"]=="observe":
            obs=payload["observation"]
            if obs["source_ref"] not in source_map:
                raise PocketIntegrityError("Unmapped legacy source lineage; fail closed")
            sid=source_map[obs["source_ref"]]
            copied=deepcopy(obs)
            copied["source_ref"]=sid
            new=attest(pocket,new,copied,source_id=sid)
        elif event["operation"]=="withdraw":
            previous_id=payload["observation_id"]
            legacy_obs=next((e["payload"]["observation"] for e in old_journal["events"]
                             if e["operation"]=="observe" and _v22_hash(e["payload"]["observation"])==previous_id),None)
            if legacy_obs is None:
                raise PocketIntegrityError("Legacy withdrawal lost its event")
            sid=source_map[legacy_obs["source_ref"]]
            new_obs=deepcopy(legacy_obs)
            new_obs["source_ref"]=sid
            new=withdraw(
                pocket,new,_hash(new_obs),source_id=sid,
                reason=payload["reason"],
            )
    return new
