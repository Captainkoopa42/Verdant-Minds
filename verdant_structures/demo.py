from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(index: int) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=f"m14-triad-{index}",
        source_ref="m14:controlled-triad",
        modality="text",
        payload_sha256=digest(f"m14-triad-{index}"),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=("kren", "tar", "vel"),
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"controlled_m14_demo": True},
        metadata={"context_id": f"context-{index % 2}"},
    )


def run(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=1414, state_dim=64, run_label="milestone-14-demo")
    development = VerdantDevelopmentPipeline()
    formation_trace: list[dict[str, object]] = []

    for index in range(7):
        result = development.advance(kernel, command(index))
        snapshot = {
            "experience_index": index,
            "plastic_association_strengths": {
                association.association_id: association.strength
                for association in kernel.state.plasticity_associations.values()
            },
            "structure_candidate_count": len(kernel.state.structure_candidates),
        }
        if kernel.state.structure_candidates:
            candidate = next(iter(kernel.state.structure_candidates.values()))
            snapshot["candidate"] = {
                "candidate_id": candidate.candidate_id,
                "status": candidate.status.value,
                "occurrence_count": candidate.occurrence_count,
                "quality": candidate.quality.model_dump(mode="json"),
            }
        formation_trace.append(snapshot)

    candidate = next(iter(kernel.state.structure_candidates.values()))
    semantic_before = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    promotion = VerdantStructurePipeline().promote(kernel, candidate.candidate_id)
    structure = kernel.state.structures[promotion.event.structure_id]
    semantic_after = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    summary = {
        "milestone": 14,
        "name": "Earned Relational Structures",
        "formation_trace": formation_trace,
        "candidate_id": candidate.candidate_id,
        "candidate_members": [
            kernel.state.concepts[item].label for item in candidate.member_concept_ids
        ],
        "candidate_quality_before_promotion": candidate.quality.model_dump(mode="json"),
        "promotion_disposition": promotion.report.disposition.value,
        "promotion_rejection_codes": list(promotion.report.rejection_codes),
        "structure_id": structure.structure_id,
        "opaque_name": structure.opaque_name,
        "semantic_label_preinstalled": structure.semantic_label_preinstalled,
        "semantic_counts_before_promotion": semantic_before,
        "semantic_counts_after_promotion": semantic_after,
        "field_prototype_sha256": structure.field_prototype_sha256,
        "metrics": kernel.metrics(),
    }
    save_checkpoint(output_dir / "milestone_14_demo.vdk", kernel.snapshot())
    (output_dir / "milestone_14_structure_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    result = run(Path("artifacts"))
    print(json.dumps(result, indent=2, sort_keys=True))
