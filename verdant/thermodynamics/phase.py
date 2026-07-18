from dataclasses import dataclass
@dataclass
class PhaseState: t_g: float = 0.5
def compute_t_g(*a, **k): return 0.5
def compute_phase(*a, **k): return PhaseState(0.5)
