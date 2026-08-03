from __future__ import annotations

import hashlib
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from verdant_governance import VerdantGovernancePipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    CouncilDecisionEvent,
    GovernanceProposalKind,
    HierarchyCandidateRecord,
    HierarchyCandidateStatus,
    HierarchyObservationEvent,
    HierarchyObservationReport,
    HierarchyPromotionDisposition,
    HierarchyPromotionEvent,
    HierarchyPromotionReport,
    HierarchyQualityVector,
    LayeredProbeCost,
    LayeredProbeDisposition,
    LayeredProbeEvent,
    LayeredProbeReport,
    StructureInteractionDisposition,
    HierarchyStaleError,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id


@dataclass(frozen=True)
class HierarchyObservationResult:
    report: HierarchyObservationReport
    event: HierarchyObservationEvent


@dataclass(frozen=True)
class HierarchyPromotionResult:
    report: HierarchyPromotionReport
    decision: CouncilDecisionEvent
    event: HierarchyPromotionEvent


@dataclass(frozen=True)
class LayeredProbeResult:
    report: LayeredProbeReport
    event: LayeredProbeEvent | None = None


class VerdantHierarchyPipeline:
    """Milestone 17: earned structures become primitives for higher-order objects.

    The observer sees only committed, symbolically verified structure interactions.
    It does not receive labels such as "path family" or "analogy class".  A
    recurring family of already-earned structures can itself earn opaque
    objecthood if the family is recurrent, internally aligned, coherent in the
    cross-symbolic field, bounded from nearby false positives, and backed by
    diverse lower-level evidence.

    A promoted layered structure can then classify a *new* base structure by
    comparing one higher-order prototype plus one symbolic verification instead
    of scanning every lower-level structure individually.  The full member scan
    is still computed as an audit baseline, not counted as runtime work when the
    layered operand is used.
    """

    def __init__(self) -> None:
        self.interaction = VerdantStructureInteractionPipeline()

    @staticmethod
    def _event_keys(kernel: VerdantKernel, evidence_refs: tuple[str, ...]) -> set[str]:
        return {kernel.state.evidence[item].event_key for item in evidence_refs}

    @staticmethod
    def _verified_graph(kernel: VerdantKernel):
        available = {
            sid for sid in kernel.state.structures if kernel.structure_is_available(sid)
        }
        adjacency: dict[str, set[str]] = {sid: set() for sid in available}
        pair_scores: dict[tuple[str, str], list[float]] = {}
        pair_events: dict[tuple[str, str], set[str]] = {}
        boundary_candidates: list[tuple[str, str, float]] = []

        for event in kernel.state.structure_interaction_events:
            source = event.report.source_structure_id
            if source not in available:
                continue
            for candidate in event.report.candidates:
                target = candidate.target_structure_id
                if target not in available or target == source:
                    continue
                pair = tuple(sorted((source, target)))
                if candidate.disposition == StructureInteractionDisposition.VERIFIED_ALIGNMENT:
                    adjacency[source].add(target)
                    adjacency[target].add(source)
                    pair_scores.setdefault(pair, []).append(float(candidate.symbolic_similarity))
                    pair_events.setdefault(pair, set()).add(event.event_id)
                elif candidate.disposition == StructureInteractionDisposition.FIELD_ONLY:
                    boundary_candidates.append((source, target, float(candidate.field_similarity)))
        return adjacency, pair_scores, pair_events, boundary_candidates

    @staticmethod
    def _components(adjacency: dict[str, set[str]]) -> tuple[tuple[str, ...], ...]:
        seen: set[str] = set()
        components: list[tuple[str, ...]] = []
        for root in sorted(adjacency):
            if root in seen or not adjacency[root]:
                continue
            stack = [root]
            component: set[str] = set()
            while stack:
                node = stack.pop()
                if node in component:
                    continue
                component.add(node)
                stack.extend(sorted(adjacency.get(node, ()), reverse=True))
            seen.update(component)
            components.append(tuple(sorted(component)))
        return tuple(sorted(components))

    def _prototype(
        self, kernel: VerdantKernel, member_structure_ids: tuple[str, ...]
    ) -> tuple[int, tuple[float, ...], tuple[float, ...], str, float]:
        vectors: list[np.ndarray] = []
        for sid in member_structure_ids:
            signature = self.interaction.signature(kernel, sid)
            vectors.append(
                np.asarray(signature.real, dtype=np.float64)
                + 1j * np.asarray(signature.imag, dtype=np.float64)
            )
        mean = np.mean(np.stack(vectors), axis=0)
        norm = float(np.linalg.norm(mean))
        if norm <= 1e-12:
            mean = np.zeros_like(vectors[0])
            mean[0] = 1.0 + 0.0j
        else:
            mean = mean / norm
        similarities = []
        for vector in vectors:
            denom = float(np.linalg.norm(vector) * np.linalg.norm(mean))
            score = float(np.real(np.vdot(vector, mean)) / denom) if denom > 1e-12 else 0.0
            similarities.append(max(0.0, min(1.0, score)))
        real = tuple(float(item) for item in mean.real.tolist())
        imag = tuple(float(item) for item in mean.imag.tolist())
        digest = hashlib.sha256(canonical_json_bytes({"real": real, "imag": imag})).hexdigest()
        return len(real), real, imag, digest, float(sum(similarities) / len(similarities))

    def _candidate_from_component(
        self,
        kernel: VerdantKernel,
        members: tuple[str, ...],
        pair_scores: dict[tuple[str, str], list[float]],
        pair_events: dict[tuple[str, str], set[str]],
        boundary_candidates: list[tuple[str, str, float]],
        prospective_cycle: int,
    ) -> HierarchyCandidateRecord | None:
        policy = kernel.state.hierarchy_policy
        if len(members) < policy.minimum_members or len(members) > policy.maximum_members:
            return None
        member_set = set(members)
        possible = max(1, len(members) * (len(members) - 1) // 2)
        internal_pairs = [
            pair for pair in combinations(members, 2)
            if tuple(sorted(pair)) in pair_scores
        ]
        pair_coverage = len(internal_pairs) / possible
        internal_scores = [
            max(pair_scores[tuple(sorted(pair))]) for pair in internal_pairs
        ]
        alignment_cohesion = (
            sum(internal_scores) / len(internal_scores) if internal_scores else 0.0
        )
        interaction_ids: set[str] = set()
        for pair in internal_pairs:
            interaction_ids.update(pair_events[tuple(sorted(pair))])
        if not interaction_ids:
            return None

        # Field-only near misses are treated as boundary pressure rather than
        # evidence of membership. This keeps fuzzy similarity from swallowing
        # nearby but symbolically different structures.
        boundary_strength = 0.0
        for source, target, score in boundary_candidates:
            endpoint_count = int(source in member_set) + int(target in member_set)
            if endpoint_count == 1:
                boundary_strength += score
        internal_strength = sum(internal_scores)
        boundary_selectivity = (
            internal_strength / (internal_strength + boundary_strength)
            if internal_strength + boundary_strength > 1e-12
            else 0.0
        )

        evidence: set[str] = set()
        for sid in members:
            evidence.update(kernel.state.structures[sid].evidence_refs)
        evidence_refs = tuple(sorted(evidence))
        event_count = len(self._event_keys(kernel, evidence_refs))
        dim, real, imag, digest, prototype_cohesion = self._prototype(kernel, members)

        quality = HierarchyQualityVector(
            recurrence=min(1.0, len(interaction_ids) / policy.minimum_interaction_events),
            pair_coverage=max(0.0, min(1.0, pair_coverage)),
            alignment_cohesion=max(0.0, min(1.0, alignment_cohesion)),
            prototype_cohesion=max(0.0, min(1.0, prototype_cohesion)),
            boundary_selectivity=max(0.0, min(1.0, boundary_selectivity)),
            evidence_diversity=min(1.0, event_count / policy.minimum_evidence_events),
            causal_utility=0.0,
        )
        eligible = (
            len(interaction_ids) >= policy.minimum_interaction_events
            and quality.pair_coverage >= policy.minimum_pair_coverage
            and quality.alignment_cohesion >= policy.minimum_alignment_cohesion
            and quality.prototype_cohesion >= policy.minimum_prototype_cohesion
            and quality.boundary_selectivity >= policy.minimum_boundary_selectivity
            and quality.evidence_diversity >= 1.0
        )
        candidate_id = stable_id("hierarchy_candidate", members)
        existing = kernel.state.hierarchy_candidates.get(candidate_id)
        status = HierarchyCandidateStatus.ELIGIBLE if eligible else HierarchyCandidateStatus.TRACKING
        if existing is not None and existing.status == HierarchyCandidateStatus.PROMOTED:
            status = HierarchyCandidateStatus.PROMOTED
        observed = set(existing.observed_cycles if existing else ())
        observed.add(prospective_cycle)
        return HierarchyCandidateRecord(
            candidate_id=candidate_id,
            status=status,
            member_structure_ids=members,
            interaction_event_ids=tuple(sorted(interaction_ids)),
            evidence_refs=evidence_refs,
            observed_cycles=tuple(sorted(observed))[-64:],
            occurrence_count=len(interaction_ids),
            created_cycle=existing.created_cycle if existing else prospective_cycle,
            updated_cycle=prospective_cycle,
            quality=quality,
            prototype_dim=dim,
            prototype_real=real,
            prototype_imag=imag,
            prototype_sha256=digest,
            promoted_layered_structure_id=(
                existing.promoted_layered_structure_id if existing else None
            ),
        )

    def inspect_observation(self, kernel: VerdantKernel) -> HierarchyObservationReport | None:
        if not kernel.state.structure_interaction_events:
            return None
        latest = kernel.state.structure_interaction_events[-1]
        if (
            kernel.state.hierarchy_observation_events
            and kernel.state.hierarchy_observation_events[-1].report.latest_interaction_event_id
            == latest.event_id
        ):
            return None
        policy = kernel.state.hierarchy_policy
        adjacency, pair_scores, pair_events, boundary = self._verified_graph(kernel)
        prospective_cycle = kernel.state.cycle + 1
        proposed: list[HierarchyCandidateRecord] = []
        for members in self._components(adjacency):
            candidate = self._candidate_from_component(
                kernel, members, pair_scores, pair_events, boundary, prospective_cycle
            )
            if candidate is None or latest.event_id not in set(candidate.interaction_event_ids):
                continue
            proposed.append(candidate)
        proposed.sort(
            key=lambda item: (
                -item.quality.alignment_cohesion,
                -item.quality.prototype_cohesion,
                item.candidate_id,
            )
        )
        proposed = proposed[: policy.maximum_candidates_per_cycle]
        proposed.sort(key=lambda item: item.candidate_id)
        if not proposed:
            return None
        observed_ids = tuple(item.candidate_id for item in proposed)
        structural = kernel.hierarchy_structural_fingerprint()
        operation = "observe_layered_structure_candidates"
        report_id = stable_id(
            "hierarchy_observation_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            latest.event_id,
            observed_ids,
            tuple(item.model_dump(mode="json") for item in proposed),
            operation,
            policy.revision,
        )
        report = HierarchyObservationReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            latest_interaction_event_id=latest.event_id,
            observed_candidate_ids=observed_ids,
            proposed_candidates=tuple(proposed),
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_hierarchy_observation_report(report)
        return report

    def commit_observation(
        self, kernel: VerdantKernel, report: HierarchyObservationReport
    ) -> HierarchyObservationEvent:
        reproduced = self.inspect_observation(kernel)
        if reproduced != report:
            raise HierarchyStaleError(
                "Hierarchy observation report does not reproduce from current state."
            )
        return kernel.commit_hierarchy_observation(report)

    def observe(self, kernel: VerdantKernel) -> HierarchyObservationResult | None:
        report = self.inspect_observation(kernel)
        if report is None:
            return None
        return HierarchyObservationResult(report, self.commit_observation(kernel, report))

    def inspect_promotion(
        self, kernel: VerdantKernel, candidate_id: str
    ) -> HierarchyPromotionReport:
        candidate = kernel.state.hierarchy_candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"Unknown hierarchy candidate {candidate_id!r}.")
        policy = kernel.state.hierarchy_policy
        q = candidate.quality
        rejection: list[str] = []
        if candidate.status == HierarchyCandidateStatus.PROMOTED:
            rejection.append("already_promoted")
        if q.recurrence < 1.0:
            rejection.append("insufficient_recurrence")
        if q.pair_coverage < policy.minimum_pair_coverage:
            rejection.append("pair_coverage_below_threshold")
        if q.alignment_cohesion < policy.minimum_alignment_cohesion:
            rejection.append("alignment_cohesion_below_threshold")
        if q.prototype_cohesion < policy.minimum_prototype_cohesion:
            rejection.append("prototype_cohesion_below_threshold")
        if q.boundary_selectivity < policy.minimum_boundary_selectivity:
            rejection.append("boundary_selectivity_below_threshold")
        if q.evidence_diversity < 1.0:
            rejection.append("insufficient_evidence_diversity")
        rejection_codes = tuple(sorted(set(rejection)))
        disposition = (
            HierarchyPromotionDisposition.PROMOTE
            if not rejection_codes
            else HierarchyPromotionDisposition.DEFER
        )
        proposed_id = stable_id("layered_structure", candidate.candidate_id)
        opaque_name = f"Q_{proposed_id.split('_')[-1][:12]}"
        operation = f"promote_layered_structure:{candidate.candidate_id}"
        structural = kernel.hierarchy_structural_fingerprint()
        report_id = stable_id(
            "hierarchy_promotion_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            candidate_id,
            disposition.value,
            rejection_codes,
            candidate.evidence_refs,
            proposed_id,
            opaque_name,
            operation,
            policy.revision,
            candidate.model_dump(mode="json"),
        )
        report = HierarchyPromotionReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            candidate_id=candidate_id,
            disposition=disposition,
            rejection_codes=rejection_codes,
            evidence_refs=candidate.evidence_refs,
            proposed_layered_structure_id=proposed_id,
            proposed_opaque_name=opaque_name,
            operation=operation,
            policy_revision=policy.revision,
            candidate_snapshot=candidate,
        )
        kernel.validate_hierarchy_promotion_report(report)
        return report

    def promotion_council_proposal(
        self,
        kernel: VerdantKernel,
        report: HierarchyPromotionReport,
        governance: VerdantGovernancePipeline | None = None,
    ):
        if report.disposition != HierarchyPromotionDisposition.PROMOTE:
            raise ValueError("An ineligible hierarchy candidate cannot be promoted.")
        governance = governance or VerdantGovernancePipeline()
        candidate = report.candidate_snapshot
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.STRUCTURAL_PROMOTION,
            operation=report.operation,
            action_class="layered_earned_structure_promotion",
            description=(
                "Promote a recurrent family of already-earned relational structures "
                "into a higher-order opaque cognitive operand without assigning a "
                "human semantic category."
            ),
            evidence_refs=report.evidence_refs,
            requested_resource=min(0.18, kernel.state.governance.attention_budget),
            relevance=0.97,
            urgency=0.18,
            novelty=0.96,
            predicted_information_gain=0.94,
            harm_risk=0.0,
            reversibility=1.0,
            metadata={
                "candidate_id": candidate.candidate_id,
                "member_structure_ids": candidate.member_structure_ids,
                "quality": candidate.quality.model_dump(mode="json"),
                "semantic_label_preinstalled": False,
                "depth": 2,
            },
        )

    def promote(
        self,
        kernel: VerdantKernel,
        candidate_id: str,
        governance: VerdantGovernancePipeline | None = None,
    ) -> HierarchyPromotionResult:
        governance = governance or VerdantGovernancePipeline()
        report = self.inspect_promotion(kernel, candidate_id)
        if report.disposition != HierarchyPromotionDisposition.PROMOTE:
            raise ValueError(
                "Hierarchy candidate is not eligible: " + ", ".join(report.rejection_codes)
            )
        proposal = self.promotion_council_proposal(kernel, report, governance)
        decision = governance.commit(kernel, governance.inspect(kernel, proposal))
        event = kernel.commit_hierarchy_promotion(
            report, council_decision_event_id=decision.decision_event_id
        )
        return HierarchyPromotionResult(report, decision, event)

    @staticmethod
    def _prototype_similarity(signature, layered) -> float:
        av = np.asarray(signature.real, dtype=np.float64) + 1j * np.asarray(
            signature.imag, dtype=np.float64
        )
        bv = np.asarray(layered.prototype_real, dtype=np.float64) + 1j * np.asarray(
            layered.prototype_imag, dtype=np.float64
        )
        denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
        if denom <= 1e-12:
            return 0.0
        return max(0.0, min(1.0, float(np.real(np.vdot(av, bv)) / denom)))

    def _baseline_member_scan(
        self, kernel: VerdantKernel, query_structure_id: str
    ) -> tuple[tuple[str, ...], LayeredProbeCost]:
        query = kernel.state.structures[query_structure_id]
        query_signature = self.interaction.signature(kernel, query_structure_id)
        matched: list[str] = []
        base_compared = 0
        symbolic = 0
        for sid, target in sorted(kernel.state.structures.items()):
            if sid == query_structure_id or not kernel.structure_is_available(sid):
                continue
            base_compared += 1
            target_signature = self.interaction.signature(kernel, sid)
            field = self.interaction._field_similarity(query_signature, target_signature)
            if field < kernel.state.structure_interaction_policy.minimum_field_similarity:
                continue
            symbolic += 1
            score, _mapping = self.interaction._symbolic_alignment(kernel, query, target)
            if score >= kernel.state.structure_interaction_policy.minimum_symbolic_similarity:
                matched.append(sid)
        return tuple(sorted(matched)), LayeredProbeCost(
            layered_prototypes_compared=0,
            base_structures_compared=base_compared,
            symbolic_verifications=symbolic,
            matched_members=len(matched),
        )

    def inspect_probe(self, kernel: VerdantKernel, query_structure_id: str) -> LayeredProbeReport:
        if query_structure_id not in kernel.state.structures:
            raise KeyError(f"Unknown query structure {query_structure_id!r}.")
        if not kernel.structure_is_available(query_structure_id):
            raise ValueError("Cannot probe from an ablated structure.")
        policy = kernel.state.hierarchy_policy
        query = kernel.state.structures[query_structure_id]
        signature = self.interaction.signature(kernel, query_structure_id)

        # Audit shadow path. It is measured for comparison but is not included
        # in runtime cost when a layered operand succeeds.
        baseline_matches, baseline_cost = self._baseline_member_scan(
            kernel, query_structure_id
        )

        ranked: list[tuple[float, str]] = []
        layered_compared = 0
        for layered_id, layered in sorted(kernel.state.layered_structures.items()):
            if not kernel.layered_structure_is_available(layered_id):
                continue
            layered_compared += 1
            ranked.append((-self._prototype_similarity(signature, layered), layered_id))
        ranked.sort()

        selected_id: str | None = None
        matched: tuple[str, ...] = ()
        symbolic_verifications = 0
        base_compared = 0
        for negative_similarity, layered_id in ranked:
            similarity = -negative_similarity
            if similarity < policy.layered_probe_similarity:
                continue
            layered = kernel.state.layered_structures[layered_id]
            representatives = [
                sid for sid in layered.member_structure_ids
                if sid != query_structure_id and kernel.structure_is_available(sid)
            ]
            if not representatives:
                continue
            representative_id = sorted(representatives)[0]
            base_compared += 1
            symbolic_verifications += 1
            score, _mapping = self.interaction._symbolic_alignment(
                kernel, query, kernel.state.structures[representative_id]
            )
            if score >= kernel.state.structure_interaction_policy.minimum_symbolic_similarity:
                selected_id = layered_id
                matched = tuple(
                    sorted(sid for sid in layered.member_structure_ids if sid != query_structure_id)
                )
                break

        if selected_id is not None:
            disposition = LayeredProbeDisposition.USE_LAYERED_STRUCTURE
            cost = LayeredProbeCost(
                layered_prototypes_compared=layered_compared,
                base_structures_compared=base_compared,
                symbolic_verifications=symbolic_verifications,
                matched_members=len(matched),
            )
        else:
            disposition = LayeredProbeDisposition.FALLBACK_MEMBER_SCAN
            matched = baseline_matches
            cost = baseline_cost

        baseline_work = baseline_cost.comparison_work
        work = cost.comparison_work
        compression_gain = (
            max(0.0, min(1.0, (baseline_work - work) / baseline_work))
            if baseline_work > 0
            else 0.0
        )
        structural = kernel.hierarchy_probe_structural_fingerprint()
        operation = "recognize_structural_family"
        report_id = stable_id(
            "layered_probe_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            query_structure_id,
            disposition.value,
            selected_id,
            matched,
            cost.model_dump(mode="json"),
            baseline_cost.model_dump(mode="json"),
            compression_gain,
            operation,
            policy.revision,
        )
        report = LayeredProbeReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            query_structure_id=query_structure_id,
            disposition=disposition,
            layered_structure_id=selected_id,
            matched_structure_ids=matched,
            cost=cost,
            baseline_cost=baseline_cost,
            compression_gain=compression_gain,
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_layered_probe_report(report)
        return report

    def commit_probe(self, kernel: VerdantKernel, report: LayeredProbeReport) -> LayeredProbeEvent:
        reproduced = self.inspect_probe(kernel, report.query_structure_id)
        if reproduced != report:
            raise HierarchyStaleError("Layered probe report does not reproduce from current state.")
        return kernel.commit_layered_probe(report)

    def probe(self, kernel: VerdantKernel, query_structure_id: str) -> LayeredProbeResult:
        report = self.inspect_probe(kernel, query_structure_id)
        return LayeredProbeResult(report, self.commit_probe(kernel, report))

    @staticmethod
    def ablate(kernel: VerdantKernel, layered_structure_id: str, reason: str):
        return kernel.set_layered_structure_availability(
            layered_structure_id, available=False, reason=reason
        )

    @staticmethod
    def restore(kernel: VerdantKernel, layered_structure_id: str, reason: str):
        return kernel.set_layered_structure_availability(
            layered_structure_id, available=True, reason=reason
        )
