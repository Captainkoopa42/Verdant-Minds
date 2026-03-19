"""Extract emergent concepts and inferred parents from a Verdant state snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analysis.state_adapter import VerdantState
except ImportError:
    from state_adapter import VerdantState


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


def _build_connection_index(vs: VerdantState) -> dict[str, list[tuple[str, float]]]:
    index: dict[str, dict[str, float]] = {}
    for node in vs.nodes:
        name = str(node["name"])
        merged = index.setdefault(name, {})
        for neighbor, weight in node.get("connections", []):
            merged[str(neighbor)] = max(float(weight), merged.get(str(neighbor), float("-inf")))
    for edge in vs.edges:
        source = str(edge["source"])
        target = str(edge["target"])
        weight = float(edge.get("weight", 1.0))
        index.setdefault(source, {})[target] = max(weight, index.setdefault(source, {}).get(target, float("-inf")))
        index.setdefault(target, {})[source] = max(weight, index.setdefault(target, {}).get(source, float("-inf")))
    return {node_id: sorted(neighbors.items(), key=lambda item: (-item[1], item[0])) for node_id, neighbors in index.items()}


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
    vs = VerdantState.load(state_path)
    basin_lookup = load_basins(discover_basins_path(state_path, basins_path), raw_state=vs.raw)
    connection_index = _build_connection_index(vs)

    concepts: list[dict[str, Any]] = []
    for node in sorted(vs.emergent_nodes, key=lambda item: str(item["name"])):
        node_id = str(node["name"])
        concept = {
            "name": node_id,
            "parents": infer_parent_concepts(node_id, node, connection_index),
            "creation_time": float(node.get("creation_time")) if node.get("creation_time") is not None else None,
            "access_count": int(node.get("access_count", 0) or 0),
            "connection_count": len(connection_index.get(node_id, [])),
            "basin_id": basin_lookup.get(node_id),
        }
        concepts.append(concept)

    return {
        "state_path": str(state_path),
        "total_emergent": len(concepts),
        "total_seeded": len(vs.seeded_nodes),
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
