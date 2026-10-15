"""Evaluate the frozen zero-new-lesson successor-retention cohort.

The exact v0.66 protocol and exact v0.65 response/evaluation history are
immutable inputs.  Four newly loaded private copies receive no teaching.  All
80 response/rejection records are saved before the unchanged external grader
can inspect the 48 valid original requests.  Reload validates the complete
native evidence without teaching, responding, walking or grading again.
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
from verdant_math.successor_repair_evaluation import evaluation as repair_evaluation
from verdant_math.successor_retention_protocol import protocol as retention_protocol

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_Role = Literal[
    "retained_repair", "no_repair_control", "valid_null", "wrong_link_control"
]
_ROLES = tuple(retention_protocol._ROLES)
_GROUPS = (
    "retained_prerequisite_control",
    "retained_partial_walk",
    "declared_domain_ceiling",
    "invalid_input",
)
_PROTOCOL_FILE_SHA256 = "d134d2762e293d7dd1374f59e8e9d5e89b584e4171b5a1748a2c7a3726c5b302"
_HISTORY_RESPONSE_FILE_SHA256 = "6f7fc01cfa4f380fd3b7f09e10fb0de4631cc1b5c1071823e59e864b6aad7f26"
_HISTORY_RESPONSE_RECEIPT_SHA256 = "c184c060a72e2e310ee1a929d54ccaa11bf0a0a3babe924f291c282f354dd31e"
_HISTORY_EVALUATION_FILE_SHA256 = "e704ee573b92f6bd9979502ae92d73f9f7f75a6928e1eb6e3a63d4900cfbea0f"
_HISTORY_EVALUATION_RECEIPT_SHA256 = "f7d9ee00425eaed98ef0e3f55d582d12aea60266d1053435e52b2493565a3b72"
_EVALUATION_VERSION = "teacher_scaffold_successor_retention_evaluation_v0.67"
_RUN_REFS = {
    "retained_repair": "math-v067:run:retained-repair",
    "no_repair_control": "math-v067:run:no-repair",
    # The valid null deliberately shares the record-local run ref so every
    # nested response can be byte-equal apart from its outer role label.
    "valid_null": "math-v067:run:retained-repair",
    "wrong_link_control": "math-v067:run:wrong-link",
}
_FALSE_FLAGS = (
    "new_successor_lesson_installed",
    "fresh_correct_answer_transfer_observed",
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
    "frozen_history_response_file_sha256": _HISTORY_RESPONSE_FILE_SHA256,
    "frozen_history_response_receipt_sha256": _HISTORY_RESPONSE_RECEIPT_SHA256,
    "frozen_history_evaluation_file_sha256": _HISTORY_EVALUATION_FILE_SHA256,
    "frozen_history_evaluation_receipt_sha256": _HISTORY_EVALUATION_RECEIPT_SHA256,
    "roles": _ROLES,
    "cases_per_role": 20,
    "valid_inputs_per_role": 12,
    "invalid_inputs_per_role": 8,
    "response_barrier": "immutable_80_record_batch_before_any_of_48_external_grades",
    "response_inputs": (
        "private_kernel_plus_role_run_case_provenance_and_original_raw_request_only;_"
        "no_group_freshness_history_effect_expected_answer_or_grade"
    ),
    "response_output": "complete_v064_route_and_nested_native_trace_or_typed_input_rejection",
    "scoring": (
        "exact_v058_left_plus_right_and_answer_classification_lifted_only_to_"
        "the_frozen_v064_bounded_request_type_after_saved_batch"
    ),
    "invalid_scoring": "eight_invalid_inputs_per_role_remain_visible_and_ungraded",
    "denominators": "20_enrolled_and_12_valid_per_role",
    "checkpoint_load": "exact_saved_v065_private_checkpoint_with_zero_new_lessons_exposures_or_claims",
    "null": "complete_retained_repair_and_valid_null_arms_equal_apart_from_outer_role",
    "persistence": "separate_immutable_response_batch_and_evaluation_bound_to_exact_bytes",
    "reload": "static_native_trace_and_grade_validation_without_response_or_grader_entry_points",
    "adaptation_replacement_or_feedback_permitted": False,
    "canonical_mutation_permitted": False,
    "attention_allocation_permitted": False,
    "obligation_simulation_permitted": False,
}


class SuccessorRetentionEvaluationIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The response barrier, native trace, grade, or frozen pairing changed."""


class Boundaries(FrozenRecord):
    new_successor_lesson_installed: StrictBool = False
    fresh_correct_answer_transfer_observed: StrictBool = False
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
                "Successor-retention evaluation grants no discovery, physical, or canonical authority."
            )
        return self


class InputRejection(FrozenRecord):
    location: tuple[StrictStr | StrictInt, ...]
    error_type: _Ref


class RetentionResponse(FrozenRecord):
    role: _Role
    case: retention_protocol.RetentionCase
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
    source_role: Literal[
        "taught_repair", "no_repair_control", "valid_null", "wrong_link_control"
    ]
    source_local_run_ref: _Ref
    local_run_ref: _Ref
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[counting.CountingLessonTrace, ...] = Field(min_length=29, max_length=29)
    responses: tuple[RetentionResponse, ...] = Field(min_length=20, max_length=20)

    @model_validator(mode="after")
    def check_arm(self):
        if (
            self.source_role != retention_protocol._SOURCE_ROLES[self.role]
            or self.local_run_ref != _RUN_REFS[self.role]
        ):
            raise ValueError("Response arm lost its frozen run reference.")
        if tuple(response.role for response in self.responses) != (self.role,) * 20:
            raise ValueError("Response arm contains a foreign role.")
        if tuple(response.case for response in self.responses) != retention_protocol._cases():
            raise ValueError("Response arm dropped, substituted, or reordered frozen cases.")
        return self


def _null_projection(arm: ResponseArm):
    raw = arm.model_dump(mode="json")
    raw["role"] = "retained_repair"
    raw["source_role"] = "taught_repair"
    for response in raw["responses"]:
        response["role"] = "retained_repair"
    return raw


class ResponseBatchReceipt(Boundaries):
    execution: dict
    frozen_protocol: retention_protocol.SuccessorRetentionProtocolEnvelope
    protocol_file_sha256: _Digest
    history_response_file_sha256: _Digest
    history_response_receipt_sha256: _Digest
    history_evaluation_file_sha256: _Digest
    history_evaluation_receipt_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    arms: tuple[ResponseArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["frozen_successor_retention_response_batch"] = (
        "frozen_successor_retention_response_batch"
    )
    exact_saved_checkpoints_loaded: Literal[True] = True
    new_successor_lessons_installed: Literal[0] = 0
    new_teacher_exposures: Literal[0] = 0
    new_claim_installations: Literal[0] = 0
    prospective_cohort_executed: Literal[True] = True
    prospective_responses_observed: Literal[True] = True
    evaluation_completed: Literal[False] = False

    @model_validator(mode="after")
    def check_receipt(self):
        if (
            canonical_json_bytes(self.execution) != canonical_json_bytes(_EXECUTION)
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or self.history_response_file_sha256 != _HISTORY_RESPONSE_FILE_SHA256
            or self.history_response_receipt_sha256 != _HISTORY_RESPONSE_RECEIPT_SHA256
            or self.history_evaluation_file_sha256 != _HISTORY_EVALUATION_FILE_SHA256
            or self.history_evaluation_receipt_sha256
            != _HISTORY_EVALUATION_RECEIPT_SHA256
            or tuple(arm.role for arm in self.arms) != _ROLES
        ):
            raise ValueError("Response batch lost its frozen inputs, roles, or execution contract.")
        if _null_projection(self.arms[0]) != _null_projection(self.arms[2]):
            raise ValueError("Complete retained-repair and exact-null response arms diverged.")
        if any(arm.lessons[:26] != self.arms[0].lessons[:26] for arm in self.arms):
            raise ValueError("Matched roles lost their identical 26-lesson prerequisite.")
        return self


class ResponseBatchEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-successor-retention-response-batch-v1"] = (
        "verdant-successor-retention-response-batch-v1"
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
            raise ValueError("Successor-retention response batch checksum mismatch.")
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
    history_response_file_sha256: _Digest
    history_response_receipt_sha256: _Digest
    history_evaluation_file_sha256: _Digest
    history_evaluation_receipt_sha256: _Digest
    response_batch_receipt_sha256: _Digest
    response_batch_file_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    grades: tuple[GradeRecord, ...] = Field(min_length=48, max_length=48)
    purpose: Literal["teacher_scaffold_successor_retention_evaluation"] = (
        "teacher_scaffold_successor_retention_evaluation"
    )
    prospective_cohort_executed: Literal[True] = True
    prospective_responses_observed: Literal[True] = True
    responses_durable_before_grading: Literal[True] = True
    invalid_inputs_retained_ungraded: Literal[True] = True
    retained_partial_trace_reuse_observed: Literal[True] = True
    evaluation_completed: Literal[True] = True

    @model_validator(mode="after")
    def check_receipt(self):
        if (
            canonical_json_bytes(self.execution) != canonical_json_bytes(_EXECUTION)
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or self.history_response_file_sha256 != _HISTORY_RESPONSE_FILE_SHA256
            or self.history_response_receipt_sha256 != _HISTORY_RESPONSE_RECEIPT_SHA256
            or self.history_evaluation_file_sha256 != _HISTORY_EVALUATION_FILE_SHA256
            or self.history_evaluation_receipt_sha256
            != _HISTORY_EVALUATION_RECEIPT_SHA256
            or tuple(grade.role for grade in self.grades)
            != tuple(role for role in _ROLES for _ in range(12))
        ):
            raise ValueError("Evaluation lost its frozen pairing, grade count, or role order.")
        return self


class EvaluationEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-successor-retention-evaluation-v1"] = (
        "verdant-successor-retention-evaluation-v1"
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
            raise ValueError("Successor-retention evaluation checksum mismatch.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Successor-retention evaluation input exceeds the size bound."
        )
    return data


def _parse(data):
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Successor-retention evaluation bytes must be canonical."
        )
    return raw


def _load_inputs(protocol_path, history_response_path, history_evaluation_path):
    protocol_data = _read(protocol_path)
    history_response_data = _read(history_response_path)
    history_evaluation_data = _read(history_evaluation_path)
    if baseline._sha(protocol_data) != _PROTOCOL_FILE_SHA256:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Evaluation requires the exact v0.66 protocol bytes."
        )
    if baseline._sha(history_response_data) != _HISTORY_RESPONSE_FILE_SHA256:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Evaluation requires the exact v0.65 response-history bytes."
        )
    if baseline._sha(history_evaluation_data) != _HISTORY_EVALUATION_FILE_SHA256:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Evaluation requires the exact v0.65 grade-history bytes."
        )
    protocol = retention_protocol.load_successor_retention_protocol(protocol_path)
    history_response = repair_evaluation.ResponseBatchEnvelope.model_validate(
        _parse(history_response_data)
    )
    history_evaluation = repair_evaluation.EvaluationEnvelope.model_validate(
        _parse(history_evaluation_data)
    )
    frozen_history = retention_protocol._validated_history()
    if (
        history_response.receipt_sha256 != _HISTORY_RESPONSE_RECEIPT_SHA256
        or history_evaluation.receipt_sha256 != _HISTORY_EVALUATION_RECEIPT_SHA256
        or history_response != frozen_history[3]
        or history_evaluation != frozen_history[4]
        or history_evaluation.receipt.response_batch_receipt_sha256
        != history_response.receipt_sha256
        or history_evaluation.receipt.response_batch_file_sha256
        != baseline._sha(history_response_data)
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Frozen retention protocol and v0.65 checkpoint history do not pair."
        )
    return (
        protocol_data,
        history_response_data,
        history_evaluation_data,
        protocol,
        history_response,
        history_evaluation,
    )


def _code_manifest(protocol):
    sources = {source.path: source for source in protocol.declaration.code_sources}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(
            path=name, sha256=baseline._sha(path.read_bytes())
        )
    return tuple(sources[name] for name in sorted(sources))


def _respond(kernel, *, role, local_run_ref, case_ref, raw_request_json):
    """Answer from only a private kernel, provenance, and the original raw request."""
    if role not in _ROLES or local_run_ref != _RUN_REFS[role]:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Behavioral response received foreign role or run provenance."
        )
    raw = json.loads(raw_request_json, object_pairs_hook=baseline._unique_object)
    try:
        bounded = retention_protocol.BoundedAdditionRequestV066.model_validate(raw)
        request = adapter.BoundedAdditionRequestV064.model_validate(
            bounded.model_dump(mode="json")
        )
    except ValidationError as exc:
        errors = tuple(
            InputRejection(location=error["loc"], error_type=error["type"])
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )
        )
        return None, None, errors
    reply = adapter.derive_successor_repaired_addition(
        kernel,
        request,
        local_run_ref=local_run_ref,
        case_ref=case_ref,
    )
    return request, reply, ()


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
        raise SuccessorRetentionEvaluationIntegrityError(
            "Lesson transition is absent from its private checkpoint."
        )
    if any(ref not in kernel.state.claims for ref in lesson.claim_refs):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Lesson claim is absent from its private checkpoint."
        )
    if any(ref not in kernel.state.evidence for ref in lesson.evidence_refs):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Lesson evidence is absent from its private checkpoint."
        )
    if not lesson.claim_refs:
        if lesson.object_label is not None:
            raise SuccessorRetentionEvaluationIntegrityError(
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
            raise SuccessorRetentionEvaluationIntegrityError(
                "Lesson trace does not match its native claim."
            )


def _validate_role_slots(kernel, source_role):
    try:
        repair_evaluation._validate_role_slots(kernel, source_role)
    except baseline.MathTeachingPilotIntegrityError as exc:
        raise SuccessorRetentionEvaluationIntegrityError(str(exc)) from exc


def _typed_request_and_errors(raw_request_json):
    raw = json.loads(raw_request_json, object_pairs_hook=baseline._unique_object)
    try:
        bounded = retention_protocol.BoundedAdditionRequestV066.model_validate(raw)
        return (
            adapter.BoundedAdditionRequestV064.model_validate(
                bounded.model_dump(mode="json")
            ),
            (),
        )
    except ValidationError as exc:
        return None, tuple(
            InputRejection(location=error["loc"], error_type=error["type"])
            for error in exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            )
        )


def _validate_batch(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    envelope,
):
    checked = ResponseBatchEnvelope.model_validate(envelope.model_dump(mode="json"))
    (
        protocol_data,
        history_response_data,
        history_evaluation_data,
        protocol,
        history_response,
        _history_evaluation,
    ) = _load_inputs(protocol_path, history_response_path, history_evaluation_path)
    receipt = checked.receipt
    if (
        receipt.frozen_protocol != protocol
        or receipt.protocol_file_sha256 != baseline._sha(protocol_data)
        or receipt.history_response_file_sha256 != baseline._sha(history_response_data)
        or receipt.history_evaluation_file_sha256
        != baseline._sha(history_evaluation_data)
        or receipt.code_sources != _code_manifest(protocol)
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Response batch history, source, code, or frozen protocol changed."
        )
    history_arms = {arm.role: arm for arm in history_response.receipt.arms}
    lineage = {
        item.future_role: item for item in protocol.declaration.checkpoint_lineage
    }
    for arm in receipt.arms:
        source = history_arms[arm.source_role]
        expected_lineage = lineage[arm.role]
        if (
            arm.source_local_run_ref != source.local_run_ref
            or arm.checkpoint_base64 != source.checkpoint_base64
            or arm.checkpoint_sha256 != source.checkpoint_sha256
            or arm.kernel_fingerprint != source.kernel_fingerprint
            or arm.lessons != source.lessons
            or expected_lineage.source_role != arm.source_role
            or expected_lineage.source_local_run_ref != arm.source_local_run_ref
            or expected_lineage.checkpoint_sha256 != arm.checkpoint_sha256
            or expected_lineage.kernel_fingerprint != arm.kernel_fingerprint
        ):
            raise SuccessorRetentionEvaluationIntegrityError(
                "Response arm changed its exact saved checkpoint or lesson lineage."
            )
        private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        before, snapshot = private.fingerprint(), private.snapshot()
        if (
            before != arm.kernel_fingerprint
            or checkpoint_bytes(snapshot) != base64.b64decode(arm.checkpoint_base64)
        ):
            raise SuccessorRetentionEvaluationIntegrityError(
                "Response arm private checkpoint failed exact reconstruction."
            )
        if adapter._order_instruction_trace(private).status != "valid":
            raise SuccessorRetentionEvaluationIntegrityError(
                "Every saved role must retain the exact correct order instruction."
            )
        _validate_role_slots(private, arm.source_role)
        for lesson in arm.lessons:
            _validate_lesson_closure(private, lesson)
        for response in arm.responses:
            request, errors = _typed_request_and_errors(
                response.case.raw_request_json
            )
            if request is None:
                if (
                    response.request is not None
                    or response.reply is not None
                    or response.input_errors != errors
                ):
                    raise SuccessorRetentionEvaluationIntegrityError(
                        "Typed input rejection failed static replay."
                    )
                continue
            if response.request != request or response.input_errors:
                raise SuccessorRetentionEvaluationIntegrityError(
                    "Valid response changed its original request boundary."
                )
            if response.reply != _static_repair_reply(private, response):
                raise SuccessorRetentionEvaluationIntegrityError(
                    "Stored native retention route or nested trace failed static replay."
                )
        if private.fingerprint() != before or private.snapshot() != snapshot:
            raise SuccessorRetentionEvaluationIntegrityError(
                "Static response validation changed a private checkpoint."
            )
    if (
        _read(protocol_path) != protocol_data
        or _read(history_response_path) != history_response_data
        or _read(history_evaluation_path) != history_evaluation_data
        or _code_manifest(protocol) != receipt.code_sources
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Frozen inputs or code changed during response validation."
        )
    return checked


def capture_successor_retention_responses(
    protocol_path,
    history_response_path,
    history_evaluation_path,
):
    """Load four exact saved checkpoints and return one complete ungraded batch."""
    (
        protocol_data,
        history_response_data,
        history_evaluation_data,
        protocol,
        history_response,
        _history_evaluation,
    ) = _load_inputs(protocol_path, history_response_path, history_evaluation_path)
    manifest, arms, privates = _code_manifest(protocol), [], []
    source_arms = {arm.role: arm for arm in history_response.receipt.arms}
    for role in _ROLES:
        source_role = retention_protocol._SOURCE_ROLES[role]
        source_arm = source_arms[source_role]
        private = baseline._checkpoint(
            source_arm.checkpoint_base64, source_arm.checkpoint_sha256
        )
        privates.append(private)
        before, snapshot = private.fingerprint(), private.snapshot()
        responses = []
        for case in protocol.declaration.cases:
            request, reply, errors = _respond(
                private,
                role=role,
                local_run_ref=_RUN_REFS[role],
                case_ref=case.case_id,
                raw_request_json=case.raw_request_json,
            )
            responses.append(
                RetentionResponse(
                    role=role,
                    case=case,
                    local_run_ref=_RUN_REFS[role],
                    case_ref=case.case_id,
                    request=request,
                    reply=reply,
                    input_errors=errors,
                )
            )
        if private.fingerprint() != before or private.snapshot() != snapshot:
            raise SuccessorRetentionEvaluationIntegrityError(
                "Retention responses changed a loaded private checkpoint."
            )
        arms.append(
            ResponseArm(
                role=role,
                source_role=source_role,
                source_local_run_ref=source_arm.local_run_ref,
                local_run_ref=_RUN_REFS[role],
                checkpoint_base64=source_arm.checkpoint_base64,
                checkpoint_sha256=source_arm.checkpoint_sha256,
                kernel_fingerprint=source_arm.kernel_fingerprint,
                lessons=source_arm.lessons,
                responses=tuple(responses),
            )
        )
    if len({id(private) for private in privates}) != 4:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Evaluation roles did not use four distinct private copies."
        )
    if (
        _read(protocol_path) != protocol_data
        or _read(history_response_path) != history_response_data
        or _read(history_evaluation_path) != history_evaluation_data
        or _code_manifest(protocol) != manifest
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Frozen protocol, history, or code changed during capture."
        )
    envelope = ResponseBatchEnvelope.build(
        ResponseBatchReceipt(
            execution=_EXECUTION,
            frozen_protocol=protocol,
            protocol_file_sha256=baseline._sha(protocol_data),
            history_response_file_sha256=baseline._sha(history_response_data),
            history_response_receipt_sha256=history_response.receipt_sha256,
            history_evaluation_file_sha256=baseline._sha(history_evaluation_data),
            history_evaluation_receipt_sha256=_HISTORY_EVALUATION_RECEIPT_SHA256,
            code_sources=manifest,
            arms=tuple(arms),
        )
    )
    return _validate_batch(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        envelope,
    )


def _protected_paths(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    receipt,
):
    paths = {
        Path(protocol_path).resolve(),
        Path(history_response_path).resolve(),
        Path(history_evaluation_path).resolve(),
    }
    paths.update((_ROOT / source.path).resolve() for source in receipt.code_sources)
    paths.update(
        (_ROOT / artifact.path).resolve()
        for artifact in receipt.frozen_protocol.declaration.prior_artifacts
    )
    paths.update(
        (_ROOT / source.path).resolve()
        for source in receipt.frozen_protocol.declaration.audit_sources
    )
    return paths


def save_response_batch(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
    envelope,
):
    checked = _validate_batch(
        protocol_path, history_response_path, history_evaluation_path, envelope
    )
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Successor-retention response batch exceeds the size bound."
        )
    if Path(response_path).resolve() in _protected_paths(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        checked.receipt,
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Cannot publish responses over frozen input, code, audit, or history."
        )
    baseline._write_immutable(Path(response_path), data)
    return baseline._sha(data)


def load_response_batch(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
):
    data = _read(response_path)
    return _validate_batch(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        ResponseBatchEnvelope.model_validate(_parse(data)),
    )


def _response_hash(response):
    return baseline._sha(canonical_json_bytes(response.model_dump(mode="json")))


def _external_grade(response):
    """Apply the unchanged v0.58 arithmetic/classification rule after capture."""
    if response.request is None or response.reply is None:
        raise SuccessorRetentionEvaluationIntegrityError(
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


def evaluate_response_batch(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
):
    """Grade only an already durable, exact response sidecar."""
    response_data = _read(response_path)
    batch = load_response_batch(
        protocol_path, history_response_path, history_evaluation_path, response_path
    )
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
            history_response_file_sha256=batch.receipt.history_response_file_sha256,
            history_response_receipt_sha256=batch.receipt.history_response_receipt_sha256,
            history_evaluation_file_sha256=batch.receipt.history_evaluation_file_sha256,
            history_evaluation_receipt_sha256=(
                batch.receipt.history_evaluation_receipt_sha256
            ),
            response_batch_receipt_sha256=batch.receipt_sha256,
            response_batch_file_sha256=baseline._sha(response_data),
            code_sources=batch.receipt.code_sources,
            grades=grades,
        )
    )
    return _validate_evaluation(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        response_path,
        envelope,
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


def _validate_evaluation(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
    envelope,
):
    checked = EvaluationEnvelope.model_validate(envelope.model_dump(mode="json"))
    response_data = _read(response_path)
    batch = load_response_batch(
        protocol_path, history_response_path, history_evaluation_path, response_path
    )
    receipt = checked.receipt
    if (
        receipt.response_batch_receipt_sha256 != batch.receipt_sha256
        or receipt.response_batch_file_sha256 != baseline._sha(response_data)
        or receipt.protocol_file_sha256 != batch.receipt.protocol_file_sha256
        or receipt.history_response_file_sha256
        != batch.receipt.history_response_file_sha256
        or receipt.history_response_receipt_sha256
        != batch.receipt.history_response_receipt_sha256
        or receipt.history_evaluation_file_sha256
        != batch.receipt.history_evaluation_file_sha256
        or receipt.history_evaluation_receipt_sha256
        != batch.receipt.history_evaluation_receipt_sha256
        or receipt.code_sources != batch.receipt.code_sources
        or receipt.grades != _expected_grades(batch)
    ):
        raise SuccessorRetentionEvaluationIntegrityError(
            "Evaluation grade, response, history, or protocol pairing changed."
        )
    return checked


def save_evaluation(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
    result_path,
    envelope,
):
    checked = _validate_evaluation(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        response_path,
        envelope,
    )
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Successor-retention evaluation exceeds the size bound."
        )
    batch = load_response_batch(
        protocol_path, history_response_path, history_evaluation_path, response_path
    )
    protected = _protected_paths(
        protocol_path,
        history_response_path,
        history_evaluation_path,
        batch.receipt,
    )
    protected.add(Path(response_path).resolve())
    if Path(result_path).resolve() in protected:
        raise SuccessorRetentionEvaluationIntegrityError(
            "Cannot publish evaluation over response, input, code, audit, or history."
        )
    baseline._write_immutable(Path(result_path), data)
    return baseline._sha(data)


def load_evaluation(
    protocol_path,
    history_response_path,
    history_evaluation_path,
    response_path,
    result_path,
):
    data = _read(result_path)
    return _validate_evaluation(
        protocol_path,
        history_response_path,
        history_evaluation_path,
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


def _step_pairs(response):
    if response.reply is None or response.reply.addition_reply is None:
        return ()
    counted = response.reply.addition_reply.counting_reply
    return tuple((step.from_number, step.to_number) for step in counted.steps)


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
    arms = {arm.role: arm for arm in batch.receipt.arms}
    retained = tuple(
        response
        for response in arms["retained_repair"].responses
        if response.case.group == "retained_partial_walk"
    )
    no_repair = tuple(
        response
        for response in arms["no_repair_control"].responses
        if response.case.group == "retained_partial_walk"
    )
    wrong = tuple(
        response
        for response in arms["wrong_link_control"].responses
        if response.case.group == "retained_partial_walk"
    )
    retained_reuse = (
        len(retained) == len(no_repair) == len(wrong) == 2
        and all(
            _step_pairs(response) == ((18, 19), (19, 20), (20, 21))
            and response.reply.answer is None
            and response.reply.addition_reply.counting_reply.reason
            == "missing_successor"
            for response in retained
        )
        and all(_step_pairs(response) == () for response in no_repair)
        and all(_step_pairs(response) == ((18, 20),) for response in wrong)
    )
    null_exact = _null_projection(batch.receipt.arms[0]) == _null_projection(
        batch.receipt.arms[2]
    )
    return {
        "status": "teacher_scaffold_successor_retention_evaluation",
        "protocol_declaration_sha256": batch.receipt.frozen_protocol.declaration_sha256,
        "history_response_receipt_sha256": batch.receipt.history_response_receipt_sha256,
        "history_evaluation_receipt_sha256": (
            batch.receipt.history_evaluation_receipt_sha256
        ),
        "response_batch_receipt_sha256": batch.receipt_sha256,
        "evaluation_receipt_sha256": evaluation.receipt_sha256,
        "responses": 80,
        "grades": 48,
        "enrolled_per_role": 20,
        "valid_inputs_per_role": 12,
        "new_successor_lessons_per_role": 0,
        "arms": by_role,
        "retained_null_exact": null_exact,
        "retained_partial_trace_reuse_observed": retained_reuse,
        **{name: False for name in _FALSE_FLAGS},
    }


