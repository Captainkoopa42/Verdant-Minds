from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint
from verdant_structures import VerdantStructurePipeline
from .pipeline import VerdantStructureInteractionPipeline


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _command(event_key: str, labels: tuple[str, ...], context: str) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref="milestone16:controlled",
        modality="text",
        payload_sha256=_digest(event_key + ":" + ":".join(labels)),
        feature_vector=(1.0, 0.0, 0.0),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"milestone16_demo": True},
        metadata={"context_id": context},
    )


def _candidate_labels(kernel: VerdantKernel, candidate) -> set[str]:
    return {kernel.state.concepts[item].normalized_label for item in candidate.member_concept_ids}


def _cultivate(kernel: VerdantKernel, prefix: str, edges: tuple[tuple[str, str], ...]) -> str:
    development = VerdantDevelopmentPipeline()
    for repeat in range(4):
        for index, edge in enumerate(edges):
            development.advance(
                kernel,
                _command(
                    f"{prefix}-{repeat}-{index}",
                    edge,
                    f"{prefix}-context-{repeat % 2}",
                ),
            )
    wanted = {label for edge in edges for label in edge}
    candidate = max(
        (item for item in kernel.state.structure_candidates.values() if _candidate_labels(kernel, item) == wanted),
        key=lambda item: item.occurrence_count,
    )
    return VerdantStructurePipeline().promote(kernel, candidate.candidate_id).event.structure_id


def run(output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=1601, state_dim=32, run_label="milestone-16-demo")
    kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.25)
    kernel.update_structure_policy(
        minimum_members=4,
        maximum_members=4,
        maximum_neighbors_per_seed=3,
        minimum_reconstructability=0.35,
        minimum_internal_cohesion=0.30,
        minimum_recurrence_events=3,
        minimum_evidence_events=3,
    )

    path_a = _cultivate(kernel, "world-a", (("a1", "a2"), ("a2", "a3"), ("a3", "a4")))
    path_b = _cultivate(kernel, "world-b", (("b1", "b2"), ("b2", "b3"), ("b3", "b4")))
    star_c = _cultivate(kernel, "world-c", (("c1", "c2"), ("c1", "c3"), ("c1", "c4")))

    pipeline = VerdantStructureInteractionPipeline()
    before_semantics = (len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims), len(kernel.state.evidence))
    result = pipeline.interact(kernel, path_a)
    after_semantics = (len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims), len(kernel.state.evidence))

    by_target = {item.target_structure_id: item for item in result.report.candidates}
    match = by_target[path_b]
    control = by_target[star_c]
    labels = lambda sid: sorted(kernel.state.concepts[item].normalized_label for item in kernel.state.structures[sid].member_concept_ids)
    mapping = [
        [kernel.state.concepts[a].normalized_label, kernel.state.concepts[b].normalized_label]
        for a, b in match.member_mapping
    ]
    summary = {
        "milestone": 16,
        "source_structure": {"id": path_a, "labels": labels(path_a), "shape": "4-node path"},
        "isomorphic_target": {"id": path_b, "labels": labels(path_b), "shape": "4-node path"},
        "nonisomorphic_control": {"id": star_c, "labels": labels(star_c), "shape": "4-node star"},
        "best_verified_target": result.report.best_target_structure_id,
        "isomorphic_field_similarity": match.field_similarity,
        "isomorphic_symbolic_similarity": match.symbolic_similarity,
        "isomorphic_disposition": match.disposition.value,
        "control_field_similarity": control.field_similarity,
        "control_symbolic_similarity": control.symbolic_similarity,
        "control_disposition": control.disposition.value,
        "verified_role_mapping": mapping,
        "surface_symbol_overlap": 0,
        "semantic_store_unchanged_by_interaction": before_semantics == after_semantics,
        "interaction_event_id": result.event.event_id,
        "metrics": kernel.metrics(),
    }
    (output_dir / "milestone_16_interaction_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    save_checkpoint(output_dir / "milestone_16_interaction_demo.vdk", kernel.snapshot())
    return summary


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    result = run(root / "artifacts")
    print(json.dumps(result, indent=2, sort_keys=True))
