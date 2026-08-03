from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations

from verdant_kernel import (
    PlasticityAssociationRecord,
    PlasticityEvent,
    PlasticityIntegrityError,
    PlasticityPairAssessment,
    PlasticityReport,
    PlasticityStaleError,
    PlasticityUpdateKind,
    VerdantKernel,
    WorkspaceCycleEvent,
    WorkspaceSourceKind,
)
from verdant_kernel.models import stable_id


@dataclass(frozen=True)
class PlasticityCycleResult:
    report: PlasticityReport
    event: PlasticityEvent


class VerdantPlasticityPipeline:
    """Evidence-bounded local plasticity with explicit anti-saturation rules.

    Milestone 13 restores a useful part of old V4: what is jointly active can
    leave a persistent trace that changes later processing.  The trace is *not*
    a canonical semantic relation.  It is a developmental association layer
    whose growth is constrained by:

    - admitted-foreground coactivation above a local learning threshold;
    - current-evidence gating for new associations;
    - bounded creation/reinforcement per cycle;
    - local decay;
    - a per-concept strength budget;
    - a hard maximum degree;
    - a global edge/node cap.

    This gives later milestones a selective substrate for candidate folds
    without reviving V4's "everything eventually binds to everything" failure.
    """

    @staticmethod
    def _workspace_event(kernel: VerdantKernel, event: WorkspaceCycleEvent) -> WorkspaceCycleEvent:
        if not kernel.state.workspace_cycle_events:
            raise PlasticityIntegrityError("Plasticity requires a workspace cycle.")
        latest = kernel.state.workspace_cycle_events[-1]
        if latest.event_id != event.event_id:
            raise PlasticityStaleError(
                "Plasticity can only inspect the latest committed workspace cycle."
            )
        if tuple(sorted(kernel.state.workspace_items)) != latest.active_item_ids:
            raise PlasticityStaleError(
                "Active workspace no longer matches the requested plasticity cycle."
            )
        return latest

    @staticmethod
    def _scope(kernel: VerdantKernel) -> set[str]:
        policy = kernel.state.plasticity_policy
        if not policy.scope_to_active_shard:
            return set(kernel.state.concepts)
        shard = kernel.state.shards.get(kernel.state.active_shard_id)
        if shard is None:
            raise PlasticityIntegrityError("Active shard is missing.")
        return set(shard.concept_ids)

    @staticmethod
    def _bounded_evidence(
        kernel: VerdantKernel,
        refs: set[str],
    ) -> tuple[str, ...]:
        cap = kernel.state.plasticity_policy.max_evidence_refs_per_association
        ordered = sorted(
            refs,
            key=lambda ref: (-kernel.state.evidence[ref].cycle, ref),
        )[:cap]
        return tuple(sorted(ordered))

    def _activation_state(
        self,
        kernel: VerdantKernel,
        event: WorkspaceCycleEvent,
        scope: set[str],
    ) -> tuple[dict[str, float], dict[str, set[str]], set[str]]:
        policy = kernel.state.plasticity_policy
        activation_parts: dict[str, list[float]] = {}
        evidence_by_concept: dict[str, set[str]] = {}
        current_evidence_concepts: set[str] = set()

        for item_id in event.active_item_ids:
            item = kernel.state.workspace_items.get(item_id)
            if item is None:
                raise PlasticityStaleError(
                    "An active workspace item is no longer active."
                )
            if item.source_kind in {
                WorkspaceSourceKind.LOCAL_ASSOCIATION,
                WorkspaceSourceKind.EARNED_STRUCTURE,
            }:
                # Learned recall and compiled structures may influence cognition,
                # but neither is allowed to bootstrap the lower-level traces that
                # caused them to exist.
                continue
            if item.effective_score < kernel.state.plasticity_policy.minimum_foreground_score:
                continue
            concept_refs = sorted(
                ref for ref in set(item.binding_refs)
                if ref in kernel.state.concepts and ref in scope
            )
            if not concept_refs:
                continue
            score = max(0.0, min(1.0, item.effective_score))
            if item.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE:
                # Directly co-present concepts deserve a reliable but still
                # weak plastic trace even before the field has learned to
                # resonate with them.  The trace must then survive repetition,
                # decay, competition, and degree/strength caps.
                score = max(score, policy.current_evidence_activation_floor)
            for concept_id in concept_refs:
                activation_parts.setdefault(concept_id, []).append(score)
                evidence_by_concept.setdefault(concept_id, set()).update(item.evidence_refs)
                if item.source_kind == WorkspaceSourceKind.CURRENT_EVIDENCE:
                    current_evidence_concepts.add(concept_id)

        # Multiple broadcast causes combine by probabilistic OR.  One strong
        # source remains strong; independent corroborating sources can raise
        # activation without simple unbounded addition.
        activation: dict[str, float] = {}
        for concept_id, parts in activation_parts.items():
            residual = 1.0
            for value in parts:
                residual *= 1.0 - value
            activation[concept_id] = max(0.0, min(1.0, 1.0 - residual))
        return activation, evidence_by_concept, current_evidence_concepts

    @staticmethod
    def _association_id(a: str, b: str) -> str:
        a, b = sorted((a, b))
        return stable_id("plasticity_association", a, b)

    def _candidate_pairs(
        self,
        kernel: VerdantKernel,
        activation: dict[str, float],
        evidence_by_concept: dict[str, set[str]],
        current_evidence_concepts: set[str],
    ) -> dict[str, tuple[tuple[str, str], float, tuple[str, ...], bool]]:
        result: dict[str, tuple[tuple[str, str], float, tuple[str, ...], bool]] = {}
        active = sorted(activation)
        for a, b in combinations(active, 2):
            evidence_a = evidence_by_concept.get(a, set())
            evidence_b = evidence_by_concept.get(b, set())
            union = evidence_a | evidence_b
            if not union:
                continue
            shared = evidence_a & evidence_b
            shared_fraction = len(shared) / max(1, len(union))
            # The weaker endpoint limits pair formation; common grounding gives
            # a modest boost without making lexical co-occurrence sufficient by
            # itself.
            score = min(activation[a], activation[b]) * (0.65 + 0.35 * shared_fraction)
            score = max(0.0, min(1.0, score))
            pair = tuple(sorted((a, b)))
            association_id = self._association_id(*pair)
            result[association_id] = (
                pair,
                score,
                self._bounded_evidence(kernel, set(union)),
                bool(set(pair) & current_evidence_concepts),
            )
        return result

    @staticmethod
    def _degree_map(
        associations: dict[str, PlasticityAssociationRecord],
    ) -> dict[str, int]:
        degree: dict[str, int] = {}
        for record in associations.values():
            for concept_id in record.concept_ids:
                degree[concept_id] = degree.get(concept_id, 0) + 1
        return degree

    def _normalize_strength_budget(
        self,
        kernel: VerdantKernel,
        associations: dict[str, PlasticityAssociationRecord],
        prospective_cycle: int,
        workspace_event_id: str,
    ) -> dict[str, PlasticityAssociationRecord]:
        budget = kernel.state.plasticity_policy.strength_budget_per_concept
        totals: dict[str, float] = {}
        for record in associations.values():
            a, b = record.concept_ids
            totals[a] = totals.get(a, 0.0) + record.strength
            totals[b] = totals.get(b, 0.0) + record.strength
        scale = {
            concept_id: min(1.0, budget / total) if total > 0.0 else 1.0
            for concept_id, total in totals.items()
        }
        result: dict[str, PlasticityAssociationRecord] = {}
        for association_id, record in associations.items():
            factor = min(scale.get(record.concept_ids[0], 1.0), scale.get(record.concept_ids[1], 1.0))
            strength = max(0.0, min(1.0, record.strength * factor))
            if abs(strength - record.strength) <= 1e-12:
                result[association_id] = record
            else:
                result[association_id] = record.model_copy(
                    update={
                        "strength": strength,
                        "updated_cycle": prospective_cycle,
                        "last_workspace_event_id": workspace_event_id,
                    }
                )
        return result

    def _apply_degree_cap(
        self,
        kernel: VerdantKernel,
        associations: dict[str, PlasticityAssociationRecord],
    ) -> dict[str, PlasticityAssociationRecord]:
        max_degree = kernel.state.plasticity_policy.max_degree
        incident: dict[str, list[PlasticityAssociationRecord]] = {}
        for record in associations.values():
            for concept_id in record.concept_ids:
                incident.setdefault(concept_id, []).append(record)
        keep_for: dict[str, set[str]] = {}
        for concept_id, records in incident.items():
            ranked = sorted(records, key=lambda item: (-item.strength, item.association_id))
            keep_for[concept_id] = {item.association_id for item in ranked[:max_degree]}
        # An edge survives only when *both* endpoints have room for it.  This is
        # conservative by design and guarantees the degree ceiling exactly.
        return {
            association_id: record
            for association_id, record in associations.items()
            if association_id in keep_for.get(record.concept_ids[0], set())
            and association_id in keep_for.get(record.concept_ids[1], set())
        }

    def _apply_edge_ratio_cap(
        self,
        kernel: VerdantKernel,
        associations: dict[str, PlasticityAssociationRecord],
    ) -> dict[str, PlasticityAssociationRecord]:
        cap = int(math.floor(kernel.state.plasticity_policy.max_edge_ratio * max(1, len(kernel.state.concepts))))
        if len(associations) <= cap:
            return associations
        ranked = sorted(
            associations.values(),
            key=lambda item: (-item.strength, item.association_id),
        )[:cap]
        return {item.association_id: item for item in ranked}

    def inspect(
        self,
        kernel: VerdantKernel,
        workspace_event: WorkspaceCycleEvent,
    ) -> PlasticityReport:
        workspace_event = self._workspace_event(kernel, workspace_event)
        policy = kernel.state.plasticity_policy
        structural = kernel.plasticity_structural_fingerprint()
        prospective_cycle = kernel.state.cycle + 1
        scope = self._scope(kernel)
        activation, evidence_by_concept, current_evidence = self._activation_state(
            kernel, workspace_event, scope
        )
        pair_info = self._candidate_pairs(
            kernel, activation, evidence_by_concept, current_evidence
        )

        before = dict(kernel.state.plasticity_associations)
        next_associations = dict(before)

        reinforcement_candidates: list[tuple[float, str]] = []
        creation_candidates: list[tuple[float, str]] = []
        for association_id, (_pair, score, _evidence, current_touched) in pair_info.items():
            if association_id in before:
                if score >= policy.reinforcement_threshold:
                    reinforcement_candidates.append((score, association_id))
            elif score >= policy.creation_threshold:
                if not policy.require_current_evidence_for_creation or current_touched:
                    creation_candidates.append((score, association_id))

        reinforcement_ids = {
            association_id
            for _score, association_id in sorted(
                reinforcement_candidates,
                key=lambda item: (-item[0], item[1]),
            )[: policy.max_reinforcements_per_cycle]
        }
        creation_ids = {
            association_id
            for _score, association_id in sorted(
                creation_candidates,
                key=lambda item: (-item[0], item[1]),
            )[: policy.max_new_associations_per_cycle]
        }

        # Local decay occurs only for associations whose two endpoints live in
        # the current plasticity scope.  Dormant regions are not globally swept.
        for association_id, record in list(next_associations.items()):
            if association_id in reinforcement_ids:
                continue
            if not set(record.concept_ids).issubset(scope):
                continue
            strength = record.strength * (1.0 - policy.decay_rate)
            next_associations[association_id] = record.model_copy(
                update={
                    "strength": strength,
                    "updated_cycle": prospective_cycle,
                    "last_workspace_event_id": workspace_event.event_id,
                }
            )

        for association_id in sorted(reinforcement_ids):
            pair, score, evidence, _current_touched = pair_info[association_id]
            prior = next_associations[association_id]
            strength = prior.strength + policy.learning_rate * score * (1.0 - prior.strength)
            merged_evidence = self._bounded_evidence(
                kernel, set(prior.evidence_refs) | set(evidence)
            )
            next_associations[association_id] = prior.model_copy(
                update={
                    "strength": max(0.0, min(1.0, strength)),
                    "exposure_count": prior.exposure_count + 1,
                    "evidence_refs": merged_evidence,
                    "updated_cycle": prospective_cycle,
                    "last_reinforced_cycle": prospective_cycle,
                    "last_workspace_event_id": workspace_event.event_id,
                }
            )

        for association_id in sorted(creation_ids):
            pair, score, evidence, _current_touched = pair_info[association_id]
            strength = policy.initial_strength + policy.learning_rate * score * (1.0 - policy.initial_strength)
            next_associations[association_id] = PlasticityAssociationRecord(
                association_id=association_id,
                concept_ids=pair,
                strength=max(policy.minimum_strength, min(1.0, strength)),
                exposure_count=1,
                evidence_refs=evidence,
                created_cycle=prospective_cycle,
                updated_cycle=prospective_cycle,
                last_reinforced_cycle=prospective_cycle,
                last_workspace_event_id=workspace_event.event_id,
            )

        next_associations = self._normalize_strength_budget(
            kernel,
            next_associations,
            prospective_cycle,
            workspace_event.event_id,
        )
        next_associations = {
            association_id: record
            for association_id, record in next_associations.items()
            if record.strength >= policy.minimum_strength
        }
        next_associations = self._apply_degree_cap(kernel, next_associations)
        next_associations = self._apply_edge_ratio_cap(kernel, next_associations)

        final_ids = set(next_associations)
        prior_ids = set(before)
        created = tuple(sorted(final_ids - prior_ids))
        reinforced = tuple(sorted(reinforcement_ids & final_ids))
        pruned = tuple(sorted(prior_ids - final_ids))
        decayed = tuple(
            sorted(
                association_id
                for association_id in prior_ids & final_ids
                if association_id not in reinforced
                and next_associations[association_id].strength < before[association_id].strength - 1e-12
            )
        )

        assessments: list[PlasticityPairAssessment] = []
        touched_ids = sorted((prior_ids | final_ids) & (set(pair_info) | set(decayed) | set(pruned)))
        for association_id in touched_ids:
            prior = before.get(association_id)
            final = next_associations.get(association_id)
            pair, score, evidence, current_touched = pair_info.get(
                association_id,
                (
                    (prior.concept_ids if prior is not None else final.concept_ids),
                    0.0,
                    (prior.evidence_refs if prior is not None else final.evidence_refs),
                    False,
                ),
            )
            if prior is None and final is not None:
                disposition = PlasticityUpdateKind.CREATE
            elif prior is not None and final is None:
                disposition = PlasticityUpdateKind.PRUNE
            elif association_id in reinforced:
                disposition = PlasticityUpdateKind.REINFORCE
            else:
                disposition = PlasticityUpdateKind.DECAY
            assessments.append(
                PlasticityPairAssessment(
                    association_id=association_id,
                    concept_ids=pair,
                    coactivation_score=score,
                    current_evidence_touched=current_touched,
                    evidence_refs=tuple(sorted(set(evidence))),
                    disposition=disposition,
                    prior_strength=prior.strength if prior is not None else 0.0,
                    proposed_strength=final.strength if final is not None else 0.0,
                )
            )

        proposed = tuple(next_associations[key] for key in sorted(next_associations))
        degree = self._degree_map(next_associations)
        max_degree_after = max(degree.values(), default=0)
        edge_ratio_after = len(proposed) / max(1, len(kernel.state.concepts))
        operation = "bounded_local_plasticity"
        report_id = stable_id(
            "plasticity_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            structural,
            workspace_event.event_id,
            tuple(sorted(activation)),
            tuple(item.model_dump(mode="json") for item in assessments),
            tuple(item.model_dump(mode="json") for item in proposed),
            created,
            reinforced,
            decayed,
            pruned,
            len(before),
            len(proposed),
            max_degree_after,
            edge_ratio_after,
            operation,
            policy.revision,
        )
        report = PlasticityReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=structural,
            workspace_event_id=workspace_event.event_id,
            candidate_concept_ids=tuple(sorted(activation)),
            assessments=tuple(assessments),
            proposed_associations=proposed,
            created_association_ids=created,
            reinforced_association_ids=reinforced,
            decayed_association_ids=decayed,
            pruned_association_ids=pruned,
            edge_count_before=len(before),
            edge_count_after=len(proposed),
            max_degree_after=max_degree_after,
            edge_ratio_after=edge_ratio_after,
            operation=operation,
            policy_revision=policy.revision,
        )
        kernel.validate_plasticity_report(report)
        return report

    def commit(
        self,
        kernel: VerdantKernel,
        report: PlasticityReport,
    ) -> PlasticityEvent:
        try:
            report = PlasticityReport.model_validate(report.model_dump(mode="json"))
        except ValueError as exc:
            raise PlasticityStaleError("Plasticity report is invalid.") from exc
        workspace_event = next(
            (
                item
                for item in kernel.state.workspace_cycle_events
                if item.event_id == report.workspace_event_id
            ),
            None,
        )
        if workspace_event is None:
            raise PlasticityStaleError("Plasticity workspace lineage is missing.")
        reproduced = self.inspect(kernel, workspace_event)
        if reproduced != report:
            raise PlasticityStaleError(
                "Plasticity report does not reproduce from current state."
            )
        return kernel.commit_plasticity_report(report)

    def run_cycle(
        self,
        kernel: VerdantKernel,
        workspace_event: WorkspaceCycleEvent,
    ) -> PlasticityCycleResult:
        report = self.inspect(kernel, workspace_event)
        event = self.commit(kernel, report)
        return PlasticityCycleResult(report=report, event=event)
