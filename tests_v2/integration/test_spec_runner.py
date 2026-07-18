"""Integration tests for VCult spec execution."""

from __future__ import annotations

import json
from pathlib import Path

from analysis.spec_validation import compute_earlier_share_from_state_path
from cultivation.spec_parser import CultivationSpec
from cultivation.spec_runner import SpecRunner

SPEC_DIR = Path(__file__).resolve().parents[2] / "cultivation" / "specs"


def _read_rows(seed_dir: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (seed_dir / "cycles.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_run_quick_spec(tmp_path: Path) -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "quick_test.vcult"))
    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()

    assert (seed_dir / "state.json").exists()
    assert (seed_dir / "cycles.jsonl").exists()
    assert (seed_dir / "summary.json").exists()
    assert (seed_dir / "spec.yaml").exists()
    assert compute_earlier_share_from_state_path(seed_dir / "state.json") == 1.0

    phase_log = json.loads((seed_dir / "phase_log.json").read_text(encoding="utf-8"))
    assert phase_log["phases"][0]["name"] == "boot"
    assert phase_log["phases"][0]["cycle_start"] == 1
    assert phase_log["phases"][0]["cycle_end"] == 20


def test_multi_phase_spec(tmp_path: Path, monkeypatch) -> None:
    class _FakeChunk:
        def get_section_content(self, _name: str):
            return {}

    class _FakeSystem:
        def __init__(self) -> None:
            self._cycle = 0
            self.config = type("Config", (), {"basin_pressure_threshold": 0.01, "basin_routing": False, "fast_bridge": False})()
            self.ecwf = type("ECWF", (), {"random_state": 0, "rng": None, "past_states": [], "_initialize_parameters": lambda self: None, "amplitude_factors": 1.0})()
            self.ethomorphic_params = type("Params", (), {"initial_amplitude": 1.0})()
            self.memory_web = type("Memory", (), {"add_concept": lambda *args, **kwargs: None})()
            self.bridge = type("Bridge", (), {"initialize_concept_mappings": lambda *args, **kwargs: 0})()

        def process_input(self, _text: str, metadata=None):
            self._cycle += 1
            return _FakeChunk()

        def get_metrics(self):
            return {
                "t_g": 0.5,
                "phase": "Flexible",
                "emergent_nodes": self._cycle,
                "memory_concepts": 82 + self._cycle,
                "basin_count": 3,
            }

        def get_scaffold_context(self):
            from cultivation.schemas import ScaffoldContext

            return ScaffoldContext(
                total_nodes=82 + self._cycle,
                emergent_count=self._cycle,
                basin_count=3,
                basin_emergent_distribution={"basin_0": self._cycle},
                top_concepts=["ethics", "causality"],
                recent_emergents=["Emergent_test"],
                earlier_share=1.0,
                cycle=self._cycle,
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

    monkeypatch.setattr(SpecRunner, "_build_system", lambda self, config: _FakeSystem())

    spec = CultivationSpec.from_file(str(SPEC_DIR / "cross_domain.vcult"))
    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()
    rows = _read_rows(seed_dir)
    phase_log = json.loads((seed_dir / "phase_log.json").read_text(encoding="utf-8"))

    assert len(phase_log["phases"]) == 3
    assert len(rows) == 100

    reflected = [int(row["cycle_index"]) + 1 for row in rows if row["is_self_reflection"]]
    assert reflected == [15, 30, 45, 60, 70, 80, 90, 100]

    assert rows[0]["phase_name"] == "ethics_foundation"
    assert rows[0]["phase_start"] is True
    assert rows[29]["phase_end"] is True
    assert rows[30]["phase_start"] is True
    assert rows[59]["phase_end"] is True
    assert rows[60]["phase_start"] is True
    assert rows[99]["phase_end"] is True


def test_validation_checks(tmp_path: Path) -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "quick_test.vcult"))
    seed_dir = SpecRunner(spec, seed=0, provider="local", outdir=str(tmp_path / "seed_0")).run()

    results = json.loads((seed_dir / "validation_results.json").read_text(encoding="utf-8"))

    assert "checks" in results
    assert results["checks"]["expect_earlier_share"]["passed"] is True
