from __future__ import annotations

import difflib
import hashlib
import io
import json
import re
import shlex
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from verdant_kernel import (
    ClaimPolarity,
    ClaimProposal,
    ClaimSourceClass,
    ConceptProposal,
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
)


CURRICULUM_SCHEMA_VERSION = "verdant.curriculum.v1"
CURRICULUM_COMPILER_VERSION = "verdant.workbench.curriculum-compiler.v1.1"
TEACHING_BUNDLE_SCHEMA_VERSION = "verdant.teaching.bundle.v1"
CURRICULUM_PACK_SCHEMA_VERSION = "verdant.curriculum.pack.v1"
CURRICULUM_PACKAGE_MEDIA_TYPE = "application/vnd.verdant.curriculum+zip"


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def normalize_source(source: str) -> str:
    return source.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"


def compiled_commands_sha256(commands: Iterable[ExperienceCommand]) -> str:
    payload = [command.model_dump(mode="json") for command in commands]
    return sha256_bytes(_canonical_json_bytes(payload))


def compiled_commands_jsonl(commands: Iterable[ExperienceCommand]) -> str:
    return "".join(
        json.dumps(command.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        for command in commands
    )


class CurriculumCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    title: str = "Untitled Curriculum"
    source_format: Literal["primitive_lines", "experience_jsonl", "teaching_bundle_json"] = "primitive_lines"
    source_text: str
    state_dim: int = Field(default=128, ge=1)
    baseline_curriculum_id: str | None = None


class CurriculumFreezeRequest(CurriculumCompileRequest):
    expected_compiled_sha256: str | None = None


class LanguageScaffoldLexeme(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lemma: str = Field(min_length=1)
    category: str = Field(min_length=1)
    forms: tuple[str, ...] = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)
    event_key: str | None = None


class LanguageScaffoldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grammar_rules: tuple[str, ...] = ()
    lexicon: tuple[LanguageScaffoldLexeme, ...] = ()
    notes: str = ""


class TeachingConceptSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(min_length=1)
    attributes: dict[str, Any] = Field(default_factory=dict)


class TeachingRelationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    target: str = Field(min_length=1)
    directed: bool = True
    weight: float = Field(default=0.8, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TeachingClaimSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    polarity: str = "affirmed"
    source_class: str = "human_testimony"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rationale: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)


class EditableTeachingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    source_text: str = ""
    modality: str = "text"
    concepts: tuple[TeachingConceptSpec, ...] = ()
    relations: tuple[TeachingRelationSpec, ...] = ()
    claims: tuple[TeachingClaimSpec, ...] = ()
    feature_vector: tuple[float, ...] | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: dict[str, Any] = Field(default_factory=dict)
    grammar_annotation: dict[str, Any] = Field(default_factory=dict)
    lexicon_annotation: tuple[dict[str, Any], ...] = ()
    event_key: str | None = None
    source_ref: str | None = None
    semantic_evidence_kind: str = "testimony"


class EditableTeachingBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_id: str = Field(default=TEACHING_BUNDLE_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    language_scaffold: LanguageScaffoldSpec = Field(default_factory=LanguageScaffoldSpec)
    items: tuple[EditableTeachingItem, ...] = Field(min_length=1)
    notes: str = ""


class CurriculumPackProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    test_id: str = Field(min_length=1)
    cue_labels: tuple[str, ...] = Field(min_length=1)
    notes: str = ""


class CurriculumPackSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    enabled: bool = True
    language_scaffold: LanguageScaffoldSpec = Field(default_factory=LanguageScaffoldSpec)
    items: tuple[EditableTeachingItem, ...] = Field(min_length=1)
    tests: tuple[CurriculumPackProbe, ...] = ()


class CurriculumPack(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)
    schema_id: str = Field(default=CURRICULUM_PACK_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    title: str = Field(min_length=1)
    description: str = ""
    state_dim: int = Field(default=128, ge=1)
    language_scaffold: LanguageScaffoldSpec = Field(default_factory=LanguageScaffoldSpec)
    sections: tuple[CurriculumPackSection, ...] = Field(min_length=1)
    notes: str = ""


class CurriculumPackCompileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    project_id: str
    pack_text: str
    selected_section_ids: tuple[str, ...] = ()
    baseline_curriculum_id: str | None = None


class CurriculumPackFreezeRequest(CurriculumPackCompileRequest):
    expected_compiled_sha256: str | None = None


class CurriculumCompileResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, serialize_by_alias=True)
    schema_id: str = Field(default=CURRICULUM_SCHEMA_VERSION, alias="schema", serialization_alias="schema")
    compiler_version: str = CURRICULUM_COMPILER_VERSION
    title: str
    source_format: str
    source_text: str
    source_sha256: str
    state_dim: int
    item_count: int
    scaffold_item_count: int = 0
    language_scaffold: dict[str, Any] = Field(default_factory=dict)
    parsed_items: tuple[dict[str, Any], ...]
    compiled_commands: tuple[dict[str, Any], ...]
    compiled_jsonl: str
    compiled_sha256: str
    warnings: tuple[str, ...] = ()
    diff_from_baseline: str | None = None


@dataclass(frozen=True)
class CurriculumPackage:
    manifest: dict[str, Any]
    source_text: str
    curriculum_ir: dict[str, Any]
    compiled_commands: tuple[ExperienceCommand, ...]
    language_scaffold: dict[str, Any]
    hashes: dict[str, str]


class CurriculumCompilerError(ValueError):
    pass


class CurriculumCompiler:
    """Deterministic, intentionally narrow Workbench curriculum compiler.

    Three source forms are supported:
    - primitive_lines: a small explicit line grammar for primitive presence/edges;
    - experience_jsonl: one complete ExperienceCommand JSON object per line;
    - teaching_bundle_json: an explicit, fully editable teaching record plus optional
      language scaffold. No prose-to-semantics inference occurs in this mode.

    Arbitrary prose is deliberately not treated as if the compiler understood it.
    Source sentences, grammar notes and lexicon notes are provenance/authoring data
    unless the author explicitly supplies concepts, relations, claims or scaffold items.
    """

    def compile(self, request: CurriculumCompileRequest, *, baseline_jsonl: str | None = None) -> CurriculumCompileResult:
        source = normalize_source(request.source_text)
        source_sha = sha256_text(source)
        title = request.title.strip() or "Untitled Curriculum"
        language_scaffold: dict[str, Any] = {}
        if request.source_format == "experience_jsonl":
            parsed, commands, warnings = self._compile_experience_jsonl(source)
        elif request.source_format == "primitive_lines":
            parsed, commands, warnings = self._compile_primitive_lines(
                source,
                title=title,
                source_sha=source_sha,
                state_dim=request.state_dim,
            )
        elif request.source_format == "teaching_bundle_json":
            parsed, commands, warnings, language_scaffold = self._compile_teaching_bundle(
                source,
                title=title,
                source_sha=source_sha,
                state_dim=request.state_dim,
            )
        else:  # pragma: no cover - Literal validation catches this first
            raise CurriculumCompilerError(f"Unsupported source format: {request.source_format}")

        if not commands:
            raise CurriculumCompilerError("Curriculum contains no executable teaching items.")
        event_keys = [command.event_key for command in commands]
        duplicates = sorted({key for key in event_keys if event_keys.count(key) > 1})
        if duplicates:
            raise CurriculumCompilerError("Duplicate event_key values: " + ", ".join(duplicates))

        jsonl = compiled_commands_jsonl(commands)
        digest = compiled_commands_sha256(commands)
        if language_scaffold:
            digest = sha256_bytes(_canonical_json_bytes({
                "language_scaffold": language_scaffold,
                "compiled_commands": [command.model_dump(mode="json") for command in commands],
            }))
        diff = None
        if baseline_jsonl is not None:
            diff = "".join(
                difflib.unified_diff(
                    baseline_jsonl.splitlines(keepends=True),
                    jsonl.splitlines(keepends=True),
                    fromfile="baseline/compiled_commands.jsonl",
                    tofile="current/compiled_commands.jsonl",
                )
            )
            if not diff:
                diff = "No compiled-command differences.\n"

        return CurriculumCompileResult(
            title=title,
            source_format=request.source_format,
            source_text=source,
            source_sha256=source_sha,
            state_dim=request.state_dim,
            item_count=len(commands),
            scaffold_item_count=len(language_scaffold.get("grammar_rules", [])) + len(language_scaffold.get("lexicon", [])),
            language_scaffold=language_scaffold,
            parsed_items=tuple(parsed),
            compiled_commands=tuple(command.model_dump(mode="json") for command in commands),
            compiled_jsonl=jsonl,
            compiled_sha256=digest,
            warnings=tuple(warnings),
            diff_from_baseline=diff,
        )

    def _compile_experience_jsonl(self, source: str) -> tuple[list[dict[str, Any]], list[ExperienceCommand], list[str]]:
        parsed: list[dict[str, Any]] = []
        commands: list[ExperienceCommand] = []
        for line_no, raw in enumerate(source.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise CurriculumCompilerError(f"Line {line_no}: invalid JSON: {exc.msg}") from exc
            try:
                command = ExperienceCommand.model_validate(obj)
            except Exception as exc:
                raise CurriculumCompilerError(f"Line {line_no}: invalid ExperienceCommand: {exc}") from exc
            parsed.append({
                "line": line_no,
                "kind": "experience_command",
                "event_key": command.event_key,
                "context_id": command.metadata.get("context_id"),
                "labels": list(command.concept_labels),
                "relation_count": len(command.relation_proposals),
                "claim_count": len(command.claim_proposals),
                "source_ref": command.source_ref,
            })
            commands.append(command)
        return parsed, commands, []

    def _compile_primitive_lines(
        self,
        source: str,
        *,
        title: str,
        source_sha: str,
        state_dim: int,
    ) -> tuple[list[dict[str, Any]], list[ExperienceCommand], list[str]]:
        parsed: list[dict[str, Any]] = []
        commands: list[ExperienceCommand] = []
        warnings: list[str] = []
        for line_no, raw in enumerate(source.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            segments = [part.strip() for part in stripped.split("|")]
            try:
                tokens = shlex.split(segments[0])
            except ValueError as exc:
                raise CurriculumCompilerError(f"Line {line_no}: {exc}") from exc
            if not tokens:
                continue
            kind = tokens[0].upper()
            options: dict[str, str] = {}
            for segment in segments[1:]:
                if not segment:
                    continue
                if "=" not in segment:
                    raise CurriculumCompilerError(f"Line {line_no}: option '{segment}' must use key=value.")
                key, value = segment.split("=", 1)
                options[key.strip().lower()] = value.strip()

            if kind == "PRESENCE":
                if len(tokens) < 3:
                    raise CurriculumCompilerError(f"Line {line_no}: PRESENCE requires context and at least one label.")
                context_id = tokens[1]
                labels = tuple(tokens[2:])
                relation_proposals: tuple[RelationProposal, ...] = ()
                item_summary = {"line": line_no, "kind": "presence", "context_id": context_id, "labels": list(labels)}
            elif kind == "EDGE":
                if len(tokens) != 5:
                    raise CurriculumCompilerError(
                        f"Line {line_no}: EDGE syntax is 'EDGE <context> <source> <relation> <target>'."
                    )
                _, context_id, source_label, relation_type, target_label = tokens
                labels = (source_label, target_label)
                directed = self._bool_option(options.get("directed", "false"), line_no)
                weight = self._float_option(options.get("weight", "0.8"), line_no, "weight")
                relation_conf = self._float_option(options.get("relation_confidence", options.get("confidence", "1.0")), line_no, "relation_confidence")
                relation_proposals = (
                    RelationProposal(
                        source_label=source_label,
                        target_label=target_label,
                        relation_type=relation_type,
                        directed=directed,
                        weight=weight,
                        confidence=relation_conf,
                    ),
                )
                item_summary = {
                    "line": line_no,
                    "kind": "edge",
                    "context_id": context_id,
                    "source": source_label,
                    "relation_type": relation_type,
                    "target": target_label,
                    "directed": directed,
                    "weight": weight,
                }
            else:
                raise CurriculumCompilerError(f"Line {line_no}: unknown statement '{tokens[0]}'.")

            confidence = self._float_option(options.get("confidence", "1.0"), line_no, "confidence")
            feature = self._feature_option(options.get("feature"), labels, state_dim)
            event_key = options.get("key") or f"vcurr:{source_sha[:12]}:{line_no:04d}"
            source_ref = options.get("source_ref") or f"workbench:curriculum:{self._slug(title)}"
            payload_seed = {
                "line": line_no,
                "event_key": event_key,
                "context_id": context_id,
                "labels": labels,
                "feature": feature,
                "relations": [item.model_dump(mode="json") for item in relation_proposals],
                "source_ref": source_ref,
            }
            command = ExperienceCommand(
                event_key=event_key,
                source_ref=source_ref,
                modality=options.get("modality", "text"),
                payload_sha256=options.get("payload_sha256") or sha256_bytes(_canonical_json_bytes(payload_seed)),
                feature_vector=feature,
                concept_labels=labels,
                relation_proposals=relation_proposals,
                confidence=confidence,
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={
                    "source_type": "workbench_compiled_curriculum",
                    "curriculum_source_sha256": source_sha,
                    "curriculum_line": line_no,
                },
                metadata={
                    "context_id": context_id,
                    "workbench_curriculum": True,
                    "curriculum_line": line_no,
                },
            )
            parsed.append({**item_summary, "event_key": event_key, "feature_dim": len(feature), "confidence": confidence})
            commands.append(command)
        return parsed, commands, warnings

    def _compile_teaching_bundle(
        self,
        source: str,
        *,
        title: str,
        source_sha: str,
        state_dim: int,
    ) -> tuple[list[dict[str, Any]], list[ExperienceCommand], list[str], dict[str, Any]]:
        try:
            raw = json.loads(source)
        except json.JSONDecodeError as exc:
            raise CurriculumCompilerError(f"Teaching bundle JSON is invalid: {exc.msg}") from exc
        try:
            bundle = EditableTeachingBundle.model_validate(raw)
        except Exception as exc:
            raise CurriculumCompilerError(f"Teaching bundle is invalid: {exc}") from exc

        scaffold = bundle.language_scaffold.model_dump(mode="json")
        parsed: list[dict[str, Any]] = []
        commands: list[ExperienceCommand] = []
        warnings: list[str] = []
        for index, item in enumerate(bundle.items, start=1):
            concept_map: dict[str, ConceptProposal] = {
                spec.label: ConceptProposal(label=spec.label, attributes=spec.attributes)
                for spec in item.concepts
            }
            referenced: set[str] = set()
            relation_proposals: list[RelationProposal] = []
            for relation in item.relations:
                referenced.update((relation.source, relation.target))
                relation_proposals.append(RelationProposal(
                    source_label=relation.source,
                    target_label=relation.target,
                    relation_type=relation.relation,
                    directed=relation.directed,
                    weight=relation.weight,
                    confidence=relation.confidence,
                ))

            claim_proposals: list[ClaimProposal] = []
            for claim in item.claims:
                referenced.update((claim.subject, claim.object))
                try:
                    polarity = ClaimPolarity(claim.polarity)
                except ValueError as exc:
                    raise CurriculumCompilerError(
                        f"Teaching item {item.item_id}: unsupported claim polarity '{claim.polarity}'."
                    ) from exc
                try:
                    source_class = ClaimSourceClass(claim.source_class)
                except ValueError as exc:
                    raise CurriculumCompilerError(
                        f"Teaching item {item.item_id}: unsupported claim source_class '{claim.source_class}'."
                    ) from exc
                claim_proposals.append(ClaimProposal(
                    subject_label=claim.subject,
                    predicate=claim.predicate,
                    object_label=claim.object,
                    polarity=polarity,
                    source_class=source_class,
                    confidence=claim.confidence,
                    rationale=claim.rationale,
                    attributes=claim.attributes,
                ))

            auto_declared = sorted(referenced - set(concept_map))
            for label in auto_declared:
                concept_map[label] = ConceptProposal(
                    label=label,
                    attributes={"status": "explicit_reference_autodeclared_by_workbench"},
                )
            if auto_declared:
                warnings.append(
                    f"Teaching item {item.item_id}: auto-declared referenced concepts: {', '.join(auto_declared)}"
                )

            labels = tuple(sorted(concept_map))
            if not labels:
                raise CurriculumCompilerError(
                    f"Teaching item {item.item_id}: declare at least one concept, relation endpoint or claim endpoint."
                )
            if item.feature_vector is not None:
                if len(item.feature_vector) != state_dim:
                    raise CurriculumCompilerError(
                        f"Teaching item {item.item_id}: feature vector width {len(item.feature_vector)} does not match state_dim {state_dim}."
                    )
                feature = tuple(float(value) for value in item.feature_vector)
            else:
                feature = self._feature_option(None, labels, state_dim)
            try:
                evidence_kind = EvidenceKind(item.semantic_evidence_kind)
            except ValueError as exc:
                raise CurriculumCompilerError(
                    f"Teaching item {item.item_id}: unsupported semantic_evidence_kind '{item.semantic_evidence_kind}'."
                ) from exc

            event_key = item.event_key or f"vcurr:{source_sha[:12]}:{item.item_id}"
            source_ref = item.source_ref or f"workbench:editable-curriculum:{self._slug(title)}"
            explicit_record = item.model_dump(mode="json")
            command = ExperienceCommand(
                event_key=event_key,
                source_ref=source_ref,
                modality=item.modality,
                payload_sha256=sha256_bytes(_canonical_json_bytes(explicit_record)),
                feature_vector=feature,
                concept_proposals=tuple(concept_map[label] for label in sorted(concept_map)),
                relation_proposals=tuple(relation_proposals),
                claim_proposals=tuple(claim_proposals),
                confidence=item.confidence,
                semantic_evidence_kind=evidence_kind,
                semantic_evidence_details={
                    "source_type": "workbench_editable_teaching_record",
                    "curriculum_source_sha256": source_sha,
                    "item_id": item.item_id,
                    "source_text": item.source_text,
                    "grammar_annotation": item.grammar_annotation,
                    "lexicon_annotation": list(item.lexicon_annotation),
                    "provenance": item.provenance,
                },
                metadata={
                    "context_id": item.context_id,
                    "workbench_curriculum": True,
                    "editable_teaching_record": True,
                    "item_id": item.item_id,
                },
            )
            parsed.append({
                "item": index,
                "item_id": item.item_id,
                "kind": "editable_teaching_record",
                "context_id": item.context_id,
                "source_text": item.source_text,
                "concepts": labels,
                "relation_count": len(relation_proposals),
                "claim_count": len(claim_proposals),
                "grammar_annotation": item.grammar_annotation,
                "lexicon_annotation": list(item.lexicon_annotation),
                "provenance": item.provenance,
                "auto_declared_concepts": auto_declared,
                "event_key": event_key,
            })
            commands.append(command)
        return parsed, commands, warnings, scaffold

    @staticmethod
    def _bool_option(value: str, line_no: int) -> bool:
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
        raise CurriculumCompilerError(f"Line {line_no}: expected boolean, got '{value}'.")

    @staticmethod
    def _float_option(value: str, line_no: int, name: str) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise CurriculumCompilerError(f"Line {line_no}: {name} must be numeric.") from exc
        if name in {"confidence", "relation_confidence"} and not 0.0 <= number <= 1.0:
            raise CurriculumCompilerError(f"Line {line_no}: {name} must be within [0,1].")
        return number

    @staticmethod
    def _feature_option(raw: str | None, labels: tuple[str, ...], state_dim: int) -> tuple[float, ...]:
        if raw is not None:
            try:
                feature = tuple(float(item.strip()) for item in raw.split(",") if item.strip())
            except ValueError as exc:
                raise CurriculumCompilerError("feature values must be numeric.") from exc
            if len(feature) != state_dim:
                raise CurriculumCompilerError(
                    f"Explicit feature vector width {len(feature)} does not match requested state_dim {state_dim}."
                )
            return feature
        seed = "|".join(sorted(label.strip().lower() for label in labels))
        slot = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % state_dim
        return tuple(1.0 if index == slot else 0.0 for index in range(state_dim))

    @staticmethod
    def _slug(value: str) -> str:
        value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return value or "curriculum"


def parse_curriculum_pack(pack_text: str) -> CurriculumPack:
    try:
        raw = json.loads(normalize_source(pack_text))
    except json.JSONDecodeError as exc:
        raise CurriculumCompilerError(f"Curriculum pack JSON is invalid: {exc.msg}") from exc
    if not isinstance(raw, dict) or raw.get("schema") != CURRICULUM_PACK_SCHEMA_VERSION:
        raise CurriculumCompilerError(
            f"Curriculum pack must declare schema '{CURRICULUM_PACK_SCHEMA_VERSION}'."
        )
    try:
        pack = CurriculumPack.model_validate(raw)
    except Exception as exc:
        raise CurriculumCompilerError(f"Invalid curriculum pack: {exc}") from exc
    section_ids = [section.section_id for section in pack.sections]
    duplicate_sections = sorted({value for value in section_ids if section_ids.count(value) > 1})
    if duplicate_sections:
        raise CurriculumCompilerError("Duplicate curriculum-pack section_id values: " + ", ".join(duplicate_sections))
    item_ids = [item.item_id for section in pack.sections for item in section.items]
    duplicate_items = sorted({value for value in item_ids if item_ids.count(value) > 1})
    if duplicate_items:
        raise CurriculumCompilerError("Duplicate curriculum-pack item_id values: " + ", ".join(duplicate_items))
    test_ids = [test.test_id for section in pack.sections for test in section.tests]
    duplicate_tests = sorted({value for value in test_ids if test_ids.count(value) > 1})
    if duplicate_tests:
        raise CurriculumCompilerError("Duplicate curriculum-pack test_id values: " + ", ".join(duplicate_tests))
    return pack


def _merge_language_scaffolds(scaffolds: Iterable[LanguageScaffoldSpec]) -> LanguageScaffoldSpec:
    rules: list[str] = []
    lexicon: list[LanguageScaffoldLexeme] = []
    seen_rules: set[str] = set()
    seen_lexemes: set[bytes] = set()
    notes: list[str] = []
    for scaffold in scaffolds:
        for rule in scaffold.grammar_rules:
            if rule not in seen_rules:
                seen_rules.add(rule)
                rules.append(rule)
        for lexeme in scaffold.lexicon:
            key = _canonical_json_bytes(lexeme.model_dump(mode="json"))
            if key not in seen_lexemes:
                seen_lexemes.add(key)
                lexicon.append(lexeme)
        if scaffold.notes.strip():
            notes.append(scaffold.notes.strip())
    return LanguageScaffoldSpec(grammar_rules=tuple(rules), lexicon=tuple(lexicon), notes="\n".join(notes))


def flatten_curriculum_pack(
    pack: CurriculumPack,
    selected_section_ids: Iterable[str] = (),
) -> tuple[EditableTeachingBundle, tuple[CurriculumPackSection, ...], tuple[CurriculumPackProbe, ...]]:
    requested = tuple(dict.fromkeys(str(value) for value in selected_section_ids if str(value).strip()))
    by_id = {section.section_id: section for section in pack.sections}
    unknown = sorted(set(requested) - set(by_id))
    if unknown:
        raise CurriculumCompilerError("Unknown curriculum-pack section_id values: " + ", ".join(unknown))
    selected = tuple(by_id[value] for value in requested) if requested else tuple(section for section in pack.sections if section.enabled)
    if not selected:
        raise CurriculumCompilerError("Curriculum pack selection contains no enabled sections.")

    items: list[EditableTeachingItem] = []
    probes: list[CurriculumPackProbe] = []
    for section in selected:
        for item in section.items:
            provenance = dict(item.provenance)
            provenance["curriculum_pack"] = {
                "schema": CURRICULUM_PACK_SCHEMA_VERSION,
                "pack_title": pack.title,
                "section_id": section.section_id,
                "section_title": section.title,
            }
            items.append(item.model_copy(update={"provenance": provenance}))
        probes.extend(section.tests)

    scaffold = _merge_language_scaffolds((pack.language_scaffold, *(section.language_scaffold for section in selected)))
    bundle = EditableTeachingBundle(
        language_scaffold=scaffold,
        items=tuple(items),
        notes=(
            f"Flattened from {CURRICULUM_PACK_SCHEMA_VERSION}: {pack.title}; "
            f"sections={','.join(section.section_id for section in selected)}.\n{pack.notes}"
        ).strip(),
    )
    return bundle, selected, tuple(probes)


def curriculum_pack_bundle_source(
    pack_text: str,
    selected_section_ids: Iterable[str] = (),
) -> tuple[CurriculumPack, EditableTeachingBundle, tuple[CurriculumPackSection, ...], tuple[CurriculumPackProbe, ...], str]:
    pack = parse_curriculum_pack(pack_text)
    bundle, selected, probes = flatten_curriculum_pack(pack, selected_section_ids)
    source = json.dumps(bundle.model_dump(mode="json", by_alias=True), indent=2, ensure_ascii=False) + "\n"
    return pack, bundle, selected, probes, source


def curriculum_pack_selection_title(pack: CurriculumPack, selected: Iterable[CurriculumPackSection]) -> str:
    sections = tuple(selected)
    if len(sections) == len(pack.sections) and all(section.enabled for section in pack.sections):
        return pack.title
    labels = " + ".join(section.title for section in sections)
    return f"{pack.title} — {labels}"


def build_curriculum_package(result: CurriculumCompileResult) -> bytes:
    commands = tuple(ExperienceCommand.model_validate(item) for item in result.compiled_commands)
    compiled_jsonl = compiled_commands_jsonl(commands)
    ir = {
        "schema": CURRICULUM_SCHEMA_VERSION,
        "compiler_version": CURRICULUM_COMPILER_VERSION,
        "title": result.title,
        "source_format": result.source_format,
        "state_dim": result.state_dim,
        "source_sha256": result.source_sha256,
        "compiled_sha256": result.compiled_sha256,
        "item_count": result.item_count,
        "scaffold_item_count": result.scaffold_item_count,
        "language_scaffold": result.language_scaffold,
        "items": list(result.parsed_items),
    }
    ir_bytes = _canonical_json_bytes(ir)
    source_bytes = result.source_text.encode("utf-8")
    commands_bytes = compiled_jsonl.encode("utf-8")
    scaffold_bytes = _canonical_json_bytes(result.language_scaffold)
    hashes = {
        "source/source.txt": sha256_bytes(source_bytes),
        "curriculum_ir.json": sha256_bytes(ir_bytes),
        "compiled_commands.jsonl": sha256_bytes(commands_bytes),
        "language_scaffold.json": sha256_bytes(scaffold_bytes),
    }
    manifest = {
        "schema": CURRICULUM_SCHEMA_VERSION,
        "compiler_version": CURRICULUM_COMPILER_VERSION,
        "package_id": f"vcurr_{result.compiled_sha256[:24]}",
        "title": result.title,
        "source_format": result.source_format,
        "state_dim": result.state_dim,
        "source_sha256": result.source_sha256,
        "compiled_sha256": result.compiled_sha256,
        "item_count": result.item_count,
        "scaffold_item_count": result.scaffold_item_count,
    }
    hashes_bytes = _canonical_json_bytes(hashes)
    manifest_bytes = _canonical_json_bytes(manifest)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in (
            ("manifest.json", manifest_bytes),
            ("source/source.txt", source_bytes),
            ("curriculum_ir.json", ir_bytes),
            ("compiled_commands.jsonl", commands_bytes),
            ("language_scaffold.json", scaffold_bytes),
            ("hashes.json", hashes_bytes),
        ):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def read_curriculum_package(path: Path | str) -> CurriculumPackage:
    path = Path(path)
    with zipfile.ZipFile(path, "r") as archive:
        required = {"manifest.json", "source/source.txt", "curriculum_ir.json", "compiled_commands.jsonl", "hashes.json"}
        names = set(archive.namelist())
        missing = required - names
        if missing:
            raise CurriculumCompilerError("Curriculum package missing: " + ", ".join(sorted(missing)))
        manifest = json.loads(archive.read("manifest.json"))
        source_bytes = archive.read("source/source.txt")
        ir_bytes = archive.read("curriculum_ir.json")
        commands_bytes = archive.read("compiled_commands.jsonl")
        scaffold_bytes = archive.read("language_scaffold.json") if "language_scaffold.json" in names else b"{}"
        hashes = json.loads(archive.read("hashes.json"))
        for name, raw in (
            ("source/source.txt", source_bytes),
            ("curriculum_ir.json", ir_bytes),
            ("compiled_commands.jsonl", commands_bytes),
            ("language_scaffold.json", scaffold_bytes),
        ):
            actual = sha256_bytes(raw)
            expected = hashes.get(name)
            if expected is not None and actual != expected:
                raise CurriculumCompilerError(f"Curriculum internal integrity failure for {name}.")
        commands: list[ExperienceCommand] = []
        for line_no, line in enumerate(commands_bytes.decode("utf-8").splitlines(), start=1):
            if line.strip():
                try:
                    commands.append(ExperienceCommand.model_validate_json(line))
                except Exception as exc:
                    raise CurriculumCompilerError(f"Compiled command line {line_no} is invalid: {exc}") from exc
        language_scaffold = json.loads(scaffold_bytes)
        digest = compiled_commands_sha256(commands)
        if language_scaffold:
            digest = sha256_bytes(_canonical_json_bytes({
                "language_scaffold": language_scaffold,
                "compiled_commands": [command.model_dump(mode="json") for command in commands],
            }))
        if digest != manifest.get("compiled_sha256"):
            raise CurriculumCompilerError("Compiled curriculum digest does not match manifest.")
        return CurriculumPackage(
            manifest=manifest,
            source_text=source_bytes.decode("utf-8"),
            curriculum_ir=json.loads(ir_bytes),
            compiled_commands=tuple(commands),
            language_scaffold=language_scaffold,
            hashes=hashes,
        )
