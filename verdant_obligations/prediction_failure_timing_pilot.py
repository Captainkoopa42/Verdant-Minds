"""Explicit, quarantined timings of an existing read-only risk-bundle call.

Clock readings are preserved, not reproducible durations or physical harm.
Both roles run the complete unchanged three-arm evaluator on private copies.
"""
from __future__ import annotations

import base64
import platform
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .prediction_failure_forecast_preregistration import (
    _guard as _forecast_guard, load_prediction_failure_forecast_preregistration,
)
from .prediction_failure_measurement_intake import (
    PredictionFailureMeasurementIntake, PredictionFailureMeasurementIntakeEnvelope,
    _bounded_read, _parse_capture, _sha,
    load_prediction_failure_measurement_intake,
)
from .prediction_failure_risk_operator import PredictionFailureGovernanceRiskOperator
from .prediction_failure_trial_plans import _write_immutable

PREDICTION_FAILURE_TIMING_PILOT_VERSION = "prediction_failure_timing_pilot_v0.55"
PREDICTION_FAILURE_TIMING_PILOT_SIDECAR_SUFFIX = ".vtp"
_ROOT = Path(__file__).resolve().parent.parent
_SOURCE_PATHS = (
    "verdant_governance/pipeline.py", "verdant_kernel/kernel.py", "verdant_kernel/models.py",
    "verdant_obligations/prediction_failure_trial_preregistration.py",
    "verdant_obligations/prediction_failure_trial_plans.py",
    "verdant_obligations/prediction_failure_risk_operator.py",
    "verdant_obligations/prediction_failure_risk_sidecar.py",
    "verdant_obligations/prediction_failure_trial_runner.py",
    "verdant_obligations/prediction_failure_resolution_evidence.py",
    "verdant_obligations/prediction_failure_forecast_preregistration.py",
    "verdant_obligations/prediction_failure_measurement_intake.py",
    "verdant_obligations/prediction_failure_timing_pilot.py",
)
_INPUT_NAMES = (
    "forecast_study_path", "resolution_evidence_path", "completed_result_path",
    "risk_receipt_path", "plan_path", "preregistration_path",
)
_ORDER = tuple((block, role) for block in range(6)
               for role in (("baseline", "valid_null") if block % 2 == 0
                            else ("valid_null", "baseline")))
_PROTOCOL = dict(
    operation="PredictionFailureGovernanceRiskOperator.evaluate_complete_bundle",
    roles=["baseline", "valid_null"], pair_count=6,
    order="alternating_baseline_null_then_null_baseline",
    warmup_calls_per_role=1, private_canonical_copy_per_role=True,
    timing_window="invoke_wrapper_and_evaluate_including_reads_and_validation",
    elapsed_unit="ms", elapsed_formula="(end_ns - start_ns) / 1000000",
    clock="time.perf_counter_ns", output_match="exact_complete_risk_evaluation",
    interpretation="descriptive_performance_pilot_only",
    excludes="clone_setup_warmup_output_comparison_intake_publication",
    adaptive_sampling_permitted=False, duration_equality_required=False,
    performance_improvement_claim_permitted=False,
)
_FALSE_FLAGS = (
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "study_executed", "calibration_observed", "source_independence_proven",
    "independent_replication_observed", "simulation_budget_authorized",
    "canonical_commit_permitted", "resolution_contract_satisfied",
    "resolution_authority_enabled", "promotion_authority_enabled",
    "policy_rewrite_authority_enabled",
)
_Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
_Text = Annotated[StrictStr, Field(min_length=1, max_length=256)]
_Ns = Annotated[StrictInt, Field(ge=0)]


class PredictionFailureTimingPilotIntegrityError(RuntimeError):
    """Timing acquisition or stored provenance crossed its pilot boundary."""


class TimingSourceDigest(FrozenRecord):
    name: _Text
    sha256: _Digest


class TimingClock(FrozenRecord):
    api: Literal["time.perf_counter_ns"] = "time.perf_counter_ns"
    implementation: _Text
    monotonic: StrictBool
    adjustable: StrictBool
    resolution_seconds: Annotated[StrictFloat, Field(gt=0, allow_inf_nan=False)]

    @model_validator(mode="after")
    def check_clock(self):
        if not self.monotonic or self.adjustable:
            raise ValueError("Timing requires a monotonic, non-adjustable clock.")
        return self


class TimingEnvironment(FrozenRecord):
    python_version: _Text
    python_implementation: _Text
    platform: _Text
    machine: _Text
    acquisition_base_revision: Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{40}$")]


class TimingSample(FrozenRecord):
    block: Annotated[StrictInt, Field(ge=0, le=5)]
    role: Literal["baseline", "valid_null"]
    start_ns: _Ns
    end_ns: _Ns
    elapsed_ms: Annotated[StrictFloat, Field(gt=0, allow_inf_nan=False)]
    evaluation_ref: _Text
    evaluation_sha256: _Digest
    canonical_before: _Digest
    canonical_after: _Digest

    @model_validator(mode="after")
    def check_sample(self):
        if (self.end_ns <= self.start_ns
            or self.elapsed_ms != (self.end_ns - self.start_ns) / 1_000_000
            or self.canonical_before != self.canonical_after):
            raise ValueError("Timing sample lost elapsed arithmetic or isolation.")
        return self


def _acquisition_values(receipt):
    return receipt.model_dump(mode="json", exclude={"pilot_id", "acquisition_id", "intake"})


def _raw(values, acquisition_id):
    samples = values["samples"]
    return canonical_json_bytes(dict(
        capture_format="verdant-prediction-failure-raw-capture-v1",
        source=dict(
            source_ref=f"timing-pilot://{acquisition_id}", acquisition_id=acquisition_id,
            acquisition_method="time.perf_counter_ns around unchanged read-only full risk-bundle call",
            clock_ref="python.time.perf_counter_ns", reported_origin="unknown",
            action_class=values["action_class"], quantity="read_only_risk_bundle_elapsed", unit="ms"),
        capture_start_ns=samples[0]["start_ns"], capture_end_ns=samples[-1]["end_ns"],
        expected_sample_count=12,
        samples=[dict(sample_id=f'block-{s["block"]}:{s["role"]}',
                      decision_event_ref=values["source_decision_ref"],
                      captured_at_ns=s["end_ns"], unit="ms", value=s["elapsed_ms"])
                 for s in samples]))


class PredictionFailureTimingPilotReceipt(FrozenRecord):
    pilot_id: str
    acquisition_id: str
    pilot_version: Literal["prediction_failure_timing_pilot_v0.55"] = PREDICTION_FAILURE_TIMING_PILOT_VERSION
    protocol: dict
    input_sources: tuple[TimingSourceDigest, ...]
    code_sources: tuple[TimingSourceDigest, ...]
    clock: TimingClock
    environment: TimingEnvironment
    canonical_kernel_id: _Text
    canonical_fingerprint: _Digest
    action_class: _Text
    source_decision_ref: _Text
    source_proposal_ref: _Text
    source_report_ref: _Text
    evaluation_ref: _Text
    evaluation_sha256: _Digest
    samples: tuple[TimingSample, ...] = Field(min_length=12, max_length=12)
    intake: PredictionFailureMeasurementIntakeEnvelope
    purpose: Literal["measurement_protocol_pilot_only"] = "measurement_protocol_pilot_only"
    quarantined: StrictBool = True
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    study_executed: StrictBool = False
    calibration_observed: StrictBool = False
    source_independence_proven: StrictBool = False
    independent_replication_observed: StrictBool = False
    simulation_budget_authorized: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_contract_satisfied: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_receipt(self):
        if (canonical_json_bytes(self.protocol) != canonical_json_bytes(_PROTOCOL)
            or tuple(s.name for s in self.input_sources) != _INPUT_NAMES
            or tuple(s.name for s in self.code_sources) != _SOURCE_PATHS
            or tuple((s.block, s.role) for s in self.samples) != _ORDER
            or any(a.end_ns > b.start_ns for a, b in zip(self.samples, self.samples[1:]))
            or any((s.evaluation_ref, s.evaluation_sha256, s.canonical_before, s.canonical_after)
                   != (self.evaluation_ref, self.evaluation_sha256,
                       self.canonical_fingerprint, self.canonical_fingerprint) for s in self.samples)
            or not self.quarantined or any(getattr(self, f) for f in _FALSE_FLAGS)):
            raise ValueError("Timing pilot lost its fixed controls or quarantine.")
        values = _acquisition_values(self)
        if self.acquisition_id != stable_id("prediction_failure_timing_acquisition", values):
            raise ValueError("Timing acquisition checksum mismatch.")
        raw = _raw(values, self.acquisition_id)
        r = self.intake.receipt
        if (base64.b64decode(r.raw_capture_base64, validate=True) != raw
            or r.capture != _parse_capture(raw)
            or r.study_sha256 != self.input_sources[0].sha256
            or r.canonical_kernel_id != self.canonical_kernel_id
            or r.canonical_fingerprint != self.canonical_fingerprint
            or r.action_class != self.action_class
            or r.historical_sample_decision_refs != (self.source_decision_ref,)
            or r.unverified_sample_decision_refs):
            raise ValueError("Timing readings lost their exact quarantined intake.")
        if self.pilot_id != stable_id("prediction_failure_timing_pilot",
                self.model_dump(mode="json", exclude={"pilot_id"})):
            raise ValueError("Timing pilot checksum mismatch.")
        return self


class PredictionFailureTimingPilotEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-prediction-failure-timing-pilot-v1"] = "verdant-prediction-failure-timing-pilot-v1"
    receipt: PredictionFailureTimingPilotReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = PredictionFailureTimingPilotReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=_sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_envelope(self):
        if self.receipt_sha256 != _sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Timing envelope checksum mismatch.")
        return self


def prediction_failure_timing_pilot_bytes(envelope):
    checked = PredictionFailureTimingPilotEnvelope.model_validate(envelope.model_dump(mode="json"))
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > 8 * 1024 * 1024:
        raise PredictionFailureTimingPilotIntegrityError("Timing sidecar exceeds its size limit.")
    return data


def read_prediction_failure_timing_pilot(path):
    """Local consistency only: hashes do not authenticate a measurement source."""
    try:
        data = _bounded_read(path, 8 * 1024 * 1024)
        envelope = PredictionFailureTimingPilotEnvelope.model_validate_json(data)
        if prediction_failure_timing_pilot_bytes(envelope) != data:
            raise ValueError("Timing sidecar is not canonical.")
        return envelope
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        raise PredictionFailureTimingPilotIntegrityError(str(exc)) from exc


def _code_manifest():
    return tuple(TimingSourceDigest(name=p, sha256=_sha((_ROOT / p).read_bytes())) for p in _SOURCE_PATHS)


@contextmanager
def _context(kernel, forecast_study_path, **inputs):
    try:
        with _forecast_guard(kernel, **inputs) as (chain, _native_manifest):
            study_path = Path(forecast_study_path)
            study_bytes = _bounded_read(study_path, 32 * 1024 * 1024)
            manifest = _code_manifest()
            before = kernel.fingerprint()
            study = load_prediction_failure_forecast_preregistration(
                study_path, kernel=kernel, **inputs).declaration
            sources = ((study_path, study_bytes), *chain)
            digests = tuple(TimingSourceDigest(name=n, sha256=_sha(b))
                            for n, (_p, b) in zip(_INPUT_NAMES, sources))

            def unchanged():
                if (kernel.fingerprint() != before or _code_manifest() != manifest
                    or any(p.read_bytes() != b for p, b in sources)):
                    raise ValueError("Timing canonical state, code or sources changed.")

            try:
                yield study, digests, manifest, {p.resolve() for p, _ in sources}, unchanged
            finally:
                unchanged()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        raise PredictionFailureTimingPilotIntegrityError(str(exc)) from exc


def _check_provenance(receipt, study, digests, manifest):
    old = study.anchor.completed_result.risk_receipt
    evidence = study.anchor.declaration.hypothesis_bundle.evidence_receipt
    expected = old.evaluation
    if (receipt.input_sources != digests or receipt.code_sources != manifest
        or receipt.canonical_kernel_id != study.canonical_kernel_id
        or receipt.canonical_fingerprint != study.canonical_fingerprint
        or receipt.action_class != study.action_class
        or receipt.source_decision_ref != evidence.prediction_source_ref
        or receipt.source_proposal_ref != evidence.proposal_ref
        or receipt.source_report_ref != evidence.council_report_ref
        or receipt.evaluation_ref != expected.evaluation_id
        or receipt.evaluation_sha256 != _sha(canonical_json_bytes(expected.model_dump(mode="json")))
        or receipt.intake.receipt.study_ref != study.declaration_id):
        raise ValueError("Timing pilot lost exact input, output or decision lineage.")


def load_prediction_failure_timing_pilot(path, *, kernel, forecast_study_path, **inputs):
    """Validate stored timing and lineage, without new clock samples or charges."""
    with _context(kernel, forecast_study_path, **inputs) as (study, digests, manifest, _paths, _unchanged):
        envelope = read_prediction_failure_timing_pilot(path)
        _check_provenance(envelope.receipt, study, digests, manifest)
        # Reuse v0.54's provenance-aware loader; temporary members are not published.
        with tempfile.TemporaryDirectory(prefix="verdant-timing-replay-") as directory:
            raw_path, intake_path = Path(directory) / "raw.json", Path(directory) / "intake.vmi"
            raw_path.write_bytes(base64.b64decode(envelope.receipt.intake.receipt.raw_capture_base64))
            intake_path.write_bytes(canonical_json_bytes(envelope.receipt.intake.model_dump(mode="json")))
            if load_prediction_failure_measurement_intake(intake_path, kernel=kernel,
                    forecast_study_path=forecast_study_path, raw_capture_path=raw_path, **inputs) != envelope.receipt.intake:
                raise ValueError("Timing intake replay drifted.")
        return envelope


def _clock():
    info = time.get_clock_info("perf_counter")
    return TimingClock(implementation=info.implementation, monotonic=info.monotonic,
                       adjustable=info.adjustable, resolution_seconds=info.resolution)


def _environment():
    revision = subprocess.run(["git", "-C", str(_ROOT), "rev-parse", "HEAD"],
                              check=True, capture_output=True, text=True).stdout.strip()
    return TimingEnvironment(python_version=platform.python_version(),
        python_implementation=platform.python_implementation(), platform=platform.platform(),
        machine=platform.machine(), acquisition_base_revision=revision)


def _invoke(kernel, plan_path, preregistration_path):
    return PredictionFailureGovernanceRiskOperator().evaluate(
        kernel=kernel, plan_path=plan_path, preregistration_path=preregistration_path)


class PredictionFailureTimingPilot:
    """Acquire one fixed paired pilot, or replay an existing immutable result."""

    def acquire(self, path, *, kernel, forecast_study_path, **inputs):
        path = Path(path)
        with _context(kernel, forecast_study_path, **inputs) as (study, digests, manifest, paths, unchanged):
            if path.resolve() in paths:
                raise ValueError("Timing acquisition needs a separate output path.")
            if path.exists():
                return load_prediction_failure_timing_pilot(path, kernel=kernel,
                    forecast_study_path=forecast_study_path, **inputs)
            old = study.anchor.completed_result.risk_receipt
            expected = old.evaluation
            expected_sha = _sha(canonical_json_bytes(expected.model_dump(mode="json")))
            copies = {role: VerdantKernel.from_state(kernel.snapshot()) for role in ("baseline", "valid_null")}
            clock, environment = _clock(), _environment()

            def invoke(role):
                return _invoke(copies[role], inputs["plan_path"], inputs["preregistration_path"])

            def verify(role, result):
                if result != expected or copies[role].fingerprint() != study.canonical_fingerprint:
                    raise ValueError("Timing operation changed its output or private canonical copy.")

            for role in copies:
                verify(role, invoke(role))
            samples = []
            for block, role in _ORDER:
                before = copies[role].fingerprint()
                start = time.perf_counter_ns()
                result = invoke(role)
                end = time.perf_counter_ns()
                verify(role, result)
                samples.append(TimingSample(block=block, role=role, start_ns=start, end_ns=end,
                    elapsed_ms=(end - start) / 1_000_000, evaluation_ref=result.evaluation_id,
                    evaluation_sha256=expected_sha, canonical_before=before,
                    canonical_after=copies[role].fingerprint()))
            values = dict(pilot_version=PREDICTION_FAILURE_TIMING_PILOT_VERSION, protocol=_PROTOCOL,
                input_sources=[s.model_dump(mode="json") for s in digests],
                code_sources=[s.model_dump(mode="json") for s in manifest],
                clock=clock.model_dump(mode="json"), environment=environment.model_dump(mode="json"),
                canonical_kernel_id=study.canonical_kernel_id, canonical_fingerprint=study.canonical_fingerprint,
                action_class=study.action_class,
                source_decision_ref=study.anchor.declaration.hypothesis_bundle.evidence_receipt.prediction_source_ref,
                source_proposal_ref=study.anchor.declaration.hypothesis_bundle.evidence_receipt.proposal_ref,
                source_report_ref=study.anchor.declaration.hypothesis_bundle.evidence_receipt.council_report_ref,
                evaluation_ref=expected.evaluation_id, evaluation_sha256=expected_sha,
                samples=[s.model_dump(mode="json") for s in samples],
                purpose="measurement_protocol_pilot_only", quarantined=True,
                **{f: False for f in _FALSE_FLAGS})
            acquisition_id = stable_id("prediction_failure_timing_acquisition", values)
            with tempfile.TemporaryDirectory(prefix="verdant-timing-acquire-") as directory:
                raw_path = Path(directory) / "raw.json"
                raw_path.write_bytes(_raw(values, acquisition_id))
                intake = PredictionFailureMeasurementIntake().ingest(Path(directory) / "intake.vmi",
                    kernel=kernel, forecast_study_path=forecast_study_path, raw_capture_path=raw_path, **inputs)
            values.update(acquisition_id=acquisition_id, intake=intake.model_dump(mode="json"))
            receipt = PredictionFailureTimingPilotReceipt(
                pilot_id=stable_id("prediction_failure_timing_pilot", values), **values)
            envelope = PredictionFailureTimingPilotEnvelope.build(receipt)
            _check_provenance(receipt, study, digests, manifest)
            unchanged()
            _write_immutable(path, prediction_failure_timing_pilot_bytes(envelope))
            return envelope
