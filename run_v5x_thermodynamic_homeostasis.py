from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_development.pipeline import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_development.v5x import V5XDevelopmentPipeline, controlled_development_config
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, load_checkpoint
from verdant_thermodynamics import PhasePolicyController, ThermodynamicPhase


DEFAULT_PROBES = (
    ("load",),
    ("switch", "load"),
    ("controller",),
    ("pressure_sensor", "controller"),
    ("actuator",),
    ("actuator", "sensor"),
    ("foundation", "frame"),
)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _features(labels: tuple[str, ...], state_dim: int) -> tuple[float, ...]:
    vector = [0.0] * state_dim
    for index, label in enumerate(labels, start=1):
        position = int(_digest(label)[:16], 16) % state_dim
        vector[position] += 1.0 / index
    return tuple(vector)


def _command(
    labels: tuple[str, ...],
    *,
    state_dim: int,
    event_key: str,
) -> ExperienceCommand:
    sentence = " ".join(labels)
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"thermodynamic-homeostasis:{event_key}",
        modality="text",
        payload_sha256=_digest(event_key + "|" + sentence),
        feature_vector=_features(labels, state_dim),
        concept_labels=labels,
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={
            "experimental_probe": True,
            "purpose": "thermodynamic_homeostasis",
        },
        metadata={
            "sentence": sentence,
            "experimental_probe": True,
            "does_not_claim_external_observation": True,
        },
    )


def _load(path: Path) -> VerdantKernel:
    return VerdantKernel.from_state(load_checkpoint(path))


def _known_labels(kernel: VerdantKernel) -> set[str]:
    return {concept.label for concept in kernel.state.concepts.values()}


def _workspace_summary(kernel: VerdantKernel, result) -> dict[str, object]:
    if result.workspace is None:
        return {"available": False, "assessments": []}
    rows = []
    for item in result.workspace.report.assessments:
        candidate = item.candidate
        bindings = []
        for ref in candidate.binding_refs:
            concept = kernel.state.concepts.get(ref)
            bindings.append(concept.label if concept is not None else ref)
        rows.append(
            {
                "rank": item.rank,
                "source_kind": candidate.source_kind.value,
                "label": candidate.label,
                "bindings": bindings,
                "disposition": item.disposition.value,
                "raw_score": item.raw_score,
                "effective_score": item.effective_score,
                "allocated_resource": item.allocated_resource,
                "rejection_codes": list(item.rejection_codes),
            }
        )
    return {
        "available": True,
        "assessments": rows,
        "admitted_earned_structures": [
            row
            for row in rows
            if row["source_kind"] == "earned_structure"
            and row["disposition"] == "admit"
        ],
        "admitted_local_associations": [
            row
            for row in rows
            if row["source_kind"] == "local_association"
            and row["disposition"] == "admit"
        ],
        "admitted_resonance": [
            row
            for row in rows
            if row["source_kind"] == "resonance"
            and row["disposition"] == "admit"
        ],
    }


def _control_summary(result) -> dict[str, object] | None:
    control = result.thermodynamic_control
    if control is None:
        return None
    return {
        "source_cycle": control.source_cycle,
        "source_t_g": control.source_t_g,
        "source_phase": control.source_phase.value,
        "controller_revision": control.policy.controller_revision,
        "effective_config": control.effective_config,
    }


def forced_rigid_pairs(checkpoint: Path) -> dict[str, object]:
    base_config = DevelopmentalCycleConfig()
    rigid = PhasePolicyController(
        experimental_control_enabled=True
    ).propose_for_phase(ThermodynamicPhase.RIGID)
    controlled_config = controlled_development_config(base_config, rigid)

    results = []
    for index, labels in enumerate(DEFAULT_PROBES, start=1):
        baseline_kernel = _load(checkpoint)
        controlled_kernel = _load(checkpoint)
        known = _known_labels(baseline_kernel)
        missing = [label for label in labels if label not in known]
        if missing:
            results.append(
                {
                    "labels": list(labels),
                    "skipped": True,
                    "missing_labels": missing,
                }
            )
            continue

        baseline_start = baseline_kernel.fingerprint()
        controlled_start = controlled_kernel.fingerprint()
        if baseline_start != controlled_start:
            raise RuntimeError("Paired kernels did not start from the same fingerprint.")

        command = _command(
            labels,
            state_dim=baseline_kernel.state.field.state_dim,
            event_key=f"forced-rigid-{index:02d}",
        )
        baseline = VerdantDevelopmentPipeline(config=base_config).advance(
            baseline_kernel, command
        )
        controlled = VerdantDevelopmentPipeline(config=controlled_config).advance(
            controlled_kernel, command
        )
        results.append(
            {
                "labels": list(labels),
                "skipped": False,
                "starting_fingerprint": baseline_start,
                "baseline": _workspace_summary(baseline_kernel, baseline),
                "forced_rigid": _workspace_summary(controlled_kernel, controlled),
                "baseline_ending_fingerprint": baseline_kernel.fingerprint(),
                "forced_rigid_ending_fingerprint": controlled_kernel.fingerprint(),
            }
        )

    return {
        "purpose": (
            "Mechanistic A/B test. The Rigid policy is forced so this section tests "
            "the controller action independently of whether Tg is a useful detector."
        ),
        "base_config": base_config.__dict__,
        "rigid_policy": rigid.model_dump(mode="json"),
        "controlled_config": controlled_config.__dict__,
        "probes": results,
    }


def automatic_sequence(checkpoint: Path) -> dict[str, object]:
    baseline_kernel = _load(checkpoint)
    controlled_kernel = _load(checkpoint)
    if baseline_kernel.fingerprint() != controlled_kernel.fingerprint():
        raise RuntimeError("Automatic paired kernels did not start identically.")

    baseline_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=False,
    )
    controlled_pipeline = V5XDevelopmentPipeline(
        enable_thermodynamic_observation=True,
        enable_thermodynamic_control=True,
    )

    known = _known_labels(baseline_kernel)
    rows = []
    for index, labels in enumerate(DEFAULT_PROBES, start=1):
        missing = [label for label in labels if label not in known]
        if missing:
            rows.append(
                {
                    "labels": list(labels),
                    "skipped": True,
                    "missing_labels": missing,
                }
            )
            continue

        command = _command(
            labels,
            state_dim=baseline_kernel.state.field.state_dim,
            event_key=f"auto-homeostasis-{index:02d}",
        )
        baseline = baseline_pipeline.advance(baseline_kernel, command)
        controlled = controlled_pipeline.advance(controlled_kernel, command)
        rows.append(
            {
                "labels": list(labels),
                "skipped": False,
                "baseline_phase": (
                    baseline.thermodynamics.phase.value
                    if baseline.thermodynamics is not None
                    else None
                ),
                "baseline_t_g": (
                    baseline.thermodynamics.t_g
                    if baseline.thermodynamics is not None
                    else None
                ),
                "controlled_phase": (
                    controlled.thermodynamics.phase.value
                    if controlled.thermodynamics is not None
                    else None
                ),
                "controlled_t_g": (
                    controlled.thermodynamics.t_g
                    if controlled.thermodynamics is not None
                    else None
                ),
                "control_applied": _control_summary(controlled),
                "baseline_workspace": _workspace_summary(
                    baseline_kernel, baseline
                ),
                "controlled_workspace": _workspace_summary(
                    controlled_kernel, controlled
                ),
            }
        )

    return {
        "purpose": (
            "Detector + controller A/B test. Control begins only after the first "
            "committed cycle because the previous cycle's Tg governs the next one."
        ),
        "starting_checkpoint": str(checkpoint),
        "steps": rows,
        "baseline_final_fingerprint": baseline_kernel.fingerprint(),
        "controlled_final_fingerprint": controlled_kernel.fingerprint(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("thermodynamic_homeostasis_report.json"),
    )
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)

    report = {
        "schema_id": "verdant.v5x.thermodynamic_homeostasis_probe.v1",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "forced_rigid": forced_rigid_pairs(checkpoint),
        "automatic": automatic_sequence(checkpoint),
    }
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    print()
    print(f"Wrote: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
