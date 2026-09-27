"""Matched structural observations derived from real counterfactual traces.

The observer compares a zero-intervention baseline with a full-patch treatment
that share the same canonical checkpoint, Attention allocation, declared
intervention, budgets, and result lineage.  It reports only the materialized
overlay difference and whether pre-existing canonical records were preserved.
It does not decide which preregistered functional outcome occurred, establish
semantic truth, resolve an obligation, or promote simulated state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, stable_id

from .counterfactual import (
    CounterfactualExecutionTrace,
    CounterfactualPlan,
    CounterfactualRunResult,
    SimulationDisposition,
    SimulationIntegrityError,
    SimulationLedger,
    derive_counterfactual_execution_trace,
)
from .hypotheses import StructuralHypothesis


MATCHED_TRACE_OBSERVER_VERSION = "matched_counterfactual_trace_observer_v0.23"


class TraceObservationIntegrityError(RuntimeError):
    """Raised when two executions are not a genuine matched trace pair."""


class StructuralTraceEffect(str, Enum):
    NO_STRUCTURAL_EFFECT = "no_structural_effect"
    ADDITIVE_OVERLAY_EFFECT = "additive_overlay_effect"
    CANONICAL_RECORD_MUTATION = "canonical_record_mutation"


@dataclass(frozen=True)
class MatchedCounterfactualPlans:
    baseline: CounterfactualPlan
    treatment: CounterfactualPlan


def build_matched_counterfactual_plans(
    hypothesis: StructuralHypothesis,
    *,
    source_event_key: str,
    requested_budget: float,
    consumed_budget: float,
) -> MatchedCounterfactualPlans:
    """Build a zero-patch baseline and full-patch treatment without outcome labels."""

    hypothesis = StructuralHypothesis.model_validate(
        hypothesis.model_dump(mode="json")
    )
    if not source_event_key.strip():
        raise ValueError("Matched counterfactual plans require a source event key.")
    if not hypothesis.patches:
        raise ValueError("Matched counterfactual treatment requires a declared patch.")
    shared = {
        "operator_version": hypothesis.grammar_version,
        "requested_budget": requested_budget,
        "consumed_budget": consumed_budget,
        "patches": hypothesis.patches,
        "disposition": SimulationDisposition.DISCARDED,
        "result_refs": (hypothesis.hypothesis_id,),
    }
    baseline = CounterfactualPlan.build(
        source_event_key=stable_id(
            "matched_counterfactual_baseline",
            MATCHED_TRACE_OBSERVER_VERSION,
            source_event_key,
            hypothesis.hypothesis_id,
        ),
        apply_patch_count=0,
        **shared,
    )
    treatment = CounterfactualPlan.build(
        source_event_key=stable_id(
            "matched_counterfactual_treatment",
            MATCHED_TRACE_OBSERVER_VERSION,
            source_event_key,
            hypothesis.hypothesis_id,
        ),
        apply_patch_count=len(hypothesis.patches),
        **shared,
    )
    return MatchedCounterfactualPlans(baseline=baseline, treatment=treatment)


def _qualified_delta_refs(
    trace: CounterfactualExecutionTrace,
    field: str,
) -> tuple[str, ...]:
    return tuple(
        sorted(
            f"{delta.collection}:{record_key}"
            for delta in trace.collection_deltas
            for record_key in getattr(delta, field)
        )
    )


class MatchedStructuralObservation(FrozenRecord):
    """Non-authoritative materialized difference between matched simulation arms."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    observer_version: str = MATCHED_TRACE_OBSERVER_VERSION
    hypothesis_ref: str
    baseline: CounterfactualExecutionTrace
    treatment: CounterfactualExecutionTrace
    effect: StructuralTraceEffect
    effect_signature: str
    added_record_refs: tuple[str, ...] = ()
    removed_record_refs: tuple[str, ...] = ()
    changed_record_refs: tuple[str, ...] = ()
    canonical_records_preserved: bool
    matched_control_verified: bool = True
    simulated_only: bool = True
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        hypothesis_ref: str,
        baseline: CounterfactualExecutionTrace,
        treatment: CounterfactualExecutionTrace,
    ) -> "MatchedStructuralObservation":
        added = _qualified_delta_refs(treatment, "added_record_keys")
        removed = _qualified_delta_refs(treatment, "removed_record_keys")
        changed = _qualified_delta_refs(treatment, "changed_record_keys")
        preserved = not removed and not changed
        if removed or changed:
            effect = StructuralTraceEffect.CANONICAL_RECORD_MUTATION
        elif added:
            effect = StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
        else:
            effect = StructuralTraceEffect.NO_STRUCTURAL_EFFECT
        effect_signature = stable_id(
            "matched_structural_effect",
            MATCHED_TRACE_OBSERVER_VERSION,
            added,
            removed,
            changed,
        )
        values = {
            "observer_version": MATCHED_TRACE_OBSERVER_VERSION,
            "hypothesis_ref": hypothesis_ref,
            "baseline": baseline,
            "treatment": treatment,
            "effect": effect,
            "effect_signature": effect_signature,
            "added_record_refs": added,
            "removed_record_refs": removed,
            "changed_record_refs": changed,
            "canonical_records_preserved": preserved,
            "matched_control_verified": True,
            "simulated_only": True,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["observation_id"] = stable_id(
            "matched_structural_observation",
            {
                key: value.model_dump(mode="json")
                if isinstance(value, CounterfactualExecutionTrace)
                else value.value
                if isinstance(value, Enum)
                else value
                for key, value in values.items()
            },
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_observation(self) -> "MatchedStructuralObservation":
        if self.observer_version != MATCHED_TRACE_OBSERVER_VERSION:
            raise ValueError("Unsupported matched trace observer version.")
        if not self.hypothesis_ref.strip():
            raise ValueError("Matched structural observation requires a hypothesis ref.")
        if self.baseline.match_signature != self.treatment.match_signature:
            raise ValueError("Matched counterfactual controls differ.")
        if self.baseline.source_event_key == self.treatment.source_event_key:
            raise ValueError("Matched counterfactual arms must use distinct event keys.")
        if (
            self.baseline.disposition != SimulationDisposition.DISCARDED
            or self.treatment.disposition != SimulationDisposition.DISCARDED
        ):
            raise ValueError("Matched structural observations require completed runs.")
        if self.baseline.applied_patch_ids:
            raise ValueError("Matched counterfactual baseline applied an intervention.")
        if any(
            delta.before_sha256 != delta.after_sha256
            for delta in self.baseline.collection_deltas
        ):
            raise ValueError("Matched counterfactual baseline changed materialized state.")
        if (
            not self.treatment.declared_patch_ids
            or self.treatment.applied_patch_ids
            != self.treatment.declared_patch_ids
        ):
            raise ValueError("Matched counterfactual treatment is not the full intervention.")
        if self.hypothesis_ref not in self.baseline.result_refs or (
            self.hypothesis_ref not in self.treatment.result_refs
        ):
            raise ValueError("Matched structural observation lost hypothesis lineage.")
        expected_added = _qualified_delta_refs(self.treatment, "added_record_keys")
        expected_removed = _qualified_delta_refs(
            self.treatment, "removed_record_keys"
        )
        expected_changed = _qualified_delta_refs(
            self.treatment, "changed_record_keys"
        )
        if (
            self.added_record_refs != expected_added
            or self.removed_record_refs != expected_removed
            or self.changed_record_refs != expected_changed
        ):
            raise ValueError("Matched structural observation delta was altered.")
        expected_preserved = not expected_removed and not expected_changed
        if self.canonical_records_preserved != expected_preserved:
            raise ValueError("Matched structural preservation result was altered.")
        if expected_removed or expected_changed:
            expected_effect = StructuralTraceEffect.CANONICAL_RECORD_MUTATION
        elif expected_added:
            expected_effect = StructuralTraceEffect.ADDITIVE_OVERLAY_EFFECT
        else:
            expected_effect = StructuralTraceEffect.NO_STRUCTURAL_EFFECT
        if self.effect != expected_effect:
            raise ValueError("Matched structural effect classification was altered.")
        expected_signature = stable_id(
            "matched_structural_effect",
            self.observer_version,
            expected_added,
            expected_removed,
            expected_changed,
        )
        if self.effect_signature != expected_signature:
            raise ValueError("Matched structural effect signature was altered.")
        if (
            not self.matched_control_verified
            or not self.simulated_only
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Matched structural observation crossed its authority boundary.")
        payload = self.model_dump(mode="json", exclude={"observation_id"})
        if self.observation_id != stable_id(
            "matched_structural_observation", payload
        ):
            raise ValueError("Matched structural observation checksum mismatch.")
        return self


class MatchedCounterfactualObserver:
    """Validate real ledger lineage and derive one matched structural receipt."""

    def observe(
        self,
        kernel: VerdantKernel,
        ledger: SimulationLedger,
        *,
        hypothesis_ref: str,
        baseline_plan: CounterfactualPlan,
        baseline_result: CounterfactualRunResult,
        treatment_plan: CounterfactualPlan,
        treatment_result: CounterfactualRunResult,
    ) -> MatchedStructuralObservation:
        try:
            baseline = derive_counterfactual_execution_trace(
                kernel,
                ledger,
                plan=baseline_plan,
                reservation=baseline_result.reservation,
                settlement=baseline_result.settlement,
            )
            treatment = derive_counterfactual_execution_trace(
                kernel,
                ledger,
                plan=treatment_plan,
                reservation=treatment_result.reservation,
                settlement=treatment_result.settlement,
            )
            if baseline_result.trace != baseline or treatment_result.trace != treatment:
                raise TraceObservationIntegrityError(
                    "Counterfactual run trace disagrees with its actual ledger records."
                )
            return MatchedStructuralObservation.build(
                hypothesis_ref=hypothesis_ref,
                baseline=baseline,
                treatment=treatment,
            )
        except TraceObservationIntegrityError:
            raise
        except (SimulationIntegrityError, ValueError, TypeError) as exc:
            raise TraceObservationIntegrityError(str(exc)) from exc
