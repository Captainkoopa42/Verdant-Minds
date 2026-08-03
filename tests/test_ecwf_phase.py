from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    KernelInvariantError,
    ResonanceIntegrityError,
    ResonanceStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def experience(
    event_key: str,
    label: str,
    features: tuple[float, ...],
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"controlled:{event_key}",
        modality="text",
        payload_sha256=digest(f"{event_key}:{label}"),
        feature_vector=features,
        concept_labels=(label,),
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_ecwf_test": True},
    )


def populated_kernel() -> VerdantKernel:
    kernel = VerdantKernel(seed=404, state_dim=64, run_label="ecwf-test")
    kernel.apply_experience(experience("alpha-1", "alpha", (1.0, 0.0, 0.0, 0.0)))
    kernel.apply_experience(experience("beta-1", "beta", (0.0, 1.0, 0.0, 0.0)))
    kernel.apply_experience(experience("gamma-1", "gamma", (0.0, 0.0, 1.0, 0.0)))
    return kernel


def test_addresses_are_deterministic_unique_dense_and_complete() -> None:
    left = populated_kernel()
    right = populated_kernel()

    assert left.state.field_addresses == right.state.field_addresses
    assert set(left.state.field_addresses) == set(left.state.concepts)
    diagnostics = left.address_diagnostics()
    assert diagnostics["address_count"] == 3
    assert diagnostics["duplicate_digest_count"] == 0
    assert diagnostics["duplicate_vector_count"] == 0
    assert diagnostics["max_pair_similarity"] < 1.0
    for address in left.state.field_addresses.values():
        assert len(address.real) == left.state.field.state_dim
        assert len(address.imag) == left.state.field.state_dim
        assert sum(abs(value) > 0.0 for value in address.real) > 1
        assert sum(abs(value) > 0.0 for value in address.imag) > 1


def test_resonance_inspection_is_pure_and_exposes_exact_contributions() -> None:
    kernel = populated_kernel()
    before = kernel.fingerprint()
    report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=3)

    assert kernel.fingerprint() == before
    assert len(report.candidates) == 3
    for candidate in report.candidates:
        contribution = candidate.contribution
        expected = (
            contribution.weighted_profile
            + contribution.weighted_current_field
            + contribution.weighted_history
        )
        assert candidate.score == pytest.approx(expected, abs=1e-12)
        assert (
            contribution.profile_weight
            + contribution.current_field_weight
            + contribution.history_weight
        ) == pytest.approx(1.0, abs=1e-12)


def test_same_cue_changes_after_accumulated_experience() -> None:
    kernel = VerdantKernel(seed=405, state_dim=64, run_label="path-dependent")
    alpha_features = (1.0, 0.0, 0.0, 0.0)
    beta_features = (0.0, 1.0, 0.0, 0.0)
    kernel.apply_experience(experience("alpha-1", "alpha", alpha_features))
    kernel.apply_experience(experience("beta-1", "beta", beta_features))

    before = kernel.inspect_resonance(alpha_features, "text", top_k=2)
    before_by_id = {item.concept_id: item.score for item in before.candidates}
    alpha_id = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "alpha"
    )

    for index in range(2, 7):
        kernel.apply_experience(
            experience(f"alpha-{index}", "alpha", alpha_features)
        )

    after = kernel.inspect_resonance(alpha_features, "text", top_k=2)
    after_by_id = {item.concept_id: item.score for item in after.candidates}
    assert after_by_id[alpha_id] > before_by_id[alpha_id]
    assert after.candidates[0].concept_id == alpha_id


def test_resonance_inspection_cannot_create_semantic_structure() -> None:
    kernel = populated_kernel()
    semantic_counts = (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )
    _ = kernel.inspect_resonance((0.2, 0.3, 0.4), "text", top_k=3)
    assert semantic_counts == (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )


def test_committed_resonance_only_adds_attention_and_audit_history() -> None:
    kernel = populated_kernel()
    latest = kernel.apply_experience(
        experience("alpha-cue-source", "alpha", (1.0, 0.0, 0.0, 0.0))
    )
    report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=2)
    before_semantic = (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
    )
    event = kernel.commit_resonance(
        report,
        evidence_refs=(
            latest.observation_evidence_id,
            latest.translation_evidence_id,
        ),
    )

    assert event.semantic_mutation_permitted is False
    assert len(event.attention_candidate_ids) == 2
    assert len(kernel.state.resonance_events) == 1
    assert before_semantic == (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
    )
    assert all(
        candidate_id in kernel.state.attention_candidates
        for candidate_id in event.attention_candidate_ids
    )


def test_stale_report_is_rejected() -> None:
    kernel = populated_kernel()
    report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=2)
    latest = kernel.apply_experience(
        experience("delta-1", "delta", (0.0, 0.0, 0.0, 1.0))
    )
    with pytest.raises(ResonanceStaleError):
        kernel.commit_resonance(
            report,
            evidence_refs=(latest.observation_evidence_id,),
        )



def test_tampered_report_is_rejected() -> None:
    kernel = populated_kernel()
    latest = kernel.apply_experience(
        experience("alpha-source-tamper", "alpha", (1.0, 0.0, 0.0, 0.0))
    )
    report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=2)
    first = report.candidates[0]
    tampered = report.model_copy(
        update={
            "candidates": (
                first.model_copy(update={"score": min(1.0, first.score + 0.1)}),
                *report.candidates[1:],
            )
        }
    )
    with pytest.raises(ResonanceIntegrityError):
        kernel.commit_resonance(
            tampered,
            evidence_refs=(latest.observation_evidence_id,),
        )

def test_checkpoint_round_trip_preserves_ecwf_exactly(tmp_path: Path) -> None:
    kernel = populated_kernel()
    latest = kernel.apply_experience(
        experience("alpha-2", "alpha", (1.0, 0.0, 0.0, 0.0))
    )
    report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=2)
    kernel.commit_resonance(
        report,
        evidence_refs=(latest.observation_evidence_id, latest.translation_evidence_id),
    )
    path = tmp_path / "ecwf.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()
    assert restored.field_fingerprint() == kernel.field_fingerprint()
    assert restored.address_diagnostics() == kernel.address_diagnostics()


def test_ecwf_sequence_is_deterministic() -> None:
    def build() -> VerdantKernel:
        kernel = populated_kernel()
        latest = kernel.apply_experience(
            experience("alpha-2", "alpha", (1.0, 0.0, 0.0, 0.0))
        )
        report = kernel.inspect_resonance((1.0, 0.0, 0.0, 0.0), "text", top_k=2)
        kernel.commit_resonance(
            report,
            evidence_refs=(latest.observation_evidence_id,),
        )
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()


def test_old_state_without_addresses_is_migrated_deterministically() -> None:
    kernel = populated_kernel()
    old_state = kernel.snapshot()
    old_state.identity = old_state.identity.model_copy(
        update={"schema_version": "0.3.0-alpha"}
    )
    old_state.field_addresses = {}

    restored = VerdantKernel.from_state(old_state)
    assert restored.state.identity.schema_version == "1.0.0-alpha"
    assert set(restored.state.field_addresses) == set(restored.state.concepts)
    assert restored.address_diagnostics()["duplicate_digest_count"] == 0


def test_address_revision_requires_explicit_migration_after_learning() -> None:
    kernel = populated_kernel()
    with pytest.raises(KernelInvariantError):
        kernel.update_ecwf_policy(address_revision=2)
