"""Trace-derived downstream outcomes for held-out Contradiction trials.

This explicitly invoked v0.41 experiment extends the durable v0.40
calibration handoff with one separately persisted outcome channel.  Before
calibration starts, a preregistration freezes a native Contradiction workspace
candidate, the one permitted treatment-dependent input, and the bounded
outcome grammar.  After the held-out pair settles, only the *count* of added
structure keys in each real counterfactual trace is mapped to contradiction
pressure and passed through Verdant's native workspace pipeline on isolated
kernel clones.

Added-record identities, Lens projections, and the functional-routing
disposition are not outcome inputs.  Both arms retain the same canonical
Contradiction source, evidence, workspace policy, and resource request.  The
artifacts are experimental sidecars outside VDK/VOB.  They provide no truth,
resolution, promotion, policy-rewrite, or canonical-write authority, and the
internal workspace result is not an external or real-world outcome.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:  # pragma: no cover - non-POSIX operation is rejected explicitly.
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
from verdant_kernel.models import (
    ContradictionRecord,
    FrozenRecord,
    canonical_json_bytes,
    stable_id,
)
from verdant_workspace import VerdantWorkspacePipeline

from .contradiction_calibration_stage import (
    CONTRADICTION_CALIBRATION_STAGE_VERSION,
    ContradictionCalibrationStageIntegrityError,
    ContradictionCalibrationStageSidecarEnvelope,
    ContradictionDurableDimensionTrialRunner,
    load_contradiction_calibration_stage_sidecar,
)
from .contradiction_dimension_criterion import (
    ContradictionDimensionCriterionDeclaration,
)
from .contradiction_hypotheses import ContradictionHypothesisProtocol
from .contradiction_trial_controls import (
    ContradictionLensTrialIntegrityError,
    ContradictionLensTrialObservation,
    ContradictionLensTrialPairContext,
    _validate_observation_ledger,
)
from .counterfactual import (
    CounterfactualExecutionTrace,
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
    SimulationLedgerState,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError


CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION = (
    "contradiction_downstream_outcome_v0.41"
)
CONTRADICTION_DOWNSTREAM_PREREGISTRATION_FORMAT = (
    "verdant-contradiction-downstream-preregistration-v1"
)
CONTRADICTION_DOWNSTREAM_RESULT_FORMAT = (
    "verdant-contradiction-downstream-result-v1"
)
CONTRADICTION_DOWNSTREAM_TRACE_FIELD = (
    "collection_deltas.structures.added_record_keys.count"
)
_MAX_SIDECAR_BYTES = 128 * 1024 * 1024
_EMPTY_SIMULATION_FINGERPRINT = SimulationLedger().fingerprint()


class ContradictionDownstreamOutcomeIntegrityError(RuntimeError):
    """Raised when downstream evidence loses preregistered lineage."""


class ContradictionDownstreamOutcomeDisposition(str, Enum):
    ADMISSION_GAIN = "admission_gain"
    VALID_NULL = "valid_null"


class ContradictionDownstreamOutcomeArm(str, Enum):
    BASELINE = "baseline"
    TREATMENT = "treatment"


CONTRADICTION_DOWNSTREAM_OUTCOME_ALTERNATIVES = tuple(
    ContradictionDownstreamOutcomeDisposition
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value))


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _record_payload(values: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
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


class ContradictionDownstreamOutcomePolicy(BaseModel):
    """Visible mapping from one trace count to workspace pressure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
    trace_field: str = CONTRADICTION_DOWNSTREAM_TRACE_FIELD
    pressure_per_added_structure: float = Field(default=1.0, ge=0.0, le=1.0)
    candidate_resource_fraction: float = Field(default=0.10, gt=0.0, le=1.0)
    persistence_cycles: int = Field(default=1, ge=1, le=1)
    evidence_grounding_signal: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_admission_score: float = Field(default=0.28, ge=0.0, le=1.0)
    count_only_mapping: bool = True
    added_record_identities_permitted: bool = False
    lens_projection_inputs_permitted: bool = False
    functional_disposition_input_permitted: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> "ContradictionDownstreamOutcomePolicy":
        if (
            self.policy_version != CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
            or self.trace_field != CONTRADICTION_DOWNSTREAM_TRACE_FIELD
            or self.pressure_per_added_structure != 1.0
            or self.candidate_resource_fraction != 0.10
            or self.persistence_cycles != 1
            or self.evidence_grounding_signal != 1.0
            or not self.count_only_mapping
            or self.added_record_identities_permitted
            or self.lens_projection_inputs_permitted
            or self.functional_disposition_input_permitted
        ):
            raise ValueError("Downstream outcome mapping crossed its fixed grammar.")
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class ContradictionDownstreamOutcomeDeclaration(FrozenRecord):
    """Outcome source, mapping, and controls frozen before calibration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
    pair_context: ContradictionLensTrialPairContext
    pair_context_ref: str
    calibration_context_ref: str
    held_out_context_ref: str
    matched_control_signature: str
    held_out_canonical_fingerprint: str
    held_out_obligation_ref: str
    source_contradiction: ContradictionRecord
    source_contradiction_ref: str
    source_claim_refs: tuple[str, str]
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
    policy: ContradictionDownstreamOutcomePolicy
    policy_sha256: str
    canonical_workspace_policy_sha256: str
    shadow_workspace_policy: WorkspacePolicy
    shadow_workspace_policy_sha256: str
    candidate_resource_request: float = Field(gt=0.0)
    trace_field: str = CONTRADICTION_DOWNSTREAM_TRACE_FIELD
    admissible_outcomes: tuple[
        ContradictionDownstreamOutcomeDisposition, ...
    ] = CONTRADICTION_DOWNSTREAM_OUTCOME_ALTERNATIVES
    must_be_durable_before_calibration: bool = True
    identical_matched_workspace_controls_required: bool = True
    explicit_valid_null_required: bool = True
    count_only_mapping: bool = True
    source_independence_observed: bool = False
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        pair_context: ContradictionLensTrialPairContext,
        held_out_kernel: VerdantKernel,
        *,
        policy: ContradictionDownstreamOutcomePolicy | None = None,
    ) -> "ContradictionDownstreamOutcomeDeclaration":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        declared_policy = ContradictionDownstreamOutcomePolicy.model_validate(
            (policy or ContradictionDownstreamOutcomePolicy()).model_dump(
                mode="json"
            )
        )
        bundle = pair.held_out.controlled_context.functional_context.hypothesis_bundle
        evidence_receipt = bundle.evidence_receipt
        contradiction = held_out_kernel.state.contradictions.get(
            evidence_receipt.contradiction_ref
        )
        if contradiction is None:
            raise ValueError("Downstream declaration source contradiction is missing.")
        source = ContradictionRecord.model_validate(
            contradiction.model_dump(mode="json")
        )
        canonical_policy = held_out_kernel.state.workspace_policy
        shadow_policy = WorkspacePolicy.model_validate(
            canonical_policy.model_copy(
                update={
                    "minimum_admission_score": (
                        declared_policy.minimum_admission_score
                    ),
                    "revision": canonical_policy.revision + 1,
                }
            ).model_dump(mode="json")
        )
        values = {
            "declaration_version": CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION,
            "pair_context": pair,
            "pair_context_ref": pair.pair_id,
            "calibration_context_ref": pair.calibration.context_id,
            "held_out_context_ref": pair.held_out.context_id,
            "matched_control_signature": pair.matched_control_signature,
            "held_out_canonical_fingerprint": held_out_kernel.fingerprint(),
            "held_out_obligation_ref": bundle.obligation_id,
            "source_contradiction": source,
            "source_contradiction_ref": source.contradiction_id,
            "source_claim_refs": tuple(sorted(source.claim_ids)),
            "source_evidence_refs": tuple(sorted(source.evidence_refs)),
            "policy": declared_policy,
            "policy_sha256": declared_policy.fingerprint(),
            "canonical_workspace_policy_sha256": _digest(
                canonical_policy.model_dump(mode="json")
            ),
            "shadow_workspace_policy": shadow_policy,
            "shadow_workspace_policy_sha256": _digest(
                shadow_policy.model_dump(mode="json")
            ),
            "candidate_resource_request": (
                shadow_policy.resource_budget
                * declared_policy.candidate_resource_fraction
            ),
            "trace_field": CONTRADICTION_DOWNSTREAM_TRACE_FIELD,
            "admissible_outcomes": CONTRADICTION_DOWNSTREAM_OUTCOME_ALTERNATIVES,
            "must_be_durable_before_calibration": True,
            "identical_matched_workspace_controls_required": True,
            "explicit_valid_null_required": True,
            "count_only_mapping": True,
            "source_independence_observed": False,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["declaration_id"] = stable_id(
            "contradiction_downstream_outcome_declaration",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_declaration(
        self,
    ) -> "ContradictionDownstreamOutcomeDeclaration":
        pair = self.pair_context
        bundle = pair.held_out.controlled_context.functional_context.hypothesis_bundle
        evidence_receipt = bundle.evidence_receipt
        if self.declaration_version != CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION:
            raise ValueError("Unknown downstream outcome declaration version.")
        expected_refs = {
            "pair_context_ref": pair.pair_id,
            "calibration_context_ref": pair.calibration.context_id,
            "held_out_context_ref": pair.held_out.context_id,
            "matched_control_signature": pair.matched_control_signature,
            "held_out_canonical_fingerprint": (
                pair.held_out.canonical_checkpoint_fingerprint
            ),
            "held_out_obligation_ref": bundle.obligation_id,
            "source_contradiction_ref": evidence_receipt.contradiction_ref,
        }
        if any(getattr(self, key) != value for key, value in expected_refs.items()):
            raise ValueError("Downstream declaration altered preregistered lineage.")
        if (
            self.source_contradiction.contradiction_id
            != self.source_contradiction_ref
            or self.source_claim_refs
            != tuple(sorted(self.source_contradiction.claim_ids))
            or self.source_claim_refs != evidence_receipt.protected_claim_refs
            or self.source_evidence_refs
            != tuple(sorted(self.source_contradiction.evidence_refs))
            or self.source_evidence_refs != evidence_receipt.protected_evidence_refs
        ):
            raise ValueError("Downstream declaration changed its canonical source.")
        if (
            self.policy_sha256 != self.policy.fingerprint()
            or self.shadow_workspace_policy_sha256
            != _digest(self.shadow_workspace_policy.model_dump(mode="json"))
            or self.shadow_workspace_policy.minimum_admission_score
            != self.policy.minimum_admission_score
            or self.candidate_resource_request
            != self.shadow_workspace_policy.resource_budget
            * self.policy.candidate_resource_fraction
            or not _is_sha256(self.canonical_workspace_policy_sha256)
        ):
            raise ValueError("Downstream declaration changed its workspace policy.")
        if (
            self.trace_field != CONTRADICTION_DOWNSTREAM_TRACE_FIELD
            or self.admissible_outcomes
            != CONTRADICTION_DOWNSTREAM_OUTCOME_ALTERNATIVES
            or not self.must_be_durable_before_calibration
            or not self.identical_matched_workspace_controls_required
            or not self.explicit_valid_null_required
            or not self.count_only_mapping
        ):
            raise ValueError("Downstream declaration changed its outcome grammar.")
        if any(
            (
                self.source_independence_observed,
                self.predictive_discrimination_observed,
                self.dimensional_separation_observed,
                self.external_outcome_observed,
                self.resolution_trial_ready,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.policy_rewrite_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Downstream declaration crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_downstream_outcome_declaration",
            self.model_dump(mode="json", exclude={"declaration_id"}),
        )
        if self.declaration_id != expected_id:
            raise ValueError("Downstream declaration checksum mismatch.")
        return self


class ContradictionDownstreamPreregistrationEnvelope(BaseModel):
    """Canonical bytes proving the outcome grammar existed first."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_DOWNSTREAM_PREREGISTRATION_FORMAT
    declaration: ContradictionDownstreamOutcomeDeclaration
    declaration_sha256: str

    @classmethod
    def build(
        cls,
        declaration: ContradictionDownstreamOutcomeDeclaration,
    ) -> "ContradictionDownstreamPreregistrationEnvelope":
        declared = ContradictionDownstreamOutcomeDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        return cls(
            declaration=declared,
            declaration_sha256=_digest(declared.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(
        self,
    ) -> "ContradictionDownstreamPreregistrationEnvelope":
        if self.sidecar_format != CONTRADICTION_DOWNSTREAM_PREREGISTRATION_FORMAT:
            raise ValueError("Unknown downstream preregistration sidecar format.")
        if self.declaration_sha256 != _digest(
            self.declaration.model_dump(mode="json")
        ):
            raise ValueError("Downstream preregistration digest mismatch.")
        return self


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
        "contradiction_downstream_workspace_control",
        CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION,
        normalized.model_dump(mode="json"),
    )


class ContradictionDownstreamWorkspaceArmObservation(FrozenRecord):
    """One native shadow-workspace result from an actual trace count."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
    declaration_ref: str
    held_out_context_ref: str
    arm: ContradictionDownstreamOutcomeArm
    trace_ref: str
    trace_field: str = CONTRADICTION_DOWNSTREAM_TRACE_FIELD
    trace_added_structure_count: int = Field(ge=0, le=1)
    contradiction_pressure: float = Field(ge=0.0, le=1.0)
    source_contradiction_ref: str
    source_claim_refs: tuple[str, str]
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
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
    actual_trace_count_consumed: bool = True
    trace_record_identities_consulted: bool = False
    lens_projections_consulted: bool = False
    functional_disposition_consulted: bool = False
    canonical_workspace_mutated: bool = False
    semantic_records_preserved: bool = True
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ContradictionDownstreamWorkspaceArmObservation":
        defaults = {
            "observer_version": CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION,
            "trace_field": CONTRADICTION_DOWNSTREAM_TRACE_FIELD,
            "native_workspace_pipeline_executed": True,
            "actual_trace_count_consumed": True,
            "trace_record_identities_consulted": False,
            "lens_projections_consulted": False,
            "functional_disposition_consulted": False,
            "canonical_workspace_mutated": False,
            "semantic_records_preserved": True,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        for key, value in defaults.items():
            values.setdefault(key, value)
        values["observation_id"] = stable_id(
            "contradiction_downstream_workspace_arm", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(
        self,
    ) -> "ContradictionDownstreamWorkspaceArmObservation":
        if (
            self.observer_version != CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
            or self.trace_field != CONTRADICTION_DOWNSTREAM_TRACE_FIELD
            or self.contradiction_pressure
            != float(self.trace_added_structure_count)
        ):
            raise ValueError("Unknown downstream workspace observation grammar.")
        signals = self.candidate.signals
        if (
            self.candidate.source_kind != WorkspaceSourceKind.CONTRADICTION
            or self.candidate.source_ref != self.source_contradiction_ref
            or self.candidate.evidence_refs != self.source_evidence_refs
            or signals.evidence_grounding != 1.0
            or signals.contradiction_pressure != self.contradiction_pressure
            or any(
                getattr(signals, field) != 0.0
                for field in (
                    "relevance",
                    "prediction_error",
                    "action_value",
                    "ethical_salience",
                    "novelty",
                    "resonance",
                )
            )
        ):
            raise ValueError("Downstream workspace candidate changed source or signal.")
        if self.candidate.metadata != {
            "downstream_outcome_version": self.observer_version,
            "declaration_ref": self.declaration_ref,
            "held_out_context_ref": self.held_out_context_ref,
            "arm": self.arm.value,
            "trace_ref": self.trace_ref,
            "trace_field": self.trace_field,
        }:
            raise ValueError("Downstream workspace candidate changed provenance.")
        if self.candidate_control_signature != _candidate_control_signature(
            self.candidate
        ):
            raise ValueError("Downstream matched workspace control was altered.")
        if len(self.admission_report.assessments) != 1:
            raise ValueError("Downstream workspace arm requires one candidate.")
        assessment = self.admission_report.assessments[0]
        if (
            assessment.candidate != self.candidate
            or self.workspace_event.report != self.admission_report
            or self.workspace_event.semantic_mutation_permitted
            or self.raw_score != assessment.raw_score
            or self.effective_score != assessment.effective_score
            or self.rejection_codes != assessment.rejection_codes
            or self.admitted
            != (assessment.disposition == WorkspaceDisposition.ADMIT)
        ):
            raise ValueError("Downstream native workspace result was altered.")
        if any(
            (
                not self.native_workspace_pipeline_executed,
                not self.actual_trace_count_consumed,
                self.trace_record_identities_consulted,
                self.lens_projections_consulted,
                self.functional_disposition_consulted,
                self.canonical_workspace_mutated,
                not self.semantic_records_preserved,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.policy_rewrite_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Downstream workspace observation crossed its boundary.")
        for digest in (
            self.workspace_policy_sha256,
            self.shadow_input_fingerprint,
            self.shadow_output_fingerprint,
            self.semantic_fingerprint,
        ):
            if not _is_sha256(digest):
                raise ValueError("Downstream workspace fingerprint is invalid.")
        if not self.candidate_control_signature.startswith(
            "contradiction_downstream_workspace_control_"
        ):
            raise ValueError("Downstream workspace control signature is invalid.")
        expected_id = stable_id(
            "contradiction_downstream_workspace_arm",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected_id:
            raise ValueError("Downstream workspace observation checksum mismatch.")
        return self


class ContradictionDownstreamOutcomeReceipt(FrozenRecord):
    """Durable trace-to-workspace observation with no authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
    declaration: ContradictionDownstreamOutcomeDeclaration
    preregistration_sha256: str
    calibration_stage_sha256: str
    calibration_stage_receipt_ref: str
    calibration_stage_version: str = CONTRADICTION_CALIBRATION_STAGE_VERSION
    held_out_observation: ContradictionLensTrialObservation
    held_out_observation_ref: str
    baseline: ContradictionDownstreamWorkspaceArmObservation
    treatment: ContradictionDownstreamWorkspaceArmObservation
    disposition: ContradictionDownstreamOutcomeDisposition
    matched_control_signature: str
    source_contradiction_ref: str
    source_claim_refs: tuple[str, str]
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
    outcome_derived_from_actual_experiment_traces: bool = True
    identical_matched_workspace_controls_verified: bool = True
    explicit_valid_null_supported: bool = True
    count_only_trace_mapping_verified: bool = True
    evidence_preserved: bool = True
    anti_suppression_verified: bool = True
    simulated_only: bool = True
    source_independence_observed: bool = False
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        declaration: ContradictionDownstreamOutcomeDeclaration,
        preregistration_sha256: str,
        calibration_stage_sha256: str,
        calibration_stage_receipt_ref: str,
        held_out_observation: ContradictionLensTrialObservation,
        baseline: ContradictionDownstreamWorkspaceArmObservation,
        treatment: ContradictionDownstreamWorkspaceArmObservation,
    ) -> "ContradictionDownstreamOutcomeReceipt":
        declared = ContradictionDownstreamOutcomeDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        observed = ContradictionLensTrialObservation.model_validate(
            held_out_observation.model_dump(mode="json")
        )
        base = ContradictionDownstreamWorkspaceArmObservation.model_validate(
            baseline.model_dump(mode="json")
        )
        treated = ContradictionDownstreamWorkspaceArmObservation.model_validate(
            treatment.model_dump(mode="json")
        )
        disposition = (
            ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            if not base.admitted and treated.admitted
            else ContradictionDownstreamOutcomeDisposition.VALID_NULL
        )
        values = {
            "receipt_version": CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION,
            "declaration": declared,
            "preregistration_sha256": preregistration_sha256,
            "calibration_stage_sha256": calibration_stage_sha256,
            "calibration_stage_receipt_ref": calibration_stage_receipt_ref,
            "calibration_stage_version": CONTRADICTION_CALIBRATION_STAGE_VERSION,
            "held_out_observation": observed,
            "held_out_observation_ref": observed.observation_id,
            "baseline": base,
            "treatment": treated,
            "disposition": disposition,
            "matched_control_signature": base.candidate_control_signature,
            "source_contradiction_ref": declared.source_contradiction_ref,
            "source_claim_refs": declared.source_claim_refs,
            "source_evidence_refs": declared.source_evidence_refs,
            "outcome_derived_from_actual_experiment_traces": True,
            "identical_matched_workspace_controls_verified": True,
            "explicit_valid_null_supported": True,
            "count_only_trace_mapping_verified": True,
            "evidence_preserved": True,
            "anti_suppression_verified": True,
            "simulated_only": True,
            "source_independence_observed": False,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_downstream_outcome_receipt", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionDownstreamOutcomeReceipt":
        if (
            self.receipt_version != CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION
            or self.calibration_stage_version
            != CONTRADICTION_CALIBRATION_STAGE_VERSION
            or not all(
                _is_sha256(value)
                for value in (
                    self.preregistration_sha256,
                    self.calibration_stage_sha256,
                )
            )
        ):
            raise ValueError("Unknown downstream outcome receipt boundary.")
        if (
            self.held_out_observation_ref
            != self.held_out_observation.observation_id
            or self.held_out_observation.context
            != self.declaration.pair_context.held_out
            or self.baseline.arm != ContradictionDownstreamOutcomeArm.BASELINE
            or self.treatment.arm != ContradictionDownstreamOutcomeArm.TREATMENT
            or self.baseline.trace_added_structure_count != 0
            or self.treatment.trace_added_structure_count != 1
            or self.baseline.declaration_ref != self.declaration.declaration_id
            or self.treatment.declaration_ref != self.declaration.declaration_id
        ):
            raise ValueError("Downstream receipt changed held-out trace lineage.")
        if (
            self.baseline.candidate_control_signature
            != self.treatment.candidate_control_signature
            or self.matched_control_signature
            != self.baseline.candidate_control_signature
            or self.baseline.workspace_policy_sha256
            != self.declaration.shadow_workspace_policy_sha256
            or self.treatment.workspace_policy_sha256
            != self.declaration.shadow_workspace_policy_sha256
        ):
            raise ValueError("Downstream receipt changed matched controls.")
        expected_disposition = (
            ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            if not self.baseline.admitted and self.treatment.admitted
            else ContradictionDownstreamOutcomeDisposition.VALID_NULL
        )
        if self.disposition != expected_disposition:
            raise ValueError("Downstream outcome disposition was altered.")
        source = self.declaration
        if (
            self.source_contradiction_ref != source.source_contradiction_ref
            or self.source_claim_refs != source.source_claim_refs
            or self.source_evidence_refs != source.source_evidence_refs
            or any(
                arm.source_contradiction_ref != self.source_contradiction_ref
                or arm.source_claim_refs != self.source_claim_refs
                or arm.source_evidence_refs != self.source_evidence_refs
                for arm in (self.baseline, self.treatment)
            )
        ):
            raise ValueError("Downstream receipt changed protected evidence.")
        if any(
            (
                not self.outcome_derived_from_actual_experiment_traces,
                not self.identical_matched_workspace_controls_verified,
                not self.explicit_valid_null_supported,
                not self.count_only_trace_mapping_verified,
                not self.evidence_preserved,
                not self.anti_suppression_verified,
                not self.simulated_only,
                self.source_independence_observed,
                self.predictive_discrimination_observed,
                self.dimensional_separation_observed,
                self.independent_held_out_replication_observed,
                self.external_outcome_observed,
                self.resolution_trial_ready,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.policy_rewrite_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Downstream receipt crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_downstream_outcome_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected_id:
            raise ValueError("Downstream outcome receipt checksum mismatch.")
        return self


class ContradictionDownstreamResultEnvelope(BaseModel):
    """Completed receipt plus the exact held-out simulation ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_DOWNSTREAM_RESULT_FORMAT
    receipt: ContradictionDownstreamOutcomeReceipt
    receipt_sha256: str
    held_out_simulation_state: SimulationLedgerState
    held_out_simulation_sha256: str
    held_out_simulation_fingerprint: str

    @classmethod
    def build(
        cls,
        receipt: ContradictionDownstreamOutcomeReceipt,
        ledger: SimulationLedger,
    ) -> "ContradictionDownstreamResultEnvelope":
        observed = ContradictionDownstreamOutcomeReceipt.model_validate(
            receipt.model_dump(mode="json")
        )
        state = ledger.snapshot()
        return cls(
            receipt=observed,
            receipt_sha256=_digest(observed.model_dump(mode="json")),
            held_out_simulation_state=state,
            held_out_simulation_sha256=_digest(state.model_dump(mode="json")),
            held_out_simulation_fingerprint=ledger.fingerprint(),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionDownstreamResultEnvelope":
        if self.sidecar_format != CONTRADICTION_DOWNSTREAM_RESULT_FORMAT:
            raise ValueError("Unknown downstream result sidecar format.")
        if (
            self.receipt_sha256 != _digest(self.receipt.model_dump(mode="json"))
            or self.held_out_simulation_sha256
            != _digest(self.held_out_simulation_state.model_dump(mode="json"))
            or not _is_sha256(self.held_out_simulation_fingerprint)
        ):
            raise ValueError("Downstream result sidecar digest mismatch.")
        return self


def _matched_traces(
    observation: ContradictionLensTrialObservation,
) -> tuple[CounterfactualExecutionTrace, CounterfactualExecutionTrace]:
    matched = (
        observation.lens_observation.functional_observation
        .provenance_observation.matched_observation
    )
    return matched.baseline, matched.treatment


def _trace_added_count(trace: CounterfactualExecutionTrace) -> int:
    """Read only the preregistered collection/key count, never key values."""

    structures = next(
        delta for delta in trace.collection_deltas if delta.collection == "structures"
    )
    return len(structures.added_record_keys)


def _validate_trace_shape(
    baseline: CounterfactualExecutionTrace,
    treatment: CounterfactualExecutionTrace,
) -> None:
    if baseline.match_signature != treatment.match_signature:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream outcome traces are not a matched pair."
        )
    for trace, expected_count, label in (
        (baseline, 0, "baseline"),
        (treatment, 1, "treatment"),
    ):
        if _trace_added_count(trace) != expected_count:
            raise ContradictionDownstreamOutcomeIntegrityError(
                f"Downstream {label} trace changed its preregistered count."
            )
        if any(
            delta.removed_record_keys or delta.changed_record_keys
            for delta in trace.collection_deltas
        ):
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream trace changed canonical record classes."
            )
        if any(
            delta.added_record_keys
            for delta in trace.collection_deltas
            if delta.collection != "structures"
        ):
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream trace changed an undeclared collection."
            )


def _validate_declaration(
    declaration: ContradictionDownstreamOutcomeDeclaration,
    held_out_kernel: VerdantKernel,
) -> None:
    if held_out_kernel.fingerprint() != declaration.held_out_canonical_fingerprint:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream declaration is paired with different canonical state."
        )
    expected = ContradictionDownstreamOutcomeDeclaration.build(
        declaration.pair_context,
        held_out_kernel,
        policy=declaration.policy,
    )
    if declaration != expected:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream declaration is stale or substituted."
        )


class ContradictionDownstreamOutcomeObserver:
    """Map matched trace counts through native isolated workspace cycles."""

    @staticmethod
    def _candidate(
        declaration: ContradictionDownstreamOutcomeDeclaration,
        *,
        arm: ContradictionDownstreamOutcomeArm,
        trace: CounterfactualExecutionTrace,
        count: int,
    ) -> WorkspaceCandidateInput:
        return WorkspaceCandidateInput(
            source_kind=WorkspaceSourceKind.CONTRADICTION,
            source_ref=declaration.source_contradiction_ref,
            label=f"trace-derived contradiction {declaration.source_contradiction_ref}",
            evidence_refs=declaration.source_evidence_refs,
            resource_request=declaration.candidate_resource_request,
            persistence_cycles=declaration.policy.persistence_cycles,
            signals=WorkspaceSignals(
                evidence_grounding=declaration.policy.evidence_grounding_signal,
                relevance=0.0,
                prediction_error=0.0,
                contradiction_pressure=min(
                    1.0,
                    count * declaration.policy.pressure_per_added_structure,
                ),
                action_value=0.0,
                ethical_salience=0.0,
                novelty=0.0,
                resonance=0.0,
            ),
            metadata={
                "downstream_outcome_version": CONTRADICTION_DOWNSTREAM_OUTCOME_VERSION,
                "declaration_ref": declaration.declaration_id,
                "held_out_context_ref": declaration.held_out_context_ref,
                "arm": arm.value,
                "trace_ref": trace.trace_id,
                "trace_field": declaration.trace_field,
            },
        )

    def _run_arm(
        self,
        kernel: VerdantKernel,
        declaration: ContradictionDownstreamOutcomeDeclaration,
        *,
        arm: ContradictionDownstreamOutcomeArm,
        trace: CounterfactualExecutionTrace,
    ) -> ContradictionDownstreamWorkspaceArmObservation:
        count = _trace_added_count(trace)
        shadow = VerdantKernel.from_state(kernel.snapshot())
        shadow.state.workspace_policy = WorkspacePolicy.model_validate(
            declaration.shadow_workspace_policy.model_dump(mode="json")
        )
        semantic_before = _semantic_fingerprint(shadow)
        shadow_input = shadow.fingerprint()
        candidate = self._candidate(
            declaration,
            arm=arm,
            trace=trace,
            count=count,
        )
        result = VerdantWorkspacePipeline().run_cycle(shadow, (candidate,))
        semantic_after = _semantic_fingerprint(shadow)
        if semantic_after != semantic_before:
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream shadow workspace changed semantic records."
            )
        assessment = result.report.assessments[0]
        return ContradictionDownstreamWorkspaceArmObservation.build(
            declaration_ref=declaration.declaration_id,
            held_out_context_ref=declaration.held_out_context_ref,
            arm=arm,
            trace_ref=trace.trace_id,
            trace_added_structure_count=count,
            contradiction_pressure=float(count),
            source_contradiction_ref=declaration.source_contradiction_ref,
            source_claim_refs=declaration.source_claim_refs,
            source_evidence_refs=declaration.source_evidence_refs,
            workspace_policy_sha256=declaration.shadow_workspace_policy_sha256,
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
        declaration: ContradictionDownstreamOutcomeDeclaration,
        preregistration_sha256: str,
        calibration_stage_sha256: str,
        calibration_stage_receipt_ref: str,
        held_out_observation: ContradictionLensTrialObservation,
    ) -> ContradictionDownstreamOutcomeReceipt:
        canonical_before = kernel.fingerprint()
        simulation_before = ledger.fingerprint()
        try:
            declared = ContradictionDownstreamOutcomeDeclaration.model_validate(
                declaration.model_dump(mode="json")
            )
            observed = ContradictionLensTrialObservation.model_validate(
                held_out_observation.model_dump(mode="json")
            )
            _validate_declaration(declared, kernel)
            if observed.context != declared.pair_context.held_out:
                raise ContradictionDownstreamOutcomeIntegrityError(
                    "Downstream observer received a foreign held-out context."
                )
            _validate_observation_ledger(kernel, ledger, observed)
            baseline_trace, treatment_trace = _matched_traces(observed)
            _validate_trace_shape(baseline_trace, treatment_trace)
            baseline = self._run_arm(
                kernel,
                declared,
                arm=ContradictionDownstreamOutcomeArm.BASELINE,
                trace=baseline_trace,
            )
            treatment = self._run_arm(
                kernel,
                declared,
                arm=ContradictionDownstreamOutcomeArm.TREATMENT,
                trace=treatment_trace,
            )
            return ContradictionDownstreamOutcomeReceipt.build(
                declaration=declared,
                preregistration_sha256=preregistration_sha256,
                calibration_stage_sha256=calibration_stage_sha256,
                calibration_stage_receipt_ref=calibration_stage_receipt_ref,
                held_out_observation=observed,
                baseline=baseline,
                treatment=treatment,
            )
        except ContradictionDownstreamOutcomeIntegrityError:
            raise
        except (
            ContradictionCalibrationStageIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            WorkspaceIntegrityError,
            ValueError,
            TypeError,
            KeyError,
            StopIteration,
        ) as exc:
            raise ContradictionDownstreamOutcomeIntegrityError(str(exc)) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError("Downstream observer mutated canonical state.")
            if ledger.fingerprint() != simulation_before:
                raise RuntimeError("Downstream observer mutated simulation state.")


def contradiction_downstream_preregistration_bytes(
    envelope: ContradictionDownstreamPreregistrationEnvelope,
) -> bytes:
    validated = ContradictionDownstreamPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream preregistration exceeds its size limit."
        )
    return data


def contradiction_downstream_result_bytes(
    envelope: ContradictionDownstreamResultEnvelope,
) -> bytes:
    validated = ContradictionDownstreamResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream result exceeds its size limit."
        )
    return data


def read_contradiction_downstream_preregistration(
    path: str | Path,
) -> ContradictionDownstreamPreregistrationEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream preregistration exceeds its size limit."
            )
        envelope = ContradictionDownstreamPreregistrationEnvelope.model_validate_json(
            data
        )
        if contradiction_downstream_preregistration_bytes(envelope) != data:
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream preregistration JSON is not canonical."
            )
        return envelope
    except ContradictionDownstreamOutcomeIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Invalid downstream preregistration sidecar."
        ) from exc


def read_contradiction_downstream_result(
    path: str | Path,
) -> ContradictionDownstreamResultEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream result exceeds its size limit."
            )
        envelope = ContradictionDownstreamResultEnvelope.model_validate_json(data)
        if contradiction_downstream_result_bytes(envelope) != data:
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream result JSON is not canonical."
            )
        return envelope
    except ContradictionDownstreamOutcomeIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Invalid downstream result sidecar."
        ) from exc


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream writer arbitration requires POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(_lock_path(path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise ContradictionDownstreamOutcomeIntegrityError(
                "Downstream sidecar path already committed different evidence."
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


def save_contradiction_downstream_preregistration(
    path: str | Path,
    envelope: ContradictionDownstreamPreregistrationEnvelope,
    *,
    held_out_kernel: VerdantKernel,
) -> str:
    validated = ContradictionDownstreamPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _validate_declaration(validated.declaration, held_out_kernel)
    _write_immutable(
        Path(path), contradiction_downstream_preregistration_bytes(validated)
    )
    return validated.declaration.declaration_id


def load_contradiction_downstream_preregistration(
    path: str | Path,
    *,
    held_out_kernel: VerdantKernel,
) -> ContradictionDownstreamPreregistrationEnvelope:
    envelope = read_contradiction_downstream_preregistration(path)
    _validate_declaration(envelope.declaration, held_out_kernel)
    return envelope


def _validate_stage(
    stage_path: str | Path,
    declaration: ContradictionDownstreamOutcomeDeclaration,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> ContradictionCalibrationStageSidecarEnvelope:
    stage = load_contradiction_calibration_stage_sidecar(
        stage_path,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    if stage.stage_receipt.pair_context != declaration.pair_context:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream outcome is paired with a foreign calibration stage."
        )
    return stage


def save_contradiction_downstream_result(
    path: str | Path,
    envelope: ContradictionDownstreamResultEnvelope,
) -> str:
    validated = ContradictionDownstreamResultEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(Path(path), contradiction_downstream_result_bytes(validated))
    return validated.receipt.receipt_id


def load_contradiction_downstream_result(
    result_path: str | Path,
    preregistration_path: str | Path,
    stage_path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    observer: ContradictionDownstreamOutcomeObserver | None = None,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> ContradictionDownstreamResultEnvelope:
    preregistration = load_contradiction_downstream_preregistration(
        preregistration_path,
        held_out_kernel=held_out_kernel,
    )
    stage = _validate_stage(
        stage_path,
        preregistration.declaration,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    envelope = read_contradiction_downstream_result(result_path)
    receipt = envelope.receipt
    preregistration_sha256 = _sha256_bytes(Path(preregistration_path).read_bytes())
    stage_sha256 = _sha256_bytes(Path(stage_path).read_bytes())
    if (
        receipt.declaration != preregistration.declaration
        or receipt.preregistration_sha256 != preregistration_sha256
        or receipt.calibration_stage_sha256 != stage_sha256
        or receipt.calibration_stage_receipt_ref
        != stage.stage_receipt.stage_receipt_id
    ):
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream result lost preregistration or calibration lineage."
        )
    ledger = SimulationLedger.from_state(envelope.held_out_simulation_state)
    if ledger.fingerprint() != envelope.held_out_simulation_fingerprint:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream result embedded a different simulation ledger."
        )
    reproduced = (observer or ContradictionDownstreamOutcomeObserver()).observe(
        held_out_kernel,
        ledger,
        declaration=preregistration.declaration,
        preregistration_sha256=preregistration_sha256,
        calibration_stage_sha256=stage_sha256,
        calibration_stage_receipt_ref=stage.stage_receipt.stage_receipt_id,
        held_out_observation=receipt.held_out_observation,
    )
    if reproduced != receipt:
        raise ContradictionDownstreamOutcomeIntegrityError(
            "Downstream result does not reproduce from actual traces."
        )
    return envelope


@dataclass(frozen=True)
class ContradictionDownstreamOutcomeRun:
    preregistration_path: Path
    stage_path: Path
    result_path: Path
    preregistration: ContradictionDownstreamPreregistrationEnvelope
    stage: ContradictionCalibrationStageSidecarEnvelope
    result: ContradictionDownstreamResultEnvelope
    calibration_ledger: SimulationLedger
    held_out_ledger: SimulationLedger
    replayed: bool

    @property
    def receipt(self) -> ContradictionDownstreamOutcomeReceipt:
        return self.result.receipt


class ContradictionDurableDownstreamOutcomeRunner:
    """Preregister, stage calibration, then publish held-out outcome."""

    def __init__(
        self,
        *,
        dimension_runner: ContradictionDurableDimensionTrialRunner | None = None,
        observer: ContradictionDownstreamOutcomeObserver | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.dimension_runner = (
            dimension_runner
            or ContradictionDurableDimensionTrialRunner(
                hypothesis_protocol=self.hypothesis_protocol
            )
        )
        self.observer = observer or ContradictionDownstreamOutcomeObserver()

    def run(
        self,
        preregistration_path: str | Path,
        stage_path: str | Path,
        result_path: str | Path,
        calibration_kernel: VerdantKernel,
        calibration_runtime: CounterfactualRuntime,
        held_out_kernel: VerdantKernel,
        held_out_runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
        *,
        pair_context: ContradictionLensTrialPairContext,
        criterion_declaration: ContradictionDimensionCriterionDeclaration,
        outcome_policy: ContradictionDownstreamOutcomePolicy | None = None,
    ) -> ContradictionDownstreamOutcomeRun:
        pre_path = Path(preregistration_path)
        calibration_path = Path(stage_path)
        completed_path = Path(result_path)
        canonical_before = (
            calibration_kernel.fingerprint(),
            held_out_kernel.fingerprint(),
        )
        lens_before = lenses.fingerprint()
        calibration_before = calibration_runtime.ledger.fingerprint()
        held_out_before = held_out_runtime.ledger.fingerprint()
        original_calibration = calibration_runtime.ledger.snapshot()
        original_held_out = held_out_runtime.ledger.snapshot()
        published = False
        try:
            if (
                calibration_before != _EMPTY_SIMULATION_FINGERPRINT
                or held_out_before != _EMPTY_SIMULATION_FINGERPRINT
            ):
                raise ContradictionDownstreamOutcomeIntegrityError(
                    "Downstream runner requires pristine caller simulation ledgers."
                )
            expected_declaration = ContradictionDownstreamOutcomeDeclaration.build(
                pair_context,
                held_out_kernel,
                policy=outcome_policy,
            )
            if calibration_path.exists() and not pre_path.exists():
                raise ContradictionDownstreamOutcomeIntegrityError(
                    "Calibration stage predates downstream preregistration."
                )
            if pre_path.exists():
                preregistration = load_contradiction_downstream_preregistration(
                    pre_path,
                    held_out_kernel=held_out_kernel,
                )
                if preregistration.declaration != expected_declaration:
                    raise ContradictionDownstreamOutcomeIntegrityError(
                        "Existing downstream preregistration is different."
                    )
            else:
                preregistration = ContradictionDownstreamPreregistrationEnvelope.build(
                    expected_declaration
                )
                save_contradiction_downstream_preregistration(
                    pre_path,
                    preregistration,
                    held_out_kernel=held_out_kernel,
                )
            preregistration_bytes = pre_path.read_bytes()
            preregistration_sha256 = _sha256_bytes(preregistration_bytes)

            if completed_path.exists():
                if not calibration_path.exists():
                    raise ContradictionDownstreamOutcomeIntegrityError(
                        "Completed result is missing its calibration stage."
                    )
                result = load_contradiction_downstream_result(
                    completed_path,
                    pre_path,
                    calibration_path,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    observer=self.observer,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                stage = _validate_stage(
                    calibration_path,
                    preregistration.declaration,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                calibration_ledger = SimulationLedger.from_state(
                    stage.calibration_simulation_state
                )
                held_out_ledger = SimulationLedger.from_state(
                    result.held_out_simulation_state
                )
                calibration_runtime.ledger.state = calibration_ledger.snapshot()
                held_out_runtime.ledger.state = held_out_ledger.snapshot()
                published = True
                return ContradictionDownstreamOutcomeRun(
                    preregistration_path=pre_path,
                    stage_path=calibration_path,
                    result_path=completed_path,
                    preregistration=preregistration,
                    stage=stage,
                    result=result,
                    calibration_ledger=calibration_ledger,
                    held_out_ledger=held_out_ledger,
                    replayed=True,
                )

            if calibration_path.exists():
                stage = _validate_stage(
                    calibration_path,
                    preregistration.declaration,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                calibration_ledger = SimulationLedger.from_state(
                    stage.calibration_simulation_state
                )
            else:
                stage_run = self.dimension_runner.prepare_and_persist(
                    calibration_path,
                    calibration_kernel,
                    calibration_runtime,
                    held_out_kernel,
                    lenses,
                    pair_context=pair_context,
                    criterion_declaration=criterion_declaration,
                )
                stage = stage_run.envelope
                calibration_ledger = SimulationLedger.from_state(
                    stage.calibration_simulation_state
                )
            if pre_path.read_bytes() != preregistration_bytes:
                raise ContradictionDownstreamOutcomeIntegrityError(
                    "Downstream preregistration changed during calibration."
                )
            stage_bytes = calibration_path.read_bytes()
            stage_sha256 = _sha256_bytes(stage_bytes)
            private_held_out = CounterfactualRuntime()
            resumed = self.dimension_runner.resume_from_stage(
                calibration_path,
                calibration_kernel,
                held_out_kernel,
                private_held_out,
                lenses,
            )
            held_out_observation = ContradictionLensTrialObservation.build(
                context=pair_context.held_out,
                run=resumed.held_out_run,
            )
            receipt = self.observer.observe(
                held_out_kernel,
                private_held_out.ledger,
                declaration=preregistration.declaration,
                preregistration_sha256=preregistration_sha256,
                calibration_stage_sha256=stage_sha256,
                calibration_stage_receipt_ref=stage.stage_receipt.stage_receipt_id,
                held_out_observation=held_out_observation,
            )
            result = ContradictionDownstreamResultEnvelope.build(
                receipt,
                private_held_out.ledger,
            )
            save_contradiction_downstream_result(completed_path, result)
            if (
                pre_path.read_bytes() != preregistration_bytes
                or calibration_path.read_bytes() != stage_bytes
            ):
                raise ContradictionDownstreamOutcomeIntegrityError(
                    "Upstream durable evidence changed during outcome publication."
                )
            calibration_runtime.ledger.state = calibration_ledger.snapshot()
            held_out_runtime.ledger.state = private_held_out.ledger.snapshot()
            held_out_ledger = SimulationLedger.from_state(
                private_held_out.ledger.snapshot()
            )
            published = True
            return ContradictionDownstreamOutcomeRun(
                preregistration_path=pre_path,
                stage_path=calibration_path,
                result_path=completed_path,
                preregistration=preregistration,
                stage=stage,
                result=result,
                calibration_ledger=calibration_ledger,
                held_out_ledger=held_out_ledger,
                replayed=False,
            )
        except ContradictionDownstreamOutcomeIntegrityError:
            raise
        except (
            ContradictionCalibrationStageIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            WorkspaceIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            StopIteration,
        ) as exc:
            raise ContradictionDownstreamOutcomeIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError("Downstream runner mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Downstream runner mutated its Lens sidecar.")
            if not published:
                if held_out_runtime.ledger.fingerprint() != held_out_before:
                    held_out_runtime.ledger.state = original_held_out
                    raise RuntimeError(
                        "Failed downstream run published held-out simulation state."
                    )
                if (
                    not calibration_path.exists()
                    and calibration_runtime.ledger.fingerprint()
                    != calibration_before
                ):
                    calibration_runtime.ledger.state = original_calibration
                    raise RuntimeError(
                        "Failed downstream run published unstaged calibration state."
                    )
