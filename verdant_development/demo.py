from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_development import DevelopmentalCycleConfig, VerdantDevelopmentPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, save_checkpoint


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _command(event_key: str, label: str, features: tuple[float, ...]) -> ExperienceCommand:
    return ExperienceCommand(
        event_key=event_key,
        source_ref=f"milestone12:{event_key}",
        modality="text",
        payload_sha256=_digest(f"{event_key}:{label}"),
        feature_vector=features,
        concept_labels=(label,),
        confidence=1.0,
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"milestone": 12, "controlled_demo": True},
    )


def run_demo(output_dir: str | Path = "artifacts") -> dict[str, object]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    kernel = VerdantKernel(seed=1212, state_dim=64, run_label="milestone-12-development")
    pipeline = VerdantDevelopmentPipeline(
        config=DevelopmentalCycleConfig(
            resonance_top_k=3,
            resonance_commit_limit=3,
            current_evidence_resource=0.30,
            resonance_resource=0.10,
        )
    )

    kren = (1.0, 0.0, 0.0, 0.0)
    tar = (0.0, 1.0, 0.0, 0.0)
    vel = (0.0, 0.0, 1.0, 0.0)

    cycle_results = []
    for event_key, label, features in (
        ("kren-1", "kren", kren),
        ("tar-1", "tar", tar),
        ("vel-1", "vel", vel),
    ):
        cycle_results.append(pipeline.advance(kernel, _command(event_key, label, features)))

    kren_id = next(
        concept_id
        for concept_id, concept in kernel.state.concepts.items()
        if concept.normalized_label == "kren"
    )
    before_report = kernel.inspect_resonance(kren, "text", top_k=3)
    before_score = next(item.score for item in before_report.candidates if item.concept_id == kren_id)

    for index in range(2, 6):
        cycle_results.append(
            pipeline.advance(kernel, _command(f"kren-{index}", "kren", kren))
        )

    after_report = kernel.inspect_resonance(kren, "text", top_k=3)
    after_score = next(item.score for item in after_report.candidates if item.concept_id == kren_id)

    checkpoint = output / "milestone_12_development_demo.vdk"
    save_checkpoint(checkpoint, kernel.snapshot())

    last = cycle_results[-1]
    assert last.workspace is not None
    summary = {
        "milestone": 12,
        "name": "Unified Developmental Heartbeat",
        "sequence": [result.experience.event_key for result in cycle_results],
        "cycles_committed": len(cycle_results),
        "kernel_cycle": kernel.state.cycle,
        "concept_count": len(kernel.state.concepts),
        "relation_count": len(kernel.state.relations),
        "claim_count": len(kernel.state.claims),
        "field_history_count": len(kernel.state.field.history),
        "resonance_event_count": len(kernel.state.resonance_events),
        "workspace_cycle_count": len(kernel.state.workspace_cycle_events),
        "active_workspace_items": len(kernel.state.workspace_items),
        "kren_resonance_before_repetition": before_score,
        "kren_resonance_after_repetition": after_score,
        "kren_resonance_gain": after_score - before_score,
        "semantic_firewall_held_every_cycle": all(
            result.semantic_firewall_held for result in cycle_results
        ),
        "latest_candidate_scope_count": len(last.candidate_scope_ids),
        "latest_workspace_sources": sorted(
            item.source_kind.value for item in kernel.state.workspace_items.values()
        ),
        "checkpoint": str(checkpoint),
        "kernel_fingerprint": kernel.fingerprint(),
    }
    summary_path = output / "milestone_12_development_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
