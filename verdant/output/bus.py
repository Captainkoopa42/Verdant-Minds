class OutputBus:
    def __init__(self): self.adapters=[]
    def register(self, adapter): self.adapters.append(adapter)
    def emit_all(self, events):
        for e in events:
            for a in self.adapters:
                if hasattr(a,'receive'): a.receive(e)
