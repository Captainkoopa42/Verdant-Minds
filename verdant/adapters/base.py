from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time
from typing import Any, Dict


@dataclass(slots=True)
class InputEvent:
    type: str
    payload: Dict[str, Any]
    source: str = "adapter"
    timestamp: float = field(default_factory=time.time)


class Adapter(ABC):
    def __init__(self) -> None:
        self._buffer: list[InputEvent] = []

    def push(self, event: InputEvent) -> None:
        self._buffer.append(event)

    @abstractmethod
    def poll(self) -> list[InputEvent]:
        """Return new input events."""
        raise NotImplementedError
