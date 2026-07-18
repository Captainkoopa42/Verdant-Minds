from verdant.memory.basins import detect_basins
class QueryInterface:
    def __init__(self, system): self.system=system
    def query(self,text):
        acts=self.system.process_input(text)
        top=sorted(acts.items(), key=lambda x:x[1], reverse=True)[:10]
        return {'top_activated_nodes':top,'activations':acts}
    def inspect_basin(self, basin_id):
        basins=getattr(self.system,'_last_basins',[]) or detect_basins(self.system.memory_web, min_size=1)
        for b in basins:
            if b.basin_id==basin_id: return {'source':'cached','basin':b.to_dict()}
        return {'source':'detected','basins':[b.to_dict() for b in basins]}
