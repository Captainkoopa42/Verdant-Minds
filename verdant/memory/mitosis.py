"""Physical graph mitosis for sharded Verdant memory stores."""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

from verdant.config import ETHICS_ANCHOR_THRESHOLD, SALIENCE_DECAY_RATE
from verdant.memory.persistence import save_state


@dataclass(frozen=True)
class DaughterShard:
    """A daughter shard produced by splitting an oversized memory graph."""

    shard_id: str
    anchors: list[str]
    node_ids: list[str]
    state: dict[str, Any]


@dataclass(frozen=True)
class MitosisResult:
    """Result of a physical shard split."""

    parent_shard_id: str
    daughters: tuple[DaughterShard, DaughterShard]
    weak_bridge_edges: list[dict[str, Any]]
    manifest: dict[str, Any]
    active_shard_id: str
    active_state: dict[str, Any]


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def shard_exceeds_limits(graph: nx.Graph, manifest: dict[str, Any]) -> bool:
    """Return True when *graph* exceeds manifest node/edge caps."""
    defaults = manifest.get("defaults", {}) if isinstance(manifest, dict) else {}
    max_nodes = int(defaults.get("max_nodes_per_shard", 512))
    max_edges = int(defaults.get("max_edges_per_shard", 20_000))
    return graph.number_of_nodes() > max_nodes or graph.number_of_edges() > max_edges


def split_and_persist(
    *,
    memory_web: Any,
    manifest: dict[str, Any],
    parent_shard_id: str,
    memory_root: str | Path,
) -> MitosisResult | None:
    """Split an oversized active shard into two persisted daughter shard files.

    The split is local to the active NetworkX graph. Internal daughter edges stay
    in their daughter shard states; cut edges are promoted into manifest-level
    weak bridge edges with their original weights preserved.
    """
    graph = memory_web.graph
    if graph.number_of_nodes() < 2 or not shard_exceeds_limits(graph, manifest):
        return None

    left_nodes, right_nodes = _bisect_graph(graph)
    if not left_nodes or not right_nodes:
        return None

    root = Path(memory_root)
    shards_dir = root / "shards"
    shards_dir.mkdir(parents=True, exist_ok=True)

    parent_meta = dict((manifest.get("shards", {}) or {}).get(parent_shard_id, {}) or {})
    daughters = (
        _build_daughter(memory_web, parent_shard_id, left_nodes, "a"),
        _build_daughter(memory_web, parent_shard_id, right_nodes, "b"),
    )
    current_cycle = int((manifest.get("runtime", {}) or {}).get("cycle", manifest.get("current_cycle", 0)) or 0)
    weak_edges = _promote_cut_edges(memory_web, graph, parent_shard_id, daughters, current_cycle=current_cycle)

    updated_manifest = _updated_manifest(
        manifest=manifest,
        parent_shard_id=parent_shard_id,
        parent_meta=parent_meta,
        daughters=daughters,
        weak_edges=weak_edges,
    )

    for daughter in daughters:
        shard_path = root / str(updated_manifest["shards"][daughter.shard_id]["path"])
        save_state(shard_path, _shard_document(daughter))

    save_state(root / "manifest.json", updated_manifest)

    parent_path_value = parent_meta.get("path")
    if isinstance(parent_path_value, str) and parent_path_value:
        parent_path = root / parent_path_value
        if parent_path.exists() and parent_path.name not in {f"{d.shard_id}.json" for d in daughters}:
            parent_path.unlink()

    active = daughters[0]
    return MitosisResult(
        parent_shard_id=parent_shard_id,
        daughters=daughters,
        weak_bridge_edges=weak_edges,
        manifest=updated_manifest,
        active_shard_id=active.shard_id,
        active_state=active.state,
    )


def _bisect_graph(graph: nx.Graph) -> tuple[set[str], set[str]]:
    communities = list(nx.algorithms.community.greedy_modularity_communities(graph, weight="weight"))
    communities = [set(str(node) for node in community) for community in communities if community]
    if len(communities) >= 2:
        communities.sort(key=lambda nodes: (-len(nodes), sorted(nodes)[0]))
        left: set[str] = set()
        right: set[str] = set()
        for community in communities:
            if len(left) <= len(right):
                left.update(community)
            else:
                right.update(community)
        return left, right

    nodes = sorted(str(node) for node in graph.nodes())
    if len(nodes) < 2:
        return set(nodes), set()

    try:
        left_raw, right_raw = nx.algorithms.community.kernighan_lin_bisection(graph, weight="weight")
        left = {str(node) for node in left_raw}
        right = {str(node) for node in right_raw}
        if left and right:
            return left, right
    except (nx.NetworkXError, ZeroDivisionError):
        pass

    midpoint = len(nodes) // 2
    return set(nodes[:midpoint]), set(nodes[midpoint:])


def _build_daughter(memory_web: Any, parent_shard_id: str, nodes: set[str], suffix: str) -> DaughterShard:
    node_ids = sorted(nodes)
    anchors = _anchor_labels(memory_web.graph.subgraph(node_ids), memory_web, limit=3)
    shard_id = _daughter_id(parent_shard_id, anchors, node_ids, suffix)
    node_set = set(node_ids)

    memory_store: dict[str, Any] = {}
    for node in node_ids:
        data = dict(memory_web.memory_store.get(node, {}) or {})
        data["connections"] = [
            tuple(conn)
            for conn in data.get("connections", [])
            if isinstance(conn, (list, tuple)) and conn and str(conn[0]) in node_set
        ]
        memory_store[node] = data

    edges = [
        {"source": str(u), "target": str(v), "weight": float(data.get("weight", 0.5))}
        for u, v, data in memory_web.graph.subgraph(node_ids).edges(data=True)
        if str(u) in node_set and str(v) in node_set
    ]

    state = {
        "memory_store": memory_store,
        "edges": edges,
        "edge_policy": memory_web.edge_policy,
        "metrics": _metrics_for_state(memory_web, memory_store, len(edges)),
    }
    return DaughterShard(shard_id=shard_id, anchors=anchors, node_ids=node_ids, state=state)


def _anchor_labels(subgraph: nx.Graph, memory_web: Any, *, limit: int) -> list[str]:
    if subgraph.number_of_nodes() == 0:
        return []
    centrality = nx.degree_centrality(subgraph)
    scored = []
    for node, cent in centrality.items():
        data = memory_web.get_concept(str(node)) or {}
        scored.append((float(cent), int(data.get("access_count", 0)), float(data.get("stability", 0.0)), str(node)))
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    return [label for *_rest, label in scored[:limit]]


def _daughter_id(parent_shard_id: str, anchors: list[str], nodes: list[str], suffix: str) -> str:
    names = anchors[:2] if anchors else nodes[:2]
    slug = "_".join(_slugify(name) for name in names if _slugify(name)) or "shard"
    digest = hashlib.sha256("|".join([parent_shard_id, suffix, *nodes]).encode("utf-8")).hexdigest()[:8]
    return f"basin_{slug}_{digest}"


def _slugify(value: str) -> str:
    slug = _SLUG_RE.sub("_", value.lower()).strip("_")
    return slug[:32]


def _compute_salience(node_data: dict[str, Any], current_cycle: int) -> float:
    peak = float(node_data.get("ethics_salience_peak", 0.0) or 0.0)
    floor = float(node_data.get("ethics_salience_floor", 0.0) or 0.0)
    last = int(node_data.get("ethics_salience_last_cycle", 0) or 0)
    cycles = max(0, int(current_cycle) - last)
    return max(floor, peak * (SALIENCE_DECAY_RATE ** cycles))


def _promote_cut_edges(
    memory_web: Any,
    graph: nx.Graph,
    parent_shard_id: str,
    daughters: tuple[DaughterShard, DaughterShard],
    *,
    current_cycle: int = 0,
) -> list[dict[str, Any]]:
    left, right = daughters
    node_to_shard = {node: left.shard_id for node in left.node_ids}
    node_to_shard.update({node: right.shard_id for node in right.node_ids})
    now = time.time()
    weak_edges: list[dict[str, Any]] = []
    for u, v, data in graph.edges(data=True):
        source = str(u)
        target = str(v)
        source_shard = node_to_shard.get(source)
        target_shard = node_to_shard.get(target)
        if source_shard is None or target_shard is None or source_shard == target_shard:
            continue
        weight = float(data.get("weight", 0.5))
        source_data = memory_web.get_concept(source) or dict(graph.nodes[source])
        target_data = memory_web.get_concept(target) or dict(graph.nodes[target])
        src_salience = _compute_salience(source_data, current_cycle)
        dst_salience = _compute_salience(target_data, current_cycle)
        is_mandatory = src_salience >= ETHICS_ANCHOR_THRESHOLD or dst_salience >= ETHICS_ANCHOR_THRESHOLD
        bridge_key = "|".join(sorted([source_shard, target_shard, source, target]))
        bridge_id = f"bridge_{hashlib.sha256(bridge_key.encode('utf-8')).hexdigest()[:12]}"
        weak_edges.append({
            "bridge_id": bridge_id,
            "parent_shard": parent_shard_id,
            "source_shard": source_shard,
            "source": source,
            "target_shard": target_shard,
            "target": target,
            "weight": weight,
            "mandatory": is_mandatory,
            "src_salience": src_salience,
            "dst_salience": dst_salience,
            "resonance": 0.0,
            "thaw_penalty": 1.0,
            "last_energy_out": 0.0,
            "last_traversed": None,
            "traversal_count": 0,
            "status": "active" if is_mandatory else "ghost",
            "created_at": now,
        })
    weak_edges.sort(key=lambda edge: (edge["source_shard"], edge["source"], edge["target_shard"], edge["target"]))
    return weak_edges


def _updated_manifest(
    *,
    manifest: dict[str, Any],
    parent_shard_id: str,
    parent_meta: dict[str, Any],
    daughters: tuple[DaughterShard, DaughterShard],
    weak_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    updated = dict(manifest)
    updated["shards"] = dict((manifest.get("shards", {}) or {}))
    updated["concept_index"] = {}
    updated["weak_bridge_edges"] = list(manifest.get("weak_bridge_edges", []) or [])
    updated["updated_at"] = time.time()

    parent_entry = dict(parent_meta)
    parent_entry.update({
        "shard_id": parent_shard_id,
        "state": "split",
        "dirty": False,
        "updated_at": updated["updated_at"],
        "mitosis": {
            "eligible": False,
            "split_at": updated["updated_at"],
            "daughter_shard_ids": [daughter.shard_id for daughter in daughters],
        },
    })
    updated["shards"][parent_shard_id] = parent_entry

    for idx, daughter in enumerate(daughters):
        updated["shards"][daughter.shard_id] = {
            "shard_id": daughter.shard_id,
            "path": f"shards/{daughter.shard_id}.json",
            "state": "active" if idx == 0 else "inactive",
            "node_count": len(daughter.state.get("memory_store", {})),
            "edge_count": len(daughter.state.get("edges", [])),
            "dirty": False,
            "created_at": updated["updated_at"],
            "updated_at": updated["updated_at"],
            "last_accessed": updated["updated_at"] if idx == 0 else None,
            "access_count": 1 if idx == 0 else 0,
            "anchors": [
                {
                    "label": label,
                    "centrality": None,
                    "access_count": int((daughter.state["memory_store"].get(label, {}) or {}).get("access_count", 0)),
                    "stability": float((daughter.state["memory_store"].get(label, {}) or {}).get("stability", 0.0)),
                }
                for label in daughter.anchors
            ],
            "anchor_labels": daughter.anchors,
            "mitosis": {
                "eligible": True,
                "parent_shard_id": parent_shard_id,
                "daughter_shard_ids": [],
            },
        }
        for label in daughter.node_ids:
            updated["concept_index"][label] = [daughter.shard_id]

    updated["active_shards"] = [daughters[0].shard_id]
    updated["weak_bridge_edges"].extend(weak_edges)
    total_node_count = sum(len(daughter.node_ids) for daughter in daughters)
    assert len(updated["concept_index"]) == total_node_count
    assert all(
        shard_id in updated["shards"]
        for homes in updated["concept_index"].values()
        for shard_id in homes
    )
    assert all(
        edge.get("source") in updated["concept_index"] and edge.get("target") in updated["concept_index"]
        for edge in updated["weak_bridge_edges"]
        if edge.get("mandatory")
    )
    return updated


def _metrics_for_state(memory_web: Any, memory_store: dict[str, Any], edge_count: int) -> dict[str, Any]:
    metrics = dict(getattr(memory_web, "metrics", {}) or {})
    node_count = len(memory_store)
    metrics["total_concepts"] = node_count
    metrics["total_connections"] = edge_count
    if node_count:
        stability_total = sum(float(data.get("stability", 0.0)) for data in memory_store.values())
        metrics["avg_stability"] = stability_total / node_count
    else:
        metrics["avg_stability"] = 0.0
    return metrics


def _shard_document(daughter: DaughterShard) -> dict[str, Any]:
    return {
        "version": 1,
        "schema": "verdant.memory_shard.v1",
        "shard_id": daughter.shard_id,
        "anchors": daughter.anchors,
        "memory_web": daughter.state,
    }
