"""Compare a self-reflective Verdant run against a baseline run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.detect_self_referential_concepts import detect_self_referential_concepts
from analysis.extract_scaffolding_metrics import load_graph
from analysis.semantic_evaluation import evaluate_semantics
from analysis.telemetry_analysis_common import load_cycles, resolve_run_dir, write_json
from analysis.extract_emergent_concepts import extract_emergent_concepts
from analysis.state_adapter import VerdantState


def _run_metrics(seed_dir: Path) -> dict[str, Any]:
    state_path = seed_dir / "state.json"
    cycles_path = seed_dir / "cycles.jsonl"
    vs = VerdantState.load(state_path)
    _, edges = load_graph(str(state_path))
    concepts = extract_emergent_concepts(state_path, basins_path=seed_dir / "basins.json")
    semantic = evaluate_semantics(concepts, mode="local")
    rows = load_cycles(cycles_path)
    self_analysis = detect_self_referential_concepts(state_path, cycles_path)

    node_map = {str(node["name"]): node for node in vs.nodes}
    total_parent_links = 0
    earlier_parent_links = 0
    for node in vs.emergent_nodes:
        creation_time = node.get("creation_time")
        if creation_time is None:
            continue
        metadata = node.get("metadata", {}) if isinstance(node.get("metadata"), dict) else {}
        parents = metadata.get("parent_concepts", [])
        if not isinstance(parents, list):
            continue
        for parent in parents:
            parent_node = node_map.get(str(parent))
            if parent_node is None:
                continue
            parent_time = parent_node.get("creation_time")
            if parent_time is None:
                continue
            total_parent_links += 1
            earlier_parent_links += int(float(parent_time) <= float(creation_time))
    earlier_share = (earlier_parent_links / total_parent_links) if total_parent_links else 1.0

    reflection_cycles = [int(row.get("cycle_index", 0)) for row in rows if bool(row.get("is_self_reflection", False))]
    first_reflection = reflection_cycles[0] if reflection_cycles else None
    before = [int(row.get("emergent_count", 0)) for row in rows if first_reflection is None or int(row.get("cycle_index", 0)) < first_reflection]
    after = [int(row.get("emergent_count", 0)) for row in rows if first_reflection is not None and int(row.get("cycle_index", 0)) >= first_reflection]
    before_rate = (before[-1] - before[0]) / max(1, len(before) - 1) if len(before) >= 2 else 0.0
    after_rate = (after[-1] - after[0]) / max(1, len(after) - 1) if len(after) >= 2 else 0.0

    return {
        "state_path": str(state_path),
        "cycles_path": str(cycles_path),
        "earlier_share": earlier_share,
        "emergent_count": vs.emergent_count,
        "basin_count": len(vs.basins) if isinstance(vs.basins, list) else 0,
        "semantic_coherence": float(semantic.get("scores", {}).get("mean_score", 0.0)),
        "self_referential_concepts": int(self_analysis.get("self_referential_count", 0)),
        "development_rate_change": after_rate - before_rate,
        "edges": len(edges),
    }


def compare_runs(self_run: Path, baseline_run: Path, seeds: int) -> dict[str, Any]:
    self_metrics = []
    baseline_metrics = []
    for seed in range(seeds):
        self_seed = self_run / f"seed_{seed}"
        baseline_seed = baseline_run / f"seed_{seed}"
        if self_seed.exists():
            self_metrics.append({"seed": seed, **_run_metrics(self_seed)})
        if baseline_seed.exists():
            baseline_metrics.append({"seed": seed, **_run_metrics(baseline_seed)})

    def _mean(rows: list[dict[str, Any]], key: str) -> float:
        if not rows:
            return 0.0
        return sum(float(row.get(key, 0.0)) for row in rows) / len(rows)

    return {
        "self_run": str(self_run),
        "baseline_run": str(baseline_run),
        "seeds_analyzed": min(len(self_metrics), len(baseline_metrics)),
        "self_reflection": {
            "per_seed": self_metrics,
            "earlier_share": _mean(self_metrics, "earlier_share"),
            "emergent_count": _mean(self_metrics, "emergent_count"),
            "basin_count": _mean(self_metrics, "basin_count"),
            "semantic_coherence": _mean(self_metrics, "semantic_coherence"),
            "self_referential_concepts": _mean(self_metrics, "self_referential_concepts"),
            "development_rate_change": _mean(self_metrics, "development_rate_change"),
        },
        "baseline": {
            "per_seed": baseline_metrics,
            "earlier_share": _mean(baseline_metrics, "earlier_share"),
            "emergent_count": _mean(baseline_metrics, "emergent_count"),
            "basin_count": _mean(baseline_metrics, "basin_count"),
            "semantic_coherence": _mean(baseline_metrics, "semantic_coherence"),
            "self_referential_concepts": _mean(baseline_metrics, "self_referential_concepts"),
            "development_rate_change": _mean(baseline_metrics, "development_rate_change"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare self-reflection runs against a baseline")
    parser.add_argument("--self-run", required=True)
    parser.add_argument("--baseline-run", required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--outfile", required=True)
    args = parser.parse_args()

    payload = compare_runs(resolve_run_dir(args.self_run), resolve_run_dir(args.baseline_run), args.seeds)
    write_json(Path(args.outfile), payload)
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
