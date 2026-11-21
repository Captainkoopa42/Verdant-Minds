"""Local heat: Tg for V5, starting where Verdant started (roadmap Stage C, revision first).

Claim boundary: IMPLEMENTED-EXPERIMENTAL. Nothing in ``verdant_*`` is modified. ``watch``
mode writes nothing into canonical state; ``revise`` mode is for forked organisms and acts
only through Milestone 18 (``verdant_refolding``) and the Council.

Lineage. verdant-intelligence gave every thought a temperature: the disagreement among its
neighbours (variance of their energies over their mean); hot thoughts lose stability and can
be reshaped, cool ones stay set. The July 2025 snapshot computed Tg from the system's own
state and let experience move it. V5x ported the V4 law and found its inputs were stand-ins
(it tracked wordiness). Here the inputs are the organism's own bonds, nothing else:

    temperature(S) = variance / mean of the current strengths of S's frozen internal bonds

A promoted structure whose members still belong together keeps bonds that rise and fade
together: its temperature does not change with how long it has been unseen (a uniform fade
leaves variance/mean almost unchanged). A structure whose world changed, one member gone
while the others keep meeting, has bonds that disagree: it heats. No counter, no window,
no threshold: the reading is a ratio of the organism's own quantities.

Where the heat sits. For each member m, ``drift(m) = 1 - mean strength of m's bonds / mean
strength of the bonds not touching m`` (clipped to [0, 1]). The member the rest are leaving
has the largest drift.

``revise`` mode: after each real experience that recruits a promoted structure (at least half
its members present) while one member is absent, an observation against each of the absent
member's bonds to the present members waits beside the organism, with that experience's
evidence and confidence = drift(m). A later experience that shows the member together with the
rest voids its waiting observations (it has not left). Only an unbroken run of absences strong
enough for M18 (its own policy) is recorded through ``record_structural_challenge``, one
canonical challenge per waiting observation, each with its own evidence. Milestone 18 decides when the challenges are
mature (its own policy: >= 2 observations, combined confidence >= 0.75), what the outcome is
(stable / revise / split / unresolved), and the Council commits; the parent is preserved,
never erased. Confidence is the heat itself: a member that merely went unmentioned while its
bonds are as strong as the others' has drift near 0 and its challenges never mature.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from verdant_kernel.models import stable_id


def _strength(kernel, association_id: str) -> float:
    bond = kernel.state.plasticity_associations.get(association_id)
    return float(bond.strength) if bond is not None else 0.0


def structure_bonds(kernel, structure) -> list[tuple[tuple[str, str], float]]:
    return [(tuple(e.concept_ids), _strength(kernel, e.association_id)) for e in structure.internal_edge_snapshots]


def temperature(kernel, structure) -> float | None:
    s = [v for _, v in structure_bonds(kernel, structure)]
    if len(s) < 2:
        return None
    mean = sum(s) / len(s)
    if mean <= 1e-12:
        return None                                    # every bond gone: nothing left to disagree
    return statistics.pvariance(s) / mean


def drift(kernel, structure) -> dict[str, float]:
    bonds = structure_bonds(kernel, structure); out = {}
    for m in structure.member_concept_ids:
        mine = [v for pair, v in bonds if m in pair]; rest = [v for pair, v in bonds if m not in pair]
        if not mine or not rest:
            continue
        rest_mean = sum(rest) / len(rest)
        if rest_mean <= 1e-12:
            continue
        out[m] = max(0.0, min(1.0, 1.0 - (sum(mine) / len(mine)) / rest_mean))
    return out


def _available(kernel, sid) -> bool:
    try:
        return bool(kernel.structure_is_available(sid))
    except Exception:
        return True


@dataclass
class HeatLog:
    temps: dict = field(default_factory=dict)          # structure_id -> [(experience, temperature)]
    challenges: list = field(default_factory=list)     # (experience, structure_id, departed label id, confidence)
    refolds: list = field(default_factory=list)        # (experience, structure_id, disposition, produced ids)
    refusals: list = field(default_factory=list)
    voided: int = 0                                    # waiting challenge observations voided by a fresh sighting


class HeatDevelopmentPipeline:
    """Drop-in for ``.advance``. mode='watch' reads only; mode='revise' (fork) acts through M18 + Council."""

    def __init__(self, inner, mode: str = "watch", departure_aware: bool = True):
        if mode not in ("watch", "revise"):
            raise ValueError("mode must be 'watch' or 'revise'")
        self.inner, self.mode = inner, mode
        self.heat_log = HeatLog(); self.pending: set[str] = set(); self.waiting: dict = {}
        if mode == "revise":
            if departure_aware:
                self.refolding = departure_aware_refolding()
            else:
                from verdant_refolding import VerdantRefoldingPipeline
                self.refolding = VerdantRefoldingPipeline()

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def advance(self, kernel, command):
        result = self.inner.advance(kernel, command)
        if getattr(result, "replayed", False):
            return result
        n = len(kernel.state.processed_event_keys)
        for sid, s in kernel.state.structures.items():
            if not _available(kernel, sid):
                continue
            t = temperature(kernel, s)
            if t is not None:
                self.heat_log.temps.setdefault(sid, []).append((n, round(t, 6)))
        if self.mode == "revise":
            self._revise(kernel, command, n)
        return result

    # -- fork-only authority ------------------------------------------------------------
    def _experience_concepts(self, kernel, command) -> tuple[set[str], tuple[str, ...]]:
        """Concept ids this experience proposed, and its evidence refs (one evidence event)."""
        key = command.event_key
        evidence = sorted(eid for eid, e in kernel.state.evidence.items() if e.event_key == key)
        labels = {p.label for p in command.concept_proposals}
        from verdant_kernel.models import normalize_label
        norm = {normalize_label(l) for l in labels}
        ids = {cid for cid, c in kernel.state.concepts.items() if normalize_label(c.label) in norm}
        return ids, tuple(evidence)

    def _revise(self, kernel, command, n: int) -> None:
        present, evidence = self._experience_concepts(kernel, command)
        if not present or not evidence:
            return
        touched = []; policy = kernel.state.refolding_policy
        for sid, s in sorted(kernel.state.structures.items()):
            if not _available(kernel, sid):
                continue
            members = set(s.member_concept_ids); here = members & present; absent = members - present
            if len(here) * 2 < len(members):
                continue
            # a member seen again together with the rest has not left: its waiting challenges are void
            for m in sorted(here):
                for key in [k for k in self.waiting if k[0] == sid and k[2] == m]:
                    self.heat_log.voided += len(self.waiting.pop(key))
            if not absent:
                continue
            d = drift(kernel, s)
            for m in sorted(absent):
                conf = round(d.get(m, 0.0), 6)
                if conf <= 0.0:
                    continue
                for e in s.internal_edge_snapshots:
                    pair = tuple(sorted(e.concept_ids))
                    if m not in pair or not (set(pair) - {m}) <= here:
                        continue
                    existing = kernel.state.structural_challenges.get(stable_id("structural_challenge", sid, pair))
                    if existing is not None and len(existing.observations) >= policy.minimum_challenge_events \
                            and existing.combined_confidence >= policy.minimum_combined_confidence:
                        continue                         # already mature in the kernel
                    queue = self.waiting.setdefault((sid, pair, m), [])
                    queue.append((evidence, conf))
                    remaining = 1.0
                    for _, c in queue:
                        remaining *= 1.0 - c
                    if len(queue) >= policy.minimum_challenge_events and 1.0 - remaining >= policy.minimum_combined_confidence:
                        # an unbroken run of absences, strong enough for M18: now it becomes canonical evidence
                        for ev, c in self.waiting.pop((sid, pair, m)):
                            try:
                                self.refolding.challenge(kernel, sid, pair, evidence_refs=ev, confidence=c)
                                self.heat_log.challenges.append((n, sid, m, c)); touched.append(sid)
                            except Exception as exc:
                                self.heat_log.refusals.append(f"{n} challenge: {type(exc).__name__}: {str(exc)[:80]}")
        self.pending.update(touched)
        in_mind = {item.source_ref for item in kernel.state.workspace_items.values()
                   if item.source_kind.value == "earned_structure"}
        for sid in sorted(self.pending):
            if sid in in_mind or not _available(kernel, sid):
                continue                                # never revise a fold while it is active in the workspace
            self.pending.discard(sid)
            try:
                report = self.refolding.inspect(kernel, sid)
            except Exception as exc:
                self.heat_log.refusals.append(f"{n} inspect: {type(exc).__name__}: {str(exc)[:80]}"); continue
            if report.disposition.value == "stable":
                continue
            if report.disposition.value == "revise" and len(report.proposals) == 1:
                twin = frozenset(report.proposals[0].member_concept_ids)
                live = [x for x, st in kernel.state.structures.items()
                        if x != sid and _available(kernel, x) and frozenset(st.member_concept_ids) == twin]
                if live:                                 # the revision already exists: retire the stale fold, make no twin
                    try:
                        kernel.set_structure_availability(sid, available=False, reason=(
                            "refold evidence: challenges " + ",".join(report.challenge_ids) + " ; revision already exists as " + live[0]))
                        self.heat_log.refolds.append((n, sid, "retired_to_existing", (live[0],)))
                    except Exception as exc:
                        self.heat_log.refusals.append(f"{n} retire: {type(exc).__name__}: {str(exc)[:80]}")
                    continue
            if report.disposition.value in ("revise", "split"):
                try:
                    event = self.refolding.commit(kernel, report)
                    self.heat_log.refolds.append((n, sid, report.disposition.value, tuple(event.produced_structure_ids)))
                except Exception as exc:
                    self.heat_log.refusals.append(f"{n} commit: {type(exc).__name__}: {str(exc)[:80]}")
            elif report.disposition.value == "unresolved" and not any(r[1] == sid and r[2] == "unresolved" for r in self.heat_log.refolds):
                self.heat_log.refolds.append((n, sid, "unresolved", ()))


# -- scoring against a changing-world expectations file --------------------------------
def _auc(pos: list[float], neg: list[float]) -> float | None:
    if not pos or not neg:
        return None
    wins = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg)
    return round(wins / (len(pos) * len(neg)), 3)


def score_changing_world(kernel, expectations: dict, heat_log: HeatLog | None, lesson: int) -> dict:
    from verdant_compilation import VerdantCompilationPipeline
    state = kernel.state; recall = VerdantCompilationPipeline()
    label = {cid: c.label for cid, c in state.concepts.items()}; id_of = {v: k for k, v in label.items()}
    by_members: dict = {}
    for sid, s in state.structures.items():
        by_members.setdefault(frozenset(label[m] for m in s.member_concept_ids), []).append(sid)
    rows = {}
    temps_at = {}
    if heat_log is not None:
        for sid, series in heat_log.temps.items():
            temps_at[sid] = series

    def temp_near(sid, at):
        series = temps_at.get(sid) or []
        before = [t for (n, t) in series if n < at]       # strictly before: the lesson at ``at`` is itself the change
        return before[-1] if before else None

    heat_rows = {"reversed_end": [], "reversed3_end": [], "intermittent_end": [], "stable_late_end": [],
                 "ordinary_end": [], "reversed_change": [], "control_change": []}
    for fam in expectations["families"]:
        g = fam["group"]
        if g.endswith("_after") or fam["last_lesson"] > lesson:
            continue
        sids = by_members.get(frozenset(fam["members"]), [])
        if g in ("reversed", "reversed3", "intermittent", "stable_late"):
            sid = sids[0] if sids else None
            rev = fam["revision"]
            allowed = frozenset(rev["allowed_revision"]) if rev["allowed_revision"] else None
            after = frozenset(fam["late_members"])
            revised = bool(allowed and any(_available(kernel, x) for x in by_members.get(allowed, [])))
            after_p = any(_available(kernel, x) for x in by_members.get(after, []))
            stale_recall = 0; cues = 0
            for m in fam["members"]:
                if m in rev["departed"] or m not in id_of:
                    continue
                got = {label[c] for c in recall.inspect(kernel, [id_of[m]]).reconstructed_concept_ids}
                cues += 1; stale_recall += bool(set(rev["departed"]) & got)
            row = {"promoted": sid is not None, "parent_available": bool(sid and _available(kernel, sid)),
                   "revised": revised, "after_promoted": after_p, "should_revise": rev["should_revise"],
                   "stale_recall": f"{stale_recall}/{cues}" if rev["departed"] else None,
                   "temp_at_change": temp_near(sid, fam["change_lesson"]) if sid else None,
                   "temp_at_end": temp_near(sid, fam["last_lesson"]) if sid else None}
            rows[fam["family_id"]] = {"group": g, **row}
            if sid:
                if row["temp_at_end"] is not None:
                    heat_rows[g + "_end"].append(row["temp_at_end"])
                if row["temp_at_change"] is not None:
                    heat_rows["reversed_change" if g.startswith("reversed") else "control_change"].append(row["temp_at_change"])
        elif fam["expectation"].get("exact_candidate_promotion_eligible") and sids:
            t = temp_near(sids[0], fam["last_lesson"])
            if t is not None:
                heat_rows["ordinary_end"].append(t)
    controls = heat_rows["intermittent_end"] + heat_rows["stable_late_end"] + heat_rows["ordinary_end"]
    rev_all = heat_rows["reversed_end"] + heat_rows["reversed3_end"]
    med = lambda xs: round(statistics.median(xs), 4) if xs else None
    return {"families": rows,
            "heat": {"auc_reversed_vs_controls_at_end": _auc(rev_all, controls),
                     "auc_reversed_vs_intermittent_at_end": _auc(rev_all, heat_rows["intermittent_end"]),
                     "auc_reversed_vs_controls_at_change": _auc(heat_rows["reversed_change"], heat_rows["control_change"]),
                     "median": {k: med(v) for k, v in heat_rows.items()}, "n": {k: len(v) for k, v in heat_rows.items()}},
            "revision": {"should_revise": sum(r["should_revise"] for r in rows.values()),
                         "revised_correctly": sum(r["revised"] and r["should_revise"] for r in rows.values()),
                         "revised_wrongly": sum((not r["should_revise"]) and not r["parent_available"] and r["promoted"] for r in rows.values()),
                         "challenges": len(heat_log.challenges) if heat_log else 0,
                         "refolds": [list(x[:3]) for x in heat_log.refolds] if heat_log else [],
                         "refusals": heat_log.refusals[-3:] if heat_log else []}}


# -- Milestone 18, departure-aware ---------------------------------------------------------
def departure_aware_refolding():
    """Milestone 18 with one reading added, nothing removed.

    Stock M18 removes the challenged frozen edges and looks at what is left. When every edge of
    one member was challenged, that member is left alone with no edge, and stock M18 calls the
    result an undersized split fragment: UNRESOLVED. In a changing world that is the commonest
    revision there is: a member has left. Here a fragment that is a single member with zero
    surviving edges, all of them challenged, is read as DEPARTED; if exactly one viable component
    remains (M18's own minimum members and edges), the disposition is REVISE to that component,
    built and authorised exactly as M18 builds a REVISE (Council commit, parent preserved and
    ablated, lineage kept). Everything else is stock M18.
    """
    from verdant_refolding import VerdantRefoldingPipeline
    from verdant_kernel import RefoldComponentProposal, RefoldDisposition, StructureRefoldReport
    from verdant_kernel.models import stable_id

    class DepartureAwareRefolding(VerdantRefoldingPipeline):
        def inspect(self, kernel, structure_id):
            report = super().inspect(kernel, structure_id)
            if report.disposition != RefoldDisposition.UNRESOLVED:
                return report
            parent = kernel.state.structures[structure_id]; policy = kernel.state.refolding_policy
            removed = set(report.removed_association_ids)
            surviving = tuple(e for e in parent.internal_edge_snapshots if e.association_id not in removed)
            components = self._components(parent.member_concept_ids, surviving)
            departed, viable, other = [], [], []
            for members in components:
                edges = self._component_edges(members, surviving)
                if len(members) == 1 and not edges:
                    departed.append(members[0])
                elif len(members) >= policy.minimum_component_members and len(edges) >= policy.minimum_component_edges:
                    viable.append((members, edges))
                else:
                    other.append(members)
            if not departed or other or len(viable) != 1:
                return report
            members, edges = viable[0]
            mature = self._mature_challenges(kernel, structure_id)
            challenge_ids = report.challenge_ids
            quality = self._quality(parent, members, edges, parent.internal_edge_snapshots, contradiction_resolved=True)
            dim, real, imag, digest = self._field_prototype(kernel, members)
            proposed_id = stable_id("refolded_structure", parent.structure_id, members,
                                    tuple(item.model_dump(mode="json") for item in edges), challenge_ids)
            proposal = RefoldComponentProposal(
                proposed_structure_id=proposed_id, proposed_opaque_name=f"P_{proposed_id.rsplit('_', 1)[-1][:12]}",
                parent_structure_id=parent.structure_id,
                lineage_root_structure_id=parent.lineage_root_structure_id or parent.structure_id,
                revision_index=parent.revision_index + 1, member_concept_ids=members,
                internal_association_ids=tuple(item.association_id for item in edges), internal_edge_snapshots=edges,
                evidence_refs=tuple(sorted(set(parent.evidence_refs) | set(report.evidence_refs))), quality=quality,
                field_state_dim=dim, field_prototype_real=real, field_prototype_imag=imag, field_prototype_sha256=digest,
                refold_basis_challenge_ids=challenge_ids)
            rejection_codes = ()
            report_id = stable_id("structure_refold_report", kernel.state.identity.kernel_id, kernel.state.cycle,
                                  report.structural_fingerprint, structure_id, RefoldDisposition.REVISE.value, challenge_ids,
                                  report.removed_association_ids, (proposal.model_dump(mode="json"),), report.evidence_refs,
                                  rejection_codes, "refold_structure", policy.revision)   # the kernel's own identity formula
            revised = StructureRefoldReport(
                report_id=report_id, kernel_id=report.kernel_id, cycle=report.cycle,
                structural_fingerprint=report.structural_fingerprint, parent_structure_id=structure_id,
                disposition=RefoldDisposition.REVISE, challenge_ids=challenge_ids,
                removed_association_ids=report.removed_association_ids, proposals=(proposal,),
                evidence_refs=report.evidence_refs, rejection_codes=rejection_codes, operation="refold_structure",
                policy_revision=policy.revision)
            kernel.validate_structure_refold_report(revised)
            return revised

    return DepartureAwareRefolding()
