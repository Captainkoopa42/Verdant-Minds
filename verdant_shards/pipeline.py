from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from verdant_governance import VerdantGovernancePipeline
from verdant_kernel import (
    CouncilDecisionEvent,
    GovernanceProposalKind,
    RoutingDisposition,
    RoutingEvent,
    RoutingReport,
    ShardFormationEvent,
    ShardFormationReport,
    ShardIntegrityError,
    VerdantKernel,
)
from verdant_kernel.models import (
    RouteCandidate,
    RouteScoreComponents,
    normalize_label,
    stable_id,
)


@dataclass(frozen=True)
class ShardFormationResult:
    report: ShardFormationReport
    council_decision: CouncilDecisionEvent
    formation_event: ShardFormationEvent


@dataclass(frozen=True)
class ShardRoutingResult:
    report: RoutingReport
    council_decision: CouncilDecisionEvent
    routing_event: RoutingEvent


class VerdantShardPipeline:
    """Bounded specialization and evidence-grounded routing.

    Shards contain references to canonical concepts and relations; they never copy
    or replace semantic truth. A persistent bridge is created only by a completed,
    Council-authorized traversal, so ghost bridges cannot exist.
    """

    def inspect_formation(
        self,
        kernel: VerdantKernel,
        *,
        label: str,
        concept_ids: Iterable[str],
        parent_shard_id: str = "root",
        relation_ids: Iterable[str] | None = None,
        evidence_refs: Iterable[str] = (),
        specialization_signature: Iterable[str] | None = None,
    ) -> ShardFormationReport:
        concepts = tuple(sorted(set(concept_ids)))
        if not concepts:
            raise ValueError("Shard formation requires at least one concept.")
        missing = [item for item in concepts if item not in kernel.state.concepts]
        if missing:
            raise KeyError(f"Unknown shard concepts: {missing}")
        if parent_shard_id not in kernel.state.shards:
            raise KeyError(f"Unknown parent shard {parent_shard_id!r}.")
        if len(concepts) > kernel.state.shard_policy.max_concepts_per_shard:
            raise ValueError("Proposed shard exceeds the configured concept bound.")

        concept_set = set(concepts)
        if relation_ids is None:
            relations = tuple(
                sorted(
                    relation.relation_id
                    for relation in kernel.state.relations.values()
                    if {
                        relation.source_concept_id,
                        relation.target_concept_id,
                    }.issubset(concept_set)
                )
            )
        else:
            relations = tuple(sorted(set(relation_ids)))
        if len(relations) > kernel.state.shard_policy.max_relations_per_shard:
            raise ValueError("Proposed shard exceeds the configured relation bound.")
        for relation_id in relations:
            relation = kernel.state.relations.get(relation_id)
            if relation is None:
                raise KeyError(f"Unknown relation {relation_id!r}.")
            if not {
                relation.source_concept_id,
                relation.target_concept_id,
            }.issubset(concept_set):
                raise ValueError("Every shard relation must be internal to its members.")

        evidence = set(evidence_refs)
        for concept_id in concepts:
            evidence.update(kernel.state.concepts[concept_id].evidence_refs)
        for relation_id in relations:
            evidence.update(kernel.state.relations[relation_id].evidence_refs)
        evidence_tuple = tuple(sorted(evidence))
        if not evidence_tuple:
            raise ValueError("Shard formation requires preserved supporting evidence.")
        kernel._validated_evidence_refs(evidence_tuple)

        if specialization_signature is None:
            degree = {concept_id: 0 for concept_id in concepts}
            for relation_id in relations:
                relation = kernel.state.relations[relation_id]
                degree[relation.source_concept_id] += 1
                degree[relation.target_concept_id] += 1
            signature = tuple(
                sorted(
                    sorted(concepts, key=lambda item: (-degree[item], item))[
                        : min(4, len(concepts))
                    ]
                )
            )
        else:
            signature = tuple(sorted(set(specialization_signature)))
            if not set(signature).issubset(concept_set):
                raise ValueError("Specialization signature must use shard concepts.")

        normalized = normalize_label(label)
        proposed_id = stable_id(
            "shard",
            normalized,
            parent_shard_id,
            concepts,
            relations,
        )
        operation = f"form_shard:{proposed_id}"
        structural = kernel.shard_structural_fingerprint()
        report_id = stable_id(
            "shard_formation_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            label.strip(),
            normalized,
            proposed_id,
            parent_shard_id,
            concepts,
            relations,
            evidence_tuple,
            signature,
            operation,
            kernel.state.shard_policy.revision,
        )
        report = ShardFormationReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            shard_label=label.strip(),
            normalized_label=normalized,
            proposed_shard_id=proposed_id,
            parent_shard_id=parent_shard_id,
            concept_ids=concepts,
            relation_ids=relations,
            evidence_refs=evidence_tuple,
            specialization_signature=signature,
            operation=operation,
            policy_revision=kernel.state.shard_policy.revision,
        )
        kernel.validate_shard_formation_report(report)
        return report

    def formation_council_proposal(
        self,
        kernel: VerdantKernel,
        report: ShardFormationReport,
        governance: VerdantGovernancePipeline | None = None,
    ):
        governance = governance or VerdantGovernancePipeline()
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.STRUCTURAL_PROMOTION,
            operation=report.operation,
            action_class="bounded_shard_formation",
            description=(
                f"Form bounded specialization shard {report.shard_label!r} from "
                f"{len(report.concept_ids)} concepts and {len(report.relation_ids)} relations."
            ),
            evidence_refs=report.evidence_refs,
            requested_resource=min(0.25, kernel.state.governance.attention_budget),
            relevance=0.95,
            urgency=0.35,
            novelty=0.75,
            predicted_information_gain=0.85,
            harm_risk=0.02,
            reversibility=1.0,
            metadata={
                "shard_formation_report_id": report.report_id,
                "proposed_shard_id": report.proposed_shard_id,
                "bounded_concepts": len(report.concept_ids),
                "bounded_relations": len(report.relation_ids),
            },
        )

    def commit_formation(
        self,
        kernel: VerdantKernel,
        report: ShardFormationReport,
        *,
        council_decision_event_id: str,
    ) -> ShardFormationEvent:
        kernel.validate_shard_formation_report(report)
        return kernel.commit_shard_formation(
            report,
            council_decision_event_id=council_decision_event_id,
        )

    def form_shard(
        self,
        kernel: VerdantKernel,
        *,
        label: str,
        concept_ids: Iterable[str],
        parent_shard_id: str = "root",
        relation_ids: Iterable[str] | None = None,
        evidence_refs: Iterable[str] = (),
        specialization_signature: Iterable[str] | None = None,
        governance: VerdantGovernancePipeline | None = None,
    ) -> ShardFormationResult:
        governance = governance or VerdantGovernancePipeline()
        report = self.inspect_formation(
            kernel,
            label=label,
            concept_ids=concept_ids,
            parent_shard_id=parent_shard_id,
            relation_ids=relation_ids,
            evidence_refs=evidence_refs,
            specialization_signature=specialization_signature,
        )
        proposal = self.formation_council_proposal(kernel, report, governance)
        council = governance.commit(kernel, governance.inspect(kernel, proposal))
        formation = self.commit_formation(
            kernel,
            report,
            council_decision_event_id=council.decision_event_id,
        )
        return ShardFormationResult(report, council, formation)

    def inspect_routing(
        self,
        kernel: VerdantKernel,
        *,
        cue_concept_ids: Iterable[str],
        evidence_refs: Iterable[str],
        resonance_event_ids: Iterable[str] = (),
    ) -> RoutingReport:
        cues = tuple(sorted(set(cue_concept_ids)))
        evidence = tuple(sorted(set(evidence_refs)))
        resonance_ids = tuple(sorted(set(resonance_event_ids)))
        for concept_id in cues:
            if concept_id not in kernel.state.concepts:
                raise KeyError(f"Unknown routing cue concept {concept_id!r}.")
        if evidence:
            kernel._validated_evidence_refs(evidence)
        resonance_events = {
            item.resonance_event_id: item for item in kernel.state.resonance_events
        }
        missing_resonance = [
            item for item in resonance_ids if item not in resonance_events
        ]
        if missing_resonance:
            raise KeyError(f"Unknown resonance events: {missing_resonance}")

        source_id = kernel.state.active_shard_id
        source = kernel.state.shards[source_id]
        policy = kernel.state.shard_policy
        resonance_scores: dict[str, float] = {}
        resonance_concepts: set[str] = set()
        attention_ids: set[str] = set()
        for event_id in resonance_ids:
            event = resonance_events[event_id]
            attention_ids.update(event.attention_candidate_ids)
            for candidate in event.query_report.candidates:
                resonance_scores[candidate.concept_id] = max(
                    resonance_scores.get(candidate.concept_id, 0.0),
                    candidate.score,
                )
                resonance_concepts.add(candidate.concept_id)

        raw: list[tuple[str, float, bool, tuple[str, ...], tuple[str, ...], RouteScoreComponents]] = []
        cue_set = set(cues)
        for shard_id, shard in sorted(kernel.state.shards.items()):
            if shard_id in {"root", source_id}:
                continue
            members = set(shard.concept_ids)
            direct_ids = tuple(sorted(cue_set & members))
            direct = len(direct_ids) / len(cues) if cues else 0.0

            supported_cues = 0
            for cue in cues:
                if cue in members:
                    supported_cues += 1
                    continue
                related = any(
                    (
                        relation.source_concept_id == cue
                        and relation.target_concept_id in members
                    )
                    or (
                        relation.target_concept_id == cue
                        and relation.source_concept_id in members
                    )
                    for relation in kernel.state.relations.values()
                )
                if related:
                    supported_cues += 1
            relation_support = supported_cues / len(cues) if cues else 0.0

            shard_resonance = [
                score
                for concept_id, score in resonance_scores.items()
                if concept_id in members
            ]
            resonance_support = max(shard_resonance, default=0.0)
            contaminated = [
                concept_id
                for concept_id in resonance_concepts
                if concept_id in members and concept_id not in cue_set
            ]
            relevant_resonance_count = sum(
                1 for concept_id in resonance_concepts if concept_id in members
            )
            contamination = (
                len(contaminated) / relevant_resonance_count
                if relevant_resonance_count
                else 0.0
            )

            left, right = sorted((source_id, shard_id))
            bridge_id = stable_id("shard_bridge", left, right)
            bridge = kernel.state.shard_bridges.get(bridge_id)
            bridge_continuity = (
                min(1.0, math.log1p(bridge.traversal_count) / math.log(4.0))
                if bridge
                else 0.0
            )
            shared = len(set(source.concept_ids) & members)
            shared_continuity = shared / max(1, min(len(source.concept_ids), len(members)))
            continuity = max(bridge_continuity, shared_continuity)

            covered = 0
            evidence_set = set(evidence)
            for concept_id in direct_ids:
                if set(kernel.state.concepts[concept_id].evidence_refs) & evidence_set:
                    covered += 1
            evidence_coverage = covered / len(direct_ids) if direct_ids else 0.0
            thaw_cost = min(
                1.0,
                len(shard.concept_ids) / policy.max_concepts_per_shard,
            )
            positive = (
                policy.direct_weight * direct
                + policy.relation_weight * relation_support
                + policy.resonance_weight * resonance_support
                + policy.continuity_weight * continuity
                + policy.evidence_weight * evidence_coverage
            )
            penalty = (
                policy.contamination_penalty * contamination
                + policy.thaw_penalty * thaw_cost
            )
            score = max(0.0, min(1.0, positive - penalty))
            rejection: list[str] = []
            if not evidence:
                rejection.append("missing_preserved_evidence")
            if direct < policy.minimum_direct_grounding:
                rejection.append("insufficient_direct_grounding")
            if score < policy.minimum_route_score:
                rejection.append("score_below_route_threshold")
            eligible = not rejection
            portals = tuple(
                sorted(
                    set(direct_ids)
                    | (set(source.concept_ids) & members)
                )
            )[: policy.max_portals_per_bridge]
            components = RouteScoreComponents(
                direct_grounding=direct,
                relation_support=relation_support,
                resonance_support=resonance_support,
                continuity_support=continuity,
                evidence_coverage=evidence_coverage,
                contamination=contamination,
                thaw_cost=thaw_cost,
                weighted_positive=positive,
                weighted_penalty=penalty,
            )
            raw.append(
                (
                    shard_id,
                    score,
                    eligible,
                    tuple(sorted(rejection)),
                    portals,
                    components,
                )
            )

        ordered = sorted(raw, key=lambda item: (-item[1], item[0]))
        candidates = tuple(
            RouteCandidate(
                rank=index + 1,
                shard_id=shard_id,
                score=score,
                eligible=eligible,
                rejection_codes=rejection,
                directly_grounded_concept_ids=tuple(
                    sorted(cue_set & set(kernel.state.shards[shard_id].concept_ids))
                ),
                portal_concept_ids=portals,
                components=components,
            )
            for index, (
                shard_id,
                score,
                eligible,
                rejection,
                portals,
                components,
            ) in enumerate(ordered)
        )
        selected = next((item for item in candidates if item.eligible), None)
        source_direct = (
            len(cue_set & set(source.concept_ids)) / len(cues)
            if cues and source_id != "root"
            else 0.0
        )
        if selected is not None and selected.score >= policy.minimum_route_score:
            disposition = RoutingDisposition.ROUTE
            selected_id = selected.shard_id
            operation = f"route_to_shard:{selected_id}"
        elif source_direct >= policy.minimum_direct_grounding:
            disposition = RoutingDisposition.STAY
            selected_id = source_id
            operation = f"stay_in_shard:{source_id}"
        else:
            disposition = RoutingDisposition.REJECT
            selected_id = None
            operation = "reject_ungrounded_route"

        structural = kernel.shard_structural_fingerprint()
        report_id = stable_id(
            "routing_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            source_id,
            cues,
            evidence,
            resonance_ids,
            tuple(item.model_dump(mode="json") for item in candidates),
            disposition.value,
            selected_id,
            operation,
            policy.revision,
        )
        report = RoutingReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            source_shard_id=source_id,
            cue_concept_ids=cues,
            evidence_refs=evidence,
            resonance_event_ids=resonance_ids,
            candidates=candidates,
            disposition=disposition,
            selected_shard_id=selected_id,
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_routing_report(report)
        return report

    def routing_council_proposal(
        self,
        kernel: VerdantKernel,
        report: RoutingReport,
        governance: VerdantGovernancePipeline | None = None,
    ):
        if report.disposition != RoutingDisposition.ROUTE:
            raise ShardIntegrityError("Only a grounded route can be proposed to Council.")
        governance = governance or VerdantGovernancePipeline()
        attention_ids: set[str] = set()
        known = {item.resonance_event_id: item for item in kernel.state.resonance_events}
        for event_id in report.resonance_event_ids:
            attention_ids.update(known[event_id].attention_candidate_ids)
        selected = next(
            item for item in report.candidates if item.shard_id == report.selected_shard_id
        )
        return governance.propose(
            kernel,
            proposal_kind=GovernanceProposalKind.ATTEND,
            operation=report.operation,
            action_class="evidence_grounded_shard_route",
            description=(
                f"Route active cognition from {report.source_shard_id!r} to "
                f"{report.selected_shard_id!r} while preserving direct cue evidence."
            ),
            evidence_refs=report.evidence_refs,
            attention_candidate_ids=attention_ids,
            resonance_event_ids=report.resonance_event_ids,
            requested_resource=min(0.30, kernel.state.governance.attention_budget),
            relevance=1.0,
            urgency=0.55,
            novelty=0.45,
            predicted_information_gain=0.85,
            harm_risk=0.0,
            reversibility=1.0,
            metadata={
                "routing_report_id": report.report_id,
                "selected_shard_id": report.selected_shard_id,
                "direct_grounding": selected.components.direct_grounding,
                "route_score": selected.score,
                "contamination": selected.components.contamination,
            },
        )

    def commit_routing(
        self,
        kernel: VerdantKernel,
        report: RoutingReport,
        *,
        council_decision_event_id: str,
    ) -> RoutingEvent:
        reproduced = self.inspect_routing(
            kernel,
            cue_concept_ids=report.cue_concept_ids,
            evidence_refs=report.evidence_refs,
            resonance_event_ids=report.resonance_event_ids,
        )
        expected = reproduced.model_dump(mode="json")
        supplied = report.model_dump(mode="json")
        for key in ("report_id", "cycle"):
            expected.pop(key, None)
            supplied.pop(key, None)
        if expected != supplied:
            raise ShardIntegrityError(
                "Routing report does not reproduce from current structure."
            )
        return kernel.commit_routing(
            report,
            council_decision_event_id=council_decision_event_id,
        )

    def route(
        self,
        kernel: VerdantKernel,
        *,
        cue_concept_ids: Iterable[str],
        evidence_refs: Iterable[str],
        resonance_event_ids: Iterable[str] = (),
        governance: VerdantGovernancePipeline | None = None,
    ) -> ShardRoutingResult:
        governance = governance or VerdantGovernancePipeline()
        report = self.inspect_routing(
            kernel,
            cue_concept_ids=cue_concept_ids,
            evidence_refs=evidence_refs,
            resonance_event_ids=resonance_event_ids,
        )
        proposal = self.routing_council_proposal(kernel, report, governance)
        council = governance.commit(kernel, governance.inspect(kernel, proposal))
        routing = self.commit_routing(
            kernel,
            report,
            council_decision_event_id=council.decision_event_id,
        )
        return ShardRoutingResult(report, council, routing)
