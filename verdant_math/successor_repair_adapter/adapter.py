"""Private-copy terminal-successor repair for the frozen v0.63 protocol.

The three successor slots and every prerequisite are teacher supplied.  This
versioned sibling extends only the native request/reply bounds needed for 21;
it never changes the v0.57, v0.58 or v0.61 implementations and exposes no
prospective cohort runner or grader.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from cognitive_chunk_v2 import ExperienceInput, PipelineOrchestrator
from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity,
    ClaimSourceClass,
    EvidenceKind,
    ExperienceCommand,
    VerdantKernel,
)
from verdant_kernel.models import FrozenRecord, canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.ordering_adapter import adapter as ordering_adapter
from verdant_math.successor_repair_protocol import protocol as repair_protocol

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_BoundedNumber = Annotated[StrictInt, Field(ge=0, le=21)]
_ROLES = repair_protocol._ROLES
_CORRECT_SUCCESSORS = repair_protocol._CORRECT_SUCCESSORS
_WRONG_SUCCESSORS = repair_protocol._WRONG_SUCCESSORS
_TEACHER_SOURCE = repair_protocol._SPEC["declared_source"]
_ADAPTER_VERSION = "teacher_scaffold_terminal_successor_adapter_v0.64"
_PROTOCOL_DECLARATION_SHA256 = "b680c4b5eb50abd80b422df2cdf1ba8504af08045f9e1b7d52a99e68a8cfa98a"
_PROTOCOL_FILE_SHA256 = "ee8f37cb145704fbb9ff753a5416b2ba473d276c96813a194465ca5960883081"
_IMPLEMENTATION = dict(
    version=_ADAPTER_VERSION,
    frozen_protocol_declaration_sha256=_PROTOCOL_DECLARATION_SHA256,
    frozen_protocol_file_sha256=_PROTOCOL_FILE_SHA256,
    source="fresh_seed_79063_state_dim_16_run_label_math-successor-repair-v063",
    roles=_ROLES,
    bounded_domain="strict_native_request_answer_and_step_values_zero_through_twenty_one",
    shared_prerequisite=(
        "same_25_correct_v058_lessons_plus_same_correct_v061_operand_order_instruction_in_every_private_role"
    ),
    repair_slots="only_three_native_math_successor_claims_or_three_matched_prompt_slots",
    role_slots={
        "taught_repair": _CORRECT_SUCCESSORS,
        "valid_null": _CORRECT_SUCCESSORS,
        "no_repair_control": (None, None, None),
        "wrong_link_control": _WRONG_SUCCESSORS,
    },
    counting=(
        "versioned_read_only_native_walk_with_unchanged_once_per_tick_rule_and_visible_missing_or_blocked_edges"
    ),
    ordering=(
        "unchanged_correct_v061_route_valid_right_keeps_only_missing_right_plus_valid_left_swaps_once"
    ),
    trace=(
        "local_run_and_case_refs", "private_kernel_fingerprint", "original_and_effective_requests",
        "native_order_and_both_mapping_lookups", "addition_rule_and_operand_mapping",
        "counting_rule", "every_versioned_successor_step_claim_and_evidence_ref",
        "complete_partial_walk_and_blocking_lookup_refs",
    ),
    terminal_ceiling="math_integer_21_has_no_declared_successor_and_must_remain_visible_missing",
    prohibited=(
        "old_type_or_manifest_edit", "integer_successor_synthesis", "numeric_token_reconstruction",
        "sorting", "recursive_retry", "fallback_arithmetic", "case_or_group_behavioral_input",
        "expected_answer_or_external_grade_input", "canonical_mutation", "attention_allocation",
        "obligation_simulation",
    ),
    adapter_only="no_v063_prospective_response_grade_or_evaluation_in_this_increment",
)
_FALSE_FLAGS = (
    "prospective_repair_testimony_installed", "prospective_cohort_executed",
    "prospective_responses_observed", "evaluation_completed", "repair_effect_observed",
    "causal_self_repair_observed", "spontaneous_rule_discovery_observed",
    "generalized_arithmetic_claim_permitted", "mathematical_understanding_claim_permitted",
    "learning_efficiency_observed", "source_authenticated", "physical_evidence_admissible",
    "harm_scoring_implemented", "independent_replication_observed", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled",
)


class SuccessorRepairAdapterIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The private repair implementation, trace or protocol pairing changed."""


class BoundedCountingRequestV064(FrozenRecord):
    start: _BoundedNumber
    ticks: tuple[Literal["tick"], ...] = Field(max_length=4)


class BoundedCountingStepV064(FrozenRecord):
    tick_index: Annotated[StrictInt, Field(ge=0, le=3)]
    application_index: Annotated[StrictInt, Field(ge=0, le=1)]
    from_number: _BoundedNumber
    to_number: _BoundedNumber
    claim_ref: _Ref
    evidence_refs: tuple[_Ref, ...] = Field(min_length=1)


class BoundedCountingReplyV064(FrozenRecord):
    status: Literal["derived", "abstained"]
    answer: _BoundedNumber | None
    reason: Literal[
        "teacher_scaffold_walk", "missing_rule", "conflicting_rule", "invalid_rule",
        "unsupported_rule", "missing_successor", "conflicting_successor", "invalid_successor",
        "cyclic_successor",
    ]
    instruction: Literal["successor_once_per_tick", "successor_twice_per_tick"] | None
    rule_claim_refs: tuple[_Ref, ...]
    rule_evidence_refs: tuple[_Ref, ...]
    steps: tuple[BoundedCountingStepV064, ...] = Field(max_length=8)
    blocked_claim_refs: tuple[_Ref, ...]
    blocked_evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_reply(self):
        derived = self.status == "derived"
        if (
            derived != (self.answer is not None)
            or derived != (self.reason == "teacher_scaffold_walk")
            or (
                derived
                and (
                    self.instruction is None
                    or len(self.rule_claim_refs) != 1
                    or not self.rule_evidence_refs
                    or self.blocked_claim_refs
                    or self.blocked_evidence_refs
                )
            )
        ):
            raise ValueError("Bounded counting reply lost its scaffold or abstention boundary.")
        for refs in (
            self.rule_claim_refs,
            self.rule_evidence_refs,
            self.blocked_claim_refs,
            self.blocked_evidence_refs,
        ):
            if refs != tuple(sorted(set(refs))):
                raise ValueError("Bounded counting evidence references must be complete and canonical.")
        return self


def count_forward_bounded(kernel: VerdantKernel, request: BoundedCountingRequestV064):
    """Follow native testimony within 0..21 without deriving a successor from integers."""
    request = BoundedCountingRequestV064.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    rule = counting._lookup(kernel, counting._PROCEDURE, "math_uses_counting_rule")
    instruction, steps = None, []

    def reply(reason, answer=None, blocked=None):
        if kernel.fingerprint() != before:
            raise SuccessorRepairAdapterIntegrityError("Bounded counting changed its private kernel.")
        return BoundedCountingReplyV064(
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
            edge = counting._lookup(kernel, f"math:integer:{current}", "math_successor")
            if edge.status != "found":
                return reply(edge.status + "_successor", blocked=edge)
            match = re.fullmatch(r"math:integer:(0|[1-9]|1[0-9]|2[01])", edge.label)
            if not match:
                return reply("invalid_successor", blocked=edge)
            target = int(match[1])
            if target in visited:
                return reply("cyclic_successor", blocked=edge)
            steps.append(BoundedCountingStepV064(
                tick_index=tick_index,
                application_index=application_index,
                from_number=current,
                to_number=target,
                claim_ref=edge.claim_refs[0],
                evidence_refs=edge.evidence_refs,
            ))
            current = target
            visited.add(current)
    return reply("teacher_scaffold_walk", answer=current)


def verify_bounded_counting_derivation(kernel, request, reply):
    checked = BoundedCountingReplyV064.model_validate(reply.model_dump(mode="json"))
    if checked != count_forward_bounded(kernel, request):
        raise SuccessorRepairAdapterIntegrityError("Bounded counting trace failed exact native replay.")


class BoundedAdditionRequestV064(FrozenRecord):
    left: _BoundedNumber
    right: _BoundedNumber


class BoundedAdditionReplyV064(FrozenRecord):
    status: Literal["derived", "abstained"]
    answer: _BoundedNumber | None
    reason: Literal[
        "teacher_scaffold_addition", "missing_addition_rule", "conflicting_addition_rule",
        "invalid_addition_rule", "unsupported_addition_rule", "missing_operand_tokens",
        "conflicting_operand_tokens", "invalid_operand_tokens", "counting_abstained",
    ]
    instruction: Literal["count_from_left_by_right", "count_from_right_by_right"] | None
    start_operand: Literal["left_operand", "right_operand"] | None
    ticks_operand: Literal["right_operand"] | None
    addition_rule_claim_refs: tuple[_Ref, ...]
    addition_rule_evidence_refs: tuple[_Ref, ...]
    operand_claim_refs: tuple[_Ref, ...]
    operand_evidence_refs: tuple[_Ref, ...]
    counting_request: BoundedCountingRequestV064 | None
    counting_reply: BoundedCountingReplyV064 | None

    @model_validator(mode="after")
    def check_reply(self):
        derived = self.status == "derived"
        if (
            derived != (self.answer is not None)
            or derived != (self.reason == "teacher_scaffold_addition")
            or (self.counting_request is None) != (self.counting_reply is None)
            or (self.instruction is None) != (self.start_operand is None)
            or (self.instruction is None) != (self.ticks_operand is None)
            or (
                derived
                and (
                    self.counting_reply is None
                    or self.counting_reply.status != "derived"
                    or self.answer != self.counting_reply.answer
                    or len(self.addition_rule_claim_refs) != 1
                    or not self.addition_rule_evidence_refs
                    or len(self.operand_claim_refs) != 1
                    or not self.operand_evidence_refs
                )
            )
        ):
            raise ValueError("Bounded addition reply lost its binding or abstention boundary.")
        for refs in (
            self.addition_rule_claim_refs,
            self.addition_rule_evidence_refs,
            self.operand_claim_refs,
            self.operand_evidence_refs,
        ):
            if refs != tuple(sorted(set(refs))):
                raise ValueError("Bounded addition evidence references must be complete and canonical.")
        return self


def derive_bounded_addition(kernel: VerdantKernel, request: BoundedAdditionRequestV064):
    """Use old native rules with versioned 0..21 request and trace types."""
    request = BoundedAdditionRequestV064.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    rule = counting._lookup(kernel, addition._PROCEDURE, "math_uses_addition_rule")
    instruction = start_operand = ticks_operand = operand = counted_request = counted_reply = None

    def reply(reason, answer=None):
        if kernel.fingerprint() != before:
            raise SuccessorRepairAdapterIntegrityError("Bounded addition changed its private kernel.")
        return BoundedAdditionReplyV064(
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
    operand = counting._lookup(kernel, f"math:integer:{request.right}", "math_counting_tokens")
    if operand.status != "found":
        return reply(operand.status + "_operand_tokens")
    try:
        tokens = addition._decode_tokens(operand.label)
    except ValueError:
        return reply("invalid_operand_tokens")
    counted_request = BoundedCountingRequestV064(
        start=request.left if start_operand == "left_operand" else request.right,
        ticks=tokens,
    )
    counted_reply = count_forward_bounded(kernel, counted_request)
    if counted_reply.answer is None:
        return reply("counting_abstained")
    return reply("teacher_scaffold_addition", answer=counted_reply.answer)


def verify_bounded_addition_derivation(kernel, request, reply):
    checked = BoundedAdditionReplyV064.model_validate(reply.model_dump(mode="json"))
    if checked.counting_reply is not None:
        verify_bounded_counting_derivation(kernel, checked.counting_request, checked.counting_reply)
    if checked != derive_bounded_addition(kernel, request):
        raise SuccessorRepairAdapterIntegrityError("Bounded addition trace failed exact native replay.")


class NativeOrderInstructionTraceV064(FrozenRecord):
    status: Literal["missing", "conflicting", "invalid", "unsupported", "valid"]
    label: StrictStr | None
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_trace(self):
        if (
            self.claim_refs != tuple(sorted(set(self.claim_refs)))
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("Order provenance must be complete and canonical.")
        if self.status == "missing":
            if self.label is not None or self.claim_refs or self.evidence_refs:
                raise ValueError("A missing order instruction cannot invent provenance.")
        elif self.status == "valid":
            if (
                self.label != ordering_adapter._CORRECT
                or len(self.claim_refs) != 1
                or not self.evidence_refs
            ):
                raise ValueError("A valid v0.64 order instruction must be the frozen correct rule.")
        elif self.status == "unsupported":
            if self.label is None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Unsupported order testimony must remain visible.")
        elif self.label is not None or not self.claim_refs or not self.evidence_refs:
            raise ValueError("Blocked order testimony lost its native provenance.")
        return self


class NativeMappingTraceV064(FrozenRecord):
    operand_role: Literal["original_right", "original_left"]
    operand: _BoundedNumber
    status: Literal["missing", "conflicting", "invalid", "unsupported", "valid"]
    label: StrictStr | None
    tokens: tuple[Literal["tick"], ...] | None = Field(default=None, max_length=4)
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_trace(self):
        if (
            self.claim_refs != tuple(sorted(set(self.claim_refs)))
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
        ):
            raise ValueError("Operand mapping provenance must be complete and canonical.")
        if self.status == "missing":
            if self.label is not None or self.tokens is not None or self.claim_refs or self.evidence_refs:
                raise ValueError("A missing operand mapping cannot invent evidence.")
        elif self.status == "valid":
            if (
                self.label is None
                or self.tokens is None
                or len(self.claim_refs) != 1
                or not self.evidence_refs
            ):
                raise ValueError("A valid operand mapping needs decoded native testimony.")
        elif self.status == "unsupported":
            if self.label is None or self.tokens is not None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Unsupported operand testimony must remain visible.")
        elif self.status == "invalid":
            if self.tokens is not None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Invalid operand testimony lost its native provenance.")
        elif self.label is not None or self.tokens is not None or not self.claim_refs or not self.evidence_refs:
            raise ValueError("Conflicting operand testimony lost its native provenance.")
        return self


def _order_instruction_trace(kernel):
    match = counting._lookup(
        kernel,
        ordering_adapter._PROCEDURE,
        ordering_adapter._PREDICATE,
    )
    if match.status != "found":
        return NativeOrderInstructionTraceV064(
            status=match.status,
            label=None,
            claim_refs=match.claim_refs,
            evidence_refs=match.evidence_refs,
        )
    status = "valid" if match.label == ordering_adapter._CORRECT else "unsupported"
    return NativeOrderInstructionTraceV064(
        status=status,
        label=match.label,
        claim_refs=match.claim_refs,
        evidence_refs=match.evidence_refs,
    )


def _mapping_trace(kernel, operand, role):
    match = counting._lookup(kernel, f"math:integer:{operand}", "math_counting_tokens")
    if match.status != "found":
        return NativeMappingTraceV064(
            operand_role=role,
            operand=operand,
            status=match.status,
            label=None,
            tokens=None,
            claim_refs=match.claim_refs,
            evidence_refs=match.evidence_refs,
        )
    try:
        tokens = addition._decode_tokens(match.label)
    except ValueError:
        status = "invalid" if match.label.startswith("math:tokens:") else "unsupported"
        return NativeMappingTraceV064(
            operand_role=role,
            operand=operand,
            status=status,
            label=match.label,
            tokens=None,
            claim_refs=match.claim_refs,
            evidence_refs=match.evidence_refs,
        )
    return NativeMappingTraceV064(
        operand_role=role,
        operand=operand,
        status="valid",
        label=match.label,
        tokens=tokens,
        claim_refs=match.claim_refs,
        evidence_refs=match.evidence_refs,
    )


_BLOCKED_ROUTES = (
    "blocked_order_instruction",
    "blocked_original_right_mapping",
    "blocked_original_left_mapping",
)


class SuccessorRepairReplyV064(FrozenRecord):
    adapter_version: Literal["teacher_scaffold_terminal_successor_adapter_v0.64"] = _ADAPTER_VERSION
    protocol_declaration_sha256: _Digest = _PROTOCOL_DECLARATION_SHA256
    local_run_ref: _Ref
    case_ref: _Ref
    private_kernel_fingerprint: _Digest
    original_request: BoundedAdditionRequestV064
    effective_request: BoundedAdditionRequestV064 | None
    status: Literal["derived", "abstained"]
    answer: _BoundedNumber | None
    route_disposition: Literal[
        "kept_valid_original_right",
        "swapped_missing_original_right",
        "blocked_order_instruction",
        "blocked_original_right_mapping",
        "blocked_original_left_mapping",
    ]
    order_instruction: NativeOrderInstructionTraceV064
    original_right_lookup: NativeMappingTraceV064
    original_left_lookup: NativeMappingTraceV064 | None
    addition_reply: BoundedAdditionReplyV064 | None

    @model_validator(mode="after")
    def check_reply(self):
        if (
            self.original_right_lookup.operand_role != "original_right"
            or self.original_right_lookup.operand != self.original_request.right
        ):
            raise ValueError("The original-right lookup lost its request binding.")
        if self.original_left_lookup is not None and (
            self.original_left_lookup.operand_role != "original_left"
            or self.original_left_lookup.operand != self.original_request.left
        ):
            raise ValueError("The original-left lookup lost its request binding.")
        if self.route_disposition in _BLOCKED_ROUTES:
            if (
                self.effective_request is not None
                or self.addition_reply is not None
                or self.status != "abstained"
                or self.answer is not None
            ):
                raise ValueError("A blocked repair route cannot fabricate an addition reply.")
        else:
            if self.effective_request is None or self.addition_reply is None:
                raise ValueError("A dispatched repair route must retain the complete nested reply.")
            expected = (
                BoundedAdditionRequestV064(
                    left=self.original_request.right,
                    right=self.original_request.left,
                )
                if self.route_disposition == "swapped_missing_original_right"
                else self.original_request
            )
            if self.effective_request != expected:
                raise ValueError("The effective request is not the original or one transposition.")
            if self.answer != self.addition_reply.answer or self.status != self.addition_reply.status:
                raise ValueError("The repair reply cannot reinterpret its nested addition reply.")
        if (self.status == "derived") != (self.answer is not None):
            raise ValueError("A repair reply cannot award partial answer credit.")
        if self.route_disposition == "swapped_missing_original_right":
            if (
                self.order_instruction.status != "valid"
                or self.original_right_lookup.status != "missing"
                or self.original_left_lookup is None
                or self.original_left_lookup.status != "valid"
            ):
                raise ValueError("The swap lost its absent-right and valid-left authorization.")
        elif self.route_disposition == "kept_valid_original_right":
            if self.order_instruction.status != "valid" or self.original_right_lookup.status != "valid":
                raise ValueError("The keep route requires the exact order rule and valid right mapping.")
        return self


def derive_successor_repaired_addition(
    kernel: VerdantKernel,
    request: BoundedAdditionRequestV064,
    *,
    local_run_ref: str,
    case_ref: str,
):
    """Route and execute one typed request once against a private repaired copy."""
    request = BoundedAdditionRequestV064.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    instruction = _order_instruction_trace(kernel)
    right = _mapping_trace(kernel, request.right, "original_right")
    left = None
    effective = None
    nested = None
    if instruction.status != "valid":
        disposition = "blocked_order_instruction"
    elif right.status == "valid":
        disposition = "kept_valid_original_right"
        effective = request
    elif right.status == "missing":
        left = _mapping_trace(kernel, request.left, "original_left")
        if left.status == "valid":
            disposition = "swapped_missing_original_right"
            effective = BoundedAdditionRequestV064(left=request.right, right=request.left)
        else:
            disposition = "blocked_original_left_mapping"
    else:
        disposition = "blocked_original_right_mapping"
    if effective is not None:
        nested = derive_bounded_addition(kernel, effective)
    if kernel.fingerprint() != before:
        raise SuccessorRepairAdapterIntegrityError("Repair routing changed its private kernel.")
    return SuccessorRepairReplyV064(
        local_run_ref=local_run_ref,
        case_ref=case_ref,
        private_kernel_fingerprint=before,
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


def verify_successor_repair_derivation(kernel, request, reply):
    checked = SuccessorRepairReplyV064.model_validate(reply.model_dump(mode="json"))
    if checked.private_kernel_fingerprint != kernel.fingerprint():
        raise SuccessorRepairAdapterIntegrityError("Repair trace belongs to another private kernel.")
    if checked.addition_reply is not None:
        verify_bounded_addition_derivation(kernel, checked.effective_request, checked.addition_reply)
    expected = derive_successor_repaired_addition(
        kernel,
        request,
        local_run_ref=checked.local_run_ref,
        case_ref=checked.case_ref,
    )
    if checked != expected:
        raise SuccessorRepairAdapterIntegrityError("Repair trace failed exact native replay.")


def _install_repair_slots(kernel: VerdantKernel, role: str):
    pipeline = ClaimLearningPipeline()
    links = {
        "taught_repair": _CORRECT_SUCCESSORS,
        "valid_null": _CORRECT_SUCCESSORS,
        "no_repair_control": ((18, None), (19, None), (20, None)),
        "wrong_link_control": _WRONG_SUCCESSORS,
    }[role]
    traces = []
    for source_number, target_number in links:
        key = f"math-v064:successor-slot:{source_number}"
        subject = f"math:integer:{source_number}"
        text = (
            f"Terminal-successor slot for {source_number}: no repair testimony supplied."
            if target_number is None
            else f"Teacher terminal-successor lesson: the next number after {source_number} is {target_number}."
        )
        target = None if target_number is None else f"math:integer:{target_number}"
        if target is not None:
            result = pipeline.record_claim(
                kernel,
                event_key=key,
                native_description=text,
                subject_label=subject,
                predicate="math_successor",
                object_label=target,
                polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.HUMAN_TESTIMONY,
                source_ref=_TEACHER_SOURCE,
                rationale="Explicit private teacher repair testimony; no discovered successor rule.",
            ).kernel_result
        else:
            chunk, store = PipelineOrchestrator().process(ExperienceInput.from_text(
                text,
                source_id=_TEACHER_SOURCE,
                source_name=f"{key}.txt",
            ))
            payload, translation = chunk.payloads[0], chunk.translations[0]
            result = kernel.apply_experience(ExperienceCommand(
                event_key=key,
                source_ref=_TEACHER_SOURCE,
                modality="text",
                payload_sha256=payload.source_sha256,
                feature_vector=tuple(float(value) for value in store.get_array(
                    translation.feature_ref
                ).reshape(-1)),
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={
                    "source_class": "human_testimony",
                    "terminal_successor_repair_supplied": False,
                },
                metadata={
                    "event_type": "terminal_successor_repair_prompt_only",
                    "epistemic_status": "no_repair_supplied",
                },
            ))
        traces.append(counting.CountingLessonTrace(
            event_key=key,
            native_description=text,
            subject_label=subject,
            predicate="math_successor",
            object_label=target,
            transition_ref=result.transition_id,
            claim_refs=tuple(sorted(result.claim_ids)),
            evidence_refs=tuple(sorted((
                result.observation_evidence_id,
                result.translation_evidence_id,
                *result.additional_evidence_ids,
            ))),
        ))
    return tuple(traces)


def prepare_private_successor_repair_kernel(role: str, source: VerdantKernel | None = None):
    """Create one private copy and install only its frozen role-specific slots."""
    if role not in _ROLES:
        raise ValueError("Unknown terminal-successor repair role.")
    source = repair_protocol.fresh_successor_repair_kernel() if source is None else source
    before, snapshot = source.fingerprint(), source.snapshot()
    if before != repair_protocol.fresh_successor_repair_kernel().fingerprint():
        raise SuccessorRepairAdapterIntegrityError("Repair teaching requires the exact fresh v0.63 source.")
    private = VerdantKernel.from_state(snapshot)
    lessons = (
        *addition._teach(private, "taught"),
        ordering_adapter._install_order_slot(private, "taught"),
        *_install_repair_slots(private, role),
    )
    reference = VerdantKernel.from_state(snapshot)
    prerequisites = (
        *addition._teach(reference, "taught"),
        ordering_adapter._install_order_slot(reference, "taught"),
    )
    if len(lessons) != 29 or lessons[:26] != prerequisites:
        raise SuccessorRepairAdapterIntegrityError("The private copy lost its exact 26-lesson prerequisite.")
    expected = _CORRECT_SUCCESSORS if role in ("taught_repair", "valid_null") else (
        _WRONG_SUCCESSORS if role == "wrong_link_control" else ()
    )
    found = []
    for source_number in (18, 19, 20):
        match = counting._lookup(private, f"math:integer:{source_number}", "math_successor")
        if match.status == "found":
            target = int(match.label.removeprefix("math:integer:"))
            found.append((source_number, target))
        elif match.status != "missing":
            raise SuccessorRepairAdapterIntegrityError("A private repair slot is not valid or absent.")
    if tuple(found) != tuple(expected) or source.fingerprint() != before or source.snapshot() != snapshot:
        raise SuccessorRepairAdapterIntegrityError("The private repair slots or source isolation diverged.")
    return private, lessons


class RepairAdapterImplementationReceipt(FrozenRecord):
    implementation: dict
    frozen_protocol: repair_protocol.SuccessorRepairProtocolEnvelope
    protocol_file_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    purpose: Literal["frozen_private_terminal_successor_adapter_implementation"] = (
        "frozen_private_terminal_successor_adapter_implementation"
    )
    repair_adapter_implemented: Literal[True] = True
    private_repair_installer_implemented: Literal[True] = True
    bounded_native_trace_verifier_implemented: Literal[True] = True
    prospective_repair_testimony_installed: StrictBool = False
    prospective_cohort_executed: StrictBool = False
    prospective_responses_observed: StrictBool = False
    evaluation_completed: StrictBool = False
    repair_effect_observed: StrictBool = False
    causal_self_repair_observed: StrictBool = False
    spontaneous_rule_discovery_observed: StrictBool = False
    generalized_arithmetic_claim_permitted: StrictBool = False
    mathematical_understanding_claim_permitted: StrictBool = False
    learning_efficiency_observed: StrictBool = False
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    independent_replication_observed: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_receipt(self):
        if (
            canonical_json_bytes(self.implementation) != canonical_json_bytes(_IMPLEMENTATION)
            or self.frozen_protocol.declaration_sha256 != _PROTOCOL_DECLARATION_SHA256
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or any(getattr(self, name) for name in _FALSE_FLAGS)
        ):
            raise ValueError("Repair adapter lost its exact protocol pairing or claim boundary.")
        return self


class RepairAdapterImplementationEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-terminal-successor-adapter-implementation-v1"] = (
        "verdant-terminal-successor-adapter-implementation-v1"
    )
    receipt: RepairAdapterImplementationReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = RepairAdapterImplementationReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(
            receipt=checked,
            receipt_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))),
        )

    @model_validator(mode="after")
    def check_hash(self):
        expected = baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json")))
        if self.receipt_sha256 != expected:
            raise ValueError("Terminal-successor adapter receipt checksum mismatch.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairAdapterIntegrityError("Repair adapter input exceeds the size bound.")
    return data


def _code_manifest(protocol):
    sources = {source.path: source for source in protocol.declaration.code_sources}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def freeze_successor_repair_adapter(protocol_path):
    """Freeze exact implementation identity without teaching or answering."""
    protocol_data = _read(protocol_path)
    if baseline._sha(protocol_data) != _PROTOCOL_FILE_SHA256:
        raise SuccessorRepairAdapterIntegrityError("Adapter requires exact immutable v0.63 protocol bytes.")
    protocol = repair_protocol.load_successor_repair_protocol(protocol_path)
    manifest = _code_manifest(protocol)
    envelope = RepairAdapterImplementationEnvelope.build(RepairAdapterImplementationReceipt(
        implementation=_IMPLEMENTATION,
        frozen_protocol=protocol,
        protocol_file_sha256=baseline._sha(protocol_data),
        code_sources=manifest,
    ))
    if _read(protocol_path) != protocol_data or _code_manifest(protocol) != manifest:
        raise SuccessorRepairAdapterIntegrityError("Protocol or implementation changed during adapter freeze.")
    return envelope


def _validate_implementation(protocol_path, envelope):
    checked = RepairAdapterImplementationEnvelope.model_validate(envelope.model_dump(mode="json"))
    expected = freeze_successor_repair_adapter(protocol_path)
    if canonical_json_bytes(checked.model_dump(mode="json")) != canonical_json_bytes(
        expected.model_dump(mode="json")
    ):
        raise SuccessorRepairAdapterIntegrityError(
            "Repair adapter failed exact code/protocol reconstruction."
        )
    return checked


def save_successor_repair_adapter(protocol_path, implementation_path, envelope):
    checked = _validate_implementation(protocol_path, envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairAdapterIntegrityError("Repair adapter sidecar exceeds the size bound.")
    target = Path(implementation_path)
    protected = {Path(protocol_path).resolve()}
    protected.update((_ROOT / source.path).resolve() for source in checked.receipt.code_sources)
    protected.update((_ROOT / path).resolve() for path, _ in repair_protocol._HISTORY)
    protected.update((_ROOT / path).resolve() for path in repair_protocol._PROBE_FILES)
    if target.resolve() in protected:
        raise SuccessorRepairAdapterIntegrityError(
            "Cannot publish over frozen protocol, code, probes or historical evidence."
        )
    baseline._write_immutable(target, data)
    return baseline._sha(data)


def load_successor_repair_adapter(protocol_path, implementation_path):
    data = _read(implementation_path)
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise SuccessorRepairAdapterIntegrityError("Repair adapter bytes must be canonical.")
    envelope = RepairAdapterImplementationEnvelope.model_validate(raw)
    return _validate_implementation(protocol_path, envelope)


def adapter_summary(envelope):
    checked = RepairAdapterImplementationEnvelope.model_validate(envelope.model_dump(mode="json"))
    return dict(
        status="frozen_private_terminal_successor_adapter_implementation",
        receipt_sha256=checked.receipt_sha256,
        protocol_declaration_sha256=checked.receipt.frozen_protocol.declaration_sha256,
        protocol_file_sha256=checked.receipt.protocol_file_sha256,
        code_files=len(checked.receipt.code_sources),
        bounded_domain_maximum=21,
        repair_adapter_implemented=True,
        private_repair_installer_implemented=True,
        bounded_native_trace_verifier_implemented=True,
        prospective_repair_testimony_installed=False,
        prospective_cohort_executed=False,
        prospective_responses_observed=False,
        evaluation_completed=False,
        repair_effect_observed=False,
        canonical_commit_permitted=False,
    )
