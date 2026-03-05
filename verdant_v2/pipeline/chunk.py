"""CognitiveChunk — the data packet that flows through the pipeline.

Each chunk carries named *sections* written by individual blocks and a
chronological *processing_log* recording every operation applied to it.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProcessingStep(BaseModel):
    """A single processing-log entry."""

    processor: str
    operation: str
    timestamp: float = Field(default_factory=time.time)
    details: Dict[str, Any] = Field(default_factory=dict)


class CognitiveChunk(BaseModel):
    """Immutable-ish data packet flowing through the nine-block pipeline.

    Attributes:
        chunk_id: Unique identifier.
        creation_time: Unix timestamp of creation.
        sections: Named sections written by pipeline blocks.
        processing_log: Chronological log of operations.
    """

    chunk_id: str = Field(
        default_factory=lambda: f"chunk_{time.time_ns()}_{uuid.uuid4().hex[:8]}"
    )
    creation_time: float = Field(default_factory=time.time)
    sections: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    processing_log: List[ProcessingStep] = Field(default_factory=list)

    # ------------------------------------------------------------------
    # Section helpers
    # ------------------------------------------------------------------

    def add_section(self, section_name: str, content: Dict[str, Any]) -> None:
        """Add a new section; raises ``ValueError`` if it already exists."""
        if section_name in self.sections:
            raise ValueError(f"Section '{section_name}' already exists")
        self.sections[section_name] = content

    def update_section(self, section_name: str, content: Dict[str, Any]) -> None:
        """Create or overwrite *section_name*."""
        self.sections[section_name] = content

    def get_section_content(self, section_name: str) -> Optional[Dict[str, Any]]:
        """Return section content or ``None``."""
        return self.sections.get(section_name)

    def get_all_sections(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of all sections."""
        return dict(self.sections)

    # ------------------------------------------------------------------
    # Processing log
    # ------------------------------------------------------------------

    def add_processing_step(
        self,
        processor_name: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a step to the processing log."""
        self.processing_log.append(
            ProcessingStep(
                processor=processor_name,
                operation=operation,
                details=details or {},
            )
        )

    def get_processing_history(
        self, processor_name: Optional[str] = None
    ) -> List[ProcessingStep]:
        """Return log entries, optionally filtered by *processor_name*."""
        if processor_name is None:
            return list(self.processing_log)
        return [s for s in self.processing_log if s.processor == processor_name]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_compact_dict(self) -> Dict[str, Any]:
        """Return an LLM-friendly summary omitting bulky internal state.

        Keeps section keys, key scalar metrics, and a condensed
        processing log (processor names + operations only).
        """
        compact_sections: Dict[str, Any] = {}
        for name, content in self.sections.items():
            summary: Dict[str, Any] = {}
            for k, v in content.items():
                if isinstance(v, (int, float, str, bool, type(None))):
                    summary[k] = v
                elif isinstance(v, list) and len(v) <= 5:
                    summary[k] = v
                elif isinstance(v, dict) and len(v) <= 5:
                    summary[k] = v
                else:
                    summary[k] = f"<{type(v).__name__} len={len(v) if hasattr(v, '__len__') else '?'}>"
            compact_sections[name] = summary

        return {
            "chunk_id": self.chunk_id,
            "creation_time": self.creation_time,
            "sections": compact_sections,
            "processing_log": [
                {"processor": s.processor, "operation": s.operation}
                for s in self.processing_log
            ],
        }
