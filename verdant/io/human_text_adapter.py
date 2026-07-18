from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
@dataclass
class InputEvent:
    type:str; source:str; payload:dict
class HumanTextInputAdapter:
    def __init__(self, person_id='human', session_id='default'): self.person_id=person_id; self.session_id=session_id; self._q=[]
    def send(self,text): self._q.append(InputEvent('text','human',{'text':text,'person_id':self.person_id,'session_id':self.session_id,'ts_utc':datetime.now(timezone.utc).isoformat()}))
    def poll(self): q,self._q=self._q,[]; return q
