"""IdentityAmbiguity anchors derived from native proto-object competition."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import (
    IdentityAmbiguityObligationKernel,
    ObjectCandidateStatus,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id

from .pipeline import ObligationMutationResult, record_detected_identity_ambiguity


IDENTITY_AMBIGUITY_DETECTOR_POLICY_VERSION = "identity_ambiguity_detector_v0.12"


class IdentityAmbiguityDetectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = IDENTITY_AMBIGUITY_DETECTOR_POLICY_VERSION
    minimum_competing_candidates: int = Field(default=2, ge=2)

    @model_validator(mode="after")
    def validate_policy(self) -> "IdentityAmbiguityDetectionPolicy":
        if not self.policy_version.strip():
            raise ValueError("Identity-ambiguity policy version cannot be empty.")
        return self


class IdentityAmbiguityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    ambiguous_candidate_ref: str
    competing_candidate_refs: tuple[str, ...] = Field(min_length=2)
    scope_key: str
    canonical_triggering_refs: tuple[str, ...] = Field(min_length=4)
    source_lineage_roots: tuple[str, ...] = ()
    context_snapshot_hash: str
    source_event_key: str
    policy_version: str

    @model_validator(mode="after")
    def validate_candidate(self) -> "IdentityAmbiguityCandidate":
        for values, label in (
            (self.competing_candidate_refs, "competing refs"),
            (self.canonical_triggering_refs, "triggering refs"),
            (self.source_lineage_roots, "lineage roots"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Identity candidate {label} must be sorted and unique.")
        if self.ambiguous_candidate_ref in self.competing_candidate_refs:
            raise ValueError("Identity candidate cannot compete with itself.")
        if not {
            self.ambiguous_candidate_ref,
            *self.competing_candidate_refs,
        }.issubset(self.canonical_triggering_refs):
            raise ValueError("Identity candidate must preserve all candidate refs.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("identity_ambiguity_candidate", payload):
            raise ValueError("Identity candidate checksum mismatch.")
        return self


@dataclass(frozen=True)
class IdentityAmbiguityDetectionReport:
    policy_version: str
    inspected_candidate_ids: tuple[str, ...]
    candidates: tuple[IdentityAmbiguityCandidate, ...]
    mutations: tuple[ObligationMutationResult, ...]

    @property
    def created_or_retriggered_count(self) -> int:
        return sum(not item.replayed for item in self.mutations)


class IdentityAmbiguityDetector:
    """Find unresolved native candidate competition without naming entities."""

    def __init__(self, policy: IdentityAmbiguityDetectionPolicy | None = None) -> None:
        self.policy = policy or IdentityAmbiguityDetectionPolicy()

    def inspect(
        self, kernel: VerdantKernel
    ) -> tuple[tuple[str, ...], tuple[IdentityAmbiguityCandidate, ...]]:
        fingerprint = kernel.fingerprint()
        inspected: list[str] = []
        candidates: list[IdentityAmbiguityCandidate] = []
        for ambiguous in sorted(
            kernel.state.object_candidates.values(), key=lambda item: item.candidate_id
        ):
            inspected.append(ambiguous.candidate_id)
            competitor_refs = tuple(sorted(ambiguous.competing_candidate_ids))
            if (
                ambiguous.status != ObjectCandidateStatus.CONTESTED
                or ambiguous.ambiguity_count < 1
                or len(competitor_refs) < self.policy.minimum_competing_candidates
                or any(ref not in kernel.state.object_candidates for ref in competitor_refs)
            ):
                continue
            records = (
                ambiguous,
                *(kernel.state.object_candidates[ref] for ref in competitor_refs),
            )
            observation_refs = tuple(
                sorted({ref for item in records for ref in item.observation_ids})
            )
            evidence_refs = tuple(
                sorted({ref for item in records for ref in item.evidence_refs})
            )
            if (
                any(ref not in kernel.state.object_observations for ref in observation_refs)
                or any(ref not in kernel.state.evidence for ref in evidence_refs)
            ):
                continue
            evidence = tuple(kernel.state.evidence[ref] for ref in evidence_refs)
            triggering_refs = tuple(
                sorted({
                    ambiguous.candidate_id,
                    *competitor_refs,
                    *observation_refs,
                    *evidence_refs,
                })
            )
            roots = tuple(sorted(set(item.source_ref for item in evidence)))
            context_payload = {
                "ambiguous_candidate": ambiguous.model_dump(mode="json"),
                "competitors": tuple(
                    item.model_dump(mode="json")
                    for item in sorted(records[1:], key=lambda item: item.candidate_id)
                ),
                "observations": tuple(
                    kernel.state.object_observations[ref].model_dump(mode="json")
                    for ref in observation_refs
                ),
                "evidence": tuple(
                    item.model_dump(mode="json")
                    for item in sorted(evidence, key=lambda item: item.evidence_id)
                ),
                "policy": self.policy.model_dump(mode="json"),
            }
            context_hash = hashlib.sha256(
                canonical_json_bytes(context_payload)
            ).hexdigest()
            scope_key = stable_id(
                "identity_ambiguity_scope", ambiguous.candidate_id
            )
            source_event_key = stable_id(
                "identity_ambiguity_detection",
                ambiguous.candidate_id,
                context_hash,
                self.policy.policy_version,
            )
            values = {
                "ambiguous_candidate_ref": ambiguous.candidate_id,
                "competing_candidate_refs": competitor_refs,
                "scope_key": scope_key,
                "canonical_triggering_refs": triggering_refs,
                "source_lineage_roots": roots,
                "context_snapshot_hash": context_hash,
                "source_event_key": source_event_key,
                "policy_version": self.policy.policy_version,
            }
            candidates.append(
                IdentityAmbiguityCandidate(
                    candidate_id=stable_id("identity_ambiguity_candidate", values),
                    **values,
                )
            )
        if kernel.fingerprint() != fingerprint:
            raise RuntimeError("Identity-ambiguity inspection mutated canonical state.")
        return tuple(inspected), tuple(candidates)

    def detect_and_record(self, kernel: VerdantKernel) -> IdentityAmbiguityDetectionReport:
        inspected, candidates = self.inspect(kernel)
        mutations: list[ObligationMutationResult] = []
        for candidate in candidates:
            obligation_id = stable_id(
                "obligation",
                "0.12",
                "IdentityAmbiguity",
                candidate.ambiguous_candidate_ref,
                candidate.scope_key,
            )
            existing = kernel.state.obligation_kernels.get(obligation_id)
            if existing is None:
                obligation = IdentityAmbiguityObligationKernel(
                    kernel_id=obligation_id,
                    ambiguous_candidate_ref=candidate.ambiguous_candidate_ref,
                    competing_candidate_refs=candidate.competing_candidate_refs,
                    scope_key=candidate.scope_key,
                    canonical_triggering_refs=candidate.canonical_triggering_refs,
                    creation_cycle=kernel.state.cycle + 1,
                    policy_version=self.policy.policy_version,
                )
            elif isinstance(existing, IdentityAmbiguityObligationKernel):
                obligation = existing
            else:
                raise RuntimeError("Identity obligation crossed a family boundary.")
            mutations.append(
                record_detected_identity_ambiguity(
                    kernel,
                    obligation=obligation,
                    triggering_refs=candidate.canonical_triggering_refs,
                    source_event_key=candidate.source_event_key,
                    context_snapshot_hash=candidate.context_snapshot_hash,
                    source_lineage_roots=candidate.source_lineage_roots,
                    policy_version=self.policy.policy_version,
                )
            )
        return IdentityAmbiguityDetectionReport(
            policy_version=self.policy.policy_version,
            inspected_candidate_ids=inspected,
            candidates=candidates,
            mutations=tuple(mutations),
        )
