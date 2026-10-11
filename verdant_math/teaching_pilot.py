"""Frozen addition-fact teaching and retrieval pilot, not an arithmetic solver.

Native teacher testimony is recorded only in private kernel copies. The exact
arithmetic grader runs after responses and never supplies answers to retrieval.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, StrictBool, StrictInt, StrictStr, model_validator

from cognitive_chunk_v2 import ExperienceInput, PipelineOrchestrator
from verdant_claims import ClaimLearningPipeline
from verdant_kernel import (
    ClaimPolarity, ClaimSourceClass, EvidenceKind, ExperienceCommand,
    VerdantKernel, checkpoint_bytes,
)
from verdant_kernel.checkpoint import load_checkpoint_bytes
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, normalize_label
from verdant_obligations.prediction_failure_trial_plans import _write_immutable

_ROOT = Path(__file__).resolve().parent.parent
_MAX_BYTES = 4 * 1024 * 1024
_Digest = Annotated[StrictStr, Field(pattern=r"^[0-9a-f]{64}$")]
_Ref = Annotated[StrictStr, Field(min_length=1, max_length=256)]
_Operand = Annotated[StrictInt, Field(ge=0, le=9)]
_Answer = Annotated[StrictInt, Field(ge=0, le=18)]
_ROLES = ("taught", "no_answer_control", "valid_null", "incorrect_teacher_control")
_TRAINING = ((0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3), (3, 3), (3, 4))
# Declared curriculum, not an answer table consulted by the responder.
_TEACHER_ANSWERS = (0, 1, 2, 3, 4, 5, 6, 7)
_INCORRECT_ANSWERS = (1, 2, 3, 4, 5, 6, 7, 8)
_HELD_OUT = ((1, 0), (2, 1), (3, 2), (4, 3), (1, 3), (2, 4), (4, 4), (4, 5))
_PROTOCOL = dict(
    version="addition_fact_teaching_v0.56", task="single_digit_addition_fact_retrieval",
    training_pairs=_TRAINING, teacher_answers=_TEACHER_ANSWERS,
    incorrect_teacher_answers=_INCORRECT_ANSWERS, held_out_pairs=_HELD_OUT,
    held_out_groups="four_reversed_pairs_then_four_new_pairs",
    roles=_ROLES, exposure_count_per_role=8, questions_per_role=16,
    source="fresh_seed_79056_state_dim_16_run_label_math-teaching-v056",
    teaching="explicit_native_human_testimony_via_ClaimLearningPipeline",
    no_answer_control="same_eight_problem_prompts_without_answers_or_claims",
    valid_null="independent_copy_with_exact_same_lessons_and_queries",
    responder="read_only_exact_claim_retrieval_without_arithmetic_or_oracle",
    scoring="external_integer_addition_after_responses_exact_equality",
    missing_or_conflicting_answer="retain_as_abstention_score_zero",
    replacement_or_adaptive_case_selection_permitted=False,
    canonical_input_mutation_permitted=False, simulation_execution=False,
    interpretation="software_fact_recall_and_held_out_limit_only",
)


class MathTeachingPilotIntegrityError(ValueError):
    """The fixed educational protocol or its execution lineage was altered."""


class AdditionProblem(FrozenRecord):
    left: _Operand
    right: _Operand


class AdditionReply(FrozenRecord):
    status: Literal["recalled", "abstained"]
    answer: _Answer | None
    reason: Literal["teacher_testimony", "unseen", "conflicting_claims", "invalid_testimony"]
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]

    @model_validator(mode="after")
    def check_reply(self):
        if ((self.status == "recalled") != (self.answer is not None)
            or (self.status == "recalled") != (self.reason == "teacher_testimony")
            or self.claim_refs != tuple(sorted(set(self.claim_refs)))
            or self.evidence_refs != tuple(sorted(set(self.evidence_refs)))
            or (self.status == "recalled" and (len(self.claim_refs) != 1 or not self.evidence_refs))):
            raise ValueError("Reply lost its abstention or testimony boundary.")
        return self


def _subject(problem: AdditionProblem) -> str:
    # Ordered operands: reversing them is a held-out operation, not a lookup alias.
    return f"math:sum:left:{problem.left}:right:{problem.right}"


def recall_addition_fact(kernel: VerdantKernel, problem: AdditionProblem) -> AdditionReply:
    """Retrieve a unique supplied fact. No addition or evaluation labels are read."""
    problem = AdditionProblem.model_validate(problem.model_dump(mode="json"))
    before = kernel.fingerprint()
    subject = normalize_label(_subject(problem))
    claims = tuple(sorted((c for c in kernel.state.claims.values()
        if kernel.state.concepts[c.subject_concept_id].normalized_label == subject
        and c.predicate == "math_sum_equals"), key=lambda c: c.claim_id))
    claim_refs = tuple(c.claim_id for c in claims)
    evidence_refs = tuple(sorted({e.evidence_id for c in claims
        for e in (*c.support_ledger, *c.refutation_ledger)}))
    answer = None
    reason = "unseen" if not claims else "conflicting_claims"
    if len(claims) == 1:
        claim = claims[0]
        label = kernel.state.concepts[claim.object_concept_id].label
        match = re.fullmatch(r"math:integer:(0|[1-9][0-9]?)", label)
        valid = (claim.polarity == ClaimPolarity.AFFIRMED and claim.net_score > 0
            and not claim.refutation_ledger and bool(claim.support_ledger)
            and all(e.source_class == ClaimSourceClass.HUMAN_TESTIMONY
                    and e.evidence_id in kernel.state.evidence
                    and kernel.state.evidence[e.evidence_id].kind == EvidenceKind.TESTIMONY
                    for e in claim.support_ledger))
        if valid and match and int(match[1]) <= 18:
            answer, reason = int(match[1]), "teacher_testimony"
        else:
            reason = "invalid_testimony"
    if kernel.fingerprint() != before:
        raise MathTeachingPilotIntegrityError("Retrieval mutated its private kernel.")
    return AdditionReply(status="recalled" if answer is not None else "abstained",
        answer=answer, reason=reason, claim_refs=claim_refs, evidence_refs=evidence_refs)


class MathLessonTrace(FrozenRecord):
    event_key: _Ref
    problem: AdditionProblem
    declared_answer: _Answer | None
    transition_ref: _Ref
    claim_refs: tuple[_Ref, ...]
    evidence_refs: tuple[_Ref, ...]


class MathObservation(FrozenRecord):
    case_id: _Ref
    split: Literal["retention", "held_out_reversed", "held_out_new"]
    problem: AdditionProblem
    reply: AdditionReply
    expected_answer: _Answer
    grade: Literal["correct", "incorrect", "abstained"]


class MathTeachingArm(FrozenRecord):
    role: Literal["taught", "no_answer_control", "valid_null", "incorrect_teacher_control"]
    checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    checkpoint_sha256: _Digest
    kernel_fingerprint: _Digest
    lessons: tuple[MathLessonTrace, ...] = Field(min_length=8, max_length=8)
    observations: tuple[MathObservation, ...] = Field(min_length=16, max_length=16)


class MathCodeDigest(FrozenRecord):
    path: _Ref
    sha256: _Digest


class MathTeachingPilotReceipt(FrozenRecord):
    protocol: dict
    source_checkpoint_base64: Annotated[StrictStr, Field(max_length=_MAX_BYTES)]
    source_checkpoint_sha256: _Digest
    source_kernel_fingerprint: _Digest
    code_sources: tuple[MathCodeDigest, ...]
    arms: tuple[MathTeachingArm, ...] = Field(min_length=4, max_length=4)
    purpose: Literal["educational_software_experiment"] = "educational_software_experiment"
    source_authenticated: StrictBool = False
    physical_evidence_admissible: StrictBool = False
    harm_scoring_implemented: StrictBool = False
    generalized_arithmetic_claim_permitted: StrictBool = False
    canonical_commit_permitted: StrictBool = False
    resolution_authority_enabled: StrictBool = False
    promotion_authority_enabled: StrictBool = False
    policy_rewrite_authority_enabled: StrictBool = False

    @model_validator(mode="after")
    def check_protocol(self):
        if (canonical_json_bytes(self.protocol) != canonical_json_bytes(_PROTOCOL)
            or tuple(a.role for a in self.arms) != _ROLES
            or any(getattr(self, name) for name in (
                "source_authenticated", "physical_evidence_admissible", "harm_scoring_implemented",
                "generalized_arithmetic_claim_permitted", "canonical_commit_permitted",
                "resolution_authority_enabled", "promotion_authority_enabled", "policy_rewrite_authority_enabled"))):
            raise ValueError("Math pilot lost frozen controls or claim boundaries.")
        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class MathTeachingPilotEnvelope(FrozenRecord):
    sidecar_format: Literal["verdant-math-teaching-pilot-v1"] = "verdant-math-teaching-pilot-v1"
    receipt: MathTeachingPilotReceipt
    receipt_sha256: _Digest

    @classmethod
    def build(cls, receipt):
        checked = MathTeachingPilotReceipt.model_validate(receipt.model_dump(mode="json"))
        return cls(receipt=checked, receipt_sha256=_sha(canonical_json_bytes(checked.model_dump(mode="json"))))

    @model_validator(mode="after")
    def check_hash(self):
        if self.receipt_sha256 != _sha(canonical_json_bytes(self.receipt.model_dump(mode="json"))):
            raise ValueError("Math pilot receipt checksum mismatch.")
        return self


def _code_manifest() -> tuple[MathCodeDigest, ...]:
    paths = ["requirements-lock.txt", "verdant_obligations/prediction_failure_trial_plans.py"]
    for directory in ("verdant_math", "verdant_claims", "verdant_kernel", "cognitive_chunk_v2"):
        paths.extend(str(p.relative_to(_ROOT)) for p in (_ROOT / directory).glob("*.py"))
    return tuple(MathCodeDigest(path=p, sha256=_sha((_ROOT / p).read_bytes())) for p in sorted(paths))


def fresh_math_kernel() -> VerdantKernel:
    return VerdantKernel(seed=79056, state_dim=16, run_label="math-teaching-v056")


def _checkpoint(encoded: str, digest: str) -> VerdantKernel:
    data = base64.b64decode(encoded, validate=True)
    if len(data) > _MAX_BYTES or _sha(data) != digest:
        raise MathTeachingPilotIntegrityError("Embedded checkpoint checksum or bound mismatch.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if (sorted(m.filename for m in members) != ["manifest.json", "state.json"]
                or any(m.compress_type != zipfile.ZIP_STORED or m.file_size > _MAX_BYTES for m in members)):
                raise MathTeachingPilotIntegrityError("Embedded checkpoint member boundary mismatch.")
        return VerdantKernel.from_state(load_checkpoint_bytes(data))
    except (zipfile.BadZipFile, KeyError) as exc:
        raise MathTeachingPilotIntegrityError("Embedded checkpoint is invalid.") from exc


def _teach(kernel, no_answers=False, incorrect=False):
    pipeline = ClaimLearningPipeline()
    traces = []
    for index, pair in enumerate(_TRAINING):
        problem = AdditionProblem(left=pair[0], right=pair[1])
        answer = None if no_answers else (_INCORRECT_ANSWERS if incorrect else _TEACHER_ANSWERS)[index]
        key = f"math-v056:lesson:{index}"
        source = "declared-math-teacher://v056"
        if answer is not None:
            result = pipeline.record_claim(kernel, event_key=key,
                native_description=f"Teacher lesson: {problem.left} + {problem.right} = {answer}.",
                subject_label=_subject(problem), predicate="math_sum_equals",
                object_label=f"math:integer:{answer}", polarity=ClaimPolarity.AFFIRMED,
                source_class=ClaimSourceClass.HUMAN_TESTIMONY, source_ref=source,
                rationale="Teacher-supplied fact; arithmetic was not independently derived.").kernel_result
        else:
            chunk, store = PipelineOrchestrator().process(ExperienceInput.from_text(
                f"Addition exercise: {problem.left} + {problem.right}. No answer supplied.",
                source_id=source, source_name=f"{key}.txt"))
            payload, translation = chunk.payloads[0], chunk.translations[0]
            result = kernel.apply_experience(ExperienceCommand(event_key=key,
                source_ref=source, modality="text", payload_sha256=payload.source_sha256,
                feature_vector=tuple(float(v) for v in store.get_array(translation.feature_ref).reshape(-1)),
                semantic_evidence_kind=EvidenceKind.TESTIMONY,
                semantic_evidence_details={"source_class": "human_testimony", "answer_supplied": False},
                metadata={"event_type": "math_prompt_only", "epistemic_status": "no_answer_supplied"}))
        traces.append(MathLessonTrace(event_key=key, problem=problem, declared_answer=answer,
            transition_ref=result.transition_id, claim_refs=tuple(sorted(result.claim_ids)),
            evidence_refs=tuple(sorted((result.observation_evidence_id,
                result.translation_evidence_id, *result.additional_evidence_ids)))))
    return tuple(traces)


def _grade(index: int, problem: AdditionProblem, reply: AdditionReply) -> MathObservation:
    # This is the only arithmetic answer oracle. It is strictly outside retrieval.
    expected = problem.left + problem.right
    split = "retention" if index < 8 else "held_out_reversed" if index < 12 else "held_out_new"
    return MathObservation(case_id=f"math-v056:case:{index}", split=split, problem=problem,
        reply=reply, expected_answer=expected,
        grade="abstained" if reply.answer is None else "correct" if reply.answer == expected else "incorrect")


def run_math_teaching_pilot(kernel: VerdantKernel | None = None) -> MathTeachingPilotEnvelope:
    """Explicit opt-in; each role learns on its own copy of the same fresh source."""
    source = fresh_math_kernel() if kernel is None else kernel
    before = source.fingerprint()
    if before != fresh_math_kernel().fingerprint():
        raise MathTeachingPilotIntegrityError("Math pilot requires its fixed fresh, unexposed source.")
    manifest = _code_manifest()
    data = checkpoint_bytes(source.snapshot())
    pending = []
    for role in _ROLES:
        private = VerdantKernel.from_state(source.snapshot())
        lessons = _teach(private, no_answers=role == "no_answer_control",
                         incorrect=role == "incorrect_teacher_control")
        private_before = private.fingerprint()
        problems = tuple(AdditionProblem(left=a, right=b) for a, b in (*_TRAINING, *_HELD_OUT))
        replies = tuple(recall_addition_fact(private, p) for p in problems)
        if private.fingerprint() != private_before:
            raise MathTeachingPilotIntegrityError("Evaluation mutated a private arm.")
        post = checkpoint_bytes(private.snapshot())
        pending.append((role, lessons, private_before, post, problems, replies))
    # Freeze all 64 responses across all roles before any grading; no label feedback.
    arms = []
    for role, lessons, private_before, post, problems, replies in pending:
        observations = tuple(_grade(i, p, r) for i, (p, r) in enumerate(zip(problems, replies)))
        arms.append(MathTeachingArm(role=role, checkpoint_base64=base64.b64encode(post).decode("ascii"),
            checkpoint_sha256=_sha(post), kernel_fingerprint=private_before,
            lessons=lessons, observations=observations))
    if source.fingerprint() != before or _code_manifest() != manifest:
        raise MathTeachingPilotIntegrityError("Canonical source or implementation changed during the pilot.")
    if arms[0].model_dump(exclude={"role"}) != arms[2].model_dump(exclude={"role"}):
        raise MathTeachingPilotIntegrityError("The exact valid-null copy diverged.")
    receipt = MathTeachingPilotReceipt(protocol=_PROTOCOL,
        source_checkpoint_base64=base64.b64encode(data).decode("ascii"),
        source_checkpoint_sha256=_sha(data), source_kernel_fingerprint=before,
        code_sources=manifest, arms=tuple(arms))
    return MathTeachingPilotEnvelope.build(receipt)


def _validate_replay(envelope: MathTeachingPilotEnvelope) -> None:
    envelope = MathTeachingPilotEnvelope.model_validate(envelope.model_dump(mode="json"))
    r = envelope.receipt
    if r.code_sources != _code_manifest():
        raise MathTeachingPilotIntegrityError("Math pilot implementation manifest changed.")
    source = _checkpoint(r.source_checkpoint_base64, r.source_checkpoint_sha256)
    if source.fingerprint() != r.source_kernel_fingerprint:
        raise MathTeachingPilotIntegrityError("Math pilot source fingerprint mismatch.")
    for arm in r.arms:
        restored = _checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)
        if restored.fingerprint() != arm.kernel_fingerprint:
            raise MathTeachingPilotIntegrityError("Math pilot arm fingerprint mismatch.")
    expected = run_math_teaching_pilot(source)
    if canonical_json_bytes(envelope.model_dump(mode="json")) != canonical_json_bytes(expected.model_dump(mode="json")):
        raise MathTeachingPilotIntegrityError("Math pilot native execution, cases or scoring failed replay.")


def save_math_teaching_pilot(path: str | Path, envelope: MathTeachingPilotEnvelope) -> str:
    _validate_replay(envelope)
    data = canonical_json_bytes(envelope.model_dump(mode="json"))
    if len(data) > _MAX_BYTES:
        raise MathTeachingPilotIntegrityError("Math pilot exceeds the sidecar size bound.")
    _write_immutable(Path(path), data)
    return _sha(data)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MathTeachingPilotIntegrityError("Duplicate math pilot JSON key.")
        result[key] = value
    return result


def load_math_teaching_pilot(path: str | Path) -> MathTeachingPilotEnvelope:
    """Validate bytes and rerun native teaching on fresh private copies, then compare."""
    with Path(path).open("rb") as handle:
        data = handle.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise MathTeachingPilotIntegrityError("Math pilot exceeds the sidecar size bound.")
    envelope = MathTeachingPilotEnvelope.model_validate(json.loads(data, object_pairs_hook=_unique_object))
    _validate_replay(envelope)
    return envelope


def restore_math_teaching_arm(envelope: MathTeachingPilotEnvelope, role: str = "taught") -> VerdantKernel:
    """Return a new private, replay-verified memory for explicit fact queries."""
    if role not in _ROLES:
        raise MathTeachingPilotIntegrityError("Unknown math pilot role.")
    _validate_replay(envelope)
    arm = next(a for a in envelope.receipt.arms if a.role == role)
    return _checkpoint(arm.checkpoint_base64, arm.checkpoint_sha256)


def math_teaching_summary(envelope: MathTeachingPilotEnvelope) -> dict:
    result = {}
    for arm in envelope.receipt.arms:
        result[arm.role] = {split: {grade: sum(o.grade == grade for o in arm.observations if o.split == split)
            for grade in ("correct", "incorrect", "abstained")}
            for split in ("retention", "held_out_reversed", "held_out_new")}
    return dict(status="educational_software_pilot", receipt_sha256=envelope.receipt_sha256,
        arms=result, physical_evidence_admissible=False, generalized_arithmetic_claim_permitted=False,
        canonical_commit_permitted=False)
