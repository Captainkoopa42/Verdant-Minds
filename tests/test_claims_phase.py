from __future__ import annotations

from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    ClaimStatus,
    EvidenceGateError,
    EvidenceKind,
    ExperienceCommand,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_language import GrammarRuleId, VerdantLanguagePipeline


def teach_property_language(kernel: VerdantKernel) -> VerdantLanguagePipeline:
    pipeline = VerdantLanguagePipeline()
    pipeline.teach_rule(kernel, GrammarRuleId.COPULAR_PROPERTY)
    pipeline.teach_foundational_lexicon(kernel)
    return pipeline


def test_opposed_handwritten_claims_are_localized_without_overwrite() -> None:
    kernel = VerdantKernel(seed=301, state_dim=48, run_label="claim-conflict")
    language = teach_property_language(kernel)

    language.learn_sentence(kernel, "The door is open.", event_key="claim-positive")
    language.learn_sentence(kernel, "The door is not open.", event_key="claim-negative")

    history = kernel.claim_history("lexeme:door", "has_property", "lexeme:open")
    assert len(history) == 2
    assert {claim.polarity for claim in history} == {
        ClaimPolarity.AFFIRMED,
        ClaimPolarity.NEGATED,
    }
    assert len(kernel.state.contradictions) == 1
    contradiction = next(iter(kernel.state.contradictions.values()))
    assert contradiction.preferred_claim_id is None
    assert {claim.status for claim in history} == {ClaimStatus.CONTESTED}
    assert kernel.current_belief("lexeme:door", "has_property", "lexeme:open") is None


def test_direct_observation_outweighs_single_human_testimony_and_creates_revision() -> None:
    kernel = VerdantKernel(seed=302, state_dim=48, run_label="observation-revision")
    language = teach_property_language(kernel)
    claims = ClaimLearningPipeline()

    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open")
    prior = kernel.current_belief("lexeme:door", "has_property", "lexeme:open")
    assert prior is not None and prior.polarity == ClaimPolarity.AFFIRMED

    claims.record_claim(
        kernel,
        event_key="visual-door-closed",
        native_description="Controlled visual observation: the door is visibly closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
        rationale="Controlled visual source contradicts teacher testimony.",
    )

    current = kernel.current_belief("lexeme:door", "has_property", "lexeme:open")
    assert current is not None and current.polarity == ClaimPolarity.NEGATED
    assert len(kernel.state.revisions) == 1
    revision = kernel.state.revisions[0]
    assert revision.prior_claim_id == prior.claim_id
    assert revision.revised_to_claim_id == current.claim_id
    assert kernel.state.claims[prior.claim_id].status == ClaimStatus.REVISED
    assert kernel.state.claims[prior.claim_id].support_ledger
    assert kernel.state.claims[prior.claim_id].refutation_ledger


def test_physical_outcome_strengthens_current_belief_without_erasing_conflict() -> None:
    kernel = VerdantKernel(seed=303, state_dim=48, run_label="outcome-weight")
    language = teach_property_language(kernel)
    claims = ClaimLearningPipeline()

    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open")
    claims.record_claim(
        kernel,
        event_key="outcome-blocked",
        native_description="Controlled outcome: forward motion was blocked by the closed door.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.PHYSICAL_OUTCOME,
        rationale="A physical consequence supports the negated claim.",
    )

    current = kernel.current_belief("lexeme:door", "has_property", "lexeme:open")
    assert current is not None and current.polarity == ClaimPolarity.NEGATED
    contradiction = next(iter(kernel.state.contradictions.values()))
    assert contradiction.preferred_claim_id == current.claim_id
    assert len(kernel.claim_history("lexeme:door", "has_property", "lexeme:open")) == 2
    assert any(
        entry.source_class == ClaimSourceClass.PHYSICAL_OUTCOME
        for entry in current.support_ledger
    )


def test_repeated_independent_testimony_can_reopen_uncertainty_but_not_delete_observation() -> None:
    kernel = VerdantKernel(seed=304, state_dim=48, run_label="reopen-uncertainty")
    language = teach_property_language(kernel)
    claims = ClaimLearningPipeline()

    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open-1")
    claims.record_claim(
        kernel,
        event_key="visual-closed",
        native_description="Controlled visual observation: the door is closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open-2")
    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open-3")

    assert kernel.current_belief("lexeme:door", "has_property", "lexeme:open") is None
    contradiction = next(iter(kernel.state.contradictions.values()))
    assert contradiction.preferred_claim_id is None
    negative = next(
        claim for claim in kernel.state.claims.values()
        if claim.polarity == ClaimPolarity.NEGATED
    )
    assert any(
        entry.source_class == ClaimSourceClass.DIRECT_OBSERVATION
        for entry in negative.support_ledger
    )
    assert len(kernel.state.revisions) == 1


def test_claim_requires_explicit_semantic_evidence() -> None:
    kernel = VerdantKernel(seed=305, state_dim=16, run_label="claim-gate")
    command = ExperienceCommand(
        event_key="ungrounded-claim",
        source_ref="test",
        modality="text",
        payload_sha256="0" * 64,
        feature_vector=(0.1, 0.2),
        claim_proposals=(
            ClaimProposal(
                subject_label="door",
                predicate="has_property",
                object_label="open",
                polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.SYSTEM_INFERENCE,
            ),
        ),
    )
    with pytest.raises(EvidenceGateError):
        kernel.apply_experience(command)


def test_support_and_refutation_ledgers_use_same_preserved_evidence() -> None:
    kernel = VerdantKernel(seed=306, state_dim=32, run_label="ledger")
    claims = ClaimLearningPipeline()
    claims.record_claim(
        kernel,
        event_key="positive-observation",
        native_description="Controlled observation says the indicator is bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    claims.record_claim(
        kernel,
        event_key="negative-observation",
        native_description="Controlled observation says the indicator is not bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    history = kernel.claim_history("indicator", "has_property", "bright")
    affirmed = next(item for item in history if item.polarity == ClaimPolarity.AFFIRMED)
    negated = next(item for item in history if item.polarity == ClaimPolarity.NEGATED)
    assert {entry.evidence_id for entry in affirmed.refutation_ledger} == {
        entry.evidence_id for entry in negated.support_ledger
    }
    assert {entry.evidence_id for entry in negated.refutation_ledger} == {
        entry.evidence_id for entry in affirmed.support_ledger
    }


def test_claim_checkpoint_round_trip_preserves_history_and_current_belief(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=307, state_dim=40, run_label="claim-checkpoint")
    language = teach_property_language(kernel)
    claims = ClaimLearningPipeline()
    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open")
    claims.record_claim(
        kernel,
        event_key="visual-closed",
        native_description="Controlled visual observation: the door is closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    path = tmp_path / "claims.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()
    current = restored.current_belief("lexeme:door", "has_property", "lexeme:open")
    assert current is not None and current.polarity == ClaimPolarity.NEGATED
    assert len(restored.state.revisions) == 1


def test_claim_sequence_is_deterministic() -> None:
    def build() -> VerdantKernel:
        kernel = VerdantKernel(seed=308, state_dim=36, run_label="claim-replay")
        claims = ClaimLearningPipeline()
        claims.record_claim(
            kernel,
            event_key="claim-a",
            native_description="Teacher testimony: the panel is active.",
            subject_label="panel",
            predicate="has_property",
            object_label="active",
            polarity=ClaimPolarity.AFFIRMED,
            source_class=ClaimSourceClass.HUMAN_TESTIMONY,
        )
        claims.record_claim(
            kernel,
            event_key="claim-b",
            native_description="Physical outcome: the panel did not respond.",
            subject_label="panel",
            predicate="has_property",
            object_label="active",
            polarity=ClaimPolarity.NEGATED,
            source_class=ClaimSourceClass.PHYSICAL_OUTCOME,
        )
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()
