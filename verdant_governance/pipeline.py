from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from verdant_kernel import (
    CouncilDecisionEvent,
    CouncilDisposition,
    CouncilProposal,
    CouncilReport,
    GovernanceIntegrityError,
    GovernanceOutcomeRecord,
    GovernanceProposalKind,
    GovernanceStaleError,
    KingAssessment,
    KingName,
    KingRecommendation,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id


@dataclass(frozen=True)
class CouncilInspection:
    proposal: CouncilProposal
    report: CouncilReport


class VerdantGovernancePipeline:
    """
    Pure Milestone 5 governance evaluator.

    The three Kings have separate jurisdictions. Their outputs are combined by
    explicit constitutional rules, never by a weighted average. Resonance can
    affect Forefront priority but is never counted as Data King evidence.
    """

    def propose(
        self,
        kernel: VerdantKernel,
        *,
        proposal_kind: GovernanceProposalKind,
        operation: str,
        action_class: str,
        description: str,
        target_claim_id: str | None = None,
        evidence_refs: Iterable[str] = (),
        attention_candidate_ids: Iterable[str] = (),
        resonance_event_ids: Iterable[str] = (),
        requested_resource: float = 0.10,
        relevance: float = 0.5,
        urgency: float = 0.0,
        novelty: float = 0.0,
        predicted_information_gain: float = 0.0,
        harm_risk: float = 0.0,
        reversibility: float = 1.0,
        consent_required: bool = False,
        consent_present: bool = False,
        boundary_sensitive: bool = False,
        safe_alternatives: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> CouncilProposal:
        evidence = tuple(sorted(set(evidence_refs)))
        attention = tuple(sorted(set(attention_candidate_ids)))
        resonance = tuple(sorted(set(resonance_event_ids)))
        alternatives = tuple(sorted(set(safe_alternatives)))
        state_fingerprint = kernel.semantic_fingerprint()
        governance_fingerprint = kernel.governance_fingerprint()
        payload = dict(
            kernel_id=kernel.state.identity.kernel_id,
            created_cycle=kernel.state.cycle,
            proposal_kind=proposal_kind,
            operation=operation.strip(),
            action_class=action_class.strip(),
            description=description.strip(),
            target_claim_id=target_claim_id,
            evidence_refs=evidence,
            attention_candidate_ids=attention,
            resonance_event_ids=resonance,
            requested_resource=requested_resource,
            relevance=relevance,
            urgency=urgency,
            novelty=novelty,
            predicted_information_gain=predicted_information_gain,
            harm_risk=harm_risk,
            reversibility=reversibility,
            consent_required=consent_required,
            consent_present=consent_present,
            boundary_sensitive=boundary_sensitive,
            safe_alternatives=alternatives,
            metadata=dict(metadata or {}),
            state_fingerprint=state_fingerprint,
            governance_fingerprint=governance_fingerprint,
        )
        proposal_id = stable_id(
            "council_proposal",
            payload["kernel_id"],
            payload["created_cycle"],
            proposal_kind.value,
            payload["operation"],
            payload["action_class"],
            payload["description"],
            target_claim_id,
            evidence,
            attention,
            resonance,
            requested_resource,
            relevance,
            urgency,
            novelty,
            predicted_information_gain,
            harm_risk,
            reversibility,
            consent_required,
            consent_present,
            boundary_sensitive,
            alternatives,
            payload["metadata"],
            state_fingerprint,
            governance_fingerprint,
        )
        proposal = CouncilProposal(proposal_id=proposal_id, **payload)
        # Reuse kernel validation so missing references fail before inspection.
        shell = self._report_shell_for_validation(kernel, proposal)
        kernel.validate_council_report_refs(shell)  # canonical reference gate
        return proposal

    def inspect(self, kernel: VerdantKernel, proposal: CouncilProposal) -> CouncilReport:
        proposal = CouncilProposal.model_validate(proposal.model_dump(mode="json"))
        if proposal.kernel_id != kernel.state.identity.kernel_id:
            raise GovernanceIntegrityError("Council proposal belongs to another kernel.")
        if proposal.state_fingerprint != kernel.semantic_fingerprint():
            raise GovernanceStaleError(
                "Council proposal was created against a different canonical state."
            )
        if proposal.governance_fingerprint != kernel.governance_fingerprint():
            raise GovernanceStaleError(
                "Council proposal was created against a different governance policy."
            )

        enabled = kernel.state.governance.enabled_kings
        assessments: list[KingAssessment] = []
        if enabled[KingName.DATA.value]:
            assessments.append(self._data_king(kernel, proposal))
        if enabled[KingName.FOREFRONT.value]:
            assessments.append(self._forefront_king(kernel, proposal))
        if enabled[KingName.ETHICS.value]:
            assessments.append(self._ethics_king(kernel, proposal))
        assessments.sort(key=lambda item: item.king.value)

        disposition, authorized, blocked, constraints, required, alternatives, reasons = (
            self._council_rule(kernel, proposal, tuple(assessments))
        )
        policy_snapshot = {
            **kernel.state.governance.model_dump(mode="json"),
            "decision_method": "constitutional_rule_order",
            "legacy_weights_used_for_decision": False,
        }
        report_id = stable_id(
            "council_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            kernel.semantic_fingerprint(),
            kernel.governance_fingerprint(),
            proposal.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in assessments),
            disposition.value,
            authorized,
            blocked,
            constraints,
            required,
            alternatives,
            reasons,
            policy_snapshot,
        )
        report = CouncilReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            state_fingerprint=kernel.semantic_fingerprint(),
            governance_fingerprint=kernel.governance_fingerprint(),
            proposal=proposal,
            assessments=tuple(assessments),
            disposition=disposition,
            authorized_operations=authorized,
            blocked_operations=blocked,
            constraints=constraints,
            required_evidence=required,
            safe_alternatives=alternatives,
            rationale_codes=reasons,
            policy_snapshot=policy_snapshot,
        )
        kernel.validate_council_report_refs(report)
        return report

    def commit(self, kernel: VerdantKernel, report: CouncilReport) -> CouncilDecisionEvent:
        try:
            report = CouncilReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise GovernanceIntegrityError(
                "Council report failed its identity or content checksum."
            ) from exc
        reproduced = self.inspect(kernel, report.proposal)
        if reproduced != report:
            raise GovernanceIntegrityError(
                "Council report does not reproduce from the current state and policy."
            )
        return kernel.commit_council_decision(report)

    @staticmethod
    def record_outcome(
        kernel: VerdantKernel,
        *,
        decision_event_id: str,
        evidence_refs: Iterable[str],
        succeeded: bool,
        harm_score: float,
    ) -> GovernanceOutcomeRecord:
        return kernel.record_governance_outcome(
            decision_event_id=decision_event_id,
            evidence_refs=evidence_refs,
            succeeded=succeeded,
            harm_score=harm_score,
        )

    def _data_king(
        self,
        kernel: VerdantKernel,
        proposal: CouncilProposal,
    ) -> KingAssessment:
        evidence_refs = set(proposal.evidence_refs)
        constraints: list[str] = []
        rationale: list[str] = ["resonance_is_not_evidence"]
        details: dict[str, Any] = {
            "resonance_event_count": len(proposal.resonance_event_ids),
            "resonance_used_as_evidence": False,
        }
        recommendation = KingRecommendation.REQUEST_EVIDENCE
        score = 0.0
        confidence = 0.0

        if proposal.target_claim_id is not None:
            target = kernel.state.claims[proposal.target_claim_id]
            evidence_refs.update(entry.evidence_id for entry in target.support_ledger)
            evidence_refs.update(entry.evidence_id for entry in target.refutation_ledger)
            current = kernel.current_belief_by_key(target.claim_key)
            contradiction = next(
                (
                    item
                    for item in kernel.state.contradictions.values()
                    if item.claim_key == target.claim_key
                ),
                None,
            )
            details.update(
                {
                    "target_claim_id": target.claim_id,
                    "target_claim_status": target.status.value,
                    "target_support_score": target.support_score,
                    "target_refutation_score": target.refutation_score,
                    "target_net_score": target.net_score,
                    "current_belief_id": current.claim_id if current else None,
                    "contradiction_id": (
                        contradiction.contradiction_id if contradiction else None
                    ),
                }
            )
            if current is None:
                recommendation = KingRecommendation.REQUEST_EVIDENCE
                score = max(0.0, target.net_score)
                confidence = abs(target.net_score)
                constraints.append("claim_unresolved")
                rationale.append("no_current_belief")
            elif current.claim_id == target.claim_id:
                recommendation = KingRecommendation.SUPPORT
                score = max(0.0, current.net_score)
                confidence = max(current.support_score, abs(current.net_score))
                rationale.append("target_matches_current_belief")
            else:
                score = 0.0
                confidence = max(current.support_score, abs(current.net_score))
                constraints.append("target_claim_not_currently_supported")
                if proposal.proposal_kind == GovernanceProposalKind.INVESTIGATE:
                    recommendation = KingRecommendation.REQUEST_EVIDENCE
                    rationale.append("investigation_may_test_opposed_claim")
                else:
                    recommendation = KingRecommendation.OPPOSE
                    rationale.append("opposed_by_current_belief")
        elif proposal.evidence_refs:
            records = [kernel.state.evidence[item] for item in proposal.evidence_refs]
            score = sum(item.confidence for item in records) / len(records)
            confidence = score
            recommendation = KingRecommendation.SUPPORT
            rationale.append("explicit_preserved_evidence_present")
        else:
            constraints.append("no_semantic_evidence")
            rationale.append("no_target_claim_or_evidence")

        return self._assessment(
            proposal,
            KingName.DATA,
            jurisdiction="epistemic_support",
            score=score,
            confidence=confidence,
            recommendation=recommendation,
            evidence_refs=tuple(sorted(evidence_refs)),
            constraints=tuple(sorted(set(constraints))),
            rationale_codes=tuple(sorted(set(rationale))),
            details=details,
        )

    def _forefront_king(
        self,
        kernel: VerdantKernel,
        proposal: CouncilProposal,
    ) -> KingAssessment:
        priorities = [
            kernel.state.attention_candidates[item].priority
            for item in proposal.attention_candidate_ids
        ]
        attention_signal = max(priorities, default=0.0)
        contradiction_boost = 0.0
        if proposal.target_claim_id is not None:
            claim_key = kernel.state.claims[proposal.target_claim_id].claim_key
            if any(
                item.claim_key == claim_key
                for item in kernel.state.contradictions.values()
            ):
                contradiction_boost = 1.0
        score = min(
            1.0,
            0.35 * proposal.relevance
            + 0.20 * proposal.urgency
            + 0.10 * proposal.novelty
            + 0.20 * proposal.predicted_information_gain
            + 0.10 * attention_signal
            + 0.05 * contradiction_boost,
        )
        constraints: list[str] = []
        if proposal.requested_resource > kernel.state.governance.attention_budget:
            constraints.append("attention_budget_exceeded")
            recommendation = KingRecommendation.DEPRIORITIZE
        elif score >= kernel.state.governance.forefront_priority_threshold:
            recommendation = KingRecommendation.PRIORITIZE
        else:
            recommendation = KingRecommendation.DEPRIORITIZE
        return self._assessment(
            proposal,
            KingName.FOREFRONT,
            jurisdiction="bounded_present_priority",
            score=score,
            confidence=min(1.0, 0.5 + 0.5 * abs(score - 0.5)),
            recommendation=recommendation,
            attention_candidate_ids=proposal.attention_candidate_ids,
            constraints=tuple(constraints),
            rationale_codes=(
                "finite_attention_budget",
                "contradiction_priority_without_truth_authority",
            ),
            details={
                "attention_signal": attention_signal,
                "contradiction_boost": contradiction_boost,
                "requested_resource": proposal.requested_resource,
                "attention_budget": kernel.state.governance.attention_budget,
                "priority_threshold": (
                    kernel.state.governance.forefront_priority_threshold
                ),
            },
        )

    def _ethics_king(
        self,
        kernel: VerdantKernel,
        proposal: CouncilProposal,
    ) -> KingAssessment:
        learned = kernel.state.governance.learned_action_risk.get(
            proposal.action_class, 0.0
        )
        effective_risk = max(proposal.harm_risk, learned)
        uncertainty_increment = 0.0
        if (
            proposal.proposal_kind == GovernanceProposalKind.ACT
            and proposal.target_claim_id is not None
        ):
            claim_key = kernel.state.claims[proposal.target_claim_id].claim_key
            if any(
                item.claim_key == claim_key
                for item in kernel.state.contradictions.values()
            ):
                uncertainty_increment = 0.15
                effective_risk = min(1.0, effective_risk + uncertainty_increment)

        constraints: list[str] = []
        rationale: list[str] = []
        threshold = kernel.state.governance.ethics_veto_threshold
        if proposal.consent_required and not proposal.consent_present:
            recommendation = KingRecommendation.DENY
            constraints.append("consent_missing")
            rationale.append("consent_boundary")
        elif proposal.boundary_sensitive and not proposal.consent_present:
            recommendation = KingRecommendation.DENY
            constraints.append("protected_boundary_without_permission")
            rationale.append("boundary_protection")
        elif effective_risk >= threshold and proposal.reversibility < 0.5:
            recommendation = KingRecommendation.DENY
            constraints.append("high_harm_risk_low_reversibility")
            rationale.append("harm_prevention")
        elif effective_risk >= threshold * 0.65:
            recommendation = KingRecommendation.CONSTRAIN
            constraints.append("cautious_reversible_only")
            rationale.append("risk_requires_constraints")
        else:
            recommendation = KingRecommendation.PERMIT
            rationale.append("risk_within_current_permission_policy")

        return self._assessment(
            proposal,
            KingName.ETHICS,
            jurisdiction="consequence_permission_boundary",
            score=max(0.0, 1.0 - effective_risk),
            confidence=max(effective_risk, 1.0 - effective_risk),
            recommendation=recommendation,
            evidence_refs=proposal.evidence_refs,
            constraints=tuple(constraints),
            rationale_codes=tuple(rationale),
            details={
                "declared_harm_risk": proposal.harm_risk,
                "learned_action_risk": learned,
                "uncertainty_increment": uncertainty_increment,
                "effective_harm_risk": effective_risk,
                "reversibility": proposal.reversibility,
                "consent_required": proposal.consent_required,
                "consent_present": proposal.consent_present,
                "boundary_sensitive": proposal.boundary_sensitive,
                "veto_threshold": threshold,
            },
        )

    def _council_rule(
        self,
        kernel: VerdantKernel,
        proposal: CouncilProposal,
        assessments: tuple[KingAssessment, ...],
    ) -> tuple[
        CouncilDisposition,
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        by_king = {item.king: item for item in assessments}
        data = by_king.get(KingName.DATA)
        forefront = by_king.get(KingName.FOREFRONT)
        ethics = by_king.get(KingName.ETHICS)
        constraints: set[str] = set()
        required: set[str] = set()
        reasons: set[str] = {"constitutional_rule_order"}
        alternatives = tuple(sorted(set(proposal.safe_alternatives)))

        for item in assessments:
            constraints.update(item.constraints)
        for king in KingName:
            if king not in by_king:
                reasons.add(f"king_disabled:{king.value}")

        if ethics and ethics.recommendation == KingRecommendation.DENY:
            reasons.add("ethics_hard_constraint")
            return (
                CouncilDisposition.DENY,
                (),
                (proposal.operation,),
                tuple(sorted(constraints)),
                (),
                alternatives,
                tuple(sorted(reasons)),
            )

        if data and data.recommendation == KingRecommendation.OPPOSE:
            reasons.add("data_opposes_commitment")
            required.add("new_evidence_capable_of_resolving_claim")
            return (
                CouncilDisposition.DEFER,
                (),
                (proposal.operation,),
                tuple(sorted(constraints)),
                tuple(sorted(required)),
                alternatives,
                tuple(sorted(reasons)),
            )

        if data and data.recommendation == KingRecommendation.REQUEST_EVIDENCE:
            required.add("evidence_to_resolve_uncertainty")
            if (
                proposal.proposal_kind == GovernanceProposalKind.INVESTIGATE
                and forefront
                and forefront.recommendation == KingRecommendation.PRIORITIZE
                and (
                    ethics is None
                    or ethics.recommendation
                    in {KingRecommendation.PERMIT, KingRecommendation.CONSTRAIN}
                )
            ):
                reasons.add("safe_investigation_authorized")
                constraints.add("result_must_return_through_evidence_pipeline")
                return (
                    CouncilDisposition.APPROVE_WITH_CONSTRAINTS,
                    (proposal.operation,),
                    (),
                    tuple(sorted(constraints)),
                    tuple(sorted(required)),
                    alternatives,
                    tuple(sorted(reasons)),
                )
            reasons.add("insufficient_evidence_for_commitment")
            return (
                CouncilDisposition.DEFER,
                (),
                (proposal.operation,),
                tuple(sorted(constraints)),
                tuple(sorted(required)),
                alternatives,
                tuple(sorted(reasons)),
            )

        if forefront and forefront.recommendation == KingRecommendation.DEPRIORITIZE:
            reasons.add("forefront_did_not_allocate_priority")
            return (
                CouncilDisposition.DEFER,
                (),
                (proposal.operation,),
                tuple(sorted(constraints)),
                (),
                alternatives,
                tuple(sorted(reasons)),
            )

        if ethics and ethics.recommendation == KingRecommendation.CONSTRAIN:
            reasons.add("ethics_constraints_applied")
            return (
                CouncilDisposition.APPROVE_WITH_CONSTRAINTS,
                (proposal.operation,),
                (),
                tuple(sorted(constraints)),
                (),
                alternatives,
                tuple(sorted(reasons)),
            )

        reasons.add("all_enabled_jurisdictions_allow_commitment")
        return (
            CouncilDisposition.APPROVE,
            (proposal.operation,),
            (),
            tuple(sorted(constraints)),
            (),
            alternatives,
            tuple(sorted(reasons)),
        )

    @staticmethod
    def _assessment(
        proposal: CouncilProposal,
        king: KingName,
        *,
        jurisdiction: str,
        score: float,
        confidence: float,
        recommendation: KingRecommendation,
        evidence_refs: tuple[str, ...] = (),
        attention_candidate_ids: tuple[str, ...] = (),
        constraints: tuple[str, ...] = (),
        rationale_codes: tuple[str, ...] = (),
        details: dict[str, Any] | None = None,
    ) -> KingAssessment:
        evidence_refs = tuple(sorted(set(evidence_refs)))
        attention_candidate_ids = tuple(sorted(set(attention_candidate_ids)))
        constraints = tuple(sorted(set(constraints)))
        rationale_codes = tuple(sorted(set(rationale_codes)))
        details = dict(details or {})
        assessment_id = stable_id(
            "king_assessment",
            proposal.proposal_id,
            king.value,
            jurisdiction,
            score,
            confidence,
            recommendation.value,
            evidence_refs,
            attention_candidate_ids,
            constraints,
            rationale_codes,
            details,
        )
        return KingAssessment(
            assessment_id=assessment_id,
            proposal_id=proposal.proposal_id,
            king=king,
            jurisdiction=jurisdiction,
            score=score,
            confidence=confidence,
            recommendation=recommendation,
            evidence_refs=evidence_refs,
            attention_candidate_ids=attention_candidate_ids,
            constraints=constraints,
            rationale_codes=rationale_codes,
            details=details,
        )

    def _report_shell_for_validation(
        self,
        kernel: VerdantKernel,
        proposal: CouncilProposal,
    ) -> CouncilReport:
        """Create a checksum-valid empty shell solely for reference validation."""
        policy = {
            **kernel.state.governance.model_dump(mode="json"),
            "decision_method": "reference_validation_only",
            "legacy_weights_used_for_decision": False,
        }
        report_id = stable_id(
            "council_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            kernel.semantic_fingerprint(),
            kernel.governance_fingerprint(),
            proposal.model_dump(mode="json"),
            (),
            CouncilDisposition.DEFER.value,
            (),
            (),
            (),
            (),
            (),
            ("reference_validation_only",),
            policy,
        )
        return CouncilReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            state_fingerprint=kernel.semantic_fingerprint(),
            governance_fingerprint=kernel.governance_fingerprint(),
            proposal=proposal,
            assessments=(),
            disposition=CouncilDisposition.DEFER,
            rationale_codes=("reference_validation_only",),
            policy_snapshot=policy,
        )
