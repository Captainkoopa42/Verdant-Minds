"""Explicit, transactional integration of the DependencyGap inquiry slice.

This coordinator is an opt-in experiment, not a scheduler. It joins native
topology detection, deterministic hypothesis composition, bounded Attention,
and copy-on-write simulation while retaining every authority boundary of the
underlying components. Hypothesis arms remain preregistered possibilities;
executing them does not assert that an outcome occurred or resolve anything.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import ObligationFamily, VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .attention import (
    AttentionBidInput,
    AttentionPortfolio,
    AttentionPortfolioResult,
)
from .counterfactual import (
    CounterfactualPlan,
    CounterfactualRunResult,
    CounterfactualRuntime,
    SimulationDisposition,
    SimulationLedger,
)
from .detection import (
    DependencyGapCandidate,
    DependencyGapDetectionReport,
    DependencyGapDetector,
)
from .hypotheses import (
    DependencyGapHypothesisGenerator,
    FunctionalOutcome,
    FunctionalPartitionIndex,
    HypothesisOperator,
    OutcomeKind,
    StructuralHypothesis,
    build_hypothesis_plan,
)
from .pipeline import ObligationMutationResult, derive_obligation_view
from .resolution_evidence import (
    TraceResolutionEvidenceDeriver,
    TraceResolutionEvidenceIntegrityError,
    TraceResolutionEvidenceReceipt,
)
from .trace_observations import (
    MatchedCounterfactualObserver,
    MatchedCounterfactualPlans,
    MatchedStructuralObservation,
    TraceObservationIntegrityError,
    build_matched_counterfactual_plans,
)


INTEGRATED_INQUIRY_POLICY_VERSION = "dependency_gap_integrated_inquiry_v0.25"
MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION = 2


class IntegratedInquiryError(RuntimeError):
    """Raised when the opt-in path cannot preserve its declared boundary."""


class IntegratedInquiryPolicy(BaseModel):
    """Visible supplied bounds and bid metrics; none are claimed as learned."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = INTEGRATED_INQUIRY_POLICY_VERSION
    maximum_simulations_per_obligation: int = Field(default=3, ge=1, le=8)
    simulation_requested_budget: float = Field(default=0.01, gt=0.0)
    simulation_consumed_budget: float = Field(default=0.005, ge=0.0)
    expected_gain: float = Field(default=0.60, ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.80, ge=0.0, le=1.0)
    urgency: float = Field(default=0.50, ge=0.0, le=1.0)
    novelty: float = Field(default=0.70, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_policy(self) -> "IntegratedInquiryPolicy":
        if not self.policy_version.strip():
            raise ValueError("Integrated inquiry policy version cannot be empty.")
        if self.simulation_consumed_budget > self.simulation_requested_budget + 1e-12:
            raise ValueError("Integrated simulation consumption exceeds its reservation.")
        return self

    @property
    def attention_requested_budget(self) -> float:
        return (
            (
                self.maximum_simulations_per_obligation
                + MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION
            )
            * self.simulation_requested_budget
        )

    @property
    def attention_estimated_cost(self) -> float:
        return (
            (
                self.maximum_simulations_per_obligation
                + MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION
            )
            * self.simulation_consumed_budget
        )


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _identity_payload(values: Mapping[str, Any], identity_field: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if key == identity_field:
            continue
        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, tuple):
            payload[key] = tuple(
                item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                for item in value
            )
        else:
            payload[key] = value
    return payload


class IntegratedInquiryTrial(FrozenRecord):
    """One complete detector-to-settlement provenance chain."""

    trial_id: str
    obligation_id: str
    detection_candidate_id: str
    obligation_event_id: str
    hypothesis_id: str
    outcome_id: str
    equivalence_signature: str
    partition_id: str
    attention_decision_id: str
    attention_allocation_id: str
    plan_id: str
    reservation_id: str
    settlement_id: str
    canonical_unchanged: bool = True
    canonical_commit_permitted: bool = False
    epistemic_authority_enabled: bool = False

    @classmethod
    def build(cls, **values: Any) -> "IntegratedInquiryTrial":
        values.setdefault("canonical_unchanged", True)
        values.setdefault("canonical_commit_permitted", False)
        values.setdefault("epistemic_authority_enabled", False)
        values["trial_id"] = stable_id(
            "integrated_inquiry_trial",
            _identity_payload(values, "trial_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_trial(self) -> "IntegratedInquiryTrial":
        identifiers = (
            self.obligation_id,
            self.detection_candidate_id,
            self.obligation_event_id,
            self.hypothesis_id,
            self.outcome_id,
            self.equivalence_signature,
            self.partition_id,
            self.attention_decision_id,
            self.attention_allocation_id,
            self.plan_id,
            self.reservation_id,
            self.settlement_id,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Integrated inquiry trial references cannot be empty.")
        if (
            not self.canonical_unchanged
            or self.canonical_commit_permitted
            or self.epistemic_authority_enabled
        ):
            raise ValueError("Integrated inquiry trials are non-committing simulations.")
        expected = stable_id(
            "integrated_inquiry_trial",
            self.model_dump(mode="json", exclude={"trial_id"}),
        )
        if self.trial_id != expected:
            raise ValueError("Integrated inquiry trial identity checksum mismatch.")
        return self


class IntegratedInquiryTrace(FrozenRecord):
    """Content-addressed, reconstructable receipt for one opt-in invocation."""

    trace_id: str
    source_event_key: str
    policy_version: str
    policy_sha256: str
    detector_policy_version: str
    detector_policy_sha256: str
    attention_policy_version: str
    attention_policy_sha256: str
    hypothesis_policy_version: str
    hypothesis_policy_sha256: str
    detection_candidate_ids: tuple[str, ...] = Field(min_length=1)
    obligation_ids: tuple[str, ...] = Field(min_length=1)
    obligation_event_ids: tuple[str, ...] = Field(min_length=1)
    hypothesis_ids: tuple[str, ...] = Field(min_length=1)
    partition_ids: tuple[str, ...] = Field(min_length=1)
    attention_decision_id: str
    attention_bid_ids: tuple[str, ...] = Field(min_length=1)
    attention_allocation_ids: tuple[str, ...] = Field(min_length=1)
    deferred_bid_ids: tuple[str, ...] = ()
    trials: tuple[IntegratedInquiryTrial, ...] = Field(min_length=1)
    matched_observations: tuple[MatchedStructuralObservation, ...] = Field(
        min_length=1
    )
    resolution_evidence_receipts: tuple[
        TraceResolutionEvidenceReceipt, ...
    ] = Field(min_length=1)
    canonical_checkpoint_fingerprint: str
    simulation_ledger_fingerprint: str
    canonical_simulation_leakage_detected: bool = False
    canonical_resolution_permitted: bool = False
    epistemic_authority_enabled: bool = False

    @classmethod
    def build(cls, **values: Any) -> "IntegratedInquiryTrace":
        for key in (
            "detection_candidate_ids",
            "obligation_ids",
            "obligation_event_ids",
            "hypothesis_ids",
            "partition_ids",
            "attention_bid_ids",
            "attention_allocation_ids",
            "deferred_bid_ids",
        ):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        trials = tuple(
            item
            if isinstance(item, IntegratedInquiryTrial)
            else IntegratedInquiryTrial.model_validate(item)
            for item in values["trials"]
        )
        values["trials"] = tuple(sorted(trials, key=lambda item: item.trial_id))
        observations = tuple(
            item
            if isinstance(item, MatchedStructuralObservation)
            else MatchedStructuralObservation.model_validate(item)
            for item in values["matched_observations"]
        )
        values["matched_observations"] = tuple(
            sorted(observations, key=lambda item: item.observation_id)
        )
        receipts = tuple(
            item
            if isinstance(item, TraceResolutionEvidenceReceipt)
            else TraceResolutionEvidenceReceipt.model_validate(item)
            for item in values["resolution_evidence_receipts"]
        )
        values["resolution_evidence_receipts"] = tuple(
            sorted(receipts, key=lambda item: item.receipt_id)
        )
        values.setdefault("canonical_simulation_leakage_detected", False)
        values.setdefault("canonical_resolution_permitted", False)
        values.setdefault("epistemic_authority_enabled", False)
        values["trace_id"] = stable_id(
            "integrated_inquiry_trace",
            _identity_payload(values, "trace_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_trace(self) -> "IntegratedInquiryTrace":
        if not all(
            item.strip()
            for item in (
                self.source_event_key,
                self.policy_version,
                self.detector_policy_version,
                self.attention_policy_version,
                self.hypothesis_policy_version,
                self.attention_decision_id,
            )
        ):
            raise ValueError("Integrated inquiry trace identifiers cannot be empty.")
        for digest in (
            self.policy_sha256,
            self.detector_policy_sha256,
            self.attention_policy_sha256,
            self.hypothesis_policy_sha256,
            self.canonical_checkpoint_fingerprint,
            self.simulation_ledger_fingerprint,
        ):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("Integrated inquiry trace digests must be SHA-256.")
        for values, label in (
            (self.detection_candidate_ids, "detection candidates"),
            (self.obligation_ids, "obligations"),
            (self.obligation_event_ids, "obligation events"),
            (self.hypothesis_ids, "hypotheses"),
            (self.partition_ids, "partitions"),
            (self.attention_bid_ids, "attention bids"),
            (self.attention_allocation_ids, "attention allocations"),
            (self.deferred_bid_ids, "deferred bids"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Integrated inquiry {label} must be sorted and unique.")
        trial_ids = tuple(item.trial_id for item in self.trials)
        if tuple(sorted(set(trial_ids))) != trial_ids:
            raise ValueError("Integrated inquiry trials must be sorted and unique.")
        observation_ids = tuple(
            item.observation_id for item in self.matched_observations
        )
        if tuple(sorted(set(observation_ids))) != observation_ids:
            raise ValueError(
                "Integrated inquiry matched observations must be sorted and unique."
            )
        receipt_ids = tuple(
            item.receipt_id for item in self.resolution_evidence_receipts
        )
        if tuple(sorted(set(receipt_ids))) != receipt_ids:
            raise ValueError(
                "Integrated resolution evidence receipts must be sorted and unique."
            )
        if (
            self.canonical_simulation_leakage_detected
            or self.canonical_resolution_permitted
            or self.epistemic_authority_enabled
        ):
            raise ValueError("Integrated inquiry traces cannot carry epistemic authority.")
        for trial in self.trials:
            if trial.obligation_id not in self.obligation_ids:
                raise ValueError("Integrated trial lost its obligation.")
            if trial.detection_candidate_id not in self.detection_candidate_ids:
                raise ValueError("Integrated trial lost its detector candidate.")
            if trial.obligation_event_id not in self.obligation_event_ids:
                raise ValueError("Integrated trial lost its obligation event.")
            if trial.hypothesis_id not in self.hypothesis_ids:
                raise ValueError("Integrated trial lost its hypothesis.")
            if trial.partition_id not in self.partition_ids:
                raise ValueError("Integrated trial lost its functional partition.")
            if trial.attention_decision_id != self.attention_decision_id:
                raise ValueError("Integrated trial crossed an Attention decision.")
            if trial.attention_allocation_id not in self.attention_allocation_ids:
                raise ValueError("Integrated trial lost its Attention allocation.")
        observed_allocations: list[str] = []
        for observation in self.matched_observations:
            baseline = observation.baseline
            treatment = observation.treatment
            if (
                baseline.obligation_id != treatment.obligation_id
                or baseline.obligation_id not in self.obligation_ids
            ):
                raise ValueError("Matched observation crossed an obligation boundary.")
            if (
                baseline.attention_decision_id != self.attention_decision_id
                or treatment.attention_decision_id != self.attention_decision_id
            ):
                raise ValueError("Matched observation crossed an Attention decision.")
            if (
                baseline.allocation_id != treatment.allocation_id
                or baseline.allocation_id not in self.attention_allocation_ids
            ):
                raise ValueError("Matched observation lost its Attention allocation.")
            if observation.hypothesis_ref not in self.hypothesis_ids:
                raise ValueError("Matched observation lost its hypothesis.")
            if (
                baseline.result_refs != (observation.hypothesis_ref,)
                or treatment.result_refs != (observation.hypothesis_ref,)
            ):
                raise ValueError(
                    "Matched observation acquired supplied outcome authority."
                )
            if (
                baseline.canonical_fingerprint
                != self.canonical_checkpoint_fingerprint
                or treatment.canonical_fingerprint
                != self.canonical_checkpoint_fingerprint
            ):
                raise ValueError("Matched observation crossed a canonical checkpoint.")
            if not observation.canonical_records_preserved:
                raise ValueError(
                    "Integrated inquiry cannot publish a mutating matched treatment."
                )
            observed_allocations.append(baseline.allocation_id)
        if tuple(sorted(observed_allocations)) != self.attention_allocation_ids:
            raise ValueError(
                "Every integrated Attention allocation requires one matched receipt."
            )
        observations_by_id = {
            item.observation_id: item for item in self.matched_observations
        }
        receipt_observation_refs: list[str] = []
        for receipt in self.resolution_evidence_receipts:
            observation = observations_by_id.get(receipt.matched_observation_ref)
            if observation is None:
                raise ValueError(
                    "Resolution evidence receipt lost its matched observation."
                )
            if (
                receipt.obligation_id != observation.baseline.obligation_id
                or receipt.hypothesis_ref != observation.hypothesis_ref
                or receipt.canonical_checkpoint_fingerprint
                != self.canonical_checkpoint_fingerprint
                or receipt.baseline_trace_ref != observation.baseline.trace_id
                or receipt.treatment_trace_ref != observation.treatment.trace_id
                or receipt.baseline_settlement_ref
                != observation.baseline.settlement_id
                or receipt.treatment_settlement_ref
                != observation.treatment.settlement_id
            ):
                raise ValueError(
                    "Resolution evidence receipt crossed its matched lineage."
                )
            if receipt.obligation_event_ref not in self.obligation_event_ids:
                raise ValueError(
                    "Resolution evidence receipt lost its obligation event."
                )
            receipt_observation_refs.append(receipt.matched_observation_ref)
        if tuple(sorted(receipt_observation_refs)) != observation_ids:
            raise ValueError(
                "Every matched observation requires one resolution coverage receipt."
            )
        expected = stable_id(
            "integrated_inquiry_trace",
            self.model_dump(mode="json", exclude={"trace_id"}),
        )
        if self.trace_id != expected:
            raise ValueError("Integrated inquiry trace identity checksum mismatch.")
        return self


@dataclass(frozen=True)
class IntegratedMatchedInquiryPair:
    """One executed zero/full control pair and its derived structural receipt."""

    obligation_id: str
    hypothesis_id: str
    plans: MatchedCounterfactualPlans
    baseline: CounterfactualRunResult
    treatment: CounterfactualRunResult
    observation: MatchedStructuralObservation
    resolution_evidence: TraceResolutionEvidenceReceipt

    @property
    def replayed(self) -> bool:
        return self.baseline.replayed and self.treatment.replayed


@dataclass(frozen=True)
class IntegratedInquiryResult:
    trace: IntegratedInquiryTrace
    detection: DependencyGapDetectionReport
    hypotheses: tuple[StructuralHypothesis, ...]
    partitions: tuple[FunctionalPartitionIndex, ...]
    attention: AttentionPortfolioResult
    plans: tuple[CounterfactualPlan, ...]
    simulations: tuple[CounterfactualRunResult, ...]
    matched_pairs: tuple[IntegratedMatchedInquiryPair, ...]
    replayed: bool


_OUTCOME_PRIORITY = {
    OutcomeKind.PATH_COMPLETES: 0,
    OutcomeKind.PATH_STALLS: 1,
    OutcomeKind.PATH_CONFLICTS: 2,
    OutcomeKind.ARTIFACT_REJECTED: 3,
    OutcomeKind.EVIDENCE_INSUFFICIENT: 4,
}


class DependencyGapInquiryCoordinator:
    """Run the existing DependencyGap components as one explicit transaction."""

    def __init__(
        self,
        *,
        policy: IntegratedInquiryPolicy | None = None,
        detector: DependencyGapDetector | None = None,
        attention: AttentionPortfolio | None = None,
        generator: DependencyGapHypothesisGenerator | None = None,
        matched_observer: MatchedCounterfactualObserver | None = None,
    ) -> None:
        self.policy = policy or IntegratedInquiryPolicy()
        self.detector = detector or DependencyGapDetector()
        self.attention = attention or AttentionPortfolio()
        self.generator = generator or DependencyGapHypothesisGenerator()
        self.matched_observer = matched_observer or MatchedCounterfactualObserver()
        if (
            self.policy.simulation_requested_budget
            > self.attention.policy.micro_probe_budget + 1e-12
        ):
            raise ValueError(
                "One integrated simulation must fit the Attention micro-probe grant."
            )

    @staticmethod
    def _validate_detection_link(
        candidate: DependencyGapCandidate,
        mutation: ObligationMutationResult,
    ) -> None:
        obligation = mutation.obligation
        if (
            obligation.family != ObligationFamily.DEPENDENCY_GAP
            or obligation.target_action_node != candidate.target_action_node
            or obligation.missing_input_signature != candidate.missing_input_signature
            or obligation.trigger_relation != candidate.trigger_relation
            or obligation.scope_key != candidate.scope_key
            or obligation.canonical_triggering_refs
            != candidate.canonical_triggering_refs
            or mutation.event.source_event_key != candidate.source_event_key
            or mutation.event.triggering_refs != candidate.canonical_triggering_refs
            or mutation.event.context_snapshot_hash != candidate.context_snapshot_hash
            or mutation.event.source_lineage_roots != candidate.source_lineage_roots
        ):
            raise IntegratedInquiryError(
                "DependencyGap detector output lost its canonical mutation lineage."
            )

    @staticmethod
    def _representative_outcomes(
        hypotheses: tuple[StructuralHypothesis, ...],
        partition: FunctionalPartitionIndex,
    ) -> tuple[FunctionalOutcome, ...]:
        outcomes = {
            outcome.outcome_id: outcome
            for hypothesis in hypotheses
            for outcome in hypothesis.outcomes
        }
        representatives = tuple(
            outcomes[item.member_outcome_ids[0]]
            for item in partition.equivalence_classes
        )
        return tuple(
            sorted(
                representatives,
                key=lambda item: (
                    _OUTCOME_PRIORITY[item.kind],
                    item.outcome_id,
                ),
            )
        )

    def run(
        self,
        kernel: VerdantKernel,
        runtime: CounterfactualRuntime,
        *,
        source_event_key: str,
    ) -> IntegratedInquiryResult:
        """Stage and publish one bounded invocation, or leave both inputs unchanged."""

        if not source_event_key.strip():
            raise IntegratedInquiryError("Integrated inquiry requires a source event key.")

        working_kernel = VerdantKernel.from_state(kernel.snapshot())
        working_runtime = CounterfactualRuntime(
            ledger=SimulationLedger.from_state(runtime.ledger.snapshot())
        )
        detection = self.detector.detect_and_record(working_kernel)
        if not detection.candidates:
            raise IntegratedInquiryError(
                "Integrated inquiry found no DependencyGap detector candidate."
            )
        if len(detection.candidates) != len(detection.mutations):
            raise IntegratedInquiryError("Detector candidate/mutation coverage is incomplete.")

        candidate_by_obligation: dict[str, DependencyGapCandidate] = {}
        mutation_by_obligation: dict[str, ObligationMutationResult] = {}
        for candidate, mutation in zip(
            detection.candidates,
            detection.mutations,
            strict=True,
        ):
            self._validate_detection_link(candidate, mutation)
            obligation_id = mutation.obligation.kernel_id
            if obligation_id in candidate_by_obligation:
                raise IntegratedInquiryError(
                    "Detector candidates collapsed onto one obligation identity."
                )
            candidate_by_obligation[obligation_id] = candidate
            mutation_by_obligation[obligation_id] = mutation

        eligible_ids = tuple(
            sorted(
                obligation_id
                for obligation_id in working_kernel.state.obligation_kernels
                if derive_obligation_view(
                    working_kernel, obligation_id
                ).current_status in self.attention.ELIGIBLE_STATUSES
            )
        )
        if set(eligible_ids) != set(candidate_by_obligation):
            raise IntegratedInquiryError(
                "Opt-in v0.22 requires the detector candidates to be exactly the "
                "eligible obligation set."
            )
        if any(
            working_kernel.state.obligation_kernels[item].family
            != ObligationFamily.DEPENDENCY_GAP
            for item in eligible_ids
        ):
            raise IntegratedInquiryError(
                "Opt-in v0.22 supports only DependencyGap obligations."
            )

        hypotheses_by_obligation: dict[str, tuple[StructuralHypothesis, ...]] = {}
        partitions_by_obligation: dict[str, FunctionalPartitionIndex] = {}
        bid_inputs: list[AttentionBidInput] = []
        for obligation_id in eligible_ids:
            hypotheses = self.generator.generate(working_kernel, obligation_id)
            if not hypotheses or any(
                item.obligation_id != obligation_id for item in hypotheses
            ):
                raise IntegratedInquiryError(
                    "Hypothesis generation lost its obligation boundary."
                )
            partition = FunctionalPartitionIndex.build(obligation_id, hypotheses)
            hypotheses_by_obligation[obligation_id] = hypotheses
            partitions_by_obligation[obligation_id] = partition
            candidate = candidate_by_obligation[obligation_id]
            mutation = mutation_by_obligation[obligation_id]
            provenance = tuple(
                sorted(
                    {
                        candidate.candidate_id,
                        mutation.event.event_id,
                        partition.partition_id,
                        *(item.hypothesis_id for item in hypotheses),
                    }
                )
            )
            bid_inputs.append(
                AttentionBidInput(
                    obligation_id=obligation_id,
                    action_operator="integrated_dependency_gap_probe",
                    requested_budget=self.policy.attention_requested_budget,
                    estimated_cost=self.policy.attention_estimated_cost,
                    expected_gain=self.policy.expected_gain,
                    uncertainty=self.policy.uncertainty,
                    urgency=self.policy.urgency,
                    novelty=self.policy.novelty,
                    metric_provenance_refs=provenance,
                    generator_version=self.generator.policy.policy_version,
                )
            )

        attention_source_key = stable_id(
            "integrated_inquiry_attention",
            source_event_key,
            self.policy.policy_version,
            self.detector.policy.policy_version,
            self.attention.policy.policy_version,
            self.generator.policy.policy_version,
        )
        attention = self.attention.decide(
            working_kernel,
            tuple(bid_inputs),
            source_event_key=attention_source_key,
        )
        decision = attention.decision
        canonical_checkpoint = working_kernel.fingerprint()

        hypothesis_by_id = {
            item.hypothesis_id: item
            for hypotheses in hypotheses_by_obligation.values()
            for item in hypotheses
        }
        plans: list[CounterfactualPlan] = []
        simulations: list[CounterfactualRunResult] = []
        trials: list[IntegratedInquiryTrial] = []
        matched_pairs: list[IntegratedMatchedInquiryPair] = []
        for allocation in decision.allocations:
            obligation_id = allocation.obligation_id
            hypotheses = hypotheses_by_obligation[obligation_id]
            partition = partitions_by_obligation[obligation_id]
            representatives = self._representative_outcomes(hypotheses, partition)
            affordable = math.floor(
                (allocation.granted_budget + 1e-12)
                / self.policy.simulation_requested_budget
            )
            arm_capacity = affordable - MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION
            trial_count = min(
                self.policy.maximum_simulations_per_obligation,
                arm_capacity,
                len(representatives),
            )
            if trial_count < 1:
                raise IntegratedInquiryError(
                    "Attention allocation cannot fund one declared simulation plus "
                    "the matched control pair."
                )
            projected = tuple(
                sorted(
                    (
                        item
                        for item in hypotheses
                        if item.operator
                        == HypothesisOperator.EVIDENCE_PATH_PROJECTION
                        and item.patches
                    ),
                    key=lambda item: item.hypothesis_id,
                )
            )
            if not projected:
                raise IntegratedInquiryError(
                    "Matched inquiry requires one patch-bearing evidence-path "
                    "hypothesis."
                )
            requested = (
                trial_count + MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION
            ) * self.policy.simulation_requested_budget
            if requested > allocation.granted_budget + 1e-12:
                raise IntegratedInquiryError(
                    "Integrated inquiry plans exceed their Attention allocation."
                )

            matched_hypothesis = projected[0]
            matched_plans = build_matched_counterfactual_plans(
                matched_hypothesis,
                source_event_key=stable_id(
                    "integrated_inquiry_matched_pair",
                    source_event_key,
                    obligation_id,
                    matched_hypothesis.hypothesis_id,
                    self.policy.policy_version,
                ),
                requested_budget=self.policy.simulation_requested_budget,
                consumed_budget=self.policy.simulation_consumed_budget,
            )
            if any(
                (
                    plan.operator_version != matched_hypothesis.grammar_version
                    or plan.patches != matched_hypothesis.patches
                    or abs(
                        plan.requested_budget
                        - self.policy.simulation_requested_budget
                    )
                    > 1e-12
                    or abs(
                        plan.consumed_budget
                        - self.policy.simulation_consumed_budget
                    )
                    > 1e-12
                    or plan.disposition != SimulationDisposition.DISCARDED
                    or plan.result_refs != (matched_hypothesis.hypothesis_id,)
                )
                for plan in (
                    matched_plans.baseline,
                    matched_plans.treatment,
                )
            ) or (
                matched_plans.baseline.apply_patch_count != 0
                or matched_plans.treatment.apply_patch_count
                != len(matched_hypothesis.patches)
            ):
                raise IntegratedInquiryError(
                    "Matched plans differ from their declared hypothesis or policy."
                )
            matched_baseline = working_runtime.execute(
                working_kernel,
                allocation_id=allocation.allocation_id,
                plan=matched_plans.baseline,
            )
            if working_kernel.fingerprint() != canonical_checkpoint:
                raise IntegratedInquiryError(
                    "Counterfactual execution changed canonical state."
                )
            matched_treatment = working_runtime.execute(
                working_kernel,
                allocation_id=allocation.allocation_id,
                plan=matched_plans.treatment,
            )
            if working_kernel.fingerprint() != canonical_checkpoint:
                raise IntegratedInquiryError(
                    "Counterfactual execution changed canonical state."
                )
            try:
                observation = self.matched_observer.observe(
                    working_kernel,
                    working_runtime.ledger,
                    hypothesis_ref=matched_hypothesis.hypothesis_id,
                    baseline_plan=matched_plans.baseline,
                    baseline_result=matched_baseline,
                    treatment_plan=matched_plans.treatment,
                    treatment_result=matched_treatment,
                )
                observation = MatchedStructuralObservation.model_validate(
                    observation.model_dump(mode="json")
                )
            except (TraceObservationIntegrityError, ValueError, TypeError) as exc:
                raise IntegratedInquiryError(
                    f"Matched structural observation failed validation: {exc}"
                ) from exc
            expected_observation = MatchedStructuralObservation.build(
                hypothesis_ref=matched_hypothesis.hypothesis_id,
                baseline=matched_baseline.trace,
                treatment=matched_treatment.trace,
            )
            if observation != expected_observation:
                raise IntegratedInquiryError(
                    "Matched structural observation disagrees with executed traces."
                )
            for matched_plan, matched_simulation in (
                (matched_plans.baseline, matched_baseline),
                (matched_plans.treatment, matched_treatment),
            ):
                if (
                    matched_simulation.reservation.plan_id != matched_plan.plan_id
                    or matched_simulation.reservation.attention_decision_id
                    != decision.decision_id
                    or matched_simulation.reservation.allocation_id
                    != allocation.allocation_id
                    or matched_simulation.reservation.obligation_id != obligation_id
                    or matched_simulation.settlement.result_refs
                    != (matched_hypothesis.hypothesis_id,)
                    or not matched_simulation.settlement.canonical_unchanged
                    or matched_simulation.settlement.canonical_commit_permitted
                    or matched_simulation.settlement.epistemic_authority_enabled
                ):
                    raise IntegratedInquiryError(
                        "Matched simulation lost provenance or authority isolation."
                    )
            if not observation.canonical_records_preserved:
                raise IntegratedInquiryError(
                    "Matched treatment changed a pre-existing canonical record."
                )
            try:
                resolution_evidence = TraceResolutionEvidenceDeriver().derive(
                    working_kernel,
                    working_runtime.ledger,
                    obligation_event_ref=(
                        mutation_by_obligation[obligation_id].event.event_id
                    ),
                    hypothesis=matched_hypothesis,
                    plans=matched_plans,
                    baseline_result=matched_baseline,
                    treatment_result=matched_treatment,
                    observation=observation,
                )
            except TraceResolutionEvidenceIntegrityError as exc:
                raise IntegratedInquiryError(
                    f"Resolution evidence coverage failed validation: {exc}"
                ) from exc
            matched_pairs.append(
                IntegratedMatchedInquiryPair(
                    obligation_id=obligation_id,
                    hypothesis_id=matched_hypothesis.hypothesis_id,
                    plans=matched_plans,
                    baseline=matched_baseline,
                    treatment=matched_treatment,
                    observation=observation,
                    resolution_evidence=resolution_evidence,
                )
            )
            for outcome in representatives[:trial_count]:
                hypothesis = hypothesis_by_id[outcome.hypothesis_id]
                plan = build_hypothesis_plan(
                    hypothesis,
                    outcome,
                    source_event_key=stable_id(
                        "integrated_inquiry_simulation",
                        source_event_key,
                        obligation_id,
                        outcome.outcome_id,
                        self.policy.policy_version,
                    ),
                    requested_budget=self.policy.simulation_requested_budget,
                    consumed_budget=self.policy.simulation_consumed_budget,
                )
                simulation = working_runtime.execute(
                    working_kernel,
                    allocation_id=allocation.allocation_id,
                    plan=plan,
                )
                if working_kernel.fingerprint() != canonical_checkpoint:
                    raise IntegratedInquiryError(
                        "Counterfactual execution changed canonical state."
                    )
                expected_result_refs = tuple(
                    sorted(
                        {
                            hypothesis.hypothesis_id,
                            outcome.outcome_id,
                            outcome.equivalence_signature,
                        }
                    )
                )
                if (
                    simulation.reservation.plan_id != plan.plan_id
                    or simulation.reservation.attention_decision_id
                    != decision.decision_id
                    or simulation.reservation.allocation_id
                    != allocation.allocation_id
                    or simulation.reservation.obligation_id != obligation_id
                    or simulation.settlement.result_refs != expected_result_refs
                    or not simulation.settlement.canonical_unchanged
                    or simulation.settlement.canonical_commit_permitted
                    or simulation.settlement.epistemic_authority_enabled
                ):
                    raise IntegratedInquiryError(
                        "Integrated simulation lost provenance or authority isolation."
                    )
                candidate = candidate_by_obligation[obligation_id]
                mutation = mutation_by_obligation[obligation_id]
                trials.append(
                    IntegratedInquiryTrial.build(
                        obligation_id=obligation_id,
                        detection_candidate_id=candidate.candidate_id,
                        obligation_event_id=mutation.event.event_id,
                        hypothesis_id=hypothesis.hypothesis_id,
                        outcome_id=outcome.outcome_id,
                        equivalence_signature=outcome.equivalence_signature,
                        partition_id=partition.partition_id,
                        attention_decision_id=decision.decision_id,
                        attention_allocation_id=allocation.allocation_id,
                        plan_id=plan.plan_id,
                        reservation_id=simulation.reservation.reservation_id,
                        settlement_id=simulation.settlement.settlement_id,
                    )
                )
                plans.append(plan)
                simulations.append(simulation)

        if not trials:
            raise IntegratedInquiryError(
                "Integrated inquiry produced no isolated simulation trial."
            )
        if working_kernel.fingerprint() != canonical_checkpoint:
            raise IntegratedInquiryError("Integrated inquiry leaked into canonical state.")

        hypotheses = tuple(
            sorted(hypothesis_by_id.values(), key=lambda item: item.hypothesis_id)
        )
        partitions = tuple(
            sorted(
                partitions_by_obligation.values(),
                key=lambda item: item.partition_id,
            )
        )
        trace = IntegratedInquiryTrace.build(
            source_event_key=source_event_key,
            policy_version=self.policy.policy_version,
            policy_sha256=_digest(self.policy.model_dump(mode="json")),
            detector_policy_version=self.detector.policy.policy_version,
            detector_policy_sha256=_digest(
                self.detector.policy.model_dump(mode="json")
            ),
            attention_policy_version=self.attention.policy.policy_version,
            attention_policy_sha256=_digest(
                self.attention.policy.model_dump(mode="json")
            ),
            hypothesis_policy_version=self.generator.policy.policy_version,
            hypothesis_policy_sha256=_digest(
                self.generator.policy.model_dump(mode="json")
            ),
            detection_candidate_ids=tuple(
                item.candidate_id for item in detection.candidates
            ),
            obligation_ids=eligible_ids,
            obligation_event_ids=tuple(
                item.event.event_id for item in detection.mutations
            ),
            hypothesis_ids=tuple(item.hypothesis_id for item in hypotheses),
            partition_ids=tuple(item.partition_id for item in partitions),
            attention_decision_id=decision.decision_id,
            attention_bid_ids=tuple(item.bid_id for item in decision.bids),
            attention_allocation_ids=tuple(
                item.allocation_id for item in decision.allocations
            ),
            deferred_bid_ids=decision.deferred_bid_ids,
            trials=tuple(trials),
            matched_observations=tuple(
                item.observation for item in matched_pairs
            ),
            resolution_evidence_receipts=tuple(
                item.resolution_evidence for item in matched_pairs
            ),
            canonical_checkpoint_fingerprint=canonical_checkpoint,
            simulation_ledger_fingerprint=working_runtime.ledger.fingerprint(),
        )

        replayed = (
            all(item.replayed for item in detection.mutations)
            and attention.replayed
            and all(item.replayed for item in simulations)
            and all(item.replayed for item in matched_pairs)
        )
        kernel.state = working_kernel.snapshot()
        runtime.ledger.state = working_runtime.ledger.snapshot()
        return IntegratedInquiryResult(
            trace=trace,
            detection=detection,
            hypotheses=hypotheses,
            partitions=partitions,
            attention=attention,
            plans=tuple(plans),
            simulations=tuple(simulations),
            matched_pairs=tuple(matched_pairs),
            replayed=replayed,
        )
