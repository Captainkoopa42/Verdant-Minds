from __future__ import annotations

import json

from verdant_workbench.models import CommandEnvelope, OrganismConfig, TeachingRequest
from verdant_workbench.v5x_adapter import V5XEngineAdapter


def _envelope(adapter: V5XEngineAdapter, key: str) -> CommandEnvelope:
    return CommandEnvelope(
        command_id="cmd_" + key,
        run_id=adapter.run_id,
        organism_id=adapter.organism_id,
        command_type="TEACH",
        expected_state_revision=adapter.state_revision,
        actor="test",
    )


def test_v5x_workbench_emits_durable_observer_event_without_control() -> None:
    adapter = V5XEngineAdapter.create(
        OrganismConfig(seed=9501, state_dim=24, run_label="homeostasis-ui"),
        run_id="run_homeostasis_ui",
        organism_id="org_homeostasis_ui",
    )
    receipt = adapter.submit_teaching(
        _envelope(adapter, "teach01"),
        TeachingRequest(context_id="homeostasis", labels=("alpha",), event_key="teach01"),
    )

    measured = [event for event in receipt.events
                if event.event_type == "THERMODYNAMIC_OBSERVED"]
    controlled = [event for event in receipt.events
                  if event.event_type == "THERMODYNAMIC_CONTROL_APPLIED"]

    assert len(measured) == 1
    assert controlled == []
    assert receipt.result["thermodynamic_control"] is None
    assert receipt.result["thermodynamic_observation"]["metadata"]["behavioral_authority"] is False
    assert measured[0].payload["cycle"] == adapter.kernel.state.cycle

    replay = adapter.submit_teaching(
        _envelope(adapter, "teach02"),
        TeachingRequest(context_id="homeostasis", labels=("alpha",), event_key="teach01"),
    )
    assert replay.replayed
    assert not any(event.event_type.startswith("THERMODYNAMIC_")
                   for event in replay.events)


def test_v5x_workbench_checkpoint_reopen_keeps_observer_only_default(tmp_path) -> None:
    adapter = V5XEngineAdapter.create(
        OrganismConfig(seed=9502, state_dim=24, run_label="homeostasis-reopen"),
        run_id="run_homeostasis_reopen",
        organism_id="org_homeostasis_reopen",
    )
    adapter.submit_teaching(
        _envelope(adapter, "first"),
        TeachingRequest(context_id="homeostasis", labels=("alpha",), event_key="first"),
    )
    original = adapter.kernel.fingerprint()
    saved = adapter.save(tmp_path / "homeostasis_reopen.vdk")

    restored = V5XEngineAdapter.load(
        saved.path,
        run_id="run_homeostasis_reopen",
        organism_id="org_homeostasis_reopen",
    )

    assert restored.kernel.fingerprint() == original
    assert restored.development.enable_thermodynamic_observation
    assert not restored.development.enable_thermodynamic_control
