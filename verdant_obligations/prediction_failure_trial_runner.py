"""Opt-in, resource-accounted execution of the frozen PredictionFailure trial.

Each arm invokes the existing risk operator between a native reservation and
settlement on a private ledger. The operator is a governance-risk proxy, not a
calibrated physical forecast. Its output is recorded only as simulated evidence.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import (
    COUNTERFACTUAL_RUNTIME_VERSION, CounterfactualOverlay, CounterfactualPlan,
    CounterfactualRuntime, CounterfactualExecutionTrace, SimulationDisposition,
    SimulationLedger, SimulationLedgerState, SimulationReservation,
    derive_counterfactual_execution_trace,
)
from .prediction_failure_risk_operator import (
    PredictionFailureGovernanceRiskOperator, PredictionFailureRiskProjection,
)
from .prediction_failure_risk_sidecar import (
    PredictionFailureRiskReceipt, load_prediction_failure_risk_receipt,
)
from .prediction_failure_trial_plans import (
    PredictionFailureTrialSimulationPlan, _write_immutable,
    load_prediction_failure_trial_plan,
)
from .prediction_failure_trial_preregistration import (
    PREDICTION_FAILURE_TRIAL_ARM_ORDER, PredictionFailureTrialArm,
    PredictionFailureTrialDisposition, PredictionFailureTrialOutcomePolicy,
)

PREDICTION_FAILURE_TRIAL_RUNNER_VERSION = "prediction_failure_trial_runner_v0.51"
PREDICTION_FAILURE_TRIAL_RESULT_FORMAT = "verdant-prediction-failure-trial-result-v1"
PREDICTION_FAILURE_TRIAL_RESULT_SIDECAR_SUFFIX = ".vft"
_MAX_SIDECAR_BYTES = 8 * 1024 * 1024


class PredictionFailureTrialResultIntegrityError(RuntimeError):
    """A result lost its execution, control, resource, or source lineage."""


def _json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(v) for v in value]
    return value


def _build(cls, field: str, prefix: str, **values):
    payload = _json(values)
    return cls(**{field: stable_id(prefix, payload), **payload})


def _check_id(record: BaseModel, field: str, prefix: str) -> None:
    if getattr(record, field) != stable_id(
        prefix, record.model_dump(mode="json", exclude={field}),
    ):
        raise ValueError("PredictionFailure execution record checksum mismatch.")


class _NonAuthoritative(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)
    simulated_only: bool = True
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @model_validator(mode="after")
    def check_authority(self):
        if (not self.simulated_only or self.causal_attribution_enabled
            or self.resolution_authority_enabled or self.promotion_authority_enabled
            or self.policy_rewrite_authority_enabled or self.canonical_commit_permitted):
            raise ValueError("PredictionFailure execution crossed its authority boundary.")
        return self


def _boundary() -> dict:
    return dict(simulated_only=True, causal_attribution_enabled=False,
                resolution_authority_enabled=False, promotion_authority_enabled=False,
                policy_rewrite_authority_enabled=False, canonical_commit_permitted=False)


class PredictionFailureTrialObservation(_NonAuthoritative):
    observation_id: str
    arm: PredictionFailureTrialArm
    risk_projection: PredictionFailureRiskProjection
    predicted_harm_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @classmethod
    def build(cls, projection: PredictionFailureRiskProjection):
        return _build(cls, "observation_id", "prediction_failure_trial_observation",
                      arm=projection.arm, risk_projection=projection,
                      predicted_harm_score=projection.predicted_harm_score, **_boundary())

    @model_validator(mode="after")
    def check_observation(self):
        if (self.arm != self.risk_projection.arm
            or self.predicted_harm_score != self.risk_projection.predicted_harm_score):
            raise ValueError("PredictionFailure observation differs from operator output.")
        _check_id(self, "observation_id", "prediction_failure_trial_observation")
        return self


class PredictionFailureTrialExecutionTrace(_NonAuthoritative):
    trace_id: str
    runner_version: str = PREDICTION_FAILURE_TRIAL_RUNNER_VERSION
    arm: PredictionFailureTrialArm
    future_plan_ref: str
    shared_design_seed: int = Field(ge=0)
    native_plan: CounterfactualPlan
    native_trace: CounterfactualExecutionTrace
    ledger: SimulationLedgerState
    prediction_failure_trial_observation: PredictionFailureTrialObservation

    @classmethod
    def build(cls, *, future_plan, native_plan, native_trace, ledger, observation):
        return _build(cls, "trace_id", "prediction_failure_trial_execution_trace",
                      runner_version=PREDICTION_FAILURE_TRIAL_RUNNER_VERSION,
                      arm=future_plan.arm, future_plan_ref=future_plan.plan_id,
                      shared_design_seed=future_plan.shared_design_seed,
                      native_plan=native_plan, native_trace=native_trace,
                      ledger=ledger, prediction_failure_trial_observation=observation,
                      **_boundary())

    @model_validator(mode="after")
    def check_trace(self):
        if (self.runner_version != PREDICTION_FAILURE_TRIAL_RUNNER_VERSION
            or self.arm != self.prediction_failure_trial_observation.arm
            or self.native_plan.patches or self.native_plan.apply_patch_count
            or self.native_plan.disposition != SimulationDisposition.DISCARDED
            or len(self.ledger.reservations) != 1 or len(self.ledger.settlements) != 1):
            raise ValueError("PredictionFailure trace lost its bounded execution shape.")
        _check_id(self, "trace_id", "prediction_failure_trial_execution_trace")
        return self


def _metrics(scores, observed: float, policy: PredictionFailureTrialOutcomePolicy):
    errors = tuple(None if score is None else abs(score - observed) for score in scores)
    baseline, ablation, null = errors
    delta = None if baseline is None or ablation is None else abs(ablation - baseline)
    null_delta = None if baseline is None or null is None else abs(null - baseline)
    if any(value is None for value in errors):
        disposition = PredictionFailureTrialDisposition.INSUFFICIENT_EVIDENCE
    elif null_delta > policy.valid_null_max_error_delta:
        disposition = PredictionFailureTrialDisposition.INVALID_VALID_NULL
    elif delta >= policy.target_error_change_threshold:
        disposition = PredictionFailureTrialDisposition.TARGET_ERROR_CHANGED
    else:
        disposition = PredictionFailureTrialDisposition.TARGET_ERROR_UNCHANGED
    return errors, delta, null_delta, disposition


class PredictionFailureTrialResult(_NonAuthoritative):
    result_id: str
    runner_version: str = PREDICTION_FAILURE_TRIAL_RUNNER_VERSION
    risk_receipt: PredictionFailureRiskReceipt
    risk_receipt_sha256: str
    traces: tuple[PredictionFailureTrialExecutionTrace, ...] = Field(min_length=3, max_length=3)
    observed_harm_score: float = Field(ge=0.0, le=1.0)
    outcome_policy: PredictionFailureTrialOutcomePolicy
    absolute_errors: tuple[float | None, float | None, float | None]
    target_error_delta: float | None = Field(default=None, ge=0.0, le=1.0)
    valid_null_error_delta: float | None = Field(default=None, ge=0.0, le=1.0)
    disposition: PredictionFailureTrialDisposition
    total_consumed_budget: float = Field(ge=0.0)
    matched_trial_executed: bool = True

    @classmethod
    def build(cls, *, receipt, receipt_bytes, traces, declaration):
        errors, delta, null_delta, disposition = _metrics(
            tuple(t.prediction_failure_trial_observation.predicted_harm_score for t in traces),
            declaration.hypothesis_bundle.evidence_receipt.observed_value,
            declaration.outcome_policy,
        )
        return _build(cls, "result_id", "prediction_failure_trial_result",
                      runner_version=PREDICTION_FAILURE_TRIAL_RUNNER_VERSION,
                      risk_receipt=receipt,
                      risk_receipt_sha256=hashlib.sha256(receipt_bytes).hexdigest(),
                      traces=traces,
                      observed_harm_score=declaration.hypothesis_bundle.evidence_receipt.observed_value,
                      outcome_policy=declaration.outcome_policy, absolute_errors=errors,
                      target_error_delta=delta, valid_null_error_delta=null_delta,
                      disposition=disposition, matched_trial_executed=True,
                      total_consumed_budget=sum(t.native_trace.consumed_budget for t in traces),
                      **_boundary())

    @model_validator(mode="after")
    def check_result(self):
        if (self.runner_version != PREDICTION_FAILURE_TRIAL_RUNNER_VERSION
            or not self.matched_trial_executed
            or tuple(t.arm for t in self.traces) != PREDICTION_FAILURE_TRIAL_ARM_ORDER
            or len({t.native_plan.plan_id for t in self.traces}) != 3
            or len({t.shared_design_seed for t in self.traces}) != 1
            or self.total_consumed_budget != self.outcome_policy.total_budget
            or any(t.native_trace.consumed_budget != self.outcome_policy.per_arm_budget
                   for t in self.traces)):
            raise ValueError("PredictionFailure result lost matched execution or resource controls.")
        expected = _metrics(
            tuple(t.prediction_failure_trial_observation.predicted_harm_score for t in self.traces),
            self.observed_harm_score, self.outcome_policy,
        )
        if expected != (self.absolute_errors, self.target_error_delta,
                        self.valid_null_error_delta, self.disposition):
            raise ValueError("PredictionFailure result changed the frozen outcome rule.")
        _check_id(self, "result_id", "prediction_failure_trial_result")
        return self


class PredictionFailureTrialResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sidecar_format: str = PREDICTION_FAILURE_TRIAL_RESULT_FORMAT
    result: PredictionFailureTrialResult
    result_sha256: str

    @classmethod
    def build(cls, result):
        result = PredictionFailureTrialResult.model_validate(result.model_dump(mode="json"))
        return cls(result=result, result_sha256=hashlib.sha256(
            canonical_json_bytes(result.model_dump(mode="json"))).hexdigest())

    @model_validator(mode="after")
    def check_envelope(self):
        if (self.sidecar_format != PREDICTION_FAILURE_TRIAL_RESULT_FORMAT
            or self.result_sha256 != hashlib.sha256(
                canonical_json_bytes(self.result.model_dump(mode="json"))).hexdigest()):
            raise ValueError("PredictionFailure result envelope checksum mismatch.")
        return self


def _native_plan(future: PredictionFailureTrialSimulationPlan, receipt_ref: str):
    return CounterfactualPlan.build(
        source_event_key=stable_id("prediction_failure_executed_arm",
                                  PREDICTION_FAILURE_TRIAL_RUNNER_VERSION,
                                  future.counterfactual_source_event_key, receipt_ref),
        operator_version=PREDICTION_FAILURE_TRIAL_RUNNER_VERSION,
        requested_budget=future.requested_budget,
        consumed_budget=future.maximum_consumed_budget,
        result_refs=(*future.result_refs, future.plan_id, receipt_ref),
    )


class PredictionFailureTrialArmRuntime:
    """Run the operator inside one private native budget reservation."""

    def execute(self, *, kernel, ledger, future_plan, receipt, plan_path, preregistration_path):
        plan = _native_plan(future_plan, receipt.receipt_id)
        decision, allocation = CounterfactualRuntime._allocation(
            kernel, future_plan.attention_allocation_ref,
        )
        reservation, replayed = ledger.reserve(
            kernel=kernel, decision=decision, allocation=allocation, plan=plan,
        )
        if replayed:
            raise PredictionFailureTrialResultIntegrityError("Trial arms require pristine ledgers.")
        # This invocation occurs after reservation and before settlement. The
        # persisted pre-execution score is used only to verify version/input drift.
        evaluation = PredictionFailureGovernanceRiskOperator().evaluate(
            kernel=kernel, plan_path=plan_path, preregistration_path=preregistration_path,
        )
        projection = next(p for p in evaluation.projections if p.arm == future_plan.arm)
        expected = next(p for p in receipt.evaluation.projections if p.arm == future_plan.arm)
        if projection != expected:
            raise PredictionFailureTrialResultIntegrityError("Reserved operator output drifted.")
        observation = PredictionFailureTrialObservation.build(projection)
        settlement = ledger.settle(reservation=reservation, plan=plan,
                                   overlay=CounterfactualOverlay(kernel), kernel=kernel)
        trace = derive_counterfactual_execution_trace(
            kernel, ledger, plan=plan, reservation=reservation, settlement=settlement,
        )
        return PredictionFailureTrialExecutionTrace.build(
            future_plan=future_plan, native_plan=plan, native_trace=trace,
            ledger=ledger.snapshot(), observation=observation,
        )


@contextmanager
def _guard(kernel, *paths):
    before = kernel.fingerprint()
    try:
        inputs = tuple((Path(p), Path(p).read_bytes()) for p in paths)
        try:
            yield inputs
        finally:
            if kernel.fingerprint() != before or any(p.read_bytes() != b for p, b in inputs):
                raise PredictionFailureTrialResultIntegrityError("Trial canonical state or inputs changed.")
    except PredictionFailureTrialResultIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureTrialResultIntegrityError(str(exc)) from exc


def _sources(kernel, risk_receipt_path, plan_path, preregistration_path):
    receipt = load_prediction_failure_risk_receipt(
        risk_receipt_path, kernel=kernel, plan_path=plan_path,
        preregistration_path=preregistration_path,
    ).receipt
    plans = load_prediction_failure_trial_plan(
        plan_path, kernel=kernel, preregistration_path=preregistration_path,
    ).plan_bundle
    _, allocation = CounterfactualRuntime._allocation(
        kernel, plans.preregistration.declaration.hypothesis_bundle.attention_allocation_ref,
    )
    if plans.total_requested_budget > allocation.granted_budget + 1e-12:
        raise PredictionFailureTrialResultIntegrityError("Three-arm trial exceeds its Attention grant.")
    return receipt, plans


def _validate_execution(kernel, trace, future, receipt):
    trace = PredictionFailureTrialExecutionTrace.model_validate(trace.model_dump(mode="json"))
    plan = _native_plan(future, receipt.receipt_id)
    decision, allocation = CounterfactualRuntime._allocation(kernel, future.attention_allocation_ref)
    reservation = SimulationReservation.build(
        source_event_key=plan.source_event_key, plan_id=plan.plan_id,
        attention_decision_id=decision.decision_id, allocation_id=allocation.allocation_id,
        obligation_id=allocation.obligation_id, requested_budget=plan.requested_budget,
        allocation_granted_budget=allocation.granted_budget,
        canonical_fingerprint=kernel.fingerprint(), canonical_cycle=kernel.state.cycle,
        runtime_version=COUNTERFACTUAL_RUNTIME_VERSION,
    )
    projection = next(p for p in receipt.evaluation.projections if p.arm == future.arm)
    if (trace.future_plan_ref != future.plan_id or trace.arm != future.arm
        or trace.shared_design_seed != future.shared_design_seed or trace.native_plan != plan
        or trace.ledger.reservations != (reservation,)
        or trace.prediction_failure_trial_observation != PredictionFailureTrialObservation.build(projection)):
        raise PredictionFailureTrialResultIntegrityError("Execution trace lost exact arm provenance.")
    restored = SimulationLedger.from_state(trace.ledger)
    expected = derive_counterfactual_execution_trace(
        kernel, restored, plan=plan, reservation=reservation, settlement=trace.ledger.settlements[0],
    )
    if trace.native_trace != expected:
        raise PredictionFailureTrialResultIntegrityError("Execution trace lost native settlement lineage.")


def _validate_result(envelope, *, kernel, receipt, plans, receipt_bytes):
    envelope = PredictionFailureTrialResultEnvelope.model_validate(envelope.model_dump(mode="json"))
    for trace, future in zip(envelope.result.traces, plans.plans, strict=True):
        _validate_execution(kernel, trace, future, receipt)
    expected = PredictionFailureTrialResult.build(
        receipt=receipt, receipt_bytes=receipt_bytes,
        traces=envelope.result.traces, declaration=plans.preregistration.declaration,
    )
    if envelope.result != expected:
        raise PredictionFailureTrialResultIntegrityError("Result differs from exact frozen trial provenance.")
    return envelope


def prediction_failure_trial_result_bytes(envelope):
    checked = PredictionFailureTrialResultEnvelope.model_validate(envelope.model_dump(mode="json"))
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureTrialResultIntegrityError("Trial result exceeds its size limit.")
    return data


def read_prediction_failure_trial_result(path):
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureTrialResultIntegrityError("Trial result exceeds its size limit.")
        envelope = PredictionFailureTrialResultEnvelope.model_validate_json(data)
        if prediction_failure_trial_result_bytes(envelope) != data:
            raise PredictionFailureTrialResultIntegrityError("Trial result is not canonical.")
        return envelope
    except PredictionFailureTrialResultIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise PredictionFailureTrialResultIntegrityError("Invalid trial result sidecar.") from exc


def load_prediction_failure_trial_result(path, *, kernel, risk_receipt_path, plan_path, preregistration_path):
    with _guard(kernel, risk_receipt_path, plan_path, preregistration_path) as inputs:
        receipt, plans = _sources(kernel, risk_receipt_path, plan_path, preregistration_path)
        return _validate_result(read_prediction_failure_trial_result(path), kernel=kernel,
                                receipt=receipt, plans=plans, receipt_bytes=inputs[0][1])


class PredictionFailureTrialRunner:
    """Stage three isolated executions; publish only a complete durable result."""

    def run(self, path, *, kernel, risk_receipt_path, plan_path, preregistration_path,
            ledgers: tuple[SimulationLedger, ...] | None = None):
        with _guard(kernel, risk_receipt_path, plan_path, preregistration_path) as inputs:
            output = Path(path)
            if output.resolve() in {p.resolve() for p, _ in inputs}:
                raise PredictionFailureTrialResultIntegrityError("Trial result needs a separate output path.")
            if output.exists():
                return load_prediction_failure_trial_result(
                    output, kernel=kernel, risk_receipt_path=risk_receipt_path,
                    plan_path=plan_path, preregistration_path=preregistration_path,
                )
            supplied = ledgers if ledgers is not None else tuple(SimulationLedger() for _ in range(3))
            if (len(supplied) != 3 or len({id(l) for l in supplied}) != 3
                or any(l.state.reservations or l.state.settlements for l in supplied)):
                raise PredictionFailureTrialResultIntegrityError("Trial requires three distinct pristine ledgers.")
            original = tuple(l.snapshot() for l in supplied)
            receipt, plans = _sources(kernel, risk_receipt_path, plan_path, preregistration_path)
            staged = tuple(SimulationLedger.from_state(s) for s in original)
            # Each arm gets a fresh canonical copy, not another arm's private state.
            traces = tuple(PredictionFailureTrialArmRuntime().execute(
                kernel=VerdantKernel.from_state(kernel.snapshot()), ledger=ledger,
                future_plan=future, receipt=receipt, plan_path=plan_path,
                preregistration_path=preregistration_path,
            ) for future, ledger in zip(plans.plans, staged, strict=True))
            result = PredictionFailureTrialResult.build(
                receipt=receipt, receipt_bytes=inputs[0][1], traces=traces,
                declaration=plans.preregistration.declaration,
            )
            envelope = _validate_result(PredictionFailureTrialResultEnvelope.build(result),
                                        kernel=kernel, receipt=receipt, plans=plans,
                                        receipt_bytes=inputs[0][1])
            if any(l.snapshot() != s for l, s in zip(supplied, original, strict=True)):
                raise PredictionFailureTrialResultIntegrityError("Caller ledgers changed during staging.")
            if any(p.read_bytes() != b for p, b in inputs):
                raise PredictionFailureTrialResultIntegrityError("Trial input bytes changed before publication.")
            _write_immutable(output, prediction_failure_trial_result_bytes(envelope))
            for caller, private in zip(supplied, staged, strict=True):
                caller.state = private.snapshot()
            return envelope
