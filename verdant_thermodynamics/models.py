from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FrozenThermodynamicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ThermodynamicPhase(str, Enum):
    RIGID = "Rigid"
    FLEXIBLE = "Flexible"
    CHAOTIC = "Chaotic"


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
    """A proposed nonsemantic policy delta; applying it is experiment-only."""

    controller_revision: str = "phase_policy_1"
    phase: ThermodynamicPhase
    workspace_resource_multiplier: float = Field(gt=0.0)
    workspace_persistence_delta: int
    plasticity_learning_multiplier: float = Field(gt=0.0)
    plasticity_decay_multiplier: float = Field(gt=0.0)
    resonance_top_k_delta: int
    resonance_commit_delta: int
    behavioral_authority_enabled: bool = False
