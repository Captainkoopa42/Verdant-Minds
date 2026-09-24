"""Answer-agnostic DependencyGap Resolution Contracts.

The validator compares replicated baseline/treatment observations produced from
the same canonical checkpoint.  It checks operational geometry and provenance,
not semantic truth.  A passing verdict remains non-authoritative: this module
cannot append a ``Resolved`` event or promote simulated state.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import EvidenceKind, VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .counterfactual import SimulationDisposition, SimulationLedger
from .equivalence import EquivalenceLensSystem, LensBindingStatus, LensUnavailableError
from .pipeline import ObligationIntegrityError


RESOLUTION_CONTRACT_VERSION = "dependency_gap_resolution_contract_v0.7"


def dependency_evidence_edge_ref(concept_ref: str, evidence_ref: str) -> str:
    """Return the deterministic identity of a concept-to-evidence membership edge."""

    return stable_id("concept_evidence_membership", concept_ref, evidence_ref)


class ResolutionIntegrityError(RuntimeError):
    pass


class TrialArm(str, Enum):
    BASELINE = "baseline"
    TREATMENT = "treatment"


class ResolutionInvariant(str, Enum):
    MATCHED_CONTROLS = "MatchedControls"
    EVIDENCE_PRESERVED = "EvidencePreserved"
    NO_SUPPRESSION = "NoSuppression"
    PREDICTIVE_DISCRIMINATION = "PredictiveDiscrimination"
    EXPLANATORY_GAIN = "ExplanatoryGain"
    LINEAGE_TRACEABILITY = "LineageTraceability"
    GOVERNANCE_PASS = "GovernancePass"
    DEPENDENCY_PATH_COMPLETION = "DependencyPathCompletion"
    CROSS_SEED_REPLICATION = "CrossSeedReplication"


class ResolutionContractPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = RESOLUTION_CONTRACT_VERSION
    minimum_matched_pairs: int = Field(default=2, ge=2, le=32)
    require_distinct_seeds: bool = True
    qualifying_evidence_kinds: tuple[EvidenceKind, ...] = (
        EvidenceKind.ACTION,
        EvidenceKind.OUTCOME,
    )
    maximum_completed_path_distance: int = Field(default=32, ge=1)

    @model_validator(mode="after")
    def validate_policy(self) -> "ResolutionContractPolicy":
        if not self.policy_version.strip():
            raise ValueError("Resolution Contract policy version cannot be empty.")
        kinds = tuple(sorted(set(self.qualifying_evidence_kinds), key=lambda x: x.value))
        if not kinds or kinds != self.qualifying_evidence_kinds:
            raise ValueError("Resolution evidence kinds must be sorted and unique.")
        return self


class ResolutionCandidate(FrozenRecord):
    candidate_id: str
    obligation_id: str
    resolution_structure_ref: str
    protected_canonical_refs: tuple[str, ...] = Field(min_length=1)
    lineage_refs: tuple[str, ...] = Field(min_length=1)
    governance_refs: tuple[str, ...] = Field(min_length=1)
    contract_version: str = RESOLUTION_CONTRACT_VERSION

    @classmethod
    def build(cls, **values: Any) -> "ResolutionCandidate":
        values.setdefault("contract_version", RESOLUTION_CONTRACT_VERSION)
        for key in (
            "protected_canonical_refs",
            "lineage_refs",
            "governance_refs",
        ):
            values[key] = tuple(sorted(set(values[key])))
        payload = {
            key: value
            for key, value in values.items()
            if key != "candidate_id"
        }
        return cls(
            candidate_id=stable_id("resolution_candidate", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_candidate(self) -> "ResolutionCandidate":
        required = (
            self.obligation_id,
            self.resolution_structure_ref,
            self.contract_version,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Resolution candidate identity fields cannot be empty.")
        for values, label in (
            (self.protected_canonical_refs, "protected refs"),
            (self.lineage_refs, "lineage refs"),
            (self.governance_refs, "governance refs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Resolution candidate {label} must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("resolution_candidate", payload):
            raise ValueError("Resolution candidate checksum mismatch.")
        return self


class DependencyPathObservation(FrozenRecord):
    node_refs: tuple[str, ...] = Field(min_length=2)
    edge_refs: tuple[str, ...] = Field(min_length=1)
    actionable_evidence_ref: str
    distance: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_path(self) -> "DependencyPathObservation":
        if not self.actionable_evidence_ref.strip():
            raise ValueError("Dependency path requires actionable evidence.")
        if self.distance != len(self.edge_refs):
            raise ValueError("Dependency path distance must equal its edge count.")
        if len(self.node_refs) != len(self.edge_refs) + 1:
            raise ValueError("Dependency path nodes and edges are not contiguous.")
        if self.node_refs[-1] != self.actionable_evidence_ref:
            raise ValueError("Dependency path must terminate at actionable evidence.")
        return self


class ResolutionTrialObservation(FrozenRecord):
    observation_id: str
    arm: TrialArm
    checkpoint_fingerprint: str
    cue_ref: str
    context_fingerprint: str
    seed: int = Field(ge=0)
    horizon: int = Field(ge=1)
    lens_binding_id: str
    simulation_settlement_ref: str
    resolution_structure_ref: str | None = None
    retrieved_refs: tuple[str, ...] = ()
    admitted_refs: tuple[str, ...] = ()
    outgoing_action_signature: str
    slot_budget: int = Field(ge=1)
    suppressed_refs: tuple[str, ...] = ()
    removed_edge_refs: tuple[str, ...] = ()
    dependency_path: DependencyPathObservation | None = None

    @classmethod
    def build(cls, **values: Any) -> "ResolutionTrialObservation":
        values.setdefault("resolution_structure_ref", None)
        values.setdefault("dependency_path", None)
        for key in (
            "retrieved_refs",
            "admitted_refs",
            "suppressed_refs",
            "removed_edge_refs",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        payload = {
            key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "observation_id"
        }
        return cls(
            observation_id=stable_id("resolution_trial_observation", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_observation(self) -> "ResolutionTrialObservation":
        required = (
            self.checkpoint_fingerprint,
            self.cue_ref,
            self.context_fingerprint,
            self.lens_binding_id,
            self.simulation_settlement_ref,
            self.outgoing_action_signature,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Resolution trial identity fields cannot be empty.")
        if len(self.checkpoint_fingerprint) != 64:
            raise ValueError("Resolution trial checkpoint fingerprint must be SHA-256.")
        for values, label in (
            (self.retrieved_refs, "retrieved refs"),
            (self.admitted_refs, "admitted refs"),
            (self.suppressed_refs, "suppressed refs"),
            (self.removed_edge_refs, "removed edges"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Resolution trial {label} must be sorted and unique.")
        if self.arm == TrialArm.BASELINE:
            if self.resolution_structure_ref is not None:
                raise ValueError("Baseline arm cannot contain the proposed resolution.")
        elif self.resolution_structure_ref is None:
            raise ValueError("Treatment arm requires the proposed resolution.")
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id("resolution_trial_observation", payload):
            raise ValueError("Resolution trial observation checksum mismatch.")
        return self


class MatchedResolutionPair(FrozenRecord):
    pair_id: str
    baseline: ResolutionTrialObservation
    treatment: ResolutionTrialObservation

    @classmethod
    def build(
        cls,
        baseline: ResolutionTrialObservation,
        treatment: ResolutionTrialObservation,
    ) -> "MatchedResolutionPair":
        return cls(
            pair_id=stable_id(
                "matched_resolution_pair",
                baseline.observation_id,
                treatment.observation_id,
            ),
            baseline=baseline,
            treatment=treatment,
        )

    @model_validator(mode="after")
    def validate_pair(self) -> "MatchedResolutionPair":
        if self.baseline.arm != TrialArm.BASELINE or self.treatment.arm != TrialArm.TREATMENT:
            raise ValueError("Matched pair arms are reversed or duplicated.")
        expected = stable_id(
            "matched_resolution_pair",
            self.baseline.observation_id,
            self.treatment.observation_id,
        )
        if self.pair_id != expected:
            raise ValueError("Matched resolution pair checksum mismatch.")
        return self


class ResolutionInvariantResult(FrozenRecord):
    invariant: ResolutionInvariant
    passed: bool
    evidence_refs: tuple[str, ...] = ()
    failure_code: str | None = None

    @model_validator(mode="after")
    def validate_result(self) -> "ResolutionInvariantResult":
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Resolution invariant evidence refs must be sorted and unique.")
        if self.passed == (self.failure_code is not None):
            raise ValueError("Resolution invariant pass/failure details disagree.")
        return self


class ResolutionContractVerdict(FrozenRecord):
    verdict_id: str
    candidate_id: str
    pair_ids: tuple[str, ...] = Field(min_length=1)
    invariant_results: tuple[ResolutionInvariantResult, ...]
    passed: bool
    resolution_authority_enabled: bool = False
    contract_version: str = RESOLUTION_CONTRACT_VERSION

    @model_validator(mode="after")
    def validate_verdict(self) -> "ResolutionContractVerdict":
        if tuple(sorted(set(self.pair_ids))) != self.pair_ids:
            raise ValueError("Resolution verdict pair IDs must be sorted and unique.")
        invariants = tuple(item.invariant for item in self.invariant_results)
        if tuple(sorted(set(invariants), key=lambda x: x.value)) != invariants:
            raise ValueError("Resolution invariant results must be sorted and unique.")
        if self.passed != all(item.passed for item in self.invariant_results):
            raise ValueError("Resolution verdict disagrees with invariant results.")
        if self.resolution_authority_enabled:
            raise ValueError("Experimental Resolution Contracts cannot resolve obligations.")
        payload = self.model_dump(mode="json", exclude={"verdict_id"})
        if self.verdict_id != stable_id("resolution_contract_verdict", payload):
            raise ValueError("Resolution verdict checksum mismatch.")
        return self


class DependencyGapResolutionValidator:
    def __init__(self, policy: ResolutionContractPolicy | None = None) -> None:
        self.policy = policy or ResolutionContractPolicy()

    @staticmethod
    def _canonical_refs(kernel: VerdantKernel) -> set[str]:
        collections = (
            kernel.state.evidence,
            kernel.state.concepts,
            kernel.state.relations,
            kernel.state.claims,
            kernel.state.structures,
            kernel.state.layered_structures,
            kernel.state.obligation_kernels,
        )
        return {ref for collection in collections for ref in collection}

    @staticmethod
    def _result(
        invariant: ResolutionInvariant,
        passed: bool,
        refs: Sequence[str],
        failure_code: str,
    ) -> ResolutionInvariantResult:
        return ResolutionInvariantResult(
            invariant=invariant,
            passed=passed,
            evidence_refs=tuple(sorted(set(refs))),
            failure_code=None if passed else failure_code,
        )

    @staticmethod
    def _path_is_canonical(
        kernel: VerdantKernel,
        path: DependencyPathObservation,
    ) -> bool:
        """Verify every observed hop against canonical topology or membership."""

        for source_ref, target_ref, edge_ref in zip(
            path.node_refs[:-1],
            path.node_refs[1:],
            path.edge_refs,
            strict=True,
        ):
            relation = kernel.state.relations.get(edge_ref)
            if relation is not None:
                if (
                    relation.source_concept_id != source_ref
                    or relation.target_concept_id != target_ref
                ):
                    return False
                continue
            concept = kernel.state.concepts.get(source_ref)
            if (
                concept is None
                or target_ref not in concept.evidence_refs
                or edge_ref
                != dependency_evidence_edge_ref(source_ref, target_ref)
            ):
                return False
        return True

    def validate(
        self,
        kernel: VerdantKernel,
        *,
        candidate: ResolutionCandidate,
        matched_pairs: Sequence[MatchedResolutionPair],
        simulation_ledger: SimulationLedger,
        lens_system: EquivalenceLensSystem,
    ) -> ResolutionContractVerdict:
        obligation = kernel.state.obligation_kernels.get(candidate.obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Unknown obligation kernel.")
        if candidate.contract_version != self.policy.policy_version:
            raise ResolutionIntegrityError("Resolution candidate contract version drifted.")
        pairs = tuple(sorted(matched_pairs, key=lambda item: item.pair_id))
        if len({item.pair_id for item in pairs}) != len(pairs):
            raise ResolutionIntegrityError("Resolution Contract duplicates a matched pair.")

        canonical_refs = self._canonical_refs(kernel)
        protected = set(candidate.protected_canonical_refs)
        expected_protected = set(obligation.canonical_triggering_refs)
        protected_valid = protected == expected_protected and protected.issubset(canonical_refs)

        settlements = {
            item.settlement_id: item for item in simulation_ledger.state.settlements
        }
        simulation_lineage = {
            ref
            for item in simulation_ledger.state.settlements
            for ref in (
                item.settlement_id,
                item.reservation_id,
                *item.result_refs,
            )
        }
        governance_refs = {
            item.event_id for item in lens_system.ledger.governance_events
        }
        definition_refs = set(lens_system.registry.definitions)
        binding_refs = {item.binding_id for item in lens_system.ledger.bindings}
        known_lineage = simulation_lineage | governance_refs | definition_refs | binding_refs

        pair_count_ok = len(pairs) >= self.policy.minimum_matched_pairs
        matched_ok = pair_count_ok
        evidence_ok = protected_valid
        suppression_ok = protected_valid
        discrimination_ok = pair_count_ok
        explanatory_ok = pair_count_ok
        path_ok = pair_count_ok
        settlement_ok = pair_count_ok
        common_treatment_actions: set[str] = set()
        seeds: set[int] = set()
        result_refs: list[str] = []

        active_lens_id = None
        try:
            active_view = lens_system.active_binding(obligation.family)
            if active_view.status == LensBindingStatus.ACTIVE:
                active_lens_id = active_view.binding.binding_id
        except LensUnavailableError:
            active_lens_id = None

        for pair in pairs:
            baseline = pair.baseline
            treatment = pair.treatment
            result_refs.extend((pair.pair_id, baseline.observation_id, treatment.observation_id))
            seeds.add(baseline.seed)
            matched_fields = (
                baseline.checkpoint_fingerprint == treatment.checkpoint_fingerprint,
                baseline.checkpoint_fingerprint == kernel.fingerprint(),
                baseline.cue_ref == treatment.cue_ref,
                baseline.context_fingerprint == treatment.context_fingerprint,
                baseline.seed == treatment.seed,
                baseline.horizon == treatment.horizon,
                baseline.lens_binding_id == treatment.lens_binding_id,
                baseline.lens_binding_id == active_lens_id,
                treatment.resolution_structure_ref == candidate.resolution_structure_ref,
            )
            matched_ok &= all(matched_fields)

            pair_settlements = (
                settlements.get(baseline.simulation_settlement_ref),
                settlements.get(treatment.simulation_settlement_ref),
            )
            settlement_ok &= all(
                item is not None
                and item.disposition == SimulationDisposition.DISCARDED
                and item.canonical_unchanged
                for item in pair_settlements
            )

            baseline_retrieved = set(baseline.retrieved_refs)
            treatment_retrieved = set(treatment.retrieved_refs)
            treatment_admitted = set(treatment.admitted_refs)
            evidence_ok &= protected.issubset(baseline_retrieved)
            evidence_ok &= protected.issubset(treatment_retrieved)
            evidence_ok &= protected.issubset(treatment_admitted)
            evidence_ok &= candidate.resolution_structure_ref in treatment_admitted

            suppression_ok &= not protected.intersection(treatment.suppressed_refs)
            suppression_ok &= not treatment.removed_edge_refs
            suppression_ok &= treatment.slot_budget >= baseline.slot_budget

            action_changed = (
                baseline.outgoing_action_signature
                != treatment.outgoing_action_signature
            )
            discrimination_ok &= action_changed
            common_treatment_actions.add(treatment.outgoing_action_signature)

            baseline_has_path = baseline.dependency_path is not None
            treatment_path = treatment.dependency_path
            actionable = (
                treatment_path is not None
                and treatment_path.actionable_evidence_ref in kernel.state.evidence
                and kernel.state.evidence[
                    treatment_path.actionable_evidence_ref
                ].kind in self.policy.qualifying_evidence_kinds
            )
            completed = (
                treatment_path is not None
                and treatment_path.node_refs[0] == obligation.target_action_node
                and treatment_path.distance
                <= self.policy.maximum_completed_path_distance
                and actionable
                and self._path_is_canonical(kernel, treatment_path)
            )
            path_ok &= not baseline_has_path and completed
            explanatory_ok &= action_changed and completed

        cross_seed_ok = pair_count_ok
        if self.policy.require_distinct_seeds:
            cross_seed_ok &= len(seeds) == len(pairs)
        cross_seed_ok &= len(common_treatment_actions) == 1

        lineage_ok = (
            set(candidate.lineage_refs).issubset(known_lineage)
            and all(item in simulation_lineage for item in candidate.lineage_refs)
            and settlement_ok
        )
        governance_ok = (
            bool(active_lens_id)
            and set(candidate.governance_refs).issubset(governance_refs)
            and bool(candidate.governance_refs)
        )

        results = tuple(
            sorted(
                (
                    self._result(ResolutionInvariant.MATCHED_CONTROLS, matched_ok, result_refs, "unmatched_control"),
                    self._result(ResolutionInvariant.EVIDENCE_PRESERVED, evidence_ok, candidate.protected_canonical_refs, "evidence_not_preserved"),
                    self._result(ResolutionInvariant.NO_SUPPRESSION, suppression_ok, result_refs, "suppression_detected"),
                    self._result(ResolutionInvariant.PREDICTIVE_DISCRIMINATION, discrimination_ok, result_refs, "outgoing_action_unchanged"),
                    self._result(ResolutionInvariant.EXPLANATORY_GAIN, explanatory_ok, result_refs, "no_operational_gain"),
                    self._result(ResolutionInvariant.LINEAGE_TRACEABILITY, lineage_ok, candidate.lineage_refs, "lineage_unverified"),
                    self._result(ResolutionInvariant.GOVERNANCE_PASS, governance_ok, candidate.governance_refs, "governance_unverified"),
                    self._result(ResolutionInvariant.DEPENDENCY_PATH_COMPLETION, path_ok, result_refs, "dependency_path_not_completed"),
                    self._result(ResolutionInvariant.CROSS_SEED_REPLICATION, cross_seed_ok, result_refs, "replication_failed"),
                ),
                key=lambda item: item.invariant.value,
            )
        )
        payload = {
            "candidate_id": candidate.candidate_id,
            "pair_ids": tuple(item.pair_id for item in pairs),
            "invariant_results": [item.model_dump(mode="json") for item in results],
            "passed": all(item.passed for item in results),
            "resolution_authority_enabled": False,
            "contract_version": self.policy.policy_version,
        }
        return ResolutionContractVerdict(
            verdict_id=stable_id("resolution_contract_verdict", payload),
            candidate_id=candidate.candidate_id,
            pair_ids=payload["pair_ids"],
            invariant_results=results,
            passed=payload["passed"],
            resolution_authority_enabled=False,
            contract_version=self.policy.policy_version,
        )
