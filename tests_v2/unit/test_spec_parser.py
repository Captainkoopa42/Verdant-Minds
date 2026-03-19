"""Unit tests for the minimal VCult spec language."""

from __future__ import annotations

from pathlib import Path

import pytest

from cultivation.spec_parser import CultivationSpec, SpecValidationError
from cultivation.spec_runner import SpecRunner

SPEC_DIR = Path(__file__).resolve().parents[2] / "cultivation" / "specs"


def test_parse_valid_spec() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "quick_test.vcult"))

    assert spec.name == "quick_test"
    assert len(spec.phases) == 1
    assert spec.total_cycles == 20
    assert spec.phases[0].topics == [
        "explore the nature of consciousness and identity",
        "examine how boundaries define and constrain emergence",
    ]


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"description": "x", "phases": []}, "Missing required field"),
        ({"name": "x", "description": "x", "phases": [{"name": "p", "cycles": 1, "topics": []}]}, "must not be empty"),
        ({"name": "x", "description": "x", "phases": [{"name": "p", "cycles": -1, "topics": ["topic"]}]}, "positive integer"),
    ],
)
def test_parse_invalid_spec(payload: dict[str, object], message: str) -> None:
    with pytest.raises(SpecValidationError, match=message):
        CultivationSpec.from_dict(payload)


def test_generate_input_sequence() -> None:
    spec = CultivationSpec.from_file(str(SPEC_DIR / "quick_test.vcult"))
    sequence = spec.generate_input_sequence()

    assert len(sequence) == 20
    reflected = [item["cycle"] for item in sequence if item["is_self_reflection"]]
    assert reflected == [10, 20]
    assert sequence[0]["input_text"] == "explore the nature of consciousness and identity"
    assert sequence[1]["input_text"] == "examine how boundaries define and constrain emergence"
    assert sequence[2]["input_text"].startswith("explore the nature of consciousness and identity")
    assert sequence[9]["input_text"] == "[SELF_REFLECTION]"


def test_topic_variation() -> None:
    spec = CultivationSpec.from_dict(
        {
            "name": "variation_test",
            "description": "variation",
            "phases": [
                {
                    "name": "boot",
                    "cycles": 10,
                    "topics": ["topic a", "topic b"],
                    "self_reflect_interval": 0,
                }
            ],
        }
    )

    inputs = [item["input_text"] for item in spec.generate_input_sequence()]

    assert inputs[0] == "topic a"
    assert inputs[1] == "topic b"
    assert inputs[2].startswith("topic a, ")
    assert inputs[3].startswith("topic b, ")
    assert len(inputs) == len(set(inputs)) == 10


def test_settings_override(tmp_path: Path) -> None:
    spec = CultivationSpec.from_dict(
        {
            "name": "settings_test",
            "description": "settings",
            "settings": {
                "bud_pressure_threshold": 0.01,
                "basin_routing": True,
                "fast_bridge": True,
            },
            "phases": [
                {
                    "name": "boot",
                    "cycles": 1,
                    "topics": ["topic a"],
                    "self_reflect_interval": 0,
                }
            ],
        }
    )

    runner = SpecRunner(spec, seed=0, outdir=str(tmp_path / "out"))
    config = runner._runner_config_from_spec()
    system = runner._build_system(config)

    assert system.config.basin_pressure_threshold == pytest.approx(0.01)
    assert system.config.basin_routing is True
    assert system.config.fast_bridge is True
