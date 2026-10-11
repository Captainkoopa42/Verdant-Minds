"""Count by traversing native teacher-testimony successor links.

The interpreter and its two supported instructions are handwritten scaffolds.
Numeric answers come from native edge targets, never an arithmetic grader.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from cognitive_chunk_v2 import ExperienceInput, PipelineOrchestrator
from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, EvidenceKind, ExperienceCommand,
    VerdantKernel, checkpoint_bytes,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, normalize_label
from verdant_math import teaching_pilot as baseline

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _Number = baseline._Digest, baseline._Ref, baseline._Answer
_MAX_BYTES = baseline._MAX_BYTES
_ONCE = "math:rule:successor_once_per_tick"
_TWICE = "math:rule:successor_twice_per_tick"
_PROCEDURE = "math:procedure:count_forward"
_ROLES = ("taught", "no_rule_control", "valid_null", "incorrect_rule_control")
# Explicit teacher curriculum. The response interpreter never reads this table.
_SUCCESSORS = ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),
               (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 12),
               (12, 13), (13, 14), (14, 15), (15, 16), (16, 17), (17, 18))
_CASES = ((5, 1), (6, 1), (7, 1), (8, 1),
          (5, 2), (6, 2), (7, 2), (8, 2),
          (5, 3), (5, 4), (6, 3), (6, 4), (7, 3), (7, 4), (8, 3), (8, 4))
_PROTOCOL = dict(
    version="successor_counting_v0.57", task="follow_taught_successors_per_tick",
    teacher_successors=_SUCCESSORS, correct_instruction=_ONCE,
    incorrect_instruction=_TWICE, roles=_ROLES, ordered_cases=_CASES,
    excluded_v056_pairs=(*baseline._TRAINING, *baseline._HELD_OUT),
    groups="four_direct_successors_four_short_compositions_eight_held_out_compositions",
    source="fresh_seed_79057_state_dim_16_run_label_math-counting-v057",
    teaching="18_native_teacher_successor_claims_and_one_procedure_slot",
    no_rule_control="same_successor_facts_and_final_prompt_without_procedure_claim",
    valid_null="independent_exact_copy_of_taught_operations",
    interpreter="handwritten_bounded_instruction_dispatch_and_native_claim_walk",
    query="start_integer_and_zero_to_four_literal_tick_tokens_without_targets",
    scoring="external_start_plus_token_count_after_all_64_responses",
    missing_invalid_conflicting_or_cyclic="retain_as_abstention_without_partial_answer_credit",
    adaptation_or_replacement_permitted=False, canonical_input_mutation_permitted=False,
    simulation_execution=False, instruction_discovery_observed=False,
    interpretation="teacher_scaffold_composition_only_not_general_arithmetic",
)


class CountingPilotIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The bounded counting protocol or a derivation lost its native lineage."""


class CountingRequest(FrozenRecord):
    start: _Number
    ticks: tuple[Literal["tick"], ...] = Field(max_length=4)


class CountingStep(FrozenRecord):
    tick_index: Annotated[StrictInt, Field(ge=0, le=3)]
    application_index: Annotated[StrictInt, Field(ge=0, le=1)]
    from_number: _Number
    to_number: _Number
    claim_ref: _Ref
    evidence_refs: tuple[_Ref, ...] = Field(min_length=1)


class CountingReply(FrozenRecord):
    status: Literal["derived", "abstained"]
    answer: _Number | None
    reason: Literal["teacher_scaffold_walk", "missing_rule", "conflicting_rule", "invalid_rule",
        "unsupported_rule", "missing_successor", "conflicting_successor", "invalid_successor", "cyclic_successor"]
    instruction: Literal["successor_once_per_tick", "successor_twice_per_tick"] | None
    rule_claim_refs: tuple[_Ref, ...]
    rule_evidence_refs: tuple[_Ref, ...]
    steps: tuple[CountingStep, ...] = Field(max_length=8)
    blocked_claim_refs: tuple[_Ref, ...]
    blocked_evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_reply(self):
        if ((self.status == "derived") != (self.answer is not None)
            or (self.status == "derived") != (self.reason == "teacher_scaffold_walk")
            or (self.status == "derived" and (self.instruction is None
                or len(self.rule_claim_refs) != 1 or not self.rule_evidence_refs
                or self.blocked_claim_refs or self.blocked_evidence_refs))):
            raise ValueError("Counting reply lost its scaffold or abstention boundary.")
        for refs in (self.rule_claim_refs, self.rule_evidence_refs,
                     self.blocked_claim_refs, self.blocked_evidence_refs):
            if refs != tuple(sorted(set(refs))):
                raise ValueError("Counting evidence references must be complete and canonical.")
        return self


class _Match(NamedTuple):
    label: str | None
    status: str
    claim_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


def _lookup(kernel, subject, predicate):
    claims = tuple(sorted((c for c in kernel.state.claims.values()
        if kernel.state.concepts[c.subject_concept_id].normalized_label == normalize_label(subject)
        and c.predicate == predicate), key=lambda c: c.claim_id))
    refs = tuple(c.claim_id for c in claims)
    evidence = tuple(sorted({e.evidence_id for c in claims
        for e in (*c.support_ledger, *c.refutation_ledger)}))
    if not claims:
        return _Match(None, "missing", refs, evidence)
    if len(claims) != 1 or claims[0].polarity != ClaimPolarity.AFFIRMED:
        return _Match(None, "conflicting", refs, evidence)
    claim = claims[0]
    if (claim.net_score <= 0 or claim.refutation_ledger or not claim.support_ledger
        or any(e.source_class != ClaimSourceClass.HUMAN_TESTIMONY
            or e.evidence_id not in kernel.state.evidence
            or kernel.state.evidence[e.evidence_id].kind != EvidenceKind.TESTIMONY
            for e in claim.support_ledger)):
        return _Match(None, "invalid", refs, evidence)
    return _Match(kernel.state.concepts[claim.object_concept_id].label, "found", refs, evidence)


def count_forward(kernel: VerdantKernel, request: CountingRequest) -> CountingReply:
    """Execute a declared scaffold over native facts, without numeric addition."""
    request = CountingRequest.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    rule = _lookup(kernel, _PROCEDURE, "math_uses_counting_rule")
    instruction, steps = None, []

    def reply(reason, answer=None, blocked=None):
        if kernel.fingerprint() != before:
            raise CountingPilotIntegrityError("Counting changed its private kernel.")
        return CountingReply(status="derived" if answer is not None else "abstained",
            answer=answer, reason=reason, instruction=instruction,
            rule_claim_refs=rule.claim_refs, rule_evidence_refs=rule.evidence_refs,
            steps=tuple(steps), blocked_claim_refs=blocked.claim_refs if blocked else (),
            blocked_evidence_refs=blocked.evidence_refs if blocked else ())

    if rule.status != "found":
        return reply(rule.status + "_rule")
    if rule.label not in (_ONCE, _TWICE):
        return reply("unsupported_rule")
    instruction = rule.label.removeprefix("math:rule:")
    applications = 1 if rule.label == _ONCE else 2
    current, visited = request.start, {request.start}
    for tick_index, _ in enumerate(request.ticks):
        for application_index in range(applications):
            edge = _lookup(kernel, f"math:integer:{current}", "math_successor")
            if edge.status != "found":
                return reply(edge.status + "_successor", blocked=edge)
            match = re.fullmatch(r"math:integer:(0|[1-9]|1[0-8])", edge.label)
            if not match:
                return reply("invalid_successor", blocked=edge)
            target = int(match[1])
            if target in visited:
                return reply("cyclic_successor", blocked=edge)
            steps.append(CountingStep(tick_index=tick_index, application_index=application_index,
                from_number=current, to_number=target, claim_ref=edge.claim_refs[0],
                evidence_refs=edge.evidence_refs))
            current = target
            visited.add(current)
    return reply("teacher_scaffold_walk", answer=current)


def verify_counting_derivation(kernel, request, reply):
    """Check every stored trace field against read-only native execution replay."""
    checked = CountingReply.model_validate(reply.model_dump(mode="json"))
    if checked != count_forward(kernel, request):
        raise CountingPilotIntegrityError("Counting derivation failed native replay.")


class CountingLessonTrace(FrozenRecord):
    event_key: _Ref
    native_description: Annotated[StrictStr, Field(min_length=1, max_length=512)]
    subject_label: _Ref
    predicate: _Ref
    object_label: _Ref | None
    transition_ref: _Ref
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]


class CountingObservation(FrozenRecord):
    case_id: _Ref
    split: Literal["direct_successor", "short_composition", "held_out_composition"]
    request: CountingRequest
    reply: CountingReply
    expected_answer: Annotated[StrictInt, Field(ge=0, le=22)]
    grade: Literal["correct", "incorrect", "abstained"]


class CountingArm(FrozenRecord):
    role: Literal["taught", "no_rule_control", "valid_null", "incorrect_rule_control"]
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[CountingLessonTrace, ...] = Field(min_length=19, max_length=19)
    observations: tuple[CountingObservation, ...] = Field(min_length=16, max_length=16)


class CountingPilotReceipt(FrozenRecord):
    protocol: dict
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    arms: tuple[CountingArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["teacher_scaffold_counting_experiment"] = "teacher_scaffold_counting_experiment"
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    instruction_discovery_observed: StrictBool = False
    generalized_arithmetic_claim_permitted: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_protocol(self):
        flags = ("source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
                 "instruction_discovery_observed", "generalized_arithmetic_claim_permitted",
                 "canonical_commit_permitted", "resolution_authority_enabled", "promotion_authority_enabled",
                 "policy_rewrite_authority_enabled")
        if (canonical_json_bytes(self.protocol) != canonical_json_bytes(_PROTOCOL)
            or tuple(a.role for a in self.arms) != _ROLES or any(getattr(self, f) for f in flags)):
            raise ValueError("Counting pilot lost its frozen controls or claim boundaries.")
        return self


class CountingPilotEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-successor-counting-pilot-v1"] = "verdant-successor-counting-pilot-v1"
    receipt: CountingPilotReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = CountingPilotReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.receipt_sha256 != baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Counting pilot receipt checksum mismatch.")
        return self


def _code_manifest():
    sources = {s.path: s for s in baseline._code_manifest()}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = str(path.relative_to(_ROOT))
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_counting_kernel():
    return VerdantKernel(seed=79057, state_dim=16, run_label="math-counting-v057")


def _teach(kernel, role):
    traces, pipeline = [], ClaimLearningPipeline()
    lessons = [(f"successor:{a}", f"Teacher successor lesson: the next number after {a} is {b}.",
        f"math:integer:{a}", "math_successor", f"math:integer:{b}") for a, b in _SUCCESSORS]
    instruction = _TWICE if role == "incorrect_rule_control" else _ONCE
    no_rule = role == "no_rule_control"
    text = ("Counting procedure slot: no rule supplied." if no_rule else
        "Teacher counting rule: follow the taught successor "
        + ("twice" if instruction == _TWICE else "once") + " for every tick token.")
    lessons.append(("rule", text, _PROCEDURE, "math_uses_counting_rule", None if no_rule else instruction))
    for key, text, subject, predicate, target in lessons:
        key = "math-v057:" + key
        source = "declared-counting-teacher://v057"
        if target is not None:
            result = pipeline.record_claim(kernel, event_key=key, native_description=text,
                subject_label=subject, predicate=predicate, object_label=target,
                polarity=ClaimPolarity.AFFIRMED, source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                source_ref=source, rationale="Explicit teacher-supplied counting scaffold; no discovered rule.").kernel_result
        else:
            chunk, store = PipelineOrchestrator().process(ExperienceInput.from_text(
                text, source_id=source, source_name=f"{key}.txt"))
            payload, translation = chunk.payloads[0], chunk.translations[0]
            result = kernel.apply_experience(ExperienceCommand(event_key=key, source_ref=source,
                modality="text", payload_sha256=payload.source_sha256,
                feature_vector=tuple(float(v) for v in store.get_array(translation.feature_ref).reshape(-1)),
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={"source_class": "human_testimony", "rule_supplied": False},
                metadata={"event_type": "counting_rule_prompt_only", "epistemic_status": "no_rule_supplied"}))
        traces.append(CountingLessonTrace(event_key=key, native_description=text,
            subject_label=subject, predicate=predicate, object_label=target,
            transition_ref=result.transition_id, claim_refs=tuple(sorted(result.claim_ids)),
            evidence_refs=tuple(sorted((result.observation_evidence_id,
                result.translation_evidence_id, *result.additional_evidence_ids)))))
    return tuple(traces)


def _grade(index, request, reply):
    # External task criterion. This calculator is never invoked by count_forward.
    expected = request.start + len(request.ticks)
    split = "direct_successor" if index < 4 else "short_composition" if index < 8 else "held_out_composition"
    return CountingObservation(case_id=f"math-v057:case:{index}", split=split, request=request,
        reply=reply, expected_answer=expected,
        grade="abstained" if reply.answer is None else "correct" if reply.answer == expected else "incorrect")


def run_counting_pilot(kernel=None):
    source = fresh_counting_kernel() if kernel is None else kernel
    before = source.fingerprint()
    if before != fresh_counting_kernel().fingerprint():
        raise CountingPilotIntegrityError("Counting pilot requires its fixed fresh unexposed source.")
    manifest, pending = _code_manifest(), []
    if set(_CASES) & set((*baseline._TRAINING, *baseline._HELD_OUT)):
        raise CountingPilotIntegrityError("Counting cases reused consumed v0.56 pairs.")
    source_bytes = checkpoint_bytes(source.snapshot())
    for role in _ROLES:
        private = VerdantKernel.from_state(source.snapshot())
        lessons = _teach(private, role)
        private_before = private.fingerprint()
        requests = tuple(CountingRequest(start=a, ticks=("tick",) * n) for a, n in _CASES)
        replies = tuple(count_forward(private, r) for r in requests)
        if private.fingerprint() != private_before:
            raise CountingPilotIntegrityError("Counting responses mutated their private memory.")
        pending.append((role, lessons, private_before, checkpoint_bytes(private.snapshot()), requests, replies))
    arms = []
    # Freeze all 64 replies before any external grading or result publication.
    for role, lessons, fingerprint, data, requests, replies in pending:
        observations = tuple(_grade(i, q, r) for i, (q, r) in enumerate(zip(requests, replies)))
        arms.append(CountingArm(role=role, checkpoint_base64=base64.b64encode(data).decode("ascii"),
            checkpoint_sha256=baseline._sha(data), kernel_fingerprint=fingerprint,
            lessons=lessons, observations=observations))
    if source.fingerprint() != before or _code_manifest() != manifest:
        raise CountingPilotIntegrityError("Counting source or implementation changed during execution.")
    if arms[0].model_dump(exclude={"role"}) != arms[2].model_dump(exclude={"role"}):
        raise CountingPilotIntegrityError("Counting exact valid-null result diverged.")
    return CountingPilotEnvelope.build(CountingPilotReceipt(protocol=_PROTOCOL,
        source_checkpoint_base64=base64.b64encode(source_bytes).decode("ascii"),
        source_checkpoint_sha256=baseline._sha(source_bytes), source_kernel_fingerprint=before,
        code_sources=manifest, arms=tuple(arms)))


def _validate_replay(envelope):
    envelope = CountingPilotEnvelope.model_validate(envelope.model_dump(mode="json"))
    receipt = envelope.receipt
    if receipt.code_sources != _code_manifest():
        raise CountingPilotIntegrityError("Counting implementation manifest changed.")
    source = baseline._checkpoint(receipt.source_checkpoint_base64, receipt.source_checkpoint_sha256)
    if source.fingerprint() != receipt.source_kernel_fingerprint:
        raise CountingPilotIntegrityError("Counting source fingerprint mismatch.")
    for arm in receipt.arms:
        private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        if private.fingerprint() != arm.kernel_fingerprint:
            raise CountingPilotIntegrityError("Counting arm fingerprint mismatch.")
        for o in arm.observations:
            verify_counting_derivation(private, o.request, o.reply)
    expected = run_counting_pilot(source)
    if canonical_json_bytes(expected.model_dump(mode="json")) != canonical_json_bytes(envelope.model_dump(mode="json")):
        raise CountingPilotIntegrityError("Counting lessons, cases, grades or native execution failed replay.")


def save_counting_pilot(path, envelope):
    _validate_replay(envelope)
    data = canonical_json_bytes(envelope.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise CountingPilotIntegrityError("Counting sidecar exceeds the size bound.")
    baseline._write_immutable(Path(path), data)
    return baseline._sha(data)


def load_counting_pilot(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise CountingPilotIntegrityError("Counting sidecar exceeds the size bound.")
    envelope = CountingPilotEnvelope.model_validate(json.loads(data, object_pairs_hook=baseline._unique_object))
    _validate_replay(envelope)
    return envelope


def restore_counting_arm(envelope, role="taught"):
    if role not in _ROLES:
        raise CountingPilotIntegrityError("Unknown counting role.")
    _validate_replay(envelope)
    arm = next(a for a in envelope.receipt.arms if a.role == role)
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def counting_summary(envelope):
    return dict(status="teacher_scaffold_counting_pilot", receipt_sha256=envelope.receipt_sha256,
        arms={a.role: {split: {grade: sum(o.grade == grade for o in a.observations if o.split == split)
            for grade in ("correct", "incorrect", "abstained")}
            for split in ("direct_successor", "short_composition", "held_out_composition")}
            for a in envelope.receipt.arms}, instruction_discovery_observed=False,
        generalized_arithmetic_claim_permitted=False, physical_evidence_admissible=False,
        canonical_commit_permitted=False)
