"""Integration tests for the self-referential cultivation loop."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def _load_rows(run_dir: Path) -> list[dict[str, object]]:
    lines = (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _earlier_share(state: dict[str, object]) -> float:
    memory = state.get("memory_web", {}) if isinstance(state, dict) else {}
    nodes = memory.get("memory_store", {}) if isinstance(memory, dict) else {}
    total = 0
    earlier = 0
    for label, entry in nodes.items():
        if not (isinstance(label, str) and label.startswith("Emergent_")):
            continue
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata", {}) if isinstance(entry.get("metadata"), dict) else {}
        parents = metadata.get("parent_concepts", [])
        if not isinstance(parents, list) or not parents:
            continue
        creation_time = float(metadata.get("creation_time", entry.get("first_seen", 0.0)))
        parent_times = []
        for parent in parents:
            pentry = nodes.get(parent)
            if not isinstance(pentry, dict):
                continue
            pmeta = pentry.get("metadata", {}) if isinstance(pentry.get("metadata"), dict) else {}
            parent_times.append(float(pmeta.get("creation_time", pentry.get("first_seen", 0.0))))
        if parent_times:
            total += 1
            if creation_time >= max(parent_times):
                earlier += 1
    return earlier / max(1, total)


def _run(tmp_path: Path, interval: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    cfg = RunnerConfig(
        cycles=100,
        provider="local",
        outdir=str(tmp_path),
        basin_routing=True,
        enable_pruning=True,
        enable_budding=True,
        enable_boundary_emergence=True,
        basin_prune_interval=3,
        basin_bud_interval=4,
        basin_pressure_threshold=0.001,
        basin_split_fraction=0.2,
        basin_min_size_for_split=5,
        basin_min_age_for_split=2,
        boundary_emergence_threshold=0.01,
        boundary_cooldown_cycles=2,
        boundary_use_ecwf=True,
        density_regulation_enabled=True,
        density_max_edge_ratio=20.0,
        density_target_edge_ratio=10.0,
        self_reflect_interval=interval,
    )
    run_dir = CultivationRunner(cfg).run([0])
    rows = _load_rows(run_dir)
    state = json.loads((run_dir / "seed_0" / "state.json").read_text(encoding="utf-8"))
    return rows, state


def test_self_concepts_emerge(tmp_path: Path) -> None:
    rows, state = _run(tmp_path / "self_concepts", interval=20)
    reflection_inputs = [str(row["self_reflection_input"]).lower() for row in rows if row["is_self_reflection"] is True]
    assert reflection_inputs
    assert any("basin" in text and "t_g" in text for text in reflection_inputs)

    memory = state["memory_web"]["memory_store"]
    emergent_names = [name.lower() for name in memory if isinstance(name, str) and name.startswith("Emergent_")]
    reflection_terms = ("basin", "boundary", "coherence", "identity", "autonomy", "constraint")
    assert any(any(term in name for term in reflection_terms) for name in emergent_names)


def test_earlier_share_with_self_reflection(tmp_path: Path) -> None:
    rows, state = _run(tmp_path / "validation", interval=25)

    assert any(row["is_self_reflection"] is True for row in rows)
    assert _earlier_share(state) == 1.0
