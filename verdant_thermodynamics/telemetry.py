from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DevelopmentTelemetryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_id: str = "verdant.development_telemetry.v1"
    run_id: str
    seed: int
    kernel_id: str
    cycle: int = Field(ge=0)
    event_key: str
    modality: str
    starting_fingerprint: str
    ending_fingerprint: str
    replayed: bool
    evidence_ids: tuple[str, ...]
    concept_ids: tuple[str, ...]
    contradiction_ids: tuple[str, ...]
    resonance_candidate_count: int = Field(ge=0)
    committed_resonance_count: int = Field(ge=0)
    workspace_candidate_count: int = Field(ge=0)
    workspace_admitted_count: int = Field(ge=0)
    workspace_allocated_resource: float = Field(ge=0.0)
    plasticity_updates_applied: int = Field(ge=0)
    structure_candidates_observed: int = Field(ge=0)
    promoted_p_count: int = Field(ge=0)
    promoted_q_count: int = Field(ge=0)
    thermodynamics: dict[str, Any] | None = None
    kernel_metrics: dict[str, Any]
    branch_commit: str | None = None


class AppendOnlyTelemetryWriter:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: DevelopmentTelemetryRecord) -> None:
        payload = json.dumps(record.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.write("\n")


def record_from_development(
    *,
    kernel,
    result,
    run_id: str,
    branch_commit: str | None = None,
) -> DevelopmentTelemetryRecord:
    experience = result.experience
    evidence_ids = tuple(
        sorted(
            {
                experience.observation_evidence_id,
                experience.translation_evidence_id,
                *experience.additional_evidence_ids,
            }
        )
    )
    resonance_candidates = (
        len(result.resonance_report.candidates) if result.resonance_report is not None else 0
    )
    committed_resonance = (
        len(result.resonance_event.attention_candidate_ids)
        if result.resonance_event is not None
        else 0
    )
    workspace_candidate_count = (
        len(result.workspace.report.assessments) if result.workspace is not None else 0
    )
    workspace_admitted = (
        len(result.workspace.report.admitted_candidate_ids) if result.workspace is not None else 0
    )
    workspace_resource = (
        float(result.workspace.report.total_allocated_resource) if result.workspace is not None else 0.0
    )
    plasticity_applied = 0
    if result.plasticity is not None:
        report = result.plasticity.report
        plasticity_applied = len(report.proposed_associations)
    structures_observed = (
        len(result.structures.report.observed_candidate_ids) if result.structures is not None else 0
    )
    return DevelopmentTelemetryRecord(
        run_id=run_id,
        seed=kernel.state.seed,
        kernel_id=kernel.state.identity.kernel_id,
        cycle=kernel.state.cycle,
        event_key=experience.event_key,
        modality=result.modality,
        starting_fingerprint=result.starting_fingerprint,
        ending_fingerprint=result.ending_fingerprint,
        replayed=result.replayed,
        evidence_ids=evidence_ids,
        concept_ids=experience.concept_ids,
        contradiction_ids=experience.contradiction_ids,
        resonance_candidate_count=resonance_candidates,
        committed_resonance_count=committed_resonance,
        workspace_candidate_count=workspace_candidate_count,
        workspace_admitted_count=workspace_admitted,
        workspace_allocated_resource=workspace_resource,
        plasticity_updates_applied=plasticity_applied,
        structure_candidates_observed=structures_observed,
        promoted_p_count=len(kernel.state.structures),
        promoted_q_count=len(kernel.state.layered_structures),
        thermodynamics=(
            result.thermodynamics.model_dump(mode="json")
            if getattr(result, "thermodynamics", None) is not None
            else None
        ),
        kernel_metrics=kernel.metrics(),
        branch_commit=branch_commit,
    )
