"""SDK-oriented client abstraction for Verdant-Memory."""

from __future__ import annotations

from typing import Any

from verdant_memory.api.memory import Memory
from verdant_memory.schema import MemorySnapshot, ObserveResult, RetrieveResult, UpdateResult


class MemoryClient:
    """Thin client wrapper suitable for direct Python SDK usage."""

    def __init__(self, memory: Memory | None = None) -> None:
        self._memory = memory or Memory()

    def observe(self, text: str, metadata: dict[str, Any] | None = None) -> ObserveResult:
        return self._memory.observe(text, metadata=metadata)

    def retrieve(self, query: str, *, top_k: int = 8) -> RetrieveResult:
        return self._memory.retrieve(query, top_k=top_k)

    def update(self, delta: dict[str, Any]) -> UpdateResult:
        return self._memory.update(delta)

    def snapshot(self) -> MemorySnapshot:
        return self._memory.snapshot()

    def load(self, snapshot: MemorySnapshot | dict[str, Any]) -> None:
        self._memory.load(snapshot)
