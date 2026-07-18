from __future__ import annotations

from analysis.basin_persistence_analysis import analyze_snapshots


def test_analyze_snapshots_tracks_stable_and_dissolved_basins() -> None:
    snapshots = [
        {
            "cycle_index": 9,
            "basins": [
                {
                    "basin_id": "basin_a",
                    "nodes": ["a", "b", "c"],
                    "internal_edges": [["a", "b", 1.0], ["b", "c", 1.0]],
                    "size": 3,
                    "emergent_count": 1,
                },
                {
                    "basin_id": "basin_b",
                    "nodes": ["x", "y", "z"],
                    "internal_edges": [["x", "y", 1.0], ["y", "z", 1.0]],
                    "size": 3,
                    "emergent_count": 1,
                },
            ],
        },
        {
            "cycle_index": 19,
            "basins": [
                {
                    "basin_id": "basin_a",
                    "nodes": ["a", "b", "c", "d"],
                    "internal_edges": [["a", "b", 1.0], ["b", "c", 1.0], ["c", "d", 1.0]],
                    "size": 4,
                    "emergent_count": 2,
                },
                {
                    "basin_id": "basin_c",
                    "nodes": ["m", "n", "o"],
                    "internal_edges": [["m", "n", 1.0], ["n", "o", 1.0]],
                    "size": 3,
                    "emergent_count": 1,
                },
            ],
        },
        {
            "cycle_index": 29,
            "basins": [
                {
                    "basin_id": "basin_a",
                    "nodes": ["a", "b", "c", "d"],
                    "internal_edges": [["a", "b", 1.0], ["b", "c", 1.0], ["c", "d", 1.0]],
                    "size": 4,
                    "emergent_count": 2,
                }
            ],
        },
    ]

    result = analyze_snapshots(snapshots, stable_score_threshold=0.5, stable_presence_threshold=0.6)

    assert "basin_a" in result["stable_basins"]
    assert "basin_b" in result["dissolved_basins"]
    assert result["per_basin"]["basin_a"]["mean_node_overlap"] > 0.7
    assert result["per_basin"]["basin_b"]["dissolved_at_cycle"] == 19
