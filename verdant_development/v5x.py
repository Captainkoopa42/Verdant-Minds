from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from verdant_kernel import ExperienceCommand, VerdantKernel
from verdant_thermodynamics import (
    PhasePolicyController,
    PhasePolicyDelta,
    ThermodynamicPhase,
    ThermodynamicState,
    VerdantThermodynamicObserver,
)

from .pipeline import (
    DevelopmentalCycleConfig,
    DevelopmentalCycleResult,
    VerdantDevelopmentPipeline,
)


def controlled_development_config(
    base: DevelopmentalCycleConfig,
    policy: PhasePolicyDelta,
) -> DevelopmentalCycleConfig:
    """Return a temporary nonsemantic developmental config for one next cycle.

    This helper deliberately does not mutate kernel policy state.  Soft
    homeostasis v1 only changes access/recruitment conditions.  Canonical
    evidence, graph memory, P/Q structures, ECWF policy, and plasticity policy
    remain untouched.

    Plasticity multipliers are intentionally not applied in this first
    experiment; they stay in PhasePolicyDelta for a later paired-control stage.
    """

    if not policy.behavioral_authority_enabled:
        return base

    top_k = max(1, base.resonance_top_k + policy.resonance_top_k_delta)
    commit_limit = max(
        0,
        min(top_k, base.resonance_commit_limit + policy.resonance_commit_delta),
    )
    historical = policy.historical_resource_multiplier

    return replace(
        base,
        resonance_top_k=top_k,
        resonance_commit_limit=commit_limit,
        resonance_recall_threshold=max(
            base.resonance_recall_threshold,
            policy.resonance_recall_threshold_floor,
        ),
        resonance_local_support_floor=max(
            base.resonance_local_support_floor,
            policy.resonance_local_support_floor,
        ),
        current_evidence_resource=max(
            1e-9,
            base.current_evidence_resource
            * policy.current_evidence_resource_multiplier,
        ),
        resonance_resource=max(1e-9, base.resonance_resource * historical),
        association_resource=max(1e-9, base.association_resource * historical),
        structure_resource=max(1e-9, base.structure_resource * historical),
        association_recall_threshold=max(
            0.0,
            min(
                1.0,
                base.association_recall_threshold
                + policy.association_recall_threshold_delta,
            ),
        ),
        structure_trigger_members=max(
            1,
            base.structure_trigger_members + policy.structure_trigger_members_delta,
        ),
        structure_trigger_fraction=max(
            base.structure_trigger_fraction,
            policy.structure_trigger_fraction_floor,
        ),
        current_evidence_persistence=max(
            1,
            base.current_evidence_persistence + policy.workspace_persistence_delta,
        ),
        resonance_persistence=max(
            1,
            base.resonance_persistence + policy.workspace_persistence_delta,
        ),
    )


@dataclass(frozen=True)
class ThermodynamicControlApplication:
    """Auditable record of the previous-cycle policy used for this cycle."""

    source_cycle: int
    source_t_g: float
    source_phase: ThermodynamicPhase
    control_phase: ThermodynamicPhase
    policy: PhasePolicyDelta
    effective_config: dict[str, object]


@dataclass(frozen=True)
class V5XDevelopmentalCycleResult:
    """Observation-enriched view of the V5 developmental heartbeat.

    Observer-only mode remains the default and preserves the historical
    byte-identical V5 path.  Experimental thermodynamic control is separately
    opt-in.  When enabled, the *previous* committed thermodynamic state may
    alter only a temporary DevelopmentalCycleConfig for the next cycle.
    """

    development: DevelopmentalCycleResult
    thermodynamics: ThermodynamicState | None
    modality: str
    thermodynamic_control: ThermodynamicControlApplication | None = None

    def __getattr__(self, name: str):
        return getattr(self.development, name)


class V5XDevelopmentPipeline:
    """V5-X wrapper with observer-only default and opt-in soft homeostasis."""

    def __init__(
        self,
        development: VerdantDevelopmentPipeline | None = None,
        *,
        thermodynamic_observer: VerdantThermodynamicObserver | None = None,
        enable_thermodynamic_observation: bool = True,
        enable_thermodynamic_control: bool = False,
        phase_policy_controller: PhasePolicyController | None = None,
    ) -> None:
        if enable_thermodynamic_control and not enable_thermodynamic_observation:
            raise ValueError(
                "Thermodynamic control requires thermodynamic observation."
            )
        self.development = development or VerdantDevelopmentPipeline()
        self.thermodynamic_observer = (
            thermodynamic_observer or VerdantThermodynamicObserver()
        )
        self.enable_thermodynamic_observation = bool(
            enable_thermodynamic_observation
        )
        self.enable_thermodynamic_control = bool(enable_thermodynamic_control)
        self.phase_policy_controller = phase_policy_controller or PhasePolicyController(
            experimental_control_enabled=self.enable_thermodynamic_control
        )
        if (
            self.enable_thermodynamic_control
            and not self.phase_policy_controller.experimental_control_enabled
        ):
            raise ValueError(
                "Thermodynamic control was enabled with a controller that has "
                "no experimental behavioral authority."
            )
        self._last_thermodynamics: dict[str, ThermodynamicState] = {}
        self._control_phases: dict[str, ThermodynamicPhase] = {}

    def _controlled_development(
        self,
        kernel_id: str,
    ) -> tuple[VerdantDevelopmentPipeline, ThermodynamicControlApplication | None]:
        if not self.enable_thermodynamic_control:
            return self.development, None
        previous = self._last_thermodynamics.get(kernel_id)
        if previous is None:
            return self.development, None

        prior_control_phase = self._control_phases.get(kernel_id)
        control_phase = self.phase_policy_controller.control_phase(
            previous,
            prior_control_phase,
        )
        proposal = self.phase_policy_controller.propose_for_phase(control_phase)
        effective = controlled_development_config(self.development.config, proposal)
        application = ThermodynamicControlApplication(
            source_cycle=previous.cycle,
            source_t_g=previous.t_g,
            source_phase=previous.phase,
            control_phase=control_phase,
            policy=proposal,
            effective_config=asdict(effective),
        )
        if effective == self.development.config:
            return self.development, application

        # Reuse the audited component pipelines but substitute a one-cycle
        # immutable config.  No kernel policy object is rewritten.
        return (
            VerdantDevelopmentPipeline(
                workspace=self.development.workspace,
                plasticity=self.development.plasticity,
                structures=self.development.structures,
                config=effective,
            ),
            application,
        )

    def advance(
        self,
        kernel: VerdantKernel,
        command: ExperienceCommand,
    ) -> V5XDevelopmentalCycleResult:
        kernel_id = kernel.state.identity.kernel_id
        development, control = self._controlled_development(kernel_id)
        result = development.advance(kernel, command)

        thermodynamics = None
        if self.enable_thermodynamic_observation and not result.replayed:
            previous = self._last_thermodynamics.get(kernel_id)
            thermodynamics = self.thermodynamic_observer.inspect(
                kernel,
                command,
                candidate_scope_count=len(result.candidate_scope_ids),
                workspace_report=(
                    result.workspace.report if result.workspace is not None else None
                ),
                previous=previous,
            )
            self._last_thermodynamics[kernel_id] = thermodynamics
            if self.enable_thermodynamic_control:
                previous_control = self._control_phases.get(kernel_id)
                self._control_phases[kernel_id] = (
                    self.phase_policy_controller.control_phase(
                        thermodynamics,
                        previous_control,
                    )
                )

        # A replay is a developmental no-op, so do not report a control action
        # as though it had altered a committed cycle.
        if result.replayed:
            control = None

        return V5XDevelopmentalCycleResult(
            development=result,
            thermodynamics=thermodynamics,
            modality=command.modality,
            thermodynamic_control=control,
        )
