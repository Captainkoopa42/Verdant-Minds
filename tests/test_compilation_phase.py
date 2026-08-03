from __future__ import annotations

import hashlib

import pytest

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_kernel import (
    CompilationDisposition,
    CompilationStaleError,
    EvidenceKind,
    ExperienceCommand,
    WorkspaceSourceKind,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
    event_key: str,
    labels: tuple[str, ...],
    *,
    context: str,
    feature: tuple[float, ...] = (1.0, 0.0, 0.0),
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="compilation:controlled",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=feature,
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_compilation_test": True},
        metadata={"context_id": context},
    )


def cultivated_promoted_kernel(seed: int = 1501) -> tuple[VerdantKernel, str, tuple[str, ...]]:
    kernel = VerdantKernel(seed=seed, state_dim=48, run_label=f"compilation-{seed}")
    development = VerdantDevelopmentPipeline()
    for index in range(7):
        development.advance(
            kernel,
            command(
                f"triad-{index}",
                ("kren", "tar", "vel"),
                context=f"ctx-{index % 2}",
            ),
        )
    assert len(kernel.state.structure_candidates) == 1
    candidate = next(iter(kernel.state.structure_candidates.values()))
    promotion = VerdantStructurePipeline().promote(kernel, candidate.candidate_id)
    structure_id = promotion.event.structure_id
    return kernel, structure_id, candidate.member_concept_ids


def concept_id(kernel: VerdantKernel, label: str) -> str:
    return next(
        item
        for item, concept in kernel.state.concepts.items()
        if concept.normalized_label == label
    )


def test_promoted_structure_reduces_reconstruction_work() -> None:
    kernel, structure_id, members = cultivated_promoted_kernel(1501)
    cue = concept_id(kernel, "kren")
    pipeline = VerdantCompilationPipeline()

    report = pipeline.inspect(kernel, (cue,))

    assert report.disposition == CompilationDisposition.USE_STRUCTURE
    assert report.structure_id == structure_id
    assert report.reconstructed_concept_ids == members
    assert report.baseline_cost.reconstructed_concepts == len(members)
    assert report.cost.structure_operands_used == 1
    assert report.cost.associations_traversed == 0
    assert report.cost.low_level_work < report.baseline_cost.low_level_work
    assert report.compression_gain > 0.0


def test_ablation_removes_gain_and_restoration_returns_it() -> None:
    kernel, structure_id, members = cultivated_promoted_kernel(1502)
    cue = concept_id(kernel, "kren")
    pipeline = VerdantCompilationPipeline()

    with_structure = pipeline.probe(kernel, (cue,)).report
    pipeline.ablate(kernel, structure_id, "M15 controlled causal ablation")
    without_structure = pipeline.probe(kernel, (cue,)).report
    pipeline.restore(kernel, structure_id, "M15 controlled causal restoration")
    restored = pipeline.probe(kernel, (cue,)).report

    assert with_structure.reconstructed_concept_ids == members
    assert without_structure.reconstructed_concept_ids == members
    assert restored.reconstructed_concept_ids == members
    assert with_structure.disposition == CompilationDisposition.USE_STRUCTURE
    assert without_structure.disposition == CompilationDisposition.FALLBACK_LOW_LEVEL
    assert restored.disposition == CompilationDisposition.USE_STRUCTURE
    assert without_structure.compression_gain == 0.0
    assert with_structure.compression_gain == pytest.approx(restored.compression_gain)
    assert with_structure.cost == restored.cost
    assert without_structure.cost.low_level_work == without_structure.baseline_cost.low_level_work
    assert without_structure.cost.low_level_work > with_structure.cost.low_level_work


def test_promoted_structure_can_enter_workspace_as_one_operand() -> None:
    kernel, structure_id, _ = cultivated_promoted_kernel(1503)
    before = dict(kernel.state.plasticity_associations)
    development = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(
            resonance_top_k=4,
            resonance_commit_limit=0,
            association_recall_threshold=1.0,
        )
    )
    result = development.advance(
        kernel,
        command("compiled-cue", ("kren",), context="probe-context"),
    )

    assert result.workspace is not None
    structure_items = [
        kernel.state.workspace_items[item_id]
        for item_id in result.workspace.event.active_item_ids
        if kernel.state.workspace_items[item_id].source_kind
        == WorkspaceSourceKind.EARNED_STRUCTURE
    ]
    assert len(structure_items) == 1
    assert structure_items[0].source_ref == structure_id
    assert set(structure_items[0].binding_refs) == set(kernel.state.structures[structure_id].member_concept_ids)
    # Merely invoking P may not bootstrap the lower-level traces that earned P.
    # Normal homeostatic decay still advances on the cycle, so strengths may
    # weaken and bookkeeping cycles may change; exposure/reinforcement may not.
    for association_id, prior in before.items():
        after = kernel.state.plasticity_associations[association_id]
        assert after.exposure_count == prior.exposure_count
        assert after.last_reinforced_cycle == prior.last_reinforced_cycle
        assert after.strength <= prior.strength


def test_ablated_structure_is_not_admitted_to_workspace() -> None:
    kernel, structure_id, _ = cultivated_promoted_kernel(1504)
    VerdantCompilationPipeline.ablate(kernel, structure_id, "workspace ablation control")
    development = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(
            resonance_top_k=4,
            resonance_commit_limit=0,
            association_recall_threshold=1.0,
        )
    )
    result = development.advance(
        kernel,
        command("ablated-cue", ("kren",), context="probe-context"),
    )
    assert result.workspace is not None
    assert all(
        kernel.state.workspace_items[item_id].source_kind
        != WorkspaceSourceKind.EARNED_STRUCTURE
        for item_id in result.workspace.event.active_item_ids
    )


def test_compilation_inspection_is_pure_and_availability_change_makes_it_stale() -> None:
    kernel, structure_id, _ = cultivated_promoted_kernel(1505)
    cue = concept_id(kernel, "kren")
    pipeline = VerdantCompilationPipeline()
    before = kernel.snapshot()
    report = pipeline.inspect(kernel, (cue,))
    assert kernel.snapshot() == before

    pipeline.ablate(kernel, structure_id, "invalidate pending compilation report")
    with pytest.raises(CompilationStaleError):
        pipeline.commit(kernel, report)


def test_compilation_checkpoint_preserves_ablation_and_probe_history(tmp_path) -> None:
    kernel, structure_id, _ = cultivated_promoted_kernel(1506)
    cue = concept_id(kernel, "kren")
    pipeline = VerdantCompilationPipeline()
    pipeline.probe(kernel, (cue,))
    pipeline.ablate(kernel, structure_id, "checkpoint ablation")
    pipeline.probe(kernel, (cue,))

    path = tmp_path / "compiled.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.state.ablated_structure_ids == kernel.state.ablated_structure_ids
    assert restored.state.structure_availability_events == kernel.state.structure_availability_events
    assert restored.state.compilation_probe_events == kernel.state.compilation_probe_events
    assert restored.fingerprint() == kernel.fingerprint()


def test_compilation_probe_does_not_mutate_semantic_truth() -> None:
    kernel, _, _ = cultivated_promoted_kernel(1507)
    cue = concept_id(kernel, "kren")
    before = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    VerdantCompilationPipeline().probe(kernel, (cue,))
    after = (
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.evidence),
    )
    assert after == before


def test_compiled_reconstruction_is_deterministic_across_identical_histories() -> None:
    left, _, _ = cultivated_promoted_kernel(1508)
    right, _, _ = cultivated_promoted_kernel(1508)
    left_cue = concept_id(left, "kren")
    right_cue = concept_id(right, "kren")
    pipeline = VerdantCompilationPipeline()

    left_report = pipeline.inspect(left, (left_cue,))
    right_report = pipeline.inspect(right, (right_cue,))
    assert left_report == right_report
