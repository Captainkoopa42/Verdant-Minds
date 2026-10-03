"""Durable, separately paired receipts for one integrated inquiry invocation.

The receipt file stores the complete content-addressed ``IntegratedInquiryTrace``
without changing canonical VDK state or the existing VOB archive formats.  A
receipt is useful only when loaded beside the exact canonical, simulation, and
Lens sidecars that produced it; every represented cross-ledger edge is checked
again on load.

This is durability for experimental evidence, not execution authority.  The
receipt cannot dispatch an action, declare an observed outcome, resolve an
obligation, or promote simulated state.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

try:  # POSIX-only writer arbitration; single-receipt files remain portable.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on non-POSIX hosts
    fcntl = None

from pydantic import BaseModel, ConfigDict, model_validator

from verdant_kernel import ObligationFamily, VerdantKernel
from verdant_kernel.models import canonical_json_bytes

from .counterfactual import (
    CounterfactualExecutionTrace,
    SimulationDisposition,
    SimulationLedger,
    SimulationReservation,
    SimulationSettlement,
)
from .equivalence import (
    EquivalenceLensSystem,
    LensIntegrityError,
    LensUnavailableError,
)
from .inquiry import IntegratedInquiryTrace


INTEGRATED_INQUIRY_RECEIPT_FORMAT = "verdant-integrated-inquiry-receipt-v1"
INTEGRATED_INQUIRY_RECEIPT_HISTORY_FORMAT = (
    "verdant-integrated-inquiry-receipt-history-v1"
)
_MAX_RECEIPT_BYTES = 128 * 1024 * 1024
_MAX_HISTORY_BYTES = 128 * 1024 * 1024
_MAX_HISTORY_ENTRIES = 128
_HISTORY_GENESIS_SHA256 = "0" * 64


class IntegratedInquiryReceiptIntegrityError(ValueError):
    """Raised when a durable inquiry receipt is altered or incorrectly paired."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


class IntegratedInquiryReceiptEnvelope(BaseModel):
    """Canonical JSON envelope for exactly one v0.30 integrated trace."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: str = INTEGRATED_INQUIRY_RECEIPT_FORMAT
    canonical_fingerprint: str
    simulation_fingerprint: str
    lens_fingerprint: str
    trace_sha256: str
    trace: IntegratedInquiryTrace

    @model_validator(mode="after")
    def validate_envelope(self) -> "IntegratedInquiryReceiptEnvelope":
        if self.format_version != INTEGRATED_INQUIRY_RECEIPT_FORMAT:
            raise ValueError("Unsupported integrated inquiry receipt format.")
        for digest in (
            self.canonical_fingerprint,
            self.simulation_fingerprint,
            self.lens_fingerprint,
            self.trace_sha256,
        ):
            if not _is_sha256(digest):
                raise ValueError("Integrated inquiry receipt digests must be SHA-256.")
        trace_bytes = canonical_json_bytes(self.trace.model_dump(mode="json"))
        if self.trace_sha256 != _digest(trace_bytes):
            raise ValueError("Integrated inquiry trace checksum mismatch.")
        return self


class IntegratedInquiryReceiptHistoryEntry(BaseModel):
    """One immutable receipt in an ordered, hash-chained history."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int
    previous_entry_sha256: str
    receipt_sha256: str
    receipt: IntegratedInquiryReceiptEnvelope

    @model_validator(mode="after")
    def validate_entry(self) -> "IntegratedInquiryReceiptHistoryEntry":
        if self.sequence < 1:
            raise ValueError("Integrated inquiry history sequences start at one.")
        if not _is_sha256(self.previous_entry_sha256) or not _is_sha256(
            self.receipt_sha256
        ):
            raise ValueError("Integrated inquiry history digests must be SHA-256.")
        if self.receipt_sha256 != _digest(_receipt_envelope_bytes(self.receipt)):
            raise ValueError("Integrated inquiry history receipt checksum mismatch.")
        return self


def _receipt_envelope_bytes(envelope: IntegratedInquiryReceiptEnvelope) -> bytes:
    return canonical_json_bytes(envelope.model_dump(mode="json"))


def _history_entry_fingerprint(
    entry: IntegratedInquiryReceiptHistoryEntry,
) -> str:
    return _digest(canonical_json_bytes(entry.model_dump(mode="json")))


class IntegratedInquiryReceiptHistoryEnvelope(BaseModel):
    """Bounded canonical history whose head commits to every prior receipt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: str = INTEGRATED_INQUIRY_RECEIPT_HISTORY_FORMAT
    head_sha256: str = _HISTORY_GENESIS_SHA256
    entries: tuple[IntegratedInquiryReceiptHistoryEntry, ...] = ()

    @model_validator(mode="after")
    def validate_history(self) -> "IntegratedInquiryReceiptHistoryEnvelope":
        if self.format_version != INTEGRATED_INQUIRY_RECEIPT_HISTORY_FORMAT:
            raise ValueError("Unsupported integrated inquiry history format.")
        if not _is_sha256(self.head_sha256):
            raise ValueError("Integrated inquiry history head must be SHA-256.")
        if len(self.entries) > _MAX_HISTORY_ENTRIES:
            raise ValueError("Integrated inquiry receipt history exceeds its entry cap.")

        previous = _HISTORY_GENESIS_SHA256
        receipt_digests: set[str] = set()
        for expected_sequence, entry in enumerate(self.entries, start=1):
            if entry.sequence != expected_sequence:
                raise ValueError("Integrated inquiry history sequence is not contiguous.")
            if entry.previous_entry_sha256 != previous:
                raise ValueError("Integrated inquiry history chain is broken.")
            if entry.receipt_sha256 in receipt_digests:
                raise ValueError("Integrated inquiry history contains a duplicate receipt.")
            receipt_digests.add(entry.receipt_sha256)
            previous = _history_entry_fingerprint(entry)
        if self.head_sha256 != previous:
            raise ValueError("Integrated inquiry history head checksum mismatch.")
        return self


def _validate_execution_link(
    execution: CounterfactualExecutionTrace,
    *,
    reservations: dict[str, SimulationReservation],
    settlements: dict[str, SimulationSettlement],
) -> None:
    reservation = reservations.get(execution.reservation_id)
    settlement = settlements.get(execution.settlement_id)
    if reservation is None or settlement is None:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt lost an isolated execution record."
        )
    if (
        reservation.plan_id != execution.plan_id
        or reservation.source_event_key != execution.source_event_key
        or reservation.obligation_id != execution.obligation_id
        or reservation.attention_decision_id != execution.attention_decision_id
        or reservation.allocation_id != execution.allocation_id
        or reservation.canonical_fingerprint != execution.canonical_fingerprint
        or reservation.requested_budget != execution.requested_budget
        or settlement.reservation_id != execution.reservation_id
        or settlement.disposition != execution.disposition
        or settlement.consumed_budget != execution.consumed_budget
        or settlement.overlay_fingerprint != execution.overlay_fingerprint
        or settlement.applied_patch_ids != execution.applied_patch_ids
        or settlement.result_refs != execution.result_refs
        or settlement.termination_code != execution.termination_code
        or settlement.canonical_before_fingerprint
        != execution.canonical_fingerprint
        or settlement.canonical_after_fingerprint
        != execution.canonical_fingerprint
        or not settlement.canonical_unchanged
        or settlement.canonical_commit_permitted
        or settlement.epistemic_authority_enabled
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry execution crossed its durable simulation lineage."
        )


def _validate_integrated_inquiry_receipt(
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
    trace: IntegratedInquiryTrace,
) -> None:
    """Recheck the exact canonical/simulation/Lens closure of one trace."""

    if (
        trace.canonical_checkpoint_fingerprint != kernel.fingerprint()
        or trace.simulation_ledger_fingerprint != simulation_ledger.fingerprint()
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt is paired with different canonical or simulation state."
        )
    request = trace.trial_control_request
    if request is None:
        raise IntegratedInquiryReceiptIntegrityError(
            "Durable v0.30 receipts require predeclared controlled-trial lineage."
        )
    if (
        request.lens_state_fingerprint != lens_system.fingerprint()
        or not trace.controlled_trial_observations
        or not trace.held_out_replication_receipts
        or not trace.workspace_admission_observations
        or not trace.held_out_workspace_admission_receipts
        or not trace.outgoing_action_observations
        or not trace.held_out_outgoing_action_receipts
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt lost complete controlled v0.30 evidence."
        )
    try:
        active = lens_system.active_binding(ObligationFamily.DEPENDENCY_GAP).binding
    except (LensIntegrityError, LensUnavailableError) as exc:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt lost its active family-local Lens."
        ) from exc
    if (
        active.binding_id != request.lens_binding_id
        or active.definition_id != request.lens_definition_id
        or active.policy_version != request.lens_policy_version
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt is paired with a different active Lens."
        )

    decisions = {
        item.decision_id: item
        for item in kernel.state.obligation_attention_decisions
    }
    decision = decisions.get(trace.attention_decision_id)
    if decision is None:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt lost its canonical Attention decision."
        )
    bid_ids = tuple(item.bid_id for item in decision.bids)
    allocation_ids = tuple(item.allocation_id for item in decision.allocations)
    basis_event_ids = tuple(sorted(item.basis_event_id for item in decision.bids))
    if (
        trace.attention_bid_ids != bid_ids
        or trace.attention_allocation_ids != allocation_ids
        or trace.deferred_bid_ids != decision.deferred_bid_ids
        or trace.obligation_ids != decision.eligible_obligation_ids
        or trace.obligation_event_ids != basis_event_ids
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt crossed its canonical Attention lineage."
        )
    canonical_events = {
        item.event_id: item for item in kernel.state.obligation_history
    }
    if any(
        obligation_id not in kernel.state.obligation_kernels
        or kernel.state.obligation_kernels[obligation_id].family
        != ObligationFamily.DEPENDENCY_GAP
        for obligation_id in trace.obligation_ids
    ) or any(
        event_id not in canonical_events for event_id in trace.obligation_event_ids
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt lost canonical obligation provenance."
        )

    reservations = {
        item.reservation_id: item
        for item in simulation_ledger.state.reservations
    }
    settlements = {
        item.settlement_id: item
        for item in simulation_ledger.state.settlements
    }
    for trial in trace.trials:
        reservation = reservations.get(trial.reservation_id)
        settlement = settlements.get(trial.settlement_id)
        if (
            reservation is None
            or settlement is None
            or reservation.plan_id != trial.plan_id
            or reservation.obligation_id != trial.obligation_id
            or reservation.attention_decision_id != trial.attention_decision_id
            or reservation.allocation_id != trial.attention_allocation_id
            or reservation.canonical_fingerprint
            != trace.canonical_checkpoint_fingerprint
            or settlement.reservation_id != trial.reservation_id
            or settlement.disposition != SimulationDisposition.DISCARDED
            or settlement.canonical_before_fingerprint
            != trace.canonical_checkpoint_fingerprint
            or settlement.canonical_after_fingerprint
            != trace.canonical_checkpoint_fingerprint
            or not settlement.canonical_unchanged
            or settlement.canonical_commit_permitted
            or settlement.epistemic_authority_enabled
            or settlement.result_refs
            != tuple(
                sorted(
                    (
                        trial.hypothesis_id,
                        trial.outcome_id,
                        trial.equivalence_signature,
                    )
                )
            )
        ):
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry trial crossed its durable simulation lineage."
            )

    for observation in trace.matched_observations:
        _validate_execution_link(
            observation.baseline,
            reservations=reservations,
            settlements=settlements,
        )
        _validate_execution_link(
            observation.treatment,
            reservations=reservations,
            settlements=settlements,
        )

    canonical_evidence = set(kernel.state.evidence)
    referenced_evidence: set[str] = set()
    for observation in trace.operational_probe_observations:
        referenced_evidence.update(observation.baseline.retrieved_evidence_refs)
        referenced_evidence.update(observation.treatment.retrieved_evidence_refs)
    for observation in trace.workspace_admission_observations:
        for arm in (observation.baseline, observation.treatment):
            referenced_evidence.update(arm.submitted_retrieved_evidence_refs)
            referenced_evidence.update(arm.admitted_retrieved_evidence_refs)
            referenced_evidence.update(arm.suppressed_retrieved_evidence_refs)
    for observation in trace.outgoing_action_observations:
        referenced_evidence.update(observation.baseline.admitted_evidence_refs)
        referenced_evidence.update(observation.treatment.admitted_evidence_refs)
    for receipt in trace.resolution_evidence_receipts:
        referenced_evidence.update(receipt.candidate_evidence_refs)
        referenced_evidence.update(receipt.overlay_newly_retrieved_evidence_refs)
    if not referenced_evidence.issubset(canonical_evidence):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt cites noncanonical evidence."
        )

    canonical_decisions = {
        item.decision_event_id for item in kernel.state.council_decisions
    }
    canonical_workspace_events = {
        item.event_id for item in kernel.state.workspace_cycle_events
    }
    canonical_workspace_items = set(kernel.state.workspace_items)
    for observation in trace.workspace_admission_observations:
        for arm in (observation.baseline, observation.treatment):
            if arm.workspace_event.event_id in canonical_workspace_events:
                raise IntegratedInquiryReceiptIntegrityError(
                    "Shadow evidence workspace event leaked into canonical state."
                )
            if set(arm.workspace_event.active_item_ids) & canonical_workspace_items:
                raise IntegratedInquiryReceiptIntegrityError(
                    "Shadow evidence workspace item leaked into canonical state."
                )
    for observation in trace.outgoing_action_observations:
        for arm in (observation.baseline, observation.treatment):
            if (
                arm.council_decision is not None
                and arm.council_decision.decision_event_id in canonical_decisions
            ):
                raise IntegratedInquiryReceiptIntegrityError(
                    "Shadow Council decision leaked into canonical governance."
                )
            if arm.action_workspace_event is not None:
                if arm.action_workspace_event.event_id in canonical_workspace_events:
                    raise IntegratedInquiryReceiptIntegrityError(
                        "Shadow action workspace event leaked into canonical state."
                    )
                if (
                    set(arm.action_workspace_event.active_item_ids)
                    & canonical_workspace_items
                ):
                    raise IntegratedInquiryReceiptIntegrityError(
                        "Shadow action workspace item leaked into canonical state."
                    )


def integrated_inquiry_receipt_bytes(
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
    trace: IntegratedInquiryTrace,
) -> bytes:
    """Build deterministic receipt bytes without mutating any paired state."""

    try:
        trace = IntegratedInquiryTrace.model_validate(trace.model_dump(mode="json"))
    except (TypeError, ValueError) as exc:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry trace failed validation."
        ) from exc
    _validate_integrated_inquiry_receipt(
        kernel,
        simulation_ledger,
        lens_system,
        trace,
    )
    trace_bytes = canonical_json_bytes(trace.model_dump(mode="json"))
    envelope = IntegratedInquiryReceiptEnvelope(
        canonical_fingerprint=kernel.fingerprint(),
        simulation_fingerprint=simulation_ledger.fingerprint(),
        lens_fingerprint=lens_system.fingerprint(),
        trace_sha256=_digest(trace_bytes),
        trace=trace,
    )
    return canonical_json_bytes(envelope.model_dump(mode="json"))


def save_integrated_inquiry_receipt(
    path: Path,
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
    trace: IntegratedInquiryTrace,
) -> str:
    """Atomically replace one receipt after syncing file and POSIX directory."""

    data = integrated_inquiry_receipt_bytes(
        kernel,
        simulation_ledger,
        lens_system,
        trace,
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return _digest(data)


def load_integrated_inquiry_receipt(
    path: Path,
    *,
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
) -> IntegratedInquiryTrace:
    """Load one receipt and revalidate it against exact paired sidecars."""

    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_RECEIPT_BYTES:
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt exceeds its size limit."
            )
        envelope = IntegratedInquiryReceiptEnvelope.model_validate_json(data)
        if canonical_json_bytes(envelope.model_dump(mode="json")) != data:
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt JSON is not canonical."
            )
        if (
            envelope.canonical_fingerprint != kernel.fingerprint()
            or envelope.simulation_fingerprint != simulation_ledger.fingerprint()
            or envelope.lens_fingerprint != lens_system.fingerprint()
        ):
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt sidecar pairing mismatch."
            )
        _validate_integrated_inquiry_receipt(
            kernel,
            simulation_ledger,
            lens_system,
            envelope.trace,
        )
        return envelope.trace
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, IntegratedInquiryReceiptIntegrityError):
            raise
        raise IntegratedInquiryReceiptIntegrityError(
            "Invalid integrated inquiry receipt."
        ) from exc


def integrated_inquiry_receipt_history_bytes(
    history: IntegratedInquiryReceiptHistoryEnvelope,
) -> bytes:
    """Return deterministic bytes for an already assembled receipt history."""

    try:
        validated = IntegratedInquiryReceiptHistoryEnvelope.model_validate(
            history.model_dump(mode="json")
        )
    except (TypeError, ValueError) as exc:
        raise IntegratedInquiryReceiptIntegrityError(
            "Invalid integrated inquiry receipt history."
        ) from exc
    data = canonical_json_bytes(validated.model_dump(mode="json"))
    if len(data) > _MAX_HISTORY_BYTES:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt history exceeds its size limit."
        )
    return data


def read_integrated_inquiry_receipt_history(
    path: Path,
) -> IntegratedInquiryReceiptHistoryEnvelope:
    """Read and intrinsically verify a canonical receipt history.

    This verifies the bounded hash chain and every embedded receipt checksum.
    Full cross-ledger validation of an individual receipt still requires its
    exact paired sidecars through ``load_integrated_inquiry_receipt_history_entry``.
    """

    try:
        data = Path(path).read_bytes()
        if len(data) > _MAX_HISTORY_BYTES:
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt history exceeds its size limit."
            )
        history = IntegratedInquiryReceiptHistoryEnvelope.model_validate_json(data)
        if integrated_inquiry_receipt_history_bytes(history) != data:
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt history JSON is not canonical."
            )
        return history
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, IntegratedInquiryReceiptIntegrityError):
            raise
        raise IntegratedInquiryReceiptIntegrityError(
            "Invalid integrated inquiry receipt history."
        ) from exc


def _history_lock_path(path: Path) -> Path:
    return path.with_name(f".{path.name}.lock")


def _remove_stale_history_temporaries(path: Path) -> None:
    for candidate in path.parent.glob(f".{path.name}.*.tmp"):
        candidate.unlink(missing_ok=True)


def append_integrated_inquiry_receipt_history(
    path: Path,
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
    trace: IntegratedInquiryTrace,
) -> str:
    """Append one unique receipt under a process-shared POSIX writer lock.

    The returned digest identifies the canonical embedded ``.viq`` receipt and
    is stable regardless of which competing writer acquires the lock first.
    Readers need no lock because the complete history is atomically replaced.
    """

    if os.name != "posix" or fcntl is None:
        raise IntegratedInquiryReceiptIntegrityError(
            "Concurrent inquiry history append requires POSIX flock support."
        )
    receipt_data = integrated_inquiry_receipt_bytes(
        kernel,
        simulation_ledger,
        lens_system,
        trace,
    )
    receipt = IntegratedInquiryReceiptEnvelope.model_validate_json(receipt_data)
    receipt_sha256 = _digest(receipt_data)

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_file_descriptor = os.open(
        _history_lock_path(path),
        os.O_RDWR | os.O_CREAT,
        0o600,
    )
    try:
        fcntl.flock(lock_file_descriptor, fcntl.LOCK_EX)
        _remove_stale_history_temporaries(path)
        if path.exists():
            history = read_integrated_inquiry_receipt_history(path)
        else:
            history = IntegratedInquiryReceiptHistoryEnvelope()

        for entry in history.entries:
            if entry.receipt_sha256 == receipt_sha256:
                return receipt_sha256
        if len(history.entries) >= _MAX_HISTORY_ENTRIES:
            raise IntegratedInquiryReceiptIntegrityError(
                "Integrated inquiry receipt history reached its entry cap."
            )

        entry = IntegratedInquiryReceiptHistoryEntry(
            sequence=len(history.entries) + 1,
            previous_entry_sha256=history.head_sha256,
            receipt_sha256=receipt_sha256,
            receipt=receipt,
        )
        updated = IntegratedInquiryReceiptHistoryEnvelope(
            head_sha256=_history_entry_fingerprint(entry),
            entries=(*history.entries, entry),
        )
        data = integrated_inquiry_receipt_history_bytes(updated)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return receipt_sha256
    finally:
        try:
            fcntl.flock(lock_file_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(lock_file_descriptor)


def load_integrated_inquiry_receipt_history_entry(
    path: Path,
    receipt_sha256: str,
    *,
    kernel: VerdantKernel,
    simulation_ledger: SimulationLedger,
    lens_system: EquivalenceLensSystem,
) -> IntegratedInquiryTrace:
    """Fully validate one history entry against its exact paired sidecars."""

    if not _is_sha256(receipt_sha256):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry history receipt identifier must be SHA-256."
        )
    history = read_integrated_inquiry_receipt_history(path)
    entry = next(
        (
            candidate
            for candidate in history.entries
            if candidate.receipt_sha256 == receipt_sha256
        ),
        None,
    )
    if entry is None:
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry receipt is absent from the requested history."
        )
    envelope = entry.receipt
    if (
        envelope.canonical_fingerprint != kernel.fingerprint()
        or envelope.simulation_fingerprint != simulation_ledger.fingerprint()
        or envelope.lens_fingerprint != lens_system.fingerprint()
    ):
        raise IntegratedInquiryReceiptIntegrityError(
            "Integrated inquiry history entry sidecar pairing mismatch."
        )
    _validate_integrated_inquiry_receipt(
        kernel,
        simulation_ledger,
        lens_system,
        envelope.trace,
    )
    return envelope.trace
