from __future__ import annotations

import json
from pathlib import Path

from cognitive_chunk_v2.archive import CognitiveChunkArchive
from verdant_kernel import VerdantKernel, save_checkpoint
from verdant_language import GrammarRuleId, VerdantLanguagePipeline

from .pipeline import VerdantECWFPipeline


def _candidate_rows(kernel: VerdantKernel, report) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for candidate in report.candidates:
        concept = kernel.state.concepts[candidate.concept_id]
        rows.append(
            {
                "rank": candidate.rank,
                "concept_id": candidate.concept_id,
                "label": concept.label,
                "score": candidate.score,
                "contribution": candidate.contribution.model_dump(mode="json"),
            }
        )
    return rows


def _score_by_label(kernel: VerdantKernel, report) -> dict[str, float]:
    return {
        kernel.state.concepts[item.concept_id].label: item.score
        for item in report.candidates
    }


def run_demo(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=2604, state_dim=96, run_label="milestone-4-ecwf")
    language = VerdantLanguagePipeline()
    ecwf = VerdantECWFPipeline()

    for rule in (
        GrammarRuleId.TRANSITIVE_SVO,
        GrammarRuleId.COPULAR_PROPERTY,
        GrammarRuleId.TEMPORAL_BEFORE,
    ):
        language.teach_rule(kernel, rule)
    language.teach_foundational_lexicon(kernel)

    cue_text = "The dog pushes the child."
    before_query = ecwf.inspect_text(
        kernel,
        cue_text,
        top_k=len(kernel.state.concepts),
        source_name="before_learning_query.txt",
    )
    before_rows = _candidate_rows(kernel, before_query.report)
    before_scores = _score_by_label(kernel, before_query.report)

    first = language.learn_sentence(
        kernel,
        "The dog pushes the child.",
        event_key="dog-push-child-first",
    )
    language.learn_sentence(
        kernel,
        "The sound occurred before the light.",
        event_key="sound-before-light",
    )
    language.learn_sentence(
        kernel,
        "The door is open.",
        event_key="door-open",
    )
    repeated = language.learn_sentence(
        kernel,
        "Dog pushed child.",
        event_key="dog-push-child-repeated",
    )

    after_query = ecwf.inspect_text(
        kernel,
        cue_text,
        top_k=len(kernel.state.concepts),
        source_name="after_learning_query.txt",
    )
    after_rows_all = _candidate_rows(kernel, after_query.report)
    after_scores = _score_by_label(kernel, after_query.report)
    target_labels = ("lexeme:dog", "lexeme:push", "lexeme:child")
    target_changes = {
        label: {
            "before": before_scores.get(label),
            "after": after_scores.get(label),
            "delta": (
                after_scores.get(label, 0.0) - before_scores.get(label, 0.0)
            ),
        }
        for label in target_labels
    }

    semantic_counts_before_commit = {
        "evidence": len(kernel.state.evidence),
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
        "contradictions": len(kernel.state.contradictions),
        "revisions": len(kernel.state.revisions),
    }
    commit_query = ecwf.inspect_text(
        kernel,
        cue_text,
        top_k=5,
        source_name="commit_query.txt",
    )
    event = kernel.commit_resonance(
        commit_query.report,
        evidence_refs=(
            repeated.kernel_result.observation_evidence_id,
            repeated.kernel_result.translation_evidence_id,
            *repeated.kernel_result.additional_evidence_ids,
        ),
        max_candidates=5,
    )
    semantic_counts_after_commit = {
        "evidence": len(kernel.state.evidence),
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
        "contradictions": len(kernel.state.contradictions),
        "revisions": len(kernel.state.revisions),
    }

    query_archive_path = output_dir / "milestone_4_resonance_query.ecchunk.zip"
    CognitiveChunkArchive.save(
        query_archive_path,
        commit_query.chunk,
        commit_query.store,
    )
    checkpoint_path = output_dir / "milestone_4_ecwf_demo.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())

    summary = {
        "milestone": 4,
        "description": (
            "Pure persistent ECWF with deterministic dense concept addressing, "
            "path-dependent resonance, exact contribution accounting, and an "
            "evidence-bounded attention boundary."
        ),
        "kernel_id": kernel.state.identity.kernel_id,
        "schema_version": kernel.state.identity.schema_version,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "query_chunk_archive": str(query_archive_path),
        "metrics": kernel.metrics(),
        "ecwf_policy": kernel.state.ecwf_policy.model_dump(mode="json"),
        "address_diagnostics": kernel.address_diagnostics(),
        "cue_text": cue_text,
        "before_learning_top_10": before_rows[:10],
        "after_learning_top_10": after_rows_all[:10],
        "target_score_changes": target_changes,
        "committed_resonance_event": event.model_dump(mode="json"),
        "semantic_counts_before_commit": semantic_counts_before_commit,
        "semantic_counts_after_commit": semantic_counts_after_commit,
        "semantic_counts_unchanged_by_resonance_commit": (
            semantic_counts_before_commit == semantic_counts_after_commit
        ),
        "important_boundary": (
            "Resonance ranks already existing possibilities and may place them in "
            "attention. It cannot create evidence, concepts, relations, claims, "
            "contradictions, or revisions."
        ),
        "claims_not_made": [
            "semantic understanding from resonance alone",
            "autonomous concept formation",
            "live sensory grounding",
            "consciousness",
        ],
    }
    summary_path = output_dir / "milestone_4_ecwf_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    artifact_dir = Path(__file__).resolve().parents[1] / "artifacts"
    print(json.dumps(run_demo(artifact_dir), indent=2, sort_keys=True))
