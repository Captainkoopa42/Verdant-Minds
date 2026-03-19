"""Execution support for declarative VCult cultivation specs."""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from verdant_v2.system import VerdantConfig, VerdantSystem

from analysis.spec_validation import compute_earlier_share_from_state_path, run_validation_checks
from cultivation.providers.base import Provider
from cultivation.providers.local import LocalProvider
from cultivation.providers.tutor import TutorProvider
from cultivation.runner import (
    RunnerConfig,
    _basin_telemetry_from_chunk,
    _dynamics_telemetry_from_chunk,
    _proposal_telemetry_from_chunk,
)
from cultivation.schemas import CycleRecord, SessionSummary
from cultivation.spec_parser import CultivationSpec


class SpecRunner:
    """Run a single-seed VCult spec through the existing cultivation system."""

    def __init__(
        self,
        spec: CultivationSpec,
        seed: int = 0,
        provider: str = "local",
        outdir: str = "outputs",
    ) -> None:
        self.spec = spec
        self.seed = int(seed)
        self.provider_name = provider.lower()
        self.outdir = Path(outdir)
        self._self_reflection_provider = TutorProvider(backend="local")

    def run(self) -> Path:
        """Execute the cultivation spec and return the seed output directory."""
        self.outdir.mkdir(parents=True, exist_ok=True)
        provider = self._make_provider()
        config = self._runner_config_from_spec()

        py_state = random.getstate()
        np_state = np.random.get_state()
        real_time = time.time
        real_default_rng = np.random.default_rng
        tick = [0]
        rng_tick = [0]

        def deterministic_time() -> float:
            tick[0] += 1
            return float(self.seed) * 10_000.0 + tick[0] * 0.01

        def deterministic_default_rng(seed_arg: int | None = None):
            if seed_arg is not None:
                return real_default_rng(seed_arg)
            rng_tick[0] += 1
            return real_default_rng(self.seed * 10_000 + rng_tick[0])

        try:
            random.seed(self.seed)
            np.random.seed(self.seed)
            np.random.default_rng = deterministic_default_rng
            time.time = deterministic_time

            system = self._build_system(config)
            self._add_additional_seeds(system)
            self._write_spec_copy()

            cycles_path = self.outdir / "cycles.jsonl"
            phase_log: list[dict[str, Any]] = []
            phase_counts: dict[str, int] = {phase.name: 0 for phase in self.spec.phases}
            entropies: list[float] = []
            hcis: list[float] = []
            global_cycle_idx = 0

            with cycles_path.open("w", encoding="utf-8") as handle:
                for phase in self.spec.phases:
                    phase_entry = {
                        "name": phase.name,
                        "description": phase.description,
                        "cycle_start": global_cycle_idx + 1,
                        "cycle_end": global_cycle_idx + phase.cycles,
                        "topics_used": [],
                        "self_reflection_cycles": [],
                    }
                    topic_pass_counts = {topic: 0 for topic in phase.topics}

                    for phase_cycle in range(1, phase.cycles + 1):
                        cycle_idx = global_cycle_idx
                        phase_counts[phase.name] += 1
                        phase_start = phase_cycle == 1
                        phase_end = phase_cycle == phase.cycles
                        is_self_reflection = (
                            phase.self_reflect_interval > 0 and phase_cycle % phase.self_reflect_interval == 0
                        )
                        topic = phase.topics[(phase_cycle - 1) % len(phase.topics)]

                        scaffold_context = None
                        if hasattr(provider, "set_scaffold_context"):
                            scaffold_context = system.get_scaffold_context()
                            provider.set_scaffold_context(scaffold_context)

                        if is_self_reflection:
                            if scaffold_context is None:
                                scaffold_context = system.get_scaffold_context()
                            self._self_reflection_provider.set_scaffold_context(scaffold_context)
                            input_text = self._self_reflection_provider.generate_self_referential_input(scaffold_context)
                            phase_entry["self_reflection_cycles"].append(cycle_idx + 1)
                        else:
                            topic_pass_counts[topic] += 1
                            input_text = self._generate_topic_input(provider, topic, topic_pass_counts[topic], cycle_idx)
                            phase_entry["topics_used"].append(input_text)

                        chunk = system.process_input(
                            input_text,
                            metadata={
                                "seed": self.seed,
                                "cycle": cycle_idx,
                                "phase": phase.name,
                                "provider": self.provider_name,
                                "is_self_reflection": is_self_reflection,
                                "phase_start": phase_start,
                                "phase_end": phase_end,
                            },
                        )

                        wave = chunk.get_section_content("wave_function_section") or {}
                        coherence = chunk.get_section_content("coherence_invariants_section") or {}
                        metrics = system.get_metrics()
                        entropy = float(wave.get("entropy", 0.0))
                        hci = float(coherence.get("housed_contradiction_index", 0.0))
                        entropies.append(entropy)
                        hcis.append(hci)

                        basin_count, largest_basin_size, self_cluster_basin_id, emergent_basins, emergent_count_by_basin, basin_membership_snapshot = _basin_telemetry_from_chunk(chunk)
                        basin_proposals_count, basin_conflict_detected, final_action_source, top_proposal_scores = _proposal_telemetry_from_chunk(chunk)
                        dynamics = _dynamics_telemetry_from_chunk(chunk)

                        record = CycleRecord(
                            cycle_index=cycle_idx,
                            seed=self.seed,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            input_text=input_text,
                            phase=phase.name,
                            phase_name=phase.name,
                            phase_start=phase_start,
                            phase_end=phase_end,
                            t_g=float(metrics.get("t_g", 0.5)),
                            entropy=entropy,
                            hci=hci,
                            emergent_count=int(metrics.get("emergent_nodes", 0)),
                            memory_size=int(metrics.get("memory_concepts", 0)),
                            basin_count=basin_count,
                            largest_basin_size=largest_basin_size,
                            self_cluster_basin_id=self_cluster_basin_id,
                            emergent_basins=emergent_basins,
                            emergent_count_by_basin=emergent_count_by_basin,
                            basin_membership_snapshot=basin_membership_snapshot,
                            basin_proposals_count=basin_proposals_count,
                            basin_conflict_detected=basin_conflict_detected,
                            final_action_source=final_action_source,
                            top_proposal_scores=top_proposal_scores,
                            intervention_mode="none",
                            pruned_edges_count=int(dynamics["pruned_edges_count"]),
                            pruned_basin_id=(str(dynamics["pruned_basin_id"]) if dynamics["pruned_basin_id"] is not None else None),
                            basin_density_before=(float(dynamics["basin_density_before"]) if dynamics["basin_density_before"] is not None else None),
                            basin_density_after=(float(dynamics["basin_density_after"]) if dynamics["basin_density_after"] is not None else None),
                            bud_events_count=int(dynamics["bud_events_count"]),
                            bud_parent_basin_id=(str(dynamics["bud_parent_basin_id"]) if dynamics["bud_parent_basin_id"] is not None else None),
                            bud_new_basin_id=(str(dynamics["bud_new_basin_id"]) if dynamics["bud_new_basin_id"] is not None else None),
                            bud_new_basin_size=(int(dynamics["bud_new_basin_size"]) if dynamics["bud_new_basin_size"] is not None else None),
                            basin_pressure_values={str(k): float(v) for k, v in dict(dynamics["basin_pressure_values"]).items()},
                            pressure_breakdown=[dict(x) for x in list(dynamics["pressure_breakdown"])],
                            boundary_emergents_created=int(dynamics["boundary_emergents_created"]),
                            boundary_pairs=[[str(x) for x in pair] for pair in list(dynamics["boundary_pairs"])],
                            density_regulation_edges_removed=int(dynamics["density_regulation_edges_removed"]),
                            global_edge_ratio_before=float(dynamics["global_edge_ratio_before"]),
                            global_edge_ratio_after=float(dynamics["global_edge_ratio_after"]),
                            cycle_time_seconds=float(dynamics["cycle_time_seconds"]),
                            graph_nodes=int(dynamics["graph_nodes"]),
                            graph_edges=int(dynamics["graph_edges"]),
                            edges_per_node=float(dynamics["edges_per_node"]),
                            bridge_pairs_evaluated=int(dynamics["bridge_pairs_evaluated"]),
                            basin_registry_active=int(dynamics["basin_registry_active"]),
                            basin_registry_dormant=int(dynamics["basin_registry_dormant"]),
                            basin_registry_events=[dict(x) for x in list(dynamics["basin_registry_events"])],
                            tutor_enabled=self.provider_name == "tutor",
                            tutor_backend=(self.provider_name if self.provider_name == "tutor" else None),
                            tutor_fallback=bool(getattr(provider, "last_fallback", False)),
                            tutor_input_length=len(input_text),
                            scaffold_context_emergents=(int(scaffold_context.emergent_count) if scaffold_context is not None else 0),
                            scaffold_context_basins=(int(scaffold_context.basin_count) if scaffold_context is not None else 0),
                            is_self_reflection=is_self_reflection,
                            self_reflection_input=(input_text if is_self_reflection else ""),
                            telemetry={
                                "phase_label": metrics.get("phase", "Flexible"),
                                "is_self_reflection": is_self_reflection,
                                "phase_name": phase.name,
                                "phase_start": phase_start,
                                "phase_end": phase_end,
                            },
                        )
                        handle.write(record.model_dump_json() + "\n")

                        if config.checkpoint_interval > 0 and (cycle_idx + 1) % config.checkpoint_interval == 0:
                            system.save_checkpoint(str(self.outdir / f"checkpoint_{cycle_idx + 1}.json"))
                        global_cycle_idx += 1

                    phase_log.append(phase_entry)

            state_path = self.outdir / "state.json"
            system.save_state(str(state_path))

            final_metrics = system.get_metrics()
            summary = SessionSummary(
                seed=self.seed,
                cycles=self.spec.total_cycles,
                provider=self.provider_name,
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
            (self.outdir / "summary.json").write_text(summary.model_dump_json(indent=2), encoding="utf-8")
            (self.outdir / "phase_log.json").write_text(json.dumps({"spec_name": self.spec.name, "phases": phase_log}, indent=2), encoding="utf-8")

            earlier_share = compute_earlier_share_from_state_path(state_path)
            validation = run_validation_checks(
                state_path=state_path,
                expectations=self.spec.validation,
                actual_metrics={
                    "earlier_share": earlier_share,
                    "emergent_count": int(final_metrics.get("emergent_nodes", 0)),
                    "basin_count": int(final_metrics.get("basin_count", 0)),
                },
            )
            (self.outdir / "validation_results.json").write_text(json.dumps(validation, indent=2), encoding="utf-8")
            for check_name, result in validation.get("checks", {}).items():
                if not result.get("passed", False):
                    print(f"WARNING: validation check failed for {check_name}: expected {result.get('expected')} got {result.get('actual')}")

            return self.outdir
        finally:
            np.random.default_rng = real_default_rng
            time.time = real_time
            random.setstate(py_state)
            np.random.set_state(np_state)

    def _make_provider(self) -> Provider:
        if self.provider_name == "local":
            return LocalProvider()
        if self.provider_name == "tutor":
            return TutorProvider(backend="local")
        raise ValueError(f"Unsupported provider for spec cultivation: {self.provider_name}")

    def _runner_config_from_spec(self) -> RunnerConfig:
        settings = dict(self.spec.settings)
        enable_all = bool(settings.pop("enable_all_dynamics", False))
        if enable_all:
            settings.setdefault("enable_pruning", True)
            settings.setdefault("enable_budding", True)
            settings.setdefault("enable_boundary_emergence", True)
        if "bud_pressure_threshold" in settings:
            settings["basin_pressure_threshold"] = settings.pop("bud_pressure_threshold")
        if "density_regulation" in settings:
            settings["density_regulation_enabled"] = settings.pop("density_regulation")
        allowed = set(RunnerConfig.__dataclass_fields__.keys()) - {"cycles", "provider", "outdir", "self_reflect_interval"}
        filtered = {key: value for key, value in settings.items() if key in allowed}
        return RunnerConfig(cycles=self.spec.total_cycles, provider=self.provider_name, outdir=str(self.outdir), **filtered)

    def _build_system(self, config: RunnerConfig) -> VerdantSystem:
        system = VerdantSystem(VerdantConfig(
            seed=self.seed,
            initialize_knowledge=True,
            basin_routing=config.basin_routing,
            basin_prune_enabled=config.enable_pruning,
            basin_prune_interval=config.basin_prune_interval,
            basin_prune_weight_threshold=config.basin_prune_weight_threshold,
            basin_prune_top_k=config.basin_prune_top_k,
            basin_bud_enabled=config.enable_budding,
            basin_bud_interval=config.basin_bud_interval,
            basin_pressure_threshold=config.basin_pressure_threshold,
            basin_split_fraction=config.basin_split_fraction,
            basin_min_size_for_split=config.basin_min_size_for_split,
            basin_min_age_for_split=config.basin_min_age_for_split,
            boundary_emergence_enabled=config.enable_boundary_emergence,
            boundary_emergence_threshold=config.boundary_emergence_threshold,
            boundary_cooldown_cycles=config.boundary_cooldown_cycles,
            boundary_use_ecwf=config.boundary_use_ecwf,
            density_regulation_enabled=config.density_regulation_enabled,
            density_max_edge_ratio=config.density_max_edge_ratio,
            density_target_edge_ratio=config.density_target_edge_ratio,
            basin_use_registry=config.basin_use_registry,
            basin_daughter_protection_cycles=config.basin_daughter_protection_cycles,
            basin_core_overlap_threshold=config.basin_core_overlap_threshold,
            basin_core_stability_cycles=config.basin_core_stability_cycles,
            basin_core_absence_tolerance=config.basin_core_absence_tolerance,
            checkpoint_interval=config.checkpoint_interval,
            checkpoint_format=config.checkpoint_format,
            fast_bridge=config.fast_bridge,
            ethomorphic_params=config.ethomorphic_params,
        ))
        system.ecwf.random_state = self.seed
        system.ecwf.rng = np.random.RandomState(self.seed)
        system.ecwf._initialize_parameters()
        if system.ethomorphic_params.initial_amplitude != 1.0:
            system.ecwf.amplitude_factors = system.ecwf.amplitude_factors * float(system.ethomorphic_params.initial_amplitude)
        system.ecwf.past_states = []
        return system

    def _add_additional_seeds(self, system: VerdantSystem) -> None:
        for label in self.spec.additional_seeds:
            system.memory_web.add_concept(
                label,
                stability=0.55,
                metadata={
                    "origin": "vcult_spec",
                    "creation_time": time.time(),
                    "spec_name": self.spec.name,
                },
            )
        if self.spec.additional_seeds:
            system.bridge.initialize_concept_mappings()

    def _generate_topic_input(self, provider: Provider, topic: str, topic_pass_index: int, cycle_idx: int) -> str:
        from cultivation.providers.topic_variation import vary_topic_for_pass

        varied_topic = vary_topic_for_pass(topic, topic_pass_index)
        if self.provider_name == "local":
            return varied_topic
        return provider.generate(varied_topic, seed=(self.seed * 1_000_003 + cycle_idx))

    def _write_spec_copy(self) -> None:
        payload = {
            "name": self.spec.name,
            "description": self.spec.description,
            **({"seeds": {"additional": self.spec.additional_seeds}} if self.spec.additional_seeds else {}),
            **({"settings": self.spec.settings} if self.spec.settings else {}),
            "phases": [asdict(phase) for phase in self.spec.phases],
            **({"validation": self.spec.validation} if self.spec.validation else {}),
        }
        (self.outdir / "spec.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
