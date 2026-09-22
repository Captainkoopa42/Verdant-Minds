from __future__ import annotations

from types import SimpleNamespace

import pytest

from verdant_thermodynamics import inspect_access_pressure


class ReadOnlyKernel:
    def __init__(self):
        self.state = SimpleNamespace(
            cycle=903,
            concepts={name: object() for name in (
                "actuator", "sensor", "controller", "pressure_state",
                "pressure_sensor",
            )},
            structures={
                "short": SimpleNamespace(
                    structure_id="short",
                    member_concept_ids=("actuator", "controller", "sensor"),
                ),
                "broad": SimpleNamespace(
                    structure_id="broad",
                    member_concept_ids=(
                        "pressure_state", "pressure_sensor",
                        "actuator", "controller", "sensor",
                    ),
                ),
            },
        )
        self.fingerprint_calls = 0

    def fingerprint(self) -> str:
        self.fingerprint_calls += 1
        return "unchanged"

    def structure_is_available(self, structure_id: str) -> bool:
        return True


def test_pressure_detects_weak_and_supported_structure_overlap_before_policy():
    kernel = ReadOnlyKernel()
    alone = inspect_access_pressure(kernel, ("actuator",))
    together = inspect_access_pressure(kernel, ("actuator", "sensor"))

    assert alone["weak_context_candidate_count"] == 2
    assert alone["supported_context_candidate_count"] == 0
    assert together["weak_context_candidate_count"] == 1
    assert together["supported_context_candidate_count"] == 1
    assert [(c["structure_id"], c["trigger_fraction"])
            for c in together["candidate_details"]] == [
                ("broad", 0.4),
                ("short", 2 / 3),
            ]
    assert together["behavioral_authority_enabled"] is False
    assert kernel.fingerprint_calls == 4


def test_pressure_refuses_unknown_concepts_and_does_not_redefine_tg():
    kernel = ReadOnlyKernel()
    with pytest.raises(ValueError, match="existing concept IDs"):
        inspect_access_pressure(kernel, ("nonexistent",))
    assert "t_g" not in inspect_access_pressure(kernel, ("actuator",))
