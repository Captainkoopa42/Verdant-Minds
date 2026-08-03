from __future__ import annotations

from dataclasses import dataclass

from cognitive_chunk_v2.archive import ResourceStore
from cognitive_chunk_v2.models import CognitiveChunkV2
from cognitive_chunk_v2.pipeline import ExperienceInput, PipelineOrchestrator
from verdant_kernel import ResonanceEvent, ResonanceReport, VerdantKernel


@dataclass(frozen=True)
class ResonanceQueryResult:
    report: ResonanceReport
    chunk: CognitiveChunkV2
    store: ResourceStore
    observation_evidence_refs: tuple[str, ...] = ()


class VerdantECWFPipeline:
    """Native text cue -> pure ECWF resonance report -> optional attention admission."""

    def __init__(self, orchestrator: PipelineOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or PipelineOrchestrator()

    def inspect_text(
        self,
        kernel: VerdantKernel,
        text: str,
        *,
        top_k: int | None = None,
        source_id: str = "controlled_resonance_query",
        source_name: str = "resonance_query.txt",
    ) -> ResonanceQueryResult:
        chunk, store = self.orchestrator.process(
            ExperienceInput.from_text(
                text,
                source_id=source_id,
                source_name=source_name,
            )
        )
        translation = chunk.translations[0]
        features = tuple(
            float(value)
            for value in store.get_array(translation.feature_ref).reshape(-1)
        )
        report = kernel.inspect_resonance(features, "text", top_k=top_k)
        return ResonanceQueryResult(report=report, chunk=chunk, store=store)

    @staticmethod
    def commit(
        kernel: VerdantKernel,
        query: ResonanceQueryResult,
        *,
        evidence_refs: tuple[str, ...],
        max_candidates: int | None = None,
        resource_request: float | None = None,
    ) -> ResonanceEvent:
        return kernel.commit_resonance(
            query.report,
            evidence_refs=evidence_refs,
            max_candidates=max_candidates,
            resource_request=resource_request,
        )
