"""Freeze a bounded terminal-successor repair study before implementation.

The declaration is grounded in the eight retained v0.62 missing-successor
traces.  It defines a versioned 0..21 schema, supplied testimony, controls and
fresh cases, but it never installs a lesson, answers a case, grades or simulates.
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
from verdant_math.addition import pilot as addition
from verdant_math.counting import pilot as counting
from verdant_math.ordering_adapter import adapter
from verdant_math.ordering_evaluation import evaluation
from verdant_math.ordering_protocol import protocol as ordering

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_BoundedNumber = Annotated[StrictInt, Field(ge=0, le=21)]

_HISTORY = (
    ("artifacts/arithmetic_teaching_v056/pilot.vmp", "36548d730ffbfa8e3dbf09436047f79c0e2ff1672fb72999242b16458361321d"),
    ("artifacts/counting_teaching_v057/pilot.vcount", "dd93ba95dd5e556541e57dfbaf9e4f8fb486547f401d4e07c7b47c8a0227fe2c"),
    ("artifacts/scaffold_addition_v058/pilot.vadd", "148586a8d060d92afa991135ad8393ea9c87f6a11c76bc797b3c12af10c2254c"),
    ("artifacts/addition_coverage_v059/challenge.vacp", "d01dd5280a1bba38342b5305e552b3eacaf12f68d12d0d64230460a0822f0fbf"),
    ("artifacts/addition_coverage_v059/evaluation.vacr", "853da03a48bf68905f4eb2b46433e9e1958a98a515d192f53e7bb68faa81840e"),
    ("artifacts/operand_order_v060/protocol.vaop", "09c6d2e0c914aa8fb8f256d59cf6ba81bfda87345413b68817bb6515dec39407"),
    ("artifacts/operand_order_v061/implementation.vaoi", "05e8878f7a87c8be748e00c25608688f7ec87ab9345cc17e5caf24666699e64f"),
    ("artifacts/operand_order_v062/responses.vaob", "25f75c01332bff48e46c521eb966f9c8634620542aa6e2126236d378126f70e4"),
    ("artifacts/operand_order_v062/evaluation.vaor", "2ec22c550b17e1f7a3ca91df21ba06ab8dc7d1d11f8d70e3e2117d8c7f419bd1"),
)
_PROBE_FILES = (
    "tests/test_math_teaching_pilot.py",
    "tests/test_counting_teaching_pilot.py",
    "tests/test_scaffold_addition_pilot.py",
    "tests/test_addition_coverage_challenge.py",
    "tests/test_operand_order_protocol.py",
    "tests/test_operand_order_adapter.py",
    "tests/test_operand_order_evaluation.py",
)
_ADAPTER_PROBES = ((9, 3), (3, 9), (13, 1), (1, 13), (6, 6), (16, 3), (18, 1), (9, 5))
_CORRECT_SUCCESSORS = ((18, 19), (19, 20), (20, 21))
_WRONG_SUCCESSORS = ((18, 20), (19, 21), (20, 18))

_PRE_BOUNDARY = (
    (9, 2), (12, 1), (11, 2), (14, 1), (15, 1),
    (13, 3), (15, 2), (14, 4), (16, 1), (13, 4),
)
_NEW_DOMAIN_ZERO = ((19, 0), (0, 19), (20, 0), (0, 20), (21, 0), (0, 21))
_REPAIR_SUPPORTED = ((20, 1), (1, 20), (19, 2), (2, 19))
_DOMAIN_CEILING = (
    (21, 1), (1, 21), (21, 2), (2, 21), (20, 3), (3, 20),
    (19, 4), (4, 19), (21, 3), (3, 21), (20, 4), (4, 20),
)
_INVALID = (
    {"left": 19, "right": True},
    {"left": None, "right": 1},
    {"left": 20, "right": "1"},
    {"left": 21, "right": 0.5},
    {"left": 22, "right": 0},
    {"left": 19},
    {"left": 19, "right": 0, "answer": 19},
    {"left": [20], "right": 0},
)
_ROWS = (
    *(("pre_boundary_control", None, {"left": left, "right": right})
      for left, right in _PRE_BOUNDARY),
    *(("new_domain_zero_identity", f"zero-{max(left, right)}", {"left": left, "right": right})
      for left, right in _NEW_DOMAIN_ZERO),
    *(("repair_supported", f"repair-{min(left, right)}-{max(left, right)}", {"left": left, "right": right})
      for left, right in _REPAIR_SUPPORTED),
    *(("declared_domain_ceiling", f"ceiling-{min(left, right)}-{max(left, right)}", {"left": left, "right": right})
      for left, right in _DOMAIN_CEILING),
    *(("invalid_input", None, raw) for raw in _INVALID),
)
_ROLES = ("taught_repair", "no_repair_control", "valid_null", "wrong_link_control")
_DOMAIN = dict(
    schema_version="bounded_successor_domain_v0.63",
    integer_minimum=0,
    integer_maximum=21,
    predecessor_schema_maximum=18,
    request_operands="strict_integers_zero_through_twenty_one",
    answer_and_step_endpoints="strict_integers_zero_through_twenty_one_or_none",
    counting_tokens="unchanged_zero_to_four_literal_tick_tokens",
    exact_teacher_successors=_CORRECT_SUCCESSORS,
    wrong_link_control_successors=_WRONG_SUCCESSORS,
    successor_at_21="missing_and_visible_no_silent_domain_widening",
    implementation="future_versioned_sibling_types_and_interpreter_only",
    old_type_or_manifest_modification_permitted=False,
    numeric_successor_synthesis_permitted=False,
)
_SPEC = dict(
    version="teacher_scaffold_terminal_successor_protocol_v0.63",
    phase="prospective_protocol_only",
    grounded_parent_commit="741a136b5cab7d6f19462aa55d7920242ae074ef",
    grounded_parent_tree="50285126a711bf9947f1dddd9cc949629dd62c4c",
    source="fresh_seed_79063_state_dim_16_run_label_math-successor-repair-v063",
    roles=_ROLES,
    bounded_domain=_DOMAIN,
    historical_anchor=(
        "eight_taught_v062_terminal_link_records_abstain_at_missing_math_integer_18_successor;"
        "their_exact_null_records_match_and_their_external_expected_answers_require_values_19_through_21"
    ),
    freshness_limit=(
        "every_unchanged_v058_addition_request_at_or_below_18_that_crosses_the_18_boundary_has_an_original_or_"
        "authorized_transposed_form_already_consumed;_v062_traces_anchor_18_to_19_while_fresh_cases_test_"
        "19_to_20_20_to_21_and_the_declared_21_ceiling"
    ),
    shared_prerequisite=(
        "same_25_correct_v058_lessons_plus_same_correct_v061_operand_order_instruction_in_every_private_role"
    ),
    repair_slots="three_teacher_successor_claims_or_three_matched_prompt_slots_only",
    taught_repair="install_exact_human_testimony_18_to_19_19_to_20_20_to_21",
    valid_null="distinct_pristine_private_copy_exact_taught_operations_and_complete_records",
    no_repair_control="same_prerequisites_three_prompt_slots_no_successor_claims",
    wrong_link_control="same_prerequisites_three_fixed_wrong_testimony_claims_18_to_20_19_to_21_20_to_18",
    control_difference="only_the_three_terminal_successor_slots_not_ordering_addition_tokens_or_old_successors",
    teacher_source_class="human_testimony",
    declared_source="declared-terminal-successor-teacher://v063",
    input_contract="versioned_strict_bounded_addition_request_original_order_no_targets_groups_or_grades",
    response_contract={
        "records_per_role": 40,
        "original_request": "exact_validated_original_order_never_overwritten",
        "effective_request": "unchanged_v061_original_or_one_authorized_transposition",
        "native_evidence": (
            "local_run_and_case_refs", "private_kernel_fingerprint", "all_29_lesson_traces",
            "order_instruction_and_both_mapping_lookups_if_applicable", "addition_rule_and_operand_mapping",
            "counting_rule", "every_versioned_successor_step_claim_and_evidence_ref",
            "complete_partial_walk_and_blocking_lookup_refs",
        ),
        "terminal_ceiling": "missing_successor_at_21_retained_as_abstention_without_answer_credit",
        "case_group_expected_answer_grade_or_historical_anchor_as_behavioral_inputs": False,
        "numeric_token_or_successor_reconstruction": False,
        "sorting_recursive_retry_or_fallback_arithmetic": False,
    },
    cases_per_role=40,
    accepted_inputs_per_role=32,
    invalid_inputs_per_role=8,
    response_order="all_160_native_response_or_rejection_records_saved_before_any_of_128_external_grades",
    scoring="separate_versioned_external_exact_sum_of_original_operands_after_saved_response_batch_only",
    invalid_handling="retain_original_typed_JSON_and_validation_errors_ungraded_in_full_denominator",
    missing_handling="retain_original_slot_route_partial_walk_and_blocking_lookup_no_replacement_or_credit",
    full_denominators="40_enrolled_and_32_valid_per_role_including_abstentions_and_invalids",
    prospective_groups=(
        "pre_boundary_control", "new_domain_zero_identity", "repair_supported",
        "declared_domain_ceiling", "invalid_input",
    ),
    next_dependency=(
        "separate_versioned_private_copy_repair_adapter_and_native_trace_verifier_before_any_cohort_execution"
    ),
    trusted_components="local_runtime_filesystem_and_native_replay_code",
    trust_limits="hashes_labels_and_replay_do_not_authenticate_teacher_truth_freeze_time_or_independence",
    outcome_conditioned_selection_tuning_or_replacement_permitted=False,
    canonical_input_mutation_permitted=False,
    attention_allocation_permitted=False,
    obligation_simulation_permitted=False,
)
_FALSE_FLAGS = (
    "repair_adapter_implemented", "repair_testimony_installed", "prospective_cohort_executed",
    "responses_observed", "evaluation_completed", "repair_effect_observed",
    "causal_self_repair_observed", "spontaneous_rule_discovery_observed",
    "generalized_arithmetic_claim_permitted", "mathematical_understanding_claim_permitted",
    "learning_efficiency_observed", "source_authenticated", "physical_evidence_admissible",
    "harm_scoring_implemented", "independent_replication_observed", "canonical_commit_permitted",
    "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled",
)


class SuccessorRepairProtocolIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """A repair declaration lost its frozen sources, cases or boundaries."""


class BoundedAdditionRequestV063(FrozenRecord):
    left: _BoundedNumber
    right: _BoundedNumber


class RepairCase(FrozenRecord):
    case_id: _Ref
    group: Literal[
        "pre_boundary_control", "new_domain_zero_identity", "repair_supported",
        "declared_domain_ceiling", "invalid_input",
    ]
    order_pair: _Ref | None
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


class ArtifactRef(FrozenRecord):
    path: _Ref
    sha256: _Digest


class ProbeExclusion(FrozenRecord):
    api: Literal["fact_recall", "counting", "addition"]
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


class FailureAnchor(FrozenRecord):
    case_ref: _Ref
    order_pair: _Ref
    response_sha256: _Digest
    grade_sha256: _Digest
    original_request: addition.AdditionRequest
    effective_request: addition.AdditionRequest
    route_disposition: Literal["kept_valid_original_right", "swapped_missing_original_right"]
    partial_steps: tuple[counting.CountingStep, ...] = Field(max_length=2)
    missing_subject: Literal["math:integer:18"] = "math:integer:18"
    blocking_claim_refs: tuple[_Ref, ...]
    blocking_evidence_refs: tuple[_Ref, ...]
    expected_answer: Annotated[StrictInt, Field(ge=19, le=21)]
    grade: Literal["abstained"] = "abstained"

    @model_validator(mode="after")
    def check_anchor(self):
        terminal = self.partial_steps[-1].to_number if self.partial_steps else self.effective_request.left
        if terminal != 18 or self.expected_answer != self.original_request.left + self.original_request.right:
            raise ValueError("Historical failure anchor lost its terminal endpoint or preserved external grade.")
        if self.blocking_claim_refs or self.blocking_evidence_refs:
            raise ValueError("A genuinely missing successor cannot invent blocking evidence.")
        return self


class Boundaries(FrozenRecord):
    repair_adapter_implemented: StrictBool = False
    repair_testimony_installed: StrictBool = False
    prospective_cohort_executed: StrictBool = False
    responses_observed: StrictBool = False
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
    def check_boundaries(self):
        if any(getattr(self, name) for name in _FALSE_FLAGS):
            raise ValueError("A prospective repair protocol supplies no execution, effect or authority.")
        return self


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairProtocolIntegrityError("Successor-repair source exceeds the size bound.")
    return data


def _parse(data):
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise SuccessorRepairProtocolIntegrityError("Successor-repair source must have canonical bytes.")
    return raw


def _validated_history():
    data = []
    for path, digest in _HISTORY:
        current = _read(_ROOT / path)
        if baseline._sha(current) != digest:
            raise SuccessorRepairProtocolIntegrityError("A pinned historical artifact changed.")
        _parse(current)
        data.append(current)
    protocol_path, implementation_path, response_path, result_path = (
        _ROOT / _HISTORY[index][0] for index in range(5, 9)
    )
    frozen_protocol = ordering.load_operand_order_protocol(protocol_path)
    implementation = adapter.load_operand_order_adapter(protocol_path, implementation_path)
    responses = evaluation.load_response_batch(protocol_path, implementation_path, response_path)
    result = evaluation.load_evaluation(
        protocol_path, implementation_path, response_path, result_path
    )
    if (
        implementation.receipt.frozen_protocol != frozen_protocol
        or responses.receipt.frozen_protocol != frozen_protocol
        or responses.receipt.frozen_implementation != implementation
        or result.receipt.response_batch_receipt_sha256 != responses.receipt_sha256
        or result.receipt.response_batch_file_sha256 != baseline._sha(data[7])
    ):
        raise SuccessorRepairProtocolIntegrityError("The v0.60/v0.61/v0.62 chain lost exact pairing.")
    raw = tuple(_parse(item) for item in data)
    counts = (
        len(raw[0]["receipt"]["code_sources"]),
        len(raw[1]["receipt"]["code_sources"]),
        len(raw[2]["receipt"]["code_sources"]),
        len(raw[3]["plan"]["code_sources"]),
        len(frozen_protocol.declaration.code_sources),
        len(implementation.receipt.code_sources),
        len(responses.receipt.code_sources),
    )
    if counts != (22, 25, 28, 31, 34, 37, 40):
        raise SuccessorRepairProtocolIntegrityError("A preserved math code manifest changed.")
    return tuple(data), raw, frozen_protocol, implementation, responses, result


def _cases():
    return tuple(
        RepairCase(
            case_id=f"math-v063:case:{index}",
            group=group,
            order_pair=pair,
            raw_request_json=canonical_json_bytes(raw).decode(),
        )
        for index, (group, pair, raw) in enumerate(_ROWS)
    )


def _probes():
    values = {
        (probe["api"], canonical_json_bytes(probe["raw"]).decode())
        for probe in ordering._PROBES
    }
    values.update(
        ("addition", canonical_json_bytes({"left": left, "right": right}).decode())
        for left, right in _ADAPTER_PROBES
    )
    return tuple(
        ProbeExclusion(api=api, raw_request_json=raw)
        for api, raw in sorted(values)
    )


def _exclusions(history):
    frozen_protocol = history[2]
    raw = set(frozen_protocol.declaration.excluded_raw_requests)
    raw.update(case.raw_request_json for case in frozen_protocol.declaration.cases)
    raw.update(
        canonical_json_bytes({"left": left, "right": right}).decode()
        for left, right in _ADAPTER_PROBES
    )
    return tuple(sorted(raw))


def _failure_anchors(history):
    responses, result = history[4], history[5]
    taught = next(arm for arm in responses.receipt.arms if arm.role == "taught")
    grades = {grade.case_ref: grade for grade in result.receipt.grades if grade.role == "taught"}
    anchors = []
    for response in taught.responses:
        if response.case.group != "terminal_link":
            continue
        reply = response.reply
        nested = reply.addition_reply
        counted = nested.counting_reply
        grade = grades[response.case_ref]
        if (
            reply.answer is not None
            or nested.reason != "counting_abstained"
            or counted.reason != "missing_successor"
            or grade.grade != "abstained"
        ):
            raise SuccessorRepairProtocolIntegrityError("A v0.62 terminal anchor changed disposition.")
        anchors.append(FailureAnchor(
            case_ref=response.case_ref,
            order_pair=response.case.order_pair,
            response_sha256=evaluation._response_hash(response),
            grade_sha256=baseline._sha(canonical_json_bytes(grade.model_dump(mode="json"))),
            original_request=response.request,
            effective_request=reply.effective_request,
            route_disposition=reply.route_disposition,
            partial_steps=counted.steps,
            blocking_claim_refs=counted.blocked_claim_refs,
            blocking_evidence_refs=counted.blocked_evidence_refs,
            expected_answer=grade.expected_answer,
        ))
    if len(anchors) != 8 or max(anchor.expected_answer for anchor in anchors) != 21:
        raise SuccessorRepairProtocolIntegrityError("Expected eight bounded terminal anchors through 21.")
    return tuple(anchors)


def _code_manifest(history):
    sources = {source.path: source for source in history[4].receipt.code_sources}
    if tuple(sources[name] for name in sorted(sources)) != history[4].receipt.code_sources:
        raise SuccessorRepairProtocolIntegrityError("The v0.62 response manifest is not canonical.")
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_successor_repair_kernel():
    return VerdantKernel(seed=79063, state_dim=16, run_label="math-successor-repair-v063")


class SuccessorRepairProtocol(Boundaries):
    protocol: dict
    cases: tuple[RepairCase, ...] = Field(min_length=40, max_length=40)
    failure_anchors: tuple[FailureAnchor, ...] = Field(min_length=8, max_length=8)
    prior_artifacts: tuple[ArtifactRef, ...] = Field(min_length=9, max_length=9)
    probe_sources: tuple[baseline.MathCodeDigest, ...] = Field(min_length=7, max_length=7)
    probe_exclusions: tuple[ProbeExclusion, ...]
    excluded_raw_requests: tuple[StrictStr, ...]
    code_sources: tuple[baseline.MathCodeDigest, ...]
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    purpose: Literal["prospective_terminal_successor_repair_protocol"] = (
        "prospective_terminal_successor_repair_protocol"
    )

    @model_validator(mode="after")
    def check_protocol(self):
        expected_artifacts = tuple(ArtifactRef(path=path, sha256=digest) for path, digest in _HISTORY)
        if (
            canonical_json_bytes(self.protocol) != canonical_json_bytes(_SPEC)
            or self.cases != _cases()
            or self.probe_exclusions != _probes()
            or self.prior_artifacts != expected_artifacts
        ):
            raise ValueError("Successor-repair protocol lost its domain, controls, cases or history.")
        if self.excluded_raw_requests != tuple(sorted(set(self.excluded_raw_requests))):
            raise ValueError("Successor-repair exclusions must be complete and canonical.")
        seen = set()
        counts = {group: 0 for group in _SPEC["prospective_groups"]}
        pairs = {}
        for case in self.cases:
            raw = json.loads(case.raw_request_json, object_pairs_hook=baseline._unique_object)
            if case.raw_request_json != canonical_json_bytes(raw).decode() or case.raw_request_json in seen:
                raise ValueError("Successor-repair cases must be canonical and distinct.")
            seen.add(case.raw_request_json)
            if case.raw_request_json in self.excluded_raw_requests:
                raise ValueError("A successor-repair case reuses a consumed input or probe.")
            try:
                request = BoundedAdditionRequestV063.model_validate(raw)
                valid = True
            except ValidationError:
                request, valid = None, False
            if valid == (case.group == "invalid_input"):
                raise ValueError("Successor-repair case validity does not match its fixed group.")
            counts[case.group] += 1
            if not valid:
                continue
            reversed_raw = canonical_json_bytes({"left": request.right, "right": request.left}).decode()
            if reversed_raw in self.excluded_raw_requests:
                raise ValueError("A possible routed form reuses a consumed case or probe.")
            if min(request.left, request.right) > 4:
                raise ValueError("A case lacks an unchanged zero-to-four operand mapping.")
            total = request.left + request.right
            if case.group == "pre_boundary_control" and not (max(request.left, request.right) <= 18 and total <= 18):
                raise ValueError("Pre-boundary control crossed the predecessor domain.")
            if case.group == "new_domain_zero_identity" and not (min(request.left, request.right) == 0 and 19 <= total <= 21):
                raise ValueError("New-domain zero case changed its declared boundary.")
            if case.group == "repair_supported" and not (19 <= max(request.left, request.right) <= 20 and total <= 21):
                raise ValueError("Repair-supported case left the frozen repaired range.")
            if case.group == "declared_domain_ceiling" and not (total > 21):
                raise ValueError("Ceiling case no longer requires a visible missing successor.")
            if case.order_pair is not None:
                pairs.setdefault(case.order_pair, []).append(request)
        if counts != {
            "pre_boundary_control": 10,
            "new_domain_zero_identity": 6,
            "repair_supported": 4,
            "declared_domain_ceiling": 12,
            "invalid_input": 8,
        }:
            raise ValueError("Successor-repair case groups or full denominators changed.")
        if any(
            len(values) != 2
            or values[0].left != values[1].right
            or values[0].right != values[1].left
            for values in pairs.values()
        ):
            raise ValueError("Paired original/swapped requests lost exact transposition.")
        return self


class SuccessorRepairProtocolEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-terminal-successor-repair-protocol-v1"] = (
        "verdant-terminal-successor-repair-protocol-v1"
    )
    declaration: SuccessorRepairProtocol
    declaration_sha256: _Digest

    @classmethod
    def build(cls, declaration):
        checked = SuccessorRepairProtocol.model_validate(declaration.model_dump(mode="json"))
        return cls(
            declaration=checked,
            declaration_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))),
        )

    @model_validator(mode="after")
    def check_hash(self):
        expected = baseline._sha(canonical_json_bytes(self.declaration.model_dump(mode="json")))
        if self.declaration_sha256 != expected:
            raise ValueError("Successor-repair declaration checksum mismatch.")
        return self


def freeze_successor_repair_protocol(source=None):
    """Pure declaration: no lesson installation, response, grade or simulation."""
    source = fresh_successor_repair_kernel() if source is None else source
    before, snapshot = source.fingerprint(), source.snapshot()
    if before != fresh_successor_repair_kernel().fingerprint():
        raise SuccessorRepairProtocolIntegrityError("Successor-repair source must be the exact fresh checkpoint.")
    history = _validated_history()
    historical_bytes = history[0]
    probes = tuple(
        baseline.MathCodeDigest(path=path, sha256=baseline._sha(_read(_ROOT / path)))
        for path in _PROBE_FILES
    )
    manifest = _code_manifest(history)
    source_bytes = checkpoint_bytes(snapshot)
    envelope = SuccessorRepairProtocolEnvelope.build(SuccessorRepairProtocol(
        protocol=_SPEC,
        cases=_cases(),
        failure_anchors=_failure_anchors(history),
        prior_artifacts=tuple(ArtifactRef(path=path, sha256=digest) for path, digest in _HISTORY),
        probe_sources=probes,
        probe_exclusions=_probes(),
        excluded_raw_requests=_exclusions(history),
        code_sources=manifest,
        source_checkpoint_base64=base64.b64encode(source_bytes).decode(),
        source_checkpoint_sha256=baseline._sha(source_bytes),
        source_kernel_fingerprint=before,
    ))
    current = _validated_history()
    current_probes = tuple(
        baseline.MathCodeDigest(path=path, sha256=baseline._sha(_read(_ROOT / path)))
        for path in _PROBE_FILES
    )
    if (
        source.fingerprint() != before
        or source.snapshot() != snapshot
        or current[0] != historical_bytes
        or current_probes != probes
        or _code_manifest(current) != manifest
    ):
        raise SuccessorRepairProtocolIntegrityError("Source, evidence, probes or code changed during freeze.")
    return envelope


def _validate(envelope):
    checked = SuccessorRepairProtocolEnvelope.model_validate(envelope.model_dump(mode="json"))
    source = baseline._checkpoint(
        checked.declaration.source_checkpoint_base64,
        checked.declaration.source_checkpoint_sha256,
    )
    if checked != freeze_successor_repair_protocol(source):
        raise SuccessorRepairProtocolIntegrityError("Successor-repair protocol failed exact reconstruction.")
    return checked


def save_successor_repair_protocol(path, envelope):
    checked = _validate(envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise SuccessorRepairProtocolIntegrityError("Successor-repair protocol exceeds the size bound.")
    protected = tuple(_ROOT / path for path, _ in _HISTORY)
    protected += tuple(_ROOT / path for path in _PROBE_FILES)
    protected += tuple(_ROOT / source.path for source in checked.declaration.code_sources)
    if Path(path).resolve() in {item.resolve() for item in protected}:
        raise SuccessorRepairProtocolIntegrityError("Cannot publish over protocol evidence, probes or code.")
    baseline._write_immutable(Path(path), data)
    return baseline._sha(data)


def load_successor_repair_protocol(path):
    data = _read(path)
    return _validate(SuccessorRepairProtocolEnvelope.model_validate(_parse(data)))


def protocol_summary(envelope):
    checked = _validate(envelope)
    return dict(
        status="prospective_terminal_successor_repair_protocol_only",
        declaration_sha256=checked.declaration_sha256,
        historical_missing_successor_anchors=8,
        proposed_domain_maximum=21,
        cases_per_role=40,
        valid_inputs_per_role=32,
        invalid_inputs_per_role=8,
        prospective_roles=4,
        **{name: False for name in _FALSE_FLAGS},
    )
