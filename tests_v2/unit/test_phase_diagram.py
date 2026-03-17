"""Unit tests for phase-diagram analysis utilities."""

from __future__ import annotations

import json

from analysis.detect_onset import detect_onset
from analysis.seed_sets import get_seed_set


def _write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_detect_onset(tmp_path) -> None:
    cycles = [
        {"cycle_index": i, "basin_count": 0, "t_g": 0.5, "memory_size": 100 + i, "emergent_count": 0, "entropy": 0.1, "hci": 0.2}
        for i in range(5)
    ]
    cycles.append({"cycle_index": 5, "basin_count": 1, "t_g": 0.566, "memory_size": 132, "emergent_count": 3, "entropy": 0.22, "hci": 0.41})
    p = tmp_path / "cycles.jsonl"
    _write_jsonl(p, cycles)

    out = detect_onset(str(p))
    assert out["onset_cycle"] == 5
    assert out["onset_t_g"] == 0.566


def test_detect_onset_no_basins(tmp_path) -> None:
    cycles = [{"cycle_index": i, "basin_count": 0} for i in range(10)]
    p = tmp_path / "cycles.jsonl"
    _write_jsonl(p, cycles)

    out = detect_onset(str(p))
    assert out["onset_cycle"] is None


def test_seed_sets() -> None:
    s82 = get_seed_set(82)
    s20 = get_seed_set(20)
    assert len(s82) == 82
    assert len(set(s82)) == 82
    assert len(s20) == 20
    assert len(set(s20)) == 20
    assert get_seed_set(20, seed=42) == get_seed_set(20, seed=42)
    assert get_seed_set(20, seed=42) != get_seed_set(20, seed=99)
