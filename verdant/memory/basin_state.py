from dataclasses import dataclass, field
@dataclass
class BasinState:
    basin_id: str = ''
    nodes: list[str] = field(default_factory=list)
