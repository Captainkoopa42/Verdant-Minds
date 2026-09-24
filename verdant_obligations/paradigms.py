"""Governed, shadow-only Paradigm Challenge lane.

The lane admits a high-blast-radius assumption to bounded re-evaluation only
after independent anomaly signals appear in multiple obligation families.  It
replays the complete immutable obligation histories through causally
non-committing simulations and records a Council-style shadow verdict.  It
cannot promote a variant, rewrite policy, or mutate canonical Verdant state.
"""
from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from verdant_kernel import ObligationEventType, ObligationFamily, VerdantKernel
from verdant_kernel.models import FrozenRecord, canonical_json_bytes, stable_id

from .counterfactual import SimulationDisposition, SimulationLedger
from .interventions import OrthogonalFingerprintObservation


PARADIGM_CHALLENGE_POLICY_VERSION = "paradigm_challenge_policy_v0.14"
PARADIGM_CHALLENGE_LEDGER_VERSION = "paradigm_challenge_ledger_v0.14"


class ParadigmChallengeIntegrityError(RuntimeError):
    pass


class ParadigmChallengeDisposition(str, Enum):
    SHADOW_SUPPORTED = "shadow_supported"
    SHADOW_REJECTED = "shadow_rejected"
    ABSTAIN = "abstain"


class ParadigmChallengePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_version: str = PARADIGM_CHALLENGE_POLICY_VERSION
    minimum_obligation_families: int = Field(default=2, ge=2)
    minimum_independent_roots: int = Field(default=2, ge=2)
    minimum_replications_per_obligation: int = Field(default=2, ge=2, le=8)
    maximum_signals: int = Field(default=8, ge=2, le=32)

    @model_validator(mode="after")
    def validate_policy(self) -> "ParadigmChallengePolicy":
        if not self.policy_version.strip():
            raise ValueError("Paradigm Challenge policy version cannot be empty.")
        return self


class ParadigmAnomalySignal(FrozenRecord):
    signal_id: str
    obligation_id: str
    obligation_family: ObligationFamily
    history_event_id: str
    target_assumption_ref: str
    provenance_root: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def build(cls, **values: Any) -> "ParadigmAnomalySignal":
        values["evidence_refs"] = tuple(sorted(set(values["evidence_refs"])))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "signal_id"
        }
        return cls(signal_id=stable_id("paradigm_anomaly_signal", payload), **values)

    @model_validator(mode="after")
    def validate_signal(self) -> "ParadigmAnomalySignal":
        if not all(
            item.strip()
            for item in (
                self.obligation_id,
                self.history_event_id,
                self.target_assumption_ref,
                self.provenance_root,
            )
        ):
            raise ValueError("Paradigm anomaly identifiers cannot be empty.")
        if tuple(sorted(set(self.evidence_refs))) != self.evidence_refs:
            raise ValueError("Paradigm anomaly evidence refs must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"signal_id"})
        if self.signal_id != stable_id("paradigm_anomaly_signal", payload):
            raise ValueError("Paradigm anomaly checksum mismatch.")
        return self


class ParadigmChallenge(FrozenRecord):
    challenge_id: str
    source_event_key: str
    sequence: int = Field(ge=1)
    target_assumption_ref: str
    signals: tuple[ParadigmAnomalySignal, ...] = Field(min_length=2)
    baseline_fingerprint: str
    policy_version: str = PARADIGM_CHALLENGE_POLICY_VERSION
    shadow_only: bool = True
    canonical_mutation_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ParadigmChallenge":
        values.setdefault("policy_version", PARADIGM_CHALLENGE_POLICY_VERSION)
        values.setdefault("shadow_only", True)
        values.setdefault("canonical_mutation_permitted", False)
        values["signals"] = tuple(sorted(values["signals"], key=lambda item: item.signal_id))
        payload = {
            key: [item.model_dump(mode="json") for item in value]
            if key == "signals"
            else value
            for key, value in values.items()
            if key != "challenge_id"
        }
        return cls(challenge_id=stable_id("paradigm_challenge", payload), **values)

    @model_validator(mode="after")
    def validate_challenge(self) -> "ParadigmChallenge":
        if not self.source_event_key.strip() or not self.target_assumption_ref.strip():
            raise ValueError("Paradigm Challenge identifiers cannot be empty.")
        ids = tuple(item.signal_id for item in self.signals)
        if tuple(sorted(set(ids))) != ids:
            raise ValueError("Paradigm Challenge signals must be sorted and unique.")
        if {item.target_assumption_ref for item in self.signals} != {
            self.target_assumption_ref
        }:
            raise ValueError("Paradigm signals do not share one challenged assumption.")
        if len(self.baseline_fingerprint) != 64:
            raise ValueError("Paradigm baseline fingerprint must be SHA-256.")
        if not self.shadow_only or self.canonical_mutation_permitted:
            raise ValueError("Paradigm Challenges are constitutionally shadow-only.")
        payload = self.model_dump(mode="json", exclude={"challenge_id"})
        if self.challenge_id != stable_id("paradigm_challenge", payload):
            raise ValueError("Paradigm Challenge checksum mismatch.")
        return self


class ParadigmShadowTrial(FrozenRecord):
    trial_id: str
    challenge_id: str
    obligation_id: str
    seed_ref: str
    proposed_variant_ref: str
    simulation_settlement_id: str
    replayed_history_event_ids: tuple[str, ...] = Field(min_length=1)
    outcome_signature: str
    improvement_observed: bool
    evidence_preserved: bool
    orthogonal_fingerprints: tuple[OrthogonalFingerprintObservation, ...] = Field(
        min_length=1
    )

    @classmethod
    def build(cls, **values: Any) -> "ParadigmShadowTrial":
        values["replayed_history_event_ids"] = tuple(
            sorted(set(values["replayed_history_event_ids"]))
        )
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
            if key != "trial_id"
        }
        return cls(trial_id=stable_id("paradigm_shadow_trial", payload), **values)

    @model_validator(mode="after")
    def validate_trial(self) -> "ParadigmShadowTrial":
        required = (
            self.challenge_id,
            self.obligation_id,
            self.seed_ref,
            self.proposed_variant_ref,
            self.simulation_settlement_id,
            self.outcome_signature,
        )
        if not all(item.strip() for item in required):
            raise ValueError("Paradigm trial identifiers cannot be empty.")
        if tuple(sorted(set(self.replayed_history_event_ids))) != (
            self.replayed_history_event_ids
        ):
            raise ValueError("Paradigm replay history must be sorted and unique.")
        contexts = tuple(item.context_ref for item in self.orthogonal_fingerprints)
        if tuple(sorted(set(contexts))) != contexts:
            raise ValueError("Paradigm orthogonal contexts must be sorted and unique.")
        payload = self.model_dump(mode="json", exclude={"trial_id"})
        if self.trial_id != stable_id("paradigm_shadow_trial", payload):
            raise ValueError("Paradigm shadow-trial checksum mismatch.")
        return self

    @property
    def orthogonal_stable(self) -> bool:
        return all(item.stable for item in self.orthogonal_fingerprints)


class ParadigmChallengeDecision(FrozenRecord):
    decision_id: str
    source_event_key: str
    sequence: int = Field(ge=2)
    challenge_id: str
    disposition: ParadigmChallengeDisposition
    trial_ids: tuple[str, ...] = Field(min_length=1)
    blast_radius_obligation_ids: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()
    policy_version: str = PARADIGM_CHALLENGE_POLICY_VERSION
    promotion_authority_enabled: bool = False
    canonical_mutation_permitted: bool = False

    @classmethod
    def build(cls, **values: Any) -> "ParadigmChallengeDecision":
        values.setdefault("policy_version", PARADIGM_CHALLENGE_POLICY_VERSION)
        values.setdefault("promotion_authority_enabled", False)
        values.setdefault("canonical_mutation_permitted", False)
        for key in ("trial_ids", "blast_radius_obligation_ids", "rejection_codes"):
            values[key] = tuple(sorted(set(values.get(key, ()))))
        payload = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in values.items()
            if key != "decision_id"
        }
        return cls(decision_id=stable_id("paradigm_challenge_decision", payload), **values)

    @model_validator(mode="after")
    def validate_decision(self) -> "ParadigmChallengeDecision":
        if not self.source_event_key.strip() or not self.challenge_id.strip():
            raise ValueError("Paradigm decision identifiers cannot be empty.")
        for values, label in (
            (self.trial_ids, "trial IDs"),
            (self.blast_radius_obligation_ids, "blast radius"),
            (self.rejection_codes, "rejection codes"),
        ):
            if tuple(sorted(set(values))) != values:
                raise ValueError(f"Paradigm decision {label} must be sorted and unique.")
        if self.disposition == ParadigmChallengeDisposition.SHADOW_SUPPORTED:
            if self.rejection_codes:
                raise ValueError("Supported shadow challenge cannot carry rejection codes.")
        elif self.disposition == ParadigmChallengeDisposition.SHADOW_REJECTED:
            if not self.rejection_codes:
                raise ValueError("Rejected shadow challenge requires rejection codes.")
        elif self.rejection_codes:
            raise ValueError("Paradigm abstention cannot carry rejection codes.")
        if self.promotion_authority_enabled or self.canonical_mutation_permitted:
            raise ValueError("Paradigm decisions cannot promote or mutate canonical state.")
        payload = self.model_dump(mode="json", exclude={"decision_id"})
        if self.decision_id != stable_id("paradigm_challenge_decision", payload):
            raise ValueError("Paradigm decision checksum mismatch.")
        return self


class ParadigmChallengeLedgerState(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    schema_version: str = PARADIGM_CHALLENGE_LEDGER_VERSION
    challenges: tuple[ParadigmChallenge, ...] = ()
    decisions: tuple[ParadigmChallengeDecision, ...] = ()

    @model_validator(mode="after")
    def validate_ledger(self) -> "ParadigmChallengeLedgerState":
        if self.schema_version != PARADIGM_CHALLENGE_LEDGER_VERSION:
            raise ValueError("Unsupported Paradigm Challenge ledger schema.")
        challenge_ids = tuple(item.challenge_id for item in self.challenges)
        decision_ids = tuple(item.decision_id for item in self.decisions)
        if (
            len(set(challenge_ids)) != len(challenge_ids)
            or len(set(decision_ids)) != len(decision_ids)
        ):
            raise ValueError("Paradigm ledger duplicates an identity.")
        source_keys = tuple(
            item.source_event_key for item in (*self.challenges, *self.decisions)
        )
        if len(set(source_keys)) != len(source_keys):
            raise ValueError("Paradigm ledger reuses a source event key.")
        known = set(challenge_ids)
        decided: set[str] = set()
        for decision in self.decisions:
            if decision.challenge_id not in known:
                raise ValueError("Paradigm decision lost its challenge.")
            if decision.challenge_id in decided:
                raise ValueError("Paradigm Challenge was decided more than once.")
            decided.add(decision.challenge_id)
        events = sorted([*self.challenges, *self.decisions], key=lambda item: item.sequence)
        if tuple(item.sequence for item in events) != tuple(range(1, len(events) + 1)):
            raise ValueError("Paradigm ledger sequence is not contiguous.")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json_bytes(self.model_dump(mode="json"))
        ).hexdigest()


class ParadigmChallengeLane:
    def __init__(
        self,
        policy: ParadigmChallengePolicy | None = None,
        state: ParadigmChallengeLedgerState | None = None,
    ) -> None:
        self.policy = policy or ParadigmChallengePolicy()
        self.state = state or ParadigmChallengeLedgerState()

    @classmethod
    def from_snapshot(
        cls,
        payload: dict[str, Any],
        policy: ParadigmChallengePolicy | None = None,
    ) -> "ParadigmChallengeLane":
        return cls(policy=policy, state=ParadigmChallengeLedgerState.model_validate(payload))

    def snapshot(self) -> dict[str, Any]:
        return self.state.model_dump(mode="json")

    def fingerprint(self) -> str:
        return self.state.fingerprint()

    def open(
        self,
        kernel: VerdantKernel,
        *,
        signals: Sequence[ParadigmAnomalySignal],
        source_event_key: str,
    ) -> ParadigmChallenge:
        normalized = tuple(sorted(signals, key=lambda item: item.signal_id))
        if not (
            self.policy.minimum_obligation_families
            <= len(normalized)
            <= self.policy.maximum_signals
        ):
            raise ParadigmChallengeIntegrityError("Paradigm signal count is out of bounds.")
        if (
            len({item.obligation_family for item in normalized})
            < self.policy.minimum_obligation_families
        ):
            raise ParadigmChallengeIntegrityError("Paradigm Challenge lacks cross-family evidence.")
        if (
            len({item.provenance_root for item in normalized})
            < self.policy.minimum_independent_roots
        ):
            raise ParadigmChallengeIntegrityError(
                "Paradigm Challenge lacks independent provenance."
            )
        targets = {item.target_assumption_ref for item in normalized}
        if len(targets) != 1:
            raise ParadigmChallengeIntegrityError("Paradigm signals target different assumptions.")
        event_by_id = {item.event_id: item for item in kernel.state.obligation_history}
        admissible_events = {
            ObligationEventType.RETRIGGERED,
            ObligationEventType.STALLED,
            ObligationEventType.RECHECK_NO_CHANGE,
            ObligationEventType.REVALIDATION_REQUIRED,
        }
        for signal in normalized:
            obligation = kernel.state.obligation_kernels.get(signal.obligation_id)
            event = event_by_id.get(signal.history_event_id)
            if obligation is None or obligation.family != signal.obligation_family:
                raise ParadigmChallengeIntegrityError("Paradigm signal lost its obligation family.")
            if (
                event is None
                or event.obligation_id != signal.obligation_id
                or event.event_type not in admissible_events
            ):
                raise ParadigmChallengeIntegrityError(
                    "Paradigm signal is not an admissible anomaly event."
                )
            if event.policy_version != signal.target_assumption_ref:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm signal does not expose its target assumption."
                )
            if signal.provenance_root not in event.source_lineage_roots:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm signal provenance is not canonical."
                )
            if not set(signal.evidence_refs).issubset(event.triggering_refs):
                raise ParadigmChallengeIntegrityError(
                    "Paradigm signal suppressed canonical evidence."
                )
        replay = next(
            (item for item in self.state.challenges if item.source_event_key == source_event_key),
            None,
        )
        sequence = (
            replay.sequence
            if replay is not None
            else len(self.state.challenges) + len(self.state.decisions) + 1
        )
        candidate = ParadigmChallenge.build(
            source_event_key=source_event_key,
            sequence=sequence,
            target_assumption_ref=next(iter(targets)),
            signals=normalized,
            baseline_fingerprint=kernel.fingerprint(),
            policy_version=self.policy.policy_version,
        )
        if replay is not None:
            if candidate != replay:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm source key was reused with changed evidence."
                )
            return replay
        self.state = ParadigmChallengeLedgerState.model_validate(
            self.state.model_copy(
                update={"challenges": (*self.state.challenges, candidate)},
                deep=True,
            ).model_dump(mode="json")
        )
        return candidate

    def decide(
        self,
        kernel: VerdantKernel,
        *,
        challenge_id: str,
        trials: Sequence[ParadigmShadowTrial],
        simulation_ledger: SimulationLedger,
        blast_radius_obligation_ids: Sequence[str],
        source_event_key: str,
    ) -> ParadigmChallengeDecision:
        challenge = next(
            (
                item
                for item in self.state.challenges
                if item.challenge_id == challenge_id
            ),
            None,
        )
        if challenge is None:
            raise ParadigmChallengeIntegrityError("Unknown Paradigm Challenge.")
        normalized = tuple(sorted(trials, key=lambda item: item.trial_id))
        if not normalized or any(item.challenge_id != challenge_id for item in normalized):
            raise ParadigmChallengeIntegrityError("Paradigm trials crossed a challenge boundary.")
        variants = {item.proposed_variant_ref for item in normalized}
        if len(variants) != 1:
            raise ParadigmChallengeIntegrityError("Paradigm trials must test one bounded variant.")
        if kernel.fingerprint() != challenge.baseline_fingerprint:
            raise ParadigmChallengeIntegrityError(
                "Canonical state changed during Paradigm shadow replay."
            )
        known_obligations = set(kernel.state.obligation_kernels)
        blast_radius = tuple(sorted(set(blast_radius_obligation_ids)))
        if not set(blast_radius).issubset(known_obligations):
            raise ParadigmChallengeIntegrityError(
                "Paradigm blast radius cites an unknown obligation."
            )
        scoped = {item.obligation_id for item in challenge.signals}
        if {item.obligation_id for item in normalized} != scoped:
            raise ParadigmChallengeIntegrityError(
                "Paradigm trials do not cover every signaled obligation."
            )
        settlements = {item.settlement_id: item for item in simulation_ledger.state.settlements}
        reservations = {item.reservation_id: item for item in simulation_ledger.state.reservations}
        rejection_codes: set[str] = set()
        history_by_obligation = {
            obligation_id: tuple(sorted(
                item.event_id for item in kernel.state.obligation_history
                if item.obligation_id == obligation_id
            ))
            for obligation_id in scoped
        }
        grouped: dict[str, list[ParadigmShadowTrial]] = {item: [] for item in scoped}
        for trial in normalized:
            grouped[trial.obligation_id].append(trial)
            expected_history = history_by_obligation[trial.obligation_id]
            if trial.replayed_history_event_ids != expected_history:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm trial did not replay full immutable history."
                )
            settlement = settlements.get(trial.simulation_settlement_id)
            if settlement is None:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm trial lost its simulation settlement."
                )
            reservation = reservations.get(settlement.reservation_id)
            required_refs = {
                challenge.challenge_id,
                trial.proposed_variant_ref,
                trial.seed_ref,
                *trial.replayed_history_event_ids,
            }
            if (
                reservation is None
                or reservation.obligation_id != trial.obligation_id
                or reservation.canonical_fingerprint != challenge.baseline_fingerprint
                or settlement.disposition != SimulationDisposition.DISCARDED
                or not settlement.canonical_unchanged
                or settlement.canonical_before_fingerprint
                != challenge.baseline_fingerprint
                or settlement.canonical_after_fingerprint
                != challenge.baseline_fingerprint
                or not required_refs.issubset(set(settlement.result_refs))
            ):
                raise ParadigmChallengeIntegrityError("Paradigm simulation lineage is invalid.")
            if not trial.evidence_preserved:
                rejection_codes.add("evidence_not_preserved")
            if not trial.orthogonal_stable:
                rejection_codes.add("orthogonal_fingerprint_changed")
        improved_families: set[ObligationFamily] = set()
        family_by_obligation = {
            item.obligation_id: item.obligation_family for item in challenge.signals
        }
        for obligation_id, obligation_trials in grouped.items():
            if len(obligation_trials) < self.policy.minimum_replications_per_obligation:
                rejection_codes.add("replication_count_insufficient")
                continue
            if len({item.seed_ref for item in obligation_trials}) != len(obligation_trials):
                rejection_codes.add("replication_seed_reused")
            if len({item.outcome_signature for item in obligation_trials}) != 1:
                rejection_codes.add("outcome_not_replicated")
            if all(item.improvement_observed for item in obligation_trials):
                improved_families.add(family_by_obligation[obligation_id])
        if rejection_codes:
            disposition = ParadigmChallengeDisposition.SHADOW_REJECTED
        elif len(improved_families) >= self.policy.minimum_obligation_families:
            disposition = ParadigmChallengeDisposition.SHADOW_SUPPORTED
        else:
            disposition = ParadigmChallengeDisposition.ABSTAIN
        replay = next(
            (item for item in self.state.decisions if item.source_event_key == source_event_key),
            None,
        )
        sequence = (
            replay.sequence
            if replay is not None
            else len(self.state.challenges) + len(self.state.decisions) + 1
        )
        candidate = ParadigmChallengeDecision.build(
            source_event_key=source_event_key,
            sequence=sequence,
            challenge_id=challenge_id,
            disposition=disposition,
            trial_ids=tuple(item.trial_id for item in normalized),
            blast_radius_obligation_ids=blast_radius,
            rejection_codes=tuple(rejection_codes),
            policy_version=self.policy.policy_version,
        )
        if replay is not None:
            if candidate != replay:
                raise ParadigmChallengeIntegrityError(
                    "Paradigm decision key was reused with changed evidence."
                )
            return replay
        self.state = ParadigmChallengeLedgerState.model_validate(
            self.state.model_copy(
                update={"decisions": (*self.state.decisions, candidate)},
                deep=True,
            ).model_dump(mode="json")
        )
        return candidate
