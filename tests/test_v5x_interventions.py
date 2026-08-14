from __future__ import annotations

from verdant_benchmarks.ethomorphism import ArmName, BenchmarkConfig, EthomorphismBenchmarkHarness
from verdant_benchmarks.interventions import (
    InterventionTier,
    fork_destructive_p_lesion,
    fork_destructive_q_lesion,
)
from verdant_benchmarks.recovery import (
    RecoveryClassification,
    governed_rederive_p,
    governed_rederive_q,
)
from verdant_compilation import VerdantCompilationPipeline
from verdant_hierarchy import VerdantHierarchyPipeline


def _trained_d():
    harness = EthomorphismBenchmarkHarness(BenchmarkConfig(seed=1901, state_dim=16, noise_concepts=0))
    runtime = harness.train_arm(ArmName.D_FULL)
    return harness, runtime


def test_destructive_p_lesion_is_fork_only_and_native_rederivation_recovers_work() -> None:
    harness, runtime = _trained_d()
    source = runtime.kernel
    target = runtime.structure_by_world[harness.novel_world.name]
    cue = harness._concept_id(source, harness.novel_world.labels[0])
    before_source = source.snapshot()
    source_work = VerdantCompilationPipeline().inspect(source, (cue,)).cost.low_level_work
    assert source_work == 1

    lesion = fork_destructive_p_lesion(source, target)
    assert lesion.manifest.tier == InterventionTier.DESTRUCTIVE_P
    assert source.snapshot() == before_source
    assert target not in lesion.kernel.state.structures
    lesioned_probe = VerdantCompilationPipeline().inspect(lesion.kernel, (cue,))
    assert lesioned_probe.cost.low_level_work == 7

    recovery = governed_rederive_p(lesion)
    assert recovery.classification == RecoveryClassification.REDERIVED_SAME_ID
    assert recovery.recovered_id == target
    assert not recovery.used_restore_operation
    recovered_probe = VerdantCompilationPipeline().inspect(lesion.kernel, (cue,))
    assert recovered_probe.cost.low_level_work == source_work
    assert source.snapshot() == before_source


def test_destructive_q_lesion_preserves_p_and_native_rederivation_recovers_family_work() -> None:
    harness, runtime = _trained_d()
    source = runtime.kernel
    target_q = runtime.layered_structure_id
    assert target_q is not None
    novel_p = runtime.structure_by_world[harness.novel_world.name]
    before_source = source.snapshot()
    before_p = dict(source.state.structures)
    source_probe = VerdantHierarchyPipeline().inspect_probe(source, novel_p)
    assert source_probe.cost.comparison_work == 3

    lesion = fork_destructive_q_lesion(source, target_q)
    assert lesion.manifest.tier == InterventionTier.DESTRUCTIVE_Q
    assert lesion.kernel.state.structures == before_p
    assert target_q not in lesion.kernel.state.layered_structures
    lesioned_probe = VerdantHierarchyPipeline().inspect_probe(lesion.kernel, novel_p)
    assert lesioned_probe.cost.comparison_work == 8

    recovery = governed_rederive_q(lesion)
    assert recovery.classification == RecoveryClassification.REDERIVED_SAME_ID
    assert recovery.recovered_id == target_q
    assert not recovery.used_restore_operation
    recovered_probe = VerdantHierarchyPipeline().inspect_probe(lesion.kernel, novel_p)
    assert recovered_probe.cost.comparison_work == source_probe.cost.comparison_work
    assert recovered_probe.matched_structure_ids == source_probe.matched_structure_ids
    assert source.snapshot() == before_source
