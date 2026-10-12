"""Private-copy operand routing for the frozen v0.60 teaching protocol.

The order rule, addition rule, operand mappings and successor facts are all
teacher supplied.  This module provides a handwritten, read-only dispatcher
and exact native replay.  It contains no prospective cohort runner or grader.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictStr, model_validator

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
from verdant_math.ordering_protocol import protocol as ordering

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _Number = baseline._Digest, baseline._Ref, baseline._Answer
_MAX_BYTES = baseline._MAX_BYTES
_PROCEDURE = ordering._INSTRUCTION["subject"]
_PREDICATE = ordering._INSTRUCTION["predicate"]
_CORRECT = ordering._INSTRUCTION["correct_label"]
_INCORRECT = ordering._INSTRUCTION["incorrect_label"]
_TEACHER_SOURCE = ordering._INSTRUCTION["declared_source"]
_ROLES = tuple(ordering._SPEC["roles"])
_ADAPTER_VERSION = "teacher_scaffold_operand_order_adapter_v0.61"
_PROTOCOL_DECLARATION_SHA256 = "1f92621d9572c5068babc6d880d239100f4847c511ead8bb10f8d2ffaa4beba8"
_PROTOCOL_FILE_SHA256 = "09c6d2e0c914aa8fb8f256d59cf6ba81bfda87345413b68817bb6515dec39407"
_IMPLEMENTATION = dict(
    version=_ADAPTER_VERSION,
    frozen_protocol_declaration_sha256=_PROTOCOL_DECLARATION_SHA256,
    frozen_protocol_file_sha256=_PROTOCOL_FILE_SHA256,
    source="fresh_seed_79060_state_dim_16_run_label_math-operand-order-v060",
    roles=_ROLES,
    prerequisite="same_25_correct_v058_lessons_in_every_distinct_private_copy",
    instruction_slot="one_native_order_claim_or_prompt_as_frozen_by_v060",
    correct_route=(
        "valid_original_right_keeps_order; only_missing_original_right_plus_valid_original_left_swaps_once; "
        "all_conflicting_invalid_or_unsupported_lookups_abstain"
    ),
    no_instruction="delegate_original_order_to_unchanged_v058_addition",
    incorrect_route="valid_original_right_swaps_once; missing_original_right_keeps_order",
    nested_interpreters=(addition._PROTOCOL["version"], counting._PROTOCOL["version"]),
    trace=(
        "local_run_and_case_refs", "private_kernel_fingerprint", "original_request",
        "effective_request", "native_order_instruction", "original_right_lookup",
        "original_left_lookup_if_checked", "route_disposition", "complete_nested_addition_reply",
    ),
    prohibited=(
        "sorting", "recursive_retry", "integer_to_tokens_reconstruction", "response_arithmetic",
        "case_or_group_labels", "expected_answers", "external_grades", "canonical_mutation",
        "attention_allocation", "obligation_simulation",
    ),
    adapter_only="no_v060_prospective_response_or_evaluation_in_this_increment",
)
_FALSE_FLAGS = (
    "prospective_cohort_executed", "prospective_responses_observed", "evaluation_completed",
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "instruction_discovery_observed", "generalized_arithmetic_claim_permitted",
    "learning_efficiency_observed", "independent_replication_observed",
    "canonical_commit_permitted", "resolution_authority_enabled", "promotion_authority_enabled",
    "policy_rewrite_authority_enabled",
)


class OperandOrderAdapterIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The private routing implementation, trace or exact protocol pairing changed."""


class NativeInstructionTrace(FrozenRecord):
    status: Literal["missing", "conflicting", "invalid", "unsupported", "valid"]
    label: StrictStr | None
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_trace(self):
        if (self.claim_refs != tuple(sorted(set(self.claim_refs)))
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))):
            raise ValueError("Order-instruction provenance must be complete and canonical.")
        if self.status == "missing":
            if self.label is not None or self.claim_refs or self.evidence_refs:
                raise ValueError("A missing order instruction cannot invent provenance.")
        elif self.status == "valid":
            if self.label not in (_CORRECT, _INCORRECT) or len(self.claim_refs) != 1 or not self.evidence_refs:
                raise ValueError("A valid order instruction needs one supported frozen label.")
        elif self.status == "unsupported":
            if self.label is None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Unsupported order testimony must remain visible.")
        elif self.label is not None or not self.claim_refs or not self.evidence_refs:
            raise ValueError("Blocked order testimony lost its native provenance.")
        return self


class NativeMappingTrace(FrozenRecord):
    operand_role: Literal["original_right", "original_left"]
    operand: _Number
    status: Literal["missing", "conflicting", "invalid", "unsupported", "valid"]
    label: StrictStr | None
    tokens: tuple[Literal["tick"], ...] | None = Field(default=None, max_length=4)
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_trace(self):
        if (self.claim_refs != tuple(sorted(set(self.claim_refs)))
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))):
            raise ValueError("Operand-mapping provenance must be complete and canonical.")
        if self.status == "missing":
            if self.label is not None or self.tokens is not None or self.claim_refs or self.evidence_refs:
                raise ValueError("A missing operand mapping cannot invent native evidence.")
        elif self.status == "valid":
            if self.label is None or self.tokens is None or len(self.claim_refs) != 1 or not self.evidence_refs:
                raise ValueError("A valid operand mapping needs decoded native testimony.")
        elif self.status == "unsupported":
            if self.label is None or self.tokens is not None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Unsupported mapping testimony must remain visible.")
        elif self.status == "invalid":
            if self.tokens is not None or not self.claim_refs or not self.evidence_refs:
                raise ValueError("Invalid operand testimony lost its native provenance.")
        elif self.label is not None or self.tokens is not None or not self.claim_refs or not self.evidence_refs:
            raise ValueError("Conflicting operand testimony lost its native provenance.")
        return self


_BLOCKED_ROUTES = (
    "blocked_order_instruction", "blocked_original_right_mapping", "blocked_original_left_mapping",
)
_SWAPPED_ROUTES = (
    "swapped_missing_original_right", "incorrect_swapped_valid_original_right",
)
_DISPATCHED_ROUTES = (
    "kept_valid_original_right", "swapped_missing_original_right",
    "no_instruction_original_order", "incorrect_swapped_valid_original_right",
    "incorrect_kept_missing_original_right",
)


class OperandOrderReply(FrozenRecord):
    adapter_version: Literal["teacher_scaffold_operand_order_adapter_v0.61"] = _ADAPTER_VERSION
    protocol_declaration_sha256: _Digest = _PROTOCOL_DECLARATION_SHA256
    local_run_ref: _Ref
    case_ref: _Ref
    private_kernel_fingerprint: _Digest
    original_request: addition.AdditionRequest
    effective_request: addition.AdditionRequest | None
    status: Literal["derived", "abstained"]
    answer: _Number | None
    route_disposition: Literal[
        "kept_valid_original_right", "swapped_missing_original_right",
        "no_instruction_original_order", "incorrect_swapped_valid_original_right",
        "incorrect_kept_missing_original_right", "blocked_order_instruction",
        "blocked_original_right_mapping", "blocked_original_left_mapping",
    ]
    order_instruction: NativeInstructionTrace
    original_right_lookup: NativeMappingTrace
    original_left_lookup: NativeMappingTrace | None
    addition_reply: addition.AdditionReply | None

    @model_validator(mode="after")
    def check_reply(self):
        if self.original_right_lookup.operand_role != "original_right" or self.original_right_lookup.operand != self.original_request.right:
            raise ValueError("The original-right lookup no longer binds the original request.")
        if self.original_left_lookup is not None and (
            self.original_left_lookup.operand_role != "original_left"
            or self.original_left_lookup.operand != self.original_request.left
        ):
            raise ValueError("The original-left lookup no longer binds the original request.")
        blocked = self.route_disposition in _BLOCKED_ROUTES
        if blocked:
            if (self.effective_request is not None or self.addition_reply is not None
                or self.status != "abstained" or self.answer is not None):
                raise ValueError("A blocked route cannot invoke or fabricate an addition response.")
        else:
            if self.route_disposition not in _DISPATCHED_ROUTES or self.effective_request is None or self.addition_reply is None:
                raise ValueError("A dispatched route must retain its complete nested addition reply.")
            expected = (addition.AdditionRequest(left=self.original_request.right, right=self.original_request.left)
                        if self.route_disposition in _SWAPPED_ROUTES else self.original_request)
            if self.effective_request != expected:
                raise ValueError("The effective request is not the declared original or one transposition.")
            if (self.answer != self.addition_reply.answer
                or self.status != self.addition_reply.status):
                raise ValueError("The order reply cannot reinterpret its nested addition reply.")
        if ((self.status == "derived") != (self.answer is not None)):
            raise ValueError("An order reply cannot give partial answer credit.")
        if self.route_disposition == "swapped_missing_original_right":
            if (self.order_instruction.label != _CORRECT or self.original_right_lookup.status != "missing"
                or self.original_left_lookup is None or self.original_left_lookup.status != "valid"):
                raise ValueError("The correct swap lost its absent-right and valid-left authorization.")
        elif self.route_disposition == "kept_valid_original_right":
            if self.order_instruction.label != _CORRECT or self.original_right_lookup.status != "valid":
                raise ValueError("The correct keep route requires a valid original-right mapping.")
        elif self.route_disposition == "no_instruction_original_order":
            if self.order_instruction.status != "missing":
                raise ValueError("Only a missing order instruction may use the fallback route.")
        elif self.route_disposition.startswith("incorrect_"):
            if self.order_instruction.label != _INCORRECT:
                raise ValueError("The incorrect control route lost its separately supplied instruction.")
        return self


def _instruction_trace(kernel: VerdantKernel) -> NativeInstructionTrace:
    match = counting._lookup(kernel, _PROCEDURE, _PREDICATE)
    if match.status != "found":
        return NativeInstructionTrace(status=match.status, label=None,
            claim_refs=match.claim_refs, evidence_refs=match.evidence_refs)
    status = "valid" if match.label in (_CORRECT, _INCORRECT) else "unsupported"
    return NativeInstructionTrace(status=status, label=match.label,
        claim_refs=match.claim_refs, evidence_refs=match.evidence_refs)


def _mapping_trace(kernel: VerdantKernel, operand: int, role: Literal["original_right", "original_left"]):
    match = counting._lookup(kernel, f"math:integer:{operand}", "math_counting_tokens")
    if match.status != "found":
        return NativeMappingTrace(operand_role=role, operand=operand, status=match.status,
            label=None, tokens=None, claim_refs=match.claim_refs, evidence_refs=match.evidence_refs)
    try:
        tokens = addition._decode_tokens(match.label)
    except ValueError:
        status = "invalid" if match.label.startswith("math:tokens:") else "unsupported"
        return NativeMappingTrace(operand_role=role, operand=operand, status=status,
            label=match.label, tokens=None, claim_refs=match.claim_refs, evidence_refs=match.evidence_refs)
    return NativeMappingTrace(operand_role=role, operand=operand, status="valid",
        label=match.label, tokens=tokens, claim_refs=match.claim_refs, evidence_refs=match.evidence_refs)


def derive_ordered_addition(
    kernel: VerdantKernel,
    request: addition.AdditionRequest,
    *,
    local_run_ref: str,
    case_ref: str,
) -> OperandOrderReply:
    """Route one validated request once, preserving every native decision input."""
    request = addition.AdditionRequest.model_validate(request.model_dump(mode="json"))
    before = kernel.fingerprint()
    instruction = _instruction_trace(kernel)
    right = _mapping_trace(kernel, request.right, "original_right")
    left = None
    effective = None
    nested = None

    if instruction.status == "missing":
        disposition = "no_instruction_original_order"
        effective = request
    elif instruction.status != "valid":
        disposition = "blocked_order_instruction"
    elif instruction.label == _CORRECT:
        if right.status == "valid":
            disposition = "kept_valid_original_right"
            effective = request
        elif right.status == "missing":
            left = _mapping_trace(kernel, request.left, "original_left")
            if left.status == "valid":
                disposition = "swapped_missing_original_right"
                effective = addition.AdditionRequest(left=request.right, right=request.left)
            else:
                disposition = "blocked_original_left_mapping"
        else:
            disposition = "blocked_original_right_mapping"
    else:
        if right.status == "valid":
            disposition = "incorrect_swapped_valid_original_right"
            effective = addition.AdditionRequest(left=request.right, right=request.left)
        elif right.status == "missing":
            disposition = "incorrect_kept_missing_original_right"
            effective = request
        else:
            disposition = "blocked_original_right_mapping"

    if effective is not None:
        nested = addition.derive_addition(kernel, effective)
    if kernel.fingerprint() != before:
        raise OperandOrderAdapterIntegrityError("Operand-order routing changed its private kernel.")
    return OperandOrderReply(
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


def verify_order_derivation(kernel, request, reply):
    """Replay the order decision and unchanged nested addition against native state."""
    checked = OperandOrderReply.model_validate(reply.model_dump(mode="json"))
    if checked.private_kernel_fingerprint != kernel.fingerprint():
        raise OperandOrderAdapterIntegrityError("Operand-order trace belongs to another private kernel.")
    if checked.addition_reply is not None:
        addition.verify_addition_derivation(kernel, checked.effective_request, checked.addition_reply)
    expected = derive_ordered_addition(kernel, request,
        local_run_ref=checked.local_run_ref, case_ref=checked.case_ref)
    if checked != expected:
        raise OperandOrderAdapterIntegrityError("Operand-order trace failed exact native replay.")


def _install_order_slot(kernel: VerdantKernel, role: str):
    pipeline = ClaimLearningPipeline()
    incorrect = role == "incorrect_instruction_control"
    no_instruction = role == "no_instruction_control"
    target = None if no_instruction else _INCORRECT if incorrect else _CORRECT
    text = (
        "Operand-order procedure slot: no rule supplied."
        if no_instruction else
        "Teacher operand-order scaffold: transpose once only when the original right mapping is "
        + ("found." if incorrect else "missing and the original left mapping is valid.")
    )
    key = "math-v061:operand-order-rule"
    if target is not None:
        result = pipeline.record_claim(kernel, event_key=key, native_description=text,
            subject_label=_PROCEDURE, predicate=_PREDICATE, object_label=target,
            polarity=ClaimPolarity.AFFIRMED, source_class=ClaimSourceClass.HUMAN_TESTIMONY,
            source_ref=_TEACHER_SOURCE,
            rationale="Explicit teacher-supplied private operand routing; no discovered commutativity rule.").kernel_result
    else:
        chunk, store = PipelineOrchestrator().process(ExperienceInput.from_text(
            text, source_id=_TEACHER_SOURCE, source_name=f"{key}.txt"))
        payload, translation = chunk.payloads[0], chunk.translations[0]
        result = kernel.apply_experience(ExperienceCommand(event_key=key, source_ref=_TEACHER_SOURCE,
            modality="text", payload_sha256=payload.source_sha256,
            feature_vector=tuple(float(v) for v in store.get_array(translation.feature_ref).reshape(-1)),
            semantic_evidence_kind=EvidenceKind.TESTIMONY,
            semantic_evidence_details={"source_class": "human_testimony", "operand_order_rule_supplied": False},
            metadata={"event_type": "operand_order_rule_prompt_only", "epistemic_status": "no_rule_supplied"}))
    return counting.CountingLessonTrace(event_key=key, native_description=text,
        subject_label=_PROCEDURE, predicate=_PREDICATE, object_label=target,
        transition_ref=result.transition_id, claim_refs=tuple(sorted(result.claim_ids)),
        evidence_refs=tuple(sorted((result.observation_evidence_id,
            result.translation_evidence_id, *result.additional_evidence_ids))))


def prepare_private_operand_order_kernel(role: str, source: VerdantKernel | None = None):
    """Create one distinct private copy and install only its frozen teaching arm."""
    if role not in _ROLES:
        raise ValueError("Unknown operand-order role.")
    source = ordering.fresh_order_kernel() if source is None else source
    before, snapshot = source.fingerprint(), source.snapshot()
    if before != ordering.fresh_order_kernel().fingerprint():
        raise OperandOrderAdapterIntegrityError("Operand-order teaching requires the exact fresh v0.60 source.")
    private = VerdantKernel.from_state(snapshot)
    lessons = (*addition._teach(private, "taught"), _install_order_slot(private, role))
    if len(lessons) != 26 or lessons[:25] != addition._teach(VerdantKernel.from_state(snapshot), "taught"):
        raise OperandOrderAdapterIntegrityError("The private copy lost the exact 25-lesson addition prerequisite.")
    expected = "missing" if role == "no_instruction_control" else "valid"
    instruction = _instruction_trace(private)
    expected_label = _INCORRECT if role == "incorrect_instruction_control" else _CORRECT
    if (instruction.status != expected
        or (expected == "valid" and instruction.label != expected_label)
        or source.fingerprint() != before or source.snapshot() != snapshot):
        raise OperandOrderAdapterIntegrityError("The private order slot or source-isolation boundary diverged.")
    return private, lessons


class AdapterImplementationReceipt(FrozenRecord):
    implementation: dict
    frozen_protocol: ordering.OperandOrderProtocolEnvelope
    protocol_file_sha256: _Digest
    code_sources: tuple[baseline.MathCodeDigest, ...]
    purpose: Literal["frozen_private_operand_order_adapter_implementation"] = (
        "frozen_private_operand_order_adapter_implementation"
    )
    adapter_implemented: Literal[True] = True
    private_instruction_installer_implemented: Literal[True] = True
    native_trace_verifier_implemented: Literal[True] = True
    prospective_cohort_executed: StrictBool = False
    prospective_responses_observed: StrictBool = False
    evaluation_completed: StrictBool = False
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    instruction_discovery_observed: StrictBool = False
    generalized_arithmetic_claim_permitted: StrictBool = False
    learning_efficiency_observed: StrictBool = False
    independent_replication_observed: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_receipt(self):
        if (canonical_json_bytes(self.implementation) != canonical_json_bytes(_IMPLEMENTATION)
            or self.frozen_protocol.declaration_sha256 != _PROTOCOL_DECLARATION_SHA256
            or self.protocol_file_sha256 != _PROTOCOL_FILE_SHA256
            or any(getattr(self, name) for name in _FALSE_FLAGS)):
            raise ValueError("Adapter implementation lost its exact protocol pairing or claim boundary.")
        return self


class AdapterImplementationEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-operand-order-adapter-implementation-v1"] = (
        "verdant-operand-order-adapter-implementation-v1"
    )
    receipt: AdapterImplementationReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = AdapterImplementationReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked,
            receipt_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.receipt_sha256 != baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Operand-order adapter receipt checksum mismatch.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise OperandOrderAdapterIntegrityError("Operand-order adapter input exceeds the size bound.")
    return data


def _code_manifest(protocol):
    sources = {s.path: s for s in protocol.declaration.code_sources}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def freeze_operand_order_adapter(protocol_path):
    """Freeze code/protocol identity without installing a lesson or answering a case."""
    protocol_data = _read(protocol_path)
    if baseline._sha(protocol_data) != _PROTOCOL_FILE_SHA256:
        raise OperandOrderAdapterIntegrityError("Adapter requires the exact immutable v0.60 protocol bytes.")
    protocol = ordering.load_operand_order_protocol(protocol_path)
    manifest = _code_manifest(protocol)
    envelope = AdapterImplementationEnvelope.build(AdapterImplementationReceipt(
        implementation=_IMPLEMENTATION,
        frozen_protocol=protocol,
        protocol_file_sha256=baseline._sha(protocol_data),
        code_sources=manifest,
    ))
    if _read(protocol_path) != protocol_data or _code_manifest(protocol) != manifest:
        raise OperandOrderAdapterIntegrityError("Protocol or implementation changed during adapter freeze.")
    return envelope


def _validate_implementation(protocol_path, envelope):
    checked = AdapterImplementationEnvelope.model_validate(envelope.model_dump(mode="json"))
    expected = freeze_operand_order_adapter(protocol_path)
    if canonical_json_bytes(checked.model_dump(mode="json")) != canonical_json_bytes(expected.model_dump(mode="json")):
        raise OperandOrderAdapterIntegrityError("Adapter implementation failed exact code/protocol reconstruction.")
    return checked


def save_operand_order_adapter(protocol_path, implementation_path, envelope):
    checked = _validate_implementation(protocol_path, envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise OperandOrderAdapterIntegrityError("Operand-order adapter sidecar exceeds the size bound.")
    target = Path(implementation_path)
    protected = {Path(protocol_path).resolve()}
    protected.update((_ROOT / source.path).resolve() for source in checked.receipt.code_sources)
    protected.update((_ROOT / path).resolve() for path, _ in ordering._HISTORY)
    if target.resolve() in protected:
        raise OperandOrderAdapterIntegrityError("Cannot publish over frozen protocol, code or historical evidence.")
    baseline._write_immutable(target, data)
    return baseline._sha(data)


def load_operand_order_adapter(protocol_path, implementation_path):
    data = _read(implementation_path)
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise OperandOrderAdapterIntegrityError("Operand-order adapter bytes must be canonical.")
    return _validate_implementation(protocol_path, AdapterImplementationEnvelope.model_validate(raw))


def adapter_summary(envelope):
    receipt = AdapterImplementationEnvelope.model_validate(envelope.model_dump(mode="json")).receipt
    return dict(status="frozen_private_operand_order_adapter_implementation",
        receipt_sha256=envelope.receipt_sha256,
        protocol_declaration_sha256=receipt.frozen_protocol.declaration_sha256,
        protocol_file_sha256=receipt.protocol_file_sha256,
        code_files=len(receipt.code_sources), adapter_implemented=True,
        private_instruction_installer_implemented=True, native_trace_verifier_implemented=True,
        prospective_cohort_executed=False, prospective_responses_observed=False,
        evaluation_completed=False, canonical_commit_permitted=False)
