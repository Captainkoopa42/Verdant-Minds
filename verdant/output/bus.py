"""Broadcast bus for Verdant output events."""

from __future__ import annotations

from typing import Iterable

from verdant.output.base import OutputAdapter
from verdant.output.events import OutputEvent


class OutputBus:
    """Broadcasts runtime output events to registered adapters."""

    def __init__(self) -> None:
        self._adapters: list[OutputAdapter] = []
        self.buffer: list[OutputEvent] = []

    @property
    def adapters(self) -> tuple[OutputAdapter, ...]:
        return tuple(self._adapters)

    def register(self, adapter: OutputAdapter) -> None:
        self._adapters.append(adapter)

    def emit_all(self, events: Iterable[OutputEvent]) -> None:
        batch = list(events)
        if not batch:
            return
        self.buffer.extend(batch)
        for event in batch:
            for adapter in self._adapters:
                adapter.emit(event)
