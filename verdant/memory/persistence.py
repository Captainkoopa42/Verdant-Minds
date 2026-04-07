"""Chunked state persistence — snapshots, diffs, and emergent registry.

Provides helpers for saving and loading the full Verdant v2 system state
as chunked JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from verdant.memory.graph import MemoryWeb


def save_snapshot(
    path: str | Path,
    memory_web: MemoryWeb,
    bridge_state: Dict[str, Any],
    ecwf_state: Dict[str, Any],
    metrics: Dict[str, Any],
    kings_state: Dict[str, Any] | None = None,
    extra: Dict[str, Any] | None = None,
) -> None:
    """Write a full system snapshot to *path* as JSON.

    Args:
        path: Destination file path.
        memory_web: The memory web instance.
        bridge_state: Serialised bridge state.
        ecwf_state: Serialised ECWF state.
        metrics: System metrics.
        kings_state: Optional Three-Kings governance state.
        extra: Optional additional data.
    """
    state: Dict[str, Any] = {
        "version": 2,
        "memory_web": memory_web.to_state_dict(),
        "bridge": bridge_state,
        "ecwf": ecwf_state,
        "metrics": metrics,
    }
    if kings_state is not None:
        state["kings"] = kings_state
    if extra is not None:
        state["extra"] = extra

    Path(path).write_text(json.dumps(state, indent=2, default=str))


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    """Load a snapshot from *path* and return the raw dict.

    The caller is responsible for reconstructing live objects from the
    returned dictionaries.

    Args:
        path: Source file path.

    Returns:
        Parsed snapshot dict.
    """
    return json.loads(Path(path).read_text())


def compute_diff(
    old_web: Dict[str, Any],
    new_web: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute a lightweight diff between two memory-web state dicts.

    Returns:
        Dict with ``added``, ``removed``, and ``changed`` concept lists.
    """
    old_nodes = set(old_web.get("memory_store", {}).keys())
    new_nodes = set(new_web.get("memory_store", {}).keys())

    added = sorted(new_nodes - old_nodes)
    removed = sorted(old_nodes - new_nodes)
    changed: list[str] = []
    for label in old_nodes & new_nodes:
        old_s = old_web["memory_store"][label].get("stability", 0)
        new_s = new_web["memory_store"][label].get("stability", 0)
        if abs(old_s - new_s) > 1e-6:
            changed.append(label)

    return {"added": added, "removed": removed, "changed": sorted(changed)}


def emergent_registry(memory_web: MemoryWeb) -> Dict[str, Any]:
    """Build a registry of emergent concepts and their metadata.

    Args:
        memory_web: The memory web instance.

    Returns:
        Dict mapping emergent labels to their metadata.
    """
    registry: Dict[str, Any] = {}
    for label in memory_web.get_emergent_nodes():
        data = memory_web.get_concept(label)
        if data:
            registry[label] = {
                "stability": data["stability"],
                "metadata": data["metadata"],
                "neighbors": memory_web.get_neighbors(label),
            }
    return registry
