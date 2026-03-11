"""Integration tests for phase 8 scaffold-aware tutor provider."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.runner import CultivationRunner, RunnerConfig


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


def _run(tmp: Path, provider: str, tutor_backend: str = "local") -> tuple[list[dict[str, object]], dict[str, object]]:
    cfg = RunnerConfig(
        cycles=20,
        provider=provider,
        tutor_backend=tutor_backend,
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
    run_dir = CultivationRunner(cfg).run([0])
    lines = (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    state = json.loads((run_dir / "seed_0" / "state.json").read_text(encoding="utf-8"))
    return rows, state


def test_phase8_tutor_local_backend_and_baseline(tmp_path: Path) -> None:
    tutor_rows, tutor_state = _run(tmp_path / "tutor", provider="tutor", tutor_backend="local")
    baseline_rows, _ = _run(tmp_path / "baseline", provider="local")

    assert len(tutor_rows) == 20
    assert tutor_rows[0]["tutor_enabled"] is True
    assert tutor_rows[0]["tutor_backend"] == "local"
    assert "tutor_fallback" in tutor_rows[0]
    assert "tutor_input_length" in tutor_rows[0]
    assert "scaffold_context_emergents" in tutor_rows[0]
    assert "scaffold_context_basins" in tutor_rows[0]

    tutor_emergents = int(tutor_rows[-1]["emergent_count"])
    baseline_emergents = int(baseline_rows[-1]["emergent_count"])
    assert tutor_emergents >= baseline_emergents
    assert tutor_emergents > 0

    assert _earlier_share(tutor_state) == 1.0
