import json
from pathlib import Path
from verdant.output.events import OutputEvent
class InteractionService:
    def __init__(self, system, in_adapter, out_adapter, query_interface, base_dir='.', continuity_window=3): self.system=system; self.in_adapter=in_adapter; self.out_adapter=out_adapter; self.qi=query_interface; self.base_dir=Path(base_dir); self.continuity_window=continuity_window
    def _rows(self, person):
        p=self.base_dir/person/'events.jsonl'
        if not p.exists(): return []
        return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
    def turn(self, person_id, text):
        prior=self._rows(person_id)[-self.continuity_window:]
        result=self.qi.query(text); response=' | '.join(n for n,_ in result['top_activated_nodes'][:3]) or '...'
        self.out_adapter.receive(OutputEvent('speech', response, 'language_processing'))
        row={'person_id':person_id,'text':text,'response':response,'continuity_context':prior}
        p=self.base_dir/person_id/'events.jsonl'; p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('a',encoding='utf-8') as h: h.write(json.dumps(row)+'\n')
        return row
