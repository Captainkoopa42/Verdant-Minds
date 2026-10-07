"""Durable pre-execution design for PredictionFailure matched trials.

This v0.47 layer freezes an exact v0.46 hypothesis bundle, its canonical
checkpoint, three matched arms, bounded future simulation budget, and an
answer-agnostic trace-outcome grammar.  It does not materialize an executable
overlay plan, run a trial, observe an outcome, or attribute causality.
"""
from __future__ import annotations

import hashlib
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

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .prediction_failure_hypotheses import (
    PredictionFailureHypothesisBundle,
    PredictionFailureHypothesisProtocol,
)


PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION = (
    "prediction_failure_trial_preregistration_v0.47"
)
PREDICTION_FAILURE_TRIAL_PREREGISTRATION_FORMAT = (
    "verdant-prediction-failure-trial-preregistration-v1"
)
PREDICTION_FAILURE_TRIAL_TRACE_VALUE_FIELD = (
    "prediction_failure_trial_observation.predicted_harm_score"
)
PREDICTION_FAILURE_TRIAL_OBSERVED_VALUE_SOURCE = (
    "hypothesis_bundle.evidence_receipt.observed_value"
)
PREDICTION_FAILURE_TRIAL_ERROR_FORMULA = (
    "abs(predicted_harm_score - observed_value)"
)
PREDICTION_FAILURE_TRIAL_TARGET_DELTA_FORMULA = (
    "abs(target_ablation_error - baseline_error)"
)
PREDICTION_FAILURE_TRIAL_VALID_NULL_DELTA_FORMULA = (
    "abs(valid_null_error - baseline_error)"
)
PREDICTION_FAILURE_TRIAL_SIDECAR_SUFFIX = ".vfp"
_MAX_SIDECAR_BYTES = 8 * 1024 * 1024


class PredictionFailureTrialPreregistrationIntegrityError(RuntimeError):
    """Raised when a PredictionFailure trial declaration loses its boundary."""


class PredictionFailureTrialArm(str, Enum):
    BASELINE = "baseline"
    TARGET_ABLATION = "target_ablation"
    VALID_NULL = "valid_null"


PREDICTION_FAILURE_TRIAL_ARM_ORDER = tuple(PredictionFailureTrialArm)


class PredictionFailureTrialMetric(str, Enum):
    ABSOLUTE_ERROR_DELTA_FROM_BASELINE = (
        "absolute_error_delta_from_baseline"
    )


class PredictionFailureTrialDisposition(str, Enum):
    TARGET_ERROR_CHANGED = "target_error_changed"
    TARGET_ERROR_UNCHANGED = "target_error_unchanged"
    INVALID_VALID_NULL = "invalid_valid_null"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


PREDICTION_FAILURE_TRIAL_DISPOSITIONS = tuple(PredictionFailureTrialDisposition)
PREDICTION_FAILURE_TRIAL_DISPOSITION_PRECEDENCE = (
    PredictionFailureTrialDisposition.INSUFFICIENT_EVIDENCE,
    PredictionFailureTrialDisposition.INVALID_VALID_NULL,
    PredictionFailureTrialDisposition.TARGET_ERROR_CHANGED,
    PredictionFailureTrialDisposition.TARGET_ERROR_UNCHANGED,
)


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


def _design_seed(bundle_id: str) -> int:
    return int(hashlib.sha256(bundle_id.encode("utf-8")).hexdigest()[:8], 16)


class PredictionFailureTrialOutcomePolicy(BaseModel):
    """Fixed future trace grammar; it is not an observed outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
    metric: PredictionFailureTrialMetric = (
        PredictionFailureTrialMetric.ABSOLUTE_ERROR_DELTA_FROM_BASELINE
    )
    trace_value_field: str = PREDICTION_FAILURE_TRIAL_TRACE_VALUE_FIELD
    observed_value_source: str = PREDICTION_FAILURE_TRIAL_OBSERVED_VALUE_SOURCE
    error_formula: str = PREDICTION_FAILURE_TRIAL_ERROR_FORMULA
    target_delta_formula: str = PREDICTION_FAILURE_TRIAL_TARGET_DELTA_FORMULA
    valid_null_delta_formula: str = (
        PREDICTION_FAILURE_TRIAL_VALID_NULL_DELTA_FORMULA
    )
    trace_value_minimum: float = Field(default=0.0, ge=0.0, le=0.0)
    trace_value_maximum: float = Field(default=1.0, ge=1.0, le=1.0)
    target_error_change_threshold: float = Field(default=0.05, gt=0.0, le=1.0)
    valid_null_max_error_delta: float = Field(default=0.0, ge=0.0, le=0.0)
    per_arm_budget: float = Field(default=0.015, gt=0.0)
    total_budget: float = Field(default=0.045, gt=0.0)
    disposition_precedence: tuple[PredictionFailureTrialDisposition, ...] = (
        PREDICTION_FAILURE_TRIAL_DISPOSITION_PRECEDENCE
    )
    trace_derived_values_required: bool = True
    one_trace_value_per_arm_required: bool = True
    complete_three_arm_trace_required: bool = True
    valid_null_baseline_equivalence_required: bool = True
    caller_supplied_arm_values_permitted: bool = False
    non_finite_trace_values_permitted: bool = False
    out_of_range_trace_values_permitted: bool = False
    post_execution_threshold_revision_permitted: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> "PredictionFailureTrialOutcomePolicy":
        if (
            self.policy_version
            != PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
            or self.metric
            != PredictionFailureTrialMetric.ABSOLUTE_ERROR_DELTA_FROM_BASELINE
            or self.trace_value_field
            != PREDICTION_FAILURE_TRIAL_TRACE_VALUE_FIELD
            or self.observed_value_source
            != PREDICTION_FAILURE_TRIAL_OBSERVED_VALUE_SOURCE
            or self.error_formula != PREDICTION_FAILURE_TRIAL_ERROR_FORMULA
            or self.target_delta_formula
            != PREDICTION_FAILURE_TRIAL_TARGET_DELTA_FORMULA
            or self.valid_null_delta_formula
            != PREDICTION_FAILURE_TRIAL_VALID_NULL_DELTA_FORMULA
            or self.trace_value_minimum != 0.0
            or self.trace_value_maximum != 1.0
            or self.target_error_change_threshold != 0.05
            or self.valid_null_max_error_delta != 0.0
            or self.per_arm_budget != 0.015
            or self.total_budget != 0.045
            or self.total_budget
            != self.per_arm_budget * len(PREDICTION_FAILURE_TRIAL_ARM_ORDER)
            or self.disposition_precedence
            != PREDICTION_FAILURE_TRIAL_DISPOSITION_PRECEDENCE
            or not self.trace_derived_values_required
            or not self.one_trace_value_per_arm_required
            or not self.complete_three_arm_trace_required
            or not self.valid_null_baseline_equivalence_required
            or self.caller_supplied_arm_values_permitted
            or self.non_finite_trace_values_permitted
            or self.out_of_range_trace_values_permitted
            or self.post_execution_threshold_revision_permitted
        ):
            raise ValueError(
                "PredictionFailure trial outcome policy crossed its fixed grammar."
            )
        return self

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class PredictionFailureTrialArmDeclaration(FrozenRecord):
    """One pre-execution arm sharing every input except target visibility."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    arm_id: str
    arm_version: str = PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
    arm: PredictionFailureTrialArm
    target_ref: str
    target_present: bool
    target_ablation_requested: bool
    no_op_control: bool
    shared_design_seed: int = Field(ge=0, le=0xFFFFFFFF)
    requested_budget: float = Field(gt=0.0)
    held_constant_ref_set_sha256: str
    matched_control_signature: str
    executable_plan_materialized: bool = False
    trace_observed: bool = False
    outcome_observed: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        arm: PredictionFailureTrialArm,
        target_ref: str,
        shared_design_seed: int,
        requested_budget: float,
        held_constant_ref_set_sha256: str,
        matched_control_signature: str,
    ) -> "PredictionFailureTrialArmDeclaration":
        modes = {
            PredictionFailureTrialArm.BASELINE: (True, False, False),
            PredictionFailureTrialArm.TARGET_ABLATION: (False, True, False),
            PredictionFailureTrialArm.VALID_NULL: (True, False, True),
        }
        target_present, ablation_requested, no_op = modes[arm]
        values = {
            "arm_version": PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION,
            "arm": arm,
            "target_ref": target_ref,
            "target_present": target_present,
            "target_ablation_requested": ablation_requested,
            "no_op_control": no_op,
            "shared_design_seed": shared_design_seed,
            "requested_budget": requested_budget,
            "held_constant_ref_set_sha256": held_constant_ref_set_sha256,
            "matched_control_signature": matched_control_signature,
            "executable_plan_materialized": False,
            "trace_observed": False,
            "outcome_observed": False,
            "canonical_commit_permitted": False,
        }
        values["arm_id"] = stable_id(
            "prediction_failure_trial_arm", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_arm(self) -> "PredictionFailureTrialArmDeclaration":
        expected_modes = {
            PredictionFailureTrialArm.BASELINE: (True, False, False),
            PredictionFailureTrialArm.TARGET_ABLATION: (False, True, False),
            PredictionFailureTrialArm.VALID_NULL: (True, False, True),
        }
        if (
            self.arm_version
            != PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
            or not self.target_ref.strip()
            or (
                self.target_present,
                self.target_ablation_requested,
                self.no_op_control,
            )
            != expected_modes[self.arm]
            or not _is_sha256(self.held_constant_ref_set_sha256)
            or not self.matched_control_signature.strip()
            or self.executable_plan_materialized
            or self.trace_observed
            or self.outcome_observed
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "PredictionFailure trial arm crossed its pre-execution boundary."
            )
        expected = stable_id(
            "prediction_failure_trial_arm",
            self.model_dump(mode="json", exclude={"arm_id"}),
        )
        if self.arm_id != expected:
            raise ValueError("PredictionFailure trial-arm checksum mismatch.")
        return self


class PredictionFailureTrialDeclaration(FrozenRecord):
    """Exact canonical lineage and matched design frozen before execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
    canonical_kernel_id: str
    canonical_fingerprint: str
    canonical_cycle: int = Field(ge=0)
    hypothesis_bundle: PredictionFailureHypothesisBundle
    hypothesis_bundle_ref: str
    hypothesis_bundle_sha256: str
    evidence_receipt_ref: str
    target_ref: str
    protected_evidence_refs: tuple[str, ...] = Field(min_length=1)
    held_constant_refs: tuple[str, ...] = Field(min_length=1)
    held_constant_ref_set_sha256: str
    shared_design_seed: int = Field(ge=0, le=0xFFFFFFFF)
    matched_control_signature: str
    arms: tuple[PredictionFailureTrialArmDeclaration, ...] = Field(
        min_length=3,
        max_length=3,
    )
    arm_refs: tuple[str, ...] = Field(min_length=3, max_length=3)
    outcome_policy: PredictionFailureTrialOutcomePolicy
    outcome_policy_sha256: str
    admissible_dispositions: tuple[PredictionFailureTrialDisposition, ...] = (
        PREDICTION_FAILURE_TRIAL_DISPOSITIONS
    )
    durable_before_execution: bool = True
    separate_result_sidecar_required: bool = True
    same_canonical_checkpoint_required: bool = True
    same_seed_required: bool = True
    complete_protected_evidence_required: bool = True
    target_visibility_only_difference_required: bool = True
    explicit_valid_null_required: bool = True
    trace_derived_outcome_required: bool = True
    runner_implemented: bool = False
    execution_plans_materialized: bool = False
    trial_executed: bool = False
    traces_observed: bool = False
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
        hypothesis_bundle: PredictionFailureHypothesisBundle,
        hypothesis_protocol: PredictionFailureHypothesisProtocol | None = None,
        outcome_policy: PredictionFailureTrialOutcomePolicy | None = None,
    ) -> "PredictionFailureTrialDeclaration":
        protocol = hypothesis_protocol or PredictionFailureHypothesisProtocol()
        bundle = protocol.validate(kernel, hypothesis_bundle)
        receipt = bundle.evidence_receipt
        policy = outcome_policy or PredictionFailureTrialOutcomePolicy()
        policy = PredictionFailureTrialOutcomePolicy.model_validate(
            policy.model_dump(mode="json")
        )
        if policy.total_budget > receipt.authorized_budget + 1e-12:
            raise ValueError(
                "PredictionFailure trial budget exceeds its Attention allocation."
            )
        held_constant_refs = tuple(
            sorted(
                {
                    bundle.bundle_id,
                    bundle.obligation_id,
                    bundle.obligation_event_ref,
                    bundle.attention_decision_ref,
                    bundle.attention_bid_ref,
                    bundle.attention_allocation_ref,
                    receipt.receipt_id,
                    receipt.outcome_ref,
                    receipt.prediction_source_ref,
                    receipt.proposal_ref,
                    receipt.council_report_ref,
                    receipt.ablation_target.target_id,
                    *(item.hypothesis_id for item in bundle.hypotheses),
                    *receipt.protected_evidence_refs,
                }
            )
        )
        held_constant_sha = _digest(held_constant_refs)
        seed = _design_seed(bundle.bundle_id)
        policy_sha = policy.fingerprint()
        matched_signature = stable_id(
            "prediction_failure_trial_matched_control",
            PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION,
            kernel.state.identity.kernel_id,
            kernel.fingerprint(),
            bundle.bundle_id,
            receipt.ablation_target.target_id,
            held_constant_sha,
            seed,
            policy_sha,
        )
        arms = tuple(
            PredictionFailureTrialArmDeclaration.build(
                arm=arm,
                target_ref=receipt.ablation_target.target_id,
                shared_design_seed=seed,
                requested_budget=policy.per_arm_budget,
                held_constant_ref_set_sha256=held_constant_sha,
                matched_control_signature=matched_signature,
            )
            for arm in PREDICTION_FAILURE_TRIAL_ARM_ORDER
        )
        values = {
            "declaration_version": (
                PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
            ),
            "canonical_kernel_id": kernel.state.identity.kernel_id,
            "canonical_fingerprint": kernel.fingerprint(),
            "canonical_cycle": kernel.state.cycle,
            "hypothesis_bundle": bundle,
            "hypothesis_bundle_ref": bundle.bundle_id,
            "hypothesis_bundle_sha256": _digest(bundle.model_dump(mode="json")),
            "evidence_receipt_ref": receipt.receipt_id,
            "target_ref": receipt.ablation_target.target_id,
            "protected_evidence_refs": receipt.protected_evidence_refs,
            "held_constant_refs": held_constant_refs,
            "held_constant_ref_set_sha256": held_constant_sha,
            "shared_design_seed": seed,
            "matched_control_signature": matched_signature,
            "arms": arms,
            "arm_refs": tuple(item.arm_id for item in arms),
            "outcome_policy": policy,
            "outcome_policy_sha256": policy_sha,
            "admissible_dispositions": PREDICTION_FAILURE_TRIAL_DISPOSITIONS,
            "durable_before_execution": True,
            "separate_result_sidecar_required": True,
            "same_canonical_checkpoint_required": True,
            "same_seed_required": True,
            "complete_protected_evidence_required": True,
            "target_visibility_only_difference_required": True,
            "explicit_valid_null_required": True,
            "trace_derived_outcome_required": True,
            "runner_implemented": False,
            "execution_plans_materialized": False,
            "trial_executed": False,
            "traces_observed": False,
            "outcomes_observed": False,
            "target_specific_effect_observed": False,
            "causal_attribution_enabled": False,
            "resolution_authority_enabled": False,
            "promotion_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["declaration_id"] = stable_id(
            "prediction_failure_trial_declaration", _payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_declaration(self) -> "PredictionFailureTrialDeclaration":
        bundle = self.hypothesis_bundle
        receipt = bundle.evidence_receipt
        expected_held_constant_refs = tuple(
            sorted(
                {
                    bundle.bundle_id,
                    bundle.obligation_id,
                    bundle.obligation_event_ref,
                    bundle.attention_decision_ref,
                    bundle.attention_bid_ref,
                    bundle.attention_allocation_ref,
                    receipt.receipt_id,
                    receipt.outcome_ref,
                    receipt.prediction_source_ref,
                    receipt.proposal_ref,
                    receipt.council_report_ref,
                    receipt.ablation_target.target_id,
                    *(item.hypothesis_id for item in bundle.hypotheses),
                    *receipt.protected_evidence_refs,
                }
            )
        )
        expected_seed = _design_seed(bundle.bundle_id)
        if (
            self.declaration_version
            != PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION
            or not self.canonical_kernel_id.strip()
            or not _is_sha256(self.canonical_fingerprint)
            or self.hypothesis_bundle_ref != bundle.bundle_id
            or self.hypothesis_bundle_sha256
            != _digest(bundle.model_dump(mode="json"))
            or self.evidence_receipt_ref != receipt.receipt_id
            or self.target_ref != receipt.ablation_target.target_id
            or self.protected_evidence_refs != receipt.protected_evidence_refs
            or self.held_constant_refs != expected_held_constant_refs
            or self.held_constant_ref_set_sha256
            != _digest(expected_held_constant_refs)
            or self.shared_design_seed != expected_seed
            or self.outcome_policy_sha256 != self.outcome_policy.fingerprint()
            or self.outcome_policy.total_budget
            > receipt.authorized_budget + 1e-12
            or self.admissible_dispositions
            != PREDICTION_FAILURE_TRIAL_DISPOSITIONS
            or tuple(item.arm for item in self.arms)
            != PREDICTION_FAILURE_TRIAL_ARM_ORDER
            or self.arm_refs != tuple(item.arm_id for item in self.arms)
        ):
            raise ValueError(
                "PredictionFailure trial declaration changed its frozen design."
            )
        expected_signature = stable_id(
            "prediction_failure_trial_matched_control",
            PREDICTION_FAILURE_TRIAL_PREREGISTRATION_VERSION,
            self.canonical_kernel_id,
            self.canonical_fingerprint,
            bundle.bundle_id,
            receipt.ablation_target.target_id,
            self.held_constant_ref_set_sha256,
            self.shared_design_seed,
            self.outcome_policy_sha256,
        )
        if self.matched_control_signature != expected_signature:
            raise ValueError(
                "PredictionFailure matched-control signature drift detected."
            )
        for arm in self.arms:
            expected_arm = PredictionFailureTrialArmDeclaration.build(
                arm=arm.arm,
                target_ref=self.target_ref,
                shared_design_seed=self.shared_design_seed,
                requested_budget=self.outcome_policy.per_arm_budget,
                held_constant_ref_set_sha256=self.held_constant_ref_set_sha256,
                matched_control_signature=self.matched_control_signature,
            )
            if arm != expected_arm:
                raise ValueError(
                    "PredictionFailure trial arms are not exactly matched."
                )
        if (
            not self.durable_before_execution
            or not self.separate_result_sidecar_required
            or not self.same_canonical_checkpoint_required
            or not self.same_seed_required
            or not self.complete_protected_evidence_required
            or not self.target_visibility_only_difference_required
            or not self.explicit_valid_null_required
            or not self.trace_derived_outcome_required
            or self.runner_implemented
            or self.execution_plans_materialized
            or self.trial_executed
            or self.traces_observed
            or self.outcomes_observed
            or self.target_specific_effect_observed
            or self.causal_attribution_enabled
            or self.resolution_authority_enabled
            or self.promotion_authority_enabled
            or self.policy_rewrite_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError(
                "PredictionFailure trial declaration crossed its claim boundary."
            )
        expected = stable_id(
            "prediction_failure_trial_declaration",
            self.model_dump(mode="json", exclude={"declaration_id"}),
        )
        if self.declaration_id != expected:
            raise ValueError("PredictionFailure trial-declaration checksum mismatch.")
        return self


class PredictionFailureTrialPreregistrationEnvelope(BaseModel):
    """Canonical immutable bytes proving the matched design existed first."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = PREDICTION_FAILURE_TRIAL_PREREGISTRATION_FORMAT
    declaration: PredictionFailureTrialDeclaration
    declaration_sha256: str

    @classmethod
    def build(
        cls,
        declaration: PredictionFailureTrialDeclaration,
    ) -> "PredictionFailureTrialPreregistrationEnvelope":
        frozen = PredictionFailureTrialDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        return cls(
            declaration=frozen,
            declaration_sha256=_digest(frozen.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(
        self,
    ) -> "PredictionFailureTrialPreregistrationEnvelope":
        if (
            self.sidecar_format
            != PREDICTION_FAILURE_TRIAL_PREREGISTRATION_FORMAT
            or self.declaration_sha256
            != _digest(self.declaration.model_dump(mode="json"))
        ):
            raise ValueError(
                "PredictionFailure trial preregistration digest mismatch."
            )
        return self


def _validate_declaration(
    declaration: PredictionFailureTrialDeclaration,
    kernel: VerdantKernel,
    hypothesis_protocol: PredictionFailureHypothesisProtocol | None = None,
) -> PredictionFailureTrialDeclaration:
    protocol = hypothesis_protocol or PredictionFailureHypothesisProtocol()
    if (
        declaration.canonical_kernel_id != kernel.state.identity.kernel_id
        or declaration.canonical_fingerprint != kernel.fingerprint()
        or declaration.canonical_cycle != kernel.state.cycle
    ):
        raise PredictionFailureTrialPreregistrationIntegrityError(
            "PredictionFailure preregistration belongs to another canonical checkpoint."
        )
    try:
        protocol.validate(kernel, declaration.hypothesis_bundle)
        expected = PredictionFailureTrialDeclaration.build(
            kernel=kernel,
            hypothesis_bundle=declaration.hypothesis_bundle,
            hypothesis_protocol=protocol,
            outcome_policy=declaration.outcome_policy,
        )
    except (ValueError, RuntimeError) as exc:
        raise PredictionFailureTrialPreregistrationIntegrityError(str(exc)) from exc
    if declaration != expected:
        raise PredictionFailureTrialPreregistrationIntegrityError(
            "PredictionFailure preregistration does not match canonical provenance."
        )
    return expected


def prediction_failure_trial_preregistration_bytes(
    envelope: PredictionFailureTrialPreregistrationEnvelope,
) -> bytes:
    validated = PredictionFailureTrialPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureTrialPreregistrationIntegrityError(
            "PredictionFailure preregistration exceeds its size limit."
        )
    return data


def read_prediction_failure_trial_preregistration(
    path: str | Path,
) -> PredictionFailureTrialPreregistrationEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureTrialPreregistrationIntegrityError(
                "PredictionFailure preregistration exceeds its size limit."
            )
        envelope = PredictionFailureTrialPreregistrationEnvelope.model_validate_json(
            data
        )
        if prediction_failure_trial_preregistration_bytes(envelope) != data:
            raise PredictionFailureTrialPreregistrationIntegrityError(
                "PredictionFailure preregistration is not canonical."
            )
        return envelope
    except PredictionFailureTrialPreregistrationIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise PredictionFailureTrialPreregistrationIntegrityError(
            "Invalid PredictionFailure trial preregistration."
        ) from exc


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise PredictionFailureTrialPreregistrationIntegrityError(
            "PredictionFailure preregistration requires POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise PredictionFailureTrialPreregistrationIntegrityError(
                "PredictionFailure preregistration path already contains "
                "different evidence."
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


def save_prediction_failure_trial_preregistration(
    path: str | Path,
    envelope: PredictionFailureTrialPreregistrationEnvelope,
    *,
    kernel: VerdantKernel,
    hypothesis_protocol: PredictionFailureHypothesisProtocol | None = None,
) -> str:
    validated = PredictionFailureTrialPreregistrationEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _validate_declaration(validated.declaration, kernel, hypothesis_protocol)
    _write_immutable(
        Path(path), prediction_failure_trial_preregistration_bytes(validated)
    )
    return validated.declaration.declaration_id


def load_prediction_failure_trial_preregistration(
    path: str | Path,
    *,
    kernel: VerdantKernel,
    hypothesis_protocol: PredictionFailureHypothesisProtocol | None = None,
) -> PredictionFailureTrialPreregistrationEnvelope:
    envelope = read_prediction_failure_trial_preregistration(path)
    _validate_declaration(envelope.declaration, kernel, hypothesis_protocol)
    return envelope


class PredictionFailureTrialPreregistrar:
    """Publish one canonical, immutable design without executing any arm."""

    def register(
        self,
        path: str | Path,
        *,
        kernel: VerdantKernel,
        hypothesis_bundle: PredictionFailureHypothesisBundle,
        hypothesis_protocol: PredictionFailureHypothesisProtocol | None = None,
    ) -> PredictionFailureTrialPreregistrationEnvelope:
        canonical_before = kernel.fingerprint()
        try:
            declaration = PredictionFailureTrialDeclaration.build(
                kernel=kernel,
                hypothesis_bundle=hypothesis_bundle,
                hypothesis_protocol=hypothesis_protocol,
            )
            envelope = PredictionFailureTrialPreregistrationEnvelope.build(
                declaration
            )
            save_prediction_failure_trial_preregistration(
                path,
                envelope,
                kernel=kernel,
                hypothesis_protocol=hypothesis_protocol,
            )
            loaded = load_prediction_failure_trial_preregistration(
                path,
                kernel=kernel,
                hypothesis_protocol=hypothesis_protocol,
            )
            if loaded != envelope:
                raise PredictionFailureTrialPreregistrationIntegrityError(
                    "Persisted PredictionFailure preregistration changed its "
                    "declaration."
                )
            return loaded
        except PredictionFailureTrialPreregistrationIntegrityError:
            raise
        except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
            raise PredictionFailureTrialPreregistrationIntegrityError(
                str(exc)
            ) from exc
        finally:
            if kernel.fingerprint() != canonical_before:
                raise RuntimeError(
                    "PredictionFailure preregistration mutated canonical state."
                )
