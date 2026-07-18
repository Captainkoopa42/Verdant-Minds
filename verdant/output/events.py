"""Structured events emitted by Verdant output adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class OutputEvent:
    """A normalized output event produced by the Verdant runtime."""

    type: str
    payload: str | dict[str, Any]
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
