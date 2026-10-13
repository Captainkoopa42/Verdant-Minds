"""Execute the frozen terminal-successor cohort behind a durable grade barrier.

The exact v0.63 protocol and v0.64 adapter are immutable inputs.  All four
private roles and all 160 response/rejection records are captured and saved
before the versioned external evaluator can see a response.  Reload performs
static native-trace and grade validation without teaching, responding or
grading again.
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, ValidationError, model_validator

from verdant_kernel import checkpoint_bytes
from verdant_kernel.models import FrozenRecord, canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.successor_repair_adapter import adapter
from verdant_math.successor_repair_protocol import protocol as repair_protocol

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_Role = Literal[
    "taught_repair", "no_repair_control", "valid_null", "wrong_link_control"
]
_ROLES = tuple(repair_protocol._ROLES)
_GROUPS = tuple(repair_protocol._SPEC["prospective_groups"])
_PROTOCOL_FILE_SHA256 = "ee8f37cb145704fbb9ff753a5416b2ba473d276c96813a194465ca5960883081"
_IMPLEMENTATION_FILE_SHA256 = "397231910c27b8a429551e326fc11f880d3522466438de09a57534825be9d83d"
_IMPLEMENTATION_RECEIPT_SHA256 = "19e0363f65400308d49455b887ffb33dcdf7a3e0bbce93bc3bb0eadc320160c2"
_EVALUATION_VERSION = "teacher_scaffold_terminal_successor_evaluation_v0.65"
_RUN_REFS = {
    "taught_repair": "math-v065:run:correct-repair",
    "no_repair_control": "math-v065:run:no-repair",
    # The valid null deliberately shares the record-local run ref so every
    # nested response can be byte-equal apart from its outer role label.
    "valid_null": "math-v065:run:correct-repair",
    "wrong_link_control": "math-v065:run:wrong-link",
}
_FALSE_FLAGS = (
    "source_authenticated",
    "physical_evidence_admissible",
    "harm_scoring_implemented",
    "causal_self_repair_observed",
    "spontaneous_rule_discovery_observed",
    "generalized_arithmetic_claim_permitted",
    "mathematical_understanding_claim_permitted",
    "learning_efficiency_observed",
    "independent_replication_observed",
    "canonical_commit_permitted",
    "resolution_authority_enabled",
    "promotion_authority_enabled",
    "policy_rewrite_authority_enabled",
)
_EXECUTION = {
    "version": _EVALUATION_VERSION,
    "frozen_protocol_file_sha256": _PROTOCOL_FILE_SHA256,
    "frozen_implementation_file_sha256": _IMPLEMENTATION_FILE_SHA256,
    "frozen_implementation_receipt_sha256": _IMPLEMENTATION_RECEIPT_SHA256,
    "roles": _ROLES,
    "cases_per_role": 40,
    "valid_inputs_per_role": 32,
    "invalid_inputs_per_role": 8,
    "response_barrier": "immutable_160_record_batch_before_any_of_128_external_grades",
    "response_inputs": "original_raw_request_only_no_group_expected_answer_or_grade",
    "response_output": "complete_v064_route_and_nested_native_trace_or_typed_input_rejection",
    "scoring": (
        "exact_v058_left_plus_right_and_answer_classification_lifted_only_to_"
        "the_frozen_v064_bounded_request_type_after_saved_batch"
    ),
    "invalid_scoring": "eight_invalid_inputs_per_role_remain_visible_and_ungraded",
    "denominators": "40_enrolled_and_32_valid_per_role",
    "null": "complete_taught_repair_and_valid_null_arms_equal_apart_from_outer_role",
    "persistence": "separate_immutable_response_batch_and_evaluation_bound_to_exact_bytes",
    "reload": "static_native_trace_and_grade_validation_without_response_or_grader_entry_points",
    "adaptation_replacement_or_feedback_permitted": False,
    "canonical_mutation_permitted": False,
    "attention_allocation_permitted": False,
    "obligation_simulation_permitted": False,
}


class SuccessorRepairEvaluationIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The response barrier, native trace, grade, or frozen pairing changed."""


class Boundaries(FrozenRecord):
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    causal_self_repair_observed: StrictBool = False
    spontaneous_rule_discovery_observed: StrictBool = False
    generalized_arithmetic_claim_permitted: StrictBool = False
    mathematical_understanding_claim_permitted: StrictBool = False
    learning_efficiency_observed: StrictBool = False
    independent_replication_observed: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_boundaries(self):
        if any(getattr(self, name) for name in _FALSE_FLAGS):
            raise ValueError(
                "Terminal-successor evaluation grants no discovery, physical, or canonical authority."
            )
        return self


class InputRejection(FrozenRecord):
    location: tuple[StrictStr | StrictInt, ...]
    error_type: _Ref


class RepairResponse(FrozenRecord):
    role: _Role
    case: repair_protocol.RepairCase
    local_run_ref: _Ref
    case_ref: _Ref
    request: adapter.BoundedAdditionRequestV064 | None
    reply: adapter.SuccessorRepairReplyV064 | None
    input_errors: tuple[InputRejection, ...]

    @model_validator(mode="after")
    def check_response(self):
        if self.case_ref != self.case.case_id or self.local_run_ref != _RUN_REFS[self.role]:
            raise ValueError("Response lost its frozen role/run/case provenance.")
        rejected = self.request is None
        if rejected != (self.reply is None) or rejected != bool(self.input_errors):
            raise ValueError("Response lost its typed input-rejection boundary.")
        if self.reply is not None and (
            self.reply.original_request != self.request
            or self.reply.local_run_ref != self.local_run_ref
            or self.reply.case_ref != self.case_ref
        ):
            raise ValueError("Response lost its original request or adapter provenance.")
        return self


class ResponseArm(FrozenRecord):
    role: _Role
    local_run_ref: _Ref
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[counting.CountingLessonTrace, ...] = Field(min_length=29, max_length=29)
    responses: tuple[RepairResponse, ...] = Field(min_length=40, max_length=40)

    @model_validator(mode="after")
    def check_arm(self):
        if self.local_run_ref != _RUN_REFS[self.role]:
            raise ValueError("Response arm lost its frozen run reference.")
        if tuple(response.role for response in self.responses) != (self.role,) * 40:
            raise ValueError("Response arm contains a foreign role.")
        if tuple(response.case for response in self.responses) != repair_protocol._cases():
            raise ValueError("Response arm dropped, substituted, or reordered frozen cases.")
        return self


def _null_projection(arm: ResponseArm):
    raw = arm.model_dump(mode="json")
    raw["role"] = "taught_repair"
    for response in raw["responses"]:
        response["role"] = "taught_repair"
    return raw


class ResponseBatchReceipt(Boundaries):
    execution: dict
    frozen_protocol: repair_protocol.SuccessorRepairProtocolEnvelope
    protocol_file_sha256: _Digest
    frozen_implementation: adapter.RepairAdapterImplementationEnvelope
    implementation_file_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    arms: tuple[ResponseArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["frozen_terminal_successor_response_batch"] = (
        "frozen_terminal_successor_response_batch"
    )
    private_repair_testimony_installed: Literal[True] = True
    prospective_cohort_executed: Literal[True] = True
    prospective_responses_observed: Literal[True] = True
    evaluation_completed: Literal[False] = False

    @model_validator(mode="after")
    def check_receipt(self):
        if (
            canonical_json_bytes(self.execution) != canonical_json_bytes(_EXECUTION)
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or self.implementation_file_sha256 != _IMPLEMENTATION_FILE_SHA256
            or self.frozen_implementation.receipt_sha256 != _IMPLEMENTATION_RECEIPT_SHA256
            or self.frozen_implementation.receipt.frozen_protocol != self.frozen_protocol
            or tuple(arm.role for arm in self.arms) != _ROLES
        ):
            raise ValueError("Response batch lost its frozen inputs, roles, or execution contract.")
        if _null_projection(self.arms[0]) != _null_projection(self.arms[2]):
            raise ValueError("Complete taught-repair and exact-null response arms diverged.")
        if any(arm.lessons[:26] != self.arms[0].lessons[:26] for arm in self.arms):
            raise ValueError("Matched roles lost their identical 26-lesson prerequisite.")
        return self


class ResponseBatchEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-terminal-successor-response-batch-v1"] = (
        "verdant-terminal-successor-response-batch-v1"
    )
    receipt: ResponseBatchReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = ResponseBatchReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(
            receipt=checked,
            receipt_sha256=baseline._sha(
                canonical_json_bytes(checked.model_dump(mode="json"))
            ),
        )

    @model_validator(mode="after")
    def check_hash(self):
        expected = baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))
        if self.receipt_sha256 != expected:
            raise ValueError("Terminal-successor response batch checksum mismatch.")
        return self


class GradeRecord(FrozenRecord):
    role: _Role
    case_ref: _Ref
    original_request: adapter.BoundedAdditionRequestV064
    response_sha256: _Digest
    expected_answer: Annotated[StrictInt, Field(ge=0, le=42)]
    grade: Literal["correct", "incorrect", "abstained"]


class EvaluationReceipt(Boundaries):
    execution: dict
    protocol_file_sha256: _Digest
    implementation_file_sha256: _Digest
    response_batch_receipt_sha256: _Digest
    response_batch_file_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    grades: tuple[GradeRecord, ...] = Field(min_length=128, max_length=128)
    purpose: Literal["teacher_scaffold_terminal_successor_evaluation"] = (
        "teacher_scaffold_terminal_successor_evaluation"
    )
    prospective_cohort_executed: Literal[True] = True
    prospective_responses_observed: Literal[True] = True
    responses_durable_before_grading: Literal[True] = True
    invalid_inputs_retained_ungraded: Literal[True] = True
    evaluation_completed: Literal[True] = True

    @model_validator(mode="after")
    def check_receipt(self):
        if (
            canonical_json_bytes(self.execution) != canonical_json_bytes(_EXECUTION)
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or self.implementation_file_sha256 != _IMPLEMENTATION_FILE_SHA256
            or tuple(grade.role for grade in self.grades)
            != tuple(role for role in _ROLES for _ in range(32))
        ):
            raise ValueError("Evaluation lost its frozen pairing, grade count, or role order.")
        return self


class EvaluationEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-terminal-successor-evaluation-v1"] = (
        "verdant-terminal-successor-evaluation-v1"
    )
    receipt: EvaluationReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = EvaluationReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(
            receipt=checked,
            receipt_sha256=baseline._sha(
                canonical_json_bytes(checked.model_dump(mode="json"))
            ),
        )

    @model_validator(mode="after")
    def check_hash(self):
        expected = baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))
        if self.receipt_sha256 != expected:
            raise ValueError("Terminal-successor evaluation checksum mismatch.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairEvaluationIntegrityError(
            "Terminal-successor evaluation input exceeds the size bound."
        )
    return data


def _parse(data):
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise SuccessorRepairEvaluationIntegrityError(
            "Terminal-successor evaluation bytes must be canonical."
        )
    return raw


def _load_inputs(protocol_path, implementation_path):
    protocol_data = _read(protocol_path)
    implementation_data = _read(implementation_path)
    if baseline._sha(protocol_data) != _PROTOCOL_FILE_SHA256:
        raise SuccessorRepairEvaluationIntegrityError(
            "Evaluation requires the exact v0.63 protocol bytes."
        )
    if baseline._sha(implementation_data) != _IMPLEMENTATION_FILE_SHA256:
        raise SuccessorRepairEvaluationIntegrityError(
            "Evaluation requires the exact v0.64 implementation bytes."
        )
    protocol = repair_protocol.load_successor_repair_protocol(protocol_path)
    implementation = adapter.load_successor_repair_adapter(
        protocol_path, implementation_path
    )
    if (
        implementation.receipt_sha256 != _IMPLEMENTATION_RECEIPT_SHA256
        or implementation.receipt.frozen_protocol != protocol
    ):
        raise SuccessorRepairEvaluationIntegrityError(
            "Frozen repair protocol and adapter implementation do not pair."
        )
    return protocol_data, implementation_data, protocol, implementation


def _code_manifest(implementation):
    sources = {source.path: source for source in implementation.receipt.code_sources}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(
            path=name, sha256=baseline._sha(path.read_bytes())
        )
    return tuple(sources[name] for name in sorted(sources))


def _respond(kernel, role, case):
    raw = json.loads(case.raw_request_json, object_pairs_hook=baseline._unique_object)
    try:
        request = adapter.BoundedAdditionRequestV064.model_validate(raw)
    except ValidationError as exc:
        errors = tuple(
            InputRejection(location=error["loc"], error_type=error["type"])
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )
        )
        return RepairResponse(
            role=role,
            case=case,
            local_run_ref=_RUN_REFS[role],
            case_ref=case.case_id,
            request=None,
            reply=None,
            input_errors=errors,
        )
    reply = adapter.derive_successor_repaired_addition(
        kernel,
        request,
        local_run_ref=_RUN_REFS[role],
        case_ref=case.case_id,
    )
    return RepairResponse(
        role=role,
        case=case,
        local_run_ref=_RUN_REFS[role],
        case_ref=case.case_id,
        request=request,
        reply=reply,
        input_errors=(),
    )


def _static_counting_reply(kernel, request):
    request = adapter.BoundedCountingRequestV064.model_validate(
        request.model_dump(mode="json")
    )
    rule = counting._lookup(kernel, counting._PROCEDURE, "math_uses_counting_rule")
    instruction, steps = None, []

    def reply(reason, answer=None, blocked=None):
        return adapter.BoundedCountingReplyV064(
            status="derived" if answer is not None else "abstained",
            answer=answer,
            reason=reason,
            instruction=instruction,
            rule_claim_refs=rule.claim_refs,
            rule_evidence_refs=rule.evidence_refs,
            steps=tuple(steps),
            blocked_claim_refs=blocked.claim_refs if blocked else (),
            blocked_evidence_refs=blocked.evidence_refs if blocked else (),
        )

    if rule.status != "found":
        return reply(rule.status + "_rule")
    if rule.label not in (counting._ONCE, counting._TWICE):
        return reply("unsupported_rule")
    instruction = rule.label.removeprefix("math:rule:")
    applications = 1 if rule.label == counting._ONCE else 2
    current, visited = request.start, {request.start}
    for tick_index, _ in enumerate(request.ticks):
        for application_index in range(applications):
            edge = counting._lookup(
                kernel, f"math:integer:{current}", "math_successor"
            )
            if edge.status != "found":
                return reply(edge.status + "_successor", blocked=edge)
            match = re.fullmatch(r"math:integer:(0|[1-9]|1[0-9]|2[01])", edge.label)
            if not match:
                return reply("invalid_successor", blocked=edge)
            target = int(match[1])
            if target in visited:
                return reply("cyclic_successor", blocked=edge)
            steps.append(
                adapter.BoundedCountingStepV064(
                    tick_index=tick_index,
                    application_index=application_index,
                    from_number=current,
                    to_number=target,
                    claim_ref=edge.claim_refs[0],
                    evidence_refs=edge.evidence_refs,
                )
            )
            current = target
            visited.add(current)
    return reply("teacher_scaffold_walk", answer=current)


def _static_addition_reply(kernel, request):
    request = adapter.BoundedAdditionRequestV064.model_validate(
        request.model_dump(mode="json")
    )
    rule = counting._lookup(kernel, addition._PROCEDURE, "math_uses_addition_rule")
    instruction = start_operand = ticks_operand = operand = counted_request = counted_reply = None

    def reply(reason, answer=None):
        return adapter.BoundedAdditionReplyV064(
            status="derived" if answer is not None else "abstained",
            answer=answer,
            reason=reason,
            instruction=instruction,
            start_operand=start_operand,
            ticks_operand=ticks_operand,
            addition_rule_claim_refs=rule.claim_refs,
            addition_rule_evidence_refs=rule.evidence_refs,
            operand_claim_refs=operand.claim_refs if operand else (),
            operand_evidence_refs=operand.evidence_refs if operand else (),
            counting_request=counted_request,
            counting_reply=counted_reply,
        )

    if rule.status != "found":
        return reply(rule.status + "_addition_rule")
    if rule.label not in (addition._LEFT, addition._RIGHT):
        return reply("unsupported_addition_rule")
    instruction = rule.label.removeprefix("math:rule:")
    start_operand = "left_operand" if rule.label == addition._LEFT else "right_operand"
    ticks_operand = "right_operand"
    operand = counting._lookup(
        kernel, f"math:integer:{request.right}", "math_counting_tokens"
    )
    if operand.status != "found":
        return reply(operand.status + "_operand_tokens")
    try:
        tokens = addition._decode_tokens(operand.label)
    except ValueError:
        return reply("invalid_operand_tokens")
    counted_request = adapter.BoundedCountingRequestV064(
        start=request.left if start_operand == "left_operand" else request.right,
        ticks=tokens,
    )
    counted_reply = _static_counting_reply(kernel, counted_request)
    if counted_reply.answer is None:
        return reply("counting_abstained")
    return reply("teacher_scaffold_addition", answer=counted_reply.answer)


def _static_repair_reply(kernel, response):
    request = response.request
    instruction = adapter._order_instruction_trace(kernel)
    right = adapter._mapping_trace(kernel, request.right, "original_right")
    left = effective = nested = None
    if instruction.status != "valid":
        disposition = "blocked_order_instruction"
    elif right.status == "valid":
        disposition, effective = "kept_valid_original_right", request
    elif right.status == "missing":
        left = adapter._mapping_trace(kernel, request.left, "original_left")
        if left.status == "valid":
            disposition = "swapped_missing_original_right"
            effective = adapter.BoundedAdditionRequestV064(
                left=request.right, right=request.left
            )
        else:
            disposition = "blocked_original_left_mapping"
    else:
        disposition = "blocked_original_right_mapping"
    if effective is not None:
        nested = _static_addition_reply(kernel, effective)
    return adapter.SuccessorRepairReplyV064(
        local_run_ref=response.local_run_ref,
        case_ref=response.case_ref,
        private_kernel_fingerprint=kernel.fingerprint(),
        original_request=request,
        effective_request=effective,
        status=nested.status if nested is not None else "abstained",
        answer=nested.answer if nested is not None else None,
        route_disposition=disposition,
        order_instruction=instruction,
        original_right_lookup=right,
        original_left_lookup=left,
        addition_reply=nested,
    )


def _validate_lesson_closure(kernel, lesson):
    transition_ids = {transition.transition_id for transition in kernel.state.transitions}
    if lesson.transition_ref not in transition_ids:
        raise SuccessorRepairEvaluationIntegrityError(
            "Lesson transition is absent from its private checkpoint."
        )
    if any(ref not in kernel.state.claims for ref in lesson.claim_refs):
        raise SuccessorRepairEvaluationIntegrityError(
            "Lesson claim is absent from its private checkpoint."
        )
    if any(ref not in kernel.state.evidence for ref in lesson.evidence_refs):
        raise SuccessorRepairEvaluationIntegrityError(
            "Lesson evidence is absent from its private checkpoint."
        )
    if not lesson.claim_refs:
        if lesson.object_label is not None:
            raise SuccessorRepairEvaluationIntegrityError(
                "A prompt-only lesson cannot claim a successor object."
            )
        return
    for ref in lesson.claim_refs:
        claim = kernel.state.claims[ref]
        subject = kernel.state.concepts[claim.subject_concept_id].label
        target = kernel.state.concepts[claim.object_concept_id].label
        if (
            subject != lesson.subject_label
            or claim.predicate != lesson.predicate
            or target != lesson.object_label
        ):
            raise SuccessorRepairEvaluationIntegrityError(
                "Lesson trace does not match its native claim."
            )


def _validate_role_slots(kernel, role):
    expected = {
        "taught_repair": repair_protocol._CORRECT_SUCCESSORS,
        "valid_null": repair_protocol._CORRECT_SUCCESSORS,
        "no_repair_control": (),
        "wrong_link_control": repair_protocol._WRONG_SUCCESSORS,
    }[role]
    found = []
    for source in (18, 19, 20):
        match = counting._lookup(kernel, f"math:integer:{source}", "math_successor")
        if match.status == "found":
            found.append((source, int(match.label.removeprefix("math:integer:"))))
        elif match.status != "missing":
            raise SuccessorRepairEvaluationIntegrityError(
                "A private repair slot is neither exact testimony nor visibly missing."
            )
    if tuple(found) != tuple(expected):
        raise SuccessorRepairEvaluationIntegrityError(
            "Response arm contains the wrong terminal-successor testimony."
        )


def _validate_batch(protocol_path, implementation_path, envelope):
    checked = ResponseBatchEnvelope.model_validate(envelope.model_dump(mode="json"))
    protocol_data, implementation_data, protocol, implementation = _load_inputs(
        protocol_path, implementation_path
    )
    receipt = checked.receipt
    if (
        receipt.frozen_protocol != protocol
        or receipt.frozen_implementation != implementation
        or receipt.protocol_file_sha256 != baseline._sha(protocol_data)
        or receipt.implementation_file_sha256 != baseline._sha(implementation_data)
        or receipt.code_sources != _code_manifest(implementation)
    ):
        raise SuccessorRepairEvaluationIntegrityError(
            "Response batch source, code, or frozen inputs changed."
        )
    for arm in receipt.arms:
        private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        if private.fingerprint() != arm.kernel_fingerprint:
            raise SuccessorRepairEvaluationIntegrityError(
                "Response arm private fingerprint mismatch."
            )
        instruction = adapter._order_instruction_trace(private)
        if instruction.status != "valid":
            raise SuccessorRepairEvaluationIntegrityError(
                "Every response arm must retain the exact correct order instruction."
            )
        _validate_role_slots(private, arm.role)
        for lesson in arm.lessons:
            _validate_lesson_closure(private, lesson)
        for response in arm.responses:
            raw = json.loads(
                response.case.raw_request_json,
                object_pairs_hook=baseline._unique_object,
            )
            try:
                request = adapter.BoundedAdditionRequestV064.model_validate(raw)
            except ValidationError as exc:
                errors = tuple(
                    InputRejection(location=error["loc"], error_type=error["type"])
                    for error in exc.errors(
                        include_url=False,
                        include_context=False,
                        include_input=False,
                    )
                )
                if (
                    response.request is not None
                    or response.reply is not None
                    or response.input_errors != errors
                ):
                    raise SuccessorRepairEvaluationIntegrityError(
                        "Typed input rejection failed static replay."
                    )
                continue
            if response.request != request or response.input_errors:
                raise SuccessorRepairEvaluationIntegrityError(
                    "Valid response changed its original request boundary."
                )
            if response.reply != _static_repair_reply(private, response):
                raise SuccessorRepairEvaluationIntegrityError(
                    "Stored native repair route or nested trace failed static replay."
                )
    return checked


def capture_successor_repair_responses(protocol_path, implementation_path, source=None):
    """Execute all roles in memory and return one complete ungraded batch."""
    protocol_data, implementation_data, protocol, implementation = _load_inputs(
        protocol_path, implementation_path
    )
    source = (
        baseline._checkpoint(
            protocol.declaration.source_checkpoint_base64,
            protocol.declaration.source_checkpoint_sha256,
        )
        if source is None
        else source
    )
    before, snapshot = source.fingerprint(), source.snapshot()
    if before != protocol.declaration.source_kernel_fingerprint:
        raise SuccessorRepairEvaluationIntegrityError(
            "Evaluation requires the exact unexposed v0.63 source."
        )
    manifest, arms, privates = _code_manifest(implementation), [], []
    for role in _ROLES:
        private, lessons = adapter.prepare_private_successor_repair_kernel(role, source)
        privates.append(private)
        fingerprint = private.fingerprint()
        responses = tuple(
            _respond(private, role, case) for case in protocol.declaration.cases
        )
        if private.fingerprint() != fingerprint:
            raise SuccessorRepairEvaluationIntegrityError(
                "Terminal-successor responses changed private memory."
            )
        data = checkpoint_bytes(private.snapshot())
        arms.append(
            ResponseArm(
                role=role,
                local_run_ref=_RUN_REFS[role],
                checkpoint_base64=base64.b64encode(data).decode(),
                checkpoint_sha256=baseline._sha(data),
                kernel_fingerprint=fingerprint,
                lessons=lessons,
                responses=responses,
            )
        )
    if len({id(private) for private in privates}) != 4:
        raise SuccessorRepairEvaluationIntegrityError(
            "Evaluation roles did not use four distinct private copies."
        )
    if (
        source.fingerprint() != before
        or source.snapshot() != snapshot
        or _read(protocol_path) != protocol_data
        or _read(implementation_path) != implementation_data
        or _code_manifest(implementation) != manifest
    ):
        raise SuccessorRepairEvaluationIntegrityError(
            "Source, frozen inputs, or implementation changed during capture."
        )
    envelope = ResponseBatchEnvelope.build(
        ResponseBatchReceipt(
            execution=_EXECUTION,
            frozen_protocol=protocol,
            protocol_file_sha256=baseline._sha(protocol_data),
            frozen_implementation=implementation,
            implementation_file_sha256=baseline._sha(implementation_data),
            code_sources=manifest,
            arms=tuple(arms),
        )
    )
    return _validate_batch(protocol_path, implementation_path, envelope)


def _protected_paths(protocol_path, implementation_path, receipt):
    paths = {Path(protocol_path).resolve(), Path(implementation_path).resolve()}
    paths.update((_ROOT / source.path).resolve() for source in receipt.code_sources)
    paths.update(
        (_ROOT / artifact.path).resolve()
        for artifact in receipt.frozen_protocol.declaration.prior_artifacts
    )
    paths.update((_ROOT / source.path).resolve() for source in receipt.frozen_protocol.declaration.probe_sources)
    return paths


def save_response_batch(protocol_path, implementation_path, response_path, envelope):
    checked = _validate_batch(protocol_path, implementation_path, envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairEvaluationIntegrityError(
            "Terminal-successor response batch exceeds the size bound."
        )
    if Path(response_path).resolve() in _protected_paths(
        protocol_path, implementation_path, checked.receipt
    ):
        raise SuccessorRepairEvaluationIntegrityError(
            "Cannot publish responses over frozen input, code, probes, or history."
        )
    baseline._write_immutable(Path(response_path), data)
    return baseline._sha(data)


def load_response_batch(protocol_path, implementation_path, response_path):
    data = _read(response_path)
    return _validate_batch(
        protocol_path,
        implementation_path,
        ResponseBatchEnvelope.model_validate(_parse(data)),
    )


def _response_hash(response):
    return baseline._sha(canonical_json_bytes(response.model_dump(mode="json")))


def _external_grade(response):
    """Apply the unchanged v0.58 arithmetic/classification rule after capture."""
    if response.request is None or response.reply is None:
        raise SuccessorRepairEvaluationIntegrityError(
            "Invalid inputs cannot be externally graded."
        )
    expected = response.request.left + response.request.right
    answer = response.reply.answer
    grade = "abstained" if answer is None else "correct" if answer == expected else "incorrect"
    return GradeRecord(
        role=response.role,
        case_ref=response.case_ref,
        original_request=response.request,
        response_sha256=_response_hash(response),
        expected_answer=expected,
        grade=grade,
    )


def evaluate_response_batch(protocol_path, implementation_path, response_path):
    """Grade only an already durable, exact response sidecar."""
    response_data = _read(response_path)
    batch = load_response_batch(protocol_path, implementation_path, response_path)
    grades = tuple(
        _external_grade(response)
        for arm in batch.receipt.arms
        for response in arm.responses
        if response.request is not None
    )
    envelope = EvaluationEnvelope.build(
        EvaluationReceipt(
            execution=_EXECUTION,
            protocol_file_sha256=batch.receipt.protocol_file_sha256,
            implementation_file_sha256=batch.receipt.implementation_file_sha256,
            response_batch_receipt_sha256=batch.receipt_sha256,
            response_batch_file_sha256=baseline._sha(response_data),
            code_sources=batch.receipt.code_sources,
            grades=grades,
        )
    )
    return _validate_evaluation(
        protocol_path, implementation_path, response_path, envelope
    )


def _expected_grades(batch):
    result = []
    for arm in batch.receipt.arms:
        for response in arm.responses:
            if response.request is None:
                continue
            expected = response.request.left + response.request.right
            answer = response.reply.answer
            grade = (
                "abstained"
                if answer is None
                else "correct"
                if answer == expected
                else "incorrect"
            )
            result.append(
                GradeRecord(
                    role=arm.role,
                    case_ref=response.case_ref,
                    original_request=response.request,
                    response_sha256=_response_hash(response),
                    expected_answer=expected,
                    grade=grade,
                )
            )
    return tuple(result)


def _validate_evaluation(protocol_path, implementation_path, response_path, envelope):
    checked = EvaluationEnvelope.model_validate(envelope.model_dump(mode="json"))
    response_data = _read(response_path)
    batch = load_response_batch(protocol_path, implementation_path, response_path)
    receipt = checked.receipt
    if (
        receipt.response_batch_receipt_sha256 != batch.receipt_sha256
        or receipt.response_batch_file_sha256 != baseline._sha(response_data)
        or receipt.protocol_file_sha256 != batch.receipt.protocol_file_sha256
        or receipt.implementation_file_sha256 != batch.receipt.implementation_file_sha256
        or receipt.code_sources != batch.receipt.code_sources
        or receipt.grades != _expected_grades(batch)
    ):
        raise SuccessorRepairEvaluationIntegrityError(
            "Evaluation grade, response, or frozen-input pairing changed."
        )
    return checked


def save_evaluation(
    protocol_path,
    implementation_path,
    response_path,
    result_path,
    envelope,
):
    checked = _validate_evaluation(
        protocol_path, implementation_path, response_path, envelope
    )
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairEvaluationIntegrityError(
            "Terminal-successor evaluation exceeds the size bound."
        )
    batch = load_response_batch(protocol_path, implementation_path, response_path)
    protected = _protected_paths(protocol_path, implementation_path, batch.receipt)
    protected.add(Path(response_path).resolve())
    if Path(result_path).resolve() in protected:
        raise SuccessorRepairEvaluationIntegrityError(
            "Cannot publish evaluation over response, input, code, probes, or history."
        )
    baseline._write_immutable(Path(result_path), data)
    return baseline._sha(data)


def load_evaluation(protocol_path, implementation_path, response_path, result_path):
    data = _read(result_path)
    return _validate_evaluation(
        protocol_path,
        implementation_path,
        response_path,
        EvaluationEnvelope.model_validate(_parse(data)),
    )


def _counts(responses, grades):
    values = [
        "invalid_input" if response.request is None else grades[response.case_ref].grade
        for response in responses
    ]
    return {
        name: values.count(name)
        for name in ("correct", "incorrect", "abstained", "invalid_input")
    }


def evaluation_summary(batch, evaluation):
    by_role = {}
    for arm in batch.receipt.arms:
        grades = {
            grade.case_ref: grade
            for grade in evaluation.receipt.grades
            if grade.role == arm.role
        }
        by_role[arm.role] = {
            "total": _counts(arm.responses, grades),
            "groups": {
                group: _counts(
                    tuple(
                        response
                        for response in arm.responses
                        if response.case.group == group
                    ),
                    grades,
                )
                for group in _GROUPS
            },
        }
    taught_supported = by_role["taught_repair"]["groups"]["repair_supported"]["correct"]
    no_repair_supported = by_role["no_repair_control"]["groups"]["repair_supported"]["correct"]
    null_exact = _null_projection(batch.receipt.arms[0]) == _null_projection(
        batch.receipt.arms[2]
    )
    return {
        "status": "teacher_scaffold_terminal_successor_evaluation",
        "protocol_declaration_sha256": batch.receipt.frozen_protocol.declaration_sha256,
        "implementation_receipt_sha256": batch.receipt.frozen_implementation.receipt_sha256,
        "response_batch_receipt_sha256": batch.receipt_sha256,
        "evaluation_receipt_sha256": evaluation.receipt_sha256,
        "responses": 160,
        "grades": 128,
        "enrolled_per_role": 40,
        "valid_inputs_per_role": 32,
        "arms": by_role,
        "taught_null_exact": null_exact,
        "repair_supported_correct_delta_over_no_repair": (
            taught_supported - no_repair_supported
        ),
        "supplied_repair_effect_observed": (
            null_exact and taught_supported > no_repair_supported
        ),
        **{name: False for name in _FALSE_FLAGS},
    }
