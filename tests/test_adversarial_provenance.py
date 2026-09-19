from __future__ import annotations

import json

from verdant_benchmarks.adversarial_provenance import (
    DEFAULT_CHECKPOINT_NAME,
    DEFAULT_REPORT_NAME,
    REPORT_SCHEMA,
    run,
)


def test_adversarial_provenance_end_to_end(tmp_path) -> None:
    report = run(tmp_path, seed=2501)

    assert report["schema_id"] == REPORT_SCHEMA
    assert report["all_required_checks_passed"]
    assert report["benchmark_status"] == "core_pass_with_native_telemetry_gap"
    assert report["final_state"]["contradiction_status"] == "weighted"
    assert report["checks"]["current_belief_is_held_open"]
    assert report["checks"]["causal_authorization_gate_blocks_operation"]
    assert report["checks"]["invalidated_source_lineage_remains_preserved"]
    assert report["checks"]["p_structures_remain_exact"]
    assert report["checks"]["q_structures_remain_exact"]
    assert report["checks"]["compiled_probe_gain_is_preserved"]
    assert report["checks"]["checkpoint_roundtrip_is_exact"]
    assert not report["experimental_observations"][
        "native_v5x_pressure_released_after_weighted_resolution"
    ]
    assert report["experimental_observations"][
        "weighted_contradiction_still_enters_workspace_as_full_pressure"
    ]
    assert (tmp_path / DEFAULT_REPORT_NAME).is_file()
    assert (tmp_path / DEFAULT_CHECKPOINT_NAME).is_file()
    for source_id in ("S1", "S2", "S3"):
        assert (tmp_path / "sources" / f"{source_id}.txt").is_file()

    disk_report = json.loads(
        (tmp_path / DEFAULT_REPORT_NAME).read_text(encoding="utf-8")
    )
    assert disk_report == report


def test_adversarial_provenance_is_deterministic_without_artifact_io(tmp_path) -> None:
    left = run(tmp_path / "left", seed=2502, write_artifacts=False)
    right = run(tmp_path / "right", seed=2502, write_artifacts=False)

    assert left == right
    assert left["all_required_checks_passed"]
    assert not left["explicit_capability_gaps"][
        "persistent_u_c_U_b_C_b_F_controller"
    ]
