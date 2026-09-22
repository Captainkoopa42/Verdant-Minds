from __future__ import annotations

from dataclasses import dataclass

from .models import PhasePolicyDelta, ThermodynamicPhase, ThermodynamicState


@dataclass(frozen=True)
class PhaseHysteresis:
    """Stateful phase boundaries for the experimental access governor.

    The recovered V4 phase classifier remains untouched telemetry. These wider
    enter/exit thresholds apply only to behavioral control, preventing a Tg
    value near 0.4 or 0.6 from flipping the access policy every cycle.
    """

    rigid_enter: float = 0.38
    rigid_exit: float = 0.42
    chaotic_exit: float = 0.58
    chaotic_enter: float = 0.62

    def select(
        self,
        t_g: float,
        previous: ThermodynamicPhase | None = None,
    ) -> ThermodynamicPhase:
        value = float(t_g)

        if previous == ThermodynamicPhase.RIGID:
            if value >= self.chaotic_enter:
                return ThermodynamicPhase.CHAOTIC
            if value < self.rigid_exit:
                return ThermodynamicPhase.RIGID
            return ThermodynamicPhase.FLEXIBLE

        if previous == ThermodynamicPhase.CHAOTIC:
            if value <= self.rigid_enter:
                return ThermodynamicPhase.RIGID
            if value > self.chaotic_exit:
                return ThermodynamicPhase.CHAOTIC
            return ThermodynamicPhase.FLEXIBLE

        if value < self.rigid_enter:
            return ThermodynamicPhase.RIGID
        if value > self.chaotic_enter:
            return ThermodynamicPhase.CHAOTIC
        return ThermodynamicPhase.FLEXIBLE


@dataclass(frozen=True)
class PhasePolicyController:
    """Experimental, nonsemantic thermodynamic homeostasis proposal surface.

    By default this remains measurement-only. Behavioral authority must be
    explicitly enabled by an experiment. The controller proposes bounded
    *temporary* policy adjustments; it never mutates canonical evidence,
    concepts, claims, P/Q structures, or kernel policies itself.

    Soft-homeostasis v1 regulates access before storage:
    - Rigid: favor current evidence, weaken historical recruitment, require
      stronger resonance plus learned local corroboration to enter workspace,
      and require both absolute and fractional context support for
      earned-structure recall.
    - Flexible: leave the developmental policy unchanged.
    - Chaotic: favor current evidence while narrowing historical/recurrent
      recruitment.

    Plasticity multipliers remain in the proposal schema for later paired
    experiments, but soft-homeostasis v1 leaves them at 1.0.
    """

    revision: str = "phase_policy_homeostasis_4"
    experimental_control_enabled: bool = False
    hysteresis: PhaseHysteresis = PhaseHysteresis()

    def control_phase(
        self,
        state: ThermodynamicState,
        previous: ThermodynamicPhase | None = None,
    ) -> ThermodynamicPhase:
        return self.hysteresis.select(state.t_g, previous)

    def propose_for_phase(self, phase: ThermodynamicPhase) -> PhasePolicyDelta:
        if phase == ThermodynamicPhase.RIGID:
            values = {
                "workspace_resource_multiplier": 1.0,
                "workspace_persistence_delta": -1,
                "plasticity_learning_multiplier": 1.0,
                "plasticity_decay_multiplier": 1.0,
                "resonance_top_k_delta": 0,
                "resonance_commit_delta": 0,
                "current_evidence_resource_multiplier": 1.15,
                "historical_resource_multiplier": 0.70,
                "resonance_recall_threshold_floor": 0.32,
                "resonance_local_support_floor": 0.32,
                "association_recall_threshold_delta": 0.08,
                "structure_trigger_members_delta": 1,
                "structure_trigger_fraction_floor": 0.50,
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
                "resonance_recall_threshold_floor": 0.0,
                "resonance_local_support_floor": 0.0,
                "association_recall_threshold_delta": 0.0,
                "structure_trigger_members_delta": 0,
                "structure_trigger_fraction_floor": 0.0,
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
                "resonance_recall_threshold_floor": 0.35,
                "resonance_local_support_floor": 0.35,
                "association_recall_threshold_delta": 0.12,
                "structure_trigger_members_delta": 1,
                "structure_trigger_fraction_floor": 0.60,
            }
        return PhasePolicyDelta(
            controller_revision=self.revision,
            phase=phase,
            behavioral_authority_enabled=self.experimental_control_enabled,
            **values,
        )

    def propose(
        self,
        state: ThermodynamicState,
        *,
        previous_control_phase: ThermodynamicPhase | None = None,
    ) -> PhasePolicyDelta:
        return self.propose_for_phase(
            self.control_phase(state, previous_control_phase)
        )
