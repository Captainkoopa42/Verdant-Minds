"""Pydantic schemas for cultivation outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
    boundary_emergents_created: int = 0
    boundary_pairs: list[list[str]] = Field(default_factory=list)


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
