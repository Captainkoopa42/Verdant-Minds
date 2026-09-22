from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from verdant_development.pipeline import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_development.v5x import V5XDevelopmentPipeline, controlled_development_config
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, load_checkpoint
from verdant_thermodynamics import (
    PhasePolicyController,
    ThermodynamicPhase,
    VerdantThermodynamicObserver,
)


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
        trigger_refs = candidate.metadata.get("trigger_concept_ids", ())
        if not isinstance(trigger_refs, (list, tuple)):
            trigger_refs = ()
        trigger_bindings = []
        for ref in trigger_refs:
            concept = kernel.state.concepts.get(ref)
            trigger_bindings.append(concept.label if concept is not None else ref)
        trigger_fraction = candidate.metadata.get("trigger_fraction")
        resonance_score = candidate.metadata.get("resonance_score")
        local_support_strength = candidate.metadata.get("local_support_strength")
        association_strength = candidate.metadata.get("association_strength")
        rows.append(
            {
                "rank": item.rank,
                "source_kind": candidate.source_kind.value,
                "label": candidate.label,
                "bindings": bindings,
                "trigger_bindings": trigger_bindings,
                "trigger_fraction": trigger_fraction,
                "resonance_score": resonance_score,
                "local_support_strength": local_support_strength,
                "association_strength": association_strength,
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


def _access_metrics(summary: dict[str, object]) -> dict[str, object]:
    if not summary.get("available"):
        return {
            "admitted_structure_count": 0,
            "low_context_structure_count": 0,
            "admitted_local_count": 0,
            "admitted_resonance_count": 0,
            "admitted_historical_resource": 0.0,
        }

    structures = summary["admitted_earned_structures"]
    local = summary["admitted_local_associations"]
    resonance = summary["admitted_resonance"]
    low_context = [
        row
        for row in structures
        if row.get("trigger_fraction") is not None
        and float(row["trigger_fraction"]) < 0.50
    ]
    historical = [*structures, *local, *resonance]
    return {
        "admitted_structure_count": len(structures),
        "low_context_structure_count": len(low_context),
        "admitted_local_count": len(local),
        "admitted_resonance_count": len(resonance),
        "admitted_historical_resource": sum(
            float(row["allocated_resource"]) for row in historical
        ),
    }


def _thermodynamic_summary(state) -> dict[str, object] | None:
    if state is None:
        return None
    return {
        "cycle": state.cycle,
        "t_g": state.t_g,
        "phase": state.phase.value,
        "h_sys": state.h_sys,
        "c_input": state.c_input,
        "c_memory": state.c_memory,
        "h_env": state.h_env,
        "computational_complexity": state.computational_complexity,
        "base_term": state.base_term,
        "entropy_feedback": state.entropy_feedback,
        "t_cog": state.t_cog,
        "previous_phase": (
            state.previous_phase.value if state.previous_phase is not None else None
        ),
        "phase_transition": state.phase_transition,
        "environment": state.environment.model_dump(mode="json"),
        "memory": state.memory.model_dump(mode="json"),
        "input": state.input.model_dump(mode="json"),
        "field": state.field.model_dump(mode="json"),
    }


def _control_summary(result) -> dict[str, object] | None:
    control = result.thermodynamic_control
    if control is None:
        return None
    return {
        "source_cycle": control.source_cycle,
        "source_t_g": control.source_t_g,
        "source_phase": control.source_phase.value,
        "control_phase": control.control_phase.value,
        "controller_revision": control.policy.controller_revision,
        "effective_config": control.effective_config,
    }


def _report_digest(report) -> str:
    payload = json.dumps(
        report.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_deltas(kernel: VerdantKernel, first, second) -> list[dict[str, object]]:
    rows = []
    for left, right in zip(first.candidates, second.candidates):
        concept = kernel.state.concepts.get(left.concept_id)
        rows.append(
            {
                "concept": concept.label if concept is not None else left.concept_id,
                "same_concept": left.concept_id == right.concept_id,
                "score_1": left.score,
                "score_2": right.score,
                "score_delta": right.score - left.score,
                "profile_delta": (
                    right.contribution.profile_alignment
                    - left.contribution.profile_alignment
                ),
                "current_delta": (
                    right.contribution.current_field_alignment
                    - left.contribution.current_field_alignment
                ),
                "history_delta": (
                    right.contribution.history_alignment
                    - left.contribution.history_alignment
                ),
            }
        )
    return rows


def _resonance_repro_diagnostic(
    checkpoint: Path,
    labels: tuple[str, ...],
    config: DevelopmentalCycleConfig,
    *,
    event_key: str,
) -> dict[str, object]:
    """Diagnose inspect -> validate -> re-inspect reproducibility without commit."""

    kernel = _load(checkpoint)
    command = _command(
        labels,
        state_dim=kernel.state.field.state_dim,
        event_key=event_key,
    )
    experience = kernel.apply_experience(command)
    shard = kernel.state.shards[kernel.state.active_shard_id]
    scope = tuple(sorted(shard.concept_ids))

    first = kernel.inspect_resonance(
        command.feature_vector,
        command.modality,
        top_k=config.resonance_top_k,
        candidate_concept_ids=scope,
    )
    validated = type(first).model_validate(first.model_dump(mode="json"))
    second = kernel.inspect_resonance(
        command.feature_vector,
        command.modality,
        top_k=max(1, len(first.candidates)),
        candidate_concept_ids=first.candidate_scope_ids,
    )
    evidence_refs = tuple(
        sorted(
            {
                experience.observation_evidence_id,
                experience.translation_evidence_id,
                *experience.additional_evidence_ids,
            }
        )
    )

    return {
        "cycle_after_experience": kernel.state.cycle,
        "candidate_count": len(first.candidates),
        "first_equals_second": first == second,
        "validated_equals_second": validated == second,
        "first_digest": _report_digest(first),
        "validated_digest": _report_digest(validated),
        "second_digest": _report_digest(second),
        "query_id_first": first.query_id,
        "query_id_second": second.query_id,
        "state_fingerprint_first": first.state_fingerprint,
        "state_fingerprint_second": second.state_fingerprint,
        "field_fingerprint_first": first.field_fingerprint,
        "field_fingerprint_second": second.field_fingerprint,
        "evidence_refs": list(evidence_refs),
        "candidate_deltas": _candidate_deltas(kernel, first, second),
    }


def forced_rigid_pairs(checkpoint: Path) -> dict[str, object]:
    base_config = DevelopmentalCycleConfig()
    rigid = PhasePolicyController(
        experimental_control_enabled=True
    ).propose_for_phase(ThermodynamicPhase.RIGID)
    controlled_config = controlled_development_config(base_config, rigid)

    results = []
    for index, labels in enumerate(DEFAULT_PROBES, start=1):
        print(f"[forced {index}/{len(DEFAULT_PROBES)}] {' + '.join(labels)}")
        baseline_kernel = _load(checkpoint)
        controlled_kernel = _load(checkpoint)
        known = _known_labels(baseline_kernel)
        missing = [label for label in labels if label not in known]
        if missing:
            print(f"  skipped; missing labels: {missing}")
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

        event_key = f"forced-rigid-{index:02d}"
        command = _command(
            labels,
            state_dim=baseline_kernel.state.field.state_dim,
            event_key=event_key,
        )
        try:
            baseline = VerdantDevelopmentPipeline(config=base_config).advance(
                baseline_kernel, command
            )
        except Exception as exc:
            print(f"  baseline FAILED: {type(exc).__name__}: {exc}")
            results.append(
                {
                    "labels": list(labels),
                    "skipped": False,
                    "failed_stage": "baseline_advance",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "resonance_repro": _resonance_repro_diagnostic(
                        checkpoint,
                        labels,
                        base_config,
                        event_key=f"diagnose-baseline-{index:02d}",
                    ),
                }
            )
            continue

        try:
            controlled = VerdantDevelopmentPipeline(
                config=controlled_config
            ).advance(controlled_kernel, command)
        except Exception as exc:
            print(f"  forced-Rigid FAILED: {type(exc).__name__}: {exc}")
            results.append(
                {
                    "labels": list(labels),
                    "skipped": False,
                    "failed_stage": "forced_rigid_advance",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "baseline": _workspace_summary(baseline_kernel, baseline),
                    "resonance_repro": _resonance_repro_diagnostic(
                        checkpoint,
                        labels,
                        controlled_config,
                        event_key=f"diagnose-controlled-{index:02d}",
                    ),
                }
            )
            continue

        print("  paired advance succeeded")
        baseline_summary = _workspace_summary(baseline_kernel, baseline)
        controlled_summary = _workspace_summary(controlled_kernel, controlled)
        observer = VerdantThermodynamicObserver()
        baseline_thermodynamics = observer.inspect(
            baseline_kernel,
            command,
            candidate_scope_count=len(baseline.candidate_scope_ids),
            workspace_report=(
                baseline.workspace.report if baseline.workspace is not None else None
            ),
        )
        controlled_thermodynamics = observer.inspect(
            controlled_kernel,
            command,
            candidate_scope_count=len(controlled.candidate_scope_ids),
            workspace_report=(
                controlled.workspace.report if controlled.workspace is not None else None
            ),
        )
        results.append(
            {
                "labels": list(labels),
                "skipped": False,
                "starting_fingerprint": baseline_start,
                "baseline": baseline_summary,
                "forced_rigid": controlled_summary,
                "baseline_access_metrics": _access_metrics(baseline_summary),
                "forced_rigid_access_metrics": _access_metrics(controlled_summary),
                "baseline_thermodynamics": _thermodynamic_summary(
                    baseline_thermodynamics
                ),
                "forced_rigid_thermodynamics": _thermodynamic_summary(
                    controlled_thermodynamics
                ),
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
        print(f"[auto {index}/{len(DEFAULT_PROBES)}] {' + '.join(labels)}")
        missing = [label for label in labels if label not in known]
        if missing:
            print(f"  skipped; missing labels: {missing}")
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
        try:
            baseline = baseline_pipeline.advance(baseline_kernel, command)
            controlled = controlled_pipeline.advance(controlled_kernel, command)
        except Exception as exc:
            print(f"  automatic sequence FAILED: {type(exc).__name__}: {exc}")
            rows.append(
                {
                    "labels": list(labels),
                    "skipped": False,
                    "failed_stage": "automatic_advance",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )
            break
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
                "baseline_thermodynamics": _thermodynamic_summary(
                    baseline.thermodynamics
                ),
                "controlled_thermodynamics": _thermodynamic_summary(
                    controlled.thermodynamics
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
        "schema_id": "verdant.v5x.thermodynamic_homeostasis_probe.v2",
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
