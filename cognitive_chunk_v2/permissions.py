from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .models import (
    ClaimRecord,
    CognitiveChunkV2,
    CognitiveEffectRecord,
    ContradictionRecord,
    ObservationRecord,
    PayloadRecord,
    ProcessingEvent,
    RevisionRecord,
    TemporalSegmentRecord,
    TranslationRecord,
)


class WritePermissionError(PermissionError):
    pass


LEDGER_PERMISSIONS: dict[str, set[str]] = {
    "SensoryInput": {
        "payloads",
        "temporal_segments",
        "observations",
        "translations",
        "sections",
        "processing_log",
    },
    "PatternRecognition": {
        "claims",
        "sections",
        "processing_log",
    },
    "MemoryStorage": {
        "cognitive_effects",
        "sections",
        "processing_log",
    },
    "InternalCommunication": {
        "sections",
        "processing_log",
    },
    "ReasoningPlanning": {
        "claims",
        "revisions",
        "contradictions",
        "sections",
        "processing_log",
    },
    "EthicsValues": {
        "sections",
        "processing_log",
    },
    "ActionSelection": {
        "sections",
        "processing_log",
    },
    "LanguageProcessing": {
        "sections",
        "processing_log",
    },
    "ContinualLearning": {
        "revisions",
        "sections",
        "processing_log",
    },
    "MergeEngine": {
        "contradictions",
        "sections",
        "processing_log",
    },
}


@dataclass
class ChunkWriter:
    chunk: CognitiveChunkV2
    block: str

    def _require(self, ledger: str) -> None:
        allowed = LEDGER_PERMISSIONS.get(self.block, set())
        if ledger not in allowed:
            raise WritePermissionError(
                f"{self.block} is not allowed to write '{ledger}'."
            )

    def append(self, ledger: str, record: Any) -> None:
        self._require(ledger)
        target = getattr(self.chunk, ledger)
        if not isinstance(target, list):
            raise TypeError(f"Ledger '{ledger}' is not a list.")
        target.append(record)

    def set_section(self, name: str, value: Any) -> None:
        self._require("sections")
        history_key = f"{name}__history"
        if name in self.chunk.sections:
            self.chunk.sections.setdefault(history_key, []).append(
                self.chunk.sections[name]
            )
        self.chunk.sections[name] = value

    def log(
        self,
        operation: str,
        *,
        input_refs: list[str],
        output_refs: list[str],
        before_fingerprint: str,
        started_unix: float,
        success: bool = True,
        error: str | None = None,
    ) -> ProcessingEvent:
        self._require("processing_log")
        after_fingerprint = self.chunk.fingerprint()
        event = ProcessingEvent(
            block=self.block,
            operation=operation,
            input_refs=input_refs,
            output_refs=output_refs,
            before_fingerprint=before_fingerprint,
            after_fingerprint=after_fingerprint,
            started_unix=started_unix,
            completed_unix=__import__("time").time(),
            success=success,
            error=error,
        )
        self.chunk.processing_log.append(event)
        return event
