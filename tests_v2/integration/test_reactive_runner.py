"""Integration tests for reactive VCult execution."""

from __future__ import annotations

import json
from pathlib import Path

from cultivation.spec_parser import CultivationSpec
from cultivation.spec_runner import SpecRunner


class _FakeChunk:
    def __init__(self, *, cycle: int, basin_count: int, bud: bool) -> None:
        self._cycle = cycle
        self._basin_count = basin_count
        self._bud = bud

    def get_section_content(self, name: str):
        if name == "basins_section":
            basins = [
                {"basin_id": f"basin_{idx}", "size": 5 + idx, "emergent_count": max(0, self._cycle - idx), "nodes": [f"concept_{idx}"]}
                for idx in range(self._basin_count)
            ]
            return {
                "basins": basins,
                "emergent_count_by_basin": {f"basin_{idx}": max(0, self._cycle - idx) for idx in range(self._basin_count)},
                "basin_membership_snapshot": {f"concept_{idx}": f"basin_{idx}" for idx in range(self._basin_count)},
            }
        if name == "basin_dynamics_section":
            return {
                "pruned_edges_count": 0,
                "bud_events_count": 1 if self._bud else 0,
                "bud_parent_basin_id": "basin_0" if self._bud else None,
                "bud_new_basin_id": f"basin_{self._basin_count - 1}" if self._bud else None,
                "bud_new_basin_size": 3 if self._bud else None,
                "basin_pressure_values": {},
                "pressure_breakdown": [],
                "boundary_emergents_created": 0,
                "boundary_pairs": [],
                "density_regulation_edges_removed": 0,
                "global_edge_ratio_before": 1.0,
                "global_edge_ratio_after": 1.0,
                "cycle_time_seconds": 0.01,
                "graph_nodes": 100,
                "graph_edges": 120,
                "edges_per_node": 1.2,
                "bridge_pairs_evaluated": 0,
                "basin_registry_active": self._basin_count,
                "basin_registry_dormant": 0,
                "basin_registry_events": [],
            }
        return {}


class _FakeSystem:
    def __init__(self) -> None:
        self._cycle = 0
        self._bud_cycles = {2, 5, 8}
        self._emergent_count = 0
        self._last_bud_cycle = None
        self._last_basins = []
        self.config = type("Config", (), {"basin_pressure_threshold": 0.01, "basin_routing": True, "fast_bridge": False})()
        self.ecwf = type("ECWF", (), {"random_state": 0, "rng": None, "past_states": [], "_initialize_parameters": lambda self: None, "amplitude_factors": 1.0})()
        self.ethomorphic_params = type("Params", (), {"initial_amplitude": 1.0})()
        self.memory_web = type("Memory", (), {"add_concept": lambda *args, **kwargs: None, "memory_store": {}, "graph": type("Graph", (), {"number_of_edges": lambda self: 120, "number_of_nodes": lambda self: 100})()})()
        self.bridge = type("Bridge", (), {"initialize_concept_mappings": lambda *args, **kwargs: 0})()
        self._checkpoints: list[str] = []

    def process_input(self, _text: str, metadata=None):
        self._cycle += 1
        if self._cycle <= 6:
            self._emergent_count += 1
        elif self._cycle <= 10:
            self._emergent_count += 0
        else:
            self._emergent_count += 1
        basin_count = 1 + min(3, self._cycle // 3)
        self._last_basins = [type("Basin", (), {"basin_id": f"basin_{idx}", "emergent_count": max(0, self._emergent_count - idx), "size": 5 + idx, "nodes": [f"concept_{idx}", f"seed_{idx}"]})() for idx in range(basin_count)]
        if self._cycle in self._bud_cycles:
            self._last_bud_cycle = self._cycle
        return _FakeChunk(cycle=self._cycle, basin_count=basin_count, bud=self._cycle in self._bud_cycles)

    def get_metrics(self):
        basin_count = 1 + min(3, self._cycle // 3)
        return {
            "t_g": 0.8 if self._cycle >= 4 else 0.5,
            "phase": "Flexible",
            "emergent_nodes": self._emergent_count,
            "memory_concepts": 82 + self._cycle,
            "basin_count": basin_count,
        }

    def get_scaffold_context(self):
        from cultivation.schemas import ScaffoldContext

        basin_count = 1 + min(3, self._cycle // 3)
        recent_bud_events = [] if self._last_bud_cycle is None else [{"cycle": self._last_bud_cycle, "basin_id": "basin_1", "parent_id": "basin_0"}]
        return ScaffoldContext(
            total_nodes=82 + self._cycle,
            emergent_count=self._emergent_count,
            basin_count=basin_count,
            basin_emergent_distribution={f"basin_{idx}": max(1, self._emergent_count - idx) for idx in range(basin_count)},
            top_concepts=["ethics", "causality", "care"],
            recent_emergents=["Emergent_test"],
            earlier_share=1.0,
            cycle=self._cycle,
            active_basin_count=basin_count,
            dormant_basin_count=0,
            total_emergent_count=self._emergent_count,
            t_g=0.8 if self._cycle >= 4 else 0.5,
            latest_emergent_names=["Emergent_test"],
            largest_basin_id="basin_0",
            largest_basin_emergent_count=max(1, self._emergent_count),
            recent_bud_events=recent_bud_events,
            edge_count=120,
            node_count=100,
            recent_dormancy_events=[],
        )

    def save_state(self, path: str) -> None:
        Path(path).write_text(json.dumps({
            "memory_web": {
                "memory_store": {
                    "seed_a": {"first_seen": 1.0, "metadata": {}},
                    "seed_b": {"first_seen": 2.0, "metadata": {}},
                    "Emergent_test": {
                        "first_seen": 3.0,
                        "metadata": {
                            "creation_time": 3.0,
                            "parent_concepts": ["seed_a", "seed_b"],
                        },
                    },
                }
            }
        }), encoding="utf-8")

    def save_checkpoint(self, path: str) -> None:
        self._checkpoints.append(path)
        Path(path).write_text(json.dumps({"cycle": self._cycle}), encoding="utf-8")


def _rows(seed_dir: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (seed_dir / "cycles.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_milestone_phase_advance(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(SpecRunner, "_build_system", lambda self, config: _FakeSystem())
    spec = CultivationSpec.from_dict(
        {
            "name": "milestone_test",
            "description": "reactive milestone",
            "phases": [
                {
                    "name": "phase_1",
                    "min_cycles": 2,
                    "max_cycles": 10,
                    "advance_when": {"all": ["emergent_count >= 5"]},
                    "topics": ["topic a"],
                },
                {
                    "name": "phase_2",
                    "cycles": 3,
                    "topics": ["topic b"],
                },
            ],
            "validation": {"expect_earlier_share": 1.0},
        }
    )

    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()
    phase_log = json.loads((seed_dir / "phase_log.json").read_text(encoding="utf-8"))
    rows = _rows(seed_dir)

    assert phase_log["phases"][0]["actual_cycles"] < 10
    assert phase_log["phases"][0]["advance_reason"] == "milestone"
    assert rows[phase_log["phases"][0]["actual_cycles"]]["phase_name"] == "phase_2"


def test_convergence_early_stop(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(SpecRunner, "_build_system", lambda self, config: _FakeSystem())
    spec = CultivationSpec.from_dict(
        {
            "name": "convergence_test",
            "description": "convergence",
            "phases": [
                {"name": "phase_1", "min_cycles": 2, "max_cycles": 12, "advance_when": {"all": ["emergent_count >= 50"]}, "topics": ["topic a"]},
                {"name": "phase_2", "min_cycles": 2, "max_cycles": 20, "advance_when": {"all": ["emergent_count >= 60"]}, "topics": ["topic b"], "on_end": ["checkpoint"]},
            ],
            "convergence": {
                "all": ["earlier_share == 1.0", "emergent_rate < 0.5 for 3 cycles"],
                "min_total_cycles": 6,
                "max_total_cycles": 32,
            },
            "validation": {"expect_earlier_share": 1.0},
        }
    )

    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()
    summary = json.loads((seed_dir / "summary.json").read_text(encoding="utf-8"))
    phase_log = json.loads((seed_dir / "phase_log.json").read_text(encoding="utf-8"))

    assert summary["cycles"] < 32
    assert phase_log["convergence"]["met"] is True
    assert phase_log["phases"][-1]["advance_reason"] == "convergence"


def test_conditional_self_reflection(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(SpecRunner, "_build_system", lambda self, config: _FakeSystem())
    spec = CultivationSpec.from_dict(
        {
            "name": "reflection_test",
            "description": "reflection",
            "phases": [
                {
                    "name": "phase_1",
                    "cycles": 12,
                    "topics": ["topic a"],
                    "self_reflect_when": {"any": ["interval 3", "latest_bud_within 3 cycles"]},
                    "self_reflect_cooldown": 2,
                }
            ],
            "validation": {"expect_earlier_share": 1.0},
        }
    )

    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()
    rows = _rows(seed_dir)
    reflected = [int(row["cycle_index"]) + 1 for row in rows if row["is_self_reflection"]]

    assert reflected == [3, 6, 9, 12]
    assert all(row["self_reflect_trigger"] for row in rows if row["is_self_reflection"])


def test_existing_specs_unchanged(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(SpecRunner, "_build_system", lambda self, config: _FakeSystem())
    for idx, name in enumerate(["quick_test.vcult", "cross_domain.vcult"]):
        spec = CultivationSpec.from_file(str(Path(__file__).resolve().parents[2] / "cultivation" / "specs" / name))
        seed_dir = SpecRunner(spec, seed=idx, provider="local", outdir=str(tmp_path / f"seed_{idx}")).run()
        validation = json.loads((seed_dir / "validation_results.json").read_text(encoding="utf-8"))
        assert validation["actual_metrics"]["earlier_share"] == 1.0
