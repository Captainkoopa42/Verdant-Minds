"""Canonical JSON persistence for Verdant runtime state."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict


def _fsync_directory(path: Path) -> None:
    """Best-effort directory fsync so atomic renames survive power loss."""
    if os.name == "nt":
        return
    try:
        dir_fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def save_state(path: str | Path, state: Dict[str, Any]) -> None:
    """Atomically serialize *state* to JSON at *path*.

    The write is staged in the target directory, flushed with ``fsync``, and
    then promoted with ``os.replace``. This prevents readers from observing a
    partially written checkpoint if the process dies mid-write.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            json.dump(state, tmp, separators=(",", ":"), default=str)
            tmp.flush()
            os.fsync(tmp.fileno())

        os.replace(tmp_path, target)
        _fsync_directory(target.parent)
    except Exception:
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def load_state(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def export_bundle(path: str | Path, *, memory_graph: Dict[str, Any], basins: Dict[str, Any], ecwf_state: Dict[str, Any], telemetry: Dict[str, Any]) -> None:
    bundle = {
        "version": 4,
        "memory_graph": memory_graph,
        "basins": basins,
        "ecwf": ecwf_state,
        "telemetry": telemetry,
    }
    save_state(path, bundle)


# Backwards compatibility wrappers.
def save_snapshot(path: str | Path, memory_web: Any, bridge_state: Dict[str, Any], ecwf_state: Dict[str, Any], metrics: Dict[str, Any], kings_state: Dict[str, Any] | None = None, extra: Dict[str, Any] | None = None) -> None:
    state: Dict[str, Any] = {
        "version": 2,
        "memory_web": memory_web.to_state_dict(),
        "bridge": bridge_state,
        "ecwf": ecwf_state,
        "metrics": metrics,
        "kings": kings_state or {},
        "extra": extra or {},
    }
    save_state(path, state)


def load_snapshot(path: str | Path) -> Dict[str, Any]:
    return load_state(path)


def compute_diff(old_web: Dict[str, Any], new_web: Dict[str, Any]) -> Dict[str, Any]:
    old_nodes = set(old_web.get("memory_store", {}).keys())
    new_nodes = set(new_web.get("memory_store", {}).keys())
    added = sorted(new_nodes - old_nodes)
    removed = sorted(old_nodes - new_nodes)
    changed = sorted(
        label
        for label in old_nodes & new_nodes
        if abs(float(old_web["memory_store"][label].get("stability", 0)) - float(new_web["memory_store"][label].get("stability", 0))) > 1e-6
    )
    return {"added": added, "removed": removed, "changed": changed}


def emergent_registry(memory_web: Any) -> Dict[str, Any]:
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
