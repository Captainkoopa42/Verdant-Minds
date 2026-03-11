"""Pydantic schemas for cultivation outputs."""

from __future__ import annotations

from dataclasses import dataclass
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
    emergent_count: int
    memory_size: int
    basin_count: int = 0
    largest_basin_size: int = 0
    self_cluster_basin_id: str | None = None
    emergent_basins: int = 0
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
    tutor_enabled: bool = False
    tutor_backend: str | None = None
    tutor_fallback: bool = False
    tutor_input_length: int = 0
    scaffold_context_emergents: int = 0
    scaffold_context_basins: int = 0


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
