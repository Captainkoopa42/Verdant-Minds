from __future__ import annotations

from verdant_kernel import ExperienceCommand, VerdantKernel, WorkspaceAdmissionReport

from .metrics import environmental_uncertainty, field_entropy, input_complexity, memory_complexity
from .models import ThermodynamicState
from .phase import FORMULA_REVISION, classify_phase, cognitive_temperature, compute_t_g


class VerdantThermodynamicObserver:
    """Pure, measurement-only observer for one committed developmental cycle."""

    formula_revision = FORMULA_REVISION

    def inspect(
        self,
        kernel: VerdantKernel,
        command: ExperienceCommand,
        *,
        candidate_scope_count: int,
        workspace_report: WorkspaceAdmissionReport | None,
        previous: ThermodynamicState | None = None,
    ) -> ThermodynamicState:
        field = field_entropy(kernel)
        input_measurement = input_complexity(command)
        memory = memory_complexity(kernel, candidate_scope_count=candidate_scope_count)
        environment = environmental_uncertainty(workspace_report)
        t_g, complexity, base, feedback = compute_t_g(
            input_measurement.c_input,
            memory.c_memory,
            environment.h_env,
            field.h_sys,
        )
        phase = classify_phase(t_g)
        previous_phase = previous.phase if previous is not None else None
        return ThermodynamicState(
            formula_revision=self.formula_revision,
            cycle=kernel.state.cycle,
            event_key=command.event_key,
            modality=command.modality,
            h_sys=field.h_sys,
            c_input=input_measurement.c_input,
            c_memory=memory.c_memory,
            h_env=environment.h_env,
            computational_complexity=complexity,
            base_term=base,
            entropy_feedback=feedback,
            t_g=t_g,
            phase=phase,
            t_cog=cognitive_temperature(t_g, field.h_sys),
            previous_phase=previous_phase,
            phase_transition=(previous_phase is not None and previous_phase != phase),
            field=field,
            input=input_measurement,
            memory=memory,
            environment=environment,
            metadata={
                "behavioral_authority": False,
                "interpretation": "dimensionless implementation telemetry",
            },
        )
