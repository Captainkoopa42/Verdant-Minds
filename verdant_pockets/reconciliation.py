"""v2.2: local experimental evidence reconciliation, never canonical writeback.

Records observational testimony, explicit source-matched withdrawals, and
conservative reverse-direction disputes. A formerly supported conditional
proof is suspended when every relevant experimental bridge is withdrawn or
disputed, while unrelated retained observations remain available.

The evidence source itself is NOT authenticated, observations are NOT native
truth, and hash linkage does NOT provide signatures or trusted governance.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from .composition import CompositionQuery, _load_source
from .evidence_retention import (
    _check_observation, acquire_observation, compose_with_evidence,
    flat_graph_control, new_ledger, validate_ledger,
)
from .experiment import PocketIntegrityError


SCHEMA = "verdant.cognitive_pocket_evidence_reconciliation.v2.2"
POLICY = "conservative_reverse_conflict_source_matched_withdrawal_v2.2"
MAX_EVENTS = 24


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: object) -> str:
    return sha256(_bytes(value)).hexdigest()


def _anchor(pocket: dict) -> dict:
    _load_source(pocket)
    return {
        "source_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "source_pocket_sha256": _hash(pocket),
    }


def start_revision(pocket: dict) -> dict:
    source = _anchor(pocket)
    return {
        "schema": SCHEMA,
        "policy": POLICY,
        "source": source,
        "events": [],
        "head_hash": _hash(source),
        "native_writeback": False,
        "obligation_writeback": False,
    }


def _validate_event(op: str, payload: dict, *, concepts: set[str],
                    observations: dict[str, dict], withdrawn: set[str]) -> None:
    if op == "observe":
        if set(payload) != {"observation"}:
            raise PocketIntegrityError("Malformed observation event")
        obs = payload["observation"]
        _check_observation(obs, concepts)
        oid = _hash(obs)
        if oid in observations:
            raise PocketIntegrityError("Duplicate observation identity; do not silently reactivate")
        observations[oid] = obs
    elif op == "withdraw":
        if set(payload) != {"observation_id", "source_ref", "reason"}:
            raise PocketIntegrityError("Malformed withdrawal event")
        oid = payload["observation_id"]
        if oid not in observations or oid in withdrawn:
            raise PocketIntegrityError("Unknown or already withdrawn observation")
        # A declared source match is *not* identity verification. It prevents
        # accidental cross-source cancellations in this controlled protocol.
        if payload["source_ref"] != observations[oid]["source_ref"]:
            raise PocketIntegrityError("Withdrawal source_ref differs from original observation")
        if (not isinstance(payload["reason"], str)
                or not 4 <= len(payload["reason"]) <= 160):
            raise PocketIntegrityError("Withdrawal needs an explicit bounded reason")
        withdrawn.add(oid)
    else:
        raise PocketIntegrityError("Unknown evidence revision operation")


def validate_revision(journal: dict, pocket: dict) -> None:
    expected_keys = {
        "schema", "policy", "source", "events", "head_hash",
        "native_writeback", "obligation_writeback",
    }
    if set(journal) != expected_keys:
        raise PocketIntegrityError("Revision journal schema/fields mismatch")
    if (journal["schema"] != SCHEMA or journal["policy"] != POLICY
            or journal["native_writeback"] is not False
            or journal["obligation_writeback"] is not False):
        raise PocketIntegrityError("Revision journal attempts unauthorized native authority")
    if journal["source"] != _anchor(pocket):
        raise PocketIntegrityError("Revision journal source binding mismatch")
    events = journal["events"]
    if not isinstance(events, list) or len(events) > MAX_EVENTS:
        raise PocketIntegrityError("Too many evidence revision events")
    concepts = {c["id"] for c in pocket["concepts"]}
    prev = _hash(journal["source"])
    observations: dict[str, dict] = {}
    withdrawn: set[str] = set()
    for seq, event in enumerate(events):
        if set(event) != {"sequence", "prev_hash", "operation", "payload", "record_hash"}:
            raise PocketIntegrityError("Malformed revision history event")
        body = {k: v for k, v in event.items() if k != "record_hash"}
        if (event["sequence"] != seq or event["prev_hash"] != prev
                or event["record_hash"] != _hash(body)):
            raise PocketIntegrityError("Revision hash chain or event order broken")
        _validate_event(event["operation"], event["payload"],
                        concepts=concepts, observations=observations,
                        withdrawn=withdrawn)
        prev = event["record_hash"]
    if journal["head_hash"] != prev:
        raise PocketIntegrityError("Revision head hash mismatch")


def _append(pocket: dict, journal: dict, operation: str, payload: dict) -> dict:
    validate_revision(journal, pocket)
    if len(journal["events"]) >= MAX_EVENTS:
        raise PocketIntegrityError("Bounded evidence revision journal is full")
    updated = deepcopy(journal)
    event = {
        "sequence": len(updated["events"]),
        "prev_hash": updated["head_hash"],
        "operation": operation,
        "payload": deepcopy(payload),
    }
    event["record_hash"] = _hash(event)
    updated["events"].append(event)
    updated["head_hash"] = event["record_hash"]
    validate_revision(updated, pocket)
    return updated


def observe(pocket: dict, journal: dict, observation: dict) -> dict:
    """Register an explicit experimenter-supplied observation in a new state."""
    return _append(pocket, journal, "observe", {"observation": observation})


def withdraw(
    pocket: dict, journal: dict, observation_id: str,
    *, source_ref: str, reason: str,
) -> dict:
    """Mark one named local observation inactive; original event is retained."""
    return _append(pocket, journal, "withdraw", {
        "observation_id": observation_id,
        "source_ref": source_ref,
        "reason": reason,
    })


def _states(pocket: dict, journal: dict):
    validate_revision(journal, pocket)
    observations = {}
    withdrawn = set()
    for event in journal["events"]:
        if event["operation"] == "observe":
            obs = event["payload"]["observation"]
            observations[_hash(obs)] = obs
        else:
            withdrawn.add(event["payload"]["observation_id"])
    active = {oid: o for oid, o in observations.items() if oid not in withdrawn}
    return observations, withdrawn, active


def reconcile_state(pocket: dict, journal: dict) -> dict:
    """Compute a conservative status for each source-attested observation.

    Reverse PRECEDES directed observations quarantine BOTH directions.
    A surviving opposite native SUPPORTED/CONFIRMED edge also quarantines.
    Withdrawal changes eligibility, never erases the original event.
    """
    observations, withdrawn, active = _states(pocket, journal)
    _, _, native, _ = _load_source(pocket)
    supported_native = {
        (r["source"], r["target"], r["type"])
        for r in native if r["directed"] and r["status"] in ("supported", "confirmed")
    }
    statuses = {}
    for oid, observation in observations.items():
        if oid in withdrawn:
            statuses[oid] = "withdrawn"
            continue
        reverse = (
            observation["target"], observation["source"], observation["type"]
        )
        native_conflict = reverse in supported_native
        testimony_conflict = any(
            other["source"] == reverse[0] and
            other["target"] == reverse[1] and
            other["type"] == reverse[2] for
            other_id, other in active.items() if other_id != oid
        )
        statuses[oid] = (
            "quarantined_disputed" if native_conflict or testimony_conflict
            else "eligible_experimental"
        )
    return {
        "source_pocket_id": pocket["pocket_id"],
        "journal_head_hash": journal["head_hash"],
        "statuses": {k: statuses[k] for k in sorted(statuses)},
        "eligible_observation_ids": sorted(
            oid for oid, s in statuses.items() if s == "eligible_experimental"
        ),
        "quarantined_observation_ids": sorted(
            oid for oid, s in statuses.items() if s == "quarantined_disputed"
        ),
        "withdrawn_observation_ids": sorted(withdrawn),
        "policy_conservatively_quarantines_reverse_predicates": True,
        "independent_source_authenticity_verified": False,
        "native_memory_modified": False,
    }


def _eligible_v21(pocket: dict, journal: dict) -> dict:
    """Materialize a temporary *in-memory* v2.1 evidence view; no VDK edits."""
    state = reconcile_state(pocket, journal)
    observed, _, _ = _states(pocket, journal)
    v21 = new_ledger(pocket)
    for oid in state["eligible_observation_ids"]:
        v21 = acquire_observation(pocket, v21, observed[oid])
    return v21


def _historical_proofs(pocket: dict, journal: dict, query: CompositionQuery) -> list[dict]:
    """Re-evaluate each earlier prefix, to identify actually dependent proofs."""
    proofs = []
    for n in range(1, len(journal["events"])):
        prefix = {
            **journal,
            "events": journal["events"][:n],
            "head_hash": journal["events"][n - 1]["record_hash"],
        }
        eligible = _eligible_v21(pocket, prefix)
        proof = compose_with_evidence(pocket, eligible, query)
        if proof["disposition"] == "supported_experimental_composition":
            proofs.append({
                "revision_sequence": n,
                "external_observation_ids": proof["witness_external_observation_ids"],
                "native_relation_ids": proof["witness_native_relation_ids"],
                "result_id": proof["result_id"],
            })
    return proofs


def inspect_revision(
    pocket: dict, journal: dict, query: CompositionQuery,
) -> dict:
    """Evaluate a query and report stale proofs only when provenance matches.

    A current positive witness is never falsely suspended because an unrelated
    observation was withdrawn. If no proof remains, identify earlier witnesses
    that depended upon now quarantined/withdrawn specific observation IDs.
    """
    query.validate()
    state = reconcile_state(pocket, journal)
    active = _eligible_v21(pocket, journal)
    current = compose_with_evidence(pocket, active, query)
    flat = flat_graph_control(pocket, active, query)
    if current["disposition"] != flat["disposition"]:
        raise PocketIntegrityError("Pocket and flat reference disagree on reconciled evidence")

    history = _historical_proofs(pocket, journal, query)
    current_status = current["disposition"]
    dependent_ids = set()
    suspended_cause = None
    if current_status != "supported_experimental_composition":
        now_unusable = (
            set(state["quarantined_observation_ids"]) |
            set(state["withdrawn_observation_ids"])
        )
        dependent_ids = {
            oid for proof in history for oid in proof["external_observation_ids"]
            if oid in now_unusable
        }
        if dependent_ids:
            suspended_cause = (
                "suspended_contested_evidence"
                if dependent_ids & set(state["quarantined_observation_ids"])
                else "suspended_withdrawn_evidence"
            )
    report = {
        "schema": "verdant.cognitive_pocket_revision_inspection.v2.2",
        "source_pocket_id": pocket["pocket_id"],
        "canonical_fingerprint": pocket["canonical_fingerprint"],
        "journal_head_hash": journal["head_hash"],
        "query": query.as_dict(),
        "disposition": suspended_cause or current_status,
        "underlying_composition_disposition": current_status,
        "conditional_proof": current,
        "flat_baseline": flat,
        "reconciliation": state,
        "suspended_proof_depended_on_observation_ids": sorted(dependent_ids),
        "historical_positive_proofs": history,
        "no_native_writeback": True,
        "no_obligation_recorded": True,
        "rule_externally_declared": True,
        "observation_truth_independently_verified": False,
    }
    report["evaluation_id"] = _hash(report)
    return report


def save_revision(path: Path, journal: dict, pocket: dict) -> None:
    validate_revision(journal, pocket)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(_bytes(journal))


def load_revision(path: Path, pocket: dict) -> dict:
    raw = Path(path).read_bytes()
    try:
        journal = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise PocketIntegrityError("Unreadable revision journal") from exc
    if raw != _bytes(journal):
        raise PocketIntegrityError("Revision journal has noncanonical bytes")
    validate_revision(journal, pocket)
    return journal


def migrate_v21(pocket: dict, v21_journal: dict) -> dict:
    """Create a new v2.2 journal containing v2.1 observations, preserving v2.1."""
    validate_ledger(v21_journal, pocket)
    revised = start_revision(pocket)
    for event in v21_journal["events"]:
        revised = observe(pocket, revised, event["observation"])
    return revised
