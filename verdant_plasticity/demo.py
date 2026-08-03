from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint


ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(
    event_key: str,
    labels: tuple[str, ...],
    feature: tuple[float, ...],
) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"m13-demo:{event_key}",
        modality="synthetic",
        payload_sha256=digest(event_key + "|" + "|".join(labels)),
        feature_vector=feature,
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"milestone": 13, "synthetic": True},
    )


def local_recall_labels(result, kernel: VerdantKernel) -> list[str]:
    labels: list[str] = []
    if result.workspace is None:
        return labels
    for assessment in result.workspace.report.assessments:
        if assessment.candidate.source_kind.value != "local_association":
            continue
        for concept_id in assessment.candidate.binding_refs:
            concept = kernel.state.concepts.get(concept_id)
            if concept is not None:
                labels.append(concept.label)
    return sorted(set(labels))


def main() -> dict[str, object]:
    kernel = VerdantKernel(seed=1313, state_dim=48, run_label="milestone-13-demo")
    kernel.update_plasticity_policy(
        max_degree=4,
        max_edge_ratio=2.0,
        strength_budget_per_concept=1.6,
        max_new_associations_per_cycle=4,
    )
    development = VerdantDevelopmentPipeline()

    probe_before = development.advance(
        kernel,
        command("probe-before", ("kren",), (1.0, 0.0, 0.0)),
    )
    before_recall = local_recall_labels(probe_before, kernel)

    pair_strengths: list[float] = []
    for index in range(6):
        development.advance(
            kernel,
            command(f"kren-tar-{index}", ("kren", "tar"), (1.0, 0.0, 0.0)),
        )
        pair = next(
            (association
             for association in kernel.state.plasticity_associations.values()
             if {
                 kernel.state.concepts[association.concept_ids[0]].normalized_label,
                 kernel.state.concepts[association.concept_ids[1]].normalized_label,
             } == {"kren", "tar"}),
            None,
        )
        pair_strengths.append(pair.strength if pair is not None else 0.0)

    probe_after = development.advance(
        kernel,
        command("probe-after", ("kren",), (1.0, 0.0, 0.0)),
    )
    after_recall = local_recall_labels(probe_after, kernel)

    # Stress growth with meaningless symbols.  Twelve concepts are trained in
    # a ring plus skip-links.  Each intended neighborhood repeats three times;
    # an unconstrained coactivation graph can still accumulate many indirect
    # links, while the M13 policy must keep degree and total strength bounded.
    labels = [f"mip_{index:02d}" for index in range(12)]
    training_pairs: list[tuple[str, str]] = []
    for index, label in enumerate(labels):
        training_pairs.append((label, labels[(index + 1) % len(labels)]))
        training_pairs.append((label, labels[(index + 3) % len(labels)]))
    for repeat in range(3):
        for pair_index, (a, b) in enumerate(training_pairs):
            feature = (
                float(pair_index % 3 == 0),
                float(pair_index % 3 == 1),
                float(pair_index % 3 == 2),
            )
            development.advance(
                kernel,
                command(f"stress-{repeat}-{pair_index:03d}", (a, b), feature),
            )

    degree: dict[str, int] = {}
    strength_total: dict[str, float] = {}
    for association in kernel.state.plasticity_associations.values():
        for concept_id in association.concept_ids:
            degree[concept_id] = degree.get(concept_id, 0) + 1
            strength_total[concept_id] = strength_total.get(concept_id, 0.0) + association.strength

    concept_count = len(kernel.state.concepts)
    edge_count = len(kernel.state.plasticity_associations)
    possible = concept_count * max(0, concept_count - 1) / 2
    density = edge_count / possible if possible else 0.0
    summary = {
        "milestone": 13,
        "title": "Local Plasticity Without Saturation",
        "concept_count": concept_count,
        "canonical_relation_count": len(kernel.state.relations),
        "plasticity_association_count": edge_count,
        "plasticity_event_count": len(kernel.state.plasticity_events),
        "plasticity_density": density,
        "plasticity_edge_ratio": edge_count / max(1, concept_count),
        "max_plasticity_degree": max(degree.values(), default=0),
        "max_total_strength_per_concept": max(strength_total.values(), default=0.0),
        "configured_max_degree": kernel.state.plasticity_policy.max_degree,
        "configured_max_edge_ratio": kernel.state.plasticity_policy.max_edge_ratio,
        "configured_strength_budget": kernel.state.plasticity_policy.strength_budget_per_concept,
        "kren_tar_strength_trajectory": pair_strengths,
        "probe_before_local_recall": before_recall,
        "probe_after_local_recall": after_recall,
        "tar_recalled_after_learning": "tar" in after_recall,
        "semantic_relation_firewall_held": len(kernel.state.relations) == 0,
        "cycle": kernel.state.cycle,
        "fingerprint": kernel.fingerprint(),
    }

    save_checkpoint(ARTIFACTS / "milestone_13_plasticity_demo.vdk", kernel.snapshot())
    (ARTIFACTS / "milestone_13_plasticity_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    main()
