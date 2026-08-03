from __future__ import annotations

import json
import re
from pathlib import Path

from cognitive_chunk_v2.archive import CognitiveChunkArchive
from verdant_kernel import VerdantKernel, save_checkpoint

from .models import GrammarRuleId
from .pipeline import LanguageLearningResult, VerdantLanguagePipeline


_SAFE = re.compile(r"[^a-z0-9_-]+")


def _safe_name(value: str) -> str:
    return _SAFE.sub("_", value.lower()).strip("_")


def _save_chunk(
    directory: Path,
    label: str,
    result: LanguageLearningResult,
) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_name(label)}.ecchunk.zip"
    CognitiveChunkArchive.save(path, result.chunk, result.store)
    return str(path)


def run_demo(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir = output_dir / "milestone_2_chunks"
    kernel = VerdantKernel(seed=2602, state_dim=64, run_label="milestone-2-language")
    pipeline = VerdantLanguagePipeline()
    archives: list[str] = []

    for rule in GrammarRuleId:
        result = pipeline.teach_rule(kernel, rule)
        archives.append(_save_chunk(chunk_dir, f"rule_{rule.value}", result))

    for index, result in enumerate(pipeline.teach_foundational_lexicon(kernel), start=1):
        archives.append(_save_chunk(chunk_dir, f"lexeme_{index:02d}", result))

    sentences = (
        ("push-ab", "A pushes B."),
        ("push-ba", "B pushes A."),
        ("door-open-positive", "The door is open."),
        ("door-open-negative", "The door is not open."),
        ("sound-before-light", "The sound occurred before the light."),
        ("light-before-sound", "The light occurred before the sound."),
        ("dog-push-present", "The dog pushes the child."),
        ("dog-push-past", "Dog pushed child."),
        ("malformed-order", "B A pushes."),
    )
    analyses: list[dict[str, object]] = []
    for event_key, sentence in sentences:
        result = pipeline.learn_sentence(
            kernel,
            sentence,
            event_key=event_key,
        )
        archives.append(_save_chunk(chunk_dir, event_key, result))
        analyses.append(
            {
                "event_key": event_key,
                "sentence": sentence,
                "parsed": result.analysis.parsed,
                "rejection_reason": result.analysis.rejection_reason,
                "frame": (
                    result.analysis.frame.model_dump(mode="json")
                    if result.analysis.frame is not None
                    else None
                ),
                "concept_ids": list(result.kernel_result.concept_ids),
                "relation_ids": list(result.kernel_result.relation_ids),
            }
        )

    concept_labels = {
        concept_id: concept.label
        for concept_id, concept in kernel.state.concepts.items()
    }
    selected_relations = []
    for relation in sorted(
        kernel.state.relations.values(),
        key=lambda item: (item.relation_type, item.source_concept_id, item.target_concept_id),
    ):
        if relation.relation_type in {
            "action:push",
            "action:chase",
            "has_property",
            "does_not_have_property",
            "before",
        }:
            selected_relations.append(
                {
                    "relation_type": relation.relation_type,
                    "source": concept_labels[relation.source_concept_id],
                    "target": concept_labels[relation.target_concept_id],
                    "confidence": relation.confidence,
                    "evidence_count": len(relation.evidence_refs),
                }
            )

    checkpoint_path = output_dir / "milestone_2_language_demo.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())
    summary = {
        "milestone": 2,
        "description": (
            "Handwritten grammar and lexicon curriculum through CognitiveChunk v2 "
            "into the canonical Verdant kernel."
        ),
        "kernel_id": kernel.state.identity.kernel_id,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "metrics": kernel.metrics(),
        "enabled_rules": [
            item.value for item in pipeline.analyzer.enabled_rules(kernel)
        ],
        "analyses": analyses,
        "selected_relations": selected_relations,
        "chunk_archive_count": len(archives),
        "chunk_archives": archives,
        "claims_not_made": [
            "autonomous grammar induction",
            "unrestricted English understanding",
            "grounding beyond handwritten text curriculum",
            "consciousness",
        ],
    }
    summary_path = output_dir / "milestone_2_language_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    artifact_dir = Path(__file__).resolve().parents[1] / "artifacts"
    print(json.dumps(run_demo(artifact_dir), indent=2, sort_keys=True))
