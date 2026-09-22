from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_kernel import VerdantKernel, save_checkpoint
from run_v5x_thermodynamic_detector_study import (
    TOKEN_COUNTS, _arm_configs, _probe_command, _run_arm,
)


def test_verbosity_control_preserves_cue_payload_and_adapter() -> None:
    one = _probe_command(("actuator", "sensor"), 128, "same-event", 1)
    sixty = _probe_command(("actuator", "sensor"), 128, "same-event", 60)

    assert TOKEN_COUNTS == (1, 60)
    assert one.event_key == sixty.event_key
    assert one.source_ref == sixty.source_ref
    assert one.payload_sha256 == sixty.payload_sha256
    assert one.feature_vector == sixty.feature_vector
    assert one.concept_labels == sixty.concept_labels
    assert len(one.metadata["sentence"].split()) == 1
    assert len(sixty.metadata["sentence"].split()) == 60
    assert one.modality == sixty.modality == "text"


def test_resonance_ablation_arms_change_only_intended_floor() -> None:
    configs = _arm_configs()
    base = configs["observer_baseline"]
    both = configs["v4_both_resonance_gates"]
    score = configs["score_only_ablation"]
    support = configs["support_only_ablation"]
    neither = configs["neither_resonance_gate"]

    assert base.resonance_recall_threshold == 0
    assert base.resonance_local_support_floor == 0
    assert both.resonance_recall_threshold == pytest.approx(0.32)
    assert both.resonance_local_support_floor == pytest.approx(0.32)
    assert score.resonance_recall_threshold == both.resonance_recall_threshold
    assert score.resonance_local_support_floor == 0
    assert support.resonance_recall_threshold == 0
    assert support.resonance_local_support_floor == both.resonance_local_support_floor
    assert neither.resonance_recall_threshold == 0
    assert neither.resonance_local_support_floor == 0
    assert both.structure_trigger_members == score.structure_trigger_members == (
        support.structure_trigger_members
    ) == neither.structure_trigger_members == 2
    assert both.structure_trigger_fraction == score.structure_trigger_fraction == (
        support.structure_trigger_fraction
    ) == neither.structure_trigger_fraction == 0.5


def test_isolated_detector_arm_does_not_overwrite_checkpoint(tmp_path: Path) -> None:
    source = VerdantKernel(seed=2217, state_dim=24, run_label="detector-fork")
    path = tmp_path / "source.vdk"
    save_checkpoint(path, source.snapshot())
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    command = _probe_command(("alpha",), 24, "isolated-arm", 1)

    left = _run_arm(path, command, _arm_configs()["observer_baseline"])
    right = _run_arm(path, command, _arm_configs()["v4_both_resonance_gates"])

    assert left["starting_fingerprint"] == right["starting_fingerprint"]
    assert left["thermodynamics_post_cycle"]["input"]["token_count"] == 1
    assert right["thermodynamics_post_cycle"]["input"]["token_count"] == 1
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
