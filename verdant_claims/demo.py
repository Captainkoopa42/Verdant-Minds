from __future__ import annotations

import json
import re
from pathlib import Path

from cognitive_chunk_v2.archive import CognitiveChunkArchive
from verdant_kernel import ClaimPolarity, ClaimSourceClass, VerdantKernel, save_checkpoint
from verdant_language import GrammarRuleId, VerdantLanguagePipeline

from .pipeline import ClaimLearningPipeline, ClaimLearningResult


_SAFE = re.compile(r"[^a-z0-9_-]+")


def _safe_name(value: str) -> str:
    return _SAFE.sub("_", value.lower()).strip("_")


def _save_chunk(directory: Path, label: str, result: ClaimLearningResult) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_name(label)}.ecchunk.zip"
    CognitiveChunkArchive.save(path, result.chunk, result.store)
    return str(path)


def run_demo(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    chunk_dir = output_dir / "milestone_3_chunks"
    kernel = VerdantKernel(seed=2603, state_dim=64, run_label="milestone-3-claims")
    language = VerdantLanguagePipeline()
    claims = ClaimLearningPipeline()
    archives: list[str] = []

    language.teach_rule(kernel, GrammarRuleId.COPULAR_PROPERTY)
    language.teach_foundational_lexicon(kernel)

    language.learn_sentence(
        kernel,
        "The door is open.",
        event_key="teacher-says-open",
    )
    observed = claims.record_claim(
        kernel,
        event_key="controlled-visual-closed",
        native_description="Controlled visual observation: the door is visibly closed.",
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
        rationale="Controlled visual evidence conflicts with teacher testimony.",
    )
    archives.append(_save_chunk(chunk_dir, "controlled-visual-closed", observed))

    outcome = claims.record_claim(
        kernel,
        event_key="controlled-outcome-blocked",
        native_description=(
            "Controlled physical outcome: forward movement was blocked at the door."
        ),
        subject_label="lexeme:door",
        predicate="has_property",
        object_label="lexeme:open",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.PHYSICAL_OUTCOME,
        rationale="Physical consequence independently supports the closed-door claim.",
    )
    archives.append(_save_chunk(chunk_dir, "controlled-outcome-blocked", outcome))

    language.learn_sentence(
        kernel,
        "The door is open.",
        event_key="teacher-repeats-open",
    )

    bright = claims.record_claim(
        kernel,
        event_key="indicator-bright-positive",
        native_description="Controlled observation: the indicator appears bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.AFFIRMED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    archives.append(_save_chunk(chunk_dir, "indicator-bright-positive", bright))
    not_bright = claims.record_claim(
        kernel,
        event_key="indicator-bright-negative",
        native_description="Controlled observation: the indicator appears not bright.",
        subject_label="indicator",
        predicate="has_property",
        object_label="bright",
        polarity=ClaimPolarity.NEGATED,
        source_class=ClaimSourceClass.DIRECT_OBSERVATION,
    )
    archives.append(_save_chunk(chunk_dir, "indicator-bright-negative", not_bright))

    labels = {key: value.label for key, value in kernel.state.concepts.items()}
    claim_rows = []
    for claim in sorted(
        kernel.state.claims.values(),
        key=lambda item: (item.claim_key, item.polarity.value),
    ):
        claim_rows.append(
            {
                "claim_id": claim.claim_id,
                "subject": labels[claim.subject_concept_id],
                "predicate": claim.predicate,
                "object": labels[claim.object_concept_id],
                "polarity": claim.polarity.value,
                "status": claim.status.value,
                "support_score": claim.support_score,
                "refutation_score": claim.refutation_score,
                "net_score": claim.net_score,
                "support_sources": [
                    entry.source_class.value for entry in claim.support_ledger
                ],
                "support_evidence_count": len(claim.support_ledger),
                "refutation_evidence_count": len(claim.refutation_ledger),
                "superseded_by_claim_id": claim.superseded_by_claim_id,
            }
        )

    contradiction_rows = [
        item.model_dump(mode="json")
        for item in sorted(
            kernel.state.contradictions.values(),
            key=lambda item: item.contradiction_id,
        )
    ]
    revision_rows = [item.model_dump(mode="json") for item in kernel.state.revisions]
    door_belief = kernel.current_belief(
        "lexeme:door", "has_property", "lexeme:open"
    )
    indicator_belief = kernel.current_belief(
        "indicator", "has_property", "bright"
    )

    checkpoint_path = output_dir / "milestone_3_claims_demo.vdk"
    checkpoint_sha256 = save_checkpoint(checkpoint_path, kernel.snapshot())
    summary = {
        "milestone": 3,
        "description": (
            "Typed claims, weighted epistemic source classes, localized "
            "contradictions, and history-preserving revision."
        ),
        "kernel_id": kernel.state.identity.kernel_id,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "metrics": kernel.metrics(),
        "epistemic_policy": kernel.state.epistemic_policy.model_dump(mode="json"),
        "current_door_belief": (
            door_belief.model_dump(mode="json") if door_belief else None
        ),
        "current_indicator_belief": (
            indicator_belief.model_dump(mode="json") if indicator_belief else None
        ),
        "claims": claim_rows,
        "contradictions": contradiction_rows,
        "revisions": revision_rows,
        "controlled_claim_chunk_archives": archives,
        "important_boundary": (
            "Direct-observation and physical-outcome source classes are controlled "
            "test declarations in Milestone 3; live device streams are not connected."
        ),
        "claims_not_made": [
            "live sensory grounding",
            "truth from source class alone",
            "unrestricted logical reasoning",
            "consciousness",
        ],
    }
    summary_path = output_dir / "milestone_3_claims_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


if __name__ == "__main__":
    artifact_dir = Path(__file__).resolve().parents[1] / "artifacts"
    print(json.dumps(run_demo(artifact_dir), indent=2, sort_keys=True))
