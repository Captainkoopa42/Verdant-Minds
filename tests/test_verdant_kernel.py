from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest

from cognitive_chunk_v2.pipeline import ExperienceInput, PipelineOrchestrator
from verdant_kernel import (
    CheckpointIntegrityError,
    EvidenceGateError,
    ExperienceCommand,
    RelationProposal,
    ReplayConflictError,
    VerdantKernel,
    checkpoint_bytes,
    ingest_cognitive_chunk,
    load_checkpoint,
    save_checkpoint,
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
    key: str,
    text: str,
    *,
    labels: tuple[str, ...] = (),
    relations: tuple[RelationProposal, ...] = (),
) -> ExperienceCommand:
    features = tuple(float(value) for value in np.linspace(0.0, 1.0, 32))
    return ExperienceCommand(
        event_key=key,
        source_ref=f"curriculum:{key}",
        modality="text",
        payload_sha256=digest(text),
        feature_vector=features,
        concept_labels=labels,
        relation_proposals=relations,
        metadata={"text_length": len(text)},
    )


def build_kernel() -> VerdantKernel:
    kernel = VerdantKernel(seed=77, state_dim=24, run_label="test")
    first = kernel.apply_experience(
        command(
            "lesson-1",
            "Gravity influences mass.",
            labels=("gravity", "mass"),
            relations=(
                RelationProposal(
                    source_label="gravity",
                    target_label="mass",
                    relation_type="influences",
                    weight=0.7,
                    confidence=0.8,
                ),
            ),
        )
    )
    kernel.set_attention_candidate(
        source_ref=first.relation_ids[0],
        priority=0.9,
        resource_request=0.25,
        reason="new causal relation",
        evidence_refs=(
            first.observation_evidence_id,
            first.translation_evidence_id,
        ),
    )
    kernel.update_governance(
        t_g=0.56,
        weights={
            "DataKing": 1.1,
            "ForefrontKing": 0.9,
            "EthicsKing": 1.5,
        },
    )
    kernel.apply_experience(
        command(
            "lesson-2",
            "Mass persists when the wording changes.",
            labels=("mass", "persistence"),
            relations=(
                RelationProposal(
                    source_label="mass",
                    target_label="persistence",
                    relation_type="supports",
                ),
            ),
        )
    )
    return kernel


def test_exact_checkpoint_round_trip(tmp_path: Path) -> None:
    kernel = build_kernel()
    path = tmp_path / "kernel.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()
    assert restored.metrics() == kernel.metrics()
    assert len(restored.state.field.history) == 2
    assert len(restored.state.attention_candidates) == 1
    assert restored.state.governance.revision == 1


def test_inspection_and_checkpoint_preview_are_pure() -> None:
    kernel = build_kernel()
    before = kernel.fingerprint()

    gravity_id = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "gravity"
    )
    _ = kernel.metrics()
    _ = kernel.neighbors(gravity_id, direction="both")
    _ = kernel.simulate_field_effect([0.1, 0.2, 0.3], "text")
    preview_one = checkpoint_bytes(kernel.snapshot())
    preview_two = checkpoint_bytes(kernel.snapshot())

    assert preview_one == preview_two
    assert kernel.fingerprint() == before


def test_one_canonical_relation_and_derived_neighbor_view() -> None:
    kernel = build_kernel()
    relation = next(iter(kernel.state.relations.values()))
    before_count = len(kernel.state.relations)

    updated = kernel.propose_relation(
        relation.source_concept_id,
        relation.target_concept_id,
        relation.relation_type,
        evidence_refs=relation.evidence_refs,
        weight=0.9,
        confidence=0.95,
    )

    assert len(kernel.state.relations) == before_count
    assert updated.relation_id == relation.relation_id
    assert updated.weight == 0.9
    assert updated.confidence == 0.95
    assert relation.target_concept_id in kernel.neighbors(
        relation.source_concept_id,
        direction="out",
    )


def test_deterministic_replay_and_idempotent_event_key() -> None:
    commands = [
        command(
            "a",
            "A pushes B.",
            labels=("A", "B"),
            relations=(
                RelationProposal(
                    source_label="A",
                    target_label="B",
                    relation_type="pushes",
                ),
            ),
        ),
        command(
            "b",
            "B pushes A.",
            labels=("B", "A"),
            relations=(
                RelationProposal(
                    source_label="B",
                    target_label="A",
                    relation_type="pushes",
                ),
            ),
        ),
    ]
    left = VerdantKernel(seed=11, state_dim=16, run_label="replay")
    right = VerdantKernel(seed=11, state_dim=16, run_label="replay")
    for item in commands:
        left.apply_experience(item)
        right.apply_experience(item)

    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()
    assert checkpoint_bytes(left.snapshot()) == checkpoint_bytes(right.snapshot())

    before = left.fingerprint()
    replay = left.apply_experience(commands[0])
    assert replay.replayed
    assert left.fingerprint() == before

    changed = commands[0].model_copy(update={"source_ref": "different-source"})
    with pytest.raises(ReplayConflictError):
        left.apply_experience(changed)


def test_evidence_gate_rejects_unsupported_relations() -> None:
    kernel = build_kernel()
    relation = next(iter(kernel.state.relations.values()))

    with pytest.raises(EvidenceGateError):
        kernel.propose_relation(
            relation.source_concept_id,
            relation.target_concept_id,
            "unsupported",
            evidence_refs=(),
        )

    with pytest.raises(EvidenceGateError):
        kernel.propose_relation(
            relation.source_concept_id,
            relation.target_concept_id,
            "unknown-evidence",
            evidence_refs=("evidence_missing",),
        )


def test_field_history_persists_and_sensitivity_is_nonmutating(tmp_path: Path) -> None:
    kernel = build_kernel()
    before = kernel.fingerprint()
    simulated = kernel.simulate_field_effect([1.0, 0.0, 0.5, 0.25], "image")
    assert simulated.shape == (24,)
    assert kernel.fingerprint() == before

    path = tmp_path / "field.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = load_checkpoint(path)
    assert restored.field.history == kernel.state.field.history
    assert restored.field.real == kernel.state.field.real
    assert restored.field.imag == kernel.state.field.imag


def test_checkpoint_integrity_detects_tampering(tmp_path: Path) -> None:
    kernel = build_kernel()
    path = tmp_path / "good.vdk"
    save_checkpoint(path, kernel.snapshot())

    with zipfile.ZipFile(path, "r") as original:
        state_payload = bytearray(original.read("state.json"))
        manifest_payload = original.read("manifest.json")
    state_payload[-2] = ord("0") if state_payload[-2] != ord("0") else ord("1")

    tampered = tmp_path / "tampered.vdk"
    with zipfile.ZipFile(tampered, "w") as archive:
        archive.writestr("state.json", bytes(state_payload))
        archive.writestr("manifest.json", manifest_payload)

    with pytest.raises(CheckpointIntegrityError):
        load_checkpoint(tampered)


def test_cognitive_chunk_v2_enters_kernel_without_semantic_promotion() -> None:
    orchestrator = PipelineOrchestrator()
    chunk, store = orchestrator.process(
        ExperienceInput.from_text(
            "Gravity pulls objects downward.",
            source_id="handwritten_physics_curriculum",
        )
    )
    kernel = VerdantKernel(seed=99, state_dim=32, run_label="chunk-adapter")

    results = ingest_cognitive_chunk(kernel, chunk, store, event_key="chunk-test")

    assert len(results) == 1
    assert len(kernel.state.evidence) == 2
    assert len(kernel.state.concepts) == 0
    assert len(kernel.state.relations) == 0
    assert len(kernel.state.field.history) == 1
    assert kernel.state.evidence[results[0].observation_evidence_id].source_ref == (
        "handwritten_physics_curriculum"
    )


def test_cognitive_chunk_adapter_is_deterministic_across_fresh_chunk_ids() -> None:
    left_chunk, left_store = PipelineOrchestrator().process(
        ExperienceInput.from_text(
            "The same native event.",
            source_id="deterministic_native_source",
        )
    )
    right_chunk, right_store = PipelineOrchestrator().process(
        ExperienceInput.from_text(
            "The same native event.",
            source_id="deterministic_native_source",
        )
    )
    left = VerdantKernel(seed=101, state_dim=32, run_label="adapter-replay")
    right = VerdantKernel(seed=101, state_dim=32, run_label="adapter-replay")

    ingest_cognitive_chunk(left, left_chunk, left_store, event_key="same-event")
    ingest_cognitive_chunk(right, right_chunk, right_store, event_key="same-event")

    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()
