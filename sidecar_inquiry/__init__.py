"""Open questions in shadow (wiring plan step 6, read-only).

Claim boundary: IMPLEMENTED-EXPERIMENTAL, READ-ONLY. Nothing in ``verdant_*`` is modified,
nothing is written into canonical state, and nothing here can change what the organism does.
The record lives beside the organism, never inside it.

Two watchers run after every real experience:

1. The obligation substrate's own five detectors (`verdant_obligations`: dependency gap,
   contradiction, prediction failure, identity ambiguity, failed policy), through their
   ``inspect`` methods only, which promise "findings without changing cycle, history, or
   fingerprints". Their findings are counted, never recorded into the organism.

2. A developmental bridge. The substrate reads claims, `requires` relations and
   action/outcome evidence; a developmental life mostly makes none of those. Its open
   questions are its structure candidates that recur but are not yet eligible. For each one,
   the bridge names which of the structure stage's own gates still fail, and gives that
   question the substrate's lifecycle in miniature:

       OPEN      a tracking candidate fails one or more named gates
       STALLED   nothing has touched it for ``stall_after`` experiences: it goes to cold storage
                 with a certificate (sha256 of the candidate's snapshot, the failing gates and
                 the reopen condition)
       WOKE      its reopen condition fired: the candidate was observed again
       RESOLVED  on recheck every gate passes (the structure stage marked it eligible)
       back to STALLED with a new certificate if the recheck still fails

   Scored afterwards: did the question name the gate that was actually the last to pass,
   and do the questions that resolve belong to the families expected to pass?
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

GATES = ("recurrence", "reconstructability", "boundary_selectivity", "internal_cohesion",
         "evidence_diversity", "cross_context_stability")


def failing_gates(kernel, candidate) -> tuple[str, ...]:
    policy, q = kernel.state.structure_policy, candidate.quality
    out = []
    if candidate.occurrence_count < policy.minimum_recurrence_events:
        out.append("recurrence")
    if q.reconstructability < policy.minimum_reconstructability:
        out.append("reconstructability")
    if q.boundary_selectivity < policy.minimum_boundary_selectivity:
        out.append("boundary_selectivity")
    if q.internal_cohesion < policy.minimum_internal_cohesion:
        out.append("internal_cohesion")
    if q.evidence_diversity < 1.0:
        out.append("evidence_diversity")
    if q.cross_context_stability < 1.0:
        out.append("cross_context_stability")
    return tuple(out)


def _certificate(candidate, gates, reopen) -> str:
    payload = {"candidate": candidate.candidate_id, "members": list(candidate.member_concept_ids),
               "occurrence_count": candidate.occurrence_count, "quality": candidate.quality.model_dump(mode="json"),
               "failing_gates": list(gates), "reopen_condition": reopen}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


@dataclass
class Question:
    candidate_id: str
    opened_at: int
    gates_at_open: tuple
    state: str = "open"
    last_touch: int = 0
    last_occurrence: int = 0
    gates_now: tuple = ()
    gates_at_stall: tuple = ()
    history: list = field(default_factory=list)      # (experience, event, gates)
    certificates: list = field(default_factory=list)
    resolved_at: int | None = None
    last_gate: str | None = None                     # the gate that failed at the final recheck before resolving


class InquiryShadow:
    def __init__(self, *, stall_after: int = 20, substrate_every: int = 10):
        self.stall_after, self.substrate_every = stall_after, substrate_every
        self.questions: dict[str, Question] = {}
        self.substrate_counts: dict[str, int] = {}
        self.substrate_findings: dict[str, set] = {}
        self.fingerprint_breaks = 0
        self.sleep_requests = 0
        from verdant_obligations import (ContradictionObligationDetector, DependencyGapDetector,
                                         FailedPolicyDetector, IdentityAmbiguityDetector, PredictionFailureDetector)
        self.detectors = {"dependency_gap": DependencyGapDetector(), "contradiction": ContradictionObligationDetector(),
                          "prediction_failure": PredictionFailureDetector(), "identity_ambiguity": IdentityAmbiguityDetector(),
                          "failed_policy": FailedPolicyDetector()}

    # -- watcher 1: the substrate's own detectors, inspect only --------------------------------
    def _substrate(self, kernel, n: int) -> None:
        before = kernel.fingerprint()
        for name, det in self.detectors.items():
            try:
                found = det.inspect(kernel)
            except Exception as exc:                  # reported, never hidden
                self.substrate_findings.setdefault(name + ":error", set()).add(f"{type(exc).__name__}: {str(exc)[:80]}")
                continue
            cands = found[1] if isinstance(found, tuple) and len(found) == 2 else found
            ids = {getattr(c, "candidate_id", repr(c)) for c in (cands or ())}
            self.substrate_findings.setdefault(name, set()).update(ids)
        if kernel.fingerprint() != before:
            self.fingerprint_breaks += 1

    # -- watcher 2: the developmental bridge ---------------------------------------------------
    def _bridge(self, kernel, n: int) -> None:
        for cid, cand in sorted(kernel.state.structure_candidates.items()):
            status = cand.status.value
            q = self.questions.get(cid)
            if status == "tracking":
                gates = failing_gates(kernel, cand)
                if not gates:
                    continue
                if q is None:
                    q = self.questions[cid] = Question(cid, n, gates, last_touch=n, last_occurrence=cand.occurrence_count, gates_now=gates)
                    q.history.append((n, "open", gates)); continue
                if q.state == "resolved":
                    q.history.append((n, "fell_back", gates)); q.state = "open"; q.resolved_at = None
                touched = cand.occurrence_count != q.last_occurrence
                if q.state == "stalled" and touched:            # reopen condition: observed again
                    q.history.append((n, "woke", q.gates_at_stall))
                    q.history.append((n, "recheck_still_failing", gates))
                    q.state = "stalled"; q.gates_at_stall = gates
                    q.certificates.append(_certificate(cand, gates, "candidate observed again"))
                    q.last_touch = n
                elif touched:
                    q.last_touch = n
                    if gates != q.gates_now:
                        q.history.append((n, "gates_changed", gates))
                elif q.state == "open" and n - q.last_touch >= self.stall_after:
                    q.state = "stalled"; q.gates_at_stall = gates
                    q.certificates.append(_certificate(cand, gates, "candidate observed again"))
                    q.history.append((n, "stalled", gates))
                q.gates_now = gates; q.last_occurrence = cand.occurrence_count
            elif status in ("eligible", "promoted") and q is not None and q.state != "resolved":
                woke = q.state == "stalled"
                if woke:
                    q.history.append((n, "woke", q.gates_at_stall))
                q.history.append((n, "resolved", ()))
                q.last_gate = q.gates_now[-1] if len(q.gates_now) == 1 else ("+".join(q.gates_now) or None)
                q.state = "resolved"; q.resolved_at = n

    def watch(self, kernel) -> None:
        n = len(kernel.state.processed_event_keys)
        if n % self.substrate_every == 0:              # fingerprint checked around the substrate call;
            self._substrate(kernel, n)                 # the bridge only reads attributes. The real proof is
        self._bridge(kernel, n)                        # the whole life ending on the plain run's fingerprint.

    # -- the scorecard ----------------------------------------------------------------------
    def summary(self, kernel=None, expectations: dict | None = None) -> dict:
        qs = list(self.questions.values())
        ever_stalled = [q for q in qs if any(e[1] == "stalled" for e in q.history)]
        out = {"questions": len(qs), "open": sum(q.state == "open" for q in qs), "stalled_now": sum(q.state == "stalled" for q in qs),
               "resolved": sum(q.state == "resolved" for q in qs), "ever_stalled": len(ever_stalled),
               "stalled_then_resolved": sum(q.state == "resolved" for q in ever_stalled),
               "wakes": sum(e[1] == "woke" for q in qs for e in q.history),
               "named_last_gate_at_stall": sum(1 for q in ever_stalled if q.state == "resolved" and q.last_gate and q.last_gate in q.gates_at_stall),
               "gates_at_open": _count(g for q in qs for g in q.gates_at_open),
               "gates_still_failing": _count(g for q in qs if q.state != "resolved" for g in q.gates_now),
               "substrate_findings": {k: len(v) for k, v in self.substrate_findings.items()},
               "substrate_errors": {k: sorted(v)[:2] for k, v in self.substrate_findings.items() if k.endswith(":error")},
               "fingerprint_breaks": self.fingerprint_breaks, "sleep_requests": self.sleep_requests}
        if kernel is not None and expectations is not None:
            label = {cid: c.label for cid, c in kernel.state.concepts.items()}
            by_members = {frozenset(label[m] for m in c.member_concept_ids): cid for cid, c in kernel.state.structure_candidates.items()}
            groups: dict = {}
            for fam in expectations["families"]:
                cid = by_members.get(frozenset(fam["members"]))
                row = groups.setdefault(fam["group"], {"families": 0, "asked": 0, "resolved": 0, "stalled_unresolved": 0, "open_unresolved": 0})
                row["families"] += 1
                q = self.questions.get(cid) if cid else None
                if q is None:
                    continue
                row["asked"] += 1
                row["resolved"] += q.state == "resolved"
                row["stalled_unresolved"] += q.state == "stalled"
                row["open_unresolved"] += q.state == "open"
            out["by_group"] = groups
        return out


def _count(items) -> dict:
    out: dict = {}
    for i in items:
        out[i] = out.get(i, 0) + 1
    return dict(sorted(out.items()))


def questions_sleep_can_answer(shadow: "InquiryShadow", kernel) -> list[str]:
    """Stalled questions whose only failing gate is internal cohesion: the bonds are there but
    weak. That is the one gate the organism can work on alone (sleep strengthens existing bonds);
    recurrence, contexts and diversity need the world."""
    out = []
    for cid, q in sorted(shadow.questions.items()):
        cand = kernel.state.structure_candidates.get(cid)
        if q.state == "stalled" and cand is not None and cand.status.value == "tracking" \
                and failing_gates(kernel, cand) == ("internal_cohesion",):
            out.append(cid)
    return out


def direct_sleep(rehearsal, shadow: "InquiryShadow") -> None:
    """FORK-ONLY authority: let stalled cohesion questions choose what sleep rehearses first.

    Everything else about a rehearsal beat is unchanged: staged and all-or-nothing, no evidence,
    concept, candidate or bond may be created or changed except existing bonds' strength, and a
    bond still needs ``min_real_exposures`` real exposures. What the question lifts is the
    generic "fading below refresh_below, seen within the horizon" filter, for the questioned
    candidate's own internal bonds only: the stored question is the reason to keep them.
    """
    plain = rehearsal.select
    cfg = rehearsal.config

    def select(kernel):
        asked = []
        for cid in questions_sleep_can_answer(shadow, kernel):
            cand = kernel.state.structure_candidates[cid]
            bonds = []; latest = None
            for aid in cand.internal_association_ids:
                bond = kernel.state.plasticity_associations.get(aid)
                if bond is None:
                    continue
                count, cycle, ev = rehearsal._real_exposures(kernel, bond)
                if ev is None or count < cfg.min_real_exposures:
                    continue
                bonds.append(aid); latest = max(latest or (0, ""), (cycle, ev))
            if bonds:
                asked.append((latest[1], tuple(sorted(cand.member_concept_ids)), tuple(sorted(bonds))))
            if len(asked) >= cfg.max_items:
                break
        shadow.sleep_requests += len(asked)
        taken = {e for e, _, _ in asked}
        rest = [row for row in plain(kernel) if row[0] not in taken]
        return tuple(asked + rest)[:cfg.max_items]

    rehearsal.select = select


class InquiringDevelopmentPipeline:
    """Drop-in for ``.advance``: the inner pipeline beats, then the shadow watches.

    ``authority=None`` (default): it cannot act. ``authority="sleep"`` is for a FORKED organism
    only: stalled cohesion questions direct what sleep rehearses (``direct_sleep``)."""

    def __init__(self, inner, shadow: InquiryShadow | None = None, authority: str | None = None):
        self.inner = inner; self.shadow = shadow or InquiryShadow(); self.authority = authority
        if authority not in (None, "sleep"):
            raise ValueError("authority must be None or 'sleep'")
        if authority == "sleep":
            node = inner
            while node is not None and not hasattr(node, "rehearsal"):
                node = node.__dict__.get("inner")
            if node is None:
                raise ValueError("authority='sleep' needs a rehearsing pipeline inside")
            direct_sleep(node.rehearsal, self.shadow)

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def advance(self, kernel, command):
        result = self.inner.advance(kernel, command)
        if not getattr(result, "replayed", False):
            self.shadow.watch(kernel)
        return result
