"""Freeze a bounded zero-new-lesson successor-retention study.

The declaration audits every consumed math request and recorded probe, then
binds exact v0.65 private checkpoints for later reuse.  It installs no lesson,
answers no case, invokes no grader and runs no obligation simulation.
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
from verdant_math.successor_repair_adapter import adapter as repair_adapter
from verdant_math.successor_repair_evaluation import evaluation as repair_evaluation
from verdant_math.successor_repair_protocol import protocol as repair_protocol

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_BoundedNumber = Annotated[StrictInt, Field(ge=0, le=21)]

_HISTORY = (
    (
        "artifacts/terminal_successor_v063/protocol.vsrp",
        "ee8f37cb145704fbb9ff753a5416b2ba473d276c96813a194465ca5960883081",
    ),
    (
        "artifacts/terminal_successor_v064/implementation.vsri",
        "397231910c27b8a429551e326fc11f880d3522466438de09a57534825be9d83d",
    ),
    (
        "artifacts/terminal_successor_v065/responses.vsrb",
        "6f7fc01cfa4f380fd3b7f09e10fb0de4631cc1b5c1071823e59e864b6aad7f26",
    ),
    (
        "artifacts/terminal_successor_v065/evaluation.vsrr",
        "e704ee573b92f6bd9979502ae92d73f9f7f75a6928e1eb6e3a63d4900cfbea0f",
    ),
)
_INTERNAL_HASHES = {
    "protocol_declaration": "b680c4b5eb50abd80b422df2cdf1ba8504af08045f9e1b7d52a99e68a8cfa98a",
    "implementation_receipt": "19e0363f65400308d49455b887ffb33dcdf7a3e0bbce93bc3bb0eadc320160c2",
    "response_receipt": "c184c060a72e2e310ee1a929d54ccaa11bf0a0a3babe924f291c282f354dd31e",
    "evaluation_receipt": "f7d9ee00425eaed98ef0e3f55d582d12aea60266d1053435e52b2493565a3b72",
}
_AUDIT_FILES = (
    "tests/test_math_teaching_pilot.py",
    "tests/test_counting_teaching_pilot.py",
    "tests/test_scaffold_addition_pilot.py",
    "tests/test_addition_coverage_challenge.py",
    "tests/test_operand_order_protocol.py",
    "tests/test_operand_order_adapter.py",
    "tests/test_operand_order_evaluation.py",
    "tests/test_successor_repair_protocol.py",
    "tests/test_successor_repair_adapter.py",
    "tests/test_successor_repair_evaluation.py",
)
_ROLES = (
    "retained_repair",
    "no_repair_control",
    "valid_null",
    "wrong_link_control",
)
_SOURCE_ROLES = {
    "retained_repair": "taught_repair",
    "no_repair_control": "no_repair_control",
    "valid_null": "valid_null",
    "wrong_link_control": "wrong_link_control",
}
_AVAILABLE_UNORDERED = ((0, 15), (0, 16), (0, 17), (1, 17), (4, 18), (4, 21))
_INVALID = (
    {"left": 18, "right": True},
    {"left": None, "right": 3},
    {"left": 21, "right": "4"},
    {"left": 18.5, "right": 4},
    {"left": -1, "right": 4},
    {"left": 18},
    {"left": 18, "right": 4, "answer": 22},
    {"left": [18], "right": 4},
)


def _group(pair):
    if pair == (4, 18):
        return "retained_partial_walk"
    if pair == (4, 21):
        return "declared_domain_ceiling"
    return "retained_prerequisite_control"


_ROWS = tuple(
    (_group(pair), f"fresh-{pair[0]}-{pair[1]}", {"left": left, "right": right})
    for pair in _AVAILABLE_UNORDERED
    for left, right in (pair, (pair[1], pair[0]))
) + tuple(("invalid_input", None, raw) for raw in _INVALID)

_SPEC = dict(
    version="teacher_scaffold_successor_retention_protocol_v0.66",
    phase="prospective_protocol_only",
    grounded_parent_commit="25d47fb038dae5c2a0e495fc38d4828e254005dc",
    grounded_parent_tree="73a6a430b412fa46af6861b8657094cf6610b9a4",
    source="fresh_seed_79066_state_dim_16_run_label_math-successor-retention-v066",
    roles=_ROLES,
    consumed_cohorts=(
        "v056_fact_recall", "v057_counting", "v058_scaffold_addition",
        "v059_addition_coverage", "v060_v062_operand_order",
        "v063_v065_terminal_successor",
    ),
    bounded_domain="unchanged_strict_native_zero_through_twenty_one",
    retained_testimony="exact_already_supplied_18_to_19_19_to_20_20_to_21_checkpoint_state",
    retention_operation=(
        "load_exact_saved_v065_private_checkpoint_and_issue_fresh_request_with_zero_new_successor_lessons"
    ),
    checkpoint_roles={
        "retained_repair": "exact_v065_taught_repair_checkpoint",
        "valid_null": "exact_v065_valid_null_checkpoint",
        "no_repair_control": "exact_v065_no_repair_control_checkpoint",
        "wrong_link_control": "exact_v065_wrong_link_control_checkpoint",
    },
    shared_prerequisites=(
        "unchanged_25_correct_v058_lessons_and_correct_v061_operand_order_instruction"
    ),
    control_difference="only_the_already_saved_three_terminal_successor_slots",
    teaching_cost={
        "saved_lesson_slots_per_role": 29,
        "new_successor_lessons_per_role": 0,
        "new_teacher_exposures_per_role": 0,
        "new_claim_installations_per_role": 0,
        "historical_correct_successor_claims_retained_or_null": 3,
        "historical_successor_claims_no_repair": 0,
        "historical_wrong_successor_claims_wrong_control": 3,
    },
    freshness_audit=(
        "both_orders_of_every_zero_to_twenty_one_pair_with_an_unchanged_zero_to_four_mapping_checked_"
        "against_183_consumed_raw_projections_and_31_recorded_probes"
    ),
    fresh_unordered_pairs=_AVAILABLE_UNORDERED,
    fresh_completion_limit=(
        "no_fresh_completion_bearing_successor_repair_case_remains_in_zero_to_twenty_one;_4_plus_18_"
        "uses_18_to_19_to_20_to_21_then_must_abstain_missing_at_21_and_4_plus_21_starts_at_the_ceiling"
    ),
    input_contract="strict_bounded_original_order_request_plus_run_and_case_provenance_only",
    response_contract={
        "records_per_role": 20,
        "original_request": "exact_typed_original_order_never_overwritten",
        "effective_request": "unchanged_v061_original_or_one_authorized_transposition",
        "native_evidence": (
            "checkpoint_and_private_kernel_fingerprints", "local_run_and_case_refs",
            "order_instruction_and_original_mapping_lookups", "addition_and_counting_rule_evidence",
            "every_retained_successor_claim_and_evidence_ref", "complete_partial_walk",
            "blocking_lookup_and_typed_rejection_metadata",
        ),
        "behavioral_inputs_excluded": (
            "case_group", "freshness_class", "expected_answer", "external_grade",
            "historical_effect_anchor", "result_conditioned_rule",
        ),
        "sorting_retry_numeric_reconstruction_or_evaluator_arithmetic": False,
    },
    cases_per_role=20,
    accepted_inputs_per_role=12,
    invalid_inputs_per_role=8,
    response_order="all_80_native_response_or_rejection_records_saved_before_any_of_48_external_grades",
    scoring="unchanged_v058_external_exact_sum_of_original_operands_after_saved_response_batch_only",
    invalid_handling="retain_original_typed_JSON_and_validation_errors_ungraded_in_full_denominator",
    missing_handling="retain_route_partial_walk_and_blocking_lookup_without_retry_replacement_or_credit",
    full_denominators="20_enrolled_and_12_valid_per_role_including_abstentions_and_invalids",
    null="complete_retained_repair_and_valid_null_records_must_match_apart_from_outer_role",
    next_dependency=(
        "optional_separate_response_and_evaluation_runner_for_partial_trace_retention_only;_otherwise_pause_"
        "the_zero_to_twenty_one_line_without_recycling_or_widening"
    ),
    teacher_source_class="self_declared_human_testimony",
    trust_limits="local_hashes_and_replay_do_not_authenticate_teacher_truth_freeze_time_or_independence",
    outcome_conditioned_selection_tuning_or_replacement_permitted=False,
    canonical_input_mutation_permitted=False,
    attention_allocation_permitted=False,
    obligation_simulation_permitted=False,
)

_FALSE_FLAGS = (
    "prospective_runner_implemented", "prospective_checkpoint_loaded",
    "new_successor_lesson_installed", "prospective_cohort_executed",
    "responses_observed", "evaluation_completed", "retained_reuse_observed",
    "fresh_correct_answer_transfer_observed", "causal_self_repair_observed",
    "spontaneous_rule_discovery_observed", "generalized_arithmetic_claim_permitted",
    "mathematical_understanding_claim_permitted", "learning_efficiency_observed",
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "independent_replication_observed", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled",
    "policy_rewrite_authority_enabled",
)


class SuccessorRetentionProtocolIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """A retention declaration lost its frozen lineage, cases or boundaries."""


class BoundedAdditionRequestV066(FrozenRecord):
    left: _BoundedNumber
    right: _BoundedNumber


class RetentionCase(FrozenRecord):
    case_id: _Ref
    group: Literal[
        "retained_prerequisite_control", "retained_partial_walk",
        "declared_domain_ceiling", "invalid_input",
    ]
    order_pair: _Ref | None
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


class ArtifactRef(FrozenRecord):
    path: _Ref
    sha256: _Digest


class CheckpointLineage(FrozenRecord):
    future_role: Literal[
        "retained_repair", "no_repair_control", "valid_null", "wrong_link_control"
    ]
    source_role: Literal[
        "taught_repair", "no_repair_control", "valid_null", "wrong_link_control"
    ]
    source_local_run_ref: _Ref
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lesson_trace_sha256: _Digest
    saved_lesson_slots: Literal[29] = 29
    historical_successor_claims: Annotated[StrictInt, Field(ge=0, le=3)]
    new_successor_lessons: Literal[0] = 0
    new_teacher_exposures: Literal[0] = 0

    @model_validator(mode="after")
    def check_role(self):
        if _SOURCE_ROLES[self.future_role] != self.source_role:
            raise ValueError("Checkpoint lineage changed its exact v0.65 source role.")
        expected = 0 if self.source_role == "no_repair_control" else 3
        if self.historical_successor_claims != expected:
            raise ValueError("Checkpoint lineage changed its historical successor cost.")
        return self


class HistoricalEffectAnchor(FrozenRecord):
    case_ref: _Ref
    original_request: repair_adapter.BoundedAdditionRequestV064
    taught_response_sha256: _Digest
    taught_grade_sha256: _Digest
    null_response_sha256: _Digest
    null_grade_sha256: _Digest
    no_repair_response_sha256: _Digest
    no_repair_grade_sha256: _Digest
    retained_steps: tuple[repair_adapter.BoundedCountingStepV064, ...] = Field(
        min_length=1, max_length=2
    )
    expected_answer: Literal[21] = 21
    taught_grade: Literal["correct"] = "correct"
    no_repair_grade: Literal["abstained"] = "abstained"

    @model_validator(mode="after")
    def check_anchor(self):
        if self.original_request.left + self.original_request.right != 21:
            raise ValueError("Historical retention anchor lost its frozen target.")
        links = tuple((step.from_number, step.to_number) for step in self.retained_steps)
        if links not in (((20, 21),), ((19, 20), (20, 21))):
            raise ValueError("Historical retention anchor lost supplied native steps.")
        return self


class HistoricalOutcome(FrozenRecord):
    role: Literal[
        "taught_repair", "no_repair_control", "valid_null", "wrong_link_control"
    ]
    correct: Annotated[StrictInt, Field(ge=0, le=32)]
    incorrect: Annotated[StrictInt, Field(ge=0, le=32)]
    abstained: Annotated[StrictInt, Field(ge=0, le=32)]
    invalid_ungraded: Literal[8] = 8
    enrolled: Literal[40] = 40
    valid: Literal[32] = 32


class Boundaries(FrozenRecord):
    prospective_runner_implemented: StrictBool = False
    prospective_checkpoint_loaded: StrictBool = False
    new_successor_lesson_installed: StrictBool = False
    prospective_cohort_executed: StrictBool = False
    responses_observed: StrictBool = False
    evaluation_completed: StrictBool = False
    retained_reuse_observed: StrictBool = False
    fresh_correct_answer_transfer_observed: StrictBool = False
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
    def check_boundaries(self):
        if any(getattr(self, name) for name in _FALSE_FLAGS):
            raise ValueError("A retention protocol supplies no response, effect or authority.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise SuccessorRetentionProtocolIntegrityError("Retention source exceeds the size bound.")
    return data


def _parse(data):
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise SuccessorRetentionProtocolIntegrityError("Retention source must have canonical bytes.")
    return raw


def _validated_history():
    data, raw = [], []
    for path, digest in _HISTORY:
        current = _read(_ROOT / path)
        if baseline._sha(current) != digest:
            raise SuccessorRetentionProtocolIntegrityError("A pinned terminal-successor artifact changed.")
        data.append(current)
        raw.append(_parse(current))
    protocol = repair_protocol.SuccessorRepairProtocolEnvelope.model_validate(raw[0])
    implementation = repair_adapter.RepairAdapterImplementationEnvelope.model_validate(raw[1])
    responses = repair_evaluation.ResponseBatchEnvelope.model_validate(raw[2])
    result = repair_evaluation.EvaluationEnvelope.model_validate(raw[3])
    if (
        protocol.declaration_sha256 != _INTERNAL_HASHES["protocol_declaration"]
        or implementation.receipt_sha256 != _INTERNAL_HASHES["implementation_receipt"]
        or responses.receipt_sha256 != _INTERNAL_HASHES["response_receipt"]
        or result.receipt_sha256 != _INTERNAL_HASHES["evaluation_receipt"]
        or implementation.receipt.frozen_protocol != protocol
        or responses.receipt.frozen_protocol != protocol
        or responses.receipt.frozen_implementation != implementation
        or result.receipt.response_batch_receipt_sha256 != responses.receipt_sha256
        or result.receipt.response_batch_file_sha256 != baseline._sha(data[2])
    ):
        raise SuccessorRetentionProtocolIntegrityError("The v0.63-v0.65 chain lost exact pairing.")
    counts = (
        len(protocol.declaration.code_sources),
        len(implementation.receipt.code_sources),
        len(responses.receipt.code_sources),
        len(result.receipt.code_sources),
    )
    if counts != (43, 46, 49, 49):
        raise SuccessorRetentionProtocolIntegrityError("A preserved terminal code manifest changed.")
    if responses.receipt.code_sources != result.receipt.code_sources:
        raise SuccessorRetentionProtocolIntegrityError("Response and grade code identities diverged.")
    return tuple(data), protocol, implementation, responses, result


def _exclusions(history):
    protocol = history[1]
    values = set(protocol.declaration.excluded_raw_requests)
    values.update(case.raw_request_json for case in protocol.declaration.cases)
    return tuple(sorted(values))


def _available_pairs(excluded):
    available = []
    for low in range(5):
        for high in range(low, 22):
            original = canonical_json_bytes({"left": low, "right": high}).decode()
            reversed_raw = canonical_json_bytes({"left": high, "right": low}).decode()
            if original not in excluded and reversed_raw not in excluded:
                available.append((low, high))
    return tuple(available)


def _cases():
    return tuple(
        RetentionCase(
            case_id=f"math-v066:case:{index}",
            group=group,
            order_pair=pair,
            raw_request_json=canonical_json_bytes(raw).decode(),
        )
        for index, (group, pair, raw) in enumerate(_ROWS)
    )


def _checkpoint_lineage(history):
    responses = history[3]
    arms = {arm.role: arm for arm in responses.receipt.arms}
    lineage = []
    for future_role in _ROLES:
        source_role = _SOURCE_ROLES[future_role]
        arm = arms[source_role]
        lineage.append(CheckpointLineage(
            future_role=future_role,
            source_role=source_role,
            source_local_run_ref=arm.local_run_ref,
            checkpoint_sha256=arm.checkpoint_sha256,
            kernel_fingerprint=arm.kernel_fingerprint,
            lesson_trace_sha256=baseline._sha(canonical_json_bytes(
                [lesson.model_dump(mode="json") for lesson in arm.lessons]
            )),
            historical_successor_claims=0 if source_role == "no_repair_control" else 3,
        ))
    if lineage[0].checkpoint_sha256 != lineage[2].checkpoint_sha256:
        raise SuccessorRetentionProtocolIntegrityError("Taught and exact-null checkpoints diverged.")
    return tuple(lineage)


def _grade_hash(grade):
    return baseline._sha(canonical_json_bytes(grade.model_dump(mode="json")))


def _effect_anchors(history):
    responses, result = history[3], history[4]
    arms = {arm.role: arm for arm in responses.receipt.arms}
    by_role = {
        role: {response.case_ref: response for response in arm.responses}
        for role, arm in arms.items()
    }
    grades = {(grade.role, grade.case_ref): grade for grade in result.receipt.grades}
    anchors = []
    for taught in arms["taught_repair"].responses:
        if taught.case.group != "repair_supported":
            continue
        case_ref = taught.case_ref
        null = by_role["valid_null"][case_ref]
        control = by_role["no_repair_control"][case_ref]
        taught_grade = grades[("taught_repair", case_ref)]
        null_grade = grades[("valid_null", case_ref)]
        control_grade = grades[("no_repair_control", case_ref)]
        if (
            taught.reply.answer != 21
            or null.reply.answer != 21
            or control.reply.answer is not None
            or taught_grade.grade != "correct"
            or null_grade.grade != "correct"
            or control_grade.grade != "abstained"
        ):
            raise SuccessorRetentionProtocolIntegrityError("A v0.65 supplied-repair effect changed.")
        anchors.append(HistoricalEffectAnchor(
            case_ref=case_ref,
            original_request=taught.request,
            taught_response_sha256=repair_evaluation._response_hash(taught),
            taught_grade_sha256=_grade_hash(taught_grade),
            null_response_sha256=repair_evaluation._response_hash(null),
            null_grade_sha256=_grade_hash(null_grade),
            no_repair_response_sha256=repair_evaluation._response_hash(control),
            no_repair_grade_sha256=_grade_hash(control_grade),
            retained_steps=taught.reply.addition_reply.counting_reply.steps,
        ))
    if len(anchors) != 4:
        raise SuccessorRetentionProtocolIntegrityError("Expected four exact v0.65 repair effects.")
    return tuple(anchors)


def _historical_outcomes(history):
    responses, result = history[3], history[4]
    expected = {
        "taught_repair": (20, 0, 12),
        "no_repair_control": (16, 0, 16),
        "valid_null": (20, 0, 12),
        "wrong_link_control": (16, 2, 14),
    }
    outcomes = []
    for arm in responses.receipt.arms:
        grades = [grade for grade in result.receipt.grades if grade.role == arm.role]
        counts = tuple(sum(grade.grade == name for grade in grades) for name in (
            "correct", "incorrect", "abstained"
        ))
        invalid = sum(response.request is None for response in arm.responses)
        if counts != expected[arm.role] or invalid != 8:
            raise SuccessorRetentionProtocolIntegrityError("A complete v0.65 outcome changed.")
        outcomes.append(HistoricalOutcome(
            role=arm.role,
            correct=counts[0],
            incorrect=counts[1],
            abstained=counts[2],
        ))
    return tuple(outcomes)


def _code_manifest(history):
    sources = {source.path: source for source in history[3].receipt.code_sources}
    if tuple(sources[name] for name in sorted(sources)) != history[3].receipt.code_sources:
        raise SuccessorRetentionProtocolIntegrityError("The v0.65 response manifest is not canonical.")
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_successor_retention_kernel():
    return VerdantKernel(seed=79066, state_dim=16, run_label="math-successor-retention-v066")


class SuccessorRetentionProtocol(Boundaries):
    protocol: dict
    cases: tuple[RetentionCase, ...] = Field(min_length=20, max_length=20)
    checkpoint_lineage: tuple[CheckpointLineage, ...] = Field(min_length=4, max_length=4)
    historical_effect_anchors: tuple[HistoricalEffectAnchor, ...] = Field(min_length=4, max_length=4)
    historical_outcomes: tuple[HistoricalOutcome, ...] = Field(min_length=4, max_length=4)
    prior_artifacts: tuple[ArtifactRef, ...] = Field(min_length=4, max_length=4)
    audit_sources: tuple[baseline.MathCodeDigest, ...] = Field(min_length=10, max_length=10)
    probe_exclusions: tuple[repair_protocol.ProbeExclusion, ...] = Field(min_length=31, max_length=31)
    excluded_raw_requests: tuple[StrictStr, ...] = Field(min_length=183, max_length=183)
    code_sources: tuple[baseline.MathCodeDigest, ...] = Field(min_length=52, max_length=52)
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    fresh_completion_bearing_case_available: Literal[False] = False
    purpose: Literal["prospective_zero_new_lesson_successor_retention_protocol"] = (
        "prospective_zero_new_lesson_successor_retention_protocol"
    )

    @model_validator(mode="after")
    def check_protocol(self):
        expected_artifacts = tuple(ArtifactRef(path=path, sha256=digest) for path, digest in _HISTORY)
        if (
            canonical_json_bytes(self.protocol) != canonical_json_bytes(_SPEC)
            or self.cases != _cases()
            or self.prior_artifacts != expected_artifacts
        ):
            raise ValueError("Retention protocol lost its cost, controls, cases or history.")
        if self.excluded_raw_requests != tuple(sorted(set(self.excluded_raw_requests))):
            raise ValueError("Retention exclusions must be complete and canonical.")
        if _available_pairs(set(self.excluded_raw_requests)) != _AVAILABLE_UNORDERED:
            raise ValueError("Retention freshness audit no longer yields the exact six pairs.")
        counts = {
            "retained_prerequisite_control": 0,
            "retained_partial_walk": 0,
            "declared_domain_ceiling": 0,
            "invalid_input": 0,
        }
        seen, pairs = set(), {}
        for case in self.cases:
            raw = json.loads(case.raw_request_json, object_pairs_hook=baseline._unique_object)
            if case.raw_request_json != canonical_json_bytes(raw).decode() or case.raw_request_json in seen:
                raise ValueError("Retention cases must be canonical and distinct.")
            seen.add(case.raw_request_json)
            if case.raw_request_json in self.excluded_raw_requests:
                raise ValueError("A retention case reuses a consumed request or probe.")
            try:
                request = BoundedAdditionRequestV066.model_validate(raw)
                valid = True
            except ValidationError:
                request, valid = None, False
            if valid == (case.group == "invalid_input"):
                raise ValueError("Retention case validity does not match its frozen group.")
            counts[case.group] += 1
            if not valid:
                if case.order_pair is not None:
                    raise ValueError("Invalid retention cases cannot invent order pairs.")
                continue
            if min(request.left, request.right) > 4:
                raise ValueError("A valid retention case lacks an unchanged operand mapping.")
            reversed_raw = canonical_json_bytes({"left": request.right, "right": request.left}).decode()
            if reversed_raw in self.excluded_raw_requests:
                raise ValueError("A routed retention form reuses consumed evidence.")
            pair = tuple(sorted((request.left, request.right)))
            pairs.setdefault(case.order_pair, []).append(request)
            if pair == (4, 18) and case.group != "retained_partial_walk":
                raise ValueError("The only retained partial-walk pair changed group.")
            if pair == (4, 21) and case.group != "declared_domain_ceiling":
                raise ValueError("The declared ceiling pair changed group.")
            if pair not in ((4, 18), (4, 21)) and case.group != "retained_prerequisite_control":
                raise ValueError("A fresh prerequisite control changed group.")
        if counts != {
            "retained_prerequisite_control": 8,
            "retained_partial_walk": 2,
            "declared_domain_ceiling": 2,
            "invalid_input": 8,
        }:
            raise ValueError("Retention case groups or full denominators changed.")
        if any(
            len(values) != 2
            or values[0].left != values[1].right
            or values[0].right != values[1].left
            for values in pairs.values()
        ):
            raise ValueError("Retention order pairs lost exact transposition.")
        return self


class SuccessorRetentionProtocolEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-successor-retention-protocol-v1"] = (
        "verdant-successor-retention-protocol-v1"
    )
    declaration: SuccessorRetentionProtocol
    declaration_sha256: _Digest

    @classmethod
    def build(cls, declaration):
        checked = SuccessorRetentionProtocol.model_validate(declaration.model_dump(mode="json"))
        return cls(
            declaration=checked,
            declaration_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))),
        )

    @model_validator(mode="after")
    def check_hash(self):
        expected = baseline._sha(canonical_json_bytes(self.declaration.model_dump(mode="json")))
        if self.declaration_sha256 != expected:
            raise ValueError("Successor-retention declaration checksum mismatch.")
        return self


def freeze_successor_retention_protocol(source=None):
    """Pure declaration: no checkpoint load, teaching, response, grade or simulation."""
    source = fresh_successor_retention_kernel() if source is None else source
    before, snapshot = source.fingerprint(), source.snapshot()
    if before != fresh_successor_retention_kernel().fingerprint():
        raise SuccessorRetentionProtocolIntegrityError("Retention source must be the exact fresh checkpoint.")
    history = _validated_history()
    historical_bytes = history[0]
    exclusions = _exclusions(history)
    if len(exclusions) != 183 or _available_pairs(set(exclusions)) != _AVAILABLE_UNORDERED:
        raise SuccessorRetentionProtocolIntegrityError("Consumed-request audit lost its exact closure.")
    audit = tuple(
        baseline.MathCodeDigest(path=path, sha256=baseline._sha(_read(_ROOT / path)))
        for path in _AUDIT_FILES
    )
    manifest = _code_manifest(history)
    source_bytes = checkpoint_bytes(snapshot)
    envelope = SuccessorRetentionProtocolEnvelope.build(SuccessorRetentionProtocol(
        protocol=_SPEC,
        cases=_cases(),
        checkpoint_lineage=_checkpoint_lineage(history),
        historical_effect_anchors=_effect_anchors(history),
        historical_outcomes=_historical_outcomes(history),
        prior_artifacts=tuple(ArtifactRef(path=path, sha256=digest) for path, digest in _HISTORY),
        audit_sources=audit,
        probe_exclusions=history[1].declaration.probe_exclusions,
        excluded_raw_requests=exclusions,
        code_sources=manifest,
        source_checkpoint_base64=base64.b64encode(source_bytes).decode(),
        source_checkpoint_sha256=baseline._sha(source_bytes),
        source_kernel_fingerprint=before,
    ))
    current = _validated_history()
    current_audit = tuple(
        baseline.MathCodeDigest(path=path, sha256=baseline._sha(_read(_ROOT / path)))
        for path in _AUDIT_FILES
    )
    if (
        source.fingerprint() != before
        or source.snapshot() != snapshot
        or current[0] != historical_bytes
        or current_audit != audit
        or _code_manifest(current) != manifest
    ):
        raise SuccessorRetentionProtocolIntegrityError("Source, history, audit or code changed during freeze.")
    return envelope


def _validate(envelope):
    checked = SuccessorRetentionProtocolEnvelope.model_validate(envelope.model_dump(mode="json"))
    source = baseline._checkpoint(
        checked.declaration.source_checkpoint_base64,
        checked.declaration.source_checkpoint_sha256,
    )
    if checked != freeze_successor_retention_protocol(source):
        raise SuccessorRetentionProtocolIntegrityError("Retention protocol failed exact reconstruction.")
    return checked


def save_successor_retention_protocol(path, envelope):
    checked = _validate(envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRetentionProtocolIntegrityError("Retention protocol exceeds the size bound.")
    protected = tuple(_ROOT / name for name, _ in _HISTORY)
    protected += tuple(_ROOT / name for name in _AUDIT_FILES)
    protected += tuple(_ROOT / source.path for source in checked.declaration.code_sources)
    if Path(path).resolve() in {item.resolve() for item in protected}:
        raise SuccessorRetentionProtocolIntegrityError("Cannot publish over retention evidence, audit or code.")
    baseline._write_immutable(Path(path), data)
    return baseline._sha(data)


def load_successor_retention_protocol(path):
    return _validate(SuccessorRetentionProtocolEnvelope.model_validate(_parse(_read(path))))


def protocol_summary(envelope):
    checked = _validate(envelope)
    return dict(
        status="prospective_zero_new_lesson_successor_retention_protocol_only",
        declaration_sha256=checked.declaration_sha256,
        excluded_raw_requests=183,
        fresh_unordered_pairs=6,
        fresh_completion_bearing_cases=0,
        cases_per_role=20,
        valid_inputs_per_role=12,
        invalid_inputs_per_role=8,
        prospective_roles=4,
        new_successor_lessons_per_role=0,
        **{name: False for name in _FALSE_FLAGS},
    )
