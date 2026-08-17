from __future__ import annotations

from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import HierarchyCandidateStatus, StructureCandidateStatus
from verdant_structures import VerdantStructurePipeline

from .ethomorphism import (
    ArmName,
    EthomorphismBenchmarkHarness as _LegacyEthomorphismBenchmarkHarness,
)


class OracleFreeEthomorphismBenchmarkHarness(_LegacyEthomorphismBenchmarkHarness):
    """Milestone 19 A/B/C/D harness with evaluator-independent promotion.

    The original M19 harness correctly withheld semantic family labels from
    Verdant state, but it still used evaluator ground truth to choose the exact
    P candidate for each benchmark world and the exact Q candidate for the
    training family before calling promotion. That made the reported
    object-selection result oracle-assisted.

    This harness keeps the same primitive curriculum and downstream assays but
    changes the formation boundary:

    * every currently eligible P candidate may be submitted to the native
      promotion/Council path without consulting world membership;
    * every promoted P is allowed to interact before Q formation;
    * every currently eligible Q candidate may be submitted to the native
      promotion/Council path without consulting the hidden family;
    * world-to-structure and family-to-Q mappings are reconstructed only after
      all training/promotion is complete, solely for scoring and interventions;
    * scoring-index construction is fingerprint-checked to ensure it does not
      mutate Verdant kernel state;
    * the benchmark fails validation if the oracle-free D arm promotes extra P
      or Q objects outside the evaluator-known target set in this controlled
      population.

    The evaluator may measure what Verdant made. It may not choose what Verdant
    gets to make.
    """

    def _promote_eligible_structures(self, runtime) -> None:
        """Submit every eligible P candidate without benchmark-ground-truth ranking."""
        if runtime.name != ArmName.D_FULL:
            return
        pipeline = VerdantStructurePipeline()
        candidates = sorted(
            runtime.kernel.state.structure_candidates.values(),
            key=lambda item: item.candidate_id,
        )
        for candidate in candidates:
            if candidate.status == StructureCandidateStatus.PROMOTED:
                continue
            try:
                pipeline.promote(runtime.kernel, candidate.candidate_id)
            except ValueError:
                # Native promotion inspection remains the authority. A stale or
                # not-yet-eligible candidate is simply left unpromoted.
                continue

    def _build_q_from_earned_interactions(self, runtime) -> None:
        """Let the full promoted-P population interact, then submit every eligible Q."""
        if runtime.name != ArmName.D_FULL:
            return
        interaction = VerdantStructureInteractionPipeline()
        hierarchy = VerdantHierarchyPipeline()

        # No family/world lookup occurs here. Every available promoted P gets
        # the same opportunity to contribute verified interaction evidence.
        for structure_id in sorted(runtime.kernel.state.structures):
            if not runtime.kernel.structure_is_available(structure_id):
                continue
            interaction.interact(runtime.kernel, structure_id)
            hierarchy.observe(runtime.kernel)

        candidates = sorted(
            runtime.kernel.state.hierarchy_candidates.values(),
            key=lambda item: item.candidate_id,
        )
        for candidate in candidates:
            if candidate.status == HierarchyCandidateStatus.PROMOTED:
                continue
            try:
                hierarchy.promote(runtime.kernel, candidate.candidate_id)
            except ValueError:
                continue

    def train_arm_unscored(self, arm: ArmName):
        """Train one arm without constructing any evaluator scoring index."""
        runtime = self._new_arm(arm)

        # The three training worlds arrive first. D may form/promote P objects
        # only from its own candidate/gate state.
        for world in self.family_worlds:
            self._feed_world(runtime, world)
            self._promote_eligible_structures(runtime)

        # Q formation occurs before the star and held-out world exist, exactly
        # as in the original protocol, but without a hidden-family selector.
        self._build_q_from_earned_interactions(runtime)

        # The control and held-out worlds arrive after higher-order formation.
        for world in (self.star_world, self.novel_world):
            self._feed_world(runtime, world)
            self._promote_eligible_structures(runtime)

        # These fields are evaluator metadata. They must remain empty until the
        # kernel has finished all formation/promotion work.
        runtime.structure_by_world.clear()
        runtime.layered_structure_id = None
        return runtime

    def index_runtime_for_scoring(self, runtime):
        """Build ground-truth mappings after training, without mutating kernel state."""
        before = runtime.kernel.fingerprint()
        runtime.structure_by_world.clear()
        runtime.layered_structure_id = None

        if runtime.name == ArmName.D_FULL:
            # Ground truth is allowed here because this mapping is used only to
            # score/query already-existing objects. It cannot alter promotion.
            for world_name, world in sorted(runtime.worlds.items()):
                expected = set(world.labels)
                matches = [
                    structure
                    for structure in runtime.kernel.state.structures.values()
                    if set(self._labels(runtime.kernel, structure.member_concept_ids)) == expected
                ]
                if matches:
                    matches.sort(key=lambda item: item.structure_id)
                    runtime.structure_by_world[world_name] = matches[0].structure_id

            if all(world.name in runtime.structure_by_world for world in self.family_worlds):
                family_ids = {
                    runtime.structure_by_world[world.name] for world in self.family_worlds
                }
                q_matches = [
                    layered
                    for layered in runtime.kernel.state.layered_structures.values()
                    if set(layered.member_structure_ids) == family_ids
                ]
                if q_matches:
                    q_matches.sort(key=lambda item: item.layered_structure_id)
                    runtime.layered_structure_id = q_matches[0].layered_structure_id

        after = runtime.kernel.fingerprint()
        if after != before:
            raise RuntimeError("Evaluator scoring index mutated Verdant kernel state.")
        return runtime

    def train_arm(self, arm: ArmName):
        runtime = self.train_arm_unscored(arm)
        return self.index_runtime_for_scoring(runtime)

    def promotion_selectivity(self) -> dict:
        """Score false-positive/false-negative promotion after formation is complete."""
        runtime = self.train_arm(ArmName.D_FULL)
        expected_world_names = tuple(
            world.name for world in (*self.family_worlds, self.star_world, self.novel_world)
        )
        missing_worlds = tuple(
            sorted(name for name in expected_world_names if name not in runtime.structure_by_world)
        )
        expected_p_ids = set(runtime.structure_by_world.values())
        promoted_p_ids = set(runtime.kernel.state.structures)
        extra_p_ids = tuple(sorted(promoted_p_ids - expected_p_ids))

        target_q_id = runtime.layered_structure_id
        expected_q_ids = {target_q_id} if target_q_id is not None else set()
        promoted_q_ids = set(runtime.kernel.state.layered_structures)
        extra_q_ids = tuple(sorted(promoted_q_ids - expected_q_ids))

        return {
            "expected_world_count": len(expected_world_names),
            "promoted_p_count": len(promoted_p_ids),
            "missing_worlds": missing_worlds,
            "extra_p_ids": extra_p_ids,
            "target_q_found": target_q_id is not None,
            "promoted_q_count": len(promoted_q_ids),
            "extra_q_ids": extra_q_ids,
        }

    def run(self):
        summary = super().run()
        audit = self.promotion_selectivity()
        summary.schema = "verdant.ethomorphism_benchmark.v2_oracle_free"
        summary.headline_checks[
            "d_oracle_free_p_promotion_is_selective"
        ] = bool(
            not audit["missing_worlds"]
            and not audit["extra_p_ids"]
            and audit["promoted_p_count"] == audit["expected_world_count"]
        )
        summary.headline_checks[
            "d_oracle_free_q_promotion_is_selective"
        ] = bool(
            audit["target_q_found"]
            and not audit["extra_q_ids"]
            and audit["promoted_q_count"] == 1
        )
        summary.interpretation["promotion_boundary"] = (
            "P/Q promotion in the A/B/C/D formation path receives no evaluator-known world membership, "
            "family membership, expected member set, or target candidate ID. Ground truth is reconstructed "
            "only after formation for scoring, and scoring-index construction is kernel-fingerprint neutral."
        )
        summary.interpretation["promotion_selectivity"] = (
            f"expected_worlds={audit['expected_world_count']}; promoted_p={audit['promoted_p_count']}; "
            f"missing_worlds={len(audit['missing_worlds'])}; extra_p={len(audit['extra_p_ids'])}; "
            f"target_q_found={audit['target_q_found']}; promoted_q={audit['promoted_q_count']}; "
            f"extra_q={len(audit['extra_q_ids'])}."
        )
        summary.interpretation["historical_warning"] = (
            "The original M19 reference numbers predate this oracle-free formation path and must not be "
            "used as evidence of evaluator-independent P/Q selection until this harness is rerun."
        )
        summary.interpretation["refolding_boundary"] = (
            "The separate refolding assay remains an explicitly targeted causal intervention: its purpose "
            "is to test refolding after a target structure is established, not autonomous target selection."
        )
        return summary


# Canonical exported name used by the benchmark runner and existing tests.
EthomorphismBenchmarkHarness = OracleFreeEthomorphismBenchmarkHarness

__all__ = [
    "EthomorphismBenchmarkHarness",
    "OracleFreeEthomorphismBenchmarkHarness",
]
