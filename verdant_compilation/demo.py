from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint
from verdant_structures import VerdantStructurePipeline


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def command(index: int) -> ExperienceCommand:
    labels = ("kren", "tar", "vel", "mip", "zog")
    return ExperienceCommand(
        event_key=f"m15-five-{index}",
        source_ref="m15:controlled-demo",
        modality="text",
        payload_sha256=digest(f"m15-five-{index}:{':'.join(labels)}"),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={
            "controlled_m15_demo": True,
            "taught_content": "primitive_symbol_presence_only",
        },
        metadata={"context_id": f"world-{index % 2}"},
    )


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=1515, state_dim=48, run_label="milestone-15-demo")
    development = VerdantDevelopmentPipeline()
    structures = VerdantStructurePipeline()
    compilation = VerdantCompilationPipeline()

    for index in range(9):
        development.advance(kernel, command(index))

    eligible = [
        item
        for item in kernel.state.structure_candidates.values()
        if item.status.value == "eligible"
    ]
    if not eligible:
        raise RuntimeError("Controlled M15 demo did not produce an eligible structure.")
    candidate = max(
        eligible,
        key=lambda item: (len(item.member_concept_ids), item.candidate_id),
    )
    promotion = structures.promote(kernel, candidate.candidate_id)
    structure_id = promotion.event.structure_id
    structure = kernel.state.structures[structure_id]
    cue = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "kren"
    )

    with_p = compilation.probe(kernel, (cue,)).report
    compilation.ablate(kernel, structure_id, "controlled M15 causal ablation")
    without_p = compilation.probe(kernel, (cue,)).report
    compilation.restore(kernel, structure_id, "controlled M15 causal restoration")
    restored_p = compilation.probe(kernel, (cue,)).report

    semantic_counts = {
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    summary = {
        "milestone": 15,
        "name": "Cognitive Compilation",
        "candidate_id": candidate.candidate_id,
        "structure_id": structure_id,
        "opaque_name": structure.opaque_name,
        "member_count": len(structure.member_concept_ids),
        "member_labels_human_readable": sorted(
            kernel.state.concepts[item].label for item in structure.member_concept_ids
        ),
        "semantic_counts_after_test": semantic_counts,
        "with_structure": with_p.model_dump(mode="json"),
        "ablated": without_p.model_dump(mode="json"),
        "restored": restored_p.model_dump(mode="json"),
        "causal_checks": {
            "same_reconstruction_all_three": (
                with_p.reconstructed_concept_ids
                == without_p.reconstructed_concept_ids
                == restored_p.reconstructed_concept_ids
            ),
            "ablation_removed_compiled_path": (
                with_p.disposition.value == "use_structure"
                and without_p.disposition.value == "fallback_low_level"
            ),
            "restoration_returned_compiled_path": (
                restored_p.disposition.value == "use_structure"
                and restored_p.cost == with_p.cost
            ),
            "compiled_low_level_work": with_p.cost.low_level_work,
            "ablated_low_level_work": without_p.cost.low_level_work,
            "restored_low_level_work": restored_p.cost.low_level_work,
            "compression_gain": with_p.compression_gain,
        },
    }
    save_checkpoint(output_dir / "milestone_15_compilation_demo.vdk", kernel.snapshot())
    (output_dir / "milestone_15_compilation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "artifacts"
    summary = run(root)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
