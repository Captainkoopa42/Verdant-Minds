"""Base contracts for Verdant output adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from verdant.output.events import OutputEvent


class OutputAdapter(ABC):
    """Abstract output adapter contract."""

    @abstractmethod
    def emit(self, event: OutputEvent) -> None:
        """Emit a single output event to a concrete destination."""
        raise NotImplementedError
