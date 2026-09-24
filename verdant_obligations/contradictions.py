"""Endogenous obligation anchors for Verdant's canonical claim contradictions.

This detector consumes only contradiction records already produced by the
claim subsystem.  It does not parse semantic labels, choose a winning claim,
or resolve the contradiction.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import ContradictionObligationKernel, VerdantKernel
from verdant_kernel.models import canonical_json_bytes, stable_id

from .pipeline import ObligationMutationResult, record_detected_contradiction


CONTRADICTION_DETECTOR_POLICY_VERSION = "contradiction_obligation_detector_v0.10"


class ContradictionObligationCandidate(BaseModel):
    """Pure, answer-agnostic projection of one canonical contradiction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    contradiction_ref: str
    claim_key: str
    claim_refs: tuple[str, str]
    scope_key: str
    canonical_triggering_refs: tuple[str, ...] = Field(min_length=3)
    source_lineage_roots: tuple[str, ...] = ()
    context_snapshot_hash: str
    source_event_key: str
    policy_version: str = CONTRADICTION_DETECTOR_POLICY_VERSION

    @model_validator(mode="after")
    def validate_candidate(self) -> "ContradictionObligationCandidate":
        for values, label in (
            (self.claim_refs, "claim refs"),
            (self.canonical_triggering_refs, "triggering refs"),
            (self.source_lineage_roots, "lineage roots"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Contradiction candidate {label} must be sorted and unique.")
        if not set(self.claim_refs).issubset(self.canonical_triggering_refs):
            raise ValueError("Contradiction candidate must preserve both opposed claims.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("contradiction_obligation_candidate", payload):
            raise ValueError("Contradiction candidate identity checksum mismatch.")
        return self


@dataclass(frozen=True)
class ContradictionDetectionReport:
    policy_version: str
    inspected_contradiction_ids: tuple[str, ...]
    candidates: tuple[ContradictionObligationCandidate, ...]
    mutations: tuple[ObligationMutationResult, ...]

    @property
    def created_or_retriggered_count(self) -> int:
        return sum(not item.replayed for item in self.mutations)


class ContradictionObligationDetector:
    """Persist native contradictions as bounded cognitive obligations."""

    policy_version = CONTRADICTION_DETECTOR_POLICY_VERSION

    def inspect(
        self, kernel: VerdantKernel
    ) -> tuple[tuple[str, ...], tuple[ContradictionObligationCandidate, ...]]:
        fingerprint = kernel.fingerprint()
        inspected: list[str] = []
        candidates: list[ContradictionObligationCandidate] = []
        for contradiction in sorted(
            kernel.state.contradictions.values(), key=lambda item: item.contradiction_id
        ):
            inspected.append(contradiction.contradiction_id)
            claims = tuple(
                kernel.state.claims.get(claim_id) for claim_id in contradiction.claim_ids
            )
            if any(claim is None for claim in claims):
                continue
            if any(claim.claim_key != contradiction.claim_key for claim in claims if claim):
                continue
            evidence_refs = tuple(sorted(set(contradiction.evidence_refs)))
            if any(ref not in kernel.state.evidence for ref in evidence_refs):
                continue
            evidence = tuple(kernel.state.evidence[ref] for ref in evidence_refs)
            claim_refs = tuple(sorted(contradiction.claim_ids))
            triggering_refs = tuple(
                sorted({contradiction.contradiction_id, *claim_refs, *evidence_refs})
            )
            roots = tuple(sorted(set(item.source_ref for item in evidence)))
            context_payload = {
                "contradiction": contradiction.model_dump(mode="json"),
                "claims": tuple(
                    claim.model_dump(mode="json")
                    for claim in sorted(claims, key=lambda item: item.claim_id)  # type: ignore[union-attr]
                ),
                "evidence": tuple(
                    item.model_dump(mode="json")
                    for item in sorted(evidence, key=lambda item: item.evidence_id)
                ),
                "policy_version": self.policy_version,
            }
            context_hash = hashlib.sha256(
                canonical_json_bytes(context_payload)
            ).hexdigest()
            scope_key = stable_id(
                "contradiction_scope",
                contradiction.claim_key,
                contradiction.contradiction_id,
            )
            source_event_key = stable_id(
                "contradiction_detection",
                contradiction.contradiction_id,
                context_hash,
                self.policy_version,
            )
            values = {
                "contradiction_ref": contradiction.contradiction_id,
                "claim_key": contradiction.claim_key,
                "claim_refs": claim_refs,
                "scope_key": scope_key,
                "canonical_triggering_refs": triggering_refs,
                "source_lineage_roots": roots,
                "context_snapshot_hash": context_hash,
                "source_event_key": source_event_key,
                "policy_version": self.policy_version,
            }
            candidates.append(
                ContradictionObligationCandidate(
                    candidate_id=stable_id("contradiction_obligation_candidate", values),
                    **values,
                )
            )
        if kernel.fingerprint() != fingerprint:
            raise RuntimeError("Contradiction inspection mutated canonical state.")
        return tuple(inspected), tuple(candidates)

    def detect_and_record(self, kernel: VerdantKernel) -> ContradictionDetectionReport:
        inspected, candidates = self.inspect(kernel)
        mutations: list[ObligationMutationResult] = []
        for candidate in candidates:
            obligation_id = stable_id(
                "obligation",
                "0.10",
                "Contradiction",
                candidate.contradiction_ref,
                candidate.claim_key,
                candidate.scope_key,
            )
            existing = kernel.state.obligation_kernels.get(obligation_id)
            if existing is None:
                obligation = ContradictionObligationKernel(
                    kernel_id=obligation_id,
                    contradiction_ref=candidate.contradiction_ref,
                    claim_key=candidate.claim_key,
                    claim_refs=candidate.claim_refs,
                    scope_key=candidate.scope_key,
                    canonical_triggering_refs=candidate.canonical_triggering_refs,
                    creation_cycle=kernel.state.cycle + 1,
                    policy_version=self.policy_version,
                )
            elif isinstance(existing, ContradictionObligationKernel):
                obligation = existing
            else:
                raise RuntimeError("Contradiction obligation identity crossed a family boundary.")
            mutations.append(
                record_detected_contradiction(
                    kernel,
                    obligation=obligation,
                    triggering_refs=candidate.canonical_triggering_refs,
                    source_event_key=candidate.source_event_key,
                    context_snapshot_hash=candidate.context_snapshot_hash,
                    source_lineage_roots=candidate.source_lineage_roots,
                    policy_version=self.policy_version,
                )
            )
        return ContradictionDetectionReport(
            policy_version=self.policy_version,
            inspected_contradiction_ids=inspected,
            candidates=candidates,
            mutations=tuple(mutations),
        )
