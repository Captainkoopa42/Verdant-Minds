"""Answer-agnostic hypothesis composition for DependencyGap obligations.

The generator consumes canonical topology and emits immutable simulation inputs.
It does not parse labels, decide truth, mutate canonical state, or resolve an
obligation.  Functional equivalence intentionally ignores continuous weights
and operator identity: outcomes are equivalent only when they expose the same
discrete canonical references, proposed topology, and bounded next action.
"""
from __future__ import annotations

from collections import deque
from enum import Enum
from typing import Any, Iterable, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, RelationStatus, VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .counterfactual import (
    CounterfactualPatch,
    CounterfactualPlan,
    SimulationDisposition,
)
from .pipeline import ObligationIntegrityError


HYPOTHESIS_GRAMMAR_VERSION = "dependency_gap_hypothesis_grammar_v0.5"
FUNCTIONAL_PARTITION_VERSION = "functional_outcome_partition_v0.5"


class HypothesisOperator(str, Enum):
    EVIDENCE_PATH_PROJECTION = "evidence_path_projection"
    NULL_ARTIFACT = "null_artifact"
    DEFER_INSUFFICIENT_EVIDENCE = "defer_insufficient_evidence"


class FunctionalAction(str, Enum):
    RETRIEVE_CANONICAL_EVIDENCE = "retrieve_canonical_evidence"
    REJECT_CANDIDATE = "reject_candidate"
    DEFER_FOR_EVIDENCE = "defer_for_evidence"


class OutcomeKind(str, Enum):
    PATH_COMPLETES = "path_completes"
    PATH_STALLS = "path_stalls"
    PATH_CONFLICTS = "path_conflicts"
    ARTIFACT_REJECTED = "artifact_rejected"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"


class HypothesisGenerationPolicy(BaseModel):
    """Visible resource and topology grammar for the experimental generator."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = HYPOTHESIS_GRAMMAR_VERSION
    maximum_path_depth: int = Field(default=4, ge=1, le=16)
    maximum_projected_paths: int = Field(default=8, ge=1, le=64)
    traversable_relation_statuses: tuple[RelationStatus, ...] = (
        RelationStatus.CONFIRMED,
        RelationStatus.SUPPORTED,
    )
    qualifying_evidence_kinds: tuple[EvidenceKind, ...] = (
        EvidenceKind.ACTION,
        EvidenceKind.OUTCOME,
    )
    directed_traversal_only: bool = True

    @model_validator(mode="after")
    def validate_policy(self) -> "HypothesisGenerationPolicy":
        if not self.policy_version.strip():
            raise ValueError("Hypothesis policy version cannot be empty.")
        statuses = tuple(sorted(set(self.traversable_relation_statuses), key=lambda x: x.value))
        if not statuses or statuses != self.traversable_relation_statuses:
            raise ValueError("Traversable relation statuses must be sorted and unique.")
        kinds = tuple(sorted(set(self.qualifying_evidence_kinds), key=lambda x: x.value))
        if not kinds or kinds != self.qualifying_evidence_kinds:
            raise ValueError("Qualifying evidence kinds must be sorted and unique.")
        return self


class ProjectedTopologyEdge(FrozenRecord):
    source_ref: str
    target_ref: str
    relation_type: str

    @model_validator(mode="after")
    def validate_edge(self) -> "ProjectedTopologyEdge":
        if not all(
            item.strip() for item in (self.source_ref, self.target_ref, self.relation_type)
        ):
            raise ValueError("Projected topology edges require non-empty fields.")
        return self


class FunctionalConsequence(FrozenRecord):
    """Discrete consequence lens used before learned Equivalence Lenses exist."""

    action: FunctionalAction
    activated_canonical_refs: tuple[str, ...] = ()
    added_edges: tuple[ProjectedTopologyEdge, ...] = ()
    suppressed_canonical_refs: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_consequence(self) -> "FunctionalConsequence":
        for values, label in (
            (self.activated_canonical_refs, "activated refs"),
            (self.suppressed_canonical_refs, "suppressed refs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Functional consequence {label} must be sorted and unique.")
        edge_keys = tuple(
            (edge.source_ref, edge.target_ref, edge.relation_type)
            for edge in self.added_edges
        )
        if tuple(sorted(set(edge_keys))) != edge_keys:
            raise ValueError("Functional consequence edges must be sorted and unique.")
        if self.suppressed_canonical_refs:
            raise ValueError("Prospective outcomes cannot suppress canonical references.")
        return self

    def equivalence_signature(self) -> str:
        return stable_id(
            "functional_equivalence",
            FUNCTIONAL_PARTITION_VERSION,
            self.model_dump(mode="json"),
        )


class FunctionalOutcome(FrozenRecord):
    outcome_id: str
    hypothesis_id: str
    kind: OutcomeKind
    consequence: FunctionalConsequence
    equivalence_signature: str

    @classmethod
    def build(
        cls,
        *,
        hypothesis_id: str,
        kind: OutcomeKind,
        consequence: FunctionalConsequence,
    ) -> "FunctionalOutcome":
        signature = consequence.equivalence_signature()
        return cls(
            outcome_id=stable_id(
                "functional_outcome", hypothesis_id, kind.value, signature
            ),
            hypothesis_id=hypothesis_id,
            kind=kind,
            consequence=consequence,
            equivalence_signature=signature,
        )

    @model_validator(mode="after")
    def validate_outcome(self) -> "FunctionalOutcome":
        expected_signature = self.consequence.equivalence_signature()
        if self.equivalence_signature != expected_signature:
            raise ValueError("Functional outcome equivalence checksum mismatch.")
        expected_id = stable_id(
            "functional_outcome",
            self.hypothesis_id,
            self.kind.value,
            expected_signature,
        )
        if self.outcome_id != expected_id:
            raise ValueError("Functional outcome identity checksum mismatch.")
        return self


class StructuralHypothesis(FrozenRecord):
    hypothesis_id: str
    obligation_id: str
    operator: HypothesisOperator
    operand_refs: tuple[str, ...]
    derivation_path_relation_ids: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    patches: tuple[CounterfactualPatch, ...] = ()
    outcomes: tuple[FunctionalOutcome, ...] = Field(min_length=1)
    grammar_version: str = HYPOTHESIS_GRAMMAR_VERSION

    @model_validator(mode="after")
    def validate_hypothesis(self) -> "StructuralHypothesis":
        for values, label in (
            (self.operand_refs, "operand refs"),
            (self.provenance_refs, "provenance refs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Hypothesis {label} must be sorted and unique.")
        if len(set(self.derivation_path_relation_ids)) != len(
            self.derivation_path_relation_ids
        ):
            raise ValueError("Hypothesis derivation path cannot repeat an edge.")
        if not self.grammar_version.strip():
            raise ValueError("Hypothesis grammar version cannot be empty.")
        if any(item.hypothesis_id != self.hypothesis_id for item in self.outcomes):
            raise ValueError("Hypothesis outcome lineage mismatch.")
        expected = _hypothesis_id(
            obligation_id=self.obligation_id,
            operator=self.operator,
            operand_refs=self.operand_refs,
            derivation_path_relation_ids=self.derivation_path_relation_ids,
            provenance_refs=self.provenance_refs,
            patches=self.patches,
            grammar_version=self.grammar_version,
        )
        if self.hypothesis_id != expected:
            raise ValueError("Structural hypothesis identity checksum mismatch.")
        return self


class FunctionalOutcomeClass(FrozenRecord):
    equivalence_signature: str
    member_outcome_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_class(self) -> "FunctionalOutcomeClass":
        if tuple(sorted(set(self.member_outcome_ids))) != self.member_outcome_ids:
            raise ValueError("Outcome class members must be sorted and unique.")
        return self


class FunctionalPartitionIndex(FrozenRecord):
    partition_id: str
    obligation_id: str
    equivalence_classes: tuple[FunctionalOutcomeClass, ...]
    rejected_duplicate_outcome_ids: tuple[str, ...] = ()
    partition_version: str = FUNCTIONAL_PARTITION_VERSION

    @classmethod
    def build(
        cls,
        obligation_id: str,
        hypotheses: Sequence[StructuralHypothesis],
    ) -> "FunctionalPartitionIndex":
        grouped: dict[str, list[str]] = {}
        for hypothesis in hypotheses:
            if hypothesis.obligation_id != obligation_id:
                raise ValueError("Outcome partition crossed an obligation boundary.")
            for outcome in hypothesis.outcomes:
                grouped.setdefault(outcome.equivalence_signature, []).append(
                    outcome.outcome_id
                )
        classes = tuple(
            FunctionalOutcomeClass(
                equivalence_signature=signature,
                member_outcome_ids=tuple(sorted(set(members))),
            )
            for signature, members in sorted(grouped.items())
        )
        duplicates = tuple(
            sorted(
                member
                for item in classes
                for member in item.member_outcome_ids[1:]
            )
        )
        payload = {
            "obligation_id": obligation_id,
            "equivalence_classes": [item.model_dump(mode="json") for item in classes],
            "rejected_duplicate_outcome_ids": duplicates,
            "partition_version": FUNCTIONAL_PARTITION_VERSION,
        }
        return cls(
            partition_id=stable_id("functional_partition", payload),
            obligation_id=obligation_id,
            equivalence_classes=classes,
            rejected_duplicate_outcome_ids=duplicates,
        )

    @model_validator(mode="after")
    def validate_partition(self) -> "FunctionalPartitionIndex":
        signatures = tuple(item.equivalence_signature for item in self.equivalence_classes)
        if tuple(sorted(set(signatures))) != signatures:
            raise ValueError("Functional outcome classes must be sorted and unique.")
        if tuple(sorted(set(self.rejected_duplicate_outcome_ids))) != (
            self.rejected_duplicate_outcome_ids
        ):
            raise ValueError("Rejected duplicate outcomes must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"partition_id"})
        if self.partition_id != stable_id("functional_partition", payload):
            raise ValueError("Functional partition identity checksum mismatch.")
        return self


def _hypothesis_id(
    *,
    obligation_id: str,
    operator: HypothesisOperator,
    operand_refs: tuple[str, ...],
    derivation_path_relation_ids: tuple[str, ...],
    provenance_refs: tuple[str, ...],
    patches: tuple[CounterfactualPatch, ...],
    grammar_version: str,
) -> str:
    return stable_id(
        "structural_hypothesis",
        {
            "obligation_id": obligation_id,
            "operator": operator.value,
            "operand_refs": operand_refs,
            "derivation_path_relation_ids": derivation_path_relation_ids,
            "provenance_refs": provenance_refs,
            "patches": [item.model_dump(mode="json") for item in patches],
            "grammar_version": grammar_version,
        },
    )


def _build_hypothesis(
    *,
    obligation_id: str,
    operator: HypothesisOperator,
    operand_refs: Iterable[str],
    provenance_refs: Iterable[str],
    derivation_path_relation_ids: Sequence[str] = (),
    patches: Sequence[CounterfactualPatch] = (),
    outcome_specs: Sequence[tuple[OutcomeKind, FunctionalConsequence]],
    grammar_version: str,
) -> StructuralHypothesis:
    operands = tuple(sorted(set(operand_refs)))
    provenance = tuple(sorted(set(provenance_refs)))
    path = tuple(derivation_path_relation_ids)
    normalized_patches = tuple(patches)
    hypothesis_id = _hypothesis_id(
        obligation_id=obligation_id,
        operator=operator,
        operand_refs=operands,
        derivation_path_relation_ids=path,
        provenance_refs=provenance,
        patches=normalized_patches,
        grammar_version=grammar_version,
    )
    outcomes = tuple(
        FunctionalOutcome.build(
            hypothesis_id=hypothesis_id,
            kind=kind,
            consequence=consequence,
        )
        for kind, consequence in outcome_specs
    )
    return StructuralHypothesis(
        hypothesis_id=hypothesis_id,
        obligation_id=obligation_id,
        operator=operator,
        operand_refs=operands,
        derivation_path_relation_ids=path,
        provenance_refs=provenance,
        patches=normalized_patches,
        outcomes=outcomes,
        grammar_version=grammar_version,
    )


class DependencyGapHypothesisGenerator:
    """Compose bounded candidates from canonical directed graph paths."""

    def __init__(self, policy: HypothesisGenerationPolicy | None = None) -> None:
        self.policy = policy or HypothesisGenerationPolicy()

    def _evidence_paths(
        self,
        kernel: VerdantKernel,
        start_ref: str,
    ) -> tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...]:
        statuses = set(self.policy.traversable_relation_statuses)
        kinds = set(self.policy.qualifying_evidence_kinds)
        adjacency: dict[str, list[tuple[str, str]]] = {}
        for relation in sorted(
            kernel.state.relations.values(), key=lambda item: item.relation_id
        ):
            if relation.status not in statuses:
                continue
            adjacency.setdefault(relation.source_concept_id, []).append(
                (relation.relation_id, relation.target_concept_id)
            )
            if not relation.directed or not self.policy.directed_traversal_only:
                adjacency.setdefault(relation.target_concept_id, []).append(
                    (relation.relation_id, relation.source_concept_id)
                )
        for edges in adjacency.values():
            edges.sort()

        queue: deque[tuple[str, tuple[str, ...], tuple[str, ...]]] = deque(
            [(start_ref, (), (start_ref,))]
        )
        found: list[tuple[tuple[str, ...], str, tuple[str, ...]]] = []
        while queue and len(found) < self.policy.maximum_projected_paths:
            node_ref, relation_path, visited = queue.popleft()
            if relation_path:
                concept = kernel.state.concepts[node_ref]
                evidence_refs = tuple(
                    sorted(
                        ref
                        for ref in concept.evidence_refs
                        if kernel.state.evidence[ref].kind in kinds
                    )
                )
                if evidence_refs:
                    found.append((relation_path, node_ref, evidence_refs))
                    continue
            if len(relation_path) >= self.policy.maximum_path_depth:
                continue
            for relation_id, next_ref in adjacency.get(node_ref, ()):
                if next_ref in visited:
                    continue
                queue.append(
                    (
                        next_ref,
                        (*relation_path, relation_id),
                        (*visited, next_ref),
                    )
                )
        return tuple(found)

    def generate(
        self,
        kernel: VerdantKernel,
        obligation_id: str,
    ) -> tuple[StructuralHypothesis, ...]:
        obligation = kernel.state.obligation_kernels.get(obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        if obligation.missing_input_signature not in kernel.state.concepts:
            raise ObligationIntegrityError(
                "DependencyGap input signature is not a canonical concept."
            )

        hypotheses: list[StructuralHypothesis] = []
        for path, evidence_concept_ref, evidence_refs in self._evidence_paths(
            kernel, obligation.missing_input_signature
        ):
            edge = ProjectedTopologyEdge(
                source_ref=obligation.target_action_node,
                target_ref=evidence_concept_ref,
                relation_type="counterfactual_dependency_bridge",
            )
            patch_key = stable_id(
                "counterfactual_dependency_bridge",
                obligation_id,
                path,
                evidence_concept_ref,
            )
            patch = CounterfactualPatch.upsert(
                "relations",
                patch_key,
                {
                    "counterfactual": True,
                    "source_concept_id": edge.source_ref,
                    "target_concept_id": edge.target_ref,
                    "relation_type": edge.relation_type,
                    "basis_relation_ids": path,
                    "evidence_refs": evidence_refs,
                    "grammar_version": self.policy.policy_version,
                },
            )
            provenance = {
                obligation_id,
                *obligation.canonical_triggering_refs,
                *path,
                evidence_concept_ref,
                *evidence_refs,
            }
            activated = tuple(sorted({evidence_concept_ref, *evidence_refs}))
            hypotheses.append(
                _build_hypothesis(
                    obligation_id=obligation_id,
                    operator=HypothesisOperator.EVIDENCE_PATH_PROJECTION,
                    operand_refs=(
                        obligation.target_action_node,
                        obligation.missing_input_signature,
                        evidence_concept_ref,
                    ),
                    provenance_refs=provenance,
                    derivation_path_relation_ids=path,
                    patches=(patch,),
                    outcome_specs=(
                        (
                            OutcomeKind.PATH_COMPLETES,
                            FunctionalConsequence(
                                action=FunctionalAction.RETRIEVE_CANONICAL_EVIDENCE,
                                activated_canonical_refs=activated,
                                added_edges=(edge,),
                            ),
                        ),
                        (
                            OutcomeKind.PATH_STALLS,
                            FunctionalConsequence(
                                action=FunctionalAction.DEFER_FOR_EVIDENCE,
                                activated_canonical_refs=(
                                    obligation.missing_input_signature,
                                ),
                            ),
                        ),
                        (
                            OutcomeKind.PATH_CONFLICTS,
                            FunctionalConsequence(
                                action=FunctionalAction.REJECT_CANDIDATE,
                                activated_canonical_refs=activated,
                            ),
                        ),
                    ),
                    grammar_version=self.policy.policy_version,
                )
            )

        base_provenance = (obligation_id, *obligation.canonical_triggering_refs)
        hypotheses.append(
            _build_hypothesis(
                obligation_id=obligation_id,
                operator=HypothesisOperator.NULL_ARTIFACT,
                operand_refs=(
                    obligation.target_action_node,
                    obligation.missing_input_signature,
                ),
                provenance_refs=base_provenance,
                outcome_specs=(
                    (
                        OutcomeKind.ARTIFACT_REJECTED,
                        FunctionalConsequence(
                            action=FunctionalAction.REJECT_CANDIDATE,
                            activated_canonical_refs=(
                                obligation.missing_input_signature,
                            ),
                        ),
                    ),
                ),
                grammar_version=self.policy.policy_version,
            )
        )
        hypotheses.append(
            _build_hypothesis(
                obligation_id=obligation_id,
                operator=HypothesisOperator.DEFER_INSUFFICIENT_EVIDENCE,
                operand_refs=(
                    obligation.target_action_node,
                    obligation.missing_input_signature,
                ),
                provenance_refs=base_provenance,
                outcome_specs=(
                    (
                        OutcomeKind.EVIDENCE_INSUFFICIENT,
                        FunctionalConsequence(
                            action=FunctionalAction.DEFER_FOR_EVIDENCE,
                            activated_canonical_refs=(
                                obligation.missing_input_signature,
                            ),
                        ),
                    ),
                ),
                grammar_version=self.policy.policy_version,
            )
        )
        return tuple(sorted(hypotheses, key=lambda item: item.hypothesis_id))


def build_hypothesis_plan(
    hypothesis: StructuralHypothesis,
    outcome: FunctionalOutcome,
    *,
    source_event_key: str,
    requested_budget: float,
    consumed_budget: float,
) -> CounterfactualPlan:
    """Translate one preregistered outcome arm into an isolated dry-run plan."""

    if outcome.hypothesis_id != hypothesis.hypothesis_id:
        raise ValueError("Dry-run outcome does not belong to the hypothesis.")
    if outcome not in hypothesis.outcomes:
        raise ValueError("Dry-run outcome is not a preregistered hypothesis arm.")
    apply_count = (
        len(hypothesis.patches)
        if outcome.kind == OutcomeKind.PATH_COMPLETES
        else 0
    )
    return CounterfactualPlan.build(
        source_event_key=source_event_key,
        operator_version=hypothesis.grammar_version,
        requested_budget=requested_budget,
        consumed_budget=consumed_budget,
        patches=hypothesis.patches,
        apply_patch_count=apply_count,
        disposition=SimulationDisposition.DISCARDED,
        result_refs=(
            hypothesis.hypothesis_id,
            outcome.outcome_id,
            outcome.equivalence_signature,
        ),
    )
