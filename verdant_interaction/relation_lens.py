"""Experimental READ-ONLY P-to-P relation lens; native topology remains unchanged.

This is a non-authoritative sidecar. It does not create canonical relations,
modify Q eligibility, promote P/Q, or reinterpret labels as semantic truth.

Native P promotion snapshots immutable member_relation_ids, but the referenced
canonical RelationRecord remains stateful; this sidecar explicitly reports
the *current* relation record status and refuses incomplete provenance.
"""
from __future__ import annotations

from collections import Counter
from itertools import permutations

from verdant_interaction.pipeline import VerdantStructureInteractionPipeline
from verdant_kernel import RelationStatus, VerdantKernel


class RelationAwareLens:
    """Match topology AND witnessed typed directed roles on a SINGLE mapping."""

    def __init__(self) -> None:
        self.native = VerdantStructureInteractionPipeline()

    @staticmethod
    def _relations(kernel: VerdantKernel, structure) -> tuple[tuple, ...] | None:
        members = set(structure.member_concept_ids)
        if not structure.member_relation_ids:
            return None
        rows = []
        for rid in structure.member_relation_ids:
            relation = kernel.state.relations.get(rid)
            if (relation is None
                or relation.status not in (RelationStatus.SUPPORTED, RelationStatus.CONFIRMED)
                or relation.source_concept_id not in members
                or relation.target_concept_id not in members
                or not relation.evidence_refs
                or any(ref not in kernel.state.evidence for ref in relation.evidence_refs)):
                return None
            rows.append((
                relation.source_concept_id, relation.target_concept_id,
                relation.relation_type, relation.directed,
            ))
        return tuple(sorted(rows))

    @staticmethod
    def _token(a: str, b: str, relation_type: str, directed: bool) -> tuple:
        endpoints = (a, b) if directed else tuple(sorted((a, b)))
        return (relation_type, directed, *endpoints)

    @staticmethod
    def _topology_score(source, target, mapping, threshold: float) -> float:
        # Reproduce native topology's per-mapping F1 + weighted edge match.
        source_edges = VerdantStructureInteractionPipeline._edge_map(source)
        target_edges = VerdantStructureInteractionPipeline._edge_map(target)
        source_max = max(source_edges.values(), default=1.0)
        target_max = max(target_edges.values(), default=1.0)
        left = {key: weight / source_max for key, weight in source_edges.items()}
        right = {key: weight / target_max for key, weight in target_edges.items()}
        mapped = {
            tuple(sorted((mapping[a], mapping[b]))): value
            for (a, b), value in left.items()
        }
        present_a = {key for key, value in mapped.items() if value >= threshold}
        present_b = {key for key, value in right.items() if value >= threshold}
        overlap = len(present_a.intersection(present_b))
        f1 = (
            2.0 * overlap / (len(present_a) + len(present_b))
            if present_a or present_b else 1.0
        )
        union = present_a | present_b
        strength = (
            sum(1.0 - abs(mapped.get(edge, 0.0) - right.get(edge, 0.0))
                for edge in union) / len(union)
            if union else 1.0
        )
        return max(0.0, min(1.0, 0.72 * f1 + 0.28 * strength))

    @staticmethod
    def _typed_f1(source_rows, target_rows, mapping) -> float:
        source_tokens = Counter(
            RelationAwareLens._token(mapping[a], mapping[b], typ, directed)
            for a, b, typ, directed in source_rows
        )
        target_tokens = Counter(
            RelationAwareLens._token(a, b, typ, directed)
            for a, b, typ, directed in target_rows
        )
        overlap = sum((source_tokens & target_tokens).values())
        denom = sum(source_tokens.values()) + sum(target_tokens.values())
        return 2.0 * overlap / denom if denom else 0.0

    def inspect(
        self,
        kernel: VerdantKernel,
        source_structure_id: str,
        target_structure_id: str,
        *,
        minimum_typed_f1: float = 0.90,
    ) -> dict:
        if not 0.0 <= minimum_typed_f1 <= 1.0:
            raise ValueError("Typed role threshold must be within [0,1]")
        if source_structure_id == target_structure_id:
            raise ValueError("Comparisons require distinct native P structures")
        left = self.native._structure(kernel, source_structure_id)
        right = self.native._structure(kernel, target_structure_id)
        original = kernel.fingerprint()
        policy = kernel.state.structure_interaction_policy
        baseline, _ = self.native._symbolic_alignment(kernel, left, right)
        baseline_accept = baseline >= policy.minimum_symbolic_similarity

        rows_a = self._relations(kernel, left)
        rows_b = self._relations(kernel, right)
        result = dict(
            source_p=source_structure_id,
            target_p=target_structure_id,
            baseline_topology_score=baseline,
            baseline_accept=baseline_accept,
            native_minimum_symbolic_similarity=policy.minimum_symbolic_similarity,
            typed_f1=None,
            typed_threshold=minimum_typed_f1,
            verdict="abstain",
            reason="missing_or_unusable_member_relation_provenance",
            best_mapping=[],
            evaluated_mappings=0,
            source_relation_count=len(rows_a) if rows_a is not None else 0,
            target_relation_count=len(rows_b) if rows_b is not None else 0,
            relation_state="current_checkpoint_records_not_frozen_promotion_semantics",
            canonical_mutation_permitted=False,
        )

        a_ids, b_ids = tuple(sorted(left.member_concept_ids)), tuple(sorted(right.member_concept_ids))
        if rows_a is not None and rows_b is not None:
            if len(a_ids) != len(b_ids) or len(a_ids) > policy.maximum_exact_members:
                result["reason"] = "incompatible_member_sizes"
            else:
                best = (-1.0, ())
                for permutation in permutations(b_ids):
                    mapping = dict(zip(a_ids, permutation))
                    result["evaluated_mappings"] += 1
                    score = self._topology_score(
                        left, right, mapping, policy.edge_presence_threshold
                    )
                    if score < policy.minimum_symbolic_similarity:
                        continue
                    typed = self._typed_f1(rows_a, rows_b, mapping)
                    mapped = tuple(zip(a_ids, permutation))
                    if typed > best[0] + 1e-12 or (abs(typed - best[0]) <= 1e-12 and mapped < best[1]):
                        best = (typed, mapped)
                result["typed_f1"] = max(0.0, best[0]) if best[0] >= 0.0 else 0.0
                result["best_mapping"] = [list(x) for x in best[1]]
                if not baseline_accept:
                    result.update(verdict="reject", reason="native_topology_below_threshold")
                elif best[0] >= minimum_typed_f1:
                    result.update(verdict="accept", reason="same_mapping_preserves_topology_and_typed_roles")
                else:
                    result.update(verdict="reject", reason="typed_or_directional_roles_mismatch")
        if kernel.fingerprint() != original:
            raise RuntimeError("Relation lens mutated Verdant canonical state")
        return result
