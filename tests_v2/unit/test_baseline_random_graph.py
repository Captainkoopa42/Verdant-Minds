"""Unit tests for random baseline temporal scaffolding generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from analysis.baseline_random_graph import BaselineConfig, build_baseline_state


def _write_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def test_baseline_state_has_emergents_timestamps_and_connections(tmp_path: Path) -> None:
    outdir = tmp_path / "seed_42"
    outdir.mkdir(parents=True, exist_ok=True)

    state = build_baseline_state(BaselineConfig(cycles=20, seed=42))
    state_path = outdir / "state.json"
    _write_state(state_path, state)

    loaded = json.loads(state_path.read_text(encoding="utf-8"))
    memory_store = loaded["memory_web"]["memory_store"]
    assert memory_store

    emergents = {k: v for k, v in memory_store.items() if k.startswith("Emergent_")}
    assert emergents
    assert all(item.get("created_at") is not None for item in emergents.values())

    total_connections = sum(len(item.get("connections", [])) for item in memory_store.values())
    assert total_connections > 0


def test_extract_scaffolding_metrics_runs_and_earlier_share_not_trivial(tmp_path: Path) -> None:
    seed_dir = tmp_path / "seed_7"
    seed_dir.mkdir(parents=True, exist_ok=True)

    state = build_baseline_state(BaselineConfig(cycles=20, seed=7))
    state_path = seed_dir / "state.json"
    _write_state(state_path, state)

    subprocess.run([
        sys.executable,
        "analysis/extract_scaffolding_metrics.py",
        "--state", str(state_path),
        "--outdir", str(seed_dir),
        "--orientation", "older_to_newer",
    ], check=True)

    metrics = json.loads((seed_dir / "metrics.json").read_text(encoding="utf-8"))
    assert "earlier_share" in metrics
    assert metrics["earlier_share"] is not None
    assert metrics["earlier_share"] < 0.95


def test_baseline_generation_is_deterministic_for_seed() -> None:
    config = BaselineConfig(cycles=20, seed=99)
    state_a = build_baseline_state(config)
    state_b = build_baseline_state(config)
    assert state_a == state_b
