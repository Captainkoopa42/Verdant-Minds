from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from itertools import permutations

import numpy as np

from verdant_kernel import (
    StructureFieldSignature,
    StructureInteractionCandidate,
    StructureInteractionDisposition,
    StructureInteractionEvent,
    StructureInteractionIntegrityError,
    StructureInteractionReport,
    VerdantKernel,
)
from verdant_kernel.models import canonical_json_bytes, stable_id


@dataclass(frozen=True)
class StructureInteractionResult:
    report: StructureInteractionReport
    event: StructureInteractionEvent


class VerdantStructureInteractionPipeline:
    """Cross-symbolic interaction between promoted earned structures.

    Stage 1 encodes a structure's *relational form* into a continuous complex
    signature that deliberately ignores concept IDs and labels.  This is a
    retrieval interface, not semantic truth.  Stage 2 independently unfolds
    the retrieved symbolic bodies and searches for the best one-to-one role
    alignment.  Field similarity can therefore nominate a possibility, but it
    cannot establish an analogy by itself.
    """

    @staticmethod
    def _structure(kernel: VerdantKernel, structure_id: str):
        structure = kernel.state.structures.get(structure_id)
        if structure is None:
            raise StructureInteractionIntegrityError(
                f"Unknown promoted structure {structure_id!r}."
            )
        if not kernel.structure_is_available(structure_id):
            raise StructureInteractionIntegrityError(
                f"Promoted structure {structure_id!r} is currently ablated."
            )
        return structure

    @staticmethod
    def _edge_map(structure) -> dict[tuple[str, str], float]:
        # Milestone 16 freezes edge strengths into StructureRecord at promotion.
        # The fallback supports older M14/M15 checkpoints, although new M16
        # structures should always carry snapshots.
        result: dict[tuple[str, str], float] = {}
        for edge in structure.internal_edge_snapshots:
            result[tuple(sorted(edge.concept_ids))] = float(edge.strength)
        return result

    @staticmethod
    def _normalized_adjacency(structure) -> tuple[tuple[str, ...], np.ndarray]:
        members = tuple(sorted(structure.member_concept_ids))
        index = {concept_id: i for i, concept_id in enumerate(members)}
        matrix = np.zeros((len(members), len(members)), dtype=np.float64)
        edges = VerdantStructureInteractionPipeline._edge_map(structure)
        max_strength = max(edges.values(), default=1.0)
        if max_strength <= 1e-12:
            max_strength = 1.0
        for (a, b), strength in edges.items():
            if a not in index or b not in index:
                continue
            value = max(0.0, min(1.0, strength / max_strength))
            i, j = index[a], index[b]
            matrix[i, j] = value
            matrix[j, i] = value
        return members, matrix

    @staticmethod
    def _invariant_features(kernel: VerdantKernel, structure_id: str) -> tuple[float, ...]:
        structure = VerdantStructureInteractionPipeline._structure(kernel, structure_id)
        policy = kernel.state.structure_interaction_policy
        members, adjacency = VerdantStructureInteractionPipeline._normalized_adjacency(structure)
        n = len(members)
        max_n = policy.maximum_exact_members
        if n > max_n:
            raise StructureInteractionIntegrityError(
                f"Structure has {n} members; exact interaction limit is {max_n}."
            )
        possible = max(1, n * (n - 1) // 2)
        upper = adjacency[np.triu_indices(n, 1)] if n > 1 else np.asarray([], dtype=np.float64)
        nonzero = upper[upper > 0.0]
        density = float(len(nonzero) / possible)

        degree = np.count_nonzero(adjacency > 0.0, axis=1).astype(np.float64)
        weighted_degree = np.sum(adjacency, axis=1)
        degree = np.sort(degree)[::-1] / max(1.0, float(n - 1))
        weighted_degree = np.sort(weighted_degree)[::-1] / max(1.0, float(n - 1))

        # Adjacency eigenvalues are invariant under relabeling/permutation and
        # preserve more relational shape than a bag of edge strengths.
        eigvals = np.sort(np.linalg.eigvalsh(adjacency))[::-1]
        eigvals = (eigvals / max(1.0, float(n - 1)) + 1.0) / 2.0

        max_edges = max_n * (max_n - 1) // 2
        edge_strengths = sorted((float(v) for v in nonzero), reverse=True)
        edge_strengths += [0.0] * (max_edges - len(edge_strengths))
        degree_values = degree.tolist() + [0.0] * (max_n - n)
        weighted_values = weighted_degree.tolist() + [0.0] * (max_n - n)
        eigen_values = eigvals.tolist() + [0.5] * (max_n - n)

        features = (
            float(n / max_n),
            density,
            *edge_strengths[:max_edges],
            *degree_values[:max_n],
            *weighted_values[:max_n],
            *eigen_values[:max_n],
        )
        return tuple(float(max(0.0, min(1.0, item))) for item in features)

    @staticmethod
    def _project(features: tuple[float, ...], dim: int) -> tuple[np.ndarray, tuple[float, ...], tuple[float, ...]]:
        # Deterministic Fourier-like projection.  No concept IDs, labels, run
        # seed, or human semantic categories participate in this encoding.
        f = np.asarray(features, dtype=np.float64)
        k = np.arange(1, len(f) + 1, dtype=np.float64)
        outputs = []
        denom = float(len(f) + dim + 1)
        for j in range(1, dim + 1):
            phase = 2.0 * math.pi * k * j / denom
            outputs.append(np.sum(f * (np.cos(phase) + 1j * np.sin(phase))))
        vector = np.asarray(outputs, dtype=np.complex128)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            vector = np.zeros(dim, dtype=np.complex128)
            vector[0] = 1.0 + 0.0j
        else:
            vector = vector / norm
        real = tuple(float(x) for x in vector.real.tolist())
        imag = tuple(float(x) for x in vector.imag.tolist())
        return vector, real, imag

    def signature(self, kernel: VerdantKernel, structure_id: str) -> StructureFieldSignature:
        policy = kernel.state.structure_interaction_policy
        features = self._invariant_features(kernel, structure_id)
        _vector, real, imag = self._project(features, policy.signature_dim)
        sha = hashlib.sha256(
            canonical_json_bytes(
                {"feature_values": features, "real": real, "imag": imag}
            )
        ).hexdigest()
        return StructureFieldSignature(
            structure_id=structure_id,
            feature_values=features,
            state_dim=policy.signature_dim,
            real=real,
            imag=imag,
            sha256=sha,
        )

    @staticmethod
    def _field_similarity(a: StructureFieldSignature, b: StructureFieldSignature) -> float:
        av = np.asarray(a.real, dtype=np.float64) + 1j * np.asarray(a.imag, dtype=np.float64)
        bv = np.asarray(b.real, dtype=np.float64) + 1j * np.asarray(b.imag, dtype=np.float64)
        denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
        if denom <= 1e-12:
            return 0.0
        score = float(np.real(np.vdot(av, bv)) / denom)
        return max(0.0, min(1.0, score))

    @staticmethod
    def _symbolic_alignment(kernel: VerdantKernel, source, target) -> tuple[float, tuple[tuple[str, str], ...]]:
        policy = kernel.state.structure_interaction_policy
        source_members = tuple(sorted(source.member_concept_ids))
        target_members = tuple(sorted(target.member_concept_ids))
        if len(source_members) != len(target_members) or len(source_members) > policy.maximum_exact_members:
            return 0.0, ()

        source_edges = VerdantStructureInteractionPipeline._edge_map(source)
        target_edges = VerdantStructureInteractionPipeline._edge_map(target)
        source_max = max(source_edges.values(), default=1.0)
        target_max = max(target_edges.values(), default=1.0)
        source_norm = {key: value / source_max for key, value in source_edges.items()}
        target_norm = {key: value / target_max for key, value in target_edges.items()}
        threshold = policy.edge_presence_threshold

        source_present = {key for key, value in source_norm.items() if value >= threshold}
        best_score = -1.0
        best_mapping: tuple[tuple[str, str], ...] = ()

        for perm in permutations(target_members):
            mapping_dict = dict(zip(source_members, perm))
            mapped_source: dict[tuple[str, str], float] = {}
            for (a, b), weight in source_norm.items():
                mapped = tuple(sorted((mapping_dict[a], mapping_dict[b])))
                mapped_source[mapped] = weight
            mapped_present = {key for key, value in mapped_source.items() if value >= threshold}
            target_present = {key for key, value in target_norm.items() if value >= threshold}
            if not mapped_present and not target_present:
                edge_f1 = 1.0
            else:
                overlap = len(mapped_present.intersection(target_present))
                edge_f1 = 2.0 * overlap / max(1, len(mapped_present) + len(target_present))
            union = mapped_present.union(target_present)
            if union:
                weight_similarity = sum(
                    1.0 - abs(mapped_source.get(edge, 0.0) - target_norm.get(edge, 0.0))
                    for edge in union
                ) / len(union)
            else:
                weight_similarity = 1.0
            score = 0.72 * edge_f1 + 0.28 * weight_similarity
            mapping = tuple(zip(source_members, perm))
            if score > best_score + 1e-12 or (
                abs(score - best_score) <= 1e-12 and mapping < best_mapping
            ):
                best_score = score
                best_mapping = mapping
        return max(0.0, min(1.0, best_score)), best_mapping

    def inspect(self, kernel: VerdantKernel, source_structure_id: str) -> StructureInteractionReport:
        source = self._structure(kernel, source_structure_id)
        policy = kernel.state.structure_interaction_policy
        source_signature = self.signature(kernel, source_structure_id)

        ranked: list[tuple[float, str, StructureFieldSignature]] = []
        for target in kernel.state.structures.values():
            if target.structure_id == source_structure_id:
                continue
            if not kernel.structure_is_available(target.structure_id):
                continue
            target_signature = self.signature(kernel, target.structure_id)
            similarity = self._field_similarity(source_signature, target_signature)
            ranked.append((-similarity, target.structure_id, target_signature))
        ranked.sort(key=lambda item: (item[0], item[1]))
        ranked = ranked[: policy.maximum_field_candidates]

        candidates: list[StructureInteractionCandidate] = []
        for rank, (negative_similarity, target_id, _signature) in enumerate(ranked, start=1):
            field_similarity = -negative_similarity
            target = kernel.state.structures[target_id]
            if field_similarity < policy.minimum_field_similarity:
                symbolic_similarity = 0.0
                mapping: tuple[tuple[str, str], ...] = ()
                disposition = StructureInteractionDisposition.REJECT
            else:
                symbolic_similarity, mapping = self._symbolic_alignment(kernel, source, target)
                disposition = (
                    StructureInteractionDisposition.VERIFIED_ALIGNMENT
                    if symbolic_similarity >= policy.minimum_symbolic_similarity
                    else StructureInteractionDisposition.FIELD_ONLY
                )
            candidates.append(
                StructureInteractionCandidate(
                    target_structure_id=target_id,
                    field_rank=rank,
                    field_similarity=field_similarity,
                    symbolic_similarity=symbolic_similarity,
                    member_mapping=mapping,
                    disposition=disposition,
                )
            )

        verified = [
            item for item in candidates
            if item.disposition == StructureInteractionDisposition.VERIFIED_ALIGNMENT
        ]
        verified.sort(
            key=lambda item: (-item.symbolic_similarity, -item.field_similarity, item.target_structure_id)
        )
        best = verified[0].target_structure_id if verified else None
        fingerprint = kernel.structure_interaction_structural_fingerprint()
        report_id = stable_id(
            "structure_interaction_report",
            kernel.state.identity.kernel_id,
            kernel.state.cycle,
            fingerprint,
            source_structure_id,
            source_signature.model_dump(mode="json"),
            tuple(item.model_dump(mode="json") for item in candidates),
            best,
            "cross_symbolic_structure_interaction",
            policy.revision,
        )
        report = StructureInteractionReport(
            report_id=report_id,
            kernel_id=kernel.state.identity.kernel_id,
            cycle=kernel.state.cycle,
            structural_fingerprint=fingerprint,
            source_structure_id=source_structure_id,
            source_signature=source_signature,
            candidates=tuple(candidates),
            best_target_structure_id=best,
            operation="cross_symbolic_structure_interaction",
            policy_revision=policy.revision,
        )
        kernel.validate_structure_interaction_report(report)
        return report

    def commit(self, kernel: VerdantKernel, report: StructureInteractionReport) -> StructureInteractionEvent:
        return kernel.commit_structure_interaction(report)

    def interact(self, kernel: VerdantKernel, source_structure_id: str) -> StructureInteractionResult:
        report = self.inspect(kernel, source_structure_id)
        return StructureInteractionResult(report=report, event=self.commit(kernel, report))
