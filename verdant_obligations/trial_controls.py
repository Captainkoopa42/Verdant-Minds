"""Predeclared controls and held-out replay for operational overlay trials.

This module binds a declared seed, bounded overlay-probe horizon, active
family-local Equivalence Lens, and supplied slot budget to the result lineage
of an actual zero/full counterfactual pair. A second observer requires one
calibration trial and at least one predeclared held-out trial to reproduce the
same structural and operational signatures.

The seed and slot budget are provenance controls only: the current
deterministic overlay runtime does not consume randomness and has no native
workspace. These receipts therefore do not establish workspace admission, an
outgoing action, a canonical dependency path, a real-world outcome, or
resolution authority.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, ObligationFamily, stable_id

from .counterfactual import (
    CounterfactualPlan,
    CounterfactualRunResult,
    SimulationIntegrityError,
    SimulationLedger,
)
from .equivalence import (
    EquivalenceLensSystem,
    LensIntegrityError,
    LensUnavailableError,
)
from .hypotheses import StructuralHypothesis
from .operational_probe import (
    MatchedOverlayOperationalObservation,
    OperationalProbeIntegrityError,
    OverlayOperationalProbe,
    OverlayOperationalProbePolicy,
)
from .trace_observations import (
    MatchedCounterfactualObserver,
    MatchedStructuralObservation,
    TraceObservationIntegrityError,
)


OPERATIONAL_TRIAL_CONTROL_VERSION = "operational_trial_controls_v0.27"
HELD_OUT_OPERATIONAL_REPLICATION_VERSION = (
    "held_out_operational_replication_v0.27"
)


class OperationalTrialControlIntegrityError(RuntimeError):
    """Raised when a controlled trial cannot be derived from actual lineage."""


class OperationalTrialSplit(str, Enum):
    CALIBRATION = "calibration"
    HELD_OUT = "held_out"


def _identity_payload(values: dict[str, Any], identity_field: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in values.items():
        if key == identity_field:
            continue
        if isinstance(value, BaseModel):
            payload[key] = value.model_dump(mode="json")
        elif isinstance(value, Enum):
            payload[key] = value.value
        elif isinstance(value, tuple):
            payload[key] = tuple(
                item.model_dump(mode="json")
                if isinstance(item, BaseModel)
                else item.value
                if isinstance(item, Enum)
                else item
                for item in value
            )
        else:
            payload[key] = value
    return payload


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class OperationalTrialContext(FrozenRecord):
    """Content-addressed controls that must be named before both arms run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    context_id: str
    policy_version: str = OPERATIONAL_TRIAL_CONTROL_VERSION
    split: OperationalTrialSplit
    seed: int = Field(ge=0)
    horizon: int = Field(ge=1, le=32)
    slot_budget: int = Field(ge=1, le=4096)
    obligation_id: str
    obligation_family: ObligationFamily
    hypothesis_ref: str
    canonical_checkpoint_fingerprint: str
    lens_binding_id: str
    lens_definition_id: str
    lens_policy_version: str
    lens_state_fingerprint: str
    predeclared: bool = True
    seed_consumed_by_runtime: bool = False
    native_workspace_budget_enforced: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "OperationalTrialContext":
        values.setdefault("policy_version", OPERATIONAL_TRIAL_CONTROL_VERSION)
        values.setdefault("predeclared", True)
        values.setdefault("seed_consumed_by_runtime", False)
        values.setdefault("native_workspace_budget_enforced", False)
        values.setdefault("observed_outcome_authority_enabled", False)
        values.setdefault("resolution_authority_enabled", False)
        values.setdefault("canonical_commit_permitted", False)
        values["context_id"] = stable_id(
            "operational_trial_context",
            _identity_payload(values, "context_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_context(self) -> "OperationalTrialContext":
        if self.policy_version != OPERATIONAL_TRIAL_CONTROL_VERSION:
            raise ValueError("Unsupported operational trial control version.")
        identifiers = (
            self.obligation_id,
            self.hypothesis_ref,
            self.lens_binding_id,
            self.lens_definition_id,
            self.lens_policy_version,
        )
        if not all(item.strip() for item in identifiers):
            raise ValueError("Operational trial control references cannot be empty.")
        if not _is_sha256(self.canonical_checkpoint_fingerprint) or not _is_sha256(
            self.lens_state_fingerprint
        ):
            raise ValueError("Operational trial control fingerprints must be SHA-256.")
        if (
            not self.predeclared
            or self.seed_consumed_by_runtime
            or self.native_workspace_budget_enforced
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Operational trial control crossed its claim boundary.")
        expected = stable_id(
            "operational_trial_context",
            self.model_dump(mode="json", exclude={"context_id"}),
        )
        if self.context_id != expected:
            raise ValueError("Operational trial control checksum mismatch.")
        return self


def build_operational_trial_context(
    kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    *,
    hypothesis: StructuralHypothesis,
    split: OperationalTrialSplit,
    seed: int,
    horizon: int,
    slot_budget: int,
) -> OperationalTrialContext:
    """Snapshot one active family-local Lens into a pre-run context."""

    hypothesis = StructuralHypothesis.model_validate(
        hypothesis.model_dump(mode="json")
    )
    obligation = kernel.state.obligation_kernels.get(hypothesis.obligation_id)
    if obligation is None:
        raise OperationalTrialControlIntegrityError(
            "Operational trial context lost its canonical obligation."
        )
    if obligation.family != ObligationFamily.DEPENDENCY_GAP:
        raise OperationalTrialControlIntegrityError(
            "Overlay operational trials currently support only DependencyGap."
        )
    try:
        active = lenses.active_binding(obligation.family).binding
    except (LensIntegrityError, LensUnavailableError) as exc:
        raise OperationalTrialControlIntegrityError(str(exc)) from exc
    return OperationalTrialContext.build(
        split=split,
        seed=seed,
        horizon=horizon,
        slot_budget=slot_budget,
        obligation_id=obligation.kernel_id,
        obligation_family=obligation.family,
        hypothesis_ref=hypothesis.hypothesis_id,
        canonical_checkpoint_fingerprint=kernel.fingerprint(),
        lens_binding_id=active.binding_id,
        lens_definition_id=active.definition_id,
        lens_policy_version=active.policy_version,
        lens_state_fingerprint=lenses.fingerprint(),
    )


def _operational_effect_signature(
    observation: MatchedOverlayOperationalObservation,
) -> str:
    return stable_id(
        "controlled_operational_effect",
        OPERATIONAL_TRIAL_CONTROL_VERSION,
        observation.effect.value,
        observation.newly_retrieved_evidence_refs,
        observation.lost_retrieved_evidence_refs,
        observation.path_changed,
        observation.baseline.disposition.value,
        observation.baseline.traversed_node_refs,
        observation.baseline.traversed_relation_refs,
        observation.baseline.retrieved_evidence_refs,
        observation.treatment.disposition.value,
        observation.treatment.traversed_node_refs,
        observation.treatment.traversed_relation_refs,
        observation.treatment.retrieved_evidence_refs,
    )


class ControlledOperationalTrialObservation(FrozenRecord):
    """One actual matched pair verified against its predeclared context."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    policy_version: str = OPERATIONAL_TRIAL_CONTROL_VERSION
    context: OperationalTrialContext
    structural_observation: MatchedStructuralObservation
    operational_observation: MatchedOverlayOperationalObservation
    structural_effect_signature: str
    operational_effect_signature: str
    context_lineage_verified: bool = True
    active_lens_verified: bool = True
    matched_control_verified: bool = True
    simulated_only: bool = True
    held_out_generalization_established: bool = False
    workspace_admission_observed: bool = False
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        context: OperationalTrialContext,
        structural_observation: MatchedStructuralObservation,
        operational_observation: MatchedOverlayOperationalObservation,
    ) -> "ControlledOperationalTrialObservation":
        values = {
            "policy_version": OPERATIONAL_TRIAL_CONTROL_VERSION,
            "context": context,
            "structural_observation": structural_observation,
            "operational_observation": operational_observation,
            "structural_effect_signature": structural_observation.effect_signature,
            "operational_effect_signature": _operational_effect_signature(
                operational_observation
            ),
            "context_lineage_verified": True,
            "active_lens_verified": True,
            "matched_control_verified": True,
            "simulated_only": True,
            "held_out_generalization_established": False,
            "workspace_admission_observed": False,
            "outgoing_action_observed": False,
            "canonical_dependency_path_established": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "controlled_operational_trial_observation",
            _identity_payload(values, "observation_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "ControlledOperationalTrialObservation":
        if self.policy_version != OPERATIONAL_TRIAL_CONTROL_VERSION:
            raise ValueError("Unsupported controlled operational trial version.")
        structural = self.structural_observation
        operational = self.operational_observation
        expected_result_refs = tuple(
            sorted((self.context.context_id, self.context.hypothesis_ref))
        )
        traces = (structural.baseline, structural.treatment)
        if any(item.result_refs != expected_result_refs for item in traces):
            raise ValueError("Trial context was not predeclared in both trace arms.")
        if (
            structural.hypothesis_ref != self.context.hypothesis_ref
            or any(
                item.obligation_id != self.context.obligation_id
                or item.canonical_fingerprint
                != self.context.canonical_checkpoint_fingerprint
                for item in traces
            )
        ):
            raise ValueError("Controlled structural trace lost its context.")
        if (
            operational.structural_observation_ref != structural.observation_id
            or operational.baseline.structural_trace_ref
            != structural.baseline.trace_id
            or operational.treatment.structural_trace_ref
            != structural.treatment.trace_id
        ):
            raise ValueError("Controlled operational trial lost structural lineage.")
        arm_pairs = (
            (operational.baseline, structural.baseline),
            (operational.treatment, structural.treatment),
        )
        if any(
            probe.obligation_id != self.context.obligation_id
            or probe.hypothesis_ref != self.context.hypothesis_ref
            or probe.canonical_checkpoint_fingerprint
            != self.context.canonical_checkpoint_fingerprint
            or probe.plan_id != trace.plan_id
            or probe.reservation_id != trace.reservation_id
            or probe.settlement_id != trace.settlement_id
            for probe, trace in arm_pairs
        ):
            raise ValueError("Controlled operational arm lost execution lineage.")
        if self.structural_effect_signature != structural.effect_signature:
            raise ValueError("Controlled structural effect signature was altered.")
        if self.operational_effect_signature != _operational_effect_signature(
            operational
        ):
            raise ValueError("Controlled operational effect signature was altered.")
        if (
            not self.context_lineage_verified
            or not self.active_lens_verified
            or not self.matched_control_verified
            or not self.simulated_only
            or self.held_out_generalization_established
            or self.workspace_admission_observed
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Controlled operational trial crossed its authority boundary.")
        expected = stable_id(
            "controlled_operational_trial_observation",
            self.model_dump(mode="json", exclude={"observation_id"}),
        )
        if self.observation_id != expected:
            raise ValueError("Controlled operational trial checksum mismatch.")
        return self


class ControlledOperationalTrialObserver:
    """Re-derive a matched trial and verify its pre-run control commitment."""

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        lenses: EquivalenceLensSystem,
        *,
        context: OperationalTrialContext,
        hypothesis: StructuralHypothesis,
        baseline_plan: CounterfactualPlan,
        baseline_result: CounterfactualRunResult,
        treatment_plan: CounterfactualPlan,
        treatment_result: CounterfactualRunResult,
    ) -> ControlledOperationalTrialObservation:
        try:
            context = OperationalTrialContext.model_validate(
                context.model_dump(mode="json")
            )
            hypothesis = StructuralHypothesis.model_validate(
                hypothesis.model_dump(mode="json")
            )
            canonical_before = kernel.fingerprint()
            lens_before = lenses.fingerprint()
            if (
                context.canonical_checkpoint_fingerprint != canonical_before
                or context.lens_state_fingerprint != lens_before
            ):
                raise OperationalTrialControlIntegrityError(
                    "Operational trial context does not match current state."
                )
            obligation = kernel.state.obligation_kernels.get(context.obligation_id)
            if (
                obligation is None
                or obligation.family != context.obligation_family
                or hypothesis.obligation_id != context.obligation_id
                or hypothesis.hypothesis_id != context.hypothesis_ref
            ):
                raise OperationalTrialControlIntegrityError(
                    "Operational trial context lost obligation or hypothesis lineage."
                )
            active = lenses.active_binding(context.obligation_family).binding
            if (
                active.binding_id != context.lens_binding_id
                or active.definition_id != context.lens_definition_id
                or active.policy_version != context.lens_policy_version
            ):
                raise OperationalTrialControlIntegrityError(
                    "Operational trial context does not name the active Lens binding."
                )
            expected_result_refs = tuple(
                sorted((context.context_id, hypothesis.hypothesis_id))
            )
            if (
                baseline_plan.result_refs != expected_result_refs
                or treatment_plan.result_refs != expected_result_refs
            ):
                raise OperationalTrialControlIntegrityError(
                    "Operational trial context was not committed before execution."
                )
            if (
                baseline_plan.patches != hypothesis.patches
                or treatment_plan.patches != hypothesis.patches
                or baseline_plan.apply_patch_count != 0
                or treatment_plan.apply_patch_count != len(hypothesis.patches)
            ):
                raise OperationalTrialControlIntegrityError(
                    "Controlled trial does not execute the declared hypothesis pair."
                )
            structural = MatchedCounterfactualObserver().observe(
                kernel,
                ledger,
                hypothesis_ref=hypothesis.hypothesis_id,
                baseline_plan=baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=treatment_plan,
                treatment_result=treatment_result,
            )
            operational = OverlayOperationalProbe(
                OverlayOperationalProbePolicy(
                    maximum_relation_hops=context.horizon
                )
            ).observe(
                kernel,
                ledger,
                hypothesis_ref=hypothesis.hypothesis_id,
                baseline_plan=baseline_plan,
                baseline_result=baseline_result,
                treatment_plan=treatment_plan,
                treatment_result=treatment_result,
                structural_observation=structural,
            )
            if kernel.fingerprint() != canonical_before or lenses.fingerprint() != lens_before:
                raise OperationalTrialControlIntegrityError(
                    "Controlled observation mutated canonical or Lens state."
                )
            return ControlledOperationalTrialObservation.build(
                context=context,
                structural_observation=structural,
                operational_observation=operational,
            )
        except OperationalTrialControlIntegrityError:
            raise
        except (
            LensIntegrityError,
            LensUnavailableError,
            OperationalProbeIntegrityError,
            SimulationIntegrityError,
            TraceObservationIntegrityError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise OperationalTrialControlIntegrityError(str(exc)) from exc


class HeldOutOperationalReplicationReceipt(FrozenRecord):
    """Exact deterministic replay across calibration and held-out contexts."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    policy_version: str = HELD_OUT_OPERATIONAL_REPLICATION_VERSION
    trials: tuple[ControlledOperationalTrialObservation, ...] = Field(min_length=2)
    calibration_trial_ref: str
    held_out_trial_refs: tuple[str, ...] = Field(min_length=1)
    seeds: tuple[int, ...] = Field(min_length=2)
    structural_effect_signature: str
    operational_effect_signature: str
    declared_seed_replay_observed: bool = True
    stochastic_generalization_established: bool = False
    native_workspace_admission_observed: bool = False
    outgoing_action_observed: bool = False
    canonical_dependency_path_established: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        trials: Sequence[ControlledOperationalTrialObservation],
    ) -> "HeldOutOperationalReplicationReceipt":
        normalized = tuple(
            ControlledOperationalTrialObservation.model_validate(
                item.model_dump(mode="json")
            )
            for item in trials
        )
        normalized = tuple(
            sorted(
                normalized,
                key=lambda item: (
                    0
                    if item.context.split == OperationalTrialSplit.CALIBRATION
                    else 1,
                    item.context.seed,
                    item.observation_id,
                ),
            )
        )
        calibration = tuple(
            item
            for item in normalized
            if item.context.split == OperationalTrialSplit.CALIBRATION
        )
        held_out = tuple(
            item
            for item in normalized
            if item.context.split == OperationalTrialSplit.HELD_OUT
        )
        if len(calibration) != 1 or not held_out:
            raise ValueError(
                "Held-out replication requires one calibration and a held-out trial."
            )
        values = {
            "policy_version": HELD_OUT_OPERATIONAL_REPLICATION_VERSION,
            "trials": normalized,
            "calibration_trial_ref": calibration[0].observation_id,
            "held_out_trial_refs": tuple(item.observation_id for item in held_out),
            "seeds": tuple(item.context.seed for item in normalized),
            "structural_effect_signature": normalized[0].structural_effect_signature,
            "operational_effect_signature": normalized[0].operational_effect_signature,
            "declared_seed_replay_observed": True,
            "stochastic_generalization_established": False,
            "native_workspace_admission_observed": False,
            "outgoing_action_observed": False,
            "canonical_dependency_path_established": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["receipt_id"] = stable_id(
            "held_out_operational_replication_receipt",
            _identity_payload(values, "receipt_id"),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "HeldOutOperationalReplicationReceipt":
        if self.policy_version != HELD_OUT_OPERATIONAL_REPLICATION_VERSION:
            raise ValueError("Unsupported held-out operational replication version.")
        calibration = tuple(
            item
            for item in self.trials
            if item.context.split == OperationalTrialSplit.CALIBRATION
        )
        held_out = tuple(
            item
            for item in self.trials
            if item.context.split == OperationalTrialSplit.HELD_OUT
        )
        if len(calibration) != 1 or not held_out:
            raise ValueError(
                "Held-out replication requires one calibration and a held-out trial."
            )
        expected_order = tuple(
            sorted(
                self.trials,
                key=lambda item: (
                    0
                    if item.context.split == OperationalTrialSplit.CALIBRATION
                    else 1,
                    item.context.seed,
                    item.observation_id,
                ),
            )
        )
        if self.trials != expected_order:
            raise ValueError("Held-out operational trials are not canonicalized.")
        contexts = tuple(item.context for item in self.trials)
        shared = {
            (
                item.policy_version,
                item.obligation_id,
                item.obligation_family,
                item.hypothesis_ref,
                item.canonical_checkpoint_fingerprint,
                item.horizon,
                item.slot_budget,
                item.lens_binding_id,
                item.lens_definition_id,
                item.lens_policy_version,
                item.lens_state_fingerprint,
            )
            for item in contexts
        }
        if len(shared) != 1:
            raise ValueError("Held-out operational controls are not matched.")
        expected_seeds = tuple(item.seed for item in contexts)
        if self.seeds != expected_seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Held-out operational trials require distinct seeds.")
        if self.calibration_trial_ref != calibration[0].observation_id or (
            self.held_out_trial_refs
            != tuple(item.observation_id for item in held_out)
        ):
            raise ValueError("Held-out operational split lineage was altered.")
        if any(
            item.structural_effect_signature != self.structural_effect_signature
            or item.operational_effect_signature != self.operational_effect_signature
            for item in self.trials
        ):
            raise ValueError("Held-out operational effect did not replicate.")
        if (
            not self.declared_seed_replay_observed
            or self.stochastic_generalization_established
            or self.native_workspace_admission_observed
            or self.outgoing_action_observed
            or self.canonical_dependency_path_established
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Held-out operational receipt crossed its authority boundary.")
        expected = stable_id(
            "held_out_operational_replication_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        )
        if self.receipt_id != expected:
            raise ValueError("Held-out operational receipt checksum mismatch.")
        return self


class HeldOutOperationalReplicationObserver:
    """Normalize controlled trials and fail closed on any replay mismatch."""

    def observe(
        self,
        trials: Sequence[ControlledOperationalTrialObservation],
    ) -> HeldOutOperationalReplicationReceipt:
        try:
            return HeldOutOperationalReplicationReceipt.build(trials)
        except (ValueError, TypeError, KeyError) as exc:
            raise OperationalTrialControlIntegrityError(str(exc)) from exc
