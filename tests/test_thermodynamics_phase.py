from __future__ import annotations

import hashlib
import json
import math

import pytest

from verdant_development.v5x import V5XDevelopmentPipeline
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
