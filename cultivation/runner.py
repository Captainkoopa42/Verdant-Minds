"""Main cultivation runner for multi-seed Verdant v2 sessions."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

# TODO: migrate verdant_v2 imports to verdant for V3
from verdant_v2.pipeline.chunk import CognitiveChunk

import numpy as np
from verdant_v2.ethomorphic_config import EthomorphicParams
from verdant_v2.memory.basins import detect_basins
from verdant_v2.memory.interventions import (
    ablate_oldest_emergent_nodes,
    scramble_emergent_edges,
)
from verdant_v2.system import VerdantConfig, VerdantSystem

from cultivation.providers.anthropic import AnthropicProvider
from cultivation.providers.base import Provider
from cultivation.providers.groq import GroqProvider
from cultivation.providers.local import LocalProvider
from cultivation.providers.mistral import MistralProvider
from cultivation.providers.tutor import TutorProvider
from cultivation.schemas import CycleRecord, SessionSummary
from cultivation.strategy.curriculum import CurriculumStrategy
from cultivation.strategy.perturbation import PerturbationEngine


def _basin_telemetry_from_chunk(chunk: CognitiveChunk) -> tuple[int, int, str | None, int, dict[str, int], dict[str, str]]:
    """Extract per-cycle basin telemetry from chunk basins section."""
    section = chunk.get_section_content("basins_section") or {}
    basins = section.get("basins", []) if isinstance(section, dict) else []
    if not isinstance(basins, list):
        return 0, 0, None, 0, {}, {}

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
    emergent_count_by_basin = section.get("emergent_count_by_basin", {}) if isinstance(section, dict) else {}
    basin_membership_snapshot = section.get("basin_membership_snapshot", {}) if isinstance(section, dict) else {}
    ecb = {str(k): int(v) for k, v in emergent_count_by_basin.items()} if isinstance(emergent_count_by_basin, dict) else {}
    bms = {str(k): str(v) for k, v in basin_membership_snapshot.items()} if isinstance(basin_membership_snapshot, dict) else {}
    return basin_count, largest, self_cluster, emergent_basins, ecb, bms


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


def _dynamics_telemetry_from_chunk(chunk: CognitiveChunk) -> dict[str, object]:
    """Extract basin dynamics telemetry from chunk sections."""
    dsec = chunk.get_section_content("basin_dynamics_section") or {}
    if not isinstance(dsec, dict):
        dsec = {}
    return {
        "pruned_edges_count": int(dsec.get("pruned_edges_count", 0)),
        "pruned_basin_id": dsec.get("pruned_basin_id"),
        "basin_density_before": dsec.get("basin_density_before"),
        "basin_density_after": dsec.get("basin_density_after"),
        "bud_events_count": int(dsec.get("bud_events_count", 0)),
        "bud_parent_basin_id": dsec.get("bud_parent_basin_id"),
        "bud_new_basin_id": dsec.get("bud_new_basin_id"),
        "bud_new_basin_size": dsec.get("bud_new_basin_size"),
        "basin_pressure_values": dsec.get("basin_pressure_values", {}),
        "pressure_breakdown": dsec.get("pressure_breakdown", []),
        "boundary_emergents_created": int(dsec.get("boundary_emergents_created", 0)),
        "boundary_pairs": dsec.get("boundary_pairs", []),
        "density_regulation_edges_removed": int(dsec.get("density_regulation_edges_removed", 0)),
        "global_edge_ratio_before": float(dsec.get("global_edge_ratio_before", 0.0)),
        "global_edge_ratio_after": float(dsec.get("global_edge_ratio_after", 0.0)),
        "cycle_time_seconds": float(dsec.get("cycle_time_seconds", 0.0)),
        "graph_nodes": int(dsec.get("graph_nodes", 0)),
        "graph_edges": int(dsec.get("graph_edges", 0)),
        "edges_per_node": float(dsec.get("edges_per_node", 0.0)),
        "bridge_pairs_evaluated": int(dsec.get("bridge_pairs_evaluated", 0)),
        "basin_registry_active": int(dsec.get("basin_registry_active", 0)),
        "basin_registry_dormant": int(dsec.get("basin_registry_dormant", 0)),
        "basin_registry_events": dsec.get("basin_registry_events", []),
    }


def _coherence_telemetry_from_system(system: VerdantSystem) -> dict[str, object | None]:
    """Extract normalized H¹ coherence telemetry from the Verdant system."""
    metrics = system.get_coherence_metrics() if hasattr(system, "get_coherence_metrics") else {}
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "h1_triangle_valid": (
            bool(metrics.get("h1_triangle_valid"))
            if metrics.get("h1_triangle_valid") is not None
            else None
        ),
        "housed_contradiction_index": (
            float(metrics.get("housed_contradiction_index"))
            if metrics.get("housed_contradiction_index") is not None
            else None
        ),
        "violation_rate": (
            float(metrics.get("violation_rate"))
            if metrics.get("violation_rate") is not None
            else None
        ),
        "alpha_critical_estimate": (
            float(metrics.get("alpha_critical_estimate"))
            if metrics.get("alpha_critical_estimate") is not None
            else None
        ),
    }


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for cultivation sessions."""

    cycles: int = 120
    provider: str = "local"
    tutor_backend: str = "groq"
    tutor_model: str | None = None
    tutor_temperature: float = 0.8
    outdir: str = "outputs_v2"
    pressure_every: int = 5
    topic_file: str | None = None
    basin_routing: bool = False
    intervention_mode: str = "none"
    intervention_cycle: int | None = None
    ablation_fraction: float = 0.1
    intervention_target: str = "global"
    intervention_seed: int | None = None
    enable_pruning: bool = False
    enable_budding: bool = False
    enable_boundary_emergence: bool = False
    basin_prune_interval: int = 15
    basin_prune_weight_threshold: float = 0.2
    basin_prune_top_k: int = 12
    basin_bud_interval: int = 20
    basin_pressure_threshold: float = 0.01
    basin_split_fraction: float = 0.15
    basin_min_size_for_split: int = 8
    basin_min_age_for_split: int = 10
    boundary_emergence_threshold: float = 0.5
    boundary_cooldown_cycles: int = 10
    boundary_use_ecwf: bool = True
    density_regulation_enabled: bool = True
    density_max_edge_ratio: float = 80.0
    density_target_edge_ratio: float = 60.0
    basin_use_registry: bool = True
    basin_daughter_protection_cycles: int = 30
    basin_core_overlap_threshold: float = 0.5
    basin_core_stability_cycles: int = 10
    basin_core_absence_tolerance: int = 3
    checkpoint_interval: int = 0
    checkpoint_format: str = "json"
    basin_snapshot_interval: int = 0
    fast_bridge: bool = False
    self_reflect_interval: int = 0
    enable_attention_buffer: bool = False
    ethomorphic_params: EthomorphicParams | None = None


class CultivationRunner:
    """Runs repeatable cultivation cycles and writes seed-scoped artifacts."""

    def __init__(self, config: RunnerConfig) -> None:
        self.config = config
        self.curriculum = CurriculumStrategy(
            pressure_every=config.pressure_every,
            external_topics=self._load_external_topics(config.topic_file),
        )
        self.perturbation = PerturbationEngine()
        self._self_reflection_provider = TutorProvider(backend="local")

    @staticmethod
    def _load_external_topics(topic_file: str | None) -> list[str] | None:
        """Load optional external topics from JSON file."""
        if not topic_file:
            return None
        topic_path = Path(topic_file)
        if not topic_path.exists():
            raise FileNotFoundError(f"Topic file not found: {topic_file}")
        payload = json.loads(topic_path.read_text(encoding="utf-8"))
        topics_source = payload.get("topics", payload) if isinstance(payload, dict) else payload
        if not isinstance(topics_source, list):
            raise ValueError("Topic file JSON must be a list or an object containing a 'topics' list")
        topics = [str(item).strip() for item in topics_source if str(item).strip()]
        return topics or None

    def run(self, seeds: Iterable[int]) -> Path:
        """Execute cultivation for all seeds and return run output directory."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(self.config.outdir) / f"run_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        for seed in seeds:
            self._run_seed(seed=seed, run_dir=run_dir)
        return run_dir

    @staticmethod
    def _concept_metadata_snapshot(system: VerdantSystem, node_id: str) -> dict[str, object]:
        """Capture compact concept identity metadata for snapshot analysis."""
        entry = system.memory_web.get_concept(node_id) or {}
        metadata = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        parents = metadata.get("parent_concepts", [])
        return {
            "node_id": str(node_id),
            "is_emergent": bool(str(node_id).startswith("Emergent_")),
            "stability": float(entry.get("stability", 0.0) or 0.0),
            "access_count": int(entry.get("access_count", 0) or 0),
            "creation_time": float(metadata.get("creation_time", entry.get("first_seen", 0.0)) or 0.0),
            "origin": metadata.get("origin"),
            "parent_concepts": [str(parent) for parent in parents] if isinstance(parents, list) else [],
        }

    @staticmethod
    def _serialize_edges(edges: Iterable[tuple[str, str, object]]) -> list[list[object]]:
        """Normalize graph edges into a stable JSON-friendly representation."""
        payload: list[list[object]] = []
        for source, target, data in edges:
            weight = 1.0
            if isinstance(data, dict):
                try:
                    weight = float(data.get("weight", 1.0))
                except (TypeError, ValueError):
                    weight = 1.0
            a, b = sorted((str(source), str(target)))
            payload.append([a, b, float(weight)])
        payload.sort(key=lambda item: (str(item[0]), str(item[1])))
        return payload

    def _build_basin_snapshot(
        self,
        *,
        system: VerdantSystem,
        cycle_idx: int,
        seed: int,
        timestamp: str,
        phase: str,
        scanned_this_cycle: bool,
    ) -> dict[str, object]:
        """Build a periodic ECWF + concept-graph snapshot for persistence analysis."""
        graph = system.memory_web.graph
        graph_edges = self._serialize_edges(graph.edges(data=True))
        metrics = system.get_metrics()
        ecwf_state = system.ecwf.to_state_dict()
        ecwf_meta = ecwf_state.get("metadata", {})
        ecwf_params = ecwf_state.get("parameters", {})
        amplitude_factors = ecwf_params.get("amplitude_factors", []) if isinstance(ecwf_params, dict) else []
        omega = ecwf_params.get("omega", []) if isinstance(ecwf_params, dict) else []
        phi = ecwf_params.get("phi", []) if isinstance(ecwf_params, dict) else []

        basins_payload: list[dict[str, object]] = []
        for basin in metrics.get("basins", []):
            if not isinstance(basin, dict):
                continue
            nodes = sorted(str(node) for node in basin.get("nodes", []) if isinstance(node, str))
            subgraph = graph.subgraph(nodes)
            basin_edges = self._serialize_edges(subgraph.edges(data=True))
            basins_payload.append(
                {
                    "basin_id": str(basin.get("basin_id")),
                    "size": int(basin.get("size", len(nodes))),
                    "emergent_count": int(basin.get("emergent_count", 0)),
                    "internal_edges": basin_edges,
                    "nodes": nodes,
                    "node_metadata": {
                        node_id: self._concept_metadata_snapshot(system, node_id)
                        for node_id in nodes
                    },
                    "top_nodes_by_access": [
                        [str(node_id), int(access)]
                        for node_id, access in basin.get("top_nodes_by_access", [])[:10]
                        if isinstance(node_id, str)
                    ],
                }
            )

        return {
            "cycle_index": int(cycle_idx),
            "seed": int(seed),
            "timestamp": timestamp,
            "phase": str(phase),
            "t_g": float(metrics.get("t_g", 0.5)),
            "scanned_this_cycle": bool(scanned_this_cycle),
            "ecwf_summary": {
                "num_cognitive_dims": int(ecwf_meta.get("num_cognitive_dims", system.config.cognitive_dims)),
                "num_ethical_dims": int(ecwf_meta.get("num_ethical_dims", system.config.ethical_dims)),
                "num_facets": int(ecwf_meta.get("num_facets", system.config.wave_facets)),
                "adaptive_rate": float(ecwf_meta.get("adaptive_rate", 0.0) or 0.0),
                "feedback_factor": float(ecwf_meta.get("feedback_factor", 0.0) or 0.0),
                "amplitude_mean": float(np.mean(amplitude_factors)) if amplitude_factors else 0.0,
                "amplitude_std": float(np.std(amplitude_factors)) if amplitude_factors else 0.0,
                "omega_mean": float(np.mean(omega)) if omega else 0.0,
                "phi_mean": float(np.mean(phi)) if phi else 0.0,
            },
            "graph_summary": {
                "node_count": int(graph.number_of_nodes()),
                "edge_count": int(graph.number_of_edges()),
                "emergent_count": int(metrics.get("emergent_nodes", 0)),
                "basin_count": int(metrics.get("basin_count", 0)),
            },
            "graph_edges": graph_edges,
            "basins": basins_payload,
        }

    def _write_basin_snapshot(
        self,
        *,
        snapshots_handle,
        system: VerdantSystem,
        cycle_idx: int,
        seed: int,
        timestamp: str,
        phase: str,
        scanned_this_cycle: bool,
        force: bool = False,
    ) -> None:
        """Persist a periodic basin snapshot when configured."""
        interval = int(self.config.basin_snapshot_interval)
        should_write = force or (interval > 0 and (cycle_idx + 1) % interval == 0)
        if snapshots_handle is None or not should_write:
            return
        payload = self._build_basin_snapshot(
            system=system,
            cycle_idx=cycle_idx,
            seed=seed,
            timestamp=timestamp,
            phase=phase,
            scanned_this_cycle=scanned_this_cycle,
        )
        snapshots_handle.write(json.dumps(payload) + "\n")

    def resume(self, checkpoint: str, additional_cycles: int) -> Path:
        """Resume a single-seed run from a saved checkpoint."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = Path(self.config.outdir) / f"run_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = Path(checkpoint)
        system = VerdantSystem.load_checkpoint(str(checkpoint_path))
        seed = int(system.config.seed or 0)
        seed_dir = run_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        provider = self._make_provider()

        py_state = random.getstate()
        np_state = np.random.get_state()
        real_time = time.time
        real_default_rng = np.random.default_rng
        tick = [int(system.get_metrics().get("cycle_count", 0))]
        rng_tick = [int(system.get_metrics().get("cycle_count", 0))]

        def deterministic_time() -> float:
            tick[0] += 1
            return float(seed) * 10_000.0 + tick[0] * 0.01

        def deterministic_default_rng(seed_arg: int | None = None):
            if seed_arg is not None:
                return real_default_rng(seed_arg)
            rng_tick[0] += 1
            return real_default_rng(seed * 10_000 + rng_tick[0])

        try:
            np.random.default_rng = deterministic_default_rng
            time.time = deterministic_time

            cycles_path = seed_dir / "cycles.jsonl"
            snapshots_path = seed_dir / "basin_snapshots.jsonl"
            with cycles_path.open("w", encoding="utf-8") as handle, snapshots_path.open("w", encoding="utf-8") as snapshots_handle:
                for offset in range(additional_cycles):
                    cycle_idx = int(system.get_metrics().get("cycle_count", 0))
                    step = self.curriculum.step(cycle_idx, seed=seed)
                    prompt = self.perturbation.perturb(step.prompt, seed=seed, cycle_index=cycle_idx)
                    input_text, scaffold_context, is_self_reflection = self._generate_cycle_input(
                        provider=provider,
                        prompt=prompt,
                        system=system,
                        seed=seed,
                        cycle_idx=cycle_idx,
                    )
                    chunk = system.process_input(
                        input_text,
                        metadata={
                            "seed": seed,
                            "cycle": cycle_idx,
                            "phase": step.phase,
                            "topic": step.topic,
                            "provider": self.config.provider,
                            "resumed_from": str(checkpoint_path),
                            "is_self_reflection": is_self_reflection,
                        },
                    )
                    metrics = system.get_metrics()
                    wave = chunk.get_section_content("wave_function_section") or {}
                    coherence = _coherence_telemetry_from_system(system)
                    basin_count, largest_basin_size, self_cluster_basin_id, emergent_basins, emergent_count_by_basin, basin_membership_snapshot = _basin_telemetry_from_chunk(chunk)
                    basin_proposals_count, basin_conflict_detected, final_action_source, top_proposal_scores = _proposal_telemetry_from_chunk(chunk)
                    dynamics = _dynamics_telemetry_from_chunk(chunk)
                    timestamp = datetime.now(timezone.utc).isoformat()
                    record = CycleRecord(
                        cycle_index=cycle_idx,
                        seed=seed,
                        timestamp=timestamp,
                        input_text=input_text,
                        phase=step.phase,
                        t_g=float(metrics.get("t_g", 0.5)),
                        entropy=float(wave.get("entropy", 0.0)),
                        hci=float(coherence.get("housed_contradiction_index", 0.0) or 0.0),
                        h1_triangle_valid=(coherence.get("h1_triangle_valid") if coherence.get("h1_triangle_valid") is not None else None),
                        housed_contradiction_index=(
                            float(coherence.get("housed_contradiction_index"))
                            if coherence.get("housed_contradiction_index") is not None
                            else None
                        ),
                        violation_rate=(
                            float(coherence.get("violation_rate"))
                            if coherence.get("violation_rate") is not None
                            else None
                        ),
                        alpha_critical_estimate=(
                            float(coherence.get("alpha_critical_estimate"))
                            if coherence.get("alpha_critical_estimate") is not None
                            else None
                        ),
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
                        intervention_mode=self.config.intervention_mode,
                        intervention_cycle=self.config.intervention_cycle,
                        intervention_target=self.config.intervention_target,
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
                        attention_buffer=dict(metrics.get("attention_buffer", {})),
                        tutor_enabled=False,
                        tutor_input_length=len(input_text),
                        scaffold_context_emergents=(int(scaffold_context.emergent_count) if scaffold_context is not None else 0),
                        scaffold_context_basins=(int(scaffold_context.basin_count) if scaffold_context is not None else 0),
                        is_self_reflection=is_self_reflection,
                        self_reflection_input=(input_text if is_self_reflection else ""),
                        telemetry={
                            "phase_label": metrics.get("phase", "Flexible"),
                            "resume_offset": offset,
                            "is_self_reflection": is_self_reflection,
                        },
                    )
                    handle.write(record.model_dump_json() + "\n")
                    self._write_basin_snapshot(
                        snapshots_handle=snapshots_handle,
                        system=system,
                        cycle_idx=cycle_idx,
                        seed=seed,
                        timestamp=timestamp,
                        phase=step.phase,
                        scanned_this_cycle=bool((chunk.get_section_content("basins_section") or {}).get("scanned_this_cycle", False)),
                        force=(offset == additional_cycles - 1),
                    )
                    if self.config.checkpoint_interval > 0 and (offset + 1) % self.config.checkpoint_interval == 0:
                        system.save_checkpoint(str(seed_dir / f"checkpoint_{cycle_idx + 1}.json"))

            state_path = seed_dir / "state.json"
            system.save_state(str(state_path))
        finally:
            np.random.default_rng = real_default_rng
            time.time = real_time
            random.setstate(py_state)
            np.random.set_state(np_state)
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
        if name == "tutor":
            return TutorProvider(
                backend=self.config.tutor_backend,
                model=self.config.tutor_model,
                temperature=self.config.tutor_temperature,
            )
        raise ValueError(f"Unknown provider: {self.config.provider}")

    def _should_self_reflect(self, cycle_idx: int) -> bool:
        interval = int(self.config.self_reflect_interval)
        cycle_number = cycle_idx + 1
        return interval > 0 and cycle_number > 0 and cycle_number % interval == 0

    def _generate_cycle_input(
        self,
        *,
        provider: Provider,
        prompt: str,
        system: VerdantSystem,
        seed: int,
        cycle_idx: int,
    ) -> tuple[str, object | None, bool]:
        scaffold_context = None
        if hasattr(provider, "set_scaffold_context"):
            scaffold_context = system.get_scaffold_context()
            provider.set_scaffold_context(scaffold_context)

        is_self_reflection = self._should_self_reflect(cycle_idx)
        if is_self_reflection:
            if scaffold_context is None:
                scaffold_context = system.get_scaffold_context()
            self._self_reflection_provider.set_scaffold_context(scaffold_context)
            text = self._self_reflection_provider.generate_self_referential_input(scaffold_context)
            return text, scaffold_context, True

        text = provider.generate(prompt, seed=(seed * 1_000_003 + cycle_idx))
        return text, scaffold_context, False

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
            system = VerdantSystem(VerdantConfig(
                seed=seed,
                initialize_knowledge=True,
                basin_routing=self.config.basin_routing,
                basin_prune_enabled=self.config.enable_pruning,
                basin_prune_interval=self.config.basin_prune_interval,
                basin_prune_weight_threshold=self.config.basin_prune_weight_threshold,
                basin_prune_top_k=self.config.basin_prune_top_k,
                basin_bud_enabled=self.config.enable_budding,
                basin_bud_interval=self.config.basin_bud_interval,
                basin_pressure_threshold=self.config.basin_pressure_threshold,
                basin_split_fraction=self.config.basin_split_fraction,
                basin_min_size_for_split=self.config.basin_min_size_for_split,
                basin_min_age_for_split=self.config.basin_min_age_for_split,
                boundary_emergence_enabled=self.config.enable_boundary_emergence,
                boundary_emergence_threshold=self.config.boundary_emergence_threshold,
                boundary_cooldown_cycles=self.config.boundary_cooldown_cycles,
                boundary_use_ecwf=self.config.boundary_use_ecwf,
                density_regulation_enabled=self.config.density_regulation_enabled,
                density_max_edge_ratio=self.config.density_max_edge_ratio,
                density_target_edge_ratio=self.config.density_target_edge_ratio,
                basin_use_registry=self.config.basin_use_registry,
                basin_daughter_protection_cycles=self.config.basin_daughter_protection_cycles,
                basin_core_overlap_threshold=self.config.basin_core_overlap_threshold,
                basin_core_stability_cycles=self.config.basin_core_stability_cycles,
                basin_core_absence_tolerance=self.config.basin_core_absence_tolerance,
                checkpoint_interval=self.config.checkpoint_interval,
                checkpoint_format=self.config.checkpoint_format,
                fast_bridge=self.config.fast_bridge,
                enable_attention_buffer=self.config.enable_attention_buffer,
                ethomorphic_params=self.config.ethomorphic_params,
            ))
            # Ensure ECWF parameters are seed-deterministic even though upstream default is random_state=None.
            system.ecwf.random_state = seed
            system.ecwf.rng = np.random.RandomState(seed)
            system.ecwf._initialize_parameters()
            if system.ethomorphic_params.initial_amplitude != 1.0:
                system.ecwf.amplitude_factors = (
                    system.ecwf.amplitude_factors * float(system.ethomorphic_params.initial_amplitude)
                )
            system.ecwf.past_states = []

            cycles_path = seed_dir / "cycles.jsonl"
            phase_counts: dict[str, int] = {"pressure": 0, "release": 0}
            entropies: list[float] = []
            hcis: list[float] = []
            pre_intervention_emergent_count = 0
            post_intervention_emergent_count = 0
            pre_intervention_basin_count = 0
            post_intervention_basin_count = 0
            post_intervention_new_emergents = 0
            intervention_done = False

            snapshots_path = seed_dir / "basin_snapshots.jsonl"
            with cycles_path.open("w", encoding="utf-8") as handle, snapshots_path.open("w", encoding="utf-8") as snapshots_handle:
                for cycle_idx in range(self.config.cycles):
                    step = self.curriculum.step(cycle_idx, seed=seed)
                    phase_counts[step.phase] = phase_counts.get(step.phase, 0) + 1

                    prompt = self.perturbation.perturb(step.prompt, seed=seed, cycle_index=cycle_idx)
                    input_text, scaffold_context, is_self_reflection = self._generate_cycle_input(
                        provider=provider,
                        prompt=prompt,
                        system=system,
                        seed=seed,
                        cycle_idx=cycle_idx,
                    )
                    tutor_fallback = bool(getattr(provider, "last_fallback", False))
                    tutor_enabled = self.config.provider.lower() == "tutor"
                    tutor_backend = self.config.tutor_backend if tutor_enabled else None

                    chunk = system.process_input(
                        input_text,
                        metadata={
                            "seed": seed,
                            "cycle": cycle_idx,
                            "phase": step.phase,
                            "topic": step.topic,
                            "provider": self.config.provider,
                            "is_self_reflection": is_self_reflection,
                        },
                    )
                    if cycle_idx % 50 == 0:
                        system.memory_web.prune_connections(max_per_node=50)

                    intervention_applied = False
                    removed_nodes_count = 0
                    removed_ee_edges = 0
                    scrambled_edge_count = 0

                    if (
                        not intervention_done
                        and self.config.intervention_mode != "none"
                        and self.config.intervention_cycle is not None
                        and cycle_idx == self.config.intervention_cycle
                    ):
                        intervention_done = True
                        intervention_applied = True
                        pre_intervention_emergent_count = len(system.memory_web.get_emergent_nodes())
                        pre_intervention_basin_count = len(detect_basins(system.memory_web, k=system.config.basin_scan_k, min_size=system.config.basin_min_size))

                        basin_nodes: set[str] | None = None
                        if self.config.intervention_target == "largest_basin":
                            basins = detect_basins(system.memory_web, k=system.config.basin_scan_k, min_size=system.config.basin_min_size)
                            if basins:
                                basin_nodes = set(basins[0].nodes)

                        if self.config.intervention_mode == "ablate_oldest_nodes":
                            stats = ablate_oldest_emergent_nodes(
                                system.memory_web,
                                fraction=self.config.ablation_fraction,
                                basin_nodes=basin_nodes,
                            )
                            removed_nodes_count = int(stats.get("removed_count", 0))
                            removed_ee_edges = int(stats.get("removed_ee_edges", 0))
                        elif self.config.intervention_mode == "scramble_ee_edges":
                            scramble_seed = self.config.intervention_seed if self.config.intervention_seed is not None else seed
                            stats = scramble_emergent_edges(
                                system.memory_web,
                                rng_seed=int(scramble_seed),
                                basin_nodes=basin_nodes,
                            )
                            scrambled_edge_count = int(stats.get("scrambled_edge_count", 0))

                        post_intervention_emergent_count = len(system.memory_web.get_emergent_nodes())
                        post_intervention_basin_count = len(detect_basins(system.memory_web, k=system.config.basin_scan_k, min_size=system.config.basin_min_size))

                    if intervention_done and self.config.intervention_mode != "none":
                        post_intervention_new_emergents = max(
                            0,
                            len(system.memory_web.get_emergent_nodes()) - post_intervention_emergent_count,
                        )

                    wave = chunk.get_section_content("wave_function_section") or {}
                    coherence = _coherence_telemetry_from_system(system)
                    metrics = system.get_metrics()

                    entropy = float(wave.get("entropy", 0.0))
                    hci = float(coherence.get("housed_contradiction_index", 0.0) or 0.0)
                    entropies.append(entropy)
                    hcis.append(hci)

                    basin_count, largest_basin_size, self_cluster_basin_id, emergent_basins, emergent_count_by_basin, basin_membership_snapshot = _basin_telemetry_from_chunk(chunk)
                    basin_proposals_count, basin_conflict_detected, final_action_source, top_proposal_scores = _proposal_telemetry_from_chunk(chunk)
                    dynamics = _dynamics_telemetry_from_chunk(chunk)
                    timestamp = datetime.now(timezone.utc).isoformat()
                    record = CycleRecord(
                        cycle_index=cycle_idx,
                        seed=seed,
                        timestamp=timestamp,
                        input_text=input_text,
                        phase=step.phase,
                        t_g=float(metrics.get("t_g", 0.5)),
                        entropy=entropy,
                        hci=hci,
                        h1_triangle_valid=(coherence.get("h1_triangle_valid") if coherence.get("h1_triangle_valid") is not None else None),
                        housed_contradiction_index=(
                            float(coherence.get("housed_contradiction_index"))
                            if coherence.get("housed_contradiction_index") is not None
                            else None
                        ),
                        violation_rate=(
                            float(coherence.get("violation_rate"))
                            if coherence.get("violation_rate") is not None
                            else None
                        ),
                        alpha_critical_estimate=(
                            float(coherence.get("alpha_critical_estimate"))
                            if coherence.get("alpha_critical_estimate") is not None
                            else None
                        ),
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
                        intervention_applied=intervention_applied,
                        intervention_mode=self.config.intervention_mode,
                        intervention_cycle=self.config.intervention_cycle,
                        intervention_target=self.config.intervention_target,
                        removed_nodes_count=removed_nodes_count,
                        removed_ee_edges=removed_ee_edges,
                        scrambled_edge_count=scrambled_edge_count,
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
                        attention_buffer=dict(metrics.get("attention_buffer", {})),
                        tutor_enabled=tutor_enabled,
                        tutor_backend=tutor_backend,
                        tutor_fallback=tutor_fallback,
                        tutor_input_length=len(input_text),
                        scaffold_context_emergents=(int(scaffold_context.emergent_count) if scaffold_context is not None else 0),
                        scaffold_context_basins=(int(scaffold_context.basin_count) if scaffold_context is not None else 0),
                        is_self_reflection=is_self_reflection,
                        self_reflection_input=(input_text if is_self_reflection else ""),
                        telemetry={
                            "phase_label": metrics.get("phase", "Flexible"),
                            "edge_classification": metrics.get("edge_classification", {}),
                            "is_self_reflection": is_self_reflection,
                        },
                    )
                    handle.write(record.model_dump_json() + "\n")
                    self._write_basin_snapshot(
                        snapshots_handle=snapshots_handle,
                        system=system,
                        cycle_idx=cycle_idx,
                        seed=seed,
                        timestamp=timestamp,
                        phase=step.phase,
                        scanned_this_cycle=bool((chunk.get_section_content("basins_section") or {}).get("scanned_this_cycle", False)),
                        force=(cycle_idx == self.config.cycles - 1),
                    )
                    if (
                        self.config.checkpoint_interval > 0
                        and (cycle_idx + 1) % self.config.checkpoint_interval == 0
                    ):
                        checkpoint_path = seed_dir / f"checkpoint_{cycle_idx + 1}.json"
                        system.save_checkpoint(str(checkpoint_path))

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
                intervention_mode=self.config.intervention_mode,
                intervention_cycle=self.config.intervention_cycle,
                ablation_fraction=self.config.ablation_fraction,
                intervention_target=self.config.intervention_target,
                pre_intervention_emergent_count=pre_intervention_emergent_count,
                post_intervention_emergent_count=post_intervention_emergent_count,
                post_intervention_new_emergents=post_intervention_new_emergents,
                pre_intervention_basin_count=pre_intervention_basin_count,
                post_intervention_basin_count=post_intervention_basin_count,
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
