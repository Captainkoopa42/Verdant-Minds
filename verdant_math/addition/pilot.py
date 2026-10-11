"""Bind native operand testimony to the existing successor-counting scaffold.

The teacher supplies the mappings and instruction; dispatch is handwritten.
Only the separate, post-response evaluator performs numeric addition.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from cognitive_chunk_v2 import ExperienceInput, PipelineOrchestrator
from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, EvidenceKind, ExperienceCommand,
    VerdantKernel, checkpoint_bytes,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as counting

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _Number = baseline._Digest, baseline._Ref, baseline._Answer
_MAX_BYTES = baseline._MAX_BYTES
_LEFT = "math:rule:count_from_left_by_right"
_RIGHT = "math:rule:count_from_right_by_right"
_PROCEDURE = "math:procedure:addition"
_ROLES = counting._ROLES
# Teacher data, not a response lookup table. No composite answer is supplied.
_TOKEN_LESSONS = ((0, "math:tokens:empty"), (1, "math:tokens:tick"),
    (2, "math:tokens:tick,tick"), (3, "math:tokens:tick,tick,tick"),
    (4, "math:tokens:tick,tick,tick,tick"))
_CASES = ((9, 0), (10, 0), (11, 0), (12, 0),
          (9, 1), (10, 2), (11, 1), (12, 2),
          (9, 3), (9, 4), (10, 3), (10, 4), (11, 3), (11, 4), (12, 3), (12, 4))
_PROTOCOL = dict(
    version="teacher_scaffold_addition_v0.58", task="native_operand_to_counting_addition",
    source="fresh_seed_79058_state_dim_16_run_label_math-addition-v058",
    counting_prerequisite_version=counting._PROTOCOL["version"],
    teacher_successors=counting._SUCCESSORS, counting_instruction=counting._ONCE,
    teacher_operand_tokens=_TOKEN_LESSONS,
    correct_instruction=_LEFT, incorrect_instruction=_RIGHT,
    roles=_ROLES, ordered_cases=_CASES,
    excluded_v056_pairs=(*baseline._TRAINING, *baseline._HELD_OUT),
    excluded_v057_pairs=counting._CASES,
    groups="four_zero_identities_four_short_compositions_eight_held_out_compositions",
    teaching="19_reused_counting_lessons_5_native_token_mappings_1_addition_procedure_slot",
    no_rule_control="identical_first_24_lessons_and_final_prompt_without_addition_claim",
    valid_null="independent_exact_copy_of_taught_operations",
    incorrect_rule_control="native_rule_selects_right_operand_as_start_and_token_source",
    query="two_ordered_integers_0_to_18_without_answers_or_tokens",
    interpreter="handwritten_native_rule_dispatch_native_token_decode_existing_count_forward",
    scoring="external_left_plus_right_after_all_64_responses",
    missing_invalid_conflicting_or_cyclic="retain_as_abstention_without_partial_answer_credit",
    adaptation_or_replacement_permitted=False, canonical_input_mutation_permitted=False,
    simulation_execution=False, instruction_discovery_observed=False,
    interpretation="teacher_scaffold_addition_only_not_generalized_arithmetic",
)


class AdditionPilotIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The bounded addition scaffold or its native derivation lost lineage."""


class AdditionRequest(FrozenRecord):
    left: _Number
    right: _Number


class AdditionReply(FrozenRecord):
    status: Literal["derived", "abstained"]
    answer: _Number | None
    reason: Literal["teacher_scaffold_addition", "missing_addition_rule", "conflicting_addition_rule",
        "invalid_addition_rule", "unsupported_addition_rule", "missing_operand_tokens",
        "conflicting_operand_tokens", "invalid_operand_tokens", "counting_abstained"]
    instruction: Literal["count_from_left_by_right", "count_from_right_by_right"] | None
    start_operand: Literal["left_operand", "right_operand"] | None
    ticks_operand: Literal["right_operand"] | None
    addition_rule_claim_refs: tuple[_Ref, ...]
    addition_rule_evidence_refs: tuple[_Ref, ...]
    operand_claim_refs: tuple[_Ref, ...]
    operand_evidence_refs: tuple[_Ref, ...]
    counting_request: counting.CountingRequest | None
    counting_reply: counting.CountingReply | None

    @model_validator(mode="after")
    def check_reply(self):
        derived = self.status == "derived"
        if (derived != (self.answer is not None)
            or derived != (self.reason == "teacher_scaffold_addition")
            or (self.counting_request is None) != (self.counting_reply is None)
            or (self.instruction is None) != (self.start_operand is None)
            or (self.instruction is None) != (self.ticks_operand is None)
            or (derived and (self.counting_reply is None
                or self.counting_reply.status != "derived" or self.answer != self.counting_reply.answer
                or len(self.addition_rule_claim_refs) != 1 or not self.addition_rule_evidence_refs
                or len(self.operand_claim_refs) != 1 or not self.operand_evidence_refs))):
            raise ValueError("Addition reply lost its binding, derivation or abstention boundary.")
        for refs in (self.addition_rule_claim_refs, self.addition_rule_evidence_refs,
                     self.operand_claim_refs, self.operand_evidence_refs):
            if refs != tuple(sorted(set(refs))):
                raise ValueError("Addition evidence references must be complete and canonical.")
        return self


def _decode_tokens(label):
    if label == "math:tokens:empty":
        return ()
    if not label.startswith("math:tokens:"):
        raise ValueError("Unknown native operand token encoding.")
    tokens = tuple(label.removeprefix("math:tokens:").split(","))
    if not 1 <= len(tokens) <= 4 or any(t != "tick" for t in tokens):
        raise ValueError("Invalid or oversized native operand token encoding.")
    return tokens


def derive_addition(kernel: VerdantKernel, request: AdditionRequest) -> AdditionReply:
    """Read native bindings and token testimony, then follow native successors."""
    request = AdditionRequest.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    rule = counting._lookup(kernel, _PROCEDURE, "math_uses_addition_rule")
    instruction = start_operand = ticks_operand = operand = counted_request = counted_reply = None

    def reply(reason, answer=None):
        if kernel.fingerprint() != before:
            raise AdditionPilotIntegrityError("Addition changed its private kernel.")
        return AdditionReply(status="derived" if answer is not None else "abstained",
            answer=answer, reason=reason, instruction=instruction,
            start_operand=start_operand, ticks_operand=ticks_operand,
            addition_rule_claim_refs=rule.claim_refs, addition_rule_evidence_refs=rule.evidence_refs,
            operand_claim_refs=operand.claim_refs if operand else (),
            operand_evidence_refs=operand.evidence_refs if operand else (),
            counting_request=counted_request, counting_reply=counted_reply)

    if rule.status != "found":
        return reply(rule.status + "_addition_rule")
    if rule.label not in (_LEFT, _RIGHT):
        return reply("unsupported_addition_rule")
    instruction = rule.label.removeprefix("math:rule:")
    start_operand = "left_operand" if rule.label == _LEFT else "right_operand"
    ticks_operand = "right_operand"
    operand = counting._lookup(kernel, f"math:integer:{request.right}", "math_counting_tokens")
    if operand.status != "found":
        return reply(operand.status + "_operand_tokens")
    try:
        tokens = _decode_tokens(operand.label)
    except ValueError:
        return reply("invalid_operand_tokens")
    counted_request = counting.CountingRequest(
        start=request.left if start_operand == "left_operand" else request.right, ticks=tokens)
    counted_reply = counting.count_forward(kernel, counted_request)
    if counted_reply.answer is None:
        return reply("counting_abstained")
    return reply("teacher_scaffold_addition", answer=counted_reply.answer)


def verify_addition_derivation(kernel, request, reply):
    """Locally replay the exact operand binding and every native counting step."""
    checked = AdditionReply.model_validate(reply.model_dump(mode="json"))
    if checked != derive_addition(kernel, request):
        raise AdditionPilotIntegrityError("Addition derivation failed native replay.")


class AdditionObservation(FrozenRecord):
    case_id: _Ref
    split: Literal["zero_identity", "short_composition", "held_out_composition"]
    request: AdditionRequest
    reply: AdditionReply
    expected_answer: Annotated[StrictInt, Field(ge=0, le=36)]
    grade: Literal["correct", "incorrect", "abstained"]


class AdditionArm(FrozenRecord):
    role: Literal["taught", "no_rule_control", "valid_null", "incorrect_rule_control"]
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[counting.CountingLessonTrace, ...] = Field(min_length=25, max_length=25)
    observations: tuple[AdditionObservation, ...] = Field(min_length=16, max_length=16)


class AdditionPilotReceipt(FrozenRecord):
    protocol: dict
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    arms: tuple[AdditionArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["teacher_scaffold_addition_experiment"] = "teacher_scaffold_addition_experiment"
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
            raise ValueError("Addition pilot lost its frozen controls or claim boundaries.")
        return self


class AdditionPilotEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-scaffold-addition-pilot-v1"] = "verdant-scaffold-addition-pilot-v1"
    receipt: AdditionPilotReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = AdditionPilotReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.receipt_sha256 != baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Addition pilot receipt checksum mismatch.")
        return self


def _code_manifest():
    sources = {s.path: s for s in counting._code_manifest()}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = str(path.relative_to(_ROOT))
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_addition_kernel():
    return VerdantKernel(seed=79058, state_dim=16, run_label="math-addition-v058")


def _teach(kernel, role):
    # Reuse the existing native prerequisite, without modifying its code or receipt.
    traces, pipeline = list(counting._teach(kernel, "taught")), ClaimLearningPipeline()
    lessons = [(f"tokens:{number}", f"Teacher operand mapping: integer {number} is encoded as {target}.",
        f"math:integer:{number}", "math_counting_tokens", target) for number, target in _TOKEN_LESSONS]
    instruction = _RIGHT if role == "incorrect_rule_control" else _LEFT
    no_rule = role == "no_rule_control"
    text = ("Addition procedure slot: no rule supplied." if no_rule else
        "Teacher addition scaffold: start at the " + ("right" if instruction == _RIGHT else "left")
        + " operand and count once per token from the right operand's taught mapping.")
    lessons.append(("addition-rule", text, _PROCEDURE, "math_uses_addition_rule", None if no_rule else instruction))
    for key, text, subject, predicate, target in lessons:
        key, source = "math-v058:" + key, "declared-addition-teacher://v058"
        if target is not None:
            result = pipeline.record_claim(kernel, event_key=key, native_description=text,
                subject_label=subject, predicate=predicate, object_label=target,
                polarity=ClaimPolarity.AFFIRMED, source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                source_ref=source, rationale="Explicit teacher operand/procedure scaffold; no discovered algorithm.").kernel_result
        else:
            chunk, store = PipelineOrchestrator().process(ExperienceInput.from_text(
                text, source_id=source, source_name=f"{key}.txt"))
            payload, translation = chunk.payloads[0], chunk.translations[0]
            result = kernel.apply_experience(ExperienceCommand(event_key=key, source_ref=source,
                modality="text", payload_sha256=payload.source_sha256,
                feature_vector=tuple(float(v) for v in store.get_array(translation.feature_ref).reshape(-1)),
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={"source_class": "human_testimony", "addition_rule_supplied": False},
                metadata={"event_type": "addition_rule_prompt_only", "epistemic_status": "no_rule_supplied"}))
        traces.append(counting.CountingLessonTrace(event_key=key, native_description=text,
            subject_label=subject, predicate=predicate, object_label=target,
            transition_ref=result.transition_id, claim_refs=tuple(sorted(result.claim_ids)),
            evidence_refs=tuple(sorted((result.observation_evidence_id,
                result.translation_evidence_id, *result.additional_evidence_ids)))))
    return tuple(traces)


def _grade(index, request, reply):
    # This is the external evaluator, never an input to derive_addition.
    expected = request.left + request.right
    split = "zero_identity" if index < 4 else "short_composition" if index < 8 else "held_out_composition"
    return AdditionObservation(case_id=f"math-v058:case:{index}", split=split, request=request,
        reply=reply, expected_answer=expected,
        grade="abstained" if reply.answer is None else "correct" if reply.answer == expected else "incorrect")


def run_addition_pilot(kernel=None):
    source = fresh_addition_kernel() if kernel is None else kernel
    before = source.fingerprint()
    if before != fresh_addition_kernel().fingerprint():
        raise AdditionPilotIntegrityError("Addition pilot requires its fixed fresh unexposed source.")
    if set(_CASES) & set((*baseline._TRAINING, *baseline._HELD_OUT, *counting._CASES)):
        raise AdditionPilotIntegrityError("Addition cases reused consumed pilot pairs.")
    manifest, pending = _code_manifest(), []
    source_bytes = checkpoint_bytes(source.snapshot())
    for role in _ROLES:
        private = VerdantKernel.from_state(source.snapshot())
        lessons = _teach(private, role)
        private_before = private.fingerprint()
        requests = tuple(AdditionRequest(left=a, right=b) for a, b in _CASES)
        replies = tuple(derive_addition(private, r) for r in requests)
        if private.fingerprint() != private_before:
            raise AdditionPilotIntegrityError("Addition responses mutated their private memory.")
        pending.append((role, lessons, private_before, checkpoint_bytes(private.snapshot()), requests, replies))
    arms = []
    # All 64 responses are frozen before any external arithmetic grading.
    for role, lessons, fingerprint, data, requests, replies in pending:
        observations = tuple(_grade(i, q, r) for i, (q, r) in enumerate(zip(requests, replies)))
        arms.append(AdditionArm(role=role, checkpoint_base64=base64.b64encode(data).decode("ascii"),
            checkpoint_sha256=baseline._sha(data), kernel_fingerprint=fingerprint,
            lessons=lessons, observations=observations))
    if source.fingerprint() != before or _code_manifest() != manifest:
        raise AdditionPilotIntegrityError("Addition source or implementation changed during execution.")
    if arms[0].model_dump(exclude={"role"}) != arms[2].model_dump(exclude={"role"}):
        raise AdditionPilotIntegrityError("Addition exact valid-null result diverged.")
    return AdditionPilotEnvelope.build(AdditionPilotReceipt(protocol=_PROTOCOL,
        source_checkpoint_base64=base64.b64encode(source_bytes).decode("ascii"),
        source_checkpoint_sha256=baseline._sha(source_bytes), source_kernel_fingerprint=before,
        code_sources=manifest, arms=tuple(arms)))


def _validate_replay(envelope):
    envelope = AdditionPilotEnvelope.model_validate(envelope.model_dump(mode="json"))
    receipt = envelope.receipt
    if receipt.code_sources != _code_manifest():
        raise AdditionPilotIntegrityError("Addition implementation manifest changed.")
    source = baseline._checkpoint(receipt.source_checkpoint_base64, receipt.source_checkpoint_sha256)
    if source.fingerprint() != receipt.source_kernel_fingerprint:
        raise AdditionPilotIntegrityError("Addition source fingerprint mismatch.")
    for arm in receipt.arms:
        private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        if private.fingerprint() != arm.kernel_fingerprint:
            raise AdditionPilotIntegrityError("Addition arm fingerprint mismatch.")
        for o in arm.observations:
            verify_addition_derivation(private, o.request, o.reply)
    expected = run_addition_pilot(source)
    if canonical_json_bytes(expected.model_dump(mode="json")) != canonical_json_bytes(envelope.model_dump(mode="json")):
        raise AdditionPilotIntegrityError("Addition lessons, cases, grades or native execution failed replay.")


def save_addition_pilot(path, envelope):
    _validate_replay(envelope)
    data = canonical_json_bytes(envelope.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise AdditionPilotIntegrityError("Addition sidecar exceeds the size bound.")
    baseline._write_immutable(Path(path), data)
    return baseline._sha(data)


def load_addition_pilot(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise AdditionPilotIntegrityError("Addition sidecar exceeds the size bound.")
    envelope = AdditionPilotEnvelope.model_validate(json.loads(data, object_pairs_hook=baseline._unique_object))
    _validate_replay(envelope)
    return envelope


def restore_addition_arm(envelope, role="taught"):
    if role not in _ROLES:
        raise AdditionPilotIntegrityError("Unknown addition role.")
    _validate_replay(envelope)
    arm = next(a for a in envelope.receipt.arms if a.role == role)
    return baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def addition_summary(envelope):
    return dict(status="teacher_scaffold_addition_pilot", receipt_sha256=envelope.receipt_sha256,
        arms={a.role: {split: {grade: sum(o.grade == grade for o in a.observations if o.split == split)
            for grade in ("correct", "incorrect", "abstained")}
            for split in ("zero_identity", "short_composition", "held_out_composition")}
            for a in envelope.receipt.arms}, instruction_discovery_observed=False,
        generalized_arithmetic_claim_permitted=False, physical_evidence_admissible=False,
        canonical_commit_permitted=False)
