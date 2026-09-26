"""Opt-in pairing for canonical state and separately governed sidecars.

The archive has no path that commits an overlay or changes the ordinary .vdk
format. Legacy v1 holds canonical plus simulation state; v2 may additionally
hold the Equivalence Lens registry and ledger. A complete archive is one atomic
file, not independently timed checkpoint writes.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from verdant_kernel import KernelInvariantError, VerdantKernel, checkpoint_bytes
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_kernel.models import canonical_json_bytes

from .counterfactual import SimulationLedger, SimulationLedgerState
from .equivalence import (
    EquivalenceLensSystem,
    LensBindingLedgerState,
    LensDefinitionRegistryState,
    LensIntegrityError,
)


EXPERIMENT_ARCHIVE_LEGACY_FORMAT = "verdant-obligation-experiment-v1"
EXPERIMENT_ARCHIVE_FORMAT = "verdant-obligation-experiment-v2"
_CANONICAL = "canonical.vdk"
_SIMULATION = "simulation.json"
_LENS_REGISTRY = "lens_registry.json"
_LENS_LEDGER = "lens_ledger.json"
_MANIFEST = "manifest.json"
_V1_FILES = (_CANONICAL, _SIMULATION)
_V2_FILES = (*_V1_FILES, _LENS_REGISTRY, _LENS_LEDGER)
_MAX_MEMBER_BYTES = 128 * 1024 * 1024
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class ExperimentArchiveIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class ExperimentArchiveBundle:
    kernel: VerdantKernel
    simulation_ledger: SimulationLedger
    lens_system: EquivalenceLensSystem | None
    format_version: str


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=_FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = 0o600 << 16
    return info


def _validate_simulation_links(kernel: VerdantKernel, ledger: SimulationLedger) -> None:
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


def _validate_lens_links(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    lenses: EquivalenceLensSystem,
) -> None:
    """Close typed references that the paired archive can actually prove."""
    future_cycles = (
        *(item.cycle for item in lenses.ledger.evidence),
        *(item.cycle for item in lenses.ledger.governance_events),
    )
    if any(cycle > kernel.state.cycle for cycle in future_cycles):
        raise ExperimentArchiveIntegrityError(
            "Lens history is ahead of the paired canonical checkpoint."
        )

    known_by_prefix = (
        ("equivalence_lens_definition_", set(lenses.registry.definitions)),
        (
            "equivalence_lens_binding_",
            {item.binding_id for item in lenses.ledger.bindings},
        ),
        (
            "equivalence_lens_evidence_",
            {item.evidence_id for item in lenses.ledger.evidence},
        ),
        (
            "equivalence_lens_governance_",
            {item.event_id for item in lenses.ledger.governance_events},
        ),
        (
            "simulation_reservation_",
            {item.reservation_id for item in ledger.state.reservations},
        ),
        (
            "simulation_settlement_",
            {item.settlement_id for item in ledger.state.settlements},
        ),
    )

    def require_known(refs: tuple[str, ...]) -> None:
        for ref in refs:
            for prefix, known in known_by_prefix:
                if ref.startswith(prefix) and ref not in known:
                    raise ExperimentArchiveIntegrityError(
                        "Lens archive contains an unresolved typed cross-ledger reference."
                    )

    for definition in lenses.registry.definitions.values():
        require_known(definition.provenance_refs)
    for binding in lenses.ledger.bindings:
        require_known(binding.calibration_refs)
    for evidence in lenses.ledger.evidence:
        require_known(
            (
                *evidence.hypothesis_refs,
                *evidence.outcome_refs,
                *evidence.independent_consequence_refs,
            )
        )
    for event in lenses.ledger.governance_events:
        require_known(event.basis_refs)
    for settlement in ledger.state.settlements:
        require_known(settlement.result_refs)


def experiment_archive_bytes(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    *,
    lens_system: EquivalenceLensSystem | None = None,
) -> bytes:
    """Build a deterministic, non-mutating experimental snapshot."""
    canonical = VerdantKernel.from_state(kernel.snapshot())
    simulation = SimulationLedger.from_state(ledger.snapshot())
    _validate_simulation_links(canonical, simulation)
    files = {
        _CANONICAL: checkpoint_bytes(canonical.snapshot()),
        _SIMULATION: canonical_json_bytes(simulation.snapshot().model_dump(mode="json")),
    }
    format_version = EXPERIMENT_ARCHIVE_LEGACY_FORMAT
    fingerprints = {
        "canonical_fingerprint": canonical.fingerprint(),
        "simulation_fingerprint": simulation.fingerprint(),
    }
    if lens_system is not None:
        registry, lens_ledger = lens_system.snapshot()
        lenses = EquivalenceLensSystem(registry=registry, ledger=lens_ledger)
        _validate_lens_links(canonical, simulation, lenses)
        files[_LENS_REGISTRY] = canonical_json_bytes(
            lenses.registry.model_dump(mode="json")
        )
        files[_LENS_LEDGER] = canonical_json_bytes(
            lenses.ledger.model_dump(mode="json")
        )
        fingerprints["lens_fingerprint"] = lenses.fingerprint()
        format_version = EXPERIMENT_ARCHIVE_FORMAT
    manifest = canonical_json_bytes({
        "format": format_version,
        **fingerprints,
        "files": {
            name: {"sha256": _digest(data), "bytes": len(data)}
            for name, data in files.items()
        },
    })
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name in (*files, _MANIFEST):
            archive.writestr(
                _zip_info(name), manifest if name == _MANIFEST else files[name]
            )
    return buffer.getvalue()


def save_experiment_archive(
    path: Path,
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    *,
    lens_system: EquivalenceLensSystem | None = None,
) -> str:
    """Replace one archive after syncing its bytes, then its POSIX directory."""
    data = experiment_archive_bytes(kernel, ledger, lens_system=lens_system)
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


def load_experiment_archive_bundle(path: Path) -> ExperimentArchiveBundle:
    """Validate and rebuild every sidecar present in one archive."""
    try:
        with zipfile.ZipFile(path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or _MANIFEST not in names:
                raise ExperimentArchiveIntegrityError(
                    "Archive has missing, duplicate, or unexpected members."
                )
            if any(item.file_size > _MAX_MEMBER_BYTES for item in archive.infolist()):
                raise ExperimentArchiveIntegrityError("Archive member exceeds size limit.")
            files = {name: archive.read(name) for name in names}
        manifest_bytes = files[_MANIFEST]
        manifest = json.loads(manifest_bytes)
        if (
            not isinstance(manifest, dict)
            or canonical_json_bytes(manifest) != manifest_bytes
        ):
            raise ExperimentArchiveIntegrityError("Archive manifest is invalid.")
        format_version = manifest.get("format")
        if format_version == EXPERIMENT_ARCHIVE_LEGACY_FORMAT:
            expected_files = _V1_FILES
            expected_manifest_keys = {
                "format", "canonical_fingerprint", "simulation_fingerprint", "files"
            }
        elif format_version == EXPERIMENT_ARCHIVE_FORMAT:
            expected_files = _V2_FILES
            expected_manifest_keys = {
                "format", "canonical_fingerprint", "simulation_fingerprint",
                "lens_fingerprint", "files",
            }
        else:
            raise ExperimentArchiveIntegrityError("Archive manifest is invalid.")
        if (
            set(manifest) != expected_manifest_keys
            or set(manifest["files"]) != set(expected_files)
            or len(names) != len(expected_files) + 1
            or set(names) != {*expected_files, _MANIFEST}
        ):
            raise ExperimentArchiveIntegrityError("Archive manifest is invalid.")
        for name in expected_files:
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
        _validate_simulation_links(kernel, ledger)
        lenses = None
        if format_version == EXPERIMENT_ARCHIVE_FORMAT:
            registry_bytes = files[_LENS_REGISTRY]
            ledger_bytes = files[_LENS_LEDGER]
            registry = LensDefinitionRegistryState.model_validate_json(registry_bytes)
            lens_ledger = LensBindingLedgerState.model_validate_json(ledger_bytes)
            if (
                canonical_json_bytes(registry.model_dump(mode="json")) != registry_bytes
                or canonical_json_bytes(lens_ledger.model_dump(mode="json"))
                != ledger_bytes
            ):
                raise ExperimentArchiveIntegrityError("Lens JSON is not canonical.")
            lenses = EquivalenceLensSystem(registry=registry, ledger=lens_ledger)
            if manifest["lens_fingerprint"] != lenses.fingerprint():
                raise ExperimentArchiveIntegrityError("Archive fingerprint mismatch.")
            _validate_lens_links(kernel, ledger, lenses)
        return ExperimentArchiveBundle(
            kernel=kernel,
            simulation_ledger=ledger,
            lens_system=lenses,
            format_version=format_version,
        )
    except (
        KeyError, TypeError, ValueError, zipfile.BadZipFile, KernelInvariantError,
        LensIntegrityError,
    ) as error:
        if isinstance(error, ExperimentArchiveIntegrityError):
            raise
        raise ExperimentArchiveIntegrityError("Invalid experiment archive.") from error


def load_experiment_archive(path: Path) -> tuple[VerdantKernel, SimulationLedger]:
    """Backward-compatible canonical and simulation view of either format."""
    bundle = load_experiment_archive_bundle(path)
    return bundle.kernel, bundle.simulation_ledger
