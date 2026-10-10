"""Quarantined raw-capture intake for a prospective PredictionFailure study.

This reader proves what bytes were imported, not where the readings originated.
It neither scores harm nor admits supplied readings as physical study outcomes.
"""
from __future__ import annotations

import base64
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictFloat, StrictInt, StrictStr, model_validator

from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .prediction_failure_forecast_preregistration import (
    _guard as _forecast_guard,
    load_prediction_failure_forecast_preregistration,
)
from .prediction_failure_trial_plans import _write_immutable

PREDICTION_FAILURE_MEASUREMENT_INTAKE_VERSION = "prediction_failure_measurement_intake_v0.54"
PREDICTION_FAILURE_RAW_CAPTURE_FORMAT = "verdant-prediction-failure-raw-capture-v1"
PREDICTION_FAILURE_MEASUREMENT_INTAKE_FORMAT = "verdant-prediction-failure-measurement-intake-v1"
PREDICTION_FAILURE_MEASUREMENT_INTAKE_SIDECAR_SUFFIX = ".vmi"
_MAX_RAW_BYTES = 1024 * 1024
_MAX_SIDECAR_BYTES = 8 * 1024 * 1024
_MISSING = (
    "authenticated_acquisition_source", "operational_measurement_protocol",
    "prospective_forecast_adapter",
)
_FALSE_FLAGS = (
    "source_authenticated", "decision_links_authenticated", "physical_evidence_admissible",
    "harm_scoring_implemented", "study_outcome_recorded", "study_executed",
    "calibration_observed", "source_independence_proven", "independent_replication_observed",
    "simulation_budget_authorized", "canonical_commit_permitted",
    "resolution_contract_satisfied", "resolution_authority_enabled",
    "promotion_authority_enabled", "policy_rewrite_authority_enabled",
)
_Text = Annotated[StrictStr, Field(min_length=1, max_length=256, pattern=r"^[^\s].*[^\s]$|^[^\s]$")]
_Unit = Literal["m", "mm", "cm", "s", "ms", "g", "kg", "N", "Pa", "V", "A", "count", "1"]


class PredictionFailureMeasurementIntakeIntegrityError(RuntimeError):
    """Raw capture or its quarantined study lineage is invalid."""


class PredictionFailureMeasurementSource(FrozenRecord):
    """Caller-reported acquisition metadata; none of it authenticates a sensor."""
    source_ref: _Text
    acquisition_id: _Text
    acquisition_method: _Text
    clock_ref: _Text
    reported_origin: Literal["physical_reported", "simulated", "unknown"]
    action_class: _Text
    quantity: _Text
    unit: _Unit


class PredictionFailureRawMeasurement(FrozenRecord):
    sample_id: _Text
    decision_event_ref: _Text
    captured_at_ns: Annotated[StrictInt, Field(ge=0)]
    unit: _Unit
    value: Annotated[StrictFloat, Field(allow_inf_nan=False)]


class PredictionFailureRawCapture(FrozenRecord):
    """One bounded single-clock, single-quantity capture, with no harm scores."""
    capture_format: Literal["verdant-prediction-failure-raw-capture-v1"]
    source: PredictionFailureMeasurementSource
    capture_start_ns: Annotated[StrictInt, Field(ge=0)]
    capture_end_ns: Annotated[StrictInt, Field(ge=0)]
    expected_sample_count: Annotated[StrictInt, Field(ge=1, le=4096)]
    samples: tuple[PredictionFailureRawMeasurement, ...] = Field(min_length=1, max_length=4096)

    @model_validator(mode="after")
    def check_capture(self):
        times = tuple(s.captured_at_ns for s in self.samples)
        if (self.capture_start_ns > self.capture_end_ns
            or len(self.samples) != self.expected_sample_count
            or len({s.sample_id for s in self.samples}) != len(self.samples)
            or any(s.unit != self.source.unit for s in self.samples)
            or any(a >= b for a, b in zip(times, times[1:]))
            or not self.capture_start_ns <= times[0] <= times[-1] <= self.capture_end_ns):
            raise ValueError("Capture lost its complete sample count, units or single-clock order.")
        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bounded_read(path, limit):
    with Path(path).open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise PredictionFailureMeasurementIntakeIntegrityError("Measurement input exceeds its size limit.")
    return data


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are ambiguous measurement evidence.")
        result[key] = value
    return result


def _bad_number(value):
    raise ValueError("Nonfinite JSON numbers are not measurements.")


def _parse_capture(data):
    if not data or len(data) > _MAX_RAW_BYTES:
        raise ValueError("Raw capture is empty or exceeds its size limit.")
    value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_bad_number)
    return PredictionFailureRawCapture.model_validate(value)


def read_prediction_failure_raw_capture(path):
    """Validate a candidate file; no canonical lineage or physical admission."""
    try:
        return _parse_capture(_bounded_read(path, _MAX_RAW_BYTES))
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise PredictionFailureMeasurementIntakeIntegrityError("Invalid raw measurement capture.") from exc


class PredictionFailureMeasurementIntakeReceipt(FrozenRecord):
    model_config = ConfigDict(extra="forbid", frozen=True)
    receipt_id: str
    intake_version: str = PREDICTION_FAILURE_MEASUREMENT_INTAKE_VERSION
    study_ref: str
    study_sha256: str
    canonical_kernel_id: str
    canonical_fingerprint: str
    action_class: str
    raw_capture_sha256: str
    raw_capture_size: int = Field(ge=1, le=_MAX_RAW_BYTES)
    raw_capture_base64: str = Field(max_length=4 * ((_MAX_RAW_BYTES + 2) // 3))
    capture: PredictionFailureRawCapture
    excluded_historical_decision_refs: tuple[str, ...]
    historical_sample_decision_refs: tuple[str, ...]
    unverified_sample_decision_refs: tuple[str, ...]
    missing_prerequisites: tuple[str, ...] = _MISSING
    purpose: Literal["measurement_protocol_pilot_only"] = "measurement_protocol_pilot_only"
    quarantined: bool = True
    source_authenticated: bool = False
    decision_links_authenticated: bool = False
    physical_evidence_admissible: bool = False
    harm_scoring_implemented: bool = False
    study_outcome_recorded: bool = False
    study_executed: bool = False
    calibration_observed: bool = False
    source_independence_proven: bool = False
    independent_replication_observed: bool = False
    simulation_budget_authorized: bool = False
    canonical_commit_permitted: bool = False
    resolution_contract_satisfied: bool = False
    resolution_authority_enabled: bool = False
    promotion_authority_enabled: bool = False
    policy_rewrite_authority_enabled: bool = False

    @model_validator(mode="after")
    def check_receipt(self):
        raw = base64.b64decode(self.raw_capture_base64, validate=True)
        refs = {s.decision_event_ref for s in self.capture.samples}
        historical = set(self.excluded_historical_decision_refs)
        if (self.intake_version != PREDICTION_FAILURE_MEASUREMENT_INTAKE_VERSION
            or len(raw) != self.raw_capture_size or _sha(raw) != self.raw_capture_sha256
            or base64.b64encode(raw).decode("ascii") != self.raw_capture_base64
            or _parse_capture(raw) != self.capture or self.capture.source.action_class != self.action_class
            or tuple(sorted(historical)) != self.excluded_historical_decision_refs
            or tuple(sorted(refs & historical)) != self.historical_sample_decision_refs
            or tuple(sorted(refs - historical)) != self.unverified_sample_decision_refs
            or self.missing_prerequisites != _MISSING or not self.quarantined
            or any(getattr(self, name) for name in _FALSE_FLAGS)):
            raise ValueError("Measurement intake lost its bytes, quarantine or historical exclusions.")
        for digest in (self.study_sha256, self.canonical_fingerprint, self.raw_capture_sha256):
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Measurement intake source identities must be SHA-256.")
        if self.receipt_id != stable_id("prediction_failure_measurement_intake",
                self.model_dump(mode="json", exclude={"receipt_id"})):
            raise ValueError("Measurement intake receipt checksum mismatch.")
        return self


class PredictionFailureMeasurementIntakeEnvelope(FrozenRecord):
    sidecar_format: str = PREDICTION_FAILURE_MEASUREMENT_INTAKE_FORMAT
    receipt: PredictionFailureMeasurementIntakeReceipt
    receipt_sha256: str

    @classmethod
    def build(cls, receipt):
        checked = PredictionFailureMeasurementIntakeReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=_sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_envelope(self):
        if (self.sidecar_format != PREDICTION_FAILURE_MEASUREMENT_INTAKE_FORMAT
            or self.receipt_sha256 != _sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))):
            raise ValueError("Measurement intake envelope checksum mismatch.")
        return self


def prediction_failure_measurement_intake_bytes(envelope):
    checked = PredictionFailureMeasurementIntakeEnvelope.model_validate(envelope.model_dump(mode="json"))
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_SIDECAR_BYTES:
        raise PredictionFailureMeasurementIntakeIntegrityError("Measurement intake sidecar exceeds its size limit.")
    return data


def read_prediction_failure_measurement_intake(path):
    """Local integrity only; load additionally checks exact canonical/raw sources."""
    try:
        data = _bounded_read(path, _MAX_SIDECAR_BYTES)
        envelope = PredictionFailureMeasurementIntakeEnvelope.model_validate_json(data)
        if prediction_failure_measurement_intake_bytes(envelope) != data:
            raise ValueError("Measurement intake sidecar is not canonical.")
        return envelope
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise PredictionFailureMeasurementIntakeIntegrityError("Invalid measurement intake sidecar.") from exc


def _expected(study, study_bytes, raw_bytes):
    capture = _parse_capture(raw_bytes)
    if capture.source.action_class != study.action_class:
        raise ValueError("Raw capture action class does not match its study.")
    refs = {s.decision_event_ref for s in capture.samples}
    historical = set(study.excluded_decision_refs)
    values = dict(
        intake_version=PREDICTION_FAILURE_MEASUREMENT_INTAKE_VERSION,
        study_ref=study.declaration_id, study_sha256=_sha(study_bytes),
        canonical_kernel_id=study.canonical_kernel_id,
        canonical_fingerprint=study.canonical_fingerprint, action_class=study.action_class,
        raw_capture_sha256=_sha(raw_bytes), raw_capture_size=len(raw_bytes),
        raw_capture_base64=base64.b64encode(raw_bytes).decode("ascii"),
        capture=capture.model_dump(mode="json"),
        excluded_historical_decision_refs=study.excluded_decision_refs,
        historical_sample_decision_refs=tuple(sorted(refs & historical)),
        unverified_sample_decision_refs=tuple(sorted(refs - historical)),
        missing_prerequisites=_MISSING, purpose="measurement_protocol_pilot_only",
        quarantined=True, **{name: False for name in _FALSE_FLAGS},
    )
    values = json.loads(canonical_json_bytes(values))
    return PredictionFailureMeasurementIntakeReceipt(
        receipt_id=stable_id("prediction_failure_measurement_intake", values), **values)


@contextmanager
def _context(*, forecast_study_path, raw_capture_path, kernel, **study_inputs):
    try:
        with _forecast_guard(kernel, **study_inputs) as (chain_inputs, _manifest):
            study_path, raw_path = Path(forecast_study_path), Path(raw_capture_path)
            study_bytes = _bounded_read(study_path, 32 * 1024 * 1024)
            raw_bytes = _bounded_read(raw_path, _MAX_RAW_BYTES)
            study = load_prediction_failure_forecast_preregistration(
                study_path, kernel=kernel, **study_inputs).declaration
            paths = {p.resolve() for p, _ in chain_inputs} | {study_path.resolve(), raw_path.resolve()}
            try:
                yield _expected(study, study_bytes, raw_bytes), paths
            finally:
                if (study_bytes != _bounded_read(study_path, 32 * 1024 * 1024)
                    or raw_bytes != _bounded_read(raw_path, _MAX_RAW_BYTES)):
                    raise ValueError("Measurement intake sources changed during the operation.")
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise PredictionFailureMeasurementIntakeIntegrityError(str(exc)) from exc


def save_prediction_failure_measurement_intake(path, envelope, **sources):
    with _context(**sources) as (expected, input_paths):
        if Path(path).resolve() in input_paths:
            raise ValueError("Measurement intake needs a separate output path.")
        checked = PredictionFailureMeasurementIntakeEnvelope.model_validate(envelope.model_dump(mode="json"))
        if checked.receipt != expected:
            raise ValueError("Measurement intake lost exact raw/study provenance.")
        _write_immutable(Path(path), prediction_failure_measurement_intake_bytes(checked))
        return checked.receipt.receipt_id


def load_prediction_failure_measurement_intake(path, **sources):
    with _context(**sources) as (expected, _paths):
        envelope = read_prediction_failure_measurement_intake(path)
        if envelope.receipt != expected:
            raise ValueError("Measurement intake lost exact raw/study provenance.")
        return envelope


class PredictionFailureMeasurementIntake:
    """Import candidate readings without scoring, execution or evidence admission."""

    def ingest(self, path, **sources):
        with _context(**sources) as (expected, _paths):
            envelope = PredictionFailureMeasurementIntakeEnvelope.build(expected)
            save_prediction_failure_measurement_intake(path, envelope, **sources)
            return envelope
