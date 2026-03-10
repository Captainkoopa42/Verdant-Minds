"""Pressure dynamics for basin pruning, budding, and boundary emergence."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math

import networkx as nx

from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.bridge.emergence import assign_emergent_concept_mappings
from verdant_v2.memory.basins import BasinInfo
from verdant_v2.memory.basin_state import BasinState
from verdant_v2.memory.graph import MemoryWeb


@dataclass
class PruneResult:
    """Result of an intra-basin pruning pass."""

    edges_pruned: int
    density_before: float
    density_after: float


@dataclass
class BudResult:
    """Result of a pressure-driven basin budding operation."""

    parent_basin_id: str
    new_basin_id: str
    new_basin_size: int


@dataclass
class BoundaryEmergenceResult:
    """Result of boundary emergent creation for co-activated basin pairs."""

    created_count: int
    boundary_pairs: list[list[str]]


def _within_basin_edges(memory_web: MemoryWeb, node_set: set[str]) -> list[tuple[str, str, float]]:
    edges: list[tuple[str, str, float]] = []
    for u, v, data in memory_web.graph.edges(data=True):
        if u in node_set and v in node_set:
            edges.append((str(u), str(v), float(data.get("weight", 0.0))))
    return edges


def _density_for_nodes(memory_web: MemoryWeb, nodes: list[str]) -> float:
    n = len(nodes)
    if n < 2:
        return 0.0
    sub = memory_web.graph.subgraph(nodes)
    max_edges = n * (n - 1) / 2
    return float(sub.number_of_edges() / max_edges) if max_edges > 0 else 0.0


def prune_basin_edges(
    memory_web: MemoryWeb,
    basin_info: BasinInfo,
    *,
    weight_threshold: float = 0.2,
    keep_top_k: int = 12,
) -> PruneResult:
    """Remove weak edges where both endpoints are in the basin."""
    node_set = set(basin_info.nodes)
    density_before = _density_for_nodes(memory_web, basin_info.nodes)

    keep_edges: set[frozenset[str]] = set()
    for node in basin_info.nodes:
        nbrs: list[tuple[str, float]] = []
        for nbr in memory_web.graph.neighbors(node):
            if nbr not in node_set:
                continue
            w = float(memory_web.graph[node][nbr].get("weight", 0.0))
            nbrs.append((str(nbr), w))
        nbrs.sort(key=lambda x: x[1], reverse=True)
        for nbr, w in nbrs[: max(0, keep_top_k)]:
            if w >= weight_threshold:
                keep_edges.add(frozenset((str(node), nbr)))

    prunable = _within_basin_edges(memory_web, node_set)
    edges_pruned = 0
    for u, v, w in prunable:
        edge_key = frozenset((u, v))
        if w < weight_threshold or edge_key not in keep_edges:
            if memory_web.graph.has_edge(u, v):
                memory_web.graph.remove_edge(u, v)
                edges_pruned += 1

    density_after = _density_for_nodes(memory_web, basin_info.nodes)
    return PruneResult(edges_pruned=edges_pruned, density_before=density_before, density_after=density_after)


def compute_basin_pressure(memory_web: MemoryWeb, basin_info: BasinInfo) -> float:
    """Compute basin pressure from density, instability, and access concentration."""
    accesses: list[float] = []
    for node in basin_info.nodes:
        entry = memory_web.get_concept(node) or {}
        accesses.append(float(entry.get("access_count", 0)))

    total = sum(accesses)
    if total <= 0:
        access_entropy = 0.0
    else:
        probs = [a / total for a in accesses if a > 0]
        access_entropy = -sum(p * math.log(p + 1e-12) for p in probs)

    inverse_access_entropy = 1.0 / (access_entropy + 1e-6)
    return float(basin_info.internal_density * (1.0 / (1.0 + basin_info.mean_stability)) * inverse_access_entropy)


def maybe_bud_basin(
    memory_web: MemoryWeb,
    basin_info: BasinInfo,
    basin_states: dict[str, BasinState],
    *,
    cycle: int,
    next_basin_id: int,
    pressure_threshold: float,
    split_fraction: float,
    min_size_for_split: int,
    min_age_for_split: int,
) -> BudResult | None:
    """Attempt to split a high-pressure basin into parent+bud membership states."""
    pressure = compute_basin_pressure(memory_web, basin_info)
    if pressure <= pressure_threshold or basin_info.size < min_size_for_split:
        return None

    state = basin_states.get(basin_info.basin_id)
    created_cycle = int(state.local_metrics.get("created_cycle", cycle)) if state else cycle
    if cycle - created_cycle < min_age_for_split:
        return None

    nodes = list(basin_info.nodes)
    node_set = set(nodes)
    sub = memory_web.graph.subgraph(nodes)
    degree = {n: int(sum(1 for nbr in sub.neighbors(n) if nbr in node_set)) for n in nodes}
    split_count = max(1, int(len(nodes) * split_fraction))

    ranked = sorted(nodes, key=lambda n: (degree[n], n))
    candidates = ranked[:split_count]

    def remaining_connected(ejected: list[str]) -> bool:
        remain = [n for n in nodes if n not in set(ejected)]
        if len(remain) <= 1:
            return True
        return nx.is_connected(memory_web.graph.subgraph(remain))

    ejected = candidates if remaining_connected(candidates) else []
    if not ejected:
        leaves = [n for n in ranked if degree[n] <= 2][:split_count]
        if leaves and remaining_connected(leaves):
            ejected = leaves
    if not ejected:
        return None

    new_basin_id = f"basin_{next_basin_id}"
    for node in ejected:
        concept = memory_web.get_concept(node) or {}
        metadata = dict(concept.get("metadata", {}))
        metadata.update({"basin_origin": "budded", "parent_basin": basin_info.basin_id, "bud_cycle": cycle})
        if concept:
            memory_web.memory_store[node]["metadata"] = metadata
            memory_web.graph.nodes[node]["metadata"] = metadata

    parent_nodes = [n for n in nodes if n not in set(ejected)]
    basin_states[basin_info.basin_id] = BasinState(
        basin_id=basin_info.basin_id,
        member_nodes=parent_nodes,
        local_metrics={"size": len(parent_nodes), "created_cycle": created_cycle},
    )
    basin_states[new_basin_id] = BasinState(
        basin_id=new_basin_id,
        member_nodes=ejected,
        local_metrics={"size": len(ejected), "created_cycle": cycle, "parent_basin": basin_info.basin_id},
    )
    return BudResult(parent_basin_id=basin_info.basin_id, new_basin_id=new_basin_id, new_basin_size=len(ejected))


def maybe_create_boundary_emergents(
    memory_web: MemoryWeb,
    bridge: EthomorphicBridge,
    active_basins: list[BasinInfo],
    activation_levels: dict[str, float],
    *,
    cycle: int,
    threshold: float,
    cooldown_cycles: int,
    last_boundary_cycles: dict[frozenset[str], int],
) -> BoundaryEmergenceResult:
    """Create boundary emergents between co-activated basin pairs with cooldown."""
    pair_scores: list[tuple[float, BasinInfo, BasinInfo]] = []
    for basin_a, basin_b in combinations(active_basins, 2):
        a_nodes, b_nodes = set(basin_a.nodes), set(basin_b.nodes)
        crossing: set[str] = set()
        for node in a_nodes:
            for nbr in memory_web.graph.neighbors(node):
                if nbr in b_nodes:
                    crossing.add(node)
                    crossing.add(str(nbr))
        overlap = float(sum(float(activation_levels.get(n, 0.0)) for n in crossing))
        pair_scores.append((overlap, basin_a, basin_b))

    pair_scores.sort(key=lambda x: x[0], reverse=True)
    top_pairs = [[a.basin_id, b.basin_id] for _, a, b in pair_scores[:3]]

    created = 0
    for overlap, basin_a, basin_b in pair_scores:
        pair_key = frozenset((basin_a.basin_id, basin_b.basin_id))
        last_cycle = last_boundary_cycles.get(pair_key, -10**9)
        if cycle - last_cycle < cooldown_cycles or overlap <= threshold:
            continue

        top_a = sorted((n for n in basin_a.nodes), key=lambda n: float(activation_levels.get(n, 0.0)), reverse=True)[:3]
        top_b = sorted((n for n in basin_b.nodes), key=lambda n: float(activation_levels.get(n, 0.0)), reverse=True)[:3]
        parents = list(dict.fromkeys(top_a + top_b))
        if len(parents) < 2:
            continue

        new_label = f"Emergent_boundary_{basin_a.basin_id}_{basin_b.basin_id}_{cycle}"
        memory_web.add_concept(
            new_label,
            stability=0.5,
            metadata={
                "origin": "boundary_emergence",
                "basins": [basin_a.basin_id, basin_b.basin_id],
                "boundary": True,
                "creation_time": cycle,
                "parent_concepts": parents,
            },
        )
        assign_emergent_concept_mappings(bridge, new_label, parents)

        for node in top_a + top_b:
            memory_web.connect(new_label, node, 0.65)

        last_boundary_cycles[pair_key] = cycle
        created += 1

    return BoundaryEmergenceResult(created_count=created, boundary_pairs=top_pairs)
