"""Predeclared, checkpoint-forked detector study for thermodynamic homeostasis.

This is NOT an accuracy benchmark or a rewritten Tg classifier. Observes the
V4-compatible Tg formula and measures conservative access under a fixed v4
policy. All runs start from fresh checkpoint forks and do not write checkpoints.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path

from verdant_development import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_development.v5x import V5XDevelopmentPipeline, controlled_development_config
from verdant_kernel import VerdantKernel
from verdant_thermodynamics import PhasePolicyController, ThermodynamicPhase, VerdantThermodynamicObserver

from run_v5x_thermodynamic_homeostasis import (
    DEFAULT_PROBES, _access_metrics, _command, _known_labels, _load,
    _thermodynamic_summary, _workspace_summary,
)

STUDY_SCHEMA = "verdant.v5x.homeostasis_detector_study.v1"
# Chosen before inspecting the new study's results. Missing labels are skipped,
# never added to the organism merely to make a test run.
EXTENDED_PROBES = (
    ("sensor",),
    ("switch",),
    ("pressure_sensor",),
    ("circuit_path", "switch"),
    ("pressure_state", "pressure_sensor"),
    ("actuator", "controller", "sensor"),
    ("target_point",),
    ("forward_axis",),
    ("motion", "moving_mass"),
    ("rough_surface", "sliding_block"),
    ("foundation", "load"),
)
ABLATION_PROBES = {
    ("controller",),
    ("switch", "load"),
    ("actuator", "sensor"),
    ("foundation", "frame"),
}
TOKEN_COUNTS = (0, 60)


def _probe_command(labels: tuple[str, ...], state_dim: int, key: str, tokens: int):
    """Hold labels, feature vector, event identity and payload SHA constant.

    Only the optional sentence metadata differs between verbosity forks.
    Tokens=0 removes the sentence adapter and uses feature-distribution
    complexity; it is intentionally NOT compared directly to the 60-token
    condition as a pure verbosity intervention. See the 1 vs 60 pair below.
    """
    command = _command(labels, state_dim=state_dim, event_key=key)
    if tokens == 0:
        return command.model_copy(update={
            "metadata": {
                **command.metadata,
                "sentence": None,
                "detector_study_tokens": 0,
            }
        })
    if tokens == 60:
        sentence = " ".join([*labels, *("context" for _ in range(60 - len(labels)))])
        return command.model_copy(update={
            "metadata": {
                **command.metadata,
                "sentence": sentence,
                "detector_study_tokens": 60,
            }
        })
    raise ValueError("tokens must be 0 or 60")


def _run_arm(checkpoint: Path, command, config: DevelopmentalCycleConfig) -> dict:
    kernel = _load(checkpoint)
    before = kernel.fingerprint()
    result = VerdantDevelopmentPipeline(config=config).advance(kernel, command)
    observer = VerdantThermodynamicObserver()
    measured = observer.inspect(
        kernel, command, candidate_scope_count=len(result.candidate_scope_ids),
        workspace_report=result.workspace.report if result.workspace else None,
    )
    workspace = _workspace_summary(kernel, result)
    # These are post-cycle outcomes. They must NOT be used as if they were
    # measurements available to the controller before this same cycle.
    return {
        "starting_fingerprint": before,
        "ending_fingerprint": kernel.fingerprint(),
        "thermodynamics_post_cycle": _thermodynamic_summary(measured),
        "access_post_cycle": _access_metrics(workspace),
        "admitted_p": [
            {"name": row["label"], "bindings": row["bindings"],
             "trigger_bindings": row["trigger_bindings"],
             "trigger_fraction": row["trigger_fraction"]}
            for row in workspace["admitted_earned_structures"]
        ],
        "admitted_local": [
            {"bindings": row["bindings"], "strength": row["association_strength"]}
            for row in workspace["admitted_local_associations"]
        ],
        "admitted_resonance": [
            {"bindings": row["bindings"], "score": row["resonance_score"],
             "support": row["local_support_strength"]}
            for row in workspace["admitted_resonance"]
        ],
    }


def _arm_configs() -> dict[str, DevelopmentalCycleConfig]:
    base = DevelopmentalCycleConfig()
    rigid = controlled_development_config(
        base,
        PhasePolicyController(
            experimental_control_enabled=True
        ).propose_for_phase(ThermodynamicPhase.RIGID),
    )
    return {
        "observer_baseline": base,
        "v4_both_resonance_gates": rigid,
        "score_only_ablation": replace(rigid, resonance_local_support_floor=0.0),
        "support_only_ablation": replace(rigid, resonance_recall_threshold=0.0),
        "neither_resonance_gate": replace(
            rigid, resonance_recall_threshold=0.0,
            resonance_local_support_floor=0.0,
        ),
    }


def _lag_stream(checkpoint: Path, labels: tuple[str, ...]) -> dict:
    """Test actual previous-cycle control across a short repeated cue stream."""
    normal = _load(checkpoint)
    experimental = _load(checkpoint)
    normal_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=False,
    )
    experiment_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=True,
    )
    rows = []
    for index in range(3):
        command = _command(
            labels, state_dim=normal.state.field.state_dim,
            event_key="detector-lag-" + "-".join(labels) + "-" + str(index),
        )
        prior = rows[-1]["observer"]["t_g"] if rows else None
        baseline = normal_pipeline.advance(normal, command)
        controlled = experiment_pipeline.advance(experimental, command)
        rows.append({
            "step": index + 1,
            "previous_cycle_t_g": prior,
            "observer": _thermodynamic_summary(baseline.thermodynamics),
            "controlled": _thermodynamic_summary(controlled.thermodynamics),
            "control": (
                {
                    "source_cycle": controlled.thermodynamic_control.source_cycle,
                    "source_t_g": controlled.thermodynamic_control.source_t_g,
                    "raw_source_phase": controlled.thermodynamic_control.source_phase.value,
                    "control_phase": controlled.thermodynamic_control.control_phase.value,
                    "effective_config": controlled.thermodynamic_control.effective_config,
                }
                if controlled.thermodynamic_control else None
            ),
            "observer_access": _access_metrics(_workspace_summary(normal, baseline)),
            "controlled_access": _access_metrics(
                _workspace_summary(experimental, controlled)
            ),
            "fingerprints_equal": normal.fingerprint() == experimental.fingerprint(),
        })
    return {"labels": list(labels), "steps": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "checkpoints", type=Path, nargs="+",
        help="At least one existing VDK; more checkpoints provide held-out cases.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--quick", action="store_true",
        help="Only original seven probes; all other safeguards remain enabled.",
    )
    args = parser.parse_args()
    configurations = _arm_configs()
    probes = DEFAULT_PROBES if args.quick else (
        *DEFAULT_PROBES, *EXTENDED_PROBES,
    )
    all_cases: list[dict] = []
    all_lag: list[dict] = []
    for checkpoint in args.checkpoints:
        checkpoint = checkpoint.resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        checkpoint_sha = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        reference = _load(checkpoint)
        labels_in_memory = _known_labels(reference)
        initial_fingerprint = reference.fingerprint()
        print(f"[detector] {checkpoint.name} | {initial_fingerprint[:12]}", flush=True)
        for labels in probes:
            missing = [label for label in labels if label not in labels_in_memory]
            if missing:
                all_cases.append({
                    "checkpoint_sha256": checkpoint_sha,
                    "labels": list(labels), "skipped": True,
                    "missing_labels": missing,
                })
                continue
            for tokens in TOKEN_COUNTS:
                key = "detector-study-" + "-".join(labels)
                command = _probe_command(
                    labels, reference.state.field.state_dim, key, tokens,
                )
                arms = {}
                selected = ("observer_baseline", "v4_both_resonance_gates")
                if labels in ABLATION_PROBES:
                    selected = tuple(configurations)
                for name in selected:
                    print(
                        f"  {' + '.join(labels)} | tokens={tokens} | {name}",
                        flush=True,
                    )
                    arms[name] = _run_arm(
                        checkpoint, command, configurations[name],
                    )
                    if arms[name]["starting_fingerprint"] != initial_fingerprint:
                        raise RuntimeError("A/B arms did not start identically")
                all_cases.append({
                    "checkpoint_sha256": checkpoint_sha,
                    "labels": list(labels), "tokens": tokens,
                    "skipped": False, "arms": arms,
                })
        for labels in (("actuator",), ("foundation", "frame")):
            if set(labels).issubset(labels_in_memory):
                print(f"  lag stream {' + '.join(labels)}", flush=True)
                all_lag.append({
                    "checkpoint_sha256": checkpoint_sha,
                    **_lag_stream(checkpoint, labels),
                })
    report = {
        "schema_id": STUDY_SCHEMA,
        "method": {
            "all_arms_start_from_same_checkpoint": True,
            "policy_revision": "phase_policy_homeostasis_4",
            "legacy_tg_formula_unchanged": True,
            "controller_default_is_observer_only": True,
            "plasticity_control_enabled": False,
            "raw_phase_classifier_unchanged": True,
            "post_cycle_tg_is_not_a_pre_cycle_detector_measurement": True,
            "token_conditions": list(TOKEN_COUNTS),
            "token_interpretation": (
                "0 tokens selects feature-distribution adapter; 60 tokens "
                "selects 60-token text adapter. These are not directly a "
                "pure length-only comparison. Compare within the same adapter "
                "using separate token-count cases before interpreting Tg."
            ),
            "pressure_proxy": (
                "Count and historical-resource allocation of admitted P "
                "structures with present-cue trigger fraction < 0.50. This "
                "is structural access pressure, NOT semantic truth or "
                "classifier ground truth."
            ),
            "ablations_only_on": [list(labels) for labels in sorted(ABLATION_PROBES)],
        },
        "checkpoints": [
            {"path": str(p.resolve()),
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in args.checkpoints
        ],
        "arm_configs": {
            key: vars(config) for key, config in configurations.items()
        },
        "paired_cases": all_cases,
        "lag_streams": all_lag,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8",
    )
    print(f"[detector] report: {args.output.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
