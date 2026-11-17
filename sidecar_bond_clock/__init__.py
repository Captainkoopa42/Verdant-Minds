"""Opt-in plasticity stage with the decay clock on the bond.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is changed; this
subclass is injected through ``VerdantDevelopmentPipeline(plasticity=...)``.

``inspect`` below is the stock ``VerdantPlasticityPipeline.inspect`` with ONE block
changed (the local decay line). It was derived from stock source with sha256
64a013f16ea2791d1ab040ff9bbffb20a2869530701ba95e0c3a4006f155d824
and ``tests/test_bond_clock_sidecar.py`` fails if the stock method drifts from that.

Stock rule: every plasticity cycle multiplies every non-reinforced bond by (1 - decay_rate).

Bond-clock rule (three parts, each a refusal first):
  1. durability  - a bond's rate is decay_rate / n, where n is the number of REAL
                   exposures behind it (OBSERVATION evidence only, capped). A bond
                   experienced once decays exactly as stock and still dies.
  2. floor       - a bond with at least ``floor_after`` real exposures does not decay
                   below ``earned_floor``. Caps, budget normalisation and pruning by
                   competition still apply to it.
  3. free sleep  - a rehearsal beat (a workspace cycle carrying a ``sidecar_rehearsal``
                   item) applies no time decay to anything.
"""
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

from verdant_kernel.models import EvidenceKind
from verdant_plasticity.pipeline import VerdantPlasticityPipeline

__all__ = ["BondClockPlasticityPipeline", "STOCK_INSPECT_SHA256"]

STOCK_INSPECT_SHA256 = "64a013f16ea2791d1ab040ff9bbffb20a2869530701ba95e0c3a4006f155d824"


class BondClockPlasticityPipeline(VerdantPlasticityPipeline):
    def __init__(self, *, durability_cap: int = 5, floor_after: int = 3, earned_floor: float = 0.10) -> None:
        super().__init__()
        if durability_cap < 1 or floor_after < 2 or not 0.0 <= earned_floor < 1.0:
            raise ValueError("Bond clock needs durability_cap>=1, floor_after>=2, 0<=earned_floor<1.")
        self.durability_cap = durability_cap; self.floor_after = floor_after; self.earned_floor = earned_floor

    @staticmethod
    def _real_exposures(kernel, record) -> int:
        evidence = kernel.state.evidence
        return sum(1 for ref in record.evidence_refs if ref in evidence and evidence[ref].kind == EvidenceKind.OBSERVATION)

    @staticmethod
    def _is_rehearsal_beat(kernel, workspace_event) -> bool:
        items = kernel.state.workspace_items
        return any(items[i].metadata.get("developmental_stage") == "sidecar_rehearsal"
                   for i in workspace_event.active_item_ids if i in items)

    def _bond_clock_rate(self, kernel, record, stock_rate: float, rehearsal_beat: bool) -> float:
        if rehearsal_beat:
            return 0.0
        return stock_rate / max(1, min(self.durability_cap, self._real_exposures(kernel, record)))

    def _bond_clock_floor(self, kernel, record) -> float:
        if self._real_exposures(kernel, record) >= self.floor_after:
            return min(record.strength, self.earned_floor)
        return 0.0

    def inspect(
        self,
        kernel: VerdantKernel,
        workspace_event: WorkspaceCycleEvent,
    ) -> PlasticityReport:
        workspace_event = self._workspace_event(kernel, workspace_event)
        policy = kernel.state.plasticity_policy
        rehearsal_beat = self._is_rehearsal_beat(kernel, workspace_event)
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
            rate = self._bond_clock_rate(kernel, record, policy.decay_rate, rehearsal_beat)
            strength = max(record.strength * (1.0 - rate), self._bond_clock_floor(kernel, record))
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
