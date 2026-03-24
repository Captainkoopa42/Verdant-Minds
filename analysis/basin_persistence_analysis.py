"""Analyze basin persistence trajectories from periodic ECWF + graph snapshots."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path as _PathBootstrap

sys.path.insert(0, str(_PathBootstrap(__file__).resolve().parents[1]))

from pathlib import Path
from typing import Any

from analysis.telemetry_analysis_common import load_jsonl, write_json

try:
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover - optional dependency at runtime
    plt = None


def _node_set(basin: dict[str, Any]) -> set[str]:
    return {str(node) for node in basin.get("nodes", []) if isinstance(node, str)}


def _edge_set(basin: dict[str, Any], *, restrict_to: set[str] | None = None) -> set[tuple[str, str]]:
    nodes = restrict_to
    result: set[tuple[str, str]] = set()
    for edge in basin.get("internal_edges", []):
        if not isinstance(edge, (list, tuple)) or len(edge) < 2:
            continue
        a, b = sorted((str(edge[0]), str(edge[1])))
        if nodes is not None and (a not in nodes or b not in nodes):
            continue
        result.add((a, b))
    return result


def _jaccard(left: set[Any], right: set[Any]) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    if not union:
        return 0.0
    return float(len(left & right) / len(union))


def _score_match(previous: dict[str, Any], current: dict[str, Any]) -> tuple[float, dict[str, float]]:
    prev_nodes = _node_set(previous)
    curr_nodes = _node_set(current)
    shared_nodes = prev_nodes & curr_nodes
    node_overlap = _jaccard(prev_nodes, curr_nodes)
    concept_identity = float(len(shared_nodes) / max(1, len(prev_nodes)))
    edge_similarity = _jaccard(
        _edge_set(previous, restrict_to=shared_nodes),
        _edge_set(current, restrict_to=shared_nodes),
    )
    score = (0.45 * node_overlap) + (0.35 * edge_similarity) + (0.20 * concept_identity)
    return score, {
        "node_overlap": node_overlap,
        "edge_structure_similarity": edge_similarity,
        "concept_identity_persistence": concept_identity,
        "persistence_score": score,
    }


def _find_match(
    previous: dict[str, Any],
    current_basins: list[dict[str, Any]],
    used_ids: set[str],
) -> tuple[dict[str, Any] | None, dict[str, float]]:
    previous_id = str(previous.get("basin_id", ""))
    by_id = {
        str(basin.get("basin_id", "")): basin
        for basin in current_basins
        if isinstance(basin, dict)
    }
    candidate = by_id.get(previous_id)
    if candidate is not None and previous_id not in used_ids:
        _, metrics = _score_match(previous, candidate)
        return candidate, metrics

    best_basin: dict[str, Any] | None = None
    best_metrics: dict[str, float] = {
        "node_overlap": 0.0,
        "edge_structure_similarity": 0.0,
        "concept_identity_persistence": 0.0,
        "persistence_score": 0.0,
    }
    best_score = -1.0
    for basin in current_basins:
        if not isinstance(basin, dict):
            continue
        basin_id = str(basin.get("basin_id", ""))
        if basin_id in used_ids:
            continue
        score, metrics = _score_match(previous, basin)
        if score > best_score:
            best_score = score
            best_basin = basin
            best_metrics = metrics

    if best_basin is None or best_metrics["node_overlap"] <= 0.0:
        return None, {
            "node_overlap": 0.0,
            "edge_structure_similarity": 0.0,
            "concept_identity_persistence": 0.0,
            "persistence_score": 0.0,
        }
    return best_basin, best_metrics


def analyze_snapshots(
    snapshots: list[dict[str, Any]],
    *,
    stable_score_threshold: float = 0.6,
    stable_presence_threshold: float = 0.7,
) -> dict[str, Any]:
    """Compute per-basin persistence trajectories across snapshots."""
    ordered = sorted(snapshots, key=lambda row: int(row.get("cycle_index", 0)))
    if not ordered:
        return {
            "snapshots_analyzed": 0,
            "snapshot_cycles": [],
            "per_snapshot_basins": [],
            "per_basin": {},
            "stable_basins": [],
            "dissolved_basins": [],
            "trajectory_summary": [],
        }

    per_snapshot_basins: list[dict[str, Any]] = []
    trajectories: dict[str, dict[str, Any]] = {}

    first_cycle = int(ordered[0].get("cycle_index", 0))
    total_cycles = [int(snapshot.get("cycle_index", 0)) for snapshot in ordered]

    for snapshot in ordered:
        basins = [basin for basin in snapshot.get("basins", []) if isinstance(basin, dict)]
        per_snapshot_basins.append(
            {
                "cycle_index": int(snapshot.get("cycle_index", 0)),
                "basin_count": len(basins),
                "basins": [
                    {
                        "basin_id": str(basin.get("basin_id")),
                        "size": int(basin.get("size", len(basin.get("nodes", [])))),
                        "emergent_count": int(basin.get("emergent_count", 0)),
                        "top_nodes": list(_node_set(basin))[:5],
                    }
                    for basin in basins
                ],
            }
        )
        for basin in basins:
            basin_id = str(basin.get("basin_id"))
            entry = trajectories.setdefault(
                basin_id,
                {
                    "basin_id": basin_id,
                    "birth_cycle": int(snapshot.get("cycle_index", 0)),
                    "presence_cycles": [],
                    "size_trajectory": [],
                    "transition_metrics": [],
                    "status": "active",
                    "dissolved_at_cycle": None,
                    "final_match_basin_id": basin_id,
                },
            )
            entry["presence_cycles"].append(int(snapshot.get("cycle_index", 0)))
            entry["size_trajectory"].append(
                {
                    "cycle_index": int(snapshot.get("cycle_index", 0)),
                    "size": int(basin.get("size", len(basin.get("nodes", [])))),
                    "emergent_count": int(basin.get("emergent_count", 0)),
                }
            )

    for previous_snapshot, current_snapshot in zip(ordered[:-1], ordered[1:]):
        current_basins = [basin for basin in current_snapshot.get("basins", []) if isinstance(basin, dict)]
        current_by_id = {str(basin.get("basin_id")): basin for basin in current_basins}
        used_ids: set[str] = set()
        for previous_basin in [basin for basin in previous_snapshot.get("basins", []) if isinstance(basin, dict)]:
            basin_id = str(previous_basin.get("basin_id"))
            trajectory = trajectories[basin_id]
            current_match, metrics = _find_match(previous_basin, current_basins, used_ids)
            transition = {
                "from_cycle": int(previous_snapshot.get("cycle_index", 0)),
                "to_cycle": int(current_snapshot.get("cycle_index", 0)),
                "matched_basin_id": (str(current_match.get("basin_id")) if current_match is not None else None),
                **metrics,
            }
            trajectory["transition_metrics"].append(transition)
            if current_match is not None:
                used_ids.add(str(current_match.get("basin_id")))
                trajectory["final_match_basin_id"] = str(current_match.get("basin_id"))
                continue
            if trajectory["dissolved_at_cycle"] is None:
                trajectory["dissolved_at_cycle"] = int(current_snapshot.get("cycle_index", 0))
                trajectory["status"] = "dissolved"

        for current_id, current_basin in current_by_id.items():
            if current_id in trajectories:
                continue
            trajectories[current_id] = {
                "basin_id": current_id,
                "birth_cycle": int(current_snapshot.get("cycle_index", 0)),
                "presence_cycles": [int(current_snapshot.get("cycle_index", 0))],
                "size_trajectory": [
                    {
                        "cycle_index": int(current_snapshot.get("cycle_index", 0)),
                        "size": int(current_basin.get("size", len(current_basin.get("nodes", [])))),
                        "emergent_count": int(current_basin.get("emergent_count", 0)),
                    }
                ],
                "transition_metrics": [],
                "status": "active",
                "dissolved_at_cycle": None,
                "final_match_basin_id": current_id,
            }

    final_cycle = total_cycles[-1]
    per_basin: dict[str, Any] = {}
    stable_basins: list[str] = []
    dissolved_basins: list[str] = []
    trajectory_summary: list[dict[str, Any]] = []

    for basin_id, trajectory in sorted(trajectories.items()):
        transitions = trajectory["transition_metrics"]
        avg_score = (
            float(sum(item["persistence_score"] for item in transitions) / len(transitions))
            if transitions
            else 1.0
        )
        avg_overlap = (
            float(sum(item["node_overlap"] for item in transitions) / len(transitions))
            if transitions
            else 1.0
        )
        avg_edge_similarity = (
            float(sum(item["edge_structure_similarity"] for item in transitions) / len(transitions))
            if transitions
            else 1.0
        )
        avg_identity = (
            float(sum(item["concept_identity_persistence"] for item in transitions) / len(transitions))
            if transitions
            else 1.0
        )

        visible_snapshots = len(trajectory["presence_cycles"])
        possible_snapshots = sum(1 for cycle in total_cycles if cycle >= trajectory["birth_cycle"])
        presence_fraction = float(visible_snapshots / max(1, possible_snapshots))
        stable = (
            bool(transitions)
            and (
            trajectory["dissolved_at_cycle"] is None
            and presence_fraction >= stable_presence_threshold
            and avg_score >= stable_score_threshold
            )
        )
        if stable:
            stable_basins.append(basin_id)
            trajectory["status"] = "stable"
        elif trajectory["dissolved_at_cycle"] is not None:
            dissolved_basins.append(basin_id)

        timeline_parts = []
        sizes_by_cycle = {item["cycle_index"]: item["size"] for item in trajectory["size_trajectory"]}
        for cycle in total_cycles:
            if cycle in sizes_by_cycle:
                timeline_parts.append(f"{cycle}:size={sizes_by_cycle[cycle]}")
            elif cycle > trajectory["birth_cycle"]:
                timeline_parts.append(f"{cycle}:dissolved")
        trajectory_summary.append(
            {
                "basin_id": basin_id,
                "timeline": " -> ".join(timeline_parts),
                "status": trajectory["status"],
            }
        )
        per_basin[basin_id] = {
            "birth_cycle": int(trajectory["birth_cycle"]),
            "final_cycle_observed": int(max(trajectory["presence_cycles"], default=trajectory["birth_cycle"])),
            "presence_cycles": list(trajectory["presence_cycles"]),
            "presence_fraction": presence_fraction,
            "mean_node_overlap": avg_overlap,
            "mean_edge_structure_similarity": avg_edge_similarity,
            "mean_concept_identity_persistence": avg_identity,
            "mean_persistence_score": avg_score,
            "transition_metrics": transitions,
            "stable": stable,
            "status": trajectory["status"],
            "dissolved_at_cycle": trajectory["dissolved_at_cycle"],
            "final_match_basin_id": trajectory["final_match_basin_id"],
        }

    return {
        "snapshots_analyzed": len(ordered),
        "snapshot_cycles": total_cycles,
        "first_cycle": first_cycle,
        "final_cycle": final_cycle,
        "per_snapshot_basins": per_snapshot_basins,
        "per_basin": per_basin,
        "stable_basins": stable_basins,
        "dissolved_basins": dissolved_basins,
        "trajectory_summary": trajectory_summary,
        "scoring": {
            "persistence_score": "0.45*node_overlap + 0.35*edge_structure_similarity + 0.20*concept_identity_persistence",
            "stable_score_threshold": stable_score_threshold,
            "stable_presence_threshold": stable_presence_threshold,
        },
    }


def render_summary_markdown(result: dict[str, Any]) -> str:
    """Create a compact human-readable basin trajectory report."""
    lines = [
        "# Basin persistence summary",
        "",
        f"- Snapshots analyzed: **{result.get('snapshots_analyzed', 0)}**",
        f"- Snapshot cycles: **{', '.join(str(cycle) for cycle in result.get('snapshot_cycles', []))}**",
        f"- Stable basins: **{', '.join(result.get('stable_basins', [])) or 'None'}**",
        f"- Dissolved basins: **{', '.join(result.get('dissolved_basins', [])) or 'None'}**",
        "",
        "## Per-basin persistence",
    ]
    for basin_id, payload in sorted((result.get("per_basin") or {}).items()):
        lines.extend(
            [
                f"### {basin_id}",
                f"- status: **{payload.get('status')}**",
                f"- mean persistence score: **{payload.get('mean_persistence_score', 0.0):.3f}**",
                f"- mean node overlap: **{payload.get('mean_node_overlap', 0.0):.3f}**",
                f"- mean edge structure similarity: **{payload.get('mean_edge_structure_similarity', 0.0):.3f}**",
                f"- mean concept identity persistence: **{payload.get('mean_concept_identity_persistence', 0.0):.3f}**",
                f"- presence cycles: **{payload.get('presence_cycles', [])}**",
                "",
            ]
        )
    lines.extend(["## Trajectories", ""])
    for item in result.get("trajectory_summary", []):
        lines.append(f"- **{item['basin_id']}** ({item['status']}): {item['timeline']}")
    lines.append("")
    return "\n".join(lines)


def plot_trajectories(result: dict[str, Any], outfile: Path) -> str | None:
    """Render a simple persistence trajectory chart when matplotlib is available."""
    if plt is None:
        return None

    per_basin = result.get("per_basin", {})
    if not isinstance(per_basin, dict) or not per_basin:
        return None

    plt.figure(figsize=(10, 6))
    plotted = 0
    for basin_id, payload in sorted(per_basin.items()):
        transitions = payload.get("transition_metrics", [])
        if not transitions:
            continue
        xs = [int(item["to_cycle"]) for item in transitions]
        ys = [float(item["persistence_score"]) for item in transitions]
        linestyle = "-" if payload.get("stable") else "--"
        plt.plot(xs, ys, marker="o", linestyle=linestyle, label=str(basin_id))
        plotted += 1

    plt.ylim(0.0, 1.05)
    plt.xlabel("Snapshot cycle")
    plt.ylabel("Persistence score")
    plt.title("Basin persistence trajectories")
    if 0 < plotted <= 12:
        plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    outfile.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outfile, dpi=160)
    plt.close()
    return str(outfile)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze longitudinal basin persistence from basin_snapshots.jsonl")
    parser.add_argument("--snapshots-jsonl", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--stable-score-threshold", type=float, default=0.6)
    parser.add_argument("--stable-presence-threshold", type=float, default=0.7)
    args = parser.parse_args()

    snapshots = load_jsonl(Path(args.snapshots_jsonl))
    result = analyze_snapshots(
        snapshots,
        stable_score_threshold=args.stable_score_threshold,
        stable_presence_threshold=args.stable_presence_threshold,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_json(outdir / "basin_persistence_summary.json", result)
    (outdir / "basin_persistence_summary.md").write_text(render_summary_markdown(result), encoding="utf-8")
    chart_path = plot_trajectories(result, outdir / "fig_basin_persistence_trajectories.png")
    if chart_path is not None:
        write_json(outdir / "basin_persistence_artifacts.json", {"trajectory_plot": chart_path})


if __name__ == "__main__":
    main()
