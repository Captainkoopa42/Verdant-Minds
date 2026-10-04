"""Calibration-frozen dimension/outcome criteria for Contradiction trials.

This module is an explicitly invoked extension of the v0.38 independent
Contradiction Lens controls.  A declaration fixes one typed Lens-output
dimension and all bounded outcome alternatives before either split runs.  A
criterion deriver then accepts only the completed calibration observation; it
cannot receive a held-out observation or simulation ledger.  The resulting
content-addressed criterion is constructed before the held-out probe is called
and is applied unchanged afterward.

The criterion observes only an internal, simulation-local association between
the cardinalities selected by ``SELECT_ACTIVATED_REFS`` and the already
bounded functional-routing disposition.  A matched held-out result may record
an internal trace-local match, an explicit out-of-profile valid null, or a
mismatch.  It does not establish Resolution-level dimensional separation,
predictive discrimination, real-world source independence, external outcome,
truth, or authority to resolve or commit anything.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_functional_context import (
    CONTRADICTION_FUNCTIONAL_ALTERNATIVES,
    ContradictionFunctionalDisposition,
)
from .contradiction_hypotheses import (
    ContradictionHypothesisBundle,
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_lens_control import (
    CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
    CONTRADICTION_LENS_MISSING_REQUIREMENTS,
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlledRun,
    ContradictionLensControlIntegrityError,
)
from .contradiction_resolution_evidence import (
    ContradictionResolutionRequirement,
)
from .contradiction_trial_controls import (
    ContradictionLensHeldOutReplicationReceipt,
    ContradictionLensTrialContext,
    ContradictionLensTrialIntegrityError,
    ContradictionLensTrialObservation,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSidecarEnvelope,
    ContradictionLensTrialSplit,
    _validate_sidecar_pairing,
)
from .counterfactual import (
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError, LensOpcode


CONTRADICTION_DIMENSION_DECLARATION_VERSION = (
    "contradiction_dimension_declaration_v0.39"
)
CONTRADICTION_DIMENSION_CRITERION_VERSION = (
    "contradiction_dimension_criterion_v0.39"
)
CONTRADICTION_DIMENSION_EVALUATION_VERSION = (
    "contradiction_dimension_evaluation_v0.39"
)
CONTRADICTION_DIMENSION_SIDECAR_FORMAT = (
    "verdant-contradiction-dimension-sidecar-v1"
)
_MAX_DIMENSION_SIDECAR_BYTES = 128 * 1024 * 1024


class ContradictionDimensionCriterionIntegrityError(RuntimeError):
    """Raised when a dimension criterion loses frozen split lineage."""


class ContradictionLensOutputDimension(str, Enum):
    """The one typed Lens-output dimension admitted by v0.39."""

    ACTIVATED_REFERENCE_CARDINALITY_PROFILE = (
        "activated_reference_cardinality_profile"
    )


class ContradictionProjectionCardinalityProfile(str, Enum):
    """ID-independent two-route cardinality classes."""

    SINGLETON_PER_ROUTE = "singleton_per_route"
    EQUAL_MULTI_REFERENCE_ROUTES = "equal_multi_reference_routes"
    ASYMMETRIC_ROUTE_CARDINALITY = "asymmetric_route_cardinality"


CONTRADICTION_PROJECTION_CARDINALITY_PROFILES = tuple(
    ContradictionProjectionCardinalityProfile
)


class ContradictionDimensionEvaluationDisposition(str, Enum):
    """Bounded held-out results for one frozen calibration criterion."""

    TRACE_LOCAL_OUTCOME_MATCH = "trace_local_outcome_match"
    VALID_NULL_OUT_OF_CALIBRATION_PROFILE = (
        "valid_null_out_of_calibration_profile"
    )
    TRACE_LOCAL_OUTCOME_MISMATCH = "trace_local_outcome_mismatch"


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


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _projection_counts(
    observation: ContradictionLensTrialObservation,
) -> tuple[int, int]:
    projections = observation.lens_observation.route_projections
    return tuple(len(item.projected_claim_refs) for item in projections)


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


class ContradictionDimensionCriterionDeclaration(FrozenRecord):
    """Method and alternatives fixed before calibration or held-out execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    declaration_id: str
    declaration_version: str = CONTRADICTION_DIMENSION_DECLARATION_VERSION
    pair_context_ref: str
    calibration_context_ref: str
    held_out_context_ref: str
    matched_control_signature: str
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    selected_operator: LensOpcode = LensOpcode.SELECT_ACTIVATED_REFS
    selected_dimension: ContradictionLensOutputDimension = (
        ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
    )
    admissible_profiles: tuple[ContradictionProjectionCardinalityProfile, ...] = (
        CONTRADICTION_PROJECTION_CARDINALITY_PROFILES
    )
    admissible_outcomes: tuple[ContradictionFunctionalDisposition, ...] = (
        CONTRADICTION_FUNCTIONAL_ALTERNATIVES
    )
    explicit_valid_null_required: bool = True
    criterion_must_precede_held_out_execution: bool = True
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        pair_context: ContradictionLensTrialPairContext,
    ) -> "ContradictionDimensionCriterionDeclaration":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        values = {
            "declaration_version": CONTRADICTION_DIMENSION_DECLARATION_VERSION,
            "pair_context_ref": pair.pair_id,
            "calibration_context_ref": pair.calibration.context_id,
            "held_out_context_ref": pair.held_out.context_id,
            "matched_control_signature": pair.matched_control_signature,
            "lens_fingerprint": pair.lens_fingerprint,
            "definition_ref": pair.definition_ref,
            "binding_ref": pair.binding_ref,
            "selected_operator": LensOpcode.SELECT_ACTIVATED_REFS,
            "selected_dimension": (
                ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            ),
            "admissible_profiles": CONTRADICTION_PROJECTION_CARDINALITY_PROFILES,
            "admissible_outcomes": CONTRADICTION_FUNCTIONAL_ALTERNATIVES,
            "explicit_valid_null_required": True,
            "criterion_must_precede_held_out_execution": True,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["declaration_id"] = stable_id(
            "contradiction_dimension_criterion_declaration",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_declaration(self) -> "ContradictionDimensionCriterionDeclaration":
        if self.declaration_version != CONTRADICTION_DIMENSION_DECLARATION_VERSION:
            raise ValueError("Unknown Contradiction dimension declaration version.")
        if self.calibration_context_ref == self.held_out_context_ref:
            raise ValueError("Dimension declaration reused one split context.")
        if (
            self.selected_operator != LensOpcode.SELECT_ACTIVATED_REFS
            or self.selected_dimension
            != ContradictionLensOutputDimension.ACTIVATED_REFERENCE_CARDINALITY_PROFILE
            or self.admissible_profiles
            != CONTRADICTION_PROJECTION_CARDINALITY_PROFILES
            or self.admissible_outcomes != CONTRADICTION_FUNCTIONAL_ALTERNATIVES
        ):
            raise ValueError("Contradiction dimension declaration changed its grammar.")
        if not _is_sha256(self.lens_fingerprint):
            raise ValueError("Dimension declaration Lens fingerprint is invalid.")
        if (
            not self.explicit_valid_null_required
            or not self.criterion_must_precede_held_out_execution
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Dimension declaration crossed its claim boundary.")
        payload = self.model_dump(mode="json", exclude={"declaration_id"})
        if self.declaration_id != stable_id(
            "contradiction_dimension_criterion_declaration", payload
        ):
            raise ValueError("Dimension declaration checksum mismatch.")
        return self


class ContradictionCalibrationDimensionCriterion(FrozenRecord):
    """A frozen criterion derived solely through the calibration-only API."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str
    criterion_version: str = CONTRADICTION_DIMENSION_CRITERION_VERSION
    declaration: ContradictionDimensionCriterionDeclaration
    calibration_observation: ContradictionLensTrialObservation
    calibration_observation_ref: str
    calibration_context_ref: str
    target_held_out_context_ref: str
    lens_fingerprint: str
    definition_ref: str
    binding_ref: str
    selected_operator: LensOpcode
    selected_dimension: ContradictionLensOutputDimension
    calibration_projection_refs: tuple[str, str]
    calibration_baseline_trace_ref: str
    calibration_treatment_trace_ref: str
    calibration_cardinalities: tuple[int, int]
    calibration_profile: ContradictionProjectionCardinalityProfile
    expected_functional_outcome: ContradictionFunctionalDisposition
    admissible_profiles: tuple[ContradictionProjectionCardinalityProfile, ...]
    admissible_outcomes: tuple[ContradictionFunctionalDisposition, ...]
    derived_from_actual_calibration_trace: bool = True
    calibration_only_derivation: bool = True
    held_out_trace_consulted: bool = False
    frozen_before_held_out_execution: bool = True
    simulated_only: bool = True
    predictive_discrimination_observed: bool = False
    dimensional_separation_observed: bool = False
    external_outcome_observed: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        declaration: ContradictionDimensionCriterionDeclaration,
        calibration_observation: ContradictionLensTrialObservation,
    ) -> "ContradictionCalibrationDimensionCriterion":
        declaration = ContradictionDimensionCriterionDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        observation = ContradictionLensTrialObservation.model_validate(
            calibration_observation.model_dump(mode="json")
        )
        context = observation.context
        functional = observation.lens_observation.functional_observation
        matched = functional.provenance_observation.matched_observation
        counts = _projection_counts(observation)
        values = {
            "criterion_version": CONTRADICTION_DIMENSION_CRITERION_VERSION,
            "declaration": declaration,
            "calibration_observation": observation,
            "calibration_observation_ref": observation.observation_id,
            "calibration_context_ref": context.context_id,
            "target_held_out_context_ref": declaration.held_out_context_ref,
            "lens_fingerprint": context.lens_fingerprint,
            "definition_ref": context.definition_ref,
            "binding_ref": context.binding_ref,
            "selected_operator": declaration.selected_operator,
            "selected_dimension": declaration.selected_dimension,
            "calibration_projection_refs": tuple(
                item.projection_id
                for item in observation.lens_observation.route_projections
            ),
            "calibration_baseline_trace_ref": matched.baseline.trace_id,
            "calibration_treatment_trace_ref": matched.treatment.trace_id,
            "calibration_cardinalities": counts,
            "calibration_profile": _cardinality_profile(counts),
            "expected_functional_outcome": functional.disposition,
            "admissible_profiles": declaration.admissible_profiles,
            "admissible_outcomes": declaration.admissible_outcomes,
            "derived_from_actual_calibration_trace": True,
            "calibration_only_derivation": True,
            "held_out_trace_consulted": False,
            "frozen_before_held_out_execution": True,
            "simulated_only": True,
            "predictive_discrimination_observed": False,
            "dimensional_separation_observed": False,
            "external_outcome_observed": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["criterion_id"] = stable_id(
            "contradiction_calibration_dimension_criterion",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_criterion(self) -> "ContradictionCalibrationDimensionCriterion":
        if self.criterion_version != CONTRADICTION_DIMENSION_CRITERION_VERSION:
            raise ValueError("Unknown Contradiction dimension criterion version.")
        declaration = self.declaration
        observation = self.calibration_observation
        context = observation.context
        functional = observation.lens_observation.functional_observation
        matched = functional.provenance_observation.matched_observation
        counts = _projection_counts(observation)
        expected = {
            "calibration_observation_ref": observation.observation_id,
            "calibration_context_ref": context.context_id,
            "target_held_out_context_ref": declaration.held_out_context_ref,
            "lens_fingerprint": context.lens_fingerprint,
            "definition_ref": context.definition_ref,
            "binding_ref": context.binding_ref,
            "selected_operator": declaration.selected_operator,
            "selected_dimension": declaration.selected_dimension,
            "calibration_projection_refs": tuple(
                item.projection_id
                for item in observation.lens_observation.route_projections
            ),
            "calibration_baseline_trace_ref": matched.baseline.trace_id,
            "calibration_treatment_trace_ref": matched.treatment.trace_id,
            "calibration_cardinalities": counts,
            "calibration_profile": _cardinality_profile(counts),
            "expected_functional_outcome": functional.disposition,
            "admissible_profiles": declaration.admissible_profiles,
            "admissible_outcomes": declaration.admissible_outcomes,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Calibration dimension criterion altered trace evidence.")
        if (
            context.split != ContradictionLensTrialSplit.CALIBRATION
            or context.context_id != declaration.calibration_context_ref
            or context.lens_fingerprint != declaration.lens_fingerprint
            or context.definition_ref != declaration.definition_ref
            or context.binding_ref != declaration.binding_ref
        ):
            raise ValueError(
                "Dimension criterion did not use its declared calibration."
            )
        if any(count < 1 for count in self.calibration_cardinalities):
            raise ValueError("Dimension criterion requires nonempty Lens projections.")
        if (
            not self.derived_from_actual_calibration_trace
            or not self.calibration_only_derivation
            or self.held_out_trace_consulted
            or not self.frozen_before_held_out_execution
            or not self.simulated_only
            or self.predictive_discrimination_observed
            or self.dimensional_separation_observed
            or self.external_outcome_observed
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Dimension criterion crossed its evidence boundary.")
        payload = self.model_dump(mode="json", exclude={"criterion_id"})
        if self.criterion_id != stable_id(
            "contradiction_calibration_dimension_criterion", payload
        ):
            raise ValueError("Calibration dimension criterion checksum mismatch.")
        return self


class ContradictionCalibrationCriterionDeriver:
    """Derive a criterion through an API that accepts no held-out result."""

    def derive(
        self,
        declaration: ContradictionDimensionCriterionDeclaration,
        calibration_observation: ContradictionLensTrialObservation,
    ) -> ContradictionCalibrationDimensionCriterion:
        try:
            return ContradictionCalibrationDimensionCriterion.build(
                declaration,
                calibration_observation,
            )
        except ContradictionDimensionCriterionIntegrityError:
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise ContradictionDimensionCriterionIntegrityError(str(exc)) from exc


class ContradictionDimensionEvaluationReceipt(FrozenRecord):
    """Held-out application of one frozen calibration-only criterion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    evaluation_version: str = CONTRADICTION_DIMENSION_EVALUATION_VERSION
    criterion: ContradictionCalibrationDimensionCriterion
    held_out_observation: ContradictionLensTrialObservation
    held_out_observation_ref: str
    held_out_context_ref: str
    held_out_projection_refs: tuple[str, str]
    held_out_baseline_trace_ref: str
    held_out_treatment_trace_ref: str
    held_out_cardinalities: tuple[int, int]
    held_out_profile: ContradictionProjectionCardinalityProfile
    observed_functional_outcome: ContradictionFunctionalDisposition
    disposition: ContradictionDimensionEvaluationDisposition
    grounded_requirements: tuple[ContradictionResolutionRequirement, ...]
    missing_requirements: tuple[ContradictionResolutionRequirement, ...]
    criterion_applied_unchanged: bool = True
    matched_control_verified: bool = True
    evidence_preserved: bool = True
    trace_local_dimension_outcome_match_observed: bool
    explicit_valid_null_observed: bool
    trace_local_outcome_mismatch_observed: bool
    simulated_only: bool = True
    dimensional_separation_observed: bool = False
    predictive_discrimination_observed: bool = False
    independent_held_out_replication_observed: bool = False
    source_independence_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        criterion: ContradictionCalibrationDimensionCriterion,
        held_out_observation: ContradictionLensTrialObservation,
    ) -> "ContradictionDimensionEvaluationReceipt":
        criterion = ContradictionCalibrationDimensionCriterion.model_validate(
            criterion.model_dump(mode="json")
        )
        observation = ContradictionLensTrialObservation.model_validate(
            held_out_observation.model_dump(mode="json")
        )
        functional = observation.lens_observation.functional_observation
        matched = functional.provenance_observation.matched_observation
        counts = _projection_counts(observation)
        profile = _cardinality_profile(counts)
        valid_null = (
            ContradictionDimensionEvaluationDisposition.
            VALID_NULL_OUT_OF_CALIBRATION_PROFILE
        )
        if profile != criterion.calibration_profile:
            disposition = valid_null
        elif functional.disposition == criterion.expected_functional_outcome:
            disposition = (
                ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH
            )
        else:
            disposition = (
                ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MISMATCH
            )
        values = {
            "evaluation_version": CONTRADICTION_DIMENSION_EVALUATION_VERSION,
            "criterion": criterion,
            "held_out_observation": observation,
            "held_out_observation_ref": observation.observation_id,
            "held_out_context_ref": observation.context.context_id,
            "held_out_projection_refs": tuple(
                item.projection_id
                for item in observation.lens_observation.route_projections
            ),
            "held_out_baseline_trace_ref": matched.baseline.trace_id,
            "held_out_treatment_trace_ref": matched.treatment.trace_id,
            "held_out_cardinalities": counts,
            "held_out_profile": profile,
            "observed_functional_outcome": functional.disposition,
            "disposition": disposition,
            "grounded_requirements": CONTRADICTION_LENS_GROUNDED_REQUIREMENTS,
            "missing_requirements": CONTRADICTION_LENS_MISSING_REQUIREMENTS,
            "criterion_applied_unchanged": True,
            "matched_control_verified": True,
            "evidence_preserved": True,
            "trace_local_dimension_outcome_match_observed": disposition
            == ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH,
            "explicit_valid_null_observed": disposition
            == valid_null,
            "trace_local_outcome_mismatch_observed": disposition
            == ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MISMATCH,
            "simulated_only": True,
            "dimensional_separation_observed": False,
            "predictive_discrimination_observed": False,
            "independent_held_out_replication_observed": False,
            "source_independence_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "contradiction_dimension_evaluation", _record_payload(values)
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionDimensionEvaluationReceipt":
        if self.evaluation_version != CONTRADICTION_DIMENSION_EVALUATION_VERSION:
            raise ValueError("Unknown Contradiction dimension evaluation version.")
        criterion = self.criterion
        observation = self.held_out_observation
        context = observation.context
        functional = observation.lens_observation.functional_observation
        matched = functional.provenance_observation.matched_observation
        counts = _projection_counts(observation)
        profile = _cardinality_profile(counts)
        valid_null = (
            ContradictionDimensionEvaluationDisposition.
            VALID_NULL_OUT_OF_CALIBRATION_PROFILE
        )
        if profile != criterion.calibration_profile:
            expected_disposition = valid_null
        elif functional.disposition == criterion.expected_functional_outcome:
            expected_disposition = (
                ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH
            )
        else:
            expected_disposition = (
                ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MISMATCH
            )
        expected = {
            "held_out_observation_ref": observation.observation_id,
            "held_out_context_ref": context.context_id,
            "held_out_projection_refs": tuple(
                item.projection_id
                for item in observation.lens_observation.route_projections
            ),
            "held_out_baseline_trace_ref": matched.baseline.trace_id,
            "held_out_treatment_trace_ref": matched.treatment.trace_id,
            "held_out_cardinalities": counts,
            "held_out_profile": profile,
            "observed_functional_outcome": functional.disposition,
            "disposition": expected_disposition,
            "trace_local_dimension_outcome_match_observed": expected_disposition
            == ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MATCH,
            "explicit_valid_null_observed": expected_disposition
            == valid_null,
            "trace_local_outcome_mismatch_observed": expected_disposition
            == ContradictionDimensionEvaluationDisposition.TRACE_LOCAL_OUTCOME_MISMATCH,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Held-out dimension evaluation was altered.")
        declaration = criterion.declaration
        if (
            context.split != ContradictionLensTrialSplit.HELD_OUT
            or context.context_id != criterion.target_held_out_context_ref
            or context.context_id != declaration.held_out_context_ref
            or context.lens_fingerprint != criterion.lens_fingerprint
            or context.definition_ref != criterion.definition_ref
            or context.binding_ref != criterion.binding_ref
        ):
            raise ValueError("Dimension evaluation crossed held-out or Lens lineage.")
        if (
            self.grounded_requirements
            != CONTRADICTION_LENS_GROUNDED_REQUIREMENTS
            or self.missing_requirements != CONTRADICTION_LENS_MISSING_REQUIREMENTS
        ):
            raise ValueError("Dimension evaluation hid a Resolution gap.")
        if set(self.grounded_requirements).intersection(self.missing_requirements):
            raise ValueError("Dimension evaluation requirements overlap.")
        if set((*self.grounded_requirements, *self.missing_requirements)) != set(
            ContradictionResolutionRequirement
        ):
            raise ValueError("Dimension evaluation coverage is not exhaustive.")
        if (
            not self.criterion_applied_unchanged
            or not self.matched_control_verified
            or not self.evidence_preserved
            or not self.simulated_only
            or self.dimensional_separation_observed
            or self.predictive_discrimination_observed
            or self.independent_held_out_replication_observed
            or self.source_independence_observed
            or self.external_outcome_observed
            or self.resolution_trial_ready
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Dimension evaluation crossed its claim boundary.")
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != stable_id(
            "contradiction_dimension_evaluation", payload
        ):
            raise ValueError("Dimension evaluation checksum mismatch.")
        return self


class ContradictionDimensionCriterionObserver:
    """Apply a frozen criterion to one held-out observation unchanged."""

    def observe(
        self,
        criterion: ContradictionCalibrationDimensionCriterion,
        held_out_observation: ContradictionLensTrialObservation,
    ) -> ContradictionDimensionEvaluationReceipt:
        try:
            return ContradictionDimensionEvaluationReceipt.build(
                criterion,
                held_out_observation,
            )
        except ContradictionDimensionCriterionIntegrityError:
            raise
        except (ValueError, TypeError, KeyError) as exc:
            raise ContradictionDimensionCriterionIntegrityError(str(exc)) from exc


@dataclass(frozen=True)
class ContradictionDimensionTrialRun:
    pair_context: ContradictionLensTrialPairContext
    declaration: ContradictionDimensionCriterionDeclaration
    calibration_run: ContradictionLensControlledRun
    criterion: ContradictionCalibrationDimensionCriterion
    held_out_run: ContradictionLensControlledRun
    replication_receipt: ContradictionLensHeldOutReplicationReceipt
    evaluation: ContradictionDimensionEvaluationReceipt

    @property
    def replayed(self) -> bool:
        return self.calibration_run.replayed and self.held_out_run.replayed


class ContradictionDimensionTrialRunner:
    """Freeze the calibration criterion before staging the held-out run."""

    def __init__(
        self,
        *,
        controlled_runner: ContradictionLensControlledProbeRunner | None = None,
        criterion_deriver: ContradictionCalibrationCriterionDeriver | None = None,
        criterion_observer: ContradictionDimensionCriterionObserver | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.controlled_runner = (
            controlled_runner
            or ContradictionLensControlledProbeRunner(
                hypothesis_protocol=self.hypothesis_protocol
            )
        )
        self.criterion_deriver = (
            criterion_deriver or ContradictionCalibrationCriterionDeriver()
        )
        self.criterion_observer = (
            criterion_observer or ContradictionDimensionCriterionObserver()
        )

    def run(
        self,
        calibration_kernel: VerdantKernel,
        calibration_runtime: CounterfactualRuntime,
        held_out_kernel: VerdantKernel,
        held_out_runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
        *,
        calibration_bundle: ContradictionHypothesisBundle,
        held_out_bundle: ContradictionHypothesisBundle,
        pair_context: ContradictionLensTrialPairContext,
        criterion_declaration: ContradictionDimensionCriterionDeclaration,
    ) -> ContradictionDimensionTrialRun:
        if calibration_kernel is held_out_kernel:
            raise ContradictionDimensionCriterionIntegrityError(
                "Dimension trial requires separate canonical kernels."
            )
        if (
            calibration_runtime is held_out_runtime
            or calibration_runtime.ledger is held_out_runtime.ledger
        ):
            raise ContradictionDimensionCriterionIntegrityError(
                "Dimension trial requires separate simulation ledgers."
            )
        canonical_before = (
            calibration_kernel.fingerprint(),
            held_out_kernel.fingerprint(),
        )
        simulation_before = (
            calibration_runtime.ledger.fingerprint(),
            held_out_runtime.ledger.fingerprint(),
        )
        lens_before = lenses.fingerprint()
        original_calibration = calibration_runtime.ledger.snapshot()
        original_held_out = held_out_runtime.ledger.snapshot()
        published = False
        try:
            pair = ContradictionLensTrialPairContext.model_validate(
                pair_context.model_dump(mode="json")
            )
            declaration = ContradictionDimensionCriterionDeclaration.model_validate(
                criterion_declaration.model_dump(mode="json")
            )
            expected_calibration = ContradictionLensTrialContext.build(
                calibration_kernel,
                calibration_bundle,
                lenses,
                split=ContradictionLensTrialSplit.CALIBRATION,
                source_event_key=(
                    pair.calibration.controlled_context.source_event_key
                ),
                hypothesis_protocol=self.hypothesis_protocol,
            )
            expected_held_out = ContradictionLensTrialContext.build(
                held_out_kernel,
                held_out_bundle,
                lenses,
                split=ContradictionLensTrialSplit.HELD_OUT,
                source_event_key=pair.held_out.controlled_context.source_event_key,
                hypothesis_protocol=self.hypothesis_protocol,
            )
            expected_pair = ContradictionLensTrialPairContext.build(
                calibration=expected_calibration,
                held_out=expected_held_out,
            )
            if pair != expected_pair:
                raise ContradictionDimensionCriterionIntegrityError(
                    "Dimension trial pair controls are stale or substituted."
                )
            if declaration != ContradictionDimensionCriterionDeclaration.build(pair):
                raise ContradictionDimensionCriterionIntegrityError(
                    "Dimension criterion declaration is stale or substituted."
                )
            calibration_working = CounterfactualRuntime(
                SimulationLedger.from_state(original_calibration)
            )
            held_out_working = CounterfactualRuntime(
                SimulationLedger.from_state(original_held_out)
            )
            calibration_run = self.controlled_runner.run(
                calibration_kernel,
                calibration_working,
                lenses,
                bundle=calibration_bundle,
                controlled_context=pair.calibration.controlled_context,
                source_event_key=(
                    pair.calibration.controlled_context.source_event_key
                ),
            )
            calibration_observation = ContradictionLensTrialObservation.build(
                context=pair.calibration,
                run=calibration_run,
            )
            criterion = self.criterion_deriver.derive(
                declaration,
                calibration_observation,
            )
            # The held-out runner is deliberately called only after the frozen,
            # content-addressed criterion exists.
            held_out_run = self.controlled_runner.run(
                held_out_kernel,
                held_out_working,
                lenses,
                bundle=held_out_bundle,
                controlled_context=pair.held_out.controlled_context,
                source_event_key=pair.held_out.controlled_context.source_event_key,
            )
            held_out_observation = ContradictionLensTrialObservation.build(
                context=pair.held_out,
                run=held_out_run,
            )
            replication = ContradictionLensHeldOutReplicationReceipt.build(
                pair_context=pair,
                calibration_observation=calibration_observation,
                held_out_observation=held_out_observation,
            )
            evaluation = self.criterion_observer.observe(
                criterion,
                held_out_observation,
            )
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
                or lenses.fingerprint() != lens_before
            ):
                raise ContradictionDimensionCriterionIntegrityError(
                    "Dimension trial crossed a protected ledger."
                )
            calibration_state = calibration_working.ledger.snapshot()
            held_out_state = held_out_working.ledger.snapshot()
            try:
                calibration_runtime.ledger.state = calibration_state
                held_out_runtime.ledger.state = held_out_state
            except Exception:
                calibration_runtime.ledger.state = original_calibration
                held_out_runtime.ledger.state = original_held_out
                raise
            published = True
            return ContradictionDimensionTrialRun(
                pair_context=pair,
                declaration=declaration,
                calibration_run=calibration_run,
                criterion=criterion,
                held_out_run=held_out_run,
                replication_receipt=replication,
                evaluation=evaluation,
            )
        except ContradictionDimensionCriterionIntegrityError:
            raise
        except (
            ContradictionLensTrialIntegrityError,
            ContradictionHypothesisIntegrityError,
            ContradictionLensControlIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionDimensionCriterionIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError("Dimension trial mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Dimension trial mutated its Lens sidecar.")
            if not published and (
                calibration_runtime.ledger.fingerprint() != simulation_before[0]
                or held_out_runtime.ledger.fingerprint() != simulation_before[1]
            ):
                raise RuntimeError("Failed dimension trial published partial state.")


class ContradictionDimensionSidecarEnvelope(BaseModel):
    """Separately durable completed v0.39 evidence, outside VDK and VOB."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: str = CONTRADICTION_DIMENSION_SIDECAR_FORMAT
    pair_context_sha256: str
    declaration_sha256: str
    criterion_sha256: str
    replication_receipt_sha256: str
    evaluation_sha256: str
    calibration_simulation_fingerprint: str
    held_out_simulation_fingerprint: str
    pair_context: ContradictionLensTrialPairContext
    declaration: ContradictionDimensionCriterionDeclaration
    criterion: ContradictionCalibrationDimensionCriterion
    replication_receipt: ContradictionLensHeldOutReplicationReceipt
    evaluation: ContradictionDimensionEvaluationReceipt

    @classmethod
    def build(
        cls,
        trial_run: ContradictionDimensionTrialRun,
        *,
        calibration_ledger: SimulationLedger,
        held_out_ledger: SimulationLedger,
    ) -> "ContradictionDimensionSidecarEnvelope":
        pair = ContradictionLensTrialPairContext.model_validate(
            trial_run.pair_context.model_dump(mode="json")
        )
        declaration = ContradictionDimensionCriterionDeclaration.model_validate(
            trial_run.declaration.model_dump(mode="json")
        )
        criterion = ContradictionCalibrationDimensionCriterion.model_validate(
            trial_run.criterion.model_dump(mode="json")
        )
        replication = ContradictionLensHeldOutReplicationReceipt.model_validate(
            trial_run.replication_receipt.model_dump(mode="json")
        )
        evaluation = ContradictionDimensionEvaluationReceipt.model_validate(
            trial_run.evaluation.model_dump(mode="json")
        )
        return cls(
            pair_context_sha256=_digest(
                canonical_json_bytes(pair.model_dump(mode="json"))
            ),
            declaration_sha256=_digest(
                canonical_json_bytes(declaration.model_dump(mode="json"))
            ),
            criterion_sha256=_digest(
                canonical_json_bytes(criterion.model_dump(mode="json"))
            ),
            replication_receipt_sha256=_digest(
                canonical_json_bytes(replication.model_dump(mode="json"))
            ),
            evaluation_sha256=_digest(
                canonical_json_bytes(evaluation.model_dump(mode="json"))
            ),
            calibration_simulation_fingerprint=calibration_ledger.fingerprint(),
            held_out_simulation_fingerprint=held_out_ledger.fingerprint(),
            pair_context=pair,
            declaration=declaration,
            criterion=criterion,
            replication_receipt=replication,
            evaluation=evaluation,
        )

    @model_validator(mode="after")
    def validate_envelope(self) -> "ContradictionDimensionSidecarEnvelope":
        if self.format_version != CONTRADICTION_DIMENSION_SIDECAR_FORMAT:
            raise ValueError("Unsupported Contradiction dimension sidecar format.")
        records = (
            (self.pair_context_sha256, self.pair_context),
            (self.declaration_sha256, self.declaration),
            (self.criterion_sha256, self.criterion),
            (self.replication_receipt_sha256, self.replication_receipt),
            (self.evaluation_sha256, self.evaluation),
        )
        if any(
            digest != _digest(canonical_json_bytes(record.model_dump(mode="json")))
            for digest, record in records
        ):
            raise ValueError("Contradiction dimension sidecar checksum mismatch.")
        if any(
            not _is_sha256(item)
            for item in (
                self.calibration_simulation_fingerprint,
                self.held_out_simulation_fingerprint,
            )
        ):
            raise ValueError("Dimension sidecar ledger fingerprint is invalid.")
        if (
            self.declaration
            != ContradictionDimensionCriterionDeclaration.build(self.pair_context)
            or self.criterion.declaration != self.declaration
            or self.replication_receipt.pair_context != self.pair_context
            or self.evaluation.criterion != self.criterion
            or self.criterion.calibration_observation
            != self.replication_receipt.calibration_observation
            or self.evaluation.held_out_observation
            != self.replication_receipt.held_out_observation
        ):
            raise ValueError("Dimension sidecar lost complete split lineage.")
        return self


def _validate_dimension_sidecar_pairing(
    envelope: ContradictionDimensionSidecarEnvelope,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    calibration_ledger: SimulationLedger,
    held_out_ledger: SimulationLedger,
) -> None:
    if (
        envelope.calibration_simulation_fingerprint
        != calibration_ledger.fingerprint()
        or envelope.held_out_simulation_fingerprint
        != held_out_ledger.fingerprint()
    ):
        raise ContradictionDimensionCriterionIntegrityError(
            "Dimension sidecar is paired with different simulation state."
        )
    base = ContradictionLensTrialSidecarEnvelope.build(
        envelope.pair_context,
        receipt=envelope.replication_receipt,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    _validate_sidecar_pairing(
        base,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    expected_criterion = ContradictionCalibrationDimensionCriterion.build(
        envelope.declaration,
        envelope.replication_receipt.calibration_observation,
    )
    expected_evaluation = ContradictionDimensionEvaluationReceipt.build(
        expected_criterion,
        envelope.replication_receipt.held_out_observation,
    )
    if (
        envelope.criterion != expected_criterion
        or envelope.evaluation != expected_evaluation
    ):
        raise ContradictionDimensionCriterionIntegrityError(
            "Dimension sidecar criterion or evaluation is not reproducible."
        )


def contradiction_dimension_sidecar_bytes(
    trial_run: ContradictionDimensionTrialRun,
    *,
    calibration_ledger: SimulationLedger,
    held_out_ledger: SimulationLedger,
) -> bytes:
    envelope = ContradictionDimensionSidecarEnvelope.build(
        trial_run,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    return canonical_json_bytes(envelope.model_dump(mode="json"))


def save_contradiction_dimension_sidecar(
    path: str | Path,
    trial_run: ContradictionDimensionTrialRun,
    *,
    calibration_ledger: SimulationLedger,
    held_out_ledger: SimulationLedger,
) -> None:
    """Atomically save completed criterion evidence outside VDK and VOB."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = contradiction_dimension_sidecar_bytes(
        trial_run,
        calibration_ledger=calibration_ledger,
        held_out_ledger=held_out_ledger,
    )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        temporary = None
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def load_contradiction_dimension_sidecar(
    path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    calibration_ledger: SimulationLedger,
    held_out_ledger: SimulationLedger,
) -> ContradictionDimensionSidecarEnvelope:
    """Load and close criterion evidence over canonical/simulation/Lens state."""

    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_DIMENSION_SIDECAR_BYTES:
            raise ContradictionDimensionCriterionIntegrityError(
                "Contradiction dimension sidecar exceeds its size limit."
            )
        envelope = ContradictionDimensionSidecarEnvelope.model_validate_json(data)
        _validate_dimension_sidecar_pairing(
            envelope,
            calibration_kernel=calibration_kernel,
            held_out_kernel=held_out_kernel,
            lenses=lenses,
            calibration_ledger=calibration_ledger,
            held_out_ledger=held_out_ledger,
        )
        return envelope
    except ContradictionDimensionCriterionIntegrityError:
        raise
    except (
        ContradictionLensTrialIntegrityError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise ContradictionDimensionCriterionIntegrityError(str(exc)) from exc
