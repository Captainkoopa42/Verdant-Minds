from dataclasses import dataclass, field
from typing import Any
@dataclass
class ProcessingStep:
    name: str
    data: dict[str, Any] = field(default_factory=dict)
@dataclass
class CognitiveChunk:
    content: str = ''
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[ProcessingStep] = field(default_factory=list)
