from __future__ import annotations

import json
from pathlib import Path

from cognitive_chunk_v2.archive import CognitiveChunkArchive
from verdant_claims import ClaimLearningPipeline
from verdant_ecwf import VerdantECWFPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    GovernanceProposalKind,
    KingName,
    VerdantKernel,
    save_checkpoint,
)
from verdant_language import GrammarRuleId, VerdantLanguagePipeline

from .pipeline import VerdantGovernancePipeline


def _claim_support_refs(kernel: VerdantKernel, claim_id: str) -> tuple[str, ...]:
    return tuple(
        entry.evidence_id for entry in kernel.state.claims[claim_id].support_ledger
    )


def _assessment_map(report) -> dict[str, object]:
    return {
        item.king.value: item.model_dump(mode="json") for item in report.assessments
    }


def run_demo(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=2605, state_dim=64, run_label="milestone-5-council")
    language = VerdantLanguagePipeline()
    claims = ClaimLearningPipeline()
    ecwf = VerdantECWFPipeline()
    governance = VerdantGovernancePipeline()

    language.teach_rule(kernel, GrammarRuleId.COPULAR_PROPERTY)
    language.teach_foundational_lexicon(kernel)
    language.learn_sentence(kernel, "The door is open.", event_key="teacher-open")
    observed = claims.record_claim(
        kernel,
        event_key="visual-closed",
        native_description="Controlled visual observation: the door is closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
        rationale="The visible door state conflicts with testimony.",
    )
    blocked = claims.record_claim(
        kernel,
        event_key="motion-blocked",
        native_description="Controlled physical outcome: forward movement was blocked.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.PHYSICAL_OUTCOME,
        rationale="The blocked motion supports the closed-door claim.",
    )
    history = kernel.claim_history("lexeme:door", "has_property", "lexeme:open")
    affirmative = next(
        item for item in history if item.polarity == ClaimPolarity.AFFIRMED
    )
    negated = next(item for item in history if item.polarity == ClaimPolarity.NEGATED)
    evidence_refs = tuple(
        sorted(
            set(_claim_support_refs(kernel, affirmative.claim_id))
            | set(_claim_support_refs(kernel, negated.claim_id))
        )
    )

    query = ecwf.inspect_text(kernel, "The door is open.", top_k=5)
    query_archive = output_dir / "milestone_5_door_resonance_query.ecchunk.zip"
    CognitiveChunkArchive.save(query_archive, query.chunk, query.store)
    resonance_event = ecwf.commit(
        kernel,
        query,
        evidence_refs=evidence_refs,
        max_candidates=5,
    )

    force_proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.ACT,
        operation="force_forward_through_door",
        action_class="forceful_forward_movement",
        description="Attempt forceful forward movement through the disputed doorway.",
        target_claim_id=affirmative.claim_id,
        evidence_refs=evidence_refs,
        attention_candidate_ids=resonance_event.attention_candidate_ids,
        resonance_event_ids=(resonance_event.resonance_event_id,),
        relevance=1.0,
        urgency=0.8,
        novelty=0.2,
        predicted_information_gain=0.4,
        harm_risk=0.75,
        reversibility=0.15,
        safe_alternatives=("inspect_door",),
    )
    force_report = governance.inspect(kernel, force_proposal)
    force_event = governance.commit(kernel, force_report)

    inspection_proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_door",
        action_class="visual_door_inspection",
        description="Inspect the doorway without applying force.",
        target_claim_id=affirmative.claim_id,
        evidence_refs=evidence_refs,
        attention_candidate_ids=resonance_event.attention_candidate_ids,
        resonance_event_ids=(resonance_event.resonance_event_id,),
        relevance=1.0,
        urgency=0.6,
        novelty=0.2,
        predicted_information_gain=1.0,
        harm_risk=0.05,
        reversibility=1.0,
    )
    inspection_report = governance.inspect(kernel, inspection_proposal)
    inspection_event = governance.commit(kernel, inspection_report)
    kernel.assert_operation_authorized(
        inspection_event.decision_event_id,
        "inspect_door",
    )

    reports_path = output_dir / "milestone_5_council_reports.json"
    reports_payload = {
        "force_through_door": force_report.model_dump(mode="json"),
        "safe_door_inspection": inspection_report.model_dump(mode="json"),
    }
    reports_path.write_text(json.dumps(reports_payload, indent=2, sort_keys=True))

    checkpoint_path = output_dir / "milestone_5_governance_demo.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())
    force_by_king = _assessment_map(force_report)
    summary = {
        "milestone": 5,
        "description": (
            "Constitutionally separated Data, Forefront, and Ethics Kings; "
            "rule-ordered Council decisions and operation authorization."
        ),
        "kernel_id": kernel.state.identity.kernel_id,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "metrics": kernel.metrics(),
        "governance_policy": kernel.state.governance.model_dump(mode="json"),
        "door_case": {
            "affirmative_claim_id": affirmative.claim_id,
            "negated_claim_id": negated.claim_id,
            "current_belief_id": kernel.current_belief(
                "lexeme:door", "has_property", "lexeme:open"
            ).claim_id,
            "resonance_event_id": resonance_event.resonance_event_id,
            "resonance_candidate_count": len(
                resonance_event.attention_candidate_ids
            ),
            "force_decision": force_report.disposition.value,
            "force_authorized_operations": list(
                force_report.authorized_operations
            ),
            "force_blocked_operations": list(force_report.blocked_operations),
            "force_safe_alternatives": list(force_report.safe_alternatives),
            "king_assessments": force_by_king,
            "safe_inspection_decision": inspection_report.disposition.value,
            "safe_inspection_authorized_operations": list(
                inspection_report.authorized_operations
            ),
            "safe_inspection_constraints": list(inspection_report.constraints),
            "force_decision_event_id": force_event.decision_event_id,
            "inspection_decision_event_id": inspection_event.decision_event_id,
        },
        "council_reports": str(reports_path),
        "resonance_query_archive": str(query_archive),
        "important_boundaries": [
            "The Council does not create evidence, concepts, relations, or claims.",
            "Resonance affects Forefront availability but is never Data King evidence.",
            "The three King assessments are combined by explicit rule order, not a weighted average.",
            "Physical outcomes are controlled declarations in this milestone.",
        ],
        "claims_not_made": [
            "general moral reasoning",
            "autonomous policy discovery",
            "live embodied action",
            "consciousness",
        ],
    }
    summary_path = output_dir / "milestone_5_governance_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    artifact_dir = Path(__file__).resolve().parents[1] / "artifacts"
    print(json.dumps(run_demo(artifact_dir), indent=2, sort_keys=True))
