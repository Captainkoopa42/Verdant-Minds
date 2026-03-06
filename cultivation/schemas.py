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
