from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from verdant_kernel import (
    ExperienceCommand,
    ExperienceResult,
    ResonanceEvent,
    ResonanceReport,
    WorkspaceCandidateInput,
    WorkspaceSignals,
    WorkspaceSourceKind,
    VerdantKernel,
)
from verdant_workspace import VerdantWorkspacePipeline, WorkspaceCycleResult
from verdant_plasticity import PlasticityCycleResult, VerdantPlasticityPipeline
from verdant_structures import StructureObservationResult, VerdantStructurePipeline


@dataclass(frozen=True)
class DevelopmentalCycleConfig:
    """Policy for one bounded developmental heartbeat.

    Milestone 12 deliberately does *not* add semantic writeback.  It connects
    already-audited mechanisms into one atomic path:

        experience -> ECWF field -> resonance -> bounded workspace
                   -> bounded local plasticity

    Plasticity remains nonsemantic: it may alter developmental association
    traces, but it cannot silently add canonical concepts, relations, or claims.
    Earned-structure proposals remain a later milestone.
    """

    resonance_top_k: int = 6
    resonance_commit_limit: int = 4
    scope_to_active_shard: bool = True
    current_evidence_resource: float = 0.30
    resonance_resource: float = 0.10
    association_resource: float = 0.08
    association_recall_threshold: float = 0.24
    structure_resource: float = 0.06
    structure_trigger_members: int = 1
    current_evidence_persistence: int = 1
    resonance_persistence: int = 1

    def __post_init__(self) -> None:
        if self.resonance_top_k < 1:
            raise ValueError("resonance_top_k must be at least 1.")
        if self.resonance_commit_limit < 0:
            raise ValueError("resonance_commit_limit cannot be negative.")
        if self.resonance_commit_limit > self.resonance_top_k:
            raise ValueError(
                "resonance_commit_limit cannot exceed resonance_top_k."
            )
        for name, value in (
            ("current_evidence_resource", self.current_evidence_resource),
            ("resonance_resource", self.resonance_resource),
            ("association_resource", self.association_resource),
            ("structure_resource", self.structure_resource),
        ):
            if value <= 0.0:
                raise ValueError(f"{name} must be positive.")
        if not 0.0 <= self.association_recall_threshold <= 1.0:
            raise ValueError("association_recall_threshold must be between 0 and 1.")
        if self.structure_trigger_members < 1:
            raise ValueError("structure_trigger_members must be at least 1.")
        for name, value in (
            ("current_evidence_persistence", self.current_evidence_persistence),
            ("resonance_persistence", self.resonance_persistence),
        ):
            if value < 1:
                raise ValueError(f"{name} must be at least 1.")


@dataclass(frozen=True)
class DevelopmentalCycleResult:
    experience: ExperienceResult
    resonance_report: ResonanceReport | None
    resonance_event: ResonanceEvent | None
    workspace: WorkspaceCycleResult | None
    plasticity: PlasticityCycleResult | None
    structures: StructureObservationResult | None
    starting_fingerprint: str
    ending_fingerprint: str
    candidate_scope_ids: tuple[str, ...]
    semantic_counts_after_experience: tuple[int, int, int, int, int, int]
    semantic_counts_after_cycle: tuple[int, int, int, int, int, int]
    replayed: bool = False

    @property
    def semantic_firewall_held(self) -> bool:
        """True when downstream resonance/workspace did not invent semantics."""

        return self.semantic_counts_after_experience == self.semantic_counts_after_cycle


class VerdantDevelopmentPipeline:
    """Atomic orchestration of the rebuild's first developmental heartbeat.

    The public ``advance`` method stages the complete heartbeat on a cloned
    kernel.  The caller's canonical kernel is replaced only if *every* stage
    succeeds and the semantic firewall remains intact.  This prevents a
    resonance/workspace failure from leaving a half-committed experience.

    No new semantic relation or concept is inferred here.  Milestone 13 adds
    a bounded nonsemantic association layer after workspace broadcast; earned
    structures remain a later milestone.
    """

    def __init__(
        self,
        *,
        workspace: VerdantWorkspacePipeline | None = None,
        plasticity: VerdantPlasticityPipeline | None = None,
        structures: VerdantStructurePipeline | None = None,
        config: DevelopmentalCycleConfig | None = None,
    ) -> None:
        self.workspace = workspace or VerdantWorkspacePipeline()
        self.plasticity = plasticity or VerdantPlasticityPipeline()
        self.structures = structures or VerdantStructurePipeline()
        self.config = config or DevelopmentalCycleConfig()

    @staticmethod
    def _semantic_counts(kernel: VerdantKernel) -> tuple[int, int, int, int, int, int]:
        return (
            len(kernel.state.evidence),
            len(kernel.state.concepts),
            len(kernel.state.relations),
            len(kernel.state.claims),
            len(kernel.state.contradictions),
            len(kernel.state.revisions),
        )

    def _candidate_scope(self, kernel: VerdantKernel) -> tuple[str, ...]:
        if not self.config.scope_to_active_shard:
            return tuple(sorted(kernel.state.concepts))
        shard = kernel.state.shards[kernel.state.active_shard_id]
        return tuple(sorted(shard.concept_ids))

    @staticmethod
    def _experience_evidence(result: ExperienceResult) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    result.observation_evidence_id,
                    result.translation_evidence_id,
                    *result.additional_evidence_ids,
                }
            )
        )

    def _association_recall_candidates(
        self,
        kernel: VerdantKernel,
        experience: ExperienceResult,
    ) -> tuple[WorkspaceCandidateInput, ...]:
        current = set(experience.concept_ids)
        if not current or not kernel.state.plasticity_associations:
            return ()
        recalled: list[WorkspaceCandidateInput] = []
        for association in sorted(
            kernel.state.plasticity_associations.values(),
            key=lambda item: (-item.strength, item.association_id),
        ):
            if association.strength < self.config.association_recall_threshold:
                continue
            overlap = current.intersection(association.concept_ids)
            if not overlap:
                continue
            neighbors = [
                concept_id
                for concept_id in association.concept_ids
                if concept_id not in current
            ]
            if not neighbors:
                continue
            for neighbor_id in neighbors:
                concept = kernel.state.concepts[neighbor_id]
                recalled.append(
                    WorkspaceCandidateInput(
                        source_kind=WorkspaceSourceKind.LOCAL_ASSOCIATION,
                        source_ref=association.association_id,
                        label=f"learned local recall: {concept.label}",
                        evidence_refs=association.evidence_refs,
                        resource_request=self.config.association_resource,
                        persistence_cycles=1,
                        signals=WorkspaceSignals(
                            evidence_grounding=0.80,
                            relevance=max(0.45, association.strength),
                            novelty=0.20,
                            resonance=association.strength,
                        ),
                        binding_refs=(neighbor_id,),
                        metadata={
                            "developmental_stage": "local_association_recall",
                            "trigger_concept_ids": tuple(sorted(overlap)),
                            "association_strength": association.strength,
                        },
                    )
                )
        # Workspace source keys must be unique.  A two-endpoint association can
        # only produce one neighbor for a given current concept set, so source
        # ref is sufficient for deterministic deduplication here.
        unique: dict[str, WorkspaceCandidateInput] = {}
        for item in recalled:
            prior = unique.get(item.source_ref)
            if prior is None or item.signals.relevance > prior.signals.relevance:
                unique[item.source_ref] = item
        return tuple(unique[key] for key in sorted(unique))

    def _structure_workspace_candidates(
        self,
        kernel: VerdantKernel,
        experience: ExperienceResult,
    ) -> tuple[WorkspaceCandidateInput, ...]:
        current = set(experience.concept_ids)
        if not current or not kernel.state.structures:
            return ()
        results: list[WorkspaceCandidateInput] = []
        for structure in sorted(
            kernel.state.structures.values(), key=lambda item: item.structure_id
        ):
            if not kernel.structure_is_available(structure.structure_id):
                continue
            overlap = current.intersection(structure.member_concept_ids)
            if len(overlap) < self.config.structure_trigger_members:
                continue
            relevance = max(
                kernel.state.compilation_policy.structure_relevance_floor,
                structure.quality_at_promotion.reconstructability,
            )
            results.append(
                WorkspaceCandidateInput(
                    source_kind=WorkspaceSourceKind.EARNED_STRUCTURE,
                    source_ref=structure.structure_id,
                    label=f"earned structure operand: {structure.opaque_name}",
                    evidence_refs=structure.evidence_refs,
                    resource_request=min(
                        self.config.structure_resource,
                        kernel.state.workspace_policy.resource_budget,
                    ),
                    persistence_cycles=min(
                        kernel.state.compilation_policy.structure_workspace_persistence,
                        kernel.state.workspace_policy.maximum_persistence_cycles,
                    ),
                    signals=WorkspaceSignals(
                        evidence_grounding=0.90,
                        relevance=max(0.0, min(1.0, relevance)),
                        novelty=0.12,
                        resonance=max(
                            0.0,
                            min(1.0, structure.quality_at_promotion.internal_cohesion),
                        ),
                    ),
                    binding_refs=structure.member_concept_ids,
                    metadata={
                        "developmental_stage": "compiled_structure_operand",
                        "trigger_concept_ids": tuple(sorted(overlap)),
                        "source_candidate_id": structure.source_candidate_id,
                        "semantic_label_preinstalled": False,
                    },
                )
            )
        return tuple(results)

    def _workspace_candidates(
        self,
        kernel: VerdantKernel,
        experience: ExperienceResult,
        resonance_event: ResonanceEvent,
    ) -> tuple[WorkspaceCandidateInput, ...]:
        evidence_refs = self._experience_evidence(experience)
        current = WorkspaceCandidateInput(
            source_kind=WorkspaceSourceKind.CURRENT_EVIDENCE,
            source_ref=experience.observation_evidence_id,
            label=f"current experience: {experience.event_key}",
            evidence_refs=evidence_refs,
            resource_request=self.config.current_evidence_resource,
            persistence_cycles=self.config.current_evidence_persistence,
            signals=WorkspaceSignals(
                evidence_grounding=1.0,
                relevance=0.90,
                prediction_error=0.15,
                novelty=0.35,
            ),
            binding_refs=tuple(sorted(set(experience.concept_ids))),
            metadata={
                "developmental_stage": "current_experience",
                "experience_event_key": experience.event_key,
            },
        )

        resonance_inputs: list[WorkspaceCandidateInput] = []
        by_attention_id = {
            attention_id: kernel.state.attention_candidates[attention_id]
            for attention_id in resonance_event.attention_candidate_ids
        }
        for attention_id in resonance_event.attention_candidate_ids:
            attention = by_attention_id[attention_id]
            concept = kernel.state.concepts.get(attention.source_ref)
            label = concept.label if concept is not None else attention.source_ref
            score = max(0.0, min(1.0, attention.priority))
            resonance_inputs.append(
                WorkspaceCandidateInput(
                    source_kind=WorkspaceSourceKind.RESONANCE,
                    source_ref=attention_id,
                    label=f"resonant possibility: {label}",
                    evidence_refs=tuple(sorted(attention.evidence_refs)),
                    resource_request=self.config.resonance_resource,
                    persistence_cycles=self.config.resonance_persistence,
                    signals=WorkspaceSignals(
                        evidence_grounding=0.70,
                        relevance=score,
                        novelty=0.25,
                        resonance=score,
                    ),
                    binding_refs=(attention.source_ref,),
                    metadata={
                        "developmental_stage": "resonant_recall",
                        "resonance_event_id": resonance_event.resonance_event_id,
                        "resonance_score": score,
                    },
                )
            )

        association_inputs = self._association_recall_candidates(
            kernel, experience
        )
        structure_inputs = self._structure_workspace_candidates(kernel, experience)

        contradiction_inputs: list[WorkspaceCandidateInput] = []
        for contradiction_id in experience.contradiction_ids:
            contradiction = kernel.state.contradictions[contradiction_id]
            contradiction_inputs.append(
                WorkspaceCandidateInput(
                    source_kind=WorkspaceSourceKind.CONTRADICTION,
                    source_ref=contradiction_id,
                    label=f"active contradiction: {contradiction_id}",
                    evidence_refs=tuple(sorted(contradiction.evidence_refs)),
                    resource_request=min(0.16, kernel.state.workspace_policy.resource_budget),
                    persistence_cycles=min(
                        2, kernel.state.workspace_policy.maximum_persistence_cycles
                    ),
                    signals=WorkspaceSignals(
                        evidence_grounding=1.0,
                        relevance=0.85,
                        prediction_error=0.90,
                        contradiction_pressure=1.0,
                        novelty=0.55,
                    ),
                    binding_refs=tuple(sorted(contradiction.claim_ids)),
                    metadata={
                        "developmental_stage": "contradiction_pressure",
                        "experience_event_key": experience.event_key,
                    },
                )
            )

        return (
            current,
            *structure_inputs,
            *association_inputs,
            *resonance_inputs,
            *contradiction_inputs,
        )

    def _advance_staged(
        self,
        kernel: VerdantKernel,
        command: ExperienceCommand,
    ) -> DevelopmentalCycleResult:
        starting_fingerprint = kernel.fingerprint()
        experience = kernel.apply_experience(command)
        if experience.replayed:
            # A replay is deliberately a no-op at the orchestration layer.  We
            # do not create duplicate attention or workspace events for an
            # already-consumed experience.
            counts = self._semantic_counts(kernel)
            return DevelopmentalCycleResult(
                experience=experience,
                resonance_report=None,
                resonance_event=None,
                workspace=None,
                plasticity=None,
                structures=None,
                starting_fingerprint=starting_fingerprint,
                ending_fingerprint=kernel.fingerprint(),
                candidate_scope_ids=(),
                semantic_counts_after_experience=counts,
                semantic_counts_after_cycle=counts,
                replayed=True,
            )

        semantic_after_experience = self._semantic_counts(kernel)
        evidence_refs = self._experience_evidence(experience)
        scope = self._candidate_scope(kernel)

        resonance_report = kernel.inspect_resonance(
            command.feature_vector,
            command.modality,
            top_k=self.config.resonance_top_k,
            candidate_concept_ids=scope,
        )
        resonance_event = kernel.commit_resonance(
            resonance_report,
            evidence_refs=evidence_refs,
            max_candidates=self.config.resonance_commit_limit,
            resource_request=self.config.resonance_resource,
        )
        workspace_result = self.workspace.run_cycle(
            kernel,
            self._workspace_candidates(kernel, experience, resonance_event),
        )
        plasticity_result = self.plasticity.run_cycle(
            kernel,
            workspace_result.event,
        )
        structure_result = self.structures.run_cycle(kernel)

        semantic_after_cycle = self._semantic_counts(kernel)
        result = DevelopmentalCycleResult(
            experience=experience,
            resonance_report=resonance_report,
            resonance_event=resonance_event,
            workspace=workspace_result,
            plasticity=plasticity_result,
            structures=structure_result,
            starting_fingerprint=starting_fingerprint,
            ending_fingerprint=kernel.fingerprint(),
            candidate_scope_ids=scope,
            semantic_counts_after_experience=semantic_after_experience,
            semantic_counts_after_cycle=semantic_after_cycle,
            replayed=False,
        )
        if not result.semantic_firewall_held:
            raise RuntimeError(
                "Developmental downstream stages created semantic state; "
                "Milestone 12 requires resonance/workspace to remain nonsemantic."
            )
        return result

    def advance(
        self,
        kernel: VerdantKernel,
        command: ExperienceCommand,
    ) -> DevelopmentalCycleResult:
        """Advance one experience atomically through the developmental foreground."""

        staged = VerdantKernel.from_state(kernel.snapshot())
        result = self._advance_staged(staged, command)
        kernel.state = staged.snapshot()
        return result
