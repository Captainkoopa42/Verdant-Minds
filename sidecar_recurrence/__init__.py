"""Opt-in structure observer that counts recurrence from the experience itself.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is changed; this
is a subclass injected through ``VerdantDevelopmentPipeline(structures=...)``.

Stock behaviour: a candidate is observed at an exposure only if its member bonds are
already >= ``minimum_member_association_strength`` (0.28) at that moment, so widely
spaced lessons lose their early occurrences to decay.

This observer changes one thing: a living bond whose two concepts are BOTH present in
the current experience is admitted to membership whatever its strength. Bonds reaching
outside the current experience still need the stock threshold. Every promotion gate
(recurrence 4, evidence, contexts, reconstructability, boundary selectivity, cohesion)
is untouched and still decides eligibility.
"""
from __future__ import annotations

from verdant_kernel import VerdantKernel
from verdant_structures import VerdantStructurePipeline

__all__ = ["ExperienceRecurrenceStructurePipeline"]


class ExperienceRecurrenceStructurePipeline(VerdantStructurePipeline):
    def _candidate_memberships(self, kernel: VerdantKernel) -> tuple[tuple[str, ...], ...]:
        policy = kernel.state.structure_policy
        scope = self._scope(kernel)
        seeds = self._latest_current_concepts(kernel).intersection(scope)
        if not seeds:
            return ()
        eligible = [
            a for a in kernel.state.plasticity_associations.values()
            if set(a.concept_ids).issubset(scope)
            and (a.strength >= policy.minimum_member_association_strength or set(a.concept_ids) <= seeds)
        ]
        incident: dict[str, list] = {}
        for a in eligible:
            for c in a.concept_ids:
                incident.setdefault(c, []).append(a)
        memberships: dict[tuple[str, ...], float] = {}
        for seed in sorted(seeds):
            ranked = sorted(incident.get(seed, []), key=lambda i: (-i.strength, i.association_id))[: policy.maximum_neighbors_per_seed]
            members = {seed}; score = 0.0
            for a in ranked:
                members.update(a.concept_ids); score += a.strength
                if len(members) >= policy.maximum_members:
                    break
            if len(members) < policy.minimum_members:
                for hop in sorted(members - {seed}):
                    for a in sorted(incident.get(hop, []), key=lambda i: (-i.strength, i.association_id)):
                        members.update(a.concept_ids); score += a.strength
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
        ranked_m = sorted(memberships.items(), key=lambda i: (-i[1], i[0]))[: policy.maximum_candidates_per_cycle]
        return tuple(i[0] for i in ranked_m)
