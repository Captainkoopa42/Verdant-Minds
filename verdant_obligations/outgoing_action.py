"""Shadow outgoing-action signatures grounded in native Verdant pathways.

The v0.29 workspace observer establishes that retrieved canonical evidence can
be admitted by Verdant's native workspace on an isolated clone.  This module
takes one further, deliberately narrow step.  Admitted evidence may seed a
supplied, reversible ``INVESTIGATE`` proposal; the real Council evaluates and
commits that proposal on the same clone, and the exact authorized operation is
then submitted as a native ``AUTHORIZED_ACTION`` workspace candidate.

No operation is dispatched to an environment.  All Council decisions,
workspace items, cycles, and policy revisions remain on a discarded clone.
The receipts therefore establish only a deterministic outgoing-action
*signature*, not action execution, a dependency-path outcome, or resolution.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDecisionEvent,
    CouncilDisposition,
    CouncilProposal,
    CouncilReport,
    GovernanceIntegrityError,
    GovernanceProposalKind,
    GovernanceStaleError,
    WorkspaceAdmissionReport,
    WorkspaceCandidateInput,
    WorkspaceCycleEvent,
    WorkspaceDisposition,
    WorkspaceIntegrityError,
    WorkspacePolicy,
    WorkspaceSignals,
    WorkspaceSourceKind,
    WorkspaceStaleError,
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
    HeldOutOperationalReplicationReceipt,
    OperationalTrialControlIntegrityError,
    OperationalTrialContext,
    OperationalTrialSplit,
)
from .workspace_admission import (
    NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION,
    HeldOutWorkspaceAdmissionReplicationObserver,
    HeldOutWorkspaceAdmissionReplicationReceipt,
    MatchedWorkspaceAdmissionObservation,
    NativeWorkspaceAdmissionObserver,
    WorkspaceAdmissionArmObservation,
    WorkspaceAdmissionProbeIntegrityError,
)


NATIVE_OUTGOING_ACTION_PROBE_VERSION = "native_outgoing_action_probe_v0.30"
HELD_OUT_OUTGOING_ACTION_REPLICATION_VERSION = (
    "held_out_outgoing_action_replication_v0.30"
)


class OutgoingActionProbeIntegrityError(RuntimeError):
    """Raised when an action signature cannot be rederived from its lineage."""


class OutgoingActionDisposition(str, Enum):
    NO_ADMITTED_EVIDENCE = "no_admitted_evidence"
    AUTHORIZED_AND_ADMITTED = "authorized_and_admitted"
    AUTHORIZED_BUT_SUPPRESSED = "authorized_but_suppressed"


class OutgoingActionEffect(str, Enum):
    ACTION_GAIN = "action_gain"
    VALID_NULL = "valid_null"
    ACTION_LOSS = "action_loss"
    ACTION_CHANGED = "action_changed"


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


class NativeOutgoingActionProbePolicy(BaseModel):
    """Visible supplied mapping from admission to a reversible investigation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = NATIVE_OUTGOING_ACTION_PROBE_VERSION
    operation_namespace: str = "inspect_dependency_input"
    action_class: str = "controlled_dependency_inspection"
    description: str = (
        "Inspect admitted dependency evidence without changing canonical state."
    )
    council_requested_resource: float = Field(default=0.10, gt=0.0)
    relevance: float = Field(default=1.0, ge=0.0, le=1.0)
    urgency: float = Field(default=0.50, ge=0.0, le=1.0)
    novelty: float = Field(default=0.0, ge=0.0, le=1.0)
    predicted_information_gain: float = Field(default=1.0, ge=0.0, le=1.0)
    harm_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    reversibility: float = Field(default=1.0, ge=0.0, le=1.0)
    candidate_resource_fraction: float = Field(default=0.10, gt=0.0, le=1.0)
    action_value_signal: float = Field(default=1.0, ge=0.0, le=1.0)
    ethical_salience_signal: float = Field(default=1.0, ge=0.0, le=1.0)
    persistence_cycles: int = Field(default=1, ge=1, le=4)

    @model_validator(mode="after")
    def validate_policy(self) -> "NativeOutgoingActionProbePolicy":
        if self.policy_version != NATIVE_OUTGOING_ACTION_PROBE_VERSION:
            raise ValueError("Unsupported native outgoing-action probe version.")
        if not all(
            item.strip()
            for item in (
                self.operation_namespace,
                self.action_class,
                self.description,
            )
        ):
            raise ValueError("Outgoing-action policy text cannot be empty.")
        if self.persistence_cycles != 1:
            raise ValueError("The v0.30 action probe supports one-cycle candidates only.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))

    def operation(self, context: OperationalTrialContext) -> str:
        suffix = stable_id(
            "native_outgoing_action_operation",
            self.policy_version,
            context.obligation_id,
            context.hypothesis_ref,
        )
        return f"{self.operation_namespace}:{suffix}"


def _workspace_probe_candidates(
    observation: WorkspaceAdmissionArmObservation,
) -> tuple[WorkspaceCandidateInput, ...]:
    return tuple(
        item.candidate
        for item in observation.admission_report.assessments
        if item.candidate.metadata.get("workspace_probe_version")
        == NATIVE_WORKSPACE_ADMISSION_PROBE_VERSION
    )


def _action_assessments(report: WorkspaceAdmissionReport) -> tuple[Any, ...]:
    return tuple(
        item
        for item in report.assessments
        if item.candidate.metadata.get("outgoing_action_probe_version")
        == NATIVE_OUTGOING_ACTION_PROBE_VERSION
    )


def _action_signature(
    *,
    policy_sha256: str,
    arm: OperationalProbeArm,
    context: OperationalTrialContext,
    evidence_refs: tuple[str, ...],
    operation: str | None,
    council_report: CouncilReport | None,
    action_report: WorkspaceAdmissionReport | None,
) -> str:
    if council_report is None or action_report is None:
        council_row: Any = None
        action_row: Any = None
    else:
        council_row = (
            council_report.disposition.value,
            tuple(operation == item for item in council_report.authorized_operations),
            tuple(operation == item for item in council_report.blocked_operations),
            council_report.constraints,
            council_report.required_evidence,
            council_report.rationale_codes,
            tuple(
                (
                    item.king.value,
                    item.score,
                    item.confidence,
                    item.recommendation.value,
                    item.constraints,
                    item.rationale_codes,
                )
                for item in council_report.assessments
            ),
        )
        action_rows = _action_assessments(action_report)
        action_row = tuple(
            (
                item.disposition.value,
                item.raw_score,
                item.effective_score,
                item.allocated_resource,
                item.rejection_codes,
            )
            for item in action_rows
        )
    return stable_id(
        "native_outgoing_action_arm_signature",
        NATIVE_OUTGOING_ACTION_PROBE_VERSION,
        policy_sha256,
        arm.value,
        context.horizon,
        context.slot_budget,
        evidence_refs,
        operation,
        council_row,
        action_row,
    )


class OutgoingActionArmObservation(FrozenRecord):
    """One workspace arm replayed through Council and action admission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    policy_version: str = NATIVE_OUTGOING_ACTION_PROBE_VERSION
    policy: NativeOutgoingActionProbePolicy
    policy_sha256: str
    arm: OperationalProbeArm
    context: OperationalTrialContext
    workspace_match_ref: str
    workspace_admission: WorkspaceAdmissionArmObservation
    canonical_checkpoint_fingerprint: str
    admitted_evidence_refs: tuple[str, ...] = ()
    operation: str | None = None
    council_proposal: CouncilProposal | None = None
    council_report: CouncilReport | None = None
    council_decision: CouncilDecisionEvent | None = None
    action_workspace_report: WorkspaceAdmissionReport | None = None
    action_workspace_event: WorkspaceCycleEvent | None = None
    action_disposition: OutgoingActionDisposition
    action_signature: str
    shadow_workspace_input_fingerprint: str
    shadow_workspace_output_fingerprint: str
    action_workspace_input_fingerprint: str
    shadow_output_fingerprint: str
    native_council_evaluated: bool
    native_council_authorized: bool
    native_action_workspace_evaluated: bool
    outgoing_action_signature_observed: bool
    shadow_execution_only: bool = True
    semantic_records_preserved: bool = True
    simulation_ledger_preserved: bool = True
    lens_state_preserved: bool = True
    canonical_workspace_mutated: bool = False
    canonical_governance_mutated: bool = False
    external_action_executed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "OutgoingActionArmObservation":
        values["admitted_evidence_refs"] = tuple(
            sorted(set(values.get("admitted_evidence_refs", ())))
        )
        values.setdefault("policy_version", NATIVE_OUTGOING_ACTION_PROBE_VERSION)
        values.setdefault("shadow_execution_only", True)
        values.setdefault("semantic_records_preserved", True)
        values.setdefault("simulation_ledger_preserved", True)
        values.setdefault("lens_state_preserved", True)
        values.setdefault("canonical_workspace_mutated", False)
        values.setdefault("canonical_governance_mutated", False)
        values.setdefault("external_action_executed", False)
        values.setdefault("canonical_dependency_path_established", False)
        values.setdefault("observed_outcome_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        values["observation_id"] = stable_id(
            "outgoing_action_arm_observation",
            _identity_payload(values, "observation_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "OutgoingActionArmObservation":
        if self.policy_version != NATIVE_OUTGOING_ACTION_PROBE_VERSION:
            raise ValueError("Unsupported outgoing-action observation version.")
        if self.policy.policy_version != self.policy_version:
            raise ValueError("Outgoing-action observation changed its policy version.")
        if self.policy_sha256 != self.policy.fingerprint():
            raise ValueError("Outgoing-action policy checksum mismatch.")
        if not self.workspace_match_ref.strip():
            raise ValueError("Outgoing-action observation lost workspace lineage.")
        for digest in (
            self.policy_sha256,
            self.canonical_checkpoint_fingerprint,
            self.shadow_workspace_input_fingerprint,
            self.shadow_workspace_output_fingerprint,
            self.action_workspace_input_fingerprint,
            self.shadow_output_fingerprint,
        ):
            if not _is_sha256(digest):
                raise ValueError("Outgoing-action fingerprints must be SHA-256.")
        if self.admitted_evidence_refs != tuple(
            sorted(set(self.admitted_evidence_refs))
        ):
            raise ValueError("Outgoing-action evidence must be sorted and unique.")
        workspace = self.workspace_admission
        if (
            workspace.arm != self.arm
            or workspace.context != self.context
            or workspace.canonical_checkpoint_fingerprint
            != self.canonical_checkpoint_fingerprint
            or workspace.admitted_retrieved_evidence_refs
            != self.admitted_evidence_refs
            or workspace.shadow_input_fingerprint
            != self.shadow_workspace_input_fingerprint
            or workspace.shadow_output_fingerprint
            != self.shadow_workspace_output_fingerprint
        ):
            raise ValueError("Outgoing-action observation crossed workspace lineage.")

        native_records = (
            self.operation,
            self.council_proposal,
            self.council_report,
            self.council_decision,
            self.action_workspace_report,
            self.action_workspace_event,
        )
        if not self.admitted_evidence_refs:
            if any(item is not None for item in native_records):
                raise ValueError("No-evidence arm cannot fabricate native action records.")
            if (
                self.action_disposition
                != OutgoingActionDisposition.NO_ADMITTED_EVIDENCE
                or self.native_council_evaluated
                or self.native_council_authorized
                or self.native_action_workspace_evaluated
                or self.outgoing_action_signature_observed
                or self.action_workspace_input_fingerprint
                != self.shadow_workspace_output_fingerprint
                or self.shadow_output_fingerprint
                != self.shadow_workspace_output_fingerprint
            ):
                raise ValueError("No-evidence outgoing-action claim was altered.")
        else:
            if any(item is None for item in native_records):
                raise ValueError("Evidence-bearing arm requires complete native records.")
            assert self.operation is not None
            assert self.council_proposal is not None
            assert self.council_report is not None
            assert self.council_decision is not None
            assert self.action_workspace_report is not None
            assert self.action_workspace_event is not None
            expected_operation = self.policy.operation(self.context)
            expected_metadata = {
                "outgoing_action_probe_version": self.policy_version,
                "context_ref": self.context.context_id,
                "workspace_match_ref": self.workspace_match_ref,
                "workspace_arm_ref": workspace.observation_id,
                "controlled_trial_ref": workspace.controlled_trial_ref,
                "arm": self.arm.value,
            }
            if (
                self.operation != expected_operation
                or self.council_proposal.proposal_kind
                != GovernanceProposalKind.INVESTIGATE
                or self.council_proposal.operation != expected_operation
                or self.council_proposal.action_class != self.policy.action_class
                or self.council_proposal.description != self.policy.description
                or self.council_proposal.target_claim_id is not None
                or self.council_proposal.evidence_refs
                != self.admitted_evidence_refs
                or self.council_proposal.attention_candidate_ids
                or self.council_proposal.resonance_event_ids
                or self.council_proposal.requested_resource
                != self.policy.council_requested_resource
                or self.council_proposal.relevance != self.policy.relevance
                or self.council_proposal.urgency != self.policy.urgency
                or self.council_proposal.novelty != self.policy.novelty
                or self.council_proposal.predicted_information_gain
                != self.policy.predicted_information_gain
                or self.council_proposal.harm_risk != self.policy.harm_risk
                or self.council_proposal.reversibility
                != self.policy.reversibility
                or self.council_proposal.metadata != expected_metadata
                or self.council_report.proposal != self.council_proposal
                or self.council_decision.report != self.council_report
                or expected_operation
                not in self.council_report.authorized_operations
                or self.council_decision.semantic_mutation_permitted
                or self.council_decision.governance_policy_mutation_permitted
                or self.action_workspace_event.report
                != self.action_workspace_report
                or self.action_workspace_event.semantic_mutation_permitted
            ):
                raise ValueError("Outgoing action escaped its native supplied mapping.")
            assessments = _action_assessments(self.action_workspace_report)
            if len(assessments) != 1:
                raise ValueError("Outgoing action requires one native workspace candidate.")
            assessment = assessments[0]
            candidate = assessment.candidate
            expected_resource = (
                self.action_workspace_report.resource_budget
                * self.policy.candidate_resource_fraction
            )
            expected_candidate_metadata = {
                **expected_metadata,
                "council_proposal_ref": self.council_proposal.proposal_id,
                "council_report_ref": self.council_report.report_id,
                "council_decision_ref": self.council_decision.decision_event_id,
            }
            if (
                candidate.source_kind != WorkspaceSourceKind.AUTHORIZED_ACTION
                or candidate.source_ref
                != self.council_decision.decision_event_id
                or candidate.evidence_refs != self.admitted_evidence_refs
                or candidate.operation != expected_operation
                or candidate.binding_refs
                or candidate.persistence_cycles != self.policy.persistence_cycles
                or abs(candidate.resource_request - expected_resource) > 1e-12
                or candidate.signals.relevance != self.policy.relevance
                or candidate.signals.action_value
                != self.policy.action_value_signal
                or candidate.signals.ethical_salience
                != self.policy.ethical_salience_signal
                or candidate.metadata != expected_candidate_metadata
            ):
                raise ValueError("Native action candidate was altered.")
            admitted = assessment.disposition == WorkspaceDisposition.ADMIT
            expected_disposition = (
                OutgoingActionDisposition.AUTHORIZED_AND_ADMITTED
                if admitted
                else OutgoingActionDisposition.AUTHORIZED_BUT_SUPPRESSED
            )
            if (
                self.action_disposition != expected_disposition
                or not self.native_council_evaluated
                or not self.native_council_authorized
                or not self.native_action_workspace_evaluated
                or self.outgoing_action_signature_observed != admitted
            ):
                raise ValueError("Native outgoing-action disposition was altered.")

        expected_signature = _action_signature(
            policy_sha256=self.policy_sha256,
            arm=self.arm,
            context=self.context,
            evidence_refs=self.admitted_evidence_refs,
            operation=self.operation,
            council_report=self.council_report,
            action_report=self.action_workspace_report,
        )
        if self.action_signature != expected_signature:
            raise ValueError("Outgoing-action signature was altered.")
        if (
            not self.shadow_execution_only
            or not self.semantic_records_preserved
            or not self.simulation_ledger_preserved
            or not self.lens_state_preserved
            or self.canonical_workspace_mutated
            or self.canonical_governance_mutated
            or self.external_action_executed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Outgoing-action observation crossed its authority boundary.")
        expected = stable_id(
            "outgoing_action_arm_observation",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Outgoing-action observation checksum mismatch.")
        return self


class MatchedOutgoingActionObservation(FrozenRecord):
    """Matched outgoing-action signatures for one controlled zero/full pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    match_id: str
    policy_version: str = NATIVE_OUTGOING_ACTION_PROBE_VERSION
    controlled_trial_ref: str
    context: OperationalTrialContext
    workspace_admission: MatchedWorkspaceAdmissionObservation
    baseline: OutgoingActionArmObservation
    treatment: OutgoingActionArmObservation
    effect: OutgoingActionEffect
    newly_observed_operations: tuple[str, ...] = ()
    lost_observed_operations: tuple[str, ...] = ()
    action_effect_signature: str
    matched_control_verified: bool = True
    native_council_path_executed: bool = True
    native_workspace_path_executed: bool = True
    deterministic_shadow_only: bool = True
    external_action_executed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @staticmethod
    def _effect(
        baseline: OutgoingActionArmObservation,
        treatment: OutgoingActionArmObservation,
    ) -> tuple[OutgoingActionEffect, tuple[str, ...], tuple[str, ...]]:
        baseline_ops = {
            baseline.operation
            for _ in (0,)
            if baseline.outgoing_action_signature_observed
            and baseline.operation is not None
        }
        treatment_ops = {
            treatment.operation
            for _ in (0,)
            if treatment.outgoing_action_signature_observed
            and treatment.operation is not None
        }
        gained = tuple(sorted(treatment_ops - baseline_ops))
        lost = tuple(sorted(baseline_ops - treatment_ops))
        if gained and not lost:
            effect = OutgoingActionEffect.ACTION_GAIN
        elif not gained and not lost:
            effect = OutgoingActionEffect.VALID_NULL
        elif lost and not gained:
            effect = OutgoingActionEffect.ACTION_LOSS
        else:
            effect = OutgoingActionEffect.ACTION_CHANGED
        return effect, gained, lost

    @classmethod
    def build(
        cls,
        *,
        workspace_admission: MatchedWorkspaceAdmissionObservation,
        baseline: OutgoingActionArmObservation,
        treatment: OutgoingActionArmObservation,
    ) -> "MatchedOutgoingActionObservation":
        effect, gained, lost = cls._effect(baseline, treatment)
        signature = stable_id(
            "matched_outgoing_action_effect",
            NATIVE_OUTGOING_ACTION_PROBE_VERSION,
            baseline.policy_sha256,
            workspace_admission.workspace_effect_signature,
            workspace_admission.context.horizon,
            workspace_admission.context.slot_budget,
            effect.value,
            gained,
            lost,
            baseline.action_signature,
            treatment.action_signature,
        )
        values = {
            "policy_version": NATIVE_OUTGOING_ACTION_PROBE_VERSION,
            "controlled_trial_ref": workspace_admission.controlled_trial_ref,
            "context": workspace_admission.context,
            "workspace_admission": workspace_admission,
            "baseline": baseline,
            "treatment": treatment,
            "effect": effect,
            "newly_observed_operations": gained,
            "lost_observed_operations": lost,
            "action_effect_signature": signature,
            "matched_control_verified": True,
            "native_council_path_executed": True,
            "native_workspace_path_executed": True,
            "deterministic_shadow_only": True,
            "external_action_executed": False,
            "canonical_dependency_path_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["match_id"] = stable_id(
            "matched_outgoing_action_observation",
            _identity_payload(values, "match_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_match(self) -> "MatchedOutgoingActionObservation":
        workspace = self.workspace_admission
        if self.policy_version != NATIVE_OUTGOING_ACTION_PROBE_VERSION:
            raise ValueError("Unsupported matched outgoing-action version.")
        if (
            self.controlled_trial_ref != workspace.controlled_trial_ref
            or self.context != workspace.context
            or self.baseline.arm != OperationalProbeArm.BASELINE
            or self.treatment.arm != OperationalProbeArm.TREATMENT
            or self.baseline.context != self.context
            or self.treatment.context != self.context
            or self.baseline.workspace_match_ref != workspace.match_id
            or self.treatment.workspace_match_ref != workspace.match_id
            or self.baseline.workspace_admission != workspace.baseline
            or self.treatment.workspace_admission != workspace.treatment
            or self.baseline.policy_sha256 != self.treatment.policy_sha256
        ):
            raise ValueError("Outgoing-action controls are not matched.")
        effect, gained, lost = self._effect(self.baseline, self.treatment)
        expected_signature = stable_id(
            "matched_outgoing_action_effect",
            self.policy_version,
            self.baseline.policy_sha256,
            workspace.workspace_effect_signature,
            self.context.horizon,
            self.context.slot_budget,
            effect.value,
            gained,
            lost,
            self.baseline.action_signature,
            self.treatment.action_signature,
        )
        if (
            self.effect != effect
            or self.newly_observed_operations != gained
            or self.lost_observed_operations != lost
            or self.action_effect_signature != expected_signature
        ):
            raise ValueError("Matched outgoing-action effect was altered.")
        if (
            not self.matched_control_verified
            or not self.native_council_path_executed
            or not self.native_workspace_path_executed
            or not self.deterministic_shadow_only
            or self.external_action_executed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Matched outgoing action crossed its authority boundary.")
        expected = stable_id(
            "matched_outgoing_action_observation",
            self.model_dump(mode="json", exclude={"match_id"}),
        )
        if self.match_id != expected:
            raise ValueError("Matched outgoing-action checksum mismatch.")
        return self


class HeldOutOutgoingActionReplicationReceipt(FrozenRecord):
    """Exact ID-independent action-effect replay across declared trial splits."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    policy_version: str = HELD_OUT_OUTGOING_ACTION_REPLICATION_VERSION
    operational_replication_ref: str
    workspace_replication_ref: str
    observations: tuple[MatchedOutgoingActionObservation, ...] = Field(
        min_length=2
    )
    calibration_match_ref: str
    held_out_match_refs: tuple[str, ...] = Field(min_length=1)
    seeds: tuple[int, ...] = Field(min_length=2)
    action_effect_signature: str
    declared_seed_replay_observed: bool = True
    native_outgoing_action_signature_observed: bool
    stochastic_generalization_established: bool = False
    external_action_executed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        operational_replication_ref: str,
        workspace_replication_ref: str,
        observations: Sequence[MatchedOutgoingActionObservation],
    ) -> "HeldOutOutgoingActionReplicationReceipt":
        normalized = tuple(
            MatchedOutgoingActionObservation.model_validate(
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
                "Outgoing-action replication requires calibration and held-out trials."
            )
        values = {
            "policy_version": HELD_OUT_OUTGOING_ACTION_REPLICATION_VERSION,
            "operational_replication_ref": operational_replication_ref,
            "workspace_replication_ref": workspace_replication_ref,
            "observations": normalized,
            "calibration_match_ref": calibration[0].match_id,
            "held_out_match_refs": tuple(item.match_id for item in held_out),
            "seeds": tuple(item.context.seed for item in normalized),
            "action_effect_signature": normalized[0].action_effect_signature,
            "declared_seed_replay_observed": True,
            "native_outgoing_action_signature_observed": any(
                item.baseline.outgoing_action_signature_observed
                or item.treatment.outgoing_action_signature_observed
                for item in normalized
            ),
            "stochastic_generalization_established": False,
            "external_action_executed": False,
            "canonical_dependency_path_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "held_out_outgoing_action_replication_receipt",
            _identity_payload(values, "receipt_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "HeldOutOutgoingActionReplicationReceipt":
        if self.policy_version != HELD_OUT_OUTGOING_ACTION_REPLICATION_VERSION:
            raise ValueError("Unsupported outgoing-action replication version.")
        if not self.operational_replication_ref.strip() or not (
            self.workspace_replication_ref.strip()
        ):
            raise ValueError("Outgoing-action replication lost parent lineage.")
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
            raise ValueError("Outgoing-action observations are not canonicalized.")
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
                "Outgoing-action replication requires calibration and held-out trials."
            )
        if (
            self.calibration_match_ref != calibration[0].match_id
            or self.held_out_match_refs
            != tuple(item.match_id for item in held_out)
        ):
            raise ValueError("Outgoing-action split lineage was altered.")
        expected_seeds = tuple(item.context.seed for item in self.observations)
        if self.seeds != expected_seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Outgoing-action replication requires distinct seeds.")
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
            raise ValueError("Outgoing-action replication controls are not matched.")
        if any(
            item.action_effect_signature != self.action_effect_signature
            for item in self.observations
        ):
            raise ValueError("Held-out outgoing-action effect did not replicate.")
        expected_observed = any(
            item.baseline.outgoing_action_signature_observed
            or item.treatment.outgoing_action_signature_observed
            for item in self.observations
        )
        if self.native_outgoing_action_signature_observed != expected_observed:
            raise ValueError("Outgoing-action replication claim was altered.")
        if (
            not self.declared_seed_replay_observed
            or self.stochastic_generalization_established
            or self.external_action_executed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Outgoing-action replication crossed its authority boundary.")
        expected = stable_id(
            "held_out_outgoing_action_replication_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected:
            raise ValueError("Outgoing-action replication checksum mismatch.")
        return self


class NativeOutgoingActionObserver:
    """Replay admission through native Council and action-workspace paths."""

    def __init__(
        self,
        policy: NativeOutgoingActionProbePolicy | None = None,
    ) -> None:
        self.policy = policy or NativeOutgoingActionProbePolicy()

    def _reconstruct_workspace_arm(
        self,
        kernel: VerdantKernel,
        observation: WorkspaceAdmissionArmObservation,
    ) -> VerdantKernel:
        canonical_policy = kernel.state.workspace_policy
        if observation.declared_slot_budget > canonical_policy.max_active_items:
            raise OutgoingActionProbeIntegrityError(
                "Action probe cannot relax the canonical workspace slot cap."
            )
        shadow = VerdantKernel.from_state(kernel.snapshot())
        shadow.state.workspace_policy = WorkspacePolicy.model_validate(
            canonical_policy.model_copy(
                update={
                    "max_active_items": observation.declared_slot_budget,
                    "revision": canonical_policy.revision + 1,
                }
            ).model_dump(mode="json")
        )
        if shadow.fingerprint() != observation.shadow_input_fingerprint:
            raise OutgoingActionProbeIntegrityError(
                "Workspace arm input cannot be reconstructed from canonical state."
            )
        result = VerdantWorkspacePipeline().run_cycle(
            shadow,
            _workspace_probe_candidates(observation),
        )
        if (
            result.report != observation.admission_report
            or result.event != observation.workspace_event
            or shadow.fingerprint() != observation.shadow_output_fingerprint
        ):
            raise OutgoingActionProbeIntegrityError(
                "Workspace arm differs from its native replay."
            )
        return shadow

    def _run_arm(
        self,
        kernel: VerdantKernel,
        *,
        context: OperationalTrialContext,
        workspace_match_ref: str,
        workspace: WorkspaceAdmissionArmObservation,
        arm: OperationalProbeArm,
        ledger_before: str,
        lens_before: str,
        ledger: SimulationLedger,
        lenses: EquivalenceLensSystem,
    ) -> OutgoingActionArmObservation:
        shadow = self._reconstruct_workspace_arm(kernel, workspace)
        semantic_before = _semantic_fingerprint(shadow)
        policy_sha256 = self.policy.fingerprint()
        evidence_refs = workspace.admitted_retrieved_evidence_refs
        action_input = shadow.fingerprint()

        if not evidence_refs:
            signature = _action_signature(
                policy_sha256=policy_sha256,
                arm=arm,
                context=context,
                evidence_refs=(),
                operation=None,
                council_report=None,
                action_report=None,
            )
            return OutgoingActionArmObservation.build(
                policy=self.policy,
                policy_sha256=policy_sha256,
                arm=arm,
                context=context,
                workspace_match_ref=workspace_match_ref,
                workspace_admission=workspace,
                canonical_checkpoint_fingerprint=kernel.fingerprint(),
                admitted_evidence_refs=(),
                operation=None,
                council_proposal=None,
                council_report=None,
                council_decision=None,
                action_workspace_report=None,
                action_workspace_event=None,
                action_disposition=OutgoingActionDisposition.NO_ADMITTED_EVIDENCE,
                action_signature=signature,
                shadow_workspace_input_fingerprint=workspace.shadow_input_fingerprint,
                shadow_workspace_output_fingerprint=workspace.shadow_output_fingerprint,
                action_workspace_input_fingerprint=action_input,
                shadow_output_fingerprint=shadow.fingerprint(),
                native_council_evaluated=False,
                native_council_authorized=False,
                native_action_workspace_evaluated=False,
                outgoing_action_signature_observed=False,
                semantic_records_preserved=(
                    _semantic_fingerprint(shadow) == semantic_before
                ),
                simulation_ledger_preserved=(
                    ledger.fingerprint() == ledger_before
                ),
                lens_state_preserved=(lenses.fingerprint() == lens_before),
            )

        operation = self.policy.operation(context)
        metadata = {
            "outgoing_action_probe_version": self.policy.policy_version,
            "context_ref": context.context_id,
            "workspace_match_ref": workspace_match_ref,
            "workspace_arm_ref": workspace.observation_id,
            "controlled_trial_ref": workspace.controlled_trial_ref,
            "arm": arm.value,
        }
        governance = VerdantGovernancePipeline()
        proposal = governance.propose(
            shadow,
            proposal_kind=GovernanceProposalKind.INVESTIGATE,
            operation=operation,
            action_class=self.policy.action_class,
            description=self.policy.description,
            evidence_refs=evidence_refs,
            requested_resource=self.policy.council_requested_resource,
            relevance=self.policy.relevance,
            urgency=self.policy.urgency,
            novelty=self.policy.novelty,
            predicted_information_gain=self.policy.predicted_information_gain,
            harm_risk=self.policy.harm_risk,
            reversibility=self.policy.reversibility,
            metadata=metadata,
        )
        report = governance.inspect(shadow, proposal)
        decision = governance.commit(shadow, report)
        if (
            report.disposition
            not in {CouncilDisposition.APPROVE, CouncilDisposition.APPROVE_WITH_CONSTRAINTS}
            or operation not in report.authorized_operations
        ):
            raise OutgoingActionProbeIntegrityError(
                "Supplied reversible investigation was not Council-authorized."
            )
        shadow.assert_operation_authorized(decision.decision_event_id, operation)
        action_input = shadow.fingerprint()
        evidence_grounding = sum(
            kernel.state.evidence[item].confidence for item in evidence_refs
        ) / len(evidence_refs)
        resource_request = (
            shadow.state.workspace_policy.resource_budget
            * self.policy.candidate_resource_fraction
        )
        candidate = WorkspaceCandidateInput(
            source_kind=WorkspaceSourceKind.AUTHORIZED_ACTION,
            source_ref=decision.decision_event_id,
            label=f"authorized dependency inspection {operation}",
            evidence_refs=evidence_refs,
            resource_request=resource_request,
            persistence_cycles=self.policy.persistence_cycles,
            signals=WorkspaceSignals(
                evidence_grounding=evidence_grounding,
                relevance=self.policy.relevance,
                prediction_error=0.0,
                contradiction_pressure=0.0,
                action_value=self.policy.action_value_signal,
                ethical_salience=self.policy.ethical_salience_signal,
                novelty=self.policy.novelty,
                resonance=0.0,
            ),
            operation=operation,
            metadata={
                **metadata,
                "council_proposal_ref": proposal.proposal_id,
                "council_report_ref": report.report_id,
                "council_decision_ref": decision.decision_event_id,
            },
        )
        action_result = VerdantWorkspacePipeline().run_cycle(shadow, (candidate,))
        assessments = _action_assessments(action_result.report)
        if len(assessments) != 1:
            raise OutgoingActionProbeIntegrityError(
                "Native workspace lost the authorized action candidate."
            )
        admitted = assessments[0].disposition == WorkspaceDisposition.ADMIT
        disposition = (
            OutgoingActionDisposition.AUTHORIZED_AND_ADMITTED
            if admitted
            else OutgoingActionDisposition.AUTHORIZED_BUT_SUPPRESSED
        )
        semantic_preserved = _semantic_fingerprint(shadow) == semantic_before
        if not semantic_preserved:
            raise OutgoingActionProbeIntegrityError(
                "Shadow action path changed semantic records."
            )
        signature = _action_signature(
            policy_sha256=policy_sha256,
            arm=arm,
            context=context,
            evidence_refs=evidence_refs,
            operation=operation,
            council_report=report,
            action_report=action_result.report,
        )
        return OutgoingActionArmObservation.build(
            policy=self.policy,
            policy_sha256=policy_sha256,
            arm=arm,
            context=context,
            workspace_match_ref=workspace_match_ref,
            workspace_admission=workspace,
            canonical_checkpoint_fingerprint=kernel.fingerprint(),
            admitted_evidence_refs=evidence_refs,
            operation=operation,
            council_proposal=proposal,
            council_report=report,
            council_decision=decision,
            action_workspace_report=action_result.report,
            action_workspace_event=action_result.event,
            action_disposition=disposition,
            action_signature=signature,
            shadow_workspace_input_fingerprint=workspace.shadow_input_fingerprint,
            shadow_workspace_output_fingerprint=workspace.shadow_output_fingerprint,
            action_workspace_input_fingerprint=action_input,
            shadow_output_fingerprint=shadow.fingerprint(),
            native_council_evaluated=True,
            native_council_authorized=True,
            native_action_workspace_evaluated=True,
            outgoing_action_signature_observed=admitted,
            semantic_records_preserved=semantic_preserved,
            simulation_ledger_preserved=(ledger.fingerprint() == ledger_before),
            lens_state_preserved=(lenses.fingerprint() == lens_before),
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
        workspace_observation: MatchedWorkspaceAdmissionObservation,
    ) -> MatchedOutgoingActionObservation:
        canonical_before = kernel.fingerprint()
        ledger_before = ledger.fingerprint()
        lens_before = lenses.fingerprint()
        try:
            workspace_observation = MatchedWorkspaceAdmissionObservation.model_validate(
                workspace_observation.model_dump(mode="json")
            )
            expected_workspace = NativeWorkspaceAdmissionObserver().observe(
                kernel,
                ledger,
                lenses,
                context=context,
                hypothesis=hypothesis,
                baseline_plan=baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=treatment_plan,
                treatment_result=treatment_result,
                controlled_observation=controlled_observation,
            )
            if workspace_observation != expected_workspace:
                raise OutgoingActionProbeIntegrityError(
                    "Outgoing action received a noncanonical workspace receipt."
                )
            baseline = self._run_arm(
                kernel,
                context=context,
                workspace_match_ref=workspace_observation.match_id,
                workspace=workspace_observation.baseline,
                arm=OperationalProbeArm.BASELINE,
                ledger_before=ledger_before,
                lens_before=lens_before,
                ledger=ledger,
                lenses=lenses,
            )
            treatment = self._run_arm(
                kernel,
                context=context,
                workspace_match_ref=workspace_observation.match_id,
                workspace=workspace_observation.treatment,
                arm=OperationalProbeArm.TREATMENT,
                ledger_before=ledger_before,
                lens_before=lens_before,
                ledger=ledger,
                lenses=lenses,
            )
            if (
                kernel.fingerprint() != canonical_before
                or ledger.fingerprint() != ledger_before
                or lenses.fingerprint() != lens_before
            ):
                raise OutgoingActionProbeIntegrityError(
                    "Outgoing-action probe mutated canonical or sidecar state."
                )
            return MatchedOutgoingActionObservation.build(
                workspace_admission=workspace_observation,
                baseline=baseline,
                treatment=treatment,
            )
        except OutgoingActionProbeIntegrityError:
            raise
        except (
            GovernanceIntegrityError,
            GovernanceStaleError,
            WorkspaceIntegrityError,
            WorkspaceStaleError,
            WorkspaceAdmissionProbeIntegrityError,
            OperationalTrialControlIntegrityError,
            SimulationIntegrityError,
            LensIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise OutgoingActionProbeIntegrityError(str(exc)) from exc


class HeldOutOutgoingActionReplicationObserver:
    """Require exact action-effect replay across predeclared trial splits."""

    def observe(
        self,
        operational_replication: HeldOutOperationalReplicationReceipt,
        workspace_replication: HeldOutWorkspaceAdmissionReplicationReceipt,
        observations: Sequence[MatchedOutgoingActionObservation],
    ) -> HeldOutOutgoingActionReplicationReceipt:
        try:
            normalized = tuple(
                MatchedOutgoingActionObservation.model_validate(
                    item.model_dump(mode="json")
                )
                for item in observations
            )
            expected_workspace = HeldOutWorkspaceAdmissionReplicationObserver().observe(
                operational_replication,
                tuple(item.workspace_admission for item in normalized),
            )
            workspace_replication = (
                HeldOutWorkspaceAdmissionReplicationReceipt.model_validate(
                    workspace_replication.model_dump(mode="json")
                )
            )
            if workspace_replication != expected_workspace:
                raise OutgoingActionProbeIntegrityError(
                    "Outgoing-action replication received a foreign workspace receipt."
                )
            receipt = HeldOutOutgoingActionReplicationReceipt.build(
                operational_replication_ref=operational_replication.receipt_id,
                workspace_replication_ref=workspace_replication.receipt_id,
                observations=normalized,
            )
            if tuple(
                item.workspace_admission.match_id for item in receipt.observations
            ) != tuple(item.match_id for item in workspace_replication.observations):
                raise OutgoingActionProbeIntegrityError(
                    "Outgoing-action replication lost workspace observation lineage."
                )
            return receipt
        except OutgoingActionProbeIntegrityError:
            raise
        except (WorkspaceAdmissionProbeIntegrityError, ValueError, TypeError) as exc:
            raise OutgoingActionProbeIntegrityError(str(exc)) from exc
