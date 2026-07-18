from __future__ import annotations
from dataclasses import dataclass

@dataclass
class PruneResult:
    edges_pruned:int; density_before:float; density_after:float
@dataclass
class DensityResult:
    edges_removed:int; density_before:float; density_after:float
@dataclass
class BoundaryCandidate:
    source:str=''; target:str=''; score:float=0.0

def _resync(memory_web):
    for n in list(memory_web.memory_store):
        if n in memory_web.graph:
            memory_web.memory_store[n]['connections']=[(str(nb), float(memory_web.graph[n][nb].get('weight',0.0))) for nb in memory_web.graph.neighbors(n)]

def prune_basin_edges(memory_web, basin, weight_threshold=0.2, keep_top_k=2):
    nodes=list(basin.nodes); sub=memory_web.graph.subgraph(nodes); before=sub.number_of_edges(); possible=len(nodes)*(len(nodes)-1)/2; db=before/possible if possible else 0
    candidates=sorted([(d.get('weight',0),a,b) for a,b,d in sub.edges(data=True) if d.get('weight',0)<=weight_threshold])
    pruned=0
    for _,a,b in candidates:
        if memory_web.graph.degree(a)>keep_top_k and memory_web.graph.degree(b)>keep_top_k:
            memory_web.remove_connection(a,b); pruned+=1
    after=memory_web.graph.subgraph(nodes).number_of_edges(); _resync(memory_web); return PruneResult(pruned, db, after/possible if possible else 0)

def regulate_density(memory_web, max_density=0.5, **kw):
    nodes=list(memory_web.graph.nodes); possible=len(nodes)*(len(nodes)-1)/2; before=memory_web.graph.number_of_edges(); db=before/possible if possible else 0; removed=0
    for a,b,d in sorted(list(memory_web.graph.edges(data=True)), key=lambda x:x[2].get('weight',0)):
        if possible and memory_web.graph.number_of_edges()/possible <= max_density: break
        memory_web.remove_connection(a,b); removed+=1
    after=memory_web.graph.number_of_edges(); _resync(memory_web); return DensityResult(removed, db, after/possible if possible else 0)

def compute_basin_pressure(*a, **k): return 0.0
def maybe_bud_basin(*a, **k): return None
def find_ejection_candidates(*a, **k): return []
def maybe_create_boundary_emergents(*a, **k): return []
