"""Native workspace-admission probes for controlled counterfactual trials.

The overlay operational probe can retrieve canonical evidence through an
actually materialized counterfactual relation.  This module takes the next
deliberately narrow step: it submits exactly those retrieved evidence records
to Verdant's native ``VerdantWorkspacePipeline`` on an isolated kernel clone.

The clone executes a real workspace cycle under the predeclared slot cap.  No
workspace item, cycle, transition, or policy change is published to the
canonical kernel.  The resulting receipts therefore establish only a bounded
shadow admission signature.  They do not establish an outgoing action, an
executed canonical dependency path, an observed world outcome, or resolution.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    WorkspaceAdmissionReport,
    WorkspaceCandidateInput,
    WorkspaceCycleEvent,
    WorkspaceDisposition,
    WorkspacePolicy,
    WorkspaceSignals,
    WorkspaceSourceKind,
    VerdantKernel,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id
from verdant_workspace import VerdantWorkspacePipeline

from .counterfactual import (
    CounterfactualPlan,
    CounterfactualRunResult,
    SimulationIntegrityError,
    SimulationLedger,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError
from .hypotheses import StructuralHypothesis
from .operational_probe import OperationalProbeArm
from .trial_controls import (
    ControlledOperationalTrialObservation,
    ControlledOperationalTrialObserver,
    HeldOutOperationalReplicationReceipt,
    OperationalTrialControlIntegrityError,
    OperationalTrialContext,
    OperationalTrialSplit,
)


NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION = (
    "native_workspace_admission_probe_v0.29"
)
HELD_OUT_WORKSPACE_ADMISSION_REPLICATION_VERSION = (
    "held_out_workspace_admission_replication_v0.29"
)


class WorkspaceAdmissionProbeIntegrityError(RuntimeError):
    """Raised when a workspace receipt cannot be rederived from its lineage."""


class WorkspaceAdmissionEffect(str, Enum):
    ADMISSION_GAIN = "admission_gain"
    VALID_NULL = "valid_null"
    ADMISSION_LOSS = "admission_loss"
    ADMISSION_CHANGED = "admission_changed"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _identity_payload(values: dict[str, Any], identity_field: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if key == identity_field:
            continue
        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, Enum):
            payload[key] = value.value
        elif isinstance(value, tuple):
            payload[key] = tuple(
                item.model_dump(mode="json")
                if isinstance(item, BaseModel)
                else item.value
                if isinstance(item, Enum)
                else item
                for item in value
            )
        else:
            payload[key] = value
    return payload


class NativeWorkspaceAdmissionProbePolicy(BaseModel):
    """Visible mapping from retrieved evidence to native workspace inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION
    candidate_resource_fraction: float = Field(default=0.10, gt=0.0, le=1.0)
    relevance_signal: float = Field(default=1.0, ge=0.0, le=1.0)
    persistence_cycles: int = Field(default=1, ge=1, le=4)

    @model_validator(mode="after")
    def validate_policy(self) -> "NativeWorkspaceAdmissionProbePolicy":
        if self.policy_version != NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION:
            raise ValueError("Unsupported native workspace-admission probe version.")
        if self.persistence_cycles != 1:
            raise ValueError(
                "The v0.29 workspace probe supports one-cycle candidates only."
            )
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


def _probe_assessments(
    report: WorkspaceAdmissionReport,
) -> tuple[Any, ...]:
    return tuple(
        item
        for item in report.assessments
        if item.candidate.metadata.get("workspace_probe_version")
        == NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION
    )


def _assessment_signature(
    *,
    policy_sha256: str,
    declared_slot_budget: int,
    assessments: Sequence[Any],
) -> str:
    rows = tuple(
        sorted(
            (
                item.candidate.source_ref,
                item.disposition.value,
                item.raw_score,
                item.effective_score,
                item.allocated_resource,
                item.rejection_codes,
            )
            for item in assessments
        )
    )
    return stable_id(
        "native_workspace_admission_assessment_signature",
        NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION,
        policy_sha256,
        declared_slot_budget,
        rows,
    )


class WorkspaceAdmissionArmObservation(FrozenRecord):
    """One controlled arm replayed through a real isolated workspace cycle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    policy_version: str = NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION
    policy_sha256: str
    arm: OperationalProbeArm
    context: OperationalTrialContext
    controlled_trial_ref: str
    operational_probe_ref: str
    plan_id: str
    settlement_id: str
    canonical_checkpoint_fingerprint: str
    canonical_workspace_max_active_items: int = Field(ge=1)
    declared_slot_budget: int = Field(ge=1)
    workspace_policy_sha256: str
    candidate_resource_request: float = Field(gt=0.0)
    submitted_retrieved_evidence_refs: tuple[str, ...] = ()
    admitted_retrieved_evidence_refs: tuple[str, ...] = ()
    suppressed_retrieved_evidence_refs: tuple[str, ...] = ()
    assessment_signature: str
    shadow_input_fingerprint: str
    admission_report: WorkspaceAdmissionReport
    workspace_event: WorkspaceCycleEvent
    shadow_output_fingerprint: str
    native_workspace_pipeline_executed: bool = True
    declared_slot_budget_enforced: bool = True
    native_workspace_admission_observed: bool
    shadow_execution_only: bool = True
    semantic_records_preserved: bool = True
    canonical_workspace_mutated: bool = False
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "WorkspaceAdmissionArmObservation":
        for key in (
            "submitted_retrieved_evidence_refs",
            "admitted_retrieved_evidence_refs",
            "suppressed_retrieved_evidence_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        values.setdefault("policy_version", NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION)
        values.setdefault("native_workspace_pipeline_executed", True)
        values.setdefault("declared_slot_budget_enforced", True)
        values.setdefault(
            "native_workspace_admission_observed",
            bool(values["admitted_retrieved_evidence_refs"]),
        )
        values.setdefault("shadow_execution_only", True)
        values.setdefault("semantic_records_preserved", True)
        values.setdefault("canonical_workspace_mutated", False)
        values.setdefault("outgoing_action_observed", False)
        values.setdefault("canonical_dependency_path_established", False)
        values.setdefault("observed_outcome_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        values["observation_id"] = stable_id(
            "workspace_admission_arm_observation",
            _identity_payload(values, "observation_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "WorkspaceAdmissionArmObservation":
        if self.policy_version != NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION:
            raise ValueError("Unsupported native workspace-admission observation.")
        identifiers = (
            self.controlled_trial_ref,
            self.operational_probe_ref,
            self.plan_id,
            self.settlement_id,
            self.assessment_signature,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Workspace-admission lineage cannot be empty.")
        for digest in (
            self.policy_sha256,
            self.canonical_checkpoint_fingerprint,
            self.workspace_policy_sha256,
            self.shadow_input_fingerprint,
            self.shadow_output_fingerprint,
        ):
            if not _is_sha256(digest):
                raise ValueError("Workspace-admission fingerprints must be SHA-256.")
        for refs, label in (
            (self.submitted_retrieved_evidence_refs, "submitted evidence"),
            (self.admitted_retrieved_evidence_refs, "admitted evidence"),
            (self.suppressed_retrieved_evidence_refs, "suppressed evidence"),
        ):
            if refs != tuple(sorted(set(refs))):
                raise ValueError(
                    f"Workspace-admission {label} must be sorted and unique."
                )
        submitted = set(self.submitted_retrieved_evidence_refs)
        admitted = set(self.admitted_retrieved_evidence_refs)
        suppressed = set(self.suppressed_retrieved_evidence_refs)
        if admitted & suppressed or admitted | suppressed != submitted:
            raise ValueError(
                "Workspace-admission dispositions do not cover submitted evidence."
            )
        if self.native_workspace_admission_observed != bool(admitted):
            raise ValueError("Workspace admission claim differs from the native report.")
        if self.declared_slot_budget > self.canonical_workspace_max_active_items:
            raise ValueError("Shadow workspace slot cap relaxed canonical policy.")
        if self.context.canonical_checkpoint_fingerprint != (
            self.canonical_checkpoint_fingerprint
        ):
            raise ValueError("Workspace-admission context crossed its checkpoint.")
        if self.context.slot_budget != self.declared_slot_budget:
            raise ValueError("Workspace admission did not enforce its declared slot cap.")
        if self.workspace_event.report != self.admission_report:
            raise ValueError("Workspace event lost its native admission report.")
        if self.workspace_event.semantic_mutation_permitted:
            raise ValueError("Workspace probe event acquired semantic authority.")
        if len(self.workspace_event.active_item_ids) > self.declared_slot_budget:
            raise ValueError("Workspace event exceeded its declared slot cap.")
        assessments = _probe_assessments(self.admission_report)
        if len(assessments) != len(self.submitted_retrieved_evidence_refs):
            raise ValueError("Workspace report lost a submitted retrieval candidate.")
        assessment_refs = tuple(
            sorted(item.candidate.source_ref for item in assessments)
        )
        if assessment_refs != self.submitted_retrieved_evidence_refs:
            raise ValueError("Workspace report substituted a retrieval candidate.")
        expected_admitted = tuple(
            sorted(
                item.candidate.source_ref
                for item in assessments
                if item.disposition == WorkspaceDisposition.ADMIT
            )
        )
        expected_suppressed = tuple(
            sorted(
                item.candidate.source_ref
                for item in assessments
                if item.disposition != WorkspaceDisposition.ADMIT
            )
        )
        if (
            self.admitted_retrieved_evidence_refs != expected_admitted
            or self.suppressed_retrieved_evidence_refs != expected_suppressed
        ):
            raise ValueError("Workspace-admission evidence index was altered.")
        for item in assessments:
            candidate = item.candidate
            expected_metadata = {
                "workspace_probe_version": self.policy_version,
                "context_ref": self.context.context_id,
                "controlled_trial_ref": self.controlled_trial_ref,
                "operational_probe_ref": self.operational_probe_ref,
                "arm": self.arm.value,
                "plan_id": self.plan_id,
                "settlement_id": self.settlement_id,
            }
            if (
                candidate.source_kind != WorkspaceSourceKind.RECALLED_EVIDENCE
                or candidate.evidence_refs != (candidate.source_ref,)
                or candidate.operation is not None
                or candidate.binding_refs
                or candidate.persistence_cycles != 1
                or abs(
                    candidate.resource_request - self.candidate_resource_request
                )
                > 1e-12
                or candidate.metadata != expected_metadata
            ):
                raise ValueError("Workspace probe candidate escaped its native mapping.")
        expected_signature = _assessment_signature(
            policy_sha256=self.policy_sha256,
            declared_slot_budget=self.declared_slot_budget,
            assessments=assessments,
        )
        if self.assessment_signature != expected_signature:
            raise ValueError("Workspace-admission assessment signature was altered.")
        if (
            not self.native_workspace_pipeline_executed
            or not self.declared_slot_budget_enforced
            or not self.shadow_execution_only
            or not self.semantic_records_preserved
            or self.canonical_workspace_mutated
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Workspace-admission observation crossed its authority boundary.")
        expected = stable_id(
            "workspace_admission_arm_observation",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Workspace-admission observation checksum mismatch.")
        return self


class MatchedWorkspaceAdmissionObservation(FrozenRecord):
    """Matched native workspace behavior for one controlled zero/full pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    policy_version: str = NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION
    controlled_trial_ref: str
    context: OperationalTrialContext
    baseline: WorkspaceAdmissionArmObservation
    treatment: WorkspaceAdmissionArmObservation
    effect: WorkspaceAdmissionEffect
    newly_admitted_evidence_refs: tuple[str, ...] = ()
    lost_admitted_evidence_refs: tuple[str, ...] = ()
    workspace_effect_signature: str
    matched_control_verified: bool = True
    native_workspace_pipeline_executed: bool = True
    declared_slot_budget_enforced: bool = True
    deterministic_shadow_only: bool = True
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @staticmethod
    def _effect(
        baseline: WorkspaceAdmissionArmObservation,
        treatment: WorkspaceAdmissionArmObservation,
    ) -> tuple[WorkspaceAdmissionEffect, tuple[str, ...], tuple[str, ...]]:
        baseline_refs = set(baseline.admitted_retrieved_evidence_refs)
        treatment_refs = set(treatment.admitted_retrieved_evidence_refs)
        gained = tuple(sorted(treatment_refs - baseline_refs))
        lost = tuple(sorted(baseline_refs - treatment_refs))
        if gained and not lost:
            effect = WorkspaceAdmissionEffect.ADMISSION_GAIN
        elif not gained and not lost:
            effect = WorkspaceAdmissionEffect.VALID_NULL
        elif lost and not gained:
            effect = WorkspaceAdmissionEffect.ADMISSION_LOSS
        else:
            effect = WorkspaceAdmissionEffect.ADMISSION_CHANGED
        return effect, gained, lost

    @classmethod
    def build(
        cls,
        *,
        controlled_trial_ref: str,
        context: OperationalTrialContext,
        baseline: WorkspaceAdmissionArmObservation,
        treatment: WorkspaceAdmissionArmObservation,
    ) -> "MatchedWorkspaceAdmissionObservation":
        effect, gained, lost = cls._effect(baseline, treatment)
        effect_signature = stable_id(
            "matched_workspace_admission_effect",
            NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION,
            baseline.policy_sha256,
            context.horizon,
            context.slot_budget,
            effect.value,
            gained,
            lost,
            baseline.assessment_signature,
            treatment.assessment_signature,
        )
        values = {
            "policy_version": NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION,
            "controlled_trial_ref": controlled_trial_ref,
            "context": context,
            "baseline": baseline,
            "treatment": treatment,
            "effect": effect,
            "newly_admitted_evidence_refs": gained,
            "lost_admitted_evidence_refs": lost,
            "workspace_effect_signature": effect_signature,
            "matched_control_verified": True,
            "native_workspace_pipeline_executed": True,
            "declared_slot_budget_enforced": True,
            "deterministic_shadow_only": True,
            "outgoing_action_observed": False,
            "canonical_dependency_path_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["match_id"] = stable_id(
            "matched_workspace_admission_observation",
            _identity_payload(values, "match_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_match(self) -> "MatchedWorkspaceAdmissionObservation":
        if self.policy_version != NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION:
            raise ValueError("Unsupported matched workspace-admission version.")
        if not self.controlled_trial_ref.strip():
            raise ValueError("Matched workspace admission requires trial lineage.")
        if (
            self.baseline.arm != OperationalProbeArm.BASELINE
            or self.treatment.arm != OperationalProbeArm.TREATMENT
            or self.baseline.context != self.context
            or self.treatment.context != self.context
            or self.baseline.controlled_trial_ref != self.controlled_trial_ref
            or self.treatment.controlled_trial_ref != self.controlled_trial_ref
            or self.baseline.policy_sha256 != self.treatment.policy_sha256
            or self.baseline.canonical_checkpoint_fingerprint
            != self.treatment.canonical_checkpoint_fingerprint
            or self.baseline.declared_slot_budget
            != self.treatment.declared_slot_budget
        ):
            raise ValueError("Workspace-admission controls are not matched.")
        effect, gained, lost = self._effect(self.baseline, self.treatment)
        expected_signature = stable_id(
            "matched_workspace_admission_effect",
            NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION,
            self.baseline.policy_sha256,
            self.context.horizon,
            self.context.slot_budget,
            effect.value,
            gained,
            lost,
            self.baseline.assessment_signature,
            self.treatment.assessment_signature,
        )
        if (
            self.effect != effect
            or self.newly_admitted_evidence_refs != gained
            or self.lost_admitted_evidence_refs != lost
            or self.workspace_effect_signature != expected_signature
        ):
            raise ValueError("Matched workspace-admission effect was altered.")
        if (
            not self.matched_control_verified
            or not self.native_workspace_pipeline_executed
            or not self.declared_slot_budget_enforced
            or not self.deterministic_shadow_only
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Matched workspace admission crossed its authority boundary.")
        expected = stable_id(
            "matched_workspace_admission_observation",
            self.model_dump(mode="json", exclude={"match_id"}),
        )
        if self.match_id != expected:
            raise ValueError("Matched workspace-admission checksum mismatch.")
        return self


class HeldOutWorkspaceAdmissionReplicationReceipt(FrozenRecord):
    """Exact workspace-effect replay across calibration and held-out trials."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    policy_version: str = HELD_OUT_WORKSPACE_ADMISSION_REPLICATION_VERSION
    operational_replication_ref: str
    observations: tuple[MatchedWorkspaceAdmissionObservation, ...] = Field(
        min_length=2
    )
    calibration_match_ref: str
    held_out_match_refs: tuple[str, ...] = Field(min_length=1)
    seeds: tuple[int, ...] = Field(min_length=2)
    workspace_effect_signature: str
    declared_seed_replay_observed: bool = True
    native_workspace_admission_observed: bool
    declared_slot_budget_enforced: bool = True
    stochastic_generalization_established: bool = False
    canonical_workspace_commit_performed: bool = False
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        operational_replication_ref: str,
        observations: Sequence[MatchedWorkspaceAdmissionObservation],
    ) -> "HeldOutWorkspaceAdmissionReplicationReceipt":
        normalized = tuple(
            MatchedWorkspaceAdmissionObservation.model_validate(
                item.model_dump(mode="json")
            )
            for item in observations
        )
        normalized = tuple(
            sorted(
                normalized,
                key=lambda item: (
                    0
                    if item.context.split == OperationalTrialSplit.CALIBRATION
                    else 1,
                    item.context.seed,
                    item.match_id,
                ),
            )
        )
        calibration = tuple(
            item
            for item in normalized
            if item.context.split == OperationalTrialSplit.CALIBRATION
        )
        held_out = tuple(
            item
            for item in normalized
            if item.context.split == OperationalTrialSplit.HELD_OUT
        )
        if len(calibration) != 1 or not held_out:
            raise ValueError(
                "Workspace replication requires one calibration and held-out trial."
            )
        values = {
            "policy_version": HELD_OUT_WORKSPACE_ADMISSION_REPLICATION_VERSION,
            "operational_replication_ref": operational_replication_ref,
            "observations": normalized,
            "calibration_match_ref": calibration[0].match_id,
            "held_out_match_refs": tuple(item.match_id for item in held_out),
            "seeds": tuple(item.context.seed for item in normalized),
            "workspace_effect_signature": normalized[0].workspace_effect_signature,
            "declared_seed_replay_observed": True,
            "native_workspace_admission_observed": any(
                item.baseline.native_workspace_admission_observed
                or item.treatment.native_workspace_admission_observed
                for item in normalized
            ),
            "declared_slot_budget_enforced": True,
            "stochastic_generalization_established": False,
            "canonical_workspace_commit_performed": False,
            "outgoing_action_observed": False,
            "canonical_dependency_path_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "held_out_workspace_admission_replication_receipt",
            _identity_payload(values, "receipt_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "HeldOutWorkspaceAdmissionReplicationReceipt":
        if self.policy_version != HELD_OUT_WORKSPACE_ADMISSION_REPLICATION_VERSION:
            raise ValueError("Unsupported workspace-admission replication version.")
        if not self.operational_replication_ref.strip():
            raise ValueError("Workspace replication requires operational lineage.")
        expected_order = tuple(
            sorted(
                self.observations,
                key=lambda item: (
                    0
                    if item.context.split == OperationalTrialSplit.CALIBRATION
                    else 1,
                    item.context.seed,
                    item.match_id,
                ),
            )
        )
        if self.observations != expected_order:
            raise ValueError("Workspace-admission observations are not canonicalized.")
        calibration = tuple(
            item
            for item in self.observations
            if item.context.split == OperationalTrialSplit.CALIBRATION
        )
        held_out = tuple(
            item
            for item in self.observations
            if item.context.split == OperationalTrialSplit.HELD_OUT
        )
        if len(calibration) != 1 or not held_out:
            raise ValueError(
                "Workspace replication requires one calibration and held-out trial."
            )
        if (
            self.calibration_match_ref != calibration[0].match_id
            or self.held_out_match_refs
            != tuple(item.match_id for item in held_out)
        ):
            raise ValueError("Workspace replication split lineage was altered.")
        expected_seeds = tuple(item.context.seed for item in self.observations)
        if self.seeds != expected_seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Workspace replication requires distinct declared seeds.")
        shared_controls = {
            (
                item.context.policy_version,
                item.context.obligation_id,
                item.context.hypothesis_ref,
                item.context.canonical_checkpoint_fingerprint,
                item.context.horizon,
                item.context.slot_budget,
                item.context.lens_binding_id,
                item.context.lens_definition_id,
                item.context.lens_policy_version,
                item.context.lens_state_fingerprint,
                item.baseline.policy_sha256,
            )
            for item in self.observations
        }
        if len(shared_controls) != 1:
            raise ValueError("Workspace-admission replication controls are not matched.")
        if any(
            item.workspace_effect_signature != self.workspace_effect_signature
            for item in self.observations
        ):
            raise ValueError("Held-out native workspace effect did not replicate.")
        expected_admission = any(
            item.baseline.native_workspace_admission_observed
            or item.treatment.native_workspace_admission_observed
            for item in self.observations
        )
        if self.native_workspace_admission_observed != expected_admission:
            raise ValueError("Workspace replication admission claim was altered.")
        if (
            not self.declared_seed_replay_observed
            or not self.declared_slot_budget_enforced
            or self.stochastic_generalization_established
            or self.canonical_workspace_commit_performed
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Workspace replication crossed its authority boundary.")
        expected = stable_id(
            "held_out_workspace_admission_replication_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected:
            raise ValueError("Workspace-admission replication checksum mismatch.")
        return self


class NativeWorkspaceAdmissionObserver:
    """Replay controlled retrievals through isolated native workspace cycles."""

    def __init__(
        self,
        policy: NativeWorkspaceAdmissionProbePolicy | None = None,
    ) -> None:
        self.policy = policy or NativeWorkspaceAdmissionProbePolicy()

    @staticmethod
    def _semantic_fingerprint(kernel: VerdantKernel) -> str:
        mappings = {
            "evidence": kernel.state.evidence,
            "concepts": kernel.state.concepts,
            "relations": kernel.state.relations,
            "claims": kernel.state.claims,
            "contradictions": kernel.state.contradictions,
            "structures": kernel.state.structures,
            "layered_structures": kernel.state.layered_structures,
            "obligation_kernels": kernel.state.obligation_kernels,
        }
        return _digest(
            {
                **{
                    name: {
                        key: value.model_dump(mode="json")
                        for key, value in sorted(collection.items())
                    }
                    for name, collection in mappings.items()
                },
                "obligation_history": tuple(
                    item.model_dump(mode="json")
                    for item in kernel.state.obligation_history
                ),
            }
        )

    def _candidate(
        self,
        kernel: VerdantKernel,
        *,
        evidence_ref: str,
        resource_request: float,
        context: OperationalTrialContext,
        controlled_trial_ref: str,
        operational_probe_ref: str,
        arm: OperationalProbeArm,
        plan_id: str,
        settlement_id: str,
    ) -> WorkspaceCandidateInput:
        evidence = kernel.state.evidence.get(evidence_ref)
        if evidence is None:
            raise WorkspaceAdmissionProbeIntegrityError(
                "Workspace probe retrieval is not canonical evidence."
            )
        return WorkspaceCandidateInput(
            source_kind=WorkspaceSourceKind.RECALLED_EVIDENCE,
            source_ref=evidence_ref,
            label=f"controlled retrieval {evidence.kind.value}:{evidence_ref}",
            evidence_refs=(evidence_ref,),
            resource_request=resource_request,
            persistence_cycles=self.policy.persistence_cycles,
            signals=WorkspaceSignals(
                evidence_grounding=evidence.confidence,
                relevance=self.policy.relevance_signal,
                prediction_error=0.0,
                contradiction_pressure=0.0,
                action_value=0.0,
                ethical_salience=0.0,
                novelty=0.0,
                resonance=0.0,
            ),
            metadata={
                "workspace_probe_version": self.policy.policy_version,
                "context_ref": context.context_id,
                "controlled_trial_ref": controlled_trial_ref,
                "operational_probe_ref": operational_probe_ref,
                "arm": arm.value,
                "plan_id": plan_id,
                "settlement_id": settlement_id,
            },
        )

    def _run_arm(
        self,
        kernel: VerdantKernel,
        *,
        context: OperationalTrialContext,
        controlled_trial_ref: str,
        arm_observation: Any,
        arm: OperationalProbeArm,
    ) -> WorkspaceAdmissionArmObservation:
        canonical_policy = kernel.state.workspace_policy
        if context.slot_budget > canonical_policy.max_active_items:
            raise WorkspaceAdmissionProbeIntegrityError(
                "Declared workspace slot cap cannot relax canonical policy."
            )
        shadow = VerdantKernel.from_state(kernel.snapshot())
        shadow.state.workspace_policy = WorkspacePolicy.model_validate(
            canonical_policy.model_copy(
                update={
                    "max_active_items": context.slot_budget,
                    "revision": canonical_policy.revision + 1,
                }
            ).model_dump(mode="json")
        )
        policy_sha256 = self.policy.fingerprint()
        workspace_policy_sha256 = _digest(
            shadow.state.workspace_policy.model_dump(mode="json")
        )
        resource_request = (
            shadow.state.workspace_policy.resource_budget
            * self.policy.candidate_resource_fraction
        )
        retrieved_refs = tuple(sorted(arm_observation.retrieved_evidence_refs))
        candidates = tuple(
            self._candidate(
                shadow,
                evidence_ref=evidence_ref,
                resource_request=resource_request,
                context=context,
                controlled_trial_ref=controlled_trial_ref,
                operational_probe_ref=arm_observation.observation_id,
                arm=arm,
                plan_id=arm_observation.plan_id,
                settlement_id=arm_observation.settlement_id,
            )
            for evidence_ref in retrieved_refs
        )
        semantic_before = self._semantic_fingerprint(shadow)
        shadow_input = shadow.fingerprint()
        result = VerdantWorkspacePipeline().run_cycle(shadow, candidates)
        semantic_preserved = self._semantic_fingerprint(shadow) == semantic_before
        if not semantic_preserved:
            raise WorkspaceAdmissionProbeIntegrityError(
                "Shadow workspace cycle changed semantic records."
            )
        assessments = _probe_assessments(result.report)
        admitted = tuple(
            sorted(
                item.candidate.source_ref
                for item in assessments
                if item.disposition == WorkspaceDisposition.ADMIT
            )
        )
        suppressed = tuple(
            sorted(
                item.candidate.source_ref
                for item in assessments
                if item.disposition != WorkspaceDisposition.ADMIT
            )
        )
        return WorkspaceAdmissionArmObservation.build(
            policy_sha256=policy_sha256,
            arm=arm,
            context=context,
            controlled_trial_ref=controlled_trial_ref,
            operational_probe_ref=arm_observation.observation_id,
            plan_id=arm_observation.plan_id,
            settlement_id=arm_observation.settlement_id,
            canonical_checkpoint_fingerprint=kernel.fingerprint(),
            canonical_workspace_max_active_items=canonical_policy.max_active_items,
            declared_slot_budget=context.slot_budget,
            workspace_policy_sha256=workspace_policy_sha256,
            candidate_resource_request=resource_request,
            submitted_retrieved_evidence_refs=retrieved_refs,
            admitted_retrieved_evidence_refs=admitted,
            suppressed_retrieved_evidence_refs=suppressed,
            assessment_signature=_assessment_signature(
                policy_sha256=policy_sha256,
                declared_slot_budget=context.slot_budget,
                assessments=assessments,
            ),
            shadow_input_fingerprint=shadow_input,
            admission_report=result.report,
            workspace_event=result.event,
            shadow_output_fingerprint=shadow.fingerprint(),
            semantic_records_preserved=semantic_preserved,
        )

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        lenses: EquivalenceLensSystem,
        *,
        context: OperationalTrialContext,
        hypothesis: StructuralHypothesis,
        baseline_plan: CounterfactualPlan,
        baseline_result: CounterfactualRunResult,
        treatment_plan: CounterfactualPlan,
        treatment_result: CounterfactualRunResult,
        controlled_observation: ControlledOperationalTrialObservation,
    ) -> MatchedWorkspaceAdmissionObservation:
        canonical_before = kernel.fingerprint()
        lens_before = lenses.fingerprint()
        try:
            controlled_observation = (
                ControlledOperationalTrialObservation.model_validate(
                    controlled_observation.model_dump(mode="json")
                )
            )
            verified = ControlledOperationalTrialObserver().observe(
                kernel,
                ledger,
                lenses,
                context=context,
                hypothesis=hypothesis,
                baseline_plan=baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=treatment_plan,
                treatment_result=treatment_result,
            )
            if verified != controlled_observation:
                raise WorkspaceAdmissionProbeIntegrityError(
                    "Workspace probe controlled observation differs from actual lineage."
                )
            operational = verified.operational_observation
            baseline = self._run_arm(
                kernel,
                context=context,
                controlled_trial_ref=verified.observation_id,
                arm_observation=operational.baseline,
                arm=OperationalProbeArm.BASELINE,
            )
            treatment = self._run_arm(
                kernel,
                context=context,
                controlled_trial_ref=verified.observation_id,
                arm_observation=operational.treatment,
                arm=OperationalProbeArm.TREATMENT,
            )
            if kernel.fingerprint() != canonical_before or lenses.fingerprint() != lens_before:
                raise WorkspaceAdmissionProbeIntegrityError(
                    "Workspace probe mutated canonical or Lens state."
                )
            return MatchedWorkspaceAdmissionObservation.build(
                controlled_trial_ref=verified.observation_id,
                context=context,
                baseline=baseline,
                treatment=treatment,
            )
        except WorkspaceAdmissionProbeIntegrityError:
            raise
        except (
            LensIntegrityError,
            OperationalTrialControlIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise WorkspaceAdmissionProbeIntegrityError(str(exc)) from exc


class HeldOutWorkspaceAdmissionReplicationObserver:
    """Require an exact native workspace effect across predeclared splits."""

    def observe(
        self,
        operational_replication: HeldOutOperationalReplicationReceipt,
        observations: Sequence[MatchedWorkspaceAdmissionObservation],
    ) -> HeldOutWorkspaceAdmissionReplicationReceipt:
        try:
            operational_replication = (
                HeldOutOperationalReplicationReceipt.model_validate(
                    operational_replication.model_dump(mode="json")
                )
            )
            receipt = HeldOutWorkspaceAdmissionReplicationReceipt.build(
                operational_replication_ref=operational_replication.receipt_id,
                observations=observations,
            )
            if {
                item.controlled_trial_ref for item in receipt.observations
            } != {
                item.observation_id for item in operational_replication.trials
            }:
                raise WorkspaceAdmissionProbeIntegrityError(
                    "Workspace replication lost its controlled operational trials."
                )
            if receipt.seeds != operational_replication.seeds:
                raise WorkspaceAdmissionProbeIntegrityError(
                    "Workspace replication crossed its predeclared seeds."
                )
            return receipt
        except WorkspaceAdmissionProbeIntegrityError:
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise WorkspaceAdmissionProbeIntegrityError(str(exc)) from exc
