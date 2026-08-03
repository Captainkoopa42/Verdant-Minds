from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint
from verdant_refolding import VerdantRefoldingPipeline
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def learning_command(event_key: str, labels: tuple[str, str], context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="m18:demo",
        modality="text",
        payload_sha256=digest(event_key + repr(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"milestone_18_demo": True},
        metadata={"context_id": context},
    )


def challenge_evidence(kernel: VerdantKernel, event_key: str, context: str) -> tuple[str, ...]:
    result = kernel.apply_experience(
        ExperienceCommand(
            event_key=event_key,
            source_ref="m18:contradiction",
            modality="text",
            payload_sha256=digest(event_key),
            feature_vector=(0.0, 1.0, 0.0),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.OBSERVATION,
            semantic_evidence_details={
                "controlled_structural_contradiction": True,
                "semantic_mutation_permitted": False,
            },
            metadata={"context_id": context, "event_type": "structural_challenge"},
        )
    )
    return tuple(
        sorted(
            {
                result.observation_evidence_id,
                result.translation_evidence_id,
                *result.additional_evidence_ids,
            }
        )
    )


def concept_id(kernel: VerdantKernel, label: str) -> str:
    return next(
        cid for cid, concept in kernel.state.concepts.items()
        if concept.normalized_label == label
    )


def member_labels(kernel: VerdantKernel, ids) -> list[str]:
    return sorted(kernel.state.concepts[item].label for item in ids)


def build_demo_kernel() -> tuple[VerdantKernel, str]:
    kernel = VerdantKernel(seed=1818, state_dim=16, run_label="milestone-18-demo")
    kernel.update_plasticity_policy(
        decay_rate=0.0,
        learning_rate=0.50,
        maximum_degree=12,
        maximum_edge_node_ratio=6.0,
        strength_budget_per_concept=5.0,
    )
    kernel.update_structure_policy(
        minimum_members=6,
        maximum_members=6,
        maximum_neighbors_per_seed=6,
        minimum_member_association_strength=0.15,
        minimum_reconstructability=0.18,
        minimum_internal_cohesion=0.18,
        minimum_boundary_selectivity=0.50,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
    )
    development = VerdantDevelopmentPipeline()
    edges = (
        ("a1", "a2"),
        ("a2", "a3"),
        ("a1", "a3"),
        ("b1", "b2"),
        ("b2", "b3"),
        ("b1", "b3"),
        ("a3", "b1"),
        ("a3", "b2"),
        ("a3", "b3"),
    )
    for repeat in range(5):
        for index, edge in enumerate(edges):
            development.advance(
                kernel,
                learning_command(
                    f"learn-{repeat}-{index}", edge, f"world-{repeat % 2}"
                ),
            )
    expected = {item for edge in edges for item in edge}
    candidate = max(
        (
            item for item in kernel.state.structure_candidates.values()
            if set(member_labels(kernel, item.member_concept_ids)) == expected
        ),
        key=lambda item: item.occurrence_count,
    )
    structure_id = VerdantStructurePipeline().promote(
        kernel, candidate.candidate_id
    ).event.structure_id
    return kernel, structure_id


def run_demo(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel, parent_id = build_demo_kernel()
    parent = kernel.state.structures[parent_id]
    refolding = VerdantRefoldingPipeline()
    compilation = VerdantCompilationPipeline()

    semantic_before = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    pre_probe = compilation.inspect(kernel, (concept_id(kernel, "a1"),))

    # One observation alone is intentionally insufficient.
    first_refs = challenge_evidence(kernel, "challenge-a3-b1-0", "challenge-0")
    refolding.challenge(
        kernel,
        parent_id,
        tuple(sorted((concept_id(kernel, "a3"), concept_id(kernel, "b1")))),
        evidence_refs=first_refs,
        confidence=0.80,
    )
    single_observation_disposition = refolding.inspect(kernel, parent_id).disposition.value

    # Finish the first challenged edge and challenge the remaining cross-links.
    refs = challenge_evidence(kernel, "challenge-a3-b1-1", "challenge-1")
    refolding.challenge(
        kernel,
        parent_id,
        tuple(sorted((concept_id(kernel, "a3"), concept_id(kernel, "b1")))),
        evidence_refs=refs,
        confidence=0.80,
    )
    for edge_index, target in enumerate(("b2", "b3"), start=2):
        for repeat in range(2):
            refs = challenge_evidence(
                kernel,
                f"challenge-a3-{target}-{repeat}",
                f"challenge-{repeat}",
            )
            refolding.challenge(
                kernel,
                parent_id,
                tuple(sorted((concept_id(kernel, "a3"), concept_id(kernel, target)))),
                evidence_refs=refs,
                confidence=0.80,
            )

    report = refolding.inspect(kernel, parent_id)
    event = refolding.commit(kernel, report)
    children = [kernel.state.structures[item] for item in event.produced_structure_ids]
    post_a = compilation.inspect(kernel, (concept_id(kernel, "a1"),))
    post_b = compilation.inspect(kernel, (concept_id(kernel, "b1"),))

    semantic_after = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }

    summary = {
        "milestone": 18,
        "name": "Refolding Under Contradiction",
        "single_observation_disposition": single_observation_disposition,
        "final_disposition": report.disposition.value,
        "parent": {
            "structure_id": parent_id,
            "opaque_name": parent.opaque_name,
            "member_labels": member_labels(kernel, parent.member_concept_ids),
            "frozen_edge_count": len(parent.internal_edge_snapshots),
            "available_after_refold": kernel.structure_is_available(parent_id),
        },
        "mature_challenge_count": len(report.challenge_ids),
        "removed_edge_count": len(report.removed_association_ids),
        "children": [
            {
                "structure_id": item.structure_id,
                "opaque_name": item.opaque_name,
                "member_labels": member_labels(kernel, item.member_concept_ids),
                "edge_count": len(item.internal_edge_snapshots),
                "lineage_parent_structure_id": item.lineage_parent_structure_id,
                "lineage_root_structure_id": item.lineage_root_structure_id,
                "revision_index": item.revision_index,
                "perturbation_survival": item.quality_at_promotion.perturbation_survival,
                "contradiction_tolerance": item.quality_at_promotion.contradiction_tolerance,
            }
            for item in children
        ],
        "compilation_before_refold": {
            "structure_id": pre_probe.structure_id,
            "reconstructed_labels": member_labels(kernel, pre_probe.reconstructed_concept_ids),
            "low_level_work": pre_probe.cost.low_level_work,
        },
        "compilation_after_refold_a1": {
            "structure_id": post_a.structure_id,
            "reconstructed_labels": member_labels(kernel, post_a.reconstructed_concept_ids),
            "low_level_work": post_a.cost.low_level_work,
        },
        "compilation_after_refold_b1": {
            "structure_id": post_b.structure_id,
            "reconstructed_labels": member_labels(kernel, post_b.reconstructed_concept_ids),
            "low_level_work": post_b.cost.low_level_work,
        },
        "semantic_counts_before": semantic_before,
        "semantic_counts_after": semantic_after,
        "semantic_firewall_held": semantic_before == semantic_after,
        "structural_challenge_count": len(kernel.state.structural_challenges),
        "refold_event_count": len(kernel.state.structure_refold_events),
        "refolded_structure_count": sum(
            item.lineage_parent_structure_id is not None
            for item in kernel.state.structures.values()
        ),
    }
    save_checkpoint(output_dir / "milestone_18_refolding_demo.vdk", kernel.snapshot())
    (output_dir / "milestone_18_refolding_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_dir / "milestone_18_demo_stdout.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "artifacts"
    print(json.dumps(run_demo(root), indent=2, sort_keys=True))
