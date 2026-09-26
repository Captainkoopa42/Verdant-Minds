"""Opt-in checkpoint pairing for canonical state and isolated simulation history.

The archive has no path that commits an overlay or changes the ordinary .vdk
format. A complete archive is one atomic file, not two independently timed
checkpoint writes.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from pathlib import Path

from verdant_kernel import KernelInvariantError, VerdantKernel, checkpoint_bytes
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_kernel.models import canonical_json_bytes

from .counterfactual import SimulationLedger, SimulationLedgerState


EXPERIMENT_ARCHIVE_FORMAT = "verdant-obligation-experiment-v1"
_CANONICAL = "canonical.vdk"
_SIMULATION = "simulation.json"
_MANIFEST = "manifest.json"
_FILES = (_CANONICAL, _SIMULATION)
_MAX_MEMBER_BYTES = 128 * 1024 * 1024
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class ExperimentArchiveIntegrityError(ValueError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _validate_links(kernel: VerdantKernel, ledger: SimulationLedger) -> None:
    decisions = {
        decision.decision_id: decision
        for decision in kernel.state.obligation_attention_decisions
    }
    reservations = {
        reservation.reservation_id: reservation
        for reservation in ledger.state.reservations
    }
    for reservation in ledger.state.reservations:
        decision = decisions.get(reservation.attention_decision_id)
        allocation = None
        if decision is not None:
            allocation = next(
                (
                    item for item in decision.allocations
                    if item.allocation_id == reservation.allocation_id
                ),
                None,
            )
        if (
            allocation is None
            or allocation.obligation_id != reservation.obligation_id
            or reservation.obligation_id not in kernel.state.obligation_kernels
            or allocation.granted_budget != reservation.allocation_granted_budget
        ):
            raise ExperimentArchiveIntegrityError(
                "Simulation reservation lost its canonical Attention allocation."
            )
        if not decision.cycle <= reservation.canonical_cycle <= kernel.state.cycle:
            raise ExperimentArchiveIntegrityError(
                "Simulation reservation is outside canonical cycle history."
            )
        if (
            reservation.canonical_cycle == kernel.state.cycle
            and reservation.canonical_fingerprint != kernel.fingerprint()
        ):
            raise ExperimentArchiveIntegrityError(
                "Simulation reservation disagrees with current canonical state."
            )
    for settlement in ledger.state.settlements:
        reservation = reservations[settlement.reservation_id]
        if settlement.canonical_before_fingerprint != reservation.canonical_fingerprint:
            raise ExperimentArchiveIntegrityError(
                "Simulation settlement differs from its reserved canonical state."
            )


def experiment_archive_bytes(kernel: VerdantKernel, ledger: SimulationLedger) -> bytes:
    """Build a deterministic, non-mutating experimental snapshot."""
    canonical = VerdantKernel.from_state(kernel.snapshot())
    simulation = SimulationLedger.from_state(ledger.snapshot())
    _validate_links(canonical, simulation)
    files = {
        _CANONICAL: checkpoint_bytes(canonical.snapshot()),
        _SIMULATION: canonical_json_bytes(simulation.snapshot().model_dump(mode="json")),
    }
    manifest = canonical_json_bytes({
        "format": EXPERIMENT_ARCHIVE_FORMAT,
        "canonical_fingerprint": canonical.fingerprint(),
        "simulation_fingerprint": simulation.fingerprint(),
        "files": {
            name: {"sha256": _digest(data), "bytes": len(data)}
            for name, data in files.items()
        },
    })
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in (*_FILES, _MANIFEST):
            archive.writestr(
                _zip_info(name), manifest if name == _MANIFEST else files[name]
            )
    return buffer.getvalue()


def save_experiment_archive(
    path: Path, kernel: VerdantKernel, ledger: SimulationLedger
) -> str:
    """Replace one archive after syncing its bytes, then its POSIX directory."""
    data = experiment_archive_bytes(kernel, ledger)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.",
            suffix=".tmp", delete=False,
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


def load_experiment_archive(path: Path) -> tuple[VerdantKernel, SimulationLedger]:
    """Reject mixed or altered members before rebuilding either state."""
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if len(names) != 3 or set(names) != {*_FILES, _MANIFEST}:
                raise ExperimentArchiveIntegrityError(
                    "Archive has missing, duplicate, or unexpected members."
                )
            if any(item.file_size > _MAX_MEMBER_BYTES for item in archive.infolist()):
                raise ExperimentArchiveIntegrityError("Archive member exceeds size limit.")
            files = {name: archive.read(name) for name in names}
        manifest_bytes = files[_MANIFEST]
        manifest = json.loads(manifest_bytes)
        if (
            canonical_json_bytes(manifest) != manifest_bytes
            or set(manifest) != {
                "format", "canonical_fingerprint", "simulation_fingerprint", "files"
            }
            or manifest["format"] != EXPERIMENT_ARCHIVE_FORMAT
            or set(manifest["files"]) != set(_FILES)
        ):
            raise ExperimentArchiveIntegrityError("Archive manifest is invalid.")
        for name in _FILES:
            data = files[name]
            if manifest["files"][name] != {
                "sha256": _digest(data), "bytes": len(data)
            }:
                raise ExperimentArchiveIntegrityError("Archive member checksum mismatch.")
        kernel = VerdantKernel.from_state(load_checkpoint_bytes(files[_CANONICAL]))
        simulation_bytes = files[_SIMULATION]
        state = SimulationLedgerState.model_validate_json(simulation_bytes)
        if canonical_json_bytes(state.model_dump(mode="json")) != simulation_bytes:
            raise ExperimentArchiveIntegrityError("Simulation JSON is not canonical.")
        ledger = SimulationLedger.from_state(state)
        if (
            manifest["canonical_fingerprint"] != kernel.fingerprint()
            or manifest["simulation_fingerprint"] != ledger.fingerprint()
        ):
            raise ExperimentArchiveIntegrityError("Archive fingerprint mismatch.")
        _validate_links(kernel, ledger)
        return kernel, ledger
    except (
        KeyError, TypeError, ValueError, zipfile.BadZipFile, KernelInvariantError
    ) as error:
        if isinstance(error, ExperimentArchiveIntegrityError):
            raise
        raise ExperimentArchiveIntegrityError("Invalid experiment archive.") from error
