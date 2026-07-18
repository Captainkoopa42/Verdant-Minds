"""Unit tests for reactive VCult parsing."""

from __future__ import annotations

from pathlib import Path

from cultivation.spec_parser import CultivationSpec

SPEC_DIR = Path(__file__).resolve().parents[2] / "cultivation" / "specs"


def test_parse_milestone_phase() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "reactive_medical.vcult"))
    phase = spec.phases[0]

    assert phase.min_cycles == 30
    assert phase.max_cycles == 80
    assert phase.advance_when == {"all": ["emergent_count >= 30", "basin_count >= 2"]}


def test_parse_conditional_reflection() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "reactive_medical.vcult"))
    phase = spec.phases[1]

    assert phase.self_reflect_when == {"any": ["interval 15", "latest_bud_within 3 cycles", "t_g > 0.75"]}
    assert phase.self_reflect_cooldown == 5


def test_parse_convergence() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "adaptive_cross_domain.vcult"))

    assert spec.convergence is not None
    assert spec.convergence.max_total_cycles == 300
    assert spec.convergence.min_total_cycles == 80
    assert spec.convergence.conditions == {"all": ["emergent_rate < 0.2 for 20 cycles"]}


def test_backward_compatible() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "quick_test.vcult"))

    assert spec.is_reactive is False
    assert spec.total_cycles == 20
    assert spec.phases[0].cycles == 20
