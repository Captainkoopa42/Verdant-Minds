"""System visualization utilities for Verdant-Minds.

This module provides a lightweight ``SystemVisualizer`` class used to
collect per-cycle metrics during tests and render a handful of summary
plots.  The goal is to aid manual inspection rather than provide a fully
fledged analytics suite, so the implementation intentionally keeps
dependencies and logic minimal.

The visualizer records information each time ``log_cycle_data`` is
called.  After all cycles have completed ``generate_visual_report`` can
be invoked to create a set of matplotlib figures such as:

* Confidence score over time
* Ethical status heatmap
* Memory activity per cycle
* Block processing time bar chart
* Simple chunk linkage graph (requires ``networkx``; skipped if missing)

All artefacts are written to the provided ``output_path``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List

import matplotlib.pyplot as plt

try:  # ``networkx`` is optional – the visualizer still works without it
    import networkx as nx  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    nx = None  # type: ignore


@dataclass
class SystemVisualizer:
    """Collects cycle data and renders diagnostic plots."""

    cycles: List[Dict[str, Any]] = field(default_factory=list)

    def log_cycle_data(self, data: Dict[str, Any]) -> None:
        """Record metrics for a single processing cycle."""

        self.cycles.append(data)

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------
    def _plot_confidence_timeline(self, output_path: str) -> None:
        cycles = [c["cycle"] for c in self.cycles]
        confidences = [c.get("confidence", 0) for c in self.cycles]

        plt.figure()
        plt.plot(cycles, confidences, marker="o")
        plt.xlabel("Cycle")
        plt.ylabel("Confidence")
        plt.title("Confidence over Time")
        plt.grid(True, alpha=0.3)
        plt.savefig(os.path.join(output_path, "confidence_timeline.png"))
        plt.close()

    def _plot_ethics_heatmap(self, output_path: str) -> None:
        statuses = list({c.get("ethics", "unknown") for c in self.cycles})
        status_to_idx = {s: i for i, s in enumerate(statuses)}

        heatmap = [[0 for _ in statuses] for _ in self.cycles]
        for row, c in enumerate(self.cycles):
            col = status_to_idx.get(c.get("ethics", "unknown"), 0)
            heatmap[row][col] = 1

        plt.figure()
        plt.imshow(heatmap, aspect="auto", interpolation="nearest")
        plt.yticks(range(len(self.cycles)), [c["cycle"] for c in self.cycles])
        plt.xticks(range(len(statuses)), statuses, rotation=45, ha="right")
        plt.title("Ethical State by Cycle")
        plt.xlabel("Ethical Status")
        plt.ylabel("Cycle")
        plt.colorbar(label="Presence")
        plt.tight_layout()
        plt.savefig(os.path.join(output_path, "ethical_state_heatmap.png"))
        plt.close()

    def _plot_memory_activity(self, output_path: str) -> None:
        cycles = [c["cycle"] for c in self.cycles]
        deltas = [c.get("memory_delta", 0) for c in self.cycles]

        plt.figure()
        plt.bar(cycles, deltas)
        plt.xlabel("Cycle")
        plt.ylabel("Memory Delta")
        plt.title("Memory Activity per Cycle")
        plt.savefig(os.path.join(output_path, "memory_activity.png"))
        plt.close()

    def _plot_block_activity(self, output_path: str) -> None:
        if not self.cycles:
            return

        blocks = sorted(self.cycles[0].get("active_blocks", {}).keys())
        data = {b: [c.get("active_blocks", {}).get(b, 0) for c in self.cycles] for b in blocks}

        x = range(len(self.cycles))
        plt.figure()
        for b in blocks:
            plt.plot(x, data[b], marker="o", label=b)
        plt.xlabel("Cycle Index")
        plt.ylabel("Time (s)")
        plt.title("Block Processing Times")
        plt.legend()
        plt.savefig(os.path.join(output_path, "block_activity.png"))
        plt.close()

    def _plot_chunk_linkage(self, output_path: str) -> None:
        if nx is None:  # pragma: no cover - optional dependency
            return

        g = nx.DiGraph()
        ids = [c.get("chunk") for c in self.cycles]
        for i in range(len(ids) - 1):
            g.add_edge(ids[i], ids[i + 1])

        plt.figure()
        pos = nx.spring_layout(g)
        nx.draw(g, pos, with_labels=True, node_color="#A0CBE2")
        plt.title("Chunk Linkage Graph")
        plt.savefig(os.path.join(output_path, "chunk_linkage.png"))
        plt.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_visual_report(self, output_path: str = "verdant_test_output") -> None:
        """Render all visualisations to ``output_path``.

        Parameters
        ----------
        output_path:
            Directory where generated images will be saved.  The directory
            is created if it does not already exist.
        """

        if not self.cycles:
            return

        os.makedirs(output_path, exist_ok=True)

        self._plot_confidence_timeline(output_path)
        self._plot_ethics_heatmap(output_path)
        self._plot_memory_activity(output_path)
        self._plot_block_activity(output_path)
        self._plot_chunk_linkage(output_path)

