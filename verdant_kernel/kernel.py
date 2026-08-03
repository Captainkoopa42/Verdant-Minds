from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .models import (
    AttentionCandidate,
    CouncilDecisionEvent,
    CouncilDisposition,
    CouncilReport,
    GovernanceOutcomeRecord,
    ClaimEvidenceEntry,
    ClaimPolarity,
    ClaimProposal,
    ClaimRecord,
    ClaimSourceClass,
    ClaimStatus,
    ConceptProposal,
    ConceptRecord,
    ContradictionRecord,
    ContradictionStatus,
    EvidenceKind,
    EvidenceRecord,
    EvidenceStance,
    ExperienceCommand,
    FieldFrame,
    FieldState,
    ConceptFieldAddress,
    ConceptResonanceProfile,
    ECWFPolicy,
    ResonanceCandidate,
    ResonanceContribution,
    ResonanceEvent,
    ResonanceReport,
    ShardPolicy,
    ShardRecord,
    ShardStatus,
    ShardFormationReport,
    ShardFormationEvent,
    ShardBridgeRecord,
    BridgeStatus,
    RoutingReport,
    RoutingEvent,
    RoutingDisposition,
    ObjectObservationKind,
    ObjectCandidateStatus,
    ObjectAssociationDisposition,
    ObjectPromotionDisposition,
    ObjectObservationRecord,
    ObjectCandidateRecord,
    ObjectObservationReport,
    ObjectObservationEvent,
    ObjectPromotionReport,
    ObjectPromotionEvent,
    WorkspaceSourceKind,
    WorkspaceDisposition,
    WorkspaceWritebackDisposition,
    WorkspacePolicy,
    WorkspaceCandidateInput,
    WorkspaceScoreComponents,
    WorkspaceCandidateAssessment,
    WorkspaceAdmissionReport,
    WorkspaceItemRecord,
    WorkspaceCycleEvent,
    WorkspaceWritebackEvent,
    PlasticityPolicy,
    PlasticityAssociationRecord,
    PlasticityPairAssessment,
    PlasticityReport,
    PlasticityEvent,
    PlasticityUpdateKind,
    StructureCandidateStatus,
    StructurePromotionDisposition,
    StructurePolicy,
    StructureQualityVector,
    StructureCandidateRecord,
    StructureObservationReport,
    StructureObservationEvent,
    StructureRecord,
    StructureEdgeSnapshot,
    StructurePromotionReport,
    StructurePromotionEvent,
    CompilationDisposition,
    StructureAvailabilityAction,
    CompilationPolicy,
    CompilationCost,
    CompilationProbeReport,
    CompilationProbeEvent,
    StructureAvailabilityEvent,
    StructureInteractionPolicy,
    StructureInteractionReport,
    StructureInteractionEvent,
    StructureInteractionDisposition,
    HierarchyCandidateStatus,
    HierarchyPromotionDisposition,
    LayeredProbeDisposition,
    HierarchyPolicy,
    HierarchyQualityVector,
    HierarchyCandidateRecord,
    HierarchyObservationReport,
    HierarchyObservationEvent,
    LayeredStructureRecord,
    HierarchyPromotionReport,
    HierarchyPromotionEvent,
    LayeredStructureAvailabilityEvent,
    LayeredProbeCost,
    LayeredProbeReport,
    LayeredProbeEvent,
    RefoldDisposition,
    RefoldingPolicy,
    StructuralChallengeObservation,
    StructuralChallengeRecord,
    RefoldComponentProposal,
    StructureRefoldReport,
    StructureRefoldEvent,
    NativeModality,
    TemporalBoundaryReason,
    SensoryPolicy,
    SensoryArchiveRecord,
    SensorySampleRecord,
    SynchronizationGroupRecord,
    TemporalEventRecord,
    TemporalEventAssemblyReport,
    TemporalEventAssemblyEvent,
    PerceptualPolicy,
    PerceptualBindingEvent,
    GovernanceState,
    KernelIdentity,
    KernelState,
    RelationRecord,
    RelationStatus,
    RevisionRecord,
    TransitionRecord,
    canonical_json_bytes,
    normalize_label,
    stable_id,
)


class KernelInvariantError(RuntimeError):
    pass


class EvidenceGateError(KernelInvariantError):
    pass


class ReplayConflictError(KernelInvariantError):
    pass


class ResonanceStaleError(KernelInvariantError):
    pass


class ResonanceIntegrityError(KernelInvariantError):
    pass


class GovernanceStaleError(KernelInvariantError):
    pass


class GovernanceIntegrityError(KernelInvariantError):
    pass


class GovernanceAuthorizationError(KernelInvariantError):
    pass


class ShardIntegrityError(KernelInvariantError):
    pass


class ShardStaleError(KernelInvariantError):
    pass


class ShardAuthorizationError(KernelInvariantError):
    pass


class ObjectIntegrityError(KernelInvariantError):
    pass


class ObjectStaleError(KernelInvariantError):
    pass


class ObjectAuthorizationError(KernelInvariantError):
    pass



class PlasticityIntegrityError(KernelInvariantError):
    pass


class PlasticityStaleError(KernelInvariantError):
    pass


class StructureIntegrityError(KernelInvariantError):
    pass


class StructureStaleError(KernelInvariantError):
    pass


class StructureAuthorizationError(KernelInvariantError):
    pass


class CompilationIntegrityError(KernelInvariantError):
    pass


class CompilationStaleError(KernelInvariantError):
    pass


class StructureInteractionIntegrityError(KernelInvariantError):
    pass


class StructureInteractionStaleError(KernelInvariantError):
    pass


class HierarchyIntegrityError(KernelInvariantError):
    pass


class HierarchyStaleError(KernelInvariantError):
    pass


class HierarchyAuthorizationError(KernelInvariantError):
    pass


class RefoldingIntegrityError(KernelInvariantError):
    pass


class RefoldingStaleError(KernelInvariantError):
    pass


class RefoldingAuthorizationError(KernelInvariantError):
    pass


class WorkspaceIntegrityError(KernelInvariantError):
    pass


class WorkspaceStaleError(KernelInvariantError):
    pass


class SensoryIntegrityError(KernelInvariantError):
    pass


class SensoryStaleError(KernelInvariantError):
    pass


@dataclass(frozen=True)
class ExperienceResult:
    event_key: str
    cycle: int
    observation_evidence_id: str
    translation_evidence_id: str
    concept_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    claim_ids: tuple[str, ...] = ()
    contradiction_ids: tuple[str, ...] = ()
    revision_ids: tuple[str, ...] = ()
    transition_id: str = ""
    additional_evidence_ids: tuple[str, ...] = ()
    replayed: bool = False


class VerdantKernel:
    """
    Canonical state authority for the independent Verdant rebuild.

    The kernel owns the only authoritative concept and relation records.
    Neighbor lists, graph metrics, and checkpoint previews are derived views.
    """

    def __init__(
        self,
        *,
        seed: int = 7741,
        state_dim: int = 128,
        run_label: str = "independent-rebuild",
        state: KernelState | None = None,
    ) -> None:
        if state is not None:
            self.state = state.model_copy(deep=True)
            self._migrate_ecwf_state()
            self._migrate_shard_state()
            self._validate_state()
            return
        kernel_id = stable_id("kernel", seed, run_label)
        self.state = KernelState(
            identity=KernelIdentity(
                kernel_id=kernel_id,
                run_label=run_label,
            ),
            seed=seed,
            field=FieldState(
                state_dim=state_dim,
                real=[0.0] * state_dim,
                imag=[0.0] * state_dim,
            ),
        )
        self._migrate_shard_state()

    @classmethod
    def from_state(cls, state: KernelState) -> "VerdantKernel":
        return cls(state=state)

    def snapshot(self) -> KernelState:
        return self.state.model_copy(deep=True)

    def fingerprint(self, *, include_transitions: bool = True) -> str:
        return self.state.fingerprint(include_transitions=include_transitions)

    def semantic_fingerprint(self) -> str:
        return self.state.fingerprint(include_transitions=False)

    def metrics(self) -> dict[str, float | int]:
        node_count = len(self.state.concepts)
        edge_count = len(self.state.relations)
        directed_possible = node_count * max(0, node_count - 1)
        density = edge_count / directed_possible if directed_possible else 0.0
        degree_total = 0
        for concept_id in self.state.concepts:
            degree_total += len(self.neighbors(concept_id, direction="both"))
        field = self._field_array()
        return {
            "cycle": self.state.cycle,
            "concept_count": node_count,
            "relation_count": edge_count,
            "claim_count": len(self.state.claims),
            "contradiction_count": len(self.state.contradictions),
            "revision_count": len(self.state.revisions),
            "evidence_count": len(self.state.evidence),
            "transition_count": len(self.state.transitions),
            "field_history_count": len(self.state.field.history),
            "field_address_count": len(self.state.field_addresses),
            "resonance_profile_count": len(self.state.resonance_profiles),
            "resonance_event_count": len(self.state.resonance_events),
            "attention_candidate_count": len(self.state.attention_candidates),
            "council_decision_count": len(self.state.council_decisions),
            "governance_outcome_count": len(self.state.governance_outcomes),
            "shard_count": len(self.state.shards),
            "specialized_shard_count": sum(1 for item in self.state.shards.values() if item.shard_id != "root"),
            "shard_formation_event_count": len(self.state.shard_formation_events),
            "shard_bridge_count": len(self.state.shard_bridges),
            "routing_event_count": len(self.state.routing_events),
            "object_observation_count": len(self.state.object_observations),
            "object_candidate_count": len(self.state.object_candidates),
            "object_observation_event_count": len(self.state.object_observation_events),
            "object_promotion_event_count": len(self.state.object_promotion_events),
            "promoted_proto_object_count": sum(
                1
                for item in self.state.object_candidates.values()
                if item.status == ObjectCandidateStatus.PROMOTED
            ),
            "sensory_archive_count": len(self.state.sensory_archives),
            "sensory_sample_count": len(self.state.sensory_samples),
            "synchronization_group_count": len(self.state.synchronization_groups),
            "temporal_event_count": len(self.state.temporal_events),
            "temporal_event_assembly_count": len(self.state.temporal_event_assembly_events),
            "perceptual_binding_event_count": len(self.state.perceptual_binding_events),
            "plasticity_association_count": len(self.state.plasticity_associations),
            "plasticity_event_count": len(self.state.plasticity_events),
            "plasticity_total_strength": sum(
                item.strength for item in self.state.plasticity_associations.values()
            ),
            "structure_candidate_count": len(self.state.structure_candidates),
            "eligible_structure_candidate_count": sum(
                1 for item in self.state.structure_candidates.values()
                if item.status == StructureCandidateStatus.ELIGIBLE
            ),
            "promoted_structure_count": len(self.state.structures),
            "structure_observation_event_count": len(self.state.structure_observation_events),
            "structure_promotion_event_count": len(self.state.structure_promotion_events),
            "ablated_structure_count": len(self.state.ablated_structure_ids),
            "structure_availability_event_count": len(self.state.structure_availability_events),
            "compilation_probe_event_count": len(self.state.compilation_probe_events),
            "structure_interaction_event_count": len(self.state.structure_interaction_events),
            "hierarchy_candidate_count": len(self.state.hierarchy_candidates),
            "eligible_hierarchy_candidate_count": sum(
                1 for item in self.state.hierarchy_candidates.values()
                if item.status == HierarchyCandidateStatus.ELIGIBLE
            ),
            "layered_structure_count": len(self.state.layered_structures),
            "hierarchy_observation_event_count": len(self.state.hierarchy_observation_events),
            "hierarchy_promotion_event_count": len(self.state.hierarchy_promotion_events),
            "ablated_layered_structure_count": len(self.state.ablated_layered_structure_ids),
            "layered_probe_event_count": len(self.state.layered_probe_events),
            "structural_challenge_count": len(self.state.structural_challenges),
            "structure_refold_event_count": len(self.state.structure_refold_events),
            "refolded_structure_count": sum(
                1 for item in self.state.structures.values()
                if item.lineage_parent_structure_id is not None
            ),
            "workspace_active_item_count": len(self.state.workspace_items),
            "workspace_cycle_event_count": len(self.state.workspace_cycle_events),
            "workspace_writeback_event_count": len(self.state.workspace_writeback_events),
            "workspace_allocated_resource": sum(item.allocated_resource for item in self.state.workspace_items.values()),
            "active_shard_id": self.state.active_shard_id,
            "directed_density": density,
            "average_neighbor_count": (
                degree_total / node_count if node_count else 0.0
            ),
            "field_norm": float(np.linalg.norm(field)),
        }

    def field_fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(
                {
                    "real": self.state.field.real,
                    "imag": self.state.field.imag,
                    "history_count": len(self.state.field.history),
                    "latest_effect_sha256": (
                        self.state.field.history[-1].effect_sha256
                        if self.state.field.history
                        else ""
                    ),
                    "policy_revision": self.state.ecwf_policy.revision,
                }
            )
        ).hexdigest()

    def governance_fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.state.governance.model_dump(mode="json"))
        ).hexdigest()

    def shard_structural_fingerprint(self) -> str:
        """Fingerprint only state that can alter specialization or routing results.

        Council logging changes cycle and decision history, but does not change this
        fingerprint. That allows a pure shard/routing report to be inspected first,
        authorized by Council, and then committed without becoming falsely stale.
        """

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "concepts": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.concepts.items())
            },
            "relations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.relations.items())
            },
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
            "shards": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.shards.items())
            },
            "bridges": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.shard_bridges.items())
            },
            "active_shard_id": self.state.active_shard_id,
            "shard_policy": self.state.shard_policy.model_dump(mode="json"),
            "field_fingerprint": self.field_fingerprint(),
            "resonance_events": [
                item.model_dump(mode="json") for item in self.state.resonance_events
            ],
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_object_policy(self, **changes: object):
        updated = self.state.object_policy.model_copy(
            update={**changes, "revision": self.state.object_policy.revision + 1}
        )
        updated = type(self.state.object_policy).model_validate(
            updated.model_dump(mode="json")
        )
        self.state.object_policy = updated
        self._validate_state()
        return updated

    def object_structural_fingerprint(self) -> str:
        """Fingerprint evidence and proto-object state without Council log churn."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
            "concepts": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.concepts.items())
            },
            "object_policy": self.state.object_policy.model_dump(mode="json"),
            "object_observations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.object_observations.items())
            },
            "object_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.object_candidates.items())
            },
            "object_observation_events": [
                item.model_dump(mode="json")
                for item in self.state.object_observation_events
            ],
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


    def plasticity_structural_fingerprint(self) -> str:
        """Fingerprint state that can alter bounded local plasticity."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "concepts": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.concepts.items())
            },
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
            "active_shard_id": self.state.active_shard_id,
            "active_shard": self.state.shards[self.state.active_shard_id].model_dump(mode="json"),
            "workspace_items": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.workspace_items.items())
            },
            "workspace_cycle_events": [
                item.model_dump(mode="json") for item in self.state.workspace_cycle_events
            ],
            "plasticity_policy": self.state.plasticity_policy.model_dump(mode="json"),
            "plasticity_associations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.plasticity_associations.items())
            },
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_plasticity_policy(self, **changes: object):
        updated = self.state.plasticity_policy.model_copy(
            update={**changes, "revision": self.state.plasticity_policy.revision + 1}
        )
        updated = type(self.state.plasticity_policy).model_validate(
            updated.model_dump(mode="json")
        )
        self.state.plasticity_policy = updated
        self._validate_state()
        return updated

    def structure_structural_fingerprint(self) -> str:
        """Fingerprint state that can alter earned-structure observation/promotion."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "concepts": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.concepts.items())
            },
            "relations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.relations.items())
            },
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
            "active_shard_id": self.state.active_shard_id,
            "plasticity_associations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.plasticity_associations.items())
            },
            "plasticity_events": [
                item.model_dump(mode="json") for item in self.state.plasticity_events
            ],
            "workspace_cycle_events": [
                item.model_dump(mode="json") for item in self.state.workspace_cycle_events
            ],
            "structure_policy": self.state.structure_policy.model_dump(mode="json"),
            "structure_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structure_candidates.items())
            },
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "structure_observation_events": [
                item.model_dump(mode="json") for item in self.state.structure_observation_events
            ],
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_structure_policy(self, **changes: object):
        updated = self.state.structure_policy.model_copy(
            update={**changes, "revision": self.state.structure_policy.revision + 1}
        )
        updated = type(self.state.structure_policy).model_validate(
            updated.model_dump(mode="json")
        )
        self.state.structure_policy = updated
        self._validate_state()
        return updated

    def compilation_structural_fingerprint(self) -> str:
        """Fingerprint state that can change compiled reconstruction or availability."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "active_shard_id": self.state.active_shard_id,
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "plasticity_associations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.plasticity_associations.items())
            },
            "compilation_policy": self.state.compilation_policy.model_dump(mode="json"),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_compilation_policy(self, **changes: object):
        updated = self.state.compilation_policy.model_copy(
            update={**changes, "revision": self.state.compilation_policy.revision + 1}
        )
        updated = type(self.state.compilation_policy).model_validate(
            updated.model_dump(mode="json")
        )
        self.state.compilation_policy = updated
        self._validate_state()
        return updated

    def structure_is_available(self, structure_id: str) -> bool:
        return (
            structure_id in self.state.structures
            and structure_id not in set(self.state.ablated_structure_ids)
        )

    def set_structure_availability(
        self,
        structure_id: str,
        *,
        available: bool,
        reason: str,
    ) -> StructureAvailabilityEvent:
        if structure_id not in self.state.structures:
            raise CompilationIntegrityError("Structure availability references a missing structure.")
        if not reason.strip():
            raise CompilationIntegrityError("Structure availability change requires a reason.")
        current = set(self.state.ablated_structure_ids)
        action = (
            StructureAvailabilityAction.RESTORE
            if available
            else StructureAvailabilityAction.ABLATE
        )
        if available:
            current.discard(structure_id)
        else:
            current.add(structure_id)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        self.state.ablated_structure_ids = tuple(sorted(current))
        event_id = stable_id(
            "structure_availability_event",
            structure_id,
            action.value,
            reason.strip(),
            self.state.cycle,
        )
        event = StructureAvailabilityEvent(
            event_id=event_id,
            structure_id=structure_id,
            action=action,
            reason=reason.strip(),
            committed_cycle=self.state.cycle,
        )
        self.state.structure_availability_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {"structure_id": structure_id, "available": available, "reason": reason.strip()}
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "set_structure_availability",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="set_structure_availability",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(structure_id,),
                output_refs=(event_id,),
            )
        )
        self._validate_state()
        return event

    def validate_compilation_probe_report(self, report: CompilationProbeReport) -> None:
        try:
            report = CompilationProbeReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise CompilationIntegrityError(
                "Compilation probe report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise CompilationIntegrityError("Compilation probe belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise CompilationStaleError("Compilation probe report cycle is stale.")
        if report.structural_fingerprint != self.compilation_structural_fingerprint():
            raise CompilationStaleError(
                "Compilation probe was computed against different cognitive state."
            )
        if report.policy_revision != self.state.compilation_policy.revision:
            raise CompilationStaleError("Compilation policy changed after inspection.")
        if any(item not in self.state.concepts for item in report.cue_concept_ids):
            raise CompilationIntegrityError("Compilation probe references a missing cue concept.")
        if any(item not in self.state.concepts for item in report.reconstructed_concept_ids):
            raise CompilationIntegrityError("Compilation probe reconstructed a missing concept.")
        if report.structure_id is not None:
            if report.structure_id not in self.state.structures:
                raise CompilationIntegrityError("Compilation probe references a missing structure.")
            if not self.structure_is_available(report.structure_id):
                raise CompilationStaleError("Compilation probe structure is currently ablated.")

    def commit_compilation_probe(
        self, report: CompilationProbeReport
    ) -> CompilationProbeEvent:
        self.validate_compilation_probe_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "compilation_probe_event",
            report.report_id,
            self.state.cycle,
        )
        event = CompilationProbeEvent(
            event_id=event_id,
            report=report,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.compilation_probe_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_compilation_probe",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_compilation_probe",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=tuple(
                    sorted(
                        {
                            report.report_id,
                            *report.cue_concept_ids,
                            *( (report.structure_id,) if report.structure_id else () ),
                        }
                    )
                ),
                output_refs=(event_id,),
            )
        )
        self._validate_state()
        return event

    def structure_interaction_structural_fingerprint(self) -> str:
        """Fingerprint state that can alter cross-symbolic structure interaction."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "plasticity_associations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.plasticity_associations.items())
            },
            "structure_interaction_policy": self.state.structure_interaction_policy.model_dump(mode="json"),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_structure_interaction_policy(self, **changes: object):
        updated = self.state.structure_interaction_policy.model_copy(
            update={
                **changes,
                "revision": self.state.structure_interaction_policy.revision + 1,
            }
        )
        updated = StructureInteractionPolicy.model_validate(updated.model_dump(mode="json"))
        self.state.structure_interaction_policy = updated
        self._validate_state()
        return updated

    def validate_structure_interaction_report(
        self, report: StructureInteractionReport
    ) -> None:
        try:
            report = StructureInteractionReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise StructureInteractionIntegrityError(
                "Structure interaction report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise StructureInteractionIntegrityError(
                "Structure interaction report belongs to another kernel."
            )
        if report.cycle != self.state.cycle:
            raise StructureInteractionStaleError("Structure interaction report cycle is stale.")
        if report.structural_fingerprint != self.structure_interaction_structural_fingerprint():
            raise StructureInteractionStaleError(
                "Structure interaction report was computed against different cognitive state."
            )
        if report.policy_revision != self.state.structure_interaction_policy.revision:
            raise StructureInteractionStaleError(
                "Structure interaction policy changed after inspection."
            )
        if report.source_structure_id not in self.state.structures:
            raise StructureInteractionIntegrityError(
                "Structure interaction references a missing source structure."
            )
        if not self.structure_is_available(report.source_structure_id):
            raise StructureInteractionStaleError(
                "Structure interaction source is currently ablated."
            )
        if report.source_signature.structure_id != report.source_structure_id:
            raise StructureInteractionIntegrityError(
                "Structure interaction source signature references the wrong structure."
            )
        for candidate in report.candidates:
            if candidate.target_structure_id not in self.state.structures:
                raise StructureInteractionIntegrityError(
                    "Structure interaction references a missing target structure."
                )
            if candidate.target_structure_id == report.source_structure_id:
                raise StructureInteractionIntegrityError(
                    "Structure interaction cannot compare a structure to itself."
                )
            if not self.structure_is_available(candidate.target_structure_id):
                raise StructureInteractionStaleError(
                    "Structure interaction target is currently ablated."
                )
            source_members = set(self.state.structures[report.source_structure_id].member_concept_ids)
            target_members = set(self.state.structures[candidate.target_structure_id].member_concept_ids)
            if any(a not in source_members or b not in target_members for a, b in candidate.member_mapping):
                raise StructureInteractionIntegrityError(
                    "Structure interaction mapping escaped source/target membership."
                )

    def commit_structure_interaction(
        self, report: StructureInteractionReport
    ) -> StructureInteractionEvent:
        self.validate_structure_interaction_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "structure_interaction_event",
            report.report_id,
            self.state.cycle,
        )
        event = StructureInteractionEvent(
            event_id=event_id,
            report=report,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.structure_interaction_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_structure_interaction",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_structure_interaction",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=tuple(
                    sorted(
                        {
                            report.report_id,
                            report.source_structure_id,
                            *(item.target_structure_id for item in report.candidates),
                        }
                    )
                ),
                output_refs=(event_id,),
            )
        )
        self._validate_state()
        return event

    def hierarchy_structural_fingerprint(self) -> str:
        """Fingerprint state that can alter higher-order structure formation/promotion."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "structure_interaction_events": [
                item.model_dump(mode="json") for item in self.state.structure_interaction_events
            ],
            "hierarchy_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.hierarchy_candidates.items())
            },
            "layered_structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.layered_structures.items())
            },
            "ablated_layered_structure_ids": self.state.ablated_layered_structure_ids,
            "hierarchy_policy": self.state.hierarchy_policy.model_dump(mode="json"),
            "interaction_policy_revision": self.state.structure_interaction_policy.revision,
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_hierarchy_policy(self, **changes: object):
        updated = self.state.hierarchy_policy.model_copy(
            update={**changes, "revision": self.state.hierarchy_policy.revision + 1}
        )
        updated = HierarchyPolicy.model_validate(updated.model_dump(mode="json"))
        self.state.hierarchy_policy = updated
        self._validate_state()
        return updated

    def layered_structure_is_available(self, layered_structure_id: str) -> bool:
        return (
            layered_structure_id in self.state.layered_structures
            and layered_structure_id not in set(self.state.ablated_layered_structure_ids)
        )

    def validate_hierarchy_observation_report(self, report: HierarchyObservationReport) -> None:
        try:
            report = HierarchyObservationReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise HierarchyIntegrityError("Hierarchy observation report failed its checksum.") from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise HierarchyIntegrityError("Hierarchy observation belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise HierarchyStaleError("Hierarchy observation report cycle is stale.")
        if report.structural_fingerprint != self.hierarchy_structural_fingerprint():
            raise HierarchyStaleError("Hierarchy observation was computed against different state.")
        if report.policy_revision != self.state.hierarchy_policy.revision:
            raise HierarchyStaleError("Hierarchy policy changed after observation inspection.")
        if not self.state.structure_interaction_events:
            raise HierarchyIntegrityError("Hierarchy observation requires interaction history.")
        if report.latest_interaction_event_id != self.state.structure_interaction_events[-1].event_id:
            raise HierarchyStaleError("Hierarchy observation no longer references the latest interaction event.")
        for candidate in report.proposed_candidates:
            if any(item not in self.state.structures for item in candidate.member_structure_ids):
                raise HierarchyIntegrityError("Hierarchy candidate references missing earned structures.")
            if any(item in self.state.ablated_structure_ids for item in candidate.member_structure_ids):
                raise HierarchyStaleError("Hierarchy candidate includes an ablated earned structure.")
            if any(item not in {event.event_id for event in self.state.structure_interaction_events} for item in candidate.interaction_event_ids):
                raise HierarchyIntegrityError("Hierarchy candidate references missing interaction history.")
            self._validated_evidence_refs(candidate.evidence_refs)

    def commit_hierarchy_observation(self, report: HierarchyObservationReport) -> HierarchyObservationEvent:
        self.validate_hierarchy_observation_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        for candidate in report.proposed_candidates:
            self.state.hierarchy_candidates[candidate.candidate_id] = candidate
        active_ids = tuple(sorted(self.state.hierarchy_candidates))
        event_id = stable_id(
            "hierarchy_observation_event", report.report_id, active_ids, self.state.cycle
        )
        event = HierarchyObservationEvent(
            event_id=event_id,
            report=report,
            active_candidate_ids=active_ids,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.hierarchy_observation_events.append(event)
        command_hash = hashlib.sha256(canonical_json_bytes(report.model_dump(mode="json"))).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition", self.state.identity.kernel_id, self.state.event_sequence,
                    "commit_hierarchy_observation", command_hash, input_fingerprint, output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_hierarchy_observation",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, report.latest_interaction_event_id),
                output_refs=(event_id, *report.observed_candidate_ids),
            )
        )
        self._validate_state()
        return event

    def validate_hierarchy_promotion_report(self, report: HierarchyPromotionReport) -> None:
        try:
            report = HierarchyPromotionReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise HierarchyIntegrityError("Hierarchy promotion report failed its checksum.") from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise HierarchyIntegrityError("Hierarchy promotion belongs to another kernel.")
        if report.structural_fingerprint != self.hierarchy_structural_fingerprint():
            raise HierarchyStaleError("Hierarchy promotion was computed against different state.")
        if report.policy_revision != self.state.hierarchy_policy.revision:
            raise HierarchyStaleError("Hierarchy policy changed after promotion inspection.")
        candidate = self.state.hierarchy_candidates.get(report.candidate_id)
        if candidate is None:
            raise HierarchyIntegrityError("Hierarchy promotion references a missing candidate.")
        if candidate != report.candidate_snapshot:
            raise HierarchyStaleError("Hierarchy candidate changed after promotion inspection.")
        if candidate.status == HierarchyCandidateStatus.PROMOTED:
            raise HierarchyIntegrityError("Hierarchy candidate is already promoted.")
        if report.evidence_refs != candidate.evidence_refs:
            raise HierarchyIntegrityError("Hierarchy promotion must preserve evidence lineage.")
        expected = stable_id("layered_structure", candidate.candidate_id)
        if report.proposed_layered_structure_id != expected:
            raise HierarchyIntegrityError("Layered structure identity drift detected.")

    def commit_hierarchy_promotion(
        self,
        report: HierarchyPromotionReport,
        *,
        council_decision_event_id: str,
    ) -> HierarchyPromotionEvent:
        self.validate_hierarchy_promotion_report(report)
        if report.disposition != HierarchyPromotionDisposition.PROMOTE:
            raise HierarchyIntegrityError("Only an eligible hierarchy candidate can be promoted.")
        if report.rejection_codes:
            raise HierarchyIntegrityError("Hierarchy promotion still contains failed gates.")
        try:
            self.assert_operation_authorized(council_decision_event_id, report.operation)
        except GovernanceAuthorizationError as exc:
            raise HierarchyAuthorizationError("Council did not authorize layered promotion.") from exc

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        candidate = self.state.hierarchy_candidates[report.candidate_id]
        record = LayeredStructureRecord(
            layered_structure_id=report.proposed_layered_structure_id,
            source_candidate_id=candidate.candidate_id,
            opaque_name=report.proposed_opaque_name,
            member_structure_ids=candidate.member_structure_ids,
            evidence_refs=candidate.evidence_refs,
            quality_at_promotion=candidate.quality,
            prototype_dim=candidate.prototype_dim,
            prototype_real=candidate.prototype_real,
            prototype_imag=candidate.prototype_imag,
            prototype_sha256=candidate.prototype_sha256,
            created_cycle=self.state.cycle,
            council_decision_event_id=council_decision_event_id,
            promotion_policy_revision=report.policy_revision,
            depth=2,
            semantic_label_preinstalled=False,
        )
        self.state.layered_structures[record.layered_structure_id] = record
        updated = candidate.model_copy(update={
            "status": HierarchyCandidateStatus.PROMOTED,
            "updated_cycle": self.state.cycle,
            "promoted_layered_structure_id": record.layered_structure_id,
        })
        self.state.hierarchy_candidates[candidate.candidate_id] = HierarchyCandidateRecord.model_validate(
            updated.model_dump(mode="json")
        )
        event_id = stable_id(
            "hierarchy_promotion_event", report.report_id, council_decision_event_id,
            record.layered_structure_id, self.state.cycle,
        )
        event = HierarchyPromotionEvent(
            event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            layered_structure_id=record.layered_structure_id,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.hierarchy_promotion_events.append(event)
        command_hash = hashlib.sha256(canonical_json_bytes({
            "report": report.model_dump(mode="json"),
            "council_decision_event_id": council_decision_event_id,
        })).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition", self.state.identity.kernel_id, self.state.event_sequence,
                    "commit_hierarchy_promotion", command_hash, input_fingerprint, output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_hierarchy_promotion",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, council_decision_event_id, candidate.candidate_id),
                output_refs=(event_id, record.layered_structure_id),
            )
        )
        self._validate_state()
        return event

    def set_layered_structure_availability(
        self, layered_structure_id: str, *, available: bool, reason: str
    ) -> LayeredStructureAvailabilityEvent:
        if layered_structure_id not in self.state.layered_structures:
            raise HierarchyIntegrityError("Layered availability references a missing structure.")
        if not reason.strip():
            raise HierarchyIntegrityError("Layered availability changes require a reason.")
        current = set(self.state.ablated_layered_structure_ids)
        if available:
            current.discard(layered_structure_id)
            action = StructureAvailabilityAction.RESTORE
        else:
            current.add(layered_structure_id)
            action = StructureAvailabilityAction.ABLATE
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        self.state.ablated_layered_structure_ids = tuple(sorted(current))
        event_id = stable_id(
            "layered_structure_availability_event", layered_structure_id,
            action.value, reason.strip(), self.state.cycle,
        )
        event = LayeredStructureAvailabilityEvent(
            event_id=event_id,
            layered_structure_id=layered_structure_id,
            action=action,
            reason=reason.strip(),
            committed_cycle=self.state.cycle,
        )
        self.state.layered_structure_availability_events.append(event)
        command_hash = hashlib.sha256(canonical_json_bytes({
            "layered_structure_id": layered_structure_id,
            "available": available,
            "reason": reason.strip(),
        })).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition", self.state.identity.kernel_id, self.state.event_sequence,
                    "set_layered_structure_availability", command_hash,
                    input_fingerprint, output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="set_layered_structure_availability",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(layered_structure_id,),
                output_refs=(event_id,),
            )
        )
        self._validate_state()
        return event

    def hierarchy_probe_structural_fingerprint(self) -> str:
        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "layered_structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.layered_structures.items())
            },
            "ablated_layered_structure_ids": self.state.ablated_layered_structure_ids,
            "hierarchy_policy": self.state.hierarchy_policy.model_dump(mode="json"),
            "structure_interaction_policy": self.state.structure_interaction_policy.model_dump(mode="json"),
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def validate_layered_probe_report(self, report: LayeredProbeReport) -> None:
        try:
            report = LayeredProbeReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise HierarchyIntegrityError("Layered probe report failed its checksum.") from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise HierarchyIntegrityError("Layered probe belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise HierarchyStaleError("Layered probe cycle is stale.")
        if report.structural_fingerprint != self.hierarchy_probe_structural_fingerprint():
            raise HierarchyStaleError("Layered probe was computed against different state.")
        if report.policy_revision != self.state.hierarchy_policy.revision:
            raise HierarchyStaleError("Hierarchy policy changed after layered probe inspection.")
        if report.query_structure_id not in self.state.structures:
            raise HierarchyIntegrityError("Layered probe query structure is missing.")
        if not self.structure_is_available(report.query_structure_id):
            raise HierarchyStaleError("Layered probe query structure is ablated.")
        if report.layered_structure_id is not None:
            if report.layered_structure_id not in self.state.layered_structures:
                raise HierarchyIntegrityError("Layered probe references a missing layered operand.")
            if not self.layered_structure_is_available(report.layered_structure_id):
                raise HierarchyStaleError("Layered probe operand is ablated.")
        if any(item not in self.state.structures for item in report.matched_structure_ids):
            raise HierarchyIntegrityError("Layered probe returned missing base structures.")
        if report.query_structure_id in report.matched_structure_ids:
            raise HierarchyIntegrityError("Layered probe cannot return the query as its own family member.")

    def commit_layered_probe(self, report: LayeredProbeReport) -> LayeredProbeEvent:
        self.validate_layered_probe_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id("layered_probe_event", report.report_id, self.state.cycle)
        event = LayeredProbeEvent(
            event_id=event_id,
            report=report,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.layered_probe_events.append(event)
        command_hash = hashlib.sha256(canonical_json_bytes(report.model_dump(mode="json"))).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition", self.state.identity.kernel_id, self.state.event_sequence,
                    "commit_layered_probe", command_hash, input_fingerprint, output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_layered_probe",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=tuple(sorted({
                    report.report_id, report.query_structure_id,
                    *( (report.layered_structure_id,) if report.layered_structure_id else () ),
                })),
                output_refs=(event_id, *report.matched_structure_ids),
            )
        )
        self._validate_state()
        return event

    def workspace_structural_fingerprint(self) -> str:
        """Fingerprint every source that can change workspace admission."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
            "contradictions": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.contradictions.items())
            },
            "attention_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.attention_candidates.items())
            },
            "resonance_events": [
                item.model_dump(mode="json") for item in self.state.resonance_events
            ],
            "object_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.object_candidates.items())
            },
            "shards": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.shards.items())
            },
            "active_shard_id": self.state.active_shard_id,
            "council_decisions": [
                item.model_dump(mode="json") for item in self.state.council_decisions
            ],
            "temporal_events": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.temporal_events.items())
            },
            "workspace_policy": self.state.workspace_policy.model_dump(mode="json"),
            "plasticity_policy": self.state.plasticity_policy.model_dump(mode="json"),
            "plasticity_associations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.plasticity_associations.items())
            },
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "compilation_policy": self.state.compilation_policy.model_dump(mode="json"),
            "workspace_items": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.workspace_items.items())
            },
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def sensory_structural_fingerprint(self) -> str:
        """Fingerprint the nonsemantic sensory substrate and event memory."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "sensory_policy": self.state.sensory_policy.model_dump(mode="json"),
            "sensory_archives": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.sensory_archives.items())
            },
            "sensory_samples": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.sensory_samples.items())
            },
            "synchronization_groups": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.synchronization_groups.items())
            },
            "temporal_events": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.temporal_events.items())
            },
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


    def perceptual_structural_fingerprint(self) -> str:
        """Fingerprint native visual event state and object hypotheses used for binding."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "perceptual_policy": self.state.perceptual_policy.model_dump(mode="json"),
            "sensory_samples": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.sensory_samples.items())
                if value.modality == NativeModality.VISION
            },
            "temporal_events": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.temporal_events.items())
            },
            "object_observations": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.object_observations.items())
            },
            "object_candidates": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.object_candidates.items())
            },
            "binding_events": [
                item.model_dump(mode="json") for item in self.state.perceptual_binding_events
            ],
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_perceptual_policy(self, **changes: object) -> PerceptualPolicy:
        updated = self.state.perceptual_policy.model_copy(
            update={**changes, "revision": self.state.perceptual_policy.revision + 1}
        )
        updated = PerceptualPolicy.model_validate(updated.model_dump(mode="json"))
        self.state.perceptual_policy = updated
        self._validate_state()
        return updated

    def record_perceptual_binding(
        self,
        *,
        report_id: str,
        report_sha256: str,
        temporal_event_ids: Iterable[str],
        sample_ids: Iterable[str],
        object_observation_event_ids: Iterable[str],
        object_candidate_ids: Iterable[str],
        policy_revision: int,
        metadata: dict[str, object] | None = None,
    ) -> PerceptualBindingEvent:
        temporal = tuple(sorted(set(temporal_event_ids)))
        samples = tuple(sorted(set(sample_ids)))
        object_events = tuple(sorted(set(object_observation_event_ids)))
        candidates = tuple(sorted(set(object_candidate_ids)))
        if not temporal or not samples:
            raise SensoryIntegrityError("Perceptual binding requires temporal events and samples.")
        if any(item not in self.state.temporal_events for item in temporal):
            raise SensoryIntegrityError("Perceptual binding references a missing temporal event.")
        if any(item not in self.state.sensory_samples for item in samples):
            raise SensoryIntegrityError("Perceptual binding references a missing sensory sample.")
        known_object_events = {item.event_id for item in self.state.object_observation_events}
        if any(item not in known_object_events for item in object_events):
            raise ObjectIntegrityError("Perceptual binding references a missing object observation event.")
        if any(item not in self.state.object_candidates for item in candidates):
            raise ObjectIntegrityError("Perceptual binding references a missing object candidate.")
        if policy_revision != self.state.perceptual_policy.revision:
            raise SensoryStaleError("Perceptual policy changed before binding commit.")
        if any(
            set(self.state.temporal_events[event_id].sample_ids).isdisjoint(samples)
            for event_id in temporal
        ):
            raise SensoryIntegrityError("Each perceptual temporal event must contribute samples.")
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "perceptual_binding_event",
            report_id,
            report_sha256,
            temporal,
            samples,
            object_events,
            candidates,
            self.state.cycle,
            policy_revision,
        )
        event = PerceptualBindingEvent(
            event_id=event_id,
            report_id=report_id,
            report_sha256=report_sha256,
            temporal_event_ids=temporal,
            sample_ids=samples,
            object_observation_event_ids=object_events,
            object_candidate_ids=candidates,
            committed_cycle=self.state.cycle,
            policy_revision=policy_revision,
            semantic_mutation_permitted=False,
            metadata=metadata or {},
        )
        self.state.perceptual_binding_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report_id": report_id,
                    "report_sha256": report_sha256,
                    "temporal_event_ids": temporal,
                    "sample_ids": samples,
                    "object_observation_event_ids": object_events,
                    "object_candidate_ids": candidates,
                    "policy_revision": policy_revision,
                    "metadata": metadata or {},
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "record_perceptual_binding",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="record_perceptual_binding",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report_id, *temporal, *samples),
                output_refs=(event_id, *object_events, *candidates),
            )
        )
        self._validate_state()
        return event

    def address_diagnostics(self) -> dict[str, float | int]:
        addresses = [
            self._address_array(item)
            for item in sorted(
                self.state.field_addresses.values(),
                key=lambda item: item.concept_id,
            )
        ]
        digests = [
            item.address_sha256
            for item in sorted(
                self.state.field_addresses.values(),
                key=lambda item: item.concept_id,
            )
        ]
        vector_keys = [
            hashlib.sha256(
                canonical_json_bytes(
                    {
                        "real": [float(value) for value in address.real],
                        "imag": [float(value) for value in address.imag],
                    }
                )
            ).hexdigest()
            for address in addresses
        ]
        similarities: list[float] = []
        for left_index, left in enumerate(addresses):
            for right in addresses[left_index + 1 :]:
                similarities.append(
                    float(min(1.0, abs(np.vdot(left, right))))
                )
        return {
            "address_count": len(addresses),
            "duplicate_digest_count": len(digests) - len(set(digests)),
            "duplicate_vector_count": len(vector_keys) - len(set(vector_keys)),
            "mean_pair_similarity": (
                float(np.mean(similarities)) if similarities else 0.0
            ),
            "max_pair_similarity": max(similarities, default=0.0),
        }

    def inspect_resonance(
        self,
        features: Iterable[float],
        modality: str,
        *,
        top_k: int | None = None,
        candidate_concept_ids: Iterable[str] | None = None,
    ) -> ResonanceReport:
        """Purely rank existing concepts. This method cannot create semantic state."""

        vector = self._validated_feature_array(features)
        requested_top_k = top_k or self.state.ecwf_policy.default_top_k
        if requested_top_k < 1:
            raise ValueError("top_k must be at least 1.")
        if candidate_concept_ids is None:
            scope = tuple(sorted(self.state.concepts))
        else:
            scope = tuple(sorted(set(candidate_concept_ids)))
            missing = [item for item in scope if item not in self.state.concepts]
            if missing:
                raise KeyError(f"Unknown resonance candidate concepts: {missing}")
        missing_addresses = [
            item for item in scope if item not in self.state.field_addresses
        ]
        if missing_addresses:
            raise KernelInvariantError(
                "Concept field addresses are missing for: "
                + ", ".join(missing_addresses)
            )

        query_effect = self._project_effect(vector, modality)
        current_field = self._field_array()
        current_norm = np.linalg.norm(current_field)
        if current_norm:
            current_field = current_field / current_norm

        policy = self.state.ecwf_policy
        raw_weights = np.asarray(
            [
                policy.query_profile_weight,
                policy.query_current_weight,
                policy.query_history_weight,
            ],
            dtype=np.float64,
        )
        normalized_weights = raw_weights / float(raw_weights.sum())
        recent_frames = self.state.field.history[-policy.history_window :]

        unranked: list[tuple[str, float, ResonanceContribution]] = []
        for concept_id in scope:
            address = self._address_array(self.state.field_addresses[concept_id])
            profile = self.state.resonance_profiles.get(concept_id)
            profile_alignment = 0.0
            if profile is not None:
                profile_vector = self._profile_array(profile)
                profile_alignment = float(
                    min(1.0, abs(np.vdot(profile_vector, query_effect)))
                )
            current_alignment = (
                float(min(1.0, abs(np.vdot(address, current_field))))
                if current_norm
                else 0.0
            )
            history_alignment = self._history_alignment(address, recent_frames)
            weighted_profile = profile_alignment * float(normalized_weights[0])
            weighted_current = current_alignment * float(normalized_weights[1])
            weighted_history = history_alignment * float(normalized_weights[2])
            score = min(
                1.0,
                weighted_profile + weighted_current + weighted_history,
            )
            contribution = ResonanceContribution(
                profile_alignment=profile_alignment,
                current_field_alignment=current_alignment,
                history_alignment=history_alignment,
                profile_weight=float(normalized_weights[0]),
                current_field_weight=float(normalized_weights[1]),
                history_weight=float(normalized_weights[2]),
                weighted_profile=weighted_profile,
                weighted_current_field=weighted_current,
                weighted_history=weighted_history,
            )
            unranked.append((concept_id, score, contribution))

        ordered = sorted(unranked, key=lambda item: (-item[1], item[0]))
        candidates = tuple(
            ResonanceCandidate(
                rank=index + 1,
                concept_id=concept_id,
                score=score,
                profile_exposure_count=(
                    self.state.resonance_profiles[concept_id].exposure_count
                    if concept_id in self.state.resonance_profiles
                    else 0
                ),
                profile_evidence_count=(
                    len(self.state.resonance_profiles[concept_id].evidence_refs)
                    if concept_id in self.state.resonance_profiles
                    else 0
                ),
                contribution=contribution,
            )
            for index, (concept_id, score, contribution) in enumerate(
                ordered[:requested_top_k]
            )
        )
        query_feature_sha256 = hashlib.sha256(
            canonical_json_bytes([float(value) for value in vector])
        ).hexdigest()
        state_fingerprint = self.semantic_fingerprint()
        field_fingerprint = self.field_fingerprint()
        query_features = tuple(float(value) for value in vector)
        query_id = stable_id(
            "resonance_query",
            self.state.identity.kernel_id,
            self.state.cycle,
            modality,
            query_feature_sha256,
            state_fingerprint,
            field_fingerprint,
            policy.revision,
            scope,
            tuple(item.model_dump(mode="json") for item in candidates),
        )
        return ResonanceReport(
            query_id=query_id,
            kernel_id=self.state.identity.kernel_id,
            cycle=self.state.cycle,
            modality=modality,
            query_features=query_features,
            query_feature_sha256=query_feature_sha256,
            state_fingerprint=state_fingerprint,
            field_fingerprint=field_fingerprint,
            policy_revision=policy.revision,
            candidate_scope_count=len(scope),
            candidate_scope_ids=scope,
            candidates=candidates,
        )

    def commit_resonance(
        self,
        report: ResonanceReport,
        *,
        evidence_refs: Iterable[str],
        max_candidates: int | None = None,
        resource_request: float | None = None,
    ) -> ResonanceEvent:
        """Admit ranked possibilities to attention without changing semantic truth."""

        try:
            report = ResonanceReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise ResonanceIntegrityError(
                "Resonance report failed its identity or content checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise ResonanceIntegrityError(
                "Resonance report belongs to a different kernel."
            )
        if report.state_fingerprint != self.semantic_fingerprint():
            raise ResonanceStaleError(
                "Resonance report was computed against a different canonical state."
            )
        if report.field_fingerprint != self.field_fingerprint():
            raise ResonanceStaleError(
                "Resonance report was computed against a different field state."
            )
        recomputed = self.inspect_resonance(
            report.query_features,
            report.modality,
            top_k=max(1, len(report.candidates)),
            candidate_concept_ids=report.candidate_scope_ids,
        )
        if recomputed != report:
            raise ResonanceIntegrityError(
                "Resonance report does not reproduce from the current field and cue."
            )
        evidence = self._validated_evidence_refs(evidence_refs)
        limit = max_candidates if max_candidates is not None else len(report.candidates)
        if limit < 0:
            raise ValueError("max_candidates cannot be negative.")
        request = (
            resource_request
            if resource_request is not None
            else self.state.ecwf_policy.default_attention_resource
        )
        if request <= 0.0 or not math.isfinite(request):
            raise ValueError("resource_request must be finite and positive.")

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        selected = report.candidates[:limit]
        attention_ids: list[str] = []
        for candidate in selected:
            contribution = candidate.contribution
            reason = (
                f"ecwf_resonance:{report.query_id}:score={candidate.score:.12f}:"
                f"profile={contribution.profile_alignment:.12f}:"
                f"current={contribution.current_field_alignment:.12f}:"
                f"history={contribution.history_alignment:.12f}"
            )
            attention = self.set_attention_candidate(
                source_ref=candidate.concept_id,
                priority=candidate.score,
                resource_request=request,
                reason=reason,
                evidence_refs=evidence,
            )
            attention_ids.append(attention.candidate_id)

        event_id = stable_id(
            "resonance_event",
            report.query_id,
            self.state.cycle,
            evidence,
            tuple(attention_ids),
        )
        event = ResonanceEvent(
            resonance_event_id=event_id,
            query_report=report,
            committed_cycle=self.state.cycle,
            evidence_refs=evidence,
            attention_candidate_ids=tuple(attention_ids),
            semantic_mutation_permitted=False,
        )
        self.state.resonance_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "evidence_refs": evidence,
                    "max_candidates": limit,
                    "resource_request": request,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        transition = TransitionRecord(
            transition_id=stable_id(
                "transition",
                self.state.identity.kernel_id,
                self.state.event_sequence,
                command_hash,
            ),
            sequence=self.state.event_sequence,
            cycle=self.state.cycle,
            operation="commit_resonance",
            command_hash=command_hash,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            input_refs=evidence,
            output_refs=(event_id, *tuple(attention_ids)),
        )
        self.state.transitions.append(transition)
        self._validate_state()
        return event

    def neighbors(
        self,
        concept_id: str,
        *,
        direction: str = "out",
    ) -> tuple[str, ...]:
        if concept_id not in self.state.concepts:
            raise KeyError(f"Unknown concept '{concept_id}'.")
        if direction not in {"out", "in", "both"}:
            raise ValueError("direction must be 'out', 'in', or 'both'.")
        found: set[str] = set()
        for relation in self.state.relations.values():
            if direction in {"out", "both"} and relation.source_concept_id == concept_id:
                found.add(relation.target_concept_id)
            if direction in {"in", "both"} and relation.target_concept_id == concept_id:
                found.add(relation.source_concept_id)
            if not relation.directed:
                if relation.target_concept_id == concept_id:
                    found.add(relation.source_concept_id)
                if relation.source_concept_id == concept_id:
                    found.add(relation.target_concept_id)
        return tuple(sorted(found))

    def simulate_field_effect(
        self,
        features: Iterable[float],
        modality: str,
    ) -> np.ndarray:
        vector = self._validated_feature_array(features)
        return self._project_effect(vector, modality)

    def apply_experience(self, command: ExperienceCommand) -> ExperienceResult:
        command_hash = hashlib.sha256(
            canonical_json_bytes(command.model_dump(mode="json"))
        ).hexdigest()
        existing_hash = self.state.processed_event_keys.get(command.event_key)
        if existing_hash is not None:
            if existing_hash != command_hash:
                raise ReplayConflictError(
                    f"Event key '{command.event_key}' was already used for a different command."
                )
            return self._replayed_result(command.event_key)

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        cycle = self.state.cycle

        observation = self._upsert_evidence(
            kind=EvidenceKind.OBSERVATION,
            event_key=command.event_key,
            source_ref=command.source_ref,
            confidence=command.confidence,
            payload_sha256=command.payload_sha256,
            details={
                "modality": command.modality,
                "role": "native_payload",
                **command.metadata,
            },
        )
        translation = self._upsert_evidence(
            kind=EvidenceKind.TRANSLATION,
            event_key=command.event_key,
            source_ref=f"{command.source_ref}:translation",
            confidence=command.confidence,
            payload_sha256=command.payload_sha256,
            details={
                "modality": command.modality,
                "feature_dim": len(command.feature_vector),
                "canonical_representation": False,
            },
        )
        semantic_evidence_ids: tuple[str, ...] = ()
        if command.semantic_evidence_kind is not None:
            semantic_evidence = self._upsert_evidence(
                kind=command.semantic_evidence_kind,
                event_key=command.event_key,
                source_ref=(
                    f"{command.source_ref}:{command.semantic_evidence_kind.value}"
                ),
                confidence=command.confidence,
                payload_sha256=command.payload_sha256,
                details={
                    "role": "semantic_support",
                    **command.semantic_evidence_details,
                },
            )
            semantic_evidence_ids = (semantic_evidence.evidence_id,)
        event_evidence = (
            observation.evidence_id,
            translation.evidence_id,
            *semantic_evidence_ids,
        )

        concept_ids: list[str] = []
        for label in command.concept_labels:
            concept = self.ensure_concept(label, evidence_refs=event_evidence)
            concept_ids.append(concept.concept_id)
        for proposal in command.concept_proposals:
            concept = self.ensure_concept(
                proposal.label,
                evidence_refs=event_evidence,
                attributes=proposal.attributes,
            )
            concept_ids.append(concept.concept_id)

        relation_ids: list[str] = []
        for proposal in command.relation_proposals:
            source = self.ensure_concept(
                proposal.source_label,
                evidence_refs=event_evidence,
            )
            target = self.ensure_concept(
                proposal.target_label,
                evidence_refs=event_evidence,
            )
            relation = self.propose_relation(
                source.concept_id,
                target.concept_id,
                proposal.relation_type,
                evidence_refs=event_evidence,
                directed=proposal.directed,
                weight=proposal.weight,
                confidence=proposal.confidence,
                status=proposal.status,
            )
            relation_ids.append(relation.relation_id)

        claim_ids: list[str] = []
        contradiction_ids: list[str] = []
        revision_ids: list[str] = []
        if command.claim_proposals and not semantic_evidence_ids:
            raise EvidenceGateError(
                "Canonical claims require explicit semantic evidence, not translation alone."
            )
        for proposal in command.claim_proposals:
            update = self.register_claim(
                proposal,
                evidence_refs=semantic_evidence_ids,
            )
            claim_ids.append(update[0].claim_id)
            if update[1] is not None:
                contradiction_ids.append(update[1].contradiction_id)
            if update[2] is not None:
                revision_ids.append(update[2].revision_id)

        bound_concept_ids = set(concept_ids)
        for relation_id in relation_ids:
            relation = self.state.relations[relation_id]
            bound_concept_ids.add(relation.source_concept_id)
            bound_concept_ids.add(relation.target_concept_id)
        for claim_id in claim_ids:
            claim = self.state.claims[claim_id]
            bound_concept_ids.add(claim.subject_concept_id)
            bound_concept_ids.add(claim.object_concept_id)
        self._apply_field_effect(
            command.feature_vector,
            command.modality,
            caused_by_refs=event_evidence,
            bound_concept_ids=tuple(sorted(bound_concept_ids)),
        )
        self.state.processed_event_keys[command.event_key] = command_hash

        output_fingerprint = self.semantic_fingerprint()
        transition = TransitionRecord(
            transition_id=stable_id(
                "transition",
                self.state.identity.kernel_id,
                self.state.event_sequence,
                command_hash,
            ),
            sequence=self.state.event_sequence,
            cycle=cycle,
            operation="apply_experience",
            command_hash=command_hash,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            input_refs=(command.source_ref,),
            output_refs=tuple(
                [*event_evidence, *sorted(set(concept_ids)), *sorted(set(relation_ids)), *sorted(set(claim_ids)), *sorted(set(contradiction_ids)), *sorted(set(revision_ids))]
            ),
        )
        self.state.transitions.append(transition)
        self._validate_state()
        return ExperienceResult(
            event_key=command.event_key,
            cycle=cycle,
            observation_evidence_id=observation.evidence_id,
            translation_evidence_id=translation.evidence_id,
            concept_ids=tuple(concept_ids),
            relation_ids=tuple(relation_ids),
            claim_ids=tuple(claim_ids),
            contradiction_ids=tuple(contradiction_ids),
            revision_ids=tuple(revision_ids),
            transition_id=transition.transition_id,
            additional_evidence_ids=semantic_evidence_ids,
        )

    def ensure_concept(
        self,
        label: str,
        *,
        evidence_refs: Iterable[str],
        attributes: dict[str, object] | None = None,
    ) -> ConceptRecord:
        evidence = self._validated_evidence_refs(evidence_refs)
        normalized = normalize_label(label)
        concept_id = stable_id("concept", normalized)
        existing = self.state.concepts.get(concept_id)
        if existing is not None:
            merged_evidence = tuple(sorted(set(existing.evidence_refs) | set(evidence)))
            merged_attributes = {**existing.attributes, **(attributes or {})}
            if (
                merged_evidence != existing.evidence_refs
                or merged_attributes != existing.attributes
            ):
                existing = existing.model_copy(
                    update={
                        "evidence_refs": merged_evidence,
                        "attributes": merged_attributes,
                    }
                )
                self.state.concepts[concept_id] = existing
            self._ensure_field_address(existing.concept_id)
            self._catalog_concept_in_shards(existing.concept_id, attach_active=False)
            return existing
        concept = ConceptRecord(
            concept_id=concept_id,
            label=label.strip(),
            normalized_label=normalized,
            created_cycle=self.state.cycle,
            evidence_refs=evidence,
            attributes=attributes or {},
        )
        self.state.concepts[concept_id] = concept
        self._ensure_field_address(concept_id)
        self._catalog_concept_in_shards(concept_id, attach_active=True)
        return concept

    def propose_relation(
        self,
        source_concept_id: str,
        target_concept_id: str,
        relation_type: str,
        *,
        evidence_refs: Iterable[str],
        directed: bool = True,
        weight: float = 0.5,
        confidence: float = 0.5,
        status: RelationStatus = RelationStatus.SUPPORTED,
    ) -> RelationRecord:
        evidence = self._validated_evidence_refs(evidence_refs)
        if source_concept_id not in self.state.concepts:
            raise KeyError(f"Unknown source concept '{source_concept_id}'.")
        if target_concept_id not in self.state.concepts:
            raise KeyError(f"Unknown target concept '{target_concept_id}'.")
        if source_concept_id == target_concept_id:
            raise KernelInvariantError("Self-relations require an explicit future policy.")
        relation_type = relation_type.strip()
        if not relation_type:
            raise ValueError("relation_type cannot be empty.")
        if not (0.0 <= weight <= 1.0 and 0.0 <= confidence <= 1.0):
            raise ValueError("weight and confidence must be between 0 and 1.")

        canonical_source = source_concept_id
        canonical_target = target_concept_id
        if not directed and canonical_target < canonical_source:
            canonical_source, canonical_target = canonical_target, canonical_source
        relation_id = stable_id(
            "relation",
            canonical_source,
            canonical_target,
            relation_type,
            directed,
        )
        existing = self.state.relations.get(relation_id)
        if existing is not None:
            updated = existing.model_copy(
                update={
                    "evidence_refs": tuple(
                        sorted(set(existing.evidence_refs) | set(evidence))
                    ),
                    "weight": max(existing.weight, weight),
                    "confidence": max(existing.confidence, confidence),
                    "updated_cycle": self.state.cycle,
                    "status": status,
                }
            )
            self.state.relations[relation_id] = updated
            self._catalog_relation_in_shards(relation_id, attach_active=False)
            return updated

        relation = RelationRecord(
            relation_id=relation_id,
            source_concept_id=canonical_source,
            target_concept_id=canonical_target,
            relation_type=relation_type,
            directed=directed,
            weight=weight,
            confidence=confidence,
            evidence_refs=evidence,
            created_cycle=self.state.cycle,
            updated_cycle=self.state.cycle,
            status=status,
        )
        self.state.relations[relation_id] = relation
        self._catalog_relation_in_shards(relation_id, attach_active=True)
        return relation

    def register_claim(
        self,
        proposal: ClaimProposal,
        *,
        evidence_refs: Iterable[str],
    ) -> tuple[ClaimRecord, ContradictionRecord | None, RevisionRecord | None]:
        evidence = self._validated_evidence_refs(evidence_refs)
        subject = self.ensure_concept(proposal.subject_label, evidence_refs=evidence)
        object_concept = self.ensure_concept(proposal.object_label, evidence_refs=evidence)
        predicate = normalize_label(proposal.predicate)
        claim_key = stable_id(
            "claimkey", subject.concept_id, predicate, object_concept.concept_id
        )
        claim_id = stable_id("claim", claim_key, proposal.polarity.value)
        previous_belief = self.current_belief_by_key(claim_key)
        source_weight = self.state.epistemic_policy.source_weights[
            proposal.source_class.value
        ]
        entries: list[ClaimEvidenceEntry] = []
        for evidence_id in evidence:
            record = self.state.evidence[evidence_id]
            confidence = min(proposal.confidence, record.confidence)
            entries.append(
                ClaimEvidenceEntry(
                    evidence_id=evidence_id,
                    source_class=proposal.source_class,
                    stance=EvidenceStance.SUPPORT,
                    confidence=confidence,
                    source_weight=source_weight,
                    effective_weight=source_weight * confidence,
                    cycle=self.state.cycle,
                    rationale=proposal.rationale,
                )
            )
        existing = self.state.claims.get(claim_id)
        if existing is None:
            existing = ClaimRecord(
                claim_id=claim_id,
                claim_key=claim_key,
                subject_concept_id=subject.concept_id,
                predicate=predicate,
                object_concept_id=object_concept.concept_id,
                polarity=proposal.polarity,
                created_cycle=self.state.cycle,
                updated_cycle=self.state.cycle,
                attributes=proposal.attributes,
            )
        merged_support = {entry.evidence_id: entry for entry in existing.support_ledger}
        for entry in entries:
            merged_support[entry.evidence_id] = entry
        existing = existing.model_copy(
            update={
                "support_ledger": tuple(
                    merged_support[key] for key in sorted(merged_support)
                ),
                "updated_cycle": self.state.cycle,
                "attributes": {**existing.attributes, **proposal.attributes},
            }
        )
        self.state.claims[claim_id] = existing
        contradiction = self._refresh_claim_pair(claim_key)
        current = self.current_belief_by_key(claim_key)
        revision: RevisionRecord | None = None
        if (
            previous_belief is not None
            and current is not None
            and previous_belief.claim_id != current.claim_id
            and contradiction is not None
        ):
            all_evidence = tuple(sorted({
                entry.evidence_id
                for claim in self._claims_for_key(claim_key)
                for entry in (*claim.support_ledger, *claim.refutation_ledger)
            }))
            revision = RevisionRecord(
                revision_id=stable_id(
                    "revision", contradiction.contradiction_id, previous_belief.claim_id,
                    current.claim_id, self.state.cycle, all_evidence
                ),
                contradiction_id=contradiction.contradiction_id,
                prior_claim_id=previous_belief.claim_id,
                revised_to_claim_id=current.claim_id,
                cycle=self.state.cycle,
                reason=(
                    "Current belief changed because weighted evidence crossed the "
                    "configured contradiction-resolution margin."
                ),
                evidence_refs=all_evidence,
                policy_snapshot=self.state.epistemic_policy.model_dump(mode="json"),
            )
            if not any(item.revision_id == revision.revision_id for item in self.state.revisions):
                self.state.revisions.append(revision)
            contradiction = contradiction.model_copy(
                update={"latest_revision_id": revision.revision_id}
            )
            self.state.contradictions[contradiction.contradiction_id] = contradiction
            prior = self.state.claims[previous_belief.claim_id]
            self.state.claims[prior.claim_id] = prior.model_copy(
                update={
                    "status": ClaimStatus.REVISED,
                    "superseded_by_claim_id": current.claim_id,
                }
            )
        return self.state.claims[claim_id], contradiction, revision

    def current_belief(
        self,
        subject_label: str,
        predicate: str,
        object_label: str,
    ) -> ClaimRecord | None:
        subject_id = stable_id("concept", normalize_label(subject_label))
        object_id = stable_id("concept", normalize_label(object_label))
        key = stable_id("claimkey", subject_id, normalize_label(predicate), object_id)
        return self.current_belief_by_key(key)

    def current_belief_by_key(self, claim_key: str) -> ClaimRecord | None:
        claims = self._claims_for_key(claim_key)
        if not claims:
            return None
        if len(claims) == 1:
            return claims[0] if claims[0].net_score >= 0 else None
        contradiction = next(
            (item for item in self.state.contradictions.values() if item.claim_key == claim_key),
            None,
        )
        if contradiction is None or contradiction.preferred_claim_id is None:
            return None
        return self.state.claims[contradiction.preferred_claim_id]

    def claim_history(
        self,
        subject_label: str,
        predicate: str,
        object_label: str,
    ) -> tuple[ClaimRecord, ...]:
        subject_id = stable_id("concept", normalize_label(subject_label))
        object_id = stable_id("concept", normalize_label(object_label))
        key = stable_id("claimkey", subject_id, normalize_label(predicate), object_id)
        return self._claims_for_key(key)

    def _claims_for_key(self, claim_key: str) -> tuple[ClaimRecord, ...]:
        return tuple(sorted(
            (claim for claim in self.state.claims.values() if claim.claim_key == claim_key),
            key=lambda item: item.polarity.value,
        ))

    @staticmethod
    def _saturating_score(entries: Iterable[ClaimEvidenceEntry]) -> float:
        remaining = 1.0
        for entry in entries:
            remaining *= 1.0 - entry.effective_weight
        return max(0.0, min(1.0, 1.0 - remaining))

    def _refresh_claim_pair(self, claim_key: str) -> ContradictionRecord | None:
        claims = {claim.polarity: claim for claim in self._claims_for_key(claim_key)}
        for polarity, claim in list(claims.items()):
            opposite = (
                ClaimPolarity.NEGATED
                if polarity == ClaimPolarity.AFFIRMED
                else ClaimPolarity.AFFIRMED
            )
            opposing = claims.get(opposite)
            refutations = ()
            if opposing is not None:
                refutations = tuple(
                    entry.model_copy(update={"stance": EvidenceStance.REFUTE})
                    for entry in opposing.support_ledger
                )
            support_score = self._saturating_score(claim.support_ledger)
            refutation_score = self._saturating_score(refutations)
            net_score = support_score - refutation_score
            status = (
                ClaimStatus.CONFIRMED
                if support_score >= self.state.epistemic_policy.confirmation_threshold
                else ClaimStatus.SUPPORTED
            )
            updated = claim.model_copy(
                update={
                    "refutation_ledger": refutations,
                    "support_score": support_score,
                    "refutation_score": refutation_score,
                    "net_score": net_score,
                    "status": status,
                    "updated_cycle": self.state.cycle,
                }
            )
            self.state.claims[claim.claim_id] = updated
            claims[polarity] = updated

        if len(claims) < 2:
            return None
        affirmed = claims[ClaimPolarity.AFFIRMED]
        negated = claims[ClaimPolarity.NEGATED]
        difference = affirmed.net_score - negated.net_score
        preferred: str | None = None
        if (
            abs(difference) >= self.state.epistemic_policy.resolution_margin
            and max(affirmed.net_score, negated.net_score)
            >= self.state.epistemic_policy.minimum_preference_score
        ):
            preferred = affirmed.claim_id if difference > 0 else negated.claim_id
        for claim in (affirmed, negated):
            if preferred is None:
                status = ClaimStatus.CONTESTED
            elif claim.claim_id == preferred:
                status = ClaimStatus.CONFIRMED
            else:
                status = ClaimStatus.REJECTED
            self.state.claims[claim.claim_id] = claim.model_copy(update={"status": status})

        contradiction_id = stable_id("contradiction", claim_key)
        existing = self.state.contradictions.get(contradiction_id)
        evidence_refs = tuple(sorted({
            entry.evidence_id
            for claim in (affirmed, negated)
            for entry in claim.support_ledger
        }))
        contradiction = ContradictionRecord(
            contradiction_id=contradiction_id,
            claim_key=claim_key,
            claim_ids=tuple(sorted((affirmed.claim_id, negated.claim_id))),
            detected_cycle=(existing.detected_cycle if existing else self.state.cycle),
            updated_cycle=self.state.cycle,
            status=(
                ContradictionStatus.WEIGHTED
                if preferred is not None
                else ContradictionStatus.ACTIVE
            ),
            preferred_claim_id=preferred,
            evidence_refs=evidence_refs,
            latest_revision_id=(existing.latest_revision_id if existing else None),
        )
        self.state.contradictions[contradiction_id] = contradiction
        return contradiction

    def register_sensory_archive(
        self,
        record: SensoryArchiveRecord,
    ) -> SensoryArchiveRecord:
        """Register a deterministic raw-payload archive before sample ingestion."""

        try:
            record = SensoryArchiveRecord.model_validate(record.model_dump(mode="json"))
        except ValueError as exc:
            raise SensoryIntegrityError("Sensory archive record is invalid.") from exc
        existing = self.state.sensory_archives.get(record.archive_id)
        if existing is not None:
            if existing != record:
                raise SensoryIntegrityError("Sensory archive ID was reused with different content.")
            return existing.model_copy(deep=True)
        duplicate_batch = next(
            (
                item
                for item in self.state.sensory_archives.values()
                if item.batch_key == record.batch_key
            ),
            None,
        )
        if duplicate_batch is not None:
            raise SensoryIntegrityError("Sensory batch key has already been registered.")
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        committed = record.model_copy(update={"created_cycle": self.state.cycle})
        committed = SensoryArchiveRecord.model_validate(committed.model_dump(mode="json"))
        self.state.sensory_archives[committed.archive_id] = committed
        command_hash = hashlib.sha256(
            canonical_json_bytes(committed.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "register_sensory_archive",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="register_sensory_archive",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(committed.archive_id,),
                output_refs=(committed.archive_id,),
            )
        )
        self._validate_state()
        return committed.model_copy(deep=True)

    def commit_sensory_sample(
        self,
        record: SensorySampleRecord,
    ) -> SensorySampleRecord:
        """Commit one native sample after its evidence and translation exist."""

        try:
            record = SensorySampleRecord.model_validate(record.model_dump(mode="json"))
        except ValueError as exc:
            raise SensoryIntegrityError("Sensory sample record is invalid.") from exc
        archive = self.state.sensory_archives.get(record.archive_id)
        if archive is None:
            raise SensoryIntegrityError("Sensory sample references an unregistered archive.")
        if record.sample_id not in archive.sample_ids:
            raise SensoryIntegrityError("Sensory sample is absent from its archive manifest.")
        if record.sample_id in self.state.sensory_samples:
            existing = self.state.sensory_samples[record.sample_id]
            if existing != record:
                raise SensoryIntegrityError("Sensory sample ID was reused with different content.")
            return existing.model_copy(deep=True)
        observation = self.state.evidence.get(record.observation_evidence_id)
        translation = self.state.evidence.get(record.translation_evidence_id)
        if observation is None or translation is None:
            raise SensoryIntegrityError("Sensory sample evidence is missing.")
        if observation.kind != EvidenceKind.OBSERVATION:
            raise SensoryIntegrityError("Sensory native evidence must be an observation.")
        if translation.kind != EvidenceKind.TRANSLATION:
            raise SensoryIntegrityError("Sensory derived evidence must be a translation.")
        if observation.payload_sha256 != record.payload_sha256:
            raise SensoryIntegrityError("Sensory native evidence payload digest drift detected.")
        prior_stream = sorted(
            (
                item
                for item in self.state.sensory_samples.values()
                if item.stream_id == record.stream_id
            ),
            key=lambda item: (item.sequence_number, item.sample_id),
        )
        if prior_stream:
            previous = prior_stream[-1]
            if record.sequence_number <= previous.sequence_number:
                raise SensoryIntegrityError("Sensory stream sequence must advance monotonically.")
            if record.timestamp_ns < previous.timestamp_ns:
                raise SensoryIntegrityError("Sensory stream timestamps cannot move backward.")
            if record.previous_sample_id != previous.sample_id:
                raise SensoryIntegrityError("Sensory previous-sample lineage is incorrect.")
        elif record.previous_sample_id is not None:
            raise SensoryIntegrityError("First sensory stream sample cannot name a predecessor.")
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        committed = record.model_copy(update={"committed_cycle": self.state.cycle})
        committed = SensorySampleRecord.model_validate(committed.model_dump(mode="json"))
        self.state.sensory_samples[committed.sample_id] = committed
        command_hash = hashlib.sha256(
            canonical_json_bytes(committed.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_sensory_sample",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_sensory_sample",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(
                    committed.archive_id,
                    committed.observation_evidence_id,
                    committed.translation_evidence_id,
                ),
                output_refs=(committed.sample_id,),
            )
        )
        self._validate_state()
        return committed.model_copy(deep=True)

    def validate_temporal_event_report(
        self,
        report: TemporalEventAssemblyReport,
    ) -> None:
        try:
            report = TemporalEventAssemblyReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise SensoryIntegrityError("Temporal event report is invalid.") from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise SensoryIntegrityError("Temporal event report belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise SensoryStaleError("Temporal event report cycle is stale.")
        if report.structural_fingerprint != self.sensory_structural_fingerprint():
            raise SensoryStaleError("Temporal event report was computed against different sensory state.")
        if report.policy_revision != self.state.sensory_policy.revision:
            raise SensoryStaleError("Sensory policy changed after event inspection.")
        if any(sample_id not in self.state.sensory_samples for sample_id in report.sample_ids):
            raise SensoryIntegrityError("Temporal event report references unknown samples.")
        already_assigned = {
            sample_id
            for event in self.state.temporal_events.values()
            for sample_id in event.sample_ids
        }
        if already_assigned.intersection(report.sample_ids):
            raise SensoryIntegrityError("A sensory sample cannot be assigned to two temporal events.")
        report_sample_set = set(report.sample_ids)
        group_ids = {group.group_id for group in report.synchronization_groups}
        if len(group_ids) != len(report.synchronization_groups):
            raise SensoryIntegrityError("Duplicate synchronization groups in report.")
        for group in report.synchronization_groups:
            if not set(group.sample_ids).issubset(report_sample_set):
                raise SensoryIntegrityError("Synchronization group includes samples outside report.")
            self._validated_evidence_refs(group.evidence_refs)
        event_sample_union: set[str] = set()
        event_group_union: set[str] = set()
        for event in report.proposed_events:
            if event.committed_cycle != self.state.cycle + 1:
                raise SensoryIntegrityError("Proposed temporal event commit cycle drift.")
            if not set(event.sample_ids).issubset(report_sample_set):
                raise SensoryIntegrityError("Temporal event includes samples outside report.")
            if not set(event.synchronization_group_ids).issubset(group_ids):
                raise SensoryIntegrityError("Temporal event includes unknown synchronization groups.")
            self._validated_evidence_refs(event.evidence_refs)
            if event_sample_union.intersection(event.sample_ids):
                raise SensoryIntegrityError("Temporal events overlap in sample membership.")
            if event_group_union.intersection(event.synchronization_group_ids):
                raise SensoryIntegrityError("Temporal events overlap in group membership.")
            event_sample_union.update(event.sample_ids)
            event_group_union.update(event.synchronization_group_ids)
        if event_sample_union != report_sample_set:
            raise SensoryIntegrityError("Temporal event report does not account for every sample.")
        if event_group_union != group_ids:
            raise SensoryIntegrityError("Temporal event report does not account for every synchronization group.")

    def commit_temporal_event_report(
        self,
        report: TemporalEventAssemblyReport,
    ) -> TemporalEventAssemblyEvent:
        self.validate_temporal_event_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        for group in report.synchronization_groups:
            self.state.synchronization_groups[group.group_id] = group
        committed_events: list[TemporalEventRecord] = []
        for event in report.proposed_events:
            committed = event.model_copy(update={"committed_cycle": self.state.cycle})
            committed = TemporalEventRecord.model_validate(committed.model_dump(mode="json"))
            self.state.temporal_events[committed.event_id] = committed
            committed_events.append(committed)
        event_ids = tuple(sorted(item.event_id for item in committed_events))
        group_ids = tuple(sorted(item.group_id for item in report.synchronization_groups))
        assembly_id = stable_id(
            "temporal_event_assembly",
            report.report_id,
            event_ids,
            group_ids,
            self.state.cycle,
        )
        assembly = TemporalEventAssemblyEvent(
            assembly_event_id=assembly_id,
            report=report,
            committed_event_ids=event_ids,
            committed_group_ids=group_ids,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.temporal_event_assembly_events.append(assembly)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_temporal_event_report",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_temporal_event_report",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, *report.sample_ids),
                output_refs=(assembly_id, *event_ids, *group_ids),
            )
        )
        self._validate_state()
        return assembly

    def update_sensory_policy(self, **changes: object) -> SensoryPolicy:
        next_policy = self.state.sensory_policy.model_copy(
            update={
                **changes,
                "revision": self.state.sensory_policy.revision + 1,
            }
        )
        self.state.sensory_policy = SensoryPolicy.model_validate(
            next_policy.model_dump(mode="json")
        )
        return self.state.sensory_policy.model_copy(deep=True)

    def validate_workspace_report(self, report: WorkspaceAdmissionReport) -> None:
        try:
            report = WorkspaceAdmissionReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise WorkspaceIntegrityError(
                "Workspace report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise WorkspaceIntegrityError("Workspace report belongs to another kernel.")
        if report.structural_fingerprint != self.workspace_structural_fingerprint():
            raise WorkspaceStaleError(
                "Workspace report was computed against different active state."
            )
        if report.policy_revision != self.state.workspace_policy.revision:
            raise WorkspaceStaleError("Workspace policy changed after inspection.")
        if report.resource_budget != self.state.workspace_policy.resource_budget:
            raise WorkspaceIntegrityError("Workspace budget drift detected.")
        if report.total_allocated_resource > report.resource_budget + 1e-9:
            raise WorkspaceIntegrityError("Workspace report exceeds its resource budget.")
        admitted = {
            item.candidate_id
            for item in report.assessments
            if item.disposition == WorkspaceDisposition.ADMIT
        }
        suppressed = {
            item.candidate_id
            for item in report.assessments
            if item.disposition != WorkspaceDisposition.ADMIT
        }
        if admitted != set(report.admitted_candidate_ids):
            raise WorkspaceIntegrityError("Workspace admitted-candidate index drift.")
        if suppressed != set(report.suppressed_candidate_ids):
            raise WorkspaceIntegrityError("Workspace suppressed-candidate index drift.")
        if len(admitted) > self.state.workspace_policy.max_active_items:
            raise WorkspaceIntegrityError("Workspace report exceeds its slot bound.")
        for item in report.assessments:
            self._validated_evidence_refs(item.candidate.evidence_refs)
            if item.candidate.persistence_cycles > self.state.workspace_policy.maximum_persistence_cycles:
                raise WorkspaceIntegrityError("Workspace persistence request exceeds policy.")
            if item.disposition == WorkspaceDisposition.ADMIT and item.allocated_resource <= 0.0:
                raise WorkspaceIntegrityError("Admitted workspace items require resources.")
            if item.disposition != WorkspaceDisposition.ADMIT and item.allocated_resource != 0.0:
                raise WorkspaceIntegrityError("Suppressed workspace items cannot hold resources.")
        missing_evictions = set(report.evicted_item_ids) - set(self.state.workspace_items)
        if missing_evictions:
            raise WorkspaceIntegrityError("Workspace report evicts unknown active items.")

    def validate_plasticity_report(self, report: PlasticityReport) -> None:
        try:
            report = PlasticityReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise PlasticityIntegrityError(
                "Plasticity report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise PlasticityIntegrityError("Plasticity report belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise PlasticityStaleError("Plasticity report cycle is stale.")
        if report.structural_fingerprint != self.plasticity_structural_fingerprint():
            raise PlasticityStaleError(
                "Plasticity report was computed against different active state."
            )
        if report.policy_revision != self.state.plasticity_policy.revision:
            raise PlasticityStaleError("Plasticity policy changed after inspection.")
        if not self.state.workspace_cycle_events:
            raise PlasticityIntegrityError("Plasticity requires a committed workspace cycle.")
        latest_workspace = self.state.workspace_cycle_events[-1]
        if latest_workspace.event_id != report.workspace_event_id:
            raise PlasticityStaleError(
                "Plasticity report does not reference the latest workspace event."
            )
        proposed = {item.association_id: item for item in report.proposed_associations}
        if len(proposed) != len(report.proposed_associations):
            raise PlasticityIntegrityError("Plasticity report contains duplicate associations.")
        degree: dict[str, int] = {}
        for association in proposed.values():
            a, b = association.concept_ids
            if a not in self.state.concepts or b not in self.state.concepts:
                raise PlasticityIntegrityError(
                    "Plasticity association references a missing concept."
                )
            self._validated_evidence_refs(association.evidence_refs)
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        max_degree = max(degree.values(), default=0)
        if max_degree != report.max_degree_after:
            raise PlasticityIntegrityError("Plasticity max-degree diagnostic drift detected.")
        if max_degree > self.state.plasticity_policy.max_degree:
            raise PlasticityIntegrityError("Plasticity report exceeds the degree cap.")
        if len(proposed) != report.edge_count_after:
            raise PlasticityIntegrityError("Plasticity edge-count diagnostic drift detected.")
        concept_count = max(1, len(self.state.concepts))
        ratio = len(proposed) / concept_count
        if abs(ratio - report.edge_ratio_after) > 1e-9:
            raise PlasticityIntegrityError("Plasticity edge-ratio diagnostic drift detected.")
        if ratio > self.state.plasticity_policy.max_edge_ratio + 1e-9:
            raise PlasticityIntegrityError("Plasticity report exceeds the edge-ratio cap.")
        if report.edge_count_before != len(self.state.plasticity_associations):
            raise PlasticityStaleError("Plasticity association count changed after inspection.")

    def commit_plasticity_report(self, report: PlasticityReport) -> PlasticityEvent:
        self.validate_plasticity_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        self.state.plasticity_associations = {
            item.association_id: item for item in report.proposed_associations
        }
        active_ids = tuple(sorted(self.state.plasticity_associations))
        event_id = stable_id(
            "plasticity_event",
            report.report_id,
            active_ids,
            self.state.cycle,
        )
        event = PlasticityEvent(
            event_id=event_id,
            report=report,
            active_association_ids=active_ids,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.plasticity_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_local_plasticity",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_local_plasticity",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, report.workspace_event_id),
                output_refs=(event_id, *active_ids),
            )
        )
        self._validate_state()
        return event

    def validate_structure_observation_report(
        self,
        report: StructureObservationReport,
    ) -> None:
        try:
            report = StructureObservationReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise StructureIntegrityError(
                "Structure observation report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise StructureIntegrityError("Structure report belongs to another kernel.")
        if report.cycle != self.state.cycle:
            raise StructureStaleError("Structure observation report cycle is stale.")
        if report.structural_fingerprint != self.structure_structural_fingerprint():
            raise StructureStaleError(
                "Structure report was computed against different active state."
            )
        if report.policy_revision != self.state.structure_policy.revision:
            raise StructureStaleError("Structure policy changed after inspection.")
        if not self.state.plasticity_events:
            raise StructureIntegrityError("Structure observation requires plasticity history.")
        if self.state.plasticity_events[-1].event_id != report.plasticity_event_id:
            raise StructureStaleError(
                "Structure report does not reference the latest plasticity event."
            )
        for candidate in report.proposed_candidates:
            if any(item not in self.state.concepts for item in candidate.member_concept_ids):
                raise StructureIntegrityError(
                    "Structure candidate references a missing concept."
                )
            if any(item not in self.state.relations for item in candidate.member_relation_ids):
                raise StructureIntegrityError(
                    "Structure candidate references a missing canonical relation."
                )
            if any(
                item not in self.state.plasticity_associations
                for item in candidate.internal_association_ids
            ):
                raise StructureIntegrityError(
                    "Structure candidate references a missing internal association."
                )
            if any(
                item not in self.state.plasticity_associations
                for item in candidate.boundary_association_ids
            ):
                raise StructureIntegrityError(
                    "Structure candidate references a missing boundary association."
                )
            self._validated_evidence_refs(candidate.evidence_refs)
            if candidate.field_state_dim not in {0, self.state.field.state_dim}:
                raise StructureIntegrityError("Structure field prototype dimension drift.")

    def commit_structure_observation(
        self,
        report: StructureObservationReport,
    ) -> StructureObservationEvent:
        self.validate_structure_observation_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        for candidate in report.proposed_candidates:
            self.state.structure_candidates[candidate.candidate_id] = candidate
        active_ids = tuple(sorted(self.state.structure_candidates))
        event_id = stable_id(
            "structure_observation_event",
            report.report_id,
            active_ids,
            self.state.cycle,
        )
        event = StructureObservationEvent(
            event_id=event_id,
            report=report,
            active_candidate_ids=active_ids,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.structure_observation_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_structure_observation",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_structure_observation",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, report.plasticity_event_id),
                output_refs=(event_id, *report.observed_candidate_ids),
            )
        )
        self._validate_state()
        return event

    def validate_structure_promotion_report(
        self,
        report: StructurePromotionReport,
    ) -> None:
        try:
            report = StructurePromotionReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise StructureIntegrityError(
                "Structure promotion report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise StructureIntegrityError("Structure promotion belongs to another kernel.")
        if report.structural_fingerprint != self.structure_structural_fingerprint():
            raise StructureStaleError(
                "Structure promotion report was computed against different state."
            )
        if report.policy_revision != self.state.structure_policy.revision:
            raise StructureStaleError("Structure policy changed after promotion inspection.")
        candidate = self.state.structure_candidates.get(report.candidate_id)
        if candidate is None:
            raise StructureIntegrityError("Structure promotion references a missing candidate.")
        if candidate != report.candidate_snapshot:
            raise StructureStaleError("Structure candidate changed after promotion inspection.")
        if candidate.status == StructureCandidateStatus.PROMOTED:
            raise StructureIntegrityError("Structure candidate is already promoted.")
        self._validated_evidence_refs(report.evidence_refs)
        if report.evidence_refs != candidate.evidence_refs:
            raise StructureIntegrityError(
                "Structure promotion must preserve the candidate evidence path."
            )
        expected_structure_id = stable_id("structure", candidate.candidate_id)
        if report.proposed_structure_id != expected_structure_id:
            raise StructureIntegrityError("Proposed structure identity drift detected.")

    def commit_structure_promotion(
        self,
        report: StructurePromotionReport,
        *,
        council_decision_event_id: str,
    ) -> StructurePromotionEvent:
        self.validate_structure_promotion_report(report)
        if report.disposition != StructurePromotionDisposition.PROMOTE:
            raise StructureIntegrityError("Only an eligible structure can be promoted.")
        if report.rejection_codes:
            raise StructureIntegrityError("Structure promotion still contains failed gates.")
        try:
            self.assert_operation_authorized(council_decision_event_id, report.operation)
        except GovernanceAuthorizationError as exc:
            raise StructureAuthorizationError(
                "Council did not authorize earned-structure promotion."
            ) from exc

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        candidate = self.state.structure_candidates[report.candidate_id]
        record = StructureRecord(
            structure_id=report.proposed_structure_id,
            source_candidate_id=candidate.candidate_id,
            opaque_name=report.proposed_opaque_name,
            member_concept_ids=candidate.member_concept_ids,
            member_relation_ids=candidate.member_relation_ids,
            internal_association_ids=candidate.internal_association_ids,
            internal_edge_snapshots=tuple(
                StructureEdgeSnapshot(
                    association_id=association_id,
                    concept_ids=self.state.plasticity_associations[association_id].concept_ids,
                    strength=self.state.plasticity_associations[association_id].strength,
                )
                for association_id in candidate.internal_association_ids
                if association_id in self.state.plasticity_associations
            ),
            evidence_refs=candidate.evidence_refs,
            quality_at_promotion=candidate.quality,
            field_state_dim=candidate.field_state_dim,
            field_prototype_real=candidate.field_prototype_real,
            field_prototype_imag=candidate.field_prototype_imag,
            field_prototype_sha256=candidate.field_prototype_sha256,
            created_cycle=self.state.cycle,
            council_decision_event_id=council_decision_event_id,
            promotion_policy_revision=report.policy_revision,
            semantic_label_preinstalled=False,
        )
        self.state.structures[record.structure_id] = record
        updated = candidate.model_copy(
            update={
                "status": StructureCandidateStatus.PROMOTED,
                "updated_cycle": self.state.cycle,
                "promoted_structure_id": record.structure_id,
            }
        )
        self.state.structure_candidates[candidate.candidate_id] = (
            StructureCandidateRecord.model_validate(updated.model_dump(mode="json"))
        )
        event_id = stable_id(
            "structure_promotion_event",
            report.report_id,
            council_decision_event_id,
            record.structure_id,
            self.state.cycle,
        )
        event = StructurePromotionEvent(
            event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            structure_id=record.structure_id,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.structure_promotion_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "council_decision_event_id": council_decision_event_id,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_structure_promotion",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_structure_promotion",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(
                    report.report_id,
                    council_decision_event_id,
                    candidate.candidate_id,
                ),
                output_refs=(event_id, record.structure_id),
            )
        )
        self._validate_state()
        return event

    def refolding_structural_fingerprint(self) -> str:
        """Fingerprint immutable fold bodies, challenges, and availability for M18."""

        payload = {
            "kernel_id": self.state.identity.kernel_id,
            "structures": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structures.items())
            },
            "ablated_structure_ids": self.state.ablated_structure_ids,
            "structural_challenges": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.structural_challenges.items())
            },
            "structure_refold_events": [
                item.model_dump(mode="json") for item in self.state.structure_refold_events
            ],
            "refolding_policy": self.state.refolding_policy.model_dump(mode="json"),
            "evidence": {
                key: value.model_dump(mode="json")
                for key, value in sorted(self.state.evidence.items())
            },
        }
        return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()

    def update_refolding_policy(self, **changes: object):
        updated = self.state.refolding_policy.model_copy(
            update={**changes, "revision": self.state.refolding_policy.revision + 1}
        )
        updated = type(self.state.refolding_policy).model_validate(
            updated.model_dump(mode="json")
        )
        self.state.refolding_policy = updated
        self._validate_state()
        return updated

    def record_structural_challenge(
        self,
        structure_id: str,
        concept_ids: tuple[str, str],
        *,
        evidence_refs: Iterable[str],
        confidence: float,
    ) -> StructuralChallengeRecord:
        if structure_id not in self.state.structures:
            raise RefoldingIntegrityError("Structural challenge references a missing structure.")
        endpoints = tuple(sorted(concept_ids))
        if len(endpoints) != 2 or endpoints[0] == endpoints[1]:
            raise RefoldingIntegrityError("Structural challenge requires two distinct endpoints.")
        structure = self.state.structures[structure_id]
        if not set(endpoints).issubset(set(structure.member_concept_ids)):
            raise RefoldingIntegrityError("Structural challenge endpoints escaped the structure.")
        edge = next(
            (item for item in structure.internal_edge_snapshots if item.concept_ids == endpoints),
            None,
        )
        if edge is None:
            raise RefoldingIntegrityError("Structural challenge must target a frozen internal edge.")
        if not 0.0 <= confidence <= 1.0:
            raise RefoldingIntegrityError("Structural challenge confidence must be in [0,1].")
        evidence = self._validated_evidence_refs(evidence_refs)
        event_keys = {self.state.evidence[item].event_key for item in evidence}
        if len(event_keys) != 1:
            raise RefoldingIntegrityError(
                "One structural challenge observation must come from one evidence event."
            )
        event_key = next(iter(event_keys))
        challenge_id = stable_id("structural_challenge", structure_id, endpoints)
        existing = self.state.structural_challenges.get(challenge_id)
        observations = {
            item.event_key: item for item in (existing.observations if existing else ())
        }
        prior_observation = observations.get(event_key)
        if prior_observation is not None:
            if prior_observation.evidence_refs != evidence or abs(prior_observation.confidence - confidence) > 1e-12:
                raise RefoldingIntegrityError(
                    "Structural challenge event key was reused with different evidence or confidence."
                )
            return existing
        prospective_cycle = self.state.cycle + 1
        observations[event_key] = StructuralChallengeObservation(
            event_key=event_key,
            evidence_refs=evidence,
            confidence=confidence,
            cycle=prospective_cycle,
        )
        ordered = tuple(observations[key] for key in sorted(observations))
        remaining = 1.0
        for item in ordered:
            remaining *= 1.0 - item.confidence
        combined = max(0.0, min(1.0, 1.0 - remaining))
        record = StructuralChallengeRecord(
            challenge_id=challenge_id,
            structure_id=structure_id,
            concept_ids=endpoints,
            observations=ordered,
            combined_confidence=combined,
            created_cycle=(existing.created_cycle if existing else prospective_cycle),
            updated_cycle=prospective_cycle,
        )
        if existing == record:
            return existing
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        self.state.structural_challenges[challenge_id] = record
        command_hash = hashlib.sha256(canonical_json_bytes(record.model_dump(mode="json"))).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "record_structural_challenge",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="record_structural_challenge",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(structure_id, *evidence),
                output_refs=(challenge_id,),
            )
        )
        self._validate_state()
        return record

    def validate_structure_refold_report(self, report: StructureRefoldReport) -> None:
        try:
            report = StructureRefoldReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise RefoldingIntegrityError("Structure refold report failed validation.") from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise RefoldingIntegrityError("Structure refold report belongs to another kernel.")
        # Council authorization advances the canonical cycle. Refolding staleness
        # is therefore keyed to the dedicated structural fingerprint and policy,
        # not the absolute cycle number recorded at pure inspection time.
        if report.structural_fingerprint != self.refolding_structural_fingerprint():
            raise RefoldingStaleError("Structure refold report was computed against different state.")
        if report.policy_revision != self.state.refolding_policy.revision:
            raise RefoldingStaleError("Refolding policy changed after inspection.")
        parent = self.state.structures.get(report.parent_structure_id)
        if parent is None:
            raise RefoldingIntegrityError("Refold report references a missing parent structure.")
        for challenge_id in report.challenge_ids:
            challenge = self.state.structural_challenges.get(challenge_id)
            if challenge is None or challenge.structure_id != parent.structure_id:
                raise RefoldingIntegrityError("Refold report lost structural challenge lineage.")
        if report.evidence_refs:
            self._validated_evidence_refs(report.evidence_refs)
        for proposal in report.proposals:
            if proposal.parent_structure_id != parent.structure_id:
                raise RefoldingIntegrityError("Refold proposal parent drift detected.")
            if any(item not in self.state.concepts for item in proposal.member_concept_ids):
                raise RefoldingIntegrityError("Refold proposal references a missing concept.")
            if any(
                item.association_id not in set(parent.internal_association_ids)
                for item in proposal.internal_edge_snapshots
            ):
                raise RefoldingIntegrityError("Refold proposal invented a non-parent edge.")
            self._validated_evidence_refs(proposal.evidence_refs)

    def commit_structure_refold(
        self,
        report: StructureRefoldReport,
        *,
        council_decision_event_id: str | None = None,
    ) -> StructureRefoldEvent:
        self.validate_structure_refold_report(report)
        actionable = report.disposition in {RefoldDisposition.REVISE, RefoldDisposition.SPLIT}
        if actionable:
            if not report.proposals:
                raise RefoldingIntegrityError("Actionable refolding requires replacement proposals.")
            if council_decision_event_id is None:
                raise RefoldingAuthorizationError("Actionable refolding requires Council authorization.")
            try:
                self.assert_operation_authorized(council_decision_event_id, report.operation)
            except GovernanceAuthorizationError as exc:
                raise RefoldingAuthorizationError("Council did not authorize refolding.") from exc
        elif council_decision_event_id is not None:
            raise RefoldingIntegrityError("Non-actionable refolding must not consume Council authorization.")

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        parent = self.state.structures[report.parent_structure_id]
        produced: list[str] = []
        if actionable:
            root_id = parent.lineage_root_structure_id or parent.structure_id
            for proposal in report.proposals:
                record = StructureRecord(
                    structure_id=proposal.proposed_structure_id,
                    source_candidate_id=parent.source_candidate_id,
                    opaque_name=proposal.proposed_opaque_name,
                    member_concept_ids=proposal.member_concept_ids,
                    member_relation_ids=tuple(
                        sorted(
                            relation_id
                            for relation_id in parent.member_relation_ids
                            if {
                                self.state.relations[relation_id].source_concept_id,
                                self.state.relations[relation_id].target_concept_id,
                            }.issubset(set(proposal.member_concept_ids))
                        )
                    ),
                    internal_association_ids=proposal.internal_association_ids,
                    internal_edge_snapshots=proposal.internal_edge_snapshots,
                    evidence_refs=proposal.evidence_refs,
                    quality_at_promotion=proposal.quality,
                    field_state_dim=proposal.field_state_dim,
                    field_prototype_real=proposal.field_prototype_real,
                    field_prototype_imag=proposal.field_prototype_imag,
                    field_prototype_sha256=proposal.field_prototype_sha256,
                    created_cycle=self.state.cycle,
                    council_decision_event_id=council_decision_event_id,
                    promotion_policy_revision=parent.promotion_policy_revision,
                    lineage_parent_structure_id=parent.structure_id,
                    lineage_root_structure_id=root_id,
                    revision_index=proposal.revision_index,
                    refold_basis_challenge_ids=proposal.refold_basis_challenge_ids,
                    semantic_label_preinstalled=False,
                )
                self.state.structures[record.structure_id] = record
                produced.append(record.structure_id)
            if self.state.refolding_policy.ablate_parent_on_success:
                current = set(self.state.ablated_structure_ids)
                current.add(parent.structure_id)
                self.state.ablated_structure_ids = tuple(sorted(current))

        event_id = stable_id(
            "structure_refold_event",
            report.report_id,
            council_decision_event_id,
            tuple(sorted(produced)),
            actionable and self.state.refolding_policy.ablate_parent_on_success,
            self.state.cycle,
        )
        event = StructureRefoldEvent(
            event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            produced_structure_ids=tuple(sorted(produced)),
            parent_ablated=actionable and self.state.refolding_policy.ablate_parent_on_success,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.structure_refold_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "council_decision_event_id": council_decision_event_id,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_structure_refold",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_structure_refold",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, report.parent_structure_id, *report.challenge_ids),
                output_refs=(event_id, *sorted(produced)),
            )
        )
        self._validate_state()
        return event

    def commit_workspace_cycle(
        self,
        report: WorkspaceAdmissionReport,
    ) -> WorkspaceCycleEvent:
        self.validate_workspace_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        next_items: dict[str, WorkspaceItemRecord] = {}
        assessment_by_id = {item.candidate_id: item for item in report.assessments}
        for candidate_id in report.admitted_candidate_ids:
            assessment = assessment_by_id[candidate_id]
            candidate = assessment.candidate
            prior = None
            if assessment.carried_from_item_id is not None:
                prior = self.state.workspace_items.get(assessment.carried_from_item_id)
            item_id = stable_id(
                "workspace_item",
                self.state.identity.kernel_id,
                candidate.source_kind.value,
                candidate.source_ref,
                candidate.operation,
            )
            admitted_cycle = prior.admitted_cycle if prior is not None else self.state.cycle
            expires_cycle = self.state.cycle + min(
                candidate.persistence_cycles,
                self.state.workspace_policy.maximum_persistence_cycles,
            ) - 1
            record = WorkspaceItemRecord(
                item_id=item_id,
                candidate_id=candidate_id,
                source_kind=candidate.source_kind,
                source_ref=candidate.source_ref,
                label=candidate.label,
                evidence_refs=candidate.evidence_refs,
                operation=candidate.operation,
                binding_refs=candidate.binding_refs,
                allocated_resource=assessment.allocated_resource,
                raw_score=assessment.raw_score,
                effective_score=assessment.effective_score,
                components=assessment.components,
                signals=candidate.signals,
                admitted_cycle=admitted_cycle,
                updated_cycle=self.state.cycle,
                expires_cycle=expires_cycle,
                admission_report_id=report.report_id,
                metadata=candidate.metadata,
            )
            next_items[item_id] = record
        self.state.workspace_items = next_items
        active_ids = tuple(sorted(next_items))
        broadcast_ids = tuple(
            sorted(
                item.item_id
                for item in next_items.values()
                if item.effective_score >= self.state.workspace_policy.broadcast_threshold
            )
        )
        event_id = stable_id(
            "workspace_cycle_event",
            report.report_id,
            active_ids,
            broadcast_ids,
            report.suppressed_candidate_ids,
            report.evicted_item_ids,
            self.state.cycle,
        )
        event = WorkspaceCycleEvent(
            event_id=event_id,
            report=report,
            active_item_ids=active_ids,
            broadcast_item_ids=broadcast_ids,
            suppressed_candidate_ids=report.suppressed_candidate_ids,
            evicted_item_ids=report.evicted_item_ids,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.workspace_cycle_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_workspace_cycle",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_workspace_cycle",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=tuple(
                    sorted(
                        {
                            report.report_id,
                            *(
                                evidence
                                for item in report.assessments
                                for evidence in item.candidate.evidence_refs
                            ),
                        }
                    )
                ),
                output_refs=(event_id, *active_ids),
            )
        )
        self._validate_state()
        return event

    def commit_workspace_writeback(
        self,
        *,
        item_id: str,
        disposition: WorkspaceWritebackDisposition,
        evidence_refs: Iterable[str],
        reason: str,
    ) -> WorkspaceWritebackEvent:
        item = self.state.workspace_items.get(item_id)
        if item is None:
            raise WorkspaceIntegrityError("Workspace writeback references no active item.")
        evidence = self._validated_evidence_refs(evidence_refs)
        if not reason.strip():
            raise WorkspaceIntegrityError("Workspace writeback requires a reason.")
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "workspace_writeback_event",
            item.model_dump(mode="json"),
            disposition.value,
            evidence,
            reason.strip(),
            self.state.cycle,
        )
        event = WorkspaceWritebackEvent(
            event_id=event_id,
            item_snapshot=item,
            disposition=disposition,
            evidence_refs=evidence,
            reason=reason.strip(),
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.workspace_writeback_events.append(event)
        if disposition == WorkspaceWritebackDisposition.RESOLVE:
            del self.state.workspace_items[item_id]
        else:
            refreshed = item.model_copy(
                update={
                    "updated_cycle": self.state.cycle,
                    "expires_cycle": max(item.expires_cycle, self.state.cycle),
                }
            )
            self.state.workspace_items[item_id] = WorkspaceItemRecord.model_validate(
                refreshed.model_dump(mode="json")
            )
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "item_id": item_id,
                    "disposition": disposition.value,
                    "evidence_refs": evidence,
                    "reason": reason.strip(),
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_workspace_writeback",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_workspace_writeback",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(item_id, *evidence),
                output_refs=(event_id,),
            )
        )
        self._validate_state()
        return event

    def set_attention_candidate(
        self,
        *,
        source_ref: str,
        priority: float,
        resource_request: float,
        reason: str,
        evidence_refs: Iterable[str],
    ) -> AttentionCandidate:
        evidence = self._validated_evidence_refs(evidence_refs)
        candidate_id = stable_id("attention", source_ref, reason)
        candidate = AttentionCandidate(
            candidate_id=candidate_id,
            source_ref=source_ref,
            created_cycle=self.state.cycle,
            priority=priority,
            resource_request=resource_request,
            reason=reason,
            evidence_refs=evidence,
        )
        self.state.attention_candidates[candidate_id] = candidate
        return candidate

    def update_governance(
        self,
        *,
        t_g: float | None = None,
        weights: dict[str, float] | None = None,
        enabled_kings: dict[str, bool] | None = None,
        attention_budget: float | None = None,
        forefront_priority_threshold: float | None = None,
        ethics_veto_threshold: float | None = None,
        outcome_learning_rate: float | None = None,
    ) -> GovernanceState:
        current = self.state.governance
        self.state.governance = current.model_copy(
            update={
                "t_g": current.t_g if t_g is None else t_g,
                "weights": current.weights if weights is None else weights,
                "enabled_kings": (
                    current.enabled_kings if enabled_kings is None else enabled_kings
                ),
                "attention_budget": (
                    current.attention_budget
                    if attention_budget is None
                    else attention_budget
                ),
                "forefront_priority_threshold": (
                    current.forefront_priority_threshold
                    if forefront_priority_threshold is None
                    else forefront_priority_threshold
                ),
                "ethics_veto_threshold": (
                    current.ethics_veto_threshold
                    if ethics_veto_threshold is None
                    else ethics_veto_threshold
                ),
                "outcome_learning_rate": (
                    current.outcome_learning_rate
                    if outcome_learning_rate is None
                    else outcome_learning_rate
                ),
                "revision": current.revision + 1,
            },
            deep=True,
        )
        # Revalidate model-copy updates because Pydantic does not validate update payloads.
        self.state.governance = GovernanceState.model_validate(
            self.state.governance.model_dump(mode="json")
        )
        return self.state.governance.model_copy(deep=True)

    def commit_council_decision(self, report: CouncilReport) -> CouncilDecisionEvent:
        """Persist a fully reproduced Council report without changing semantic truth."""

        try:
            report = CouncilReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise GovernanceIntegrityError(
                "Council report failed its identity or content checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise GovernanceIntegrityError(
                "Council report belongs to a different kernel."
            )
        if report.state_fingerprint != self.semantic_fingerprint():
            raise GovernanceStaleError(
                "Council report was computed against a different canonical state."
            )
        if report.governance_fingerprint != self.governance_fingerprint():
            raise GovernanceStaleError(
                "Council report was computed against a different governance policy."
            )
        self._validate_council_report_refs(report)

        evidence_refs = tuple(
            sorted(
                set(report.proposal.evidence_refs).union(
                    *[set(item.evidence_refs) for item in report.assessments]
                )
            )
        )
        if evidence_refs:
            self._validated_evidence_refs(evidence_refs)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "council_decision",
            report.report_id,
            self.state.cycle,
            evidence_refs,
        )
        event = CouncilDecisionEvent(
            decision_event_id=event_id,
            report=report,
            committed_cycle=self.state.cycle,
            evidence_refs=evidence_refs,
            semantic_mutation_permitted=False,
            governance_policy_mutation_permitted=False,
        )
        self.state.council_decisions.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        transition = TransitionRecord(
            transition_id=stable_id(
                "transition",
                self.state.identity.kernel_id,
                self.state.event_sequence,
                "commit_council_decision",
                command_hash,
                input_fingerprint,
                output_fingerprint,
            ),
            sequence=self.state.event_sequence,
            cycle=self.state.cycle,
            operation="commit_council_decision",
            command_hash=command_hash,
            input_fingerprint=input_fingerprint,
            output_fingerprint=output_fingerprint,
            input_refs=(report.proposal.proposal_id, report.report_id),
            output_refs=(event_id,),
        )
        self.state.transitions.append(transition)
        self._validate_state()
        return event

    def operation_authorized(self, decision_event_id: str, operation: str) -> bool:
        event = next(
            (
                item
                for item in self.state.council_decisions
                if item.decision_event_id == decision_event_id
            ),
            None,
        )
        if event is None:
            raise GovernanceAuthorizationError("Unknown Council decision event.")
        return operation in event.report.authorized_operations

    def assert_operation_authorized(
        self,
        decision_event_id: str,
        operation: str,
    ) -> None:
        if not self.operation_authorized(decision_event_id, operation):
            raise GovernanceAuthorizationError(
                f"Operation {operation!r} is not authorized by Council decision "
                f"{decision_event_id!r}."
            )

    def validate_shard_formation_report(
        self,
        report: ShardFormationReport,
    ) -> None:
        try:
            report = ShardFormationReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise ShardIntegrityError(
                "Shard formation report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise ShardIntegrityError("Shard report belongs to another kernel.")
        if report.structural_fingerprint != self.shard_structural_fingerprint():
            raise ShardStaleError(
                "Shard formation report was computed against different structure."
            )
        if report.policy_revision != self.state.shard_policy.revision:
            raise ShardStaleError("Shard policy changed after report inspection.")
        if report.parent_shard_id not in self.state.shards:
            raise ShardIntegrityError("Shard parent does not exist.")
        if report.proposed_shard_id in self.state.shards:
            raise ShardIntegrityError("Proposed shard already exists.")
        if len(report.concept_ids) > self.state.shard_policy.max_concepts_per_shard:
            raise ShardIntegrityError("Proposed shard exceeds concept bound.")
        if len(report.relation_ids) > self.state.shard_policy.max_relations_per_shard:
            raise ShardIntegrityError("Proposed shard exceeds relation bound.")
        missing_concepts = [
            item for item in report.concept_ids if item not in self.state.concepts
        ]
        if missing_concepts:
            raise ShardIntegrityError(
                "Shard report references missing concepts: "
                + ", ".join(missing_concepts)
            )
        concept_set = set(report.concept_ids)
        for relation_id in report.relation_ids:
            relation = self.state.relations.get(relation_id)
            if relation is None:
                raise ShardIntegrityError("Shard report references a missing relation.")
            if not {
                relation.source_concept_id,
                relation.target_concept_id,
            }.issubset(concept_set):
                raise ShardIntegrityError(
                    "Shard relation endpoints must both belong to the shard."
                )
        self._validated_evidence_refs(report.evidence_refs)
        if not set(report.specialization_signature).issubset(concept_set):
            raise ShardIntegrityError(
                "Specialization signature must reference member concepts."
            )

    def commit_shard_formation(
        self,
        report: ShardFormationReport,
        *,
        council_decision_event_id: str,
    ) -> ShardFormationEvent:
        self.validate_shard_formation_report(report)
        try:
            self.assert_operation_authorized(
                council_decision_event_id,
                report.operation,
            )
        except GovernanceAuthorizationError as exc:
            raise ShardAuthorizationError(
                "Council did not authorize shard formation."
            ) from exc

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        event_id = stable_id(
            "shard_formation_event",
            report.report_id,
            council_decision_event_id,
            self.state.cycle,
        )
        event = ShardFormationEvent(
            formation_event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        shard = ShardRecord(
            shard_id=report.proposed_shard_id,
            label=report.shard_label,
            normalized_label=report.normalized_label,
            status=ShardStatus.DORMANT,
            created_cycle=self.state.cycle,
            updated_cycle=self.state.cycle,
            parent_shard_id=report.parent_shard_id,
            concept_ids=report.concept_ids,
            relation_ids=report.relation_ids,
            evidence_refs=report.evidence_refs,
            specialization_signature=report.specialization_signature,
            formation_event_id=event_id,
        )
        self.state.shards[shard.shard_id] = shard
        self.state.shard_formation_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "council_decision_event_id": council_decision_event_id,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_shard_formation",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_shard_formation",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(
                    report.report_id,
                    council_decision_event_id,
                    *report.evidence_refs,
                ),
                output_refs=(event_id, shard.shard_id),
            )
        )
        self._validate_state()
        return event

    def validate_routing_report(self, report: RoutingReport) -> None:
        try:
            report = RoutingReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise ShardIntegrityError(
                "Routing report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise ShardIntegrityError("Routing report belongs to another kernel.")
        if report.structural_fingerprint != self.shard_structural_fingerprint():
            raise ShardStaleError(
                "Routing report was computed against different shard structure."
            )
        if report.policy_revision != self.state.shard_policy.revision:
            raise ShardStaleError("Shard policy changed after routing inspection.")
        if report.source_shard_id != self.state.active_shard_id:
            raise ShardStaleError("Active shard changed after routing inspection.")
        if report.source_shard_id not in self.state.shards:
            raise ShardIntegrityError("Routing source shard does not exist.")
        self._validated_evidence_refs(report.evidence_refs)
        for concept_id in report.cue_concept_ids:
            if concept_id not in self.state.concepts:
                raise ShardIntegrityError("Routing cue references a missing concept.")
        known_resonance = {
            item.resonance_event_id for item in self.state.resonance_events
        }
        if any(item not in known_resonance for item in report.resonance_event_ids):
            raise ShardIntegrityError("Routing report references missing resonance.")
        candidate_ids = [item.shard_id for item in report.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ShardIntegrityError("Routing report duplicates shard candidates.")
        for candidate in report.candidates:
            if candidate.shard_id not in self.state.shards:
                raise ShardIntegrityError("Routing candidate shard is missing.")
            if any(
                item not in self.state.concepts
                for item in candidate.directly_grounded_concept_ids
            ):
                raise ShardIntegrityError("Routing grounding references missing concepts.")
        if report.disposition == RoutingDisposition.ROUTE:
            selected = next(
                (
                    item
                    for item in report.candidates
                    if item.shard_id == report.selected_shard_id
                ),
                None,
            )
            if selected is None or not selected.eligible:
                raise ShardIntegrityError("Selected routing candidate is not eligible.")
            if (
                selected.components.direct_grounding
                < self.state.shard_policy.minimum_direct_grounding
            ):
                raise ShardIntegrityError(
                    "Selected route lacks required direct grounding."
                )
            if selected.score < self.state.shard_policy.minimum_route_score:
                raise ShardIntegrityError("Selected route score is below threshold.")
            expected_direct = tuple(
                sorted(
                    set(report.cue_concept_ids)
                    & set(self.state.shards[selected.shard_id].concept_ids)
                )
            )
            if expected_direct != selected.directly_grounded_concept_ids:
                raise ShardIntegrityError("Routing direct-grounding set drift detected.")

    def commit_routing(
        self,
        report: RoutingReport,
        *,
        council_decision_event_id: str,
    ) -> RoutingEvent:
        self.validate_routing_report(report)
        if report.disposition != RoutingDisposition.ROUTE:
            raise ShardIntegrityError("Only a ROUTE report can be committed.")
        try:
            self.assert_operation_authorized(
                council_decision_event_id,
                report.operation,
            )
        except GovernanceAuthorizationError as exc:
            raise ShardAuthorizationError(
                "Council did not authorize shard routing."
            ) from exc

        selected = next(
            item
            for item in report.candidates
            if item.shard_id == report.selected_shard_id
        )
        source_id = self.state.active_shard_id
        target_id = selected.shard_id
        if source_id == target_id:
            raise ShardIntegrityError("Routing target is already active.")
        evidence = self._validated_evidence_refs(report.evidence_refs)
        direct = selected.directly_grounded_concept_ids
        if not direct:
            raise EvidenceGateError("A route requires direct cue grounding.")

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        left, right = sorted((source_id, target_id))
        bridge_id = stable_id("shard_bridge", left, right)
        existing = self.state.shard_bridges.get(bridge_id)
        portals = tuple(
            sorted(
                set(selected.portal_concept_ids)
                | set(direct)
            )[: self.state.shard_policy.max_portals_per_bridge]
        )
        if existing is None:
            bridge = ShardBridgeRecord(
                bridge_id=bridge_id,
                source_shard_id=left,
                target_shard_id=right,
                portal_concept_ids=portals,
                evidence_refs=evidence,
                traversal_count=1,
                created_cycle=self.state.cycle,
                last_traversed_cycle=self.state.cycle,
                status=BridgeStatus.TRAVERSED,
            )
        else:
            bridge = existing.model_copy(
                update={
                    "portal_concept_ids": tuple(
                        sorted(set(existing.portal_concept_ids) | set(portals))
                    )[: self.state.shard_policy.max_portals_per_bridge],
                    "evidence_refs": tuple(
                        sorted(set(existing.evidence_refs) | set(evidence))
                    ),
                    "traversal_count": existing.traversal_count + 1,
                    "last_traversed_cycle": self.state.cycle,
                }
            )
        self.state.shard_bridges[bridge_id] = ShardBridgeRecord.model_validate(
            bridge.model_dump(mode="json")
        )

        for shard_id, shard in list(self.state.shards.items()):
            if shard_id == "root":
                status = ShardStatus.ACTIVE if target_id == "root" else ShardStatus.ROOT
            else:
                status = ShardStatus.ACTIVE if shard_id == target_id else ShardStatus.DORMANT
            if shard.status != status:
                self.state.shards[shard_id] = shard.model_copy(
                    update={"status": status, "updated_cycle": self.state.cycle}
                )
        self.state.active_shard_id = target_id
        event_id = stable_id(
            "routing_event",
            report.report_id,
            council_decision_event_id,
            self.state.cycle,
            source_id,
            target_id,
            bridge_id,
            direct,
            evidence,
        )
        event = RoutingEvent(
            routing_event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            committed_cycle=self.state.cycle,
            from_shard_id=source_id,
            to_shard_id=target_id,
            bridge_id=bridge_id,
            direct_cue_concept_ids=direct,
            evidence_refs=evidence,
            semantic_mutation_permitted=False,
        )
        self.state.routing_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "council_decision_event_id": council_decision_event_id,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_routing",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_routing",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(
                    report.report_id,
                    council_decision_event_id,
                    *evidence,
                ),
                output_refs=(event_id, bridge_id, target_id),
            )
        )
        self._validate_state()
        return event

    def validate_object_observation_report(
        self,
        report: ObjectObservationReport,
    ) -> None:
        try:
            report = ObjectObservationReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise ObjectIntegrityError(
                "Object observation report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise ObjectIntegrityError("Object report belongs to another kernel.")
        if report.structural_fingerprint != self.object_structural_fingerprint():
            raise ObjectStaleError(
                "Object observation report was computed against different state."
            )
        if report.policy_revision != self.state.object_policy.revision:
            raise ObjectStaleError("Objecthood policy changed after inspection.")
        evidence = self.state.evidence.get(report.observation.evidence_ref)
        if evidence is None:
            raise ObjectIntegrityError("Object observation lacks preserved evidence.")
        if report.observation.kind == ObjectObservationKind.VISIBLE:
            if evidence.kind != EvidenceKind.OBSERVATION:
                raise ObjectIntegrityError(
                    "Visible object observations require native observation evidence."
                )
        target = report.observation.target_candidate_id
        if target is not None and target not in self.state.object_candidates:
            raise ObjectIntegrityError("Object update targets a missing candidate.")
        proposed = report.proposed_candidate
        if proposed.updated_cycle != self.state.cycle + 1:
            raise ObjectIntegrityError("Proposed candidate has the wrong commit cycle.")
        if report.disposition == ObjectAssociationDisposition.CREATE:
            if proposed.candidate_id in self.state.object_candidates:
                raise ObjectIntegrityError("New object candidate already exists.")
            if report.selected_candidate_id is not None:
                raise ObjectIntegrityError("CREATE reports cannot select an existing candidate.")
        else:
            selected = report.selected_candidate_id or target
            if selected is None or selected not in self.state.object_candidates:
                raise ObjectIntegrityError("Object update requires an existing candidate.")
            if proposed.candidate_id != selected:
                raise ObjectIntegrityError("Proposed candidate identity drift detected.")
            if self.state.object_candidates[selected].status == ObjectCandidateStatus.PROMOTED:
                raise ObjectIntegrityError("Promoted candidates cannot be silently rewritten.")

    def commit_object_observation(
        self,
        report: ObjectObservationReport,
    ) -> ObjectObservationEvent:
        self.validate_object_observation_report(report)
        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        observation = report.observation
        observation_id = stable_id(
            "object_observation",
            self.state.identity.kernel_id,
            observation.episode_id,
            observation.frame_index,
            observation.evidence_ref,
            observation.kind.value,
            observation.model_dump(mode="json"),
        )
        if observation_id in self.state.object_observations:
            raise ObjectIntegrityError("Object observation already exists.")
        record = ObjectObservationRecord(
            observation_id=observation_id,
            episode_id=observation.episode_id,
            frame_index=observation.frame_index,
            evidence_ref=observation.evidence_ref,
            modality=observation.modality,
            kind=observation.kind,
            appearance_features=observation.appearance_features,
            position=observation.position,
            motion=observation.motion,
            common_motion_supported=observation.common_motion_supported,
            target_candidate_id=observation.target_candidate_id,
            committed_cycle=self.state.cycle,
            metadata=observation.metadata,
        )
        if observation_id not in report.proposed_candidate.observation_ids:
            raise ObjectIntegrityError(
                "Proposed candidate does not preserve the committed observation."
            )
        if observation.evidence_ref not in report.proposed_candidate.evidence_refs:
            raise ObjectIntegrityError(
                "Proposed candidate does not preserve native evidence."
            )
        self.state.object_observations[observation_id] = record
        candidate = ObjectCandidateRecord.model_validate(
            report.proposed_candidate.model_dump(mode="json")
        )
        self.state.object_candidates[candidate.candidate_id] = candidate
        event_id = stable_id(
            "object_observation_event",
            report.report_id,
            observation_id,
            candidate.candidate_id,
            self.state.cycle,
        )
        event = ObjectObservationEvent(
            event_id=event_id,
            report=report,
            observation_id=observation_id,
            candidate_id=candidate.candidate_id,
            committed_cycle=self.state.cycle,
            semantic_mutation_permitted=False,
        )
        self.state.object_observation_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(report.model_dump(mode="json"))
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_object_observation",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_object_observation",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(report.report_id, observation.evidence_ref),
                output_refs=(event_id, observation_id, candidate.candidate_id),
            )
        )
        self._validate_state()
        return event

    def validate_object_promotion_report(
        self,
        report: ObjectPromotionReport,
    ) -> None:
        try:
            report = ObjectPromotionReport.model_validate(
                report.model_dump(mode="json")
            )
        except ValueError as exc:
            raise ObjectIntegrityError(
                "Object promotion report failed its identity checksum."
            ) from exc
        if report.kernel_id != self.state.identity.kernel_id:
            raise ObjectIntegrityError("Object promotion belongs to another kernel.")
        if report.structural_fingerprint != self.object_structural_fingerprint():
            raise ObjectStaleError(
                "Object promotion report was computed against different state."
            )
        if report.policy_revision != self.state.object_policy.revision:
            raise ObjectStaleError("Objecthood policy changed after promotion inspection.")
        candidate = self.state.object_candidates.get(report.candidate_id)
        if candidate is None:
            raise ObjectIntegrityError("Object promotion references a missing candidate.")
        if candidate != report.candidate_snapshot:
            raise ObjectStaleError("Object candidate changed after promotion inspection.")
        if candidate.status == ObjectCandidateStatus.PROMOTED:
            raise ObjectIntegrityError("Object candidate is already promoted.")
        self._validated_evidence_refs(report.evidence_refs)
        if report.evidence_refs != candidate.evidence_refs:
            raise ObjectIntegrityError("Promotion must preserve the full candidate evidence path.")
        expected_concept_id = stable_id("concept", normalize_label(report.proposed_label))
        if expected_concept_id != report.proposed_concept_id:
            raise ObjectIntegrityError("Proposed proto-object concept identity drift detected.")

    def commit_object_promotion(
        self,
        report: ObjectPromotionReport,
        *,
        council_decision_event_id: str,
    ) -> ObjectPromotionEvent:
        self.validate_object_promotion_report(report)
        if report.disposition != ObjectPromotionDisposition.PROMOTE:
            raise ObjectIntegrityError("Only an eligible PROMOTE report can be committed.")
        if report.rejection_codes:
            raise ObjectIntegrityError("Promotion report still contains rejection gates.")
        try:
            self.assert_operation_authorized(
                council_decision_event_id,
                report.operation,
            )
        except GovernanceAuthorizationError as exc:
            raise ObjectAuthorizationError(
                "Council did not authorize proto-object promotion."
            ) from exc

        input_fingerprint = self.semantic_fingerprint()
        self.state.cycle += 1
        self.state.event_sequence += 1
        candidate = self.state.object_candidates[report.candidate_id]
        concept = self.ensure_concept(
            report.proposed_label,
            evidence_refs=report.evidence_refs,
            attributes={
                "concept_type": "earned_proto_object",
                "object_candidate_id": candidate.candidate_id,
                "support_score": candidate.support_score,
                "support_components": candidate.support_components.model_dump(mode="json"),
                "source_observation_ids": list(candidate.observation_ids),
                "episode_ids": list(candidate.episode_ids),
                "promotion_policy_revision": report.policy_revision,
                "semantic_category_preinstalled": False,
            },
        )
        if concept.concept_id != report.proposed_concept_id:
            raise ObjectIntegrityError("Committed proto-object concept identity mismatch.")
        updated = candidate.model_copy(
            update={
                "status": ObjectCandidateStatus.PROMOTED,
                "updated_cycle": self.state.cycle,
                "promoted_concept_id": concept.concept_id,
            }
        )
        self.state.object_candidates[candidate.candidate_id] = ObjectCandidateRecord.model_validate(
            updated.model_dump(mode="json")
        )
        event_id = stable_id(
            "object_promotion_event",
            report.report_id,
            council_decision_event_id,
            concept.concept_id,
            self.state.cycle,
        )
        event = ObjectPromotionEvent(
            event_id=event_id,
            report=report,
            council_decision_event_id=council_decision_event_id,
            concept_id=concept.concept_id,
            committed_cycle=self.state.cycle,
        )
        self.state.object_promotion_events.append(event)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "report": report.model_dump(mode="json"),
                    "council_decision_event_id": council_decision_event_id,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "commit_object_promotion",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="commit_object_promotion",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(
                    report.report_id,
                    council_decision_event_id,
                    *report.evidence_refs,
                ),
                output_refs=(event_id, concept.concept_id, candidate.candidate_id),
            )
        )
        self._validate_state()
        return event


    def record_governance_outcome(
        self,
        *,
        decision_event_id: str,
        evidence_refs: Iterable[str],
        succeeded: bool,
        harm_score: float,
    ) -> GovernanceOutcomeRecord:
        if not math.isfinite(harm_score) or not 0.0 <= harm_score <= 1.0:
            raise ValueError("harm_score must be a finite probability.")
        event = next(
            (
                item
                for item in self.state.council_decisions
                if item.decision_event_id == decision_event_id
            ),
            None,
        )
        if event is None:
            raise GovernanceAuthorizationError("Unknown Council decision event.")
        if event.report.proposal.operation not in event.report.authorized_operations:
            raise GovernanceAuthorizationError(
                "Outcomes may only be recorded for an authorized operation."
            )
        if any(
            item.decision_event_id == decision_event_id
            for item in self.state.governance_outcomes
        ):
            raise GovernanceIntegrityError(
                "A governance outcome already exists for this decision event."
            )
        evidence = self._validated_evidence_refs(evidence_refs)
        if not evidence:
            raise EvidenceGateError("Governance outcomes require preserved evidence.")
        if not any(
            self.state.evidence[item].kind == EvidenceKind.OUTCOME for item in evidence
        ):
            raise EvidenceGateError(
                "Governance outcome learning requires at least one physical outcome record."
            )

        proposal = event.report.proposal
        current = self.state.governance
        before = current.learned_action_risk.get(proposal.action_class, 0.0)
        after = min(
            1.0,
            (1.0 - current.outcome_learning_rate) * before
            + current.outcome_learning_rate * harm_score,
        )
        input_fingerprint = self.semantic_fingerprint()
        revision_before = current.revision
        self.state.cycle += 1
        self.state.event_sequence += 1
        risks = dict(current.learned_action_risk)
        risks[proposal.action_class] = after
        self.state.governance = GovernanceState.model_validate(
            current.model_copy(
                update={
                    "learned_action_risk": risks,
                    "revision": current.revision + 1,
                }
            ).model_dump(mode="json")
        )
        outcome_id = stable_id(
            "governance_outcome",
            decision_event_id,
            proposal.action_class,
            evidence,
            succeeded,
            harm_score,
            before,
            after,
            self.state.cycle,
        )
        outcome = GovernanceOutcomeRecord(
            outcome_id=outcome_id,
            decision_event_id=decision_event_id,
            action_class=proposal.action_class,
            evidence_refs=evidence,
            succeeded=succeeded,
            harm_score=harm_score,
            prediction_error=abs(harm_score - proposal.harm_risk),
            cycle=self.state.cycle,
            learned_risk_before=before,
            learned_risk_after=after,
            policy_revision_before=revision_before,
            policy_revision_after=self.state.governance.revision,
        )
        self.state.governance_outcomes.append(outcome)
        command_hash = hashlib.sha256(
            canonical_json_bytes(
                {
                    "decision_event_id": decision_event_id,
                    "evidence_refs": evidence,
                    "succeeded": succeeded,
                    "harm_score": harm_score,
                }
            )
        ).hexdigest()
        output_fingerprint = self.semantic_fingerprint()
        self.state.transitions.append(
            TransitionRecord(
                transition_id=stable_id(
                    "transition",
                    self.state.identity.kernel_id,
                    self.state.event_sequence,
                    "record_governance_outcome",
                    command_hash,
                    input_fingerprint,
                    output_fingerprint,
                ),
                sequence=self.state.event_sequence,
                cycle=self.state.cycle,
                operation="record_governance_outcome",
                command_hash=command_hash,
                input_fingerprint=input_fingerprint,
                output_fingerprint=output_fingerprint,
                input_refs=(decision_event_id, *evidence),
                output_refs=(outcome_id,),
            )
        )
        self._validate_state()
        return outcome

    def validate_council_report_refs(self, report: CouncilReport) -> None:
        """Public read-only reference gate for governance proposal/report builders."""
        self._validate_council_report_refs(report)

    def _validate_council_report_refs(self, report: CouncilReport) -> None:
        proposal = report.proposal
        if proposal.kernel_id != self.state.identity.kernel_id:
            raise GovernanceIntegrityError("Council proposal belongs to another kernel.")
        if proposal.state_fingerprint != report.state_fingerprint:
            raise GovernanceIntegrityError("Council proposal/report state drift detected.")
        if proposal.governance_fingerprint != report.governance_fingerprint:
            raise GovernanceIntegrityError(
                "Council proposal/report governance drift detected."
            )
        if proposal.target_claim_id is not None and proposal.target_claim_id not in self.state.claims:
            raise GovernanceIntegrityError("Council proposal references a missing claim.")
        if proposal.evidence_refs:
            self._validated_evidence_refs(proposal.evidence_refs)
        for candidate_id in proposal.attention_candidate_ids:
            if candidate_id not in self.state.attention_candidates:
                raise GovernanceIntegrityError(
                    "Council proposal references a missing attention candidate."
                )
        known_resonance = {
            item.resonance_event_id for item in self.state.resonance_events
        }
        if any(item not in known_resonance for item in proposal.resonance_event_ids):
            raise GovernanceIntegrityError(
                "Council proposal references a missing resonance event."
            )
        for assessment in report.assessments:
            if assessment.proposal_id != proposal.proposal_id:
                raise GovernanceIntegrityError(
                    "King assessment belongs to another proposal."
                )
            if assessment.evidence_refs:
                self._validated_evidence_refs(assessment.evidence_refs)
            if any(
                item not in self.state.attention_candidates
                for item in assessment.attention_candidate_ids
            ):
                raise GovernanceIntegrityError(
                    "King assessment references a missing attention candidate."
                )


    def _upsert_evidence(
        self,
        *,
        kind: EvidenceKind,
        event_key: str,
        source_ref: str,
        confidence: float,
        payload_sha256: str | None,
        details: dict[str, object],
    ) -> EvidenceRecord:
        evidence_id = stable_id(
            "evidence",
            self.state.identity.kernel_id,
            event_key,
            kind.value,
            source_ref,
            payload_sha256,
        )
        existing = self.state.evidence.get(evidence_id)
        if existing is not None:
            return existing
        evidence = EvidenceRecord(
            evidence_id=evidence_id,
            kind=kind,
            source_ref=source_ref,
            event_key=event_key,
            cycle=self.state.cycle,
            confidence=confidence,
            payload_sha256=payload_sha256,
            details=details,
        )
        self.state.evidence[evidence_id] = evidence
        return evidence

    def _validated_evidence_refs(
        self,
        evidence_refs: Iterable[str],
    ) -> tuple[str, ...]:
        refs = tuple(sorted(set(evidence_refs)))
        if not refs:
            raise EvidenceGateError(
                "Persistent concepts and relations require at least one evidence reference."
            )
        missing = [ref for ref in refs if ref not in self.state.evidence]
        if missing:
            raise EvidenceGateError(
                f"Unknown evidence references: {', '.join(missing)}"
            )
        return refs

    def _field_array(self) -> np.ndarray:
        return np.asarray(self.state.field.real, dtype=np.float64) + 1j * np.asarray(
            self.state.field.imag,
            dtype=np.float64,
        )

    @staticmethod
    def _normalize_complex(vector: np.ndarray) -> np.ndarray:
        vector = np.asarray(vector, dtype=np.complex128)
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm

    @staticmethod
    def _validated_feature_array(features: Iterable[float]) -> np.ndarray:
        vector = np.asarray(tuple(features), dtype=np.float64).reshape(-1)
        if vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError("Features must be a finite non-empty vector.")
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm

    def _projection_seed(self, modality: str, feature_dim: int) -> int:
        digest = hashlib.blake2b(
            canonical_json_bytes(
                [self.state.seed, modality, feature_dim, self.state.field.state_dim]
            ),
            digest_size=8,
            person=b"vkernel",
        ).digest()
        return int.from_bytes(digest, "little")

    def _project_effect(self, features: np.ndarray, modality: str) -> np.ndarray:
        rng = np.random.default_rng(self._projection_seed(modality, features.size))
        scale = 1.0 / math.sqrt(features.size)
        real_projection = rng.normal(
            0.0,
            scale,
            size=(features.size, self.state.field.state_dim),
        )
        imag_projection = rng.normal(
            0.0,
            scale,
            size=(features.size, self.state.field.state_dim),
        )
        real = np.tanh(3.0 * (features @ real_projection))
        imag = np.tanh(3.0 * (features @ imag_projection))
        return self._normalize_complex(real + 1j * imag)

    def _address_array(self, address: ConceptFieldAddress) -> np.ndarray:
        return np.asarray(address.real, dtype=np.float64) + 1j * np.asarray(
            address.imag,
            dtype=np.float64,
        )

    def _address_seed(self, concept_id: str, nonce: int) -> int:
        digest = hashlib.blake2b(
            canonical_json_bytes(
                [
                    self.state.seed,
                    concept_id,
                    self.state.field.state_dim,
                    self.state.ecwf_policy.address_revision,
                    nonce,
                ]
            ),
            digest_size=8,
            person=b"vecaddr4",
        ).digest()
        return int.from_bytes(digest, "little")

    def _derive_field_address(
        self,
        concept_id: str,
        nonce: int,
    ) -> ConceptFieldAddress:
        rng = np.random.default_rng(self._address_seed(concept_id, nonce))
        phase = rng.uniform(-math.pi, math.pi, self.state.field.state_dim)
        vector = np.exp(1j * phase) / math.sqrt(self.state.field.state_dim)
        real = tuple(float(value) for value in vector.real)
        imag = tuple(float(value) for value in vector.imag)
        digest = hashlib.sha256(
            canonical_json_bytes(
                {
                    "concept_id": concept_id,
                    "state_dim": self.state.field.state_dim,
                    "address_revision": self.state.ecwf_policy.address_revision,
                    "nonce": nonce,
                    "real": real,
                    "imag": imag,
                }
            )
        ).hexdigest()
        return ConceptFieldAddress(
            concept_id=concept_id,
            address_sha256=digest,
            created_cycle=self.state.cycle,
            state_dim=self.state.field.state_dim,
            derivation_nonce=nonce,
            real=real,
            imag=imag,
        )

    def _ensure_field_address(self, concept_id: str) -> ConceptFieldAddress:
        existing = self.state.field_addresses.get(concept_id)
        if existing is not None:
            return existing
        used = {
            item.address_sha256: item.concept_id
            for item in self.state.field_addresses.values()
        }
        nonce = 0
        while True:
            candidate = self._derive_field_address(concept_id, nonce)
            owner = used.get(candidate.address_sha256)
            if owner is None or owner == concept_id:
                self.state.field_addresses[concept_id] = candidate
                return candidate
            nonce += 1

    def _profile_array(self, profile: ConceptResonanceProfile) -> np.ndarray:
        return np.asarray(profile.real, dtype=np.float64) + 1j * np.asarray(
            profile.imag,
            dtype=np.float64,
        )

    def _update_resonance_profile(
        self,
        concept_id: str,
        feature_effect: np.ndarray,
        evidence_refs: tuple[str, ...],
    ) -> ConceptResonanceProfile:
        existing = self.state.resonance_profiles.get(concept_id)
        if existing is None:
            updated_vector = self._normalize_complex(feature_effect)
            exposure_count = 1
            created_cycle = self.state.cycle
            merged_evidence = evidence_refs
        else:
            previous = self._profile_array(existing)
            exposure_count = existing.exposure_count + 1
            updated_vector = self._normalize_complex(
                existing.exposure_count * previous + feature_effect
            )
            created_cycle = existing.created_cycle
            merged_evidence = tuple(
                sorted(set(existing.evidence_refs) | set(evidence_refs))
            )
        profile = ConceptResonanceProfile(
            concept_id=concept_id,
            state_dim=self.state.field.state_dim,
            exposure_count=exposure_count,
            created_cycle=created_cycle,
            updated_cycle=self.state.cycle,
            evidence_refs=merged_evidence,
            real=tuple(float(value) for value in updated_vector.real),
            imag=tuple(float(value) for value in updated_vector.imag),
        )
        self.state.resonance_profiles[concept_id] = profile
        return profile

    def _concept_binding_effect(
        self,
        concept_ids: Iterable[str],
    ) -> np.ndarray | None:
        unique_ids = tuple(sorted(set(concept_ids)))
        if not unique_ids:
            return None
        addresses = [
            self._address_array(self.state.field_addresses[concept_id])
            for concept_id in unique_ids
        ]
        return self._normalize_complex(np.sum(addresses, axis=0))

    def _history_alignment(
        self,
        address: np.ndarray,
        frames: Iterable[FieldFrame],
    ) -> float:
        frame_list = list(frames)
        if not frame_list:
            return 0.0
        decay = self.state.ecwf_policy.history_decay
        weighted = 0.0
        total_weight = 0.0
        for age, frame in enumerate(reversed(frame_list)):
            weight = decay**age
            frame_vector = np.asarray(frame.real, dtype=np.float64) + 1j * np.asarray(
                frame.imag,
                dtype=np.float64,
            )
            norm = np.linalg.norm(frame_vector)
            if norm:
                frame_vector = frame_vector / norm
            alignment = float(min(1.0, abs(np.vdot(address, frame_vector))))
            weighted += weight * alignment
            total_weight += weight
        return weighted / total_weight if total_weight else 0.0

    def _apply_field_effect(
        self,
        features: Iterable[float],
        modality: str,
        *,
        caused_by_refs: Iterable[str],
        bound_concept_ids: Iterable[str] = (),
    ) -> None:
        evidence = self._validated_evidence_refs(caused_by_refs)
        vector = self._validated_feature_array(features)
        before = self._field_array()
        feature_effect = self._project_effect(vector, modality)
        bound_ids = tuple(sorted(set(bound_concept_ids)))
        for concept_id in bound_ids:
            if concept_id not in self.state.concepts:
                raise KernelInvariantError(
                    f"Field binding references unknown concept '{concept_id}'."
                )
            self._ensure_field_address(concept_id)
        for concept_id in bound_ids:
            self._update_resonance_profile(concept_id, feature_effect, evidence)
        concept_effect = self._concept_binding_effect(bound_ids)
        policy = self.state.ecwf_policy
        components = [policy.feature_coupling * feature_effect]
        if concept_effect is not None:
            components.append(policy.concept_coupling * concept_effect)
        experience_effect = self._normalize_complex(np.sum(components, axis=0))
        if np.linalg.norm(before) == 0:
            after = experience_effect
        else:
            after = self._normalize_complex(
                policy.retention * before + experience_effect
            )
        delta = after - before
        effect_sha256 = hashlib.sha256(
            canonical_json_bytes(
                {
                    "real": [float(value) for value in experience_effect.real],
                    "imag": [float(value) for value in experience_effect.imag],
                    "bound_concept_ids": bound_ids,
                    "policy_revision": policy.revision,
                }
            )
        ).hexdigest()
        self.state.field.real = [float(value) for value in after.real]
        self.state.field.imag = [float(value) for value in after.imag]
        self.state.field.history.append(
            FieldFrame(
                cycle=self.state.cycle,
                caused_by_refs=evidence,
                real=tuple(float(value) for value in after.real),
                imag=tuple(float(value) for value in after.imag),
                delta_norm=float(np.linalg.norm(delta)),
                effect_sha256=effect_sha256,
                bound_concept_ids=bound_ids,
                policy_revision=policy.revision,
            )
        )

    def update_ecwf_policy(self, **changes: object) -> ECWFPolicy:
        requested_address_revision = changes.get("address_revision")
        if (
            requested_address_revision is not None
            and requested_address_revision != self.state.ecwf_policy.address_revision
            and self.state.concepts
        ):
            raise KernelInvariantError(
                "Address revision cannot change after concepts exist without an explicit migration."
            )
        next_policy = self.state.ecwf_policy.model_copy(
            update={
                **changes,
                "revision": self.state.ecwf_policy.revision + 1,
            }
        )
        self.state.ecwf_policy = ECWFPolicy.model_validate(
            next_policy.model_dump(mode="json")
        )
        return self.state.ecwf_policy.model_copy(deep=True)

    def _migrate_ecwf_state(self) -> None:
        if self.state.identity.schema_version != "1.0.0-alpha":
            self.state.identity = self.state.identity.model_copy(
                update={"schema_version": "1.0.0-alpha"}
            )
        for concept_id in sorted(self.state.concepts):
            self._ensure_field_address(concept_id)

    def _migrate_shard_state(self) -> None:
        root = self.state.shards.get("root")
        all_concepts = tuple(sorted(self.state.concepts))
        all_relations = tuple(sorted(self.state.relations))
        if root is None:
            root = ShardRecord(
                shard_id="root",
                label="root",
                normalized_label="root",
                status=ShardStatus.ACTIVE if self.state.active_shard_id == "root" else ShardStatus.ROOT,
                created_cycle=0,
                updated_cycle=self.state.cycle,
                concept_ids=all_concepts,
                relation_ids=all_relations,
                evidence_refs=(),
                specialization_signature=(),
            )
        else:
            migrated_status = (
                ShardStatus.ACTIVE
                if self.state.active_shard_id == "root"
                else ShardStatus.ROOT
            )
            migrated_concepts = tuple(
                sorted(set(root.concept_ids) | set(all_concepts))
            )
            migrated_relations = tuple(
                sorted(set(root.relation_ids) | set(all_relations))
            )
            changed = (
                root.status != migrated_status
                or root.concept_ids != migrated_concepts
                or root.relation_ids != migrated_relations
            )
            root = root.model_copy(
                update={
                    "status": migrated_status,
                    "concept_ids": migrated_concepts,
                    "relation_ids": migrated_relations,
                    "updated_cycle": self.state.cycle if changed else root.updated_cycle,
                }
            )
        self.state.shards["root"] = ShardRecord.model_validate(root.model_dump(mode="json"))
        if self.state.active_shard_id not in self.state.shards:
            self.state.active_shard_id = "root"
        for shard_id, shard in list(self.state.shards.items()):
            if shard_id == "root":
                continue
            expected_status = (
                ShardStatus.ACTIVE
                if shard_id == self.state.active_shard_id
                else ShardStatus.DORMANT
            )
            if shard.status != expected_status:
                self.state.shards[shard_id] = shard.model_copy(
                    update={"status": expected_status}
                )

    def _catalog_concept_in_shards(
        self,
        concept_id: str,
        *,
        attach_active: bool,
    ) -> None:
        self._migrate_shard_state()
        root = self.state.shards["root"]
        if concept_id not in root.concept_ids:
            self.state.shards["root"] = root.model_copy(
                update={
                    "concept_ids": tuple(sorted((*root.concept_ids, concept_id))),
                    "updated_cycle": self.state.cycle,
                }
            )
        active_id = self.state.active_shard_id
        if not attach_active or active_id == "root":
            return
        active = self.state.shards[active_id]
        if concept_id in active.concept_ids:
            return
        if len(active.concept_ids) >= self.state.shard_policy.max_concepts_per_shard:
            return
        self.state.shards[active_id] = active.model_copy(
            update={
                "concept_ids": tuple(sorted((*active.concept_ids, concept_id))),
                "updated_cycle": self.state.cycle,
            }
        )

    def _catalog_relation_in_shards(
        self,
        relation_id: str,
        *,
        attach_active: bool,
    ) -> None:
        self._migrate_shard_state()
        relation = self.state.relations[relation_id]
        root = self.state.shards["root"]
        if relation_id not in root.relation_ids:
            self.state.shards["root"] = root.model_copy(
                update={
                    "relation_ids": tuple(sorted((*root.relation_ids, relation_id))),
                    "updated_cycle": self.state.cycle,
                }
            )
        active_id = self.state.active_shard_id
        if not attach_active or active_id == "root":
            return
        active = self.state.shards[active_id]
        if relation_id in active.relation_ids:
            return
        if len(active.relation_ids) >= self.state.shard_policy.max_relations_per_shard:
            return
        endpoints = {relation.source_concept_id, relation.target_concept_id}
        if not endpoints.issubset(set(active.concept_ids)):
            return
        self.state.shards[active_id] = active.model_copy(
            update={
                "relation_ids": tuple(sorted((*active.relation_ids, relation_id))),
                "updated_cycle": self.state.cycle,
            }
        )

    def _replayed_result(self, event_key: str) -> ExperienceResult:
        matching = [
            transition
            for transition in self.state.transitions
            if transition.operation == "apply_experience"
            and self.state.processed_event_keys.get(event_key) == transition.command_hash
        ]
        transition = matching[-1]
        evidence_ids = [
            ref for ref in transition.output_refs if ref.startswith("evidence_")
        ]
        concept_ids = tuple(
            ref for ref in transition.output_refs if ref.startswith("concept_")
        )
        relation_ids = tuple(
            ref for ref in transition.output_refs if ref.startswith("relation_")
        )
        claim_ids = tuple(
            ref for ref in transition.output_refs if ref.startswith("claim_")
        )
        contradiction_ids = tuple(
            ref for ref in transition.output_refs if ref.startswith("contradiction_")
        )
        revision_ids = tuple(
            ref for ref in transition.output_refs if ref.startswith("revision_")
        )
        return ExperienceResult(
            event_key=event_key,
            cycle=transition.cycle,
            observation_evidence_id=evidence_ids[0],
            translation_evidence_id=evidence_ids[1],
            concept_ids=concept_ids,
            relation_ids=relation_ids,
            claim_ids=claim_ids,
            contradiction_ids=contradiction_ids,
            revision_ids=revision_ids,
            transition_id=transition.transition_id,
            additional_evidence_ids=tuple(evidence_ids[2:]),
            replayed=True,
        )

    def _validate_state(self) -> None:
        for concept_id, concept in self.state.concepts.items():
            self._validated_evidence_refs(concept.evidence_refs)
            address = self.state.field_addresses.get(concept_id)
            if address is None:
                raise KernelInvariantError(
                    f"Concept '{concept_id}' has no persistent field address."
                )
            if address.concept_id != concept_id:
                raise KernelInvariantError("Field address dictionary key drift detected.")
            expected = self._derive_field_address(
                concept_id,
                address.derivation_nonce,
            )
            if expected.address_sha256 != address.address_sha256:
                raise KernelInvariantError("Field address checksum drift detected.")
            if expected.real != address.real or expected.imag != address.imag:
                raise KernelInvariantError("Field address vector drift detected.")
        orphan_addresses = set(self.state.field_addresses) - set(self.state.concepts)
        if orphan_addresses:
            raise KernelInvariantError(
                "Orphan field addresses detected: " + ", ".join(sorted(orphan_addresses))
            )
        address_digests = [
            address.address_sha256 for address in self.state.field_addresses.values()
        ]
        if len(address_digests) != len(set(address_digests)):
            raise KernelInvariantError("Duplicate field address digests detected.")
        for concept_id, profile in self.state.resonance_profiles.items():
            if concept_id not in self.state.concepts:
                raise KernelInvariantError("Orphan resonance profile detected.")
            if profile.concept_id != concept_id:
                raise KernelInvariantError("Resonance profile dictionary key drift detected.")
            if profile.state_dim != self.state.field.state_dim:
                raise KernelInvariantError("Resonance profile dimension drift detected.")
            self._validated_evidence_refs(profile.evidence_refs)
        for relation_id, relation in self.state.relations.items():
            if relation_id != relation.relation_id:
                raise KernelInvariantError("Relation dictionary key drift detected.")
            if relation.source_concept_id not in self.state.concepts:
                raise KernelInvariantError("Relation source concept is missing.")
            if relation.target_concept_id not in self.state.concepts:
                raise KernelInvariantError("Relation target concept is missing.")
            self._validated_evidence_refs(relation.evidence_refs)
        for claim_id, claim in self.state.claims.items():
            if claim_id != claim.claim_id:
                raise KernelInvariantError("Claim dictionary key drift detected.")
            if claim.subject_concept_id not in self.state.concepts:
                raise KernelInvariantError("Claim subject concept is missing.")
            if claim.object_concept_id not in self.state.concepts:
                raise KernelInvariantError("Claim object concept is missing.")
            self._validated_evidence_refs(
                entry.evidence_id for entry in claim.support_ledger
            )
            if claim.refutation_ledger:
                self._validated_evidence_refs(
                    entry.evidence_id for entry in claim.refutation_ledger
                )
        for contradiction_id, contradiction in self.state.contradictions.items():
            if contradiction_id != contradiction.contradiction_id:
                raise KernelInvariantError("Contradiction dictionary key drift detected.")
            if any(claim_id not in self.state.claims for claim_id in contradiction.claim_ids):
                raise KernelInvariantError("Contradiction references a missing claim.")
            if contradiction.evidence_refs:
                self._validated_evidence_refs(contradiction.evidence_refs)
        for revision in self.state.revisions:
            if revision.prior_claim_id not in self.state.claims:
                raise KernelInvariantError("Revision prior claim is missing.")
            if revision.revised_to_claim_id not in self.state.claims:
                raise KernelInvariantError("Revision replacement claim is missing.")
            self._validated_evidence_refs(revision.evidence_refs)
        if len(self.state.field.real) != self.state.field.state_dim:
            raise KernelInvariantError("Field real dimension drift detected.")
        if len(self.state.field.imag) != self.state.field.state_dim:
            raise KernelInvariantError("Field imaginary dimension drift detected.")
        for frame in self.state.field.history:
            self._validated_evidence_refs(frame.caused_by_refs)
            if len(frame.real) != self.state.field.state_dim:
                raise KernelInvariantError("Field history real dimension drift detected.")
            if len(frame.imag) != self.state.field.state_dim:
                raise KernelInvariantError("Field history imaginary dimension drift detected.")
            if any(
                concept_id not in self.state.concepts
                for concept_id in frame.bound_concept_ids
            ):
                raise KernelInvariantError(
                    "Field history references a missing bound concept."
                )
        for event in self.state.resonance_events:
            self._validated_evidence_refs(event.evidence_refs)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError(
                    "Resonance events may not carry semantic mutation permission."
                )
            for candidate in event.query_report.candidates:
                if candidate.concept_id not in self.state.concepts:
                    raise KernelInvariantError(
                        "Resonance report references a missing concept."
                    )
            for attention_id in event.attention_candidate_ids:
                if attention_id not in self.state.attention_candidates:
                    raise KernelInvariantError(
                        "Resonance event references a missing attention candidate."
                    )
        if "root" not in self.state.shards:
            raise KernelInvariantError("Root shard is missing.")
        if self.state.active_shard_id not in self.state.shards:
            raise KernelInvariantError("Active shard ID does not exist.")
        root = self.state.shards["root"]
        if not set(self.state.concepts).issubset(set(root.concept_ids)):
            raise KernelInvariantError("Root shard does not catalog every concept.")
        if not set(self.state.relations).issubset(set(root.relation_ids)):
            raise KernelInvariantError("Root shard does not catalog every relation.")
        active_count = 0
        formation_ids = {
            item.formation_event_id for item in self.state.shard_formation_events
        }
        for shard_id, shard in self.state.shards.items():
            if shard_id != shard.shard_id:
                raise KernelInvariantError("Shard dictionary key drift detected.")
            if shard.status == ShardStatus.ACTIVE:
                active_count += 1
                if shard_id != self.state.active_shard_id:
                    raise KernelInvariantError("Shard active status drift detected.")
            if shard_id == "root":
                expected = (
                    ShardStatus.ACTIVE
                    if self.state.active_shard_id == "root"
                    else ShardStatus.ROOT
                )
                if shard.status != expected:
                    raise KernelInvariantError("Root shard status drift detected.")
            else:
                expected = (
                    ShardStatus.ACTIVE
                    if shard_id == self.state.active_shard_id
                    else ShardStatus.DORMANT
                )
                if shard.status != expected:
                    raise KernelInvariantError("Specialized shard status drift detected.")
                if len(shard.concept_ids) > self.state.shard_policy.max_concepts_per_shard:
                    raise KernelInvariantError("Specialized shard exceeds concept bound.")
                if len(shard.relation_ids) > self.state.shard_policy.max_relations_per_shard:
                    raise KernelInvariantError("Specialized shard exceeds relation bound.")
                if shard.formation_event_id not in formation_ids:
                    raise KernelInvariantError("Specialized shard lacks formation lineage.")
            if any(item not in self.state.concepts for item in shard.concept_ids):
                raise KernelInvariantError("Shard references a missing concept.")
            if any(item not in self.state.relations for item in shard.relation_ids):
                raise KernelInvariantError("Shard references a missing relation.")
            if shard.evidence_refs:
                self._validated_evidence_refs(shard.evidence_refs)
            member_set = set(shard.concept_ids)
            for relation_id in shard.relation_ids:
                relation = self.state.relations[relation_id]
                if not {
                    relation.source_concept_id,
                    relation.target_concept_id,
                }.issubset(member_set):
                    raise KernelInvariantError(
                        "Shard relation endpoints are outside shard membership."
                    )
        if active_count != 1:
            raise KernelInvariantError("Exactly one shard must be active.")
        for formation in self.state.shard_formation_events:
            if formation.semantic_mutation_permitted:
                raise KernelInvariantError("Shard formation may not mutate semantics.")
            if formation.report.proposed_shard_id not in self.state.shards:
                raise KernelInvariantError("Formation event references missing shard.")
            if not self.operation_authorized(
                formation.council_decision_event_id,
                formation.report.operation,
            ):
                raise KernelInvariantError("Shard formation lacks Council authorization.")
        for bridge_id, bridge in self.state.shard_bridges.items():
            if bridge_id != bridge.bridge_id:
                raise KernelInvariantError("Bridge dictionary key drift detected.")
            if bridge.source_shard_id not in self.state.shards:
                raise KernelInvariantError("Bridge source shard is missing.")
            if bridge.target_shard_id not in self.state.shards:
                raise KernelInvariantError("Bridge target shard is missing.")
            if bridge.traversal_count < 1:
                raise KernelInvariantError("Ghost bridge detected.")
            self._validated_evidence_refs(bridge.evidence_refs)
            if any(item not in self.state.concepts for item in bridge.portal_concept_ids):
                raise KernelInvariantError("Bridge portal references missing concept.")
        known_bridges = set(self.state.shard_bridges)
        for routing in self.state.routing_events:
            if routing.semantic_mutation_permitted:
                raise KernelInvariantError("Routing may not mutate semantic truth.")
            if routing.bridge_id not in known_bridges:
                raise KernelInvariantError("Routing event references missing bridge.")
            if routing.from_shard_id not in self.state.shards:
                raise KernelInvariantError("Routing source shard is missing.")
            if routing.to_shard_id not in self.state.shards:
                raise KernelInvariantError("Routing target shard is missing.")
            self._validated_evidence_refs(routing.evidence_refs)
            if not routing.direct_cue_concept_ids:
                raise KernelInvariantError("Routing event lacks direct grounding.")
            if any(
                item not in self.state.shards[routing.to_shard_id].concept_ids
                for item in routing.direct_cue_concept_ids
            ):
                raise KernelInvariantError(
                    "Routing direct cue is not grounded in target shard."
                )
            if not self.operation_authorized(
                routing.council_decision_event_id,
                routing.report.operation,
            ):
                raise KernelInvariantError("Routing event lacks Council authorization.")
        observation_membership: dict[str, str] = {}
        for observation_id, observation in self.state.object_observations.items():
            if observation_id != observation.observation_id:
                raise KernelInvariantError("Object observation dictionary key drift detected.")
            evidence = self.state.evidence.get(observation.evidence_ref)
            if evidence is None:
                raise KernelInvariantError("Object observation evidence is missing.")
            if observation.kind == ObjectObservationKind.VISIBLE:
                if evidence.kind != EvidenceKind.OBSERVATION:
                    raise KernelInvariantError(
                        "Visible object observation is not backed by native evidence."
                    )
        for candidate_id, candidate in self.state.object_candidates.items():
            if candidate_id != candidate.candidate_id:
                raise KernelInvariantError("Object candidate dictionary key drift detected.")
            self._validated_evidence_refs(candidate.evidence_refs)
            if any(item not in self.state.object_observations for item in candidate.observation_ids):
                raise KernelInvariantError("Object candidate references a missing observation.")
            for observation_id in candidate.observation_ids:
                prior = observation_membership.get(observation_id)
                if prior is not None and prior != candidate_id:
                    raise KernelInvariantError(
                        "One object observation belongs to multiple candidates."
                    )
                observation_membership[observation_id] = candidate_id
            if set(candidate.episode_ids) != {
                self.state.object_observations[item].episode_id
                for item in candidate.observation_ids
            }:
                raise KernelInvariantError("Object candidate episode index drift detected.")
            if candidate.promoted_concept_id is not None:
                concept = self.state.concepts.get(candidate.promoted_concept_id)
                if concept is None:
                    raise KernelInvariantError("Promoted object concept is missing.")
                if concept.attributes.get("object_candidate_id") != candidate_id:
                    raise KernelInvariantError("Promoted object lineage attribute drift detected.")
            if any(item not in self.state.object_candidates for item in candidate.competing_candidate_ids):
                raise KernelInvariantError("Object candidate references a missing competitor.")
        if set(observation_membership) != set(self.state.object_observations):
            raise KernelInvariantError("An object observation is not owned by a candidate.")
        known_object_events = {item.event_id for item in self.state.object_observation_events}
        if len(known_object_events) != len(self.state.object_observation_events):
            raise KernelInvariantError("Duplicate object observation events detected.")
        for event in self.state.object_observation_events:
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Object tracking may not create semantic truth.")
            if event.observation_id not in self.state.object_observations:
                raise KernelInvariantError("Object event references a missing observation.")
            if event.candidate_id not in self.state.object_candidates:
                raise KernelInvariantError("Object event references a missing candidate.")
        for promotion in self.state.object_promotion_events:
            if promotion.concept_id not in self.state.concepts:
                raise KernelInvariantError("Object promotion concept is missing.")
            candidate = self.state.object_candidates.get(promotion.report.candidate_id)
            if candidate is None or candidate.promoted_concept_id != promotion.concept_id:
                raise KernelInvariantError("Object promotion candidate lineage is broken.")
            if not self.operation_authorized(
                promotion.council_decision_event_id,
                promotion.report.operation,
            ):
                raise KernelInvariantError("Object promotion lacks Council authorization.")


        manifest_sample_ids: set[str] = set()
        for archive_id, archive in self.state.sensory_archives.items():
            if archive_id != archive.archive_id:
                raise KernelInvariantError("Sensory archive dictionary key drift detected.")
            overlap = manifest_sample_ids.intersection(archive.sample_ids)
            if overlap:
                raise KernelInvariantError("Sensory sample appears in multiple archives.")
            manifest_sample_ids.update(archive.sample_ids)
        if not set(self.state.sensory_samples).issubset(manifest_sample_ids):
            raise KernelInvariantError("Sensory sample is missing from archive manifests.")
        stream_records: dict[str, list[SensorySampleRecord]] = {}
        for sample_id, sample in self.state.sensory_samples.items():
            if sample_id != sample.sample_id:
                raise KernelInvariantError("Sensory sample dictionary key drift detected.")
            archive = self.state.sensory_archives.get(sample.archive_id)
            if archive is None or sample_id not in archive.sample_ids:
                raise KernelInvariantError("Sensory sample archive lineage is broken.")
            observation = self.state.evidence.get(sample.observation_evidence_id)
            translation = self.state.evidence.get(sample.translation_evidence_id)
            if observation is None or observation.kind != EvidenceKind.OBSERVATION:
                raise KernelInvariantError("Sensory sample native observation evidence is invalid.")
            if translation is None or translation.kind != EvidenceKind.TRANSLATION:
                raise KernelInvariantError("Sensory sample translation evidence is invalid.")
            if observation.payload_sha256 != sample.payload_sha256:
                raise KernelInvariantError("Sensory sample payload digest drift detected.")
            stream_records.setdefault(sample.stream_id, []).append(sample)
        for records in stream_records.values():
            records.sort(key=lambda item: (item.sequence_number, item.sample_id))
            prior: SensorySampleRecord | None = None
            seen_sequences: set[int] = set()
            for sample in records:
                if sample.sequence_number in seen_sequences:
                    raise KernelInvariantError("Duplicate sensory stream sequence detected.")
                seen_sequences.add(sample.sequence_number)
                if prior is None:
                    if sample.previous_sample_id is not None:
                        raise KernelInvariantError("First sensory sample has a predecessor.")
                else:
                    if sample.previous_sample_id != prior.sample_id:
                        raise KernelInvariantError("Sensory stream predecessor lineage drift detected.")
                    if sample.timestamp_ns < prior.timestamp_ns:
                        raise KernelInvariantError("Sensory stream timestamp order drift detected.")
                prior = sample
        assigned_samples: set[str] = set()
        assigned_groups: set[str] = set()
        for group_id, group in self.state.synchronization_groups.items():
            if group_id != group.group_id:
                raise KernelInvariantError("Synchronization group dictionary key drift detected.")
            if any(item not in self.state.sensory_samples for item in group.sample_ids):
                raise KernelInvariantError("Synchronization group references missing samples.")
            self._validated_evidence_refs(group.evidence_refs)
            timestamps = [self.state.sensory_samples[item].timestamp_ns for item in group.sample_ids]
            if max(timestamps) - min(timestamps) != group.maximum_skew_ns:
                raise KernelInvariantError("Synchronization group skew drift detected.")
        for event_id, event in self.state.temporal_events.items():
            if event_id != event.event_id:
                raise KernelInvariantError("Temporal event dictionary key drift detected.")
            if any(item not in self.state.sensory_samples for item in event.sample_ids):
                raise KernelInvariantError("Temporal event references missing samples.")
            if any(item not in self.state.synchronization_groups for item in event.synchronization_group_ids):
                raise KernelInvariantError("Temporal event references missing synchronization groups.")
            if assigned_samples.intersection(event.sample_ids):
                raise KernelInvariantError("Sensory sample belongs to multiple temporal events.")
            if assigned_groups.intersection(event.synchronization_group_ids):
                raise KernelInvariantError("Synchronization group belongs to multiple temporal events.")
            assigned_samples.update(event.sample_ids)
            assigned_groups.update(event.synchronization_group_ids)
            self._validated_evidence_refs(event.evidence_refs)
            if any(item not in self.state.sensory_archives for item in event.archive_ids):
                raise KernelInvariantError("Temporal event references missing archives.")
        known_event_ids = set(self.state.temporal_events)
        known_group_ids = set(self.state.synchronization_groups)
        assembly_ids: set[str] = set()
        for assembly in self.state.temporal_event_assembly_events:
            if assembly.assembly_event_id in assembly_ids:
                raise KernelInvariantError("Duplicate temporal event assembly detected.")
            assembly_ids.add(assembly.assembly_event_id)
            if assembly.semantic_mutation_permitted:
                raise KernelInvariantError("Temporal event assembly may not create semantic truth.")
            if not set(assembly.committed_event_ids).issubset(known_event_ids):
                raise KernelInvariantError("Temporal assembly references missing events.")
            if not set(assembly.committed_group_ids).issubset(known_group_ids):
                raise KernelInvariantError("Temporal assembly references missing groups.")

        plasticity_degree: dict[str, int] = {}
        for association_id, association in self.state.plasticity_associations.items():
            if association_id != association.association_id:
                raise KernelInvariantError("Plasticity association dictionary key drift detected.")
            a, b = association.concept_ids
            if a not in self.state.concepts or b not in self.state.concepts:
                raise KernelInvariantError("Plasticity association references a missing concept.")
            self._validated_evidence_refs(association.evidence_refs)
            plasticity_degree[a] = plasticity_degree.get(a, 0) + 1
            plasticity_degree[b] = plasticity_degree.get(b, 0) + 1
            if association.updated_cycle > self.state.cycle:
                raise KernelInvariantError("Plasticity association update lies in the future.")
            if association.last_reinforced_cycle > association.updated_cycle:
                raise KernelInvariantError("Plasticity reinforcement cycle exceeds update cycle.")
        if max(plasticity_degree.values(), default=0) > self.state.plasticity_policy.max_degree:
            raise KernelInvariantError("Plasticity association degree cap exceeded.")
        plasticity_ratio = len(self.state.plasticity_associations) / max(1, len(self.state.concepts))
        if plasticity_ratio > self.state.plasticity_policy.max_edge_ratio + 1e-9:
            raise KernelInvariantError("Plasticity association edge-ratio cap exceeded.")
        plasticity_event_ids: set[str] = set()
        known_workspace_event_ids = {
            item.event_id for item in self.state.workspace_cycle_events
        }
        for event in self.state.plasticity_events:
            if event.event_id in plasticity_event_ids:
                raise KernelInvariantError("Duplicate plasticity event detected.")
            plasticity_event_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Plasticity may not create semantic truth.")
            if event.report.workspace_event_id not in known_workspace_event_ids:
                raise KernelInvariantError("Plasticity event lost workspace lineage.")
            for association in event.report.proposed_associations:
                if any(ref not in self.state.evidence for ref in association.evidence_refs):
                    raise KernelInvariantError("Plasticity history references missing evidence.")

        known_structure_observation_ids: set[str] = set()
        known_plasticity_event_ids = {item.event_id for item in self.state.plasticity_events}
        historical_plasticity_association_ids = set(self.state.plasticity_associations)
        for plasticity_event in self.state.plasticity_events:
            historical_plasticity_association_ids.update(
                item.association_id for item in plasticity_event.report.proposed_associations
            )
        for candidate_id, candidate in self.state.structure_candidates.items():
            if candidate_id != candidate.candidate_id:
                raise KernelInvariantError("Structure candidate dictionary key drift detected.")
            if any(item not in self.state.concepts for item in candidate.member_concept_ids):
                raise KernelInvariantError("Structure candidate references a missing concept.")
            if any(item not in self.state.relations for item in candidate.member_relation_ids):
                raise KernelInvariantError("Structure candidate references a missing relation.")
            if any(item not in historical_plasticity_association_ids for item in candidate.internal_association_ids):
                raise KernelInvariantError("Structure candidate references unknown plastic history.")
            if any(item not in historical_plasticity_association_ids for item in candidate.boundary_association_ids):
                raise KernelInvariantError("Structure candidate boundary references unknown plastic history.")
            self._validated_evidence_refs(candidate.evidence_refs)
            if candidate.field_state_dim not in {0, self.state.field.state_dim}:
                raise KernelInvariantError("Structure candidate field dimension drift detected.")
            if candidate.promoted_structure_id is not None and candidate.promoted_structure_id not in self.state.structures:
                raise KernelInvariantError("Promoted structure candidate lost its structure record.")
        for event in self.state.structure_observation_events:
            if event.event_id in known_structure_observation_ids:
                raise KernelInvariantError("Duplicate structure observation event detected.")
            known_structure_observation_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Structure observation may not create semantic truth.")
            if event.report.plasticity_event_id not in known_plasticity_event_ids:
                raise KernelInvariantError("Structure observation lost plasticity lineage.")
            for candidate in event.report.proposed_candidates:
                self._validated_evidence_refs(candidate.evidence_refs)
        known_decision_ids = {item.decision_event_id for item in self.state.council_decisions}
        for structure_id, structure in self.state.structures.items():
            if structure_id != structure.structure_id:
                raise KernelInvariantError("Structure dictionary key drift detected.")
            candidate = self.state.structure_candidates.get(structure.source_candidate_id)
            if candidate is None:
                raise KernelInvariantError("Structure lost its source candidate.")
            if structure.lineage_parent_structure_id is None:
                if candidate.promoted_structure_id != structure_id:
                    raise KernelInvariantError("Structure/candidate promotion lineage drift detected.")
            else:
                if structure.lineage_parent_structure_id not in self.state.structures:
                    raise KernelInvariantError("Refolded structure lost its parent lineage.")
                if structure.lineage_root_structure_id not in self.state.structures:
                    raise KernelInvariantError("Refolded structure lost its root lineage.")
                if any(item not in self.state.structural_challenges for item in structure.refold_basis_challenge_ids):
                    raise KernelInvariantError("Refolded structure lost challenge lineage.")
            if any(item not in self.state.concepts for item in structure.member_concept_ids):
                raise KernelInvariantError("Structure references a missing concept.")
            if any(item not in self.state.relations for item in structure.member_relation_ids):
                raise KernelInvariantError("Structure references a missing relation.")
            if any(item not in historical_plasticity_association_ids for item in structure.internal_association_ids):
                raise KernelInvariantError("Structure references unknown plastic history.")
            self._validated_evidence_refs(structure.evidence_refs)
            if structure.council_decision_event_id not in known_decision_ids:
                raise KernelInvariantError("Structure lacks Council promotion authorization.")
        seen_structure_promotions: set[str] = set()
        for event in self.state.structure_promotion_events:
            if event.event_id in seen_structure_promotions:
                raise KernelInvariantError("Duplicate structure promotion event detected.")
            seen_structure_promotions.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Structure promotion may not create semantic truth.")
            if event.structure_id not in self.state.structures:
                raise KernelInvariantError("Structure promotion event lost its structure.")
            if event.council_decision_event_id not in known_decision_ids:
                raise KernelInvariantError("Structure promotion event lost Council authorization.")

        if tuple(sorted(set(self.state.ablated_structure_ids))) != self.state.ablated_structure_ids:
            raise KernelInvariantError("Ablated structure IDs must be sorted and unique.")
        if any(item not in self.state.structures for item in self.state.ablated_structure_ids):
            raise KernelInvariantError("Ablation state references a missing structure.")
        availability_ids: set[str] = set()
        for event in self.state.structure_availability_events:
            if event.event_id in availability_ids:
                raise KernelInvariantError("Duplicate structure availability event detected.")
            availability_ids.add(event.event_id)
            if event.structure_id not in self.state.structures:
                raise KernelInvariantError("Structure availability history lost its structure.")
        compilation_event_ids: set[str] = set()
        for event in self.state.compilation_probe_events:
            if event.event_id in compilation_event_ids:
                raise KernelInvariantError("Duplicate compilation probe event detected.")
            compilation_event_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Compilation probes may not mutate semantics.")
            if event.report.structure_id is not None and event.report.structure_id not in self.state.structures:
                raise KernelInvariantError("Compilation history lost its structure operand.")

        for challenge_id, challenge in self.state.structural_challenges.items():
            if challenge_id != challenge.challenge_id:
                raise KernelInvariantError("Structural challenge dictionary key drift detected.")
            if challenge.structure_id not in self.state.structures:
                raise KernelInvariantError("Structural challenge lost its target structure.")
            parent = self.state.structures[challenge.structure_id]
            if not any(item.concept_ids == challenge.concept_ids for item in parent.internal_edge_snapshots):
                raise KernelInvariantError("Structural challenge no longer targets a frozen parent edge.")
            for observation in challenge.observations:
                self._validated_evidence_refs(observation.evidence_refs)
        refold_event_ids: set[str] = set()
        for event in self.state.structure_refold_events:
            if event.event_id in refold_event_ids:
                raise KernelInvariantError("Duplicate structure refold event detected.")
            refold_event_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Structure refolding may not create semantic truth.")
            if event.report.parent_structure_id not in self.state.structures:
                raise KernelInvariantError("Refold history lost its parent structure.")
            for structure_id in event.produced_structure_ids:
                if structure_id not in self.state.structures:
                    raise KernelInvariantError("Refold history lost a produced structure.")
            if event.council_decision_event_id is not None and event.council_decision_event_id not in known_decision_ids:
                raise KernelInvariantError("Refold event lost Council authorization.")

        interaction_event_ids: set[str] = set()
        for event in self.state.structure_interaction_events:
            if event.event_id in interaction_event_ids:
                raise KernelInvariantError("Duplicate structure interaction event detected.")
            interaction_event_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Structure interaction may not mutate semantics.")
            if event.report.source_structure_id not in self.state.structures:
                raise KernelInvariantError("Structure interaction history lost its source structure.")
            for candidate in event.report.candidates:
                if candidate.target_structure_id not in self.state.structures:
                    raise KernelInvariantError("Structure interaction history lost a target structure.")

        hierarchy_observation_ids: set[str] = set()
        for candidate_id, candidate in self.state.hierarchy_candidates.items():
            if candidate_id != candidate.candidate_id:
                raise KernelInvariantError("Hierarchy candidate dictionary key drift detected.")
            if any(item not in self.state.structures for item in candidate.member_structure_ids):
                raise KernelInvariantError("Hierarchy candidate references missing earned structures.")
            if any(item not in interaction_event_ids for item in candidate.interaction_event_ids):
                raise KernelInvariantError("Hierarchy candidate lost interaction lineage.")
            self._validated_evidence_refs(candidate.evidence_refs)
            if (
                candidate.promoted_layered_structure_id is not None
                and candidate.promoted_layered_structure_id not in self.state.layered_structures
            ):
                raise KernelInvariantError("Promoted hierarchy candidate lost its layered structure.")
        for event in self.state.hierarchy_observation_events:
            if event.event_id in hierarchy_observation_ids:
                raise KernelInvariantError("Duplicate hierarchy observation event detected.")
            hierarchy_observation_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Hierarchy observation may not mutate semantics.")
            if event.report.latest_interaction_event_id not in interaction_event_ids:
                raise KernelInvariantError("Hierarchy observation lost interaction lineage.")
        for layered_id, layered in self.state.layered_structures.items():
            if layered_id != layered.layered_structure_id:
                raise KernelInvariantError("Layered structure dictionary key drift detected.")
            candidate = self.state.hierarchy_candidates.get(layered.source_candidate_id)
            if candidate is None:
                raise KernelInvariantError("Layered structure lost its source candidate.")
            if candidate.promoted_layered_structure_id != layered_id:
                raise KernelInvariantError("Layered structure/candidate lineage drift detected.")
            if any(item not in self.state.structures for item in layered.member_structure_ids):
                raise KernelInvariantError("Layered structure references missing lower-level structures.")
            self._validated_evidence_refs(layered.evidence_refs)
            if layered.council_decision_event_id not in known_decision_ids:
                raise KernelInvariantError("Layered structure lacks Council promotion authorization.")
        hierarchy_promotion_ids: set[str] = set()
        for event in self.state.hierarchy_promotion_events:
            if event.event_id in hierarchy_promotion_ids:
                raise KernelInvariantError("Duplicate hierarchy promotion event detected.")
            hierarchy_promotion_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Hierarchy promotion may not mutate semantics.")
            if event.layered_structure_id not in self.state.layered_structures:
                raise KernelInvariantError("Hierarchy promotion history lost its layered structure.")
            if event.council_decision_event_id not in known_decision_ids:
                raise KernelInvariantError("Hierarchy promotion lost Council authorization.")
        if tuple(sorted(set(self.state.ablated_layered_structure_ids))) != self.state.ablated_layered_structure_ids:
            raise KernelInvariantError("Ablated layered structure IDs must be sorted and unique.")
        if any(item not in self.state.layered_structures for item in self.state.ablated_layered_structure_ids):
            raise KernelInvariantError("Layered ablation references a missing layered structure.")
        layered_availability_ids: set[str] = set()
        for event in self.state.layered_structure_availability_events:
            if event.event_id in layered_availability_ids:
                raise KernelInvariantError("Duplicate layered structure availability event detected.")
            layered_availability_ids.add(event.event_id)
            if event.layered_structure_id not in self.state.layered_structures:
                raise KernelInvariantError("Layered availability history lost its structure.")
        layered_probe_ids: set[str] = set()
        for event in self.state.layered_probe_events:
            if event.event_id in layered_probe_ids:
                raise KernelInvariantError("Duplicate layered probe event detected.")
            layered_probe_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Layered probes may not mutate semantics.")
            if event.report.query_structure_id not in self.state.structures:
                raise KernelInvariantError("Layered probe history lost its query structure.")
            if (
                event.report.layered_structure_id is not None
                and event.report.layered_structure_id not in self.state.layered_structures
            ):
                raise KernelInvariantError("Layered probe history lost its higher-order operand.")
            if any(item not in self.state.structures for item in event.report.matched_structure_ids):
                raise KernelInvariantError("Layered probe history lost matched structures.")

        allocated = sum(item.allocated_resource for item in self.state.workspace_items.values())
        if allocated > self.state.workspace_policy.resource_budget + 1e-9:
            raise KernelInvariantError("Active workspace exceeds its resource budget.")
        if len(self.state.workspace_items) > self.state.workspace_policy.max_active_items:
            raise KernelInvariantError("Active workspace exceeds its slot bound.")
        known_workspace_reports = {
            event.report.report_id for event in self.state.workspace_cycle_events
        }
        for item_id, item in self.state.workspace_items.items():
            if item_id != item.item_id:
                raise KernelInvariantError("Workspace item dictionary key drift detected.")
            self._validated_evidence_refs(item.evidence_refs)
            if item.admission_report_id not in known_workspace_reports:
                raise KernelInvariantError("Workspace item lacks admission lineage.")
            if item.source_kind == WorkspaceSourceKind.AUTHORIZED_ACTION:
                if item.operation is None:
                    raise KernelInvariantError("Workspace action lacks an operation.")
                if not self.operation_authorized(item.source_ref, item.operation):
                    raise KernelInvariantError("Workspace action lacks Council authorization.")
            if item.source_kind == WorkspaceSourceKind.EARNED_STRUCTURE:
                structure = self.state.structures.get(item.source_ref)
                if structure is None:
                    raise KernelInvariantError("Workspace earned structure source is missing.")
                if item.source_ref in self.state.ablated_structure_ids:
                    raise KernelInvariantError("Ablated structure remains active in workspace.")
                if not set(item.binding_refs).issubset(set(structure.member_concept_ids)):
                    raise KernelInvariantError("Workspace earned structure binding escaped its members.")
        known_workspace_items = set(self.state.workspace_items)
        event_ids: set[str] = set()
        for event in self.state.workspace_cycle_events:
            if event.event_id in event_ids:
                raise KernelInvariantError("Duplicate workspace cycle event detected.")
            event_ids.add(event.event_id)
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Workspace cycle may not mutate semantics.")
            if event.report.total_allocated_resource > event.report.resource_budget + 1e-9:
                raise KernelInvariantError("Historical workspace event exceeded its budget.")
        for event in self.state.workspace_writeback_events:
            if event.semantic_mutation_permitted:
                raise KernelInvariantError("Workspace writeback may not mutate semantics.")
            self._validated_evidence_refs(event.evidence_refs)
            if (
                event.disposition == WorkspaceWritebackDisposition.RESOLVE
                and event.item_snapshot.item_id in known_workspace_items
                and not any(
                    later.committed_cycle > event.committed_cycle
                    and event.item_snapshot.item_id in later.active_item_ids
                    for later in self.state.workspace_cycle_events
                )
            ):
                raise KernelInvariantError("Resolved workspace item remained active.")

        for decision in self.state.council_decisions:
            if decision.semantic_mutation_permitted:
                raise KernelInvariantError(
                    "Council decisions may not mutate semantic truth."
                )
            if decision.governance_policy_mutation_permitted:
                raise KernelInvariantError(
                    "Council decisions may not silently mutate governance policy."
                )
            self._validate_council_report_refs(decision.report)
            if decision.evidence_refs:
                self._validated_evidence_refs(decision.evidence_refs)
        known_decisions = {
            item.decision_event_id for item in self.state.council_decisions
        }
        seen_outcomes: set[str] = set()
        for outcome in self.state.governance_outcomes:
            if outcome.decision_event_id not in known_decisions:
                raise KernelInvariantError(
                    "Governance outcome references a missing Council decision."
                )
            if outcome.decision_event_id in seen_outcomes:
                raise KernelInvariantError(
                    "Multiple governance outcomes reference one Council decision."
                )
            seen_outcomes.add(outcome.decision_event_id)
            self._validated_evidence_refs(outcome.evidence_refs)
            if not any(
                self.state.evidence[item].kind == EvidenceKind.OUTCOME
                for item in outcome.evidence_refs
            ):
                raise KernelInvariantError(
                    "Governance outcome lacks physical outcome evidence."
                )
