"""Read-only relational abstraction and exact typed transfer atop NATIVE Council-earned Q.

Native Q formation, structure similarity, and governance remain unchanged.
This sidecar interprets each promoted Q as one or more typed-role subgroups,
without assuming different types are synonymous.

Safety invariant at strict typed F1=1.0: role-canonicalization is a NECESSARY
prefilter, never a substitute for full native-topology + typed-role verification.
Every reported positive gets the exact RelationAwareLens verification.
Missing/invalid role provenance is explicitly rechecked and ABSTAINS.
"""
from __future__ import annotations

from collections import defaultdict
from itertools import permutations

from verdant_interaction.relation_lens import RelationAwareLens
from verdant_kernel import VerdantKernel


class RelationalAbstractionProbe:
    """Three controlled query paths: exhaustive, keyed-P, Q-group-indexed.

    Strict exact type/direction preservation only. Cross-type analogy remains
    visible in native topology scores but is not treated as typed equivalence.
    """

    def __init__(self) -> None:
        self.lens = RelationAwareLens()

    @staticmethod
    def _role_key(kernel: VerdantKernel, sid: str) -> tuple | None:
        structure = kernel.state.structures[sid]
        rows = RelationAwareLens._relations(kernel, structure)
        if rows is None:
            return None
        members = tuple(sorted(structure.member_concept_ids))
        policy = kernel.state.structure_interaction_policy
        if len(members) > policy.maximum_exact_members:
            return None
        # Directed relation roles are ordered; undirected pairs are unordered.
        # Identity-invariant under arbitrary *concept name* permutations.
        best = None
        for ordering in permutations(range(len(members))):
            rename = dict(zip(members, ordering))
            tokens = tuple(sorted(
                RelationAwareLens._token(rename[a], rename[b], typ, directed)
                for a, b, typ, directed in rows
            ))
            if best is None or tokens < best:
                best = tokens
        return (len(members), best)

    def _reference(
        self, kernel: VerdantKernel, query_sid: str, available: tuple[str, ...],
    ) -> dict:
        verdicts = {}
        mappings = 0
        for sid in available:
            r = self.lens.inspect(kernel, query_sid, sid, minimum_typed_f1=1.0)
            verdicts[sid] = r["verdict"]
            mappings += r["evaluated_mappings"]
        return dict(
            verdicts=verdicts,
            exact_verifications=len(available),
            permutations_examined=mappings,
            key_comparisons=0,
            q_group_key_comparisons=0,
            incomplete_evidence_rechecks=0,
        )

    def _keyed(
        self, kernel: VerdantKernel, query_sid: str, available: tuple[str, ...],
        query_key: tuple | None, cached_keys: dict[str, tuple | None],
    ) -> dict:
        verdicts = {}
        verifications = mappings = rechecks = 0
        for sid in available:
            key = cached_keys[sid]
            if query_key is not None and key is not None and key != query_key:
                verdicts[sid] = "reject"
            else:
                r = self.lens.inspect(kernel, query_sid, sid, minimum_typed_f1=1.0)
                verdicts[sid] = r["verdict"]
                verifications += 1
                mappings += r["evaluated_mappings"]
                if key is None or query_key is None:
                    rechecks += 1
        return dict(
            verdicts=verdicts,
            exact_verifications=verifications,
            permutations_examined=mappings,
            key_comparisons=len(available),
            q_group_key_comparisons=0,
            incomplete_evidence_rechecks=rechecks,
        )

    def _q_index(
        self, kernel: VerdantKernel, query_sid: str, available: tuple[str, ...],
        query_key: tuple | None, cached_keys: dict[str, tuple | None],
    ) -> dict:
        # Every P is covered at MOST once, preventing duplicate credit from
        # overlapping Qs. Q memberships are authoritative and never inferred.
        uncovered = set(available)
        groups = []
        used_q = []
        for qid, q in sorted(kernel.state.layered_structures.items()):
            if not kernel.layered_structure_is_available(qid):
                continue
            members = [sid for sid in q.member_structure_ids if sid in uncovered]
            if not members:
                continue
            for sid in members:
                uncovered.remove(sid)
            buckets = defaultdict(list)
            for sid in members:
                buckets[cached_keys[sid]].append(sid)
            for key, ids in sorted(buckets.items(), key=lambda x: repr(x[0])):
                groups.append((key, tuple(sorted(ids)), qid))
            used_q.append(qid)

        verdicts = {}
        verifications = mappings = rechecks = checked = 0
        for key, members, qid in groups:
            checked += 1  # ONE typed-role key comparison per Q subgroup
            if key is not None and query_key is not None and key != query_key:
                for sid in members:
                    verdicts[sid] = "reject"
            else:
                for sid in members:
                    r = self.lens.inspect(
                        kernel, query_sid, sid, minimum_typed_f1=1.0
                    )
                    verdicts[sid] = r["verdict"]
                    verifications += 1
                    mappings += r["evaluated_mappings"]
                    if key is None or query_key is None:
                        rechecks += 1
        for sid in sorted(uncovered):
            checked += 1
            key = cached_keys[sid]
            if key is not None and query_key is not None and key != query_key:
                verdicts[sid] = "reject"
            else:
                r = self.lens.inspect(
                    kernel, query_sid, sid, minimum_typed_f1=1.0
                )
                verdicts[sid] = r["verdict"]
                verifications += 1
                mappings += r["evaluated_mappings"]
                if key is None or query_key is None:
                    rechecks += 1
        if set(verdicts) != set(available):
            raise RuntimeError("Q role-overlay failed to cover every available P")
        return dict(
            verdicts=verdicts,
            exact_verifications=verifications,
            permutations_examined=mappings,
            key_comparisons=checked,
            q_group_key_comparisons=len(groups),
            q_groups=len(groups),
            q_ids_used=used_q,
            unmatched_p_not_in_q=len(uncovered),
            incomplete_evidence_rechecks=rechecks,
        )

    @staticmethod
    def _score(report: dict) -> dict:
        verdicts = report.pop("verdicts")
        report["accepted_ids"] = sorted(
            sid for sid, verdict in verdicts.items() if verdict == "accept"
        )
        report["abstained_ids"] = sorted(
            sid for sid, verdict in verdicts.items() if verdict == "abstain"
        )
        report["rejected_count"] = sum(
            verdict == "reject" for verdict in verdicts.values()
        )
        report["all_verdicts"] = dict(sorted(verdicts.items()))
        return report

    def inspect(self, kernel: VerdantKernel, query_sid: str) -> dict:
        if query_sid not in kernel.state.structures or not kernel.structure_is_available(query_sid):
            raise ValueError("Query must be an available, genuinely promoted native P")
        before = kernel.fingerprint()
        available = tuple(sorted(
            sid for sid in kernel.state.structures
            if sid != query_sid and kernel.structure_is_available(sid)
        ))
        # Source of truth is the CURRENT checkpoint relation ledger. Group
        # projection is deliberately not counted as free persistent memory.
        cached_keys = {sid: self._role_key(kernel, sid) for sid in available}
        query_key = self._role_key(kernel, query_sid)
        reference = self._score(self._reference(kernel, query_sid, available))
        keyed = self._score(self._keyed(
            kernel, query_sid, available, query_key, cached_keys
        ))
        q_grouped = self._score(self._q_index(
            kernel, query_sid, available, query_key, cached_keys
        ))
        identical = (
            reference["all_verdicts"] == keyed["all_verdicts"]
            == q_grouped["all_verdicts"]
        )
        if not identical:
            raise RuntimeError("Q abstraction violated exact typed retrieval")
        if before != kernel.fingerprint():
            raise RuntimeError("Read-only relational abstraction mutated native Verdant")
        return dict(
            query_p=query_sid,
            query_created_cycle=kernel.state.structures[query_sid].created_cycle,
            checkpoint_fingerprint=before,
            q_present=len(kernel.state.layered_structures),
            comparison_p_count=len(available),
            exact_typed_f1_threshold=1.0,
            canonical_roles_from_current_checkpoint=True,
            all_verdicts_identical=identical,
            q_grouping_source="existing_native_council_promoted_q_members_only",
            native_structure_or_q_mutation=False,
            construction_role_keys=len(cached_keys)+1,
            construction_ignored_in_query_cost=True,
            # P-only key checks and Q-subgroup checks are not the same
            # operation as heavyweight role-verification/permutation work.
            exhaustive=reference,
            p_keyed=keyed,
            q_overlay=q_grouped,
            measured_wall_clock_speedup=False,
            learned_semantic_equivalence=False,
            actual_prospective_accuracy_not_claimed=True,
        )
