"""Unit tests for self-referential cultivation."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.providers.tutor import TutorProvider
from cultivation.runner import CultivationRunner, RunnerConfig
from cultivation.schemas import ScaffoldContext


def _context(*, cycle: int = 20, emergent_count: int = 12, t_g: float = 0.7234) -> ScaffoldContext:
    return ScaffoldContext(
        total_nodes=42,
        emergent_count=emergent_count,
        basin_count=3,
        basin_emergent_distribution={"basin_0": 7, "basin_1": 3, "basin_2": 2},
        top_concepts=["coherence", "identity", "constraint"],
        recent_emergents=["Emergent_coherence_constraint", "Emergent_autonomy_identity"],
        earlier_share=1.0,
        cycle=cycle,
        active_basin_count=3,
        dormant_basin_count=2,
        total_emergent_count=emergent_count,
        t_g=t_g,
        latest_emergent_names=["coherence", "boundary", "autonomy"],
        largest_basin_id="basin_11",
        largest_basin_emergent_count=9,
        recent_bud_events=[{"cycle": cycle - 2, "basin_id": "basin_15", "parent_id": "basin_11", "members": 4}],
        edge_count=88,
        node_count=42,
        recent_dormancy_events=[{"cycle": cycle - 1, "basin_id": "basin_4", "core_size": 3}],
        h1_triangle_valid=True,
        housed_contradiction_index=0.125,
        violation_rate=0.0,
        alpha_critical_estimate=1.0,
    )


def _read_rows(run_dir: Path) -> list[dict[str, object]]:
    lines = (run_dir / "seed_0" / "cycles.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _earlier_share(state: dict[str, object]) -> float:
    memory = state.get("memory_web", {}) if isinstance(state, dict) else {}
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


def test_self_referential_input_generation() -> None:
    provider = TutorProvider(backend="local")
    text_a = provider.generate_self_referential_input(_context(cycle=20, emergent_count=12, t_g=0.7234))
    text_b = provider.generate_self_referential_input(_context(cycle=21, emergent_count=13, t_g=0.8123))

    lowered = text_a.lower()
    assert "12 emergent concepts" in lowered
    assert "t_g is 0.7234" in lowered or "t_g=0.7234" in lowered
    assert "basin_11" in text_a
    assert "basin_15" in text_a
    assert "coherence" in lowered
    assert "h¹ coherence check is currently valid" in lowered
    assert text_a != text_b


def test_self_reflection_interval(tmp_path: Path) -> None:
    cfg = RunnerConfig(cycles=20, provider="local", outdir=str(tmp_path), self_reflect_interval=5)
    run_dir = CultivationRunner(cfg).run([0])
    rows = _read_rows(run_dir)

    reflected = [int(row["cycle_index"]) + 1 for row in rows if row["is_self_reflection"] is True]
    assert reflected == [5, 10, 15, 20]
    normal = [int(row["cycle_index"]) + 1 for row in rows if row["is_self_reflection"] is False]
    assert normal == [1, 2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17, 18, 19]
    assert all(row["self_reflection_input"] for row in rows if row["is_self_reflection"] is True)


def test_self_reflection_preserves_earlier_share(tmp_path: Path) -> None:
    cfg = RunnerConfig(cycles=40, provider="local", outdir=str(tmp_path), self_reflect_interval=10)
    run_dir = CultivationRunner(cfg).run([0])
    state = json.loads((run_dir / "seed_0" / "state.json").read_text(encoding="utf-8"))

    assert _earlier_share(state) == 1.0


def test_self_reflection_disabled_by_default(tmp_path: Path) -> None:
    cfg = RunnerConfig(cycles=20, provider="local", outdir=str(tmp_path))
    run_dir = CultivationRunner(cfg).run([0])
    rows = _read_rows(run_dir)

    assert all(row["is_self_reflection"] is False for row in rows)
    assert all(row["self_reflection_input"] == "" for row in rows)
