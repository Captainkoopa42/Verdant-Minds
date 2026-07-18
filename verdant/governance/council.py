from __future__ import annotations
class ThreeKingsCouncil:
    def __init__(self): self.influence_weights={'data':1.0,'ethics':1.0,'forefront':1.0}; self.interaction_history=[]
    def to_state_dict(self): return {'influence_weights':dict(self.influence_weights),'interaction_history':list(self.interaction_history)[-200:]}
    @classmethod
    def from_state_dict(cls,state):
        c=cls();
        for k,v in state.get('influence_weights',{}).items(): c.influence_weights[k]=float(v)
        c.interaction_history=list(state.get('interaction_history',[])); return c
