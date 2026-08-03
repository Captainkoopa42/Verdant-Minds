from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_development import VerdantDevelopmentPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint
from verdant_structures import VerdantStructurePipeline

from .pipeline import VerdantHierarchyPipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(event_key: str, labels: tuple[str, ...], context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="m17:controlled-demo",
        modality="text",
        payload_sha256=digest(event_key + ":" + ":".join(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"m17_controlled_demo": True},
        metadata={"context_id": context},
    )


def candidate_labels(kernel: VerdantKernel, candidate) -> set[str]:
    return {kernel.state.concepts[cid].normalized_label for cid in candidate.member_concept_ids}


def cultivate_path(kernel: VerdantKernel, prefix: str, center: str | None = None) -> str:
    development = VerdantDevelopmentPipeline()
    if center is None:
        edges = ((f"{prefix}1", f"{prefix}2"), (f"{prefix}2", f"{prefix}3"), (f"{prefix}3", f"{prefix}4"))
    else:
        edges = ((center, f"{prefix}2"), (center, f"{prefix}3"), (center, f"{prefix}4"))
    for repeat in range(2):
        for index, edge in enumerate(edges):
            development.advance(
                kernel,
                command(
                    f"{prefix}-{repeat}-{index}",
                    edge,
                    f"{prefix}-context-{repeat}",
                ),
            )
    expected = {label for edge in edges for label in edge}
    candidate = max(
        (
            item
            for item in kernel.state.structure_candidates.values()
            if candidate_labels(kernel, item) == expected
        ),
        key=lambda item: item.occurrence_count,
    )
    return VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event.structure_id


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=17017, state_dim=16, run_label="milestone-17-demo")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
    kernel.update_structure_policy(
        minimum_members=4,
        maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_member_association_strength=0.20,
        minimum_reconstructability=0.25,
        minimum_internal_cohesion=0.20,
        minimum_recurrence_events=2,
        minimum_evidence_events=2,
        minimum_contexts=2,
    )
    kernel.update_hierarchy_policy(
        minimum_interaction_events=3,
        minimum_evidence_events=6,
        layered_probe_similarity=0.985,
    )

    family = [cultivate_path(kernel, prefix) for prefix in ("a", "b", "c")]
    interaction = VerdantStructureInteractionPipeline()
    hierarchy = VerdantHierarchyPipeline()
    progression = []
    for sid in family:
        interaction.interact(kernel, sid)
        observed = hierarchy.observe(kernel)
        if observed:
            item = observed.report.proposed_candidates[0]
            progression.append(
                {
                    "interaction_events": len(item.interaction_event_ids),
                    "status": item.status.value,
                    "pair_coverage": item.quality.pair_coverage,
                    "alignment_cohesion": item.quality.alignment_cohesion,
                    "prototype_cohesion": item.quality.prototype_cohesion,
                }
            )

    candidate = next(
        item for item in kernel.state.hierarchy_candidates.values()
        if set(item.member_structure_ids) == set(family)
    )
    promoted = hierarchy.promote(kernel, candidate.candidate_id)
    layered_id = promoted.event.layered_structure_id

    # Controls are created only after Q has already formed.
    star = cultivate_path(kernel, "s", center="s1")
    novel = cultivate_path(kernel, "d")

    enabled = hierarchy.inspect_probe(kernel, novel)
    hierarchy.ablate(kernel, layered_id, "M17 controlled demo ablation")
    ablated = hierarchy.inspect_probe(kernel, novel)
    hierarchy.restore(kernel, layered_id, "M17 controlled demo restoration")
    restored = hierarchy.inspect_probe(kernel, novel)
    star_probe = hierarchy.inspect_probe(kernel, star)

    summary = {
        "milestone": 17,
        "family_member_structure_ids": family,
        "higher_order_candidate_id": candidate.candidate_id,
        "layered_structure_id": layered_id,
        "layered_opaque_name": kernel.state.layered_structures[layered_id].opaque_name,
        "candidate_progression": progression,
        "quality_at_promotion": candidate.quality.model_dump(mode="json"),
        "novel_query_structure_id": novel,
        "unrelated_star_structure_id": star,
        "with_q": enabled.model_dump(mode="json"),
        "ablated_q": ablated.model_dump(mode="json"),
        "restored_q": restored.model_dump(mode="json"),
        "unrelated_control": star_probe.model_dump(mode="json"),
        "semantic_counts": {
            "concepts": len(kernel.state.concepts),
            "relations": len(kernel.state.relations),
            "claims": len(kernel.state.claims),
        },
        "metrics": kernel.metrics(),
    }
    (output_dir / "milestone_17_hierarchy_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    save_checkpoint(output_dir / "milestone_17_hierarchy_demo.vdk", kernel.snapshot())
    return summary


if __name__ == "__main__":
    summary = run(Path("artifacts"))
    print(json.dumps(summary, indent=2, sort_keys=True))
