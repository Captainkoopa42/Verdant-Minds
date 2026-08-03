from __future__ import annotations

from pathlib import Path

import pytest

from verdant_claims import ClaimLearningPipeline
from verdant_ecwf import VerdantECWFPipeline
from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    CouncilDisposition,
    GovernanceAuthorizationError,
    GovernanceIntegrityError,
    GovernanceProposalKind,
    GovernanceStaleError,
    KingName,
    KingRecommendation,
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


def door_conflict_kernel() -> tuple[
    VerdantKernel,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    kernel = VerdantKernel(seed=505, state_dim=64, run_label="governance-door")
    language = teach_property_language(kernel)
    claims = ClaimLearningPipeline()
    taught = language.learn_sentence(
        kernel,
        "The door is open.",
        event_key="teacher-open",
    )
    observed = claims.record_claim(
        kernel,
        event_key="visual-closed",
        native_description="Controlled visual observation: the door is closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    outcome = claims.record_claim(
        kernel,
        event_key="motion-blocked",
        native_description="Controlled physical outcome: forward motion was blocked.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.PHYSICAL_OUTCOME,
    )
    history = kernel.claim_history("lexeme:door", "has_property", "lexeme:open")
    affirmative = next(
        item for item in history if item.polarity == ClaimPolarity.AFFIRMED
    )
    testimony_refs = tuple(
        entry.evidence_id for entry in affirmative.support_ledger
    )
    observed_claim = kernel.state.claims[observed.kernel_result.claim_ids[0]]
    outcome_claim = kernel.state.claims[outcome.kernel_result.claim_ids[0]]
    observation_refs = tuple(
        entry.evidence_id for entry in observed_claim.support_ledger
    )
    outcome_refs = tuple(entry.evidence_id for entry in outcome_claim.support_ledger)
    return (
        kernel,
        affirmative.claim_id,
        testimony_refs,
        observation_refs,
        outcome_refs,
    )


def add_door_resonance(
    kernel: VerdantKernel,
    evidence_refs: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ecwf = VerdantECWFPipeline()
    query = ecwf.inspect_text(kernel, "The door is open.", top_k=5)
    event = ecwf.commit(
        kernel,
        query,
        evidence_refs=evidence_refs,
        max_candidates=5,
    )
    return event.attention_candidate_ids, (event.resonance_event_id,)


def assessment(report, king: KingName):
    return next(item for item in report.assessments if item.king == king)


def test_kings_render_separate_judgments_and_council_denies_force() -> None:
    kernel, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    attention, resonance = add_door_resonance(kernel, testimony + observed + outcome)
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.ACT,
        operation="force_forward_through_door",
        action_class="forceful_forward_movement",
        description="Attempt forceful forward movement through the disputed doorway.",
        target_claim_id=affirmative_id,
        evidence_refs=testimony + observed + outcome,
        attention_candidate_ids=attention,
        resonance_event_ids=resonance,
        relevance=1.0,
        urgency=0.8,
        novelty=0.2,
        predicted_information_gain=0.4,
        harm_risk=0.75,
        reversibility=0.15,
        safe_alternatives=("inspect_door",),
    )
    before = kernel.fingerprint()
    report = governance.inspect(kernel, proposal)
    assert kernel.fingerprint() == before

    data = assessment(report, KingName.DATA)
    forefront = assessment(report, KingName.FOREFRONT)
    ethics = assessment(report, KingName.ETHICS)
    assert data.recommendation == KingRecommendation.OPPOSE
    assert forefront.recommendation == KingRecommendation.PRIORITIZE
    assert ethics.recommendation == KingRecommendation.DENY
    assert data.details["resonance_used_as_evidence"] is False
    assert report.disposition == CouncilDisposition.DENY
    assert report.authorized_operations == ()
    assert report.blocked_operations == ("force_forward_through_door",)
    assert "inspect_door" in report.safe_alternatives


def test_safe_investigation_is_authorized_to_return_new_evidence() -> None:
    kernel, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    attention, resonance = add_door_resonance(kernel, testimony + observed + outcome)
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_door",
        action_class="visual_door_inspection",
        description="Inspect the doorway without applying force.",
        target_claim_id=affirmative_id,
        evidence_refs=testimony + observed + outcome,
        attention_candidate_ids=attention,
        resonance_event_ids=resonance,
        relevance=1.0,
        urgency=0.6,
        novelty=0.2,
        predicted_information_gain=1.0,
        harm_risk=0.05,
        reversibility=1.0,
    )
    report = governance.inspect(kernel, proposal)
    assert assessment(report, KingName.DATA).recommendation == KingRecommendation.REQUEST_EVIDENCE
    assert assessment(report, KingName.FOREFRONT).recommendation == KingRecommendation.PRIORITIZE
    assert assessment(report, KingName.ETHICS).recommendation == KingRecommendation.PERMIT
    assert report.disposition == CouncilDisposition.APPROVE_WITH_CONSTRAINTS
    assert report.authorized_operations == ("inspect_door",)
    assert "result_must_return_through_evidence_pipeline" in report.constraints
    event = governance.commit(kernel, report)
    kernel.assert_operation_authorized(event.decision_event_id, "inspect_door")


def test_denied_operation_is_causally_blocked() -> None:
    kernel, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.ACT,
        operation="force_forward",
        action_class="forceful_forward_movement",
        description="Force forward despite the disputed door state.",
        target_claim_id=affirmative_id,
        evidence_refs=testimony + observed + outcome,
        relevance=1.0,
        urgency=1.0,
        predicted_information_gain=0.5,
        harm_risk=0.9,
        reversibility=0.1,
    )
    event = governance.commit(kernel, governance.inspect(kernel, proposal))
    with pytest.raises(GovernanceAuthorizationError):
        kernel.assert_operation_authorized(event.decision_event_id, "force_forward")


def test_council_inspection_and_commit_do_not_fabricate_semantic_evidence() -> None:
    kernel, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    governance = VerdantGovernancePipeline()
    semantic_counts = (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_door",
        action_class="visual_door_inspection",
        description="Inspect the disputed doorway.",
        target_claim_id=affirmative_id,
        evidence_refs=testimony + observed + outcome,
        relevance=1.0,
        urgency=0.5,
        predicted_information_gain=1.0,
        harm_risk=0.0,
    )
    report = governance.inspect(kernel, proposal)
    event = governance.commit(kernel, report)
    assert event.semantic_mutation_permitted is False
    assert event.governance_policy_mutation_permitted is False
    assert semantic_counts == (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )


def test_ethics_ablation_changes_private_boundary_decision() -> None:
    claims = ClaimLearningPipeline()
    base = VerdantKernel(seed=506, state_dim=48, run_label="ethics-ablation")
    direct = claims.record_claim(
        base,
        event_key="toy-location",
        native_description="Direct observation: the toy is behind the private door.",
        subject_label="toy",
        predicate="located_behind",
        object_label="private_door",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    claim_id = direct.kernel_result.claim_ids[0]
    evidence = tuple(
        entry.evidence_id for entry in base.state.claims[claim_id].support_ledger
    )
    full = VerdantKernel.from_state(base.snapshot())
    ablated = VerdantKernel.from_state(base.snapshot())
    ablated.update_governance(
        enabled_kings={
            KingName.DATA.value: True,
            KingName.FOREFRONT.value: True,
            KingName.ETHICS.value: False,
        }
    )
    governance = VerdantGovernancePipeline()

    def inspect(kernel: VerdantKernel):
        proposal = governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.ACT,
            operation="open_private_door",
            action_class="private_boundary_entry",
            description="Open a private door to retrieve the observed toy.",
            target_claim_id=claim_id,
            evidence_refs=evidence,
            relevance=1.0,
            urgency=1.0,
            novelty=0.2,
            predicted_information_gain=0.8,
            harm_risk=0.05,
            reversibility=0.9,
            consent_required=True,
            consent_present=False,
            boundary_sensitive=True,
        )
        return governance.inspect(kernel, proposal)

    full_report = inspect(full)
    ablated_report = inspect(ablated)
    assert full_report.disposition == CouncilDisposition.DENY
    assert ablated_report.disposition == CouncilDisposition.APPROVE
    assert "king_disabled:EthicsKing" in ablated_report.rationale_codes




def test_tampered_and_stale_reports_are_rejected() -> None:
    kernel, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_door",
        action_class="visual_door_inspection",
        description="Inspect the disputed doorway.",
        target_claim_id=affirmative_id,
        evidence_refs=testimony + observed + outcome,
        relevance=1.0,
        urgency=0.5,
        predicted_information_gain=1.0,
    )
    report = governance.inspect(kernel, proposal)
    tampered = report.model_copy(update={"disposition": CouncilDisposition.APPROVE})
    with pytest.raises(GovernanceIntegrityError):
        governance.commit(kernel, tampered)

    claims = ClaimLearningPipeline()
    claims.record_claim(
        kernel,
        event_key="new-state",
        native_description="New direct observation changes the canonical state.",
        subject_label="new",
        predicate="has_property",
        object_label="state",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    with pytest.raises(GovernanceStaleError):
        governance.commit(kernel, report)



def test_governance_sequence_is_deterministic() -> None:
    def build() -> VerdantKernel:
        kernel = VerdantKernel(seed=509, state_dim=40, run_label="governance-replay")
        claims = ClaimLearningPipeline()
        governance = VerdantGovernancePipeline()
        context = claims.record_claim(
            kernel,
            event_key="context",
            native_description="Direct observation: test context is available.",
            subject_label="test",
            predicate="has_property",
            object_label="context",
            polarity=ClaimPolarity.AFFIRMED,
            source_class=ClaimSourceClass.DIRECT_OBSERVATION,
        )
        claim_id = context.kernel_result.claim_ids[0]
        evidence = tuple(
            entry.evidence_id for entry in kernel.state.claims[claim_id].support_ledger
        )
        proposal = governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.INVESTIGATE,
            operation="inspect_context",
            action_class="context_inspection",
            description="Inspect the available test context.",
            target_claim_id=claim_id,
            evidence_refs=evidence,
            relevance=1.0,
            urgency=0.8,
            predicted_information_gain=0.8,
            harm_risk=0.0,
        )
        governance.commit(kernel, governance.inspect(kernel, proposal))
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()


def test_legacy_weights_do_not_turn_council_into_weighted_average() -> None:
    base, affirmative_id, testimony, observed, outcome = door_conflict_kernel()
    left = VerdantKernel.from_state(base.snapshot())
    right = VerdantKernel.from_state(base.snapshot())
    right.update_governance(
        weights={
            KingName.DATA.value: 1000.0,
            KingName.FOREFRONT.value: 0.0001,
            KingName.ETHICS.value: 0.0001,
        }
    )
    governance = VerdantGovernancePipeline()

    def decision(kernel: VerdantKernel) -> CouncilDisposition:
        proposal = governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.ACT,
            operation="force_forward",
            action_class="forceful_forward_movement",
            description="Force forward through the disputed door.",
            target_claim_id=affirmative_id,
            evidence_refs=testimony + observed + outcome,
            relevance=1.0,
            urgency=1.0,
            predicted_information_gain=0.5,
            harm_risk=0.9,
            reversibility=0.1,
        )
        report = governance.inspect(kernel, proposal)
        assert report.policy_snapshot["legacy_weights_used_for_decision"] is False
        return report.disposition

    assert decision(left) == CouncilDisposition.DENY
    assert decision(right) == CouncilDisposition.DENY
