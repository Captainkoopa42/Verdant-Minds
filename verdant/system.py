from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from .memory.graph import MemoryWeb, ShardedMemoryWeb
from .memory.persistence import save_state as _save_json, load_state as _load_json
from .memory.basins import detect_basins
from .governance.council import ThreeKingsCouncil

@dataclass
class VerdantConfig:
    seed: int = 0
    enable_sharding: bool = True

class VerdantSystem:
    def __init__(self, config: VerdantConfig | None = None):
        self.config=config or VerdantConfig(); self.memory_web=ShardedMemoryWeb.monolith(MemoryWeb()); self.council=ThreeKingsCouncil(); self._checkpoint_path=None; self._last_basins=[]; self.adapters=[]; self.output_adapters=[]
    def register_adapter(self,a): self.adapters.append(a)
    def register_output_adapter(self,a): self.output_adapters.append(a)
    def process_input(self,text:str):
        labels=[w.strip('.,!?;:').lower() for w in text.split() if w.strip('.,!?;:')]
        prev=None
        for w in labels:
            self.memory_web.add_concept(w,0.5,{});
            if prev: self.memory_web.connect(prev,w,0.5)
            prev=w
        return self.memory_web.activate_concepts(labels[:3])
    def get_metrics(self):
        self._last_basins=detect_basins(self.memory_web, min_size=1)
        return {'node_count':self.memory_web.graph.number_of_nodes(),'edge_count':self.memory_web.graph.number_of_edges(),'basin_count':len(self._last_basins),'basins':[b.to_dict() for b in self._last_basins],'t_g':0.5}
    def save_state(self,path:str):
        self._checkpoint_path=path; p=Path(path); shard_root=p.with_name(p.stem+'_shards'); self.memory_web.flush_shards(shard_root)
        state={'version':'4','memory_web':self.memory_web.active_canvas.to_state_dict(),'manifest':self.memory_web.manifest,'council':self.council.to_state_dict()}
        _save_json(p,state)
        _save_json(p.with_name(p.stem+'_council.json'), self.council.to_state_dict())
    def load_state(self,path:str):
        self._checkpoint_path=path; p=Path(path); state=_load_json(p)
        self.memory_web=ShardedMemoryWeb.monolith(MemoryWeb.from_state_dict(state.get('memory_web',{}))); self.memory_web.manifest=state.get('manifest', self.memory_web.manifest)
        cstate=state.get('council')
        side=p.with_name(p.stem+'_council.json')
        if cstate is None and side.exists(): cstate=_load_json(side)
        if cstate: self.council=ThreeKingsCouncil.from_state_dict(cstate)
