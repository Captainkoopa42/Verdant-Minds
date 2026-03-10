"""Basin-local micro-pipeline processor (Distributed Cognition v0)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

from ethomorphic.bridge.bridge import EthomorphicBridge

from verdant_v2.memory.activation import spread_activation
from verdant_v2.memory.graph import MemoryWeb
from verdant_v2.pipeline.blocks.action import ActionBlock
from verdant_v2.pipeline.blocks.ethics import EthicsBlock
from verdant_v2.pipeline.blocks.memory import MemoryBlock
from verdant_v2.pipeline.blocks.reasoning import ReasoningBlock
from verdant_v2.pipeline.chunk import CognitiveChunk


@dataclass
class BasinProposal:
    """Action proposal emitted by a basin-local micro-pipeline."""

    basin_id: str
    selected_action: str
    action_confidence: float
    ethical_score: float
    key_concepts: List[str]
    reasoning_summary: str
    phase_state: str
    coherence: Optional[float] = None


class BasinProcessor:
    """Runs a reduced local pipeline (Memory -> Reasoning -> Ethics -> Action)."""

    def __init__(self, memory_web: MemoryWeb, bridge: EthomorphicBridge) -> None:
        self._global_memory = memory_web
        self._global_bridge = bridge

    def _build_local_memory(self, member_nodes: List[str]) -> MemoryWeb:
        """Build a basin-scoped memory view from global memory."""
        local = MemoryWeb(edge_policy=self._global_memory.edge_policy)
        allowed = set(member_nodes)

        for node in member_nodes:
            src = self._global_memory.get_concept(node)
            if src is None:
                continue
            local.add_concept(
                node,
                stability=float(src.get("stability", 0.5)),
                metadata=dict(src.get("metadata", {})),
            )
            local.memory_store[node]["access_count"] = int(src.get("access_count", 0))
            local.memory_store[node]["first_seen"] = float(src.get("first_seen", 0.0))
            local.memory_store[node]["last_accessed"] = float(src.get("last_accessed", 0.0))

        for u, v, d in self._global_memory.graph.edges(data=True):
            if u in allowed and v in allowed and u in local.memory_store and v in local.memory_store:
                local.connect(u, v, float(d.get("weight", 0.5)))
        return local

    def run(
        self,
        *,
        basin_id: str,
        member_nodes: List[str],
        global_chunk: CognitiveChunk,
        priority_seeds: Optional[List[str]] = None,
    ) -> Optional[BasinProposal]:
        """Execute basin-local cognition pass and return a proposal."""
        if not member_nodes:
            return None

        local_memory = self._build_local_memory(member_nodes)
        local_bridge = EthomorphicBridge(
            memory=local_memory,
            ecwf=self._global_bridge.ecwf,
            influence_factor=self._global_bridge.influence_factor,
        )
        local_bridge.initialize_concept_mappings()

        local_chunk = CognitiveChunk()
        local_chunk.update_section(
            "sensory_input_section",
            global_chunk.get_section_content("sensory_input_section") or {},
        )
        local_chunk.update_section(
            "pattern_recognition_section",
            global_chunk.get_section_content("pattern_recognition_section") or {},
        )
        local_chunk.update_section(
            "processing_metrics_section",
            global_chunk.get_section_content("processing_metrics_section") or {},
        )
        local_chunk.update_section(
            "routing_section",
            {
                "mode": "basin_local",
                "active_basin_ids": [basin_id],
                "priority_seeds": [s for s in (priority_seeds or []) if s in set(member_nodes)],
                "scope_nodes": member_nodes,
            },
        )

        # Reduced micro-pipeline: Memory -> Reasoning -> Ethics -> Action
        mem_block = MemoryBlock(memory_web=local_memory, bridge=local_bridge)
        reason_block = ReasoningBlock()
        ethics_block = EthicsBlock()
        action_block = ActionBlock()

        local_chunk = mem_block.process(local_chunk)

        # Restrict activation signal to basin member nodes only.
        mem = local_chunk.get_section_content("memory_section") or {}
        acts = mem.get("activated_concepts", {})
        if isinstance(acts, dict):
            mem["activated_concepts"] = {k: v for k, v in acts.items() if k in set(member_nodes)}
            local_chunk.update_section("memory_section", mem)

        # Explicit basin-scoped local activation trace.
        seeds = [s for s in (priority_seeds or []) if s in set(member_nodes)]
        local_activations = spread_activation(local_memory, seeds or member_nodes[:3])
        local_chunk.update_section("basin_local_memory_section", {
            "basin_id": basin_id,
            "member_nodes": member_nodes,
            "local_activations": local_activations,
        })

        local_chunk = reason_block.process(local_chunk)
        local_chunk = ethics_block.process(local_chunk)
        local_chunk = action_block.process(local_chunk)

        action = local_chunk.get_section_content("action_selection_section") or {}
        reasoning = local_chunk.get_section_content("reasoning_section") or {}
        ethics = local_chunk.get_section_content("ethical_consideration_section") or {}
        wave = local_chunk.get_section_content("wave_function_section") or {}
        coherence = local_chunk.get_section_content("coherence_invariants_section") or {}

        selected = str(action.get("selected_action", "global_default"))
        conf = float(action.get("action_confidence", 0.0))
        ethical_score = float(ethics.get("overall_score", 0.0))
        key_concepts = list((global_chunk.get_section_content("pattern_recognition_section") or {}).get("concepts", []))[:6]
        summary = str(reasoning.get("summary", ""))
        adjustments = reasoning.get("uncertainty_adjustments", {})
        if isinstance(adjustments, list):
            phase_hint = adjustments[0].get("phase") if adjustments and isinstance(adjustments[0], dict) else None
        elif isinstance(adjustments, dict):
            phase_hint = adjustments.get("phase")
        else:
            phase_hint = None
        phase_state = str(phase_hint or wave.get("phase") or "unknown")
        coh = coherence.get("housed_contradiction_index")
        coh_val = float(coh) if isinstance(coh, (int, float)) else None

        return BasinProposal(
            basin_id=basin_id,
            selected_action=selected,
            action_confidence=conf,
            ethical_score=ethical_score,
            key_concepts=key_concepts,
            reasoning_summary=summary,
            phase_state=phase_state,
            coherence=coh_val,
        )


def proposal_to_dict(p: BasinProposal) -> Dict[str, object]:
    """Convert proposal dataclass to serializable dict."""
    return asdict(p)
