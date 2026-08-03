from __future__ import annotations

import hashlib
import json
import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def make_id(prefix: str) -> str:
    return f"{prefix}_{time.time_ns()}_{uuid.uuid4().hex}"


class Modality(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    STRUCTURED = "structured"


class PayloadRole(str, Enum):
    PRIMARY = "primary"
    DERIVED_SNIPPET = "derived_snippet"
    AUDIO_TRACK = "audio_track"
    VIDEO_TRACK = "video_track"
    FRAME = "frame"
    TRANSCRIPT = "transcript"


class TemporalTrack(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    AUDIOVISUAL = "audiovisual"


class ClaimStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    SUPPORTED = "supported"
    CONFIRMED = "confirmed"
    CONTRADICTED = "contradicted"
    REVISED = "revised"
    REJECTED = "rejected"


class FrozenRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChunkIdentity(FrozenRecord):
    chunk_id: str = Field(default_factory=lambda: make_id("chunk"))
    schema_version: str = "2.0.0-alpha"
    created_unix: float = Field(default_factory=time.time)


class LineageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent_chunk_ids: list[str] = Field(default_factory=list)
    merged_chunk_ids: list[str] = Field(default_factory=list)
    derived_from_chunk_ids: list[str] = Field(default_factory=list)


class PayloadRecord(FrozenRecord):
    payload_id: str = Field(default_factory=lambda: make_id("payload"))
    modality: Modality
    role: PayloadRole = PayloadRole.PRIMARY
    source_sha256: str
    media_type: str
    byte_length: int = Field(ge=0)
    storage_path: str
    source_name: str | None = None
    parent_payload_id: str | None = None
    segment_id: str | None = None


class TemporalSegmentRecord(FrozenRecord):
    """
    Future-video contract.

    A segment can point to the audiovisual stream, the audio track alone,
    or the video track alone. The current build serializes and validates
    this structure but does not yet decode video.
    """

    segment_id: str = Field(default_factory=lambda: make_id("segment"))
    parent_payload_id: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    track: TemporalTrack
    selected_by: str
    selection_reason: str
    constraint_tags: list[str] = Field(default_factory=list)

    @field_validator("end_ms")
    @classmethod
    def end_after_zero(cls, value: int) -> int:
        return value


class ObservationRecord(FrozenRecord):
    observation_id: str = Field(default_factory=lambda: make_id("obs"))
    payload_id: str
    source_id: str
    observed_unix: float = Field(default_factory=time.time)
    measurement_type: str
    data: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)


class TranslationRecord(FrozenRecord):
    translation_id: str = Field(default_factory=lambda: make_id("translation"))
    payload_id: str
    modality: Modality
    translator_id: str
    translator_version: str
    feature_ref: str
    feature_dim: int = Field(gt=0)
    uncertainty: float = Field(ge=0.0, le=1.0)
    assumptions: list[str] = Field(default_factory=list)


class ClaimRecord(FrozenRecord):
    claim_id: str = Field(default_factory=lambda: make_id("claim"))
    scope: str
    value: Any
    status: ClaimStatus = ClaimStatus.HYPOTHESIS
    evidence_refs: list[str] = Field(default_factory=list)
    created_by: str
    confidence: float = Field(ge=0.0, le=1.0)


class ContradictionRecord(FrozenRecord):
    contradiction_id: str = Field(default_factory=lambda: make_id("contradiction"))
    scope: str
    claim_ids: list[str] = Field(min_length=2)
    status: str = "unresolved"
    discriminating_tests: list[str] = Field(default_factory=list)


class CognitiveEffectRecord(FrozenRecord):
    effect_id: str = Field(default_factory=lambda: make_id("effect"))
    caused_by_refs: list[str]
    subsystem: str
    state_before_ref: str
    state_after_ref: str
    state_delta_ref: str
    effect_norm: float = Field(ge=0.0)


class RevisionRecord(FrozenRecord):
    revision_id: str = Field(default_factory=lambda: make_id("revision"))
    revises_claim_id: str
    replacement_claim_id: str
    reason: str
    evidence_refs: list[str] = Field(default_factory=list)
    created_by: str


class ProcessingEvent(FrozenRecord):
    event_id: str = Field(default_factory=lambda: make_id("event"))
    block: str
    operation: str
    input_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    before_fingerprint: str
    after_fingerprint: str
    started_unix: float
    completed_unix: float
    success: bool = True
    error: str | None = None


class CognitiveChunkV2(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    identity: ChunkIdentity = Field(default_factory=ChunkIdentity)
    lineage: LineageRecord = Field(default_factory=LineageRecord)

    payloads: list[PayloadRecord] = Field(default_factory=list)
    temporal_segments: list[TemporalSegmentRecord] = Field(default_factory=list)
    observations: list[ObservationRecord] = Field(default_factory=list)
    translations: list[TranslationRecord] = Field(default_factory=list)
    claims: list[ClaimRecord] = Field(default_factory=list)
    contradictions: list[ContradictionRecord] = Field(default_factory=list)
    cognitive_effects: list[CognitiveEffectRecord] = Field(default_factory=list)
    revisions: list[RevisionRecord] = Field(default_factory=list)
    processing_log: list[ProcessingEvent] = Field(default_factory=list)

    # Compatibility surface for the existing nine-block architecture.
    sections: dict[str, Any] = Field(default_factory=dict)

    def fingerprint(self, *, include_processing_log: bool = False) -> str:
        payload = self.model_dump(mode="json")
        if not include_processing_log:
            payload["processing_log"] = []
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def active_claims_for_scope(self, scope: str) -> list[ClaimRecord]:
        inactive = {
            ClaimStatus.REJECTED,
            ClaimStatus.REVISED,
        }
        return [
            claim for claim in self.claims
            if claim.scope == scope and claim.status not in inactive
        ]

    def merge_from(self, other: "CognitiveChunkV2") -> None:
        self.lineage.merged_chunk_ids.append(other.identity.chunk_id)

        def extend_unique(target: list[Any], incoming: list[Any], key: str) -> None:
            existing = {getattr(item, key) for item in target}
            for item in incoming:
                identifier = getattr(item, key)
                if identifier not in existing:
                    target.append(item)
                    existing.add(identifier)

        extend_unique(self.payloads, other.payloads, "payload_id")
        extend_unique(self.temporal_segments, other.temporal_segments, "segment_id")
        extend_unique(self.observations, other.observations, "observation_id")
        extend_unique(self.translations, other.translations, "translation_id")
        extend_unique(self.claims, other.claims, "claim_id")
        extend_unique(self.cognitive_effects, other.cognitive_effects, "effect_id")
        extend_unique(self.revisions, other.revisions, "revision_id")

        for key, value in other.sections.items():
            if key not in self.sections:
                self.sections[key] = value
            elif self.sections[key] != value:
                conflict_key = f"{key}__merge_conflicts"
                self.sections.setdefault(conflict_key, []).append(value)

        known = {
            tuple(sorted(record.claim_ids))
            for record in self.contradictions
        }
        scopes = {claim.scope for claim in self.claims}
        for scope in scopes:
            claims = self.active_claims_for_scope(scope)
            for index, left in enumerate(claims):
                for right in claims[index + 1:]:
                    if left.value == right.value:
                        continue
                    pair = tuple(sorted([left.claim_id, right.claim_id]))
                    if pair in known:
                        continue
                    self.contradictions.append(
                        ContradictionRecord(
                            scope=scope,
                            claim_ids=list(pair),
                            discriminating_tests=[
                                f"Collect independent evidence for scope '{scope}'."
                            ],
                        )
                    )
                    known.add(pair)
