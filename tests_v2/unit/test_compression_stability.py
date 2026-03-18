"""Unit tests for compression and stability post-hoc analyses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from analysis.compression_analysis import select_compression_proxy
from analysis.stability_analysis import (
    classify_trend,
    compute_growth_contraction,
    rolling_stability_ratio,
)
from analysis.telemetry_analysis_common import lagged_correlations, load_cycles


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_compression_proxy_extraction(tmp_path: Path) -> None:
    cycles_path = tmp_path / "cycles.jsonl"
    rows = [
        {"cycle_index": 0, "memory_size": 10, "basin_density_before": 0.10},
        {"cycle_index": 1, "memory_size": 11, "basin_density_before": None},
        {"cycle_index": 2, "memory_size": 12, "basin_density_before": 0.40},
    ]
    _write_jsonl(cycles_path, rows)

    proxy_type, proxy = select_compression_proxy(load_cycles(cycles_path))

    assert proxy_type == "basin_density_before"
    assert proxy == pytest.approx([0.10, 0.25, 0.40])


def test_lag_correlation() -> None:
    signal_a = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    signal_b = [0.0, 0.0, 0.0, 1.0, 0.0, 1.0]

    corrs = lagged_correlations(signal_a, signal_b, max_lag=4)
    peak_lag = max(range(len(corrs)), key=lambda idx: corrs[idx])

    assert peak_lag == 2


def test_stability_ratio() -> None:
    rows = []
    emergent_count = 0
    for cycle in range(6):
        emergent_count += 2
        rows.append(
            {
                "cycle_index": cycle,
                "emergent_count": emergent_count,
                "memory_size": 20,
                "pruned_edges_count": 5,
                "density_regulation_edges_removed": 0,
                "removed_nodes_count": 0,
                "global_edge_ratio_before": 1.0 + (0.25 * cycle),
            }
        )

    signals = compute_growth_contraction(rows)
    node_cycles, node_ratio = rolling_stability_ratio(
        signals["emergent_births"],
        signals["removed_nodes_count"],
        window=3,
    )
    edge_cycles, edge_ratio = rolling_stability_ratio(
        signals["edges_created"],
        [p + d for p, d in zip(signals["pruned_edges_count"], signals["density_regulation_edges_removed"])],
        window=3,
    )

    assert node_cycles == [2, 3, 4, 5]
    assert node_ratio[-1] == pytest.approx(2.0 / 1e-6)
    assert edge_ratio[-1] == pytest.approx(2.0)


def test_trend_detection() -> None:
    homeostatic, _ = classify_trend([1.8, 1.4, 1.15, 1.05, 1.01])
    growing, _ = classify_trend([0.7, 0.9, 1.2, 1.5, 1.9])

    assert homeostatic == "homeostatic"
    assert growing == "growing"
