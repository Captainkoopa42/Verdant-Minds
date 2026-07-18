"""Integration tests for phase 7 ECWF-native boundary dynamics."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


def _run(tmp: Path, seed: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    cfg = RunnerConfig(
        cycles=40,
        provider="local",
        outdir=str(tmp),
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
    )
    run_dir = CultivationRunner(cfg).run([seed])
    lines = (run_dir / f"seed_{seed}" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    state = json.loads((run_dir / f"seed_{seed}" / "state.json").read_text(encoding="utf-8"))
    return rows, state


def _earlier_share(state: dict[str, object]) -> float:
    memory = state.get("memory_web", {})
    nodes = memory.get("memory_store", {}) if isinstance(memory, dict) else {}
    if not isinstance(nodes, dict):
        return 0.0

    total = 0
    earlier = 0
    for label, entry in nodes.items():
        if not (isinstance(label, str) and label.startswith("Emergent_")):
            continue
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        parent_concepts = metadata.get("parent_concepts", [])
        if not isinstance(parent_concepts, list) or not parent_concepts:
            continue
        creation_time = float(metadata.get("creation_time", 0.0))
        total += 1
        parent_times = []
        for p in parent_concepts:
            pentry = nodes.get(p)
            if not isinstance(pentry, dict):
                continue
            pmeta = pentry.get("metadata", {})
            if not isinstance(pmeta, dict):
                continue
            parent_times.append(float(pmeta.get("creation_time", pentry.get("first_seen", 0.0))))
        if parent_times and creation_time >= max(parent_times):
            earlier += 1
    return earlier / max(1, total)


def test_phase7_ecwf_boundary_determinism_and_dynamics(tmp_path: Path) -> None:
    rows1, state1 = _run(tmp_path / "run1", 2)
    rows2, state2 = _run(tmp_path / "run2", 2)

    assert [r["boundary_emergents_created"] for r in rows1] == [r["boundary_emergents_created"] for r in rows2]
    assert [r["bud_events_count"] for r in rows1] == [r["bud_events_count"] for r in rows2]
    assert [r["density_regulation_edges_removed"] for r in rows1] == [r["density_regulation_edges_removed"] for r in rows2]

    assert sum(int(r["boundary_emergents_created"]) for r in rows1) >= 1
    assert sum(int(r["bud_events_count"]) for r in rows1) >= 1
    assert sum(int(r["density_regulation_edges_removed"]) for r in rows1) >= 1

    for r in rows1:
        assert float(r["global_edge_ratio_after"]) <= float(r["global_edge_ratio_before"])

    assert _earlier_share(state1) > 0.95

    nodes = state1.get("memory_web", {}).get("memory_store", {})
    boundary_times = [
        float(entry.get("metadata", {}).get("creation_time", 0.0))
        for label, entry in nodes.items()
        if isinstance(label, str)
        and label.startswith("Emergent_boundary")
        and isinstance(entry, dict)
        and isinstance(entry.get("metadata", {}), dict)
        and entry["metadata"].get("ecwf_candidate") is True
    ]
    assert boundary_times
    assert all(bt > 0.0 and bt != int(bt) for bt in boundary_times)

    assert _earlier_share(state1) == _earlier_share(state2)
