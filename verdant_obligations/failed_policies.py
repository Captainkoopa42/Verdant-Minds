"""FailedPolicy anchors for repeated blocks of one stable governance scope.

Repeated denial is only an unresolved structural signal.  It is not evidence
that the safety decision was wrong, and this module has no policy-revision or
resolution authority.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    CouncilDisposition,
    FailedPolicyObligationKernel,
    GovernanceProposalKind,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id

from .pipeline import ObligationMutationResult, record_detected_failed_policy


FAILED_POLICY_DETECTOR_POLICY_VERSION = "failed_policy_detector_v0.13"


class FailedPolicyDetectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = FAILED_POLICY_DETECTOR_POLICY_VERSION
    minimum_repeated_denials: int = Field(default=2, ge=2)

    @model_validator(mode="after")
    def validate_policy(self) -> "FailedPolicyDetectionPolicy":
        if not self.policy_version.strip():
            raise ValueError("Failed-policy detector version cannot be empty.")
        return self


class FailedPolicyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    operation: str
    action_class: str
    proposal_kind: GovernanceProposalKind
    failure_signal: str = "repeated_governance_block"
    blocked_decision_refs: tuple[str, ...] = Field(min_length=2)
    scope_key: str
    canonical_triggering_refs: tuple[str, ...] = Field(min_length=4)
    source_lineage_roots: tuple[str, ...] = ()
    context_snapshot_hash: str
    source_event_key: str
    policy_version: str

    @model_validator(mode="after")
    def validate_candidate(self) -> "FailedPolicyCandidate":
        if self.failure_signal != "repeated_governance_block":
            raise ValueError("Failed-policy candidate has an unsupported signal.")
        for values, label in (
            (self.blocked_decision_refs, "blocked decisions"),
            (self.canonical_triggering_refs, "triggering refs"),
            (self.source_lineage_roots, "lineage roots"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Failed-policy candidate {label} must be sorted and unique.")
        if not set(self.blocked_decision_refs).issubset(
            self.canonical_triggering_refs
        ):
            raise ValueError("Failed-policy candidate suppressed a blocked decision.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("failed_policy_candidate", payload):
            raise ValueError("Failed-policy candidate checksum mismatch.")
        return self


@dataclass(frozen=True)
class FailedPolicyDetectionReport:
    policy_version: str
    inspected_decision_ids: tuple[str, ...]
    candidates: tuple[FailedPolicyCandidate, ...]
    mutations: tuple[ObligationMutationResult, ...]

    @property
    def created_or_retriggered_count(self) -> int:
        return sum(not item.replayed for item in self.mutations)


class FailedPolicyDetector:
    """Detect repeated DENY outcomes without judging or weakening the denial."""

    def __init__(self, policy: FailedPolicyDetectionPolicy | None = None) -> None:
        self.policy = policy or FailedPolicyDetectionPolicy()

    def inspect(
        self, kernel: VerdantKernel
    ) -> tuple[tuple[str, ...], tuple[FailedPolicyCandidate, ...]]:
        fingerprint = kernel.fingerprint()
        inspected = tuple(
            sorted(item.decision_event_id for item in kernel.state.council_decisions)
        )
        grouped: dict[tuple[str, str, GovernanceProposalKind], list] = defaultdict(list)
        for decision in kernel.state.council_decisions:
            report = decision.report
            proposal = report.proposal
            if (
                report.disposition == CouncilDisposition.DENY
                and proposal.operation in report.blocked_operations
            ):
                grouped[
                    (proposal.operation, proposal.action_class, proposal.proposal_kind)
                ].append(decision)

        candidates: list[FailedPolicyCandidate] = []
        for (operation, action_class, proposal_kind), decisions in sorted(
            grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2].value)
        ):
            decisions = sorted(decisions, key=lambda item: item.decision_event_id)
            if len(decisions) < self.policy.minimum_repeated_denials:
                continue
            decision_refs = tuple(item.decision_event_id for item in decisions)
            evidence_refs = tuple(
                sorted({ref for item in decisions for ref in item.evidence_refs})
            )
            if any(ref not in kernel.state.evidence for ref in evidence_refs):
                continue
            report_refs = tuple(sorted(item.report.report_id for item in decisions))
            proposal_refs = tuple(
                sorted(item.report.proposal.proposal_id for item in decisions)
            )
            triggering_refs = tuple(
                sorted({*decision_refs, *report_refs, *proposal_refs, *evidence_refs})
            )
            roots = tuple(
                sorted({kernel.state.evidence[ref].source_ref for ref in evidence_refs})
            )
            scope_key = stable_id(
                "failed_policy_scope", operation, action_class, proposal_kind.value
            )
            context_payload = {
                "decisions": tuple(
                    item.model_dump(mode="json") for item in decisions
                ),
                "policy": self.policy.model_dump(mode="json"),
            }
            context_hash = hashlib.sha256(
                canonical_json_bytes(context_payload)
            ).hexdigest()
            source_event_key = stable_id(
                "failed_policy_detection",
                scope_key,
                context_hash,
                self.policy.policy_version,
            )
            values = {
                "operation": operation,
                "action_class": action_class,
                "proposal_kind": proposal_kind,
                "blocked_decision_refs": decision_refs,
                "scope_key": scope_key,
                "canonical_triggering_refs": triggering_refs,
                "source_lineage_roots": roots,
                "context_snapshot_hash": context_hash,
                "source_event_key": source_event_key,
                "policy_version": self.policy.policy_version,
            }
            candidates.append(
                FailedPolicyCandidate(
                    candidate_id=stable_id("failed_policy_candidate", {
                        key: (
                            value.value
                            if isinstance(value, GovernanceProposalKind)
                            else value
                        )
                        for key, value in values.items()
                    } | {"failure_signal": "repeated_governance_block"}),
                    **values,
                )
            )
        if kernel.fingerprint() != fingerprint:
            raise RuntimeError("Failed-policy inspection mutated canonical state.")
        return inspected, tuple(candidates)

    def detect_and_record(self, kernel: VerdantKernel) -> FailedPolicyDetectionReport:
        inspected, candidates = self.inspect(kernel)
        mutations: list[ObligationMutationResult] = []
        for candidate in candidates:
            obligation_id = stable_id(
                "obligation",
                "0.13",
                "FailedPolicy",
                candidate.operation,
                candidate.action_class,
                candidate.proposal_kind.value,
                candidate.scope_key,
            )
            existing = kernel.state.obligation_kernels.get(obligation_id)
            if existing is None:
                obligation = FailedPolicyObligationKernel(
                    kernel_id=obligation_id,
                    operation=candidate.operation,
                    action_class=candidate.action_class,
                    proposal_kind=candidate.proposal_kind,
                    blocked_decision_refs=candidate.blocked_decision_refs,
                    scope_key=candidate.scope_key,
                    canonical_triggering_refs=candidate.canonical_triggering_refs,
                    creation_cycle=kernel.state.cycle + 1,
                    policy_version=self.policy.policy_version,
                )
            elif isinstance(existing, FailedPolicyObligationKernel):
                obligation = existing
            else:
                raise RuntimeError("Failed-policy obligation crossed a family boundary.")
            mutations.append(
                record_detected_failed_policy(
                    kernel,
                    obligation=obligation,
                    triggering_refs=candidate.canonical_triggering_refs,
                    source_event_key=candidate.source_event_key,
                    context_snapshot_hash=candidate.context_snapshot_hash,
                    source_lineage_roots=candidate.source_lineage_roots,
                    policy_version=self.policy.policy_version,
                )
            )
        return FailedPolicyDetectionReport(
            policy_version=self.policy.policy_version,
            inspected_decision_ids=inspected,
            candidates=candidates,
            mutations=tuple(mutations),
        )
