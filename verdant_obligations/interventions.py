"""Non-executing Council Tournament of Least Regret.

The tournament compares bounded intervention proposals through explicit
counterfactual observations.  It recommends one proposal by epistemic
preservation, never applies it.  Component footprint is used only after the
preservation regrets tie; high blast radius is a cost, not an automatic veto.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import SimulationDisposition, SimulationLedger
from .diagnostics import (
    DiagnosticConclusion,
    DiagnosticEngine,
    DiagnosticResult,
)
from .equivalence import EquivalenceLensSystem


COUNCIL_INTERVENTION_POLICY_VERSION = "council_least_regret_policy_v0.9"
COUNCIL_INTERVENTION_LEDGER_VERSION = "council_intervention_ledger_v0.9"


class CouncilInterventionIntegrityError(RuntimeError):
    pass


class InterventionKind(str, Enum):
    ROLLBACK_BINDING = "rollback_binding"
    DEMOTE_LENS = "demote_lens"
    ADJUST_ATTENTION_POLICY = "adjust_attention_policy"
    REVISE_GENERATOR = "revise_generator"
    COORDINATED_SUBSTITUTION = "coordinated_substitution"


class CouncilTournamentDisposition(str, Enum):
    RECOMMEND = "recommend"
    ABSTAIN = "abstain"


class CouncilInterventionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = COUNCIL_INTERVENTION_POLICY_VERSION
    minimum_candidates: int = Field(default=2, ge=2, le=16)
    maximum_candidates: int = Field(default=8, ge=2, le=32)

    @model_validator(mode="after")
    def validate_policy(self) -> "CouncilInterventionPolicy":
        if self.minimum_candidates > self.maximum_candidates:
            raise ValueError("Council candidate bounds are reversed.")
        if not self.policy_version.strip():
            raise ValueError("Council intervention policy version cannot be empty.")
        return self


class CouncilInterventionCandidate(FrozenRecord):
    candidate_id: str
    diagnostic_result_id: str
    kind: InterventionKind
    target_component_refs: tuple[str, ...] = Field(min_length=1)
    proposed_variant_ref: str
    basis_refs: tuple[str, ...] = Field(min_length=1)
    policy_version: str = COUNCIL_INTERVENTION_POLICY_VERSION

    @classmethod
    def build(cls, **values: Any) -> "CouncilInterventionCandidate":
        values.setdefault("policy_version", COUNCIL_INTERVENTION_POLICY_VERSION)
        for key in ("target_component_refs", "basis_refs"):
            values[key] = tuple(sorted(set(values[key])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "candidate_id"
        }
        return cls(candidate_id=stable_id("council_intervention", payload), **values)

    @model_validator(mode="after")
    def validate_candidate(self) -> "CouncilInterventionCandidate":
        required = (
            self.diagnostic_result_id,
            self.proposed_variant_ref,
            self.policy_version,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Council intervention identity fields cannot be empty.")
        for values, label in (
            (self.target_component_refs, "component refs"),
            (self.basis_refs, "basis refs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Council intervention {label} must be sorted and unique.")
        if self.diagnostic_result_id not in self.basis_refs:
            raise ValueError("Council intervention must cite its Diagnostic Result.")
        payload = self.model_dump(mode="json", exclude={"candidate_id"})
        if self.candidate_id != stable_id("council_intervention", payload):
            raise ValueError("Council intervention checksum mismatch.")
        return self

    @property
    def component_footprint(self) -> int:
        return len(self.target_component_refs)


class OrthogonalFingerprintObservation(FrozenRecord):
    context_ref: str
    before_fingerprint: str
    after_fingerprint: str

    @model_validator(mode="after")
    def validate_observation(self) -> "OrthogonalFingerprintObservation":
        if not self.context_ref.strip():
            raise ValueError("Orthogonal context ref cannot be empty.")
        for digest in (self.before_fingerprint, self.after_fingerprint):
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise ValueError("Orthogonal fingerprints must be lowercase SHA-256.")
        return self

    @property
    def stable(self) -> bool:
        return self.before_fingerprint == self.after_fingerprint


class EpistemicPreservationObservation(FrozenRecord):
    evaluation_id: str
    candidate_id: str
    simulation_settlement_id: str
    checkpoint_fingerprint: str
    repair_restored: bool
    would_reopen_obligation_ids: tuple[str, ...] = ()
    wave_state_deviation_ppm: int = Field(ge=0)
    c_memory_deviation_units: int = Field(ge=0)
    tg_observer_deviation_ppm: int = Field(ge=0)
    orthogonal_fingerprints: tuple[OrthogonalFingerprintObservation, ...] = Field(
        min_length=1
    )
    basis_refs: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(cls, **values: Any) -> "EpistemicPreservationObservation":
        for key in ("would_reopen_obligation_ids", "basis_refs"):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        observations = tuple(
            item if isinstance(item, OrthogonalFingerprintObservation)
            else OrthogonalFingerprintObservation.model_validate(item)
            for item in values["orthogonal_fingerprints"]
        )
        values["orthogonal_fingerprints"] = tuple(
            sorted(observations, key=lambda item: item.context_ref)
        )
        payload = {
            key: [item.model_dump(mode="json") for item in value]
            if key == "orthogonal_fingerprints"
            else value
            for key, value in values.items()
            if key != "evaluation_id"
        }
        return cls(
            evaluation_id=stable_id("epistemic_preservation", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_evaluation(self) -> "EpistemicPreservationObservation":
        required = (
            self.candidate_id,
            self.simulation_settlement_id,
            self.checkpoint_fingerprint,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Preservation observation identifiers cannot be empty.")
        if len(self.checkpoint_fingerprint) != 64:
            raise ValueError("Preservation checkpoint fingerprint must be SHA-256.")
        if tuple(sorted(set(self.would_reopen_obligation_ids))) != (
            self.would_reopen_obligation_ids
        ):
            raise ValueError("Blast-radius obligation refs must be sorted and unique.")
        if tuple(sorted(set(self.basis_refs))) != self.basis_refs:
            raise ValueError("Preservation basis refs must be sorted and unique.")
        contexts = tuple(item.context_ref for item in self.orthogonal_fingerprints)
        if tuple(sorted(set(contexts))) != contexts:
            raise ValueError("Orthogonal validation contexts must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"evaluation_id"})
        if self.evaluation_id != stable_id("epistemic_preservation", payload):
            raise ValueError("Preservation observation checksum mismatch.")
        return self

    @property
    def orthogonal_stable(self) -> bool:
        return all(item.stable for item in self.orthogonal_fingerprints)

    @property
    def preservation_vector(self) -> tuple[int, int, int, int]:
        return (
            len(self.would_reopen_obligation_ids),
            self.wave_state_deviation_ppm,
            self.c_memory_deviation_units,
            self.tg_observer_deviation_ppm,
        )


class CouncilCandidateAssessment(FrozenRecord):
    candidate_id: str
    admissible: bool
    exclusion_codes: tuple[str, ...] = ()
    preservation_vector: tuple[int, int, int, int]
    regret_rank_vector: tuple[int, ...] = ()
    maximum_regret_rank: int | None = Field(default=None, ge=1)
    total_regret_rank: int | None = Field(default=None, ge=1)
    component_footprint: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_assessment(self) -> "CouncilCandidateAssessment":
        if not self.candidate_id.strip():
            raise ValueError("Council assessment candidate cannot be empty.")
        if tuple(sorted(set(self.exclusion_codes))) != self.exclusion_codes:
            raise ValueError("Council exclusion codes must be sorted and unique.")
        if any(value < 0 for value in self.preservation_vector):
            raise ValueError("Council preservation metrics cannot be negative.")
        ranked = bool(self.regret_rank_vector)
        if self.admissible != ranked:
            raise ValueError("Only admissible Council candidates receive regret ranks.")
        if self.admissible:
            if len(self.regret_rank_vector) != 4:
                raise ValueError("Council regret rank vector must cover four metrics.")
            if any(value < 1 for value in self.regret_rank_vector):
                raise ValueError("Council regret ranks must be positive.")
            if self.maximum_regret_rank != max(self.regret_rank_vector):
                raise ValueError("Council maximum regret rank is inconsistent.")
            if self.total_regret_rank != sum(self.regret_rank_vector):
                raise ValueError("Council total regret rank is inconsistent.")
            if self.exclusion_codes:
                raise ValueError("Admissible Council candidate cannot be excluded.")
        elif self.maximum_regret_rank is not None or self.total_regret_rank is not None:
            raise ValueError("Excluded Council candidate cannot carry regret ranks.")
        return self


class CouncilTournamentDecision(FrozenRecord):
    decision_id: str
    source_event_key: str
    sequence: int = Field(ge=1)
    diagnostic_result_id: str
    disposition: CouncilTournamentDisposition
    candidate_ids: tuple[str, ...] = Field(min_length=2)
    pareto_frontier_candidate_ids: tuple[str, ...] = ()
    selected_candidate_id: str | None = None
    assessments: tuple[CouncilCandidateAssessment, ...] = Field(min_length=2)
    request_sha256: str
    policy_version: str = COUNCIL_INTERVENTION_POLICY_VERSION
    intervention_authority_enabled: bool = False

    @classmethod
    def build(cls, **values: Any) -> "CouncilTournamentDecision":
        values.setdefault("policy_version", COUNCIL_INTERVENTION_POLICY_VERSION)
        values.setdefault("intervention_authority_enabled", False)
        for key in ("candidate_ids", "pareto_frontier_candidate_ids"):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        assessments = tuple(
            item if isinstance(item, CouncilCandidateAssessment)
            else CouncilCandidateAssessment.model_validate(item)
            for item in values["assessments"]
        )
        values["assessments"] = tuple(
            sorted(assessments, key=lambda item: item.candidate_id)
        )
        payload = {
            key: value.value if isinstance(value, Enum)
            else [item.model_dump(mode="json") for item in value]
            if key == "assessments"
            else value
            for key, value in values.items()
            if key != "decision_id"
        }
        return cls(
            decision_id=stable_id("council_tournament_decision", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_decision(self) -> "CouncilTournamentDecision":
        if not self.source_event_key.strip() or not self.diagnostic_result_id.strip():
            raise ValueError("Council decision identity fields cannot be empty.")
        if self.intervention_authority_enabled:
            raise ValueError("Experimental Council decisions cannot apply interventions.")
        if len(self.request_sha256) != 64 or any(
            ch not in "0123456789abcdef" for ch in self.request_sha256
        ):
            raise ValueError("Council request hash must be lowercase SHA-256.")
        if tuple(sorted(set(self.candidate_ids))) != self.candidate_ids:
            raise ValueError("Council candidate IDs must be sorted and unique.")
        if tuple(sorted(set(self.pareto_frontier_candidate_ids))) != (
            self.pareto_frontier_candidate_ids
        ):
            raise ValueError("Council Pareto frontier must be sorted and unique.")
        assessment_ids = tuple(item.candidate_id for item in self.assessments)
        if tuple(sorted(set(assessment_ids))) != assessment_ids:
            raise ValueError("Council assessments must be sorted and unique.")
        if assessment_ids != self.candidate_ids:
            raise ValueError("Council decision must assess every candidate exactly once.")
        if not set(self.pareto_frontier_candidate_ids).issubset(self.candidate_ids):
            raise ValueError("Council Pareto frontier references an unknown candidate.")
        admissible_ids = tuple(
            item.candidate_id for item in self.assessments if item.admissible
        )
        if admissible_ids != self.pareto_frontier_candidate_ids:
            raise ValueError("Council frontier must equal the admissible assessments.")
        if self.disposition == CouncilTournamentDisposition.RECOMMEND:
            if self.selected_candidate_id not in self.pareto_frontier_candidate_ids:
                raise ValueError("Council recommendation must select from the frontier.")
            expected = min(
                (item for item in self.assessments if item.admissible),
                key=lambda item: (
                    item.maximum_regret_rank,
                    item.total_regret_rank,
                    item.component_footprint,
                    item.candidate_id,
                ),
            ).candidate_id
            if self.selected_candidate_id != expected:
                raise ValueError("Council recommendation violates least-regret ordering.")
        elif self.selected_candidate_id is not None or self.pareto_frontier_candidate_ids:
            raise ValueError("Council abstention cannot select or expose a frontier.")
        payload = self.model_dump(mode="json", exclude={"decision_id"})
        if self.decision_id != stable_id("council_tournament_decision", payload):
            raise ValueError("Council tournament decision checksum mismatch.")
        return self


class CouncilInterventionLedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = COUNCIL_INTERVENTION_LEDGER_VERSION
    decisions: tuple[CouncilTournamentDecision, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> "CouncilInterventionLedgerState":
        if self.schema_version != COUNCIL_INTERVENTION_LEDGER_VERSION:
            raise ValueError("Unsupported Council intervention ledger schema.")
        ids = tuple(item.decision_id for item in self.decisions)
        sources = tuple(item.source_event_key for item in self.decisions)
        if len(set(ids)) != len(ids) or len(set(sources)) != len(sources):
            raise ValueError("Council intervention ledger duplicates an event.")
        for expected, decision in enumerate(self.decisions, start=1):
            if decision.sequence != expected:
                raise ValueError("Council intervention sequence is not contiguous.")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.model_dump(mode="json"))
        ).hexdigest()


def _dominates(left: tuple[int, ...], right: tuple[int, ...]) -> bool:
    return all(a <= b for a, b in zip(left, right, strict=True)) and any(
        a < b for a, b in zip(left, right, strict=True)
    )


class CouncilLeastRegretTournament:
    def __init__(
        self,
        policy: CouncilInterventionPolicy | None = None,
        state: CouncilInterventionLedgerState | None = None,
    ) -> None:
        self.policy = policy or CouncilInterventionPolicy()
        self.state = state or CouncilInterventionLedgerState()

    @classmethod
    def from_snapshot(
        cls,
        payload: dict[str, Any],
        policy: CouncilInterventionPolicy | None = None,
    ) -> "CouncilLeastRegretTournament":
        return cls(
            policy=policy,
            state=CouncilInterventionLedgerState.model_validate(payload),
        )

    def snapshot(self) -> dict[str, Any]:
        return self.state.model_dump(mode="json")

    def fingerprint(self) -> str:
        return self.state.fingerprint()

    @staticmethod
    def _diagnostic_result(
        diagnostics: DiagnosticEngine,
        result_id: str,
    ) -> tuple[DiagnosticResult, Any]:
        result = next(
            (item for item in diagnostics.state.results if item.result_id == result_id),
            None,
        )
        if result is None:
            raise CouncilInterventionIntegrityError("Unknown Diagnostic Result.")
        obligation = next(
            item for item in diagnostics.state.obligations
            if item.diagnostic_id == result.diagnostic_id
        )
        if result.conclusion in {
            DiagnosticConclusion.VALID_NULL,
            DiagnosticConclusion.INCONCLUSIVE,
        }:
            raise CouncilInterventionIntegrityError(
                "Null or inconclusive diagnostics cannot authorize a tournament."
            )
        return result, obligation

    def decide(
        self,
        kernel: VerdantKernel,
        *,
        diagnostic_result_id: str,
        candidates: Sequence[CouncilInterventionCandidate],
        evaluations: Sequence[EpistemicPreservationObservation],
        diagnostics: DiagnosticEngine,
        simulation_ledger: SimulationLedger,
        lens_system: EquivalenceLensSystem,
        source_event_key: str,
    ) -> CouncilTournamentDecision:
        result, diagnostic = self._diagnostic_result(
            diagnostics, diagnostic_result_id
        )
        normalized_candidates = tuple(sorted(candidates, key=lambda item: item.candidate_id))
        normalized_evaluations = tuple(
            sorted(evaluations, key=lambda item: item.candidate_id)
        )
        if not (
            self.policy.minimum_candidates
            <= len(normalized_candidates)
            <= self.policy.maximum_candidates
        ):
            raise CouncilInterventionIntegrityError("Council candidate count is out of bounds.")
        candidate_ids = tuple(item.candidate_id for item in normalized_candidates)
        if len(set(candidate_ids)) != len(candidate_ids):
            raise CouncilInterventionIntegrityError("Council candidate is duplicated.")
        evaluation_ids = tuple(item.candidate_id for item in normalized_evaluations)
        if evaluation_ids != candidate_ids:
            raise CouncilInterventionIntegrityError(
                "Every Council candidate requires exactly one preservation observation."
            )
        validation_suites = {
            tuple(item.context_ref for item in evaluation.orthogonal_fingerprints)
            for evaluation in normalized_evaluations
        }
        if len(validation_suites) != 1:
            raise CouncilInterventionIntegrityError(
                "Council candidates must share one orthogonal validation suite."
            )
        known_components = {
            diagnostic.trigger.attention_decision_id,
            diagnostic.trigger.hypothesis_ref,
            diagnostic.trigger.lens_binding_id,
            diagnostic.trigger.lens_definition_id,
        }
        known_components.update(result.attributed_component_refs)
        binding = lens_system.binding_view(diagnostic.trigger.lens_binding_id).binding
        definition = lens_system.registry.definitions[
            diagnostic.trigger.lens_definition_id
        ]
        binding_components = {binding.binding_id}
        definition_components = {definition.definition_id}
        if binding.predecessor_binding_id is not None:
            binding_components.add(binding.predecessor_binding_id)
            known_components.add(binding.predecessor_binding_id)
        if definition.parent_definition_id is not None:
            definition_components.add(definition.parent_definition_id)
            known_components.add(definition.parent_definition_id)
        for candidate in normalized_candidates:
            if candidate.diagnostic_result_id != diagnostic_result_id:
                raise CouncilInterventionIntegrityError(
                    "Council candidate crossed a Diagnostic Result boundary."
                )
            if candidate.policy_version != self.policy.policy_version:
                raise CouncilInterventionIntegrityError(
                    "Council candidate policy version drifted."
                )
            if not set(candidate.target_component_refs).issubset(known_components):
                raise CouncilInterventionIntegrityError(
                    "Council candidate targets an unknown causal component."
                )
            targets = set(candidate.target_component_refs)
            typed_target_ok = {
                InterventionKind.ROLLBACK_BINDING: (
                    len(targets) == 1 and targets.issubset(binding_components)
                ),
                InterventionKind.DEMOTE_LENS: (
                    len(targets) == 1 and targets.issubset(definition_components)
                ),
                InterventionKind.ADJUST_ATTENTION_POLICY: targets == {
                    diagnostic.trigger.attention_decision_id
                },
                InterventionKind.REVISE_GENERATOR: targets == {
                    diagnostic.trigger.hypothesis_ref
                },
                InterventionKind.COORDINATED_SUBSTITUTION: len(targets) >= 2,
            }[candidate.kind]
            if not typed_target_ok:
                raise CouncilInterventionIntegrityError(
                    "Council intervention kind does not match its component target."
                )
        settlements = {
            item.settlement_id: item for item in simulation_ledger.state.settlements
        }
        reservations = {
            item.reservation_id: item for item in simulation_ledger.state.reservations
        }
        known_obligations = set(kernel.state.obligation_kernels)
        exclusions: dict[str, tuple[str, ...]] = {}
        for evaluation in normalized_evaluations:
            candidate = next(
                item for item in normalized_candidates
                if item.candidate_id == evaluation.candidate_id
            )
            codes: set[str] = set()
            if evaluation.checkpoint_fingerprint != kernel.fingerprint():
                codes.add("checkpoint_mismatch")
            settlement = settlements.get(evaluation.simulation_settlement_id)
            if (
                settlement is None
                or not settlement.canonical_unchanged
                or settlement.disposition != SimulationDisposition.DISCARDED
            ):
                codes.add("simulation_unverified")
            else:
                reservation = reservations[settlement.reservation_id]
                if reservation.obligation_id != diagnostic.trigger.obligation_id:
                    codes.add("obligation_boundary_crossed")
                required_lineage = {
                    candidate.candidate_id,
                    *evaluation.basis_refs,
                }
                if not required_lineage.issubset(set(settlement.result_refs)):
                    codes.add("simulation_lineage_missing")
            if not set(evaluation.would_reopen_obligation_ids).issubset(
                known_obligations
            ):
                codes.add("blast_radius_unverified")
            if not evaluation.repair_restored:
                codes.add("repair_not_restored")
            if not evaluation.orthogonal_stable:
                codes.add("orthogonal_fingerprint_changed")
            exclusions[evaluation.candidate_id] = tuple(sorted(codes))

        admissible_evaluations = tuple(
            item for item in normalized_evaluations if not exclusions[item.candidate_id]
        )
        frontier = tuple(
            item
            for item in admissible_evaluations
            if not any(
                other.candidate_id != item.candidate_id
                and _dominates(other.preservation_vector, item.preservation_vector)
                for other in admissible_evaluations
            )
        )
        rank_maps: list[dict[int, int]] = []
        if frontier:
            for dimension in range(4):
                ordered = sorted({item.preservation_vector[dimension] for item in frontier})
                rank_maps.append({value: index + 1 for index, value in enumerate(ordered)})
        frontier_ids = {item.candidate_id for item in frontier}
        assessments = []
        by_candidate = {item.candidate_id: item for item in normalized_candidates}
        by_evaluation = {item.candidate_id: item for item in normalized_evaluations}
        for candidate_id in candidate_ids:
            candidate = by_candidate[candidate_id]
            evaluation = by_evaluation[candidate_id]
            codes = set(exclusions[candidate_id])
            if not codes and candidate_id not in frontier_ids:
                codes.add("pareto_dominated")
            admissible = candidate_id in frontier_ids
            ranks = tuple(
                rank_maps[index][value]
                for index, value in enumerate(evaluation.preservation_vector)
            ) if admissible else ()
            assessments.append(
                CouncilCandidateAssessment(
                    candidate_id=candidate_id,
                    admissible=admissible,
                    exclusion_codes=tuple(sorted(codes)),
                    preservation_vector=evaluation.preservation_vector,
                    regret_rank_vector=ranks,
                    maximum_regret_rank=max(ranks) if ranks else None,
                    total_regret_rank=sum(ranks) if ranks else None,
                    component_footprint=candidate.component_footprint,
                )
            )
        if frontier:
            assessment_by_id = {item.candidate_id: item for item in assessments}
            selected = min(
                frontier,
                key=lambda item: (
                    assessment_by_id[item.candidate_id].maximum_regret_rank,
                    assessment_by_id[item.candidate_id].total_regret_rank,
                    by_candidate[item.candidate_id].component_footprint,
                    item.candidate_id,
                ),
            ).candidate_id
            disposition = CouncilTournamentDisposition.RECOMMEND
            pareto_ids = tuple(sorted(frontier_ids))
        else:
            selected = None
            disposition = CouncilTournamentDisposition.ABSTAIN
            pareto_ids = ()
        replay = next(
            (
                item for item in self.state.decisions
                if item.source_event_key == source_event_key
            ),
            None,
        )
        sequence = replay.sequence if replay is not None else len(self.state.decisions) + 1
        request_payload = {
            "policy": self.policy.model_dump(mode="json"),
            "diagnostic_result_id": diagnostic_result_id,
            "candidates": tuple(
                item.model_dump(mode="json") for item in normalized_candidates
            ),
            "evaluations": tuple(
                item.model_dump(mode="json") for item in normalized_evaluations
            ),
        }
        request_sha256 = hashlib.sha256(
            canonical_json_bytes(request_payload)
        ).hexdigest()
        candidate = CouncilTournamentDecision.build(
            source_event_key=source_event_key,
            sequence=sequence,
            diagnostic_result_id=diagnostic_result_id,
            disposition=disposition,
            candidate_ids=candidate_ids,
            pareto_frontier_candidate_ids=pareto_ids,
            selected_candidate_id=selected,
            assessments=tuple(assessments),
            request_sha256=request_sha256,
            policy_version=self.policy.policy_version,
        )
        if replay is not None:
            if candidate != replay:
                raise CouncilInterventionIntegrityError(
                    "Council source event key was reused with changed evidence."
                )
            return replay
        updated = self.state.model_copy(
            update={"decisions": (*self.state.decisions, candidate)},
            deep=True,
        )
        self.state = CouncilInterventionLedgerState.model_validate(
            updated.model_dump(mode="json")
        )
        return candidate
