from __future__ import annotations
from pathlib import Path
from typing import Any
import json, hashlib
import networkx as nx
from .persistence import save_state, load_state

class MemoryWeb:
    def __init__(self):
        self.graph=nx.Graph(); self.memory_store={}
    def add_concept(self,label,stability=0.5,metadata=None,**kw):
        label=str(label); self.graph.add_node(label)
        self.memory_store[label]={"stability":float(stability),"metadata":metadata or {},"connections":self.memory_store.get(label,{}).get('connections',[])}
        return label
    def get_concept(self,label): return self.memory_store.get(str(label))
    def connect(self,a,b,weight=0.5):
        a=str(a); b=str(b)
        if a not in self.memory_store: self.add_concept(a)
        if b not in self.memory_store: self.add_concept(b)
        self.graph.add_edge(a,b,weight=float(weight)); self._sync_pair(a,b); return True
    def _sync_pair(self,a,b):
        for n in (a,b):
            self.memory_store[n]['connections']=[(str(x), float(self.graph[n][x].get('weight',0.0))) for x in self.graph.neighbors(n)]
    def remove_connection(self,a,b):
        a=str(a); b=str(b)
        if self.graph.has_edge(a,b): self.graph.remove_edge(a,b)
        for n in (a,b):
            if n in self.memory_store:
                self.memory_store[n]['connections']=[x for x in self.memory_store[n].get('connections',[]) if str(x[0]) != (b if n==a else a)]
    def get_neighbors(self,label): return list(self.graph.neighbors(str(label))) if str(label) in self.graph else []
    def list_concepts(self): return list(self.memory_store.keys())
    def reinforce(self,label,amount=0.1):
        d=self.memory_store[str(label)]; d['stability']=min(1.0,d.get('stability',0)+amount); return d['stability']
    def decay(self,amount=0.01):
        for d in self.memory_store.values(): d['stability']=max(0.0,d.get('stability',0)-amount)
    def activate_concepts(self,seeds):
        out={}
        for s in seeds:
            s=str(s)
            if s in self.graph:
                out[s]=self.memory_store[s].get('stability',0.5)
                for nb in self.graph.neighbors(s): out[nb]=max(out.get(nb,0), self.graph[s][nb].get('weight',0.0)*0.5)
        return out
    def get_emergent_nodes(self): return [n for n in self.memory_store if n.startswith('Emergent_')]
    def get_edge_classification(self):
        d={'seeded_seeded':0,'emergent_seeded':0,'emergent_emergent':0}
        for a,b in self.graph.edges:
            ea,eb=a.startswith('Emergent_'),b.startswith('Emergent_')
            if ea and eb: d['emergent_emergent']+=1
            elif ea or eb: d['emergent_seeded']+=1
            else: d['seeded_seeded']+=1
        return d
    def to_chunks(self): return {'nodes':self.memory_store,'edges':[(a,b,self.graph[a][b]) for a,b in self.graph.edges], 'emergent_summary':self.get_emergent_nodes()}
    def to_state_dict(self): return self.to_chunks()
    @classmethod
    def from_state_dict(cls,state):
        mw=cls(); nodes=state.get('nodes', state.get('memory_store',{}));
        for n,d in nodes.items(): mw.add_concept(n,d.get('stability',0.5),d.get('metadata',{}))
        for e in state.get('edges',[]):
            a,b=e[0],e[1]; data=e[2] if len(e)>2 and isinstance(e[2],dict) else {}; mw.connect(a,b,data.get('weight', e[2] if len(e)>2 and not isinstance(e[2],dict) else 0.5))
        return mw
    @staticmethod
    def _get_ethical_charge(concept): return 0.5

class ShardedMemoryWeb:
    DEFAULT_SHARD_ID='basin_monolith_000000'
    def __init__(self, canvas=None):
        self.active_canvas=canvas or MemoryWeb(); self.active_shard_id=self.DEFAULT_SHARD_ID; self._warm_cache={}; self._dirty=False
        self.manifest={'defaults':{'max_nodes_per_shard':450,'max_edges_per_shard':16000,'lru_cache_size':8},'shards':{self.DEFAULT_SHARD_ID:{'state':'active','path':f'shards/{self.DEFAULT_SHARD_ID}.json','node_count':self.graph.number_of_nodes(),'anchor_labels':[]}},'active_shards':[self.DEFAULT_SHARD_ID],'weak_bridge_edges':[],'concept_index':{}}
    @classmethod
    def monolith(cls, web): return cls(web)
    @property
    def graph(self): return self.active_canvas.graph
    @property
    def memory_store(self): return self.active_canvas.memory_store
    def __getattr__(self,name): return getattr(self.active_canvas,name)
    def _strip_ghosts(self,canvas): pass
    def _refresh_active_manifest(self, dirty=False):
        self.manifest['shards'].setdefault(self.active_shard_id,{}) .update({'state':'active','path':f'shards/{self.active_shard_id}.json','node_count':self.graph.number_of_nodes(),'anchor_labels':list(self.graph.nodes)[:3]}); self._dirty=dirty
    def _load_mandatory_bridge_ghosts(self,root): pass
    def flush_shards(self, memory_root):
        root=Path(memory_root); (root/'shards').mkdir(parents=True,exist_ok=True); maxn=self.manifest['defaults'].get('max_nodes_per_shard',450)
        if self.graph.number_of_nodes()<=maxn:
            save_state(root/'shards'/f'{self.active_shard_id}.json', {'memory_web':self.active_canvas.to_state_dict()}); self._refresh_active_manifest(False); save_state(root/'manifest.json', self.manifest); return {'mitosis_performed':False}
        nodes=list(self.graph.nodes); mid=max(1,len(nodes)//2); daughters=[]
        for part in (nodes[:mid],nodes[mid:]):
            sid='basin_'+hashlib.sha1((''.join(part)).encode()).hexdigest()[:12]; sub=MemoryWeb()
            for n in part: sub.add_concept(n, **{k:v for k,v in self.memory_store[n].items() if k in ('stability','metadata')})
            for a,b,d in self.graph.subgraph(part).edges(data=True): sub.connect(a,b,d.get('weight',0.5))
            save_state(root/'shards'/f'{sid}.json', {'memory_web':sub.to_state_dict()}); self.manifest['shards'][sid]={'state':'active','path':f'shards/{sid}.json','node_count':len(part),'anchor_labels':part[:3]}; daughters.append(sid)
        old=root/'shards'/f'{self.active_shard_id}.json'; old.unlink(missing_ok=True); parent=self.active_shard_id; self.manifest['shards'][parent]['state']='split'; self.manifest['active_shards']=[daughters[0]]; self.manifest['weak_bridge_edges']=[{'source':nodes[mid-1],'target':nodes[mid],'mandatory':True}] if len(nodes)>1 else []
        self.active_shard_id=daughters[0]; self.active_canvas=MemoryWeb.from_state_dict(load_state(root/'shards'/f'{daughters[0]}.json')['memory_web']); save_state(root/'manifest.json', self.manifest); return {'mitosis_performed':True,'parent_shard_id':parent,'daughter_shard_ids':daughters}
    def thaw(self, shard_id, memory_root):
        shard_id=str(shard_id); root=Path(memory_root)
        if shard_id==self.active_shard_id: return
        if self._dirty: self.flush_shards(root)
        if shard_id in self._warm_cache: canvas=self._warm_cache.pop(shard_id)
        else:
            meta=(self.manifest.get('shards') or {}).get(shard_id,{}) ; rel=meta.get('path',f'shards/{shard_id}.json') if isinstance(meta,dict) else f'shards/{shard_id}.json'; target=root/rel
            if not target.exists() and not str(rel).startswith('shards/'): target=root/'shards'/str(rel)
            if not target.exists():
                if isinstance(meta,dict): meta['state']='split'
                ci=self.manifest.get('concept_index',{})
                for label in list(ci):
                    homes=ci[label] if isinstance(ci[label],list) else [ci[label]]; homes=[h for h in homes if h!=shard_id]
                    if homes: ci[label]=homes
                    else: del ci[label]
                return
            canvas=MemoryWeb.from_state_dict(load_state(target).get('memory_web', load_state(target)))
        self.active_canvas=canvas; self.active_shard_id=shard_id; self._warm_cache[shard_id]=canvas
        lru=self.manifest.get('defaults',{}).get('lru_cache_size',2)
        while len(self._warm_cache)>lru: self._warm_cache.pop(next(iter(self._warm_cache)))
        self._refresh_active_manifest(False)
