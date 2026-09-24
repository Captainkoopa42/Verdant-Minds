"""PredictionFailure anchors derived from canonical governance outcomes."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import PredictionFailureObligationKernel, VerdantKernel
from verdant_kernel.models import canonical_json_bytes, stable_id

from .pipeline import ObligationMutationResult, record_detected_prediction_failure


PREDICTION_FAILURE_DETECTOR_POLICY_VERSION = "prediction_failure_detector_v0.11"


class PredictionFailureDetectionPolicy(BaseModel):
    """Visible initial threshold; it is not a learned evaluator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = PREDICTION_FAILURE_DETECTOR_POLICY_VERSION
    minimum_prediction_error: float = Field(default=0.25, gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_policy(self) -> "PredictionFailureDetectionPolicy":
        if not self.policy_version.strip():
            raise ValueError("Prediction-failure policy version cannot be empty.")
        return self


class PredictionFailureCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    outcome_ref: str
    prediction_source_ref: str
    action_class: str
    expected_value: float = Field(ge=0.0, le=1.0)
    observed_value: float = Field(ge=0.0, le=1.0)
    prediction_error: float = Field(gt=0.0, le=1.0)
    scope_key: str
    canonical_triggering_refs: tuple[str, ...] = Field(min_length=3)
    source_lineage_roots: tuple[str, ...] = ()
    context_snapshot_hash: str
    source_event_key: str
    policy_version: str

    @model_validator(mode="after")
    def validate_candidate(self) -> "PredictionFailureCandidate":
        for values, label in (
            (self.canonical_triggering_refs, "triggering refs"),
            (self.source_lineage_roots, "lineage roots"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Prediction candidate {label} must be sorted and unique.")
        if not math.isclose(
            abs(self.observed_value - self.expected_value),
            self.prediction_error,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("Prediction candidate error does not match its values.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("prediction_failure_candidate", payload):
            raise ValueError("Prediction candidate identity checksum mismatch.")
        return self


@dataclass(frozen=True)
class PredictionFailureDetectionReport:
    policy_version: str
    inspected_outcome_ids: tuple[str, ...]
    candidates: tuple[PredictionFailureCandidate, ...]
    mutations: tuple[ObligationMutationResult, ...]

    @property
    def created_or_retriggered_count(self) -> int:
        return sum(not item.replayed for item in self.mutations)


class PredictionFailureDetector:
    """Detect large explicit prediction errors without evaluating semantics."""

    def __init__(self, policy: PredictionFailureDetectionPolicy | None = None) -> None:
        self.policy = policy or PredictionFailureDetectionPolicy()

    def inspect(
        self, kernel: VerdantKernel
    ) -> tuple[tuple[str, ...], tuple[PredictionFailureCandidate, ...]]:
        fingerprint = kernel.fingerprint()
        decisions = {
            item.decision_event_id: item for item in kernel.state.council_decisions
        }
        inspected: list[str] = []
        candidates: list[PredictionFailureCandidate] = []
        for outcome in sorted(
            kernel.state.governance_outcomes, key=lambda item: item.outcome_id
        ):
            inspected.append(outcome.outcome_id)
            if outcome.prediction_error < self.policy.minimum_prediction_error:
                continue
            decision = decisions.get(outcome.decision_event_id)
            if decision is None:
                continue
            proposal = decision.report.proposal
            if proposal.action_class != outcome.action_class:
                continue
            if any(ref not in kernel.state.evidence for ref in outcome.evidence_refs):
                continue
            evidence = tuple(kernel.state.evidence[ref] for ref in outcome.evidence_refs)
            triggering_refs = tuple(
                sorted({
                    outcome.outcome_id,
                    outcome.decision_event_id,
                    proposal.proposal_id,
                    *outcome.evidence_refs,
                })
            )
            roots = tuple(sorted(set(item.source_ref for item in evidence)))
            context_payload = {
                "outcome": outcome.model_dump(mode="json"),
                "proposal": proposal.model_dump(mode="json"),
                "evidence": tuple(
                    item.model_dump(mode="json")
                    for item in sorted(evidence, key=lambda item: item.evidence_id)
                ),
                "policy": self.policy.model_dump(mode="json"),
            }
            context_hash = hashlib.sha256(
                canonical_json_bytes(context_payload)
            ).hexdigest()
            scope_key = stable_id(
                "prediction_failure_scope",
                outcome.decision_event_id,
                outcome.action_class,
            )
            source_event_key = stable_id(
                "prediction_failure_detection",
                outcome.outcome_id,
                context_hash,
                self.policy.policy_version,
            )
            values = {
                "outcome_ref": outcome.outcome_id,
                "prediction_source_ref": outcome.decision_event_id,
                "action_class": outcome.action_class,
                "expected_value": proposal.harm_risk,
                "observed_value": outcome.harm_score,
                "prediction_error": outcome.prediction_error,
                "scope_key": scope_key,
                "canonical_triggering_refs": triggering_refs,
                "source_lineage_roots": roots,
                "context_snapshot_hash": context_hash,
                "source_event_key": source_event_key,
                "policy_version": self.policy.policy_version,
            }
            candidates.append(
                PredictionFailureCandidate(
                    candidate_id=stable_id("prediction_failure_candidate", values),
                    **values,
                )
            )
        if kernel.fingerprint() != fingerprint:
            raise RuntimeError("Prediction-failure inspection mutated canonical state.")
        return tuple(inspected), tuple(candidates)

    def detect_and_record(self, kernel: VerdantKernel) -> PredictionFailureDetectionReport:
        inspected, candidates = self.inspect(kernel)
        mutations: list[ObligationMutationResult] = []
        for candidate in candidates:
            obligation_id = stable_id(
                "obligation",
                "0.11",
                "PredictionFailure",
                candidate.outcome_ref,
                candidate.prediction_source_ref,
                candidate.action_class,
                candidate.scope_key,
            )
            existing = kernel.state.obligation_kernels.get(obligation_id)
            if existing is None:
                obligation = PredictionFailureObligationKernel(
                    kernel_id=obligation_id,
                    outcome_ref=candidate.outcome_ref,
                    prediction_source_ref=candidate.prediction_source_ref,
                    action_class=candidate.action_class,
                    expected_value=candidate.expected_value,
                    observed_value=candidate.observed_value,
                    prediction_error=candidate.prediction_error,
                    scope_key=candidate.scope_key,
                    canonical_triggering_refs=candidate.canonical_triggering_refs,
                    creation_cycle=kernel.state.cycle + 1,
                    policy_version=self.policy.policy_version,
                )
            elif isinstance(existing, PredictionFailureObligationKernel):
                obligation = existing
            else:
                raise RuntimeError("Prediction obligation crossed a family boundary.")
            mutations.append(
                record_detected_prediction_failure(
                    kernel,
                    obligation=obligation,
                    triggering_refs=candidate.canonical_triggering_refs,
                    source_event_key=candidate.source_event_key,
                    context_snapshot_hash=candidate.context_snapshot_hash,
                    source_lineage_roots=candidate.source_lineage_roots,
                    policy_version=self.policy.policy_version,
                )
            )
        return PredictionFailureDetectionReport(
            policy_version=self.policy.policy_version,
            inspected_outcome_ids=inspected,
            candidates=candidates,
            mutations=tuple(mutations),
        )
