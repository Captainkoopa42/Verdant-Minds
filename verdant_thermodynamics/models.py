from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenThermodynamicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ThermodynamicPhase(str, Enum):
    RIGID = "Rigid"
    FLEXIBLE = "Flexible"
    CHAOTIC = "Chaotic"


class AccessPressureMeasurementStatus(str, Enum):
    """Whether a pre-admission access-pressure measurement is interpretable."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class AccessPressureCandidate(FrozenThermodynamicModel):
    """One available earned structure overlapping the incoming cue."""

    structure_id: str
    member_count: int = Field(ge=1)
    trigger_count: int = Field(ge=1)
    trigger_fraction: float = Field(gt=0.0, le=1.0)
    trigger_concept_ids: tuple[str, ...] = Field(min_length=1)
    weak_context: bool

    @model_validator(mode="after")
    def validate_candidate(self) -> "AccessPressureCandidate":
        if tuple(sorted(set(self.trigger_concept_ids))) != self.trigger_concept_ids:
            raise ValueError("Access-pressure trigger concept IDs must be sorted and unique.")
        if self.trigger_count != len(self.trigger_concept_ids):
            raise ValueError("Access-pressure trigger count does not match its concept IDs.")
        if self.trigger_count > self.member_count:
            raise ValueError("Access-pressure trigger count exceeds structure membership.")
        expected = self.trigger_count / self.member_count
        if abs(self.trigger_fraction - expected) > 1e-12:
            raise ValueError("Access-pressure trigger fraction is inconsistent.")
        if self.weak_context != (self.trigger_fraction < 0.5):
            raise ValueError("Access-pressure weak-context classification is inconsistent.")
        return self


class AccessPressureObservation(FrozenThermodynamicModel):
    """Typed, causally read-only observation made before current-cue admission.

    An incomplete record is explicit: it means at least one cue concept did not
    exist in the inspected checkpoint.  It must never be read as zero pressure.
    """

    schema_id: str = "verdant.access_pressure_observation.v2"
    observer_revision: str = "earned_structure_overlap_v2"
    measurement_status: AccessPressureMeasurementStatus
    behavioral_authority_enabled: bool = False
    semantic_truth_judgement: bool = False
    source_event_key: str = ""
    canonical_state_fingerprint: str
    cycle_before_experience: int = Field(ge=0)
    cue_labels: tuple[str, ...] = ()
    cue_concept_ids: tuple[str, ...] = ()
    unknown_cue_labels: tuple[str, ...] = ()
    available_overlapping_structures: int = Field(default=0, ge=0)
    weak_context_candidate_count: int = Field(default=0, ge=0)
    supported_context_candidate_count: int = Field(default=0, ge=0)
    max_weak_trigger_fraction: float | None = Field(default=None, gt=0.0, lt=0.5)
    candidate_details: tuple[AccessPressureCandidate, ...] = ()

    @model_validator(mode="after")
    def validate_observation(self) -> "AccessPressureObservation":
        for values, label in (
            (self.cue_labels, "cue labels"),
            (self.cue_concept_ids, "cue concept IDs"),
            (self.unknown_cue_labels, "unknown cue labels"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Access-pressure {label} must be sorted and unique.")
        if not self.canonical_state_fingerprint:
            raise ValueError("Access-pressure observation requires a canonical fingerprint.")
        if self.behavioral_authority_enabled:
            raise ValueError("Access-pressure telemetry has no behavioral authority.")
        if self.semantic_truth_judgement:
            raise ValueError("Access-pressure telemetry cannot judge semantic truth.")
        if self.measurement_status == AccessPressureMeasurementStatus.INCOMPLETE:
            if not self.unknown_cue_labels:
                raise ValueError("Incomplete access pressure requires unknown cue labels.")
            if self.candidate_details or any(
                (
                    self.available_overlapping_structures,
                    self.weak_context_candidate_count,
                    self.supported_context_candidate_count,
                )
            ):
                raise ValueError("Incomplete access pressure cannot publish partial candidate counts.")
            if self.max_weak_trigger_fraction is not None:
                raise ValueError("Incomplete access pressure cannot publish a weak trigger maximum.")
            return self
        if self.unknown_cue_labels:
            raise ValueError("Complete access pressure cannot contain unknown cue labels.")
        if self.available_overlapping_structures != len(self.candidate_details):
            raise ValueError("Access-pressure candidate count is inconsistent.")
        weak = tuple(item for item in self.candidate_details if item.weak_context)
        supported = tuple(item for item in self.candidate_details if not item.weak_context)
        if self.weak_context_candidate_count != len(weak):
            raise ValueError("Access-pressure weak candidate count is inconsistent.")
        if self.supported_context_candidate_count != len(supported):
            raise ValueError("Access-pressure supported candidate count is inconsistent.")
        expected_max = max((item.trigger_fraction for item in weak), default=None)
        if expected_max != self.max_weak_trigger_fraction:
            raise ValueError("Access-pressure weak trigger maximum is inconsistent.")
        ids = tuple(item.structure_id for item in self.candidate_details)
        if tuple(sorted(set(ids))) != ids:
            raise ValueError("Access-pressure candidates must be sorted and unique.")
        return self


class FieldEntropyMeasurement(FrozenThermodynamicModel):
    adapter_revision: str = "field_power_shannon_v1"
    state_dim: int = Field(ge=1)
    total_power: float = Field(ge=0.0)
    h_sys: float = Field(ge=0.0, le=1.0)


class InputComplexityMeasurement(FrozenThermodynamicModel):
    adapter_revision: str
    modality: str
    feature_count: int = Field(ge=1)
    nonzero_feature_count: int = Field(ge=0)
    feature_density: float = Field(ge=0.0, le=1.0)
    feature_entropy: float = Field(ge=0.0, le=1.0)
    token_count: int | None = Field(default=None, ge=0)
    token_complexity: float | None = Field(default=None, ge=0.0, le=1.0)
    c_input: float = Field(ge=0.0, le=1.0)


class MemoryComplexityMeasurement(FrozenThermodynamicModel):
    adapter_revision: str = "active_workspace_concepts_v4_compat_1"
    candidate_scope_count: int = Field(ge=0)
    active_workspace_items: int = Field(ge=0)
    active_workspace_concepts: int = Field(ge=0)
    workspace_item_occupancy: float = Field(ge=0.0, le=1.0)
    allocated_resource: float = Field(ge=0.0)
    resource_load: float = Field(ge=0.0, le=1.0)
    c_memory: float = Field(ge=0.0, le=1.0)


class EnvironmentMeasurement(FrozenThermodynamicModel):
    adapter_revision: str = "workspace_uncertainty_v1"
    candidate_count: int = Field(ge=0)
    mean_prediction_error: float = Field(ge=0.0, le=1.0)
    mean_novelty: float = Field(ge=0.0, le=1.0)
    mean_contradiction_pressure: float = Field(ge=0.0, le=1.0)
    h_env: float = Field(ge=0.0, le=1.0)


class ThermodynamicState(FrozenThermodynamicModel):
    """Measurement-only V5 projection of the recovered V4 phase model.

    ``t_g`` and ``t_cog`` are implementation-defined dimensionless telemetry.
    They are not temperatures in kelvin and carry no physical-thermodynamic
    claim by themselves.
    """

    schema_id: str = "verdant.thermodynamic_state.v1"
    formula_revision: str = "tg_v4_compat_1"
    cycle: int = Field(ge=0)
    event_key: str
    modality: str
    h_sys: float = Field(ge=0.0, le=1.0)
    c_input: float = Field(ge=0.0, le=1.0)
    c_memory: float = Field(ge=0.0, le=1.0)
    h_env: float = Field(ge=0.0, le=1.0)
    computational_complexity: float = Field(ge=0.0, le=1.0)
    base_term: float
    entropy_feedback: float
    t_g: float = Field(ge=0.1, le=0.9)
    phase: ThermodynamicPhase
    t_cog: float = Field(ge=0.0, le=2.0)
    previous_phase: ThermodynamicPhase | None = None
    phase_transition: bool = False
    field: FieldEntropyMeasurement
    input: InputComplexityMeasurement
    memory: MemoryComplexityMeasurement
    environment: EnvironmentMeasurement
    metadata: dict[str, Any] = Field(default_factory=dict)


class PhasePolicyDelta(FrozenThermodynamicModel):
    """A proposed nonsemantic policy delta; applying it is experiment-only.

    The original six fields remain for compatibility. Soft-homeostasis v1 adds
    explicit access-control knobs so the experiment can favor current evidence
    and reduce historical recruitment without deleting memory.
    """

    controller_revision: str = "phase_policy_homeostasis_4"
    phase: ThermodynamicPhase
    workspace_resource_multiplier: float = Field(gt=0.0)
    workspace_persistence_delta: int
    plasticity_learning_multiplier: float = Field(gt=0.0)
    plasticity_decay_multiplier: float = Field(gt=0.0)
    resonance_top_k_delta: int
    resonance_commit_delta: int
    current_evidence_resource_multiplier: float = Field(default=1.0, gt=0.0)
    historical_resource_multiplier: float = Field(default=1.0, gt=0.0)
    resonance_recall_threshold_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    resonance_local_support_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    association_recall_threshold_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    structure_trigger_members_delta: int = 0
    structure_trigger_fraction_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    behavioral_authority_enabled: bool = False
