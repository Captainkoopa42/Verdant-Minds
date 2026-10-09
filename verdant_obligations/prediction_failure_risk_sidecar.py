"""Immutable, non-authoritative receipts for the v0.49 risk operator.

The receipt binds the complete read-only evaluation to the exact canonical
checkpoint and durable .vfp/.vpp bytes. Loading recomputes that evaluation;
checksums alone never establish provenance. No simulation is executed here.
"""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .prediction_failure_risk_operator import (
    PredictionFailureGovernanceRiskOperator,
    PredictionFailureRiskEvaluation,
)
from .prediction_failure_trial_plans import (
    _write_immutable,
    load_prediction_failure_trial_plan,
)


PREDICTION_FAILURE_RISK_RECEIPT_VERSION = "prediction_failure_risk_receipt_v0.50"
PREDICTION_FAILURE_RISK_RECEIPT_FORMAT = "verdant-prediction-failure-risk-receipt-v1"
PREDICTION_FAILURE_RISK_RECEIPT_SIDECAR_SUFFIX = ".vfr"
_MAX_SIDECAR_BYTES = 2 * 1024 * 1024


class PredictionFailureRiskReceiptIntegrityError(RuntimeError):
    """The output receipt lost its exact input or non-authority boundary."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


class PredictionFailureRiskReceipt(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    receipt_version: str = PREDICTION_FAILURE_RISK_RECEIPT_VERSION
    canonical_kernel_id: str
    canonical_fingerprint: str
    canonical_cycle: int = Field(ge=0)
    preregistration_ref: str
    preregistration_sha256: str
    plan_bundle_ref: str
    plan_sha256: str
    evaluation: PredictionFailureRiskEvaluation
    matched_trial_executed: bool = False
    simulation_trace_observed: bool = False
    trial_result_observed: bool = False
    causal_attribution_enabled: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls, *, kernel: VerdantKernel, preregistration_ref: str,
        preregistration_bytes: bytes, plan_bytes: bytes,
        evaluation: PredictionFailureRiskEvaluation,
    ) -> "PredictionFailureRiskReceipt":
        values = dict(
            receipt_version=PREDICTION_FAILURE_RISK_RECEIPT_VERSION,
            canonical_kernel_id=kernel.state.identity.kernel_id,
            canonical_fingerprint=kernel.fingerprint(),
            canonical_cycle=kernel.state.cycle,
            preregistration_ref=preregistration_ref,
            preregistration_sha256=_sha(preregistration_bytes),
            plan_bundle_ref=evaluation.plan_bundle_ref,
            plan_sha256=_sha(plan_bytes),
            evaluation=evaluation.model_dump(mode="json"),
            matched_trial_executed=False, simulation_trace_observed=False,
            trial_result_observed=False, causal_attribution_enabled=False,
            resolution_authority_enabled=False, promotion_authority_enabled=False,
            policy_rewrite_authority_enabled=False, canonical_commit_permitted=False,
        )
        return cls(
            receipt_id=stable_id("prediction_failure_risk_receipt", values),
            **values,
        )

    @model_validator(mode="after")
    def check_boundary(self) -> "PredictionFailureRiskReceipt":
        if (
            self.receipt_version != PREDICTION_FAILURE_RISK_RECEIPT_VERSION
            or not self.canonical_kernel_id or not self.preregistration_ref
            or not self.plan_bundle_ref
            or not all(_is_sha256(value) for value in (
                self.canonical_fingerprint, self.preregistration_sha256,
                self.plan_sha256,
            ))
            or self.evaluation.canonical_fingerprint != self.canonical_fingerprint
            or self.evaluation.plan_bundle_ref != self.plan_bundle_ref
            or self.matched_trial_executed or self.simulation_trace_observed
            or self.trial_result_observed or self.causal_attribution_enabled
            or self.resolution_authority_enabled or self.promotion_authority_enabled
            or self.policy_rewrite_authority_enabled or self.canonical_commit_permitted
        ):
            raise ValueError("PredictionFailure risk receipt crossed its boundary.")
        if self.receipt_id != stable_id(
            "prediction_failure_risk_receipt",
            self.model_dump(mode="json", exclude={"receipt_id"}),
        ):
            raise ValueError("PredictionFailure risk receipt checksum mismatch.")
        return self


class PredictionFailureRiskReceiptEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar_format: str = PREDICTION_FAILURE_RISK_RECEIPT_FORMAT
    receipt: PredictionFailureRiskReceipt
    receipt_sha256: str

    @classmethod
    def build(
        cls, receipt: PredictionFailureRiskReceipt,
    ) -> "PredictionFailureRiskReceiptEnvelope":
        frozen = PredictionFailureRiskReceipt.model_validate(
            receipt.model_dump(mode="json")
        )
        return cls(
            receipt=frozen,
            receipt_sha256=_sha(canonical_json_bytes(frozen.model_dump(mode="json"))),
        )

    @model_validator(mode="after")
    def check_digest(self) -> "PredictionFailureRiskReceiptEnvelope":
        if (
            self.sidecar_format != PREDICTION_FAILURE_RISK_RECEIPT_FORMAT
            or self.receipt_sha256
            != _sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))
        ):
            raise ValueError("PredictionFailure risk receipt envelope mismatch.")
        return self


def prediction_failure_risk_receipt_bytes(
    envelope: PredictionFailureRiskReceiptEnvelope,
) -> bytes:
    validated = PredictionFailureRiskReceiptEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureRiskReceiptIntegrityError(
            "PredictionFailure risk receipt exceeds its size limit."
        )
    return data


def read_prediction_failure_risk_receipt(
    path: str | Path,
) -> PredictionFailureRiskReceiptEnvelope:
    """Check canonical bytes and local integrity, without asserting provenance."""
    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_SIDECAR_BYTES:
            raise PredictionFailureRiskReceiptIntegrityError(
                "PredictionFailure risk receipt exceeds its size limit."
            )
        envelope = PredictionFailureRiskReceiptEnvelope.model_validate_json(data)
        if prediction_failure_risk_receipt_bytes(envelope) != data:
            raise PredictionFailureRiskReceiptIntegrityError(
                "PredictionFailure risk receipt is not canonical."
            )
        return envelope
    except PredictionFailureRiskReceiptIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise PredictionFailureRiskReceiptIntegrityError(
            "Invalid PredictionFailure risk receipt."
        ) from exc


def _assert_unchanged(
    kernel: VerdantKernel, fingerprint: str,
    inputs: tuple[tuple[Path, bytes], ...],
) -> None:
    if kernel.fingerprint() != fingerprint:
        raise PredictionFailureRiskReceiptIntegrityError(
            "PredictionFailure risk receipt mutated canonical state."
        )
    if any(path.read_bytes() != data for path, data in inputs):
        raise PredictionFailureRiskReceiptIntegrityError(
            "PredictionFailure risk receipt inputs changed during validation."
        )


@contextmanager
def _guard_inputs(
    kernel: VerdantKernel, plan_path: str | Path,
    preregistration_path: str | Path,
) -> Iterator[tuple[tuple[Path, bytes], ...]]:
    before = kernel.fingerprint()
    try:
        inputs = tuple(
            (Path(path), Path(path).read_bytes())
            for path in (plan_path, preregistration_path)
        )
        try:
            yield inputs
        finally:
            _assert_unchanged(kernel, before, inputs)
    except PredictionFailureRiskReceiptIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureRiskReceiptIntegrityError(str(exc)) from exc


def _expected_receipt(
    kernel: VerdantKernel, inputs: tuple[tuple[Path, bytes], ...],
) -> PredictionFailureRiskReceipt:
    (plan_path, plan_bytes), (preregistration_path, preregistration_bytes) = inputs
    plan = load_prediction_failure_trial_plan(
        plan_path, kernel=kernel, preregistration_path=preregistration_path,
    )
    evaluation = PredictionFailureGovernanceRiskOperator().evaluate(
        kernel=kernel, plan_path=plan_path,
        preregistration_path=preregistration_path,
    )
    _assert_unchanged(kernel, evaluation.canonical_fingerprint, inputs)
    return PredictionFailureRiskReceipt.build(
        kernel=kernel,
        preregistration_ref=plan.plan_bundle.preregistration.declaration.declaration_id,
        preregistration_bytes=preregistration_bytes,
        plan_bytes=plan_bytes, evaluation=evaluation,
    )


def save_prediction_failure_risk_receipt(
    path: str | Path, envelope: PredictionFailureRiskReceiptEnvelope, *,
    kernel: VerdantKernel, plan_path: str | Path,
    preregistration_path: str | Path,
) -> str:
    """Publish only an exactly recomputed receipt; occupied paths never merge."""
    with _guard_inputs(kernel, plan_path, preregistration_path) as inputs:
        if Path(path).resolve() in {p.resolve() for p, _ in inputs}:
            raise PredictionFailureRiskReceiptIntegrityError(
                "PredictionFailure risk receipt needs a separate output path."
            )
        validated = PredictionFailureRiskReceiptEnvelope.model_validate(
            envelope.model_dump(mode="json")
        )
        if validated.receipt != _expected_receipt(kernel, inputs):
            raise PredictionFailureRiskReceiptIntegrityError(
                "PredictionFailure risk receipt does not match exact input provenance."
            )
        # Reuse the established POSIX locked, synced, atomic immutable writer.
        _write_immutable(Path(path), prediction_failure_risk_receipt_bytes(validated))
        return validated.receipt.receipt_id


def load_prediction_failure_risk_receipt(
    path: str | Path, *, kernel: VerdantKernel, plan_path: str | Path,
    preregistration_path: str | Path,
) -> PredictionFailureRiskReceiptEnvelope:
    """Replay provenance validation without constructing a simulation ledger."""
    with _guard_inputs(kernel, plan_path, preregistration_path) as inputs:
        envelope = read_prediction_failure_risk_receipt(path)
        if envelope.receipt != _expected_receipt(kernel, inputs):
            raise PredictionFailureRiskReceiptIntegrityError(
                "PredictionFailure risk receipt does not match exact input provenance."
            )
        return envelope


class PredictionFailureRiskReceiptRecorder:
    """Explicitly persist the read-only risk evaluation in a separate sidecar."""

    def record(
        self, path: str | Path, *, kernel: VerdantKernel,
        plan_path: str | Path, preregistration_path: str | Path,
    ) -> PredictionFailureRiskReceiptEnvelope:
        with _guard_inputs(kernel, plan_path, preregistration_path) as inputs:
            envelope = PredictionFailureRiskReceiptEnvelope.build(
                _expected_receipt(kernel, inputs)
            )
            save_prediction_failure_risk_receipt(
                path, envelope, kernel=kernel, plan_path=plan_path,
                preregistration_path=preregistration_path,
            )
            return envelope
