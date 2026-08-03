from __future__ import annotations

from dataclasses import dataclass

from cognitive_chunk_v2 import CognitiveChunkV2, ExperienceInput, PipelineOrchestrator, ResourceStore
from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    ExperienceResult,
    VerdantKernel,
)


_SOURCE_EVIDENCE_KIND = {
    ClaimSourceClass.DIRECT_OBSERVATION: EvidenceKind.OBSERVATION,
    ClaimSourceClass.PHYSICAL_OUTCOME: EvidenceKind.OUTCOME,
    ClaimSourceClass.SELF_ACTION: EvidenceKind.ACTION,
    ClaimSourceClass.HUMAN_TESTIMONY: EvidenceKind.TESTIMONY,
    ClaimSourceClass.EXTERNAL_TESTIMONY: EvidenceKind.TESTIMONY,
    ClaimSourceClass.SYSTEM_INFERENCE: EvidenceKind.SYSTEM,
    ClaimSourceClass.TRANSLATION: EvidenceKind.TRANSLATION,
}


@dataclass(frozen=True)
class ClaimLearningResult:
    kernel_result: ExperienceResult
    chunk: CognitiveChunkV2
    store: ResourceStore


class ClaimLearningPipeline:
    """
    Controlled bridge for Milestone 3 claim-source experiments.

    It preserves a native textual description through CognitiveChunk v2, then
    presents one explicit typed claim to the canonical kernel. Direct observation
    and physical outcome source classes in this milestone are controlled test
    declarations rather than live device streams.
    """

    def __init__(self, orchestrator: PipelineOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()

    def record_claim(
        self,
        kernel: VerdantKernel,
        *,
        event_key: str,
        native_description: str,
        subject_label: str,
        predicate: str,
        object_label: str,
        polarity: ClaimPolarity,
        source_class: ClaimSourceClass,
        confidence: float = 1.0,
        source_ref: str | None = None,
        rationale: str = "",
    ) -> ClaimLearningResult:
        source = source_ref or f"controlled_{source_class.value}"
        chunk, store = self.orchestrator.process(
            ExperienceInput.from_text(
                native_description,
                source_id=source,
                source_name=f"{event_key}.txt",
            )
        )
        payload = chunk.payloads[0]
        translation = chunk.translations[0]
        observation = next(
            item for item in chunk.observations if item.payload_id == payload.payload_id
        )
        command = ExperienceCommand(
            event_key=event_key,
            source_ref=observation.source_id,
            modality="text",
            payload_sha256=payload.source_sha256,
            feature_vector=tuple(
                float(value)
                for value in store.get_array(translation.feature_ref).reshape(-1)
            ),
            claim_proposals=(
                ClaimProposal(
                    subject_label=subject_label,
                    predicate=predicate,
                    object_label=object_label,
                    polarity=polarity,
                    source_class=source_class,
                    confidence=confidence,
                    rationale=rationale,
                    attributes={"controlled_milestone_3_source": True},
                ),
            ),
            confidence=confidence,
            semantic_evidence_kind=_SOURCE_EVIDENCE_KIND[source_class],
            semantic_evidence_details={
                "source_class": source_class.value,
                "controlled_test_source": True,
                "live_sensor_connected": False,
            },
            metadata={
                "event_type": "controlled_claim_evidence",
                "source_class": source_class.value,
                "polarity": polarity.value,
                "translator_id": translation.translator_id,
                "translator_version": translation.translator_version,
                "semantic_promotion_policy": "explicit_typed_claim_with_source_class",
            },
        )
        return ClaimLearningResult(kernel.apply_experience(command), chunk, store)
