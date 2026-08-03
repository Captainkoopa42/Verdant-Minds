from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from verdant_ecwf import VerdantECWFPipeline
from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    ConceptProposal,
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    RoutingDisposition,
    ShardAuthorizationError,
    ShardIntegrityError,
    ShardStaleError,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_shards import VerdantShardPipeline


DOMAINS = {
    "physics": (
        ("gravity", "mass", "acceleration", "force"),
        (
            ("gravity", "mass", "acts_on"),
            ("force", "acceleration", "causes"),
            ("mass", "acceleration", "modulates"),
        ),
        (1.0, 0.0, 0.0, 0.0),
    ),
    "ecology": (
        ("watershed", "rainfall", "wildfire", "habitat"),
        (
            ("watershed", "rainfall", "channels"),
            ("rainfall", "wildfire", "influences"),
            ("wildfire", "habitat", "changes"),
        ),
        (0.0, 1.0, 0.0, 0.0),
    ),
    "interaction": (
        ("care", "trust", "repair", "boundary"),
        (
            ("care", "trust", "supports"),
            ("trust", "repair", "enables"),
            ("boundary", "care", "constrains"),
        ),
        (0.0, 0.0, 1.0, 0.0),
    ),
}


def teach(
    kernel: VerdantKernel,
    *,
    event_key: str,
    text: str,
    concepts: tuple[str, ...],
    relations: tuple[tuple[str, str, str], ...] = (),
    features: tuple[float, ...] = (0.0, 0.0, 0.0, 1.0),
):
    return kernel.apply_experience(
        ExperienceCommand(
            event_key=event_key,
            source_ref=f"handwritten-curriculum:{event_key}",
            modality="text",
            payload_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            feature_vector=features,
            concept_proposals=tuple(
                ConceptProposal(label=label) for label in concepts
            ),
            relation_proposals=tuple(
                RelationProposal(
                    source_label=source,
                    target_label=target,
                    relation_type=relation_type,
                    weight=0.80,
                    confidence=0.90,
                )
                for source, target, relation_type in relations
            ),
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "handwritten_curriculum": True,
                "milestone": 6,
            },
        )
    )


def concept_ids(kernel: VerdantKernel, labels: tuple[str, ...]) -> tuple[str, ...]:
    by_label = {item.label: item.concept_id for item in kernel.state.concepts.values()}
    return tuple(sorted(by_label[label] for label in labels))


def build_specialized_kernel() -> tuple[
    VerdantKernel,
    VerdantShardPipeline,
    dict[str, str],
]:
    kernel = VerdantKernel(seed=606, state_dim=64, run_label="shard-tests")
    shards = VerdantShardPipeline()
    shard_ids: dict[str, str] = {}
    for index, (domain, (labels, relations, features)) in enumerate(DOMAINS.items()):
        teach(
            kernel,
            event_key=f"domain-{index}-{domain}",
            text=f"Controlled handwritten lesson for {domain}.",
            concepts=labels,
            relations=relations,
            features=features,
        )
    for domain, (labels, _, _) in DOMAINS.items():
        formed = shards.form_shard(
            kernel,
            label=domain,
            concept_ids=concept_ids(kernel, labels),
        )
        shard_ids[domain] = formed.formation_event.report.proposed_shard_id
    return kernel, shards, shard_ids


def cue_domain(
    kernel: VerdantKernel,
    domain: str,
    event_key: str,
    labels: tuple[str, ...] | None = None,
):
    domain_labels, _, features = DOMAINS[domain]
    selected = labels or domain_labels[:3]
    result = teach(
        kernel,
        event_key=event_key,
        text=f"New controlled {domain} cue using {', '.join(selected)}.",
        concepts=tuple(selected),
        features=features,
    )
    evidence = (
        result.observation_evidence_id,
        result.translation_evidence_id,
        *result.additional_evidence_ids,
    )
    return concept_ids(kernel, tuple(selected)), tuple(sorted(evidence))


def semantic_counts(kernel: VerdantKernel) -> tuple[int, ...]:
    return (
        len(kernel.state.evidence),
        len(kernel.state.concepts),
        len(kernel.state.relations),
        len(kernel.state.claims),
        len(kernel.state.contradictions),
        len(kernel.state.revisions),
    )


def test_root_catalogs_canonical_truth_and_shards_only_reference_it() -> None:
    kernel, _, shard_ids = build_specialized_kernel()
    root = kernel.state.shards["root"]
    assert set(root.concept_ids) == set(kernel.state.concepts)
    assert set(root.relation_ids) == set(kernel.state.relations)
    assert kernel.state.active_shard_id == "root"
    for shard_id in shard_ids.values():
        shard = kernel.state.shards[shard_id]
        assert len(shard.concept_ids) == 4
        assert len(shard.relation_ids) == 3
        assert all(item in kernel.state.concepts for item in shard.concept_ids)
        assert all(item in kernel.state.relations for item in shard.relation_ids)


def test_formation_inspection_is_pure_and_requires_council_authorization() -> None:
    kernel = VerdantKernel(seed=607, state_dim=48, run_label="formation-auth")
    teach(
        kernel,
        event_key="physics",
        text="Gravity, mass, force, and acceleration are related.",
        concepts=DOMAINS["physics"][0],
        relations=DOMAINS["physics"][1],
        features=DOMAINS["physics"][2],
    )
    shards = VerdantShardPipeline()
    before = kernel.fingerprint()
    report = shards.inspect_formation(
        kernel,
        label="physics",
        concept_ids=concept_ids(kernel, DOMAINS["physics"][0]),
    )
    assert kernel.fingerprint() == before
    with pytest.raises(ShardAuthorizationError):
        shards.commit_formation(
            kernel,
            report,
            council_decision_event_id="missing-decision",
        )


def test_shard_bounds_are_enforced_before_commitment() -> None:
    kernel = VerdantKernel(seed=608, state_dim=48, run_label="bounds")
    labels = tuple(f"item-{index}" for index in range(4))
    teach(
        kernel,
        event_key="four-items",
        text="Four bounded test items.",
        concepts=labels,
    )
    kernel.state.shard_policy.max_concepts_per_shard = 3
    with pytest.raises(ValueError):
        VerdantShardPipeline().inspect_formation(
            kernel,
            label="too-large",
            concept_ids=concept_ids(kernel, labels),
        )


def test_directly_grounded_route_selects_ecology_and_preserves_the_cue() -> None:
    kernel, shards, shard_ids = build_specialized_kernel()
    cues, evidence = cue_domain(kernel, "ecology", "ecology-cue")
    before = semantic_counts(kernel)
    report = shards.inspect_routing(
        kernel,
        cue_concept_ids=cues,
        evidence_refs=evidence,
    )
    assert report.disposition == RoutingDisposition.ROUTE
    assert report.selected_shard_id == shard_ids["ecology"]
    selected = next(item for item in report.candidates if item.eligible)
    assert selected.components.direct_grounding == 1.0
    assert selected.directly_grounded_concept_ids == cues
    result = shards.route(
        kernel,
        cue_concept_ids=cues,
        evidence_refs=evidence,
    )
    assert kernel.state.active_shard_id == shard_ids["ecology"]
    assert result.routing_event.direct_cue_concept_ids == cues
    assert result.routing_event.evidence_refs == evidence
    assert semantic_counts(kernel) == before


def test_resonance_without_direct_cue_cannot_route() -> None:
    kernel, shards, _ = build_specialized_kernel()
    _, evidence = cue_domain(kernel, "physics", "resonance-only-evidence")
    report = kernel.inspect_resonance(
        DOMAINS["physics"][2],
        "text",
        top_k=6,
    )
    resonance = kernel.commit_resonance(
        report,
        evidence_refs=evidence,
        max_candidates=6,
    )
    route = shards.inspect_routing(
        kernel,
        cue_concept_ids=(),
        evidence_refs=evidence,
        resonance_event_ids=(resonance.resonance_event_id,),
    )
    assert route.disposition == RoutingDisposition.REJECT
    assert route.selected_shard_id is None
    assert all(not item.eligible for item in route.candidates)
    assert all(
        "insufficient_direct_grounding" in item.rejection_codes
        for item in route.candidates
    )


def test_resonance_may_modulate_but_cannot_override_direct_grounding() -> None:
    kernel, shards, shard_ids = build_specialized_kernel()
    ecology_cues, ecology_evidence = cue_domain(
        kernel, "ecology", "ecology-with-physics-resonance"
    )
    physics_query = kernel.inspect_resonance(
        DOMAINS["physics"][2],
        "text",
        top_k=8,
    )
    physics_resonance = kernel.commit_resonance(
        physics_query,
        evidence_refs=ecology_evidence,
        max_candidates=8,
    )
    report = shards.inspect_routing(
        kernel,
        cue_concept_ids=ecology_cues,
        evidence_refs=ecology_evidence,
        resonance_event_ids=(physics_resonance.resonance_event_id,),
    )
    assert report.selected_shard_id == shard_ids["ecology"]
    ecology = next(
        item for item in report.candidates if item.shard_id == shard_ids["ecology"]
    )
    physics = next(
        item for item in report.candidates if item.shard_id == shard_ids["physics"]
    )
    assert ecology.eligible is True
    assert physics.eligible is False
    assert physics.components.direct_grounding == 0.0


def test_no_ghost_bridges_and_completed_traversal_is_persisted() -> None:
    kernel, shards, _ = build_specialized_kernel()
    assert kernel.state.shard_bridges == {}
    cues, evidence = cue_domain(kernel, "ecology", "first-traversal")
    result = shards.route(kernel, cue_concept_ids=cues, evidence_refs=evidence)
    bridge = kernel.state.shard_bridges[result.routing_event.bridge_id]
    assert bridge.traversal_count == 1
    assert bridge.last_traversed_cycle == result.routing_event.committed_cycle
    assert bridge.evidence_refs == evidence
    assert all(item.traversal_count >= 1 for item in kernel.state.shard_bridges.values())


def test_repeated_cross_shard_route_increments_real_bridge_traffic() -> None:
    kernel, shards, shard_ids = build_specialized_kernel()
    ecology_cues, ecology_evidence = cue_domain(kernel, "ecology", "to-ecology")
    shards.route(kernel, cue_concept_ids=ecology_cues, evidence_refs=ecology_evidence)

    physics_cues, physics_evidence = cue_domain(kernel, "physics", "to-physics")
    first_cross = shards.route(
        kernel,
        cue_concept_ids=physics_cues,
        evidence_refs=physics_evidence,
    )
    assert first_cross.routing_event.to_shard_id == shard_ids["physics"]
    bridge_id = first_cross.routing_event.bridge_id
    assert kernel.state.shard_bridges[bridge_id].traversal_count == 1

    ecology_cues_2, ecology_evidence_2 = cue_domain(
        kernel, "ecology", "back-to-ecology"
    )
    second_cross = shards.route(
        kernel,
        cue_concept_ids=ecology_cues_2,
        evidence_refs=ecology_evidence_2,
    )
    assert second_cross.routing_event.bridge_id == bridge_id
    assert kernel.state.shard_bridges[bridge_id].traversal_count == 2
    assert kernel.state.active_shard_id == shard_ids["ecology"]


def test_exactly_one_shard_is_active_after_each_route() -> None:
    kernel, shards, _ = build_specialized_kernel()
    for index, domain in enumerate(("ecology", "physics", "interaction")):
        cues, evidence = cue_domain(kernel, domain, f"active-{index}-{domain}")
        shards.route(kernel, cue_concept_ids=cues, evidence_refs=evidence)
        active = [
            item.shard_id
            for item in kernel.state.shards.values()
            if item.status.value == "active"
        ]
        assert active == [kernel.state.active_shard_id]


def test_stale_routing_report_is_rejected_after_structural_change() -> None:
    kernel, shards, _ = build_specialized_kernel()
    cues, evidence = cue_domain(kernel, "ecology", "stale-route")
    report = shards.inspect_routing(
        kernel,
        cue_concept_ids=cues,
        evidence_refs=evidence,
    )
    teach(
        kernel,
        event_key="structural-change",
        text="A new supported concept changes the canonical structure.",
        concepts=("new-supported-concept",),
    )
    with pytest.raises(ShardStaleError):
        kernel.validate_routing_report(report)


def test_tampered_routing_report_is_rejected() -> None:
    kernel, shards, _ = build_specialized_kernel()
    cues, evidence = cue_domain(kernel, "ecology", "tamper-route")
    report = shards.inspect_routing(
        kernel,
        cue_concept_ids=cues,
        evidence_refs=evidence,
    )
    selected = report.candidates[0]
    altered = selected.model_copy(update={"score": max(0.0, selected.score - 0.1)})
    tampered = report.model_copy(
        update={"candidates": (altered, *report.candidates[1:])}
    )
    with pytest.raises(ShardIntegrityError):
        shards.commit_routing(
            kernel,
            tampered,
            council_decision_event_id="missing",
        )


def test_checkpoint_round_trip_preserves_shards_bridges_and_routes(
    tmp_path: Path,
) -> None:
    kernel, shards, _ = build_specialized_kernel()
    cues, evidence = cue_domain(kernel, "ecology", "checkpoint-route")
    shards.route(kernel, cue_concept_ids=cues, evidence_refs=evidence)
    path = tmp_path / "milestone-6.vdk"
    save_checkpoint(path, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(path))
    assert restored.snapshot() == kernel.snapshot()
    assert restored.fingerprint() == kernel.fingerprint()


def test_deterministic_rebuild_produces_identical_shard_history() -> None:
    def run_once() -> VerdantKernel:
        kernel, shards, _ = build_specialized_kernel()
        for index, domain in enumerate(("ecology", "physics", "interaction")):
            cues, evidence = cue_domain(kernel, domain, f"det-{index}-{domain}")
            shards.route(kernel, cue_concept_ids=cues, evidence_refs=evidence)
        return kernel

    left = run_once()
    right = run_once()
    assert left.snapshot() == right.snapshot()
    assert left.fingerprint() == right.fingerprint()
