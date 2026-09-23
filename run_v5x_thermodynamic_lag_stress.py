"""Stress the real N-to-N+1 thermodynamic controller with matched cue streams.

The Tg formula and access policy remain untouched.  This is a targeted
falsification test for verbosity-induced phase transitions, hysteresis, lag
and whether context-supported Ps survive an automatic control intervention.

Run against copied checkpoint *forks*; never mutate the input VDK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_development.v5x import V5XDevelopmentPipeline
from verdant_thermodynamics import ThermodynamicPhase
from run_v5x_thermodynamic_detector_study import _probe_command
from run_v5x_thermodynamic_homeostasis import (
    _access_metrics, _known_labels, _load, _thermodynamic_summary,
    _workspace_summary,
)

# Chosen using the previous single-cycle detector-study result. These are
# DEVELOPMENT examples, not held-out claims about generalization.
SEQUENCES = (
    (
        "high_recruitment_then_same_short",
        (
            (("actuator",), 60),
            (("actuator",), 1),
            (("foundation", "frame"), 1),
        ),
    ),
    (
        "high_recruitment_then_supported_context",
        (
            (("actuator", "controller", "sensor"), 60),
            (("foundation", "frame"), 1),
            (("actuator", "sensor"), 1),
        ),
    ),
    (
        "long_supported_context_negative_control",
        (
            (("foundation", "frame"), 60),
            (("actuator",), 1),
            (("foundation", "frame"), 1),
        ),
    ),
    (
        "short_recruitment_negative_control",
        (
            (("actuator",), 1),
            (("actuator",), 1),
            (("foundation", "frame"), 1),
        ),
    ),
)


def _control_record(result) -> dict | None:
    control = result.thermodynamic_control
    if control is None:
        return None
    return {
        "source_cycle": control.source_cycle,
        "source_t_g": control.source_t_g,
        "source_raw_phase": control.source_phase.value,
        "control_phase": control.control_phase.value,
        "policy_revision": control.policy.controller_revision,
        "effective_config": control.effective_config,
        "non_identity_policy": control.control_phase != ThermodynamicPhase.FLEXIBLE,
    }


def _run_sequence(checkpoint: Path, name: str, sequence) -> dict:
    baseline_kernel = _load(checkpoint)
    controlled_kernel = _load(checkpoint)
    baseline_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=False,
    )
    controlled_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=True,
    )
    initial_fingerprint = baseline_kernel.fingerprint()
    if controlled_kernel.fingerprint() != initial_fingerprint:
        raise RuntimeError("Sequences did not start from equal checkpoint forks.")

    rows = []
    for index, (labels, tokens) in enumerate(sequence, start=1):
        key = f"thermo-lag-stress-{name}-{index:02d}"
        command = _probe_command(
            labels, baseline_kernel.state.field.state_dim, key, tokens
        )
        observer = baseline_pipeline.advance(baseline_kernel, command)
        experimental = controlled_pipeline.advance(controlled_kernel, command)
        # These typed observations were captured before current-cue admission
        # and before prior-cycle control acted. Unknown cue concepts produce an
        # explicit incomplete record rather than a misleading zero count.
        pre_pressure = [
            item.access_pressure.model_dump(mode="json")
            if item.access_pressure is not None else None
            for item in (observer, experimental)
        ]
        control = _control_record(experimental)
        previous_observer_t_g = (
            rows[-1]["observer_t_g"] if rows else None
        )
        if control is not None:
            prior_controlled_t_g = rows[-1]["controlled_t_g"]
            if control["source_t_g"] != prior_controlled_t_g:
                raise RuntimeError("Controller source Tg is not previous controlled Tg.")
        elif index != 1:
            raise RuntimeError("Control metadata unexpectedly missing after cycle one.")

        observer_workspace = _workspace_summary(baseline_kernel, observer)
        controlled_workspace = _workspace_summary(controlled_kernel, experimental)
        observer_thermo = _thermodynamic_summary(observer.thermodynamics)
        controlled_thermo = _thermodynamic_summary(experimental.thermodynamics)
        print(
            f"  [{name} {index}/{len(sequence)}] {'+'.join(labels)} "
            f"tokens={tokens}, source={control['control_phase'] if control else 'initial'}, "
            f"Tg={observer_thermo['t_g']:.6f}",
            flush=True,
        )
        rows.append({
            "index": index,
            "labels": list(labels),
            "tokens": tokens,
            "previous_observer_t_g": previous_observer_t_g,
            "observer_pre_access_pressure": pre_pressure[0],
            "controlled_pre_access_pressure": pre_pressure[1],
            "control_applied_this_cycle": control,
            "observer_t_g": observer_thermo["t_g"],
            "controlled_t_g": controlled_thermo["t_g"],
            "observer_thermodynamics": observer_thermo,
            "controlled_thermodynamics": controlled_thermo,
            "observer_access": _access_metrics(observer_workspace),
            "controlled_access": _access_metrics(controlled_workspace),
            "observer_admitted_ps": [
                {"bindings": p["bindings"], "trigger_fraction": p["trigger_fraction"]}
                for p in observer_workspace["admitted_earned_structures"]
            ],
            "controlled_admitted_ps": [
                {"bindings": p["bindings"], "trigger_fraction": p["trigger_fraction"]}
                for p in controlled_workspace["admitted_earned_structures"]
            ],
            "observer_admitted_resonance": observer_workspace["admitted_resonance"],
            "controlled_admitted_resonance": controlled_workspace["admitted_resonance"],
            "fingerprints_equal": (
                baseline_kernel.fingerprint() == controlled_kernel.fingerprint()
            ),
        })
    return {
        "name": name,
        "starting_fingerprint": initial_fingerprint,
        "ending_fingerprints_equal": (
            baseline_kernel.fingerprint() == controlled_kernel.fingerprint()
        ),
        "steps": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoints", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases: list[dict] = []
    for checkpoint in args.checkpoints:
        checkpoint = checkpoint.resolve()
        if not checkpoint.is_file():
            raise FileNotFoundError(checkpoint)
        original_bytes = checkpoint.read_bytes()
        checksum = hashlib.sha256(original_bytes).hexdigest()
        labels = _known_labels(_load(checkpoint))
        for name, sequence in SEQUENCES:
            missing = sorted({
                label
                for cue, _tokens in sequence
                for label in cue
                if label not in labels
            })
            if missing:
                cases.append({
                    "name": name,
                    "checkpoint_sha256": checksum,
                    "skipped": True,
                    "missing_labels": missing,
                })
                continue
            case = _run_sequence(checkpoint, name, sequence)
            cases.append({
                "checkpoint_sha256": checksum,
                "skipped": False,
                **case,
            })
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != checksum:
            raise RuntimeError("Input checkpoint changed during the study.")
    report = {
        "schema_id": "verdant.v5x.homeostasis_lag_stress.v2",
        "method": (
            "Preselected DEVELOPMENT stress sequences derived from the "
            "one-checkpoint detector study. Previous-cycle controlled Tg "
            "must match policy source Tg; first cycle has no control. "
            "Unchanged V4 Tg, unchanged homeostasis v4 controller, "
            "no semantic truth labels, no checkpoint writes."
        ),
        "checkpoints": [
            {"path": str(path.resolve()),
             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in args.checkpoints
        ],
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, sort_keys=True, indent=2), encoding="utf-8"
    )
    print(f"[lag-stress] wrote: {args.output.resolve()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
