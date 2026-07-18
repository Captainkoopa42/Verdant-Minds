"""Runtime state container for basin-local processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BasinState:
    """Lightweight persisted runtime state for a basin."""

    basin_id: str
    member_nodes: List[str]
    local_metrics: Dict[str, Any] = field(default_factory=dict)
    last_local_coherence: Optional[float] = None
    last_local_phase: Optional[str] = None
    last_proposal: Optional[Dict[str, Any]] = None

