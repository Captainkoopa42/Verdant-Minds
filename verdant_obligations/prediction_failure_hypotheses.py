"""Bounded hypotheses for native governance prediction failures.

The protocol preregisters one canonical target-ablation question alongside a
null alternative and an insufficient-evidence alternative.  It preserves the
complete Council prediction/outcome lineage but does not execute a trial,
attribute causality, resolve an obligation, or mutate canonical state.
"""
from __future__ import annotations

import hashlib
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    EvidenceKind,
    ObligationFamily,
    ObligationStatus,
    PredictionFailureObligationKernel,
    VerdantKernel,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .pipeline import derive_obligation_view


PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION = (
    "prediction_failure_hypothesis_protocol_v0.46"
)
PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR = (
    "preregister_prediction_failure_target_ablation"
)


class PredictionFailureHypothesisIntegrityError(RuntimeError):
    """Raised when a prediction-failure hypothesis loses canonical lineage."""


class PredictionFailureAblationComponent(str, Enum):
    DECLARED_HARM_RISK = "declared_harm_risk"


class PredictionFailureHypothesisKind(str, Enum):
    TARGET_ABLATION_TEST = "target_ablation_test"
    NULL_NOT_TARGET_SPECIFIC = "null_not_target_specific"
    DEFER_INSUFFICIENT_EVIDENCE = "defer_insufficient_evidence"


class PredictionFailureEvidenceCondition(str, Enum):
    ERROR_CHANGES_UNDER_MATCHED_TARGET_ABLATION = (
        "error_changes_under_matched_target_ablation"
    )
    ERROR_PERSISTS_UNDER_MATCHED_TARGET_ABLATION = (
        "error_persists_under_matched_target_ablation"
    )
    ADDITIONAL_CANONICAL_EVIDENCE_REQUIRED = (
        "additional_canonical_evidence_required"
    )


_CONDITION_BY_KIND = {
    PredictionFailureHypothesisKind.TARGET_ABLATION_TEST: (
        PredictionFailureEvidenceCondition.ERROR_CHANGES_UNDER_MATCHED_TARGET_ABLATION
    ),
    PredictionFailureHypothesisKind.NULL_NOT_TARGET_SPECIFIC: (
        PredictionFailureEvidenceCondition.ERROR_PERSISTS_UNDER_MATCHED_TARGET_ABLATION
    ),
    PredictionFailureHypothesisKind.DEFER_INSUFFICIENT_EVIDENCE: (
        PredictionFailureEvidenceCondition.ADDITIONAL_CANONICAL_EVIDENCE_REQUIRED
    ),
}


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class PredictionFailureHypothesisPolicy(BaseModel):
    """Visible bounds for family-local prediction-failure hypotheses."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    protocol_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
    action_operator: str = PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR
    minimum_attention_budget: float = Field(default=0.05, gt=0.0)
    hypothesis_count: int = Field(default=3, ge=3, le=3)

    @model_validator(mode="after")
    def validate_policy(self) -> "PredictionFailureHypothesisPolicy":
        if self.protocol_version != PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown prediction-failure hypothesis protocol version.")
        if self.action_operator != PREDICTION_FAILURE_TARGET_ABLATION_ACTION_OPERATOR:
            raise ValueError("Unknown prediction-failure hypothesis action operator.")
        return self


class PredictionFailureAblationTarget(FrozenRecord):
    """One canonical prediction field proposed for a future matched ablation."""

    target_id: str
    component: PredictionFailureAblationComponent
    proposal_ref: str
    prediction_source_ref: str
    action_class: str
    declared_value: float = Field(ge=0.0, le=1.0)
    proposal_snapshot_sha256: str
    ablation_executed: bool = False
    causal_target_asserted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "PredictionFailureAblationTarget":
        values.setdefault(
            "component", PredictionFailureAblationComponent.DECLARED_HARM_RISK
        )
        values.setdefault("ablation_executed", False)
        values.setdefault("causal_target_asserted", False)
        payload = {key: value for key, value in values.items() if key != "target_id"}
        values["target_id"] = stable_id(
            "prediction_failure_ablation_target", payload
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_target(self) -> "PredictionFailureAblationTarget":
        if not all(
            item.strip()
            for item in (
                self.proposal_ref,
                self.prediction_source_ref,
                self.action_class,
            )
        ):
            raise ValueError("Prediction-failure ablation target lost native lineage.")
        if self.component != PredictionFailureAblationComponent.DECLARED_HARM_RISK:
            raise ValueError("Prediction-failure target must be declared harm risk.")
        if not _is_sha256(self.proposal_snapshot_sha256):
            raise ValueError("Prediction-failure target requires a proposal snapshot.")
        if self.ablation_executed or self.causal_target_asserted:
            raise ValueError(
                "Prediction-failure target cannot claim execution or cause."
            )
        payload = self.model_dump(mode="json", exclude={"target_id"})
        if self.target_id != stable_id("prediction_failure_ablation_target", payload):
            raise ValueError("Prediction-failure ablation-target checksum mismatch.")
        return self


class PredictionFailureEvidenceReceipt(FrozenRecord):
    """Complete native prediction/outcome evidence authorized by Attention."""

    receipt_id: str
    protocol_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    obligation_event_ref: str
    outcome_ref: str
    prediction_source_ref: str
    proposal_ref: str
    council_report_ref: str
    action_class: str
    expected_value: float = Field(ge=0.0, le=1.0)
    observed_value: float = Field(ge=0.0, le=1.0)
    prediction_error: float = Field(gt=0.0, le=1.0)
    ablation_target: PredictionFailureAblationTarget
    forecast_basis_evidence_refs: tuple[str, ...] = Field(min_length=1)
    decision_evidence_refs: tuple[str, ...] = Field(min_length=1)
    outcome_evidence_refs: tuple[str, ...] = Field(min_length=1)
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    shared_evidence_refs: tuple[str, ...] = ()
    forecast_basis_source_roots: tuple[str, ...] = Field(min_length=1)
    decision_source_roots: tuple[str, ...] = Field(min_length=1)
    outcome_source_roots: tuple[str, ...] = Field(min_length=1)
    shared_source_roots: tuple[str, ...] = ()
    attention_decision_ref: str
    attention_bid_ref: str
    attention_allocation_ref: str
    authorized_budget: float = Field(gt=0.0)
    context_snapshot_sha256: str
    evidence_suppression_permitted: bool = False
    matched_trial_executed: bool = False
    ablation_outcome_observed: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "PredictionFailureEvidenceReceipt":
        values.setdefault(
            "protocol_version", PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
        )
        for key in (
            "forecast_basis_evidence_refs",
            "decision_evidence_refs",
            "outcome_evidence_refs",
            "protected_evidence_refs",
            "forecast_basis_source_roots",
            "decision_source_roots",
            "outcome_source_roots",
        ):
            values[key] = tuple(sorted(set(values[key])))
        values["shared_evidence_refs"] = tuple(
            sorted(
                set(values["decision_evidence_refs"]).intersection(
                    values["outcome_evidence_refs"]
                )
            )
        )
        values["shared_source_roots"] = tuple(
            sorted(
                set(values["decision_source_roots"]).intersection(
                    values["outcome_source_roots"]
                )
            )
        )
        values.setdefault("evidence_suppression_permitted", False)
        values.setdefault("matched_trial_executed", False)
        values.setdefault("ablation_outcome_observed", False)
        values.setdefault("causal_attribution_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {key: value for key, value in values.items() if key != "receipt_id"}
        values["receipt_id"] = stable_id(
            "prediction_failure_evidence_receipt",
            {
                key: (
                    value.model_dump(mode="json")
                    if isinstance(value, BaseModel)
                    else value
                )
                for key, value in payload.items()
            },
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "PredictionFailureEvidenceReceipt":
        identifiers = (
            self.obligation_id,
            self.obligation_event_ref,
            self.outcome_ref,
            self.prediction_source_ref,
            self.proposal_ref,
            self.council_report_ref,
            self.action_class,
            self.attention_decision_ref,
            self.attention_bid_ref,
            self.attention_allocation_ref,
        )
        if not all(value.strip() for value in identifiers):
            raise ValueError("Prediction-failure evidence receipt lost native lineage.")
        if self.protocol_version != PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown prediction-failure evidence protocol version.")
        if not math.isclose(
            abs(self.observed_value - self.expected_value),
            self.prediction_error,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise ValueError("Prediction-failure receipt error does not match values.")
        if not _is_sha256(self.context_snapshot_sha256):
            raise ValueError("Prediction-failure context must be a SHA-256 digest.")
        for refs, label in (
            (self.forecast_basis_evidence_refs, "forecast evidence"),
            (self.decision_evidence_refs, "decision evidence"),
            (self.outcome_evidence_refs, "outcome evidence"),
            (self.protected_evidence_refs, "protected evidence"),
            (self.shared_evidence_refs, "shared evidence"),
            (self.forecast_basis_source_roots, "forecast roots"),
            (self.decision_source_roots, "decision roots"),
            (self.outcome_source_roots, "outcome roots"),
            (self.shared_source_roots, "shared roots"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Prediction-failure receipt {label} must be sorted and unique."
                )
        forecast = set(self.forecast_basis_evidence_refs)
        decision = set(self.decision_evidence_refs)
        outcome = set(self.outcome_evidence_refs)
        if not forecast.issubset(decision):
            raise ValueError(
                "Forecast-basis evidence escaped Council decision lineage."
            )
        if set(self.protected_evidence_refs) != decision.union(outcome):
            raise ValueError(
                "Prediction-failure receipt suppressed canonical evidence."
            )
        if self.shared_evidence_refs != tuple(sorted(decision.intersection(outcome))):
            raise ValueError("Prediction-failure evidence partition drift detected.")
        if self.shared_source_roots != tuple(
            sorted(
                set(self.decision_source_roots).intersection(
                    self.outcome_source_roots
                )
            )
        ):
            raise ValueError("Prediction-failure source partition drift detected.")
        target = self.ablation_target
        if (
            target.proposal_ref != self.proposal_ref
            or target.prediction_source_ref != self.prediction_source_ref
            or target.action_class != self.action_class
            or target.declared_value != self.expected_value
        ):
            raise ValueError("Prediction-failure target drifted from receipt lineage.")
        if any(
            (
                self.evidence_suppression_permitted,
                self.matched_trial_executed,
                self.ablation_outcome_observed,
                self.causal_attribution_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError(
                "Prediction-failure evidence receipt cannot carry authority."
            )
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "prediction_failure_evidence_receipt", payload
        ):
            raise ValueError("Prediction-failure evidence-receipt checksum mismatch.")
        return self


class PredictionFailureHypothesis(FrozenRecord):
    """One mandatory alternative without trial or causal authority."""

    hypothesis_id: str
    protocol_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    outcome_ref: str
    kind: PredictionFailureHypothesisKind
    anticipated_condition: PredictionFailureEvidenceCondition
    ablation_target_ref: str
    evidence_receipt_ref: str
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    matched_trial_required: bool = True
    selected: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "PredictionFailureHypothesis":
        values.setdefault(
            "protocol_version", PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
        )
        values["anticipated_condition"] = _CONDITION_BY_KIND[values["kind"]]
        for key in ("protected_evidence_refs", "provenance_refs"):
            values[key] = tuple(sorted(set(values[key])))
        values.setdefault("matched_trial_required", True)
        values.setdefault("selected", False)
        values.setdefault("causal_attribution_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {
            key: value for key, value in values.items() if key != "hypothesis_id"
        }
        values["hypothesis_id"] = stable_id(
            "prediction_failure_hypothesis", payload
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_hypothesis(self) -> "PredictionFailureHypothesis":
        if self.protocol_version != PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown prediction-failure hypothesis protocol version.")
        if self.anticipated_condition != _CONDITION_BY_KIND[self.kind]:
            raise ValueError("Prediction-failure hypothesis condition drift detected.")
        for refs, label in (
            (self.protected_evidence_refs, "protected evidence"),
            (self.provenance_refs, "provenance"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Prediction-failure hypothesis {label} must be sorted and unique."
                )
        if not all(
            value.strip()
            for value in (
                self.obligation_id,
                self.outcome_ref,
                self.ablation_target_ref,
                self.evidence_receipt_ref,
            )
        ):
            raise ValueError("Prediction-failure hypothesis lost required lineage.")
        if not self.matched_trial_required:
            raise ValueError("Prediction-failure hypotheses require a matched trial.")
        if any(
            (
                self.selected,
                self.causal_attribution_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Prediction-failure hypotheses cannot carry authority.")
        payload = self.model_dump(mode="json", exclude={"hypothesis_id"})
        if self.hypothesis_id != stable_id("prediction_failure_hypothesis", payload):
            raise ValueError("Prediction-failure hypothesis checksum mismatch.")
        return self


class PredictionFailureHypothesisBundle(FrozenRecord):
    """Mandatory target-ablation, null, and insufficient-evidence alternatives."""

    bundle_id: str
    protocol_version: str = PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
    obligation_id: str
    obligation_event_ref: str
    attention_decision_ref: str
    attention_bid_ref: str
    attention_allocation_ref: str
    context_snapshot_sha256: str
    evidence_receipt: PredictionFailureEvidenceReceipt
    hypotheses: tuple[PredictionFailureHypothesis, ...] = Field(
        min_length=3, max_length=3
    )
    selected_hypothesis_ref: str | None = None
    matched_trial_executed: bool = False
    ablation_outcome_observed: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "PredictionFailureHypothesisBundle":
        values.setdefault(
            "protocol_version", PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION
        )
        values["hypotheses"] = tuple(
            sorted(values["hypotheses"], key=lambda item: item.hypothesis_id)
        )
        values.setdefault("selected_hypothesis_ref", None)
        values.setdefault("matched_trial_executed", False)
        values.setdefault("ablation_outcome_observed", False)
        values.setdefault("causal_attribution_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        payload = {key: value for key, value in values.items() if key != "bundle_id"}
        values["bundle_id"] = stable_id(
            "prediction_failure_hypothesis_bundle",
            {
                key: (
                    value.model_dump(mode="json")
                    if isinstance(value, BaseModel)
                    else tuple(item.model_dump(mode="json") for item in value)
                    if key == "hypotheses"
                    else value
                )
                for key, value in payload.items()
            },
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_bundle(self) -> "PredictionFailureHypothesisBundle":
        if self.protocol_version != PREDICTION_FAILURE_HYPOTHESIS_PROTOCOL_VERSION:
            raise ValueError("Unknown prediction-failure hypothesis bundle version.")
        if not _is_sha256(self.context_snapshot_sha256):
            raise ValueError(
                "Prediction-failure bundle context must be a SHA-256 digest."
            )
        if (
            tuple(sorted(self.hypotheses, key=lambda item: item.hypothesis_id))
            != self.hypotheses
        ):
            raise ValueError("Prediction-failure hypotheses must be identity-sorted.")
        if {item.kind for item in self.hypotheses} != set(
            PredictionFailureHypothesisKind
        ):
            raise ValueError(
                "Prediction-failure bundle requires target, null, and defer arms."
            )
        receipt = self.evidence_receipt
        lineage = (
            (self.obligation_id, receipt.obligation_id),
            (self.obligation_event_ref, receipt.obligation_event_ref),
            (self.attention_decision_ref, receipt.attention_decision_ref),
            (self.attention_bid_ref, receipt.attention_bid_ref),
            (self.attention_allocation_ref, receipt.attention_allocation_ref),
            (self.context_snapshot_sha256, receipt.context_snapshot_sha256),
        )
        if any(left != right for left, right in lineage):
            raise ValueError("Prediction-failure bundle lost evidence-receipt lineage.")
        required_provenance = tuple(
            sorted(
                {
                    self.obligation_id,
                    self.obligation_event_ref,
                    self.attention_decision_ref,
                    self.attention_bid_ref,
                    self.attention_allocation_ref,
                    receipt.receipt_id,
                    receipt.outcome_ref,
                    receipt.prediction_source_ref,
                    receipt.proposal_ref,
                    receipt.council_report_ref,
                    receipt.ablation_target.target_id,
                    *receipt.protected_evidence_refs,
                }
            )
        )
        for hypothesis in self.hypotheses:
            if (
                hypothesis.obligation_id != self.obligation_id
                or hypothesis.outcome_ref != receipt.outcome_ref
                or hypothesis.ablation_target_ref
                != receipt.ablation_target.target_id
                or hypothesis.evidence_receipt_ref != receipt.receipt_id
                or hypothesis.protected_evidence_refs
                != receipt.protected_evidence_refs
                or hypothesis.provenance_refs != required_provenance
            ):
                raise ValueError(
                    "Prediction-failure hypothesis suppressed bundle provenance."
                )
        if self.selected_hypothesis_ref is not None:
            raise ValueError("Prediction-failure bundles cannot select a hypothesis.")
        if any(
            (
                self.matched_trial_executed,
                self.ablation_outcome_observed,
                self.causal_attribution_enabled,
                self.resolution_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError(
                "Prediction-failure hypothesis bundles cannot carry authority."
            )
        payload = self.model_dump(mode="json", exclude={"bundle_id"})
        if self.bundle_id != stable_id(
            "prediction_failure_hypothesis_bundle", payload
        ):
            raise ValueError("Prediction-failure hypothesis-bundle checksum mismatch.")
        return self


class PredictionFailureHypothesisProtocol:
    """Generate and validate one read-only family-local hypothesis bundle."""

    ELIGIBLE_STATUSES = frozenset(
        {
            ObligationStatus.OPEN,
            ObligationStatus.INVESTIGATING,
            ObligationStatus.MAY_WAKE,
            ObligationStatus.REOPENED,
        }
    )

    def __init__(self, policy: PredictionFailureHypothesisPolicy | None = None) -> None:
        self.policy = policy or PredictionFailureHypothesisPolicy()

    @staticmethod
    def _last_event(kernel: VerdantKernel, obligation_id: str):
        events = tuple(
            item
            for item in kernel.state.obligation_history
            if item.obligation_id == obligation_id
        )
        if not events:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation has no canonical history."
            )
        return events[-1]

    def _attention_lineage(self, kernel: VerdantKernel, allocation_id: str):
        matches = []
        for decision in kernel.state.obligation_attention_decisions:
            for allocation in decision.allocations:
                if allocation.allocation_id == allocation_id:
                    bid = next(
                        (
                            item
                            for item in decision.bids
                            if item.bid_id == allocation.bid_id
                        ),
                        None,
                    )
                    matches.append((decision, bid, allocation))
        if len(matches) != 1 or matches[0][1] is None:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure hypothesis requires one canonical Attention "
                "allocation."
            )
        decision, bid, allocation = matches[0]
        assert bid is not None
        if (
            decision.epistemic_authority_enabled
            or bid.action_operator != self.policy.action_operator
            or bid.generator_version != self.policy.protocol_version
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "Attention allocation does not authorize this PredictionFailure "
                "protocol."
            )
        if allocation.granted_budget + 1e-12 < self.policy.minimum_attention_budget:
            raise PredictionFailureHypothesisIntegrityError(
                "Attention allocation is below the PredictionFailure protocol minimum."
            )
        return decision, bid, allocation

    def _generate(
        self,
        kernel: VerdantKernel,
        *,
        obligation_id: str,
        attention_allocation_id: str,
    ) -> PredictionFailureHypothesisBundle:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if not isinstance(obligation, PredictionFailureObligationKernel) or (
            obligation.family != ObligationFamily.PREDICTION_FAILURE
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "Hypothesis protocol requires a canonical PredictionFailure obligation."
            )
        if (
            derive_obligation_view(kernel, obligation_id).current_status
            not in self.ELIGIBLE_STATUSES
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation is not eligible for hypothesis attention."
            )
        event = self._last_event(kernel, obligation_id)
        attention_decision, bid, allocation = self._attention_lineage(
            kernel, attention_allocation_id
        )
        if (
            allocation.obligation_id != obligation_id
            or bid.obligation_id != obligation_id
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "Attention allocation belongs to another obligation."
            )
        if bid.basis_event_id != event.event_id:
            raise PredictionFailureHypothesisIntegrityError(
                "Attention allocation is stale relative to PredictionFailure history."
            )

        outcomes = tuple(
            item
            for item in kernel.state.governance_outcomes
            if item.outcome_id == obligation.outcome_ref
        )
        if len(outcomes) != 1:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation requires one canonical outcome."
            )
        outcome = outcomes[0]
        decisions = tuple(
            item
            for item in kernel.state.council_decisions
            if item.decision_event_id == obligation.prediction_source_ref
        )
        if len(decisions) != 1:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation requires one canonical Council decision."
            )
        council_decision = decisions[0]
        proposal = council_decision.report.proposal
        if (
            outcome.decision_event_id != council_decision.decision_event_id
            or outcome.action_class != proposal.action_class
            or obligation.prediction_source_ref != council_decision.decision_event_id
            or obligation.action_class != outcome.action_class
            or obligation.expected_value != proposal.harm_risk
            or obligation.observed_value != outcome.harm_score
            or not math.isclose(
                obligation.prediction_error,
                outcome.prediction_error,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation drifted from native outcome lineage."
            )
        expected_triggering = tuple(
            sorted(
                {
                    outcome.outcome_id,
                    council_decision.decision_event_id,
                    proposal.proposal_id,
                    *outcome.evidence_refs,
                }
            )
        )
        if obligation.canonical_triggering_refs != expected_triggering:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure obligation triggering lineage drift detected."
            )

        forecast_refs = tuple(sorted(set(proposal.evidence_refs)))
        decision_refs = tuple(sorted(set(council_decision.evidence_refs)))
        outcome_refs = tuple(sorted(set(outcome.evidence_refs)))
        protected_refs = tuple(sorted(set(decision_refs).union(outcome_refs)))
        if (
            not forecast_refs
            or not decision_refs
            or not outcome_refs
            or not set(forecast_refs).issubset(decision_refs)
            or any(ref not in kernel.state.evidence for ref in protected_refs)
            or not any(
                kernel.state.evidence[ref].kind == EvidenceKind.OUTCOME
                for ref in outcome_refs
            )
        ):
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure hypothesis requires complete forecast and outcome "
                "evidence."
            )
        required_attention_refs = set(event.triggering_refs).union(forecast_refs)
        if not required_attention_refs.issubset(bid.metric_provenance_refs):
            raise PredictionFailureHypothesisIntegrityError(
                "Attention bid suppressed PredictionFailure triggering or forecast "
                "evidence."
            )

        target = PredictionFailureAblationTarget.build(
            proposal_ref=proposal.proposal_id,
            prediction_source_ref=council_decision.decision_event_id,
            action_class=proposal.action_class,
            declared_value=proposal.harm_risk,
            proposal_snapshot_sha256=_sha256(proposal.model_dump(mode="json")),
        )
        evidence = {
            ref: kernel.state.evidence[ref]
            for ref in protected_refs
        }
        forecast_roots = tuple(
            sorted({kernel.state.evidence[ref].source_ref for ref in forecast_refs})
        )
        decision_roots = tuple(
            sorted({kernel.state.evidence[ref].source_ref for ref in decision_refs})
        )
        outcome_roots = tuple(
            sorted({kernel.state.evidence[ref].source_ref for ref in outcome_refs})
        )
        context_payload = {
            "protocol": self.policy.model_dump(mode="json"),
            "obligation": obligation.model_dump(mode="json"),
            "obligation_event": event.model_dump(mode="json"),
            "council_decision": council_decision.model_dump(mode="json"),
            "governance_outcome": outcome.model_dump(mode="json"),
            "ablation_target": target.model_dump(mode="json"),
            "evidence": tuple(
                evidence[ref].model_dump(mode="json") for ref in protected_refs
            ),
            "attention_decision": attention_decision.model_dump(mode="json"),
            "attention_bid": bid.model_dump(mode="json"),
            "attention_allocation": allocation.model_dump(mode="json"),
        }
        context_hash = _sha256(context_payload)
        try:
            receipt = PredictionFailureEvidenceReceipt.build(
                obligation_id=obligation_id,
                obligation_event_ref=event.event_id,
                outcome_ref=outcome.outcome_id,
                prediction_source_ref=council_decision.decision_event_id,
                proposal_ref=proposal.proposal_id,
                council_report_ref=council_decision.report.report_id,
                action_class=outcome.action_class,
                expected_value=proposal.harm_risk,
                observed_value=outcome.harm_score,
                prediction_error=outcome.prediction_error,
                ablation_target=target,
                forecast_basis_evidence_refs=forecast_refs,
                decision_evidence_refs=decision_refs,
                outcome_evidence_refs=outcome_refs,
                protected_evidence_refs=protected_refs,
                forecast_basis_source_roots=forecast_roots,
                decision_source_roots=decision_roots,
                outcome_source_roots=outcome_roots,
                attention_decision_ref=attention_decision.decision_id,
                attention_bid_ref=bid.bid_id,
                attention_allocation_ref=allocation.allocation_id,
                authorized_budget=allocation.granted_budget,
                context_snapshot_sha256=context_hash,
            )
        except ValueError as exc:
            raise PredictionFailureHypothesisIntegrityError(
                "Canonical PredictionFailure evidence is not a complete lineage."
            ) from exc

        provenance = tuple(
            sorted(
                {
                    obligation_id,
                    event.event_id,
                    attention_decision.decision_id,
                    bid.bid_id,
                    allocation.allocation_id,
                    receipt.receipt_id,
                    outcome.outcome_id,
                    council_decision.decision_event_id,
                    council_decision.report.report_id,
                    proposal.proposal_id,
                    target.target_id,
                    *protected_refs,
                }
            )
        )
        hypotheses = tuple(
            PredictionFailureHypothesis.build(
                obligation_id=obligation_id,
                outcome_ref=outcome.outcome_id,
                kind=kind,
                ablation_target_ref=target.target_id,
                evidence_receipt_ref=receipt.receipt_id,
                protected_evidence_refs=protected_refs,
                provenance_refs=provenance,
            )
            for kind in PredictionFailureHypothesisKind
        )
        return PredictionFailureHypothesisBundle.build(
            obligation_id=obligation_id,
            obligation_event_ref=event.event_id,
            attention_decision_ref=attention_decision.decision_id,
            attention_bid_ref=bid.bid_id,
            attention_allocation_ref=allocation.allocation_id,
            context_snapshot_sha256=context_hash,
            evidence_receipt=receipt,
            hypotheses=hypotheses,
        )

    def generate(
        self,
        kernel: VerdantKernel,
        *,
        obligation_id: str,
        attention_allocation_id: str,
    ) -> PredictionFailureHypothesisBundle:
        fingerprint = kernel.fingerprint()
        try:
            return self._generate(
                kernel,
                obligation_id=obligation_id,
                attention_allocation_id=attention_allocation_id,
            )
        finally:
            if kernel.fingerprint() != fingerprint:
                raise RuntimeError(
                    "PredictionFailure hypothesis generation mutated canonical state."
                )

    def validate(
        self,
        kernel: VerdantKernel,
        bundle: PredictionFailureHypothesisBundle,
    ) -> PredictionFailureHypothesisBundle:
        expected = self.generate(
            kernel,
            obligation_id=bundle.obligation_id,
            attention_allocation_id=bundle.attention_allocation_ref,
        )
        if bundle != expected:
            raise PredictionFailureHypothesisIntegrityError(
                "PredictionFailure hypothesis bundle does not match canonical "
                "provenance."
            )
        return expected
