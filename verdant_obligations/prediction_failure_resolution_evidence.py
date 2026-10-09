"""Non-authoritative coverage of the completed PredictionFailure experiment.

A changed governance-risk proxy is diagnostic evidence, not a repaired physical
forecast. This version records the missing contract prerequisites explicitly;
it has no protocol for supplying them or producing a passing Resolution result.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .prediction_failure_trial_plans import (
    _write_immutable, load_prediction_failure_trial_plan,
)
from .prediction_failure_trial_preregistration import (
    PredictionFailureTrialDeclaration, PredictionFailureTrialDisposition,
    PredictionFailureTrialPreregistrationEnvelope,
    prediction_failure_trial_preregistration_bytes,
)
from .prediction_failure_trial_runner import (
    PredictionFailureTrialResult, PredictionFailureTrialResultEnvelope,
    load_prediction_failure_trial_result, prediction_failure_trial_result_bytes,
)

PREDICTION_FAILURE_RESOLUTION_EVIDENCE_VERSION = (
    "prediction_failure_resolution_evidence_v0.52"
)
PREDICTION_FAILURE_RESOLUTION_EVIDENCE_FORMAT = (
    "verdant-prediction-failure-resolution-evidence-v1"
)
PREDICTION_FAILURE_RESOLUTION_EVIDENCE_SIDECAR_SUFFIX = ".vfe"
_MAX_SIDECAR_BYTES = 16 * 1024 * 1024


class PredictionFailureResolutionEvidenceIntegrityError(RuntimeError):
    """Coverage lost its completed-trial provenance or authority boundary."""


class PredictionFailureResolutionRequirement(str, Enum):
    ATTENTION_AUTHORIZATION = "attention_authorization"
    BOUNDED_RESOURCE_USE = "bounded_resource_use"
    CALIBRATED_PHYSICAL_PREDICTION = "calibrated_physical_prediction"
    CANONICAL_CHECKPOINT = "canonical_checkpoint"
    CANONICAL_RECORD_PRESERVATION = "canonical_record_preservation"
    CAUSAL_REPAIR_EVIDENCE = "causal_repair_evidence"
    COMPLETE_EVIDENCE_LINEAGE = "complete_evidence_lineage"
    ERROR_REDUCTION = "error_reduction"
    FROZEN_PREREGISTRATION = "frozen_preregistration"
    INDEPENDENT_HELD_OUT_REPLICATION = "independent_held_out_replication"
    MATCHED_CONTROLS = "matched_controls"
    NULL_INCONCLUSIVE_COUNTERWEIGHTS = "null_inconclusive_counterweights"
    SETTLEMENT_LINEAGE = "settlement_lineage"
    SOURCE_INDEPENDENCE = "source_independence"
    SUFFICIENT_PREDICTION_EVIDENCE = "sufficient_prediction_evidence"
    TARGET_SPECIFIC_ERROR_CHANGE = "target_specific_error_change"
    TRACE_DERIVED_PREDICTIONS = "trace_derived_predictions"
    VALID_NULL = "valid_null"


# Structural coverage follows only from exact provenance-aware trial loading.
# Numeric availability, null equality, change and direction are derived below.
_STRUCTURAL_REQUIREMENTS = (
    PredictionFailureResolutionRequirement.ATTENTION_AUTHORIZATION,
    PredictionFailureResolutionRequirement.BOUNDED_RESOURCE_USE,
    PredictionFailureResolutionRequirement.CANONICAL_CHECKPOINT,
    PredictionFailureResolutionRequirement.CANONICAL_RECORD_PRESERVATION,
    PredictionFailureResolutionRequirement.COMPLETE_EVIDENCE_LINEAGE,
    PredictionFailureResolutionRequirement.FROZEN_PREREGISTRATION,
    PredictionFailureResolutionRequirement.MATCHED_CONTROLS,
    PredictionFailureResolutionRequirement.NULL_INCONCLUSIVE_COUNTERWEIGHTS,
    PredictionFailureResolutionRequirement.SETTLEMENT_LINEAGE,
    PredictionFailureResolutionRequirement.TRACE_DERIVED_PREDICTIONS,
)
PREDICTION_FAILURE_UNPROVEN_RESOLUTION_REQUIREMENTS = (
    PredictionFailureResolutionRequirement.CALIBRATED_PHYSICAL_PREDICTION,
    PredictionFailureResolutionRequirement.CAUSAL_REPAIR_EVIDENCE,
    PredictionFailureResolutionRequirement.INDEPENDENT_HELD_OUT_REPLICATION,
    PredictionFailureResolutionRequirement.SOURCE_INDEPENDENCE,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _coverage(result: PredictionFailureTrialResult):
    baseline, ablation, null = result.absolute_errors
    sufficient = all(error is not None for error in (baseline, ablation, null))
    valid_null = baseline is not None and null is not None and (
        result.valid_null_error_delta == result.outcome_policy.valid_null_max_error_delta
    )
    changed = result.disposition == PredictionFailureTrialDisposition.TARGET_ERROR_CHANGED
    reduction = None if baseline is None or ablation is None else baseline - ablation
    improved = sufficient and valid_null and changed and (
        reduction >= result.outcome_policy.target_error_change_threshold
    )
    grounded = set(_STRUCTURAL_REQUIREMENTS)
    for requirement, passed in (
        (PredictionFailureResolutionRequirement.SUFFICIENT_PREDICTION_EVIDENCE, sufficient),
        (PredictionFailureResolutionRequirement.VALID_NULL, valid_null),
        (PredictionFailureResolutionRequirement.TARGET_SPECIFIC_ERROR_CHANGE, changed),
        (PredictionFailureResolutionRequirement.ERROR_REDUCTION, improved),
    ):
        if passed:
            grounded.add(requirement)
    missing = set(PredictionFailureResolutionRequirement) - grounded
    return (tuple(sorted(grounded, key=lambda item: item.value)),
            tuple(sorted(missing, key=lambda item: item.value)), reduction, changed, improved)


def _values(result, declaration, result_bytes):
    evidence = declaration.hypothesis_bundle.evidence_receipt
    grounded, missing, reduction, changed, improved = _coverage(result)
    return dict(
        evidence_version=PREDICTION_FAILURE_RESOLUTION_EVIDENCE_VERSION,
        declaration=declaration.model_dump(mode="json"),
        completed_result=result.model_dump(mode="json"),
        completed_result_ref=result.result_id,
        completed_result_sha256=_sha(result_bytes),
        preregistration_ref=declaration.declaration_id,
        risk_receipt_ref=result.risk_receipt.receipt_id,
        canonical_kernel_id=declaration.canonical_kernel_id,
        canonical_fingerprint=declaration.canonical_fingerprint,
        canonical_cycle=declaration.canonical_cycle,
        obligation_id=evidence.obligation_id,
        obligation_event_ref=evidence.obligation_event_ref,
        hypothesis_bundle_ref=declaration.hypothesis_bundle_ref,
        evidence_receipt_ref=evidence.receipt_id,
        protected_evidence_refs=evidence.protected_evidence_refs,
        attention_decision_ref=evidence.attention_decision_ref,
        attention_allocation_ref=evidence.attention_allocation_ref,
        trace_refs=tuple(t.trace_id for t in result.traces),
        observation_refs=tuple(t.prediction_failure_trial_observation.observation_id
                               for t in result.traces),
        reservation_refs=tuple(t.native_trace.reservation_id for t in result.traces),
        settlement_refs=tuple(t.native_trace.settlement_id for t in result.traces),
        trial_disposition=result.disposition,
        signed_proxy_error_reduction=reduction,
        target_error_change_observed=changed,
        proxy_error_reduction_observed=improved,
        grounded_requirements=grounded, missing_requirements=missing,
        resolution_contract_satisfied=not missing,
        resolution_trial_ready=False,
        simulated_only=True, causal_attribution_enabled=False,
        observed_outcome_authority_enabled=False, resolution_authority_enabled=False,
        promotion_authority_enabled=False, policy_rewrite_authority_enabled=False,
        canonical_commit_permitted=False,
    )


class PredictionFailureResolutionEvidenceReceipt(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    evidence_version: str = PREDICTION_FAILURE_RESOLUTION_EVIDENCE_VERSION
    declaration: PredictionFailureTrialDeclaration
    completed_result: PredictionFailureTrialResult
    completed_result_ref: str
    completed_result_sha256: str
    preregistration_ref: str
    risk_receipt_ref: str
    canonical_kernel_id: str
    canonical_fingerprint: str
    canonical_cycle: int = Field(ge=0)
    obligation_id: str
    obligation_event_ref: str
    hypothesis_bundle_ref: str
    evidence_receipt_ref: str
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    attention_decision_ref: str
    attention_allocation_ref: str
    trace_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    observation_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    reservation_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    settlement_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    trial_disposition: PredictionFailureTrialDisposition
    signed_proxy_error_reduction: float | None = Field(default=None, ge=-1.0, le=1.0)
    target_error_change_observed: bool
    proxy_error_reduction_observed: bool
    grounded_requirements: tuple[PredictionFailureResolutionRequirement, ...]
    missing_requirements: tuple[PredictionFailureResolutionRequirement, ...]
    resolution_contract_satisfied: bool = False
    resolution_trial_ready: bool = False
    simulated_only: bool = True
    causal_attribution_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, *, result, declaration, result_bytes):
        result = PredictionFailureTrialResult.model_validate(result.model_dump(mode="json"))
        declaration = PredictionFailureTrialDeclaration.model_validate(
            declaration.model_dump(mode="json"))
        values = _values(result, declaration, result_bytes)
        payload = canonical_json_bytes(values)
        # stable_id consumes the same JSON mapping used by ordinary model dumps.
        return cls(receipt_id=stable_id("prediction_failure_resolution_evidence_receipt",
                                        json.loads(payload)), **values)

    @model_validator(mode="after")
    def check_coverage(self):
        declaration, result = self.declaration, self.completed_result
        receipt = result.risk_receipt
        prereg_bytes = prediction_failure_trial_preregistration_bytes(
            PredictionFailureTrialPreregistrationEnvelope.build(declaration))
        if (receipt.preregistration_ref != declaration.declaration_id
            or receipt.preregistration_sha256 != _sha(prereg_bytes)
            or receipt.canonical_kernel_id != declaration.canonical_kernel_id
            or receipt.canonical_fingerprint != declaration.canonical_fingerprint
            or receipt.canonical_cycle != declaration.canonical_cycle
            or result.outcome_policy != declaration.outcome_policy
            or result.observed_harm_score != declaration.hypothesis_bundle.evidence_receipt.observed_value
            or any(t.shared_design_seed != declaration.shared_design_seed for t in result.traces)):
            raise ValueError("PredictionFailure resolution evidence mixed trial sources.")
        result_bytes = prediction_failure_trial_result_bytes(
            PredictionFailureTrialResultEnvelope.build(result))
        expected = _values(result, declaration, result_bytes)
        actual = self.model_dump(mode="json", exclude={"receipt_id"})
        if actual != json.loads(canonical_json_bytes(expected)):
            raise ValueError("PredictionFailure resolution coverage was hidden or altered.")
        if (not set(PREDICTION_FAILURE_UNPROVEN_RESOLUTION_REQUIREMENTS).issubset(
                self.missing_requirements)
            or self.resolution_contract_satisfied or self.resolution_trial_ready):
            raise ValueError("PredictionFailure trial cannot satisfy the Resolution Contract.")
        if self.receipt_id != stable_id("prediction_failure_resolution_evidence_receipt", actual):
            raise ValueError("PredictionFailure resolution-evidence checksum mismatch.")
        return self


class PredictionFailureResolutionEvidenceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = PREDICTION_FAILURE_RESOLUTION_EVIDENCE_FORMAT
    receipt: PredictionFailureResolutionEvidenceReceipt
    receipt_sha256: str

    @classmethod
    def build(cls, receipt):
        checked = PredictionFailureResolutionEvidenceReceipt.model_validate(
            receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=_sha(
            canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_envelope(self):
        if (self.sidecar_format != PREDICTION_FAILURE_RESOLUTION_EVIDENCE_FORMAT
            or self.receipt_sha256 != _sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))):
            raise ValueError("PredictionFailure resolution-evidence envelope mismatch.")
        return self


def prediction_failure_resolution_evidence_bytes(envelope):
    checked = PredictionFailureResolutionEvidenceEnvelope.model_validate(
        envelope.model_dump(mode="json"))
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence exceeds its size limit.")
    return data


def read_prediction_failure_resolution_evidence(path):
    """Check local shape and bytes; canonical/source provenance requires load."""
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence exceeds its size limit.")
        envelope = PredictionFailureResolutionEvidenceEnvelope.model_validate_json(data)
        if prediction_failure_resolution_evidence_bytes(envelope) != data:
            raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence is not canonical.")
        return envelope
    except PredictionFailureResolutionEvidenceIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureResolutionEvidenceIntegrityError("Invalid resolution-evidence sidecar.") from exc


def _assert_unchanged(kernel, fingerprint, inputs):
    if kernel.fingerprint() != fingerprint or any(p.read_bytes() != b for p, b in inputs):
        raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence canonical state or inputs changed.")


@contextmanager
def _guard(kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
    before = kernel.fingerprint()
    try:
        inputs = tuple((Path(p), Path(p).read_bytes()) for p in (
            completed_result_path, risk_receipt_path, plan_path, preregistration_path))
        try:
            yield inputs
        finally:
            _assert_unchanged(kernel, before, inputs)
    except PredictionFailureResolutionEvidenceIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureResolutionEvidenceIntegrityError(str(exc)) from exc


def _expected_receipt(kernel: VerdantKernel, inputs):
    (result_path, result_bytes), (risk_path, _), (plan_path, _), (prereg_path, _) = inputs
    result = load_prediction_failure_trial_result(
        result_path, kernel=kernel, risk_receipt_path=risk_path,
        plan_path=plan_path, preregistration_path=prereg_path).result
    declaration = load_prediction_failure_trial_plan(
        plan_path, kernel=kernel, preregistration_path=prereg_path,
    ).plan_bundle.preregistration.declaration
    _assert_unchanged(kernel, result.risk_receipt.canonical_fingerprint, inputs)
    return PredictionFailureResolutionEvidenceReceipt.build(
        result=result, declaration=declaration, result_bytes=result_bytes)


def save_prediction_failure_resolution_evidence(path, envelope, *, kernel,
        completed_result_path, risk_receipt_path, plan_path, preregistration_path):
    """Persist only exact derived coverage; never create a Resolution verdict."""
    with _guard(kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as inputs:
        if Path(path).resolve() in {p.resolve() for p, _ in inputs}:
            raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence needs a separate output path.")
        checked = PredictionFailureResolutionEvidenceEnvelope.model_validate(envelope.model_dump(mode="json"))
        if checked.receipt != _expected_receipt(kernel, inputs):
            raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence lost exact completed-trial provenance.")
        _assert_unchanged(kernel, checked.receipt.canonical_fingerprint, inputs)
        _write_immutable(Path(path), prediction_failure_resolution_evidence_bytes(checked))
        return checked.receipt.receipt_id


def load_prediction_failure_resolution_evidence(path, *, kernel, completed_result_path,
        risk_receipt_path, plan_path, preregistration_path):
    """Reconstruct coverage without executing or charging another simulation."""
    with _guard(kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as inputs:
        envelope = read_prediction_failure_resolution_evidence(path)
        if envelope.receipt != _expected_receipt(kernel, inputs):
            raise PredictionFailureResolutionEvidenceIntegrityError("Resolution evidence lost exact completed-trial provenance.")
        return envelope


class PredictionFailureResolutionEvidenceDeriver:
    """Explicitly assess a completed trial; callers cannot supply coverage."""

    def derive(self, *, kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
        with _guard(kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as inputs:
            return _expected_receipt(kernel, inputs)


class PredictionFailureResolutionEvidenceRecorder:
    """Publish immutable unresolved coverage in a separately durable sidecar."""

    def record(self, path, *, kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
        with _guard(kernel, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as inputs:
            envelope = PredictionFailureResolutionEvidenceEnvelope.build(_expected_receipt(kernel, inputs))
            save_prediction_failure_resolution_evidence(
                path, envelope, kernel=kernel, completed_result_path=completed_result_path,
                risk_receipt_path=risk_receipt_path, plan_path=plan_path,
                preregistration_path=preregistration_path)
            return envelope
