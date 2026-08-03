from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from verdant_kernel import (
    CompilationCost,
    CompilationDisposition,
    CompilationProbeEvent,
    CompilationProbeReport,
    CompilationIntegrityError,
    VerdantKernel,
)
from verdant_kernel.models import stable_id


@dataclass(frozen=True)
class CompilationProbeResult:
    report: CompilationProbeReport
    event: CompilationProbeEvent | None = None


class VerdantCompilationPipeline:
    """Use-driven cognitive compilation for promoted earned structures.

    The operation is intentionally narrow and measurable. Given one or more
    canonical cue concepts, Verdant must reconstruct the bounded learned region
    relevant to those cues. Without a usable promoted structure it performs a
    bounded traversal over learned plastic associations. With a usable
    structure, the same operation may load that structure as one operand and
    recover its preserved member set without re-traversing the local graph.

    This does not claim cross-domain abstraction. It tests the Milestone 15
    question: did manufacturing P change the cost of later computation?
    """

    @staticmethod
    def _scope(kernel: VerdantKernel) -> set[str]:
        shard = kernel.state.shards[kernel.state.active_shard_id]
        return set(shard.concept_ids)

    @staticmethod
    def _normalize_cues(kernel: VerdantKernel, cue_concept_ids) -> tuple[str, ...]:
        cues = tuple(sorted(set(cue_concept_ids)))
        if not cues:
            raise CompilationIntegrityError("Compilation probe requires at least one cue concept.")
        missing = [item for item in cues if item not in kernel.state.concepts]
        if missing:
            raise CompilationIntegrityError(
                "Compilation probe references missing concepts: " + ", ".join(missing)
            )
        return cues

    def _low_level_reconstruct(
        self,
        kernel: VerdantKernel,
        cues: tuple[str, ...],
    ) -> tuple[tuple[str, ...], CompilationCost]:
        policy = kernel.state.compilation_policy
        scope = self._scope(kernel)
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for association in kernel.state.plasticity_associations.values():
            if association.strength < policy.minimum_association_strength:
                continue
            a, b = association.concept_ids
            if a not in scope or b not in scope:
                continue
            adjacency.setdefault(a, []).append((association.association_id, b))
            adjacency.setdefault(b, []).append((association.association_id, a))
        for concept_id in adjacency:
            adjacency[concept_id].sort()

        visited = set(cues)
        queue = deque((cue, 0) for cue in cues)
        inspected = 0
        traversed_ids: set[str] = set()
        while queue and len(visited) < policy.maximum_low_level_concepts:
            concept_id, depth = queue.popleft()
            inspected += 1
            if depth >= policy.maximum_low_level_hops:
                continue
            for association_id, neighbor in adjacency.get(concept_id, ()):
                traversed_ids.add(association_id)
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
                if len(visited) >= policy.maximum_low_level_concepts:
                    break
        cost = CompilationCost(
            concepts_inspected=inspected,
            associations_traversed=len(traversed_ids),
            structures_inspected=0,
            structure_operands_used=0,
            reconstructed_concepts=len(visited),
            estimated_workspace_resource=min(
                kernel.state.workspace_policy.resource_budget,
                0.03 * inspected + 0.015 * len(traversed_ids),
            ),
        )
        return tuple(sorted(visited)), cost

    def _best_structure(
        self,
        kernel: VerdantKernel,
        cues: tuple[str, ...],
    ):
        policy = kernel.state.compilation_policy
        cue_set = set(cues)
        available = []
        for structure in kernel.state.structures.values():
            if not kernel.structure_is_available(structure.structure_id):
                continue
            overlap = len(cue_set.intersection(structure.member_concept_ids))
            if overlap < policy.minimum_trigger_members:
                continue
            available.append(
                (
                    -overlap,
                    -structure.quality_at_promotion.reconstructability,
                    structure.structure_id,
                    structure,
                )
            )
        if not available:
            return None, 0
        available.sort(key=lambda item: item[:3])
        return available[0][3], len(available)

    def inspect(
        self,
        kernel: VerdantKernel,
        cue_concept_ids,
    ) -> CompilationProbeReport:
        cues = self._normalize_cues(kernel, cue_concept_ids)
        baseline_members, baseline_cost = self._low_level_reconstruct(kernel, cues)
        structure, structures_inspected = self._best_structure(kernel, cues)
        if structure is None:
            disposition = CompilationDisposition.FALLBACK_LOW_LEVEL
            reconstructed = baseline_members
            cost = baseline_cost.model_copy(
                update={"structures_inspected": structures_inspected}
            )
            structure_id = None
            compression_gain = 0.0
        else:
            disposition = CompilationDisposition.USE_STRUCTURE
            reconstructed = tuple(sorted(set(cues) | set(structure.member_concept_ids)))
            cost = CompilationCost(
                concepts_inspected=len(cues),
                associations_traversed=0,
                structures_inspected=max(1, structures_inspected),
                structure_operands_used=1,
                reconstructed_concepts=len(reconstructed),
                estimated_workspace_resource=kernel.state.compilation_policy.structure_workspace_resource,
            )
            structure_id = structure.structure_id
            baseline_work = max(1, baseline_cost.low_level_work)
            compiled_work = cost.low_level_work
            compression_gain = max(0.0, min(1.0, 1.0 - compiled_work / baseline_work))

        fingerprint = kernel.compilation_structural_fingerprint()
        policy_revision = kernel.state.compilation_policy.revision
        report_id = stable_id(
            "compilation_probe_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            fingerprint,
            cues,
            reconstructed,
            disposition.value,
            structure_id,
            cost.model_dump(mode="json"),
            baseline_cost.model_dump(mode="json"),
            compression_gain,
            "reconstruct_relational_region",
            policy_revision,
        )
        return CompilationProbeReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=fingerprint,
            cue_concept_ids=cues,
            reconstructed_concept_ids=reconstructed,
            disposition=disposition,
            structure_id=structure_id,
            cost=cost,
            baseline_cost=baseline_cost,
            compression_gain=compression_gain,
            operation="reconstruct_relational_region",
            policy_revision=policy_revision,
        )

    def commit(self, kernel: VerdantKernel, report: CompilationProbeReport) -> CompilationProbeEvent:
        return kernel.commit_compilation_probe(report)

    def probe(self, kernel: VerdantKernel, cue_concept_ids) -> CompilationProbeResult:
        report = self.inspect(kernel, cue_concept_ids)
        event = self.commit(kernel, report)
        return CompilationProbeResult(report=report, event=event)

    @staticmethod
    def ablate(kernel: VerdantKernel, structure_id: str, reason: str = "controlled ablation"):
        return kernel.set_structure_availability(
            structure_id,
            available=False,
            reason=reason,
        )

    @staticmethod
    def restore(kernel: VerdantKernel, structure_id: str, reason: str = "controlled restoration"):
        return kernel.set_structure_availability(
            structure_id,
            available=True,
            reason=reason,
        )
