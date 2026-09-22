from __future__ import annotations

import hashlib
import json
import math

import pytest

from verdant_development.pipeline import DevelopmentalCycleConfig
from verdant_development.v5x import V5XDevelopmentPipeline, controlled_development_config
from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    VerdantKernel,
)
from verdant_thermodynamics import (
    AppendOnlyTelemetryWriter,
    PhaseHysteresis,
    PhasePolicyController,
    ThermodynamicPhase,
    VerdantThermodynamicObserver,
    classify_phase,
    cognitive_temperature,
    compute_t_g,
    normalized_shannon_from_nonnegative,
    record_from_development,
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _command(event_key: str, *, sentence: str = "alpha beta", features=(1.0, 0.0, 0.0)):
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"thermo:{event_key}",
        modality="text",
        payload_sha256=_digest(event_key + sentence),
        feature_vector=tuple(features),
        concept_labels=(event_key.split("-")[0],),
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"thermodynamic_test": True},
        metadata={"sentence": sentence},
    )


def test_normalized_shannon_has_expected_extremes() -> None:
    entropy, mass = normalized_shannon_from_nonnegative([0.0, 0.0, 0.0, 0.0])
    assert entropy == 0.0
    assert mass == 0.0

    entropy, mass = normalized_shannon_from_nonnegative([1.0, 1.0, 1.0, 1.0])
    assert entropy == pytest.approx(1.0)
    assert mass == 4.0

    entropy, _ = normalized_shannon_from_nonnegative([1.0, 0.0, 0.0, 0.0])
    assert entropy == 0.0


def test_v4_compat_tg_formula_is_exact_and_bounded() -> None:
    t_g, complexity, base, feedback = compute_t_g(0.2, 0.6, 0.25, 0.5)
    assert complexity == pytest.approx(0.4)
    assert base == pytest.approx(0.4 + 0.3 * 0.4 - 0.2 * 0.25)
    assert feedback == pytest.approx(0.1 * math.sin(math.pi * 0.5))
    assert t_g == pytest.approx(base + feedback)

    assert compute_t_g(-9, -9, 9, 0)[0] == pytest.approx(0.2)
    assert 0.1 <= compute_t_g(9, 9, -9, 0.5)[0] <= 0.9


def test_phase_boundaries_match_v4() -> None:
    assert classify_phase(0.399) == ThermodynamicPhase.RIGID
    assert classify_phase(0.4) == ThermodynamicPhase.FLEXIBLE
    assert classify_phase(0.6) == ThermodynamicPhase.FLEXIBLE
    assert classify_phase(0.601) == ThermodynamicPhase.CHAOTIC


def test_cognitive_temperature_matches_recovered_definition() -> None:
    assert cognitive_temperature(0.55, 0.25) == pytest.approx(0.70)


def test_text_input_adapter_uses_v4_token_count_complexity() -> None:
    kernel = VerdantKernel(seed=2301, state_dim=24, run_label="thermo-token")
    result = V5XDevelopmentPipeline().advance(
        kernel,
        _command("alpha-1", sentence="one two three four five"),
    )
    assert result.thermodynamics is not None
    assert result.thermodynamics.input.adapter_revision == "text_token_count_v4_compat_1"
    assert result.thermodynamics.input.token_count == 5
    assert result.thermodynamics.c_input == pytest.approx(0.05)


def test_observer_is_deterministic_and_measurement_only() -> None:
    enabled = VerdantKernel(seed=2302, state_dim=32, run_label="thermo-null")
    disabled = VerdantKernel(seed=2302, state_dim=32, run_label="thermo-null")
    command = _command("alpha-1", sentence="alpha arrives")

    with_observer = V5XDevelopmentPipeline(enable_thermodynamic_observation=True)
    without_observer = V5XDevelopmentPipeline(enable_thermodynamic_observation=False)
    observed = with_observer.advance(enabled, command)
    unobserved = without_observer.advance(disabled, command)

    assert observed.thermodynamics is not None
    assert unobserved.thermodynamics is None
    assert enabled.snapshot() == disabled.snapshot()
    assert enabled.fingerprint() == disabled.fingerprint()

    replay_kernel = VerdantKernel(seed=2302, state_dim=32, run_label="thermo-null")
    replay_result = V5XDevelopmentPipeline().advance(replay_kernel, command)
    assert replay_result.thermodynamics == observed.thermodynamics


def test_contradiction_pressure_increases_environmental_uncertainty() -> None:
    kernel = VerdantKernel(seed=2303, state_dim=32, run_label="thermo-contradiction")
    pipeline = V5XDevelopmentPipeline()
    positive = ExperienceCommand(
        event_key="indicator-positive",
        source_ref="thermo:positive",
        modality="text",
        payload_sha256=_digest("positive"),
        feature_vector=(1.0, 0.0, 0.0),
        claim_proposals=(ClaimProposal(
            subject_label="indicator",
            predicate="has_property",
            object_label="bright",
            polarity=ClaimPolarity.AFFIRMED,
            source_class=ClaimSourceClass.DIRECT_OBSERVATION,
            confidence=1.0,
        ),),
        semantic_evidence_kind=EvidenceKind.OBSERVATION,
        metadata={"sentence": "indicator is bright"},
    )
    negative = positive.model_copy(update={
        "event_key": "indicator-negative",
        "source_ref": "thermo:negative",
        "payload_sha256": _digest("negative"),
        "claim_proposals": (ClaimProposal(
            subject_label="indicator",
            predicate="has_property",
            object_label="bright",
            polarity=ClaimPolarity.NEGATED,
            source_class=ClaimSourceClass.DIRECT_OBSERVATION,
            confidence=1.0,
        ),),
        "metadata": {"sentence": "indicator is not bright"},
    })

    quiet = pipeline.advance(kernel, positive)
    stressed = pipeline.advance(kernel, negative)
    assert quiet.thermodynamics is not None and stressed.thermodynamics is not None
    assert stressed.experience.contradiction_ids
    assert stressed.thermodynamics.environment.mean_contradiction_pressure > 0.0
    assert stressed.thermodynamics.h_env > quiet.thermodynamics.h_env


def test_phase_controller_only_proposes_and_never_mutates_kernel() -> None:
    kernel = VerdantKernel(seed=2304, state_dim=24, run_label="thermo-controller")
    state = V5XDevelopmentPipeline().advance(kernel, _command("alpha-1")).thermodynamics
    assert state is not None
    before = kernel.fingerprint()

    proposal = PhasePolicyController().propose(state)

    assert not proposal.behavioral_authority_enabled
    assert kernel.fingerprint() == before


def test_soft_homeostasis_rigid_policy_favors_current_evidence_without_memory_deletion() -> None:
    base = DevelopmentalCycleConfig()
    proposal = PhasePolicyController(
        experimental_control_enabled=True
    ).propose_for_phase(ThermodynamicPhase.RIGID)

    effective = controlled_development_config(base, proposal)

    assert proposal.behavioral_authority_enabled
    assert effective.current_evidence_resource > base.current_evidence_resource
    assert effective.resonance_resource < base.resonance_resource
    assert effective.resonance_recall_threshold > base.resonance_recall_threshold
    assert effective.association_resource < base.association_resource
    assert effective.structure_resource < base.structure_resource
    assert effective.association_recall_threshold > base.association_recall_threshold
    assert effective.structure_trigger_members == base.structure_trigger_members + 1
    assert effective.structure_trigger_fraction == pytest.approx(0.50)
    # Rigid access control does not broaden resonance. The checkpoint probe
    # showed that freeing slots can otherwise replace P intrusion with weak,
    # unrelated resonant candidates.
    assert effective.resonance_top_k == base.resonance_top_k
    assert effective.resonance_commit_limit == base.resonance_commit_limit


def test_soft_homeostasis_hysteresis_prevents_boundary_flapping() -> None:
    hysteresis = PhaseHysteresis()

    # Flexible does not enter Rigid on a tiny dip below the raw 0.4 boundary.
    assert hysteresis.select(0.399, ThermodynamicPhase.FLEXIBLE) == ThermodynamicPhase.FLEXIBLE
    assert hysteresis.select(0.379, ThermodynamicPhase.FLEXIBLE) == ThermodynamicPhase.RIGID

    # Once Rigid, it stays Rigid until the wider exit boundary is crossed.
    assert hysteresis.select(0.401, ThermodynamicPhase.RIGID) == ThermodynamicPhase.RIGID
    assert hysteresis.select(0.419, ThermodynamicPhase.RIGID) == ThermodynamicPhase.RIGID
    assert hysteresis.select(0.420, ThermodynamicPhase.RIGID) == ThermodynamicPhase.FLEXIBLE

    # The same rule applies on the chaotic side.
    assert hysteresis.select(0.601, ThermodynamicPhase.FLEXIBLE) == ThermodynamicPhase.FLEXIBLE
    assert hysteresis.select(0.621, ThermodynamicPhase.FLEXIBLE) == ThermodynamicPhase.CHAOTIC
    assert hysteresis.select(0.599, ThermodynamicPhase.CHAOTIC) == ThermodynamicPhase.CHAOTIC
    assert hysteresis.select(0.580, ThermodynamicPhase.CHAOTIC) == ThermodynamicPhase.FLEXIBLE


def test_soft_homeostasis_flexible_policy_is_identity() -> None:
    base = DevelopmentalCycleConfig()
    proposal = PhasePolicyController(
        experimental_control_enabled=True
    ).propose_for_phase(ThermodynamicPhase.FLEXIBLE)

    assert controlled_development_config(base, proposal) == base


def test_soft_homeostasis_requires_observer_when_control_is_enabled() -> None:
    with pytest.raises(ValueError, match="requires thermodynamic observation"):
        V5XDevelopmentPipeline(
            enable_thermodynamic_observation=False,
            enable_thermodynamic_control=True,
        )


def test_soft_homeostasis_applies_previous_cycle_only_and_does_not_rewrite_kernel_policies() -> None:
    kernel = VerdantKernel(seed=2310, state_dim=24, run_label="thermo-homeostasis")
    pipeline = V5XDevelopmentPipeline(enable_thermodynamic_control=True)

    first = pipeline.advance(kernel, _command("alpha-1", sentence="alpha arrives"))
    assert first.thermodynamic_control is None
    assert first.thermodynamics is not None

    kernel_id = kernel.state.identity.kernel_id
    pipeline._last_thermodynamics[kernel_id] = first.thermodynamics.model_copy(
        update={"phase": ThermodynamicPhase.RIGID, "t_g": 0.35}
    )

    workspace_policy_before = kernel.state.workspace_policy.model_copy(deep=True)
    ecwf_policy_before = kernel.state.ecwf_policy.model_copy(deep=True)
    compilation_policy_before = kernel.state.compilation_policy.model_copy(deep=True)
    plasticity_policy_before = kernel.state.plasticity_policy.model_copy(deep=True)

    second = pipeline.advance(kernel, _command("beta-2", sentence="beta arrives"))

    assert second.thermodynamic_control is not None
    assert second.thermodynamic_control.source_phase == ThermodynamicPhase.RIGID
    assert second.thermodynamic_control.control_phase == ThermodynamicPhase.RIGID
    assert second.thermodynamic_control.source_t_g == pytest.approx(0.35)
    assert second.thermodynamic_control.effective_config["structure_trigger_members"] == 2
    assert second.thermodynamic_control.effective_config["structure_trigger_fraction"] == pytest.approx(0.50)
    assert second.thermodynamic_control.effective_config["resonance_recall_threshold"] == pytest.approx(0.32)
    assert second.thermodynamic_control.effective_config["association_recall_threshold"] > 0.24

    assert kernel.state.workspace_policy == workspace_policy_before
    assert kernel.state.ecwf_policy == ecwf_policy_before
    assert kernel.state.compilation_policy == compilation_policy_before
    assert kernel.state.plasticity_policy == plasticity_policy_before


def test_append_only_telemetry_serializes_development_cycle(tmp_path) -> None:
    kernel = VerdantKernel(seed=2305, state_dim=24, run_label="thermo-telemetry")
    pipeline = V5XDevelopmentPipeline()
    output = tmp_path / "cycles.jsonl"
    writer = AppendOnlyTelemetryWriter(output)

    for index in range(2):
        result = pipeline.advance(kernel, _command(f"alpha-{index + 1}"))
        writer.append(record_from_development(kernel=kernel, result=result, run_id="test-run", branch_commit="V5-X"))

    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(rows) == 2
    assert rows[0]["schema_id"] == "verdant.development_telemetry.v1"
    assert rows[0]["thermodynamics"]["formula_revision"] == "tg_v4_compat_1"
    assert rows[0]["modality"] == "text"
    assert rows[1]["cycle"] > rows[0]["cycle"]


def test_cultivation_session_writes_thermodynamic_jsonl(tmp_path) -> None:
    from run_v5x_cultivation import V5XCultivationSession

    kernel = VerdantKernel(seed=2306, state_dim=24, run_label="cultivation-telemetry")
    output = tmp_path / "cultivation.jsonl"
    session = V5XCultivationSession(
        kernel,
        tmp_path / "checkpoint.vdk",
        telemetry_writer=AppendOnlyTelemetryWriter(output),
        run_id="cultivation-test",
        branch_commit="V5-X-test",
    )
    session.teach(("alpha", "beta"), context_id="pair")

    row = json.loads(output.read_text().strip())
    assert row["run_id"] == "cultivation-test"
    assert row["branch_commit"] == "V5-X-test"
    assert row["thermodynamics"]["metadata"]["behavioral_authority"] is False


def test_t0_sweep_is_null_equivalent_and_formula_spans_all_regions() -> None:
    from verdant_benchmarks.thermodynamic_sweep import ThermodynamicSweepHarness

    summary = ThermodynamicSweepHarness(seed=2307, state_dim=24).run()
    assert summary.observer_null_equivalence
    assert summary.governance_tg_unchanged
    assert summary.formula_grid["all_phase_regions_reachable"]
    assert summary.formula_grid["phase_counts"]["Rigid"] > 0
    assert summary.formula_grid["phase_counts"]["Flexible"] > 0
    assert summary.formula_grid["phase_counts"]["Chaotic"] > 0
