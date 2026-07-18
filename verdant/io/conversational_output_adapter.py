class ConversationalOutputAdapter:
    def __init__(self): self.last_response=None
    def receive(self,event):
        if getattr(event,'type',None)=='speech': self.last_response=event.payload
    def get_last_response(self): return self.last_response
