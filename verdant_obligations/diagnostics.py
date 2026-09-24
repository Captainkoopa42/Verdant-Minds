"""Bounded, non-recursive Diagnostic Obligations.

Diagnostics are an experimental sidecar over canonical Attention records,
counterfactual settlements, and Equivalence-Lens bindings.  They attribute an
operational inquiry failure without editing any component.  Every diagnostic
terminates once; a failed or inconclusive diagnostic cannot spawn another
diagnostic about itself.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import SimulationLedger
from .equivalence import EquivalenceLensSystem
from .pipeline import ObligationIntegrityError


DIAGNOSTIC_POLICY_VERSION = "diagnostic_obligation_policy_v0.8"
DIAGNOSTIC_LEDGER_SCHEMA_VERSION = "diagnostic_obligation_ledger_v0.8"


class DiagnosticIntegrityError(RuntimeError):
    pass


class DiagnosticRecursionError(DiagnosticIntegrityError):
    pass


class DiagnosticTriggerKind(str, Enum):
    INQUIRY_FAILURE = "inquiry_failure"
    EVALUATOR_TRIPWIRE = "evaluator_tripwire"


class DiagnosticProbeKind(str, Enum):
    PRIMITIVE_BASELINE = "primitive_baseline"
    ADJACENT_CONTEXT = "adjacent_context"
    GENERATOR_COHERENCE = "generator_coherence"
    COST_CALIBRATION = "cost_calibration"


class DiagnosticProbeFinding(str, Enum):
    AGREED = "agreed"
    LENS_COLLAPSED_DISTINCT = "lens_collapsed_distinct"
    LENS_SPLIT_EQUIVALENT = "lens_split_equivalent"
    RECOVERED = "recovered"
    NOT_RECOVERED = "not_recovered"
    TOPOLOGY_VALID = "topology_valid"
    TOPOLOGY_INVALID = "topology_invalid"
    COST_WITHIN_BOUND = "cost_within_bound"
    COST_EXCEEDED = "cost_exceeded"
    GAIN_IMPOSSIBLE = "gain_impossible"
    INCONCLUSIVE = "inconclusive"


class DiagnosticConclusion(str, Enum):
    VALID_NULL = "valid_null"
    LENS_OVER_SMOOTHING = "lens_over_smoothing"
    LENS_HYPER_DISCRIMINATION = "lens_hyper_discrimination"
    BINDING_MISCALIBRATION = "binding_miscalibration"
    GENERATOR_FAULT = "generator_fault"
    SCHEDULER_MISALIGNMENT = "scheduler_misalignment"
    INTERACTION_SUSPECTED = "interaction_suspected"
    INCONCLUSIVE = "inconclusive"


class DiagnosticPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = DIAGNOSTIC_POLICY_VERSION
    maximum_probes: int = Field(default=4, ge=1, le=8)
    maximum_simulation_budget: float = Field(default=0.08, gt=0.0)
    maximum_diagnostic_depth: int = Field(default=1, ge=1, le=1)


class InquiryFailureEvidence(FrozenRecord):
    evidence_id: str
    trigger_kind: DiagnosticTriggerKind
    attention_decision_id: str
    failed_settlement_id: str
    obligation_id: str
    lens_binding_id: str
    lens_definition_id: str
    hypothesis_ref: str
    completed_within_predicted_cost: bool
    graph_traversal_valid: bool
    action_executed: bool
    explanatory_gain_observed: bool
    evidence_refs: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(cls, **values: Any) -> "InquiryFailureEvidence":
        values["evidence_refs"] = tuple(sorted(set(values["evidence_refs"])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "evidence_id"
        }
        return cls(
            evidence_id=stable_id("inquiry_failure_evidence", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_evidence(self) -> "InquiryFailureEvidence":
        required = (
            self.attention_decision_id,
            self.failed_settlement_id,
            self.obligation_id,
            self.lens_binding_id,
            self.lens_definition_id,
            self.hypothesis_ref,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Inquiry failure evidence identifiers cannot be empty.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Inquiry failure evidence refs must be sorted and unique.")
        if (
            self.trigger_kind == DiagnosticTriggerKind.INQUIRY_FAILURE
            and self.completed_within_predicted_cost
            and self.graph_traversal_valid
            and self.action_executed
            and self.explanatory_gain_observed
        ):
            raise ValueError("A successful inquiry cannot trigger a diagnostic.")
        payload = self.model_dump(mode="json", exclude={"evidence_id"})
        if self.evidence_id != stable_id("inquiry_failure_evidence", payload):
            raise ValueError("Inquiry failure evidence checksum mismatch.")
        return self

    @property
    def is_valid_null(self) -> bool:
        return (
            self.completed_within_predicted_cost
            and self.graph_traversal_valid
            and self.action_executed
            and not self.explanatory_gain_observed
        )


class DiagnosticObligation(FrozenRecord):
    diagnostic_id: str
    source_event_key: str
    sequence: int = Field(ge=1)
    creation_cycle: int = Field(ge=0)
    diagnostic_depth: int = Field(ge=1, le=1)
    trigger: InquiryFailureEvidence
    policy_version: str = DIAGNOSTIC_POLICY_VERSION
    epistemic_authority_enabled: bool = False

    @classmethod
    def build(cls, **values: Any) -> "DiagnosticObligation":
        values.setdefault("diagnostic_depth", 1)
        values.setdefault("policy_version", DIAGNOSTIC_POLICY_VERSION)
        values.setdefault("epistemic_authority_enabled", False)
        payload = {
            key: value.model_dump(mode="json") if isinstance(value, BaseModel) else value
            for key, value in values.items()
            if key != "diagnostic_id"
        }
        return cls(
            diagnostic_id=stable_id("diagnostic_obligation", payload),
            **values,
        )

    @model_validator(mode="after")
    def validate_obligation(self) -> "DiagnosticObligation":
        if not self.source_event_key.strip() or not self.policy_version.strip():
            raise ValueError("Diagnostic obligation identity fields cannot be empty.")
        if self.epistemic_authority_enabled:
            raise ValueError("Diagnostic obligations cannot carry epistemic authority.")
        payload = self.model_dump(mode="json", exclude={"diagnostic_id"})
        if self.diagnostic_id != stable_id("diagnostic_obligation", payload):
            raise ValueError("Diagnostic obligation checksum mismatch.")
        return self


class DiagnosticProbeObservation(FrozenRecord):
    probe_id: str
    diagnostic_id: str
    kind: DiagnosticProbeKind
    finding: DiagnosticProbeFinding
    simulation_settlement_id: str
    basis_refs: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(cls, **values: Any) -> "DiagnosticProbeObservation":
        values["basis_refs"] = tuple(sorted(set(values["basis_refs"])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "probe_id"
        }
        return cls(probe_id=stable_id("diagnostic_probe", payload), **values)

    @model_validator(mode="after")
    def validate_probe(self) -> "DiagnosticProbeObservation":
        if not self.diagnostic_id.strip() or not self.simulation_settlement_id.strip():
            raise ValueError("Diagnostic probe identifiers cannot be empty.")
        if tuple(sorted(set(self.basis_refs))) != self.basis_refs:
            raise ValueError("Diagnostic probe basis refs must be sorted and unique.")
        allowed = {
            DiagnosticProbeKind.PRIMITIVE_BASELINE: {
                DiagnosticProbeFinding.AGREED,
                DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT,
                DiagnosticProbeFinding.LENS_SPLIT_EQUIVALENT,
                DiagnosticProbeFinding.INCONCLUSIVE,
            },
            DiagnosticProbeKind.ADJACENT_CONTEXT: {
                DiagnosticProbeFinding.RECOVERED,
                DiagnosticProbeFinding.NOT_RECOVERED,
                DiagnosticProbeFinding.INCONCLUSIVE,
            },
            DiagnosticProbeKind.GENERATOR_COHERENCE: {
                DiagnosticProbeFinding.TOPOLOGY_VALID,
                DiagnosticProbeFinding.TOPOLOGY_INVALID,
                DiagnosticProbeFinding.INCONCLUSIVE,
            },
            DiagnosticProbeKind.COST_CALIBRATION: {
                DiagnosticProbeFinding.COST_WITHIN_BOUND,
                DiagnosticProbeFinding.COST_EXCEEDED,
                DiagnosticProbeFinding.GAIN_IMPOSSIBLE,
                DiagnosticProbeFinding.INCONCLUSIVE,
            },
        }
        if self.finding not in allowed[self.kind]:
            raise ValueError("Diagnostic probe finding does not match its probe kind.")
        payload = self.model_dump(mode="json", exclude={"probe_id"})
        if self.probe_id != stable_id("diagnostic_probe", payload):
            raise ValueError("Diagnostic probe checksum mismatch.")
        return self


class DiagnosticResult(FrozenRecord):
    result_id: str
    source_event_key: str
    sequence: int = Field(ge=2)
    diagnostic_id: str
    conclusion: DiagnosticConclusion
    attributed_component_refs: tuple[str, ...] = ()
    probe_ids: tuple[str, ...] = ()
    consumed_simulation_budget: float = Field(ge=0.0)
    terminal: bool = True
    may_spawn_diagnostic: bool = False
    epistemic_authority_enabled: bool = False
    policy_version: str = DIAGNOSTIC_POLICY_VERSION

    @classmethod
    def build(cls, **values: Any) -> "DiagnosticResult":
        values.setdefault("terminal", True)
        values.setdefault("may_spawn_diagnostic", False)
        values.setdefault("epistemic_authority_enabled", False)
        values.setdefault("policy_version", DIAGNOSTIC_POLICY_VERSION)
        for key in ("attributed_component_refs", "probe_ids"):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "result_id"
        }
        return cls(result_id=stable_id("diagnostic_result", payload), **values)

    @model_validator(mode="after")
    def validate_result(self) -> "DiagnosticResult":
        if not self.source_event_key.strip() or not self.diagnostic_id.strip():
            raise ValueError("Diagnostic result identifiers cannot be empty.")
        for values, label in (
            (self.attributed_component_refs, "component refs"),
            (self.probe_ids, "probe IDs"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Diagnostic result {label} must be sorted and unique.")
        if not self.terminal or self.may_spawn_diagnostic:
            raise ValueError("Every diagnostic result must terminate without recursion.")
        if self.epistemic_authority_enabled:
            raise ValueError("Diagnostic results cannot carry epistemic authority.")
        unattributed = {
            DiagnosticConclusion.VALID_NULL,
            DiagnosticConclusion.INCONCLUSIVE,
        }
        if self.conclusion in unattributed and self.attributed_component_refs:
            raise ValueError("Null and inconclusive diagnostics cannot attribute fault.")
        if self.conclusion not in unattributed and not self.attributed_component_refs:
            raise ValueError("A fault conclusion requires attributed component refs.")
        if (
            self.conclusion == DiagnosticConclusion.INTERACTION_SUSPECTED
            and len(self.attributed_component_refs) < 2
        ):
            raise ValueError("An interaction fault requires at least two components.")
        payload = self.model_dump(mode="json", exclude={"result_id"})
        if self.result_id != stable_id("diagnostic_result", payload):
            raise ValueError("Diagnostic result checksum mismatch.")
        return self


class DiagnosticLedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = DIAGNOSTIC_LEDGER_SCHEMA_VERSION
    obligations: tuple[DiagnosticObligation, ...] = ()
    results: tuple[DiagnosticResult, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> "DiagnosticLedgerState":
        if self.schema_version != DIAGNOSTIC_LEDGER_SCHEMA_VERSION:
            raise ValueError("Unsupported Diagnostic Obligation ledger schema.")
        obligation_ids = tuple(item.diagnostic_id for item in self.obligations)
        result_ids = tuple(item.result_id for item in self.results)
        source_keys = tuple(
            item.source_event_key for item in (*self.obligations, *self.results)
        )
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("Diagnostic ledger duplicates an obligation.")
        if len(set(result_ids)) != len(result_ids):
            raise ValueError("Diagnostic ledger duplicates a result.")
        if len(set(source_keys)) != len(source_keys):
            raise ValueError("Diagnostic ledger reuses a source event key.")
        known = set(obligation_ids)
        concluded: set[str] = set()
        for result in self.results:
            if result.diagnostic_id not in known:
                raise ValueError("Diagnostic result lost its obligation.")
            if result.diagnostic_id in concluded:
                raise ValueError("A Diagnostic Obligation concluded more than once.")
            concluded.add(result.diagnostic_id)
        expected_sequence = 1
        events = sorted(
            [*self.obligations, *self.results],
            key=lambda item: item.sequence,
        )
        for event in events:
            if event.sequence != expected_sequence:
                raise ValueError("Diagnostic ledger sequence is not contiguous.")
            expected_sequence += 1
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.model_dump(mode="json"))
        ).hexdigest()


class DiagnosticEngine:
    def __init__(
        self,
        policy: DiagnosticPolicy | None = None,
        state: DiagnosticLedgerState | None = None,
    ) -> None:
        self.policy = policy or DiagnosticPolicy()
        self.state = state or DiagnosticLedgerState()

    @classmethod
    def from_snapshot(
        cls,
        payload: dict[str, Any],
        policy: DiagnosticPolicy | None = None,
    ) -> "DiagnosticEngine":
        return cls(policy=policy, state=DiagnosticLedgerState.model_validate(payload))

    def snapshot(self) -> dict[str, Any]:
        return self.state.model_dump(mode="json")

    def fingerprint(self) -> str:
        return self.state.fingerprint()

    @staticmethod
    def _decision(kernel: VerdantKernel, decision_id: str):
        return next(
            (
                item
                for item in kernel.state.obligation_attention_decisions
                if item.decision_id == decision_id
            ),
            None,
        )

    @staticmethod
    def _settlement(simulation_ledger: SimulationLedger, settlement_id: str):
        return next(
            (
                item
                for item in simulation_ledger.state.settlements
                if item.settlement_id == settlement_id
            ),
            None,
        )

    def open(
        self,
        kernel: VerdantKernel,
        *,
        trigger: InquiryFailureEvidence,
        simulation_ledger: SimulationLedger,
        lens_system: EquivalenceLensSystem,
        source_event_key: str,
    ) -> DiagnosticObligation:
        replay = next(
            (
                item for item in self.state.obligations
                if item.source_event_key == source_event_key
            ),
            None,
        )
        if replay is not None:
            candidate = DiagnosticObligation.build(
                source_event_key=source_event_key,
                sequence=replay.sequence,
                creation_cycle=replay.creation_cycle,
                trigger=trigger,
                policy_version=self.policy.policy_version,
            )
            if candidate != replay:
                raise DiagnosticIntegrityError(
                    "Diagnostic source event key was reused with a changed request."
                )
            return replay
        if any(
            item.source_event_key == source_event_key for item in self.state.results
        ):
            raise DiagnosticIntegrityError("Diagnostic source event key is unavailable.")
        obligation = kernel.state.obligation_kernels.get(trigger.obligation_id)
        if obligation is None:
            raise ObligationIntegrityError("Diagnostic trigger cites an unknown obligation.")
        decision = self._decision(kernel, trigger.attention_decision_id)
        if decision is None or trigger.obligation_id not in decision.eligible_obligation_ids:
            raise DiagnosticIntegrityError(
                "Diagnostic trigger cites an unrelated Attention decision."
            )
        settlement = self._settlement(
            simulation_ledger, trigger.failed_settlement_id
        )
        if settlement is None or not settlement.canonical_unchanged:
            raise DiagnosticIntegrityError(
                "Diagnostic trigger cites an invalid simulation settlement."
            )
        reservation = next(
            item for item in simulation_ledger.state.reservations
            if item.reservation_id == settlement.reservation_id
        )
        if reservation.obligation_id != trigger.obligation_id:
            raise DiagnosticIntegrityError(
                "Diagnostic settlement crossed an obligation boundary."
            )
        binding = lens_system.binding_view(trigger.lens_binding_id).binding
        if binding.obligation_family != obligation.family:
            raise DiagnosticIntegrityError(
                "Diagnostic lens binding crossed an obligation-family boundary."
            )
        if binding.definition_id != trigger.lens_definition_id:
            raise DiagnosticIntegrityError(
                "Diagnostic trigger cites the wrong lens definition."
            )
        if trigger.hypothesis_ref not in settlement.result_refs:
            raise DiagnosticIntegrityError(
                "Diagnostic hypothesis lacks simulation lineage."
            )
        required_evidence = {
            trigger.attention_decision_id,
            trigger.failed_settlement_id,
            trigger.lens_binding_id,
            trigger.lens_definition_id,
            trigger.hypothesis_ref,
        }
        if not required_evidence.issubset(set(trigger.evidence_refs)):
            raise DiagnosticIntegrityError(
                "Diagnostic trigger omits required causal evidence refs."
            )
        candidate = DiagnosticObligation.build(
            source_event_key=source_event_key,
            sequence=len(self.state.obligations) + len(self.state.results) + 1,
            creation_cycle=kernel.state.cycle,
            trigger=trigger,
            policy_version=self.policy.policy_version,
        )
        updated = self.state.model_copy(
            update={"obligations": (*self.state.obligations, candidate)},
            deep=True,
        )
        self.state = DiagnosticLedgerState.model_validate(
            updated.model_dump(mode="json")
        )
        return candidate

    @staticmethod
    def _conclusion(
        obligation: DiagnosticObligation,
        probes: tuple[DiagnosticProbeObservation, ...],
    ) -> tuple[DiagnosticConclusion, tuple[str, ...]]:
        if obligation.trigger.is_valid_null:
            return DiagnosticConclusion.VALID_NULL, ()
        signals: list[tuple[DiagnosticConclusion, str]] = []
        for probe in probes:
            if probe.finding == DiagnosticProbeFinding.LENS_COLLAPSED_DISTINCT:
                signals.append((
                    DiagnosticConclusion.LENS_OVER_SMOOTHING,
                    obligation.trigger.lens_definition_id,
                ))
            elif probe.finding == DiagnosticProbeFinding.LENS_SPLIT_EQUIVALENT:
                signals.append((
                    DiagnosticConclusion.LENS_HYPER_DISCRIMINATION,
                    obligation.trigger.lens_definition_id,
                ))
            elif probe.finding == DiagnosticProbeFinding.RECOVERED:
                signals.append((
                    DiagnosticConclusion.BINDING_MISCALIBRATION,
                    obligation.trigger.lens_binding_id,
                ))
            elif probe.finding == DiagnosticProbeFinding.TOPOLOGY_INVALID:
                signals.append((
                    DiagnosticConclusion.GENERATOR_FAULT,
                    obligation.trigger.hypothesis_ref,
                ))
            elif probe.finding in {
                DiagnosticProbeFinding.COST_EXCEEDED,
                DiagnosticProbeFinding.GAIN_IMPOSSIBLE,
            }:
                signals.append((
                    DiagnosticConclusion.SCHEDULER_MISALIGNMENT,
                    obligation.trigger.attention_decision_id,
                ))
        distinct = {item[0] for item in signals}
        refs = tuple(sorted({item[1] for item in signals}))
        if len(distinct) == 1:
            return signals[0][0], refs
        if len(distinct) > 1 and len(refs) > 1:
            return DiagnosticConclusion.INTERACTION_SUSPECTED, refs
        return DiagnosticConclusion.INCONCLUSIVE, ()

    def conclude(
        self,
        *,
        diagnostic_id: str,
        probes: Sequence[DiagnosticProbeObservation],
        simulation_ledger: SimulationLedger,
        source_event_key: str,
    ) -> DiagnosticResult:
        obligation = next(
            (
                item for item in self.state.obligations
                if item.diagnostic_id == diagnostic_id
            ),
            None,
        )
        if obligation is None:
            raise DiagnosticIntegrityError("Unknown Diagnostic Obligation.")
        prior = next(
            (item for item in self.state.results if item.diagnostic_id == diagnostic_id),
            None,
        )
        normalized = tuple(sorted(probes, key=lambda item: item.probe_id))
        if len(normalized) > self.policy.maximum_probes:
            raise DiagnosticIntegrityError("Diagnostic probe cap exceeded.")
        if len({item.probe_id for item in normalized}) != len(normalized):
            raise DiagnosticIntegrityError("Diagnostic probe was repeated.")
        if any(item.diagnostic_id != diagnostic_id for item in normalized):
            raise DiagnosticIntegrityError("Diagnostic probe crossed an obligation boundary.")
        settlements = {
            item.settlement_id: item
            for item in simulation_ledger.state.settlements
        }
        selected = []
        for probe in normalized:
            settlement = settlements.get(probe.simulation_settlement_id)
            if settlement is None or not settlement.canonical_unchanged:
                raise DiagnosticIntegrityError(
                    "Diagnostic probe lacks an isolated simulation settlement."
                )
            selected.append(settlement)
        if len({item.settlement_id for item in selected}) != len(selected):
            raise DiagnosticIntegrityError(
                "Diagnostic probes cannot reuse one simulation settlement."
            )
        reservations = {
            item.reservation_id: item
            for item in simulation_ledger.state.reservations
        }
        for probe, settlement in zip(normalized, selected, strict=True):
            reservation = reservations[settlement.reservation_id]
            if reservation.obligation_id != obligation.trigger.obligation_id:
                raise DiagnosticIntegrityError(
                    "Diagnostic probe crossed the parent obligation boundary."
                )
            if diagnostic_id not in settlement.result_refs or not set(
                probe.basis_refs
            ).issubset(set(settlement.result_refs)):
                raise DiagnosticIntegrityError(
                    "Diagnostic probe lacks declared simulation lineage."
                )
        consumed = sum((item.consumed_budget for item in selected), 0.0)
        if consumed > self.policy.maximum_simulation_budget + 1e-12:
            raise DiagnosticIntegrityError("Diagnostic simulation budget exceeded.")
        conclusion, component_refs = self._conclusion(obligation, normalized)
        sequence = (
            prior.sequence if prior is not None
            else len(self.state.obligations) + len(self.state.results) + 1
        )
        candidate = DiagnosticResult.build(
            source_event_key=source_event_key,
            sequence=sequence,
            diagnostic_id=diagnostic_id,
            conclusion=conclusion,
            attributed_component_refs=component_refs,
            probe_ids=tuple(item.probe_id for item in normalized),
            consumed_simulation_budget=consumed,
            policy_version=self.policy.policy_version,
        )
        if prior is not None:
            if candidate != prior:
                raise DiagnosticIntegrityError(
                    "Concluded diagnostic was replayed with changed evidence."
                )
            return prior
        if any(
            item.source_event_key == source_event_key
            for item in (*self.state.obligations, *self.state.results)
        ):
            raise DiagnosticIntegrityError("Diagnostic source event key is unavailable.")
        updated = self.state.model_copy(
            update={"results": (*self.state.results, candidate)},
            deep=True,
        )
        self.state = DiagnosticLedgerState.model_validate(
            updated.model_dump(mode="json")
        )
        return candidate

    def open_from_diagnostic_result(self, result: DiagnosticResult) -> None:
        del result
        raise DiagnosticRecursionError(
            "A Diagnostic Obligation result is terminal and cannot spawn a diagnostic."
        )
