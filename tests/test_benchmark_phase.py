from __future__ import annotations

from verdant_benchmarks import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness


def small_harness() -> EthomorphismBenchmarkHarness:
    return EthomorphismBenchmarkHarness(
        BenchmarkConfig(noise_concepts=12, noise_repeats=1)
    )


def test_benchmark_curriculum_is_deterministic_and_target_family_is_not_taught() -> None:
    left = small_harness()
    right = small_harness()
    assert left.curriculum_sha256() == right.curriculum_sha256()
    commands = left.curriculum_commands()
    assert commands
    assert all(proposal.relation_type == "linked" for cmd in commands for proposal in cmd.relation_proposals)
    # The evaluator knows the hidden family for scoring, but no canonical concept,
    # relation type, or claim named "path" is installed by the curriculum.
    assert all(
        "path" not in cmd.concept_labels
        and all(p.relation_type != "path" for p in cmd.relation_proposals)
        and "path" not in cmd.model_dump_json().lower()
        for cmd in commands
    )


def test_c_and_d_share_plastic_substrate_but_only_d_promotes_folds() -> None:
    harness = small_harness()
    c = harness.train_arm(ArmName.C_PLASTIC)
    d = harness.train_arm(ArmName.D_FULL)
    assert len(c.kernel.state.plasticity_associations) == len(d.kernel.state.plasticity_associations) > 0
    assert len(c.kernel.state.structures) == 0
    assert len(c.kernel.state.layered_structures) == 0
    assert len(d.kernel.state.structures) >= 5
    assert len(d.kernel.state.layered_structures) >= 1


def test_all_arms_solve_heldout_local_reconstruction_but_d_compiles_it() -> None:
    harness = small_harness()
    metrics = {
        arm: harness.evaluate_arm(harness.train_arm(arm))
        for arm in ArmName
    }
    assert all(item.local_reconstruction_success for item in metrics.values())
    assert metrics[ArmName.D_FULL].local_structure_used
    assert metrics[ArmName.D_FULL].local_reconstruction_work < metrics[ArmName.C_PLASTIC].local_reconstruction_work
    assert metrics[ArmName.D_FULL].local_reconstruction_work < metrics[ArmName.A_GRAPH].local_reconstruction_work


def test_full_arm_transfer_is_selective_and_q_reduces_family_comparison_work() -> None:
    harness = small_harness()
    d = harness.train_arm(ArmName.D_FULL)
    metrics = harness.evaluate_arm(d)
    assert metrics.family_transfer_success
    assert metrics.family_selectivity_success
    assert metrics.family_comparison_work < 8  # native M17 fallback on this population


def test_p_and_q_ablation_restoration_controls_follow_exact_objects() -> None:
    harness = small_harness()
    d = harness.train_arm(ArmName.D_FULL)
    causal = harness.causal_controls(d)
    assert causal.same_reconstruction
    assert causal.gain_followed_structure
    assert causal.same_family_matches
    assert causal.q_gain_followed_object


def test_refolding_control_preserves_parent_lineage_and_semantic_counts() -> None:
    result = small_harness().refolding_control()
    assert result.disposition == "split"
    assert result.parent_preserved
    assert result.parent_dormant_after_success
    assert result.produced_children == 2
    assert result.lineage_preserved
    assert result.semantic_counts_unchanged


def test_long_run_plastic_health_stays_inside_explicit_caps() -> None:
    harness = small_harness()
    for arm in (ArmName.C_PLASTIC, ArmName.D_FULL):
        health = harness.long_run_health(arm)
        assert health.within_degree_cap
        assert health.within_edge_ratio_cap
        assert health.density < 0.90


def test_full_arm_training_is_deterministic() -> None:
    harness = small_harness()
    left = harness.train_arm(ArmName.D_FULL)
    right = harness.train_arm(ArmName.D_FULL)
    assert left.kernel.snapshot() == right.kernel.snapshot()
    assert left.kernel.fingerprint() == right.kernel.fingerprint()
    assert left.structure_by_world == right.structure_by_world
    assert left.layered_structure_id == right.layered_structure_id
