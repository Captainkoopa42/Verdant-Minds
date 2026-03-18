from __future__ import annotations

from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig
from verdant_v2.system import VerdantConfig, VerdantSystem


def _run_cycles(system: VerdantSystem, start: int, count: int) -> None:
    for cycle in range(start, start + count):
        system.process_input(f"Cycle {cycle}: memory ethics emergence continuity.")


def test_save_load_checkpoint(tmp_path: Path) -> None:
    system = VerdantSystem(VerdantConfig(seed=11, basin_use_registry=True, fast_bridge=True))
    _run_cycles(system, 0, 10)

    checkpoint = tmp_path / "checkpoint_10.json"
    system.save_checkpoint(str(checkpoint))
    loaded = VerdantSystem.load_checkpoint(str(checkpoint))

    _run_cycles(system, 10, 5)
    _run_cycles(loaded, 10, 5)

    for key in ("cycle_count", "memory_concepts", "emergent_nodes", "basin_count", "largest_basin_size"):
        assert loaded.get_metrics()[key] == system.get_metrics()[key]
    assert loaded._basin_registry.to_dict() == system._basin_registry.to_dict()
    assert set(loaded.memory_web.list_concepts()) == set(system.memory_web.list_concepts())
    assert set(loaded.memory_web.graph.edges()) == set(system.memory_web.graph.edges())


def test_checkpoint_cli(tmp_path: Path) -> None:
    config = RunnerConfig(
        cycles=10,
        provider="local",
        outdir=str(tmp_path / "out"),
        checkpoint_interval=5,
        basin_use_registry=True,
        fast_bridge=True,
    )
    run_dir = CultivationRunner(config).run([0])
    seed_dir = run_dir / "seed_0"

    assert (seed_dir / "checkpoint_5.json").exists()
    assert (seed_dir / "checkpoint_10.json").exists()
