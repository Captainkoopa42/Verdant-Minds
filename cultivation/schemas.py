"""Pydantic schemas for cultivation outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ScaffoldContext:
    """Snapshot of scaffold-relevant system state for tutor prompting."""

    total_nodes: int
    emergent_count: int
    basin_count: int
    basin_emergent_distribution: dict[str, int]
    top_concepts: list[str]
    recent_emergents: list[str]
    earlier_share: float
    cycle: int
    active_basin_count: int = 0
    dormant_basin_count: int = 0
    total_emergent_count: int = 0
    t_g: float = 0.0
    latest_emergent_names: list[str] = field(default_factory=list)
    largest_basin_id: str = ""
    largest_basin_emergent_count: int = 0
    recent_bud_events: list[dict[str, Any]] = field(default_factory=list)
    edge_count: int = 0
    node_count: int = 0
    recent_dormancy_events: list[dict[str, Any]] = field(default_factory=list)
    h1_triangle_valid: bool | None = None
    housed_contradiction_index: float | None = None
    violation_rate: float | None = None
    alpha_critical_estimate: float | None = None


class CycleRecord(BaseModel):
    """Per-cycle telemetry record written to JSONL."""

    cycle_index: int
    seed: int
    timestamp: str
    input_text: str
    phase: str
    t_g: float
    entropy: float
    hci: float
    h1_triangle_valid: bool | None = None
    housed_contradiction_index: float | None = None
    violation_rate: float | None = None
    alpha_critical_estimate: float | None = None
    emergent_count: int
    memory_size: int
    basin_count: int = 0
    largest_basin_size: int = 0
    self_cluster_basin_id: str | None = None
    emergent_basins: int = 0
    emergent_count_by_basin: dict[str, int] = Field(default_factory=dict)
    basin_membership_snapshot: dict[str, str] = Field(default_factory=dict)
    basin_proposals_count: int = 0
    basin_conflict_detected: bool = False
    final_action_source: str = "global_default"
    top_proposal_scores: list[dict[str, Any]] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    intervention_applied: bool = False
    intervention_mode: str = "none"
    intervention_cycle: int | None = None
    intervention_target: str | None = None
    removed_nodes_count: int = 0
    removed_ee_edges: int = 0
    scrambled_edge_count: int = 0
    pruned_edges_count: int = 0
    pruned_basin_id: str | None = None
    basin_density_before: float | None = None
    basin_density_after: float | None = None
    bud_events_count: int = 0
    bud_parent_basin_id: str | None = None
    bud_new_basin_id: str | None = None
    bud_new_basin_size: int | None = None
    basin_pressure_values: dict[str, float] = Field(default_factory=dict)
    pressure_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    boundary_emergents_created: int = 0
    boundary_pairs: list[list[str]] = Field(default_factory=list)
    density_regulation_edges_removed: int = 0
    global_edge_ratio_before: float = 0.0
    global_edge_ratio_after: float = 0.0
    cycle_time_seconds: float = 0.0
    graph_nodes: int = 0
    graph_edges: int = 0
    edges_per_node: float = 0.0
    bridge_pairs_evaluated: int = 0
    basin_registry_active: int = 0
    basin_registry_dormant: int = 0
    basin_registry_events: list[dict[str, Any]] = Field(default_factory=list)
    attention_buffer: dict[str, Any] = Field(default_factory=dict)
    tutor_enabled: bool = False
    tutor_backend: str | None = None
    tutor_fallback: bool = False
    tutor_input_length: int = 0
    scaffold_context_emergents: int = 0
    scaffold_context_basins: int = 0
    is_self_reflection: bool = False
    self_reflection_input: str = ""
    phase_name: str | None = None
    phase_cycle: int = 0
    phase_conditions_met: dict[str, Any] = Field(default_factory=dict)
    self_reflect_trigger: str | None = None
    basin_target: str | None = None
    convergence_met: bool = False
    phase_start: bool = False
    phase_end: bool = False


class SessionSummary(BaseModel):
    """End-of-seed run summary."""

    seed: int
    cycles: int
    provider: str
    phase_counts: dict[str, int]
    final_t_g: float
    final_phase: str
    avg_entropy: float
    avg_hci: float
    emergent_count: int
    memory_size: int
    state_path: str
    cycles_path: str
    intervention_mode: str = "none"
    intervention_cycle: int | None = None
    ablation_fraction: float = 0.0
    intervention_target: str | None = None
    pre_intervention_emergent_count: int = 0
    post_intervention_emergent_count: int = 0
    post_intervention_new_emergents: int = 0
    pre_intervention_basin_count: int = 0
    post_intervention_basin_count: int = 0
