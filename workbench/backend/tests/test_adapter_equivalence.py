from __future__ import annotations

import hashlib
import json

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, checkpoint_bytes
from verdant_workbench import CommandEnvelope, OrganismConfig, TeachingRequest, VerdantEngineAdapter
from verdant_workbench.adapter import deterministic_feature, StaleWorkbenchCommandError


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _direct_command(*, labels: tuple[str, ...], context: str, event_key: str, width: int) -> ExperienceCommand:
    feature = deterministic_feature(labels, width)
    payload = {"event_key": event_key, "context_id": context, "labels": labels, "feature_vector": feature}
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"workbench:{context}",
        modality="text",
        payload_sha256=_digest(json.dumps(payload, sort_keys=True)),
        feature_vector=feature,
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"workbench": True, "taught_content": "primitive_symbol_presence_only"},
        metadata={"context_id": context, "workbench_event": True},
    )


def test_workbench_adapter_matches_direct_engine_for_same_commands():
    seed = 1901
    width = 16
    run_label = "wb-equivalence"
    direct = VerdantKernel(seed=seed, state_dim=width, run_label=run_label)
    pipeline = VerdantDevelopmentPipeline()
    adapter = VerdantEngineAdapter.create(
        OrganismConfig(seed=seed, state_dim=width, run_label=run_label),
        run_id="run_equivalence",
        organism_id="org_equivalence",
    )

    sequence = [
        ("world-a", ("kren", "tar"), "eq-001"),
        ("world-a", ("tar", "vel"), "eq-002"),
        ("world-b", ("kren", "tar"), "eq-003"),
        ("world-b", ("tar", "vel"), "eq-004"),
    ]
    for context, labels, event_key in sequence:
        direct_command = _direct_command(labels=labels, context=context, event_key=event_key, width=width)
        pipeline.advance(direct, direct_command)
        envelope = CommandEnvelope(
            command_id=f"cmd_{event_key}",
            run_id=adapter.run_id,
            organism_id=adapter.organism_id,
            command_type="TEACH",
            expected_state_revision=adapter.state_revision,
            actor="test",
        )
        adapter.submit_teaching(
            envelope,
            TeachingRequest(context_id=context, labels=labels, event_key=event_key),
        )

    assert direct.fingerprint() == adapter.kernel.fingerprint()
    assert checkpoint_bytes(direct.snapshot()) == checkpoint_bytes(adapter.kernel.snapshot())
    assert direct.metrics() == adapter.metrics()


def test_event_envelopes_are_traceable_and_payload_hashed():
    adapter = VerdantEngineAdapter.create(
        OrganismConfig(seed=12, state_dim=8, run_label="event-test"),
        run_id="run_event",
        organism_id="org_event",
    )
    envelope = CommandEnvelope(
        command_id="cmd_event_1",
        run_id=adapter.run_id,
        organism_id=adapter.organism_id,
        command_type="TEACH",
        expected_state_revision=adapter.state_revision,
        actor="test",
    )
    receipt = adapter.submit_teaching(envelope, TeachingRequest(context_id="lab", labels=("a", "b"), event_key="event-001"))
    assert receipt.events
    for event in receipt.events:
        assert event.source_command_id == envelope.command_id
        raw = json.dumps(event.payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        assert hashlib.sha256(raw).hexdigest() == event.payload_sha256


def test_stale_workbench_command_is_rejected_before_mutation():
    adapter = VerdantEngineAdapter.create(
        OrganismConfig(seed=12, state_dim=8, run_label="stale-test"),
        run_id="run_stale",
        organism_id="org_stale",
    )
    stale = CommandEnvelope(
        command_id="cmd_stale",
        run_id=adapter.run_id,
        organism_id=adapter.organism_id,
        command_type="TEACH",
        expected_state_revision=99,
        actor="test",
    )
    before = adapter.kernel.fingerprint()
    with pytest.raises(StaleWorkbenchCommandError):
        adapter.submit_teaching(stale, TeachingRequest(context_id="lab", labels=("a",), event_key="stale-001"))
    assert adapter.kernel.fingerprint() == before
