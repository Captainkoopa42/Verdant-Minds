from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDecisionEvent,
    GovernanceProposalKind,
    StructureCandidateRecord,
    StructureCandidateStatus,
    StructureObservationEvent,
    StructureObservationReport,
    StructurePromotionDisposition,
    StructurePromotionEvent,
    StructurePromotionReport,
    StructureQualityVector,
    StructureStaleError,
    VerdantKernel,
    WorkspaceSourceKind,
)
from verdant_kernel.models import canonical_json_bytes, stable_id


@dataclass(frozen=True)
class StructureObservationResult:
    report: StructureObservationReport
    event: StructureObservationEvent


@dataclass(frozen=True)
class StructurePromotionResult:
    report: StructurePromotionReport
    decision: CouncilDecisionEvent
    event: StructurePromotionEvent


class VerdantStructurePipeline:
    """Milestone 14 observer for earned relational structures.

    The observer never assigns a human semantic label. It looks only for
    recurring, bounded relational configurations that arise in the learned
    plastic layer, then measures whether treating those configurations as a
    stable unit is defensible. Candidate observation is nonsemantic; promotion
    creates a new opaque cognitive operand, not a canonical concept or claim.
    """

    @staticmethod
    def _scope(kernel: VerdantKernel) -> set[str]:
        policy = kernel.state.structure_policy
        if not policy.scope_to_active_shard:
            return set(kernel.state.concepts)
        return set(kernel.state.shards[kernel.state.active_shard_id].concept_ids)

    @staticmethod
    def _latest_current_concepts(kernel: VerdantKernel) -> set[str]:
        if not kernel.state.workspace_cycle_events:
            return set()
        result: set[str] = set()
        for item in kernel.state.workspace_items.values():
            if item.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE:
                result.update(
                    ref for ref in item.binding_refs if ref in kernel.state.concepts
                )
        return result

    @staticmethod
    def _contexts(kernel: VerdantKernel, evidence_refs: Iterable[str]) -> set[str]:
        # Multiple evidence records (native observation, translation, semantic
        # support) are normally emitted for one event. They must not masquerade
        # as multiple contexts. Prefer an explicit context_id found anywhere in
        # the event; otherwise all unspecified events share one conservative
        # context bucket.
        explicit_by_event: dict[str, str] = {}
        event_keys: set[str] = set()
        for evidence_id in evidence_refs:
            evidence = kernel.state.evidence[evidence_id]
            event_keys.add(evidence.event_key)
            context = evidence.details.get("context_id")
            if context is not None:
                explicit_by_event[evidence.event_key] = str(context)
        return {explicit_by_event.get(event_key, "unspecified") for event_key in event_keys}

    @staticmethod
    def _event_keys(kernel: VerdantKernel, evidence_refs: Iterable[str]) -> set[str]:
        return {kernel.state.evidence[item].event_key for item in evidence_refs}

    @staticmethod
    def _field_prototype(
        kernel: VerdantKernel,
        member_ids: tuple[str, ...],
    ) -> tuple[int, tuple[float, ...], tuple[float, ...], str]:
        vectors: list[np.ndarray] = []
        for concept_id in member_ids:
            profile = kernel.state.resonance_profiles.get(concept_id)
            if profile is not None:
                vector = np.asarray(profile.real, dtype=np.float64) + 1j * np.asarray(
                    profile.imag, dtype=np.float64
                )
                vectors.append(vector)
                continue
            address = kernel.state.field_addresses.get(concept_id)
            if address is not None:
                vector = np.asarray(address.real, dtype=np.float64) + 1j * np.asarray(
                    address.imag, dtype=np.float64
                )
                vectors.append(vector)
        if not vectors:
            return 0, (), (), ""
        mean = np.mean(np.stack(vectors), axis=0)
        norm = float(np.linalg.norm(mean))
        if norm <= 1e-12:
            return 0, (), (), ""
        mean = mean / norm
        real = tuple(float(item) for item in mean.real.tolist())
        imag = tuple(float(item) for item in mean.imag.tolist())
        digest = hashlib.sha256(
            canonical_json_bytes({"real": real, "imag": imag})
        ).hexdigest()
        return len(real), real, imag, digest

    @staticmethod
    def _canonical_relations(
        kernel: VerdantKernel,
        member_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        members = set(member_ids)
        return tuple(
            sorted(
                relation_id
                for relation_id, relation in kernel.state.relations.items()
                if relation.source_concept_id in members
                and relation.target_concept_id in members
            )
        )

    @staticmethod
    def _associations_for_members(
        kernel: VerdantKernel,
        member_ids: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        members = set(member_ids)
        internal: list[str] = []
        boundary: list[str] = []
        for association_id, association in kernel.state.plasticity_associations.items():
            endpoint_count = len(members.intersection(association.concept_ids))
            if endpoint_count == 2:
                internal.append(association_id)
            elif endpoint_count == 1:
                boundary.append(association_id)
        return tuple(sorted(internal)), tuple(sorted(boundary))

    @staticmethod
    def _quality(
        kernel: VerdantKernel,
        *,
        member_ids: tuple[str, ...],
        internal_ids: tuple[str, ...],
        boundary_ids: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        occurrence_count: int,
    ) -> StructureQualityVector:
        policy = kernel.state.structure_policy
        internal = [kernel.state.plasticity_associations[item] for item in internal_ids]
        boundary = [kernel.state.plasticity_associations[item] for item in boundary_ids]
        possible = max(1, len(member_ids) * (len(member_ids) - 1) // 2)
        edge_coverage = min(1.0, len(internal) / possible)
        mean_strength = (
            sum(item.strength for item in internal) / len(internal) if internal else 0.0
        )
        # Reconstructability is deliberately not identical to raw density. A
        # sparse but strong structure can score reasonably; a dense set of weak
        # accidental traces cannot.
        reconstructability = math.sqrt(max(0.0, edge_coverage * mean_strength))
        internal_strength = sum(item.strength for item in internal)
        boundary_strength = sum(item.strength for item in boundary)
        boundary_selectivity = (
            internal_strength / (internal_strength + boundary_strength)
            if internal_strength + boundary_strength > 0.0
            else 0.0
        )
        event_count = len(VerdantStructurePipeline._event_keys(kernel, evidence_refs))
        context_count = len(VerdantStructurePipeline._contexts(kernel, evidence_refs))
        return StructureQualityVector(
            recurrence=min(1.0, occurrence_count / policy.minimum_recurrence_events),
            reconstructability=max(0.0, min(1.0, reconstructability)),
            boundary_selectivity=max(0.0, min(1.0, boundary_selectivity)),
            internal_cohesion=max(0.0, min(1.0, mean_strength)),
            evidence_diversity=min(1.0, event_count / policy.minimum_evidence_events),
            cross_context_stability=min(1.0, context_count / policy.minimum_contexts),
            perturbation_survival=0.0,
            compression_gain=0.0,
            contradiction_tolerance=1.0,
        )

    @staticmethod
    def _eligible(kernel: VerdantKernel, quality: StructureQualityVector, occurrence_count: int) -> bool:
        policy = kernel.state.structure_policy
        return (
            occurrence_count >= policy.minimum_recurrence_events
            and quality.reconstructability >= policy.minimum_reconstructability
            and quality.boundary_selectivity >= policy.minimum_boundary_selectivity
            and quality.internal_cohesion >= policy.minimum_internal_cohesion
            and quality.evidence_diversity >= 1.0
            and quality.cross_context_stability >= 1.0
        )

    def _candidate_memberships(self, kernel: VerdantKernel) -> tuple[tuple[str, ...], ...]:
        policy = kernel.state.structure_policy
        scope = self._scope(kernel)
        seeds = self._latest_current_concepts(kernel).intersection(scope)
        if not seeds:
            return ()
        eligible = [
            association
            for association in kernel.state.plasticity_associations.values()
            if association.strength >= policy.minimum_member_association_strength
            and set(association.concept_ids).issubset(scope)
        ]
        incident: dict[str, list] = {}
        for association in eligible:
            for concept_id in association.concept_ids:
                incident.setdefault(concept_id, []).append(association)
        memberships: dict[tuple[str, ...], float] = {}
        for seed in sorted(seeds):
            ranked = sorted(
                incident.get(seed, []),
                key=lambda item: (-item.strength, item.association_id),
            )[: policy.maximum_neighbors_per_seed]
            members = {seed}
            score = 0.0
            for association in ranked:
                members.update(association.concept_ids)
                score += association.strength
                if len(members) >= policy.maximum_members:
                    break
            # If a seed only has one strong edge, allow one deterministic second
            # hop so a three-member candidate can emerge without global spread.
            if len(members) < policy.minimum_members:
                first_hop = sorted(members - {seed})
                for hop in first_hop:
                    for association in sorted(
                        incident.get(hop, []),
                        key=lambda item: (-item.strength, item.association_id),
                    ):
                        members.update(association.concept_ids)
                        score += association.strength
                        if len(members) >= policy.minimum_members:
                            break
                    if len(members) >= policy.minimum_members:
                        break
            if not policy.minimum_members <= len(members) <= policy.maximum_members:
                continue
            membership = tuple(sorted(members))
            internal, _ = self._associations_for_members(kernel, membership)
            if len(internal) < len(membership) - 1:
                continue
            memberships[membership] = max(memberships.get(membership, 0.0), score)
        ranked_memberships = sorted(
            memberships.items(), key=lambda item: (-item[1], item[0])
        )[: policy.maximum_candidates_per_cycle]
        return tuple(item[0] for item in ranked_memberships)

    def inspect(self, kernel: VerdantKernel) -> StructureObservationReport | None:
        if not kernel.state.plasticity_events:
            return None
        memberships = self._candidate_memberships(kernel)
        if not memberships:
            return None
        policy = kernel.state.structure_policy
        structural = kernel.structure_structural_fingerprint()
        prospective_cycle = kernel.state.cycle + 1
        latest_plasticity = kernel.state.plasticity_events[-1]
        latest_workspace = kernel.state.workspace_cycle_events[-1]
        proposed: list[StructureCandidateRecord] = []
        for member_ids in memberships:
            candidate_id = stable_id("structure_candidate", member_ids)
            existing = kernel.state.structure_candidates.get(candidate_id)
            internal_ids, boundary_ids = self._associations_for_members(kernel, member_ids)
            canonical_relation_ids = self._canonical_relations(kernel, member_ids)
            evidence: set[str] = set()
            for association_id in (*internal_ids, *boundary_ids):
                evidence.update(kernel.state.plasticity_associations[association_id].evidence_refs)
            for relation_id in canonical_relation_ids:
                evidence.update(kernel.state.relations[relation_id].evidence_refs)
            for item in kernel.state.workspace_items.values():
                if set(item.binding_refs).intersection(member_ids):
                    evidence.update(item.evidence_refs)
            if existing is not None:
                evidence.update(existing.evidence_refs)
            evidence_refs = tuple(sorted(evidence))[-policy.max_evidence_refs :]
            workspace_ids = set(existing.workspace_event_ids if existing else ())
            workspace_ids.add(latest_workspace.event_id)
            workspace_event_ids = tuple(sorted(workspace_ids))[-policy.max_observation_history :]
            observed_cycles = set(existing.observed_cycles if existing else ())
            observed_cycles.add(prospective_cycle)
            observed_cycles_tuple = tuple(sorted(observed_cycles))[-policy.max_observation_history :]
            occurrence_count = (existing.occurrence_count if existing else 0) + 1
            quality = self._quality(
                kernel,
                member_ids=member_ids,
                internal_ids=internal_ids,
                boundary_ids=boundary_ids,
                evidence_refs=evidence_refs,
                occurrence_count=occurrence_count,
            )
            status = (
                StructureCandidateStatus.ELIGIBLE
                if self._eligible(kernel, quality, occurrence_count)
                else StructureCandidateStatus.TRACKING
            )
            if existing is not None and existing.status == StructureCandidateStatus.PROMOTED:
                status = StructureCandidateStatus.PROMOTED
            dim, real, imag, field_hash = self._field_prototype(kernel, member_ids)
            proposed.append(
                StructureCandidateRecord(
                    candidate_id=candidate_id,
                    status=status,
                    member_concept_ids=member_ids,
                    member_relation_ids=canonical_relation_ids,
                    internal_association_ids=internal_ids,
                    boundary_association_ids=boundary_ids,
                    evidence_refs=evidence_refs,
                    workspace_event_ids=workspace_event_ids,
                    observed_cycles=observed_cycles_tuple,
                    occurrence_count=occurrence_count,
                    created_cycle=existing.created_cycle if existing else prospective_cycle,
                    updated_cycle=prospective_cycle,
                    quality=quality,
                    field_state_dim=dim,
                    field_prototype_real=real,
                    field_prototype_imag=imag,
                    field_prototype_sha256=field_hash,
                    promoted_structure_id=existing.promoted_structure_id if existing else None,
                )
            )
        proposed.sort(key=lambda item: item.candidate_id)
        observed_ids = tuple(item.candidate_id for item in proposed)
        operation = "observe_earned_structure_candidates"
        report_id = stable_id(
            "structure_observation_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            latest_plasticity.event_id,
            observed_ids,
            tuple(item.model_dump(mode="json") for item in proposed),
            operation,
            policy.revision,
        )
        report = StructureObservationReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            plasticity_event_id=latest_plasticity.event_id,
            observed_candidate_ids=observed_ids,
            proposed_candidates=tuple(proposed),
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_structure_observation_report(report)
        return report

    def commit(
        self,
        kernel: VerdantKernel,
        report: StructureObservationReport,
    ) -> StructureObservationEvent:
        try:
            report = StructureObservationReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise StructureStaleError("Structure observation report is invalid.") from exc
        reproduced = self.inspect(kernel)
        if reproduced != report:
            raise StructureStaleError(
                "Structure observation report does not reproduce from current state."
            )
        return kernel.commit_structure_observation(report)

    def run_cycle(self, kernel: VerdantKernel) -> StructureObservationResult | None:
        report = self.inspect(kernel)
        if report is None:
            return None
        return StructureObservationResult(report, self.commit(kernel, report))

    def inspect_promotion(
        self,
        kernel: VerdantKernel,
        candidate_id: str,
    ) -> StructurePromotionReport:
        candidate = kernel.state.structure_candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"Unknown structure candidate {candidate_id!r}.")
        policy = kernel.state.structure_policy
        q = candidate.quality
        rejection: list[str] = []
        if candidate.status == StructureCandidateStatus.PROMOTED:
            rejection.append("already_promoted")
        if candidate.occurrence_count < policy.minimum_recurrence_events:
            rejection.append("insufficient_recurrence")
        if q.reconstructability < policy.minimum_reconstructability:
            rejection.append("reconstruction_below_threshold")
        if q.boundary_selectivity < policy.minimum_boundary_selectivity:
            rejection.append("boundary_selectivity_below_threshold")
        if q.internal_cohesion < policy.minimum_internal_cohesion:
            rejection.append("internal_cohesion_below_threshold")
        if q.evidence_diversity < 1.0:
            rejection.append("insufficient_evidence_diversity")
        if q.cross_context_stability < 1.0:
            rejection.append("insufficient_cross_context_stability")
        rejection_codes = tuple(sorted(set(rejection)))
        disposition = (
            StructurePromotionDisposition.PROMOTE
            if not rejection_codes
            else StructurePromotionDisposition.DEFER
        )
        proposed_structure_id = stable_id("structure", candidate.candidate_id)
        opaque_name = f"P_{proposed_structure_id.split('_')[-1][:12]}"
        operation = f"promote_earned_structure:{candidate.candidate_id}"
        structural = kernel.structure_structural_fingerprint()
        report_id = stable_id(
            "structure_promotion_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            candidate_id,
            disposition.value,
            rejection_codes,
            candidate.evidence_refs,
            proposed_structure_id,
            opaque_name,
            operation,
            policy.revision,
            candidate.model_dump(mode="json"),
        )
        report = StructurePromotionReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            candidate_id=candidate_id,
            disposition=disposition,
            rejection_codes=rejection_codes,
            evidence_refs=candidate.evidence_refs,
            proposed_structure_id=proposed_structure_id,
            proposed_opaque_name=opaque_name,
            operation=operation,
            policy_revision=policy.revision,
            candidate_snapshot=candidate,
        )
        kernel.validate_structure_promotion_report(report)
        return report

    def promotion_council_proposal(
        self,
        kernel: VerdantKernel,
        report: StructurePromotionReport,
        governance: VerdantGovernancePipeline | None = None,
    ):
        if report.disposition != StructurePromotionDisposition.PROMOTE:
            raise ValueError("An ineligible structure cannot be proposed for promotion.")
        governance = governance or VerdantGovernancePipeline()
        candidate = report.candidate_snapshot
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.STRUCTURAL_PROMOTION,
            operation=report.operation,
            action_class="earned_relational_structure_promotion",
            description=(
                "Promote a recurring, reconstructable, boundary-selective relational "
                "candidate into an opaque reusable cognitive operand without assigning "
                "a human semantic category."
            ),
            evidence_refs=report.evidence_refs,
            requested_resource=min(0.18, kernel.state.governance.attention_budget),
            relevance=0.95,
            urgency=0.20,
            novelty=0.90,
            predicted_information_gain=0.90,
            harm_risk=0.0,
            reversibility=1.0,
            metadata={
                "candidate_id": candidate.candidate_id,
                "member_count": len(candidate.member_concept_ids),
                "occurrence_count": candidate.occurrence_count,
                "quality": candidate.quality.model_dump(mode="json"),
                "semantic_label_preinstalled": False,
            },
        )

    def promote(
        self,
        kernel: VerdantKernel,
        candidate_id: str,
        governance: VerdantGovernancePipeline | None = None,
    ) -> StructurePromotionResult:
        governance = governance or VerdantGovernancePipeline()
        report = self.inspect_promotion(kernel, candidate_id)
        if report.disposition != StructurePromotionDisposition.PROMOTE:
            raise ValueError(
                "Structure candidate is not eligible: " + ", ".join(report.rejection_codes)
            )
        proposal = self.promotion_council_proposal(kernel, report, governance)
        decision = governance.commit(kernel, governance.inspect(kernel, proposal))
        event = kernel.commit_structure_promotion(
            report,
            council_decision_event_id=decision.decision_event_id,
        )
        return StructurePromotionResult(report, decision, event)
