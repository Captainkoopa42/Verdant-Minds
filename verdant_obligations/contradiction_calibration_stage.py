"""Crash-safe calibration handoff for two-phase Contradiction trials.

This module is an explicitly invoked v0.40 extension of the v0.39
calibration-frozen dimension criterion.  It executes only the calibration
split, derives the frozen criterion, and commits a self-contained stage
sidecar before any held-out runtime is accepted.  A later process can validate
that sidecar against both preregistered canonical contexts and the unchanged
Lens lineage, reconstruct the exact calibration simulation ledger, and then
run the held-out split from a pristine ledger.

The sidecar is experimental evidence outside VDK/VOB.  Its local POSIX writer
lock provides first-committer-wins arbitration, idempotent same-stage writes,
stale-temporary recovery, atomic replacement, and directory sync.  It does not
establish power-loss, network-filesystem, Windows, hostile-path, or distributed
durability, and it grants no truth, resolution, promotion, or canonical-write
authority.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - the non-POSIX branch is exercised by validation.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from pydantic import BaseModel, ConfigDict, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .contradiction_dimension_criterion import (
    ContradictionCalibrationCriterionDeriver,
    ContradictionCalibrationDimensionCriterion,
    ContradictionDimensionCriterionDeclaration,
    ContradictionDimensionCriterionIntegrityError,
    ContradictionDimensionCriterionObserver,
    ContradictionDimensionEvaluationReceipt,
)
from .contradiction_hypotheses import (
    ContradictionHypothesisIntegrityError,
    ContradictionHypothesisProtocol,
)
from .contradiction_lens_control import (
    ContradictionLensControlledProbeRunner,
    ContradictionLensControlledRun,
    ContradictionLensControlIntegrityError,
)
from .contradiction_trial_controls import (
    ContradictionLensHeldOutReplicationReceipt,
    ContradictionLensTrialContext,
    ContradictionLensTrialObservation,
    ContradictionLensTrialPairContext,
    ContradictionLensTrialSplit,
    ContradictionLensTrialIntegrityError,
    _validate_observation_ledger,
)
from .counterfactual import (
    CounterfactualRuntime,
    SimulationIntegrityError,
    SimulationLedger,
    SimulationLedgerState,
)
from .equivalence import EquivalenceLensSystem, LensIntegrityError


CONTRADICTION_CALIBRATION_STAGE_VERSION = (
    "contradiction_calibration_stage_v0.40"
)
CONTRADICTION_CALIBRATION_STAGE_SIDECAR_FORMAT = (
    "verdant-contradiction-calibration-stage-v1"
)
_MAX_CALIBRATION_STAGE_BYTES = 128 * 1024 * 1024
_EMPTY_SIMULATION_FINGERPRINT = SimulationLedger().fingerprint()


class ContradictionCalibrationStageIntegrityError(RuntimeError):
    """Raised when a durable calibration stage loses exact split lineage."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _record_payload(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.model_dump(mode="json")
        if isinstance(value, BaseModel)
        else value
        for key, value in values.items()
    }


def _calibration_trace_refs(
    observation: ContradictionLensTrialObservation,
) -> tuple[tuple[str, str], tuple[str, str]]:
    matched = (
        observation.lens_observation.functional_observation
        .provenance_observation.matched_observation
    )
    return (
        (matched.baseline.reservation_id, matched.treatment.reservation_id),
        (matched.baseline.settlement_id, matched.treatment.settlement_id),
    )


class ContradictionCalibrationStageReceipt(FrozenRecord):
    """Content-addressed calibration evidence with no held-out observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage_receipt_id: str
    stage_version: str = CONTRADICTION_CALIBRATION_STAGE_VERSION
    pair_context: ContradictionLensTrialPairContext
    declaration: ContradictionDimensionCriterionDeclaration
    calibration_observation: ContradictionLensTrialObservation
    criterion: ContradictionCalibrationDimensionCriterion
    pair_context_ref: str
    calibration_context_ref: str
    held_out_context_ref: str
    matched_control_signature: str
    lens_fingerprint: str
    calibration_reservation_refs: tuple[str, str]
    calibration_settlement_refs: tuple[str, str]
    calibration_pre_simulation_fingerprint: str
    calibration_simulation_fingerprint: str
    required_held_out_pre_simulation_fingerprint: str
    calibration_only: bool = True
    matched_controls_unchanged: bool = True
    complete_calibration_ledger_embedded: bool = True
    held_out_execution_started: bool = False
    held_out_trace_consulted: bool = False
    simulated_only: bool = True
    dimensional_separation_observed: bool = False
    predictive_discrimination_observed: bool = False
    independent_held_out_replication_observed: bool = False
    external_outcome_observed: bool = False
    resolution_trial_ready: bool = False
    truth_selection_authority_enabled: bool = False
    observed_outcome_authority_enabled: bool = False
    resolution_authority_enabled: bool = False
    canonical_commit_permitted: bool = False

    @classmethod
    def build(
        cls,
        *,
        pair_context: ContradictionLensTrialPairContext,
        declaration: ContradictionDimensionCriterionDeclaration,
        calibration_observation: ContradictionLensTrialObservation,
        criterion: ContradictionCalibrationDimensionCriterion,
        calibration_ledger: SimulationLedger,
    ) -> "ContradictionCalibrationStageReceipt":
        pair = ContradictionLensTrialPairContext.model_validate(
            pair_context.model_dump(mode="json")
        )
        declared = ContradictionDimensionCriterionDeclaration.model_validate(
            declaration.model_dump(mode="json")
        )
        observation = ContradictionLensTrialObservation.model_validate(
            calibration_observation.model_dump(mode="json")
        )
        frozen = ContradictionCalibrationDimensionCriterion.model_validate(
            criterion.model_dump(mode="json")
        )
        reservation_refs, settlement_refs = _calibration_trace_refs(observation)
        values = {
            "stage_version": CONTRADICTION_CALIBRATION_STAGE_VERSION,
            "pair_context": pair,
            "declaration": declared,
            "calibration_observation": observation,
            "criterion": frozen,
            "pair_context_ref": pair.pair_id,
            "calibration_context_ref": pair.calibration.context_id,
            "held_out_context_ref": pair.held_out.context_id,
            "matched_control_signature": pair.matched_control_signature,
            "lens_fingerprint": pair.lens_fingerprint,
            "calibration_reservation_refs": reservation_refs,
            "calibration_settlement_refs": settlement_refs,
            "calibration_pre_simulation_fingerprint": (
                _EMPTY_SIMULATION_FINGERPRINT
            ),
            "calibration_simulation_fingerprint": calibration_ledger.fingerprint(),
            "required_held_out_pre_simulation_fingerprint": (
                _EMPTY_SIMULATION_FINGERPRINT
            ),
            "calibration_only": True,
            "matched_controls_unchanged": True,
            "complete_calibration_ledger_embedded": True,
            "held_out_execution_started": False,
            "held_out_trace_consulted": False,
            "simulated_only": True,
            "dimensional_separation_observed": False,
            "predictive_discrimination_observed": False,
            "independent_held_out_replication_observed": False,
            "external_outcome_observed": False,
            "resolution_trial_ready": False,
            "truth_selection_authority_enabled": False,
            "observed_outcome_authority_enabled": False,
            "resolution_authority_enabled": False,
            "canonical_commit_permitted": False,
        }
        values["stage_receipt_id"] = stable_id(
            "contradiction_calibration_stage_receipt",
            _record_payload(values),
        )
        return cls(**values)

    @model_validator(mode="after")
    def validate_receipt(self) -> "ContradictionCalibrationStageReceipt":
        if self.stage_version != CONTRADICTION_CALIBRATION_STAGE_VERSION:
            raise ValueError("Unknown Contradiction calibration-stage version.")
        reservation_refs, settlement_refs = _calibration_trace_refs(
            self.calibration_observation
        )
        expected = {
            "pair_context_ref": self.pair_context.pair_id,
            "calibration_context_ref": self.pair_context.calibration.context_id,
            "held_out_context_ref": self.pair_context.held_out.context_id,
            "matched_control_signature": (
                self.pair_context.matched_control_signature
            ),
            "lens_fingerprint": self.pair_context.lens_fingerprint,
            "calibration_reservation_refs": reservation_refs,
            "calibration_settlement_refs": settlement_refs,
        }
        if any(getattr(self, key) != value for key, value in expected.items()):
            raise ValueError("Calibration stage altered its preregistered lineage.")
        if (
            self.declaration
            != ContradictionDimensionCriterionDeclaration.build(self.pair_context)
            or self.calibration_observation.context != self.pair_context.calibration
            or self.criterion
            != ContradictionCalibrationDimensionCriterion.build(
                self.declaration,
                self.calibration_observation,
            )
        ):
            raise ValueError("Calibration stage criterion is not reproducible.")
        if (
            self.calibration_pre_simulation_fingerprint
            != _EMPTY_SIMULATION_FINGERPRINT
            or self.required_held_out_pre_simulation_fingerprint
            != _EMPTY_SIMULATION_FINGERPRINT
            or not _is_sha256(self.calibration_simulation_fingerprint)
        ):
            raise ValueError("Calibration stage changed its ledger boundary.")
        if (
            not self.calibration_only
            or not self.matched_controls_unchanged
            or not self.complete_calibration_ledger_embedded
            or self.held_out_execution_started
            or self.held_out_trace_consulted
            or not self.simulated_only
            or self.dimensional_separation_observed
            or self.predictive_discrimination_observed
            or self.independent_held_out_replication_observed
            or self.external_outcome_observed
            or self.resolution_trial_ready
            or self.truth_selection_authority_enabled
            or self.observed_outcome_authority_enabled
            or self.resolution_authority_enabled
            or self.canonical_commit_permitted
        ):
            raise ValueError("Calibration stage crossed its evidence boundary.")
        payload = self.model_dump(mode="json", exclude={"stage_receipt_id"})
        if self.stage_receipt_id != stable_id(
            "contradiction_calibration_stage_receipt", payload
        ):
            raise ValueError("Calibration-stage receipt checksum mismatch.")
        return self


class ContradictionCalibrationStageSidecarEnvelope(BaseModel):
    """Canonical stage sidecar containing complete calibration ledger state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: str = CONTRADICTION_CALIBRATION_STAGE_SIDECAR_FORMAT
    stage_receipt_sha256: str
    calibration_simulation_state_sha256: str
    stage_receipt: ContradictionCalibrationStageReceipt
    calibration_simulation_state: SimulationLedgerState

    @classmethod
    def build(
        cls,
        stage_receipt: ContradictionCalibrationStageReceipt,
        calibration_ledger: SimulationLedger,
    ) -> "ContradictionCalibrationStageSidecarEnvelope":
        receipt = ContradictionCalibrationStageReceipt.model_validate(
            stage_receipt.model_dump(mode="json")
        )
        state = calibration_ledger.snapshot()
        return cls(
            stage_receipt_sha256=_digest(
                canonical_json_bytes(receipt.model_dump(mode="json"))
            ),
            calibration_simulation_state_sha256=_digest(
                canonical_json_bytes(state.model_dump(mode="json"))
            ),
            stage_receipt=receipt,
            calibration_simulation_state=state,
        )

    @model_validator(mode="after")
    def validate_envelope(
        self,
    ) -> "ContradictionCalibrationStageSidecarEnvelope":
        if self.format_version != CONTRADICTION_CALIBRATION_STAGE_SIDECAR_FORMAT:
            raise ValueError("Unsupported Contradiction calibration-stage format.")
        receipt_bytes = canonical_json_bytes(
            self.stage_receipt.model_dump(mode="json")
        )
        state_bytes = canonical_json_bytes(
            self.calibration_simulation_state.model_dump(mode="json")
        )
        if (
            self.stage_receipt_sha256 != _digest(receipt_bytes)
            or self.calibration_simulation_state_sha256 != _digest(state_bytes)
            or self.stage_receipt.calibration_simulation_fingerprint
            != self.calibration_simulation_state.fingerprint()
        ):
            raise ValueError("Contradiction calibration-stage checksum mismatch.")
        return self


@dataclass(frozen=True)
class ContradictionCalibrationStageRun:
    path: Path
    envelope: ContradictionCalibrationStageSidecarEnvelope
    calibration_run: ContradictionLensControlledRun

    @property
    def criterion(self) -> ContradictionCalibrationDimensionCriterion:
        return self.envelope.stage_receipt.criterion


@dataclass(frozen=True)
class ContradictionResumedDimensionTrialRun:
    stage_path: Path
    stage: ContradictionCalibrationStageSidecarEnvelope
    calibration_ledger: SimulationLedger
    held_out_run: ContradictionLensControlledRun
    replication_receipt: ContradictionLensHeldOutReplicationReceipt
    evaluation: ContradictionDimensionEvaluationReceipt

    @property
    def criterion(self) -> ContradictionCalibrationDimensionCriterion:
        return self.stage.stage_receipt.criterion


def contradiction_calibration_stage_sidecar_bytes(
    envelope: ContradictionCalibrationStageSidecarEnvelope,
) -> bytes:
    validated = ContradictionCalibrationStageSidecarEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_CALIBRATION_STAGE_BYTES:
        raise ContradictionCalibrationStageIntegrityError(
            "Contradiction calibration stage exceeds its size limit."
        )
    return data


def read_contradiction_calibration_stage_sidecar(
    path: str | Path,
) -> ContradictionCalibrationStageSidecarEnvelope:
    """Intrinsically validate one canonical stage sidecar without authority."""

    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_CALIBRATION_STAGE_BYTES:
            raise ContradictionCalibrationStageIntegrityError(
                "Contradiction calibration stage exceeds its size limit."
            )
        envelope = ContradictionCalibrationStageSidecarEnvelope.model_validate_json(
            data
        )
        if contradiction_calibration_stage_sidecar_bytes(envelope) != data:
            raise ContradictionCalibrationStageIntegrityError(
                "Contradiction calibration stage JSON is not canonical."
            )
        return envelope
    except ContradictionCalibrationStageIntegrityError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ContradictionCalibrationStageIntegrityError(
            "Invalid Contradiction calibration-stage sidecar."
        ) from exc


def _validate_pair_context(
    pair: ContradictionLensTrialPairContext,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> None:
    protocol = hypothesis_protocol or ContradictionHypothesisProtocol()
    expected_calibration = ContradictionLensTrialContext.build(
        calibration_kernel,
        pair.calibration.controlled_context.functional_context.hypothesis_bundle,
        lenses,
        split=ContradictionLensTrialSplit.CALIBRATION,
        source_event_key=pair.calibration.controlled_context.source_event_key,
        hypothesis_protocol=protocol,
    )
    expected_held_out = ContradictionLensTrialContext.build(
        held_out_kernel,
        pair.held_out.controlled_context.functional_context.hypothesis_bundle,
        lenses,
        split=ContradictionLensTrialSplit.HELD_OUT,
        source_event_key=pair.held_out.controlled_context.source_event_key,
        hypothesis_protocol=protocol,
    )
    expected_pair = ContradictionLensTrialPairContext.build(
        calibration=expected_calibration,
        held_out=expected_held_out,
    )
    if pair != expected_pair:
        raise ContradictionCalibrationStageIntegrityError(
            "Calibration stage is paired with stale or substituted controls."
        )


def _validate_stage_pairing(
    envelope: ContradictionCalibrationStageSidecarEnvelope,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> SimulationLedger:
    receipt = envelope.stage_receipt
    pair = receipt.pair_context
    if (
        pair.calibration.canonical_checkpoint_fingerprint
        != calibration_kernel.fingerprint()
        or pair.held_out.canonical_checkpoint_fingerprint
        != held_out_kernel.fingerprint()
        or pair.lens_fingerprint != lenses.fingerprint()
    ):
        raise ContradictionCalibrationStageIntegrityError(
            "Calibration stage is paired with different protected state."
        )
    _validate_pair_context(
        pair,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    ledger = SimulationLedger.from_state(envelope.calibration_simulation_state)
    if ledger.fingerprint() != receipt.calibration_simulation_fingerprint:
        raise ContradictionCalibrationStageIntegrityError(
            "Calibration stage is paired with different simulation state."
        )
    _validate_observation_ledger(
        calibration_kernel,
        ledger,
        receipt.calibration_observation,
    )
    reservation_ids = tuple(
        item.reservation_id for item in ledger.state.reservations
    )
    settlement_ids = tuple(item.settlement_id for item in ledger.state.settlements)
    if (
        len(reservation_ids) != 2
        or len(settlement_ids) != 2
        or set(reservation_ids) != set(receipt.calibration_reservation_refs)
        or set(settlement_ids) != set(receipt.calibration_settlement_refs)
    ):
        raise ContradictionCalibrationStageIntegrityError(
            "Calibration stage embedded uncontrolled simulation evidence."
        )
    return ledger


def load_contradiction_calibration_stage_sidecar(
    path: str | Path,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> ContradictionCalibrationStageSidecarEnvelope:
    """Revalidate a stage against both contexts and its complete ledger."""

    try:
        envelope = read_contradiction_calibration_stage_sidecar(path)
        _validate_stage_pairing(
            envelope,
            calibration_kernel=calibration_kernel,
            held_out_kernel=held_out_kernel,
            lenses=lenses,
            hypothesis_protocol=hypothesis_protocol,
        )
        return envelope
    except ContradictionCalibrationStageIntegrityError:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise ContradictionCalibrationStageIntegrityError(str(exc)) from exc


def _stage_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _remove_stale_stage_temporaries(path: Path) -> None:
    for candidate in path.parent.glob(f".{path.name}.*.tmp"):
        candidate.unlink(missing_ok=True)


def save_contradiction_calibration_stage_sidecar(
    path: str | Path,
    envelope: ContradictionCalibrationStageSidecarEnvelope,
    *,
    calibration_kernel: VerdantKernel,
    held_out_kernel: VerdantKernel,
    lenses: EquivalenceLensSystem,
    hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
) -> str:
    """Commit one immutable stage under a process-shared POSIX writer lock.

    The first complete stage committed to a path owns that path.  Rewriting the
    identical stage is idempotent; a different stage is rejected rather than
    replacing already published calibration evidence.
    """

    if os.name != "posix" or fcntl is None:
        raise ContradictionCalibrationStageIntegrityError(
            "Calibration-stage writer arbitration requires POSIX flock support."
        )
    validated = ContradictionCalibrationStageSidecarEnvelope.model_validate(
        envelope.model_dump(mode="json")
    )
    _validate_stage_pairing(
        validated,
        calibration_kernel=calibration_kernel,
        held_out_kernel=held_out_kernel,
        lenses=lenses,
        hypothesis_protocol=hypothesis_protocol,
    )
    data = contradiction_calibration_stage_sidecar_bytes(validated)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_file_descriptor = os.open(
        _stage_lock_path(target),
        os.O_RDWR | os.O_CREAT,
        0o600,
    )
    try:
        fcntl.flock(lock_file_descriptor, fcntl.LOCK_EX)
        _remove_stale_stage_temporaries(target)
        if target.exists():
            current = read_contradiction_calibration_stage_sidecar(target)
            current_data = contradiction_calibration_stage_sidecar_bytes(current)
            if current_data == data:
                return validated.stage_receipt.stage_receipt_id
            raise ContradictionCalibrationStageIntegrityError(
                "Calibration-stage path already committed a different receipt."
            )
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
            directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
            directory_fd = os.open(target.parent, directory_flags)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return validated.stage_receipt.stage_receipt_id
    finally:
        try:
            fcntl.flock(lock_file_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(lock_file_descriptor)


class ContradictionDurableDimensionTrialRunner:
    """Persist calibration first, then resume held-out work from that artifact."""

    def __init__(
        self,
        *,
        controlled_runner: ContradictionLensControlledProbeRunner | None = None,
        criterion_deriver: ContradictionCalibrationCriterionDeriver | None = None,
        criterion_observer: ContradictionDimensionCriterionObserver | None = None,
        hypothesis_protocol: ContradictionHypothesisProtocol | None = None,
    ) -> None:
        self.hypothesis_protocol = (
            hypothesis_protocol or ContradictionHypothesisProtocol()
        )
        self.controlled_runner = (
            controlled_runner
            or ContradictionLensControlledProbeRunner(
                hypothesis_protocol=self.hypothesis_protocol
            )
        )
        self.criterion_deriver = (
            criterion_deriver or ContradictionCalibrationCriterionDeriver()
        )
        self.criterion_observer = (
            criterion_observer or ContradictionDimensionCriterionObserver()
        )

    def prepare_and_persist(
        self,
        path: str | Path,
        calibration_kernel: VerdantKernel,
        calibration_runtime: CounterfactualRuntime,
        held_out_kernel: VerdantKernel,
        lenses: EquivalenceLensSystem,
        *,
        pair_context: ContradictionLensTrialPairContext,
        criterion_declaration: ContradictionDimensionCriterionDeclaration,
    ) -> ContradictionCalibrationStageRun:
        """Execute calibration only and commit it before held-out is possible."""

        if calibration_kernel is held_out_kernel:
            raise ContradictionCalibrationStageIntegrityError(
                "Calibration stage requires separate canonical kernels."
            )
        canonical_before = (
            calibration_kernel.fingerprint(),
            held_out_kernel.fingerprint(),
        )
        lens_before = lenses.fingerprint()
        simulation_before = calibration_runtime.ledger.fingerprint()
        original_calibration = calibration_runtime.ledger.snapshot()
        published = False
        try:
            if simulation_before != _EMPTY_SIMULATION_FINGERPRINT:
                raise ContradictionCalibrationStageIntegrityError(
                    "Calibration stage requires a pristine simulation ledger."
                )
            pair = ContradictionLensTrialPairContext.model_validate(
                pair_context.model_dump(mode="json")
            )
            declaration = ContradictionDimensionCriterionDeclaration.model_validate(
                criterion_declaration.model_dump(mode="json")
            )
            _validate_pair_context(
                pair,
                calibration_kernel=calibration_kernel,
                held_out_kernel=held_out_kernel,
                lenses=lenses,
                hypothesis_protocol=self.hypothesis_protocol,
            )
            if declaration != ContradictionDimensionCriterionDeclaration.build(pair):
                raise ContradictionCalibrationStageIntegrityError(
                    "Calibration-stage declaration is stale or substituted."
                )
            working_runtime = CounterfactualRuntime()
            calibration_bundle = (
                pair.calibration.controlled_context.functional_context
                .hypothesis_bundle
            )
            calibration_run = self.controlled_runner.run(
                calibration_kernel,
                working_runtime,
                lenses,
                bundle=calibration_bundle,
                controlled_context=pair.calibration.controlled_context,
                source_event_key=(
                    pair.calibration.controlled_context.source_event_key
                ),
            )
            observation = ContradictionLensTrialObservation.build(
                context=pair.calibration,
                run=calibration_run,
            )
            criterion = self.criterion_deriver.derive(declaration, observation)
            receipt = ContradictionCalibrationStageReceipt.build(
                pair_context=pair,
                declaration=declaration,
                calibration_observation=observation,
                criterion=criterion,
                calibration_ledger=working_runtime.ledger,
            )
            envelope = ContradictionCalibrationStageSidecarEnvelope.build(
                receipt,
                working_runtime.ledger,
            )
            save_contradiction_calibration_stage_sidecar(
                path,
                envelope,
                calibration_kernel=calibration_kernel,
                held_out_kernel=held_out_kernel,
                lenses=lenses,
                hypothesis_protocol=self.hypothesis_protocol,
            )
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
                or lenses.fingerprint() != lens_before
            ):
                raise ContradictionCalibrationStageIntegrityError(
                    "Calibration stage crossed a protected ledger."
                )
            calibration_runtime.ledger.state = (
                envelope.calibration_simulation_state.model_copy(deep=True)
            )
            published = True
            return ContradictionCalibrationStageRun(
                path=Path(path),
                envelope=envelope,
                calibration_run=calibration_run,
            )
        except ContradictionCalibrationStageIntegrityError:
            raise
        except (
            ContradictionDimensionCriterionIntegrityError,
            ContradictionHypothesisIntegrityError,
            ContradictionLensControlIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionCalibrationStageIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError("Calibration stage mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Calibration stage mutated its Lens sidecar.")
            if (
                not published
                and calibration_runtime.ledger.fingerprint() != simulation_before
            ):
                calibration_runtime.ledger.state = original_calibration
                raise RuntimeError(
                    "Failed calibration stage published partial simulation state."
                )

    def resume_from_stage(
        self,
        path: str | Path,
        calibration_kernel: VerdantKernel,
        held_out_kernel: VerdantKernel,
        held_out_runtime: CounterfactualRuntime,
        lenses: EquivalenceLensSystem,
    ) -> ContradictionResumedDimensionTrialRun:
        """Run held-out work only after loading the durable calibration stage."""

        canonical_before = (
            calibration_kernel.fingerprint(),
            held_out_kernel.fingerprint(),
        )
        lens_before = lenses.fingerprint()
        held_out_before = held_out_runtime.ledger.fingerprint()
        original_held_out = held_out_runtime.ledger.snapshot()
        stage_bytes_before = Path(path).read_bytes()
        published = False
        try:
            stage = load_contradiction_calibration_stage_sidecar(
                path,
                calibration_kernel=calibration_kernel,
                held_out_kernel=held_out_kernel,
                lenses=lenses,
                hypothesis_protocol=self.hypothesis_protocol,
            )
            receipt = stage.stage_receipt
            if (
                held_out_before
                != receipt.required_held_out_pre_simulation_fingerprint
            ):
                raise ContradictionCalibrationStageIntegrityError(
                    "Held-out resume requires its pristine preregistered ledger."
                )
            pair = receipt.pair_context
            held_out_bundle = (
                pair.held_out.controlled_context.functional_context
                .hypothesis_bundle
            )
            working_runtime = CounterfactualRuntime(
                SimulationLedger.from_state(original_held_out)
            )
            held_out_run = self.controlled_runner.run(
                held_out_kernel,
                working_runtime,
                lenses,
                bundle=held_out_bundle,
                controlled_context=pair.held_out.controlled_context,
                source_event_key=pair.held_out.controlled_context.source_event_key,
            )
            held_out_observation = ContradictionLensTrialObservation.build(
                context=pair.held_out,
                run=held_out_run,
            )
            replication = ContradictionLensHeldOutReplicationReceipt.build(
                pair_context=pair,
                calibration_observation=receipt.calibration_observation,
                held_out_observation=held_out_observation,
            )
            evaluation = self.criterion_observer.observe(
                receipt.criterion,
                held_out_observation,
            )
            if (
                replication.pair_context.matched_control_signature
                != receipt.matched_control_signature
                or evaluation.criterion != receipt.criterion
            ):
                raise ContradictionCalibrationStageIntegrityError(
                    "Held-out resume changed frozen controls or criterion."
                )
            if Path(path).read_bytes() != stage_bytes_before:
                raise ContradictionCalibrationStageIntegrityError(
                    "Calibration-stage sidecar changed during held-out resume."
                )
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
                or lenses.fingerprint() != lens_before
            ):
                raise ContradictionCalibrationStageIntegrityError(
                    "Held-out resume crossed a protected ledger."
                )
            held_out_runtime.ledger.state = working_runtime.ledger.snapshot()
            published = True
            calibration_ledger = SimulationLedger.from_state(
                stage.calibration_simulation_state
            )
            return ContradictionResumedDimensionTrialRun(
                stage_path=Path(path),
                stage=stage,
                calibration_ledger=calibration_ledger,
                held_out_run=held_out_run,
                replication_receipt=replication,
                evaluation=evaluation,
            )
        except ContradictionCalibrationStageIntegrityError:
            raise
        except (
            ContradictionDimensionCriterionIntegrityError,
            ContradictionHypothesisIntegrityError,
            ContradictionLensControlIntegrityError,
            ContradictionLensTrialIntegrityError,
            LensIntegrityError,
            SimulationIntegrityError,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ContradictionCalibrationStageIntegrityError(str(exc)) from exc
        finally:
            if (
                calibration_kernel.fingerprint() != canonical_before[0]
                or held_out_kernel.fingerprint() != canonical_before[1]
            ):
                raise RuntimeError("Held-out resume mutated canonical state.")
            if lenses.fingerprint() != lens_before:
                raise RuntimeError("Held-out resume mutated its Lens sidecar.")
            if (
                not published
                and held_out_runtime.ledger.fingerprint() != held_out_before
            ):
                held_out_runtime.ledger.state = original_held_out
                raise RuntimeError(
                    "Failed held-out resume published partial simulation state."
                )
