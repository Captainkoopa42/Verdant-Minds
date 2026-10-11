"""Frozen coverage/operand-order challenge for the unchanged v0.58 scaffold.

This wrapper supplies no new lessons, interpreter or arithmetic scoring rule.
A durable plan must exist before execution. Invalid inputs and abstentions
remain in the frozen cohort; no result feeds back into native memory.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, ValidationError, model_validator

from verdant_kernel import VerdantKernel, checkpoint_bytes
from verdant_kernel.models import FrozenRecord, canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as counting
from verdant_math.addition import pilot as addition

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_ROLES = addition._ROLES
_GROUPS = ("supported_small_orders", "supported_large_left", "reversed_missing_mapping",
           "other_missing_mapping", "missing_successor", "invalid_input")
_PROBES = ((9, 5), (3, 9), (18, 1))
_INVALID_PROBES = ((True, 3), (9, False), (9.0, 3), (9, 3.0), ("9", 3),
                   (9, "3"), (-1, 3), (9, -1), (19, 3), (9, 19))
_EXCLUDED = (*baseline._TRAINING, *baseline._HELD_OUT, *counting._CASES,
             *addition._CASES, *_PROBES)
# Teacher-coverage categories are declared before results, and never changed
# to reflect the incorrect-rule arm's different starting operand.
_ROWS = (
    ("supported_small_orders", "small-02", {"left": 0, "right": 2}),
    ("supported_small_orders", "small-02", {"left": 2, "right": 0}),
    ("supported_small_orders", "small-03", {"left": 0, "right": 3}),
    ("supported_small_orders", "small-03", {"left": 3, "right": 0}),
    ("supported_small_orders", "small-04", {"left": 0, "right": 4}),
    ("supported_small_orders", "small-04", {"left": 4, "right": 0}),
    ("supported_small_orders", "small-14", {"left": 1, "right": 4}),
    ("supported_small_orders", "small-14", {"left": 4, "right": 1}),
    ("supported_large_left", "large-13-1", {"left": 13, "right": 1}),
    ("supported_large_left", "large-14-2", {"left": 14, "right": 2}),
    ("supported_large_left", "large-15-3", {"left": 15, "right": 3}),
    ("supported_large_left", "large-16-2", {"left": 16, "right": 2}),
    ("reversed_missing_mapping", "large-13-1", {"left": 1, "right": 13}),
    ("reversed_missing_mapping", "large-14-2", {"left": 2, "right": 14}),
    ("reversed_missing_mapping", "large-15-3", {"left": 3, "right": 15}),
    ("reversed_missing_mapping", "large-16-2", {"left": 2, "right": 16}),
    ("other_missing_mapping", None, {"left": 6, "right": 6}),
    ("other_missing_mapping", None, {"left": 8, "right": 7}),
    ("other_missing_mapping", None, {"left": 17, "right": 5}),
    ("other_missing_mapping", None, {"left": 18, "right": 18}),
    ("missing_successor", None, {"left": 17, "right": 2}),
    ("missing_successor", None, {"left": 16, "right": 3}),
    ("missing_successor", None, {"left": 15, "right": 4}),
    ("missing_successor", None, {"left": 18, "right": 2}),
    ("invalid_input", None, {"left": 14, "right": False}),
    ("invalid_input", None, {"left": None, "right": 2}),
    ("invalid_input", None, {"left": 16, "right": 2.5}),
    ("invalid_input", None, {"left": 13, "right": "2"}),
    ("invalid_input", None, {"left": 20, "right": 2}),
    ("invalid_input", None, {"left": 17}),
    ("invalid_input", None, {"left": 18, "right": 0, "answer": 18}),
    ("invalid_input", None, {"left": [14], "right": 1}),
)
_SPEC = dict(
    version="addition_coverage_operand_order_v0.59",
    adapter_version=addition._PROTOCOL["version"],
    source="fresh_seed_79059_state_dim_16_run_label_math-coverage-v059",
    roles=_ROLES, groups=_GROUPS, ordered_cases=_ROWS,
    excluded_consumed_and_observed_ordered_pairs=_EXCLUDED,
    excluded_observed_invalid_payloads=tuple({"left": a, "right": b} for a, b in _INVALID_PROBES),
    teaching="unchanged_addition_v058_25_lessons_and_same_four_controls",
    query="unchanged_AdditionRequest_and_derive_addition_no_targets_or_group_labels",
    scoring="unchanged_addition_v058_grade_after_all_128_responses_or_input_rejections",
    invalid_input="retain_original_typed_json_and_API_error_locations_and_types_no_target_no_answer_credit",
    abstention="retain_all_partial_and_blocking_evidence_no_answer_credit",
    denominator="all_32_enrolled_cases_per_role_including_8_invalid_inputs",
    groups_basis="predeclared_taught_coverage_not_outcome_dependent_reclassification",
    persistence="immutable_plan_before_any_query_separate_result_bound_to_exact_plan_bytes",
    adaptation_or_replacement_permitted=False, canonical_input_mutation_permitted=False,
    simulation_execution=False, curriculum_extension_permitted=False,
    interpretation="sampled_teacher_coverage_and_order_boundary_only",
)
_FLAGS = ("source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
          "instruction_discovery_observed", "generalized_arithmetic_claim_permitted",
          "canonical_commit_permitted", "resolution_authority_enabled", "promotion_authority_enabled",
          "policy_rewrite_authority_enabled")


class CoverageIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """The frozen coverage challenge or its local execution lineage changed."""


class Boundaries(FrozenRecord):
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
    def check_boundaries(self):
        if any(getattr(self, f) for f in _FLAGS):
            raise ValueError("Coverage measurement grants no discovery, physical or canonical authority.")
        return self


class ChallengeCase(FrozenRecord):
    case_id: _Ref
    group: Literal["supported_small_orders", "supported_large_left", "reversed_missing_mapping",
                   "other_missing_mapping", "missing_successor", "invalid_input"]
    order_pair: _Ref | None
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


def _cases():
    return tuple(ChallengeCase(case_id=f"math-v059:case:{i}", group=g, order_pair=p,
        raw_request_json=canonical_json_bytes(raw).decode("utf-8"))
        for i, (g, p, raw) in enumerate(_ROWS))


def _code_manifest():
    sources = {s.path: s for s in addition._code_manifest()}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = str(path.relative_to(_ROOT))
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_coverage_kernel():
    return VerdantKernel(seed=79059, state_dim=16, run_label="math-coverage-v059")


class CoveragePlan(Boundaries):
    protocol: dict
    cases: tuple[ChallengeCase, ...] = Field(min_length=32, max_length=32)
    code_sources: tuple[baseline.MathCodeDigest, ...]
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    purpose: Literal["unchanged_addition_coverage_challenge"] = "unchanged_addition_coverage_challenge"

    @model_validator(mode="after")
    def check_protocol(self):
        if (canonical_json_bytes(self.protocol) != canonical_json_bytes(_SPEC)
            or self.cases != _cases()):
            raise ValueError("Coverage plan lost its frozen cases, controls or scoring.")
        excluded = {canonical_json_bytes({"left": a, "right": b}) for a, b in (*_EXCLUDED, *_INVALID_PROBES)}
        raw = tuple(c.raw_request_json.encode("utf-8") for c in self.cases)
        if len(set(raw)) != len(raw) or any(r in excluded for r in raw):
            raise ValueError("Coverage cases must be fresh and disjoint from consumed cases and probes.")
        return self


class CoveragePlanEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-addition-coverage-plan-v1"] = "verdant-addition-coverage-plan-v1"
    plan: CoveragePlan
    plan_sha256: _Digest

    @classmethod
    def build(cls, plan):
        checked = CoveragePlan.model_validate(plan.model_dump(mode="json"))
        return cls(plan=checked, plan_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.plan_sha256 != baseline._sha(canonical_json_bytes(self.plan.model_dump(mode="json"))):
            raise ValueError("Coverage plan checksum mismatch.")
        return self


def freeze_coverage_plan():
    source = fresh_coverage_kernel()
    data = checkpoint_bytes(source.snapshot())
    return CoveragePlanEnvelope.build(CoveragePlan(protocol=_SPEC, cases=_cases(),
        code_sources=_code_manifest(), source_checkpoint_base64=base64.b64encode(data).decode("ascii"),
        source_checkpoint_sha256=baseline._sha(data), source_kernel_fingerprint=source.fingerprint()))


def _validate_plan(envelope):
    envelope = CoveragePlanEnvelope.model_validate(envelope.model_dump(mode="json"))
    p = envelope.plan
    source = baseline._checkpoint(p.source_checkpoint_base64, p.source_checkpoint_sha256)
    if (p.code_sources != _code_manifest() or source.fingerprint() != p.source_kernel_fingerprint
        or source.fingerprint() != fresh_coverage_kernel().fingerprint()
        or canonical_json_bytes(envelope.model_dump(mode="json"))
           != canonical_json_bytes(freeze_coverage_plan().model_dump(mode="json"))):
        raise CoverageIntegrityError("Coverage plan source or implementation changed.")
    return envelope


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise CoverageIntegrityError("Coverage sidecar exceeds the size bound.")
    return data


def _parse(data):
    return json.loads(data, object_pairs_hook=baseline._unique_object)


def save_coverage_plan(path, envelope):
    checked = _validate_plan(envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise CoverageIntegrityError("Coverage sidecar exceeds the size bound.")
    baseline._write_immutable(Path(path), data)
    return baseline._sha(data)


def load_coverage_plan(path):
    return _validate_plan(CoveragePlanEnvelope.model_validate(_parse(_read(path))))


class InputRejection(FrozenRecord):
    location: tuple[StrictStr | StrictInt, ...]
    error_type: _Ref


class CoverageResponse(FrozenRecord):
    case: ChallengeCase
    request: addition.AdditionRequest | None
    reply: addition.AdditionReply | None
    input_errors: tuple[InputRejection, ...]

    @model_validator(mode="after")
    def check_input_boundary(self):
        if ((self.request is None) != (self.reply is None)
            or (self.request is None) != bool(self.input_errors)):
            raise ValueError("Coverage response lost its input-rejection boundary.")
        return self


def _respond(kernel, case):
    raw = _parse(case.raw_request_json)
    try:
        request = addition.AdditionRequest.model_validate(raw)
    except ValidationError as exc:
        # Preserve original typed input and stable API rejection metadata.
        # No arithmetic target is inferred from malformed input.
        errors = tuple(InputRejection(location=e["loc"], error_type=e["type"])
                       for e in exc.errors(include_url=False, include_context=False, include_input=False))
        return CoverageResponse(case=case, request=None, reply=None, input_errors=errors)
    return CoverageResponse(case=case, request=request,
        reply=addition.derive_addition(kernel, request), input_errors=())


class CoverageObservation(CoverageResponse):
    expected_answer: Annotated[StrictInt, Field(ge=0, le=36)] | None
    grade: Literal["correct", "incorrect", "abstained", "invalid_input"]

    @model_validator(mode="after")
    def check_grade_boundary(self):
        if ((self.request is None) != (self.grade == "invalid_input")
            or (self.request is None) != (self.expected_answer is None)):
            raise ValueError("Invalid coverage input must retain rejection without an arithmetic target.")
        return self


def _score(index, response):
    if response.request is None:
        expected, grade = None, "invalid_input"
    else:
        # Reuse the old evaluator unchanged. Its old split/case IDs are not
        # coverage group labels and are deliberately not copied.
        scored = addition._grade(index, response.request, response.reply)
        expected, grade = scored.expected_answer, scored.grade
    return CoverageObservation(**response.model_dump(mode="json"), expected_answer=expected, grade=grade)


class CoverageArm(FrozenRecord):
    role: Literal["taught", "no_rule_control", "valid_null", "incorrect_rule_control"]
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[counting.CountingLessonTrace, ...] = Field(min_length=25, max_length=25)
    observations: tuple[CoverageObservation, ...] = Field(min_length=32, max_length=32)


class CoverageReceipt(Boundaries):
    frozen_plan: CoveragePlanEnvelope
    plan_file_sha256: _Digest
    arms: tuple[CoverageArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["unchanged_addition_coverage_evaluation"] = "unchanged_addition_coverage_evaluation"

    @model_validator(mode="after")
    def check_roles(self):
        if tuple(a.role for a in self.arms) != _ROLES:
            raise ValueError("Coverage evaluation lost its frozen roles.")
        return self


class CoverageEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-addition-coverage-result-v1"] = "verdant-addition-coverage-result-v1"
    receipt: CoverageReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = CoverageReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.receipt_sha256 != baseline._sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Coverage evaluation checksum mismatch.")
        return self


def run_coverage_challenge(plan_path, kernel=None):
    # A missing/conflicting/retuned durable plan fails before teaching/query.
    plan_data = _read(plan_path)
    envelope = _validate_plan(CoveragePlanEnvelope.model_validate(_parse(plan_data)))
    plan = envelope.plan
    source = (baseline._checkpoint(plan.source_checkpoint_base64, plan.source_checkpoint_sha256)
              if kernel is None else kernel)
    before = source.fingerprint()
    if before != plan.source_kernel_fingerprint:
        raise CoverageIntegrityError("Coverage requires its fixed fresh unexposed source.")
    manifest, pending = _code_manifest(), []
    for role in _ROLES:
        private = VerdantKernel.from_state(source.snapshot())
        lessons = addition._teach(private, role)
        fingerprint = private.fingerprint()
        responses = tuple(_respond(private, c) for c in plan.cases)
        if private.fingerprint() != fingerprint:
            raise CoverageIntegrityError("Coverage queries changed their private kernel.")
        pending.append((role, lessons, fingerprint, checkpoint_bytes(private.snapshot()), responses))
    # Freeze all 128 responses/input rejections before any evaluator call.
    arms = tuple(CoverageArm(role=role, lessons=lessons, kernel_fingerprint=fp,
        checkpoint_base64=base64.b64encode(data).decode("ascii"), checkpoint_sha256=baseline._sha(data),
        observations=tuple(_score(i, r) for i, r in enumerate(responses)))
        for role, lessons, fp, data, responses in pending)
    if (source.fingerprint() != before or _code_manifest() != manifest
        or _read(plan_path) != plan_data):
        raise CoverageIntegrityError("Coverage source, implementation or durable plan changed during execution.")
    if (arms[0].model_dump(exclude={"role"}) != arms[2].model_dump(exclude={"role"})
        or any(a.lessons[:24] != arms[0].lessons[:24] for a in arms)):
        raise CoverageIntegrityError("Coverage exact null or matched lesson controls diverged.")
    return CoverageEnvelope.build(CoverageReceipt(frozen_plan=envelope,
        plan_file_sha256=baseline._sha(plan_data), arms=arms))


def _validate_replay(plan_path, envelope):
    envelope = CoverageEnvelope.model_validate(envelope.model_dump(mode="json"))
    receipt = envelope.receipt
    plan_data = _read(plan_path)
    plan = load_coverage_plan(plan_path)
    if (receipt.frozen_plan != plan or receipt.plan_file_sha256 != baseline._sha(plan_data)):
        raise CoverageIntegrityError("Coverage evaluation is bound to different frozen plan bytes.")
    for arm in receipt.arms:
        private = baseline._checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        if private.fingerprint() != arm.kernel_fingerprint:
            raise CoverageIntegrityError("Coverage arm fingerprint mismatch.")
        if tuple(o.case for o in arm.observations) != plan.plan.cases:
            raise CoverageIntegrityError("Coverage evaluation dropped, substituted or reordered frozen cases.")
        for o in arm.observations:
            response = _respond(private, o.case)
            recorded = CoverageResponse.model_validate(o.model_dump(mode="json", exclude={"expected_answer", "grade"}))
            if response != recorded:
                raise CoverageIntegrityError("Coverage native binding, partial derivation or input rejection failed replay.")
    expected = run_coverage_challenge(plan_path)
    if canonical_json_bytes(expected.model_dump(mode="json")) != canonical_json_bytes(envelope.model_dump(mode="json")):
        raise CoverageIntegrityError("Coverage lessons, scoring or full native execution failed replay.")


def save_coverage_challenge(plan_path, result_path, envelope):
    _validate_replay(plan_path, envelope)
    data = canonical_json_bytes(envelope.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise CoverageIntegrityError("Coverage sidecar exceeds the size bound.")
    baseline._write_immutable(Path(result_path), data)
    return baseline._sha(data)


def load_coverage_challenge(plan_path, result_path):
    envelope = CoverageEnvelope.model_validate(_parse(_read(result_path)))
    _validate_replay(plan_path, envelope)
    return envelope


def coverage_summary(envelope):
    def counts(observations):
        return {grade: sum(o.grade == grade for o in observations)
                for grade in ("correct", "incorrect", "abstained", "invalid_input")}

    return dict(status="unchanged_addition_coverage_challenge",
        plan_sha256=envelope.receipt.frozen_plan.plan_sha256,
        plan_file_sha256=envelope.receipt.plan_file_sha256, receipt_sha256=envelope.receipt_sha256,
        enrolled_per_role=32, valid_inputs_per_role=24,
        arms={a.role: dict(total=counts(a.observations), groups={g: counts(tuple(o for o in a.observations
            if o.case.group == g)) for g in _GROUPS}) for a in envelope.receipt.arms},
        **{flag: False for flag in _FLAGS})
