from __future__ import annotations

import hashlib

import pytest

from verdant_development import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    WorkspaceSourceKind,
    VerdantKernel,
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
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
        semantic_evidence_details={"controlled_development_test": True},
    )


def test_one_call_connects_experience_field_resonance_and_workspace() -> None:
    kernel = VerdantKernel(seed=1201, state_dim=48, run_label="development-heartbeat")
    pipeline = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(resonance_top_k=3, resonance_commit_limit=3)
    )

    first = pipeline.advance(kernel, command("alpha-1", "alpha", (1.0, 0.0, 0.0)))
    assert first.experience.event_key == "alpha-1"
    assert first.resonance_report is not None
    assert first.resonance_event is not None
    assert first.workspace is not None
    assert first.semantic_firewall_held
    assert len(kernel.state.field.history) == 1
    assert len(kernel.state.resonance_events) == 1
    assert len(kernel.state.workspace_cycle_events) == 1
    assert any(
        item.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE
        for item in kernel.state.workspace_items.values()
    )


def test_downstream_stages_do_not_invent_semantic_truth() -> None:
    kernel = VerdantKernel(seed=1202, state_dim=48, run_label="development-firewall")
    pipeline = VerdantDevelopmentPipeline()
    result = pipeline.advance(
        kernel,
        command("alpha-1", "alpha", (1.0, 0.0, 0.0)),
    )

    assert result.semantic_firewall_held
    assert result.semantic_counts_after_experience == result.semantic_counts_after_cycle
    assert len(kernel.state.concepts) == 1
    assert len(kernel.state.relations) == 0
    assert len(kernel.state.claims) == 0


def test_same_sequence_is_deterministic() -> None:
    def build() -> VerdantKernel:
        kernel = VerdantKernel(seed=1203, state_dim=48, run_label="development-deterministic")
        pipeline = VerdantDevelopmentPipeline()
        pipeline.advance(kernel, command("alpha-1", "alpha", (1.0, 0.0, 0.0)))
        pipeline.advance(kernel, command("beta-1", "beta", (0.0, 1.0, 0.0)))
        pipeline.advance(kernel, command("alpha-2", "alpha", (1.0, 0.0, 0.0)))
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()


def test_replay_does_not_duplicate_resonance_or_workspace_activity() -> None:
    kernel = VerdantKernel(seed=1204, state_dim=48, run_label="development-replay")
    pipeline = VerdantDevelopmentPipeline()
    item = command("alpha-1", "alpha", (1.0, 0.0, 0.0))
    first = pipeline.advance(kernel, item)
    before = kernel.fingerprint()
    resonance_count = len(kernel.state.resonance_events)
    workspace_count = len(kernel.state.workspace_cycle_events)

    replay = pipeline.advance(kernel, item)

    assert not first.replayed
    assert replay.replayed
    assert replay.resonance_event is None
    assert replay.workspace is None
    assert kernel.fingerprint() == before
    assert len(kernel.state.resonance_events) == resonance_count
    assert len(kernel.state.workspace_cycle_events) == workspace_count


def test_pipeline_is_atomic_when_downstream_workspace_rejects_configuration() -> None:
    kernel = VerdantKernel(seed=1205, state_dim=48, run_label="development-atomic")
    before = kernel.snapshot()
    pipeline = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(current_evidence_resource=2.0)
    )

    with pytest.raises(Exception):
        pipeline.advance(kernel, command("alpha-1", "alpha", (1.0, 0.0, 0.0)))

    assert kernel.snapshot() == before


def test_accumulated_experience_changes_later_resonant_foreground() -> None:
    kernel = VerdantKernel(seed=1206, state_dim=64, run_label="development-path-dependent")
    pipeline = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(resonance_top_k=2, resonance_commit_limit=2)
    )
    alpha = (1.0, 0.0, 0.0, 0.0)
    beta = (0.0, 1.0, 0.0, 0.0)
    pipeline.advance(kernel, command("alpha-1", "alpha", alpha))
    pipeline.advance(kernel, command("beta-1", "beta", beta))

    before = kernel.inspect_resonance(alpha, "text", top_k=2)
    alpha_id = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "alpha"
    )
    before_score = next(
        item.score for item in before.candidates if item.concept_id == alpha_id
    )

    for index in range(2, 6):
        pipeline.advance(kernel, command(f"alpha-{index}", "alpha", alpha))

    after = kernel.inspect_resonance(alpha, "text", top_k=2)
    after_score = next(
        item.score for item in after.candidates if item.concept_id == alpha_id
    )
    assert after_score > before_score


def test_new_contradiction_is_eligible_for_the_same_shared_present() -> None:
    kernel = VerdantKernel(seed=1207, state_dim=48, run_label="development-contradiction")
    pipeline = VerdantDevelopmentPipeline()

    positive = ExperienceCommand(
        event_key="claim-positive",
        source_ref="controlled:claim-positive",
        modality="text",
        payload_sha256=digest("claim-positive"),
        feature_vector=(1.0, 0.0, 0.0),
        claim_proposals=(
            ClaimProposal(
                subject_label="indicator",
                predicate="has_property",
                object_label="bright",
                polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.DIRECT_OBSERVATION,
                confidence=1.0,
            ),
        ),
        semantic_evidence_kind=EvidenceKind.OBSERVATION,
    )
    negative = ExperienceCommand(
        event_key="claim-negative",
        source_ref="controlled:claim-negative",
        modality="text",
        payload_sha256=digest("claim-negative"),
        feature_vector=(0.0, 1.0, 0.0),
        claim_proposals=(
            ClaimProposal(
                subject_label="indicator",
                predicate="has_property",
                object_label="bright",
                polarity=ClaimPolarity.NEGATED,
                source_class=ClaimSourceClass.DIRECT_OBSERVATION,
                confidence=1.0,
            ),
        ),
        semantic_evidence_kind=EvidenceKind.OBSERVATION,
    )

    pipeline.advance(kernel, positive)
    result = pipeline.advance(kernel, negative)

    assert result.experience.contradiction_ids
    assert result.workspace is not None
    assert any(
        assessment.candidate.source_kind == WorkspaceSourceKind.CONTRADICTION
        for assessment in result.workspace.report.assessments
    )
