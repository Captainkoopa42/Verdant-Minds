from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_claims import ClaimLearningPipeline
from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    GovernanceProposalKind,
    WorkspaceCandidateInput,
    WorkspaceSignals,
    WorkspaceSourceKind,
    WorkspaceWritebackDisposition,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_workspace import VerdantWorkspacePipeline


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
BASE_CHECKPOINT = ARTIFACT_DIR / "milestone_7_objects_demo.vdk"
CHECKPOINT_PATH = ARTIFACT_DIR / "milestone_9_workspace_demo.vdk"
SUMMARY_PATH = ARTIFACT_DIR / "milestone_9_workspace_summary.json"
REPORTS_PATH = ARTIFACT_DIR / "milestone_9_workspace_reports.json"


def native_evidence(
    kernel: VerdantKernel,
    *,
    key: str,
    features: tuple[float, ...],
    kind: EvidenceKind | None = None,
    modality: str = "controlled_native",
) -> str:
    payload = f"{key}:{features}:{kind}".encode("utf-8")
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"milestone-9:{key}",
            modality=modality,
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            feature_vector=features,
            semantic_evidence_kind=kind,
            semantic_evidence_details={
                "controlled_test": True,
                "live_hardware_connected": False,
            },
        )
    )
    return (
        result.additional_evidence_ids[0]
        if kind is not None
        else result.observation_evidence_id
    )




def source_candidate(
    *,
    kind: WorkspaceSourceKind,
    source_ref: str,
    label: str,
    evidence_refs: tuple[str, ...],
    resource: float,
    signals: WorkspaceSignals,
    persistence: int = 4,
    operation: str | None = None,
    binding_refs: tuple[str, ...] = (),
) -> WorkspaceCandidateInput:
    return WorkspaceCandidateInput(
        source_kind=kind,
        source_ref=source_ref,
        label=label,
        evidence_refs=tuple(sorted(evidence_refs)),
        resource_request=resource,
        persistence_cycles=persistence,
        signals=signals,
        operation=operation,
        binding_refs=tuple(sorted(binding_refs)),
        metadata={"milestone_9_controlled_source": True},
    )


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel.from_state(load_checkpoint(BASE_CHECKPOINT))
    claims = ClaimLearningPipeline()
    governance = VerdantGovernancePipeline()
    workspace = VerdantWorkspacePipeline()

    testimony = claims.record_claim(
        kernel,
        event_key="workspace-door-testimony",
        native_description="Teacher testimony: the door is open.",
        subject_label="door",
        predicate="has_property",
        object_label="open",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.HUMAN_TESTIMONY,
    )
    observation = claims.record_claim(
        kernel,
        event_key="workspace-door-observation",
        native_description="Controlled observation: the door is closed.",
        subject_label="door",
        predicate="has_property",
        object_label="open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    contradiction_id = observation.kernel_result.contradiction_ids[0]
    contradiction = kernel.state.contradictions[contradiction_id]
    current_evidence = observation.kernel_result.additional_evidence_ids[0]

    object_candidate = next(
        item
        for item in kernel.state.object_candidates.values()
        if item.promoted_concept_id is not None
    )
    object_concept_id = object_candidate.promoted_concept_id
    active_shard = kernel.state.shards[kernel.state.active_shard_id]

    resonance_report = kernel.inspect_resonance(
        (0.21, 0.34, 0.55, 0.89),
        "workspace_controlled_query",
        top_k=min(4, len(kernel.state.concepts)),
    )
    resonance_event = kernel.commit_resonance(
        resonance_report,
        evidence_refs=contradiction.evidence_refs,
        max_candidates=2,
        resource_request=0.10,
    )
    resonance_attention = kernel.state.attention_candidates[
        resonance_event.attention_candidate_ids[0]
    ]

    affirmative_claim_id = next(
        claim.claim_id
        for claim in kernel.state.claims.values()
        if claim.claim_key == contradiction.claim_key
        and claim.polarity == ClaimPolarity.AFFIRMED
    )
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation="inspect_door",
        action_class="reversible_visual_inspection",
        description="Inspect the contradicted door state without applying force.",
        target_claim_id=affirmative_claim_id,
        evidence_refs=contradiction.evidence_refs,
        attention_candidate_ids=resonance_event.attention_candidate_ids,
        resonance_event_ids=(resonance_event.resonance_event_id,),
        requested_resource=0.14,
        relevance=1.0,
        urgency=0.65,
        novelty=0.25,
        predicted_information_gain=1.0,
        harm_risk=0.02,
        reversibility=1.0,
        safe_alternatives=("remain_stationary",),
    )
    decision = governance.commit(kernel, governance.inspect(kernel, proposal))
    if "inspect_door" not in decision.report.authorized_operations:
        raise RuntimeError("Controlled safe-inspection proposal was not authorized.")
    decision_evidence = tuple(
        sorted(set(decision.evidence_refs) | set(decision.report.proposal.evidence_refs))
    )

    semantic_before = {
        "concepts": kernel.state.concepts.copy(),
        "relations": kernel.state.relations.copy(),
        "claims": kernel.state.claims.copy(),
        "contradictions": kernel.state.contradictions.copy(),
    }

    binding = (
        contradiction_id,
        decision.decision_event_id,
        object_candidate.candidate_id,
    )
    cycle_one_inputs = (
        source_candidate(
            kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
            source_ref=current_evidence,
            label="current closed-door observation",
            evidence_refs=(current_evidence,),
            resource=0.18,
            signals=WorkspaceSignals(
                evidence_grounding=1.0,
                relevance=1.0,
                prediction_error=0.4,
                contradiction_pressure=1.0,
                action_value=0.3,
                ethical_salience=0.2,
                novelty=0.7,
            ),
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.GOVERNANCE_CONSTRAINT,
            source_ref=decision.decision_event_id,
            label="Council constraints for safe inspection",
            evidence_refs=decision_evidence,
            resource=0.13,
            signals=WorkspaceSignals(
                evidence_grounding=0.9,
                relevance=1.0,
                contradiction_pressure=1.0,
                action_value=0.7,
                ethical_salience=1.0,
                novelty=0.4,
            ),
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.AUTHORIZED_ACTION,
            source_ref=decision.decision_event_id,
            label="authorized inspect-door action",
            evidence_refs=decision_evidence,
            resource=0.14,
            signals=WorkspaceSignals(
                evidence_grounding=0.9,
                relevance=1.0,
                prediction_error=0.2,
                action_value=1.0,
                ethical_salience=0.7,
                novelty=0.3,
            ),
            operation="inspect_door",
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.CONTRADICTION,
            source_ref=contradiction_id,
            label="door-state contradiction",
            evidence_refs=contradiction.evidence_refs,
            resource=0.16,
            signals=WorkspaceSignals(
                evidence_grounding=0.9,
                relevance=1.0,
                prediction_error=0.8,
                contradiction_pressure=1.0,
                ethical_salience=0.6,
                novelty=0.4,
            ),
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.PROTO_OBJECT,
            source_ref=object_candidate.candidate_id,
            label="earned proto-object in the current scene",
            evidence_refs=object_candidate.evidence_refs[:3],
            resource=0.14,
            signals=WorkspaceSignals(
                evidence_grounding=0.85,
                relevance=0.8,
                prediction_error=0.3,
                action_value=0.4,
                novelty=0.8,
            ),
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.SHARD_CONTEXT,
            source_ref=active_shard.shard_id,
            label="active canonical shard context",
            evidence_refs=object_candidate.evidence_refs[:3],
            resource=0.10,
            signals=WorkspaceSignals(
                evidence_grounding=0.7,
                relevance=0.7,
                action_value=0.3,
                novelty=0.2,
            ),
            binding_refs=binding,
        ),
        source_candidate(
            kind=WorkspaceSourceKind.RESONANCE,
            source_ref=resonance_attention.candidate_id,
            label="ECWF possibility candidate",
            evidence_refs=resonance_attention.evidence_refs,
            resource=0.12,
            signals=WorkspaceSignals(
                evidence_grounding=0.2,
                relevance=0.9,
                novelty=0.7,
                resonance=min(1.0, resonance_attention.priority),
            ),
        ),
    )
    first_cycle = workspace.run_cycle(kernel, cycle_one_inputs)
    current_item_id = next(
        item.item_id
        for item in kernel.state.workspace_items.values()
        if item.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE
    )

    inspection_outcome = native_evidence(
        kernel,
        key="workspace-inspection-outcome",
        features=(0.0, 1.0, 0.0),
        kind=EvidenceKind.OUTCOME,
        modality="controlled_visual_outcome",
    )
    writeback = workspace.writeback(
        kernel,
        item_id=current_item_id,
        disposition=WorkspaceWritebackDisposition.RESOLVE,
        evidence_refs=(inspection_outcome,),
        reason="The immediate sensory focus was resolved by the inspection outcome.",
    )
    second_cycle = workspace.run_cycle(
        kernel,
        (
            source_candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=inspection_outcome,
                label="current inspection outcome",
                evidence_refs=(inspection_outcome,),
                resource=0.18,
                signals=WorkspaceSignals(
                    evidence_grounding=1.0,
                    relevance=1.0,
                    prediction_error=0.15,
                    contradiction_pressure=0.8,
                    action_value=0.5,
                    ethical_salience=0.4,
                    novelty=0.8,
                ),
                binding_refs=binding,
            ),
        ),
    )

    semantic_after = {
        "concepts": kernel.state.concepts.copy(),
        "relations": kernel.state.relations.copy(),
        "claims": kernel.state.claims.copy(),
        "contradictions": kernel.state.contradictions.copy(),
    }
    semantic_unchanged_by_workspace = semantic_before == semantic_after

    checkpoint_sha256 = save_checkpoint(CHECKPOINT_PATH, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(CHECKPOINT_PATH))
    exact_reload = restored.snapshot() == kernel.snapshot()

    first_assessments = [
        {
            "source_kind": item.candidate.source_kind.value,
            "label": item.candidate.label,
            "disposition": item.disposition.value,
            "effective_score": item.effective_score,
            "allocated_resource": item.allocated_resource,
            "rejection_codes": list(item.rejection_codes),
        }
        for item in first_cycle.report.assessments
    ]
    second_active = [
        {
            "item_id": item.item_id,
            "source_kind": item.source_kind.value,
            "label": item.label,
            "resource": item.allocated_resource,
            "effective_score": item.effective_score,
            "expires_cycle": item.expires_cycle,
        }
        for item in sorted(kernel.state.workspace_items.values(), key=lambda value: value.item_id)
    ]
    reports = {
        "cycle_one": first_cycle.report.model_dump(mode="json"),
        "cycle_two": second_cycle.report.model_dump(mode="json"),
        "writeback": writeback.model_dump(mode="json"),
    }
    REPORTS_PATH.write_text(json.dumps(reports, indent=2, sort_keys=True), encoding="utf-8")

    summary = {
        "milestone": 9,
        "title": "Bounded Active Developmental Workspace",
        "base_checkpoint": str(BASE_CHECKPOINT),
        "llm_in_loop": False,
        "pretrained_attention_policy_in_loop": False,
        "metrics": kernel.metrics(),
        "workspace_policy": kernel.state.workspace_policy.model_dump(mode="json"),
        "integrated_sources_presented": [
            item.value for item in WorkspaceSourceKind
        ],
        "cycle_one": {
            "candidate_count": len(first_cycle.report.assessments),
            "active_count": len(first_cycle.event.active_item_ids),
            "broadcast_count": len(first_cycle.event.broadcast_item_ids),
            "allocated_resource": first_cycle.report.total_allocated_resource,
            "resource_budget": first_cycle.report.resource_budget,
            "assessments": first_assessments,
            "resonance_admitted": any(
                item.candidate.source_kind == WorkspaceSourceKind.RESONANCE
                and item.disposition.value == "admit"
                for item in first_cycle.report.assessments
            ),
            "current_evidence_admitted": any(
                item.candidate.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE
                and item.disposition.value == "admit"
                for item in first_cycle.report.assessments
            ),
        },
        "writeback": {
            "disposition": writeback.disposition.value,
            "resolved_item_id": writeback.item_snapshot.item_id,
            "outcome_evidence_refs": list(writeback.evidence_refs),
        },
        "cycle_two": {
            "active_count": len(second_cycle.event.active_item_ids),
            "broadcast_count": len(second_cycle.event.broadcast_item_ids),
            "allocated_resource": second_cycle.report.total_allocated_resource,
            "active_items": second_active,
        },
        "integrated_state": {
            "contradiction_id": contradiction_id,
            "proto_object_candidate_id": object_candidate.candidate_id,
            "active_shard_id": active_shard.shard_id,
            "resonance_event_id": resonance_event.resonance_event_id,
            "council_decision_event_id": decision.decision_event_id,
            "authorized_operation": "inspect_door",
        },
        "semantic_truth_unchanged_by_workspace": semantic_unchanged_by_workspace,
        "exact_checkpoint_reload": exact_reload,
        "checkpoint": str(CHECKPOINT_PATH),
        "checkpoint_sha256": checkpoint_sha256,
        "reports": str(REPORTS_PATH),
        "important_boundaries": [
            "The workspace coordinates existing records and cannot create concepts, relations, claims, or evidence.",
            "The finite-resource score is an explicit experimental scheduling policy, not a claim of human attention.",
            "The demonstration uses controlled numerical and textual evidence rather than live device streams.",
            "Workspace broadcast means cross-subsystem availability inside this architecture; it is not evidence of consciousness.",
        ],
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
