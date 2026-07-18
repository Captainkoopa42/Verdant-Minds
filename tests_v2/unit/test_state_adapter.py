from __future__ import annotations

import json
import subprocess
import sys

import pytest
from pathlib import Path

from analysis.state_adapter import VerdantState


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_v2_format_loading(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "nodes": [
                {"name": "identity", "creation_time": 0.0, "access_count": 3, "connection_count": 1},
                {"name": "Emergent_bridge", "creation_time": 1.5, "access_count": 5, "connection_count": 1},
            ],
            "edges": [
                {"source": "identity", "target": "Emergent_bridge", "weight": 0.7},
            ],
        },
        "extra": {"last_basins": [{"basin_id": "basin_0", "nodes": ["identity", "Emergent_bridge"]}]},
    }
    path = tmp_path / "state.json"
    _write(path, state)

    vs = VerdantState.load(path)

    assert vs.format_version == "v2"
    assert vs.node_count == 2
    assert vs.edge_count == 1
    assert vs.emergent_count == 1
    assert vs.get_node("Emergent_bridge")["is_emergent"] is True
    assert vs.get_node("identity")["creation_time"] == 0.0
    assert isinstance(vs.basins, list)


def test_v3_format_loading(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "memory_store": {
                "identity": {
                    "stability": 0.9,
                    "connections": [["Emergent_bridge", 0.4]],
                    "first_seen": 0.0,
                    "access_count": 3,
                    "metadata": {"origin": "seed", "creation_time": 0.0},
                },
                "Emergent_bridge": {
                    "stability": 0.6,
                    "connections": [["identity", 0.4]],
                    "first_seen": 1.25,
                    "access_count": 7,
                    "metadata": {"origin": "wave_emergence", "creation_time": 99.0},
                },
            },
            "edges": [{"source": "identity", "target": "Emergent_bridge", "weight": 1.0}],
        },
        "extra": {"basin_registry": {"basins": {"basin_0": {"nodes": ["identity", "Emergent_bridge"]}}}},
    }
    path = tmp_path / "state.json"
    _write(path, state)

    vs = VerdantState.load(path)

    assert vs.format_version == "v3"
    assert vs.node_count == 2
    assert vs.edge_count == 1
    assert vs.emergent_count == 1
    emergent = vs.get_node("Emergent_bridge")
    assert emergent is not None
    assert emergent["creation_time"] == 1.25
    assert emergent["is_emergent"] is True
    assert vs.basin_registry["basins"]["basin_0"]["nodes"] == ["identity", "Emergent_bridge"]


def test_edge_deduplication(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "memory_store": {
                "a": {"connections": [["b", 0.2], ["c", 0.9]], "first_seen": 0.0, "metadata": {}},
                "b": {"connections": [["a", 0.4]], "first_seen": 1.0, "metadata": {}},
                "c": {"connections": [["a", 0.9]], "first_seen": 2.0, "metadata": {}},
            },
            "edges": [
                {"source": "a", "target": "b", "weight": 1.0},
                {"source": "a", "target": "c", "weight": 1.0},
            ],
        }
    }
    path = tmp_path / "state.json"
    _write(path, state)

    vs = VerdantState.load(path)
    edges = {(edge["source"], edge["target"]): edge["weight"] for edge in vs.edges}

    assert vs.edge_count == 2
    assert edges[("a", "b")] == pytest.approx(0.3)
    assert edges[("a", "c")] == pytest.approx(0.9)


def test_emergent_edge_detection(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "memory_store": {
                "seed_0": {"connections": [["Emergent_a", 0.3]], "first_seen": 0.0, "metadata": {"origin": "seed"}},
                "seed_1": {"connections": [["Emergent_b", 0.4]], "first_seen": 0.1, "metadata": {"origin": "seed"}},
                "Emergent_a": {"connections": [["Emergent_b", 0.5], ["Emergent_c", 0.7]], "first_seen": 1.0, "metadata": {"origin": "wave_emergence"}},
                "Emergent_b": {"connections": [["Emergent_a", 0.5], ["seed_1", 0.4]], "first_seen": 2.0, "metadata": {"origin": "wave_emergence"}},
                "Emergent_c": {"connections": [["Emergent_a", 0.7]], "first_seen": 3.0, "metadata": {"origin": "wave_emergence"}},
            },
            "edges": [],
        }
    }
    path = tmp_path / "state.json"
    _write(path, state)

    vs = VerdantState.load(path)
    pairs = {(edge["source"], edge["target"]) for edge in vs.emergent_edges}

    assert vs.emergent_count == 3
    assert pairs == {("Emergent_a", "Emergent_b"), ("Emergent_a", "Emergent_c")}


def test_earlier_share_v3(tmp_path: Path) -> None:
    state = {
        "memory_web": {
            "memory_store": {
                "Emergent_a": {"connections": [["Emergent_b", 0.5], ["Emergent_c", 0.6]], "first_seen": 1.0, "metadata": {"origin": "wave_emergence", "creation_time": 1.0}},
                "Emergent_b": {"connections": [["Emergent_a", 0.5], ["Emergent_d", 0.7]], "first_seen": 2.0, "metadata": {"origin": "wave_emergence", "creation_time": 2.0}},
                "Emergent_c": {"connections": [["Emergent_a", 0.6], ["Emergent_d", 0.8]], "first_seen": 3.0, "metadata": {"origin": "wave_emergence", "creation_time": 3.0}},
                "Emergent_d": {"connections": [["Emergent_b", 0.7], ["Emergent_c", 0.8], ["Emergent_e", 0.9]], "first_seen": 4.0, "metadata": {"origin": "wave_emergence", "creation_time": 4.0}},
                "Emergent_e": {"connections": [["Emergent_d", 0.9]], "first_seen": 5.0, "metadata": {"origin": "wave_emergence", "creation_time": 5.0}},
            },
            "edges": [],
        },
        "extra": {"last_basins": []},
    }
    state_path = tmp_path / "state.json"
    outdir = tmp_path / "out"
    _write(state_path, state)

    subprocess.run(
        [
            sys.executable,
            "analysis/extract_scaffolding_metrics.py",
            "--state",
            str(state_path),
            "--outdir",
            str(outdir),
        ],
        check=True,
    )

    metrics = json.loads((outdir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["emergent_edges"] == 5
    assert metrics["comparable_emergent_edges"] == 5
    assert metrics["earlier_share"] == 1.0
