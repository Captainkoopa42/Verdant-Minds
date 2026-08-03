from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from verdant_kernel import (
    EvidenceKind,
    WorkspaceAdmissionReport,
    WorkspaceCandidateAssessment,
    WorkspaceCandidateInput,
    WorkspaceCycleEvent,
    WorkspaceDisposition,
    WorkspaceIntegrityError,
    WorkspaceScoreComponents,
    WorkspaceSourceKind,
    WorkspaceStaleError,
    WorkspaceWritebackDisposition,
    WorkspaceWritebackEvent,
    VerdantKernel,
)
from verdant_kernel.models import stable_id


@dataclass(frozen=True)
class WorkspaceCycleResult:
    report: WorkspaceAdmissionReport
    event: WorkspaceCycleEvent


class VerdantWorkspacePipeline:
    """Bounded shared present for the independent Verdant rebuild.

    The workspace ranks and binds already-existing evidence, possibilities,
    contradictions, objects, shard context, and Council decisions. It
    cannot create semantic truth. Admission is a finite-resource scheduling
    decision whose full scoring and suppression path remains inspectable.
    """

    _SOURCE_ORDER = {
        WorkspaceSourceKind.CURRENT_EVIDENCE: 0,
        WorkspaceSourceKind.TEMPORAL_EVENT: 1,
        WorkspaceSourceKind.GOVERNANCE_CONSTRAINT: 2,
        WorkspaceSourceKind.AUTHORIZED_ACTION: 3,
        WorkspaceSourceKind.CONTRADICTION: 4,
        WorkspaceSourceKind.PROTO_OBJECT: 5,
        WorkspaceSourceKind.EARNED_STRUCTURE: 6,
        WorkspaceSourceKind.SHARD_CONTEXT: 7,
        WorkspaceSourceKind.LOCAL_ASSOCIATION: 8,
        WorkspaceSourceKind.RECALLED_EVIDENCE: 9,
        WorkspaceSourceKind.RESONANCE: 10,
    }

    @staticmethod
    def _source_key(candidate: WorkspaceCandidateInput) -> tuple[str, str, str | None]:
        return (
            candidate.source_kind.value,
            candidate.source_ref,
            candidate.operation,
        )

    @staticmethod
    def _decision(kernel: VerdantKernel, decision_event_id: str):
        return next(
            (
                item
                for item in kernel.state.council_decisions
                if item.decision_event_id == decision_event_id
            ),
            None,
        )

    def _validate_source(
        self,
        kernel: VerdantKernel,
        candidate: WorkspaceCandidateInput,
    ) -> None:
        missing = [
            evidence_ref
            for evidence_ref in candidate.evidence_refs
            if evidence_ref not in kernel.state.evidence
        ]
        if missing:
            raise WorkspaceIntegrityError(
                "Workspace candidate references missing evidence: "
                + ", ".join(sorted(missing))
            )
        kind = candidate.source_kind
        source_ref = candidate.source_ref
        evidence_set = set(candidate.evidence_refs)

        if candidate.persistence_cycles > kernel.state.workspace_policy.maximum_persistence_cycles:
            raise WorkspaceIntegrityError(
                "Workspace persistence request exceeds the configured maximum."
            )
        if candidate.resource_request > kernel.state.workspace_policy.resource_budget:
            raise WorkspaceIntegrityError(
                "One workspace candidate cannot request more than the whole budget."
            )

        if kind in {
            WorkspaceSourceKind.CURRENT_EVIDENCE,
            WorkspaceSourceKind.RECALLED_EVIDENCE,
        }:
            if source_ref not in kernel.state.evidence:
                raise WorkspaceIntegrityError("Workspace evidence source is missing.")
            if source_ref not in evidence_set:
                raise WorkspaceIntegrityError(
                    "Workspace evidence source must remain in its evidence lineage."
                )
            return

        if kind == WorkspaceSourceKind.TEMPORAL_EVENT:
            event = kernel.state.temporal_events.get(source_ref)
            if event is None:
                raise WorkspaceIntegrityError("Workspace temporal event source is missing.")
            if not evidence_set.issubset(set(event.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace temporal event evidence is outside its native lineage."
                )
            return

        if kind == WorkspaceSourceKind.RESONANCE:
            attention = kernel.state.attention_candidates.get(source_ref)
            if attention is None:
                raise WorkspaceIntegrityError("Workspace resonance source is missing.")
            if not evidence_set.issubset(set(attention.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace resonance candidate added evidence outside its source."
                )
            if candidate.signals.resonance > min(1.0, attention.priority) + 1e-9:
                raise WorkspaceIntegrityError(
                    "Workspace resonance signal exceeds the persisted source priority."
                )
            return

        if kind == WorkspaceSourceKind.LOCAL_ASSOCIATION:
            association = kernel.state.plasticity_associations.get(source_ref)
            if association is None:
                raise WorkspaceIntegrityError("Workspace local-association source is missing.")
            if not evidence_set.issubset(set(association.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace local-association evidence is outside its learned lineage."
                )
            if candidate.signals.resonance > association.strength + 1e-9:
                raise WorkspaceIntegrityError(
                    "Workspace local-association signal exceeds persisted strength."
                )
            if any(ref not in association.concept_ids for ref in candidate.binding_refs):
                raise WorkspaceIntegrityError(
                    "Workspace local-association binding escapes its endpoints."
                )
            return

        if kind == WorkspaceSourceKind.CONTRADICTION:
            contradiction = kernel.state.contradictions.get(source_ref)
            if contradiction is None:
                raise WorkspaceIntegrityError("Workspace contradiction source is missing.")
            if not evidence_set.issubset(set(contradiction.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace contradiction evidence is outside its ledger."
                )
            return

        if kind == WorkspaceSourceKind.PROTO_OBJECT:
            object_candidate = kernel.state.object_candidates.get(source_ref)
            if object_candidate is None:
                raise WorkspaceIntegrityError("Workspace proto-object source is missing.")
            if not evidence_set.issubset(set(object_candidate.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace proto-object evidence is outside its observation lineage."
                )
            return

        if kind == WorkspaceSourceKind.EARNED_STRUCTURE:
            structure = kernel.state.structures.get(source_ref)
            if structure is None:
                raise WorkspaceIntegrityError("Workspace earned-structure source is missing.")
            if not kernel.structure_is_available(source_ref):
                raise WorkspaceIntegrityError("Workspace cannot admit an ablated structure.")
            if not evidence_set.issubset(set(structure.evidence_refs)):
                raise WorkspaceIntegrityError(
                    "Workspace earned-structure evidence is outside its promotion lineage."
                )
            if any(ref not in structure.member_concept_ids for ref in candidate.binding_refs):
                raise WorkspaceIntegrityError(
                    "Workspace earned-structure binding escapes its learned members."
                )
            return

        if kind == WorkspaceSourceKind.SHARD_CONTEXT:
            shard = kernel.state.shards.get(source_ref)
            if shard is None:
                raise WorkspaceIntegrityError("Workspace shard source is missing.")
            if source_ref != kernel.state.active_shard_id:
                raise WorkspaceIntegrityError(
                    "Workspace shard context must name the currently active shard."
                )
            return


        if kind in {
            WorkspaceSourceKind.GOVERNANCE_CONSTRAINT,
            WorkspaceSourceKind.AUTHORIZED_ACTION,
        }:
            decision = self._decision(kernel, source_ref)
            if decision is None:
                raise WorkspaceIntegrityError("Workspace Council source is missing.")
            allowed_evidence = set(decision.evidence_refs) | set(
                decision.report.proposal.evidence_refs
            )
            if not evidence_set.issubset(allowed_evidence):
                raise WorkspaceIntegrityError(
                    "Workspace Council candidate added evidence outside the decision."
                )
            if kind == WorkspaceSourceKind.AUTHORIZED_ACTION:
                assert candidate.operation is not None
                if candidate.operation not in decision.report.authorized_operations:
                    raise WorkspaceIntegrityError(
                        "Workspace action was not authorized by the referenced Council decision."
                    )
            return

        raise WorkspaceIntegrityError(f"Unsupported workspace source kind: {kind!r}.")

    @staticmethod
    def _weighted_score(kernel: VerdantKernel, candidate: WorkspaceCandidateInput):
        policy = kernel.state.workspace_policy
        signals = candidate.signals
        components = WorkspaceScoreComponents(
            evidence=signals.evidence_grounding * policy.evidence_weight,
            relevance=signals.relevance * policy.relevance_weight,
            prediction_error=signals.prediction_error * policy.prediction_error_weight,
            contradiction=signals.contradiction_pressure * policy.contradiction_weight,
            action=signals.action_value * policy.action_weight,
            ethics=signals.ethical_salience * policy.ethics_weight,
            novelty=signals.novelty * policy.novelty_weight,
            resonance=signals.resonance * policy.resonance_weight,
            stickiness=0.0,
            resource_penalty=(
                candidate.resource_request / policy.resource_budget
            )
            * policy.resource_penalty_weight,
        )
        total_weight = (
            policy.evidence_weight
            + policy.relevance_weight
            + policy.prediction_error_weight
            + policy.contradiction_weight
            + policy.action_weight
            + policy.ethics_weight
            + policy.novelty_weight
            + policy.resonance_weight
        )
        positive = (
            components.evidence
            + components.relevance
            + components.prediction_error
            + components.contradiction
            + components.action
            + components.ethics
            + components.novelty
            + components.resonance
        )
        raw_score = max(0.0, min(1.0, positive / total_weight))
        return raw_score, components

    def _carry_candidates(
        self,
        kernel: VerdantKernel,
        submitted_keys: set[tuple[str, str, str | None]],
    ) -> list[tuple[WorkspaceCandidateInput, str]]:
        policy = kernel.state.workspace_policy
        result: list[tuple[WorkspaceCandidateInput, str]] = []
        for item in sorted(kernel.state.workspace_items.values(), key=lambda value: value.item_id):
            key = (item.source_kind.value, item.source_ref, item.operation)
            if key in submitted_keys:
                continue
            if kernel.state.cycle >= item.expires_cycle:
                continue
            signals = item.signals.model_copy(
                update={
                    field: getattr(item.signals, field) * policy.carry_decay
                    for field in type(item.signals).model_fields
                }
            )
            remaining = max(1, item.expires_cycle - kernel.state.cycle)
            candidate = WorkspaceCandidateInput(
                source_kind=item.source_kind,
                source_ref=item.source_ref,
                label=item.label,
                evidence_refs=item.evidence_refs,
                resource_request=item.allocated_resource,
                persistence_cycles=remaining,
                signals=signals,
                operation=item.operation,
                binding_refs=item.binding_refs,
                metadata={**item.metadata, "carried_forward": True},
            )
            result.append((candidate, item.item_id))
        return result

    def inspect(
        self,
        kernel: VerdantKernel,
        candidates: Sequence[WorkspaceCandidateInput],
    ) -> WorkspaceAdmissionReport:
        policy = kernel.state.workspace_policy
        submitted: list[tuple[WorkspaceCandidateInput, str | None]] = []
        submitted_keys: set[tuple[str, str, str | None]] = set()
        for candidate in candidates:
            candidate = WorkspaceCandidateInput.model_validate(
                candidate.model_dump(mode="json")
            )
            self._validate_source(kernel, candidate)
            key = self._source_key(candidate)
            if key in submitted_keys:
                raise WorkspaceIntegrityError(
                    "One workspace cycle cannot submit the same source twice."
                )
            submitted_keys.add(key)
            prior = next(
                (
                    item.item_id
                    for item in kernel.state.workspace_items.values()
                    if (item.source_kind.value, item.source_ref, item.operation) == key
                ),
                None,
            )
            submitted.append((candidate, prior))
        submitted.extend(self._carry_candidates(kernel, submitted_keys))

        scored: list[dict[str, object]] = []
        for candidate, prior_item_id in submitted:
            self._validate_source(kernel, candidate)
            raw_score, components = self._weighted_score(kernel, candidate)
            stickiness = policy.stickiness_weight if prior_item_id is not None else 0.0
            components = components.model_copy(update={"stickiness": stickiness})
            effective = max(
                0.0,
                min(
                    1.0,
                    raw_score + stickiness - components.resource_penalty,
                ),
            )
            candidate_id = stable_id(
                "workspace_candidate",
                kernel.state.identity.kernel_id,
                kernel.state.cycle,
                candidate.model_dump(mode="json"),
                prior_item_id,
                policy.revision,
            )
            scored.append(
                {
                    "candidate": candidate,
                    "candidate_id": candidate_id,
                    "prior_item_id": prior_item_id,
                    "raw_score": raw_score,
                    "effective_score": effective,
                    "components": components,
                }
            )

        def selection_key(row: dict[str, object]):
            candidate = row["candidate"]
            assert isinstance(candidate, WorkspaceCandidateInput)
            effective = float(row["effective_score"])
            efficiency = effective / max(candidate.resource_request, 1e-12)
            return (
                self._SOURCE_ORDER[candidate.source_kind],
                -effective,
                -efficiency,
                str(row["candidate_id"]),
            )

        admitted: set[str] = set()
        rejection: dict[str, list[str]] = {}
        used_resource = 0.0
        resonance_resource = 0.0
        used_slots = 0

        for row in sorted(scored, key=selection_key):
            candidate = row["candidate"]
            assert isinstance(candidate, WorkspaceCandidateInput)
            candidate_id = str(row["candidate_id"])
            effective = float(row["effective_score"])
            reasons: list[str] = []
            if effective < policy.minimum_admission_score:
                reasons.append("below_admission_threshold")
            if used_slots >= policy.max_active_items:
                reasons.append("slot_budget_exhausted")
            if used_resource + candidate.resource_request > policy.resource_budget + 1e-9:
                reasons.append("resource_budget_exhausted")
            if candidate.source_kind == WorkspaceSourceKind.RESONANCE:
                max_resonance = policy.resource_budget * policy.resonance_budget_fraction
                if resonance_resource + candidate.resource_request > max_resonance + 1e-9:
                    reasons.append("resonance_budget_cap")
            if not reasons:
                admitted.add(candidate_id)
                used_slots += 1
                used_resource += candidate.resource_request
                if candidate.source_kind == WorkspaceSourceKind.RESONANCE:
                    resonance_resource += candidate.resource_request
            rejection[candidate_id] = sorted(set(reasons))

        # If current sensory evidence was supplied, require at least one current item
        # to survive whenever its request fits the total budget and it clears threshold.
        viable_current = [
            row
            for row in scored
            if isinstance(row["candidate"], WorkspaceCandidateInput)
            and row["candidate"].source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE
            and float(row["effective_score"]) >= policy.minimum_admission_score
            and row["candidate"].resource_request <= policy.resource_budget
        ]
        if viable_current and not any(str(row["candidate_id"]) in admitted for row in viable_current):
            raise WorkspaceIntegrityError(
                "Workspace selection lost all viable current sensory evidence."
            )

        ranked_rows = sorted(
            scored,
            key=lambda row: (
                -float(row["effective_score"]),
                self._SOURCE_ORDER[row["candidate"].source_kind],
                str(row["candidate_id"]),
            ),
        )
        assessments: list[WorkspaceCandidateAssessment] = []
        for rank, row in enumerate(ranked_rows, start=1):
            candidate = row["candidate"]
            assert isinstance(candidate, WorkspaceCandidateInput)
            candidate_id = str(row["candidate_id"])
            is_admitted = candidate_id in admitted
            assessments.append(
                WorkspaceCandidateAssessment(
                    rank=rank,
                    candidate_id=candidate_id,
                    candidate=candidate,
                    disposition=(
                        WorkspaceDisposition.ADMIT
                        if is_admitted
                        else WorkspaceDisposition.SUPPRESS
                    ),
                    raw_score=float(row["raw_score"]),
                    effective_score=float(row["effective_score"]),
                    allocated_resource=(candidate.resource_request if is_admitted else 0.0),
                    rejection_codes=tuple(rejection[candidate_id]),
                    components=row["components"],
                    carried_from_item_id=row["prior_item_id"],
                )
            )

        admitted_ids = tuple(sorted(admitted))
        suppressed_ids = tuple(
            sorted(
                item.candidate_id
                for item in assessments
                if item.disposition != WorkspaceDisposition.ADMIT
            )
        )
        retained_prior_ids = {
            item.carried_from_item_id
            for item in assessments
            if item.disposition == WorkspaceDisposition.ADMIT
            and item.carried_from_item_id is not None
        }
        evicted_ids = tuple(
            sorted(set(kernel.state.workspace_items) - retained_prior_ids)
        )
        structural = kernel.workspace_structural_fingerprint()
        operation = "advance_bounded_workspace"
        report_id = stable_id(
            "workspace_admission_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            tuple(item.model_dump(mode="json") for item in assessments),
            admitted_ids,
            suppressed_ids,
            evicted_ids,
            used_resource,
            policy.resource_budget,
            operation,
            policy.revision,
        )
        report = WorkspaceAdmissionReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            assessments=tuple(assessments),
            admitted_candidate_ids=admitted_ids,
            suppressed_candidate_ids=suppressed_ids,
            evicted_item_ids=evicted_ids,
            total_allocated_resource=used_resource,
            resource_budget=policy.resource_budget,
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_workspace_report(report)
        return report

    def commit(
        self,
        kernel: VerdantKernel,
        report: WorkspaceAdmissionReport,
    ) -> WorkspaceCycleEvent:
        try:
            report = WorkspaceAdmissionReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise WorkspaceStaleError("Workspace report is invalid.") from exc
        reproduced = self.inspect(
            kernel,
            tuple(
                item.candidate
                for item in report.assessments
                if item.carried_from_item_id is None
                or not item.candidate.metadata.get("carried_forward", False)
            ),
        )
        if reproduced != report:
            raise WorkspaceStaleError(
                "Workspace report does not reproduce from current state."
            )
        return kernel.commit_workspace_cycle(report)

    def run_cycle(
        self,
        kernel: VerdantKernel,
        candidates: Sequence[WorkspaceCandidateInput],
    ) -> WorkspaceCycleResult:
        report = self.inspect(kernel, candidates)
        event = self.commit(kernel, report)
        return WorkspaceCycleResult(report=report, event=event)

    def writeback(
        self,
        kernel: VerdantKernel,
        *,
        item_id: str,
        disposition: WorkspaceWritebackDisposition,
        evidence_refs: Iterable[str],
        reason: str,
    ) -> WorkspaceWritebackEvent:
        return kernel.commit_workspace_writeback(
            item_id=item_id,
            disposition=disposition,
            evidence_refs=evidence_refs,
            reason=reason,
        )
