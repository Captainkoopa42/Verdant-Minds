from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig
from verdant.system import VerdantSystem


def test_daughter_persistence_under_detection(tmp_path: Path) -> None:
    config = RunnerConfig(
        cycles=40,
        provider="local",
        outdir=str(tmp_path / "out"),
        basin_routing=True,
        enable_pruning=True,
        enable_budding=True,
        enable_boundary_emergence=True,
        basin_pressure_threshold=0.001,
        basin_use_registry=True,
        fast_bridge=True,
    )
    run_dir = CultivationRunner(config).run([0])
    state = json.loads((run_dir / "seed_0" / "state.json").read_text(encoding="utf-8"))
    registry = state["extra"]["basin_registry"]
    basins = registry["basins"]

    assert any(event["event_type"] == "budded" for event in registry["history"])
    daughters = [basin for basin in basins.values() if basin.get("parent_id")]
    assert daughters
    assert all("emergent_count_peak" in basin for basin in daughters)


def test_long_run_stability(tmp_path: Path) -> None:
    config = RunnerConfig(
        cycles=100,
        provider="local",
        outdir=str(tmp_path / "out"),
        basin_routing=True,
        basin_use_registry=True,
        fast_bridge=True,
    )
    run_dir = CultivationRunner(config).run([0])
    summary = json.loads((run_dir / "seed_0" / "summary.json").read_text(encoding="utf-8"))
    cycles = [json.loads(line) for line in (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    last = cycles[-1]
    system = VerdantSystem.load_checkpoint(str(run_dir / "seed_0" / "state.json"))

    assert summary["cycles"] == 100
    assert system.get_scaffold_context().earlier_share == 1.0
    assert last["cycle_time_seconds"] >= 0.0
    assert last["graph_edges"] >= 0
    assert last["basin_registry_active"] >= 0
