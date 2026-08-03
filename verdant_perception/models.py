from __future__ import annotations

import hashlib
import math
from typing import Any

from pydantic import Field, model_validator

from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id


class RegionProposal(FrozenRecord):
    region_id: str
    sample_id: str
    temporal_event_id: str
    frame_index: int = Field(ge=0)
    evidence_ref: str
    bbox_norm: tuple[float, float, float, float]
    centroid_norm: tuple[float, float]
    area_fraction: float = Field(gt=0.0, le=1.0)
    appearance_features: tuple[float, ...] = Field(min_length=1)
    motion: tuple[float, float]
    prior_region_id: str | None = None
    common_motion_supported: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_region(self) -> "RegionProposal":
        numeric = [
            *self.bbox_norm,
            *self.centroid_norm,
            self.area_fraction,
            *self.appearance_features,
            *self.motion,
        ]
        if any(not math.isfinite(item) for item in numeric):
            raise ValueError("Perceptual region values must be finite.")
        x0, y0, x1, y1 = self.bbox_norm
        if not (0.0 <= x0 < x1 <= 1.0 and 0.0 <= y0 < y1 <= 1.0):
            raise ValueError("Perceptual region bounding box is invalid.")
        if not all(0.0 <= item <= 1.0 for item in self.centroid_norm):
            raise ValueError("Perceptual region centroid must be normalized.")
        expected = stable_id(
            "perceptual_region",
            self.sample_id,
            self.temporal_event_id,
            self.frame_index,
            self.evidence_ref,
            self.bbox_norm,
            self.centroid_norm,
            self.area_fraction,
            self.appearance_features,
            self.motion,
            self.prior_region_id,
            self.common_motion_supported,
            self.metadata,
        )
        if expected != self.region_id:
            raise ValueError("Perceptual region identity checksum mismatch.")
        return self


class FramePerception(FrozenRecord):
    sample_id: str
    temporal_event_id: str
    frame_index: int = Field(ge=0)
    region_proposals: tuple[RegionProposal, ...] = Field(default_factory=tuple)
    unmatched_prior_region_ids: tuple[str, ...] = Field(default_factory=tuple)
    image_sha256: str

    @model_validator(mode="after")
    def validate_frame(self) -> "FramePerception":
        if tuple(sorted(set(self.unmatched_prior_region_ids))) != self.unmatched_prior_region_ids:
            raise ValueError("Unmatched prior region IDs must be sorted and unique.")
        region_ids = tuple(item.region_id for item in self.region_proposals)
        if len(region_ids) != len(set(region_ids)):
            raise ValueError("Perceptual frame duplicates a region.")
        if len(self.image_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in self.image_sha256):
            raise ValueError("Perceptual frame image digest must be lowercase SHA-256.")
        return self


class RegionCandidateBinding(FrozenRecord):
    region_id: str
    object_observation_event_id: str
    object_observation_id: str
    candidate_id: str
    disposition: str


class OcclusionBinding(FrozenRecord):
    temporal_event_id: str
    frame_index: int = Field(ge=0)
    candidate_id: str
    object_observation_event_id: str
    object_observation_id: str
    evidence_ref: str


class PerceptualBindingReport(FrozenRecord):
    report_id: str
    kernel_id: str
    initial_cycle: int = Field(ge=0)
    structural_fingerprint: str
    temporal_event_ids: tuple[str, ...] = Field(min_length=1)
    sample_ids: tuple[str, ...] = Field(min_length=1)
    frames: tuple[FramePerception, ...] = Field(min_length=1)
    region_bindings: tuple[RegionCandidateBinding, ...] = Field(default_factory=tuple)
    occlusion_bindings: tuple[OcclusionBinding, ...] = Field(default_factory=tuple)
    resulting_candidate_ids: tuple[str, ...] = Field(default_factory=tuple)
    policy_revision: int = Field(ge=0)
    operation: str
    output_state_fingerprint: str

    @model_validator(mode="after")
    def validate_report(self) -> "PerceptualBindingReport":
        for values, label in (
            (self.temporal_event_ids, "temporal event"),
            (self.sample_ids, "sample"),
            (self.resulting_candidate_ids, "candidate"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Perceptual report {label} IDs must be sorted and unique.")
        if len(self.output_state_fingerprint) != 64:
            raise ValueError("Perceptual report output fingerprint must be SHA-256.")
        expected = stable_id(
            "perceptual_binding_report",
            self.kernel_id,
            self.initial_cycle,
            self.structural_fingerprint,
            self.temporal_event_ids,
            self.sample_ids,
            tuple(item.model_dump(mode="json") for item in self.frames),
            tuple(item.model_dump(mode="json") for item in self.region_bindings),
            tuple(item.model_dump(mode="json") for item in self.occlusion_bindings),
            self.resulting_candidate_ids,
            self.policy_revision,
            self.operation,
            self.output_state_fingerprint,
        )
        if expected != self.report_id:
            raise ValueError("Perceptual binding report identity checksum mismatch.")
        return self

    def digest(self) -> str:
        return hashlib.sha256(canonical_json_bytes(self.model_dump(mode="json"))).hexdigest()
