"""Basin detection over MemoryWeb backbone graphs."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Tuple

import networkx as nx

from verdant_v2.memory.graph import MemoryWeb


@dataclass
class BasinInfo:
    """Summary statistics for a detected basin/community."""

    basin_id: str
    nodes: List[str]
    size: int
    internal_edges: int
    boundary_edges: int
    internal_density: float
    emergent_count: int
    mean_stability: float
    top_nodes_by_access: List[Tuple[str, int]]
    created_at: float


def _build_backbone(memory_web: MemoryWeb, k: int) -> nx.Graph:
    """Build undirected backbone using top-k weighted neighbors per node."""
    g = nx.Graph()
    for node in memory_web.graph.nodes():
        g.add_node(node)

    for node in memory_web.graph.nodes():
        neighbors = []
        for nbr in memory_web.graph.neighbors(node):
            w = float(memory_web.graph[node][nbr].get("weight", 0.5))
            neighbors.append((nbr, w))
        neighbors.sort(key=lambda x: x[1], reverse=True)
        for nbr, w in neighbors[: max(1, k)]:
            if g.has_edge(node, nbr):
                old = float(g[node][nbr].get("weight", 0.0))
                g[node][nbr]["weight"] = max(old, w)
            else:
                g.add_edge(node, nbr, weight=w)
    return g


def detect_basins(memory_web: MemoryWeb, *, k: int = 6, min_size: int = 5) -> List[BasinInfo]:
    """Detect backbone communities and return basin summaries."""
    if memory_web.graph.number_of_nodes() == 0:
        return []

    backbone = _build_backbone(memory_web, k)
    if backbone.number_of_edges() == 0:
        return []

    communities = nx.algorithms.community.greedy_modularity_communities(backbone, weight="weight")
    now = time.time()
    basins: List[BasinInfo] = []

    for idx, comm in enumerate(communities):
        nodes = sorted(str(n) for n in comm)
        if len(nodes) < min_size:
            continue

        sub = backbone.subgraph(nodes)
        internal_edges = int(sub.number_of_edges())

        node_set = set(nodes)
        boundary_edges = 0
        for u, v in backbone.edges():
            in_u = u in node_set
            in_v = v in node_set
            if in_u ^ in_v:
                boundary_edges += 1

        n = len(nodes)
        max_edges = n * (n - 1) / 2
        density = (internal_edges / max_edges) if max_edges > 0 else 0.0

        emergent_count = sum(1 for nlabel in nodes if nlabel.startswith("Emergent_"))

        stabilities = []
        accesses: List[Tuple[str, int]] = []
        for nlabel in nodes:
            entry = memory_web.get_concept(nlabel) or {}
            stabilities.append(float(entry.get("stability", 0.0)))
            accesses.append((nlabel, int(entry.get("access_count", 0))))
        mean_stability = (sum(stabilities) / len(stabilities)) if stabilities else 0.0
        accesses.sort(key=lambda x: x[1], reverse=True)

        basins.append(
            BasinInfo(
                basin_id=f"basin_{idx}",
                nodes=nodes,
                size=n,
                internal_edges=internal_edges,
                boundary_edges=boundary_edges,
                internal_density=float(density),
                emergent_count=emergent_count,
                mean_stability=float(mean_stability),
                top_nodes_by_access=accesses[:10],
                created_at=now,
            )
        )

    basins.sort(key=lambda b: b.size, reverse=True)
    return basins
