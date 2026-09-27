"""Opt-in pairing for canonical state and separately governed sidecars.

The archive has no path that commits an overlay or changes the ordinary .vdk
format. Legacy v1 holds canonical plus simulation state; v2 may additionally
hold the Equivalence Lens registry and ledger; v3 may also hold the terminal
Diagnostic ledger; v4 may also hold the non-executing Council tournament.
A complete archive is one atomic file, not independently timed checkpoint
writes.
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

from .counterfactual import (
    SimulationDisposition,
    SimulationLedger,
    SimulationLedgerState,
)
from .diagnostics import (
    DiagnosticConclusion,
    DiagnosticEngine,
    DiagnosticLedgerState,
)
from .equivalence import (
    EquivalenceLensSystem,
    LensBindingLedgerState,
    LensDefinitionRegistryState,
    LensIntegrityError,
)
from .interventions import (
    CouncilInterventionLedgerState,
    CouncilInterventionPolicy,
    CouncilLeastRegretTournament,
)


EXPERIMENT_ARCHIVE_LEGACY_FORMAT = "verdant-obligation-experiment-v1"
EXPERIMENT_ARCHIVE_FORMAT = "verdant-obligation-experiment-v2"
EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT = "verdant-obligation-experiment-v3"
EXPERIMENT_ARCHIVE_COUNCIL_FORMAT = "verdant-obligation-experiment-v4"
_CANONICAL = "canonical.vdk"
_SIMULATION = "simulation.json"
_LENS_REGISTRY = "lens_registry.json"
_LENS_LEDGER = "lens_ledger.json"
_DIAGNOSTIC_LEDGER = "diagnostic_ledger.json"
_COUNCIL_POLICY = "council_policy.json"
_COUNCIL_LEDGER = "council_ledger.json"
_MANIFEST = "manifest.json"
_V1_FILES = (_CANONICAL, _SIMULATION)
_V2_FILES = (*_V1_FILES, _LENS_REGISTRY, _LENS_LEDGER)
_V3_FILES = (*_V2_FILES, _DIAGNOSTIC_LEDGER)
_V4_FILES = (*_V3_FILES, _COUNCIL_POLICY, _COUNCIL_LEDGER)
_MAX_MEMBER_BYTES = 128 * 1024 * 1024
_FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


class ExperimentArchiveIntegrityError(ValueError):
    pass


@dataclass(frozen=True)
class ExperimentArchiveBundle:
    kernel: VerdantKernel
    simulation_ledger: SimulationLedger
    lens_system: EquivalenceLensSystem | None
    diagnostic_engine: DiagnosticEngine | None
    council_tournament: CouncilLeastRegretTournament | None
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


def _validate_diagnostic_links(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    lenses: EquivalenceLensSystem,
    diagnostics: DiagnosticEngine,
) -> None:
    """Recheck every durable causal edge represented by the Diagnostic ledger."""
    decisions = {
        item.decision_id: item
        for item in kernel.state.obligation_attention_decisions
    }
    reservations = {
        item.reservation_id: item for item in ledger.state.reservations
    }
    settlements = {
        item.settlement_id: item for item in ledger.state.settlements
    }
    bindings = {
        item.binding_id: item for item in lenses.ledger.bindings
    }
    definitions = set(lenses.registry.definitions)

    diagnostic_by_id = {
        item.diagnostic_id: item for item in diagnostics.state.obligations
    }
    for diagnostic in diagnostics.state.obligations:
        trigger = diagnostic.trigger
        parent = kernel.state.obligation_kernels.get(trigger.obligation_id)
        decision = decisions.get(trigger.attention_decision_id)
        settlement = settlements.get(trigger.failed_settlement_id)
        reservation = (
            reservations.get(settlement.reservation_id)
            if settlement is not None
            else None
        )
        binding = bindings.get(trigger.lens_binding_id)
        if diagnostic.creation_cycle > kernel.state.cycle:
            raise ExperimentArchiveIntegrityError(
                "Diagnostic history is ahead of the paired canonical checkpoint."
            )
        if parent is None:
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger lost its parent obligation."
            )
        if (
            decision is None
            or trigger.obligation_id not in decision.eligible_obligation_ids
        ):
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger lost its canonical Attention decision."
            )
        if (
            settlement is None
            or reservation is None
            or not settlement.canonical_unchanged
            or reservation.obligation_id != trigger.obligation_id
            or reservation.attention_decision_id != trigger.attention_decision_id
        ):
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger lost its failed-inquiry simulation lineage."
            )
        if (
            binding is None
            or binding.obligation_family != parent.family
            or binding.definition_id != trigger.lens_definition_id
            or trigger.lens_definition_id not in definitions
        ):
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger lost its family-local Lens lineage."
            )
        if trigger.hypothesis_ref not in settlement.result_refs:
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger lost its hypothesis simulation lineage."
            )
        required_evidence = {
            trigger.attention_decision_id,
            trigger.failed_settlement_id,
            trigger.lens_binding_id,
            trigger.lens_definition_id,
            trigger.hypothesis_ref,
        }
        if not required_evidence.issubset(set(trigger.evidence_refs)):
            raise ExperimentArchiveIntegrityError(
                "Diagnostic ledger omits required causal evidence refs."
            )

    expected_attribution = {
        DiagnosticConclusion.LENS_OVER_SMOOTHING: lambda trigger: {
            trigger.lens_definition_id
        },
        DiagnosticConclusion.LENS_HYPER_DISCRIMINATION: lambda trigger: {
            trigger.lens_definition_id
        },
        DiagnosticConclusion.BINDING_MISCALIBRATION: lambda trigger: {
            trigger.lens_binding_id
        },
        DiagnosticConclusion.GENERATOR_FAULT: lambda trigger: {
            trigger.hypothesis_ref
        },
        DiagnosticConclusion.SCHEDULER_MISALIGNMENT: lambda trigger: {
            trigger.attention_decision_id
        },
    }
    for result in diagnostics.state.results:
        diagnostic = diagnostic_by_id[result.diagnostic_id]
        trigger = diagnostic.trigger
        actual = set(result.attributed_component_refs)
        if result.conclusion in expected_attribution:
            if actual != expected_attribution[result.conclusion](trigger):
                raise ExperimentArchiveIntegrityError(
                    "Diagnostic result attribution escaped its causal lineage."
                )
        elif result.conclusion == DiagnosticConclusion.INTERACTION_SUSPECTED:
            allowed = {
                trigger.lens_definition_id,
                trigger.lens_binding_id,
                trigger.hypothesis_ref,
                trigger.attention_decision_id,
            }
            if not actual.issubset(allowed):
                raise ExperimentArchiveIntegrityError(
                    "Diagnostic interaction attribution escaped its causal lineage."
                )

        probe_settlements = tuple(
            settlement
            for settlement in ledger.state.settlements
            if result.diagnostic_id in settlement.result_refs
            and reservations[settlement.reservation_id].obligation_id
            == trigger.obligation_id
        )
        if len(probe_settlements) < len(result.probe_ids):
            raise ExperimentArchiveIntegrityError(
                "Diagnostic result lacks enough isolated probe settlements."
            )
        available_budget = sum(
            item.consumed_budget for item in probe_settlements
        )
        if result.consumed_simulation_budget > available_budget + 1e-12:
            raise ExperimentArchiveIntegrityError(
                "Diagnostic result exceeds its traceable simulation budget."
            )


def _council_fingerprint(tournament: CouncilLeastRegretTournament) -> str:
    payload = {
        "policy": tournament.policy.model_dump(mode="json"),
        "ledger": tournament.state.model_dump(mode="json"),
    }
    return _digest(canonical_json_bytes(payload))


def _validate_council_links(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    diagnostics: DiagnosticEngine,
    council: CouncilLeastRegretTournament,
) -> None:
    """Close the durable Council edges represented by the v0.9 ledger."""
    if council.policy != CouncilInterventionPolicy():
        raise ExperimentArchiveIntegrityError(
            "Council archive cannot prove a non-default policy without durable "
            "candidate observations."
        )
    results = {item.result_id: item for item in diagnostics.state.results}
    obligations = {
        item.diagnostic_id: item for item in diagnostics.state.obligations
    }
    reservations = {
        item.reservation_id: item for item in ledger.state.reservations
    }
    settlements = tuple(ledger.state.settlements)
    for decision in council.state.decisions:
        result = results.get(decision.diagnostic_result_id)
        diagnostic = (
            obligations.get(result.diagnostic_id) if result is not None else None
        )
        if result is None or diagnostic is None:
            raise ExperimentArchiveIntegrityError(
                "Council ledger lost its terminal Diagnostic Result."
            )
        if result.conclusion in {
            DiagnosticConclusion.VALID_NULL,
            DiagnosticConclusion.INCONCLUSIVE,
        }:
            raise ExperimentArchiveIntegrityError(
                "Council ledger cites a non-actionable Diagnostic Result."
            )
        if decision.policy_version != council.policy.policy_version:
            raise ExperimentArchiveIntegrityError(
                "Council decision disagrees with its paired policy."
            )
        if diagnostic.trigger.obligation_id not in kernel.state.obligation_kernels:
            raise ExperimentArchiveIntegrityError(
                "Council ledger lost its parent obligation."
            )
        for candidate_id in decision.candidate_ids:
            linked = tuple(
                settlement
                for settlement in settlements
                if candidate_id in settlement.result_refs
            )
            valid = any(
                settlement.canonical_unchanged
                and settlement.disposition == SimulationDisposition.DISCARDED
                and reservations[settlement.reservation_id].obligation_id
                == diagnostic.trigger.obligation_id
                for settlement in linked
            )
            if not valid:
                raise ExperimentArchiveIntegrityError(
                    "Council ledger lost a candidate's isolated simulation lineage."
                )


def experiment_archive_bytes(
    kernel: VerdantKernel,
    ledger: SimulationLedger,
    *,
    lens_system: EquivalenceLensSystem | None = None,
    diagnostic_engine: DiagnosticEngine | None = None,
    council_tournament: CouncilLeastRegretTournament | None = None,
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
    if diagnostic_engine is not None:
        if lens_system is None:
            raise ExperimentArchiveIntegrityError(
                "Diagnostic archives require their paired Lens sidecar."
            )
        diagnostics = DiagnosticEngine.from_snapshot(diagnostic_engine.snapshot())
        _validate_diagnostic_links(canonical, simulation, lenses, diagnostics)
        files[_DIAGNOSTIC_LEDGER] = canonical_json_bytes(
            diagnostics.state.model_dump(mode="json")
        )
        fingerprints["diagnostic_fingerprint"] = diagnostics.fingerprint()
        format_version = EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT
    if council_tournament is not None:
        if diagnostic_engine is None:
            raise ExperimentArchiveIntegrityError(
                "Council archives require their paired Diagnostic sidecar."
            )
        council = CouncilLeastRegretTournament(
            policy=CouncilInterventionPolicy.model_validate(
                council_tournament.policy.model_dump(mode="json")
            ),
            state=CouncilInterventionLedgerState.model_validate(
                council_tournament.snapshot()
            ),
        )
        _validate_council_links(canonical, simulation, diagnostics, council)
        files[_COUNCIL_POLICY] = canonical_json_bytes(
            council.policy.model_dump(mode="json")
        )
        files[_COUNCIL_LEDGER] = canonical_json_bytes(
            council.state.model_dump(mode="json")
        )
        fingerprints["council_fingerprint"] = _council_fingerprint(council)
        format_version = EXPERIMENT_ARCHIVE_COUNCIL_FORMAT
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
    diagnostic_engine: DiagnosticEngine | None = None,
    council_tournament: CouncilLeastRegretTournament | None = None,
) -> str:
    """Replace one archive after syncing its bytes, then its POSIX directory."""
    data = experiment_archive_bytes(
        kernel,
        ledger,
        lens_system=lens_system,
        diagnostic_engine=diagnostic_engine,
        council_tournament=council_tournament,
    )
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
        elif format_version == EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT:
            expected_files = _V3_FILES
            expected_manifest_keys = {
                "format", "canonical_fingerprint", "simulation_fingerprint",
                "lens_fingerprint", "diagnostic_fingerprint", "files",
            }
        elif format_version == EXPERIMENT_ARCHIVE_COUNCIL_FORMAT:
            expected_files = _V4_FILES
            expected_manifest_keys = {
                "format", "canonical_fingerprint", "simulation_fingerprint",
                "lens_fingerprint", "diagnostic_fingerprint",
                "council_fingerprint", "files",
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
        if format_version in {
            EXPERIMENT_ARCHIVE_FORMAT,
            EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT,
            EXPERIMENT_ARCHIVE_COUNCIL_FORMAT,
        }:
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
        diagnostics = None
        if format_version in {
            EXPERIMENT_ARCHIVE_DIAGNOSTIC_FORMAT,
            EXPERIMENT_ARCHIVE_COUNCIL_FORMAT,
        }:
            diagnostic_bytes = files[_DIAGNOSTIC_LEDGER]
            diagnostic_state = DiagnosticLedgerState.model_validate_json(
                diagnostic_bytes
            )
            if (
                canonical_json_bytes(diagnostic_state.model_dump(mode="json"))
                != diagnostic_bytes
            ):
                raise ExperimentArchiveIntegrityError(
                    "Diagnostic JSON is not canonical."
                )
            diagnostics = DiagnosticEngine.from_snapshot(
                diagnostic_state.model_dump(mode="json")
            )
            if manifest["diagnostic_fingerprint"] != diagnostics.fingerprint():
                raise ExperimentArchiveIntegrityError("Archive fingerprint mismatch.")
            _validate_diagnostic_links(kernel, ledger, lenses, diagnostics)
        council = None
        if format_version == EXPERIMENT_ARCHIVE_COUNCIL_FORMAT:
            policy_bytes = files[_COUNCIL_POLICY]
            council_bytes = files[_COUNCIL_LEDGER]
            policy = CouncilInterventionPolicy.model_validate_json(policy_bytes)
            council_state = CouncilInterventionLedgerState.model_validate_json(
                council_bytes
            )
            if (
                canonical_json_bytes(policy.model_dump(mode="json"))
                != policy_bytes
                or canonical_json_bytes(council_state.model_dump(mode="json"))
                != council_bytes
            ):
                raise ExperimentArchiveIntegrityError(
                    "Council JSON is not canonical."
                )
            council = CouncilLeastRegretTournament(
                policy=policy,
                state=council_state,
            )
            if manifest["council_fingerprint"] != _council_fingerprint(council):
                raise ExperimentArchiveIntegrityError("Archive fingerprint mismatch.")
            _validate_council_links(kernel, ledger, diagnostics, council)
        return ExperimentArchiveBundle(
            kernel=kernel,
            simulation_ledger=ledger,
            lens_system=lenses,
            diagnostic_engine=diagnostics,
            council_tournament=council,
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
