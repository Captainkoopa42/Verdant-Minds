"""Pipeline orchestrator — runs a CognitiveChunk through all nine blocks.

The orchestrator holds references to block instances and runs them in
canonical order. Governance hooks are applied between blocks as
specified by v1.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from verdant.memory.basins import detect_basins
from verdant.memory.graph import MemoryWeb
from verdant.pipeline.basin_processor import BasinProcessor, proposal_to_dict
from verdant.pipeline.chunk import CognitiveChunk


@runtime_checkable
class Block(Protocol):
    """Protocol every pipeline block must satisfy."""

    name: str

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Process *chunk* and return the (possibly modified) chunk."""
        ...


class PipelineOrchestrator:
    """Runs a chunk through the nine-block pipeline in order."""

    def __init__(
        self,
        blocks: List[Block],
        *,
        data_king_hook: Optional[Any] = None,
        ethics_king_hook: Optional[Any] = None,
        forefront_king_hook: Optional[Any] = None,
        three_kings_hook: Optional[Any] = None,
        memory_web: Optional[MemoryWeb] = None,
        basin_routing: bool = False,
        basin_top_m: int = 2,
        basin_scan_k: int = 6,
        bridge: Optional[Any] = None,
    ) -> None:
        self.blocks = blocks
        self.data_king_hook = data_king_hook
        self.ethics_king_hook = ethics_king_hook
        self.forefront_king_hook = forefront_king_hook
        self.three_kings_hook = three_kings_hook
        self.memory_web = memory_web
        self.basin_routing = basin_routing
        self.basin_top_m = max(1, basin_top_m)
        self.basin_scan_k = max(1, basin_scan_k)
        self.bridge = bridge

    def _score_basins(self, chunk: CognitiveChunk) -> List[Any]:
        if self.memory_web is None:
            return []
        basins = detect_basins(self.memory_web, k=self.basin_scan_k, min_size=3)
        if not basins:
            return []

        pattern = chunk.get_section_content("pattern_recognition_section") or {}
        candidate = set(pattern.get("concepts", [])) | set(pattern.get("keywords", []))
        scored: List[tuple[float, Any]] = []
        for basin in basins:
            node_set = set(basin.nodes)
            activated = sum(1 for c in candidate if c in node_set)
            mean_access = 0.0
            if basin.top_nodes_by_access:
                mean_access = sum(a for _, a in basin.top_nodes_by_access) / len(basin.top_nodes_by_access)
            score = activated + 0.5 * basin.emergent_count + 0.1 * mean_access
            scored.append((score, basin))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [b for s, b in scored[: self.basin_top_m] if s > 0]
        if not selected and scored:
            selected = [scored[0][1]]
        return selected

    def _attach_routing_context(self, chunk: CognitiveChunk) -> List[Any]:
        """Compute basin-aware routing hints for memory block."""
        if not self.basin_routing:
            return []
        selected = self._score_basins(chunk)
        if not selected:
            return []

        seed_priority: List[str] = []
        for basin in selected:
            seed_priority.extend([node for node, _ in basin.top_nodes_by_access[:5]])
        if not seed_priority:
            for basin in selected:
                seed_priority.extend(basin.nodes[:5])

        chunk.update_section(
            "routing_section",
            {
                "mode": "basin_routing",
                "active_basin_ids": [b.basin_id for b in selected],
                "priority_seeds": list(dict.fromkeys(seed_priority)),
                "scan_k": self.basin_scan_k,
                "top_m": self.basin_top_m,
            },
        )
        return selected

    def _run_basin_micro_pipelines(self, chunk: CognitiveChunk, selected_basins: List[Any]) -> None:
        if not self.basin_routing or not selected_basins or self.memory_web is None or self.bridge is None:
            return
        processor = BasinProcessor(self.memory_web, self.bridge)
        routing = chunk.get_section_content("routing_section") or {}
        priority = routing.get("priority_seeds", []) if isinstance(routing, dict) else []

        proposals: List[Dict[str, object]] = []
        for basin in selected_basins:
            proposal = processor.run(
                basin_id=basin.basin_id,
                member_nodes=list(basin.nodes),
                global_chunk=chunk,
                priority_seeds=priority,
            )
            if proposal is not None:
                proposals.append(proposal_to_dict(proposal))

        chunk.update_section("basin_proposals_section", {"proposals": proposals})

    @staticmethod
    def _arbitrate_proposals(chunk: CognitiveChunk) -> None:
        proposal_section = chunk.get_section_content("basin_proposals_section") or {}
        proposals = proposal_section.get("proposals", []) if isinstance(proposal_section, dict) else []
        if not isinstance(proposals, list) or not proposals:
            chunk.update_section("basin_arbitration_section", {
                "conflict_detected": False,
                "final_action_source": "global_default",
                "top_proposal_scores": [],
            })
            return

        scored: List[tuple[float, Dict[str, object]]] = []
        actions = []
        for p in proposals:
            if not isinstance(p, dict):
                continue
            conf = float(p.get("action_confidence", 0.0))
            eth = float(p.get("ethical_score", 0.0))
            score = 0.7 * conf + 0.3 * eth
            scored.append((score, p))
            actions.append(str(p.get("selected_action", "")))

        scored.sort(key=lambda x: (-x[0], str(x[1].get("basin_id", ""))))
        best_score, best = scored[0]
        conflict = len(set(actions)) > 1

        action_section = chunk.get_section_content("action_selection_section") or {}
        if action_section:
            action_section["selected_action"] = str(best.get("selected_action", action_section.get("selected_action", "global_default")))
            action_section["action_confidence"] = float(action_section.get("action_confidence", 0.0)) * 0.5 + best_score * 0.5
            action_section["action_reason"] = f"Arbitrated from basin proposals; winner={best.get('basin_id')}"
            action_section["final_action_source"] = str(best.get("basin_id", "global_default"))
            chunk.update_section("action_selection_section", action_section)

        chunk.update_section("basin_arbitration_section", {
            "conflict_detected": conflict,
            "final_action_source": str(best.get("basin_id", "global_default")),
            "top_proposal_scores": [
                {"basin_id": str(p.get("basin_id", "")), "score": float(s)}
                for s, p in scored[:3]
            ],
        })

    def run(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Execute the full pipeline, returning the enriched chunk."""
        timings: Dict[str, float] = {}
        selected_basins: List[Any] = []

        for block in self.blocks:
            if block.name == "MemoryStorage":
                selected_basins = self._attach_routing_context(chunk)
                self._run_basin_micro_pipelines(chunk, selected_basins)

            t0 = time.time()
            chunk = block.process(chunk)
            timings[block.name] = time.time() - t0

            if block.name == "InternalCommunication" and self.data_king_hook:
                t0 = time.time()
                chunk = self.data_king_hook.oversee(chunk)
                timings["DataKing"] = time.time() - t0

            if block.name == "EthicsValues" and self.ethics_king_hook:
                t0 = time.time()
                chunk = self.ethics_king_hook.oversee(chunk)
                timings["EthicsKing"] = time.time() - t0

            if block.name == "ActionSelection":
                if self.forefront_king_hook:
                    t0 = time.time()
                    chunk = self.forefront_king_hook.oversee(chunk)
                    timings["ForefrontKing"] = time.time() - t0
                if self.three_kings_hook:
                    t0 = time.time()
                    chunk = self.three_kings_hook.oversee(chunk)
                    timings["ThreeKings"] = time.time() - t0
                if self.basin_routing:
                    self._arbitrate_proposals(chunk)

        metrics = chunk.get_section_content("processing_metrics_section") or {}
        metrics["block_timings"] = timings
        chunk.update_section("processing_metrics_section", metrics)
        return chunk

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Alias for canonical process entrypoint."""
        return self.run(chunk)
