"""Compatibility adapter for Verdant persisted state snapshots."""

from __future__ import annotations

import json
from datetime import datetime
from functools import cached_property
from pathlib import Path
from typing import Any


JsonDict = dict[str, Any]


def parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).timestamp()
        except Exception:
            continue
    try:
        return float(text)
    except Exception:
        return None


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_connection(item: Any) -> tuple[str, float] | None:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        try:
            return str(item[0]), float(item[1])
        except (TypeError, ValueError):
            return None
    if isinstance(item, dict):
        target = item.get("target") or item.get("dst") or item.get("to") or item.get("name") or item.get("id")
        if target is None:
            return None
        weight = item.get("weight", item.get("w", item.get("strength", 1.0)))
        try:
            return str(target), float(weight)
        except (TypeError, ValueError):
            return None
    return None


class VerdantState:
    """Unified reader for current and historical state.json formats."""

    def __init__(self, path: Path, raw: JsonDict, format_version: str) -> None:
        self.path = Path(path)
        self._raw = raw
        self.format_version = format_version

    @classmethod
    def load(cls, path: str | Path) -> "VerdantState":
        state_path = Path(path)
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"State file {state_path} must deserialize to a JSON object")

        memory_web = raw.get("memory_web")
        if isinstance(memory_web, dict) and isinstance(memory_web.get("memory_store"), dict):
            return cls(state_path, raw, "v3")
        if isinstance(memory_web, dict) and ("nodes" in memory_web or "concepts" in memory_web):
            return cls(state_path, raw, "v2")
        if "nodes" in raw or "concepts" in raw:
            return cls(state_path, raw, "v2")
        raise ValueError("Unknown state format")

    @property
    def raw(self) -> JsonDict:
        return self._raw

    @property
    def _memory_web(self) -> JsonDict:
        memory_web = self._raw.get("memory_web")
        return memory_web if isinstance(memory_web, dict) else {}

    @cached_property
    def nodes(self) -> list[JsonDict]:
        if self.format_version == "v3":
            store = self._memory_web.get("memory_store") or {}
            nodes: list[JsonDict] = []
            for name, payload in store.items():
                payload = payload if isinstance(payload, dict) else {}
                metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
                connections = [conn for conn in (_normalize_connection(item) for item in payload.get("connections", []) or []) if conn is not None]
                creation_time = parse_ts(
                    first_present(
                        payload.get("first_seen"),
                        metadata.get("creation_time"),
                        metadata.get("created_at"),
                        payload.get("created_at"),
                    )
                )
                nodes.append(
                    {
                        "name": str(name),
                        "creation_time": creation_time,
                        "timestamp": creation_time,
                        "access_count": int(payload.get("access_count", payload.get("access", 0)) or 0),
                        "connection_count": len(connections),
                        "is_emergent": ("Emergent" in str(name)) or metadata.get("origin") == "wave_emergence",
                        "stability": float(payload.get("stability", 0.0) or 0.0),
                        "metadata": metadata,
                        "connections": connections,
                        "raw": payload,
                    }
                )
            return nodes

        source_nodes = self._memory_web.get("nodes") or self._memory_web.get("concepts") or self._raw.get("nodes") or self._raw.get("concepts") or []
        nodes = []
        for raw_node in source_nodes:
            if not isinstance(raw_node, dict):
                continue
            name = raw_node.get("name") or raw_node.get("id") or raw_node.get("key")
            if name is None:
                continue
            metadata = raw_node.get("metadata") if isinstance(raw_node.get("metadata"), dict) else {}
            connections = [conn for conn in (_normalize_connection(item) for item in raw_node.get("connections", []) or []) if conn is not None]
            creation_time = parse_ts(
                first_present(
                    raw_node.get("creation_time"),
                    raw_node.get("timestamp"),
                    raw_node.get("created_at"),
                    raw_node.get("time"),
                    raw_node.get("first_seen"),
                    metadata.get("creation_time"),
                    metadata.get("created_at"),
                )
            )
            connection_count = raw_node.get("connection_count")
            if not isinstance(connection_count, int):
                connection_count = len(connections)
            nodes.append(
                {
                    "name": str(name),
                    "creation_time": creation_time,
                    "timestamp": creation_time,
                    "access_count": int(raw_node.get("access_count", raw_node.get("access", 0)) or 0),
                    "connection_count": int(connection_count),
                    "is_emergent": "Emergent" in str(name),
                    "stability": float(first_present(raw_node.get("stability"), metadata.get("stability"), 0.0) or 0.0),
                    "metadata": metadata,
                    "connections": connections,
                    "raw": raw_node,
                }
            )
        return nodes

    @cached_property
    def _node_map(self) -> dict[str, JsonDict]:
        return {str(node["name"]): node for node in self.nodes}

    @cached_property
    def edges(self) -> list[JsonDict]:
        if self.format_version == "v3":
            edge_weights: dict[tuple[str, str], list[float]] = {}
            known_nodes = set(self._node_map)
            for source, node in self._node_map.items():
                for target, weight in node.get("connections", []):
                    if source == target or target not in known_nodes:
                        continue
                    a, b = sorted((source, target))
                    edge_weights.setdefault((a, b), []).append(float(weight))
            return [
                {"source": source, "target": target, "weight": float(sum(weights) / len(weights))}
                for (source, target), weights in sorted(edge_weights.items())
            ]

        raw_edges = self._memory_web.get("edges") or self._raw.get("edges") or self._raw.get("relations") or self._raw.get("links") or []
        edges: list[JsonDict] = []
        for edge in raw_edges:
            if isinstance(edge, (list, tuple)) and len(edge) >= 3:
                try:
                    edges.append({"source": str(edge[0]), "target": str(edge[1]), "weight": float(edge[2])})
                except (TypeError, ValueError):
                    continue
                continue
            if not isinstance(edge, dict):
                continue
            source = edge.get("source") or edge.get("src") or edge.get("from")
            target = edge.get("target") or edge.get("dst") or edge.get("to")
            if source is None or target is None:
                continue
            try:
                weight = float(edge.get("weight", edge.get("w", 1.0)))
            except (TypeError, ValueError):
                weight = 1.0
            edges.append({"source": str(source), "target": str(target), "weight": weight})
        return edges

    @property
    def emergent_nodes(self) -> list[JsonDict]:
        return [node for node in self.nodes if bool(node.get("is_emergent"))]

    @property
    def seeded_nodes(self) -> list[JsonDict]:
        return [node for node in self.nodes if not bool(node.get("is_emergent"))]

    @property
    def emergent_edges(self) -> list[JsonDict]:
        emergent_names = {str(node["name"]) for node in self.emergent_nodes}
        return [edge for edge in self.edges if edge["source"] in emergent_names and edge["target"] in emergent_names]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def emergent_count(self) -> int:
        return len(self.emergent_nodes)

    def get_node(self, name: str) -> JsonDict | None:
        return self._node_map.get(str(name))

    @property
    def basins(self) -> JsonDict | list[Any]:
        extra = self._raw.get("extra") if isinstance(self._raw.get("extra"), dict) else {}
        if "last_basins" in extra:
            return extra.get("last_basins") or []
        basins_path = self.path.with_name("basins.json")
        if basins_path.exists():
            payload = json.loads(basins_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload.get("basins", payload)
            return payload
        return []

    @property
    def basin_registry(self) -> JsonDict:
        extra = self._raw.get("extra") if isinstance(self._raw.get("extra"), dict) else {}
        registry = extra.get("basin_registry")
        return registry if isinstance(registry, dict) else {}
