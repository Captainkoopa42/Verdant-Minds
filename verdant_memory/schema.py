"""Public schema models for Verdant-Memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ConceptRecord(BaseModel):
    """Normalized concept node representation exposed by Verdant-Memory."""

    label: str
    stability: float = 0.0
    access_count: int = 0
    last_accessed: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EdgeRecord(BaseModel):
    """Normalized edge record exposed by Verdant-Memory."""

    source: str
    target: str
    weight: float = 0.5


class MemoryGraphState(BaseModel):
    """Portable graph-level memory state."""

    concepts: list[ConceptRecord] = Field(default_factory=list)
    edges: list[EdgeRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySnapshot(BaseModel):
    """Versioned external snapshot contract for Verdant-Memory."""

    schema_version: str = "verdant-memory.v1"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    graph: MemoryGraphState
    internal_state: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_legacy(cls, payload: dict[str, Any]) -> "MemorySnapshot":
        """Convert compatible legacy payloads into the v1 contract.

        This keeps migration hooks in one place as schema versions evolve.
        """
        if payload.get("schema_version") == "verdant-memory.v1":
            return cls.model_validate(payload)

        # legacy fallback: allow direct internal state dicts that include memory_web.
        state = payload.get("internal_state", payload)
        memory = state.get("memory_web", {}) if isinstance(state, dict) else {}
        store = memory.get("memory_store", {}) if isinstance(memory, dict) else {}
        edges = memory.get("edges", []) if isinstance(memory, dict) else []

        concepts = [
            ConceptRecord(
                label=str(label),
                stability=float(data.get("stability", 0.0)),
                access_count=int(data.get("access_count", 0)),
                last_accessed=float(data.get("last_accessed", 0.0)),
                metadata=dict(data.get("metadata", {}) or {}),
            )
            for label, data in store.items()
            if isinstance(data, dict)
        ]
        graph_edges = [
            EdgeRecord(
                source=str(edge.get("source", "")),
                target=str(edge.get("target", "")),
                weight=float(edge.get("weight", 0.5)),
            )
            for edge in edges
            if isinstance(edge, dict)
        ]
        return cls(
            graph=MemoryGraphState(concepts=concepts, edges=graph_edges, metadata={"migrated": True}),
            internal_state=state if isinstance(state, dict) else {},
        )


class ObserveResult(BaseModel):
    selected_action: str
    generated_response: str
    memory_size: int
    cycle: int


class RetrieveResult(BaseModel):
    query: str
    primary_concept: str | None = None
    related: list[dict[str, Any]] = Field(default_factory=list)
    memory_context: dict[str, Any] = Field(default_factory=dict)


class UpdateResult(BaseModel):
    concepts_added: int = 0
    edges_added: int = 0
    concepts_reinforced: int = 0
