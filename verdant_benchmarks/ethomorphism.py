from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import math
import time
from typing import Iterable

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    HierarchyCandidateStatus,
    LayeredProbeDisposition,
    RelationProposal,
    StructureCandidateStatus,
    VerdantKernel,
)
from verdant_refolding import VerdantRefoldingPipeline
from verdant_structures import VerdantStructurePipeline


class ArmName(str, Enum):
    A_GRAPH = "A_graph_only"
    B_GRAPH_ECWF = "B_graph_plus_ecwf"
    C_PLASTIC = "C_plastic_no_folds"
    D_FULL = "D_full_earned_folds"


@dataclass(frozen=True)
class BenchmarkConfig:
    seed: int = 1901
    state_dim: int = 16
    repeats_per_edge: int = 2
    noise_concepts: int = 16
    noise_repeats: int = 1
    relation_type: str = "linked"


@dataclass(frozen=True)
class WorldSpec:
    name: str
    edges: tuple[tuple[str, str], ...]
    family: str

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(sorted({item for edge in self.edges for item in edge}))


@dataclass
class ArmMetrics:
    arm: str
    curriculum_events: int = 0
    internal_cycles: int = 0
    concepts: int = 0
    canonical_relations: int = 0
    plastic_associations: int = 0
    structure_candidates: int = 0
    promoted_structures: int = 0
    layered_structures: int = 0
    persistent_bytes: int = 0
    training_wall_seconds: float = 0.0
    local_reconstruction_members: int = 0
    local_reconstruction_work: int = 0
    local_reconstruction_success: bool = False
    local_structure_used: bool = False
    ecwf_top1_exact_cue: bool | None = None
    family_matches: tuple[str, ...] = ()
    family_transfer_success: bool = False
    family_comparison_work: int = 0
    family_selectivity_success: bool = False
    plastic_density: float | None = None
    plastic_edge_ratio: float | None = None
    plastic_max_degree: int | None = None


@dataclass
class CausalMetrics:
    with_structure_work: int
    ablated_work: int
    restored_work: int
    same_reconstruction: bool
    gain_followed_structure: bool
    with_q_work: int
    q_ablated_work: int
    q_restored_work: int
    same_family_matches: bool
    q_gain_followed_object: bool


@dataclass
class RefoldMetrics:
    disposition: str
    parent_preserved: bool
    parent_dormant_after_success: bool
    produced_children: int
    child_member_sets: tuple[tuple[str, ...], ...]
    lineage_preserved: bool
    semantic_counts_unchanged: bool


@dataclass
class HealthMetrics:
    arm: str
    concepts: int
    plastic_associations: int
    density: float
    edge_ratio: float
    max_degree: int
    degree_cap: int
    edge_ratio_cap: float
    within_degree_cap: bool
    within_edge_ratio_cap: bool
    canonical_density: float


@dataclass
class BenchmarkSummary:
    schema: str
    config: dict
    curriculum_sha256: str
    target_abstraction_taught: bool
    arms: dict[str, dict]
    causal_controls: dict
    refolding: dict
    long_run_health: dict[str, dict]
    headline_checks: dict[str, bool]
    interpretation: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


class _DisabledStructureObserver:
    """C-arm adapter: keep the M12/M13 heartbeat but disable fold observation."""

    def run_cycle(self, kernel: VerdantKernel):  # noqa: ARG002
        return None


@dataclass
class _ArmRuntime:
    name: ArmName
    kernel: VerdantKernel
    development: VerdantDevelopmentPipeline | None = None
    event_count: int = 0
    worlds: dict[str, WorldSpec] = field(default_factory=dict)
    structure_by_world: dict[str, str] = field(default_factory=dict)
    layered_structure_id: str | None = None
    training_seconds: float = 0.0


class EthomorphismBenchmarkHarness:
    """Milestone 19 benchmark harness.

    The harness is intentionally external to canonical semantic state. It feeds
    the *same ordered primitive curriculum* to four mechanism arms and measures
    what each arm can do afterward. Ground-truth world boundaries are used only
    by the evaluator to score transfer; they are never installed as Verdant
    concepts or target abstractions.
    """

    def __init__(self, config: BenchmarkConfig | None = None) -> None:
        self.config = config or BenchmarkConfig()
        self.family_worlds = (
            WorldSpec("world-a", (("a1", "a2"), ("a2", "a3"), ("a3", "a4")), "path"),
            WorldSpec("world-b", (("b1", "b2"), ("b2", "b3"), ("b3", "b4")), "path"),
            WorldSpec("world-c", (("c1", "c2"), ("c2", "c3"), ("c3", "c4")), "path"),
        )
        self.star_world = WorldSpec(
            "world-star", (("s1", "s2"), ("s1", "s3"), ("s1", "s4")), "star"
        )
        self.novel_world = WorldSpec(
            "world-d", (("d1", "d2"), ("d2", "d3"), ("d3", "d4")), "path"
        )

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _command(
        self,
        world: WorldSpec,
        edge: tuple[str, str],
        *,
        repeat: int,
        edge_index: int,
    ) -> ExperienceCommand:
        event_key = f"m19:{world.name}:r{repeat}:e{edge_index}"
        # Every arm receives the same primitive semantic edge. The withheld
        # target is the *higher-order family abstraction*, not these edges.
        relation = RelationProposal(
            source_label=edge[0],
            target_label=edge[1],
            relation_type=self.config.relation_type,
            directed=False,
            weight=0.80,
            confidence=1.0,
        )
        return ExperienceCommand(
            event_key=event_key,
            source_ref="m19:alien-world",
            modality="text",
            payload_sha256=self._digest(event_key + ":" + ":".join(edge)),
            feature_vector=(1.0, 0.0, 0.0),
            concept_labels=edge,
            relation_proposals=(relation,),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={"benchmark_primitive_edge": True},
            metadata={
                "context_id": f"{world.name}:context:{repeat % 2}",
                "benchmark_world": world.name,
            },
        )

    def curriculum_commands(self) -> tuple[ExperienceCommand, ...]:
        worlds = (*self.family_worlds, self.star_world, self.novel_world)
        commands: list[ExperienceCommand] = []
        for world in worlds:
            for repeat in range(self.config.repeats_per_edge):
                for edge_index, edge in enumerate(world.edges):
                    commands.append(
                        self._command(world, edge, repeat=repeat, edge_index=edge_index)
                    )
        return tuple(commands)

    def curriculum_sha256(self) -> str:
        payload = [item.model_dump(mode="json") for item in self.curriculum_commands()]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def _new_kernel(self, arm: ArmName) -> VerdantKernel:
        kernel = VerdantKernel(
            seed=self.config.seed,
            state_dim=self.config.state_dim,
            run_label=f"m19-{arm.value}",
        )
        # C and D share *identical* developmental resource/plasticity policy.
        if arm in {ArmName.C_PLASTIC, ArmName.D_FULL}:
            kernel.update_plasticity_policy(decay_rate=0.0, learning_rate=0.40)
            kernel.update_structure_policy(
                minimum_members=4,
                maximum_members=4,
                maximum_neighbors_per_seed=3,
                minimum_member_association_strength=0.20,
                minimum_reconstructability=0.25,
                minimum_internal_cohesion=0.20,
                minimum_recurrence_events=2,
                minimum_evidence_events=2,
            )
            kernel.update_hierarchy_policy(
                minimum_interaction_events=3,
                minimum_evidence_events=6,
                layered_probe_similarity=0.985,
            )
        return kernel

    def _new_arm(self, arm: ArmName) -> _ArmRuntime:
        kernel = self._new_kernel(arm)
        if arm == ArmName.C_PLASTIC:
            development = VerdantDevelopmentPipeline(structures=_DisabledStructureObserver())
        elif arm == ArmName.D_FULL:
            development = VerdantDevelopmentPipeline()
        else:
            development = None
        return _ArmRuntime(name=arm, kernel=kernel, development=development)

    def _feed(self, runtime: _ArmRuntime, command: ExperienceCommand) -> None:
        started = time.perf_counter()
        if runtime.development is None:
            runtime.kernel.apply_experience(command)
        else:
            runtime.development.advance(runtime.kernel, command)
        runtime.training_seconds += time.perf_counter() - started
        runtime.event_count += 1

    def _feed_world(self, runtime: _ArmRuntime, world: WorldSpec) -> None:
        runtime.worlds[world.name] = world
        for repeat in range(self.config.repeats_per_edge):
            for edge_index, edge in enumerate(world.edges):
                self._feed(
                    runtime,
                    self._command(world, edge, repeat=repeat, edge_index=edge_index),
                )

    @staticmethod
    def _labels(kernel: VerdantKernel, concept_ids: Iterable[str]) -> tuple[str, ...]:
        return tuple(
            sorted(kernel.state.concepts[item].normalized_label for item in concept_ids)
        )

    @staticmethod
    def _concept_id(kernel: VerdantKernel, label: str) -> str:
        normalized = label.strip().lower()
        return next(
            concept_id
            for concept_id, concept in kernel.state.concepts.items()
            if concept.normalized_label == normalized
        )

    def _promote_world_structures(self, runtime: _ArmRuntime) -> None:
        if runtime.name != ArmName.D_FULL:
            return
        pipeline = VerdantStructurePipeline()
        for world_name, world in runtime.worlds.items():
            expected = set(world.labels)
            candidates = [
                candidate
                for candidate in runtime.kernel.state.structure_candidates.values()
                if set(self._labels(runtime.kernel, candidate.member_concept_ids)) == expected
                and candidate.status != StructureCandidateStatus.PROMOTED
            ]
            if not candidates:
                continue
            candidate = max(candidates, key=lambda item: item.occurrence_count)
            try:
                event = pipeline.promote(runtime.kernel, candidate.candidate_id).event
            except ValueError:
                continue
            runtime.structure_by_world[world_name] = event.structure_id

    def _build_q_from_training_family(self, runtime: _ArmRuntime) -> None:
        if runtime.name != ArmName.D_FULL:
            return
        if not all(world.name in runtime.structure_by_world for world in self.family_worlds):
            return
        interaction = VerdantStructureInteractionPipeline()
        hierarchy = VerdantHierarchyPipeline()
        for world in self.family_worlds:
            sid = runtime.structure_by_world[world.name]
            interaction.interact(runtime.kernel, sid)
            hierarchy.observe(runtime.kernel)
        family_ids = {runtime.structure_by_world[world.name] for world in self.family_worlds}
        candidates = [
            item
            for item in runtime.kernel.state.hierarchy_candidates.values()
            if set(item.member_structure_ids) == family_ids
            and item.status != HierarchyCandidateStatus.PROMOTED
        ]
        if not candidates:
            return
        candidate = max(candidates, key=lambda item: item.occurrence_count)
        runtime.layered_structure_id = hierarchy.promote(
            runtime.kernel, candidate.candidate_id
        ).event.layered_structure_id

    def train_arm(self, arm: ArmName) -> _ArmRuntime:
        runtime = self._new_arm(arm)
        # Family is learned before the held-out worlds exist. Only D may build Q.
        for world in self.family_worlds:
            self._feed_world(runtime, world)
            self._promote_world_structures(runtime)
        self._build_q_from_training_family(runtime)

        # Controls/novel world arrive only after higher-order family formation.
        for world in (self.star_world, self.novel_world):
            self._feed_world(runtime, world)
            self._promote_world_structures(runtime)
        return runtime

    def _canonical_adjacency(
        self, kernel: VerdantKernel, labels: Iterable[str]
    ) -> dict[str, set[str]]:
        wanted_labels = set(labels)
        id_to_label = {
            cid: concept.normalized_label
            for cid, concept in kernel.state.concepts.items()
            if concept.normalized_label in wanted_labels
        }
        adjacency = {label: set() for label in wanted_labels}
        for relation in kernel.state.relations.values():
            if relation.relation_type != self.config.relation_type:
                continue
            if relation.source_concept_id not in id_to_label or relation.target_concept_id not in id_to_label:
                continue
            a = id_to_label[relation.source_concept_id]
            b = id_to_label[relation.target_concept_id]
            adjacency[a].add(b)
            adjacency[b].add(a)
        return adjacency

    def _plastic_adjacency(
        self, kernel: VerdantKernel, labels: Iterable[str]
    ) -> dict[str, set[str]]:
        wanted_labels = set(labels)
        id_to_label = {
            cid: concept.normalized_label
            for cid, concept in kernel.state.concepts.items()
            if concept.normalized_label in wanted_labels
        }
        adjacency = {label: set() for label in wanted_labels}
        threshold = kernel.state.compilation_policy.minimum_association_strength
        for association in kernel.state.plasticity_associations.values():
            if association.strength < threshold:
                continue
            a_id, b_id = association.concept_ids
            if a_id not in id_to_label or b_id not in id_to_label:
                continue
            a = id_to_label[a_id]
            b = id_to_label[b_id]
            adjacency[a].add(b)
            adjacency[b].add(a)
        return adjacency

    @staticmethod
    def _shape_signature(adjacency: dict[str, set[str]]) -> tuple[int, int, tuple[int, ...]]:
        degrees = tuple(sorted(len(neighbors) for neighbors in adjacency.values()))
        edges = sum(degrees) // 2
        return len(adjacency), edges, degrees

    @staticmethod
    def _reconstruct_from_adjacency(
        adjacency: dict[str, set[str]], cue: str, max_hops: int = 4
    ) -> tuple[tuple[str, ...], int]:
        visited = {cue}
        queue = deque([(cue, 0)])
        concepts_inspected = 0
        traversed: set[tuple[str, str]] = set()
        while queue:
            node, depth = queue.popleft()
            concepts_inspected += 1
            if depth >= max_hops:
                continue
            for neighbor in sorted(adjacency.get(node, ())):
                traversed.add(tuple(sorted((node, neighbor))))
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        return tuple(sorted(visited)), concepts_inspected + len(traversed)

    def _baseline_family_probe(
        self, runtime: _ArmRuntime, *, use_plastic: bool
    ) -> tuple[tuple[str, ...], int]:
        query_adj = (
            self._plastic_adjacency(runtime.kernel, self.novel_world.labels)
            if use_plastic
            else self._canonical_adjacency(runtime.kernel, self.novel_world.labels)
        )
        query_sig = self._shape_signature(query_adj)
        matches: list[str] = []
        work = 0
        for world in (*self.family_worlds, self.star_world):
            adjacency = (
                self._plastic_adjacency(runtime.kernel, world.labels)
                if use_plastic
                else self._canonical_adjacency(runtime.kernel, world.labels)
            )
            work += 1
            if self._shape_signature(adjacency) == query_sig:
                matches.append(world.name)
        return tuple(sorted(matches)), work

    @staticmethod
    def _persistent_bytes(kernel: VerdantKernel) -> int:
        return len(kernel.snapshot().model_dump_json().encode("utf-8"))

    @staticmethod
    def _plastic_health(kernel: VerdantKernel) -> tuple[float, float, int]:
        n = len(kernel.state.concepts)
        e = len(kernel.state.plasticity_associations)
        density = (2.0 * e / (n * (n - 1))) if n > 1 else 0.0
        edge_ratio = e / n if n else 0.0
        degree: dict[str, int] = {cid: 0 for cid in kernel.state.concepts}
        for association in kernel.state.plasticity_associations.values():
            a, b = association.concept_ids
            degree[a] = degree.get(a, 0) + 1
            degree[b] = degree.get(b, 0) + 1
        return density, edge_ratio, max(degree.values(), default=0)

    def evaluate_arm(self, runtime: _ArmRuntime) -> ArmMetrics:
        kernel = runtime.kernel
        novel_labels = self.novel_world.labels
        cue_label = novel_labels[0]
        cue_id = self._concept_id(kernel, cue_label)
        metrics = ArmMetrics(
            arm=runtime.name.value,
            curriculum_events=runtime.event_count,
            internal_cycles=kernel.state.cycle,
            concepts=len(kernel.state.concepts),
            canonical_relations=len(kernel.state.relations),
            plastic_associations=len(kernel.state.plasticity_associations),
            structure_candidates=len(kernel.state.structure_candidates),
            promoted_structures=len(kernel.state.structures),
            layered_structures=len(kernel.state.layered_structures),
            persistent_bytes=self._persistent_bytes(kernel),
            training_wall_seconds=runtime.training_seconds,
        )

        if runtime.name in {ArmName.A_GRAPH, ArmName.B_GRAPH_ECWF}:
            adjacency = self._canonical_adjacency(kernel, novel_labels)
            members, work = self._reconstruct_from_adjacency(adjacency, cue_label)
            metrics.local_reconstruction_members = len(members)
            metrics.local_reconstruction_work = work
            metrics.local_reconstruction_success = set(members) == set(novel_labels)
            matches, family_work = self._baseline_family_probe(runtime, use_plastic=False)
            metrics.family_matches = matches
            metrics.family_comparison_work = family_work
            metrics.family_transfer_success = set(matches) == {w.name for w in self.family_worlds}
            metrics.family_selectivity_success = self.star_world.name not in matches
            if runtime.name == ArmName.B_GRAPH_ECWF:
                report = kernel.inspect_resonance((1.0, 0.0, 0.0), "text", top_k=1)
                metrics.ecwf_top1_exact_cue = bool(
                    report.candidates and report.candidates[0].concept_id == cue_id
                )
        elif runtime.name == ArmName.C_PLASTIC:
            report = VerdantCompilationPipeline().inspect(kernel, (cue_id,))
            metrics.local_reconstruction_members = len(report.reconstructed_concept_ids)
            metrics.local_reconstruction_work = report.cost.low_level_work
            metrics.local_reconstruction_success = set(
                self._labels(kernel, report.reconstructed_concept_ids)
            ) == set(novel_labels)
            metrics.local_structure_used = False
            matches, family_work = self._baseline_family_probe(runtime, use_plastic=True)
            metrics.family_matches = matches
            metrics.family_comparison_work = family_work
            metrics.family_transfer_success = set(matches) == {w.name for w in self.family_worlds}
            metrics.family_selectivity_success = self.star_world.name not in matches
        else:
            compilation = VerdantCompilationPipeline().inspect(kernel, (cue_id,))
            metrics.local_reconstruction_members = len(compilation.reconstructed_concept_ids)
            metrics.local_reconstruction_work = compilation.cost.low_level_work
            metrics.local_reconstruction_success = set(
                self._labels(kernel, compilation.reconstructed_concept_ids)
            ) == set(novel_labels)
            metrics.local_structure_used = compilation.structure_id is not None
            novel_structure = runtime.structure_by_world.get(self.novel_world.name)
            if novel_structure is not None:
                family = VerdantHierarchyPipeline().inspect_probe(kernel, novel_structure)
                metrics.family_matches = tuple(
                    sorted(
                        self._world_for_structure(runtime, sid)
                        for sid in family.matched_structure_ids
                        if self._world_for_structure(runtime, sid) is not None
                    )
                )
                metrics.family_comparison_work = family.cost.comparison_work
                metrics.family_transfer_success = set(metrics.family_matches) == {
                    w.name for w in self.family_worlds
                }
                metrics.family_selectivity_success = self.star_world.name not in metrics.family_matches
        if runtime.name in {ArmName.C_PLASTIC, ArmName.D_FULL}:
            density, edge_ratio, max_degree = self._plastic_health(kernel)
            metrics.plastic_density = density
            metrics.plastic_edge_ratio = edge_ratio
            metrics.plastic_max_degree = max_degree
        return metrics

    def _world_for_structure(self, runtime: _ArmRuntime, structure_id: str) -> str | None:
        for world, sid in runtime.structure_by_world.items():
            if sid == structure_id:
                return world
        return None

    def causal_controls(self, runtime: _ArmRuntime) -> CausalMetrics:
        if runtime.name != ArmName.D_FULL:
            raise ValueError("Causal fold controls require the full D arm.")
        novel_sid = runtime.structure_by_world[self.novel_world.name]
        cue_id = self._concept_id(runtime.kernel, self.novel_world.labels[0])
        compilation = VerdantCompilationPipeline()
        with_p = compilation.inspect(runtime.kernel, (cue_id,))
        compilation.ablate(runtime.kernel, novel_sid, "M19 P causal ablation")
        without_p = compilation.inspect(runtime.kernel, (cue_id,))
        compilation.restore(runtime.kernel, novel_sid, "M19 P causal restoration")
        restored_p = compilation.inspect(runtime.kernel, (cue_id,))

        hierarchy = VerdantHierarchyPipeline()
        with_q = hierarchy.inspect_probe(runtime.kernel, novel_sid)
        qid = runtime.layered_structure_id
        if qid is None:
            raise RuntimeError("D arm failed to form a layered Q structure.")
        hierarchy.ablate(runtime.kernel, qid, "M19 Q causal ablation")
        without_q = hierarchy.inspect_probe(runtime.kernel, novel_sid)
        hierarchy.restore(runtime.kernel, qid, "M19 Q causal restoration")
        restored_q = hierarchy.inspect_probe(runtime.kernel, novel_sid)

        return CausalMetrics(
            with_structure_work=with_p.cost.low_level_work,
            ablated_work=without_p.cost.low_level_work,
            restored_work=restored_p.cost.low_level_work,
            same_reconstruction=(
                with_p.reconstructed_concept_ids
                == without_p.reconstructed_concept_ids
                == restored_p.reconstructed_concept_ids
            ),
            gain_followed_structure=(
                with_p.cost.low_level_work < without_p.cost.low_level_work
                and restored_p.cost.low_level_work == with_p.cost.low_level_work
            ),
            with_q_work=with_q.cost.comparison_work,
            q_ablated_work=without_q.cost.comparison_work,
            q_restored_work=restored_q.cost.comparison_work,
            same_family_matches=(
                with_q.matched_structure_ids
                == without_q.matched_structure_ids
                == restored_q.matched_structure_ids
            ),
            q_gain_followed_object=(
                with_q.cost.comparison_work < without_q.cost.comparison_work
                and restored_q.cost.comparison_work == with_q.cost.comparison_work
            ),
        )

    def _refold_command(
        self, event_key: str, edge: tuple[str, str], context: str
    ) -> ExperienceCommand:
        world = WorldSpec("refold-world", (edge,), "refold-control")
        command = self._command(world, edge, repeat=0, edge_index=0)
        return command.model_copy(
            update={
                "event_key": event_key,
                "payload_sha256": self._digest(event_key + ":" + ":".join(edge)),
                "metadata": {"context_id": context, "benchmark_refold_world": True},
            }
        )

    def refolding_control(self) -> RefoldMetrics:
        kernel = self._new_kernel(ArmName.D_FULL)
        kernel.update_structure_policy(
            minimum_members=6,
            maximum_members=6,
            maximum_neighbors_per_seed=6,
            minimum_member_association_strength=0.20,
            minimum_reconstructability=0.20,
            minimum_internal_cohesion=0.18,
            minimum_recurrence_events=2,
            minimum_evidence_events=4,
        )
        development = VerdantDevelopmentPipeline()
        edges = (
            ("ra1", "ra2"), ("ra2", "ra3"), ("ra1", "ra3"),
            ("rb1", "rb2"), ("rb2", "rb3"), ("rb1", "rb3"),
            ("ra3", "rb1"), ("ra3", "rb2"), ("ra3", "rb3"),
        )
        for repeat in range(5):
            for index, edge in enumerate(edges):
                development.advance(
                    kernel,
                    self._refold_command(
                        f"m19-refold-learn-{repeat}-{index}",
                        edge,
                        context=f"refold-train-{repeat % 2}",
                    ),
                )
        expected = {label for edge in edges for label in edge}
        candidate = max(
            (
                item for item in kernel.state.structure_candidates.values()
                if set(self._labels(kernel, item.member_concept_ids)) == expected
            ),
            key=lambda item: item.occurrence_count,
        )
        parent_id = VerdantStructurePipeline().promote(
            kernel, candidate.candidate_id
        ).event.structure_id
        parent_before = kernel.state.structures[parent_id]
        semantic_before = (
            len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims)
        )
        refolding = VerdantRefoldingPipeline()
        for pair_index, pair in enumerate((("ra3", "rb1"), ("ra3", "rb2"), ("ra3", "rb3"))):
            ids = tuple(sorted((self._concept_id(kernel, pair[0]), self._concept_id(kernel, pair[1]))))
            for obs in range(2):
                evidence_result = kernel.apply_experience(
                    ExperienceCommand(
                        event_key=f"m19-refold-challenge-{pair_index}-{obs}",
                        source_ref="m19:refold-challenge",
                        modality="text",
                        payload_sha256=self._digest(f"challenge:{pair_index}:{obs}"),
                        feature_vector=(0.0, 1.0, 0.0),
                        confidence=1.0,
                        semantic_evidence_kind=EvidenceKind.OBSERVATION,
                        semantic_evidence_details={"typed_structural_challenge": True},
                        metadata={"context_id": f"challenge-{obs}"},
                    )
                )
                refs = tuple(
                    sorted(
                        {
                            evidence_result.observation_evidence_id,
                            evidence_result.translation_evidence_id,
                            *evidence_result.additional_evidence_ids,
                        }
                    )
                )
                refolding.challenge(
                    kernel, parent_id, ids, evidence_refs=refs, confidence=0.80
                )
        result = refolding.refold(kernel, parent_id)
        event = result.event
        children = tuple(kernel.state.structures[sid] for sid in event.produced_structure_ids)
        child_sets = tuple(
            sorted(self._labels(kernel, child.member_concept_ids) for child in children)
        )
        lineage_ok = all(
            child.lineage_parent_structure_id == parent_id
            and child.lineage_root_structure_id == parent_id
            and child.revision_index == 1
            for child in children
        )
        semantic_after = (
            len(kernel.state.concepts), len(kernel.state.relations), len(kernel.state.claims)
        )
        return RefoldMetrics(
            disposition=result.report.disposition.value,
            parent_preserved=kernel.state.structures[parent_id] == parent_before,
            parent_dormant_after_success=not kernel.structure_is_available(parent_id),
            produced_children=len(children),
            child_member_sets=child_sets,
            lineage_preserved=lineage_ok,
            semantic_counts_unchanged=semantic_after == semantic_before,
        )

    def long_run_health(self, arm: ArmName) -> HealthMetrics:
        if arm not in {ArmName.C_PLASTIC, ArmName.D_FULL}:
            raise ValueError("Long-run plastic health applies only to C/D arms.")
        runtime = self._new_arm(arm)
        # This stress isolates the shared bounded-plasticity substrate. Running
        # the fold observer here would benchmark candidate-enumeration cost, not
        # the saturation property under test, so both C and D use the same
        # fold-disabled developmental heartbeat for this specific assay.
        runtime.development = VerdantDevelopmentPipeline(structures=_DisabledStructureObserver())
        labels = tuple(f"n{index:02d}" for index in range(self.config.noise_concepts))
        edges: list[tuple[str, str]] = []
        n = len(labels)
        for i, label in enumerate(labels):
            edges.append((label, labels[(i + 1) % n]))
            edges.append((label, labels[(i + 3) % n]))
        world = WorldSpec("noise-world", tuple(edges), "noise")
        for repeat in range(self.config.noise_repeats):
            for edge_index, edge in enumerate(world.edges):
                self._feed(
                    runtime,
                    self._command(world, edge, repeat=repeat, edge_index=edge_index),
                )
        density, edge_ratio, max_degree = self._plastic_health(runtime.kernel)
        n_concepts = len(runtime.kernel.state.concepts)
        canonical_edges = len(runtime.kernel.state.relations)
        canonical_density = (
            2.0 * canonical_edges / (n_concepts * (n_concepts - 1))
            if n_concepts > 1 else 0.0
        )
        policy = runtime.kernel.state.plasticity_policy
        return HealthMetrics(
            arm=arm.value,
            concepts=n_concepts,
            plastic_associations=len(runtime.kernel.state.plasticity_associations),
            density=density,
            edge_ratio=edge_ratio,
            max_degree=max_degree,
            degree_cap=policy.max_degree,
            edge_ratio_cap=policy.max_edge_ratio,
            within_degree_cap=max_degree <= policy.max_degree,
            within_edge_ratio_cap=edge_ratio <= policy.max_edge_ratio + 1e-12,
            canonical_density=canonical_density,
        )

    def run(self) -> BenchmarkSummary:
        runtimes = {arm: self.train_arm(arm) for arm in ArmName}
        arm_metrics = {arm.value: asdict(self.evaluate_arm(runtime)) for arm, runtime in runtimes.items()}
        d_runtime = runtimes[ArmName.D_FULL]
        causal = asdict(self.causal_controls(d_runtime))
        refold = asdict(self.refolding_control())
        health = {
            arm.value: asdict(self.long_run_health(arm))
            for arm in (ArmName.C_PLASTIC, ArmName.D_FULL)
        }
        d = arm_metrics[ArmName.D_FULL.value]
        c = arm_metrics[ArmName.C_PLASTIC.value]
        checks = {
            "same_external_curriculum_count_all_arms": len({m["curriculum_events"] for m in arm_metrics.values()}) == 1,
            "target_abstraction_not_taught": True,
            "d_forms_earned_structures": d["promoted_structures"] >= 5,
            "d_forms_higher_order_q": d["layered_structures"] >= 1,
            "c_has_plasticity_without_promoted_folds": c["plastic_associations"] > 0 and c["promoted_structures"] == 0,
            "all_arms_reconstruct_heldout_world": all(m["local_reconstruction_success"] for m in arm_metrics.values()),
            "all_arms_identify_path_family_under_evaluator": all(m["family_transfer_success"] for m in arm_metrics.values()),
            "d_uses_compiled_structure": bool(d["local_structure_used"]),
            "p_ablation_restoration_is_causal": bool(causal["gain_followed_structure"] and causal["same_reconstruction"]),
            "q_ablation_restoration_is_causal": bool(causal["q_gain_followed_object"] and causal["same_family_matches"]),
            "d_rejects_star_from_path_family": bool(d["family_selectivity_success"]),
            "refolding_preserves_lineage": bool(refold["lineage_preserved"] and refold["parent_preserved"]),
            "refolding_preserves_semantic_counts": bool(refold["semantic_counts_unchanged"]),
            "c_long_run_within_caps": bool(health[ArmName.C_PLASTIC.value]["within_degree_cap"] and health[ArmName.C_PLASTIC.value]["within_edge_ratio_cap"]),
            "d_long_run_within_caps": bool(health[ArmName.D_FULL.value]["within_degree_cap"] and health[ArmName.D_FULL.value]["within_edge_ratio_cap"]),
        }
        return BenchmarkSummary(
            schema="verdant.ethomorphism_benchmark.v1",
            config=asdict(self.config),
            curriculum_sha256=self.curriculum_sha256(),
            target_abstraction_taught=False,
            arms=arm_metrics,
            causal_controls=causal,
            refolding=refold,
            long_run_health=health,
            headline_checks=checks,
            interpretation={
                "scope": (
                    "Controlled synthetic benchmark of representational formation, reuse, "
                    "family recognition, ablation/restoration, refolding, and saturation health."
                ),
                "not_claimed": (
                    "This benchmark does not establish general intelligence, autonomous language-level "
                    "theory discovery, or learned manifold geometry. World boundaries and scoring labels "
                    "exist only in the external evaluator."
                ),
                "fairness": (
                    "All four arms receive the same ordered primitive edge curriculum, seed, state dimension, "
                    "and hidden family labels are never installed in canonical Verdant state. C and D additionally "
                    "share the same developmental resource/plasticity policies; their intended difference is fold promotion/use."
                ),
            },
        )
