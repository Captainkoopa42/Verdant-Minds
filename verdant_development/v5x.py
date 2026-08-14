from __future__ import annotations

from dataclasses import dataclass

from verdant_kernel import ExperienceCommand, VerdantKernel
from verdant_thermodynamics import ThermodynamicState, VerdantThermodynamicObserver

from .pipeline import DevelopmentalCycleResult, VerdantDevelopmentPipeline


@dataclass(frozen=True)
class V5XDevelopmentalCycleResult:
    """Observation-enriched view of an otherwise canonical V5 heartbeat.

    The wrapped V5 result remains the authority for cognitive state. EU01
    thermodynamic state is external telemetry and is never written into the
    kernel by this wrapper.
    """

    development: DevelopmentalCycleResult
    thermodynamics: ThermodynamicState | None
    modality: str

    def __getattr__(self, name: str):
        return getattr(self.development, name)


class V5XDevelopmentPipeline:
    """V5-X opt-in wrapper around the byte-identical V5 developmental path."""

    def __init__(
        self,
        development: VerdantDevelopmentPipeline | None = None,
        *,
        thermodynamic_observer: VerdantThermodynamicObserver | None = None,
        enable_thermodynamic_observation: bool = True,
    ) -> None:
        self.development = development or VerdantDevelopmentPipeline()
        self.thermodynamic_observer = thermodynamic_observer or VerdantThermodynamicObserver()
        self.enable_thermodynamic_observation = bool(enable_thermodynamic_observation)
        self._last_thermodynamics: dict[str, ThermodynamicState] = {}

    def advance(
        self,
        kernel: VerdantKernel,
        command: ExperienceCommand,
    ) -> V5XDevelopmentalCycleResult:
        result = self.development.advance(kernel, command)
        thermodynamics = None
        if self.enable_thermodynamic_observation and not result.replayed:
            previous = self._last_thermodynamics.get(kernel.state.identity.kernel_id)
            thermodynamics = self.thermodynamic_observer.inspect(
                kernel,
                command,
                candidate_scope_count=len(result.candidate_scope_ids),
                workspace_report=(result.workspace.report if result.workspace is not None else None),
                previous=previous,
            )
            self._last_thermodynamics[kernel.state.identity.kernel_id] = thermodynamics
        return V5XDevelopmentalCycleResult(
            development=result,
            thermodynamics=thermodynamics,
            modality=command.modality,
        )
