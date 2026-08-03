from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    GovernanceProposalKind,
    RefoldComponentProposal,
    RefoldDisposition,
    RefoldingStaleError,
    StructureEdgeSnapshot,
    StructureQualityVector,
    StructureRefoldEvent,
    StructureRefoldReport,
    StructuralChallengeRecord,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id


@dataclass(frozen=True)
class RefoldingResult:
    report: StructureRefoldReport
    event: StructureRefoldEvent


class VerdantRefoldingPipeline:
    """Milestone 18 selective unfolding/refolding under structural contradiction.

    A promoted structure stores a frozen relational body. New evidence may explicitly
    challenge one of those frozen internal edges. Challenges are evidence-grounded,
    recurrent, and nonsemantic: they do not directly rewrite concepts, relations, or
    claims. When enough contradictory observations accumulate, the structure is
    unfolded, challenged edges are removed, and the surviving topology is assessed.

    Outcomes:
      * STABLE: no mature challenge currently changes the fold.
      * REVISE: the fold remains connected but needs a new structural revision.
      * SPLIT: removing challenged edges reveals multiple viable components.
      * UNRESOLVED: the contradiction damages the fold but no defensible replacement
        can yet be committed.

    Successful REVISE/SPLIT operations are Council-authorized. The parent StructureRecord
    is never overwritten; it is preserved and normally ablated while new lineage-linked
    StructureRecords become available.
    """

    @staticmethod
    def _event_keys(kernel: VerdantKernel, evidence_refs: Iterable[str]) -> set[str]:
        return {kernel.state.evidence[item].event_key for item in evidence_refs}

    @staticmethod
    def _field_prototype(
        kernel: VerdantKernel, member_ids: tuple[str, ...]
    ) -> tuple[int, tuple[float, ...], tuple[float, ...], str]:
        vectors: list[np.ndarray] = []
        for concept_id in member_ids:
            profile = kernel.state.resonance_profiles.get(concept_id)
            if profile is not None:
                vectors.append(
                    np.asarray(profile.real, dtype=np.float64)
                    + 1j * np.asarray(profile.imag, dtype=np.float64)
                )
                continue
            address = kernel.state.field_addresses.get(concept_id)
            if address is not None:
                vectors.append(
                    np.asarray(address.real, dtype=np.float64)
                    + 1j * np.asarray(address.imag, dtype=np.float64)
                )
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
    def _components(
        member_ids: tuple[str, ...], edges: tuple[StructureEdgeSnapshot, ...]
    ) -> tuple[tuple[str, ...], ...]:
        adjacency = {item: set() for item in member_ids}
        for edge in edges:
            a, b = edge.concept_ids
            adjacency[a].add(b)
            adjacency[b].add(a)
        seen: set[str] = set()
        components: list[tuple[str, ...]] = []
        for root in sorted(adjacency):
            if root in seen:
                continue
            stack = [root]
            component: set[str] = set()
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                component.add(node)
                stack.extend(sorted(adjacency[node], reverse=True))
            seen.update(component)
            components.append(tuple(sorted(component)))
        return tuple(sorted(components))

    @staticmethod
    def _component_edges(
        members: tuple[str, ...], edges: tuple[StructureEdgeSnapshot, ...]
    ) -> tuple[StructureEdgeSnapshot, ...]:
        member_set = set(members)
        return tuple(
            sorted(
                (edge for edge in edges if set(edge.concept_ids).issubset(member_set)),
                key=lambda item: item.association_id,
            )
        )

    @staticmethod
    def _quality(
        parent,
        members: tuple[str, ...],
        edges: tuple[StructureEdgeSnapshot, ...],
        parent_edges: tuple[StructureEdgeSnapshot, ...],
        *,
        contradiction_resolved: bool,
    ) -> StructureQualityVector:
        possible = max(1, len(members) * (len(members) - 1) // 2)
        edge_coverage = min(1.0, len(edges) / possible)
        mean_strength = sum(item.strength for item in edges) / len(edges) if edges else 0.0
        reconstructability = math.sqrt(max(0.0, edge_coverage * mean_strength))
        surviving_strength = sum(item.strength for item in edges)
        original_strength = sum(item.strength for item in parent_edges)
        perturbation_survival = (
            surviving_strength / original_strength if original_strength > 1e-12 else 0.0
        )
        q = parent.quality_at_promotion
        return StructureQualityVector(
            recurrence=q.recurrence,
            reconstructability=max(0.0, min(1.0, reconstructability)),
            boundary_selectivity=q.boundary_selectivity,
            internal_cohesion=max(0.0, min(1.0, mean_strength)),
            evidence_diversity=q.evidence_diversity,
            cross_context_stability=q.cross_context_stability,
            perturbation_survival=max(0.0, min(1.0, perturbation_survival)),
            compression_gain=q.compression_gain,
            contradiction_tolerance=(1.0 if contradiction_resolved else 0.0),
        )

    @staticmethod
    def _mature_challenges(
        kernel: VerdantKernel, structure_id: str
    ) -> tuple[StructuralChallengeRecord, ...]:
        policy = kernel.state.refolding_policy
        return tuple(
            sorted(
                (
                    item
                    for item in kernel.state.structural_challenges.values()
                    if item.structure_id == structure_id
                    and len(item.observations) >= policy.minimum_challenge_events
                    and item.combined_confidence >= policy.minimum_combined_confidence
                ),
                key=lambda item: item.challenge_id,
            )
        )

    def challenge(
        self,
        kernel: VerdantKernel,
        structure_id: str,
        concept_ids: tuple[str, str],
        *,
        evidence_refs: Iterable[str],
        confidence: float = 1.0,
    ) -> StructuralChallengeRecord:
        return kernel.record_structural_challenge(
            structure_id,
            concept_ids,
            evidence_refs=evidence_refs,
            confidence=confidence,
        )

    def inspect(self, kernel: VerdantKernel, structure_id: str) -> StructureRefoldReport:
        if structure_id not in kernel.state.structures:
            raise ValueError("Unknown structure for refolding inspection.")
        parent = kernel.state.structures[structure_id]
        policy = kernel.state.refolding_policy
        mature = self._mature_challenges(kernel, structure_id)
        challenge_ids = tuple(item.challenge_id for item in mature)
        evidence_refs = tuple(
            sorted(
                {
                    evidence_id
                    for challenge in mature
                    for observation in challenge.observations
                    for evidence_id in observation.evidence_refs
                }
            )
        )
        challenged_pairs = {item.concept_ids for item in mature}
        removed = tuple(
            sorted(
                edge.association_id
                for edge in parent.internal_edge_snapshots
                if edge.concept_ids in challenged_pairs
            )
        )
        surviving = tuple(
            edge
            for edge in parent.internal_edge_snapshots
            if edge.association_id not in set(removed)
        )
        rejection: list[str] = []
        proposals: list[RefoldComponentProposal] = []

        if not mature or not removed:
            disposition = RefoldDisposition.STABLE
            if not mature:
                rejection.append("no_mature_structural_challenge")
            else:
                rejection.append("challenge_did_not_target_frozen_edge")
        else:
            components = self._components(parent.member_concept_ids, surviving)
            viable = []
            invalid = []
            for members in components:
                edges = self._component_edges(members, surviving)
                if (
                    len(members) >= policy.minimum_component_members
                    and len(edges) >= policy.minimum_component_edges
                ):
                    viable.append((members, edges))
                else:
                    invalid.append((members, edges))

            if len(components) > 1:
                if invalid or len(viable) < 2:
                    disposition = RefoldDisposition.UNRESOLVED
                    rejection.append("split_contains_undersized_or_edge_poor_fragment")
                else:
                    disposition = RefoldDisposition.SPLIT
            else:
                members = components[0]
                edges = self._component_edges(members, surviving)
                if (
                    len(members) >= policy.minimum_component_members
                    and len(edges) >= policy.minimum_component_edges
                ):
                    viable = [(members, edges)]
                    disposition = RefoldDisposition.REVISE
                else:
                    disposition = RefoldDisposition.UNRESOLVED
                    rejection.append("remaining_structure_below_refold_minimum")

            if disposition in {RefoldDisposition.REVISE, RefoldDisposition.SPLIT}:
                challenge_evidence = set(evidence_refs)
                base_evidence = set(parent.evidence_refs)
                lineage_root = parent.lineage_root_structure_id or parent.structure_id
                revision_index = parent.revision_index + 1
                for members, edges in viable:
                    component_evidence = tuple(sorted(base_evidence | challenge_evidence))
                    quality = self._quality(
                        parent,
                        members,
                        edges,
                        parent.internal_edge_snapshots,
                        contradiction_resolved=True,
                    )
                    dim, real, imag, digest = self._field_prototype(kernel, members)
                    proposed_id = stable_id(
                        "refolded_structure",
                        parent.structure_id,
                        members,
                        tuple(item.model_dump(mode="json") for item in edges),
                        challenge_ids,
                    )
                    proposals.append(
                        RefoldComponentProposal(
                            proposed_structure_id=proposed_id,
                            proposed_opaque_name=f"P_{proposed_id.rsplit('_', 1)[-1][:12]}",
                            parent_structure_id=parent.structure_id,
                            lineage_root_structure_id=lineage_root,
                            revision_index=revision_index,
                            member_concept_ids=members,
                            internal_association_ids=tuple(item.association_id for item in edges),
                            internal_edge_snapshots=edges,
                            evidence_refs=component_evidence,
                            quality=quality,
                            field_state_dim=dim,
                            field_prototype_real=real,
                            field_prototype_imag=imag,
                            field_prototype_sha256=digest,
                            refold_basis_challenge_ids=challenge_ids,
                        )
                    )

        proposals.sort(key=lambda item: item.proposed_structure_id)
        rejection_codes = tuple(sorted(set(rejection)))
        structural = kernel.refolding_structural_fingerprint()
        report_id = stable_id(
            "structure_refold_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            structure_id,
            disposition.value,
            challenge_ids,
            removed,
            tuple(item.model_dump(mode="json") for item in proposals),
            evidence_refs,
            rejection_codes,
            "refold_structure",
            policy.revision,
        )
        report = StructureRefoldReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            parent_structure_id=structure_id,
            disposition=disposition,
            challenge_ids=challenge_ids,
            removed_association_ids=removed,
            proposals=tuple(proposals),
            evidence_refs=evidence_refs,
            rejection_codes=rejection_codes,
            operation="refold_structure",
            policy_revision=policy.revision,
        )
        kernel.validate_structure_refold_report(report)
        return report

    def _council_proposal(
        self,
        kernel: VerdantKernel,
        report: StructureRefoldReport,
        governance: VerdantGovernancePipeline,
    ):
        if report.disposition not in {RefoldDisposition.REVISE, RefoldDisposition.SPLIT}:
            raise ValueError("Only actionable refolding may be proposed to Council.")
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.STRUCTURAL_PROMOTION,
            operation=report.operation,
            action_class="earned_structure_refolding",
            description=(
                "Preserve an earned structure's historical body while replacing its active "
                "use with one or more lineage-linked structural revisions after recurrent, "
                "evidence-grounded contradiction of frozen internal edges."
            ),
            evidence_refs=report.evidence_refs,
            requested_resource=min(0.18, kernel.state.governance.attention_budget),
            relevance=0.97,
            urgency=0.45,
            novelty=0.75,
            predicted_information_gain=0.90,
            harm_risk=0.0,
            reversibility=1.0,
            metadata={
                "parent_structure_id": report.parent_structure_id,
                "disposition": report.disposition.value,
                "challenge_ids": report.challenge_ids,
                "removed_association_ids": report.removed_association_ids,
                "replacement_ids": tuple(item.proposed_structure_id for item in report.proposals),
                "semantic_mutation_permitted": False,
            },
        )

    def commit(
        self,
        kernel: VerdantKernel,
        report: StructureRefoldReport,
        governance: VerdantGovernancePipeline | None = None,
    ) -> StructureRefoldEvent:
        reproduced = self.inspect(kernel, report.parent_structure_id)
        if reproduced != report:
            raise RefoldingStaleError(
                "Structure refold report does not reproduce from current state."
            )
        if report.disposition in {RefoldDisposition.REVISE, RefoldDisposition.SPLIT}:
            governance = governance or VerdantGovernancePipeline()
            proposal = self._council_proposal(kernel, report, governance)
            decision = governance.commit(kernel, governance.inspect(kernel, proposal))
            return kernel.commit_structure_refold(
                report, council_decision_event_id=decision.decision_event_id
            )
        return kernel.commit_structure_refold(report)

    def refold(
        self,
        kernel: VerdantKernel,
        structure_id: str,
        governance: VerdantGovernancePipeline | None = None,
    ) -> RefoldingResult:
        report = self.inspect(kernel, structure_id)
        event = self.commit(kernel, report, governance)
        return RefoldingResult(report=report, event=event)
