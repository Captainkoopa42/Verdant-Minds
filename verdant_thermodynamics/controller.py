from __future__ import annotations

from dataclasses import dataclass

from .models import PhasePolicyDelta, ThermodynamicPhase, ThermodynamicState


@dataclass(frozen=True)
class PhasePolicyController:
    """Experimental, nonsemantic thermodynamic homeostasis proposal surface.

    By default this remains measurement-only.  Behavioral authority must be
    explicitly enabled by an experiment.  The controller proposes bounded
    *temporary* policy adjustments; it never mutates canonical evidence,
    concepts, claims, P/Q structures, or kernel policies itself.

    Soft-homeostasis v1 intentionally regulates access before storage:
    - Rigid: favor current evidence, weaken historical recruitment, require
      more context for earned-structure recall, and slightly broaden the
      inspected resonance set without committing more of it.
    - Flexible: leave the developmental policy unchanged.
    - Chaotic: favor current evidence while narrowing historical/recurrent
      recruitment.

    Plasticity multipliers are retained in the proposal schema for later paired
    experiments, but soft-homeostasis v1 leaves them at 1.0.
    """

    revision: str = "phase_policy_homeostasis_1"
    experimental_control_enabled: bool = False

    def propose_for_phase(self, phase: ThermodynamicPhase) -> PhasePolicyDelta:
        if phase == ThermodynamicPhase.RIGID:
            values = {
                "workspace_resource_multiplier": 1.0,
                "workspace_persistence_delta": -1,
                "plasticity_learning_multiplier": 1.0,
                "plasticity_decay_multiplier": 1.0,
                "resonance_top_k_delta": 1,
                "resonance_commit_delta": 0,
                "current_evidence_resource_multiplier": 1.15,
                "historical_resource_multiplier": 0.70,
                "association_recall_threshold_delta": 0.08,
                "structure_trigger_members_delta": 1,
            }
        elif phase == ThermodynamicPhase.FLEXIBLE:
            values = {
                "workspace_resource_multiplier": 1.0,
                "workspace_persistence_delta": 0,
                "plasticity_learning_multiplier": 1.0,
                "plasticity_decay_multiplier": 1.0,
                "resonance_top_k_delta": 0,
                "resonance_commit_delta": 0,
                "current_evidence_resource_multiplier": 1.0,
                "historical_resource_multiplier": 1.0,
                "association_recall_threshold_delta": 0.0,
                "structure_trigger_members_delta": 0,
            }
        else:
            values = {
                "workspace_resource_multiplier": 1.0,
                "workspace_persistence_delta": -1,
                "plasticity_learning_multiplier": 1.0,
                "plasticity_decay_multiplier": 1.0,
                "resonance_top_k_delta": -2,
                "resonance_commit_delta": -1,
                "current_evidence_resource_multiplier": 1.10,
                "historical_resource_multiplier": 0.65,
                "association_recall_threshold_delta": 0.12,
                "structure_trigger_members_delta": 1,
            }
        return PhasePolicyDelta(
            controller_revision=self.revision,
            phase=phase,
            behavioral_authority_enabled=self.experimental_control_enabled,
            **values,
        )

    def propose(self, state: ThermodynamicState) -> PhasePolicyDelta:
        return self.propose_for_phase(state.phase)
