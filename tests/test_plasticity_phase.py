from __future__ import annotations

import hashlib

import pytest

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    PlasticityStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_plasticity import VerdantPlasticityPipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
    event_key: str,
    labels: tuple[str, ...],
    feature: tuple[float, ...] = (1.0, 0.0, 0.0),
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"plasticity:{event_key}",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=feature,
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_plasticity_test": True},
    )


def one_association(kernel: VerdantKernel):
    assert len(kernel.state.plasticity_associations) == 1
    return next(iter(kernel.state.plasticity_associations.values()))


def test_repeated_coactivation_creates_and_strengthens_nonsemantic_association() -> None:
    kernel = VerdantKernel(seed=1301, state_dim=40, run_label="plasticity-strengthen")
    pipeline = VerdantDevelopmentPipeline()

    first = pipeline.advance(kernel, command("pair-1", ("kren", "tar")))
    association = one_association(kernel)
    first_strength = association.strength

    second = pipeline.advance(kernel, command("pair-2", ("kren", "tar")))
    association = one_association(kernel)

    assert first.plasticity is not None
    assert first.plasticity.report.created_association_ids
    assert second.plasticity is not None
    assert second.plasticity.report.reinforced_association_ids
    assert association.strength > first_strength
    assert association.exposure_count == 2
    assert len(kernel.state.relations) == 0


def test_unreinforced_local_association_decays() -> None:
    kernel = VerdantKernel(seed=1302, state_dim=40, run_label="plasticity-decay")
    pipeline = VerdantDevelopmentPipeline()
    pipeline.advance(kernel, command("ab-1", ("alpha", "beta")))
    pipeline.advance(kernel, command("ab-2", ("alpha", "beta")))
    association_id = next(iter(kernel.state.plasticity_associations))
    before = kernel.state.plasticity_associations[association_id].strength

    pipeline.advance(kernel, command("cd-1", ("gamma", "delta"), (0.0, 1.0, 0.0)))
    after = kernel.state.plasticity_associations[association_id].strength

    assert after < before


def test_plasticity_inspection_is_pure_and_stale_reports_fail() -> None:
    kernel = VerdantKernel(seed=1303, state_dim=40, run_label="plasticity-stale")
    development = VerdantDevelopmentPipeline()
    development.advance(kernel, command("ab-1", ("alpha", "beta")))
    workspace_event = kernel.state.workspace_cycle_events[-1]
    plasticity = VerdantPlasticityPipeline()

    before = kernel.snapshot()
    report = plasticity.inspect(kernel, workspace_event)
    assert kernel.snapshot() == before

    kernel.update_plasticity_policy(max_degree=kernel.state.plasticity_policy.max_degree + 1)
    with pytest.raises(PlasticityStaleError):
        plasticity.commit(kernel, report)


def test_replay_does_not_duplicate_plasticity() -> None:
    kernel = VerdantKernel(seed=1304, state_dim=40, run_label="plasticity-replay")
    development = VerdantDevelopmentPipeline()
    cmd = command("same-event", ("alpha", "beta"))

    first = development.advance(kernel, cmd)
    counts = (
        len(kernel.state.plasticity_events),
        len(kernel.state.plasticity_associations),
    )
    replay = development.advance(kernel, cmd)

    assert first.plasticity is not None
    assert replay.replayed is True
    assert replay.plasticity is None
    assert counts == (
        len(kernel.state.plasticity_events),
        len(kernel.state.plasticity_associations),
    )


def test_degree_and_edge_ratio_caps_prevent_clique_growth() -> None:
    kernel = VerdantKernel(seed=1305, state_dim=48, run_label="plasticity-anti-soup")
    kernel.update_plasticity_policy(
        max_degree=4,
        max_edge_ratio=2.0,
        max_new_associations_per_cycle=4,
        strength_budget_per_concept=1.6,
    )
    development = VerdantDevelopmentPipeline()

    labels = [f"unit_{index:02d}" for index in range(16)]
    for index in range(32):
        a = labels[index % len(labels)]
        b = labels[(index * 7 + 5) % len(labels)]
        if a == b:
            b = labels[(index + 1) % len(labels)]
        feature = (
            float((index % 3) == 0),
            float((index % 3) == 1),
            float((index % 3) == 2),
        )
        development.advance(kernel, command(f"growth-{index:03d}", (a, b), feature))

    degree: dict[str, int] = {}
    for association in kernel.state.plasticity_associations.values():
        for concept_id in association.concept_ids:
            degree[concept_id] = degree.get(concept_id, 0) + 1

    assert max(degree.values(), default=0) <= 4
    assert len(kernel.state.plasticity_associations) <= 2.0 * len(kernel.state.concepts)
    n = len(kernel.state.concepts)
    undirected_possible = n * (n - 1) / 2
    density = len(kernel.state.plasticity_associations) / max(1, undirected_possible)
    assert density < 0.35


def test_strength_budget_forces_competition() -> None:
    kernel = VerdantKernel(seed=1306, state_dim=48, run_label="plasticity-competition")
    kernel.update_plasticity_policy(
        max_degree=8,
        max_edge_ratio=4.0,
        strength_budget_per_concept=0.75,
    )
    development = VerdantDevelopmentPipeline()

    for index, other in enumerate(("b", "c", "d", "e", "f", "g")):
        for repeat in range(3):
            development.advance(
                kernel,
                command(f"hub-{index}-{repeat}", ("hub", other), (1.0, 0.0, 0.0)),
            )

    hub_id = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "hub"
    )
    total = sum(
        association.strength
        for association in kernel.state.plasticity_associations.values()
        if hub_id in association.concept_ids
    )
    assert total <= kernel.state.plasticity_policy.strength_budget_per_concept + 1e-9


def test_checkpoint_round_trip_preserves_plasticity(tmp_path) -> None:
    kernel = VerdantKernel(seed=1307, state_dim=40, run_label="plasticity-checkpoint")
    development = VerdantDevelopmentPipeline()
    development.advance(kernel, command("ab-1", ("alpha", "beta")))
    development.advance(kernel, command("ab-2", ("alpha", "beta")))

    path = tmp_path / "plasticity.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))

    assert restored.state.plasticity_associations == kernel.state.plasticity_associations
    assert restored.state.plasticity_events == kernel.state.plasticity_events
    assert restored.fingerprint() == kernel.fingerprint()


def test_identical_histories_produce_identical_plasticity() -> None:
    left = VerdantKernel(seed=1308, state_dim=40, run_label="plasticity-deterministic")
    right = VerdantKernel(seed=1308, state_dim=40, run_label="plasticity-deterministic")
    lp = VerdantDevelopmentPipeline()
    rp = VerdantDevelopmentPipeline()
    sequence = [
        command("x-1", ("x", "y"), (1.0, 0.0, 0.0)),
        command("z-1", ("z", "y"), (0.0, 1.0, 0.0)),
        command("x-2", ("x", "y"), (1.0, 0.0, 0.0)),
        command("z-2", ("z", "y"), (0.0, 1.0, 0.0)),
    ]
    for item in sequence:
        lp.advance(left, item)
        rp.advance(right, item)

    assert left.state.plasticity_associations == right.state.plasticity_associations
    assert left.state.plasticity_events == right.state.plasticity_events
    assert left.fingerprint() == right.fingerprint()


def test_learned_association_changes_later_workspace_and_ablation_removes_effect() -> None:
    learned = VerdantKernel(seed=1309, state_dim=40, run_label="plasticity-causal")
    development = VerdantDevelopmentPipeline()
    for index in range(3):
        development.advance(
            learned, command(f"ab-{index}", ("alpha", "beta"), (1.0, 0.0, 0.0))
        )

    ablated = VerdantKernel.from_state(learned.snapshot())
    ablated.state.plasticity_associations = {}
    ablated._validate_state()

    learned_result = development.advance(
        learned, command("alpha-alone", ("alpha",), (1.0, 0.0, 0.0))
    )
    ablated_result = VerdantDevelopmentPipeline().advance(
        ablated, command("alpha-alone", ("alpha",), (1.0, 0.0, 0.0))
    )

    learned_local = [
        item
        for item in learned_result.workspace.report.assessments
        if item.candidate.source_kind.value == "local_association"
    ]
    ablated_local = [
        item
        for item in ablated_result.workspace.report.assessments
        if item.candidate.source_kind.value == "local_association"
    ]
    assert len(learned_local) == 1
    assert learned_local[0].disposition.value == "admit"
    recalled_id = learned_local[0].candidate.binding_refs[0]
    assert learned.state.concepts[recalled_id].normalized_label == "beta"
    assert ablated_local == []
