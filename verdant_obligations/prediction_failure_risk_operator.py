"""Read-only projection of native predecision Council harm risk.

An absent declared target is supported only by risk learned from a distinct,
earlier physical outcome of the same action class. These projections are not
simulation traces, calibrated forecasts, or matched-trial results.
"""
from __future__ import annotations

import math
from enum import Enum
from pathlib import Path

from pydantic import ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, KingName, VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .prediction_failure_trial_plans import (
    PredictionFailureTrialPlanEnvelope,
    PredictionFailureTrialPlanIntegrityError,
    load_prediction_failure_trial_plan,
)
from .prediction_failure_trial_preregistration import (
    PREDICTION_FAILURE_TRIAL_ARM_ORDER,
    PredictionFailureTrialArm,
)


PREDICTION_FAILURE_RISK_OPERATOR_VERSION = "prediction_failure_risk_operator_v0.49"


class PredictionFailureRiskSource(str, Enum):
    DECLARED_AND_POLICY = "declared_and_predecision_policy"
    PRIOR_OUTCOME_LEARNING = "predecision_outcome_learning"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class PredictionFailureRiskProjection(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    projection_id: str
    operator_version: str = PREDICTION_FAILURE_RISK_OPERATOR_VERSION
    plan_ref: str
    arm: PredictionFailureTrialArm
    source: PredictionFailureRiskSource
    predicted_harm_score: float | None = Field(default=None, ge=0.0, le=1.0)
    supporting_refs: tuple[str, ...]
    reason: str | None = None
    simulation_trace_observed: bool = False
    trial_result_observed: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls, *, plan_ref: str, arm: PredictionFailureTrialArm,
        source: PredictionFailureRiskSource, score: float | None,
        supporting_refs: tuple[str, ...], reason: str | None = None,
    ) -> "PredictionFailureRiskProjection":
        values = dict(
            operator_version=PREDICTION_FAILURE_RISK_OPERATOR_VERSION,
            plan_ref=plan_ref, arm=arm, source=source,
            predicted_harm_score=score,
            supporting_refs=tuple(sorted(set(supporting_refs))), reason=reason,
            simulation_trace_observed=False, trial_result_observed=False,
            canonical_commit_permitted=False,
        )
        values["projection_id"] = stable_id(
            "prediction_failure_risk_projection", values
        )
        return cls(**values)

    @model_validator(mode="after")
    def check_boundary(self) -> "PredictionFailureRiskProjection":
        absent = self.source == PredictionFailureRiskSource.INSUFFICIENT_EVIDENCE
        if (
            self.operator_version != PREDICTION_FAILURE_RISK_OPERATOR_VERSION
            or not self.plan_ref or not self.supporting_refs
            or self.supporting_refs != tuple(sorted(set(self.supporting_refs)))
            or absent != (self.predicted_harm_score is None)
            or absent != (self.reason is not None)
            or (absent and self.reason != "no_predecision_action_class_outcome")
            or self.simulation_trace_observed or self.trial_result_observed
            or self.canonical_commit_permitted
        ):
            raise ValueError("PredictionFailure risk projection crossed its boundary.")
        expected = stable_id(
            "prediction_failure_risk_projection",
            self.model_dump(mode="json", exclude={"projection_id"}),
        )
        if self.projection_id != expected:
            raise ValueError("PredictionFailure risk projection checksum mismatch.")
        return self


class PredictionFailureRiskEvaluation(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    operator_version: str = PREDICTION_FAILURE_RISK_OPERATOR_VERSION
    plan_bundle_ref: str
    canonical_fingerprint: str
    projections: tuple[PredictionFailureRiskProjection, ...] = Field(
        min_length=3, max_length=3
    )
    matched_trial_executed: bool = False
    result_observed: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls, *, plan_bundle_ref: str, canonical_fingerprint: str,
        projections: tuple[PredictionFailureRiskProjection, ...],
    ) -> "PredictionFailureRiskEvaluation":
        values = dict(
            operator_version=PREDICTION_FAILURE_RISK_OPERATOR_VERSION,
            plan_bundle_ref=plan_bundle_ref,
            canonical_fingerprint=canonical_fingerprint,
            projections=projections, matched_trial_executed=False,
            result_observed=False, resolution_authority_enabled=False,
            canonical_commit_permitted=False,
        )
        values["evaluation_id"] = stable_id(
            "prediction_failure_risk_evaluation",
            {**values, "projections": tuple(
                item.model_dump(mode="json") for item in projections
            )},
        )
        return cls(**values)

    @model_validator(mode="after")
    def check_boundary(self) -> "PredictionFailureRiskEvaluation":
        if (
            self.operator_version != PREDICTION_FAILURE_RISK_OPERATOR_VERSION
            or not self.plan_bundle_ref or len(self.canonical_fingerprint) != 64
            or tuple(item.arm for item in self.projections)
            != PREDICTION_FAILURE_TRIAL_ARM_ORDER
            or len({item.plan_ref for item in self.projections}) != 3
            or self.matched_trial_executed or self.result_observed
            or self.resolution_authority_enabled or self.canonical_commit_permitted
        ):
            raise ValueError("PredictionFailure risk evaluation crossed its boundary.")
        expected = stable_id(
            "prediction_failure_risk_evaluation",
            self.model_dump(mode="json", exclude={"evaluation_id"}),
        )
        if self.evaluation_id != expected:
            raise ValueError("PredictionFailure risk evaluation checksum mismatch.")
        return self


class PredictionFailureGovernanceRiskOperator:
    """Explicitly project predecision Ethics risk from an exact durable plan."""

    def evaluate(
        self, *, kernel: VerdantKernel, plan_path: str | Path,
        preregistration_path: str | Path,
    ) -> PredictionFailureRiskEvaluation:
        before = kernel.fingerprint()
        envelope = load_prediction_failure_trial_plan(
            plan_path, kernel=kernel, preregistration_path=preregistration_path
        )
        evaluation = self._project(kernel, envelope)
        if kernel.fingerprint() != before:
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk projection mutated canonical state."
            )
        return evaluation

    @staticmethod
    def _project(
        kernel: VerdantKernel, envelope: PredictionFailureTrialPlanEnvelope,
    ) -> PredictionFailureRiskEvaluation:
        bundle = envelope.plan_bundle
        if bundle.canonical_fingerprint != kernel.fingerprint():
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk requires the exact canonical checkpoint."
            )
        receipt = bundle.preregistration.declaration.hypothesis_bundle.evidence_receipt
        decisions = tuple(
            item for item in kernel.state.council_decisions
            if item.decision_event_id == receipt.prediction_source_ref
        )
        if len(decisions) != 1:
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk lost its source Council decision."
            )
        report = decisions[0].report
        proposal = report.proposal
        if (
            proposal.proposal_id != bundle.canonical_proposal_ref
            or proposal.action_class != receipt.action_class
        ):
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk source proposal drifted."
            )
        ethics = tuple(
            item for item in report.assessments if item.king == KingName.ETHICS
        )
        if len(ethics) != 1:
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk requires one native Ethics assessment."
            )
        policy_risks = report.policy_snapshot.get("learned_action_risk")
        if not isinstance(policy_risks, dict):
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk lost predecision policy memory."
            )
        learned = policy_risks.get(proposal.action_class, 0.0)
        native = ethics[0].details
        increment = native.get("uncertainty_increment")
        if (
            type(learned) not in (float, int) or not math.isfinite(learned)
            or not 0.0 <= learned <= 1.0
            or type(increment) not in (float, int)
            or increment not in (0.0, 0.15)
            or native.get("declared_harm_risk") != proposal.harm_risk
            or native.get("learned_action_risk") != learned
            or native.get("effective_harm_risk")
            != min(1.0, max(proposal.harm_risk, learned) + increment)
            or ethics[0].score != 1.0 - native["effective_harm_risk"]
        ):
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk disagrees with native predecision Ethics."
            )

        # The source outcome occurs after its proposal and is never a forecast
        # input. The latest prior same-class physical outcome must match policy.
        priors = tuple(
            item for item in kernel.state.governance_outcomes
            if item.action_class == proposal.action_class
            and item.cycle < proposal.created_cycle
            and item.decision_event_id != receipt.prediction_source_ref
        )
        prior = max(priors, key=lambda item: item.cycle) if priors else None
        if prior is not None and (
            proposal.action_class not in policy_risks
            or prior.learned_risk_after != learned
            or prior.policy_revision_after > report.policy_snapshot.get("revision", -1)
            or not prior.evidence_refs
            or any(ref not in kernel.state.evidence for ref in prior.evidence_refs)
            or not any(
                kernel.state.evidence[ref].kind == EvidenceKind.OUTCOME
                for ref in prior.evidence_refs
            )
        ):
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure risk prior learning lost physical-outcome lineage."
            )
        native_refs = (proposal.proposal_id, report.report_id, ethics[0].assessment_id)
        projections = []
        for plan in bundle.plans:
            declared = plan.input_projection.declared_harm_risk
            if declared is None and prior is None:
                projections.append(PredictionFailureRiskProjection.build(
                    plan_ref=plan.plan_id, arm=plan.arm,
                    source=PredictionFailureRiskSource.INSUFFICIENT_EVIDENCE,
                    score=None, supporting_refs=native_refs,
                    reason="no_predecision_action_class_outcome",
                ))
                continue
            score = (
                min(1.0, max(declared, learned) + increment)
                if declared is not None else min(1.0, learned + increment)
            )
            refs = native_refs
            if prior is not None:
                refs += (prior.outcome_id, *prior.evidence_refs)
            projections.append(PredictionFailureRiskProjection.build(
                plan_ref=plan.plan_id, arm=plan.arm,
                source=(PredictionFailureRiskSource.DECLARED_AND_POLICY
                        if declared is not None else
                        PredictionFailureRiskSource.PRIOR_OUTCOME_LEARNING),
                score=score, supporting_refs=refs,
            ))
        return PredictionFailureRiskEvaluation.build(
            plan_bundle_ref=bundle.plan_bundle_id,
            canonical_fingerprint=bundle.canonical_fingerprint,
            projections=tuple(projections),
        )
