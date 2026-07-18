from dataclasses import dataclass
@dataclass
class AttentionItem:
    label: str
    weight: float = 1.0
