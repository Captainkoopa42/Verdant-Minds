from dataclasses import dataclass
from typing import Any
@dataclass
class OutputEvent:
    type: str
    payload: Any
    source: str = ''
