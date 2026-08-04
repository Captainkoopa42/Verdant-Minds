from verdant_benchmarks.q_evaluation import QEvaluationConfig, QEvaluationHarness


def test_q_evaluation_records_controlled_successes_and_failures() -> None:
    result = QEvaluationHarness(
        QEvaluationConfig(
            seeds=(1701,),
            thresholds=(0.985,),
            scaling_levels=(0,),
            baseline_seeds=(),
        )
    ).run()
    aggregate = result["aggregate"]
    assert aggregate["held_out_family_recognition"]["successes"] == 3
    assert aggregate["negative_control_rejection"]["successes"] == 3
    assert aggregate["causal_ablation_restoration"]["successes"] == 3
    assert aggregate["formation_failures"] == []
    assert result["scientific_sha256"]
