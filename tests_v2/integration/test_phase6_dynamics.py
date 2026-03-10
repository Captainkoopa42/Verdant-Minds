"""Integration tests for phase 6 basin pressure dynamics."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


DYNAMICS_KEYS = {
    "pruned_edges_count",
    "pruned_basin_id",
    "basin_density_before",
    "basin_density_after",
    "bud_events_count",
    "bud_parent_basin_id",
    "bud_new_basin_id",
    "bud_new_basin_size",
    "basin_pressure_values",
    "boundary_emergents_created",
    "boundary_pairs",
}


def _run(tmp: Path, seed: int) -> list[dict[str, object]]:
    cfg = RunnerConfig(
        cycles=20,
        provider="local",
        outdir=str(tmp),
        basin_routing=True,
        enable_pruning=True,
        enable_budding=True,
        enable_boundary_emergence=True,
        basin_prune_interval=3,
        basin_prune_top_k=4,
        basin_bud_interval=4,
        basin_pressure_threshold=0.0001,
        basin_split_fraction=0.2,
        basin_min_size_for_split=5,
        basin_min_age_for_split=2,
        boundary_emergence_threshold=0.01,
        boundary_cooldown_cycles=2,
    )
    run_dir = CultivationRunner(cfg).run([seed])
    lines = (run_dir / f"seed_{seed}" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def test_phase6_dynamics_emits_events_and_is_deterministic(tmp_path: Path) -> None:
    rows1 = _run(tmp_path / "run1", 0)
    rows2 = _run(tmp_path / "run2", 0)

    assert all(DYNAMICS_KEYS.issubset(set(r.keys())) for r in rows1)

    p1 = [int(r.get("pruned_edges_count", 0)) for r in rows1]
    p2 = [int(r.get("pruned_edges_count", 0)) for r in rows2]
    b1 = [int(r.get("bud_events_count", 0)) for r in rows1]
    b2 = [int(r.get("bud_events_count", 0)) for r in rows2]
    e1 = [int(r.get("boundary_emergents_created", 0)) for r in rows1]
    e2 = [int(r.get("boundary_emergents_created", 0)) for r in rows2]

    assert p1 == p2
    assert b1 == b2
    assert e1 == e2

    assert sum(p1) >= 1
    assert sum(b1) >= 1
    assert sum(e1) >= 1
