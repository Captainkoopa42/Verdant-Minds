"""Read-only-original dashboard readiness smoke against a native VDK checkpoint.

Tests V5-X Workbench adapter load, a disposable teaching fork, thermodynamic
observability, saving and reopening; never imports or overwrites the source.
This is a backend smoke, NOT a frontend build or a real UI-click test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "workbench" / "backend"
for directory in (ROOT, BACKEND):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from verdant_workbench.models import CommandEnvelope, TeachingRequest
from verdant_workbench.v5x_adapter import V5XEngineAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.checkpoint.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    run_id = "run_thermo_dashboard_smoke"
    organism_id = "org_thermo_dashboard_smoke"
    adapter = V5XEngineAdapter.load(
        source, run_id=run_id, organism_id=organism_id,
    )
    original_fingerprint = adapter.kernel.fingerprint()
    original_cycle = adapter.kernel.state.cycle
    if adapter.development.enable_thermodynamic_control:
        raise RuntimeError("Workbench loaded a checkpoint with automatic control on.")
    if not adapter.development.enable_thermodynamic_observation:
        raise RuntimeError("Workbench must have thermodynamic observation on.")
    event_key = "thermo-dashboard-smoke-" + original_sha[:12]
    if event_key in adapter.kernel.state.processed_event_keys:
        raise RuntimeError("Smoke event key already used by the source checkpoint.")
    receipt = adapter.submit_teaching(
        CommandEnvelope(
            command_id="cmd_" + event_key,
            run_id=adapter.run_id,
            organism_id=adapter.organism_id,
            command_type="TEACH",
            expected_state_revision=adapter.state_revision,
            actor="test",
        ),
        TeachingRequest(
            context_id="thermo-dashboard-smoke",
            labels=("foundation", "frame"),
            event_key=event_key,
        ),
    )
    if receipt.replayed:
        raise RuntimeError("Smoke teaching replayed unexpectedly.")
    if not receipt.result["semantic_firewall_held"]:
        raise RuntimeError("Developmental semantic firewall failed.")
    events = tuple(
        event for event in receipt.events
        if event.event_type == "THERMODYNAMIC_OBSERVED"
    )
    if len(events) != 1 or receipt.result["thermodynamic_control"] is not None:
        raise RuntimeError("Expected one observer event and no control action.")
    pressure_events = tuple(
        event for event in receipt.events
        if event.event_type == "ACCESS_PRESSURE_OBSERVED"
    )
    pressure = receipt.result["access_pressure_observation"]
    if len(pressure_events) != 1 or pressure is None:
        raise RuntimeError("Expected one pre-admission access-pressure event.")
    if pressure["behavioral_authority_enabled"]:
        raise RuntimeError("Access-pressure observation gained behavioral authority.")
    if (
        pressure["canonical_state_fingerprint"] != original_fingerprint
        or pressure["cycle_before_experience"] != original_cycle
    ):
        raise RuntimeError("Access pressure was not measured against the pre-admission state.")
    observed = receipt.result["thermodynamic_observation"]
    if observed is None or observed["metadata"]["behavioral_authority"]:
        raise RuntimeError("Thermodynamic observation is missing or authoritative.")
    after_teach_fingerprint = adapter.kernel.fingerprint()
    with TemporaryDirectory(prefix="verdant-thermo-dashboard-") as temp:
        checkpoint_fork_path = Path(temp) / "dashboard-fork.vdk"
        saved = adapter.save(checkpoint_fork_path)
        reopened = V5XEngineAdapter.load(
            saved.path, run_id=run_id, organism_id=organism_id,
        )
        if reopened.kernel.fingerprint() != after_teach_fingerprint:
            raise RuntimeError("Saving/reopening altered the fork's organism state.")
        if reopened.development.enable_thermodynamic_control:
            raise RuntimeError("Reopened Workbench turned on automatic control.")
        if not reopened.development.enable_thermodynamic_observation:
            raise RuntimeError("Reopened Workbench lost thermodynamic observation.")
    if hashlib.sha256(source.read_bytes()).hexdigest() != original_sha:
        raise RuntimeError("Original VDK changed during smoke test.")
    report = {
        "schema_id": "verdant.v5x.thermodynamic_dashboard_smoke.v1",
        "original_checkpoint_sha256": original_sha,
        "original_fingerprint": original_fingerprint,
        "original_cycle": original_cycle,
        "post_teaching_fingerprint": after_teach_fingerprint,
        "post_teaching_cycle": adapter.kernel.state.cycle,
        "reopened_fingerprint_equal": True,
        "observer_event_type": events[0].event_type,
        "access_pressure_event_type": pressure_events[0].event_type,
        "access_pressure_measurement_status": pressure["measurement_status"],
        "access_pressure_pre_cycle_provenance": True,
        "observed_t_g": observed["t_g"],
        "observed_phase": observed["phase"],
        "automatic_control_enabled": False,
        "original_checkpoint_unchanged": True,
        "scope": "backend V5-X Workbench adapter smoke; frontend build and UI workflow not covered",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Report: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
