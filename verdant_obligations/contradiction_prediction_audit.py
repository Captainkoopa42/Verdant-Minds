"""Calibration-only cardinality prediction audit for Contradiction.

This explicitly invoked v0.42 experiment takes the calibration profile already
frozen by v0.40 and applies one preregistered, cardinality-only prediction rule
to two v0.41 downstream outcome contexts.  The contexts share the exact same
canonical source, held-out simulation trace, Lens lineage, and workspace
controls; only the preregistered workspace admission threshold differs.  The
normal context produces an admission gain while the zero-threshold context is
an explicit valid null.

The rule is durably committed after calibration and before held-out execution.
Its derivation API accepts no held-out observation, outcome receipt, or outcome
ledger.  The matched valid-null control deliberately falsifies the current
cardinality-only rule: the positive context matches, but the same prediction is
a false positive in the control.  The artifact therefore records evidence
*against* predictive discrimination and grants no truth, resolution,
promotion, policy-rewrite, or canonical-write authority.
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

from pydantic import BaseModel, ConfigDict, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_calibration_stage import (
    ContradictionCalibrationStageIntegrityError,
    ContradictionCalibrationStageReceipt,
    ContradictionCalibrationStageSidecarEnvelope,
    ContradictionDurableDimensionTrialRunner,
)
from .contradiction_dimension_criterion import (
    ContradictionDimensionCriterionDeclaration,
    ContradictionLensOutputDimension,
    ContradictionProjectionCardinalityProfile,
)
from .contradiction_downstream_outcome import (
    ContradictionDownstreamOutcomeDeclaration,
    ContradictionDownstreamOutcomeDisposition,
    ContradictionDownstreamOutcomeIntegrityError,
    ContradictionDownstreamOutcomeObserver,
    ContradictionDownstreamOutcomePolicy,
    ContradictionDownstreamPreregistrationEnvelope,
    ContradictionDownstreamResultEnvelope,
    _validate_stage,
    load_contradiction_downstream_preregistration,
    save_contradiction_downstream_preregistration,
)
from .contradiction_hypotheses import ContradictionHypothesisProtocol
from .contradiction_trial_controls import (
    ContradictionLensTrialIntegrityError,
    ContradictionLensTrialObservation,
    ContradictionLensTrialPairContext,
)
from .counterfactual import (
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError


CONTRADICTION_PREDICTION_AUDIT_VERSION = (
    "contradiction_prediction_audit_v0.42"
)
CONTRADICTION_PREDICTION_RULE_FORMAT = (
    "verdant-contradiction-prediction-rule-v1"
)
CONTRADICTION_PREDICTION_AUDIT_FORMAT = (
    "verdant-contradiction-prediction-audit-v1"
)
CONTRADICTION_PREDICTION_PROFILE_MAPPING = (
    (
        ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE,
        ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN,
    ),
    (
        ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES,
        ContradictionDownstreamOutcomeDisposition.VALID_NULL,
    ),
    (
        ContradictionProjectionCardinalityProfile.ASYMMETRIC_ROUTE_CARDINALITY,
        ContradictionDownstreamOutcomeDisposition.VALID_NULL,
    ),
)
_POSITIVE_MINIMUM_ADMISSION_SCORE = 0.28
_CONTROL_MINIMUM_ADMISSION_SCORE = 0.0
_MAX_SIDECAR_BYTES = 128 * 1024 * 1024
_EMPTY_SIMULATION_FINGERPRINT = SimulationLedger().fingerprint()


class ContradictionPredictionAuditIntegrityError(RuntimeError):
    """Raised when prediction evidence crosses its frozen boundary."""


class ContradictionPredictionContextRole(str, Enum):
    POSITIVE = "positive"
    VALID_NULL_CONTROL = "valid_null_control"


class ContradictionPredictionAuditDisposition(str, Enum):
    CARDINALITY_ONLY_FALSE_POSITIVE = "cardinality_only_false_positive"
    POSITIVE_CONTEXT_MISMATCH = "positive_context_mismatch"
    CONTROL_NOT_VALID_NULL = "control_not_valid_null"


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
                else tuple(
                    nested.value if isinstance(nested, Enum) else nested
                    for nested in item
                )
                if isinstance(item, tuple)
                else item
                for item in value
            )
        else:
            payload[key] = value
    return payload


def _projection_counts(
    observation: ContradictionLensTrialObservation,
) -> tuple[int, int]:
    return tuple(
        len(item.projected_claim_refs)
        for item in observation.lens_observation.route_projections
    )


def _cardinality_profile(
    counts: tuple[int, int],
) -> ContradictionProjectionCardinalityProfile:
    if counts == (1, 1):
        return ContradictionProjectionCardinalityProfile.SINGLETON_PER_ROUTE
    if counts[0] == counts[1]:
        return (
            ContradictionProjectionCardinalityProfile.EQUAL_MULTI_REFERENCE_ROUTES
        )
    return ContradictionProjectionCardinalityProfile.ASYMMETRIC_ROUTE_CARDINALITY


def _normalized_outcome_context(
    declaration: ContradictionDownstreamOutcomeDeclaration,
) -> dict[str, Any]:
    payload = declaration.model_dump(mode="json")
    payload["declaration_id"] = "normalized"
    payload["policy"]["minimum_admission_score"] = "matched-control"
    payload["policy_sha256"] = "normalized"
    payload["shadow_workspace_policy"]["minimum_admission_score"] = (
        "matched-control"
    )
    payload["shadow_workspace_policy_sha256"] = "normalized"
    return payload


def _outcome_context_control_signature(
    declaration: ContradictionDownstreamOutcomeDeclaration,
) -> str:
    return stable_id(
        "contradiction_prediction_outcome_control",
        CONTRADICTION_PREDICTION_AUDIT_VERSION,
        _normalized_outcome_context(declaration),
    )


def _validate_matched_declarations(
    positive: ContradictionDownstreamOutcomeDeclaration,
    control: ContradictionDownstreamOutcomeDeclaration,
) -> str:
    if positive.pair_context != control.pair_context:
        raise ValueError("Prediction contexts changed their held-out pair.")
    if (
        positive.policy.minimum_admission_score
        != _POSITIVE_MINIMUM_ADMISSION_SCORE
        or control.policy.minimum_admission_score
        != _CONTROL_MINIMUM_ADMISSION_SCORE
    ):
        raise ValueError("Prediction contexts changed their frozen thresholds.")
    positive_signature = _outcome_context_control_signature(positive)
    control_signature = _outcome_context_control_signature(control)
    if positive_signature != control_signature:
        raise ValueError("Prediction contexts are not exact matched controls.")
    return positive_signature


class ContradictionCardinalityPredictionPolicy(BaseModel):
    """Preregistered mapping hypothesis with no outcome-dependent inputs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = CONTRADICTION_PREDICTION_AUDIT_VERSION
    selected_dimension: ContradictionLensOutputDimension = (
        ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
    )
    profile_mapping: tuple[
        tuple[
            ContradictionProjectionCardinalityProfile,
            ContradictionDownstreamOutcomeDisposition,
        ],
        ...,
    ] = CONTRADICTION_PREDICTION_PROFILE_MAPPING
    cardinality_only: bool = True
    downstream_policy_input_permitted: bool = False
    held_out_trace_input_permitted: bool = False
    outcome_receipt_input_permitted: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> "ContradictionCardinalityPredictionPolicy":
        if (
            self.policy_version != CONTRADICTION_PREDICTION_AUDIT_VERSION
            or self.selected_dimension
            != ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            or self.profile_mapping != CONTRADICTION_PREDICTION_PROFILE_MAPPING
            or not self.cardinality_only
            or self.downstream_policy_input_permitted
            or self.held_out_trace_input_permitted
            or self.outcome_receipt_input_permitted
        ):
            raise ValueError("Prediction policy crossed its fixed grammar.")
        return self

    def prediction_for(
        self,
        profile: ContradictionProjectionCardinalityProfile,
    ) -> ContradictionDownstreamOutcomeDisposition:
        return dict(self.profile_mapping)[profile]

    def fingerprint(self) -> str:
        return _digest(self.model_dump(mode="json"))


class ContradictionCalibrationPredictionRule(FrozenRecord):
    """Rule selected solely from the durable calibration-stage profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    rule_version: str = CONTRADICTION_PREDICTION_AUDIT_VERSION
    policy: ContradictionCardinalityPredictionPolicy
    policy_sha256: str
    positive_declaration: ContradictionDownstreamOutcomeDeclaration
    positive_declaration_ref: str
    positive_preregistration_sha256: str
    control_declaration: ContradictionDownstreamOutcomeDeclaration
    control_declaration_ref: str
    control_preregistration_sha256: str
    outcome_context_control_signature: str
    calibration_stage_receipt: ContradictionCalibrationStageReceipt
    calibration_stage_receipt_ref: str
    calibration_stage_receipt_sha256: str
    calibration_stage_sha256: str
    calibration_context_ref: str
    target_held_out_context_ref: str
    lens_fingerprint: str
    selected_dimension: ContradictionLensOutputDimension
    calibration_cardinalities: tuple[int, int]
    calibration_profile: ContradictionProjectionCardinalityProfile
    predicted_outcome: ContradictionDownstreamOutcomeDisposition
    outcome_declarations_durable_before_calibration: bool = True
    derived_from_calibration_only: bool = True
    held_out_execution_started: bool = False
    held_out_trace_consulted: bool = False
    outcome_receipt_consulted: bool = False
    downstream_policy_consulted_for_prediction: bool = False
    frozen_before_held_out_execution: bool = True
    simulated_only: bool = True
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
        positive_preregistration: ContradictionDownstreamPreregistrationEnvelope,
        control_preregistration: ContradictionDownstreamPreregistrationEnvelope,
        calibration_stage: ContradictionCalibrationStageSidecarEnvelope,
        *,
        positive_preregistration_sha256: str,
        control_preregistration_sha256: str,
        calibration_stage_sha256: str,
        policy: ContradictionCardinalityPredictionPolicy | None = None,
    ) -> "ContradictionCalibrationPredictionRule":
        positive = ContradictionDownstreamPreregistrationEnvelope.model_validate(
            positive_preregistration.model_dump(mode="json")
        )
        control = ContradictionDownstreamPreregistrationEnvelope.model_validate(
            control_preregistration.model_dump(mode="json")
        )
        stage = ContradictionCalibrationStageSidecarEnvelope.model_validate(
            calibration_stage.model_dump(mode="json")
        )
        declared_policy = ContradictionCardinalityPredictionPolicy.model_validate(
            (policy or ContradictionCardinalityPredictionPolicy()).model_dump(
                mode="json"
            )
        )
        context_signature = _validate_matched_declarations(
            positive.declaration,
            control.declaration,
        )
        receipt = stage.stage_receipt
        criterion = receipt.criterion
        values = {
            "rule_version": CONTRADICTION_PREDICTION_AUDIT_VERSION,
            "policy": declared_policy,
            "policy_sha256": declared_policy.fingerprint(),
            "positive_declaration": positive.declaration,
            "positive_declaration_ref": positive.declaration.declaration_id,
            "positive_preregistration_sha256": (
                positive_preregistration_sha256
            ),
            "control_declaration": control.declaration,
            "control_declaration_ref": control.declaration.declaration_id,
            "control_preregistration_sha256": (
                control_preregistration_sha256
            ),
            "outcome_context_control_signature": context_signature,
            "calibration_stage_receipt": receipt,
            "calibration_stage_receipt_ref": receipt.stage_receipt_id,
            "calibration_stage_receipt_sha256": _digest(
                receipt.model_dump(mode="json")
            ),
            "calibration_stage_sha256": calibration_stage_sha256,
            "calibration_context_ref": receipt.calibration_context_ref,
            "target_held_out_context_ref": receipt.held_out_context_ref,
            "lens_fingerprint": receipt.lens_fingerprint,
            "selected_dimension": criterion.selected_dimension,
            "calibration_cardinalities": criterion.calibration_cardinalities,
            "calibration_profile": criterion.calibration_profile,
            "predicted_outcome": declared_policy.prediction_for(
                criterion.calibration_profile
            ),
            "outcome_declarations_durable_before_calibration": True,
            "derived_from_calibration_only": True,
            "held_out_execution_started": False,
            "held_out_trace_consulted": False,
            "outcome_receipt_consulted": False,
            "downstream_policy_consulted_for_prediction": False,
            "frozen_before_held_out_execution": True,
            "simulated_only": True,
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
        values["rule_id"] = stable_id(
            "contradiction_calibration_prediction_rule",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_rule(self) -> "ContradictionCalibrationPredictionRule":
        receipt = self.calibration_stage_receipt
        criterion = receipt.criterion
        expected_context_signature = _validate_matched_declarations(
            self.positive_declaration,
            self.control_declaration,
        )
        expected = {
            "policy_sha256": self.policy.fingerprint(),
            "positive_declaration_ref": self.positive_declaration.declaration_id,
            "control_declaration_ref": self.control_declaration.declaration_id,
            "outcome_context_control_signature": expected_context_signature,
            "calibration_stage_receipt_ref": receipt.stage_receipt_id,
            "calibration_stage_receipt_sha256": _digest(
                receipt.model_dump(mode="json")
            ),
            "calibration_context_ref": receipt.calibration_context_ref,
            "target_held_out_context_ref": receipt.held_out_context_ref,
            "lens_fingerprint": receipt.lens_fingerprint,
            "selected_dimension": criterion.selected_dimension,
            "calibration_cardinalities": criterion.calibration_cardinalities,
            "calibration_profile": criterion.calibration_profile,
            "predicted_outcome": self.policy.prediction_for(
                criterion.calibration_profile
            ),
        }
        if self.rule_version != CONTRADICTION_PREDICTION_AUDIT_VERSION:
            raise ValueError("Unknown Contradiction prediction-rule version.")
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Prediction rule changed calibration evidence.")
        if (
            self.positive_declaration.pair_context != receipt.pair_context
            or self.control_declaration.pair_context != receipt.pair_context
            or criterion.selected_dimension
            != ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            or receipt.held_out_execution_started
            or receipt.held_out_trace_consulted
            or not receipt.calibration_only
        ):
            raise ValueError("Prediction rule crossed its calibration-only API.")
        if not all(
            _is_sha256(value)
            for value in (
                self.positive_preregistration_sha256,
                self.control_preregistration_sha256,
                self.calibration_stage_sha256,
            )
        ):
            raise ValueError("Prediction rule has invalid durable provenance.")
        if any(
            (
                not self.outcome_declarations_durable_before_calibration,
                not self.derived_from_calibration_only,
                self.held_out_execution_started,
                self.held_out_trace_consulted,
                self.outcome_receipt_consulted,
                self.downstream_policy_consulted_for_prediction,
                not self.frozen_before_held_out_execution,
                not self.simulated_only,
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
            raise ValueError("Prediction rule crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_calibration_prediction_rule",
            self.model_dump(mode="json", exclude={"rule_id"}),
        )
        if self.rule_id != expected_id:
            raise ValueError("Prediction-rule checksum mismatch.")
        return self


class ContradictionPredictionRuleEnvelope(BaseModel):
    """Canonical rule bytes committed before held-out execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_PREDICTION_RULE_FORMAT
    rule: ContradictionCalibrationPredictionRule
    rule_sha256: str

    @classmethod
    def build(
        cls,
        rule: ContradictionCalibrationPredictionRule,
    ) -> "ContradictionPredictionRuleEnvelope":
        frozen = ContradictionCalibrationPredictionRule.model_validate(
            rule.model_dump(mode="json")
        )
        return cls(
            rule=frozen,
            rule_sha256=_digest(frozen.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionPredictionRuleEnvelope":
        if self.sidecar_format != CONTRADICTION_PREDICTION_RULE_FORMAT:
            raise ValueError("Unknown Contradiction prediction-rule format.")
        if self.rule_sha256 != _digest(self.rule.model_dump(mode="json")):
            raise ValueError("Prediction-rule sidecar digest mismatch.")
        return self


class ContradictionPredictionContextEvaluation(FrozenRecord):
    """One unchanged rule application to one downstream context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: str
    evaluation_version: str = CONTRADICTION_PREDICTION_AUDIT_VERSION
    role: ContradictionPredictionContextRole
    rule_ref: str
    declaration_ref: str
    outcome_result_sha256: str
    held_out_observation_ref: str
    held_out_cardinalities: tuple[int, int]
    held_out_profile: ContradictionProjectionCardinalityProfile
    predicted_outcome: ContradictionDownstreamOutcomeDisposition
    observed_outcome: ContradictionDownstreamOutcomeDisposition
    prediction_matches_observation: bool
    valid_null_control: bool
    false_positive_observed: bool
    rule_applied_unchanged: bool = True
    held_out_trace_used_only_for_evaluation: bool = True
    downstream_policy_used_only_for_observation: bool = True

    @classmethod
    def build(
        cls,
        rule: ContradictionCalibrationPredictionRule,
        role: ContradictionPredictionContextRole,
        result: ContradictionDownstreamResultEnvelope,
    ) -> "ContradictionPredictionContextEvaluation":
        receipt = result.receipt
        observation = receipt.held_out_observation
        counts = _projection_counts(observation)
        profile = _cardinality_profile(counts)
        predicted = rule.policy.prediction_for(profile)
        expected_declaration = (
            rule.positive_declaration
            if role == ContradictionPredictionContextRole.POSITIVE
            else rule.control_declaration
        )
        if receipt.declaration != expected_declaration:
            raise ValueError("Prediction evaluation received a foreign outcome.")
        matches = predicted == receipt.disposition
        valid_null_control = (
            role == ContradictionPredictionContextRole.VALID_NULL_CONTROL
        )
        values = {
            "evaluation_version": CONTRADICTION_PREDICTION_AUDIT_VERSION,
            "role": role,
            "rule_ref": rule.rule_id,
            "declaration_ref": expected_declaration.declaration_id,
            "outcome_result_sha256": _digest(result.model_dump(mode="json")),
            "held_out_observation_ref": observation.observation_id,
            "held_out_cardinalities": counts,
            "held_out_profile": profile,
            "predicted_outcome": predicted,
            "observed_outcome": receipt.disposition,
            "prediction_matches_observation": matches,
            "valid_null_control": valid_null_control,
            "false_positive_observed": valid_null_control
            and predicted
            == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            and receipt.disposition
            == ContradictionDownstreamOutcomeDisposition.VALID_NULL,
            "rule_applied_unchanged": True,
            "held_out_trace_used_only_for_evaluation": True,
            "downstream_policy_used_only_for_observation": True,
        }
        values["evaluation_id"] = stable_id(
            "contradiction_prediction_context_evaluation",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_evaluation(
        self,
    ) -> "ContradictionPredictionContextEvaluation":
        expected_match = self.predicted_outcome == self.observed_outcome
        control = self.role == ContradictionPredictionContextRole.VALID_NULL_CONTROL
        expected_false_positive = (
            control
            and self.predicted_outcome
            == ContradictionDownstreamOutcomeDisposition.ADMISSION_GAIN
            and self.observed_outcome
            == ContradictionDownstreamOutcomeDisposition.VALID_NULL
        )
        if self.evaluation_version != CONTRADICTION_PREDICTION_AUDIT_VERSION:
            raise ValueError("Unknown prediction-context evaluation version.")
        if (
            not _is_sha256(self.outcome_result_sha256)
            or self.prediction_matches_observation != expected_match
            or self.valid_null_control != control
            or self.false_positive_observed != expected_false_positive
            or not self.rule_applied_unchanged
            or not self.held_out_trace_used_only_for_evaluation
            or not self.downstream_policy_used_only_for_observation
        ):
            raise ValueError("Prediction-context evaluation was altered.")
        expected_id = stable_id(
            "contradiction_prediction_context_evaluation",
            self.model_dump(mode="json", exclude={"evaluation_id"}),
        )
        if self.evaluation_id != expected_id:
            raise ValueError("Prediction-context evaluation checksum mismatch.")
        return self


def _audit_disposition(
    positive: ContradictionPredictionContextEvaluation,
    control: ContradictionPredictionContextEvaluation,
) -> ContradictionPredictionAuditDisposition:
    if control.observed_outcome != ContradictionDownstreamOutcomeDisposition.VALID_NULL:
        return ContradictionPredictionAuditDisposition.CONTROL_NOT_VALID_NULL
    if not positive.prediction_matches_observation:
        return ContradictionPredictionAuditDisposition.POSITIVE_CONTEXT_MISMATCH
    return ContradictionPredictionAuditDisposition.CARDINALITY_ONLY_FALSE_POSITIVE


class ContradictionPredictionAuditReceipt(FrozenRecord):
    """Matched-control falsification result with no promotion authority."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = CONTRADICTION_PREDICTION_AUDIT_VERSION
    rule: ContradictionCalibrationPredictionRule
    rule_ref: str
    positive_evaluation: ContradictionPredictionContextEvaluation
    control_evaluation: ContradictionPredictionContextEvaluation
    disposition: ContradictionPredictionAuditDisposition
    same_held_out_observation_verified: bool = True
    same_cardinality_input_verified: bool = True
    same_simulation_ledger_verified: bool = True
    matched_outcome_controls_verified: bool = True
    rule_frozen_before_held_out_verified: bool = True
    positive_association_observed: bool
    valid_null_false_positive_observed: bool
    cardinality_only_rule_falsified: bool
    evidence_preserved: bool = True
    anti_suppression_verified: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    independent_held_out_replication_observed: bool = False
    source_independence_observed: bool = False
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
        rule: ContradictionCalibrationPredictionRule,
        positive_result: ContradictionDownstreamResultEnvelope,
        control_result: ContradictionDownstreamResultEnvelope,
    ) -> "ContradictionPredictionAuditReceipt":
        frozen_rule = ContradictionCalibrationPredictionRule.model_validate(
            rule.model_dump(mode="json")
        )
        positive = ContradictionPredictionContextEvaluation.build(
            frozen_rule,
            ContradictionPredictionContextRole.POSITIVE,
            positive_result,
        )
        control = ContradictionPredictionContextEvaluation.build(
            frozen_rule,
            ContradictionPredictionContextRole.VALID_NULL_CONTROL,
            control_result,
        )
        if (
            positive.held_out_observation_ref
            != control.held_out_observation_ref
            or positive.held_out_cardinalities
            != control.held_out_cardinalities
            or positive.held_out_profile != control.held_out_profile
        ):
            raise ValueError("Prediction audit did not reuse one held-out input.")
        disposition = _audit_disposition(positive, control)
        false_positive = control.false_positive_observed
        values = {
            "receipt_version": CONTRADICTION_PREDICTION_AUDIT_VERSION,
            "rule": frozen_rule,
            "rule_ref": frozen_rule.rule_id,
            "positive_evaluation": positive,
            "control_evaluation": control,
            "disposition": disposition,
            "same_held_out_observation_verified": True,
            "same_cardinality_input_verified": True,
            "same_simulation_ledger_verified": True,
            "matched_outcome_controls_verified": True,
            "rule_frozen_before_held_out_verified": True,
            "positive_association_observed": (
                positive.prediction_matches_observation
            ),
            "valid_null_false_positive_observed": false_positive,
            "cardinality_only_rule_falsified": false_positive
            or not positive.prediction_matches_observation,
            "evidence_preserved": True,
            "anti_suppression_verified": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "independent_held_out_replication_observed": False,
            "source_independence_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "policy_rewrite_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_prediction_audit_receipt",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionPredictionAuditReceipt":
        positive = self.positive_evaluation
        control = self.control_evaluation
        expected_disposition = _audit_disposition(positive, control)
        false_positive = control.false_positive_observed
        if self.receipt_version != CONTRADICTION_PREDICTION_AUDIT_VERSION:
            raise ValueError("Unknown Contradiction prediction-audit version.")
        if (
            self.rule_ref != self.rule.rule_id
            or positive.rule_ref != self.rule_ref
            or control.rule_ref != self.rule_ref
            or positive.role != ContradictionPredictionContextRole.POSITIVE
            or control.role
            != ContradictionPredictionContextRole.VALID_NULL_CONTROL
            or self.disposition != expected_disposition
            or positive.held_out_observation_ref
            != control.held_out_observation_ref
            or positive.held_out_cardinalities
            != control.held_out_cardinalities
            or positive.held_out_profile != control.held_out_profile
            or self.positive_association_observed
            != positive.prediction_matches_observation
            or self.valid_null_false_positive_observed != false_positive
            or self.cardinality_only_rule_falsified
            != (false_positive or not positive.prediction_matches_observation)
        ):
            raise ValueError("Prediction audit changed matched-control evidence.")
        if any(
            (
                not self.same_held_out_observation_verified,
                not self.same_cardinality_input_verified,
                not self.same_simulation_ledger_verified,
                not self.matched_outcome_controls_verified,
                not self.rule_frozen_before_held_out_verified,
                not self.evidence_preserved,
                not self.anti_suppression_verified,
                not self.simulated_only,
                self.predictive_discrimination_observed,
                self.dimensional_separation_observed,
                self.independent_held_out_replication_observed,
                self.source_independence_observed,
                self.external_outcome_observed,
                self.resolution_trial_ready,
                self.truth_selection_authority_enabled,
                self.observed_outcome_authority_enabled,
                self.resolution_authority_enabled,
                self.policy_rewrite_authority_enabled,
                self.canonical_commit_permitted,
            )
        ):
            raise ValueError("Prediction audit crossed its claim boundary.")
        expected_id = stable_id(
            "contradiction_prediction_audit_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected_id:
            raise ValueError("Prediction-audit receipt checksum mismatch.")
        return self


class ContradictionPredictionAuditEnvelope(BaseModel):
    """Atomic audit result containing both observations and one ledger."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = CONTRADICTION_PREDICTION_AUDIT_FORMAT
    receipt: ContradictionPredictionAuditReceipt
    receipt_sha256: str
    positive_result: ContradictionDownstreamResultEnvelope
    positive_result_sha256: str
    control_result: ContradictionDownstreamResultEnvelope
    control_result_sha256: str

    @classmethod
    def build(
        cls,
        rule: ContradictionCalibrationPredictionRule,
        positive_result: ContradictionDownstreamResultEnvelope,
        control_result: ContradictionDownstreamResultEnvelope,
    ) -> "ContradictionPredictionAuditEnvelope":
        positive = ContradictionDownstreamResultEnvelope.model_validate(
            positive_result.model_dump(mode="json")
        )
        control = ContradictionDownstreamResultEnvelope.model_validate(
            control_result.model_dump(mode="json")
        )
        if (
            positive.held_out_simulation_state
            != control.held_out_simulation_state
            or positive.held_out_simulation_fingerprint
            != control.held_out_simulation_fingerprint
            or positive.receipt.held_out_observation
            != control.receipt.held_out_observation
        ):
            raise ValueError("Prediction audit changed its shared held-out trace.")
        receipt = ContradictionPredictionAuditReceipt.build(
            rule,
            positive,
            control,
        )
        return cls(
            receipt=receipt,
            receipt_sha256=_digest(receipt.model_dump(mode="json")),
            positive_result=positive,
            positive_result_sha256=_digest(positive.model_dump(mode="json")),
            control_result=control,
            control_result_sha256=_digest(control.model_dump(mode="json")),
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionPredictionAuditEnvelope":
        if self.sidecar_format != CONTRADICTION_PREDICTION_AUDIT_FORMAT:
            raise ValueError("Unknown Contradiction prediction-audit format.")
        if (
            self.receipt_sha256 != _digest(self.receipt.model_dump(mode="json"))
            or self.positive_result_sha256
            != _digest(self.positive_result.model_dump(mode="json"))
            or self.control_result_sha256
            != _digest(self.control_result.model_dump(mode="json"))
        ):
            raise ValueError("Prediction-audit sidecar digest mismatch.")
        if (
            self.positive_result.held_out_simulation_state
            != self.control_result.held_out_simulation_state
            or self.positive_result.held_out_simulation_fingerprint
            != self.control_result.held_out_simulation_fingerprint
            or self.positive_result.receipt.held_out_observation
            != self.control_result.receipt.held_out_observation
            or self.receipt.positive_evaluation.outcome_result_sha256
            != self.positive_result_sha256
            or self.receipt.control_evaluation.outcome_result_sha256
            != self.control_result_sha256
        ):
            raise ValueError("Prediction-audit sidecar changed shared evidence.")
        return self


def contradiction_prediction_rule_bytes(
    envelope: ContradictionPredictionRuleEnvelope,
) -> bytes:
    validated = ContradictionPredictionRuleEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction-rule sidecar exceeds its size limit."
        )
    return data


def contradiction_prediction_audit_bytes(
    envelope: ContradictionPredictionAuditEnvelope,
) -> bytes:
    validated = ContradictionPredictionAuditEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction-audit sidecar exceeds its size limit."
        )
    return data


def read_contradiction_prediction_rule(
    path: str | Path,
) -> ContradictionPredictionRuleEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionAuditIntegrityError(
                "Prediction-rule sidecar exceeds its size limit."
            )
        envelope = ContradictionPredictionRuleEnvelope.model_validate_json(data)
        if contradiction_prediction_rule_bytes(envelope) != data:
            raise ContradictionPredictionAuditIntegrityError(
                "Prediction-rule JSON is not canonical."
            )
        return envelope
    except ContradictionPredictionAuditIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionAuditIntegrityError(
            "Invalid Contradiction prediction-rule sidecar."
        ) from exc


def read_contradiction_prediction_audit(
    path: str | Path,
) -> ContradictionPredictionAuditEnvelope:
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise ContradictionPredictionAuditIntegrityError(
                "Prediction-audit sidecar exceeds its size limit."
            )
        envelope = ContradictionPredictionAuditEnvelope.model_validate_json(data)
        if contradiction_prediction_audit_bytes(envelope) != data:
            raise ContradictionPredictionAuditIntegrityError(
                "Prediction-audit JSON is not canonical."
            )
        return envelope
    except ContradictionPredictionAuditIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionPredictionAuditIntegrityError(
            "Invalid Contradiction prediction-audit sidecar."
        ) from exc


def _lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _write_immutable(path: Path, data: bytes) -> None:
    if os.name != "posix" or fcntl is None:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction sidecar arbitration requires POSIX flock support."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(_lock_path(path), os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        if path.exists():
            if path.read_bytes() == data:
                return
            raise ContradictionPredictionAuditIntegrityError(
                "Prediction sidecar path already committed different evidence."
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


def save_contradiction_prediction_rule(
    path: str | Path,
    envelope: ContradictionPredictionRuleEnvelope,
) -> str:
    validated = ContradictionPredictionRuleEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(Path(path), contradiction_prediction_rule_bytes(validated))
    return validated.rule.rule_id


def save_contradiction_prediction_audit(
    path: str | Path,
    envelope: ContradictionPredictionAuditEnvelope,
) -> str:
    validated = ContradictionPredictionAuditEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _write_immutable(Path(path), contradiction_prediction_audit_bytes(validated))
    return validated.receipt.receipt_id


def load_contradiction_prediction_rule(
    rule_path: str | Path,
    positive_preregistration_path: str | Path,
    control_preregistration_path: str | Path,
    stage_path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> ContradictionPredictionRuleEnvelope:
    positive = load_contradiction_downstream_preregistration(
        positive_preregistration_path,
        held_out_kernel=held_out_kernel,
    )
    control = load_contradiction_downstream_preregistration(
        control_preregistration_path,
        held_out_kernel=held_out_kernel,
    )
    stage = _validate_stage(
        stage_path,
        positive.declaration,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    if stage.stage_receipt.pair_context != control.declaration.pair_context:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction control is paired with a foreign calibration stage."
        )
    envelope = read_contradiction_prediction_rule(rule_path)
    expected = ContradictionCalibrationPredictionRule.build(
        positive,
        control,
        stage,
        positive_preregistration_sha256=_sha256_bytes(
            Path(positive_preregistration_path).read_bytes()
        ),
        control_preregistration_sha256=_sha256_bytes(
            Path(control_preregistration_path).read_bytes()
        ),
        calibration_stage_sha256=_sha256_bytes(Path(stage_path).read_bytes()),
        policy=envelope.rule.policy,
    )
    if envelope.rule != expected:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction rule lost preregistration or calibration lineage."
        )
    return envelope


def _validate_embedded_result(
    result: ContradictionDownstreamResultEnvelope,
    preregistration: ContradictionDownstreamPreregistrationEnvelope,
    *,
    preregistration_sha256: str,
    stage: ContradictionCalibrationStageSidecarEnvelope,
    stage_sha256: str,
    held_out_kernel: VerdantKernel,
    observer: ContradictionDownstreamOutcomeObserver,
) -> None:
    receipt = result.receipt
    if (
        receipt.declaration != preregistration.declaration
        or receipt.preregistration_sha256 != preregistration_sha256
        or receipt.calibration_stage_sha256 != stage_sha256
        or receipt.calibration_stage_receipt_ref
        != stage.stage_receipt.stage_receipt_id
    ):
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction audit lost downstream durable lineage."
        )
    ledger = SimulationLedger.from_state(result.held_out_simulation_state)
    if ledger.fingerprint() != result.held_out_simulation_fingerprint:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction audit embedded a foreign simulation ledger."
        )
    reproduced = observer.observe(
        held_out_kernel,
        ledger,
        declaration=preregistration.declaration,
        preregistration_sha256=preregistration_sha256,
        calibration_stage_sha256=stage_sha256,
        calibration_stage_receipt_ref=stage.stage_receipt.stage_receipt_id,
        held_out_observation=receipt.held_out_observation,
    )
    if reproduced != receipt:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction audit does not reproduce from held-out traces."
        )


def load_contradiction_prediction_audit(
    audit_path: str | Path,
    rule_path: str | Path,
    positive_preregistration_path: str | Path,
    control_preregistration_path: str | Path,
    stage_path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    observer: ContradictionDownstreamOutcomeObserver | None = None,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> ContradictionPredictionAuditEnvelope:
    rule_envelope = load_contradiction_prediction_rule(
        rule_path,
        positive_preregistration_path,
        control_preregistration_path,
        stage_path,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    positive = load_contradiction_downstream_preregistration(
        positive_preregistration_path,
        held_out_kernel=held_out_kernel,
    )
    control = load_contradiction_downstream_preregistration(
        control_preregistration_path,
        held_out_kernel=held_out_kernel,
    )
    stage = _validate_stage(
        stage_path,
        positive.declaration,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    envelope = read_contradiction_prediction_audit(audit_path)
    outcome_observer = observer or ContradictionDownstreamOutcomeObserver()
    stage_sha256 = _sha256_bytes(Path(stage_path).read_bytes())
    positive_sha256 = _sha256_bytes(
        Path(positive_preregistration_path).read_bytes()
    )
    control_sha256 = _sha256_bytes(
        Path(control_preregistration_path).read_bytes()
    )
    _validate_embedded_result(
        envelope.positive_result,
        positive,
        preregistration_sha256=positive_sha256,
        stage=stage,
        stage_sha256=stage_sha256,
        held_out_kernel=held_out_kernel,
        observer=outcome_observer,
    )
    _validate_embedded_result(
        envelope.control_result,
        control,
        preregistration_sha256=control_sha256,
        stage=stage,
        stage_sha256=stage_sha256,
        held_out_kernel=held_out_kernel,
        observer=outcome_observer,
    )
    expected = ContradictionPredictionAuditEnvelope.build(
        rule_envelope.rule,
        envelope.positive_result,
        envelope.control_result,
    )
    if envelope != expected:
        raise ContradictionPredictionAuditIntegrityError(
            "Prediction audit changed its frozen rule or matched outcomes."
        )
    return envelope


@dataclass(frozen=True)
class ContradictionPredictionAuditRun:
    positive_preregistration_path: Path
    control_preregistration_path: Path
    stage_path: Path
    rule_path: Path
    audit_path: Path
    positive_preregistration: ContradictionDownstreamPreregistrationEnvelope
    control_preregistration: ContradictionDownstreamPreregistrationEnvelope
    stage: ContradictionCalibrationStageSidecarEnvelope
    rule: ContradictionPredictionRuleEnvelope
    audit: ContradictionPredictionAuditEnvelope
    calibration_ledger: SimulationLedger
    held_out_ledger: SimulationLedger
    replayed: bool

    @property
    def receipt(self) -> ContradictionPredictionAuditReceipt:
        return self.audit.receipt


class ContradictionDurablePredictionAuditRunner:
    """Freeze a calibration-only rule, then audit one shared held-out trace."""

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
        positive_preregistration_path: str | Path,
        control_preregistration_path: str | Path,
        stage_path: str | Path,
        rule_path: str | Path,
        audit_path: str | Path,
        calibration_kernel: VerdantKernel,
        calibration_runtime: CounterfactualRuntime,
        held_out_kernel: VerdantKernel,
        held_out_runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
        *,
        pair_context: ContradictionLensTrialPairContext,
        criterion_declaration: ContradictionDimensionCriterionDeclaration,
    ) -> ContradictionPredictionAuditRun:
        positive_path = Path(positive_preregistration_path)
        control_path = Path(control_preregistration_path)
        calibration_path = Path(stage_path)
        frozen_rule_path = Path(rule_path)
        completed_path = Path(audit_path)
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
                raise ContradictionPredictionAuditIntegrityError(
                    "Prediction audit requires pristine caller simulation ledgers."
                )
            if calibration_path.exists() and (
                not positive_path.exists() or not control_path.exists()
            ):
                raise ContradictionPredictionAuditIntegrityError(
                    "Calibration stage predates both prediction contexts."
                )
            if frozen_rule_path.exists() and not calibration_path.exists():
                raise ContradictionPredictionAuditIntegrityError(
                    "Prediction rule is missing its calibration stage."
                )
            if completed_path.exists() and not frozen_rule_path.exists():
                raise ContradictionPredictionAuditIntegrityError(
                    "Prediction audit is missing its frozen rule."
                )

            expected_positive = ContradictionDownstreamOutcomeDeclaration.build(
                pair_context,
                held_out_kernel,
                policy=ContradictionDownstreamOutcomePolicy(
                    minimum_admission_score=(
                        _POSITIVE_MINIMUM_ADMISSION_SCORE
                    )
                ),
            )
            expected_control = ContradictionDownstreamOutcomeDeclaration.build(
                pair_context,
                held_out_kernel,
                policy=ContradictionDownstreamOutcomePolicy(
                    minimum_admission_score=(
                        _CONTROL_MINIMUM_ADMISSION_SCORE
                    )
                ),
            )
            positive = self._ensure_preregistration(
                positive_path,
                expected_positive,
                held_out_kernel,
            )
            control = self._ensure_preregistration(
                control_path,
                expected_control,
                held_out_kernel,
            )
            positive_bytes = positive_path.read_bytes()
            control_bytes = control_path.read_bytes()

            if calibration_path.exists():
                stage = _validate_stage(
                    calibration_path,
                    positive.declaration,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                if stage.stage_receipt.pair_context != control.declaration.pair_context:
                    raise ContradictionPredictionAuditIntegrityError(
                        "Prediction control is paired with a foreign stage."
                    )
            else:
                private_calibration = CounterfactualRuntime()
                stage = self.dimension_runner.prepare_and_persist(
                    calibration_path,
                    calibration_kernel,
                    private_calibration,
                    held_out_kernel,
                    lenses,
                    pair_context=pair_context,
                    criterion_declaration=criterion_declaration,
                ).envelope
            stage_bytes = calibration_path.read_bytes()

            expected_rule = ContradictionCalibrationPredictionRule.build(
                positive,
                control,
                stage,
                positive_preregistration_sha256=_sha256_bytes(positive_bytes),
                control_preregistration_sha256=_sha256_bytes(control_bytes),
                calibration_stage_sha256=_sha256_bytes(stage_bytes),
            )
            if frozen_rule_path.exists():
                rule = load_contradiction_prediction_rule(
                    frozen_rule_path,
                    positive_path,
                    control_path,
                    calibration_path,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                if rule.rule != expected_rule:
                    raise ContradictionPredictionAuditIntegrityError(
                        "Existing prediction rule is different."
                    )
            else:
                rule = ContradictionPredictionRuleEnvelope.build(expected_rule)
                save_contradiction_prediction_rule(frozen_rule_path, rule)
            rule_bytes = frozen_rule_path.read_bytes()

            calibration_ledger = SimulationLedger.from_state(
                stage.calibration_simulation_state
            )
            if completed_path.exists():
                audit = load_contradiction_prediction_audit(
                    completed_path,
                    frozen_rule_path,
                    positive_path,
                    control_path,
                    calibration_path,
                    calibration_kernel=calibration_kernel,
                    held_out_kernel=held_out_kernel,
                    lenses=lenses,
                    observer=self.observer,
                    hypothesis_protocol=self.hypothesis_protocol,
                )
                held_out_ledger = SimulationLedger.from_state(
                    audit.positive_result.held_out_simulation_state
                )
                calibration_runtime.ledger.state = calibration_ledger.snapshot()
                held_out_runtime.ledger.state = held_out_ledger.snapshot()
                published = True
                return ContradictionPredictionAuditRun(
                    positive_preregistration_path=positive_path,
                    control_preregistration_path=control_path,
                    stage_path=calibration_path,
                    rule_path=frozen_rule_path,
                    audit_path=completed_path,
                    positive_preregistration=positive,
                    control_preregistration=control,
                    stage=stage,
                    rule=rule,
                    audit=audit,
                    calibration_ledger=calibration_ledger,
                    held_out_ledger=held_out_ledger,
                    replayed=True,
                )

            if (
                positive_path.read_bytes() != positive_bytes
                or control_path.read_bytes() != control_bytes
                or calibration_path.read_bytes() != stage_bytes
                or frozen_rule_path.read_bytes() != rule_bytes
            ):
                raise ContradictionPredictionAuditIntegrityError(
                    "Prediction evidence changed before held-out execution."
                )
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
            stage_sha256 = _sha256_bytes(stage_bytes)
            positive_receipt = self.observer.observe(
                held_out_kernel,
                private_held_out.ledger,
                declaration=positive.declaration,
                preregistration_sha256=_sha256_bytes(positive_bytes),
                calibration_stage_sha256=stage_sha256,
                calibration_stage_receipt_ref=stage.stage_receipt.stage_receipt_id,
                held_out_observation=held_out_observation,
            )
            control_receipt = self.observer.observe(
                held_out_kernel,
                private_held_out.ledger,
                declaration=control.declaration,
                preregistration_sha256=_sha256_bytes(control_bytes),
                calibration_stage_sha256=stage_sha256,
                calibration_stage_receipt_ref=stage.stage_receipt.stage_receipt_id,
                held_out_observation=held_out_observation,
            )
            positive_result = ContradictionDownstreamResultEnvelope.build(
                positive_receipt,
                private_held_out.ledger,
            )
            control_result = ContradictionDownstreamResultEnvelope.build(
                control_receipt,
                private_held_out.ledger,
            )
            audit = ContradictionPredictionAuditEnvelope.build(
                rule.rule,
                positive_result,
                control_result,
            )
            save_contradiction_prediction_audit(completed_path, audit)
            if (
                positive_path.read_bytes() != positive_bytes
                or control_path.read_bytes() != control_bytes
                or calibration_path.read_bytes() != stage_bytes
                or frozen_rule_path.read_bytes() != rule_bytes
            ):
                raise ContradictionPredictionAuditIntegrityError(
                    "Upstream prediction evidence changed during publication."
                )
            held_out_ledger = SimulationLedger.from_state(
                private_held_out.ledger.snapshot()
            )
            calibration_runtime.ledger.state = calibration_ledger.snapshot()
            held_out_runtime.ledger.state = held_out_ledger.snapshot()
            published = True
            return ContradictionPredictionAuditRun(
                positive_preregistration_path=positive_path,
                control_preregistration_path=control_path,
                stage_path=calibration_path,
                rule_path=frozen_rule_path,
                audit_path=completed_path,
                positive_preregistration=positive,
                control_preregistration=control,
                stage=stage,
                rule=rule,
                audit=audit,
                calibration_ledger=calibration_ledger,
                held_out_ledger=held_out_ledger,
                replayed=False,
            )
        except ContradictionPredictionAuditIntegrityError:
            raise
        except (
            ContradictionCalibrationStageIntegrityError,
            ContradictionDownstreamOutcomeIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
            StopIteration,
        ) as exc:
            raise ContradictionPredictionAuditIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError("Prediction audit mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Prediction audit mutated its Lens sidecar.")
            if not published:
                if calibration_runtime.ledger.fingerprint() != calibration_before:
                    calibration_runtime.ledger.state = original_calibration
                    raise RuntimeError(
                        "Failed prediction audit published calibration state."
                    )
                if held_out_runtime.ledger.fingerprint() != held_out_before:
                    held_out_runtime.ledger.state = original_held_out
                    raise RuntimeError(
                        "Failed prediction audit published held-out state."
                    )

    @staticmethod
    def _ensure_preregistration(
        path: Path,
        expected: ContradictionDownstreamOutcomeDeclaration,
        held_out_kernel: VerdantKernel,
    ) -> ContradictionDownstreamPreregistrationEnvelope:
        if path.exists():
            envelope = load_contradiction_downstream_preregistration(
                path,
                held_out_kernel=held_out_kernel,
            )
            if envelope.declaration != expected:
                raise ContradictionPredictionAuditIntegrityError(
                    "Existing prediction context is different."
                )
            return envelope
        envelope = ContradictionDownstreamPreregistrationEnvelope.build(expected)
        save_contradiction_downstream_preregistration(
            path,
            envelope,
            held_out_kernel=held_out_kernel,
        )
        return envelope
