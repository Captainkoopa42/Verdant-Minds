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
from .equivalence import (
    EquivalenceLensSystem,
    LensIntegrityError,
    LensUnavailableError,
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
from .operational_probe import (
    MatchedOverlayOperationalObservation,
    OperationalProbeIntegrityError,
    OverlayOperationalProbe,
    OverlayOperationalProbePolicy,
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
from .trial_controls import (
    ControlledOperationalTrialObservation,
    ControlledOperationalTrialObserver,
    HeldOutOperationalReplicationObserver,
    HeldOutOperationalReplicationReceipt,
    OperationalTrialContext,
    OperationalTrialControlIntegrityError,
    OperationalTrialSplit,
    build_operational_trial_context,
)
from .workspace_admission import (
    HeldOutWorkspaceAdmissionReplicationObserver,
    HeldOutWorkspaceAdmissionReplicationReceipt,
    MatchedWorkspaceAdmissionObservation,
    NativeWorkspaceAdmissionObserver,
    WorkspaceAdmissionProbeIntegrityError,
)
from .outgoing_action import (
    HeldOutOutgoingActionReplicationObserver,
    HeldOutOutgoingActionReplicationReceipt,
    MatchedOutgoingActionObservation,
    NativeOutgoingActionObserver,
    OutgoingActionProbeIntegrityError,
)


INTEGRATED_INQUIRY_POLICY_VERSION = "dependency_gap_integrated_inquiry_v0.26"
INTEGRATED_CONTROLLED_INQUIRY_VERSION = (
    "dependency_gap_integrated_trial_controls_v0.28"
)
MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION = 2
CONTROLLED_MATCHED_SIMULATIONS_PER_OBLIGATION = 4


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


class IntegratedInquiryTrialControlRequest(FrozenRecord):
    """Pre-Attention commitment to one calibration and one held-out pair."""

    request_id: str
    policy_version: str = INTEGRATED_CONTROLLED_INQUIRY_VERSION
    calibration_seed: int = Field(ge=0)
    held_out_seed: int = Field(ge=0)
    horizon: int = Field(ge=1, le=32)
    slot_budget: int = Field(ge=1, le=4096)
    obligation_family: ObligationFamily = ObligationFamily.DEPENDENCY_GAP
    lens_binding_id: str
    lens_definition_id: str
    lens_policy_version: str
    lens_state_fingerprint: str
    matched_pair_count: int = 2
    counterfactual_arm_count: int = 4
    predeclared: bool = True
    seed_consumed_by_runtime: bool = False
    native_workspace_budget_enforced: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        lenses: EquivalenceLensSystem,
        *,
        calibration_seed: int,
        held_out_seed: int,
        horizon: int,
        slot_budget: int,
    ) -> "IntegratedInquiryTrialControlRequest":
        try:
            active = lenses.active_binding(
                ObligationFamily.DEPENDENCY_GAP
            ).binding
        except (LensIntegrityError, LensUnavailableError) as exc:
            raise IntegratedInquiryError(str(exc)) from exc
        values = {
            "policy_version": INTEGRATED_CONTROLLED_INQUIRY_VERSION,
            "calibration_seed": calibration_seed,
            "held_out_seed": held_out_seed,
            "horizon": horizon,
            "slot_budget": slot_budget,
            "obligation_family": ObligationFamily.DEPENDENCY_GAP,
            "lens_binding_id": active.binding_id,
            "lens_definition_id": active.definition_id,
            "lens_policy_version": active.policy_version,
            "lens_state_fingerprint": lenses.fingerprint(),
            "matched_pair_count": 2,
            "counterfactual_arm_count": 4,
            "predeclared": True,
            "seed_consumed_by_runtime": False,
            "native_workspace_budget_enforced": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["request_id"] = stable_id(
            "integrated_inquiry_trial_control_request",
            _identity_payload(values, "request_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_request(self) -> "IntegratedInquiryTrialControlRequest":
        if self.policy_version != INTEGRATED_CONTROLLED_INQUIRY_VERSION:
            raise ValueError("Unsupported integrated trial-control version.")
        if self.calibration_seed == self.held_out_seed:
            raise ValueError(
                "Integrated calibration and held-out seeds must be distinct."
            )
        if self.obligation_family != ObligationFamily.DEPENDENCY_GAP:
            raise ValueError(
                "Integrated trial controls currently support only DependencyGap."
            )
        if not all(
            item.strip()
            for item in (
                self.lens_binding_id,
                self.lens_definition_id,
                self.lens_policy_version,
            )
        ):
            raise ValueError("Integrated trial-control Lens refs cannot be empty.")
        if len(self.lens_state_fingerprint) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.lens_state_fingerprint
        ):
            raise ValueError(
                "Integrated trial-control Lens fingerprint must be SHA-256."
            )
        if self.matched_pair_count != 2 or self.counterfactual_arm_count != 4:
            raise ValueError(
                "Integrated controls require exactly two zero/full matched pairs."
            )
        if (
            not self.predeclared
            or self.seed_consumed_by_runtime
            or self.native_workspace_budget_enforced
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Integrated trial controls crossed their claim boundary.")
        expected = stable_id(
            "integrated_inquiry_trial_control_request",
            self.model_dump(mode="json", exclude={"request_id"}),
        )
        if self.request_id != expected:
            raise ValueError("Integrated trial-control request checksum mismatch.")
        return self


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
    operational_probe_observations: tuple[
        MatchedOverlayOperationalObservation, ...
    ] = Field(min_length=1)
    resolution_evidence_receipts: tuple[
        TraceResolutionEvidenceReceipt, ...
    ] = Field(min_length=1)
    canonical_checkpoint_fingerprint: str
    simulation_ledger_fingerprint: str
    trial_control_request: IntegratedInquiryTrialControlRequest | None = None
    controlled_trial_observations: tuple[
        ControlledOperationalTrialObservation, ...
    ] = ()
    held_out_replication_receipts: tuple[
        HeldOutOperationalReplicationReceipt, ...
    ] = ()
    workspace_admission_observations: tuple[
        MatchedWorkspaceAdmissionObservation, ...
    ] = ()
    held_out_workspace_admission_receipts: tuple[
        HeldOutWorkspaceAdmissionReplicationReceipt, ...
    ] = ()
    outgoing_action_observations: tuple[
        MatchedOutgoingActionObservation, ...
    ] = ()
    held_out_outgoing_action_receipts: tuple[
        HeldOutOutgoingActionReplicationReceipt, ...
    ] = ()
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
        operational_observations = tuple(
            item
            if isinstance(item, MatchedOverlayOperationalObservation)
            else MatchedOverlayOperationalObservation.model_validate(item)
            for item in values["operational_probe_observations"]
        )
        values["operational_probe_observations"] = tuple(
            sorted(operational_observations, key=lambda item: item.match_id)
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
        if values.get("trial_control_request") is not None:
            request = values["trial_control_request"]
            values["trial_control_request"] = (
                request
                if isinstance(request, IntegratedInquiryTrialControlRequest)
                else IntegratedInquiryTrialControlRequest.model_validate(request)
            )
        controlled = tuple(
            item
            if isinstance(item, ControlledOperationalTrialObservation)
            else ControlledOperationalTrialObservation.model_validate(item)
            for item in values.get("controlled_trial_observations", ())
        )
        values["controlled_trial_observations"] = tuple(
            sorted(controlled, key=lambda item: item.observation_id)
        )
        replications = tuple(
            item
            if isinstance(item, HeldOutOperationalReplicationReceipt)
            else HeldOutOperationalReplicationReceipt.model_validate(item)
            for item in values.get("held_out_replication_receipts", ())
        )
        values["held_out_replication_receipts"] = tuple(
            sorted(replications, key=lambda item: item.receipt_id)
        )
        workspace_observations = tuple(
            item
            if isinstance(item, MatchedWorkspaceAdmissionObservation)
            else MatchedWorkspaceAdmissionObservation.model_validate(item)
            for item in values.get("workspace_admission_observations", ())
        )
        values["workspace_admission_observations"] = tuple(
            sorted(workspace_observations, key=lambda item: item.match_id)
        )
        workspace_replications = tuple(
            item
            if isinstance(item, HeldOutWorkspaceAdmissionReplicationReceipt)
            else HeldOutWorkspaceAdmissionReplicationReceipt.model_validate(item)
            for item in values.get("held_out_workspace_admission_receipts", ())
        )
        values["held_out_workspace_admission_receipts"] = tuple(
            sorted(workspace_replications, key=lambda item: item.receipt_id)
        )
        action_observations = tuple(
            item
            if isinstance(item, MatchedOutgoingActionObservation)
            else MatchedOutgoingActionObservation.model_validate(item)
            for item in values.get("outgoing_action_observations", ())
        )
        values["outgoing_action_observations"] = tuple(
            sorted(action_observations, key=lambda item: item.match_id)
        )
        action_replications = tuple(
            item
            if isinstance(item, HeldOutOutgoingActionReplicationReceipt)
            else HeldOutOutgoingActionReplicationReceipt.model_validate(item)
            for item in values.get("held_out_outgoing_action_receipts", ())
        )
        values["held_out_outgoing_action_receipts"] = tuple(
            sorted(action_replications, key=lambda item: item.receipt_id)
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
        operational_ids = tuple(
            item.match_id for item in self.operational_probe_observations
        )
        if tuple(sorted(set(operational_ids))) != operational_ids:
            raise ValueError(
                "Integrated operational observations must be sorted and unique."
            )
        receipt_ids = tuple(
            item.receipt_id for item in self.resolution_evidence_receipts
        )
        if tuple(sorted(set(receipt_ids))) != receipt_ids:
            raise ValueError(
                "Integrated resolution evidence receipts must be sorted and unique."
            )
        controlled_ids = tuple(
            item.observation_id for item in self.controlled_trial_observations
        )
        if tuple(sorted(set(controlled_ids))) != controlled_ids:
            raise ValueError(
                "Integrated controlled observations must be sorted and unique."
            )
        replication_ids = tuple(
            item.receipt_id for item in self.held_out_replication_receipts
        )
        if tuple(sorted(set(replication_ids))) != replication_ids:
            raise ValueError(
                "Integrated held-out receipts must be sorted and unique."
            )
        workspace_observation_ids = tuple(
            item.match_id for item in self.workspace_admission_observations
        )
        if tuple(sorted(set(workspace_observation_ids))) != workspace_observation_ids:
            raise ValueError(
                "Integrated workspace observations must be sorted and unique."
            )
        workspace_replication_ids = tuple(
            item.receipt_id
            for item in self.held_out_workspace_admission_receipts
        )
        if (
            tuple(sorted(set(workspace_replication_ids)))
            != workspace_replication_ids
        ):
            raise ValueError(
                "Integrated workspace replications must be sorted and unique."
            )
        action_observation_ids = tuple(
            item.match_id for item in self.outgoing_action_observations
        )
        if tuple(sorted(set(action_observation_ids))) != action_observation_ids:
            raise ValueError(
                "Integrated outgoing-action observations must be sorted and unique."
            )
        action_replication_ids = tuple(
            item.receipt_id for item in self.held_out_outgoing_action_receipts
        )
        if tuple(sorted(set(action_replication_ids))) != action_replication_ids:
            raise ValueError(
                "Integrated outgoing-action replications must be sorted and unique."
            )
        if self.trial_control_request is None:
            if (
                self.controlled_trial_observations
                or self.held_out_replication_receipts
                or self.workspace_admission_observations
                or self.held_out_workspace_admission_receipts
                or self.outgoing_action_observations
                or self.held_out_outgoing_action_receipts
            ):
                raise ValueError(
                    "Integrated controlled evidence requires a predeclared request."
                )
        elif (
            not self.controlled_trial_observations
            or not self.held_out_replication_receipts
            or not self.workspace_admission_observations
            or not self.held_out_workspace_admission_receipts
            or not self.outgoing_action_observations
            or not self.held_out_outgoing_action_receipts
        ):
            raise ValueError(
                "Integrated trial controls require complete controlled evidence."
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
        controlled_by_structural_ref: dict[
            str, ControlledOperationalTrialObservation
        ] = {}
        for controlled in self.controlled_trial_observations:
            structural_ref = controlled.structural_observation.observation_id
            if structural_ref in controlled_by_structural_ref:
                raise ValueError(
                    "Matched structural observation has multiple controlled receipts."
                )
            controlled_by_structural_ref[structural_ref] = controlled

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
            controlled = controlled_by_structural_ref.get(
                observation.observation_id
            )
            expected_result_refs = (
                tuple(
                    sorted(
                        (
                            observation.hypothesis_ref,
                            controlled.context.context_id,
                        )
                    )
                )
                if controlled is not None
                else (observation.hypothesis_ref,)
            )
            if (
                baseline.result_refs != expected_result_refs
                or treatment.result_refs != expected_result_refs
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
        expected_matches_per_allocation = (
            2 if self.trial_control_request is not None else 1
        )
        observed_allocation_ids = set(observed_allocations)
        if observed_allocation_ids != set(self.attention_allocation_ids) or any(
            observed_allocations.count(allocation_id)
            != expected_matches_per_allocation
            for allocation_id in self.attention_allocation_ids
        ):
            raise ValueError(
                "Every integrated Attention allocation requires its declared matched receipts."
            )
        if set(controlled_by_structural_ref) != (
            set(observation_ids)
            if self.trial_control_request is not None
            else set()
        ):
            raise ValueError(
                "Integrated controlled receipts do not cover the matched observations."
            )
        observations_by_id = {
            item.observation_id: item for item in self.matched_observations
        }
        operational_by_structural_ref: dict[
            str, MatchedOverlayOperationalObservation
        ] = {}
        for operational in self.operational_probe_observations:
            structural = observations_by_id.get(
                operational.structural_observation_ref
            )
            if structural is None:
                raise ValueError(
                    "Operational probe lost its matched structural observation."
                )
            if operational.structural_observation_ref in operational_by_structural_ref:
                raise ValueError(
                    "Matched structural observation has multiple operational probes."
                )
            if (
                operational.baseline.obligation_id
                != structural.baseline.obligation_id
                or operational.treatment.obligation_id
                != structural.treatment.obligation_id
                or operational.baseline.hypothesis_ref
                != structural.hypothesis_ref
                or operational.treatment.hypothesis_ref
                != structural.hypothesis_ref
                or operational.baseline.structural_trace_ref
                != structural.baseline.trace_id
                or operational.treatment.structural_trace_ref
                != structural.treatment.trace_id
                or operational.baseline.settlement_id
                != structural.baseline.settlement_id
                or operational.treatment.settlement_id
                != structural.treatment.settlement_id
                or operational.baseline.canonical_checkpoint_fingerprint
                != self.canonical_checkpoint_fingerprint
                or operational.treatment.canonical_checkpoint_fingerprint
                != self.canonical_checkpoint_fingerprint
            ):
                raise ValueError(
                    "Operational probe crossed its matched structural lineage."
                )
            operational_by_structural_ref[
                operational.structural_observation_ref
            ] = operational
        if tuple(sorted(operational_by_structural_ref)) != observation_ids:
            raise ValueError(
                "Every matched observation requires one operational probe."
            )
        request = self.trial_control_request
        if request is not None:
            controlled_by_allocation: dict[
                str, list[ControlledOperationalTrialObservation]
            ] = {}
            for structural_ref, controlled in controlled_by_structural_ref.items():
                structural = observations_by_id[structural_ref]
                operational = operational_by_structural_ref[structural_ref]
                context = controlled.context
                if (
                    controlled.structural_observation != structural
                    or controlled.operational_observation != operational
                    or context.obligation_id != structural.baseline.obligation_id
                    or context.hypothesis_ref != structural.hypothesis_ref
                    or context.canonical_checkpoint_fingerprint
                    != self.canonical_checkpoint_fingerprint
                    or context.obligation_family != request.obligation_family
                    or context.lens_binding_id != request.lens_binding_id
                    or context.lens_definition_id != request.lens_definition_id
                    or context.lens_policy_version != request.lens_policy_version
                    or context.lens_state_fingerprint
                    != request.lens_state_fingerprint
                    or context.horizon != request.horizon
                    or context.slot_budget != request.slot_budget
                ):
                    raise ValueError(
                        "Controlled trial crossed its integrated request lineage."
                    )
                expected_seed = (
                    request.calibration_seed
                    if context.split == OperationalTrialSplit.CALIBRATION
                    else request.held_out_seed
                )
                if context.seed != expected_seed:
                    raise ValueError(
                        "Controlled trial crossed its predeclared split seed."
                    )
                allocation_id = structural.baseline.allocation_id
                controlled_by_allocation.setdefault(allocation_id, []).append(
                    controlled
                )

            replication_by_allocation: dict[
                str, HeldOutOperationalReplicationReceipt
            ] = {}
            for replication in self.held_out_replication_receipts:
                allocation_ids = {
                    item.structural_observation.baseline.allocation_id
                    for item in replication.trials
                }
                if len(allocation_ids) != 1:
                    raise ValueError(
                        "Held-out replication crossed an Attention allocation."
                    )
                allocation_id = next(iter(allocation_ids))
                if allocation_id in replication_by_allocation:
                    raise ValueError(
                        "Attention allocation has multiple held-out receipts."
                    )
                expected_trials = tuple(
                    sorted(
                        controlled_by_allocation.get(allocation_id, ()),
                        key=lambda item: (
                            0
                            if item.context.split
                            == OperationalTrialSplit.CALIBRATION
                            else 1,
                            item.context.seed,
                            item.observation_id,
                        ),
                    )
                )
                if replication.trials != expected_trials:
                    raise ValueError(
                        "Held-out replication lost its controlled trial set."
                    )
                replication_by_allocation[allocation_id] = replication
            if set(replication_by_allocation) != set(
                self.attention_allocation_ids
            ):
                raise ValueError(
                    "Every controlled allocation requires one held-out receipt."
                )
            controlled_by_id = {
                item.observation_id: item
                for item in self.controlled_trial_observations
            }
            workspace_by_controlled: dict[
                str, MatchedWorkspaceAdmissionObservation
            ] = {}
            for workspace in self.workspace_admission_observations:
                controlled = controlled_by_id.get(workspace.controlled_trial_ref)
                if controlled is None:
                    raise ValueError(
                        "Workspace admission lost its controlled trial."
                    )
                if workspace.controlled_trial_ref in workspace_by_controlled:
                    raise ValueError(
                        "Controlled trial has multiple workspace observations."
                    )
                operational = controlled.operational_observation
                structural = controlled.structural_observation
                if (
                    workspace.context != controlled.context
                    or workspace.baseline.operational_probe_ref
                    != operational.baseline.observation_id
                    or workspace.treatment.operational_probe_ref
                    != operational.treatment.observation_id
                    or workspace.baseline.plan_id != structural.baseline.plan_id
                    or workspace.treatment.plan_id != structural.treatment.plan_id
                    or workspace.baseline.settlement_id
                    != structural.baseline.settlement_id
                    or workspace.treatment.settlement_id
                    != structural.treatment.settlement_id
                    or workspace.baseline.canonical_checkpoint_fingerprint
                    != self.canonical_checkpoint_fingerprint
                    or workspace.treatment.canonical_checkpoint_fingerprint
                    != self.canonical_checkpoint_fingerprint
                ):
                    raise ValueError(
                        "Workspace admission crossed controlled execution lineage."
                    )
                workspace_by_controlled[workspace.controlled_trial_ref] = workspace
            if set(workspace_by_controlled) != set(controlled_by_id):
                raise ValueError(
                    "Every controlled trial requires one workspace observation."
                )

            operational_replications_by_id = {
                item.receipt_id: item
                for item in self.held_out_replication_receipts
            }
            workspace_replication_refs: set[str] = set()
            for workspace_replication in (
                self.held_out_workspace_admission_receipts
            ):
                operational_replication = operational_replications_by_id.get(
                    workspace_replication.operational_replication_ref
                )
                if operational_replication is None:
                    raise ValueError(
                        "Workspace replication lost its operational receipt."
                    )
                if (
                    workspace_replication.operational_replication_ref
                    in workspace_replication_refs
                ):
                    raise ValueError(
                        "Operational receipt has multiple workspace replications."
                    )
                expected_workspace = tuple(
                    sorted(
                        (
                            workspace_by_controlled[item.observation_id]
                            for item in operational_replication.trials
                        ),
                        key=lambda item: (
                            0
                            if item.context.split
                            == OperationalTrialSplit.CALIBRATION
                            else 1,
                            item.context.seed,
                            item.match_id,
                        ),
                    )
                )
                if workspace_replication.observations != expected_workspace:
                    raise ValueError(
                        "Workspace replication lost its controlled observation set."
                    )
                workspace_replication_refs.add(
                    workspace_replication.operational_replication_ref
                )
            if workspace_replication_refs != set(
                operational_replications_by_id
            ):
                raise ValueError(
                    "Every held-out receipt requires one workspace replication."
                )

            action_by_workspace: dict[str, MatchedOutgoingActionObservation] = {}
            for action in self.outgoing_action_observations:
                workspace = workspace_by_controlled.get(
                    action.controlled_trial_ref
                )
                if workspace is None or action.workspace_admission != workspace:
                    raise ValueError(
                        "Outgoing action lost its exact workspace observation."
                    )
                if workspace.match_id in action_by_workspace:
                    raise ValueError(
                        "Workspace observation has multiple outgoing-action receipts."
                    )
                if (
                    action.context != workspace.context
                    or action.baseline.canonical_checkpoint_fingerprint
                    != self.canonical_checkpoint_fingerprint
                    or action.treatment.canonical_checkpoint_fingerprint
                    != self.canonical_checkpoint_fingerprint
                ):
                    raise ValueError(
                        "Outgoing action crossed controlled execution lineage."
                    )
                action_by_workspace[workspace.match_id] = action
            if set(action_by_workspace) != {
                item.match_id for item in self.workspace_admission_observations
            }:
                raise ValueError(
                    "Every workspace observation requires one outgoing-action receipt."
                )

            workspace_replications_by_id = {
                item.receipt_id: item
                for item in self.held_out_workspace_admission_receipts
            }
            action_replication_refs: set[str] = set()
            for action_replication in self.held_out_outgoing_action_receipts:
                workspace_replication = workspace_replications_by_id.get(
                    action_replication.workspace_replication_ref
                )
                if workspace_replication is None:
                    raise ValueError(
                        "Outgoing-action replication lost its workspace receipt."
                    )
                if (
                    action_replication.workspace_replication_ref
                    in action_replication_refs
                ):
                    raise ValueError(
                        "Workspace replication has multiple action replications."
                    )
                expected_actions = tuple(
                    action_by_workspace[item.match_id]
                    for item in workspace_replication.observations
                )
                if (
                    action_replication.operational_replication_ref
                    != workspace_replication.operational_replication_ref
                    or action_replication.observations != expected_actions
                ):
                    raise ValueError(
                        "Outgoing-action replication lost its controlled action set."
                    )
                action_replication_refs.add(
                    action_replication.workspace_replication_ref
                )
            if action_replication_refs != set(workspace_replications_by_id):
                raise ValueError(
                    "Every workspace replication requires one action replication."
                )
        receipt_observation_refs: list[str] = []
        for receipt in self.resolution_evidence_receipts:
            observation = observations_by_id.get(receipt.matched_observation_ref)
            if observation is None:
                raise ValueError(
                    "Resolution evidence receipt lost its matched observation."
                )
            operational = operational_by_structural_ref[
                receipt.matched_observation_ref
            ]
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
                or receipt.matched_operational_probe_ref != operational.match_id
                or receipt.baseline_operational_probe_ref
                != operational.baseline.observation_id
                or receipt.treatment_operational_probe_ref
                != operational.treatment.observation_id
                or receipt.overlay_access_effect != operational.effect
                or receipt.overlay_newly_retrieved_evidence_refs
                != operational.newly_retrieved_evidence_refs
                or receipt.overlay_treatment_path_node_refs
                != operational.treatment.traversed_node_refs
                or receipt.overlay_treatment_path_relation_refs
                != operational.treatment.traversed_relation_refs
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
    operational_observation: MatchedOverlayOperationalObservation
    resolution_evidence: TraceResolutionEvidenceReceipt
    context: OperationalTrialContext | None = None
    controlled_observation: ControlledOperationalTrialObservation | None = None
    workspace_admission_observation: (
        MatchedWorkspaceAdmissionObservation | None
    ) = None
    outgoing_action_observation: MatchedOutgoingActionObservation | None = None

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
    held_out_replications: tuple[HeldOutOperationalReplicationReceipt, ...]
    held_out_workspace_admission_replications: tuple[
        HeldOutWorkspaceAdmissionReplicationReceipt, ...
    ]
    held_out_outgoing_action_replications: tuple[
        HeldOutOutgoingActionReplicationReceipt, ...
    ]
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
        operational_probe: OverlayOperationalProbe | None = None,
        controlled_trial_observer: ControlledOperationalTrialObserver | None = None,
        held_out_replication_observer: HeldOutOperationalReplicationObserver
        | None = None,
        workspace_admission_observer: NativeWorkspaceAdmissionObserver
        | None = None,
        held_out_workspace_admission_observer: (
            HeldOutWorkspaceAdmissionReplicationObserver | None
        ) = None,
        outgoing_action_observer: NativeOutgoingActionObserver | None = None,
        held_out_outgoing_action_observer: (
            HeldOutOutgoingActionReplicationObserver | None
        ) = None,
    ) -> None:
        self.policy = policy or IntegratedInquiryPolicy()
        self.detector = detector or DependencyGapDetector()
        self.attention = attention or AttentionPortfolio()
        self.generator = generator or DependencyGapHypothesisGenerator()
        self.matched_observer = matched_observer or MatchedCounterfactualObserver()
        self.operational_probe = operational_probe or OverlayOperationalProbe()
        self.controlled_trial_observer = (
            controlled_trial_observer or ControlledOperationalTrialObserver()
        )
        self.held_out_replication_observer = (
            held_out_replication_observer
            or HeldOutOperationalReplicationObserver()
        )
        self.workspace_admission_observer = (
            workspace_admission_observer or NativeWorkspaceAdmissionObserver()
        )
        self.held_out_workspace_admission_observer = (
            held_out_workspace_admission_observer
            or HeldOutWorkspaceAdmissionReplicationObserver()
        )
        self.outgoing_action_observer = (
            outgoing_action_observer or NativeOutgoingActionObserver()
        )
        self.held_out_outgoing_action_observer = (
            held_out_outgoing_action_observer
            or HeldOutOutgoingActionReplicationObserver()
        )
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
        lenses: EquivalenceLensSystem | None = None,
        trial_controls: IntegratedInquiryTrialControlRequest | None = None,
    ) -> IntegratedInquiryResult:
        """Stage and publish one bounded invocation, or leave both inputs unchanged."""

        if not source_event_key.strip():
            raise IntegratedInquiryError("Integrated inquiry requires a source event key.")

        if (lenses is None) != (trial_controls is None):
            raise IntegratedInquiryError(
                "Controlled integrated inquiry requires both Lens state and a "
                "predeclared trial-control request."
            )
        lens_checkpoint: str | None = None
        if trial_controls is not None and lenses is not None:
            try:
                trial_controls = IntegratedInquiryTrialControlRequest.model_validate(
                    trial_controls.model_dump(mode="json")
                )
                lens_checkpoint = lenses.fingerprint()
                active = lenses.active_binding(
                    trial_controls.obligation_family
                ).binding
            except (
                LensIntegrityError,
                LensUnavailableError,
                ValueError,
                TypeError,
            ) as exc:
                raise IntegratedInquiryError(
                    f"Integrated trial controls failed validation: {exc}"
                ) from exc
            if (
                lens_checkpoint != trial_controls.lens_state_fingerprint
                or active.binding_id != trial_controls.lens_binding_id
                or active.definition_id != trial_controls.lens_definition_id
                or active.policy_version != trial_controls.lens_policy_version
            ):
                raise IntegratedInquiryError(
                    "Integrated trial controls do not name the active Lens state."
                )

        working_kernel = VerdantKernel.from_state(kernel.snapshot())
        working_runtime = CounterfactualRuntime(
            ledger=SimulationLedger.from_state(runtime.ledger.snapshot())
        )
        working_lenses: EquivalenceLensSystem | None = None
        if lenses is not None:
            lens_registry, lens_ledger = lenses.snapshot()
            working_lenses = EquivalenceLensSystem(
                registry=lens_registry,
                ledger=lens_ledger,
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
        matched_simulation_count = (
            CONTROLLED_MATCHED_SIMULATIONS_PER_OBLIGATION
            if trial_controls is not None
            else MATCHED_CONTROL_SIMULATIONS_PER_OBLIGATION
        )
        control_provenance = (
            (
                trial_controls.request_id,
                trial_controls.lens_binding_id,
                trial_controls.lens_definition_id,
                trial_controls.lens_state_fingerprint,
            )
            if trial_controls is not None
            else ()
        )
        attention_requested_budget = (
            self.policy.maximum_simulations_per_obligation
            + matched_simulation_count
        ) * self.policy.simulation_requested_budget
        attention_estimated_cost = (
            self.policy.maximum_simulations_per_obligation
            + matched_simulation_count
        ) * self.policy.simulation_consumed_budget
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
                        *control_provenance,
                        *(item.hypothesis_id for item in hypotheses),
                    }
                )
            )
            bid_inputs.append(
                AttentionBidInput(
                    obligation_id=obligation_id,
                    action_operator=(
                        "integrated_dependency_gap_controlled_probe"
                        if trial_controls is not None
                        else "integrated_dependency_gap_probe"
                    ),
                    requested_budget=attention_requested_budget,
                    estimated_cost=attention_estimated_cost,
                    expected_gain=self.policy.expected_gain,
                    uncertainty=self.policy.uncertainty,
                    urgency=self.policy.urgency,
                    novelty=self.policy.novelty,
                    metric_provenance_refs=provenance,
                    generator_version=self.generator.policy.policy_version,
                )
            )

        attention_source_parts = [
            source_event_key,
            self.policy.policy_version,
            self.detector.policy.policy_version,
            self.attention.policy.policy_version,
            self.generator.policy.policy_version,
        ]
        if trial_controls is not None:
            attention_source_parts.extend(
                (trial_controls.policy_version, trial_controls.request_id)
            )
        attention_source_key = stable_id(
            "integrated_inquiry_attention",
            *attention_source_parts,
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
        held_out_replications: list[HeldOutOperationalReplicationReceipt] = []
        held_out_workspace_replications: list[
            HeldOutWorkspaceAdmissionReplicationReceipt
        ] = []
        held_out_action_replications: list[
            HeldOutOutgoingActionReplicationReceipt
        ] = []
        for allocation in decision.allocations:
            obligation_id = allocation.obligation_id
            hypotheses = hypotheses_by_obligation[obligation_id]
            partition = partitions_by_obligation[obligation_id]
            representatives = self._representative_outcomes(hypotheses, partition)
            affordable = math.floor(
                (allocation.granted_budget + 1e-12)
                / self.policy.simulation_requested_budget
            )
            arm_capacity = affordable - matched_simulation_count
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
                trial_count + matched_simulation_count
            ) * self.policy.simulation_requested_budget
            if requested > allocation.granted_budget + 1e-12:
                raise IntegratedInquiryError(
                    "Integrated inquiry plans exceed their Attention allocation."
                )

            matched_hypothesis = projected[0]
            controlled_contexts: tuple[OperationalTrialContext | None, ...]
            if trial_controls is not None:
                if working_lenses is None:
                    raise IntegratedInquiryError(
                        "Controlled inquiry lost its staged Lens state."
                    )
                try:
                    controlled_contexts = (
                        build_operational_trial_context(
                            working_kernel,
                            working_lenses,
                            hypothesis=matched_hypothesis,
                            split=OperationalTrialSplit.CALIBRATION,
                            seed=trial_controls.calibration_seed,
                            horizon=trial_controls.horizon,
                            slot_budget=trial_controls.slot_budget,
                        ),
                        build_operational_trial_context(
                            working_kernel,
                            working_lenses,
                            hypothesis=matched_hypothesis,
                            split=OperationalTrialSplit.HELD_OUT,
                            seed=trial_controls.held_out_seed,
                            horizon=trial_controls.horizon,
                            slot_budget=trial_controls.slot_budget,
                        ),
                    )
                except OperationalTrialControlIntegrityError as exc:
                    raise IntegratedInquiryError(
                        f"Integrated trial context failed validation: {exc}"
                    ) from exc
            else:
                controlled_contexts = (None,)

            allocation_controlled: list[
                ControlledOperationalTrialObservation
            ] = []
            allocation_workspace_observations: list[
                MatchedWorkspaceAdmissionObservation
            ] = []
            allocation_action_observations: list[
                MatchedOutgoingActionObservation
            ] = []
            for context in controlled_contexts:
                pair_source_key = (
                    stable_id(
                        "integrated_inquiry_matched_pair",
                        source_event_key,
                        obligation_id,
                        matched_hypothesis.hypothesis_id,
                        self.policy.policy_version,
                    )
                    if context is None
                    else stable_id(
                        "integrated_inquiry_controlled_matched_pair",
                        source_event_key,
                        obligation_id,
                        matched_hypothesis.hypothesis_id,
                        self.policy.policy_version,
                        trial_controls.request_id,
                        context.context_id,
                    )
                )
                expected_result_refs = tuple(
                    sorted(
                        (
                            matched_hypothesis.hypothesis_id,
                            *((context.context_id,) if context is not None else ()),
                        )
                    )
                )
                matched_plans = build_matched_counterfactual_plans(
                    matched_hypothesis,
                    source_event_key=pair_source_key,
                    requested_budget=self.policy.simulation_requested_budget,
                    consumed_budget=self.policy.simulation_consumed_budget,
                    additional_result_refs=(
                        (context.context_id,) if context is not None else ()
                    ),
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
                        or plan.result_refs != expected_result_refs
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

                controlled_observation: (
                    ControlledOperationalTrialObservation | None
                ) = None
                workspace_admission_observation: (
                    MatchedWorkspaceAdmissionObservation | None
                ) = None
                outgoing_action_observation: (
                    MatchedOutgoingActionObservation | None
                ) = None
                if context is not None:
                    if working_lenses is None:
                        raise IntegratedInquiryError(
                            "Controlled inquiry lost its staged Lens state."
                        )
                    try:
                        controlled_observation = (
                            self.controlled_trial_observer.observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                            )
                        )
                        controlled_observation = (
                            ControlledOperationalTrialObservation.model_validate(
                                controlled_observation.model_dump(mode="json")
                            )
                        )
                        expected_controlled = (
                            ControlledOperationalTrialObserver().observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                            )
                        )
                    except (
                        OperationalTrialControlIntegrityError,
                        ValueError,
                        TypeError,
                    ) as exc:
                        raise IntegratedInquiryError(
                            f"Controlled matched observation failed validation: {exc}"
                        ) from exc
                    if controlled_observation != expected_controlled:
                        raise IntegratedInquiryError(
                            "Controlled observer disagrees with executed lineage."
                        )
                    observation = controlled_observation.structural_observation
                    operational_observation = (
                        controlled_observation.operational_observation
                    )
                    allocation_controlled.append(controlled_observation)
                    try:
                        workspace_admission_observation = (
                            self.workspace_admission_observer.observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                                controlled_observation=controlled_observation,
                            )
                        )
                        workspace_admission_observation = (
                            MatchedWorkspaceAdmissionObservation.model_validate(
                                workspace_admission_observation.model_dump(
                                    mode="json"
                                )
                            )
                        )
                        expected_workspace_admission = (
                            NativeWorkspaceAdmissionObserver().observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                                controlled_observation=controlled_observation,
                            )
                        )
                    except (
                        WorkspaceAdmissionProbeIntegrityError,
                        ValueError,
                        TypeError,
                    ) as exc:
                        raise IntegratedInquiryError(
                            "Native workspace-admission observation failed "
                            f"validation: {exc}"
                        ) from exc
                    if (
                        workspace_admission_observation
                        != expected_workspace_admission
                    ):
                        raise IntegratedInquiryError(
                            "Workspace-admission observer disagrees with the "
                            "controlled execution."
                        )
                    allocation_workspace_observations.append(
                        workspace_admission_observation
                    )
                    try:
                        outgoing_action_observation = (
                            self.outgoing_action_observer.observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                                controlled_observation=controlled_observation,
                                workspace_observation=(
                                    workspace_admission_observation
                                ),
                            )
                        )
                        outgoing_action_observation = (
                            MatchedOutgoingActionObservation.model_validate(
                                outgoing_action_observation.model_dump(
                                    mode="json"
                                )
                            )
                        )
                        expected_outgoing_action = (
                            NativeOutgoingActionObserver().observe(
                                working_kernel,
                                working_runtime.ledger,
                                working_lenses,
                                context=context,
                                hypothesis=matched_hypothesis,
                                baseline_plan=matched_plans.baseline,
                                baseline_result=matched_baseline,
                                treatment_plan=matched_plans.treatment,
                                treatment_result=matched_treatment,
                                controlled_observation=controlled_observation,
                                workspace_observation=(
                                    workspace_admission_observation
                                ),
                            )
                        )
                    except (
                        OutgoingActionProbeIntegrityError,
                        ValueError,
                        TypeError,
                    ) as exc:
                        raise IntegratedInquiryError(
                            "Native outgoing-action observation failed "
                            f"validation: {exc}"
                        ) from exc
                    if outgoing_action_observation != expected_outgoing_action:
                        raise IntegratedInquiryError(
                            "Outgoing-action observer disagrees with the "
                            "controlled execution."
                        )
                    allocation_action_observations.append(
                        outgoing_action_observation
                    )
                else:
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
                    except (
                        TraceObservationIntegrityError,
                        ValueError,
                        TypeError,
                    ) as exc:
                        raise IntegratedInquiryError(
                            "Matched structural observation failed validation: "
                            f"{exc}"
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
                    try:
                        operational_observation = self.operational_probe.observe(
                            working_kernel,
                            working_runtime.ledger,
                            hypothesis_ref=matched_hypothesis.hypothesis_id,
                            baseline_plan=matched_plans.baseline,
                            baseline_result=matched_baseline,
                            treatment_plan=matched_plans.treatment,
                            treatment_result=matched_treatment,
                            structural_observation=observation,
                        )
                        operational_observation = (
                            MatchedOverlayOperationalObservation.model_validate(
                                operational_observation.model_dump(mode="json")
                            )
                        )
                    except (
                        OperationalProbeIntegrityError,
                        ValueError,
                        TypeError,
                    ) as exc:
                        raise IntegratedInquiryError(
                            f"Operational probe failed validation: {exc}"
                        ) from exc
                    expected_operational_observation = (
                        OverlayOperationalProbe().observe(
                            working_kernel,
                            working_runtime.ledger,
                            hypothesis_ref=matched_hypothesis.hypothesis_id,
                            baseline_plan=matched_plans.baseline,
                            baseline_result=matched_baseline,
                            treatment_plan=matched_plans.treatment,
                            treatment_result=matched_treatment,
                            structural_observation=observation,
                        )
                    )
                    if operational_observation != expected_operational_observation:
                        raise IntegratedInquiryError(
                            "Operational probe disagrees with executed overlays."
                        )

                for matched_plan, matched_simulation in (
                    (matched_plans.baseline, matched_baseline),
                    (matched_plans.treatment, matched_treatment),
                ):
                    if (
                        matched_simulation.reservation.plan_id
                        != matched_plan.plan_id
                        or matched_simulation.reservation.attention_decision_id
                        != decision.decision_id
                        or matched_simulation.reservation.allocation_id
                        != allocation.allocation_id
                        or matched_simulation.reservation.obligation_id
                        != obligation_id
                        or matched_simulation.settlement.result_refs
                        != expected_result_refs
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
                probe_policy = (
                    OverlayOperationalProbePolicy(
                        maximum_relation_hops=context.horizon
                    )
                    if context is not None
                    else None
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
                        operational_observation=operational_observation,
                        operational_probe_policy=probe_policy,
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
                        operational_observation=operational_observation,
                        resolution_evidence=resolution_evidence,
                        context=context,
                        controlled_observation=controlled_observation,
                        workspace_admission_observation=(
                            workspace_admission_observation
                        ),
                        outgoing_action_observation=(
                            outgoing_action_observation
                        ),
                    )
                )

            if trial_controls is not None:
                try:
                    replication = self.held_out_replication_observer.observe(
                        tuple(allocation_controlled)
                    )
                    replication = (
                        HeldOutOperationalReplicationReceipt.model_validate(
                            replication.model_dump(mode="json")
                        )
                    )
                    expected_replication = (
                        HeldOutOperationalReplicationObserver().observe(
                            tuple(allocation_controlled)
                        )
                    )
                except (
                    OperationalTrialControlIntegrityError,
                    ValueError,
                    TypeError,
                ) as exc:
                    raise IntegratedInquiryError(
                        f"Held-out replication failed validation: {exc}"
                    ) from exc
                if replication != expected_replication:
                    raise IntegratedInquiryError(
                        "Held-out observer disagrees with controlled trials."
                    )
                held_out_replications.append(replication)
                try:
                    workspace_replication = (
                        self.held_out_workspace_admission_observer.observe(
                            replication,
                            tuple(allocation_workspace_observations),
                        )
                    )
                    workspace_replication = (
                        HeldOutWorkspaceAdmissionReplicationReceipt.model_validate(
                            workspace_replication.model_dump(mode="json")
                        )
                    )
                    expected_workspace_replication = (
                        HeldOutWorkspaceAdmissionReplicationObserver().observe(
                            replication,
                            tuple(allocation_workspace_observations),
                        )
                    )
                except (
                    WorkspaceAdmissionProbeIntegrityError,
                    ValueError,
                    TypeError,
                ) as exc:
                    raise IntegratedInquiryError(
                        "Held-out workspace-admission replication failed "
                        f"validation: {exc}"
                    ) from exc
                if workspace_replication != expected_workspace_replication:
                    raise IntegratedInquiryError(
                        "Workspace replication observer disagrees with the "
                        "controlled trials."
                    )
                held_out_workspace_replications.append(workspace_replication)
                try:
                    action_replication = (
                        self.held_out_outgoing_action_observer.observe(
                            replication,
                            workspace_replication,
                            tuple(allocation_action_observations),
                        )
                    )
                    action_replication = (
                        HeldOutOutgoingActionReplicationReceipt.model_validate(
                            action_replication.model_dump(mode="json")
                        )
                    )
                    expected_action_replication = (
                        HeldOutOutgoingActionReplicationObserver().observe(
                            replication,
                            workspace_replication,
                            tuple(allocation_action_observations),
                        )
                    )
                except (
                    OutgoingActionProbeIntegrityError,
                    ValueError,
                    TypeError,
                ) as exc:
                    raise IntegratedInquiryError(
                        "Held-out outgoing-action replication failed "
                        f"validation: {exc}"
                    ) from exc
                if action_replication != expected_action_replication:
                    raise IntegratedInquiryError(
                        "Action replication observer disagrees with the "
                        "controlled trials."
                    )
                held_out_action_replications.append(action_replication)
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
                        *(
                            (trial_controls.request_id,)
                            if trial_controls is not None
                            else ()
                        ),
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
        if lens_checkpoint is not None and (
            working_lenses is None
            or working_lenses.fingerprint() != lens_checkpoint
            or lenses is None
            or lenses.fingerprint() != lens_checkpoint
        ):
            raise IntegratedInquiryError(
                "Integrated inquiry changed its predeclared Lens state."
            )

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
            operational_probe_observations=tuple(
                item.operational_observation for item in matched_pairs
            ),
            resolution_evidence_receipts=tuple(
                item.resolution_evidence for item in matched_pairs
            ),
            canonical_checkpoint_fingerprint=canonical_checkpoint,
            simulation_ledger_fingerprint=working_runtime.ledger.fingerprint(),
            trial_control_request=trial_controls,
            controlled_trial_observations=tuple(
                item.controlled_observation
                for item in matched_pairs
                if item.controlled_observation is not None
            ),
            held_out_replication_receipts=tuple(held_out_replications),
            workspace_admission_observations=tuple(
                item.workspace_admission_observation
                for item in matched_pairs
                if item.workspace_admission_observation is not None
            ),
            held_out_workspace_admission_receipts=tuple(
                held_out_workspace_replications
            ),
            outgoing_action_observations=tuple(
                item.outgoing_action_observation
                for item in matched_pairs
                if item.outgoing_action_observation is not None
            ),
            held_out_outgoing_action_receipts=tuple(
                held_out_action_replications
            ),
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
            held_out_replications=tuple(held_out_replications),
            held_out_workspace_admission_replications=tuple(
                held_out_workspace_replications
            ),
            held_out_outgoing_action_replications=tuple(
                held_out_action_replications
            ),
            replayed=replayed,
        )
