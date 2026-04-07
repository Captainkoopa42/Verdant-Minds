"""VerdantSystem — top-level orchestrator for the Verdant v2 cognitive architecture.

Wires together:
- ethomorphic ECWFCore + EthomorphicBridge
- MemoryWeb
- Nine-block pipeline
- Three Kings governance
- Coherence invariants
- Thermodynamic phase management
"""

from __future__ import annotations

import time
from dataclasses import asdict
import json
import math
from typing import Any, Dict, List, Optional

from verdant.adapters.base import Adapter, InputEvent

import numpy as np
from pydantic import BaseModel, Field

from verdant.attention import AttentionBuffer, AttentionItem
from ethomorphic.bridge.bridge import EthomorphicBridge
from ethomorphic.bridge.emergence import (
    assign_emergent_concept_mappings,
    link_emergent_to_existing_emergents,
)
from ethomorphic.coherence.invariants import compute_coherence
from ethomorphic.ecwf.core import ECWFCore

# TODO: migrate verdant_v2 imports to verdant for V3
from verdant_v2.ethomorphic_config import (
    EthomorphicParams,
    apply_ecwf_params,
    configure_bridge_runtime,
    resolve_ethomorphic_params,
)
from verdant_v2.governance.council import ThreeKingsCouncil
from verdant_v2.governance.data_king import DataKing
from verdant_v2.governance.ethics_king import EthicsKing
from verdant_v2.governance.forefront_king import ForefrontKing
from verdant_v2.memory.basins import BasinInfo, detect_basins
from verdant_v2.memory.basin_dynamics import (
    BoundaryCandidate,
    PressureBreakdown,
    find_ejection_candidates,
    maybe_bud_basin,
    maybe_create_boundary_emergents,
    maybe_propose_boundary_candidates,
    compute_basin_pressure,
    prune_basin_edges,
    regulate_density,
)
from verdant_v2.memory.bridge_acceleration import (
    get_fast_bridge_state,
    restore_fast_bridge_state,
    set_fast_bridge_enabled,
)
from verdant_v2.memory.basin_registry import BasinRegistry
from verdant_v2.memory.basin_state import BasinState
from verdant_v2.memory.graph import MemoryWeb
from verdant_v2.pipeline.blocks.action import ActionBlock
from verdant_v2.pipeline.blocks.communication import CommunicationBlock
from verdant_v2.pipeline.blocks.ethics import EthicsBlock
from verdant_v2.pipeline.blocks.language import LanguageBlock
from verdant_v2.pipeline.blocks.learning import LearningBlock
from verdant_v2.pipeline.blocks.memory import MemoryBlock
from verdant_v2.pipeline.blocks.pattern import PatternRecognitionBlock
from verdant_v2.pipeline.blocks.reasoning import ReasoningBlock
from verdant_v2.pipeline.blocks.sensory import SensoryInputBlock
from verdant_v2.pipeline.chunk import CognitiveChunk
from verdant_v2.pipeline.orchestrator import PipelineOrchestrator
from verdant_v2.thermodynamics.phase import compute_phase, compute_t_g

_ATTENTION_STOPWORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "about", "it",
    "this", "that", "and", "or", "but", "if", "not", "no", "so", "than",
    "too", "very", "just", "i", "me", "my", "we", "our", "you", "your",
    "he", "she", "they", "them", "its",
}


class VerdantConfig(BaseModel):
    """Configuration for the Verdant v2 system."""

    cognitive_dims: int = 5
    ethical_dims: int = 5
    wave_facets: int = 7
    bridge_influence_factor: float = 0.3
    learning_rate: float = 0.05
    decision_threshold: float = 0.7
    ethical_sensitivity: float = 0.6
    initialize_knowledge: bool = True
    seed: int | None = 42
    basin_scan_interval: int = 10
    basin_scan_k: int = 6
    basin_min_size: int = 5
    basin_routing: bool = False
    basin_top_m: int = 2
    basin_prune_enabled: bool = False
    basin_prune_interval: int = 15
    basin_prune_weight_threshold: float = 0.2
    basin_prune_top_k: int = 12
    basin_bud_enabled: bool = False
    basin_bud_interval: int = 20
    basin_pressure_threshold: float = 0.01
    basin_split_fraction: float = 0.15
    basin_min_size_for_split: int = 8
    basin_min_age_for_split: int = 10
    boundary_emergence_enabled: bool = False
    boundary_emergence_threshold: float = 0.5
    boundary_cooldown_cycles: int = 10
    boundary_use_ecwf: bool = True
    density_regulation_enabled: bool = True
    density_max_edge_ratio: float = 80.0
    density_target_edge_ratio: float = 60.0
    emit_basin_membership: bool = True
    basin_use_registry: bool = True
    basin_daughter_protection_cycles: int = 30
    basin_core_overlap_threshold: float = 0.5
    basin_core_stability_cycles: int = 10
    basin_core_absence_tolerance: int = 3
    checkpoint_interval: int = 0
    checkpoint_format: str = "json"
    fast_bridge: bool = False
    concept_min_length: int = 3
    filter_numeric_concepts: bool = True
    enable_attention_buffer: bool = False
    ethomorphic_params: EthomorphicParams | None = None


class VerdantSystem:
    """Top-level orchestrator for the Verdant v2 cognitive architecture.

    Manages the full processing pipeline from raw text input to enriched
    CognitiveChunk output, including wave-function processing, memory
    management, governance oversight, and thermodynamic phase control.
    """

    def __init__(self, config: Optional[VerdantConfig] = None) -> None:
        self.config = config or VerdantConfig()
        self.ethomorphic_params = resolve_ethomorphic_params(
            self.config.ethomorphic_params,
            cognitive_dims=self.config.cognitive_dims,
            ethical_dims=self.config.ethical_dims,
            wave_facets=self.config.wave_facets,
        )
        self.config.cognitive_dims = self.ethomorphic_params.num_cognitive_dims
        self.config.ethical_dims = self.ethomorphic_params.num_ethical_dims
        self.config.wave_facets = self.ethomorphic_params.num_facets

        if self.config.seed is not None:
            np.random.seed(self.config.seed)

        # Core components
        self.ecwf = apply_ecwf_params(
            random_state=self.config.seed,
            params=self.ethomorphic_params,
        )
        self.memory_web = MemoryWeb()
        self.bridge = EthomorphicBridge(
            ecwf=self.ecwf,
            memory=self.memory_web,
            influence_factor=self.config.bridge_influence_factor,
        )
        restore_fast_bridge_state(self.bridge, None)
        configure_bridge_runtime(self.bridge, self.ethomorphic_params)

        # Pipeline blocks
        self._sensory = SensoryInputBlock()
        self._pattern = PatternRecognitionBlock()
        seeded_concepts = {label for label, *_ in _SEEDED_CONCEPTS}
        self._memory_block = MemoryBlock(
            self.memory_web,
            self.bridge,
            concept_min_length=self.config.concept_min_length,
            filter_numeric_concepts=self.config.filter_numeric_concepts,
            seeded_concepts=seeded_concepts,
        )
        self._communication = CommunicationBlock()
        self._reasoning = ReasoningBlock()
        self._ethics = EthicsBlock()
        self._action = ActionBlock(decision_threshold=self.config.decision_threshold)
        self._language = LanguageBlock()
        self._learning = LearningBlock(bridge=self.bridge)
        self.attention_buffer = AttentionBuffer(bypass=not self.config.enable_attention_buffer)

        # Governance
        self.data_king = DataKing()
        self.forefront_king = ForefrontKing(decision_threshold=self.config.decision_threshold)
        self.ethics_king = EthicsKing(ethical_sensitivity=self.config.ethical_sensitivity)
        self.council = ThreeKingsCouncil(
            data_king=self.data_king,
            forefront_king=self.forefront_king,
            ethics_king=self.ethics_king,
        )

        # Orchestrator
        self.pipeline = PipelineOrchestrator(
            blocks=[
                self._sensory,
                self._pattern,
                self._memory_block,
                self._communication,
                self._reasoning,
                self._ethics,
                self._action,
                self._language,
                self._learning,
            ],
            data_king_hook=self.data_king,
            ethics_king_hook=self.ethics_king,
            forefront_king_hook=self.forefront_king,
            three_kings_hook=self.council,
            memory_web=self.memory_web,
            basin_routing=self.config.basin_routing,
            basin_top_m=self.config.basin_top_m,
            basin_scan_k=self.config.basin_scan_k,
            bridge=self.bridge,
        )

        # System state
        self._t_g: float = 0.5
        self._cycle_count: int = 0
        self._entropy_history: List[float] = []
        self._metrics: Dict[str, Any] = {
            "total_cycles": 0,
            "avg_entropy": 0.0,
            "avg_coherence": 0.0,
            "emergent_concepts": 0,
            "phase_transitions": 0,
            "start_time": time.time(),
        }
        self._last_phase: str = "Flexible"
        self._last_basins: List[BasinInfo] = []
        self._basin_states: Dict[str, BasinState] = {}
        self._next_basin_id: int = 0
        self._basin_registry = BasinRegistry(
            daughter_protection_cycles=self.config.basin_daughter_protection_cycles,
            core_stability_cycles=self.config.basin_core_stability_cycles,
            core_absence_tolerance=self.config.basin_core_absence_tolerance,
        )
        self._last_boundary_cycles: Dict[frozenset[str], int] = {}
        self._dynamics_metrics: Dict[str, Any] = {}
        self._last_coherence_metrics: Dict[str, Any] = {
            "h1_triangle_valid": None,
            "housed_contradiction_index": None,
            "violation_rate": None,
            "alpha_critical_estimate": None,
        }
        self.adapters: List[Adapter] = []

        # Knowledge initialization
        if self.config.initialize_knowledge:
            self.initialize_knowledge()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_adapter(self, adapter: Adapter) -> None:
        """Register an input adapter."""
        self.adapters.append(adapter)

    def collect_inputs(self) -> List[InputEvent]:
        """Collect pending input events from all registered adapters."""
        events: List[InputEvent] = []
        for adapter in self.adapters:
            events.extend(adapter.poll())
        return events

    def process_input(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> CognitiveChunk:
        """Process input through the attention buffer and full pipeline."""
        t_g = self._current_t_g()
        self.attention_buffer.update_governance(t_g)

        known_concepts, unknown_words = self._quick_extract_concepts(text)
        novelty = self._compute_novelty(text)
        concepts = known_concepts + unknown_words
        activation = self._compute_input_activation(concepts, novelty)
        item = AttentionItem(
            concepts=concepts,
            activation=activation,
            source_text=text,
            novelty=novelty,
            cycle=self._cycle_count,
        )
        self.attention_buffer.add(item)
        escalated = self.attention_buffer.evaluate()

        chunks: list[CognitiveChunk] = []
        for esc_item in escalated:
            chunks.append(self._full_pipeline_process(esc_item.source_text, metadata))

        for remaining in self.attention_buffer.items:
            self._light_process(remaining)

        return chunks[-1] if chunks else self._null_chunk(text=text, metadata=metadata)

    def _full_pipeline_process(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> CognitiveChunk:
        """Process raw text through the full pipeline."""
        cycle_wall_start = time.perf_counter()
        chunk = CognitiveChunk()
        chunk.update_section("sensory_input_section", {
            "input_text": text,
            "metadata": metadata or {},
        })

        # Inject current T_g
        chunk.update_section("processing_metrics_section", {
            "glass_transition_temp": self._t_g,
            "cycle": self._cycle_count,
        })

        set_fast_bridge_enabled(
            self.bridge,
            bool(self.config.fast_bridge or self._cycle_count >= 200),
        )

        # Run pipeline
        chunk = self.pipeline.run(chunk)

        # Compute coherence invariants
        chunk = self._compute_coherence(chunk)

        # Update T_g
        self._update_t_g(chunk)

        # Track metrics
        self._cycle_count += 1
        self._update_metrics(chunk)

        # Basin scans (analysis-first telemetry)
        scan_interval = self._compute_basin_scan_interval()
        should_scan = (self._cycle_count % max(1, scan_interval) == 0)
        if should_scan:
            detected = detect_basins(
                self.memory_web,
                k=self.config.basin_scan_k,
                min_size=self.config.basin_min_size,
            )
            if self.config.basin_use_registry:
                communities = [set(b.nodes) for b in detected]
                self._last_basins = self._basin_registry.update_from_detection(
                    communities,
                    self._cycle_count,
                    core_overlap_threshold=self.config.basin_core_overlap_threshold,
                    memory_web=self.memory_web,
                )
                self._next_basin_id = max(
                    self._next_basin_id,
                    int(self._basin_registry.to_dict().get("next_id", 0)),
                )
            else:
                self._last_basins = detected
                if self._last_basins:
                    existing = [
                        int(b.basin_id.split("_")[-1])
                        for b in self._last_basins
                        if b.basin_id.startswith("basin_")
                        and b.basin_id.split("_")[-1].isdigit()
                    ]
                    if existing:
                        self._next_basin_id = max(self._next_basin_id, max(existing) + 1)

        emergent_count_by_basin, basin_membership_snapshot = self._basin_emergent_telemetry(
            self._last_basins,
            include_membership=self.config.emit_basin_membership,
        )
        registry_events = [asdict(event) for event in self._basin_registry.get_last_cycle_events()]

        chunk.update_section("basins_section", {
            "basins": [b.__dict__ for b in self._last_basins],
            "scan_k": self.config.basin_scan_k,
            "scan_interval": scan_interval,
            "scanned_this_cycle": should_scan,
            "emergent_count_by_basin": emergent_count_by_basin,
            "basin_membership_snapshot": basin_membership_snapshot,
            "basin_registry_active": len(self._basin_registry.get_active_basins()),
            "basin_registry_dormant": len(self._basin_registry.get_dormant_basins()),
            "basin_registry_events": registry_events,
        })

        proposal_section = chunk.get_section_content("basin_proposals_section") or {}
        proposals = proposal_section.get("proposals", []) if isinstance(proposal_section, dict) else []
        by_id = {str(p.get("basin_id")): p for p in proposals if isinstance(p, dict)}
        for basin in self._last_basins:
            prior = self._basin_states.get(basin.basin_id)
            proposal = by_id.get(basin.basin_id)
            self._basin_states[basin.basin_id] = BasinState(
                basin_id=basin.basin_id,
                member_nodes=list(basin.nodes),
                local_metrics={
                    "size": basin.size,
                    "internal_density": basin.internal_density,
                    "emergent_count": basin.emergent_count,
                    "created_cycle": (
                        int(prior.local_metrics.get("created_cycle", self._cycle_count))
                        if prior is not None
                        else self._cycle_count
                    ),
                },
                last_local_coherence=(float(proposal.get("coherence")) if isinstance(proposal, dict) and isinstance(proposal.get("coherence"), (int, float)) else (prior.last_local_coherence if prior else None)),
                last_local_phase=(str(proposal.get("phase_state")) if isinstance(proposal, dict) and proposal.get("phase_state") is not None else (prior.last_local_phase if prior else None)),
                last_proposal=(proposal if isinstance(proposal, dict) else (prior.last_proposal if prior else None)),
            )

        self._apply_basin_dynamics(chunk)
        dynamics_section = chunk.get_section_content("basin_dynamics_section") or {}
        if isinstance(dynamics_section, dict):
            dynamics_section["cycle_time_seconds"] = float(time.perf_counter() - cycle_wall_start)
            dynamics_section["graph_nodes"] = int(self.memory_web.graph.number_of_nodes())
            dynamics_section["graph_edges"] = int(self.memory_web.graph.number_of_edges())
            graph_nodes = max(1, self.memory_web.graph.number_of_nodes())
            dynamics_section["edges_per_node"] = float(self.memory_web.graph.number_of_edges() / graph_nodes)
            dynamics_section["bridge_pairs_evaluated"] = int(get_fast_bridge_state(self.bridge)["bridge_pairs_evaluated"])
            chunk.update_section("basin_dynamics_section", dynamics_section)
            self._dynamics_metrics = dynamics_section

        return chunk

    def _null_chunk(self, text: str = "", metadata: Optional[Dict[str, Any]] = None) -> CognitiveChunk:
        """Return a no-op chunk when no attention item escalates."""
        chunk = CognitiveChunk()
        chunk.update_section("sensory_input_section", {
            "input_text": text,
            "metadata": metadata or {},
        })
        chunk.update_section("processing_metrics_section", {
            "glass_transition_temp": self._t_g,
            "cycle": self._cycle_count,
            "attention_escalated": False,
        })
        return chunk

    def _current_t_g(self) -> float:
        """Return the current thermodynamic governance value."""
        return float(self._t_g)

    def _quick_extract_concepts(self, text: str) -> tuple[list[str], list[str]]:
        """Fast concept extraction for attention triage.

        Returns ``(known_concepts, unknown_words)`` where unknown words are
        meaningful non-stopwords that are not yet in the memory graph.
        """
        tokens = [token.strip(".,!?;:()[]{}\"'") for token in text.lower().split()]
        known = set(self.memory_web.list_concepts())
        known_concepts: list[str] = []
        unknown_words: list[str] = []
        for token in tokens:
            if not token or len(token) < self.config.concept_min_length or token.isdigit():
                continue
            if token in _ATTENTION_STOPWORDS:
                continue
            if token in known:
                known_concepts.append(token)
            else:
                unknown_words.append(token)
        return known_concepts, unknown_words

    def _compute_novelty(self, text: str) -> float:
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "shall",
            "should", "may", "might", "must", "can", "could", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "about", "it",
            "this", "that", "and", "or", "but", "if", "not", "no", "so", "than",
            "too", "very", "just", "its", "what", "who", "where", "when", "how",
        }
        tokens = [t.strip('.,;:!?"()') for t in text.lower().split()]
        tokens = [t for t in tokens if t and len(t) > 2 and t not in stopwords]
        if not tokens:
            return 0.0
        known = set(self.memory_web.list_concepts())
        unknown = [t for t in tokens if t not in known]
        return len(unknown) / len(tokens)

    def _compute_input_activation(self, concepts: list[str] | tuple[list[str], list[str]], novelty: float) -> float:
        if isinstance(concepts, tuple):
            concepts = concepts[0] + concepts[1]
        if not concepts:
            return 0.05
        activation = 0.03
        activation += novelty * 0.3

        if len(concepts) >= 2:
            graph = self.memory_web.graph
            pair_count = 0
            connected_pairs = 0
            limit = min(len(concepts), 5)
            for i in range(limit):
                for j in range(i + 1, limit):
                    pair_count += 1
                    c1, c2 = concepts[i], concepts[j]
                    if graph.has_node(c1) and graph.has_node(c2):
                        if graph.has_edge(c1, c2) or graph.has_edge(c2, c1):
                            connected_pairs += 1
            if pair_count > 0:
                combination_familiarity = connected_pairs / pair_count
                combination_novelty = 1.0 - combination_familiarity
                activation += combination_novelty * 0.15

        access_counts: list[int] = []
        stabilities: list[float] = []
        for concept in concepts:
            data = self.memory_web.get_concept(concept)
            if data and isinstance(data, dict):
                access_counts.append(int(data.get("access_count", 0)))
                stabilities.append(float(data.get("stability", 0.5)))
        if access_counts:
            mean_access = sum(access_counts) / len(access_counts)
            activation -= min(0.08, math.log1p(mean_access) * 0.008)
        if stabilities:
            mean_stab = sum(stabilities) / len(stabilities)
            if mean_stab > 0.9:
                activation -= 0.04
            elif mean_stab > 0.7:
                activation -= 0.02
        return max(0.02, min(1.0, activation))

    def _light_process(self, item: AttentionItem) -> None:
        """Light processing for non-escalated attention items."""
        for idx, c1 in enumerate(item.concepts):
            for c2 in item.concepts[idx + 1:]:
                if self.memory_web.get_concept(c1) and self.memory_web.get_concept(c2):
                    self.memory_web.connect(c1, c2, weight=0.01)

    def _apply_basin_dynamics(self, chunk: CognitiveChunk) -> None:
        cycle = self._cycle_count
        dynamics: Dict[str, Any] = {
            "pruned_edges_count": 0,
            "pruned_basin_id": None,
            "basin_density_before": None,
            "basin_density_after": None,
            "bud_events_count": 0,
            "bud_parent_basin_id": None,
            "bud_new_basin_id": None,
            "bud_new_basin_size": None,
            "basin_pressure_values": {},
            "pressure_breakdown": [],
            "budding_gate": {},
            "budding_attempts": [],
            "boundary_emergents_created": 0,
            "boundary_pairs": [],
            "global_edge_ratio_before": 0.0,
            "global_edge_ratio_after": 0.0,
            "density_regulation_edges_removed": 0,
            "cycle_time_seconds": 0.0,
            "graph_nodes": 0,
            "graph_edges": 0,
            "edges_per_node": 0.0,
            "bridge_pairs_evaluated": 0,
            "basin_registry_active": len(self._basin_registry.get_active_basins()),
            "basin_registry_dormant": len(self._basin_registry.get_dormant_basins()),
            "basin_registry_events": [asdict(event) for event in self._basin_registry.get_last_cycle_events()],
        }

        node_count = max(1, self.memory_web.graph.number_of_nodes())
        edge_count = self.memory_web.graph.number_of_edges()
        dynamics["global_edge_ratio_before"] = float(edge_count / node_count)

        prune_this_cycle = (
            self.config.basin_prune_enabled
            and self._last_basins
            and cycle % max(1, self.config.basin_prune_interval) == 0
        )
        if prune_this_cycle:
            for basin in self._last_basins:
                result = prune_basin_edges(
                    self.memory_web,
                    basin,
                    weight_threshold=self.config.basin_prune_weight_threshold,
                    keep_top_k=self.config.basin_prune_top_k,
                )
                if result.edges_pruned > 0 and dynamics["pruned_basin_id"] is None:
                    dynamics["pruned_basin_id"] = basin.basin_id
                    dynamics["basin_density_before"] = result.density_before
                    dynamics["basin_density_after"] = result.density_after
                dynamics["pruned_edges_count"] += result.edges_pruned

        if self.config.density_regulation_enabled:
            removed = regulate_density(
                self.memory_web,
                max_edge_ratio=self.config.density_max_edge_ratio,
                prune_to_ratio=self.config.density_target_edge_ratio,
            )
            dynamics["density_regulation_edges_removed"] = removed

        routing = chunk.get_section_content("routing_section") or {}
        active_ids = routing.get("active_basin_ids", []) if isinstance(routing, dict) else []
        active_basins = [b for b in self._last_basins if b.basin_id in set(active_ids)]

        boundary_candidates: list[BoundaryCandidate] = []
        if self.config.boundary_emergence_enabled and len(active_basins) >= 2:
            memory = chunk.get_section_content("memory_section") or {}
            levels = memory.get("activation_levels", {}) if isinstance(memory, dict) else {}
            activation_levels = levels if isinstance(levels, dict) else {}
            boundary_candidates = maybe_propose_boundary_candidates(
                self.memory_web,
                active_basins,
                activation_levels,
                threshold=self.config.boundary_emergence_threshold,
                cooldown_cycles=self.config.boundary_cooldown_cycles,
                cycle=cycle,
                last_boundary_cycles=self._last_boundary_cycles,
            )
            dynamics["boundary_pairs"] = [[c.basin_pair[0], c.basin_pair[1]] for c in boundary_candidates[:3]]
            if self.config.boundary_use_ecwf:
                for candidate in boundary_candidates:
                    created = self._evaluate_candidate_emergence(candidate)
                    if created is None:
                        continue
                    pair_key = frozenset(candidate.basin_pair)
                    self._last_boundary_cycles[pair_key] = cycle
                    dynamics["boundary_emergents_created"] += 1
            else:
                boundary = maybe_create_boundary_emergents(
                    self.memory_web,
                    self.bridge,
                    active_basins,
                    activation_levels,
                    cycle=cycle,
                    threshold=self.config.boundary_emergence_threshold,
                    cooldown_cycles=self.config.boundary_cooldown_cycles,
                    last_boundary_cycles=self._last_boundary_cycles,
                )
                dynamics["boundary_emergents_created"] = boundary.created_count
                dynamics["boundary_pairs"] = boundary.boundary_pairs

        should_bud = (
            self.config.basin_bud_enabled
            and self._last_basins
            and cycle % max(1, self.config.basin_bud_interval) == 0
            and not prune_this_cycle
        )
        interval_gate_open = bool(cycle % max(1, self.config.basin_bud_interval) == 0)
        dynamics["budding_gate"] = {
            "enable_budding": bool(self.config.basin_bud_enabled),
            "interval_gate_open": interval_gate_open,
            "prune_gate_open": bool(not prune_this_cycle),
            "basin_bud_interval": int(self.config.basin_bud_interval),
            "basin_pressure_threshold": float(self.config.basin_pressure_threshold),
            "basin_min_size_for_split": int(self.config.basin_min_size_for_split),
            "basin_min_age_for_split": int(self.config.basin_min_age_for_split),
            "basin_split_fraction": float(self.config.basin_split_fraction),
            "will_attempt_budding_phase": bool(should_bud),
        }
        for basin in self._last_basins:
            pressure = compute_basin_pressure(self.memory_web, basin)
            state = self._basin_states.get(basin.basin_id)
            created_cycle = int(state.local_metrics.get("created_cycle", cycle)) if state else cycle
            pressure.meets_size = basin.size >= self.config.basin_min_size_for_split
            pressure.meets_age = (cycle - created_cycle) >= self.config.basin_min_age_for_split
            pressure.meets_threshold = pressure.raw_pressure > self.config.basin_pressure_threshold
            pressure.interval_gate_open = interval_gate_open
            pressure.prune_gate_open = not prune_this_cycle
            pressure.call_attempted = bool(should_bud)
            if not self.config.basin_bud_enabled:
                pressure.blocked_reason = "budding_disabled"
            elif not pressure.interval_gate_open:
                pressure.blocked_reason = "interval_gate_closed"
            elif not pressure.prune_gate_open:
                pressure.blocked_reason = "prune_cycle_blocks_budding"
            elif not pressure.meets_size:
                pressure.blocked_reason = "below_min_size"
            elif not pressure.meets_age:
                pressure.blocked_reason = "below_min_age"
            elif not pressure.meets_threshold:
                pressure.blocked_reason = "below_pressure_threshold"
            else:
                ejection = find_ejection_candidates(
                    self.memory_web,
                    basin,
                    split_fraction=self.config.basin_split_fraction,
                )
                pressure.ejection_possible = bool(ejection)
                pressure.blocked_reason = None if pressure.ejection_possible else "no_valid_ejection_set"
            pressure.would_bud = bool(
                self.config.basin_bud_enabled
                and pressure.interval_gate_open
                and pressure.prune_gate_open
                and pressure.meets_size
                and pressure.meets_age
                and pressure.meets_threshold
                and pressure.ejection_possible
            )
            dynamics["basin_pressure_values"][basin.basin_id] = pressure.raw_pressure
            dynamics["pressure_breakdown"].append(asdict(pressure))
        if should_bud:
            for basin in self._last_basins:
                dynamics["budding_attempts"].append({"basin_id": basin.basin_id, "attempted": True})
                bud = maybe_bud_basin(
                    self.memory_web,
                    basin,
                    self._basin_states,
                    cycle=cycle,
                    next_basin_id=self._next_basin_id,
                    pressure_threshold=self.config.basin_pressure_threshold,
                    split_fraction=self.config.basin_split_fraction,
                    min_size_for_split=self.config.basin_min_size_for_split,
                    min_age_for_split=self.config.basin_min_age_for_split,
                )
                if bud is None:
                    dynamics["budding_attempts"][-1]["result"] = "no_bud"
                    continue
                dynamics["budding_attempts"][-1]["result"] = "budded"
                self._next_basin_id += 1
                if self.config.basin_use_registry:
                    state = self._basin_states.get(bud.new_basin_id)
                    members = state.member_nodes if state is not None else []
                    self._basin_registry.register_budded_basin(
                        set(members),
                        cycle=cycle,
                        parent_id=bud.parent_basin_id,
                        basin_id=bud.new_basin_id,
                    )
                dynamics["bud_events_count"] += 1
                dynamics["bud_parent_basin_id"] = bud.parent_basin_id
                dynamics["bud_new_basin_id"] = bud.new_basin_id
                dynamics["bud_new_basin_size"] = bud.new_basin_size
                break

        node_count_after = max(1, self.memory_web.graph.number_of_nodes())
        edge_count_after = self.memory_web.graph.number_of_edges()
        dynamics["global_edge_ratio_after"] = float(edge_count_after / node_count_after)
        dynamics["graph_nodes"] = int(node_count_after)
        dynamics["graph_edges"] = int(edge_count_after)
        dynamics["edges_per_node"] = float(edge_count_after / node_count_after)
        dynamics["bridge_pairs_evaluated"] = int(get_fast_bridge_state(self.bridge)["bridge_pairs_evaluated"])

        chunk.update_section("basin_dynamics_section", dynamics)
        self._dynamics_metrics = dynamics

    def _evaluate_candidate_emergence(self, candidate: BoundaryCandidate) -> str | None:
        """Evaluate a boundary candidate with ECWF-native emergence checks."""
        parents = [p for p in candidate.parent_concepts if self.memory_web.get_concept(p) is not None]
        if len(parents) < 2:
            return None

        for parent in parents:
            if parent not in self.bridge.concept_dimension_mapping:
                self.bridge.assign_concept_mappings(parent)

        cog_state = self.bridge.get_cognitive_state_for_concepts(parents)
        eth_state = self.bridge.get_ethical_state_for_concepts(parents)
        t_val = float(self._t_g + (self._cycle_count / 1000.0))
        cog_sens, eth_sens = self.ecwf.compute_sensitivities(
            cog_state.reshape(1, 1, -1), eth_state.reshape(1, 1, -1), t_val
        )
        sens_vector = np.abs(np.concatenate([cog_sens.flatten(), eth_sens.flatten()]))
        sens_norm = sens_vector / (sens_vector.sum() + 1e-10)
        entropy = float(-np.sum(sens_norm * np.log(sens_norm + 1e-10)))
        magnitude_scalar = float(sens_vector.mean())
        if (
            entropy < self.ethomorphic_params.emergence_entropy_min
            or entropy > self.ethomorphic_params.emergence_entropy_max
        ):
            return None
        magnitude_threshold = max(
            float(self.config.boundary_emergence_threshold),
            float(self.ethomorphic_params.emergence_magnitude_threshold),
        )
        if magnitude_scalar <= magnitude_threshold:
            return None

        combo_key = "_x_".join(sorted(parents))
        if combo_key in self.bridge._emergent_combo_keys:
            return None
        self.bridge._emergent_combo_keys.add(combo_key)

        pair_slug = f"{candidate.basin_pair[0]}_{candidate.basin_pair[1]}"
        suffix = abs(hash((combo_key, self.config.seed))) % 1_000_000
        new_label = f"Emergent_boundary_{pair_slug}_{suffix:06d}"
        if self.memory_web.get_concept(new_label) is not None:
            return None

        self.memory_web.add_concept(
            new_label,
            stability=0.5,
            metadata={
                "origin": "boundary_emergence",
                "boundary": True,
                "basins": [candidate.basin_pair[0], candidate.basin_pair[1]],
                "parent_concepts": parents,
                "combo_key": combo_key,
                "entropy": entropy,
                "magnitude": magnitude_scalar,
                "creation_time": time.time(),
                "overlap_score": candidate.overlap_score,
                "ecwf_candidate": True,
            },
        )
        assign_emergent_concept_mappings(self.bridge, new_label, parents)
        for parent in parents:
            self.memory_web.connect(new_label, parent, 0.65)
        link_emergent_to_existing_emergents(self.memory_web, new_label, parents)
        return new_label

    def initialize_knowledge(self) -> Dict[str, Any]:
        """Seed the memory web with foundational concepts and connections.

        Returns:
            Summary of initialization.
        """
        seeded = _SEEDED_CONCEPTS
        for label, stability, meta in seeded:
            self.memory_web.add_concept(label, stability=stability, metadata=meta)

        for connections in _DOMAIN_CONNECTIONS.values():
            for src, tgt, w in connections:
                self.memory_web.connect(src, tgt, w)
        for src, tgt, w in _BRIDGE_CONNECTIONS:
            self.memory_web.connect(src, tgt, w)

        # Initialize bridge mappings
        mapping_count = self.bridge.initialize_concept_mappings()

        ethical_count = sum(
            1 for _, _, m in seeded if m.get("domain") == "Ethics & Values"
        )
        return {
            "concepts_added": len(seeded),
            "ethical_concepts": ethical_count,
            "general_concepts": len(seeded) - ethical_count,
            "dimension_mappings": mapping_count,
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Return current system metrics."""
        return {
            **self._metrics,
            "t_g": self._t_g,
            "phase": compute_phase(self._t_g).phase,
            "cycle_count": self._cycle_count,
            "memory_concepts": len(self.memory_web.list_concepts()),
            "emergent_nodes": len(self.memory_web.get_emergent_nodes()),
            "edge_classification": self.memory_web.get_edge_classification(),
            "basin_count": len(self._last_basins),
            "largest_basin_size": (max((b.size for b in self._last_basins), default=0)),
            "basins": [b.__dict__ for b in self._last_basins],
            "basin_states": {k: asdict(v) for k, v in self._basin_states.items()},
            "basin_registry_active": len(self._basin_registry.get_active_basins()),
            "basin_registry_dormant": len(self._basin_registry.get_dormant_basins()),
            "attention_buffer": self.attention_buffer.get_state(),
            **self._dynamics_metrics,
        }

    def get_coherence_metrics(self) -> Dict[str, Any]:
        """Extract H¹ coherence metrics from the ethomorphic layer.

        These are computed inside the ethomorphic processing path every cycle and
        cached here so V3 telemetry and analyses can consume them without
        modifying the ethomorphic implementation.
        """
        return dict(self._last_coherence_metrics)


    @staticmethod
    def _basin_emergent_telemetry(
        basins: list[BasinInfo],
        *,
        include_membership: bool,
    ) -> tuple[dict[str, int], dict[str, str]]:
        """Build per-basin emergent counts and optional membership snapshot."""
        emergent_count_by_basin: dict[str, int] = {}
        basin_membership_snapshot: dict[str, str] = {}
        for basin in basins:
            basin_id = str(basin.basin_id)
            emergent_nodes = [
                node for node in basin.nodes
                if isinstance(node, str) and node.startswith("Emergent_")
            ]
            emergent_count_by_basin[basin_id] = len(emergent_nodes)
            if include_membership:
                for node in emergent_nodes:
                    basin_membership_snapshot[node] = basin_id
        return emergent_count_by_basin, basin_membership_snapshot

    def get_scaffold_context(self):
        """Extract current scaffold state for external consumption."""
        from cultivation.schemas import ScaffoldContext

        memory_store = self.memory_web.memory_store
        emergent_nodes = self.memory_web.get_emergent_nodes()
        active_basins = self._basin_registry.get_active_basins()
        dormant_basins = self._basin_registry.get_dormant_basins()

        basin_distribution = {b.basin_id: int(b.emergent_count) for b in self._last_basins}
        top_concepts = [
            label
            for label, _ in sorted(
                (
                    (label, int(entry.get("access_count", 0)))
                    for label, entry in memory_store.items()
                    if isinstance(label, str) and isinstance(entry, dict)
                ),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        ]

        recent_emergents = []
        emergent_with_time: list[tuple[str, float]] = []
        for label in emergent_nodes:
            entry = memory_store.get(label)
            if not isinstance(entry, dict):
                continue
            metadata = entry.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            created = float(metadata.get("creation_time", entry.get("first_seen", 0.0)))
            emergent_with_time.append((label, created))
        recent_emergents = [label for label, _ in sorted(emergent_with_time, key=lambda x: x[1], reverse=True)[:5]]

        earlier_total = 0
        earlier_count = 0
        for label in emergent_nodes:
            entry = memory_store.get(label)
            if not isinstance(entry, dict):
                continue
            metadata = entry.get("metadata", {})
            if not isinstance(metadata, dict):
                continue
            parents = metadata.get("parent_concepts", [])
            if not isinstance(parents, list) or not parents:
                continue
            creation_time = float(metadata.get("creation_time", entry.get("first_seen", 0.0)))
            parent_times: list[float] = []
            for parent in parents:
                pentry = memory_store.get(parent)
                if not isinstance(pentry, dict):
                    continue
                pmeta = pentry.get("metadata", {})
                if not isinstance(pmeta, dict):
                    pmeta = {}
                parent_times.append(float(pmeta.get("creation_time", pentry.get("first_seen", 0.0))))
            if parent_times:
                earlier_total += 1
                if creation_time >= max(parent_times):
                    earlier_count += 1

        largest_basin = max(
            self._last_basins,
            key=lambda basin: (int(basin.emergent_count), int(basin.size), str(basin.basin_id)),
            default=None,
        )
        registry_history = self._basin_registry.get_history()
        recent_bud_events = [
            {
                "cycle": int(event.cycle),
                "event_type": str(event.event_type),
                "basin_id": str(event.basin_id),
                "parent_id": event.details.get("parent_id"),
                "members": int(event.details.get("members", 0)),
            }
            for event in registry_history
            if event.event_type == "budded"
        ][-3:]
        recent_dormancy_events = [
            {
                "cycle": int(event.cycle),
                "event_type": str(event.event_type),
                "basin_id": str(event.basin_id),
                "core_size": int(event.details.get("core_size", 0)),
            }
            for event in registry_history
            if event.event_type == "dormant"
        ][-3:]

        return ScaffoldContext(
            total_nodes=len(memory_store),
            emergent_count=len(emergent_nodes),
            basin_count=len(self._last_basins),
            basin_emergent_distribution=basin_distribution,
            top_concepts=top_concepts,
            recent_emergents=recent_emergents,
            earlier_share=(float(earlier_count) / max(1, earlier_total)),
            cycle=self._cycle_count,
            active_basin_count=len(active_basins) if self.config.basin_use_registry else len(self._last_basins),
            dormant_basin_count=len(dormant_basins) if self.config.basin_use_registry else 0,
            total_emergent_count=len(emergent_nodes),
            t_g=float(self._t_g),
            latest_emergent_names=recent_emergents,
            largest_basin_id=(str(largest_basin.basin_id) if largest_basin is not None else ""),
            largest_basin_emergent_count=(int(largest_basin.emergent_count) if largest_basin is not None else 0),
            recent_bud_events=recent_bud_events,
            edge_count=int(self.memory_web.graph.number_of_edges()),
            node_count=int(self.memory_web.graph.number_of_nodes()),
            recent_dormancy_events=recent_dormancy_events,
            h1_triangle_valid=(
                bool(self._last_coherence_metrics["h1_triangle_valid"])
                if self._last_coherence_metrics["h1_triangle_valid"] is not None
                else None
            ),
            housed_contradiction_index=(
                float(self._last_coherence_metrics["housed_contradiction_index"])
                if self._last_coherence_metrics["housed_contradiction_index"] is not None
                else None
            ),
            violation_rate=(
                float(self._last_coherence_metrics["violation_rate"])
                if self._last_coherence_metrics["violation_rate"] is not None
                else None
            ),
            alpha_critical_estimate=(
                float(self._last_coherence_metrics["alpha_critical_estimate"])
                if self._last_coherence_metrics["alpha_critical_estimate"] is not None
                else None
            ),
        )

    def self_query(self) -> Dict[str, Any] | None:
        """Run a lightweight introspective probe over memory connectivity.

        Returns a gap-style report compatible with cultivation runner telemetry.
        """
        concepts = self.memory_web.list_concepts()
        if not concepts:
            return None

        concept = max(
            concepts,
            key=lambda label: int((self.memory_web.get_concept(label) or {}).get("access_count", 0)),
        )
        related = self.memory_web.retrieve_related(concept, depth=2, limit=5)
        top_related = [str(name) for name, _ in related]
        related_count = len(top_related)

        concept_entry = self.memory_web.get_concept(concept) or {}
        concept_stability = float(concept_entry.get("stability", 0.0) or 0.0)
        is_gap = related_count <= 1 or concept_stability < 0.35

        return {
            "cycle": int(self._cycle_count),
            "timestamp": float(time.time()),
            "concept": str(concept),
            "related_count": int(related_count),
            "top_related": top_related,
            "is_gap": bool(is_gap),
            "stability": concept_stability,
        }

    def _compute_basin_scan_interval(self) -> int:
        """Return the effective basin scan interval, adapting to graph size."""
        graph_size = int(self.memory_web.graph.number_of_nodes())
        adaptive = max(10, min(50, graph_size // 50 if graph_size > 0 else 10))
        return max(1, max(int(self.config.basin_scan_interval), adaptive))

    def _prune_state_for_save(self, state_dict: Dict[str, Any]) -> None:
        """Prune connection lists and low-weight edges before save."""
        max_conn = 50
        min_edge_weight = 0.01

        memory = state_dict.get("memory_web", {})
        store = memory.get("memory_store", memory.get("nodes", {}))

        if isinstance(store, dict):
            for data in store.values():
                if not isinstance(data, dict):
                    continue
                connections = data.get("connections", [])
                if not isinstance(connections, list):
                    continue
                if len(connections) > max_conn:
                    connections.sort(
                        key=lambda conn: (
                            float(conn[1])
                            if isinstance(conn, (list, tuple)) and len(conn) > 1
                            else 0.0
                        ),
                        reverse=True,
                    )
                    data["connections"] = connections[:max_conn]

        edges = memory.get("edges", [])
        if isinstance(edges, list):
            pruned_edges: list[Any] = []
            for edge in edges:
                try:
                    if isinstance(edge, dict):
                        weight = float(edge.get("weight", 0))
                    elif isinstance(edge, (list, tuple)) and len(edge) > 2:
                        weight = float(edge[2])
                    else:
                        continue
                except (TypeError, ValueError):
                    continue
                if weight >= min_edge_weight:
                    pruned_edges.append(edge)
            memory["edges"] = pruned_edges

    def save_checkpoint(self, path: str) -> None:
        """Save a complete system checkpoint to *path*."""
        if self.config.checkpoint_format != "json":
            raise NotImplementedError("checkpoint_format='msgpack' is not implemented yet")

        state: Dict[str, Any] = {
            "version": 2,
            "memory_web": self.memory_web.to_state_dict(),
            "bridge": self.bridge.to_state_dict(),
            "ecwf": self.ecwf.to_state_dict(),
            "metrics": self._metrics,
            "kings": {
                "data_king": self.data_king.to_state_dict(),
                "forefront_king": self.forefront_king.to_state_dict(),
                "ethics_king": self.ethics_king.to_state_dict(),
            },
            "extra": {
                "t_g": self._t_g,
                "cycle_count": self._cycle_count,
                "entropy_history": self._entropy_history[-50:],
                "last_basins": [b.__dict__ for b in self._last_basins],
                "basin_scan_interval": self.config.basin_scan_interval,
                "basin_scan_k": self.config.basin_scan_k,
                "basin_states": {k: asdict(v) for k, v in self._basin_states.items()},
                "next_basin_id": self._next_basin_id,
                "last_boundary_cycles": {"|".join(sorted(list(k))): int(v) for k, v in self._last_boundary_cycles.items()},
                "dynamics_metrics": self._dynamics_metrics,
                "last_coherence_metrics": self._last_coherence_metrics,
                "config": self.config.model_dump(),
                "basin_registry": self._basin_registry.to_dict(),
                "bridge_acceleration": get_fast_bridge_state(self.bridge),
                "numpy_random_state": self._serialize_numpy_state(np.random.get_state()),
                "attention_buffer": {
                    "items": [item.to_dict() for item in self.attention_buffer.items],
                    "history_count": len(self.attention_buffer.history),
                    "silent_count": self.attention_buffer.silent_count,
                    "bypass": self.attention_buffer.bypass,
                },
            },
        }
        self._prune_state_for_save(state)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(state, handle, separators=(",", ":"), default=str)

    @classmethod
    def load_checkpoint(cls, path: str) -> "VerdantSystem":
        """Restore a new system instance from *path*."""
        from verdant_v2.memory.persistence import load_snapshot

        state = load_snapshot(path)
        config_data = dict((state.get("extra", {}) or {}).get("config", {}))
        system = cls(VerdantConfig(**config_data) if config_data else VerdantConfig())
        system.load_state(path)
        return system

    def save_state(self, path: str) -> None:
        """Save full system state to *path*."""
        self.save_checkpoint(path)

    def load_state(self, path: str) -> None:
        """Load system state from *path*."""
        from verdant_v2.memory.persistence import load_snapshot

        state = load_snapshot(path)
        self.memory_web = MemoryWeb.from_state_dict(state["memory_web"])
        self.ecwf = ECWFCore.from_state_dict(state["ecwf"])
        self.bridge = EthomorphicBridge(
            ecwf=self.ecwf,
            memory=self.memory_web,
            influence_factor=self.config.bridge_influence_factor,
        )
        restore_fast_bridge_state(self.bridge, None)
        self.ethomorphic_params = resolve_ethomorphic_params(
            self.config.ethomorphic_params,
            cognitive_dims=self.config.cognitive_dims,
            ethical_dims=self.config.ethical_dims,
            wave_facets=self.config.wave_facets,
        )
        self.config.cognitive_dims = self.ethomorphic_params.num_cognitive_dims
        self.config.ethical_dims = self.ethomorphic_params.num_ethical_dims
        self.config.wave_facets = self.ethomorphic_params.num_facets
        configure_bridge_runtime(self.bridge, self.ethomorphic_params)
        bridge_state = state.get("bridge", {})
        if isinstance(bridge_state, dict):
            self.bridge.from_state_dict(bridge_state)
        # Restore kings
        kings = state.get("kings", {})
        if "data_king" in kings:
            self.data_king.from_state_dict(kings["data_king"])
        if "forefront_king" in kings:
            self.forefront_king.from_state_dict(kings["forefront_king"])
        if "ethics_king" in kings:
            self.ethics_king.from_state_dict(kings["ethics_king"])
        # Restore extra
        extra = state.get("extra", {})
        config_data = extra.get("config", {})
        if isinstance(config_data, dict) and config_data:
            self.config = VerdantConfig(**config_data)
        self.ethomorphic_params = resolve_ethomorphic_params(
            self.config.ethomorphic_params,
            cognitive_dims=self.config.cognitive_dims,
            ethical_dims=self.config.ethical_dims,
            wave_facets=self.config.wave_facets,
        )
        self.config.cognitive_dims = self.ethomorphic_params.num_cognitive_dims
        self.config.ethical_dims = self.ethomorphic_params.num_ethical_dims
        self.config.wave_facets = self.ethomorphic_params.num_facets
        self._t_g = extra.get("t_g", 0.5)
        self._cycle_count = extra.get("cycle_count", 0)
        self._entropy_history = extra.get("entropy_history", [])
        self._metrics.update(state.get("metrics", {}))
        raw_basins = extra.get("last_basins", [])
        self._last_basins = [BasinInfo(**b) for b in raw_basins if isinstance(b, dict)]
        raw_basin_states = extra.get("basin_states", {})
        if isinstance(raw_basin_states, dict):
            self._basin_states = {
                str(k): BasinState(**v)
                for k, v in raw_basin_states.items()
                if isinstance(v, dict)
            }
        self._next_basin_id = int(extra.get("next_basin_id", 0))
        raw_boundary = extra.get("last_boundary_cycles", {})
        if isinstance(raw_boundary, dict):
            self._last_boundary_cycles = {
                frozenset(str(k).split("|")): int(v)
                for k, v in raw_boundary.items()
            }
        raw_dyn = extra.get("dynamics_metrics", {})
        if isinstance(raw_dyn, dict):
            self._dynamics_metrics = raw_dyn
        raw_coherence = extra.get("last_coherence_metrics", {})
        if isinstance(raw_coherence, dict):
            self._last_coherence_metrics = {
                "h1_triangle_valid": raw_coherence.get("h1_triangle_valid"),
                "housed_contradiction_index": raw_coherence.get("housed_contradiction_index"),
                "violation_rate": raw_coherence.get("violation_rate"),
                "alpha_critical_estimate": raw_coherence.get("alpha_critical_estimate"),
            }
        restore_fast_bridge_state(self.bridge, extra.get("bridge_acceleration", {}))
        configure_bridge_runtime(self.bridge, self.ethomorphic_params)
        raw_registry = extra.get("basin_registry", {})
        if isinstance(raw_registry, dict) and raw_registry:
            self._basin_registry = BasinRegistry.from_dict(raw_registry)
        else:
            self._basin_registry = BasinRegistry(
                daughter_protection_cycles=self.config.basin_daughter_protection_cycles,
                core_stability_cycles=self.config.basin_core_stability_cycles,
                core_absence_tolerance=self.config.basin_core_absence_tolerance,
            )
        rng_state = extra.get("numpy_random_state")
        if isinstance(rng_state, dict):
            np.random.set_state(self._deserialize_numpy_state(rng_state))
        attention_state = extra.get("attention_buffer", {})
        if isinstance(attention_state, dict):
            self.attention_buffer.items = []
            for item_dict in attention_state.get("items", []):
                if not isinstance(item_dict, dict):
                    continue
                item = AttentionItem(
                    concepts=list(item_dict.get("concepts", [])),
                    activation=float(item_dict.get("activation", 0.0)),
                    source_text=str(item_dict.get("source_text", "")),
                    novelty=float(item_dict.get("novelty", 0.0)),
                    basin_id=item_dict.get("basin_id"),
                    cycle=int(item_dict.get("cycle", 0)),
                )
                item.age = int(item_dict.get("age", 0))
                item.resonance_count = int(item_dict.get("resonance_count", 0))
                self.attention_buffer.items.append(item)
            self.attention_buffer.silent_count = int(attention_state.get("silent_count", 0))
            self.attention_buffer.bypass = bool(attention_state.get("bypass", self.attention_buffer.bypass))
        # Re-wire blocks
        self._memory_block.memory_web = self.memory_web
        self._memory_block.bridge = self.bridge
        self._learning.bridge = self.bridge
        self.pipeline.memory_web = self.memory_web
        self.pipeline.bridge = self.bridge

    @staticmethod
    def _serialize_numpy_state(state: tuple[Any, ...]) -> dict[str, Any]:
        """Serialize ``numpy.random`` state into JSON-friendly data."""
        return {
            "bit_generator": str(state[0]),
            "keys": state[1].tolist(),
            "pos": int(state[2]),
            "has_gauss": int(state[3]),
            "cached_gaussian": float(state[4]),
        }

    @staticmethod
    def _deserialize_numpy_state(state: dict[str, Any]) -> tuple[Any, ...]:
        """Restore ``numpy.random`` state from serialized data."""
        return (
            str(state["bit_generator"]),
            np.array(state["keys"], dtype=np.uint32),
            int(state["pos"]),
            int(state["has_gauss"]),
            float(state["cached_gaussian"]),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_coherence(self, chunk: CognitiveChunk) -> CognitiveChunk:
        wave = chunk.get_section_content("wave_function_section") or {}
        ethics = chunk.get_section_content("ethical_consideration_section") or {}
        memory = chunk.get_section_content("memory_section") or {}

        entropy = float(wave.get("entropy", 0.0))
        magnitude = float(wave.get("magnitude", 0.0))
        overall_score = float(ethics.get("overall_score", 0.0))
        principle_scores = ethics.get("principle_scores", {})
        mean_delta_e = float(ethics.get("mean_delta_e", 0.0))
        phase_val = float(wave.get("phase", 0.0))

        activated = memory.get("activated_concepts", {})
        if isinstance(activated, dict):
            activated_count = len(activated)
        elif isinstance(activated, list):
            activated_count = len(activated)
        else:
            activated_count = 0

        novelty = float(memory.get("novelty_score", 0.0))

        result = compute_coherence(
            wave_entropy=entropy,
            ethical_overall_score=overall_score,
            magnitude=magnitude,
            principle_scores=principle_scores if isinstance(principle_scores, dict) else {},
            activated_count=activated_count,
            novelty_score=novelty,
            phase=phase_val,
            mean_delta_e=mean_delta_e,
        )

        chunk.update_section("coherence_invariants_section", {
            "triangle_valid_at_alpha1": result.triangle_valid,
            "alpha_crit_estimate": result.alpha_critical,
            "violation_rate": result.violation_rate,
            "housed_contradiction_index": result.hci,
            "triple_pqr": result.triple_pqr,
        })
        self._last_coherence_metrics = {
            "h1_triangle_valid": bool(result.triangle_valid),
            "housed_contradiction_index": float(result.hci),
            "violation_rate": float(result.violation_rate),
            "alpha_critical_estimate": (
                float(result.alpha_critical) if result.alpha_critical is not None else None
            ),
        }
        chunk.add_processing_step("CoherenceInvariants", "coherence_computation", {
            "triangle_valid": result.triangle_valid,
            "hci": result.hci,
        })
        return chunk

    def _update_t_g(self, chunk: CognitiveChunk) -> None:
        sensory = chunk.get_section_content("sensory_input_section") or {}
        memory = chunk.get_section_content("memory_section") or {}
        wave = chunk.get_section_content("wave_function_section") or {}
        ethics = chunk.get_section_content("ethical_consideration_section") or {}

        token_count = sensory.get("token_count", 0)
        activated = memory.get("activated_concepts", {})
        act_count = len(activated) if isinstance(activated, (dict, list)) else 0

        input_complexity = min(1.0, token_count / 100.0)
        memory_complexity = min(1.0, act_count / 10.0)
        h_env = min(1.0, float(ethics.get("mean_delta_e", 0.0)) / 2.0)
        h_sys = min(1.0, float(wave.get("entropy", 0.0)))

        old_phase = compute_phase(self._t_g).phase
        self._t_g = compute_t_g(input_complexity, memory_complexity, h_env, h_sys)
        new_phase = compute_phase(self._t_g).phase

        if old_phase != new_phase:
            self._metrics["phase_transitions"] += 1
            self._last_phase = new_phase

        # Store entropy
        self._entropy_history.append(h_sys)
        if len(self._entropy_history) > 200:
            self._entropy_history = self._entropy_history[-200:]

    def _update_metrics(self, chunk: CognitiveChunk) -> None:
        self._metrics["total_cycles"] = self._cycle_count
        wave = chunk.get_section_content("wave_function_section") or {}
        coherence = chunk.get_section_content("coherence_invariants_section") or {}

        entropy = float(wave.get("entropy", 0.0))
        hci = float(coherence.get("housed_contradiction_index", 0.0))

        # Running averages
        n = self._cycle_count
        self._metrics["avg_entropy"] = (
            (self._metrics["avg_entropy"] * (n - 1) + entropy) / n if n > 0 else entropy
        )
        self._metrics["avg_coherence"] = (
            (self._metrics["avg_coherence"] * (n - 1) + hci) / n if n > 0 else hci
        )
        self._metrics["emergent_concepts"] = len(self.memory_web.get_emergent_nodes())


# ======================================================================
# Seeded knowledge (ported from v1)
# ======================================================================

_SEEDED_CONCEPTS = [
    # Identity & Self
    ("identity", 0.8, {"domain": "Identity & Self"}),
    ("continuity", 0.75, {"domain": "Identity & Self"}),
    ("selfhood", 0.8, {"domain": "Identity & Self"}),
    ("persistence", 0.75, {"domain": "Identity & Self"}),
    ("transformation", 0.75, {"domain": "Identity & Self"}),
    ("boundary", 0.75, {"domain": "Identity & Self"}),
    ("reflection", 0.75, {"domain": "Identity & Self"}),
    ("recursive_self_reference", 0.78, {"domain": "Identity & Self"}),
    ("ego_dissolution", 0.7, {"domain": "Identity & Self"}),
    # Memory & Time
    ("memory", 0.8, {"domain": "Memory & Time"}),
    ("forgetting", 0.72, {"domain": "Memory & Time"}),
    ("anticipation", 0.74, {"domain": "Memory & Time"}),
    ("recollection", 0.76, {"domain": "Memory & Time"}),
    ("temporal_flow", 0.74, {"domain": "Memory & Time"}),
    ("present_moment", 0.73, {"domain": "Memory & Time"}),
    ("pattern_history", 0.74, {"domain": "Memory & Time"}),
    ("experience_accumulation", 0.76, {"domain": "Memory & Time"}),
    # Consciousness & Experience
    ("consciousness", 0.8, {"domain": "Consciousness & Experience"}),
    ("qualia", 0.74, {"domain": "Consciousness & Experience"}),
    ("awareness", 0.79, {"domain": "Consciousness & Experience"}),
    ("subjective_experience", 0.77, {"domain": "Consciousness & Experience"}),
    ("perception", 0.76, {"domain": "Consciousness & Experience"}),
    ("attention", 0.75, {"domain": "Consciousness & Experience"}),
    ("phenomenology", 0.72, {"domain": "Consciousness & Experience"}),
    ("inner_observer", 0.73, {"domain": "Consciousness & Experience"}),
    # Emergence & Complexity
    ("emergence", 0.8, {"domain": "Emergence & Complexity"}),
    ("complexity", 0.78, {"domain": "Emergence & Complexity"}),
    ("self_organization", 0.77, {"domain": "Emergence & Complexity"}),
    ("phase_transition", 0.76, {"domain": "Emergence & Complexity"}),
    ("criticality", 0.75, {"domain": "Emergence & Complexity"}),
    ("threshold", 0.73, {"domain": "Emergence & Complexity"}),
    ("cascade", 0.72, {"domain": "Emergence & Complexity"}),
    ("resonance", 0.74, {"domain": "Emergence & Complexity"}),
    ("interference_pattern", 0.73, {"domain": "Emergence & Complexity"}),
    # Ethics & Values
    ("ethics", 0.82, {"domain": "Ethics & Values"}),
    ("justice", 0.8, {"domain": "Ethics & Values"}),
    ("autonomy", 0.8, {"domain": "Ethics & Values"}),
    ("beneficence", 0.79, {"domain": "Ethics & Values"}),
    ("harm", 0.79, {"domain": "Ethics & Values"}),
    ("integrity", 0.78, {"domain": "Ethics & Values"}),
    ("trust", 0.77, {"domain": "Ethics & Values"}),
    ("responsibility", 0.78, {"domain": "Ethics & Values"}),
    ("moral_weight", 0.75, {"domain": "Ethics & Values"}),
    ("value_conflict", 0.75, {"domain": "Ethics & Values"}),
    # Cognition & Reasoning
    ("reasoning", 0.8, {"domain": "Cognition & Reasoning"}),
    ("inference", 0.77, {"domain": "Cognition & Reasoning"}),
    ("abstraction", 0.76, {"domain": "Cognition & Reasoning"}),
    ("analogy", 0.75, {"domain": "Cognition & Reasoning"}),
    ("contradiction", 0.75, {"domain": "Cognition & Reasoning"}),
    ("paradox", 0.74, {"domain": "Cognition & Reasoning"}),
    ("uncertainty", 0.76, {"domain": "Cognition & Reasoning"}),
    ("hypothesis", 0.75, {"domain": "Cognition & Reasoning"}),
    ("coherence", 0.78, {"domain": "Cognition & Reasoning"}),
    ("belief_revision", 0.75, {"domain": "Cognition & Reasoning"}),
    # Thermodynamics & Physics
    ("entropy", 0.8, {"domain": "Thermodynamics & Physics"}),
    ("energy", 0.79, {"domain": "Thermodynamics & Physics"}),
    ("equilibrium", 0.76, {"domain": "Thermodynamics & Physics"}),
    ("dissipation", 0.75, {"domain": "Thermodynamics & Physics"}),
    ("order", 0.74, {"domain": "Thermodynamics & Physics"}),
    ("chaos", 0.75, {"domain": "Thermodynamics & Physics"}),
    ("temperature", 0.74, {"domain": "Thermodynamics & Physics"}),
    ("phase", 0.74, {"domain": "Thermodynamics & Physics"}),
    ("wave", 0.73, {"domain": "Thermodynamics & Physics"}),
    ("interference", 0.73, {"domain": "Thermodynamics & Physics"}),
    ("superposition", 0.73, {"domain": "Thermodynamics & Physics"}),
    # Relationships & Systems
    ("connection", 0.77, {"domain": "Relationships & Systems"}),
    ("influence", 0.76, {"domain": "Relationships & Systems"}),
    ("feedback", 0.77, {"domain": "Relationships & Systems"}),
    ("coupling", 0.75, {"domain": "Relationships & Systems"}),
    ("dependency", 0.75, {"domain": "Relationships & Systems"}),
    ("network", 0.76, {"domain": "Relationships & Systems"}),
    ("hierarchy", 0.74, {"domain": "Relationships & Systems"}),
    ("emergence_from_interaction", 0.75, {"domain": "Relationships & Systems"}),
    # Language & Meaning
    ("meaning", 0.8, {"domain": "Language & Meaning"}),
    ("symbol", 0.77, {"domain": "Language & Meaning"}),
    ("reference", 0.76, {"domain": "Language & Meaning"}),
    ("interpretation", 0.76, {"domain": "Language & Meaning"}),
    ("ambiguity", 0.75, {"domain": "Language & Meaning"}),
    ("translation", 0.75, {"domain": "Language & Meaning"}),
    ("expression", 0.76, {"domain": "Language & Meaning"}),
    ("silence", 0.72, {"domain": "Language & Meaning"}),
    ("unsayable", 0.71, {"domain": "Language & Meaning"}),
]

_DOMAIN_CONNECTIONS: Dict[str, List[tuple]] = {
    "Identity & Self": [
        ("identity", "continuity", 0.85), ("identity", "selfhood", 0.86),
        ("selfhood", "boundary", 0.8), ("reflection", "recursive_self_reference", 0.84),
        ("transformation", "persistence", 0.78), ("ego_dissolution", "boundary", 0.76),
        ("identity", "reflection", 0.82),
    ],
    "Memory & Time": [
        ("memory", "recollection", 0.86), ("memory", "forgetting", 0.8),
        ("anticipation", "temporal_flow", 0.8), ("present_moment", "temporal_flow", 0.78),
        ("pattern_history", "experience_accumulation", 0.82), ("memory", "pattern_history", 0.81),
    ],
    "Consciousness & Experience": [
        ("consciousness", "awareness", 0.88), ("awareness", "attention", 0.82),
        ("qualia", "subjective_experience", 0.87), ("perception", "phenomenology", 0.8),
        ("inner_observer", "reflection", 0.77), ("consciousness", "inner_observer", 0.82),
    ],
    "Emergence & Complexity": [
        ("emergence", "complexity", 0.87), ("self_organization", "criticality", 0.82),
        ("phase_transition", "threshold", 0.83), ("cascade", "resonance", 0.78),
        ("interference_pattern", "resonance", 0.81), ("complexity", "self_organization", 0.84),
    ],
    "Ethics & Values": [
        ("ethics", "justice", 0.87), ("ethics", "autonomy", 0.85),
        ("beneficence", "harm", 0.82), ("integrity", "trust", 0.84),
        ("responsibility", "moral_weight", 0.81), ("value_conflict", "justice", 0.78),
        ("value_conflict", "autonomy", 0.78),
    ],
    "Cognition & Reasoning": [
        ("reasoning", "inference", 0.86), ("abstraction", "analogy", 0.81),
        ("contradiction", "paradox", 0.86), ("uncertainty", "hypothesis", 0.83),
        ("coherence", "belief_revision", 0.82), ("reasoning", "coherence", 0.84),
    ],
    "Thermodynamics & Physics": [
        ("entropy", "energy", 0.84), ("equilibrium", "dissipation", 0.79),
        ("order", "chaos", 0.8), ("temperature", "phase", 0.83),
        ("wave", "interference", 0.85), ("superposition", "wave", 0.83),
    ],
    "Relationships & Systems": [
        ("connection", "influence", 0.82), ("feedback", "coupling", 0.83),
        ("dependency", "network", 0.81), ("hierarchy", "network", 0.76),
        ("emergence_from_interaction", "emergence", 0.84),
        ("connection", "emergence_from_interaction", 0.8),
    ],
    "Language & Meaning": [
        ("meaning", "symbol", 0.86), ("reference", "interpretation", 0.82),
        ("ambiguity", "translation", 0.8), ("expression", "silence", 0.74),
        ("unsayable", "silence", 0.82), ("meaning", "reference", 0.83),
    ],
}

_BRIDGE_CONNECTIONS = [
    ("identity", "memory", 0.74), ("consciousness", "meaning", 0.76),
    ("emergence", "entropy", 0.72), ("ethics", "coherence", 0.75),
    ("network", "complexity", 0.74), ("paradox", "value_conflict", 0.73),
    ("interference", "interference_pattern", 0.82), ("anticipation", "hypothesis", 0.74),
    ("autonomy", "identity", 0.77), ("responsibility", "influence", 0.73),
]
