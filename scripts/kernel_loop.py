#!/usr/bin/env python3
import csv
import json
import time
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from usm import UnifiedSyntheticMind


def to_jsonable(obj):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if hasattr(obj, "tolist"):
        try:
            return to_jsonable(obj.tolist())
        except Exception:
            pass
    return str(obj)


def main():
    try:
        mind = UnifiedSyntheticMind(config={"initialize_knowledge": False})
    except TypeError:
        mind = UnifiedSyntheticMind()

    inputs = [
        "Hello Verdant.",
        "What is your current status?",
        "Summarize ethics considerations for AI.",
        "Give a cautious answer with uncertainty.",
        "What should we do next?",
    ]

    artifacts = Path("artifacts")
    chunks_dir = artifacts / "chunks"
    artifacts.mkdir(parents=True, exist_ok=True)
    chunks_dir.mkdir(parents=True, exist_ok=True)

    csv_path = artifacts / "kernel_log.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "iteration",
                "system_entropy",
                "glass_transition_temp",
                "housed_contradiction_index",
                "violation_rate",
                "alpha_crit_estimate",
                "mean_edge_delta_e",
            ],
        )
        writer.writeheader()

        last_mean_edge_delta_e = 0.0

        for i in range(1, 101):
            text = inputs[(i - 1) % len(inputs)]
            chunk = mind.process_input(text)

            metrics = chunk.get_section_content("processing_metrics_section") or {}
            coherence = chunk.get_section_content("coherence_invariants_section") or {}

            mean_edge_delta_e = last_mean_edge_delta_e
            if i % 10 == 0:
                delta_values = [
                    data.get("delta_e")
                    for _, _, data in mind.memory_web.graph.edges(data=True)
                    if data.get("delta_e") is not None
                ]
                if delta_values:
                    mean_edge_delta_e = sum(delta_values) / len(delta_values)
                else:
                    mean_edge_delta_e = 0.0
                last_mean_edge_delta_e = mean_edge_delta_e

            row = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "iteration": i,
                "system_entropy": metrics.get("system_entropy"),
                "glass_transition_temp": metrics.get("glass_transition_temp"),
                "housed_contradiction_index": coherence.get("housed_contradiction_index"),
                "violation_rate": coherence.get("violation_rate"),
                "alpha_crit_estimate": coherence.get("alpha_crit_estimate"),
                "mean_edge_delta_e": mean_edge_delta_e,
            }
            writer.writerow(row)

            if i % 10 == 0:
                snap = chunks_dir / f"chunk_{i}.json"
                snap.write_text(json.dumps(to_jsonable(chunk.sections), indent=2))

    print(f"wrote: {csv_path}")
    print(f"chunk snapshots in: {chunks_dir}")


if __name__ == "__main__":
    main()
