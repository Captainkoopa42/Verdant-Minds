"""Interventions for scaffold-ablation experiments on MemoryWeb."""

from __future__ import annotations

import random
from typing import Any

from verdant_v2.memory.graph import MemoryWeb


def _node_timestamp(memory_web: MemoryWeb, node: str) -> float:
    data = memory_web.get_concept(node) or {}
    metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
    if not isinstance(metadata, dict):
        metadata = {}
    for key in ("created_at", "creation_time", "first_seen"):
        value = metadata.get(key) if key in metadata else data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0.0


def get_emergent_nodes_sorted_by_age(memory_web: MemoryWeb) -> list[str]:
    """Return emergent nodes ordered oldest-first by creation timestamp."""
    emergent = memory_web.get_emergent_nodes()
    return sorted(emergent, key=lambda n: (_node_timestamp(memory_web, n), n))


def ablate_oldest_emergent_nodes(
    memory_web: MemoryWeb,
    fraction: float,
    basin_nodes: set[str] | None = None,
) -> dict[str, Any]:
    """Remove the oldest emergent nodes globally or within ``basin_nodes``."""
    frac = max(0.0, min(1.0, float(fraction)))
    if frac <= 0.0:
        return {"removed_nodes": [], "removed_count": 0, "removed_ee_edges": 0}

    sorted_nodes = get_emergent_nodes_sorted_by_age(memory_web)
    if basin_nodes is not None:
        sorted_nodes = [n for n in sorted_nodes if n in basin_nodes]

    target_count = int(len(sorted_nodes) * frac)
    if target_count <= 0 and sorted_nodes:
        target_count = 1

    removed_nodes = sorted_nodes[:target_count]
    removed_ee_edges = 0

    for node in removed_nodes:
        if node not in memory_web.graph:
            continue

        neighbors = list(memory_web.graph.neighbors(node))
        for nbr in neighbors:
            if nbr.startswith("Emergent_"):
                removed_ee_edges += 1
            if nbr in memory_web.memory_store:
                conns = memory_web.memory_store[nbr].get("connections", [])
                memory_web.memory_store[nbr]["connections"] = [
                    (label, weight) for label, weight in conns if label != node
                ]

        if node in memory_web.memory_store:
            del memory_web.memory_store[node]

        memory_web.graph.remove_node(node)

    memory_web.metrics["total_concepts"] = len(memory_web.memory_store)
    memory_web.metrics["total_connections"] = memory_web.graph.number_of_edges()

    return {
        "removed_nodes": removed_nodes,
        "removed_count": len(removed_nodes),
        "removed_ee_edges": removed_ee_edges,
    }


def scramble_emergent_edges(
    memory_web: MemoryWeb,
    rng_seed: int,
    basin_nodes: set[str] | None = None,
) -> dict[str, Any]:
    """Deterministically scramble emergent↔emergent edges in scope."""
    emergent_nodes = set(memory_web.get_emergent_nodes())
    if basin_nodes is not None:
        emergent_nodes &= set(basin_nodes)

    original_edges: list[tuple[str, str]] = []
    for u, v in memory_web.graph.edges():
        if u in emergent_nodes and v in emergent_nodes:
            edge = (u, v) if u < v else (v, u)
            original_edges.append(edge)

    original_edges = sorted(set(original_edges))
    original_edge_count = len(original_edges)
    if original_edge_count == 0:
        return {"scrambled_edge_count": 0, "original_edge_count": 0}

    # Preserve degree sequence via stub matching when possible.
    degree_counts: dict[str, int] = {n: 0 for n in emergent_nodes}
    weight_map: dict[tuple[str, str], float] = {}
    for u, v in original_edges:
        degree_counts[u] += 1
        degree_counts[v] += 1
        weight_map[(u, v)] = float(memory_web.graph[u][v].get("weight", 0.5))

    rng = random.Random(rng_seed)
    stubs: list[str] = []
    for node, deg in sorted(degree_counts.items()):
        stubs.extend([node] * deg)
    rng.shuffle(stubs)

    new_edges: set[tuple[str, str]] = set()
    max_attempts = max(50, len(stubs) * 20)
    attempts = 0

    while len(stubs) >= 2 and attempts < max_attempts:
        a = stubs.pop()
        partner_idx = None
        for i in range(len(stubs) - 1, -1, -1):
            b = stubs[i]
            edge = (a, b) if a < b else (b, a)
            if a != b and edge not in new_edges:
                partner_idx = i
                break
        if partner_idx is None:
            stubs.insert(0, a)
            rng.shuffle(stubs)
            attempts += 1
            continue

        b = stubs.pop(partner_idx)
        edge = (a, b) if a < b else (b, a)
        new_edges.add(edge)
        attempts += 1

    if len(new_edges) != original_edge_count:
        candidates = [(u, v) for u in sorted(emergent_nodes) for v in sorted(emergent_nodes) if u < v]
        rng.shuffle(candidates)
        for edge in candidates:
            if len(new_edges) >= original_edge_count:
                break
            if edge[0] != edge[1] and edge not in new_edges:
                new_edges.add(edge)

    old_set = set(original_edges)
    for u, v in old_set:
        if memory_web.graph.has_edge(u, v):
            memory_web.graph.remove_edge(u, v)

    ordered_new = sorted(new_edges)[:original_edge_count]
    weights = [weight_map[e] for e in original_edges]
    for idx, (u, v) in enumerate(ordered_new):
        memory_web.graph.add_edge(u, v, weight=weights[idx % len(weights)])

    # Rebuild connections for affected emergent nodes to stay consistent.
    touched = set(emergent_nodes)
    for node in touched:
        if node not in memory_web.memory_store:
            continue
        memory_web.memory_store[node]["connections"] = [
            (nbr, wt)
            for (nbr, wt) in memory_web.memory_store[node].get("connections", [])
            if nbr not in touched
        ]

    for u, v in ordered_new:
        w = float(memory_web.graph[u][v].get("weight", 0.5))
        if u in memory_web.memory_store:
            memory_web.memory_store[u].setdefault("connections", []).append((v, w))
        if v in memory_web.memory_store:
            memory_web.memory_store[v].setdefault("connections", []).append((u, w))

    memory_web.metrics["total_connections"] = memory_web.graph.number_of_edges()

    return {
        "scrambled_edge_count": len(ordered_new),
        "original_edge_count": original_edge_count,
    }
