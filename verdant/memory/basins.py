from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import networkx as nx

@dataclass
class BasinInfo:
    basin_id: str
    nodes: list[str]
    size: int
    internal_edges: int
    boundary_edges: int
    internal_density: float
    emergent_count: int
    mean_stability: float
    top_nodes_by_access: list[tuple[str, int]]
    created_at: float = 0.0
    def to_dict(self) -> dict[str, Any]: return asdict(self)

def detect_basins(memory_web, min_size: int = 2) -> list[BasinInfo]:
    basins=[]
    for i, comp in enumerate(nx.connected_components(memory_web.graph)):
        nodes=sorted(map(str, comp))
        if len(nodes)<min_size: continue
        sub=memory_web.graph.subgraph(nodes)
        possible=len(nodes)*(len(nodes)-1)/2
        st=[memory_web.memory_store.get(n,{}).get('stability',0.0) for n in nodes]
        basins.append(BasinInfo(f"basin_{i}", nodes, len(nodes), sub.number_of_edges(), 0, sub.number_of_edges()/possible if possible else 0.0, sum(n.startswith('Emergent_') for n in nodes), sum(st)/len(st) if st else 0.0, [(n, memory_web.graph.degree(n)) for n in nodes[:5]], 0.0))
    return basins
