from __future__ import annotations

import hashlib
import json
from pathlib import Path

from verdant_kernel import (
    ConceptProposal,
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_shards import VerdantShardPipeline


ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
CHECKPOINT_PATH = ARTIFACT_DIR / "milestone_6_shards_demo.vdk"
SUMMARY_PATH = ARTIFACT_DIR / "milestone_6_shards_summary.json"
REPORTS_PATH = ARTIFACT_DIR / "milestone_6_routing_reports.json"

DOMAINS = {
    "physics": {
        "concepts": ("gravity", "mass", "acceleration", "force"),
        "relations": (
            ("gravity", "mass", "acts_on"),
            ("force", "acceleration", "causes"),
            ("mass", "acceleration", "modulates"),
        ),
        "features": (1.0, 0.0, 0.0, 0.0),
    },
    "ecology": {
        "concepts": ("watershed", "rainfall", "wildfire", "habitat"),
        "relations": (
            ("watershed", "rainfall", "channels"),
            ("rainfall", "wildfire", "influences"),
            ("wildfire", "habitat", "changes"),
        ),
        "features": (0.0, 1.0, 0.0, 0.0),
    },
    "interaction": {
        "concepts": ("care", "trust", "repair", "boundary"),
        "relations": (
            ("care", "trust", "supports"),
            ("trust", "repair", "enables"),
            ("boundary", "care", "constrains"),
        ),
        "features": (0.0, 0.0, 1.0, 0.0),
    },
}


def _experience(
    kernel: VerdantKernel,
    *,
    key: str,
    text: str,
    concepts: tuple[str, ...],
    relations: tuple[tuple[str, str, str], ...] = (),
    features: tuple[float, ...],
):
    return kernel.apply_experience(
        ExperienceCommand(
            event_key=key,
            source_ref=f"handwritten-curriculum:{key}",
            modality="text",
            payload_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            feature_vector=features,
            concept_proposals=tuple(
                ConceptProposal(label=label) for label in concepts
            ),
            relation_proposals=tuple(
                RelationProposal(
                    source_label=source,
                    target_label=target,
                    relation_type=relation_type,
                    weight=0.80,
                    confidence=0.90,
                )
                for source, target, relation_type in relations
            ),
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "handwritten_curriculum": True,
                "milestone": 6,
            },
        )
    )


def _concept_ids(kernel: VerdantKernel, labels: tuple[str, ...]) -> tuple[str, ...]:
    by_label = {item.label: item.concept_id for item in kernel.state.concepts.values()}
    return tuple(sorted(by_label[label] for label in labels))


def _cue(kernel: VerdantKernel, domain: str, key: str):
    specification = DOMAINS[domain]
    labels = specification["concepts"][:3]
    result = _experience(
        kernel,
        key=key,
        text=f"Controlled {domain} cue: {', '.join(labels)}.",
        concepts=labels,
        features=specification["features"],
    )
    evidence = tuple(
        sorted(
            (
                result.observation_evidence_id,
                result.translation_evidence_id,
                *result.additional_evidence_ids,
            )
        )
    )
    return _concept_ids(kernel, labels), evidence


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    kernel = VerdantKernel(seed=606, state_dim=64, run_label="milestone-6-demo")
    shards = VerdantShardPipeline()

    for index, (domain, specification) in enumerate(DOMAINS.items()):
        _experience(
            kernel,
            key=f"domain-{index}-{domain}",
            text=f"Controlled handwritten lesson for {domain}.",
            concepts=specification["concepts"],
            relations=specification["relations"],
            features=specification["features"],
        )

    formed: dict[str, str] = {}
    for domain, specification in DOMAINS.items():
        result = shards.form_shard(
            kernel,
            label=domain,
            concept_ids=_concept_ids(kernel, specification["concepts"]),
        )
        formed[domain] = result.formation_event.report.proposed_shard_id

    # Deliberately surface physics resonance while the direct presented cue is ecology.
    ecology_cues, ecology_evidence = _cue(kernel, "ecology", "route-ecology-1")
    physics_resonance_report = kernel.inspect_resonance(
        DOMAINS["physics"]["features"],
        "text",
        top_k=8,
    )
    physics_resonance = kernel.commit_resonance(
        physics_resonance_report,
        evidence_refs=ecology_evidence,
        max_candidates=8,
    )
    semantic_before_first_route = {
        "evidence": len(kernel.state.evidence),
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }
    ecology_route = shards.route(
        kernel,
        cue_concept_ids=ecology_cues,
        evidence_refs=ecology_evidence,
        resonance_event_ids=(physics_resonance.resonance_event_id,),
    )
    semantic_after_first_route = {
        "evidence": len(kernel.state.evidence),
        "concepts": len(kernel.state.concepts),
        "relations": len(kernel.state.relations),
        "claims": len(kernel.state.claims),
    }

    physics_cues, physics_evidence = _cue(kernel, "physics", "route-physics")
    physics_route = shards.route(
        kernel,
        cue_concept_ids=physics_cues,
        evidence_refs=physics_evidence,
    )

    ecology_cues_2, ecology_evidence_2 = _cue(kernel, "ecology", "route-ecology-2")
    ecology_return = shards.route(
        kernel,
        cue_concept_ids=ecology_cues_2,
        evidence_refs=ecology_evidence_2,
    )

    save_checkpoint(CHECKPOINT_PATH, kernel.snapshot())
    restored = VerdantKernel.from_state(load_checkpoint(CHECKPOINT_PATH))
    exact_reload = restored.snapshot() == kernel.snapshot()

    def route_payload(result):
        selected = next(
            item
            for item in result.report.candidates
            if item.shard_id == result.report.selected_shard_id
        )
        return {
            "from_shard": result.routing_event.from_shard_id,
            "to_shard": result.routing_event.to_shard_id,
            "to_label": kernel.state.shards[result.routing_event.to_shard_id].label,
            "route_score": selected.score,
            "direct_grounding": selected.components.direct_grounding,
            "relation_support": selected.components.relation_support,
            "resonance_support": selected.components.resonance_support,
            "contamination": selected.components.contamination,
            "thaw_cost": selected.components.thaw_cost,
            "direct_cue_concept_ids": list(
                result.routing_event.direct_cue_concept_ids
            ),
            "evidence_refs": list(result.routing_event.evidence_refs),
            "bridge_id": result.routing_event.bridge_id,
        }

    routes = [
        route_payload(ecology_route),
        route_payload(physics_route),
        route_payload(ecology_return),
    ]
    bridge_summary = {
        bridge_id: {
            "source_label": kernel.state.shards[bridge.source_shard_id].label,
            "target_label": kernel.state.shards[bridge.target_shard_id].label,
            "traversal_count": bridge.traversal_count,
            "portal_count": len(bridge.portal_concept_ids),
            "evidence_count": len(bridge.evidence_refs),
        }
        for bridge_id, bridge in sorted(kernel.state.shard_bridges.items())
    }
    specialized = {
        shard.label: {
            "shard_id": shard.shard_id,
            "status": shard.status.value,
            "concept_count": len(shard.concept_ids),
            "relation_count": len(shard.relation_ids),
            "signature_labels": [
                kernel.state.concepts[item].label
                for item in shard.specialization_signature
            ],
        }
        for shard in kernel.state.shards.values()
        if shard.shard_id != "root"
    }
    summary = {
        "milestone": 6,
        "title": "Bounded Specialization and Evidence-Grounded Routing",
        "llm_in_loop": False,
        "curriculum": "handwritten controlled lessons",
        "metrics": kernel.metrics(),
        "root_catalog": {
            "concept_count": len(kernel.state.shards["root"].concept_ids),
            "relation_count": len(kernel.state.shards["root"].relation_ids),
        },
        "specialized_shards": specialized,
        "routes": routes,
        "bridges": bridge_summary,
        "ghost_bridge_count": sum(
            1
            for bridge in kernel.state.shard_bridges.values()
            if bridge.traversal_count < 1
        ),
        "first_route_selected_ecology_despite_physics_resonance": (
            ecology_route.routing_event.to_shard_id == formed["ecology"]
        ),
        "first_route_direct_cue_retained": (
            ecology_route.routing_event.direct_cue_concept_ids == ecology_cues
        ),
        "routing_created_semantic_truth": (
            semantic_before_first_route != semantic_after_first_route
        ),
        "semantic_counts_before_first_route": semantic_before_first_route,
        "semantic_counts_after_first_route": semantic_after_first_route,
        "exact_checkpoint_reload": exact_reload,
        "active_shard_label": kernel.state.shards[kernel.state.active_shard_id].label,
        "policy": kernel.state.shard_policy.model_dump(mode="json"),
    }
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    REPORTS_PATH.write_text(
        json.dumps(
            [
                ecology_route.report.model_dump(mode="json"),
                physics_route.report.model_dump(mode="json"),
                ecology_return.report.model_dump(mode="json"),
            ],
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
