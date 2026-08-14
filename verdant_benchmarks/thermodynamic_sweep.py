from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from itertools import product

from verdant_development.v5x import V5XDevelopmentPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    VerdantKernel,
)
from verdant_thermodynamics import ThermodynamicPhase, compute_t_g


@dataclass(frozen=True)
class ThermodynamicSweepSummary:
    schema_id: str
    seed: int
    state_dim: int
    formula_revision: str
    formula_grid: dict
    runtime_states: tuple[dict, ...]
    observer_null_equivalence: bool
    governance_tg_unchanged: bool
    observed_phase_labels: tuple[str, ...]
    interpretation: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


class ThermodynamicSweepHarness:
    """EU01/T0 measurement-only characterization of the recovered V4 law."""

    def __init__(self, *, seed: int = 1901, state_dim: int = 32) -> None:
        self.seed = int(seed)
        self.state_dim = int(state_dim)

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _commands(self) -> tuple[ExperienceCommand, ...]:
        short = ExperienceCommand(
            event_key="t0:short",
            source_ref="v5x:t0",
            modality="text",
            payload_sha256=self._digest("t0:short"),
            feature_vector=(1.0, 0.0, 0.0),
            concept_labels=("quiet",),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            metadata={"sentence": "quiet signal", "t0_scenario": "short_input"},
        )
        labels = tuple(f"dense_{index}" for index in range(10))
        long_sentence = " ".join(f"token{index}" for index in range(100))
        dense = ExperienceCommand(
            event_key="t0:dense",
            source_ref="v5x:t0",
            modality="text",
            payload_sha256=self._digest("t0:dense"),
            feature_vector=(0.0, 1.0, 0.0),
            concept_labels=labels,
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            metadata={"sentence": long_sentence, "t0_scenario": "high_input_and_workspace_load"},
        )
        positive_claim = ClaimProposal(
            subject_label="indicator",
            predicate="has_property",
            object_label="bright",
            polarity=ClaimPolarity.AFFIRMED,
            source_class=ClaimSourceClass.DIRECT_OBSERVATION,
            confidence=1.0,
        )
        negative_claim = positive_claim.model_copy(update={"polarity": ClaimPolarity.NEGATED})
        positive = ExperienceCommand(
            event_key="t0:claim-positive",
            source_ref="v5x:t0",
            modality="text",
            payload_sha256=self._digest("t0:claim-positive"),
            feature_vector=(0.0, 0.0, 1.0),
            claim_proposals=(positive_claim,),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.OBSERVATION,
            metadata={"sentence": "indicator is bright", "t0_scenario": "claim_baseline"},
        )
        negative = ExperienceCommand(
            event_key="t0:claim-negative",
            source_ref="v5x:t0",
            modality="text",
            payload_sha256=self._digest("t0:claim-negative"),
            feature_vector=(0.0, 0.0, 1.0),
            claim_proposals=(negative_claim,),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.OBSERVATION,
            metadata={"sentence": "indicator is not bright", "t0_scenario": "contradiction_pressure"},
        )
        return short, dense, positive, negative

    @staticmethod
    def _formula_grid() -> dict:
        axes = {
            "c_input": (0.0, 0.25, 0.5, 0.75, 1.0),
            "c_memory": (0.0, 0.5, 1.0),
            "h_env": (0.0, 0.5, 1.0),
            "h_sys": (0.0, 0.5, 1.0),
        }
        rows = []
        counts = {phase.value: 0 for phase in ThermodynamicPhase}
        minimum = 1.0
        maximum = 0.0
        for c_input, c_memory, h_env, h_sys in product(*axes.values()):
            t_g, complexity, base, feedback = compute_t_g(c_input, c_memory, h_env, h_sys)
            if t_g < 0.4:
                phase = ThermodynamicPhase.RIGID
            elif t_g <= 0.6:
                phase = ThermodynamicPhase.FLEXIBLE
            else:
                phase = ThermodynamicPhase.CHAOTIC
            counts[phase.value] += 1
            minimum = min(minimum, t_g)
            maximum = max(maximum, t_g)
            rows.append({
                "c_input": c_input,
                "c_memory": c_memory,
                "h_env": h_env,
                "h_sys": h_sys,
                "computational_complexity": complexity,
                "base_term": base,
                "entropy_feedback": feedback,
                "t_g": t_g,
                "phase": phase.value,
            })
        return {
            "axes": axes,
            "row_count": len(rows),
            "phase_counts": counts,
            "minimum_t_g": minimum,
            "maximum_t_g": maximum,
            "all_phase_regions_reachable": all(value > 0 for value in counts.values()),
            "rows": rows,
        }

    def run(self) -> ThermodynamicSweepSummary:
        commands = self._commands()
        enabled = VerdantKernel(seed=self.seed, state_dim=self.state_dim, run_label="v5x-t0")
        disabled = VerdantKernel(seed=self.seed, state_dim=self.state_dim, run_label="v5x-t0")
        observer = V5XDevelopmentPipeline(enable_thermodynamic_observation=True)
        null = V5XDevelopmentPipeline(enable_thermodynamic_observation=False)
        governance_tg_start = enabled.state.governance.t_g
        runtime_states: list[dict] = []
        for command in commands:
            measured = observer.advance(enabled, command)
            null.advance(disabled, command)
            if measured.thermodynamics is None:
                raise RuntimeError("T0 observer failed to emit thermodynamic state.")
            runtime_states.append(measured.thermodynamics.model_dump(mode="json"))
        null_equivalence = enabled.snapshot() == disabled.snapshot()
        governance_tg_unchanged = enabled.state.governance.t_g == governance_tg_start
        labels = tuple(sorted({item["phase"] for item in runtime_states}))
        grid = self._formula_grid()
        return ThermodynamicSweepSummary(
            schema_id="verdant.thermodynamic_sweep.v1",
            seed=self.seed,
            state_dim=self.state_dim,
            formula_revision="tg_v4_compat_1",
            formula_grid=grid,
            runtime_states=tuple(runtime_states),
            observer_null_equivalence=null_equivalence,
            governance_tg_unchanged=governance_tg_unchanged,
            observed_phase_labels=labels,
            interpretation={
                "measurement": "T_g and T_cog are dimensionless implementation telemetry recovered from the V4 control law.",
                "authority": "EU01/T0 does not feed these values back into workspace, plasticity, governance, or language policy.",
                "fce": "Fractal Cognitive Entropy is not defined or claimed by this harness.",
            },
        )
