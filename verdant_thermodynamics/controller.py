from __future__ import annotations

from dataclasses import dataclass

from .models import PhasePolicyDelta, ThermodynamicPhase, ThermodynamicState


@dataclass(frozen=True)
class PhasePolicyController:
    """EU01 experimental controller proposal surface.

    The controller deliberately has no method that mutates a VerdantKernel.
    Until T0 measurement/null gates are reviewed, it can only produce a bounded
    proposal for a future paired-control experiment.
    """

    revision: str = "phase_policy_1"
    experimental_control_enabled: bool = False

    def propose(self, state: ThermodynamicState) -> PhasePolicyDelta:
        if state.phase == ThermodynamicPhase.RIGID:
            values = (0.80, -1, 0.75, 0.75, -1, -1)
        elif state.phase == ThermodynamicPhase.FLEXIBLE:
            values = (1.00, 0, 1.00, 1.00, 0, 0)
        else:
            values = (1.20, 1, 1.20, 1.20, 1, 1)
        return PhasePolicyDelta(
            controller_revision=self.revision,
            phase=state.phase,
            workspace_resource_multiplier=values[0],
            workspace_persistence_delta=values[1],
            plasticity_learning_multiplier=values[2],
            plasticity_decay_multiplier=values[3],
            resonance_top_k_delta=values[4],
            resonance_commit_delta=values[5],
            behavioral_authority_enabled=self.experimental_control_enabled,
        )
