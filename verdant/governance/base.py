"""King base protocol for governance layer."""

from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable

from verdant.pipeline.chunk import CognitiveChunk


@runtime_checkable
class King(Protocol):
    """Protocol every governance king must satisfy."""

    name: str

    def oversee(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Apply governance oversight to *chunk*."""
        ...

    def to_state_dict(self) -> Dict[str, Any]:
        """Serialise king state."""
        ...

    def from_state_dict(self, state: Dict[str, Any]) -> None:
        """Restore king state."""
        ...
