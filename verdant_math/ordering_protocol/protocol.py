"""Freeze operand-order instruction, provenance and controls before implementation.

This module reads pinned historical bytes and declares prospective requirements.
It never teaches, routes operands, answers a question, grades or simulates.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictStr, ValidationError, model_validator

from verdant_kernel import VerdantKernel, checkpoint_bytes
from verdant_kernel.models import FrozenRecord, canonical_json_bytes
from verdant_math import teaching_pilot as baseline
from verdant_math.counting import pilot as counting
from verdant_math.addition import pilot as addition
from verdant_math.coverage import challenge as coverage

_ROOT = Path(__file__).resolve().parents[2]
_Digest, _Ref, _MAX_BYTES = baseline._Digest, baseline._Ref, baseline._MAX_BYTES
_HISTORY = (
    ("artifacts/arithmetic_teaching_v056/pilot.vmp", "36548d730ffbfa8e3dbf09436047f79c0e2ff1672fb72999242b16458361321d"),
    ("artifacts/counting_teaching_v057/pilot.vcount", "dd93ba95dd5e556541e57dfbaf9e4f8fb486547f401d4e07c7b47c8a0227fe2c"),
    ("artifacts/scaffold_addition_v058/pilot.vadd", "148586a8d060d92afa991135ad8393ea9c87f6a11c76bc797b3c12af10c2254c"),
    ("artifacts/addition_coverage_v059/challenge.vacp", "d01dd5280a1bba38342b5305e552b3eacaf12f68d12d0d64230460a0822f0fbf"),
    ("artifacts/addition_coverage_v059/evaluation.vacr", "853da03a48bf68905f4eb2b46433e9e1958a98a515d192f53e7bb68faa81840e"),
)
_PROBE_FILES = (
    "tests/test_math_teaching_pilot.py", "tests/test_counting_teaching_pilot.py",
    "tests/test_scaffold_addition_pilot.py", "tests/test_addition_coverage_challenge.py",
)
# Actual previously queried/rejected API payloads. The source tests are also
# hashed below, so later probes require a new prospective declaration.
_PROBES = (
    *(dict(api="addition", raw={"left": a, "right": b}) for a, b in
      ((9, 5), (3, 9), (18, 1))),
    *(dict(api="fact_recall", raw={"left": a, "right": 1}) for a in
      (True, 1.0, "1", -1, 10)),
    *(dict(api="counting", raw={"start": a, "ticks": list(ticks)}) for a, ticks in
      ((True, ("tick",)), (5.0, ("tick",)), ("5", ("tick",)), (-1, ("tick",)),
       (19, ("tick",)), (5, ("wrong",)), (5, ("tick",) * 5), (18, ()))),
    *(dict(api="addition", raw={"left": a, "right": b}) for a, b in
      coverage._INVALID_PROBES),
)
_PAIRS = ((5, 0), (6, 0), (7, 0), (8, 0), (13, 0), (14, 0), (13, 2), (14, 3))
_TERMINAL = ((18, 3), (17, 3), (16, 4), (17, 4))
_ROWS = (
    *(("original_mapping", f"supported-{i}", {"left": a, "right": b})
      for i, (a, b) in enumerate(_PAIRS)),
    *(("swap_candidate", f"supported-{i}", {"left": b, "right": a})
      for i, (a, b) in enumerate(_PAIRS)),
    *(("both_mappings_absent", None, {"left": a, "right": b}) for a, b in
      ((5, 6), (6, 5), (7, 7), (14, 15), (15, 15), (16, 16), (12, 13), (13, 12))),
    *(("terminal_link", f"terminal-{i}", {"left": a, "right": b})
      for i, (a, b) in enumerate(_TERMINAL)),
    *(("terminal_link", f"terminal-{i}", {"left": b, "right": a})
      for i, (a, b) in enumerate(_TERMINAL)),
    *(("invalid_input", None, raw) for raw in (
        {"left": 12, "right": True}, {"left": None, "right": 4},
        {"left": 11, "right": "4"}, {"left": 15, "right": 0.5},
        {"left": 25, "right": 4}, {"left": 16},
        {"left": 14, "right": 0, "answer": 0}, {"left": [15], "right": 0})),
)
_INSTRUCTION = {
    "subject": "math:procedure:addition_operand_order",
    "predicate": "math_uses_operand_order_rule",
    "source_class": "human_testimony",
    "declared_source": "declared-operand-order-teacher://v060",
    "correct_label": "math:rule:swap_only_for_missing_right_mapping",
    "incorrect_label": "math:rule:swap_only_for_found_right_mapping",
    "authority_scope": "read_only_private_operand_routing_only",
    "validity": "one_affirmed_positive_unopposed_native_testimony_claim_and_complete_evidence",
    "correct_trigger": "original_right_lookup_missing_and_original_left_mapping_valid",
    "mapping_validity": "existing_native_lookup_found_and_unchanged_decode_tokens_not_numeric_reconstruction",
    "correct_right_found": "preserve_original_order_with_valid_decoded_native_mapping",
    "right_conflicting_invalid_or_unsupported": "retain_evidence_and_abstain_never_swap",
    "correct_left_missing_conflicting_invalid_or_unsupported": "retain_both_lookups_and_abstain",
    "incorrect_trigger": "original_right_mapping_valid_then_swap_regardless_of_left_mapping",
    "incorrect_otherwise": "retain_original_order_for_missing_right_mapping",
    "no_instruction": "reuse_original_order_addition_with_existing_addition_instruction",
    "instruction_conflicting_invalid_or_unsupported": "retain_instruction_evidence_and_abstain",
    "maximum_swaps": 1,
    "sorting_or_recursive_retry_permitted": False,
}
_SPEC = dict(
    version="teacher_scaffold_operand_order_protocol_v0.60",
    phase="prospective_protocol_only",
    grounded_parent_commit="7cae607ac7678954e0fd9369b401609330d5ea63",
    source="fresh_seed_79060_state_dim_16_run_label_math-operand-order-v060",
    roles=("taught", "no_instruction_control", "valid_null", "incorrect_instruction_control"),
    instruction=_INSTRUCTION,
    teaching="same_25_correct_v058_lessons_each_role_then_one_order_instruction_or_prompt_slot",
    control_difference="only_the_26th_instruction_slot_not_the_existing_addition_rule",
    valid_null="distinct_pristine_private_copy_exact_taught_operations_and_all_records",
    reused_versions=(baseline._PROTOCOL["version"], counting._PROTOCOL["version"],
                     addition._PROTOCOL["version"], coverage._SPEC["version"]),
    input_contract="unchanged_strict_AdditionRequest_original_order_no_targets_or_group_labels",
    response_contract={
        "maximum_records_per_role": 40, "maximum_swaps_per_record": 1,
        "original_request": "exact_validated_original_order_never_overwritten",
        "effective_request": "original_or_one_teacher_authorized_transposition_only",
        "provenance": ("local_run_ref", "case_ref", "private_kernel_fingerprint",
            "order_instruction_claim_and_evidence_refs", "original_right_mapping_lookup_and_refs",
            "left_mapping_lookup_and_refs_if_checked", "route_disposition", "effective_request",
            "unchanged_addition_reply_and_all_mapping_rule_successor_blocking_refs"),
        "bound": "reuse_unchanged_v058_addition_v057_counting_with_zero_to_four_native_tokens",
        "verification": "later_native_trace_verifier_reconstructs_route_and_nested_derivation",
        "absent_mapping": "keep_original_lookup_absence_and_any_left_lookup_not_a_default",
        "terminal_failure": "retain_every_partial_successor_step_answer_none",
        "no_fallback_arithmetic": True,
        "case_labels_expected_answers_or_grades_permitted": False,
    },
    cases_per_role=40, accepted_inputs_per_role=32, invalid_inputs_per_role=8,
    response_order="all_160_records_before_any_of_128_external_grades",
    scoring="unchanged_v058_addition_grade_on_original_request_only_after_all_roles_complete",
    full_denominators="40_enrolled_and_32_valid_per_role_keep_all_abstentions_and_invalids",
    invalid_handling="retain_typed_raw_JSON_API_error_locations_and_types_no_target_or_answer_credit",
    missing_handling="retain_slot_original_group_partial_and_blocking_evidence_no_replacement_or_credit",
    correctness="exact_integer_original_left_plus_original_right_external_only_no_feedback",
    group_basis="predeclared_taught_mapping_link_coverage_never_reclassified_by_control_outcomes",
    freshness="both_possible_ordered_pairs_excluded_against_four_consumed_cohorts_and_all_recorded_probes",
    prospective_groups=("original_mapping", "swap_candidate", "both_mappings_absent",
                        "terminal_link", "invalid_input"),
    adapter_before_evaluation="separate_versioned_sibling_adapter_and_trace_verifier_before_later_cohort_run",
    separate_evaluation="immutable_result_bound_to_exact_saved_protocol_and_frozen_adapter_bytes",
    trusted_components="local_runtime_filesystem_and_native_replay_code",
    trust_limits="hashes_labels_replay_prove_no_teacher_authentication_historical_freeze_time_or_independence",
    adaptation_replacement_or_metric_tuning_permitted=False,
    canonical_input_mutation_permitted=False, simulation_execution_permitted=False,
)
_FALSE_FLAGS = (
    "adapter_implemented", "instruction_installed", "responses_observed", "evaluation_completed",
    "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
    "instruction_discovery_observed", "generalized_arithmetic_claim_permitted",
    "learning_efficiency_observed", "independent_replication_observed",
    "canonical_commit_permitted", "resolution_authority_enabled", "promotion_authority_enabled",
    "policy_rewrite_authority_enabled",
)


class OperandOrderProtocolIntegrityError(baseline.MathTeachingPilotIntegrityError):
    """A prospective declaration lost its exact sources, cases or boundaries."""


class OrderCase(FrozenRecord):
    case_id: _Ref
    group: Literal["original_mapping", "swap_candidate", "both_mappings_absent", "terminal_link", "invalid_input"]
    order_pair: _Ref | None
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


class ArtifactRef(FrozenRecord):
    path: _Ref
    sha256: _Digest


class ProbeExclusion(FrozenRecord):
    api: Literal["fact_recall", "counting", "addition"]
    raw_request_json: Annotated[StrictStr, Field(max_length=1024)]


class Boundaries(FrozenRecord):
    adapter_implemented: StrictBool = False
    instruction_installed: StrictBool = False
    responses_observed: StrictBool = False
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
    def check_boundaries(self):
        if any(getattr(self, name) for name in _FALSE_FLAGS):
            raise ValueError("A prospective protocol supplies no execution, learning or canonical authority.")
        return self


def _cases():
    return tuple(OrderCase(case_id=f"math-v060:case:{i}", group=g, order_pair=p,
        raw_request_json=canonical_json_bytes(raw).decode()) for i, (g, p, raw) in enumerate(_ROWS))


def _probes():
    return tuple(ProbeExclusion(api=p["api"], raw_request_json=canonical_json_bytes(p["raw"]).decode())
                 for p in _PROBES)


def _read(path):
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise OperandOrderProtocolIntegrityError("Operand-order source exceeds the size bound.")
    return data


def _prior_data():
    result = []
    for path, digest in _HISTORY:
        data = _read(_ROOT / path)
        if baseline._sha(data) != digest:
            raise OperandOrderProtocolIntegrityError("A pinned historical artifact changed.")
        raw = json.loads(data, object_pairs_hook=baseline._unique_object)
        if data != canonical_json_bytes(raw):
            raise OperandOrderProtocolIntegrityError("Historical artifact must have canonical bytes.")
        result.append(raw)
    # Compare the actual old manifests without replaying teaching or queries.
    actual = (result[0]["receipt"]["code_sources"], result[1]["receipt"]["code_sources"],
              result[2]["receipt"]["code_sources"], result[3]["plan"]["code_sources"])
    for old, current in zip(actual, (baseline._code_manifest(), counting._code_manifest(),
                                    addition._code_manifest(), coverage._code_manifest())):
        if old != [s.model_dump(mode="json") for s in current]:
            raise OperandOrderProtocolIntegrityError("A preserved math implementation changed.")
    if result[4]["receipt"]["frozen_plan"] != result[3]:
        raise OperandOrderProtocolIntegrityError("Coverage history lost its exact plan pairing.")
    return result


def _exclusions(priors):
    raw = set()
    for observation in priors[0]["receipt"]["arms"][0]["observations"]:
        raw.add(canonical_json_bytes(observation["problem"]).decode())
    for observation in priors[1]["receipt"]["arms"][0]["observations"]:
        q = observation["request"]
        raw.add(canonical_json_bytes(dict(left=q["start"], right=len(q["ticks"]))).decode())
    for observation in priors[2]["receipt"]["arms"][0]["observations"]:
        raw.add(canonical_json_bytes(observation["request"]).decode())
    raw.update(c["raw_request_json"] for c in priors[3]["plan"]["cases"])
    for p in _PROBES:
        q = p["raw"]
        projected = dict(left=q["start"], right=len(q["ticks"])) if p["api"] == "counting" else q
        raw.add(canonical_json_bytes(projected).decode())
    return tuple(sorted(raw))


def _code_manifest():
    sources = {s.path: s for s in coverage._code_manifest()}
    for path in Path(__file__).resolve().parent.glob("*.py"):
        name = path.relative_to(_ROOT).as_posix()
        sources[name] = baseline.MathCodeDigest(path=name, sha256=baseline._sha(path.read_bytes()))
    return tuple(sources[name] for name in sorted(sources))


def fresh_order_kernel():
    return VerdantKernel(seed=79060, state_dim=16, run_label="math-operand-order-v060")


class OperandOrderProtocol(Boundaries):
    protocol: dict
    cases: tuple[OrderCase, ...] = Field(min_length=40, max_length=40)
    prior_artifacts: tuple[ArtifactRef, ...] = Field(min_length=5, max_length=5)
    probe_sources: tuple[baseline.MathCodeDigest, ...] = Field(min_length=4, max_length=4)
    excluded_raw_requests: tuple[StrictStr, ...]
    probe_exclusions: tuple[ProbeExclusion, ...]
    code_sources: tuple[baseline.MathCodeDigest, ...]
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    purpose: Literal["prospective_teacher_operand_order_protocol"] = "prospective_teacher_operand_order_protocol"

    @model_validator(mode="after")
    def check_protocol(self):
        if (canonical_json_bytes(self.protocol) != canonical_json_bytes(_SPEC)
            or self.cases != _cases() or self.probe_exclusions != _probes()
            or self.prior_artifacts != tuple(ArtifactRef(path=p, sha256=d) for p, d in _HISTORY)):
            raise ValueError("Operand-order protocol lost frozen instruction, controls, cases or history.")
        if self.excluded_raw_requests != tuple(sorted(set(self.excluded_raw_requests))):
            raise ValueError("Prospective exclusions must be complete and canonical.")
        seen = set()
        for case in self.cases:
            raw = json.loads(case.raw_request_json, object_pairs_hook=baseline._unique_object)
            if case.raw_request_json != canonical_json_bytes(raw).decode() or case.raw_request_json in seen:
                raise ValueError("Prospective cases must be canonical and distinct.")
            seen.add(case.raw_request_json)
            if case.raw_request_json in self.excluded_raw_requests:
                raise ValueError("A prospective case reuses a consumed input or probe.")
            if set(raw) == {"left", "right"}:
                reversed_raw = canonical_json_bytes(dict(left=raw["right"], right=raw["left"])).decode()
                if reversed_raw in self.excluded_raw_requests:
                    raise ValueError("A swapped prospective input reuses a consumed case or probe.")
            try:
                addition.AdditionRequest.model_validate(raw)
                valid = True
            except ValidationError:
                valid = False
            if valid == (case.group == "invalid_input"):
                raise ValueError("Prospective input validity does not match its fixed group.")
        return self


class OperandOrderProtocolEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-operand-order-protocol-v1"] = "verdant-operand-order-protocol-v1"
    declaration: OperandOrderProtocol
    declaration_sha256: _Digest

    @classmethod
    def build(cls, declaration):
        checked = OperandOrderProtocol.model_validate(declaration.model_dump(mode="json"))
        return cls(declaration=checked,
                   declaration_sha256=baseline._sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.declaration_sha256 != baseline._sha(canonical_json_bytes(self.declaration.model_dump(mode="json"))):
            raise ValueError("Operand-order declaration checksum mismatch.")
        return self


def freeze_operand_order_protocol(source=None):
    """Pure declaration: no native lesson, response, routing, grade or simulation."""
    source = fresh_order_kernel() if source is None else source
    before = source.fingerprint()
    if before != fresh_order_kernel().fingerprint():
        raise OperandOrderProtocolIntegrityError("Operand-order source must be the exact fresh checkpoint.")
    priors, manifest = _prior_data(), _code_manifest()
    data = checkpoint_bytes(source.snapshot())
    probes = tuple(baseline.MathCodeDigest(path=p, sha256=baseline._sha(_read(_ROOT / p))) for p in _PROBE_FILES)
    envelope = OperandOrderProtocolEnvelope.build(OperandOrderProtocol(
        protocol=_SPEC, cases=_cases(), prior_artifacts=tuple(ArtifactRef(path=p, sha256=d) for p, d in _HISTORY),
        probe_sources=probes, excluded_raw_requests=_exclusions(priors), probe_exclusions=_probes(),
        code_sources=manifest, source_checkpoint_base64=base64.b64encode(data).decode(),
        source_checkpoint_sha256=baseline._sha(data), source_kernel_fingerprint=before))
    if (source.fingerprint() != before or _code_manifest() != manifest or _prior_data() != priors
        or probes != tuple(baseline.MathCodeDigest(path=p, sha256=baseline._sha(_read(_ROOT / p))) for p in _PROBE_FILES)):
        raise OperandOrderProtocolIntegrityError("Source or code changed during protocol freeze.")
    return envelope


def _validate(envelope):
    checked = OperandOrderProtocolEnvelope.model_validate(envelope.model_dump(mode="json"))
    source = baseline._checkpoint(checked.declaration.source_checkpoint_base64,
                                  checked.declaration.source_checkpoint_sha256)
    if checked != freeze_operand_order_protocol(source):
        raise OperandOrderProtocolIntegrityError("Operand-order protocol failed exact source reconstruction.")
    return checked


def save_operand_order_protocol(path, envelope):
    checked = _validate(envelope)
    data = canonical_json_bytes(checked.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise OperandOrderProtocolIntegrityError("Operand-order protocol exceeds the size bound.")
    target = Path(path)
    protected = tuple(_ROOT / p for p, _ in _HISTORY) + tuple(_ROOT / p for p in _PROBE_FILES)
    protected += tuple(_ROOT / s.path for s in checked.declaration.code_sources)
    if target.resolve() in {p.resolve() for p in protected}:
        raise OperandOrderProtocolIntegrityError("Cannot publish over protocol input evidence or code.")
    baseline._write_immutable(target, data)
    # No runtime or historical-freeze authentication is claimed by this writer.
    return baseline._sha(data)


def load_operand_order_protocol(path):
    data = _read(path)
    raw = json.loads(data, object_pairs_hook=baseline._unique_object)
    if data != canonical_json_bytes(raw):
        raise OperandOrderProtocolIntegrityError("Operand-order protocol bytes must be canonical.")
    return _validate(OperandOrderProtocolEnvelope.model_validate(raw))


def protocol_summary(envelope):
    checked = _validate(envelope)
    return dict(status="prospective_operand_order_protocol_only",
        declaration_sha256=checked.declaration_sha256, cases_per_role=40, valid_inputs_per_role=32,
        invalid_inputs_per_role=8, prospective_roles=4, responses_observed=False,
        adapter_implemented=False, evaluation_completed=False, source_authenticated=False,
        physical_evidence_admissible=False, canonical_commit_permitted=False)
