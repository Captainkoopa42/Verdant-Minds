from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    GovernanceProposalKind,
    WorkspaceAdmissionReport,
    WorkspaceCandidateInput,
    WorkspaceIntegrityError,
    WorkspacePolicy,
    WorkspaceSignals,
    WorkspaceSourceKind,
    WorkspaceStaleError,
    WorkspaceWritebackDisposition,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_claims import ClaimLearningPipeline
from verdant_workspace import VerdantWorkspacePipeline


def add_evidence(
    kernel: VerdantKernel,
    *,
    key: str,
    kind: EvidenceKind | None = None,
    values: tuple[float, ...] = (0.2, 0.4),
) -> str:
    payload = f"{key}:{kind}:{values}".encode()
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"workspace-test:{key}",
            modality="controlled",
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            feature_vector=values,
            semantic_evidence_kind=kind,
            semantic_evidence_details={"controlled_test": True},
        )
    )
    return (
        result.additional_evidence_ids[0]
        if kind is not None
        else result.observation_evidence_id
    )


def candidate(
    *,
    kind: WorkspaceSourceKind,
    source_ref: str,
    evidence_refs: tuple[str, ...],
    label: str,
    resource: float = 0.2,
    persistence: int = 1,
    operation: str | None = None,
    evidence_grounding: float = 0.8,
    relevance: float = 0.8,
    contradiction: float = 0.0,
    action: float = 0.0,
    ethics: float = 0.0,
    resonance: float = 0.0,
) -> WorkspaceCandidateInput:
    return WorkspaceCandidateInput(
        source_kind=kind,
        source_ref=source_ref,
        label=label,
        evidence_refs=tuple(sorted(evidence_refs)),
        resource_request=resource,
        persistence_cycles=persistence,
        signals=WorkspaceSignals(
            evidence_grounding=evidence_grounding,
            relevance=relevance,
            prediction_error=0.1,
            contradiction_pressure=contradiction,
            action_value=action,
            ethical_salience=ethics,
            novelty=0.3,
            resonance=resonance,
        ),
        operation=operation,
    )


def approved_decision(kernel: VerdantKernel, evidence_ref: str, operation: str = "inspect"):
    governance = VerdantGovernancePipeline()
    proposal = governance.propose(
        kernel,
        proposal_kind=GovernanceProposalKind.INVESTIGATE,
        operation=operation,
        action_class="controlled_inspection",
        description="Perform a reversible controlled inspection.",
        evidence_refs=(evidence_ref,),
        relevance=1.0,
        urgency=0.4,
        novelty=0.2,
        predicted_information_gain=1.0,
        harm_risk=0.01,
        reversibility=1.0,
    )
    report = governance.inspect(kernel, proposal)
    return governance.commit(kernel, report)


def test_workspace_enforces_resource_and_slot_bounds() -> None:
    kernel = VerdantKernel(seed=901, state_dim=32, run_label="workspace-bounds")
    kernel.state.workspace_policy = WorkspacePolicy(
        resource_budget=0.55,
        max_active_items=2,
        current_evidence_reserve=0.20,
    )
    refs = [add_evidence(kernel, key=f"e-{index}") for index in range(4)]
    inputs = [
        candidate(
            kind=WorkspaceSourceKind.CURRENT_EVIDENCE if index == 0 else WorkspaceSourceKind.RECALLED_EVIDENCE,
            source_ref=ref,
            evidence_refs=(ref,),
            label=f"item-{index}",
            resource=0.25,
        )
        for index, ref in enumerate(refs)
    ]
    event = VerdantWorkspacePipeline().run_cycle(kernel, inputs).event
    assert len(event.active_item_ids) == 2
    assert sum(item.allocated_resource for item in kernel.state.workspace_items.values()) <= 0.55
    assert len(event.suppressed_candidate_ids) == 2


def test_current_evidence_survives_high_resonance_pressure() -> None:
    kernel = VerdantKernel(seed=902, state_dim=32, run_label="workspace-grounding")
    current = add_evidence(kernel, key="current")
    resonance_evidence = add_evidence(kernel, key="res-evidence")
    attention_ids = []
    for index in range(4):
        item = kernel.set_attention_candidate(
            source_ref=f"resonance:{index}",
            priority=1.0,
            resource_request=0.2,
            reason=f"high resonance {index}",
            evidence_refs=(resonance_evidence,),
        )
        attention_ids.append(item.candidate_id)
    inputs = [
        candidate(
            kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
            source_ref=current,
            evidence_refs=(current,),
            label="current sensory evidence",
            resource=0.3,
            evidence_grounding=1.0,
            relevance=0.65,
        )
    ] + [
        candidate(
            kind=WorkspaceSourceKind.RESONANCE,
            source_ref=attention_id,
            evidence_refs=(resonance_evidence,),
            label=f"resonance {index}",
            resource=0.2,
            evidence_grounding=0.2,
            relevance=1.0,
            resonance=1.0,
        )
        for index, attention_id in enumerate(attention_ids)
    ]
    result = VerdantWorkspacePipeline().run_cycle(kernel, inputs)
    kinds = {item.source_kind for item in kernel.state.workspace_items.values()}
    assert WorkspaceSourceKind.CURRENT_EVIDENCE in kinds
    resonance_count = sum(
        item.source_kind == WorkspaceSourceKind.RESONANCE
        for item in kernel.state.workspace_items.values()
    )
    assert resonance_count <= 1
    assert any(
        "resonance_budget_cap" in assessment.rejection_codes
        for assessment in result.report.assessments
    )


def test_authorized_action_requires_the_exact_council_decision() -> None:
    kernel = VerdantKernel(seed=903, state_dim=32, run_label="workspace-action")
    evidence = add_evidence(kernel, key="door")
    decision = approved_decision(kernel, evidence, operation="inspect_door")
    workspace = VerdantWorkspacePipeline()
    valid = candidate(
        kind=WorkspaceSourceKind.AUTHORIZED_ACTION,
        source_ref=decision.decision_event_id,
        evidence_refs=(evidence,),
        label="inspect the door",
        operation="inspect_door",
        action=1.0,
        resource=0.25,
    )
    workspace.run_cycle(kernel, (valid,))
    assert any(item.operation == "inspect_door" for item in kernel.state.workspace_items.values())

    invalid = candidate(
        kind=WorkspaceSourceKind.AUTHORIZED_ACTION,
        source_ref=decision.decision_event_id,
        evidence_refs=(evidence,),
        label="force the door",
        operation="force_door",
        action=1.0,
    )
    with pytest.raises(WorkspaceIntegrityError):
        workspace.inspect(kernel, (invalid,))


def test_workspace_cycle_does_not_create_semantic_truth() -> None:
    kernel = VerdantKernel(seed=904, state_dim=32, run_label="workspace-semantic-boundary")
    evidence = add_evidence(kernel, key="present")
    before = {
        "evidence": dict(kernel.state.evidence),
        "concepts": dict(kernel.state.concepts),
        "relations": dict(kernel.state.relations),
        "claims": dict(kernel.state.claims),
        "contradictions": dict(kernel.state.contradictions),
    }
    VerdantWorkspacePipeline().run_cycle(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="present evidence",
            ),
        ),
    )
    assert kernel.state.evidence == before["evidence"]
    assert kernel.state.concepts == before["concepts"]
    assert kernel.state.relations == before["relations"]
    assert kernel.state.claims == before["claims"]
    assert kernel.state.contradictions == before["contradictions"]


def test_workspace_persistence_decays_and_expires() -> None:
    kernel = VerdantKernel(seed=905, state_dim=32, run_label="workspace-persistence")
    evidence = add_evidence(kernel, key="persistent")
    workspace = VerdantWorkspacePipeline()
    first = workspace.run_cycle(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="persistent present",
                persistence=2,
            ),
        ),
    )
    item_id = first.event.active_item_ids[0]
    first_score = kernel.state.workspace_items[item_id].effective_score
    second = workspace.run_cycle(kernel, ())
    assert item_id in second.event.active_item_ids
    assert kernel.state.workspace_items[item_id].effective_score < first_score
    third = workspace.run_cycle(kernel, ())
    assert item_id not in third.event.active_item_ids
    assert item_id in third.event.evicted_item_ids


def test_workspace_report_becomes_stale_after_relevant_state_change() -> None:
    kernel = VerdantKernel(seed=906, state_dim=32, run_label="workspace-stale")
    evidence = add_evidence(kernel, key="first")
    workspace = VerdantWorkspacePipeline()
    report = workspace.inspect(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="first",
            ),
        ),
    )
    add_evidence(kernel, key="later")
    with pytest.raises(WorkspaceStaleError):
        workspace.commit(kernel, report)


def test_tampered_workspace_report_is_rejected() -> None:
    kernel = VerdantKernel(seed=907, state_dim=32, run_label="workspace-tamper")
    evidence = add_evidence(kernel, key="tamper")
    workspace = VerdantWorkspacePipeline()
    report = workspace.inspect(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="tamper target",
            ),
        ),
    )
    tampered = report.model_copy(
        update={"total_allocated_resource": report.total_allocated_resource + 0.1}
    )
    with pytest.raises(WorkspaceStaleError):
        workspace.commit(kernel, tampered)


def test_workspace_writeback_resolves_focus_without_erasing_evidence() -> None:
    kernel = VerdantKernel(seed=908, state_dim=32, run_label="workspace-writeback")
    evidence = add_evidence(kernel, key="question")
    outcome = add_evidence(kernel, key="answer", kind=EvidenceKind.OUTCOME)
    workspace = VerdantWorkspacePipeline()
    event = workspace.run_cycle(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="unresolved question",
                persistence=3,
            ),
        ),
    ).event
    item_id = event.active_item_ids[0]
    before_evidence = dict(kernel.state.evidence)
    writeback = workspace.writeback(
        kernel,
        item_id=item_id,
        disposition=WorkspaceWritebackDisposition.RESOLVE,
        evidence_refs=(outcome,),
        reason="The controlled outcome resolved the immediate focus.",
    )
    assert writeback.item_snapshot.item_id == item_id
    assert item_id not in kernel.state.workspace_items
    assert kernel.state.evidence == before_evidence


def test_contradiction_can_enter_shared_present_with_its_full_ledger() -> None:
    kernel = VerdantKernel(seed=909, state_dim=32, run_label="workspace-contradiction")
    claims = ClaimLearningPipeline()
    positive = claims.record_claim(
        kernel,
        event_key="bright-positive",
        native_description="Controlled observation: indicator is bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    negative = claims.record_claim(
        kernel,
        event_key="bright-negative",
        native_description="Controlled observation: indicator is not bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    contradiction_id = positive.kernel_result.contradiction_ids[0] if positive.kernel_result.contradiction_ids else negative.kernel_result.contradiction_ids[0]
    contradiction = kernel.state.contradictions[contradiction_id]
    VerdantWorkspacePipeline().run_cycle(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CONTRADICTION,
                source_ref=contradiction_id,
                evidence_refs=contradiction.evidence_refs,
                label="indicator conflict",
                contradiction=1.0,
                relevance=1.0,
            ),
        ),
    )
    item = next(iter(kernel.state.workspace_items.values()))
    assert item.source_ref == contradiction_id
    assert item.evidence_refs == contradiction.evidence_refs


def test_workspace_checkpoint_round_trip(tmp_path: Path) -> None:
    kernel = VerdantKernel(seed=910, state_dim=32, run_label="workspace-checkpoint")
    evidence = add_evidence(kernel, key="checkpoint")
    VerdantWorkspacePipeline().run_cycle(
        kernel,
        (
            candidate(
                kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                source_ref=evidence,
                evidence_refs=(evidence,),
                label="checkpoint focus",
                persistence=3,
            ),
        ),
    )
    path = tmp_path / "workspace.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()


def test_workspace_sequence_is_deterministic() -> None:
    def build() -> VerdantKernel:
        kernel = VerdantKernel(seed=911, state_dim=32, run_label="workspace-replay")
        evidence = add_evidence(kernel, key="same")
        VerdantWorkspacePipeline().run_cycle(
            kernel,
            (
                candidate(
                    kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
                    source_ref=evidence,
                    evidence_refs=(evidence,),
                    label="same focus",
                    persistence=2,
                ),
            ),
        )
        VerdantWorkspacePipeline().run_cycle(kernel, ())
        return kernel

    left = build()
    right = build()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()


def test_workspace_rejects_evidence_outside_resonance_lineage() -> None:
    kernel = VerdantKernel(seed=912, state_dim=32, run_label="workspace-lineage")
    valid_ref = add_evidence(kernel, key="valid")
    foreign_ref = add_evidence(kernel, key="foreign")
    attention = kernel.set_attention_candidate(
        source_ref="resonance-source",
        priority=0.9,
        resource_request=0.1,
        reason="controlled resonance",
        evidence_refs=(valid_ref,),
    )
    bad = candidate(
        kind=WorkspaceSourceKind.RESONANCE,
        source_ref=attention.candidate_id,
        evidence_refs=(foreign_ref,),
        label="poisoned resonance",
        resonance=0.9,
    )
    with pytest.raises(WorkspaceIntegrityError):
        VerdantWorkspacePipeline().inspect(kernel, (bad,))
