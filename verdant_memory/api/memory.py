"""Public Verdant-Memory API."""

from __future__ import annotations

from typing import Any

from verdant.system import VerdantConfig

from verdant_memory.core.engine import MemoryEngine
from verdant_memory.schema import MemorySnapshot, ObserveResult, RetrieveResult, UpdateResult


class Memory:
    """Developer-facing persistent memory substrate API.

    This API intentionally hides internal research mechanics (ECWF, basins,
    governance, cultivation internals) behind five stable primitives:
    observe, retrieve, update, snapshot, load.
    """

    def __init__(self, *, config: VerdantConfig | None = None) -> None:
        self._engine = MemoryEngine(config=config)

    def observe(self, text: str, metadata: dict[str, Any] | None = None) -> ObserveResult:
        """Add an observation into memory and advance internal state."""
        payload = self._engine.observe(text=text, metadata=metadata)
        return ObserveResult.model_validate(payload)

    def retrieve(self, query: str, *, top_k: int = 8) -> RetrieveResult:
        """Retrieve structured memory context relevant to *query*."""
        payload = self._engine.retrieve(query=query, top_k=top_k)
        return RetrieveResult.model_validate(payload)

    def update(self, delta: dict[str, Any]) -> UpdateResult:
        """Apply structured memory mutations.

        Supported keys:
        - concepts: [{label, stability?, metadata?}]
        - edges: [{source, target, weight?}]
        - reinforce: [{label, amount?}]
        """
        payload = self._engine.apply_delta(delta)
        return UpdateResult.model_validate(payload)

    def snapshot(self) -> MemorySnapshot:
        """Return a full versioned snapshot."""
        return self._engine.snapshot()

    def load(self, snapshot: MemorySnapshot | dict[str, Any]) -> None:
        """Restore full state from a snapshot payload."""
        if isinstance(snapshot, dict):
            snapshot = MemorySnapshot.from_legacy(snapshot)
        self._engine.load(snapshot)
