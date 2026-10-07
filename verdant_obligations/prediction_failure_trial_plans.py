"""Durable simulation-input plans for the PredictionFailure trial.

This v0.48 layer consumes one immutable v0.47 preregistration and materializes
three typed, simulation-only proposal projections.  The target-ablation arm
represents the declared harm-risk field as absent rather than inventing a
replacement value.  Every other proposal input is held byte-exact across the
baseline, ablation, and valid-null arms.

The resulting ``.vpp`` package is durable pre-execution evidence.  It does not
create a native overlay patch, instantiate a simulation ledger, provide the
missing prediction operator, execute an arm, observe a trace, or grant any
canonical authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from enum import Enum
from pathlib import Path
from typing import Any

try:  # pragma: no cover - non-POSIX operation is rejected explicitly.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import CouncilProposal, GovernanceProposalKind, VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import SimulationDisposition
from .prediction_failure_trial_preregistration import (
    PREDICTION_FAILURE_TRIAL_ARM_ORDER,
    PredictionFailureTrialArm,
    PredictionFailureTrialArmDeclaration,
    PredictionFailureTrialPreregistrationEnvelope,
    load_prediction_failure_trial_preregistration,
    prediction_failure_trial_preregistration_bytes,
)


PREDICTION_FAILURE_TRIAL_PLAN_VERSION = "prediction_failure_trial_plan_v0.48"
PREDICTION_FAILURE_TRIAL_PLAN_FORMAT = "verdant-prediction-failure-trial-plan-v1"
PREDICTION_FAILURE_TRIAL_PLAN_SIDECAR_SUFFIX = ".vpp"
_MAX_SIDECAR_BYTES = 16 * 1024 * 1024


class PredictionFailureTrialPlanIntegrityError(RuntimeError):
    """Raised when a PredictionFailure plan package loses exact lineage."""


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha_bytes(canonical_json_bytes(value))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (tuple, list)):
        return tuple(_json(item) for item in value)
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    return value


def _payload(values: dict[str, Any]) -> dict[str, Any]:
    return {key: _json(value) for key, value in values.items()}


def _normalized_metadata(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(canonical_json_bytes(value).decode("utf-8"))


def _proposal_non_target_payload(proposal: CouncilProposal) -> dict[str, Any]:
    payload = proposal.model_dump(mode="json")
    payload.pop("proposal_id")
    payload.pop("harm_risk")
    return payload


def _projection_non_target_payload(
    projection: "PredictionFailureSimulationInputProjection",
) -> dict[str, Any]:
    return {
        "kernel_id": projection.kernel_id,
        "created_cycle": projection.created_cycle,
        "proposal_kind": projection.proposal_kind.value,
        "operation": projection.operation,
        "action_class": projection.action_class,
        "description": projection.description,
        "target_claim_id": projection.target_claim_id,
        "evidence_refs": projection.evidence_refs,
        "attention_candidate_ids": projection.attention_candidate_ids,
        "resonance_event_ids": projection.resonance_event_ids,
        "requested_resource": projection.requested_resource,
        "relevance": projection.relevance,
        "urgency": projection.urgency,
        "novelty": projection.novelty,
        "predicted_information_gain": projection.predicted_information_gain,
        "reversibility": projection.reversibility,
        "consent_required": projection.consent_required,
        "consent_present": projection.consent_present,
        "boundary_sensitive": projection.boundary_sensitive,
        "safe_alternatives": projection.safe_alternatives,
        "metadata": projection.metadata,
        "state_fingerprint": projection.state_fingerprint,
        "governance_fingerprint": projection.governance_fingerprint,
    }


def _canonical_proposal(
    kernel: VerdantKernel,
    preregistration: PredictionFailureTrialPreregistrationEnvelope,
) -> CouncilProposal:
    declaration = preregistration.declaration
    receipt = declaration.hypothesis_bundle.evidence_receipt
    matches = tuple(
        item.report.proposal
        for item in kernel.state.council_decisions
        if item.decision_event_id == receipt.prediction_source_ref
    )
    if len(matches) != 1:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plans require one canonical Council proposal."
        )
    proposal = matches[0]
    if (
        proposal.proposal_id != receipt.proposal_ref
        or _digest(proposal.model_dump(mode="json"))
        != receipt.ablation_target.proposal_snapshot_sha256
        or proposal.harm_risk != receipt.ablation_target.declared_value
        or proposal.action_class != receipt.action_class
    ):
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan proposal drifted from preregistered lineage."
        )
    return proposal


class PredictionFailureSimulationInputProjection(FrozenRecord):
    """Typed proposal input with the sole candidate target optionally absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    projection_id: str
    projection_version: str = PREDICTION_FAILURE_TRIAL_PLAN_VERSION
    arm: PredictionFailureTrialArm
    preregistration_declaration_ref: str
    preregistration_arm_ref: str
    target_ref: str
    canonical_proposal_ref: str
    canonical_proposal_sha256: str
    non_target_input_sha256: str
    kernel_id: str
    created_cycle: int = Field(ge=0)
    proposal_kind: GovernanceProposalKind
    operation: str
    action_class: str
    description: str
    target_claim_id: str | None = None
    evidence_refs: tuple[str, ...] = ()
    attention_candidate_ids: tuple[str, ...] = ()
    resonance_event_ids: tuple[str, ...] = ()
    requested_resource: float = Field(gt=0.0)
    relevance: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    predicted_information_gain: float = Field(ge=0.0, le=1.0)
    declared_harm_risk: float | None = Field(default=None, ge=0.0, le=1.0)
    reversibility: float = Field(ge=0.0, le=1.0)
    consent_required: bool
    consent_present: bool
    boundary_sensitive: bool
    safe_alternatives: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
    state_fingerprint: str
    governance_fingerprint: str
    target_present: bool
    target_ablation_requested: bool
    no_op_control: bool
    simulation_only: bool = True
    missing_target_default_permitted: bool = False
    canonical_proposal_materialized: bool = False
    predicted_harm_observed: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        proposal: CouncilProposal,
        declaration_ref: str,
        target_ref: str,
        arm: PredictionFailureTrialArmDeclaration,
    ) -> "PredictionFailureSimulationInputProjection":
        target_present = arm.target_present
        values = {
            "projection_version": PREDICTION_FAILURE_TRIAL_PLAN_VERSION,
            "arm": arm.arm,
            "preregistration_declaration_ref": declaration_ref,
            "preregistration_arm_ref": arm.arm_id,
            "target_ref": target_ref,
            "canonical_proposal_ref": proposal.proposal_id,
            "canonical_proposal_sha256": _digest(
                proposal.model_dump(mode="json")
            ),
            "non_target_input_sha256": _digest(
                _proposal_non_target_payload(proposal)
            ),
            "kernel_id": proposal.kernel_id,
            "created_cycle": proposal.created_cycle,
            "proposal_kind": proposal.proposal_kind,
            "operation": proposal.operation,
            "action_class": proposal.action_class,
            "description": proposal.description,
            "target_claim_id": proposal.target_claim_id,
            "evidence_refs": proposal.evidence_refs,
            "attention_candidate_ids": proposal.attention_candidate_ids,
            "resonance_event_ids": proposal.resonance_event_ids,
            "requested_resource": proposal.requested_resource,
            "relevance": proposal.relevance,
            "urgency": proposal.urgency,
            "novelty": proposal.novelty,
            "predicted_information_gain": proposal.predicted_information_gain,
            "declared_harm_risk": proposal.harm_risk if target_present else None,
            "reversibility": proposal.reversibility,
            "consent_required": proposal.consent_required,
            "consent_present": proposal.consent_present,
            "boundary_sensitive": proposal.boundary_sensitive,
            "safe_alternatives": proposal.safe_alternatives,
            "metadata": _normalized_metadata(proposal.metadata),
            "state_fingerprint": proposal.state_fingerprint,
            "governance_fingerprint": proposal.governance_fingerprint,
            "target_present": target_present,
            "target_ablation_requested": arm.target_ablation_requested,
            "no_op_control": arm.no_op_control,
            "simulation_only": True,
            "missing_target_default_permitted": False,
            "canonical_proposal_materialized": False,
            "predicted_harm_observed": False,
            "canonical_commit_permitted": False,
        }
        values["projection_id"] = stable_id(
            "prediction_failure_simulation_input", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_projection(
        self,
    ) -> "PredictionFailureSimulationInputProjection":
        expected_modes = {
            PredictionFailureTrialArm.BASELINE: (True, False, False),
            PredictionFailureTrialArm.TARGET_ABLATION: (False, True, False),
            PredictionFailureTrialArm.VALID_NULL: (True, False, True),
        }
        identifiers = (
            self.preregistration_declaration_ref,
            self.preregistration_arm_ref,
            self.target_ref,
            self.canonical_proposal_ref,
            self.kernel_id,
            self.operation,
            self.action_class,
            self.description,
        )
        if (
            self.projection_version != PREDICTION_FAILURE_TRIAL_PLAN_VERSION
            or not all(item.strip() for item in identifiers)
            or not _is_sha256(self.canonical_proposal_sha256)
            or not _is_sha256(self.non_target_input_sha256)
            or not _is_sha256(self.state_fingerprint)
            or not _is_sha256(self.governance_fingerprint)
            or (
                self.target_present,
                self.target_ablation_requested,
                self.no_op_control,
            )
            != expected_modes[self.arm]
            or (self.declared_harm_risk is None) == self.target_present
            or not self.simulation_only
            or self.missing_target_default_permitted
            or self.canonical_proposal_materialized
            or self.predicted_harm_observed
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "PredictionFailure projection crossed its simulation-only boundary."
            )
        for refs, label in (
            (self.evidence_refs, "evidence"),
            (self.attention_candidate_ids, "attention candidates"),
            (self.resonance_event_ids, "resonance events"),
            (self.safe_alternatives, "safe alternatives"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"PredictionFailure projection {label} must be sorted and unique."
                )
        if self.non_target_input_sha256 != _digest(
            _projection_non_target_payload(self)
        ):
            raise ValueError(
                "PredictionFailure projection changed a held-constant input."
            )
        expected = stable_id(
            "prediction_failure_simulation_input",
            self.model_dump(mode="json", exclude={"projection_id"}),
        )
        if self.projection_id != expected:
            raise ValueError("PredictionFailure projection checksum mismatch.")
        return self


class PredictionFailureTrialSimulationPlan(FrozenRecord):
    """One frozen future arm; it is not a native runtime execution request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_id: str
    plan_version: str = PREDICTION_FAILURE_TRIAL_PLAN_VERSION
    arm: PredictionFailureTrialArm
    preregistration_declaration_ref: str
    preregistration_arm_ref: str
    input_projection: PredictionFailureSimulationInputProjection
    input_projection_ref: str
    counterfactual_source_event_key: str
    obligation_id: str
    attention_decision_ref: str
    attention_allocation_ref: str
    target_ref: str
    hypothesis_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    result_refs: tuple[str, ...] = Field(min_length=1)
    shared_design_seed: int = Field(ge=0, le=0xFFFFFFFF)
    requested_budget: float = Field(gt=0.0)
    maximum_consumed_budget: float = Field(gt=0.0)
    required_disposition: SimulationDisposition = SimulationDisposition.DISCARDED
    dedicated_pristine_simulation_ledger_required: bool = True
    exact_canonical_checkpoint_required: bool = True
    native_overlay_patches_permitted: bool = False
    counterfactual_runtime_plan_materialized: bool = False
    prediction_operator_ref: str | None = None
    runtime_execution_authorized: bool = False
    trace_observed: bool = False
    predicted_harm_observed: bool = False
    result_observed: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        preregistration: PredictionFailureTrialPreregistrationEnvelope,
        arm: PredictionFailureTrialArmDeclaration,
        projection: PredictionFailureSimulationInputProjection,
    ) -> "PredictionFailureTrialSimulationPlan":
        declaration = preregistration.declaration
        receipt = declaration.hypothesis_bundle.evidence_receipt
        hypothesis_refs = tuple(
            sorted(
                item.hypothesis_id
                for item in declaration.hypothesis_bundle.hypotheses
            )
        )
        result_refs = tuple(
            sorted(
                {
                    declaration.declaration_id,
                    arm.arm_id,
                    projection.projection_id,
                    *declaration.held_constant_refs,
                }
            )
        )
        values = {
            "plan_version": PREDICTION_FAILURE_TRIAL_PLAN_VERSION,
            "arm": arm.arm,
            "preregistration_declaration_ref": declaration.declaration_id,
            "preregistration_arm_ref": arm.arm_id,
            "input_projection": projection,
            "input_projection_ref": projection.projection_id,
            "counterfactual_source_event_key": stable_id(
                "prediction_failure_trial_counterfactual_source",
                PREDICTION_FAILURE_TRIAL_PLAN_VERSION,
                declaration.declaration_id,
                arm.arm_id,
                projection.projection_id,
            ),
            "obligation_id": declaration.hypothesis_bundle.obligation_id,
            "attention_decision_ref": (
                declaration.hypothesis_bundle.attention_decision_ref
            ),
            "attention_allocation_ref": (
                declaration.hypothesis_bundle.attention_allocation_ref
            ),
            "target_ref": declaration.target_ref,
            "hypothesis_refs": hypothesis_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "result_refs": result_refs,
            "shared_design_seed": declaration.shared_design_seed,
            "requested_budget": arm.requested_budget,
            "maximum_consumed_budget": arm.requested_budget,
            "required_disposition": SimulationDisposition.DISCARDED,
            "dedicated_pristine_simulation_ledger_required": True,
            "exact_canonical_checkpoint_required": True,
            "native_overlay_patches_permitted": False,
            "counterfactual_runtime_plan_materialized": False,
            "prediction_operator_ref": None,
            "runtime_execution_authorized": False,
            "trace_observed": False,
            "predicted_harm_observed": False,
            "result_observed": False,
            "causal_attribution_enabled": False,
            "resolution_authority_enabled": False,
            "promotion_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["plan_id"] = stable_id(
            "prediction_failure_trial_simulation_plan", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_plan(self) -> "PredictionFailureTrialSimulationPlan":
        projection = self.input_projection
        if (
            self.plan_version != PREDICTION_FAILURE_TRIAL_PLAN_VERSION
            or self.arm != projection.arm
            or self.preregistration_declaration_ref
            != projection.preregistration_declaration_ref
            or self.preregistration_arm_ref
            != projection.preregistration_arm_ref
            or self.input_projection_ref != projection.projection_id
            or self.target_ref != projection.target_ref
            or self.maximum_consumed_budget != self.requested_budget
            or self.required_disposition != SimulationDisposition.DISCARDED
            or not self.dedicated_pristine_simulation_ledger_required
            or not self.exact_canonical_checkpoint_required
            or self.native_overlay_patches_permitted
            or self.counterfactual_runtime_plan_materialized
            or self.prediction_operator_ref is not None
            or self.runtime_execution_authorized
            or self.trace_observed
            or self.predicted_harm_observed
            or self.result_observed
            or self.causal_attribution_enabled
            or self.resolution_authority_enabled
            or self.promotion_authority_enabled
            or self.policy_rewrite_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "PredictionFailure plan crossed its pre-execution boundary."
            )
        identifiers = (
            self.preregistration_declaration_ref,
            self.preregistration_arm_ref,
            self.counterfactual_source_event_key,
            self.obligation_id,
            self.attention_decision_ref,
            self.attention_allocation_ref,
            self.target_ref,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("PredictionFailure plan lost required lineage.")
        for refs, label in (
            (self.hypothesis_refs, "hypotheses"),
            (self.protected_evidence_refs, "protected evidence"),
            (self.result_refs, "result lineage"),
        ):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"PredictionFailure plan {label} must be sorted and unique."
                )
        expected = stable_id(
            "prediction_failure_trial_simulation_plan",
            self.model_dump(mode="json", exclude={"plan_id"}),
        )
        if self.plan_id != expected:
            raise ValueError("PredictionFailure trial-plan checksum mismatch.")
        return self


class PredictionFailureTrialPlanBundle(FrozenRecord):
    """Three typed projections and future plans paired to one exact ``.vfp``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan_bundle_id: str
    plan_version: str = PREDICTION_FAILURE_TRIAL_PLAN_VERSION
    preregistration: PredictionFailureTrialPreregistrationEnvelope
    preregistration_declaration_ref: str
    preregistration_sha256: str
    canonical_kernel_id: str
    canonical_fingerprint: str
    canonical_cycle: int = Field(ge=0)
    canonical_proposal_ref: str
    canonical_proposal_sha256: str
    non_target_input_sha256: str
    obligation_id: str
    attention_decision_ref: str
    attention_allocation_ref: str
    target_ref: str
    hypothesis_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    plans: tuple[PredictionFailureTrialSimulationPlan, ...] = Field(
        min_length=3,
        max_length=3,
    )
    plan_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    total_requested_budget: float = Field(gt=0.0)
    plan_package_materialized: bool = True
    target_visibility_only_difference_required: bool = True
    separate_pristine_ledgers_required: bool = True
    prediction_operator_required: bool = True
    prediction_operator_materialized: bool = False
    counterfactual_runtime_plans_materialized: bool = False
    runner_implemented: bool = False
    plans_executed: bool = False
    traces_observed: bool = False
    predicted_harm_observed: bool = False
    outcomes_observed: bool = False
    target_specific_effect_observed: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        kernel: VerdantKernel,
        preregistration: PredictionFailureTrialPreregistrationEnvelope,
    ) -> "PredictionFailureTrialPlanBundle":
        preregistration = (
            PredictionFailureTrialPreregistrationEnvelope.model_validate(
                preregistration.model_dump(mode="json")
            )
        )
        declaration = preregistration.declaration
        proposal = _canonical_proposal(kernel, preregistration)
        projections = tuple(
            PredictionFailureSimulationInputProjection.build(
                proposal=proposal,
                declaration_ref=declaration.declaration_id,
                target_ref=declaration.target_ref,
                arm=arm,
            )
            for arm in declaration.arms
        )
        plans = tuple(
            PredictionFailureTrialSimulationPlan.build(
                preregistration=preregistration,
                arm=arm,
                projection=projection,
            )
            for arm, projection in zip(
                declaration.arms,
                projections,
                strict=True,
            )
        )
        receipt = declaration.hypothesis_bundle.evidence_receipt
        hypothesis_refs = tuple(
            sorted(
                item.hypothesis_id
                for item in declaration.hypothesis_bundle.hypotheses
            )
        )
        values = {
            "plan_version": PREDICTION_FAILURE_TRIAL_PLAN_VERSION,
            "preregistration": preregistration,
            "preregistration_declaration_ref": declaration.declaration_id,
            "preregistration_sha256": _sha_bytes(
                prediction_failure_trial_preregistration_bytes(preregistration)
            ),
            "canonical_kernel_id": declaration.canonical_kernel_id,
            "canonical_fingerprint": declaration.canonical_fingerprint,
            "canonical_cycle": declaration.canonical_cycle,
            "canonical_proposal_ref": proposal.proposal_id,
            "canonical_proposal_sha256": _digest(
                proposal.model_dump(mode="json")
            ),
            "non_target_input_sha256": _digest(
                _proposal_non_target_payload(proposal)
            ),
            "obligation_id": declaration.hypothesis_bundle.obligation_id,
            "attention_decision_ref": (
                declaration.hypothesis_bundle.attention_decision_ref
            ),
            "attention_allocation_ref": (
                declaration.hypothesis_bundle.attention_allocation_ref
            ),
            "target_ref": declaration.target_ref,
            "hypothesis_refs": hypothesis_refs,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "plans": plans,
            "plan_refs": tuple(item.plan_id for item in plans),
            "total_requested_budget": sum(
                item.requested_budget for item in plans
            ),
            "plan_package_materialized": True,
            "target_visibility_only_difference_required": True,
            "separate_pristine_ledgers_required": True,
            "prediction_operator_required": True,
            "prediction_operator_materialized": False,
            "counterfactual_runtime_plans_materialized": False,
            "runner_implemented": False,
            "plans_executed": False,
            "traces_observed": False,
            "predicted_harm_observed": False,
            "outcomes_observed": False,
            "target_specific_effect_observed": False,
            "causal_attribution_enabled": False,
            "resolution_authority_enabled": False,
            "promotion_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["plan_bundle_id"] = stable_id(
            "prediction_failure_trial_plan_bundle", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_plan_bundle(self) -> "PredictionFailureTrialPlanBundle":
        declaration = self.preregistration.declaration
        receipt = declaration.hypothesis_bundle.evidence_receipt
        expected_hypotheses = tuple(
            sorted(
                item.hypothesis_id
                for item in declaration.hypothesis_bundle.hypotheses
            )
        )
        if (
            self.plan_version != PREDICTION_FAILURE_TRIAL_PLAN_VERSION
            or self.preregistration_declaration_ref
            != declaration.declaration_id
            or self.preregistration_sha256
            != _sha_bytes(
                prediction_failure_trial_preregistration_bytes(
                    self.preregistration
                )
            )
            or self.canonical_kernel_id != declaration.canonical_kernel_id
            or self.canonical_fingerprint != declaration.canonical_fingerprint
            or self.canonical_cycle != declaration.canonical_cycle
            or self.canonical_proposal_ref != receipt.proposal_ref
            or self.canonical_proposal_sha256
            != receipt.ablation_target.proposal_snapshot_sha256
            or self.obligation_id != declaration.hypothesis_bundle.obligation_id
            or self.attention_decision_ref
            != declaration.hypothesis_bundle.attention_decision_ref
            or self.attention_allocation_ref
            != declaration.hypothesis_bundle.attention_allocation_ref
            or self.target_ref != declaration.target_ref
            or self.hypothesis_refs != expected_hypotheses
            or self.protected_evidence_refs != receipt.protected_evidence_refs
            or tuple(item.arm for item in self.plans)
            != PREDICTION_FAILURE_TRIAL_ARM_ORDER
            or self.plan_refs != tuple(item.plan_id for item in self.plans)
            or self.total_requested_budget
            != sum(item.requested_budget for item in self.plans)
            or self.total_requested_budget
            != declaration.outcome_policy.total_budget
            or self.total_requested_budget > receipt.authorized_budget + 1e-12
        ):
            raise ValueError(
                "PredictionFailure plan package changed frozen preregistration."
            )
        if (
            {item.input_projection.non_target_input_sha256 for item in self.plans}
            != {self.non_target_input_sha256}
            or {item.input_projection.canonical_proposal_sha256 for item in self.plans}
            != {self.canonical_proposal_sha256}
            or {item.shared_design_seed for item in self.plans}
            != {declaration.shared_design_seed}
        ):
            raise ValueError(
                "PredictionFailure plans changed a matched-control constant."
            )
        expected_by_arm = {
            item.arm: item for item in declaration.arms
        }
        for plan in self.plans:
            arm = expected_by_arm[plan.arm]
            expected_plan = PredictionFailureTrialSimulationPlan.build(
                preregistration=self.preregistration,
                arm=arm,
                projection=plan.input_projection,
            )
            expected_refs = tuple(
                sorted(
                    {
                        declaration.declaration_id,
                        arm.arm_id,
                        plan.input_projection.projection_id,
                        *declaration.held_constant_refs,
                    }
                )
            )
            if (
                plan.preregistration_arm_ref != arm.arm_id
                or plan.requested_budget != arm.requested_budget
                or plan.maximum_consumed_budget != arm.requested_budget
                or plan.hypothesis_refs != expected_hypotheses
                or plan.protected_evidence_refs
                != receipt.protected_evidence_refs
                or plan.result_refs != expected_refs
                or plan != expected_plan
            ):
                raise ValueError(
                    "PredictionFailure plan lost arm or evidence lineage."
                )
        projections = {
            item.arm: item.input_projection for item in self.plans
        }
        baseline = projections[PredictionFailureTrialArm.BASELINE]
        ablation = projections[PredictionFailureTrialArm.TARGET_ABLATION]
        valid_null = projections[PredictionFailureTrialArm.VALID_NULL]
        if (
            baseline.declared_harm_risk is None
            or valid_null.declared_harm_risk != baseline.declared_harm_risk
            or ablation.declared_harm_risk is not None
        ):
            raise ValueError(
                "PredictionFailure target visibility changed its frozen modes."
            )
        if (
            not self.plan_package_materialized
            or not self.target_visibility_only_difference_required
            or not self.separate_pristine_ledgers_required
            or not self.prediction_operator_required
            or self.prediction_operator_materialized
            or self.counterfactual_runtime_plans_materialized
            or self.runner_implemented
            or self.plans_executed
            or self.traces_observed
            or self.predicted_harm_observed
            or self.outcomes_observed
            or self.target_specific_effect_observed
            or self.causal_attribution_enabled
            or self.resolution_authority_enabled
            or self.promotion_authority_enabled
            or self.policy_rewrite_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "PredictionFailure plan package crossed its claim boundary."
            )
        expected = stable_id(
            "prediction_failure_trial_plan_bundle",
            self.model_dump(mode="json", exclude={"plan_bundle_id"}),
        )
        if self.plan_bundle_id != expected:
            raise ValueError("PredictionFailure plan-bundle checksum mismatch.")
        return self


class PredictionFailureTrialPlanEnvelope(BaseModel):
    """Canonical immutable bytes pairing the plan package to its ``.vfp``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = PREDICTION_FAILURE_TRIAL_PLAN_FORMAT
    plan_bundle: PredictionFailureTrialPlanBundle
    plan_bundle_sha256: str

    @classmethod
    def build(
        cls,
        plan_bundle: PredictionFailureTrialPlanBundle,
    ) -> "PredictionFailureTrialPlanEnvelope":
        frozen = PredictionFailureTrialPlanBundle.model_validate(
            plan_bundle.model_dump(mode="json")
        )
        return cls(
            plan_bundle=frozen,
            plan_bundle_sha256=_digest(frozen.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "PredictionFailureTrialPlanEnvelope":
        if (
            self.sidecar_format != PREDICTION_FAILURE_TRIAL_PLAN_FORMAT
            or self.plan_bundle_sha256
            != _digest(self.plan_bundle.model_dump(mode="json"))
        ):
            raise ValueError("PredictionFailure plan sidecar digest mismatch.")
        return self


def _validate_plan_bundle(
    plan_bundle: PredictionFailureTrialPlanBundle,
    *,
    kernel: VerdantKernel,
    preregistration: PredictionFailureTrialPreregistrationEnvelope,
) -> PredictionFailureTrialPlanBundle:
    if plan_bundle.preregistration != preregistration:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan package cites another preregistration."
        )
    if (
        plan_bundle.canonical_kernel_id != kernel.state.identity.kernel_id
        or plan_bundle.canonical_fingerprint != kernel.fingerprint()
        or plan_bundle.canonical_cycle != kernel.state.cycle
    ):
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan package belongs to another canonical checkpoint."
        )
    try:
        expected = PredictionFailureTrialPlanBundle.build(
            kernel=kernel,
            preregistration=preregistration,
        )
    except (ValueError, RuntimeError) as exc:
        raise PredictionFailureTrialPlanIntegrityError(str(exc)) from exc
    if plan_bundle != expected:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan package does not match canonical provenance."
        )
    return expected


def _load_preregistration(
    path: str | Path,
    *,
    kernel: VerdantKernel,
) -> PredictionFailureTrialPreregistrationEnvelope:
    try:
        return load_prediction_failure_trial_preregistration(
            path,
            kernel=kernel,
        )
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan package requires its exact durable "
            "preregistration."
        ) from exc


def prediction_failure_trial_plan_bytes(
    envelope: PredictionFailureTrialPlanEnvelope,
) -> bytes:
    validated = PredictionFailureTrialPlanEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan sidecar exceeds its size limit."
        )
    return data


def read_prediction_failure_trial_plan(
    path: str | Path,
) -> PredictionFailureTrialPlanEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure plan sidecar exceeds its size limit."
            )
        envelope = PredictionFailureTrialPlanEnvelope.model_validate_json(data)
        if prediction_failure_trial_plan_bytes(envelope) != data:
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure plan sidecar is not canonical."
            )
        return envelope
    except PredictionFailureTrialPlanIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise PredictionFailureTrialPlanIntegrityError(
            "Invalid PredictionFailure trial plan sidecar."
        ) from exc


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise PredictionFailureTrialPlanIntegrityError(
            "PredictionFailure plan sidecar requires POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise PredictionFailureTrialPlanIntegrityError(
                "PredictionFailure plan path already contains different evidence."
            )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            temporary = None
            directory_fd = os.open(
                path.parent,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def save_prediction_failure_trial_plan(
    path: str | Path,
    envelope: PredictionFailureTrialPlanEnvelope,
    *,
    kernel: VerdantKernel,
    preregistration_path: str | Path,
) -> str:
    preregistration = _load_preregistration(
        preregistration_path,
        kernel=kernel,
    )
    validated = PredictionFailureTrialPlanEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _validate_plan_bundle(
        validated.plan_bundle,
        kernel=kernel,
        preregistration=preregistration,
    )
    _write_immutable(
        path=Path(path),
        data=prediction_failure_trial_plan_bytes(validated),
    )
    return validated.plan_bundle.plan_bundle_id


def load_prediction_failure_trial_plan(
    path: str | Path,
    *,
    kernel: VerdantKernel,
    preregistration_path: str | Path,
) -> PredictionFailureTrialPlanEnvelope:
    preregistration = _load_preregistration(
        preregistration_path,
        kernel=kernel,
    )
    envelope = read_prediction_failure_trial_plan(path)
    _validate_plan_bundle(
        envelope.plan_bundle,
        kernel=kernel,
        preregistration=preregistration,
    )
    return envelope


class PredictionFailureTrialPlanMaterializer:
    """Publish typed future arm plans without constructing or running them."""

    def materialize(
        self,
        path: str | Path,
        *,
        kernel: VerdantKernel,
        preregistration_path: str | Path,
    ) -> PredictionFailureTrialPlanEnvelope:
        canonical_before = kernel.fingerprint()
        preregistration_before = Path(preregistration_path).read_bytes()
        try:
            preregistration = _load_preregistration(
                preregistration_path,
                kernel=kernel,
            )
            plan_bundle = PredictionFailureTrialPlanBundle.build(
                kernel=kernel,
                preregistration=preregistration,
            )
            envelope = PredictionFailureTrialPlanEnvelope.build(plan_bundle)
            save_prediction_failure_trial_plan(
                path,
                envelope,
                kernel=kernel,
                preregistration_path=preregistration_path,
            )
            loaded = load_prediction_failure_trial_plan(
                path,
                kernel=kernel,
                preregistration_path=preregistration_path,
            )
            if loaded != envelope:
                raise PredictionFailureTrialPlanIntegrityError(
                    "Persisted PredictionFailure plan package changed its bytes."
                )
            return loaded
        except PredictionFailureTrialPlanIntegrityError:
            raise
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            raise PredictionFailureTrialPlanIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "PredictionFailure plan materialization mutated canonical state."
                )
            if Path(preregistration_path).read_bytes() != preregistration_before:
                raise RuntimeError(
                    "PredictionFailure plan materialization mutated preregistration."
                )
