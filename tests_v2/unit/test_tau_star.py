from __future__ import annotations

import json
from pathlib import Path

from analysis.tau_star import TauStarComputer
from analysis.verdant_triangle_verification import run_sensitivity, verify_verdant_triangle
from verdant_v2.system import VerdantConfig, VerdantSystem


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_manual_state(tmp_path: Path) -> Path:
    state = {
        "memory_web": {
            "memory_store": {
                "good": {
                    "stability": 0.9,
                    "connections": [["harm", 0.8], ["neutral", 0.7]],
                    "first_seen": 0.0,
                    "access_count": 4,
                    "metadata": {"origin": "seed"},
                },
                "harm": {
                    "stability": 0.4,
                    "connections": [["good", 0.8], ["neutral", 0.6]],
                    "first_seen": 1.0,
                    "access_count": 3,
                    "metadata": {"origin": "seed"},
                },
                "neutral": {
                    "stability": 0.7,
                    "connections": [["good", 0.7], ["harm", 0.6]],
                    "first_seen": 2.0,
                    "access_count": 2,
                    "metadata": {"origin": "seed"},
                },
                "isolated": {
                    "stability": 0.2,
                    "connections": [],
                    "first_seen": 3.0,
                    "access_count": 1,
                    "metadata": {"origin": "seed"},
                },
            }
        },
        "bridge": {
            "concept_dimension_mapping": {
                "good": [["ethical", 0, 1.0], ["cognitive", 0, 0.5]],
                "harm": [["ethical", 1, 1.0], ["cognitive", 0, 0.3]],
                "neutral": [["ethical", 0, 0.4], ["cognitive", 1, 0.8]],
                "isolated": [["cognitive", 1, 0.6]],
            }
        },
        "ecwf": {
            "metadata": {"num_cognitive_dims": 2, "num_ethical_dims": 2}
        },
        "extra": {
            "basin_registry": {
                "basins": {
                    "basin_0": {"nodes": ["good", "neutral"]},
                    "basin_1": {"nodes": ["harm"]},
                }
            }
        },
    }
    state_path = tmp_path / "state.json"
    _write(state_path, state)
    return state_path


def _make_system_state(tmp_path: Path, cycles: int = 20) -> Path:
    system = VerdantSystem(
        VerdantConfig(
            seed=17,
            initialize_knowledge=True,
            basin_use_registry=True,
            fast_bridge=True,
        )
    )
    for cycle in range(cycles):
        system.process_input(
            f"Cycle {cycle}: justice harm trust privacy autonomy emergence continuity."
        )
    state_path = tmp_path / "system_state.json"
    system.save_checkpoint(str(state_path))
    return state_path


def test_tau_star_basic(tmp_path: Path) -> None:
    state_path = _make_system_state(tmp_path, cycles=10)
    computer = TauStarComputer(state_path)
    pairs = computer.compute_all_pairs()

    assert pairs
    first_pair = next(iter(pairs))
    value = computer.compute_tau_star(*first_pair)

    assert isinstance(value, float)
    assert 0.0 <= value <= 1.0


def test_tau_star_symmetry(tmp_path: Path) -> None:
    state_path = _make_manual_state(tmp_path)
    computer = TauStarComputer(state_path)

    assert computer.compute_tau_star("good", "harm") == computer.compute_tau_star("harm", "good")


def test_tau_star_disconnected(tmp_path: Path) -> None:
    state_path = _make_manual_state(tmp_path)
    disconnected = TauStarComputer(state_path, include_disconnected=False)
    included = TauStarComputer(state_path, include_disconnected=True)

    assert disconnected.compute_tau_star("good", "isolated") is None
    value = included.compute_tau_star("good", "isolated")
    assert isinstance(value, float)
    assert 0.0 <= value <= 1.0


def test_triangle_inequality_small(tmp_path: Path) -> None:
    state_path = _make_system_state(tmp_path, cycles=20)
    report, figures = verify_verdant_triangle(state_path, max_triples=10_000)

    for key in (
        "total_triples_checked",
        "valid_triples",
        "invalid_triples",
        "validity_fraction",
        "tau_star_stats",
        "sample_invalid_triples",
    ):
        assert key in report
    assert isinstance(report["validity_fraction"], float)
    assert "tau_star_distribution" in figures


def test_triangle_report_includes_basin_breakdown(tmp_path: Path) -> None:
    state_path = _make_manual_state(tmp_path)
    report, _ = verify_verdant_triangle(state_path, max_triples=10_000)

    assert "within_basin" in report
    assert "cross_basin" in report
    assert report["within_basin"]["total_triples"] >= 0
    assert report["cross_basin"]["total_triples"] >= 0


def test_sensitivity_sweep(tmp_path: Path) -> None:
    state_path = _make_system_state(tmp_path, cycles=20)
    sensitivity = run_sensitivity(state_path, max_triples=10_000)

    assert "configurations" in sensitivity
    assert len(sensitivity["configurations"]) >= 3
    for config in sensitivity["configurations"][:3]:
        assert "validity_fraction" in config
        assert isinstance(config["validity_fraction"], float)
