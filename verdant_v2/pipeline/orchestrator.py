"""Pipeline orchestrator — runs a CognitiveChunk through all nine blocks.

The orchestrator holds references to block instances and runs them in
the canonical order.  Governance hooks are applied between blocks as
specified by v1.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from verdant_v2.pipeline.chunk import CognitiveChunk


@runtime_checkable
class Block(Protocol):
    """Protocol every pipeline block must satisfy."""

    name: str

    def process(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Process *chunk* and return the (possibly modified) chunk."""
        ...


class PipelineOrchestrator:
    """Runs a chunk through the nine-block pipeline in order.

    Accepts optional governance hooks that are called between blocks at
    the canonical positions (after InternalCommunication, after EthicsValues,
    after ActionSelection).
    """

    def __init__(
        self,
        blocks: List[Block],
        *,
        data_king_hook: Optional[Any] = None,
        ethics_king_hook: Optional[Any] = None,
        forefront_king_hook: Optional[Any] = None,
        three_kings_hook: Optional[Any] = None,
    ) -> None:
        self.blocks = blocks
        self.data_king_hook = data_king_hook
        self.ethics_king_hook = ethics_king_hook
        self.forefront_king_hook = forefront_king_hook
        self.three_kings_hook = three_kings_hook

    def run(self, chunk: CognitiveChunk) -> CognitiveChunk:
        """Execute the full pipeline, returning the enriched chunk."""
        timings: Dict[str, float] = {}

        for block in self.blocks:
            t0 = time.time()
            chunk = block.process(chunk)
            timings[block.name] = time.time() - t0

            # Governance hooks at canonical positions
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

        # Record processing timings
        metrics = chunk.get_section_content("processing_metrics_section") or {}
        metrics["block_timings"] = timings
        chunk.update_section("processing_metrics_section", metrics)
        return chunk
