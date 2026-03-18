"""Extract emergent concepts and inferred parents from a Verdant state snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


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


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _normalize_connection(item: Any) -> tuple[str, float] | None:
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return str(item[0]), float(item[1])
    if isinstance(item, dict):
        target = item.get("target") or item.get("dst") or item.get("to") or item.get("name") or item.get("id")
        if target is None:
            return None
        weight = item.get("weight", item.get("w", item.get("strength", 1.0)))
        return str(target), float(weight)
    return None


def _load_snapshot_graph(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    memory_web = data.get("memory_web") or {}
    store = memory_web.get("memory_store") or {}
    edge_list = memory_web.get("edges") or []

    nodes: dict[str, dict[str, Any]] = {}
    for node_id, payload in store.items():
        payload = payload if isinstance(payload, dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        connections = [_normalize_connection(item) for item in payload.get("connections", []) or []]
        nodes[str(node_id)] = {
            "id": str(node_id),
            "timestamp": parse_ts(_first_present(metadata.get("created_at"), metadata.get("creation_time"), payload.get("first_seen"))),
            "first_seen": parse_ts(payload.get("first_seen")),
            "access_count": int(payload.get("access_count", payload.get("access", 0)) or 0),
            "connections": [c for c in connections if c is not None],
            "metadata": metadata,
            "raw": payload,
        }

    edges: list[dict[str, Any]] = []
    for edge in edge_list:
        if isinstance(edge, (list, tuple)) and len(edge) >= 3:
            edges.append({"source": str(edge[0]), "target": str(edge[1]), "weight": float(edge[2])})
            continue
        if isinstance(edge, dict):
            source = edge.get("source") or edge.get("src") or edge.get("from")
            target = edge.get("target") or edge.get("dst") or edge.get("to")
            if source is None or target is None:
                continue
            edges.append(
                {
                    "source": str(source),
                    "target": str(target),
                    "weight": float(edge.get("weight", edge.get("w", 1.0))),
                }
            )
    return nodes, edges


def _load_generic_graph(data: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    raw_nodes = data.get("nodes") or data.get("concepts") or []
    raw_edges = data.get("edges") or data.get("relations") or data.get("links") or []
    nodes: dict[str, dict[str, Any]] = {}
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            continue
        node_id = raw.get("id") or raw.get("name") or raw.get("key")
        if node_id is None:
            continue
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        connections = [_normalize_connection(item) for item in raw.get("connections", []) or []]
        nodes[str(node_id)] = {
            "id": str(node_id),
            "timestamp": parse_ts(_first_present(raw.get("timestamp"), raw.get("created_at"), raw.get("time"), metadata.get("creation_time"))),
            "first_seen": parse_ts(raw.get("first_seen")),
            "access_count": int(raw.get("access_count", raw.get("access", 0)) or 0),
            "connections": [c for c in connections if c is not None],
            "metadata": metadata,
            "raw": raw,
        }

    edges: list[dict[str, Any]] = []
    for edge in raw_edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source") or edge.get("src") or edge.get("from")
        target = edge.get("target") or edge.get("dst") or edge.get("to")
        if source is None or target is None:
            continue
        edges.append({"source": str(source), "target": str(target), "weight": float(edge.get("weight", edge.get("w", 1.0)))})
    return nodes, edges


def load_graph(state_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"State file {state_path} must deserialize to a JSON object")
    if "memory_web" in data:
        nodes, edges = _load_snapshot_graph(data)
    else:
        nodes, edges = _load_generic_graph(data)
    return nodes, edges, data


def _build_connection_index(nodes: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, list[tuple[str, float]]]:
    index = {node_id: list(node.get("connections", [])) for node_id, node in nodes.items()}
    for edge in edges:
        source = str(edge["source"])
        target = str(edge["target"])
        weight = float(edge.get("weight", 1.0))
        index.setdefault(source, []).append((target, weight))
        index.setdefault(target, []).append((source, weight))
    deduped: dict[str, list[tuple[str, float]]] = {}
    for node_id, neighbors in index.items():
        merged: dict[str, float] = {}
        for neighbor, weight in neighbors:
            merged[neighbor] = max(float(weight), merged.get(neighbor, float("-inf")))
        deduped[node_id] = sorted(merged.items(), key=lambda item: (-item[1], item[0]))
    return deduped


def _basin_lookup_from_records(records: list[Any]) -> dict[str, str]:
    basin_by_node: dict[str, str] = {}
    for basin in records:
        if not isinstance(basin, dict):
            continue
        basin_id = basin.get("basin_id")
        nodes = basin.get("nodes", [])
        if not isinstance(basin_id, str) or not isinstance(nodes, list):
            continue
        for node in nodes:
            basin_by_node[str(node)] = basin_id
    return basin_by_node


def load_basins(basins_path: Path | None, raw_state: dict[str, Any] | None = None) -> dict[str, str]:
    if basins_path is not None and basins_path.exists():
        payload = json.loads(basins_path.read_text(encoding="utf-8"))
        records = payload.get("basins", []) if isinstance(payload, dict) else []
        return _basin_lookup_from_records(records if isinstance(records, list) else [])
    extra = (raw_state or {}).get("extra", {}) if isinstance(raw_state, dict) else {}
    records = extra.get("last_basins", []) if isinstance(extra, dict) else []
    if isinstance(records, list):
        return _basin_lookup_from_records(records)
    return {}


def discover_basins_path(state_path: Path, explicit_basins: Path | None = None) -> Path | None:
    if explicit_basins is not None:
        return explicit_basins
    candidates = [state_path.with_name("basins.json"), state_path.parent / "analysis" / "basins.json"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def infer_parent_concepts(node_id: str, node: dict[str, Any], connection_index: dict[str, list[tuple[str, float]]]) -> list[str]:
    metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
    metadata_parents = metadata.get("parent_concepts")
    if isinstance(metadata_parents, list) and metadata_parents:
        return [str(parent) for parent in metadata_parents]

    ranked = connection_index.get(node_id, [])
    seeded = [(neighbor, weight) for neighbor, weight in ranked if not str(neighbor).startswith("Emergent_") and neighbor != node_id]
    emergent = [(neighbor, weight) for neighbor, weight in ranked if str(neighbor).startswith("Emergent_") and neighbor != node_id]

    inferred = [neighbor for neighbor, _ in seeded[:3]]
    top_window = ranked[:5]
    emergent_dominant = bool(top_window) and sum(1 for neighbor, _ in top_window if str(neighbor).startswith("Emergent_")) >= max(1, len(top_window) // 2)
    if emergent_dominant or not inferred:
        inferred.extend(neighbor for neighbor, _ in emergent[:2])

    seen: set[str] = set()
    ordered: list[str] = []
    for parent in inferred:
        if parent not in seen:
            seen.add(parent)
            ordered.append(parent)
    return ordered


def extract_emergent_concepts(state_path: Path, basins_path: Path | None = None) -> dict[str, Any]:
    nodes, edges, raw_state = load_graph(state_path)
    basin_lookup = load_basins(discover_basins_path(state_path, basins_path), raw_state=raw_state)
    connection_index = _build_connection_index(nodes, edges)

    concepts: list[dict[str, Any]] = []
    for node_id, node in sorted(nodes.items()):
        if not node_id.startswith("Emergent_"):
            continue
        creation_time = _first_present(
            node.get("metadata", {}).get("creation_time") if isinstance(node.get("metadata"), dict) else None,
            node.get("timestamp"),
            node.get("first_seen"),
        )
        concept = {
            "name": node_id,
            "parents": infer_parent_concepts(node_id, node, connection_index),
            "creation_time": float(creation_time) if creation_time is not None else None,
            "access_count": int(node.get("access_count", 0) or 0),
            "connection_count": len(connection_index.get(node_id, [])),
            "basin_id": basin_lookup.get(node_id),
        }
        concepts.append(concept)

    return {
        "state_path": str(state_path),
        "total_emergent": len(concepts),
        "total_seeded": sum(1 for node_id in nodes if not node_id.startswith("Emergent_")),
        "concepts": concepts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract emergent concepts and parent relationships from state.json")
    parser.add_argument("--state", required=True)
    parser.add_argument("--outfile", required=True)
    parser.add_argument("--basins", default=None, help="Optional basins.json path. Defaults to auto-discovery near the state file.")
    args = parser.parse_args()

    result = extract_emergent_concepts(Path(args.state), Path(args.basins) if args.basins else None)
    out_path = Path(args.outfile)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"outfile": str(out_path), "total_emergent": result["total_emergent"]}, indent=2))


if __name__ == "__main__":
    main()
