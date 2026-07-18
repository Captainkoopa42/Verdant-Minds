"""Integration tests for Phase 3 cultivation runner."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def _load_summary(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_cultivation_runner_outputs_and_determinism(tmp_path: Path) -> None:
    """Two-seed run writes artifacts and is deterministic for local provider."""
    config = RunnerConfig(cycles=10, provider="local", outdir=str(tmp_path / "out"), pressure_every=4)

    run1 = CultivationRunner(config).run([0, 1])

    for seed in (0, 1):
        seed_dir = run1 / f"seed_{seed}"
        assert (seed_dir / "state.json").exists()
        assert (seed_dir / "cycles.jsonl").exists()
        assert (seed_dir / "summary.json").exists()

        lines = (seed_dir / "cycles.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 10
        first = json.loads(lines[0])
        assert first["cycle_index"] == 0
        assert first["seed"] == seed
        assert "entropy" in first
        assert "hci" in first
        assert "emergent_count" in first

    # determinism check on same seed/config (excluding timestamp-bearing paths)
    run2 = CultivationRunner(config).run([0])
    s1 = _load_summary(run1 / "seed_0" / "summary.json")
    s2 = _load_summary(run2 / "seed_0" / "summary.json")

    for k in ("cycles", "provider", "phase_counts", "final_t_g", "final_phase", "avg_entropy", "avg_hci", "emergent_count", "memory_size"):
        assert s1[k] == s2[k]
