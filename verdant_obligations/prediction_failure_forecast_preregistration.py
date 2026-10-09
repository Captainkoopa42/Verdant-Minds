"""Prospective, non-authoritative forecast-audit preregistration.

This freezes a future study, not a dataset or a calibration result. Native
governance harm scores remain caller supplied; a trace-derived physical
measurement observer and a prospective forecast adapter are still missing.
"""
from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, VerdantKernel
from verdant_kernel.models import (
    CouncilDecisionEvent, EvidenceRecord, FrozenRecord, GovernanceOutcomeRecord,
    canonical_json_bytes, stable_id,
)

from .prediction_failure_resolution_evidence import (
    PredictionFailureResolutionEvidenceReceipt,
    PredictionFailureResolutionRequirement,
    load_prediction_failure_resolution_evidence,
    prediction_failure_resolution_evidence_bytes,
    PredictionFailureResolutionEvidenceEnvelope,
)
from .prediction_failure_risk_operator import PREDICTION_FAILURE_RISK_OPERATOR_VERSION
from .prediction_failure_trial_plans import _write_immutable

PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION = (
    "prediction_failure_forecast_preregistration_v0.53"
)
PREDICTION_FAILURE_FORECAST_PREREGISTRATION_FORMAT = (
    "verdant-prediction-failure-forecast-preregistration-v1"
)
PREDICTION_FAILURE_FORECAST_PREREGISTRATION_SIDECAR_SUFFIX = ".vfs"
_MAX_SIDECAR_BYTES = 32 * 1024 * 1024
_SOURCE_PATHS = (
    "verdant_governance/pipeline.py", "verdant_kernel/kernel.py",
    "verdant_kernel/models.py", "verdant_obligations/prediction_failure_risk_operator.py",
)


class PredictionFailureForecastPreregistrationIntegrityError(RuntimeError):
    """The future study lost its source, temporal or authority boundary."""


class PredictionFailureForecastArm(str, Enum):
    NATIVE_RISK = "native_risk"
    DECLARED_RISK_CONTROL = "declared_risk_control"
    VALID_NULL = "valid_null"


_POLICY_VALUES = dict(
    policy_version=PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION,
    forecast_operator_version=PREDICTION_FAILURE_RISK_OPERATOR_VERSION,
    arms=[arm.value for arm in PredictionFailureForecastArm],
    calibration_case_count=8, evaluation_case_count=8, maximum_case_count=16,
    enrollment_rule="first_authorized_same_action_class_decisions_after_cutoff",
    partition_rule="first_eight_calibration_audit_next_eight_evaluation",
    decision_order="committed_cycle_then_decision_event_id",
    native_forecast_field="KingAssessment[Ethics].details.effective_harm_risk",
    declared_control_field="CouncilReport.proposal.harm_risk",
    native_forecast_formula="min(1, max(declared_risk, frozen_learned_risk) + uncertainty_increment)",
    valid_null_rule="exact_native_risk_replay",
    measurement_trace_field="physical_measurement_trace.harm_score",
    error_formula="abs(forecast_score - trace_derived_measured_harm)",
    aggregation_rule="arithmetic_mean_complete_enrolled_block_only",
    improvement_formula="declared_control_mean_error - native_risk_mean_error",
    evaluation_improvement_threshold=0.05, valid_null_error_tolerance=0.0,
    per_arm_budget=0.015, per_case_budget=0.045, maximum_total_budget=0.72,
    proposal_creation_after_cutoff_required=True,
    decision_commit_after_cutoff_required=True,
    all_forecasts_sealed_before_any_enrolled_outcome=True,
    frozen_governance_memory_required=True,
    matched_non_target_inputs_required=True,
    distinct_pristine_ledger_per_arm_required=True,
    new_attention_allocation_per_case_required=True,
    trace_derived_physical_measurement_required=True,
    measurement_protocol_frozen_before_forecasts_required=True,
    identical_measurement_protocol_across_cases_required=True,
    protected_evidence_required=True,
    disjoint_support_and_future_outcome_refs_required=True,
    disjoint_calibration_and_evaluation_refs_required=True,
    complete_block_required=True,
    outcome_conditioned_enrollment_permitted=False,
    missing_case_replacement_permitted=False,
    future_outcome_as_forecast_input_permitted=False,
    calibration_curve_fitting_permitted=False,
    evaluation_outcome_fitting_permitted=False,
    supplied_forecast_or_measurement_permitted=False,
    governance_harm_score_alone_admissible=False,
    measurement_metric_tuning_permitted=False,
    automatic_execution_permitted=False,
)


class PredictionFailureForecastStudyPolicy(BaseModel):
    """Visible fixed design; eight plus eight cases do not establish power."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION
    forecast_operator_version: str = PREDICTION_FAILURE_RISK_OPERATOR_VERSION
    arms: tuple[PredictionFailureForecastArm, ...] = tuple(PredictionFailureForecastArm)
    calibration_case_count: int = 8
    evaluation_case_count: int = 8
    maximum_case_count: int = 16
    enrollment_rule: str = _POLICY_VALUES["enrollment_rule"]
    partition_rule: str = _POLICY_VALUES["partition_rule"]
    decision_order: str = _POLICY_VALUES["decision_order"]
    native_forecast_field: str = _POLICY_VALUES["native_forecast_field"]
    declared_control_field: str = _POLICY_VALUES["declared_control_field"]
    native_forecast_formula: str = _POLICY_VALUES["native_forecast_formula"]
    valid_null_rule: str = _POLICY_VALUES["valid_null_rule"]
    measurement_trace_field: str = _POLICY_VALUES["measurement_trace_field"]
    error_formula: str = _POLICY_VALUES["error_formula"]
    aggregation_rule: str = _POLICY_VALUES["aggregation_rule"]
    improvement_formula: str = _POLICY_VALUES["improvement_formula"]
    evaluation_improvement_threshold: float = 0.05
    valid_null_error_tolerance: float = 0.0
    per_arm_budget: float = 0.015
    per_case_budget: float = 0.045
    maximum_total_budget: float = 0.72
    proposal_creation_after_cutoff_required: bool = True
    decision_commit_after_cutoff_required: bool = True
    all_forecasts_sealed_before_any_enrolled_outcome: bool = True
    frozen_governance_memory_required: bool = True
    matched_non_target_inputs_required: bool = True
    distinct_pristine_ledger_per_arm_required: bool = True
    new_attention_allocation_per_case_required: bool = True
    trace_derived_physical_measurement_required: bool = True
    measurement_protocol_frozen_before_forecasts_required: bool = True
    identical_measurement_protocol_across_cases_required: bool = True
    protected_evidence_required: bool = True
    disjoint_support_and_future_outcome_refs_required: bool = True
    disjoint_calibration_and_evaluation_refs_required: bool = True
    complete_block_required: bool = True
    outcome_conditioned_enrollment_permitted: bool = False
    missing_case_replacement_permitted: bool = False
    future_outcome_as_forecast_input_permitted: bool = False
    calibration_curve_fitting_permitted: bool = False
    evaluation_outcome_fitting_permitted: bool = False
    supplied_forecast_or_measurement_permitted: bool = False
    governance_harm_score_alone_admissible: bool = False
    measurement_metric_tuning_permitted: bool = False
    automatic_execution_permitted: bool = False

    @model_validator(mode="after")
    def check_frozen_design(self):
        if self.model_dump(mode="json") != _POLICY_VALUES:
            raise ValueError("Forecast study changed its frozen prospective design.")
        return self


class PredictionFailureForecastSourceFile(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)
    repository_path: str
    sha256: str

    @model_validator(mode="after")
    def check_file(self):
        if (self.repository_path not in _SOURCE_PATHS or len(self.sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.sha256)):
            raise ValueError("Forecast source manifest contains an invalid file.")
        return self


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _source_manifest():
    root = Path(__file__).resolve().parent.parent
    return tuple(PredictionFailureForecastSourceFile(
        repository_path=p, sha256=_sha((root / p).read_bytes())) for p in _SOURCE_PATHS)


def _json(value):
    return json.loads(canonical_json_bytes(value))


def _values(*, anchor, anchor_bytes, kernel, source_manifest, prior, decision, evidence):
    return dict(
        declaration_version=PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION,
        anchor=anchor.model_dump(mode="json"), anchor_ref=anchor.receipt_id,
        anchor_sha256=_sha(anchor_bytes),
        canonical_kernel_id=kernel.state.identity.kernel_id,
        canonical_fingerprint=kernel.fingerprint(), cutoff_cycle=kernel.state.cycle,
        cutoff_event_sequence=kernel.state.event_sequence,
        action_class=anchor.declaration.hypothesis_bundle.evidence_receipt.action_class,
        governance_fingerprint=kernel.governance_fingerprint(),
        frozen_learned_risk=kernel.state.governance.learned_action_risk[prior.action_class],
        support_outcome=prior.model_dump(mode="json"),
        support_decision=decision.model_dump(mode="json"),
        support_evidence=tuple(e.model_dump(mode="json") for e in evidence),
        excluded_decision_refs=tuple(sorted(d.decision_event_id for d in kernel.state.council_decisions)),
        excluded_outcome_refs=tuple(sorted(o.outcome_id for o in kernel.state.governance_outcomes)),
        native_source_files=tuple(s.model_dump(mode="json") for s in source_manifest),
        study_policy=PredictionFailureForecastStudyPolicy().model_dump(mode="json"),
        missing_prerequisites=("physical_measurement_trace_observer", "prospective_forecast_adapter"),
        prospective_only=True, forecasts_recorded=False, future_outcomes_observed=False,
        study_executed=False, physical_measurement_protocol_implemented=False,
        prospective_forecast_adapter_implemented=False, calibration_observed=False,
        predictive_improvement_observed=False, independent_replication_observed=False,
        source_independence_proven=False, resolution_contract_satisfied=False,
        simulation_budget_authorized=False, canonical_commit_permitted=False,
        resolution_authority_enabled=False, promotion_authority_enabled=False,
        policy_rewrite_authority_enabled=False,
    )


class PredictionFailureForecastStudyDeclaration(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION
    anchor: PredictionFailureResolutionEvidenceReceipt
    anchor_ref: str
    anchor_sha256: str
    canonical_kernel_id: str
    canonical_fingerprint: str
    cutoff_cycle: int = Field(ge=0)
    cutoff_event_sequence: int = Field(ge=0)
    action_class: str
    governance_fingerprint: str
    frozen_learned_risk: float = Field(ge=0.0, le=1.0)
    support_outcome: GovernanceOutcomeRecord
    support_decision: CouncilDecisionEvent
    support_evidence: tuple[EvidenceRecord, ...] = Field(min_length=1)
    excluded_decision_refs: tuple[str, ...] = Field(min_length=1)
    excluded_outcome_refs: tuple[str, ...] = Field(min_length=1)
    native_source_files: tuple[PredictionFailureForecastSourceFile, ...] = Field(min_length=4, max_length=4)
    study_policy: PredictionFailureForecastStudyPolicy
    missing_prerequisites: tuple[str, ...]
    prospective_only: bool = True
    forecasts_recorded: bool = False
    future_outcomes_observed: bool = False
    study_executed: bool = False
    physical_measurement_protocol_implemented: bool = False
    prospective_forecast_adapter_implemented: bool = False
    calibration_observed: bool = False
    predictive_improvement_observed: bool = False
    independent_replication_observed: bool = False
    source_independence_proven: bool = False
    resolution_contract_satisfied: bool = False
    simulation_budget_authorized: bool = False
    canonical_commit_permitted: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False

    @model_validator(mode="after")
    def check_declaration(self):
        anchor, prior, decision = self.anchor, self.support_outcome, self.support_decision
        anchor_bytes = prediction_failure_resolution_evidence_bytes(
            PredictionFailureResolutionEvidenceEnvelope.build(anchor))
        if (self.declaration_version != PREDICTION_FAILURE_FORECAST_PREREGISTRATION_VERSION
            or self.anchor_ref != anchor.receipt_id or self.anchor_sha256 != _sha(anchor_bytes)
            or self.canonical_kernel_id != anchor.canonical_kernel_id
            or self.canonical_fingerprint != anchor.canonical_fingerprint
            or self.cutoff_cycle != anchor.canonical_cycle
            or self.action_class != anchor.declaration.hypothesis_bundle.evidence_receipt.action_class
            or self.frozen_learned_risk != prior.learned_risk_after
            or prior.action_class != self.action_class
            or prior.decision_event_id != decision.decision_event_id
            or decision.report.proposal.action_class != self.action_class
            or decision.report.proposal.operation not in decision.report.authorized_operations
            or not decision.report.proposal.created_cycle < decision.committed_cycle < prior.cycle
            or prior.cycle > self.cutoff_cycle
            or tuple(e.evidence_id for e in self.support_evidence) != prior.evidence_refs
            or any(e.cycle > prior.cycle for e in self.support_evidence)
            or not any(e.kind == EvidenceKind.OUTCOME for e in self.support_evidence)
            or tuple(s.repository_path for s in self.native_source_files) != _SOURCE_PATHS
            or self.missing_prerequisites != ("physical_measurement_trace_observer", "prospective_forecast_adapter")):
            raise ValueError("Forecast declaration lost its earlier-support or anchor lineage.")
        for refs in (self.excluded_decision_refs, self.excluded_outcome_refs):
            if tuple(sorted(set(refs))) != refs:
                raise ValueError("Forecast historical exclusions are not complete identities.")
        if (prior.outcome_id not in self.excluded_outcome_refs
            or decision.decision_event_id not in self.excluded_decision_refs
            or anchor.declaration.hypothesis_bundle.evidence_receipt.outcome_ref not in self.excluded_outcome_refs
            or anchor.declaration.hypothesis_bundle.evidence_receipt.prediction_source_ref not in self.excluded_decision_refs
            or PredictionFailureResolutionRequirement.CALIBRATED_PHYSICAL_PREDICTION not in anchor.missing_requirements):
            raise ValueError("Forecast declaration reused historical targets or suppressed missing calibration.")
        for value in (self.canonical_fingerprint, self.governance_fingerprint):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("Forecast checkpoint identity must be SHA-256.")
        flags = self.model_dump(mode="json")
        names = (
            "forecasts_recorded", "future_outcomes_observed", "study_executed",
            "physical_measurement_protocol_implemented", "prospective_forecast_adapter_implemented",
            "calibration_observed", "predictive_improvement_observed", "independent_replication_observed",
            "source_independence_proven", "resolution_contract_satisfied", "simulation_budget_authorized",
            "canonical_commit_permitted", "resolution_authority_enabled", "promotion_authority_enabled",
            "policy_rewrite_authority_enabled",
        )
        if not self.prospective_only or any(flags[name] for name in names):
            raise ValueError("Forecast preregistration cannot claim execution, calibration or authority.")
        if self.declaration_id != stable_id("prediction_failure_forecast_study_declaration",
                self.model_dump(mode="json", exclude={"declaration_id"})):
            raise ValueError("Forecast declaration checksum mismatch.")
        return self


class PredictionFailureForecastPreregistrationEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sidecar_format: str = PREDICTION_FAILURE_FORECAST_PREREGISTRATION_FORMAT
    declaration: PredictionFailureForecastStudyDeclaration
    declaration_sha256: str

    @classmethod
    def build(cls, declaration):
        checked = PredictionFailureForecastStudyDeclaration.model_validate(declaration.model_dump(mode="json"))
        return cls(declaration=checked, declaration_sha256=_sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_digest(self):
        if (self.sidecar_format != PREDICTION_FAILURE_FORECAST_PREREGISTRATION_FORMAT
            or self.declaration_sha256 != _sha(canonical_json_bytes(self.declaration.model_dump(mode="json")))):
            raise ValueError("Forecast preregistration envelope checksum mismatch.")
        return self


def prediction_failure_forecast_preregistration_bytes(envelope):
    checked = PredictionFailureForecastPreregistrationEnvelope.model_validate(envelope.model_dump(mode="json"))
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration exceeds its size limit.")
    return data


def read_prediction_failure_forecast_preregistration(path):
    """Local integrity only; canonical and source-code provenance require load."""
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration exceeds its size limit.")
        envelope = PredictionFailureForecastPreregistrationEnvelope.model_validate_json(data)
        if prediction_failure_forecast_preregistration_bytes(envelope) != data:
            raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration is not canonical.")
        return envelope
    except PredictionFailureForecastPreregistrationIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureForecastPreregistrationIntegrityError("Invalid forecast preregistration.") from exc


def _assert_unchanged(kernel, before, inputs, manifest):
    if (kernel.fingerprint() != before or _source_manifest() != manifest
        or any(p.read_bytes() != b for p, b in inputs)):
        raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration canonical state or sources changed.")


@contextmanager
def _guard(kernel, resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
    before = kernel.fingerprint()
    try:
        manifest = _source_manifest()
        inputs = tuple((Path(p), Path(p).read_bytes()) for p in (
            resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path))
        try:
            yield inputs, manifest
        finally:
            _assert_unchanged(kernel, before, inputs, manifest)
    except PredictionFailureForecastPreregistrationIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureForecastPreregistrationIntegrityError(str(exc)) from exc


def _expected(kernel, inputs, manifest):
    (coverage, coverage_bytes), (result, _), (risk, _), (plan, _), (prereg, _) = inputs
    # Revalidate native state as well as the complete completed-study chain.
    VerdantKernel.from_state(kernel.snapshot())
    anchor = load_prediction_failure_resolution_evidence(
        coverage, kernel=kernel, completed_result_path=result, risk_receipt_path=risk,
        plan_path=plan, preregistration_path=prereg).receipt
    action_class = anchor.declaration.hypothesis_bundle.evidence_receipt.action_class
    priors = [o for o in kernel.state.governance_outcomes if o.action_class == action_class]
    if not priors:
        raise PredictionFailureForecastPreregistrationIntegrityError("No canonical earlier learning support exists.")
    prior = max(priors, key=lambda o: o.cycle)
    decision = next(d for d in kernel.state.council_decisions if d.decision_event_id == prior.decision_event_id)
    evidence = tuple(kernel.state.evidence[ref] for ref in prior.evidence_refs)
    values = _json(_values(anchor=anchor, anchor_bytes=coverage_bytes, kernel=kernel,
                          source_manifest=manifest, prior=prior, decision=decision, evidence=evidence))
    return PredictionFailureForecastStudyDeclaration(
        declaration_id=stable_id("prediction_failure_forecast_study_declaration", values), **values)


def save_prediction_failure_forecast_preregistration(path, envelope, *, kernel,
        resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
    with _guard(kernel, resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as (inputs, manifest):
        if Path(path).resolve() in {p.resolve() for p, _ in inputs}:
            raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration needs a separate output path.")
        checked = PredictionFailureForecastPreregistrationEnvelope.model_validate(envelope.model_dump(mode="json"))
        if checked.declaration != _expected(kernel, inputs, manifest):
            raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration lost exact source provenance.")
        _assert_unchanged(kernel, checked.declaration.canonical_fingerprint, inputs, manifest)
        _write_immutable(Path(path), prediction_failure_forecast_preregistration_bytes(checked))
        return checked.declaration.declaration_id


def load_prediction_failure_forecast_preregistration(path, *, kernel,
        resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path):
    with _guard(kernel, resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as (inputs, manifest):
        envelope = read_prediction_failure_forecast_preregistration(path)
        if envelope.declaration != _expected(kernel, inputs, manifest):
            raise PredictionFailureForecastPreregistrationIntegrityError("Forecast preregistration lost exact source provenance.")
        return envelope


class PredictionFailureForecastPreregistrar:
    """Freeze a future audit without forecasts, measurements, grants or execution."""

    def register(self, path, *, kernel, resolution_evidence_path, completed_result_path,
            risk_receipt_path, plan_path, preregistration_path):
        with _guard(kernel, resolution_evidence_path, completed_result_path, risk_receipt_path, plan_path, preregistration_path) as (inputs, manifest):
            envelope = PredictionFailureForecastPreregistrationEnvelope.build(_expected(kernel, inputs, manifest))
            save_prediction_failure_forecast_preregistration(
                path, envelope, kernel=kernel, resolution_evidence_path=resolution_evidence_path,
                completed_result_path=completed_result_path, risk_receipt_path=risk_receipt_path,
                plan_path=plan_path, preregistration_path=preregistration_path)
            return envelope
