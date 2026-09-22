from __future__ import annotations

import hashlib

from verdant_kernel import VerdantKernel, save_checkpoint
from run_v5x_thermodynamic_lag_stress import SEQUENCES, _run_sequence


def test_lag_stress_source_is_previous_controlled_cycle_and_checkpoint_is_read_only(tmp_path):
    source = VerdantKernel(seed=2260, state_dim=24, run_label="lag-stress-fork")
    path = tmp_path / "original.vdk"
    save_checkpoint(path, source.snapshot())
    unchanged = hashlib.sha256(path.read_bytes()).hexdigest()

    result = _run_sequence(
        path,
        "minimal-source-provenance",
        ((("alpha",), 60), (("alpha",), 1), (("beta",), 1)),
    )
    first, second, third = result["steps"]

    assert first["control_applied_this_cycle"] is None
    assert second["control_applied_this_cycle"]["source_t_g"] == first["controlled_t_g"]
    assert third["control_applied_this_cycle"]["source_t_g"] == second["controlled_t_g"]
    assert first["tokens"] == 60
    assert second["tokens"] == third["tokens"] == 1
    # New concepts cannot be inspected as though their P membership had
    # existed in the starting checkpoint.
    assert first["observer_pre_access_pressure"] is None
    assert first["controlled_pre_access_pressure"] is None
    assert second["observer_pre_access_pressure"] is not None
    assert second["controlled_pre_access_pressure"] is not None
    assert second["observer_pre_access_pressure"]["behavioral_authority_enabled"] is False
    assert hashlib.sha256(path.read_bytes()).hexdigest() == unchanged


def test_lag_stress_has_short_and_long_context_controls():
    names = {name for name, _sequence in SEQUENCES}
    assert "high_recruitment_then_same_short" in names
    assert "high_recruitment_then_supported_context" in names
    assert "long_supported_context_negative_control" in names
    assert "short_recruitment_negative_control" in names
