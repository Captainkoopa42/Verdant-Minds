from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .models import EventEnvelope, utc_now_iso


def _canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_payload(payload)).hexdigest()


def make_event(*, run_id: str, organism_id: str, kernel, command_id: str, event_type: str, payload: dict[str, Any], native_id: str | None = None) -> EventEnvelope:
    digest = payload_hash(payload)
    identity = native_id or digest[:24]
    event_id = "evt_" + hashlib.sha256(
        f"{run_id}|{organism_id}|{command_id}|{event_type}|{identity}".encode("utf-8")
    ).hexdigest()[:28]
    return EventEnvelope(
        event_id=event_id,
        run_id=run_id,
        organism_id=organism_id,
        engine_cycle=kernel.state.cycle,
        state_revision=kernel.state.event_sequence,
        event_type=event_type,
        source_command_id=command_id,
        timestamp_utc=utc_now_iso(),
        payload=payload,
        payload_sha256=digest,
    )


def development_events(*, run_id: str, organism_id: str, kernel, command_id: str, result) -> tuple[EventEnvelope, ...]:
    events: list[EventEnvelope] = []
    exp = result.experience
    exp_payload = {
        "event_key": exp.event_key,
        "cycle": exp.cycle,
        "concept_ids": list(exp.concept_ids),
        "relation_ids": list(exp.relation_ids),
        "claim_ids": list(exp.claim_ids),
        "contradiction_ids": list(exp.contradiction_ids),
        "revision_ids": list(exp.revision_ids),
        "observation_evidence_id": exp.observation_evidence_id,
        "translation_evidence_id": exp.translation_evidence_id,
        "additional_evidence_ids": list(exp.additional_evidence_ids),
        "replayed": exp.replayed,
    }
    events.append(make_event(
        run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
        event_type="EVIDENCE_ACCEPTED", payload=exp_payload, native_id=exp.event_key,
    ))
    if result.resonance_event is not None:
        native = result.resonance_event
        events.append(make_event(
            run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
            event_type="RESONANCE_COMMITTED", payload=native.model_dump(mode="json"),
            native_id=getattr(native, "event_id", None),
        ))
    if result.workspace is not None and result.workspace.event is not None:
        native = result.workspace.event
        events.append(make_event(
            run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
            event_type="WORKSPACE_CYCLE", payload=native.model_dump(mode="json"),
            native_id=getattr(native, "event_id", None),
        ))
    if result.plasticity is not None and result.plasticity.event is not None:
        native = result.plasticity.event
        events.append(make_event(
            run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
            event_type="PLASTICITY_CHANGED", payload=native.model_dump(mode="json"),
            native_id=getattr(native, "event_id", None),
        ))
    if result.structures is not None and result.structures.event is not None:
        native = result.structures.event
        events.append(make_event(
            run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
            event_type="STRUCTURE_CANDIDATE_OBSERVED", payload=native.model_dump(mode="json"),
            native_id=getattr(native, "event_id", None),
        ))
    return tuple(events)


def model_event(*, run_id: str, organism_id: str, kernel, command_id: str, event_type: str, model) -> EventEnvelope:
    payload = model.model_dump(mode="json") if hasattr(model, "model_dump") else dict(model)
    return make_event(
        run_id=run_id, organism_id=organism_id, kernel=kernel, command_id=command_id,
        event_type=event_type, payload=payload, native_id=getattr(model, "event_id", None),
    )
