"""Run semantic evaluation across multiple Verdant seeds and aggregate the results."""

from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.extract_emergent_concepts import extract_emergent_concepts
from analysis.semantic_evaluation import evaluate_semantics


def _resolve_state_paths(run_dir_pattern: str, seeds: int | None = None) -> list[tuple[int | None, Path]]:
    paths: list[tuple[int | None, Path]] = []
    for raw_match in sorted(glob.glob(run_dir_pattern)):
        run_root = Path(raw_match)
        if run_root.is_file() and run_root.name == "state.json":
            paths.append((None, run_root))
            continue
        for state_path in sorted(run_root.glob("seed_*/state.json")):
            seed_name = state_path.parent.name
            seed_value = int(seed_name.split("seed_")[-1]) if seed_name.startswith("seed_") else None
            paths.append((seed_value, state_path))
    paths.sort(key=lambda item: (item[0] is None, item[0] if item[0] is not None else 10**9, str(item[1])))
    if seeds is not None:
        return paths[:seeds]
    return paths


def _aggregate(seed_results: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    total = sum(int(result["semantic"]["total_evaluated"]) for result in seed_results)
    meaningful = sum(int(result["semantic"]["scores"]["meaningful_count"]) for result in seed_results)
    partial = sum(int(result["semantic"]["scores"]["partial_count"]) for result in seed_results)
    not_meaningful = sum(int(result["semantic"]["scores"]["not_meaningful_count"]) for result in seed_results)
    weighted_score_sum = sum(
        float(result["semantic"]["scores"]["mean_score"]) * int(result["semantic"]["total_evaluated"]) for result in seed_results
    )

    basin_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"score_sum": 0.0, "total_count": 0})
    concepts_all: list[dict[str, Any]] = []
    per_seed: list[dict[str, Any]] = []
    for result in seed_results:
        seed = result.get("seed")
        semantic = result["semantic"]
        per_seed.append(
            {
                "seed": seed,
                "meaningful_fraction": semantic["scores"]["meaningful_fraction"],
                "partial_fraction": semantic["scores"]["partial_fraction"],
                "not_meaningful_fraction": semantic["scores"]["not_meaningful_fraction"],
                "mean_score": semantic["scores"]["mean_score"],
                "total_evaluated": semantic["total_evaluated"],
                "state_path": semantic.get("state_path"),
            }
        )
        for concept in semantic.get("per_concept", []):
            merged = dict(concept)
            merged["seed"] = seed
            concepts_all.append(merged)
        for basin_id, basin_payload in semantic.get("by_basin", {}).items():
            basin_totals[basin_id]["score_sum"] += float(basin_payload["mean_score"]) * int(basin_payload["count"])
            basin_totals[basin_id]["total_count"] += int(basin_payload["count"])

    by_basin_overall = {
        basin_id: {
            "mean_score": round(payload["score_sum"] / payload["total_count"], 4),
            "total_count": int(payload["total_count"]),
        }
        for basin_id, payload in sorted(basin_totals.items())
        if int(payload["total_count"]) > 0
    }

    return {
        "seeds_analyzed": len(seed_results),
        "mode": mode,
        "overall_meaningful_fraction": round(meaningful / total, 4) if total else 0.0,
        "overall_partial_fraction": round(partial / total, 4) if total else 0.0,
        "overall_not_meaningful_fraction": round(not_meaningful / total, 4) if total else 0.0,
        "overall_mean_score": round(weighted_score_sum / total, 4) if total else 0.0,
        "total_concepts_evaluated": total,
        "per_seed": per_seed,
        "by_basin_overall": by_basin_overall,
        "all_concepts": concepts_all,
    }


def run_semantic_evaluation(
    run_dir_pattern: str,
    outdir: Path,
    *,
    seeds: int | None = None,
    mode: str = "local",
    backend: str | None = None,
    model: str | None = None,
    sleep_seconds: float = 1.0,
) -> dict[str, Any]:
    state_paths = _resolve_state_paths(run_dir_pattern, seeds=seeds)
    if not state_paths:
        raise FileNotFoundError(f"No seed state.json files matched pattern: {run_dir_pattern}")

    outdir.mkdir(parents=True, exist_ok=True)
    seed_results: list[dict[str, Any]] = []
    for fallback_idx, (seed, state_path) in enumerate(state_paths):
        resolved_seed = seed if seed is not None else fallback_idx
        seed_dir = outdir / f"seed_{resolved_seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        concepts = extract_emergent_concepts(state_path, basins_path=state_path.parent / "basins.json")
        semantic = evaluate_semantics(concepts, mode=mode, backend=backend, model=model, sleep_seconds=sleep_seconds)
        (seed_dir / "emergent_concepts.json").write_text(json.dumps(concepts, indent=2), encoding="utf-8")
        (seed_dir / "semantic_evaluation.json").write_text(json.dumps(semantic, indent=2), encoding="utf-8")
        seed_results.append({"seed": resolved_seed, "state_path": str(state_path), "concepts": concepts, "semantic": semantic})

    aggregate = _aggregate(seed_results, mode)
    (outdir / "aggregate_semantic.json").write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    return aggregate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run semantic evaluation across multiple seeds")
    parser.add_argument("--run-dir", required=True, help="Glob pattern matching run directories that contain seed_*/state.json")
    parser.add_argument("--seeds", type=int, default=None)
    parser.add_argument("--mode", choices=["local", "llm"], default="local")
    parser.add_argument("--backend", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    args = parser.parse_args()

    aggregate = run_semantic_evaluation(
        args.run_dir,
        Path(args.outdir),
        seeds=args.seeds,
        mode=args.mode,
        backend=args.backend,
        model=args.model,
        sleep_seconds=args.sleep_seconds,
    )
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
