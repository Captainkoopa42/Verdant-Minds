"""Deterministic, answer-agnostic DependencyGap detection.

The detector operates only on already-canonical graph records.  It does not
parse labels, infer that an arbitrary relation is a dependency, or decide that
an answer is true.  Its small typed policy declares which directed relation
types are dependency edges and which evidence kinds count as an available
input.  That policy remains external evaluator machinery in v0.2 and is
therefore deliberately versioned and provenance-visible.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, RelationStatus, VerdantKernel
from verdant_kernel.models import canonical_json_bytes, stable_id

from .pipeline import DependencyGapPipeline, ObligationMutationResult


TOPOLOGICAL_DETECTOR_POLICY_VERSION = "dependency_gap_topology_detector_v0.2"


class DependencyGapDetectionPolicy(BaseModel):
    """Visible structural grammar for one bounded detector revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = TOPOLOGICAL_DETECTOR_POLICY_VERSION
    dependency_relation_types: tuple[str, ...] = ("requires",)
    eligible_relation_statuses: tuple[RelationStatus, ...] = (
        RelationStatus.CONFIRMED,
        RelationStatus.SUPPORTED,
    )
    qualifying_input_evidence_kinds: tuple[EvidenceKind, ...] = (
        EvidenceKind.ACTION,
        EvidenceKind.OUTCOME,
    )
    minimum_relation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    require_directed_edge: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> "DependencyGapDetectionPolicy":
        relation_types = tuple(
            sorted(set(item.strip() for item in self.dependency_relation_types))
        )
        if not relation_types or not all(relation_types):
            raise ValueError("Dependency detector requires non-empty relation types.")
        if relation_types != self.dependency_relation_types:
            raise ValueError("Dependency relation types must be sorted and unique.")
        statuses = tuple(sorted(set(self.eligible_relation_statuses), key=lambda x: x.value))
        if not statuses or statuses != self.eligible_relation_statuses:
            raise ValueError("Eligible relation statuses must be sorted and unique.")
        evidence_kinds = tuple(
            sorted(set(self.qualifying_input_evidence_kinds), key=lambda x: x.value)
        )
        if not evidence_kinds or evidence_kinds != self.qualifying_input_evidence_kinds:
            raise ValueError("Qualifying evidence kinds must be sorted and unique.")
        if not self.policy_version.strip():
            raise ValueError("Dependency detector policy version cannot be empty.")
        return self


class DependencyGapCandidate(BaseModel):
    """Pure structural finding produced before any canonical obligation write."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_id: str
    relation_id: str
    target_action_node: str
    missing_input_signature: str
    trigger_relation: str
    scope_key: str
    canonical_triggering_refs: tuple[str, ...] = Field(min_length=1)
    source_lineage_roots: tuple[str, ...] = ()
    context_snapshot_hash: str
    source_event_key: str
    policy_version: str

    @model_validator(mode="after")
    def validate_candidate(self) -> "DependencyGapCandidate":
        for values, label in (
            (self.canonical_triggering_refs, "triggering refs"),
            (self.source_lineage_roots, "lineage roots"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Dependency candidate {label} must be sorted and unique.")
        payload = {
            "relation_id": self.relation_id,
            "target_action_node": self.target_action_node,
            "missing_input_signature": self.missing_input_signature,
            "trigger_relation": self.trigger_relation,
            "scope_key": self.scope_key,
            "canonical_triggering_refs": self.canonical_triggering_refs,
            "source_lineage_roots": self.source_lineage_roots,
            "context_snapshot_hash": self.context_snapshot_hash,
            "source_event_key": self.source_event_key,
            "policy_version": self.policy_version,
        }
        if self.candidate_id != stable_id("dependency_gap_candidate", payload):
            raise ValueError("Dependency candidate identity checksum mismatch.")
        return self


@dataclass(frozen=True)
class DependencyGapDetectionReport:
    """Non-canonical receipt for one bounded detector heartbeat."""

    policy_version: str
    inspected_relation_ids: tuple[str, ...]
    candidates: tuple[DependencyGapCandidate, ...]
    mutations: tuple[ObligationMutationResult, ...]

    @property
    def created_or_retriggered_count(self) -> int:
        return sum(not item.replayed for item in self.mutations)

    @property
    def replayed_count(self) -> int:
        return sum(item.replayed for item in self.mutations)


class DependencyGapDetector:
    """Find missing inputs from explicit canonical dependency topology."""

    def __init__(
        self,
        *,
        policy: DependencyGapDetectionPolicy | None = None,
        obligations: DependencyGapPipeline | None = None,
    ) -> None:
        self.policy = policy or DependencyGapDetectionPolicy()
        self.obligations = obligations or DependencyGapPipeline()

    def inspect(
        self,
        kernel: VerdantKernel,
    ) -> tuple[tuple[str, ...], tuple[DependencyGapCandidate, ...]]:
        """Return findings without changing cycle, history, or fingerprints."""

        inspected: list[str] = []
        candidates: list[DependencyGapCandidate] = []
        eligible_statuses = set(self.policy.eligible_relation_statuses)
        accepted_kinds = set(self.policy.qualifying_input_evidence_kinds)

        for relation in sorted(
            kernel.state.relations.values(), key=lambda item: item.relation_id
        ):
            if relation.relation_type not in self.policy.dependency_relation_types:
                continue
            inspected.append(relation.relation_id)
            if self.policy.require_directed_edge and not relation.directed:
                continue
            if relation.status not in eligible_statuses:
                continue
            if relation.confidence < self.policy.minimum_relation_confidence:
                continue

            source = kernel.state.concepts[relation.source_concept_id]
            target = kernel.state.concepts[relation.target_concept_id]
            target_evidence = tuple(
                kernel.state.evidence[ref] for ref in target.evidence_refs
            )
            if any(item.kind in accepted_kinds for item in target_evidence):
                continue

            local_evidence_refs = tuple(
                sorted(set(relation.evidence_refs) | set(target.evidence_refs))
            )
            local_evidence = tuple(
                kernel.state.evidence[ref] for ref in local_evidence_refs
            )
            triggering_refs = tuple(
                sorted(
                    {
                        relation.relation_id,
                        source.concept_id,
                        target.concept_id,
                        *local_evidence_refs,
                    }
                )
            )
            lineage_roots = tuple(
                sorted(set(item.source_ref for item in local_evidence))
            )
            context_payload = {
                "relation": relation.model_dump(mode="json"),
                "source": source.model_dump(mode="json"),
                "target": target.model_dump(mode="json"),
                "evidence": tuple(
                    item.model_dump(mode="json")
                    for item in sorted(local_evidence, key=lambda value: value.evidence_id)
                ),
                "policy": self.policy.model_dump(mode="json"),
            }
            context_hash = hashlib.sha256(
                canonical_json_bytes(context_payload)
            ).hexdigest()
            scope_key = stable_id(
                "dependency_gap_scope",
                relation.relation_id,
                target.concept_id,
            )
            source_event_key = stable_id(
                "dependency_gap_detection",
                relation.relation_id,
                context_hash,
                self.policy.policy_version,
            )
            payload = {
                "relation_id": relation.relation_id,
                "target_action_node": source.concept_id,
                "missing_input_signature": target.concept_id,
                "trigger_relation": relation.relation_type,
                "scope_key": scope_key,
                "canonical_triggering_refs": triggering_refs,
                "source_lineage_roots": lineage_roots,
                "context_snapshot_hash": context_hash,
                "source_event_key": source_event_key,
                "policy_version": self.policy.policy_version,
            }
            candidates.append(
                DependencyGapCandidate(
                    candidate_id=stable_id("dependency_gap_candidate", payload),
                    **payload,
                )
            )

        return tuple(inspected), tuple(candidates)

    def detect_and_record(self, kernel: VerdantKernel) -> DependencyGapDetectionReport:
        """Inspect one frozen pre-write view, then append findings deterministically."""

        inspected, candidates = self.inspect(kernel)
        mutations = tuple(
            self.obligations.observe_gap(
                kernel,
                target_action_node=item.target_action_node,
                missing_input_signature=item.missing_input_signature,
                trigger_relation=item.trigger_relation,
                triggering_refs=item.canonical_triggering_refs,
                source_event_key=item.source_event_key,
                context_snapshot_hash=item.context_snapshot_hash,
                source_lineage_roots=item.source_lineage_roots,
                scope_key=item.scope_key,
                policy_version=item.policy_version,
            )
            for item in candidates
        )
        return DependencyGapDetectionReport(
            policy_version=self.policy.policy_version,
            inspected_relation_ids=inspected,
            candidates=candidates,
            mutations=mutations,
        )

