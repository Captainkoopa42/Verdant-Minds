from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class InputEvent:
    def __init__(self, type: str, payload: Dict[str, Any]):
        self.type = type
        self.payload = payload


class Adapter(ABC):
    @abstractmethod
    def poll(self) -> list[InputEvent]:
        """Return new input events."""
        raise NotImplementedError
