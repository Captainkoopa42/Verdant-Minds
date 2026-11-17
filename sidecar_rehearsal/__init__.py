"""Opt-in rehearsal ("sleep") sidecar for the V5 developmental heartbeat.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. Nothing in ``verdant_*`` is modified and
nothing here runs unless a caller constructs these classes.

Lineage: V0-V4 had ``VerdantSystem.dream_cycle`` (random concepts re-entered as
ordinary text after idle cycles). This port keeps the behaviour and drops the two
properties V5 cannot accept: it is deterministic (selection is a pure function of
canonical state) and a rehearsal is never an experience.

What a rehearsal beat is
    staged copy -> workspace cycle whose only new inputs are RECALLED_EVIDENCE
    items re-presenting remembered experiences whose bonds are fading -> plasticity cycle -> commit.
    ``apply_experience``, resonance commit and structure observation are NOT run.

What that means
    * no evidence, concept, relation or claim is created;
    * no structure candidate is created or changed, so occurrence counts,
      observed cycles, contexts and quality still come from real experience only;
    * no plastic association is created: the rehearsal item's score is held below
      the plasticity creation threshold, and the staged beat is discarded if any
      association appears anyway;
    * the only intended effect is reinforcement of bonds that real experience
      already created. Bonds are chosen by how often real experience reinforced
      them (OBSERVATION evidence only), never by how often they were rehearsed.

Known side effects, reported not hidden: every plasticity cycle applies local decay
to all bonds, so a rehearsal beat costs every non-rehearsed bond one decay step; and
workspace items still persisting from the last real experience take part in the
beat as they would in any workspace cycle.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from verdant_kernel import VerdantKernel
from verdant_kernel.models import (EvidenceKind, WorkspaceCandidateInput,
                                   WorkspaceSignals, WorkspaceSourceKind)
from verdant_development import VerdantDevelopmentPipeline
from verdant_plasticity import VerdantPlasticityPipeline
from verdant_workspace import VerdantWorkspacePipeline

__all__ = ["RehearsalConfig", "RehearsalReport", "VerdantRehearsalPipeline", "RehearsingDevelopmentPipeline"]


@dataclass(frozen=True)
class RehearsalConfig:
    every_experiences: int = 8          # sleep after every Nth committed experience
    max_items: int = 5                  # remembered experiences re-presented per beat
    min_real_exposures: int = 2         # real exposures a bond needs before it may be rehearsed
    refresh_below: float = 0.26         # only bonds weaker than this are refreshed
    horizon_cycles: int = 400           # stop rehearsing what has not really recurred for this long
    resource_request: float = 0.15
    evidence_grounding: float = 1.0
    relevance: float = 0.90

    def __post_init__(self) -> None:
        if self.every_experiences < 1 or self.max_items < 1 or self.min_real_exposures < 1:
            raise ValueError("Rehearsal needs every_experiences>=1, max_items>=1 and min_real_exposures>=1.")


@dataclass(frozen=True)
class RehearsalReport:
    cycle: int
    input_fingerprint: str
    selected_evidence_ids: tuple[str, ...]
    committed: bool
    refusal: str | None = None
    reinforced_association_ids: tuple[str, ...] = ()
    reinforced_outside_selection: tuple[str, ...] = ()
    mean_strength_before: float = 0.0
    mean_strength_after: float = 0.0
    output_fingerprint: str | None = None
    report_id: str = field(default="")

    def with_id(self) -> "RehearsalReport":
        body = {k: v for k, v in self.__dict__.items() if k != "report_id"}
        digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=list).encode()).hexdigest()[:24]
        return RehearsalReport(**{**body, "report_id": "rehearsal_report_" + digest})


def _semantic_counts(kernel: VerdantKernel) -> tuple[int, ...]:
    s = kernel.state
    return (len(s.evidence), len(s.concepts), len(s.relations), len(s.claims), len(s.structures),
            len(s.structure_candidates), len(s.processed_event_keys))


class VerdantRehearsalPipeline:
    def __init__(self, config: RehearsalConfig | None = None) -> None:
        self.config = config or RehearsalConfig()
        self.workspace = VerdantWorkspacePipeline(); self.plasticity = VerdantPlasticityPipeline()

    # ---- selection: a pure function of canonical state ---------------------
    @staticmethod
    def _real_exposures(kernel: VerdantKernel, bond) -> tuple[int, int, str | None]:
        """(count, latest cycle, latest id) of OBSERVATION evidence behind a bond: real experience only."""
        obs = [kernel.state.evidence[r] for r in bond.evidence_refs
               if r in kernel.state.evidence and kernel.state.evidence[r].kind == EvidenceKind.OBSERVATION]
        if not obs:
            return 0, 0, None
        latest = max(obs, key=lambda e: (e.cycle, e.evidence_id))
        return len(obs), latest.cycle, latest.evidence_id

    def select(self, kernel: VerdantKernel) -> tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...]:
        """Recalled experiences to rehearse: (evidence id, concept ids, bond ids), best first.

        A bond qualifies when real experience reinforced it at least ``min_real_exposures``
        times, the last real exposure is inside the horizon, and it is alive but weaker than
        ``refresh_below``. Bonds are grouped by the latest real experience they share, so
        one item re-presents one remembered experience.
        """
        s = kernel.state; cfg = self.config; groups: dict[str, list] = {}
        for bond in s.plasticity_associations.values():
            if bond.strength >= cfg.refresh_below:
                continue
            count, cycle, latest = self._real_exposures(kernel, bond)
            if latest is None or count < cfg.min_real_exposures or s.cycle - cycle > cfg.horizon_cycles:
                continue
            groups.setdefault(latest, []).append((count, cycle, bond))
        rows = []
        for evidence_id, items in groups.items():
            rows.append((-max(i[0] for i in items), -max(i[1] for i in items), evidence_id, items))
        rows.sort(key=lambda r: r[:3])
        out = []
        for _, _, evidence_id, items in rows[:cfg.max_items]:
            concepts = tuple(sorted({c for _, _, b in items for c in b.concept_ids}))
            out.append((evidence_id, concepts, tuple(sorted(b.association_id for _, _, b in items))))
        return tuple(out)

    def _inputs(self, kernel: VerdantKernel, selected) -> tuple[WorkspaceCandidateInput, ...]:
        cfg = self.config; out = []
        for evidence_id, concepts, bonds in selected:
            out.append(WorkspaceCandidateInput(
                source_kind=WorkspaceSourceKind.RECALLED_EVIDENCE, source_ref=evidence_id,
                label=f"rehearsal of remembered experience {evidence_id[-8:]}", evidence_refs=(evidence_id,),
                resource_request=cfg.resource_request, persistence_cycles=1,
                signals=WorkspaceSignals(evidence_grounding=cfg.evidence_grounding, relevance=cfg.relevance),
                binding_refs=concepts,
                metadata={"developmental_stage": "sidecar_rehearsal", "bond_count": len(bonds),
                          "claim_boundary": "IMPLEMENTED-EXPERIMENTAL", "is_experience": False}))
        return tuple(out)

    # ---- one staged, all-or-nothing beat ----------------------------------
    def run(self, kernel: VerdantKernel) -> RehearsalReport:
        selected = self.select(kernel); fp = kernel.fingerprint()
        if not selected:
            return RehearsalReport(kernel.state.cycle, fp, (), False, "nothing_to_rehearse").with_id()
        ids = tuple(e for e, _, _ in selected)
        staged = VerdantKernel.from_state(kernel.snapshot())
        before_counts = _semantic_counts(staged)
        before_cands = {k: v for k, v in staged.state.structure_candidates.items()}
        before_bonds = {k: v.strength for k, v in staged.state.plasticity_associations.items()}
        ws = self.workspace.run_cycle(staged, self._inputs(staged, selected))
        self.plasticity.run_cycle(staged, ws.event)
        after_bonds = {k: v.strength for k, v in staged.state.plasticity_associations.items()}
        refusal = None
        if _semantic_counts(staged) != before_counts:
            refusal = "semantic_state_changed"
        elif any(staged.state.structure_candidates.get(k) != v for k, v in before_cands.items()):
            refusal = "structure_candidate_changed"
        elif set(after_bonds) - set(before_bonds):
            refusal = "association_created"
        if refusal:
            return RehearsalReport(kernel.state.cycle, fp, ids, False, refusal).with_id()
        wanted = {a for _, _, bonds in selected for a in bonds}
        up = tuple(sorted(k for k, v in after_bonds.items() if v > before_bonds[k] + 1e-12))
        mean = lambda d: sum(d.get(a, 0.0) for a in wanted) / max(1, len(wanted))
        kernel.state = staged.snapshot()
        return RehearsalReport(kernel.state.cycle, fp, ids, True, None, tuple(a for a in up if a in wanted),
                               tuple(a for a in up if a not in wanted), round(mean(before_bonds), 6),
                               round(mean(after_bonds), 6), kernel.fingerprint()).with_id()


class RehearsingDevelopmentPipeline:
    """Drop-in for ``VerdantDevelopmentPipeline.advance`` with a rehearsal beat every Nth experience.

    The trigger is derived from canonical state (number of processed experiences), so two
    runs of the same lessons sleep at the same points and end on the same fingerprint.
    """

    def __init__(self, inner: VerdantDevelopmentPipeline | None = None, config: RehearsalConfig | None = None) -> None:
        self.inner = inner or VerdantDevelopmentPipeline()
        self.rehearsal = VerdantRehearsalPipeline(config); self.reports: list[RehearsalReport] = []

    def advance(self, kernel: VerdantKernel, command):
        result = self.inner.advance(kernel, command)
        if not result.replayed and len(kernel.state.processed_event_keys) % self.rehearsal.config.every_experiences == 0:
            self.reports.append(self.rehearsal.run(kernel))
        return result
