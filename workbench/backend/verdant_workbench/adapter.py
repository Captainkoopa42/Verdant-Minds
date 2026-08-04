from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from verdant_compilation import VerdantCompilationPipeline
from verdant_development import VerdantDevelopmentPipeline
from verdant_hierarchy import VerdantHierarchyPipeline
from verdant_interaction import VerdantStructureInteractionPipeline
from verdant_kernel import EvidenceKind, ExperienceCommand, VerdantKernel, load_checkpoint, save_checkpoint
from verdant_refolding import VerdantRefoldingPipeline
from verdant_structures import VerdantStructurePipeline
from verdant_language import ControlledGrammarAnalyzer, VerdantLanguagePipeline
from verdant_language.models import GRAMMAR_RULES, GrammarRuleId, LexemeSpec, LexicalCategory

from .events import development_events, make_event, model_event
from .forensics import detail as forensic_detail, graph as forensic_graph, list_structures as forensic_list_structures, replay as forensic_replay
from .living import living_frame, living_timeline
from .models import (
    CheckpointDescriptor,
    CommandEnvelope,
    CommandReceipt,
    OrganismConfig,
    OrganismDescriptor,
    ProbeRequest,
    GrammarPreviewRequest,
    GrammarRuleTeachRequest,
    LexemeTeachRequest,
    LanguageSentenceTeachRequest,
    Snapshot,
    SnapshotScope,
    TeachingRequest,
    new_id,
)


class WorkbenchAdapterError(RuntimeError):
    pass


class StaleWorkbenchCommandError(WorkbenchAdapterError):
    pass


class UnsupportedWorkbenchOperation(WorkbenchAdapterError):
    pass


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def deterministic_feature(labels: tuple[str, ...], width: int) -> tuple[float, ...]:
    text = "|".join(sorted(item.strip().lower() for item in labels if item.strip()))
    slot = int(_digest(text)[:8], 16) % width
    return tuple(1.0 if index == slot else 0.0 for index in range(width))


class VerdantEngineAdapter:
    """Stable Workbench-facing facade over the existing Verdant engine.

    This class owns no cognitive semantics. It delegates to the already-tested
    engine pipelines, applies Workbench revision checks, and maps committed
    engine activity into observational event envelopes.
    """

    def __init__(self, *, kernel: VerdantKernel, run_id: str, organism_id: str) -> None:
        self.kernel = kernel
        self.run_id = run_id
        self.organism_id = organism_id
        self.development = VerdantDevelopmentPipeline()
        self.structures = VerdantStructurePipeline()
        self.compilation = VerdantCompilationPipeline()
        self.interaction = VerdantStructureInteractionPipeline()
        self.hierarchy = VerdantHierarchyPipeline()
        self.refolding = VerdantRefoldingPipeline()
        self.language = VerdantLanguagePipeline()
        self.grammar = ControlledGrammarAnalyzer()
        self.event_ledger = []
        self._manual_sequence = len(
            [key for key in kernel.state.processed_event_keys if key.startswith("workbench-")]
        )

    @classmethod
    def create(
        cls,
        config: OrganismConfig,
        *,
        run_id: str | None = None,
        organism_id: str | None = None,
    ) -> "VerdantEngineAdapter":
        kernel = VerdantKernel(seed=config.seed, state_dim=config.state_dim, run_label=config.run_label)
        return cls(
            kernel=kernel,
            run_id=run_id or new_id("run"),
            organism_id=organism_id or new_id("org"),
        )

    @classmethod
    def load(
        cls,
        checkpoint_path: Path | str,
        *,
        run_id: str | None = None,
        organism_id: str | None = None,
    ) -> "VerdantEngineAdapter":
        kernel = VerdantKernel.from_state(load_checkpoint(Path(checkpoint_path)))
        return cls(
            kernel=kernel,
            run_id=run_id or new_id("run"),
            organism_id=organism_id or new_id("org"),
        )

    @property
    def state_revision(self) -> int:
        return int(self.kernel.state.event_sequence)

    def descriptor(self) -> OrganismDescriptor:
        return OrganismDescriptor(
            organism_id=self.organism_id,
            run_id=self.run_id,
            kernel_id=self.kernel.state.identity.kernel_id,
            seed=self.kernel.state.seed,
            state_dim=self.kernel.state.field.state_dim,
            run_label=self.kernel.state.identity.run_label,
            cycle=self.kernel.state.cycle,
            state_revision=self.state_revision,
            fingerprint=self.kernel.fingerprint(),
        )

    def _check_envelope(self, envelope: CommandEnvelope) -> None:
        if envelope.run_id != self.run_id or envelope.organism_id != self.organism_id:
            raise WorkbenchAdapterError("Command run/organism identity does not match adapter.")
        expected = envelope.expected_state_revision
        if expected is not None and expected != self.state_revision:
            raise StaleWorkbenchCommandError(
                f"Expected state revision {expected}, current revision is {self.state_revision}."
            )

    def _receipt(self, *, envelope: CommandEnvelope, before_revision: int, before_cycle: int, before_fingerprint: str, events=(), result=None, replayed=False) -> CommandReceipt:
        events = tuple(events)
        self.event_ledger.extend(events)
        return CommandReceipt(
            command_id=envelope.command_id,
            command_type=envelope.command_type,
            organism_id=self.organism_id,
            run_id=self.run_id,
            state_revision_before=before_revision,
            state_revision_after=self.state_revision,
            cycle_before=before_cycle,
            cycle_after=self.kernel.state.cycle,
            fingerprint_before=before_fingerprint,
            fingerprint_after=self.kernel.fingerprint(),
            replayed=replayed,
            events=events,
            result=result or {},
        )

    def _next_event_key(self) -> str:
        self._manual_sequence += 1
        return f"workbench-{self._manual_sequence:06d}"

    def compile_teaching_request(self, request: TeachingRequest) -> ExperienceCommand:
        labels = tuple(item.strip() for item in request.labels if item.strip())
        if not labels:
            raise WorkbenchAdapterError("Teaching request requires at least one non-empty label.")
        event_key = request.event_key or self._next_event_key()
        feature = request.feature_vector or deterministic_feature(labels, self.kernel.state.field.state_dim)
        if len(feature) != self.kernel.state.field.state_dim:
            raise WorkbenchAdapterError(
                f"Feature vector width {len(feature)} does not match engine state_dim {self.kernel.state.field.state_dim}."
            )
        payload = {
            "event_key": event_key,
            "context_id": request.context_id,
            "labels": labels,
            "feature_vector": feature,
        }
        return ExperienceCommand(
            event_key=event_key,
            source_ref=f"workbench:{request.context_id}",
            modality="text",
            payload_sha256=_digest(json.dumps(payload, sort_keys=True)),
            feature_vector=feature,
            concept_labels=labels,
            confidence=request.confidence,
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={
                "workbench": True,
                "taught_content": "primitive_symbol_presence_only",
            },
            metadata={"context_id": request.context_id, "workbench_event": True},
        )

    def submit_teaching(self, envelope: CommandEnvelope, request: TeachingRequest) -> CommandReceipt:
        return self.submit_experience(envelope, self.compile_teaching_request(request))

    def submit_experience(self, envelope: CommandEnvelope, command: ExperienceCommand) -> CommandReceipt:
        self._check_envelope(envelope)
        before_revision = self.state_revision
        before_cycle = self.kernel.state.cycle
        before_fp = self.kernel.fingerprint()
        result = self.development.advance(self.kernel, command)
        events = development_events(
            run_id=self.run_id,
            organism_id=self.organism_id,
            kernel=self.kernel,
            command_id=envelope.command_id,
            result=result,
        )
        return self._receipt(
            envelope=envelope,
            before_revision=before_revision,
            before_cycle=before_cycle,
            before_fingerprint=before_fp,
            events=events,
            replayed=result.replayed,
            result={
                "experience_event_key": result.experience.event_key,
                "semantic_firewall_held": result.semantic_firewall_held,
                "candidate_scope_ids": list(result.candidate_scope_ids),
            },
        )

    def grammar_status(self) -> dict[str, Any]:
        enabled = self.grammar.enabled_rules(self.kernel)
        lexicon = self.grammar.lexicon(self.kernel)
        rules = []
        for rule_id, spec in GRAMMAR_RULES.items():
            rules.append({
                "rule_id": rule_id.value,
                "pattern": spec.pattern,
                "description": spec.description,
                "curriculum_text": spec.curriculum_text,
                "roles": list(spec.roles),
                "enabled": rule_id in enabled,
            })
        entries = [
            {"form": form, "lemma": lemma, "category": category.value}
            for form, (lemma, category) in sorted(lexicon.items())
        ]
        return {
            "state_revision": self.state_revision,
            "cycle": self.kernel.state.cycle,
            "enabled_rules": [item.value for item in enabled],
            "rules": rules,
            "lexicon": entries,
        }

    def grammar_preview(self, request: GrammarPreviewRequest) -> dict[str, Any]:
        before_fp = self.kernel.fingerprint()
        before_revision = self.state_revision
        plan = self.grammar.plan(request.sentence, request.event_key, self.kernel)
        after_fp = self.kernel.fingerprint()
        if after_fp != before_fp or self.state_revision != before_revision:
            raise WorkbenchAdapterError("Grammar preview mutated canonical Verdant state.")
        return {
            "state_revision": before_revision,
            "fingerprint": before_fp,
            "analysis": plan.analysis.model_dump(mode="json"),
            "concept_proposals": [item.model_dump(mode="json") for item in plan.concept_proposals],
            "relation_proposals": [item.model_dump(mode="json") for item in plan.relation_proposals],
            "claim_proposals": [item.model_dump(mode="json") for item in plan.claim_proposals],
        }

    def _language_receipt(self, *, envelope: CommandEnvelope, before_revision: int, before_cycle: int, before_fingerprint: str, learning_result, action: str) -> CommandReceipt:
        exp = learning_result.kernel_result
        payload = {
            "event_key": exp.event_key,
            "cycle": exp.cycle,
            "concept_ids": list(exp.concept_ids),
            "relation_ids": list(exp.relation_ids),
            "claim_ids": list(exp.claim_ids),
            "contradiction_ids": list(exp.contradiction_ids),
            "revision_ids": list(exp.revision_ids),
            "observation_evidence_id": exp.observation_evidence_id,
            "translation_evidence_id": exp.translation_evidence_id,
            "additional_evidence_ids": list(exp.additional_evidence_ids),
            "replayed": exp.replayed,
            "language_action": action,
            "analysis": learning_result.analysis.model_dump(mode="json"),
        }
        event = make_event(
            run_id=self.run_id,
            organism_id=self.organism_id,
            kernel=self.kernel,
            command_id=envelope.command_id,
            event_type="EVIDENCE_ACCEPTED",
            payload=payload,
            native_id=exp.event_key,
        )
        return self._receipt(
            envelope=envelope,
            before_revision=before_revision,
            before_cycle=before_cycle,
            before_fingerprint=before_fingerprint,
            events=(event,),
            replayed=exp.replayed,
            result={
                "experience_event_key": exp.event_key,
                "analysis": learning_result.analysis.model_dump(mode="json"),
                "language_action": action,
            },
        )

    def teach_grammar_rule(self, envelope: CommandEnvelope, request: GrammarRuleTeachRequest) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        try:
            rule_id = GrammarRuleId(request.rule_id)
        except ValueError as exc:
            raise WorkbenchAdapterError(f"Unknown grammar rule: {request.rule_id}") from exc
        result = self.language.teach_rule(self.kernel, rule_id, event_key=request.event_key)
        return self._language_receipt(
            envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
            learning_result=result, action="grammar_rule",
        )

    def teach_lexeme(self, envelope: CommandEnvelope, request: LexemeTeachRequest) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        try:
            category = LexicalCategory(request.category)
        except ValueError as exc:
            raise WorkbenchAdapterError(f"Unknown lexical category: {request.category}") from exc
        result = self.language.teach_lexeme(
            self.kernel,
            LexemeSpec(lemma=request.lemma, category=category, forms=request.forms, attributes=request.attributes),
            event_key=request.event_key,
        )
        return self._language_receipt(
            envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
            learning_result=result, action="lexeme",
        )

    def teach_language_sentence(self, envelope: CommandEnvelope, request: LanguageSentenceTeachRequest) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.language.learn_sentence(self.kernel, request.sentence, event_key=request.event_key)
        return self._language_receipt(
            envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
            learning_result=result, action="sentence",
        )

    def _resolve_concepts(self, labels: tuple[str, ...]) -> tuple[str, ...]:
        wanted = {item.strip().lower() for item in labels}
        matches = [
            concept_id for concept_id, concept in self.kernel.state.concepts.items()
            if concept.normalized_label in wanted
        ]
        if len(matches) != len(wanted):
            found = {self.kernel.state.concepts[item].normalized_label for item in matches}
            missing = sorted(wanted - found)
            raise WorkbenchAdapterError("Unknown cue label(s): " + ", ".join(missing))
        return tuple(sorted(matches))

    def probe(self, envelope: CommandEnvelope, request: ProbeRequest) -> CommandReceipt:
        self._check_envelope(envelope)
        before_revision = self.state_revision
        before_cycle = self.kernel.state.cycle
        before_fp = self.kernel.fingerprint()
        result = self.compilation.probe(self.kernel, self._resolve_concepts(request.cue_labels))
        event = model_event(
            run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
            command_id=envelope.command_id, event_type="STRUCTURE_USED", model=result.event,
        )
        return self._receipt(
            envelope=envelope, before_revision=before_revision, before_cycle=before_cycle,
            before_fingerprint=before_fp, events=(event,),
            result=result.report.model_dump(mode="json"),
        )

    def promote_structure(self, envelope: CommandEnvelope, candidate_id: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.structures.promote(self.kernel, candidate_id)
        event = model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                            command_id=envelope.command_id, event_type="STRUCTURE_PROMOTED", model=result.event)
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=(event,), result={"structure_id": result.event.structure_id})

    def ablate_structure(self, envelope: CommandEnvelope, structure_id: str) -> CommandReceipt:
        return self._set_structure_availability(envelope, structure_id, available=False)

    def restore_structure(self, envelope: CommandEnvelope, structure_id: str) -> CommandReceipt:
        return self._set_structure_availability(envelope, structure_id, available=True)

    def _set_structure_availability(self, envelope: CommandEnvelope, structure_id: str, *, available: bool) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        native = self.compilation.restore(self.kernel, structure_id, "Workbench restoration") if available else self.compilation.ablate(self.kernel, structure_id, "Workbench ablation")
        event = model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                            command_id=envelope.command_id, event_type="STRUCTURE_AVAILABILITY_CHANGED", model=native)
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=(event,), result={"structure_id": structure_id, "available": available})

    def interact(self, envelope: CommandEnvelope, structure_id: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.interaction.interact(self.kernel, structure_id)
        event = model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                            command_id=envelope.command_id, event_type="STRUCTURE_INTERACTION_VERIFIED", model=result.event)
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=(event,), result=result.report.model_dump(mode="json"))

    def observe_hierarchy(self, envelope: CommandEnvelope) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.hierarchy.observe(self.kernel)
        if result is None:
            return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2], events=(), result={})
        events = () if result.event is None else (
            model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                        command_id=envelope.command_id, event_type="HIERARCHY_CANDIDATE_OBSERVED", model=result.event),
        )
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=events, result=result.report.model_dump(mode="json") if result.report else {})

    def promote_hierarchy(self, envelope: CommandEnvelope, candidate_id: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.hierarchy.promote(self.kernel, candidate_id)
        event = model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                            command_id=envelope.command_id, event_type="HIERARCHY_PROMOTED", model=result.event)
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=(event,), result={"layered_structure_id": result.event.layered_structure_id})

    def probe_hierarchy(self, envelope: CommandEnvelope, query_structure_id: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.hierarchy.probe(self.kernel, query_structure_id)
        event = model_event(
            run_id=self.run_id,
            organism_id=self.organism_id,
            kernel=self.kernel,
            command_id=envelope.command_id,
            event_type="LAYERED_PROBE_COMMITTED",
            model=result.event,
        )
        return self._receipt(
            envelope=envelope,
            before_revision=before[0],
            before_cycle=before[1],
            before_fingerprint=before[2],
            events=(event,),
            result=result.report.model_dump(mode="json"),
        )

    def ablate_hierarchy(self, envelope: CommandEnvelope, layered_structure_id: str) -> CommandReceipt:
        return self._set_hierarchy_availability(
            envelope, layered_structure_id, available=False
        )

    def restore_hierarchy(self, envelope: CommandEnvelope, layered_structure_id: str) -> CommandReceipt:
        return self._set_hierarchy_availability(
            envelope, layered_structure_id, available=True
        )

    def _set_hierarchy_availability(
        self,
        envelope: CommandEnvelope,
        layered_structure_id: str,
        *,
        available: bool,
    ) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        if available:
            native = self.hierarchy.restore(
                self.kernel, layered_structure_id, "Workbench Q restoration"
            )
        else:
            native = self.hierarchy.ablate(
                self.kernel, layered_structure_id, "Workbench Q ablation"
            )
        event = model_event(
            run_id=self.run_id,
            organism_id=self.organism_id,
            kernel=self.kernel,
            command_id=envelope.command_id,
            event_type="LAYERED_STRUCTURE_AVAILABILITY_CHANGED",
            model=native,
        )
        return self._receipt(
            envelope=envelope,
            before_revision=before[0],
            before_cycle=before[1],
            before_fingerprint=before[2],
            events=(event,),
            result={
                "layered_structure_id": layered_structure_id,
                "available": available,
            },
        )

    def challenge(self, envelope: CommandEnvelope, *, structure_id: str, concept_ids: tuple[str, str], confidence: float, evidence_ref: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.refolding.challenge(
            self.kernel,
            structure_id,
            concept_ids,
            evidence_refs=(evidence_ref,),
            confidence=confidence,
        )
        event = model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                            command_id=envelope.command_id, event_type="STRUCTURAL_CHALLENGE_RECORDED", model=result)
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=(event,), result=result.model_dump(mode="json"))

    def refold(self, envelope: CommandEnvelope, structure_id: str) -> CommandReceipt:
        self._check_envelope(envelope)
        before = (self.state_revision, self.kernel.state.cycle, self.kernel.fingerprint())
        result = self.refolding.refold(self.kernel, structure_id)
        events = () if result.event is None else (
            model_event(run_id=self.run_id, organism_id=self.organism_id, kernel=self.kernel,
                        command_id=envelope.command_id, event_type="STRUCTURE_REFOLDED", model=result.event),
        )
        return self._receipt(envelope=envelope, before_revision=before[0], before_cycle=before[1], before_fingerprint=before[2],
                             events=events, result=result.report.model_dump(mode="json"))


    def forensic_list_structures(self) -> dict[str, Any]:
        return forensic_list_structures(self.kernel)

    def forensic_structure_detail(self, structure_id: str) -> dict[str, Any]:
        return forensic_detail(self.kernel, structure_id)

    def forensic_structure_replay(self, structure_id: str) -> dict[str, Any]:
        return forensic_replay(self.kernel, structure_id)

    def forensic_structure_graph(self, structure_id: str) -> dict[str, Any]:
        return forensic_graph(self.kernel, structure_id)

    def living_explorer_frame(self, cycle: int | None = None, *, max_nodes: int = 240, max_edges: int = 500) -> dict[str, Any]:
        return living_frame(self.kernel, cycle, max_nodes=max_nodes, max_edges=max_edges)

    def living_explorer_timeline(self, *, max_frames: int = 240, max_nodes: int = 240, max_edges: int = 500, include_frames: bool = True) -> dict[str, Any]:
        return living_timeline(self.kernel, max_frames=max_frames, max_nodes=max_nodes, max_edges=max_edges, include_frames=include_frames)

    def metrics(self) -> dict[str, Any]:
        return self.kernel.metrics()

    def snapshot(self, scope: SnapshotScope = SnapshotScope.SUMMARY) -> Snapshot:
        metrics = self.kernel.metrics()
        if scope == SnapshotScope.SUMMARY:
            payload = {"metrics": metrics}
        elif scope == SnapshotScope.WORKSPACE:
            payload = {
                "metrics": metrics,
                "workspace_items": [item.model_dump(mode="json") for item in self.kernel.state.workspace_items.values()],
            }
        elif scope == SnapshotScope.STRUCTURES:
            payload = {
                "metrics": metrics,
                "structure_candidates": [item.model_dump(mode="json") for item in self.kernel.state.structure_candidates.values()],
                "structures": [item.model_dump(mode="json") for item in self.kernel.state.structures.values()],
                "hierarchy_candidates": [item.model_dump(mode="json") for item in self.kernel.state.hierarchy_candidates.values()],
                "layered_structures": [item.model_dump(mode="json") for item in self.kernel.state.layered_structures.values()],
            }
        elif scope == SnapshotScope.FULL_DEBUG:
            payload = {"state": self.kernel.snapshot().model_dump(mode="json")}
        else:
            raise UnsupportedWorkbenchOperation(str(scope))
        return Snapshot(
            organism_id=self.organism_id,
            run_id=self.run_id,
            scope=scope,
            engine_cycle=self.kernel.state.cycle,
            state_revision=self.state_revision,
            fingerprint=self.kernel.fingerprint(),
            payload=payload,
        )

    def save(self, path: Path | str) -> CheckpointDescriptor:
        path = Path(path)
        digest = save_checkpoint(path, self.kernel.snapshot())
        return CheckpointDescriptor(
            path=str(path),
            checkpoint_sha256=digest,
            canonical_fingerprint=self.kernel.fingerprint(),
            state_revision=self.state_revision,
            cycle=self.kernel.state.cycle,
        )
