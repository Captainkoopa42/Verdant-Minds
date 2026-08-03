from __future__ import annotations

import argparse
import hashlib
import json
import shlex
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from verdant_development import VerdantDevelopmentPipeline
from verdant_compilation import VerdantCompilationPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_refolding import VerdantRefoldingPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    VerdantKernel,
    load_checkpoint,
    save_checkpoint,
)
from verdant_structures import VerdantStructurePipeline


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _feature_for(labels: Iterable[str], width: int = 8) -> tuple[float, ...]:
    """Deterministic exact one-hot cue so resonance replay is bit-stable."""
    text = "|".join(sorted(item.strip().lower() for item in labels if item.strip()))
    slot = int(_digest(text)[:8], 16) % width
    return tuple(1.0 if index == slot else 0.0 for index in range(width))


def _quality_dict(candidate) -> dict[str, float]:
    return {
        key: round(float(getattr(candidate.quality, key)), 4)
        for key in (
            "recurrence",
            "reconstructability",
            "boundary_selectivity",
            "internal_cohesion",
            "evidence_diversity",
            "cross_context_stability",
            "perturbation_survival",
            "compression_gain",
            "contradiction_tolerance",
        )
    }


class CultivationSession:
    def __init__(self, kernel: VerdantKernel, checkpoint_path: Path) -> None:
        self.kernel = kernel
        self.checkpoint_path = checkpoint_path
        self.development = VerdantDevelopmentPipeline()
        self.structures = VerdantStructurePipeline()
        self.compilation = VerdantCompilationPipeline()
        self.interaction = VerdantStructureInteractionPipeline()
        self.hierarchy = VerdantHierarchyPipeline()
        self.refolding = VerdantRefoldingPipeline()
        self.manual_sequence = len(
            [key for key in kernel.state.processed_event_keys if key.startswith("manual-")]
        )

    def _next_event_key(self) -> str:
        self.manual_sequence += 1
        return f"manual-{self.manual_sequence:06d}"

    def teach(
        self,
        labels: tuple[str, ...],
        *,
        context_id: str,
        feature_vector: tuple[float, ...] | None = None,
        event_key: str | None = None,
    ):
        labels = tuple(item.strip() for item in labels if item.strip())
        if not labels:
            raise ValueError("Teach requires at least one symbol/label.")
        event_key = event_key or self._next_event_key()
        feature_vector = feature_vector or _feature_for(labels)
        command = ExperienceCommand(
            event_key=event_key,
            source_ref=f"cultivation:{context_id}",
            modality="text",
            payload_sha256=_digest(
                json.dumps(
                    {
                        "event_key": event_key,
                        "context_id": context_id,
                        "labels": labels,
                        "feature_vector": feature_vector,
                    },
                    sort_keys=True,
                )
            ),
            feature_vector=feature_vector,
            concept_labels=labels,
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "cultivation_runner": True,
                "taught_content": "primitive_symbol_presence_only",
            },
            metadata={"context_id": context_id, "runner_event": True},
        )
        result = self.development.advance(self.kernel, command)
        self._print_cycle(result)
        return result

    def _print_cycle(self, result) -> None:
        print(f"\n=== DEVELOPMENT CYCLE: {result.experience.event_key} ===")
        print("TAUGHT symbols:", ", ".join(result.experience.concept_ids) or "(none)")
        if result.plasticity is not None:
            report = result.plasticity.report
            print(
                "ASSOCIATED:",
                f"+{len(report.created_association_ids)} created,",
                f"{len(report.reinforced_association_ids)} reinforced,",
                f"{len(report.pruned_association_ids)} pruned",
            )
        if result.structures is None:
            print("MANUFACTURED candidates: none this cycle")
        else:
            print("MANUFACTURED candidates:")
            for candidate_id in result.structures.report.observed_candidate_ids:
                candidate = self.kernel.state.structure_candidates[candidate_id]
                labels = [
                    self.kernel.state.concepts[item].label
                    for item in candidate.member_concept_ids
                ]
                print(
                    f"  {candidate.candidate_id}  status={candidate.status.value} "
                    f"occurrences={candidate.occurrence_count} members={labels}"
                )
                print("    gates:", json.dumps(_quality_dict(candidate), sort_keys=True))

    def status(self) -> None:
        metrics = self.kernel.metrics()
        print("\n=== VERDANT STATUS ===")
        keys = (
            "cycle",
            "concept_count",
            "relation_count",
            "plasticity_association_count",
            "structure_candidate_count",
            "eligible_structure_candidate_count",
            "promoted_structure_count",
            "ablated_structure_count",
            "compilation_probe_event_count",
            "structure_interaction_event_count",
            "hierarchy_candidate_count",
            "eligible_hierarchy_candidate_count",
            "layered_structure_count",
            "layered_probe_event_count",
            "structural_challenge_count",
            "structure_refold_event_count",
            "refolded_structure_count",
            "workspace_active_item_count",
            "field_history_count",
        )
        for key in keys:
            print(f"{key:36s} {metrics[key]}")

    def list_candidates(self) -> None:
        print("\n=== STRUCTURE CANDIDATES ===")
        if not self.kernel.state.structure_candidates:
            print("(none)")
            return
        for index, candidate in enumerate(
            sorted(self.kernel.state.structure_candidates.values(), key=lambda item: item.candidate_id),
            start=1,
        ):
            labels = [
                self.kernel.state.concepts[item].label
                for item in candidate.member_concept_ids
            ]
            promotion = self.structures.inspect_promotion(self.kernel, candidate.candidate_id)
            print(
                f"[{index}] {candidate.candidate_id}  {candidate.status.value} "
                f"members={labels} occurrences={candidate.occurrence_count}"
            )
            print("    quality:", json.dumps(_quality_dict(candidate), sort_keys=True))
            print(
                "    promotion:",
                promotion.disposition.value,
                ", ".join(promotion.rejection_codes) or "all gates passed",
            )

    def list_structures(self) -> None:
        print("\n=== PROMOTED EARNED STRUCTURES ===")
        if not self.kernel.state.structures:
            print("(none)")
            return
        for structure in sorted(
            self.kernel.state.structures.values(), key=lambda item: item.structure_id
        ):
            labels = [
                self.kernel.state.concepts[item].label
                for item in structure.member_concept_ids
            ]
            availability = (
                "AVAILABLE"
                if self.kernel.structure_is_available(structure.structure_id)
                else "ABLATED"
            )
            print(
                f"{structure.opaque_name}  id={structure.structure_id} "
                f"members={labels}  {availability}"
            )
            print(
                "    provenance: MANUFACTURED+PROMOTED; semantic label preinstalled =",
                structure.semantic_label_preinstalled,
            )

    def promote(self, selector: str) -> None:
        candidates = sorted(
            self.kernel.state.structure_candidates.values(), key=lambda item: item.candidate_id
        )
        candidate_id = selector
        if selector.isdigit():
            index = int(selector) - 1
            if index < 0 or index >= len(candidates):
                raise ValueError("Candidate index is out of range.")
            candidate_id = candidates[index].candidate_id
        result = self.structures.promote(self.kernel, candidate_id)
        structure = self.kernel.state.structures[result.event.structure_id]
        print(
            f"PROMOTED {candidate_id} -> {structure.opaque_name} "
            f"({structure.structure_id})"
        )
        print("Semantic concepts/relations/claims were not added by this promotion.")

    def _resolve_structure(self, selector: str) -> str:
        structures = sorted(
            self.kernel.state.structures.values(), key=lambda item: item.structure_id
        )
        if selector.isdigit():
            index = int(selector) - 1
            if index < 0 or index >= len(structures):
                raise ValueError("Structure index is out of range.")
            return structures[index].structure_id
        for structure in structures:
            if selector in {structure.structure_id, structure.opaque_name}:
                return structure.structure_id
        raise ValueError("No promoted structure matches that selector.")

    def _resolve_concept(self, label: str) -> str:
        normalized = label.strip().lower()
        for concept_id, concept in self.kernel.state.concepts.items():
            if concept.normalized_label == normalized or concept_id == label:
                return concept_id
        raise ValueError(f"Unknown concept/symbol: {label}")

    @staticmethod
    def _print_compilation_report(report) -> None:
        print("\n=== COGNITIVE COMPILATION PROBE ===")
        print("disposition:", report.disposition.value)
        print("structure:", report.structure_id or "(low-level fallback)")
        print("reconstructed concepts:", len(report.reconstructed_concept_ids))
        print(
            "compiled cost:",
            f"concepts={report.cost.concepts_inspected}",
            f"associations={report.cost.associations_traversed}",
            f"structures={report.cost.structure_operands_used}",
            f"workspace≈{report.cost.estimated_workspace_resource:.3f}",
        )
        print(
            "low-level baseline:",
            f"concepts={report.baseline_cost.concepts_inspected}",
            f"associations={report.baseline_cost.associations_traversed}",
            f"workspace≈{report.baseline_cost.estimated_workspace_resource:.3f}",
        )
        print(f"compression gain: {report.compression_gain:.4f}")

    def compile_probe(self, label: str):
        cue = self._resolve_concept(label)
        result = self.compilation.probe(self.kernel, (cue,))
        self._print_compilation_report(result.report)
        return result

    def ablate(self, selector: str) -> None:
        structure_id = self._resolve_structure(selector)
        event = self.compilation.ablate(
            self.kernel, structure_id, "manual cultivation-runner ablation"
        )
        print(f"ABLATED {structure_id}  event={event.event_id}")

    def restore(self, selector: str) -> None:
        structure_id = self._resolve_structure(selector)
        event = self.compilation.restore(
            self.kernel, structure_id, "manual cultivation-runner restoration"
        )
        print(f"RESTORED {structure_id}  event={event.event_id}")

    def compare(self, label: str) -> None:
        cue = self._resolve_concept(label)
        enabled = self.compilation.probe(self.kernel, (cue,)).report
        if enabled.structure_id is None:
            self._print_compilation_report(enabled)
            print("No available earned structure was selected; causal comparison cannot run.")
            return
        structure_id = enabled.structure_id
        self.compilation.ablate(
            self.kernel, structure_id, "runner compare controlled ablation"
        )
        ablated = self.compilation.probe(self.kernel, (cue,)).report
        self.compilation.restore(
            self.kernel, structure_id, "runner compare controlled restoration"
        )
        restored = self.compilation.probe(self.kernel, (cue,)).report
        print("\n=== ABLATION / RESTORATION COMPARISON ===")
        for name, report in (
            ("WITH P", enabled),
            ("ABLATE P", ablated),
            ("RESTORE P", restored),
        ):
            print(
                f"{name:10s} disposition={report.disposition.value:18s} "
                f"low_level_work={report.cost.low_level_work:3d} "
                f"gain={report.compression_gain:.4f} "
                f"reconstructed={len(report.reconstructed_concept_ids)}"
            )

    def interact(self, selector: str) -> None:
        structure_id = self._resolve_structure(selector)
        result = self.interaction.interact(self.kernel, structure_id)
        report = result.report
        source = self.kernel.state.structures[structure_id]
        print("\n=== CROSS-SYMBOLIC STRUCTURE INTERACTION ===")
        print(f"source: {source.opaque_name} ({structure_id})")
        if not report.candidates:
            print("no other available structures")
            return
        for item in report.candidates:
            target = self.kernel.state.structures[item.target_structure_id]
            print(
                f"{item.field_rank:2d}. {target.opaque_name} "
                f"field={item.field_similarity:.4f} "
                f"symbolic={item.symbolic_similarity:.4f} "
                f"{item.disposition.value}"
            )
            if item.member_mapping:
                mapped = [
                    (
                        self.kernel.state.concepts[a].label,
                        self.kernel.state.concepts[b].label,
                    )
                    for a, b in item.member_mapping
                ]
                print("    role mapping:", mapped)
        print("best verified target:", report.best_target_structure_id or "(none)")
        self.observe_hierarchy()

    def observe_hierarchy(self) -> None:
        result = self.hierarchy.observe(self.kernel)
        if result is None:
            print("No new higher-order candidate from the latest interaction.")
            return
        print("\n=== LAYERED STRUCTURE OBSERVATION ===")
        for candidate_id in result.report.observed_candidate_ids:
            candidate = self.kernel.state.hierarchy_candidates[candidate_id]
            names = [self.kernel.state.structures[sid].opaque_name for sid in candidate.member_structure_ids]
            print(
                f"{candidate.candidate_id} status={candidate.status.value} "
                f"members={names} interactions={len(candidate.interaction_event_ids)}"
            )
            print("    quality:", json.dumps(candidate.quality.model_dump(mode="json"), sort_keys=True))

    def list_hierarchy(self) -> None:
        print("\n=== HIGHER-ORDER CANDIDATES ===")
        if not self.kernel.state.hierarchy_candidates:
            print("(none)")
        for index, candidate in enumerate(
            sorted(self.kernel.state.hierarchy_candidates.values(), key=lambda item: item.candidate_id),
            start=1,
        ):
            names = [self.kernel.state.structures[sid].opaque_name for sid in candidate.member_structure_ids]
            promotion = self.hierarchy.inspect_promotion(self.kernel, candidate.candidate_id)
            print(
                f"[{index}] {candidate.candidate_id} {candidate.status.value} "
                f"members={names} interactions={len(candidate.interaction_event_ids)}"
            )
            print("    quality:", json.dumps(candidate.quality.model_dump(mode="json"), sort_keys=True))
            print("    promotion:", promotion.disposition.value, ", ".join(promotion.rejection_codes) or "all gates passed")
        print("\n=== PROMOTED LAYERED STRUCTURES ===")
        if not self.kernel.state.layered_structures:
            print("(none)")
        for layered in sorted(self.kernel.state.layered_structures.values(), key=lambda item: item.layered_structure_id):
            names = [self.kernel.state.structures[sid].opaque_name for sid in layered.member_structure_ids]
            availability = "AVAILABLE" if self.kernel.layered_structure_is_available(layered.layered_structure_id) else "ABLATED"
            print(
                f"{layered.opaque_name} id={layered.layered_structure_id} depth={layered.depth} "
                f"members={names} {availability}"
            )

    def _resolve_hierarchy_candidate(self, selector: str) -> str:
        candidates = sorted(self.kernel.state.hierarchy_candidates.values(), key=lambda item: item.candidate_id)
        if selector.isdigit():
            index = int(selector) - 1
            if index < 0 or index >= len(candidates):
                raise ValueError("Higher-order candidate index is out of range.")
            return candidates[index].candidate_id
        if selector in self.kernel.state.hierarchy_candidates:
            return selector
        raise ValueError("No higher-order candidate matches that selector.")

    def _resolve_layered(self, selector: str) -> str:
        layered = sorted(self.kernel.state.layered_structures.values(), key=lambda item: item.layered_structure_id)
        if selector.isdigit():
            index = int(selector) - 1
            if index < 0 or index >= len(layered):
                raise ValueError("Layered structure index is out of range.")
            return layered[index].layered_structure_id
        for item in layered:
            if selector in {item.layered_structure_id, item.opaque_name}:
                return item.layered_structure_id
        raise ValueError("No layered structure matches that selector.")

    def promote_hierarchy(self, selector: str) -> None:
        candidate_id = self._resolve_hierarchy_candidate(selector)
        result = self.hierarchy.promote(self.kernel, candidate_id)
        layered = self.kernel.state.layered_structures[result.event.layered_structure_id]
        print(f"PROMOTED HIGHER ORDER {candidate_id} -> {layered.opaque_name} ({layered.layered_structure_id})")
        print("Its primitives are earned structures; no semantic concept/claim was installed.")

    @staticmethod
    def _print_layered_probe(report) -> None:
        print("\n=== LAYERED FAMILY PROBE ===")
        print("disposition:", report.disposition.value)
        print("layered operand:", report.layered_structure_id or "(fallback member scan)")
        print("matched lower-level structures:", list(report.matched_structure_ids))
        print(
            "runtime comparisons:",
            f"Q={report.cost.layered_prototypes_compared}",
            f"P={report.cost.base_structures_compared}",
            f"symbolic={report.cost.symbolic_verifications}",
            f"work={report.cost.comparison_work}",
        )
        print(
            "audit baseline:",
            f"P={report.baseline_cost.base_structures_compared}",
            f"symbolic={report.baseline_cost.symbolic_verifications}",
            f"work={report.baseline_cost.comparison_work}",
        )
        print(f"comparison compression gain: {report.compression_gain:.4f}")

    def layered_probe(self, structure_selector: str):
        structure_id = self._resolve_structure(structure_selector)
        result = self.hierarchy.probe(self.kernel, structure_id)
        self._print_layered_probe(result.report)
        return result

    def layered_compare(self, structure_selector: str) -> None:
        structure_id = self._resolve_structure(structure_selector)
        enabled = self.hierarchy.inspect_probe(self.kernel, structure_id)
        if enabled.layered_structure_id is None:
            self._print_layered_probe(enabled)
            print("No layered structure selected; causal Q comparison cannot run.")
            return
        layered_id = enabled.layered_structure_id
        self.hierarchy.ablate(self.kernel, layered_id, "runner Q compare controlled ablation")
        ablated = self.hierarchy.inspect_probe(self.kernel, structure_id)
        self.hierarchy.restore(self.kernel, layered_id, "runner Q compare controlled restoration")
        restored = self.hierarchy.inspect_probe(self.kernel, structure_id)
        print("\n=== HIGHER-ORDER ABLATION / RESTORATION ===")
        for name, report in (("WITH Q", enabled), ("ABLATE Q", ablated), ("RESTORE Q", restored)):
            print(
                f"{name:10s} disposition={report.disposition.value:24s} "
                f"work={report.cost.comparison_work:3d} gain={report.compression_gain:.4f} "
                f"matches={len(report.matched_structure_ids)}"
            )

    def ablate_layered(self, selector: str) -> None:
        layered_id = self._resolve_layered(selector)
        event = self.hierarchy.ablate(self.kernel, layered_id, "manual layered ablation")
        print(f"ABLATED {layered_id} event={event.event_id}")

    def restore_layered(self, selector: str) -> None:
        layered_id = self._resolve_layered(selector)
        event = self.hierarchy.restore(self.kernel, layered_id, "manual layered restoration")
        print(f"RESTORED {layered_id} event={event.event_id}")

    def challenge_structure(
        self,
        selector: str,
        label_a: str,
        label_b: str,
        confidence: float = 0.80,
    ) -> None:
        structure_id = self._resolve_structure(selector)
        concept_ids = tuple(sorted((self._resolve_concept(label_a), self._resolve_concept(label_b))))
        event_key = self._next_event_key()
        command = ExperienceCommand(
            event_key=event_key,
            source_ref="cultivation:structural_challenge",
            modality="text",
            payload_sha256=_digest(
                json.dumps(
                    {
                        "event_key": event_key,
                        "structure_id": structure_id,
                        "concept_ids": concept_ids,
                        "confidence": confidence,
                    },
                    sort_keys=True,
                )
            ),
            feature_vector=_feature_for((label_a, label_b)),
            confidence=1.0,
            semantic_evidence_kind=EvidenceKind.OBSERVATION,
            semantic_evidence_details={
                "cultivation_runner": True,
                "controlled_structural_contradiction": True,
                "semantic_mutation_permitted": False,
            },
            metadata={
                "event_type": "structural_challenge",
                "target_structure_id": structure_id,
            },
        )
        experience = self.kernel.apply_experience(command)
        evidence_refs = tuple(
            sorted(
                {
                    experience.observation_evidence_id,
                    experience.translation_evidence_id,
                    *experience.additional_evidence_ids,
                }
            )
        )
        challenge = self.refolding.challenge(
            self.kernel,
            structure_id,
            concept_ids,
            evidence_refs=evidence_refs,
            confidence=confidence,
        )
        labels = tuple(self.kernel.state.concepts[item].label for item in challenge.concept_ids)
        print("\n=== STRUCTURAL CONTRADICTION ===")
        print("target:", self.kernel.state.structures[structure_id].opaque_name, structure_id)
        print("challenged edge:", labels)
        print("observations:", len(challenge.observations))
        print(f"combined confidence: {challenge.combined_confidence:.4f}")

    def refold_structure(self, selector: str) -> None:
        structure_id = self._resolve_structure(selector)
        result = self.refolding.refold(self.kernel, structure_id)
        report = result.report
        print("\n=== REFOLDING RESULT ===")
        print("parent:", self.kernel.state.structures[structure_id].opaque_name, structure_id)
        print("disposition:", report.disposition.value)
        print("mature challenges:", len(report.challenge_ids))
        print("removed frozen edges:", len(report.removed_association_ids))
        if report.rejection_codes:
            print("unresolved gates:", ", ".join(report.rejection_codes))
        if result.event.produced_structure_ids:
            print("produced:")
            for child_id in result.event.produced_structure_ids:
                child = self.kernel.state.structures[child_id]
                member_labels = [self.kernel.state.concepts[item].label for item in child.member_concept_ids]
                print(
                    f"  {child.opaque_name}  id={child.structure_id} "
                    f"revision={child.revision_index} members={member_labels}"
                )
            print("parent active:", self.kernel.structure_is_available(structure_id))
        else:
            print("no replacement structure committed; parent remains active =", self.kernel.structure_is_available(structure_id))

    def list_refolds(self) -> None:
        print("\n=== STRUCTURAL CHALLENGES / REFOLDS ===")
        if not self.kernel.state.structural_challenges and not self.kernel.state.structure_refold_events:
            print("(none)")
            return
        for challenge in sorted(self.kernel.state.structural_challenges.values(), key=lambda item: item.challenge_id):
            names = [self.kernel.state.concepts[item].label for item in challenge.concept_ids]
            print(
                f"CHALLENGE {challenge.challenge_id} parent={challenge.structure_id} "
                f"edge={names} observations={len(challenge.observations)} "
                f"confidence={challenge.combined_confidence:.4f}"
            )
        for event in self.kernel.state.structure_refold_events:
            print(
                f"REFOLD {event.event_id} parent={event.report.parent_structure_id} "
                f"disposition={event.report.disposition.value} produced={list(event.produced_structure_ids)}"
            )

    def save(self, path: Path | None = None) -> None:
        path = path or self.checkpoint_path
        save_checkpoint(path, self.kernel.snapshot())
        self.checkpoint_path = path
        print(f"Saved checkpoint: {path}")

    def export(self, path: Path) -> None:
        payload = {
            "metrics": self.kernel.metrics(),
            "plastic_associations": [
                item.model_dump(mode="json")
                for item in sorted(
                    self.kernel.state.plasticity_associations.values(),
                    key=lambda item: item.association_id,
                )
            ],
            "structure_candidates": [
                {
                    **item.model_dump(mode="json"),
                    "human_readable_member_labels": [
                        self.kernel.state.concepts[concept_id].label
                        for concept_id in item.member_concept_ids
                    ],
                }
                for item in sorted(
                    self.kernel.state.structure_candidates.values(),
                    key=lambda item: item.candidate_id,
                )
            ],
            "compilation_probe_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.compilation_probe_events
            ],
            "structure_interaction_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.structure_interaction_events
            ],
            "hierarchy_candidates": [
                item.model_dump(mode="json")
                for item in self.kernel.state.hierarchy_candidates.values()
            ],
            "layered_structures": [
                item.model_dump(mode="json")
                for item in self.kernel.state.layered_structures.values()
            ],
            "hierarchy_observation_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.hierarchy_observation_events
            ],
            "hierarchy_promotion_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.hierarchy_promotion_events
            ],
            "layered_probe_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.layered_probe_events
            ],
            "structure_availability_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.structure_availability_events
            ],
            "structural_challenges": [
                item.model_dump(mode="json")
                for item in self.kernel.state.structural_challenges.values()
            ],
            "structure_refold_events": [
                item.model_dump(mode="json")
                for item in self.kernel.state.structure_refold_events
            ],
            "structures": [
                {
                    **item.model_dump(mode="json"),
                    "human_readable_member_labels": [
                        self.kernel.state.concepts[concept_id].label
                        for concept_id in item.member_concept_ids
                    ],
                }
                for item in sorted(
                    self.kernel.state.structures.values(),
                    key=lambda item: item.structure_id,
                )
            ],
            "provenance_classes": {
                "programmed": "policies, gates, update laws",
                "taught": "input primitive labels and explicitly supplied semantic records",
                "observed": "exact evidence/events",
                "associated": "nonsemantic plastic traces",
                "manufactured": "StructureCandidate records selected from developmental history",
                "promoted": "Council-authorized opaque StructureRecord operands",
                "used": "compiled StructureRecord invocations and measured reconstruction cost",
                "ablated_restored": "controlled causal availability interventions",
                "cross_symbolic": "continuous structural retrieval followed by symbolic verification",
                "layered": "higher-order Q operands manufactured from verified interactions among earned P operands",
                "challenged": "evidence-grounded contradiction of frozen internal fold edges",
                "refolded": "lineage-preserving revisions/splits authorized after recurrent structural contradiction",
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"Exported telemetry: {path}")

    def run_jsonl(self, path: Path) -> None:
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            item = json.loads(raw)
            labels = tuple(item["labels"])
            context = str(item.get("context_id", "script"))
            feature = item.get("feature_vector")
            self.teach(
                labels,
                context_id=context,
                feature_vector=tuple(float(v) for v in feature) if feature else None,
                event_key=item.get("event_key"),
            )


def _help() -> None:
    print(
        """
Commands:
  teach <context> <label1> [label2 ...]   present primitive symbols together
  probe <context> <label>                 same path, intended as a one-symbol probe
  status                                  show bounded runtime counts
  candidates                              inspect manufactured StructureCandidates
  structures                              inspect promoted opaque structures
  promote <index-or-candidate-id>         Council-gated promotion attempt
  compile <label>                         reconstruct through P when available
  compare <label>                         WITH P -> ABLATE -> RESTORE causal probe
  interact <index-or-structure-id>         field retrieval -> symbolic role verification; observe Q
  hierarchy                               inspect higher-order candidates and promoted Q operands
  promoteq <index-or-candidate-id>        Council-gated higher-order promotion
  qprobe <index-or-structure-id>          classify a P through Q when available
  qcompare <index-or-structure-id>        WITH Q -> ABLATE -> RESTORE causal probe
  qablate <index-or-Q-id>                 disable one layered structure
  qrestore <index-or-Q-id>                restore one layered structure
  challenge <P> <labelA> <labelB> [conf] record evidence against one frozen P edge
  refold <P>                              assess/commit stable, revision, split, or unresolved response
  refolds                                 inspect contradiction/refolding lineage
  ablate <index-or-structure-id>          disable one promoted structure
  restore <index-or-structure-id>         restore one promoted structure
  save [path]                             write checkpoint
  export <path>                           write read-only telemetry JSON
  help                                    show this help
  quit                                    exit

The runner deliberately does not teach structure meanings. It only supplies the
primitive symbols you type. Association, candidate formation, gate scores, and
promotion lineage are recorded separately.
""".strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verdant Milestone 18 cultivation runner")
    parser.add_argument("--checkpoint", default="verdant_cultivation.vdk")
    parser.add_argument("--load", action="store_true", help="load --checkpoint if it exists")
    parser.add_argument("--script", type=Path, help="run JSONL cultivation events before interactive mode")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--seed", type=int, default=7741)
    parser.add_argument("--state-dim", type=int, default=128)
    args = parser.parse_args()

    checkpoint_path = Path(args.checkpoint)
    if args.load and checkpoint_path.exists():
        kernel = VerdantKernel.from_state(load_checkpoint(checkpoint_path))
        print(f"Loaded checkpoint: {checkpoint_path}")
    else:
        kernel = VerdantKernel(
            seed=args.seed,
            state_dim=args.state_dim,
            run_label="cultivation-runner-m18",
        )
        print("Started clean Verdant cultivation kernel.")
    session = CultivationSession(kernel, checkpoint_path)

    if args.script:
        session.run_jsonl(args.script)
    if args.non_interactive:
        session.status()
        return 0

    _help()
    while True:
        try:
            raw = input("\nverdant> ").strip()
        except EOFError:
            print()
            break
        if not raw:
            continue
        parts = shlex.split(raw)
        command = parts[0].lower()
        try:
            if command in {"quit", "exit", "q"}:
                break
            if command == "help":
                _help()
            elif command == "status":
                session.status()
            elif command == "candidates":
                session.list_candidates()
            elif command == "structures":
                session.list_structures()
            elif command == "promote":
                if len(parts) != 2:
                    raise ValueError("Usage: promote <index-or-candidate-id>")
                session.promote(parts[1])
            elif command == "compile":
                if len(parts) != 2:
                    raise ValueError("Usage: compile <label>")
                session.compile_probe(parts[1])
            elif command == "compare":
                if len(parts) != 2:
                    raise ValueError("Usage: compare <label>")
                session.compare(parts[1])
            elif command == "interact":
                if len(parts) != 2:
                    raise ValueError("Usage: interact <index-or-structure-id>")
                session.interact(parts[1])
            elif command == "hierarchy":
                session.list_hierarchy()
            elif command == "promoteq":
                if len(parts) != 2:
                    raise ValueError("Usage: promoteq <index-or-candidate-id>")
                session.promote_hierarchy(parts[1])
            elif command == "qprobe":
                if len(parts) != 2:
                    raise ValueError("Usage: qprobe <index-or-structure-id>")
                session.layered_probe(parts[1])
            elif command == "qcompare":
                if len(parts) != 2:
                    raise ValueError("Usage: qcompare <index-or-structure-id>")
                session.layered_compare(parts[1])
            elif command == "qablate":
                if len(parts) != 2:
                    raise ValueError("Usage: qablate <index-or-Q-id>")
                session.ablate_layered(parts[1])
            elif command == "qrestore":
                if len(parts) != 2:
                    raise ValueError("Usage: qrestore <index-or-Q-id>")
                session.restore_layered(parts[1])
            elif command == "challenge":
                if len(parts) not in {4, 5}:
                    raise ValueError("Usage: challenge <structure> <labelA> <labelB> [confidence]")
                session.challenge_structure(
                    parts[1], parts[2], parts[3], float(parts[4]) if len(parts) == 5 else 0.80
                )
            elif command == "refold":
                if len(parts) != 2:
                    raise ValueError("Usage: refold <structure>")
                session.refold_structure(parts[1])
            elif command == "refolds":
                session.list_refolds()
            elif command == "ablate":
                if len(parts) != 2:
                    raise ValueError("Usage: ablate <index-or-structure-id>")
                session.ablate(parts[1])
            elif command == "restore":
                if len(parts) != 2:
                    raise ValueError("Usage: restore <index-or-structure-id>")
                session.restore(parts[1])
            elif command == "save":
                session.save(Path(parts[1]) if len(parts) > 1 else None)
            elif command == "export":
                if len(parts) != 2:
                    raise ValueError("Usage: export <path>")
                session.export(Path(parts[1]))
            elif command in {"teach", "probe"}:
                if len(parts) < 3:
                    raise ValueError(f"Usage: {command} <context> <label1> [label2 ...]")
                labels = tuple(parts[2:]) if command == "teach" else (parts[2],)
                session.teach(labels, context_id=parts[1])
            else:
                print("Unknown command. Type 'help'.")
        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
