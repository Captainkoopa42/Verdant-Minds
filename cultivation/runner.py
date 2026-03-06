"""Main cultivation runner for multi-seed Verdant v2 sessions."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from verdant_v2.pipeline.chunk import CognitiveChunk

import numpy as np
from verdant_v2.system import VerdantConfig, VerdantSystem

from cultivation.providers.anthropic import AnthropicProvider
from cultivation.providers.base import Provider
from cultivation.providers.groq import GroqProvider
from cultivation.providers.local import LocalProvider
from cultivation.providers.mistral import MistralProvider
from cultivation.schemas import CycleRecord, SessionSummary
from cultivation.strategy.curriculum import CurriculumStrategy
from cultivation.strategy.perturbation import PerturbationEngine


def _basin_telemetry_from_chunk(chunk: CognitiveChunk) -> tuple[int, int, str | None, int]:
    """Extract per-cycle basin telemetry from chunk basins section."""
    section = chunk.get_section_content("basins_section") or {}
    basins = section.get("basins", []) if isinstance(section, dict) else []
    if not isinstance(basins, list):
        return 0, 0, None, 0

    basin_count = len(basins)
    largest = 0
    emergent_basins = 0
    self_cluster = None
    for basin in basins:
        if not isinstance(basin, dict):
            continue
        size = int(basin.get("size", 0))
        if size > largest:
            largest = size
        if int(basin.get("emergent_count", 0)) > 0:
            emergent_basins += 1
        nodes = basin.get("nodes", [])
        if self_cluster is None and isinstance(nodes, list) and "selfhood" in nodes:
            self_cluster = str(basin.get("basin_id"))
    return basin_count, largest, self_cluster, emergent_basins


def _proposal_telemetry_from_chunk(chunk: CognitiveChunk) -> tuple[int, bool, str, list[dict[str, float]]]:
    """Extract basin proposal/arbitration telemetry from chunk sections."""
    psec = chunk.get_section_content("basin_proposals_section") or {}
    props = psec.get("proposals", []) if isinstance(psec, dict) else []
    prop_count = len(props) if isinstance(props, list) else 0

    asec = chunk.get_section_content("basin_arbitration_section") or {}
    conflict = bool(asec.get("conflict_detected", False)) if isinstance(asec, dict) else False
    source = str(asec.get("final_action_source", "global_default")) if isinstance(asec, dict) else "global_default"
    top = asec.get("top_proposal_scores", []) if isinstance(asec, dict) else []
    top_list = [x for x in top if isinstance(x, dict)] if isinstance(top, list) else []
    return prop_count, conflict, source, top_list


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for cultivation sessions."""

    cycles: int = 120
    provider: str = "local"
    outdir: str = "outputs_v2"
    pressure_every: int = 5
    basin_routing: bool = False


class CultivationRunner:
    """Runs repeatable cultivation cycles and writes seed-scoped artifacts."""

    def __init__(self, config: RunnerConfig) -> None:
        self.config = config
        self.curriculum = CurriculumStrategy(pressure_every=config.pressure_every)
        self.perturbation = PerturbationEngine()

    def run(self, seeds: Iterable[int]) -> Path:
        """Execute cultivation for all seeds and return run output directory."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(self.config.outdir) / f"run_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        for seed in seeds:
            self._run_seed(seed=seed, run_dir=run_dir)
        return run_dir

    def _make_provider(self) -> Provider:
        name = self.config.provider.lower()
        if name == "local":
            return LocalProvider()
        if name == "anthropic":
            return AnthropicProvider()
        if name == "groq":
            return GroqProvider()
        if name == "mistral":
            return MistralProvider()
        raise ValueError(f"Unknown provider: {self.config.provider}")

    def _run_seed(self, *, seed: int, run_dir: Path) -> None:
        seed_dir = run_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        provider = self._make_provider()

        py_state = random.getstate()
        np_state = np.random.get_state()
        real_time = time.time
        real_default_rng = np.random.default_rng
        tick = [0]
        rng_tick = [0]

        def deterministic_time() -> float:
            tick[0] += 1
            return float(seed) * 10_000.0 + tick[0] * 0.01

        def deterministic_default_rng(seed_arg: int | None = None):
            if seed_arg is not None:
                return real_default_rng(seed_arg)
            rng_tick[0] += 1
            return real_default_rng(seed * 10_000 + rng_tick[0])

        try:
            random.seed(seed)
            np.random.seed(seed)
            np.random.default_rng = deterministic_default_rng
            time.time = deterministic_time
            system = VerdantSystem(VerdantConfig(seed=seed, initialize_knowledge=True, basin_routing=self.config.basin_routing))
            # Ensure ECWF parameters are seed-deterministic even though upstream default is random_state=None.
            system.ecwf.random_state = seed
            system.ecwf.rng = np.random.RandomState(seed)
            system.ecwf._initialize_parameters()
            system.ecwf.past_states = []

            cycles_path = seed_dir / "cycles.jsonl"
            phase_counts: dict[str, int] = {"pressure": 0, "release": 0}
            entropies: list[float] = []
            hcis: list[float] = []

            with cycles_path.open("w", encoding="utf-8") as handle:
                for cycle_idx in range(self.config.cycles):
                    step = self.curriculum.step(cycle_idx, seed=seed)
                    phase_counts[step.phase] = phase_counts.get(step.phase, 0) + 1

                    prompt = self.perturbation.perturb(step.prompt, seed=seed, cycle_index=cycle_idx)
                    input_text = provider.generate(prompt, seed=(seed * 1_000_003 + cycle_idx))

                    chunk = system.process_input(
                        input_text,
                        metadata={
                            "seed": seed,
                            "cycle": cycle_idx,
                            "phase": step.phase,
                            "topic": step.topic,
                            "provider": self.config.provider,
                        },
                    )

                    wave = chunk.get_section_content("wave_function_section") or {}
                    coherence = chunk.get_section_content("coherence_invariants_section") or {}
                    metrics = system.get_metrics()

                    entropy = float(wave.get("entropy", 0.0))
                    hci = float(coherence.get("housed_contradiction_index", 0.0))
                    entropies.append(entropy)
                    hcis.append(hci)

                    basin_count, largest_basin_size, self_cluster_basin_id, emergent_basins = _basin_telemetry_from_chunk(chunk)
                    basin_proposals_count, basin_conflict_detected, final_action_source, top_proposal_scores = _proposal_telemetry_from_chunk(chunk)
                    record = CycleRecord(
                        cycle_index=cycle_idx,
                        seed=seed,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        input_text=input_text,
                        phase=step.phase,
                        t_g=float(metrics.get("t_g", 0.5)),
                        entropy=entropy,
                        hci=hci,
                        emergent_count=int(metrics.get("emergent_nodes", 0)),
                        memory_size=int(metrics.get("memory_concepts", 0)),
                        basin_count=basin_count,
                        largest_basin_size=largest_basin_size,
                        self_cluster_basin_id=self_cluster_basin_id,
                        emergent_basins=emergent_basins,
                        basin_proposals_count=basin_proposals_count,
                        basin_conflict_detected=basin_conflict_detected,
                        final_action_source=final_action_source,
                        top_proposal_scores=top_proposal_scores,
                        telemetry={
                            "phase_label": metrics.get("phase", "Flexible"),
                            "edge_classification": metrics.get("edge_classification", {}),
                        },
                    )
                    handle.write(record.model_dump_json() + "\n")

            state_path = seed_dir / "state.json"
            system.save_state(str(state_path))

            final_metrics = system.get_metrics()
            summary = SessionSummary(
                seed=seed,
                cycles=self.config.cycles,
                provider=self.config.provider,
                phase_counts=phase_counts,
                final_t_g=float(final_metrics.get("t_g", 0.5)),
                final_phase=str(final_metrics.get("phase", "Flexible")),
                avg_entropy=(sum(entropies) / len(entropies) if entropies else 0.0),
                avg_hci=(sum(hcis) / len(hcis) if hcis else 0.0),
                emergent_count=int(final_metrics.get("emergent_nodes", 0)),
                memory_size=int(final_metrics.get("memory_concepts", 0)),
                state_path=str(state_path),
                cycles_path=str(cycles_path),
            )
            (seed_dir / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
        finally:
            np.random.default_rng = real_default_rng
            time.time = real_time
            random.setstate(py_state)
            np.random.set_state(np_state)


def parse_seeds(seed_spec: str) -> list[int]:
    """Parse `0-19` or `0,3,7` style seed specifications."""
    spec = seed_spec.strip()
    if "," in spec:
        return [int(x.strip()) for x in spec.split(",") if x.strip()]
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        start, end = int(lo), int(hi)
        if end < start:
            raise ValueError("Seed range must be ascending (e.g., 0-19).")
        return list(range(start, end + 1))
    return [int(spec)]
