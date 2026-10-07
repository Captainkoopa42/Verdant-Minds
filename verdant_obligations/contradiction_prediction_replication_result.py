"""Durable execution of the frozen v0.44 Contradiction replication.

This opt-in layer requires an existing immutable ``.vrp`` declaration.  It
executes all four declared matched trials on private simulation ledgers,
consumes only the actual ``structures.after_record_count`` through one fixed
native shadow-workspace policy, and atomically stores a separate ``.vrr``
result.  Profile-group-held-out rules train only on the predeclared high-trace
variation; low-trace contexts remain untouched negative controls.

The result is simulated experimental evidence.  It grants no truth,
resolution, promotion, policy-rewrite, or canonical-write authority.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Sequence

try:  # pragma: no cover
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    WorkspaceAdmissionReport,
    WorkspaceCandidateInput,
    WorkspaceCycleEvent,
    WorkspaceDisposition,
    WorkspaceIntegrityError,
    WorkspacePolicy,
    WorkspaceSignals,
    WorkspaceSourceKind,
    VerdantKernel,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id
from verdant_workspace import VerdantWorkspacePipeline

from .contradiction_dimension_criterion import (
    ContradictionProjectionCardinalityProfile,
)
from .contradiction_downstream_outcome import (
    ContradictionDownstreamOutcomeDisposition,
)
from .contradiction_prediction_replication import (
    CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT,
    CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD,
    ContradictionPredictionReplicationContext,
    ContradictionPredictionReplicationContextInput,
    ContradictionPredictionReplicationDeclaration,
    ContradictionPredictionReplicationFold,
    ContradictionPredictionReplicationIntegrityError,
    ContradictionPredictionReplicationOutcomePolicy,
    ContradictionPredictionReplicationPreregistrationEnvelope,
    ContradictionPredictionReplicationTraceRole,
    read_contradiction_prediction_replication_preregistration,
)
from .contradiction_trial_controls import (
    ContradictionLensHeldOutReplicationReceipt,
    ContradictionLensHeldOutTrialRunner,
    ContradictionLensTrialIntegrityError,
    ContradictionLensTrialObservation,
    _validate_observation_ledger,
)
from .counterfactual import (
    CounterfactualExecutionTrace,
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
    SimulationLedgerState,
)
from .equivalence import LensIntegrityError


CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION = (
    "contradiction_prediction_replication_result_v0.45"
)
CONTRADICTION_PREDICTION_REPLICATION_RESULT_FORMAT = (
    "verdant-contradiction-prediction-replication-result-v1"
)
_MAX_SIDECAR_BYTES = 256 * 1024 * 1024
_EMPTY_LEDGER = SimulationLedger().fingerprint()


class ContradictionPredictionReplicationResultIntegrityError(RuntimeError):
    """Raised when completed replication evidence loses frozen lineage."""


class ContradictionPredictionReplicationArm(str, Enum):
    BASELINE = "baseline"
    TREATMENT = "treatment"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha(canonical_json_bytes(value))


def _is_sha(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


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


def _projection_counts(
    observation: ContradictionLensTrialObservation,
) -> tuple[int, int]:
    return tuple(
        len(item.projected_claim_refs)
        for item in observation.lens_observation.route_projections
    )


def _profile(
    counts: tuple[int, int],
) -> ContradictionProjectionCardinalityProfile:
    if counts == (1, 1):
        return ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    if counts[0] == counts[1]:
        return ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES
    return ContradictionProjectionCardinalityProfile.ASYMMETRIC_ROUTE_CARDINALITY


def _matched_traces(
    observation: ContradictionLensTrialObservation,
) -> tuple[CounterfactualExecutionTrace, CounterfactualExecutionTrace]:
    matched = (
        observation.lens_observation.functional_observation
        .provenance_observation.matched_observation
    )
    return matched.baseline, matched.treatment


def _structure_delta(trace: CounterfactualExecutionTrace):
    return next(
        item for item in trace.collection_deltas if item.collection == "structures"
    )


def _validate_trace_provenance(
    baseline: CounterfactualExecutionTrace,
    treatment: CounterfactualExecutionTrace,
) -> None:
    if baseline.match_signature != treatment.match_signature:
        raise ContradictionPredictionReplicationResultIntegrityError(
            "Replication traces are not a matched pair."
        )
    if baseline.applied_patch_ids or not treatment.applied_patch_ids:
        raise ContradictionPredictionReplicationResultIntegrityError(
            "Replication trace arms changed intervention roles."
        )
    for trace in (baseline, treatment):
        if any(
            delta.removed_record_keys or delta.changed_record_keys
            for delta in trace.collection_deltas
        ) or any(
            delta.added_record_keys
            for delta in trace.collection_deltas
            if delta.collection != "structures"
        ):
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication trace changed a protected collection."
            )


def _workspace_policy(
    policy: ContradictionPredictionReplicationOutcomePolicy,
) -> WorkspacePolicy:
    return WorkspacePolicy(
        minimum_admission_score=policy.minimum_admission_score,
        revision=1,
    )


def _candidate_control_signature(candidate: WorkspaceCandidateInput) -> str:
    normalized = candidate.model_copy(
        update={
            "signals": candidate.signals.model_copy(
                update={"contradiction_pressure": 0.0}
            ),
            "metadata": {
                key: value
                for key, value in candidate.metadata.items()
                if key not in {"arm", "trace_ref"}
            },
        }
    )
    return stable_id(
        "contradiction_prediction_replication_workspace_control",
        CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
        normalized.model_dump(mode="json"),
    )


class ContradictionPredictionReplicationArmObservation(FrozenRecord):
    """One native shadow-workspace result from one actual after-count."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
    declaration_ref: str
    context_ref: str
    trace_role: ContradictionPredictionReplicationTraceRole
    arm: ContradictionPredictionReplicationArm
    trace_ref: str
    trace_field: str = CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD
    trace_before_structure_count: int = Field(ge=0)
    trace_after_structure_count: int = Field(ge=0)
    trace_added_structure_count: int = Field(ge=0)
    contradiction_pressure: float = Field(ge=0.0, le=1.0)
    source_contradiction_ref: str
    source_claim_refs: tuple[str, str]
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
    workspace_policy: WorkspacePolicy
    workspace_policy_sha256: str
    candidate_control_signature: str
    candidate: WorkspaceCandidateInput
    admission_report: WorkspaceAdmissionReport
    workspace_event: WorkspaceCycleEvent
    raw_score: float = Field(ge=0.0, le=1.0)
    effective_score: float = Field(ge=0.0, le=1.0)
    admitted: bool
    rejection_codes: tuple[str, ...]
    shadow_input_fingerprint: str
    shadow_output_fingerprint: str
    semantic_fingerprint: str
    native_workspace_pipeline_executed: bool = True
    actual_after_record_count_consumed: bool = True
    trace_record_identities_consulted: bool = False
    lens_projections_consulted: bool = False
    functional_disposition_consulted: bool = False
    semantic_records_preserved: bool = True
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ContradictionPredictionReplicationArmObservation":
        values.setdefault("observer_version", CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION)
        values.setdefault("trace_field", CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD)
        values.setdefault("native_workspace_pipeline_executed", True)
        values.setdefault("actual_after_record_count_consumed", True)
        values.setdefault("trace_record_identities_consulted", False)
        values.setdefault("lens_projections_consulted", False)
        values.setdefault("functional_disposition_consulted", False)
        values.setdefault("semantic_records_preserved", True)
        values.setdefault("authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        values["observation_id"] = stable_id(
            "contradiction_prediction_replication_arm", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionPredictionReplicationArmObservation":
        expected_policy = WorkspacePolicy(minimum_admission_score=0.35, revision=1)
        expected_pressure = min(1.0, self.trace_after_structure_count * 0.5)
        assessment = self.admission_report.assessments[0] if len(
            self.admission_report.assessments
        ) == 1 else None
        if (
            self.observer_version != CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
            or self.trace_field != CONTRADICTION_PREDICTION_REPLICATION_TRACE_FIELD
            or self.trace_after_structure_count
            != self.trace_before_structure_count + self.trace_added_structure_count
            or self.contradiction_pressure != expected_pressure
            or self.workspace_policy != expected_policy
            or self.workspace_policy_sha256
            != _digest(expected_policy.model_dump(mode="json"))
            or self.candidate_control_signature
            != _candidate_control_signature(self.candidate)
            or assessment is None
            or assessment.candidate != self.candidate
            or self.workspace_event.report != self.admission_report
            or self.workspace_event.semantic_mutation_permitted
            or self.raw_score != assessment.raw_score
            or self.effective_score != assessment.effective_score
            or self.rejection_codes != assessment.rejection_codes
            or self.admitted != (assessment.disposition == WorkspaceDisposition.ADMIT)
        ):
            raise ValueError("Replication arm changed its fixed native result.")
        signals = self.candidate.signals
        if (
            self.candidate.source_kind != WorkspaceSourceKind.CONTRADICTION
            or self.candidate.source_ref != self.source_contradiction_ref
            or self.candidate.evidence_refs != self.source_evidence_refs
            or self.candidate.resource_request != 0.10
            or self.candidate.persistence_cycles != 1
            or signals.evidence_grounding != 1.0
            or signals.contradiction_pressure != self.contradiction_pressure
            or any(
                getattr(signals, field) != 0.0
                for field in (
                    "relevance", "prediction_error", "action_value",
                    "ethical_salience", "novelty", "resonance",
                )
            )
        ):
            raise ValueError("Replication workspace candidate changed its inputs.")
        if self.candidate.metadata != {
            "replication_result_version": self.observer_version,
            "declaration_ref": self.declaration_ref,
            "context_ref": self.context_ref,
            "trace_role": self.trace_role.value,
            "arm": self.arm.value,
            "trace_ref": self.trace_ref,
            "trace_field": self.trace_field,
        }:
            raise ValueError("Replication workspace provenance was altered.")
        if any((
            not self.native_workspace_pipeline_executed,
            not self.actual_after_record_count_consumed,
            self.trace_record_identities_consulted,
            self.lens_projections_consulted,
            self.functional_disposition_consulted,
            not self.semantic_records_preserved,
            self.authority_enabled,
            self.canonical_commit_permitted,
        )) or not all(_is_sha(item) for item in (
            self.workspace_policy_sha256,
            self.shadow_input_fingerprint,
            self.shadow_output_fingerprint,
            self.semantic_fingerprint,
        )):
            raise ValueError("Replication arm crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_replication_arm",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Replication-arm checksum mismatch.")
        return self


class ContradictionPredictionReplicationContextObservation(FrozenRecord):
    """One context's executed count transition and fixed-policy outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observation_version: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
    declaration_ref: str
    context: ContradictionPredictionReplicationContext
    context_ref: str
    trial_receipt: ContradictionLensHeldOutReplicationReceipt
    trial_receipt_ref: str
    actual_cardinalities: tuple[int, int]
    actual_profile: ContradictionProjectionCardinalityProfile
    baseline: ContradictionPredictionReplicationArmObservation
    treatment: ContradictionPredictionReplicationArmObservation
    outcome: ContradictionDownstreamOutcomeDisposition
    count_transition_matched_declaration: bool
    profile_matched_declaration: bool
    fixed_policy_applied_unchanged: bool = True
    matched_trace_control_verified: bool = True
    actual_replication_trace_observed: bool = True
    downstream_outcome_observed: bool = True
    evidence_preserved: bool = True
    anti_suppression_verified: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        declaration_ref: str,
        context: ContradictionPredictionReplicationContext,
        trial_receipt: ContradictionLensHeldOutReplicationReceipt,
        baseline: ContradictionPredictionReplicationArmObservation,
        treatment: ContradictionPredictionReplicationArmObservation,
    ) -> "ContradictionPredictionReplicationContextObservation":
        declared = ContradictionPredictionReplicationContext.model_validate(
            context.model_dump(mode="json")
        )
        trial = ContradictionLensHeldOutReplicationReceipt.model_validate(
            trial_receipt.model_dump(mode="json")
        )
        base = ContradictionPredictionReplicationArmObservation.model_validate(
            baseline.model_dump(mode="json")
        )
        treated = ContradictionPredictionReplicationArmObservation.model_validate(
            treatment.model_dump(mode="json")
        )
        counts = _projection_counts(trial.held_out_observation)
        actual_profile = _profile(counts)
        count_match = (
            base.trace_after_structure_count
            == declared.declared_baseline_after_structure_count
            and treated.trace_after_structure_count
            == declared.declared_treatment_after_structure_count
            and treated.trace_added_structure_count
            == declared.declared_treatment_added_structure_count
        )
        values = {
            "observation_version": CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
            "declaration_ref": declaration_ref,
            "context": declared,
            "context_ref": declared.context_id,
            "trial_receipt": trial,
            "trial_receipt_ref": trial.receipt_id,
            "actual_cardinalities": counts,
            "actual_profile": actual_profile,
            "baseline": base,
            "treatment": treated,
            "outcome": (
                ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
                if not base.admitted and treated.admitted
                else ContradictionDownstreamOutcomeDisposition.VALID_NULL
            ),
            "count_transition_matched_declaration": count_match,
            "profile_matched_declaration": actual_profile == declared.expected_profile,
            "fixed_policy_applied_unchanged": True,
            "matched_trace_control_verified": True,
            "actual_replication_trace_observed": True,
            "downstream_outcome_observed": True,
            "evidence_preserved": True,
            "anti_suppression_verified": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "contradiction_prediction_replication_context_observation", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ContradictionPredictionReplicationContextObservation":
        counts = _projection_counts(self.trial_receipt.held_out_observation)
        profile = _profile(counts)
        expected_outcome = (
            ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            if not self.baseline.admitted and self.treatment.admitted
            else ContradictionDownstreamOutcomeDisposition.VALID_NULL
        )
        count_match = (
            self.baseline.trace_after_structure_count
            == self.context.declared_baseline_after_structure_count
            and self.treatment.trace_after_structure_count
            == self.context.declared_treatment_after_structure_count
            and self.treatment.trace_added_structure_count
            == self.context.declared_treatment_added_structure_count
        )
        if (
            self.observation_version != CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
            or self.context_ref != self.context.context_id
            or self.trial_receipt_ref != self.trial_receipt.receipt_id
            or self.trial_receipt.pair_context != self.context.pair_context
            or self.actual_cardinalities != counts
            or self.actual_profile != profile
            or self.profile_matched_declaration != (profile == self.context.expected_profile)
            or self.outcome != expected_outcome
            or self.count_transition_matched_declaration != count_match
            or self.baseline.declaration_ref != self.declaration_ref
            or self.treatment.declaration_ref != self.declaration_ref
            or self.baseline.context_ref != self.context_ref
            or self.treatment.context_ref != self.context_ref
            or self.baseline.trace_role != self.context.trace_role
            or self.treatment.trace_role != self.context.trace_role
            or self.baseline.arm != ContradictionPredictionReplicationArm.BASELINE
            or self.treatment.arm != ContradictionPredictionReplicationArm.TREATMENT
            or self.baseline.candidate_control_signature
            != self.treatment.candidate_control_signature
        ):
            raise ValueError("Replication context observation was altered.")
        functional = self.context.pair_context.held_out.controlled_context.functional_context
        for arm in (self.baseline, self.treatment):
            if (
                arm.source_contradiction_ref != functional.contradiction_ref
                or arm.source_claim_refs != self.context.evaluation_claim_refs
                or arm.source_evidence_refs != self.context.evaluation_evidence_refs
            ):
                raise ValueError("Replication context source provenance was altered.")
        if any((
            not self.fixed_policy_applied_unchanged,
            not self.matched_trace_control_verified,
            not self.actual_replication_trace_observed,
            not self.downstream_outcome_observed,
            not self.evidence_preserved,
            not self.anti_suppression_verified,
            not self.simulated_only,
            self.predictive_discrimination_observed,
            self.dimensional_separation_observed,
            self.independent_held_out_replication_observed,
            self.authority_enabled,
            self.canonical_commit_permitted,
        )):
            raise ValueError("Replication context crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_replication_context_observation",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Replication-context observation checksum mismatch.")
        return self


class ContradictionPredictionReplicationFoldResult(FrozenRecord):
    """Frozen profile-only rule and its held-out variation/control evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_id: str
    result_version: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
    declaration_ref: str
    fold: ContradictionPredictionReplicationFold
    fold_ref: str
    training_variation_context_ref: str
    training_variation_observation_ref: str
    training_variation_observation_sha256: str
    trained_profile: ContradictionProjectionCardinalityProfile
    trained_outcome: ContradictionDownstreamOutcomeDisposition
    unseen_profile_default: ContradictionDownstreamOutcomeDisposition
    evaluation_profile: ContradictionProjectionCardinalityProfile
    predicted_outcome: ContradictionDownstreamOutcomeDisposition
    evaluation_variation_context_ref: str
    evaluation_variation_observation_ref: str
    evaluation_variation_observation_sha256: str
    evaluation_variation_outcome: ContradictionDownstreamOutcomeDisposition
    evaluation_variation_match: bool
    evaluation_control_context_ref: str
    evaluation_control_observation_ref: str
    evaluation_control_observation_sha256: str
    evaluation_control_outcome: ContradictionDownstreamOutcomeDisposition
    evaluation_control_match: bool
    variation_training_only: bool = True
    low_trace_control_consulted_during_fit: bool = False
    trace_role_as_prediction_input: bool = False
    trace_field_as_prediction_input: bool = False
    evaluation_consulted_during_fit: bool = False
    rule_applied_unchanged: bool = True
    joint_discrimination_observed: bool
    rule_family_falsified: bool
    predictive_discrimination_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionReplicationDeclaration,
        fold: ContradictionPredictionReplicationFold,
        observations: dict[str, ContradictionPredictionReplicationContextObservation],
    ) -> "ContradictionPredictionReplicationFoldResult":
        training = tuple(observations[ref] for ref in fold.training_context_refs)
        evaluation = tuple(observations[ref] for ref in fold.evaluation_context_refs)
        training_variation = next(
            item for item in training
            if item.context.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
        )
        evaluation_variation = next(
            item for item in evaluation
            if item.context.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
        )
        evaluation_control = next(
            item for item in evaluation
            if item.context.trace_role
            == ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL
        )
        if (
            fold not in declaration.folds
            or training_variation.actual_profile != fold.training_profile
            or evaluation_variation.actual_profile != fold.evaluation_profile
            or evaluation_control.actual_profile != fold.evaluation_profile
        ):
            raise ValueError("Replication fold received foreign profile evidence.")
        predicted = declaration.rule_family.unseen_profile_default
        variation_match = predicted == evaluation_variation.outcome
        control_match = predicted == evaluation_control.outcome
        joint = variation_match and control_match
        values = {
            "result_version": CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
            "declaration_ref": declaration.declaration_id,
            "fold": fold,
            "fold_ref": fold.fold_id,
            "training_variation_context_ref": training_variation.context_ref,
            "training_variation_observation_ref": training_variation.observation_id,
            "training_variation_observation_sha256": _digest(
                training_variation.model_dump(mode="json")
            ),
            "trained_profile": fold.training_profile,
            "trained_outcome": training_variation.outcome,
            "unseen_profile_default": declaration.rule_family.unseen_profile_default,
            "evaluation_profile": fold.evaluation_profile,
            "predicted_outcome": predicted,
            "evaluation_variation_context_ref": evaluation_variation.context_ref,
            "evaluation_variation_observation_ref": evaluation_variation.observation_id,
            "evaluation_variation_observation_sha256": _digest(
                evaluation_variation.model_dump(mode="json")
            ),
            "evaluation_variation_outcome": evaluation_variation.outcome,
            "evaluation_variation_match": variation_match,
            "evaluation_control_context_ref": evaluation_control.context_ref,
            "evaluation_control_observation_ref": evaluation_control.observation_id,
            "evaluation_control_observation_sha256": _digest(
                evaluation_control.model_dump(mode="json")
            ),
            "evaluation_control_outcome": evaluation_control.outcome,
            "evaluation_control_match": control_match,
            "variation_training_only": True,
            "low_trace_control_consulted_during_fit": False,
            "trace_role_as_prediction_input": False,
            "trace_field_as_prediction_input": False,
            "evaluation_consulted_during_fit": False,
            "rule_applied_unchanged": True,
            "joint_discrimination_observed": joint,
            "rule_family_falsified": not joint,
            "predictive_discrimination_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["result_id"] = stable_id(
            "contradiction_prediction_replication_fold_result", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_result(self) -> "ContradictionPredictionReplicationFoldResult":
        variation_match = self.predicted_outcome == self.evaluation_variation_outcome
        control_match = self.predicted_outcome == self.evaluation_control_outcome
        joint = variation_match and control_match
        if (
            self.result_version != CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
            or self.fold_ref != self.fold.fold_id
            or self.trained_profile != self.fold.training_profile
            or self.evaluation_profile != self.fold.evaluation_profile
            or self.unseen_profile_default
            != ContradictionDownstreamOutcomeDisposition.VALID_NULL
            or self.predicted_outcome != self.unseen_profile_default
            or not all(_is_sha(item) for item in (
                self.training_variation_observation_sha256,
                self.evaluation_variation_observation_sha256,
                self.evaluation_control_observation_sha256,
            ))
            or self.evaluation_variation_match != variation_match
            or self.evaluation_control_match != control_match
            or self.joint_discrimination_observed != joint
            or self.rule_family_falsified != (not joint)
            or not self.variation_training_only
            or self.low_trace_control_consulted_during_fit
            or self.trace_role_as_prediction_input
            or self.trace_field_as_prediction_input
            or self.evaluation_consulted_during_fit
            or not self.rule_applied_unchanged
            or self.predictive_discrimination_observed
            or self.authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Replication fold result crossed its frozen grammar.")
        expected = stable_id(
            "contradiction_prediction_replication_fold_result",
            self.model_dump(mode="json", exclude={"result_id"}),
        )
        if self.result_id != expected:
            raise ValueError("Replication-fold result checksum mismatch.")
        return self


class ContradictionPredictionReplicationContextExecution(FrozenRecord):
    """One replayable context result with both isolated simulation ledgers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    execution_id: str
    execution_version: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
    context_ref: str
    observation: ContradictionPredictionReplicationContextObservation
    observation_sha256: str
    calibration_simulation_state: SimulationLedgerState
    calibration_simulation_sha256: str
    calibration_simulation_fingerprint: str
    held_out_simulation_state: SimulationLedgerState
    held_out_simulation_sha256: str
    held_out_simulation_fingerprint: str

    @classmethod
    def build(
        cls,
        observation: ContradictionPredictionReplicationContextObservation,
        calibration_ledger: SimulationLedger,
        held_out_ledger: SimulationLedger,
    ) -> "ContradictionPredictionReplicationContextExecution":
        observed = ContradictionPredictionReplicationContextObservation.model_validate(
            observation.model_dump(mode="json")
        )
        calibration = calibration_ledger.snapshot()
        held_out = held_out_ledger.snapshot()
        values = {
            "execution_version": CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
            "context_ref": observed.context_ref,
            "observation": observed,
            "observation_sha256": _digest(observed.model_dump(mode="json")),
            "calibration_simulation_state": calibration,
            "calibration_simulation_sha256": _digest(calibration.model_dump(mode="json")),
            "calibration_simulation_fingerprint": calibration_ledger.fingerprint(),
            "held_out_simulation_state": held_out,
            "held_out_simulation_sha256": _digest(held_out.model_dump(mode="json")),
            "held_out_simulation_fingerprint": held_out_ledger.fingerprint(),
        }
        values["execution_id"] = stable_id(
            "contradiction_prediction_replication_context_execution", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_execution(self) -> "ContradictionPredictionReplicationContextExecution":
        calibration = SimulationLedger.from_state(self.calibration_simulation_state)
        held_out = SimulationLedger.from_state(self.held_out_simulation_state)
        if (
            self.execution_version != CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
            or self.context_ref != self.observation.context_ref
            or self.observation_sha256 != _digest(self.observation.model_dump(mode="json"))
            or self.calibration_simulation_sha256
            != _digest(self.calibration_simulation_state.model_dump(mode="json"))
            or self.held_out_simulation_sha256
            != _digest(self.held_out_simulation_state.model_dump(mode="json"))
            or self.calibration_simulation_fingerprint != calibration.fingerprint()
            or self.held_out_simulation_fingerprint != held_out.fingerprint()
        ):
            raise ValueError("Replication context execution digest mismatch.")
        expected = stable_id(
            "contradiction_prediction_replication_context_execution",
            self.model_dump(mode="json", exclude={"execution_id"}),
        )
        if self.execution_id != expected:
            raise ValueError("Replication context-execution checksum mismatch.")
        return self


class ContradictionPredictionReplicationReceipt(FrozenRecord):
    """Four actual contexts and two unchanged group-held-out evaluations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
    declaration: ContradictionPredictionReplicationDeclaration
    declaration_ref: str
    declaration_sha256: str
    preregistration_sha256: str
    context_observations: tuple[
        ContradictionPredictionReplicationContextObservation, ...
    ]
    context_observation_refs: tuple[str, ...]
    context_observation_sha256s: tuple[str, ...]
    fold_results: tuple[
        ContradictionPredictionReplicationFoldResult,
        ContradictionPredictionReplicationFoldResult,
    ]
    all_profiles_observed: bool
    all_count_transitions_matched: bool
    low_controls_valid_null: bool
    high_variations_admission_gain: bool
    outcome_variation_observed: bool
    outcome_varies_with_trace_background: bool
    outcome_varies_with_profile: bool
    replication_plan_falsified: bool
    bounded_rule_family_falsified: bool
    fixed_policy_applied_across_contexts: bool = True
    actual_replication_traces_observed: bool = True
    untouched_low_trace_controls_verified: bool = True
    prior_falsifications_preserved: bool = True
    evidence_preserved: bool = True
    anti_suppression_verified: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionPredictionReplicationDeclaration,
        preregistration_sha256: str,
        executions: Sequence[ContradictionPredictionReplicationContextExecution],
    ) -> "ContradictionPredictionReplicationReceipt":
        by_context = {item.context_ref: item.observation for item in executions}
        if set(by_context) != set(declaration.context_refs):
            raise ValueError("Replication executions do not close the declaration.")
        observations = tuple(by_context[ref] for ref in declaration.context_refs)
        folds = tuple(
            ContradictionPredictionReplicationFoldResult.build(
                declaration, fold, by_context
            )
            for fold in declaration.folds
        )
        lows = tuple(
            item for item in observations
            if item.context.trace_role
            == ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL
        )
        highs = tuple(
            item for item in observations
            if item.context.trace_role
            == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION
        )
        low_null = all(
            item.outcome == ContradictionDownstreamOutcomeDisposition.VALID_NULL
            for item in lows
        )
        high_gain = all(
            item.outcome == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            for item in highs
        )
        profiles = {item.actual_profile for item in observations}
        all_profiles = profiles == set(declaration.required_profiles)
        all_counts = all(item.count_transition_matched_declaration for item in observations)
        by_profile = {
            profile: {
                item.outcome for item in observations if item.actual_profile == profile
            }
            for profile in declaration.required_profiles
        }
        profile_variation = (
            all(len(items) == 1 for items in by_profile.values())
            and len({next(iter(items)) for items in by_profile.values()}) > 1
        )
        values = {
            "receipt_version": CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
            "declaration": declaration,
            "declaration_ref": declaration.declaration_id,
            "declaration_sha256": _digest(declaration.model_dump(mode="json")),
            "preregistration_sha256": preregistration_sha256,
            "context_observations": observations,
            "context_observation_refs": tuple(item.observation_id for item in observations),
            "context_observation_sha256s": tuple(
                _digest(item.model_dump(mode="json")) for item in observations
            ),
            "fold_results": folds,
            "all_profiles_observed": all_profiles,
            "all_count_transitions_matched": all_counts,
            "low_controls_valid_null": low_null,
            "high_variations_admission_gain": high_gain,
            "outcome_variation_observed": len({item.outcome for item in observations}) > 1,
            "outcome_varies_with_trace_background": low_null and high_gain,
            "outcome_varies_with_profile": profile_variation,
            "replication_plan_falsified": not (all_profiles and all_counts),
            "bounded_rule_family_falsified": all(item.rule_family_falsified for item in folds),
            "fixed_policy_applied_across_contexts": True,
            "actual_replication_traces_observed": True,
            "untouched_low_trace_controls_verified": True,
            "prior_falsifications_preserved": True,
            "evidence_preserved": True,
            "anti_suppression_verified": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_prediction_replication_receipt", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionPredictionReplicationReceipt":
        lows = tuple(item for item in self.context_observations if item.context.trace_role
                     == ContradictionPredictionReplicationTraceRole.LOW_TRACE_CONTROL)
        highs = tuple(item for item in self.context_observations if item.context.trace_role
                      == ContradictionPredictionReplicationTraceRole.HIGH_TRACE_VARIATION)
        low_null = all(item.outcome == ContradictionDownstreamOutcomeDisposition.VALID_NULL
                       for item in lows)
        high_gain = all(item.outcome == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
                        for item in highs)
        all_profiles = {item.actual_profile for item in self.context_observations} == set(
            self.declaration.required_profiles
        )
        all_counts = all(item.count_transition_matched_declaration
                         for item in self.context_observations)
        by_profile = {
            profile: {item.outcome for item in self.context_observations
                      if item.actual_profile == profile}
            for profile in self.declaration.required_profiles
        }
        profile_variation = (
            all(len(items) == 1 for items in by_profile.values())
            and len({next(iter(items)) for items in by_profile.values()}) > 1
        )
        if (
            self.receipt_version != CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION
            or self.declaration_ref != self.declaration.declaration_id
            or self.declaration_sha256 != _digest(self.declaration.model_dump(mode="json"))
            or not _is_sha(self.preregistration_sha256)
            or tuple(item.context_ref for item in self.context_observations)
            != self.declaration.context_refs
            or self.context_observation_refs
            != tuple(item.observation_id for item in self.context_observations)
            or self.context_observation_sha256s
            != tuple(_digest(item.model_dump(mode="json")) for item in self.context_observations)
            or tuple(item.fold for item in self.fold_results) != self.declaration.folds
            or self.all_profiles_observed != all_profiles
            or self.all_count_transitions_matched != all_counts
            or self.low_controls_valid_null != low_null
            or self.high_variations_admission_gain != high_gain
            or self.outcome_variation_observed
            != (len({item.outcome for item in self.context_observations}) > 1)
            or self.outcome_varies_with_trace_background != (low_null and high_gain)
            or self.outcome_varies_with_profile != profile_variation
            or self.replication_plan_falsified != (not (all_profiles and all_counts))
            or self.bounded_rule_family_falsified
            != all(item.rule_family_falsified for item in self.fold_results)
        ):
            raise ValueError("Replication receipt altered observed evidence.")
        if any((
            not self.fixed_policy_applied_across_contexts,
            not self.actual_replication_traces_observed,
            not self.untouched_low_trace_controls_verified,
            not self.prior_falsifications_preserved,
            not self.evidence_preserved,
            not self.anti_suppression_verified,
            not self.simulated_only,
            self.predictive_discrimination_observed,
            self.dimensional_separation_observed,
            self.independent_held_out_replication_observed,
            self.authority_enabled,
            self.canonical_commit_permitted,
        )):
            raise ValueError("Replication receipt crossed its claim boundary.")
        expected = stable_id(
            "contradiction_prediction_replication_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected:
            raise ValueError("Replication-receipt checksum mismatch.")
        return self


class ContradictionPredictionReplicationResultEnvelope(BaseModel):
    """Canonical completed sidecar with replayable simulation evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_PREDICTION_REPLICATION_RESULT_FORMAT
    preregistration_sha256: str
    receipt: ContradictionPredictionReplicationReceipt
    receipt_sha256: str
    executions: tuple[ContradictionPredictionReplicationContextExecution, ...]
    execution_sha256s: tuple[str, ...]

    @classmethod
    def build(
        cls,
        preregistration_sha256: str,
        declaration: ContradictionPredictionReplicationDeclaration,
        executions: Sequence[ContradictionPredictionReplicationContextExecution],
    ) -> "ContradictionPredictionReplicationResultEnvelope":
        by_context = {item.context_ref: item for item in executions}
        if set(by_context) != set(declaration.context_refs):
            raise ValueError("Replication result does not close all contexts.")
        ordered = tuple(by_context[ref] for ref in declaration.context_refs)
        receipt = ContradictionPredictionReplicationReceipt.build(
            declaration, preregistration_sha256, ordered
        )
        return cls(
            preregistration_sha256=preregistration_sha256,
            receipt=receipt,
            receipt_sha256=_digest(receipt.model_dump(mode="json")),
            executions=ordered,
            execution_sha256s=tuple(
                _digest(item.model_dump(mode="json")) for item in ordered
            ),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionPredictionReplicationResultEnvelope":
        if (
            self.sidecar_format != CONTRADICTION_PREDICTION_REPLICATION_RESULT_FORMAT
            or not _is_sha(self.preregistration_sha256)
            or self.receipt.preregistration_sha256 != self.preregistration_sha256
            or self.receipt_sha256 != _digest(self.receipt.model_dump(mode="json"))
            or tuple(item.context_ref for item in self.executions)
            != self.receipt.declaration.context_refs
            or tuple(item.observation for item in self.executions)
            != self.receipt.context_observations
            or self.execution_sha256s
            != tuple(_digest(item.model_dump(mode="json")) for item in self.executions)
        ):
            raise ValueError("Replication result sidecar digest mismatch.")
        return self


class ContradictionPredictionReplicationObserver:
    """Map actual after-counts through the one frozen native policy."""

    @staticmethod
    def _candidate(
        declaration_ref: str,
        context: ContradictionPredictionReplicationContext,
        *,
        arm: ContradictionPredictionReplicationArm,
        trace: CounterfactualExecutionTrace,
        count: int,
        policy: ContradictionPredictionReplicationOutcomePolicy,
    ) -> WorkspaceCandidateInput:
        functional = context.pair_context.held_out.controlled_context.functional_context
        return WorkspaceCandidateInput(
            source_kind=WorkspaceSourceKind.CONTRADICTION,
            source_ref=functional.contradiction_ref,
            label=f"replication trace {context.context_id}",
            evidence_refs=functional.protected_evidence_refs,
            resource_request=policy.candidate_resource_fraction,
            persistence_cycles=policy.persistence_cycles,
            signals=WorkspaceSignals(
                evidence_grounding=policy.evidence_grounding_signal,
                contradiction_pressure=min(
                    policy.maximum_pressure, count * policy.pressure_per_structure
                ),
            ),
            metadata={
                "replication_result_version": CONTRADICTION_PREDICTION_REPLICATION_RESULT_VERSION,
                "declaration_ref": declaration_ref,
                "context_ref": context.context_id,
                "trace_role": context.trace_role.value,
                "arm": arm.value,
                "trace_ref": trace.trace_id,
                "trace_field": policy.trace_field,
            },
        )

    def _run_arm(
        self,
        kernel: VerdantKernel,
        declaration_ref: str,
        context: ContradictionPredictionReplicationContext,
        *,
        arm: ContradictionPredictionReplicationArm,
        trace: CounterfactualExecutionTrace,
        policy: ContradictionPredictionReplicationOutcomePolicy,
    ) -> ContradictionPredictionReplicationArmObservation:
        delta = _structure_delta(trace)
        shadow = VerdantKernel.from_state(kernel.snapshot())
        workspace_policy = _workspace_policy(policy)
        shadow.state.workspace_policy = workspace_policy
        semantic_before = _semantic_fingerprint(shadow)
        shadow_input = shadow.fingerprint()
        candidate = self._candidate(
            declaration_ref,
            context,
            arm=arm,
            trace=trace,
            count=delta.after_record_count,
            policy=policy,
        )
        result = VerdantWorkspacePipeline().run_cycle(shadow, (candidate,))
        semantic_after = _semantic_fingerprint(shadow)
        if semantic_after != semantic_before:
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication shadow workspace changed semantic records."
            )
        assessment = result.report.assessments[0]
        return ContradictionPredictionReplicationArmObservation.build(
            declaration_ref=declaration_ref,
            context_ref=context.context_id,
            trace_role=context.trace_role,
            arm=arm,
            trace_ref=trace.trace_id,
            trace_before_structure_count=delta.before_record_count,
            trace_after_structure_count=delta.after_record_count,
            trace_added_structure_count=len(delta.added_record_keys),
            contradiction_pressure=min(
                policy.maximum_pressure,
                delta.after_record_count * policy.pressure_per_structure,
            ),
            source_contradiction_ref=candidate.source_ref,
            source_claim_refs=context.evaluation_claim_refs,
            source_evidence_refs=context.evaluation_evidence_refs,
            workspace_policy=workspace_policy,
            workspace_policy_sha256=_digest(workspace_policy.model_dump(mode="json")),
            candidate_control_signature=_candidate_control_signature(candidate),
            candidate=candidate,
            admission_report=result.report,
            workspace_event=result.event,
            raw_score=assessment.raw_score,
            effective_score=assessment.effective_score,
            admitted=assessment.disposition == WorkspaceDisposition.ADMIT,
            rejection_codes=assessment.rejection_codes,
            shadow_input_fingerprint=shadow_input,
            shadow_output_fingerprint=shadow.fingerprint(),
            semantic_fingerprint=semantic_after,
        )

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        declaration: ContradictionPredictionReplicationDeclaration,
        context: ContradictionPredictionReplicationContext,
        trial_receipt: ContradictionLensHeldOutReplicationReceipt,
    ) -> ContradictionPredictionReplicationContextObservation:
        canonical_before = kernel.fingerprint()
        simulation_before = ledger.fingerprint()
        try:
            if context not in declaration.contexts:
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication observer received an undeclared context."
                )
            trial = ContradictionLensHeldOutReplicationReceipt.model_validate(
                trial_receipt.model_dump(mode="json")
            )
            if trial.pair_context != context.pair_context:
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication observer received a foreign trial receipt."
                )
            _validate_observation_ledger(kernel, ledger, trial.held_out_observation)
            baseline_trace, treatment_trace = _matched_traces(trial.held_out_observation)
            _validate_trace_provenance(baseline_trace, treatment_trace)
            baseline = self._run_arm(
                kernel,
                declaration.declaration_id,
                context,
                arm=ContradictionPredictionReplicationArm.BASELINE,
                trace=baseline_trace,
                policy=declaration.outcome_policy,
            )
            treatment = self._run_arm(
                kernel,
                declaration.declaration_id,
                context,
                arm=ContradictionPredictionReplicationArm.TREATMENT,
                trace=treatment_trace,
                policy=declaration.outcome_policy,
            )
            return ContradictionPredictionReplicationContextObservation.build(
                declaration_ref=declaration.declaration_id,
                context=context,
                trial_receipt=trial,
                baseline=baseline,
                treatment=treatment,
            )
        except ContradictionPredictionReplicationResultIntegrityError:
            raise
        except (
            ContradictionLensTrialIntegrityError,
            SimulationIntegrityError,
            WorkspaceIntegrityError,
            ValueError,
            TypeError,
            KeyError,
            StopIteration,
        ) as exc:
            raise ContradictionPredictionReplicationResultIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError("Replication observer mutated canonical state.")
            if ledger.fingerprint() != simulation_before:
                raise RuntimeError("Replication observer mutated simulation state.")


def contradiction_prediction_replication_result_bytes(
    envelope: ContradictionPredictionReplicationResultEnvelope,
) -> bytes:
    validated = ContradictionPredictionReplicationResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionReplicationResultIntegrityError(
            "Replication result exceeds its size limit."
        )
    return data


def read_contradiction_prediction_replication_result(
    path: str | Path,
) -> ContradictionPredictionReplicationResultEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication result exceeds its size limit."
            )
        envelope = ContradictionPredictionReplicationResultEnvelope.model_validate_json(data)
        if contradiction_prediction_replication_result_bytes(envelope) != data:
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication result is not canonical."
            )
        return envelope
    except ContradictionPredictionReplicationResultIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionReplicationResultIntegrityError(
            "Invalid replication result."
        ) from exc


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise ContradictionPredictionReplicationResultIntegrityError(
            "Replication result sidecars require POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication result path already contains different evidence."
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
                path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
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


def save_contradiction_prediction_replication_result(
    path: str | Path,
    envelope: ContradictionPredictionReplicationResultEnvelope,
) -> str:
    validated = ContradictionPredictionReplicationResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(Path(path), contradiction_prediction_replication_result_bytes(validated))
    return validated.receipt.receipt_id


@dataclass(frozen=True)
class ContradictionPredictionReplicationExecutionInput:
    context: ContradictionPredictionReplicationContextInput
    calibration_runtime: CounterfactualRuntime
    held_out_runtime: CounterfactualRuntime


def _expected_declaration(
    inputs: Sequence[ContradictionPredictionReplicationExecutionInput],
) -> ContradictionPredictionReplicationDeclaration:
    return ContradictionPredictionReplicationDeclaration.build(
        tuple(
            ContradictionPredictionReplicationContext.build(
                item.context.pair_context,
                item.context.calibration_kernel,
                item.context.held_out_kernel,
                item.context.lenses,
                trace_role=item.context.trace_role,
            )
            for item in inputs
        )
    )


def _context_id(item: ContradictionPredictionReplicationExecutionInput) -> str:
    return ContradictionPredictionReplicationContext.build(
        item.context.pair_context,
        item.context.calibration_kernel,
        item.context.held_out_kernel,
        item.context.lenses,
        trace_role=item.context.trace_role,
    ).context_id


def load_contradiction_prediction_replication_result(
    result_path: str | Path,
    preregistration_path: str | Path,
    inputs: Sequence[ContradictionPredictionReplicationExecutionInput],
    *,
    observer: ContradictionPredictionReplicationObserver | None = None,
) -> ContradictionPredictionReplicationResultEnvelope:
    try:
        prereg_path = Path(preregistration_path)
        result = read_contradiction_prediction_replication_result(result_path)
        preregistration = read_contradiction_prediction_replication_preregistration(
            prereg_path
        )
        preregistration_sha256 = _sha(prereg_path.read_bytes())
        if (
            preregistration.declaration != _expected_declaration(inputs)
            or result.preregistration_sha256 != preregistration_sha256
            or result.receipt.declaration != preregistration.declaration
        ):
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication result is paired with different preregistration."
            )
        by_context = {_context_id(item): item for item in inputs}
        verifier = observer or ContradictionPredictionReplicationObserver()
        rebuilt = []
        for execution in result.executions:
            item = by_context.get(execution.context_ref)
            if item is None:
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication result contains a foreign context."
                )
            calibration_ledger = SimulationLedger.from_state(
                execution.calibration_simulation_state
            )
            held_out_ledger = SimulationLedger.from_state(
                execution.held_out_simulation_state
            )
            trial = execution.observation.trial_receipt
            _validate_observation_ledger(
                item.context.calibration_kernel,
                calibration_ledger,
                trial.calibration_observation,
            )
            _validate_observation_ledger(
                item.context.held_out_kernel,
                held_out_ledger,
                trial.held_out_observation,
            )
            observed = verifier.observe(
                item.context.held_out_kernel,
                held_out_ledger,
                declaration=preregistration.declaration,
                context=execution.observation.context,
                trial_receipt=trial,
            )
            replayed_execution = ContradictionPredictionReplicationContextExecution.build(
                observed, calibration_ledger, held_out_ledger
            )
            if replayed_execution != execution:
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication result does not reproduce from actual traces."
                )
            rebuilt.append(replayed_execution)
        expected = ContradictionPredictionReplicationResultEnvelope.build(
            preregistration_sha256,
            preregistration.declaration,
            tuple(rebuilt),
        )
        if expected != result:
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication result changed its frozen fold evaluation."
            )
        return result
    except ContradictionPredictionReplicationResultIntegrityError:
        raise
    except (
        ContradictionPredictionReplicationIntegrityError,
        ContradictionLensTrialIntegrityError,
        LensIntegrityError,
        SimulationIntegrityError,
        WorkspaceIntegrityError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise ContradictionPredictionReplicationResultIntegrityError(str(exc)) from exc


@dataclass(frozen=True)
class ContradictionPredictionReplicationRun:
    preregistration_path: Path
    result_path: Path
    preregistration: ContradictionPredictionReplicationPreregistrationEnvelope
    result: ContradictionPredictionReplicationResultEnvelope
    replayed: bool

    @property
    def receipt(self) -> ContradictionPredictionReplicationReceipt:
        return self.result.receipt


class ContradictionDurablePredictionReplicationRunner:
    """Execute or replay all four contexts only after `.vrp` is durable."""

    def __init__(
        self,
        *,
        trial_runner: ContradictionLensHeldOutTrialRunner | None = None,
        observer: ContradictionPredictionReplicationObserver | None = None,
    ) -> None:
        self.trial_runner = trial_runner or ContradictionLensHeldOutTrialRunner()
        self.observer = observer or ContradictionPredictionReplicationObserver()

    def run(
        self,
        preregistration_path: str | Path,
        result_path: str | Path,
        inputs: Sequence[ContradictionPredictionReplicationExecutionInput],
    ) -> ContradictionPredictionReplicationRun:
        if len(inputs) != CONTRADICTION_PREDICTION_REPLICATION_CONTEXT_COUNT:
            raise ContradictionPredictionReplicationResultIntegrityError(
                "Replication execution requires four context inputs."
            )
        prereg_path = Path(preregistration_path)
        completed_path = Path(result_path)
        items = tuple(inputs)
        canonical_before = tuple((
            item.context.calibration_kernel.fingerprint(),
            item.context.held_out_kernel.fingerprint(),
        ) for item in items)
        lens_before = tuple(item.context.lenses.fingerprint() for item in items)
        runtime_before = tuple((
            item.calibration_runtime.ledger.snapshot(),
            item.held_out_runtime.ledger.snapshot(),
        ) for item in items)
        published = False
        try:
            if not prereg_path.exists():
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication result requires its preexisting .vrp declaration."
                )
            if len({id(runtime) for item in items for runtime in (
                item.calibration_runtime, item.held_out_runtime
            )}) != 2 * len(items):
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication execution requires distinct caller runtimes."
                )
            if any(runtime.ledger.fingerprint() != _EMPTY_LEDGER
                   for item in items for runtime in (
                       item.calibration_runtime, item.held_out_runtime
                   )):
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication execution requires pristine caller ledgers."
                )
            preregistration = read_contradiction_prediction_replication_preregistration(
                prereg_path
            )
            if preregistration.declaration != _expected_declaration(items):
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication inputs differ from the frozen .vrp declaration."
                )
            preregistration_bytes = prereg_path.read_bytes()
            preregistration_sha256 = _sha(preregistration_bytes)
            preexisted = completed_path.exists()
            if preexisted:
                result = load_contradiction_prediction_replication_result(
                    completed_path,
                    prereg_path,
                    items,
                    observer=self.observer,
                )
            else:
                by_context = {_context_id(item): item for item in items}
                executions = []
                for context in preregistration.declaration.contexts:
                    item = by_context[context.context_id]
                    calibration_runtime = CounterfactualRuntime(SimulationLedger())
                    held_out_runtime = CounterfactualRuntime(SimulationLedger())
                    pair = item.context.pair_context
                    trial = self.trial_runner.run(
                        item.context.calibration_kernel,
                        calibration_runtime,
                        item.context.held_out_kernel,
                        held_out_runtime,
                        item.context.lenses,
                        calibration_bundle=(
                            pair.calibration.controlled_context.functional_context.hypothesis_bundle
                        ),
                        held_out_bundle=(
                            pair.held_out.controlled_context.functional_context.hypothesis_bundle
                        ),
                        pair_context=pair,
                    )
                    observation = self.observer.observe(
                        item.context.held_out_kernel,
                        held_out_runtime.ledger,
                        declaration=preregistration.declaration,
                        context=context,
                        trial_receipt=trial.receipt,
                    )
                    executions.append(
                        ContradictionPredictionReplicationContextExecution.build(
                            observation,
                            calibration_runtime.ledger,
                            held_out_runtime.ledger,
                        )
                    )
                    if prereg_path.read_bytes() != preregistration_bytes:
                        raise ContradictionPredictionReplicationResultIntegrityError(
                            "Replication preregistration changed during execution."
                        )
                result = ContradictionPredictionReplicationResultEnvelope.build(
                    preregistration_sha256,
                    preregistration.declaration,
                    tuple(executions),
                )
                save_contradiction_prediction_replication_result(completed_path, result)
                result = load_contradiction_prediction_replication_result(
                    completed_path,
                    prereg_path,
                    items,
                    observer=self.observer,
                )
            if prereg_path.read_bytes() != preregistration_bytes:
                raise ContradictionPredictionReplicationResultIntegrityError(
                    "Replication preregistration changed before publication."
                )
            by_context = {_context_id(item): item for item in items}
            try:
                for execution in result.executions:
                    item = by_context[execution.context_ref]
                    item.calibration_runtime.ledger.state = execution.calibration_simulation_state
                    item.held_out_runtime.ledger.state = execution.held_out_simulation_state
            except Exception:
                for item, snapshots in zip(items, runtime_before, strict=True):
                    item.calibration_runtime.ledger.state = snapshots[0]
                    item.held_out_runtime.ledger.state = snapshots[1]
                raise
            published = True
            return ContradictionPredictionReplicationRun(
                preregistration_path=prereg_path,
                result_path=completed_path,
                preregistration=preregistration,
                result=result,
                replayed=preexisted,
            )
        except ContradictionPredictionReplicationResultIntegrityError:
            raise
        except (
            ContradictionPredictionReplicationIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            WorkspaceIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionPredictionReplicationResultIntegrityError(str(exc)) from exc
        finally:
            for index, item in enumerate(items):
                if (
                    item.context.calibration_kernel.fingerprint() != canonical_before[index][0]
                    or item.context.held_out_kernel.fingerprint() != canonical_before[index][1]
                ):
                    raise RuntimeError("Replication runner mutated canonical state.")
                if item.context.lenses.fingerprint() != lens_before[index]:
                    raise RuntimeError("Replication runner mutated a Lens sidecar.")
            if not published:
                for item, snapshots in zip(items, runtime_before, strict=True):
                    item.calibration_runtime.ledger.state = snapshots[0]
                    item.held_out_runtime.ledger.state = snapshots[1]
