"""Opt-in recall that chooses how to remember: pull, relive, search wider, or imagine.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. Read-only: nothing here writes to the organism. Every
call checks that the organism's fingerprint is unchanged afterwards. Imagining happens on numbers
derived from the record, never on the record itself, so the original memory stays exactly as it was.

Every answer says how it was reached, and every element carries where it came from:
    EARNED      inside an earned structure (a promoted P) with the cue
    REMEMBERED  met with the cue in at least 3 real experiences, and still bonded
    WEAK        met with the cue in fewer than 3 real experiences (met, not earned)
    FADED       met with the cue, but the bond has faded below recall
    RELIVED     recovered from the field's own record of a past experience
    SEARCHED    resembles the cue, and the record shows it was never met with it
    CONTEXT     on the mind at the moment being relived or imagined, not part of it
    ECHO        called up by the memory itself (the unchanged replay calls it up too)
    IMAGINED    introduced by imagination, or called up only by the new combination;
                never presented as remembered
Meetings are counted from the record (real experiences holding both), never from how many
internal cycles reinforced a bond.

Recall chooses its mode from what it finds:
    pull     earned or remembered partners answer directly (cheap)
    relive   weak partners are checked by going back to the experiences behind the bond: how many
             meetings, in how many settings, and whether those experiences resemble each other
    search   nothing met with the cue: look wider for concepts whose profiles resemble the cue's
    unknown  the cue itself was never met

Reliving reads the field history: every experience left a frame holding the field right after it,
and the frame before it holds the mind just before. With retention r, after = (r*before + e)/n for a
unit-length experience effect e, so e is recovered exactly: n solves |n*after - r*before| = 1.

Imagining replays a relived experience with one concept swapped for another (its field address and
resonance profile take the old one's place) and plays it against a chosen context: the mind as it was
then, or as it is now. The imagined moment is read with the organism's own readouts (live-field and
profile alignment) on numbers only; nothing is committed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from verdant_compilation import VerdantCompilationPipeline
from verdant_kernel.models import EvidenceKind

__all__ = ["recall", "relive", "imagine", "Recollection", "RelivedExperience", "Imagined"]

STRONG_EXPOSURES = 3


@dataclass(frozen=True)
class RelivedExperience:
    event_key: str
    cycle: int
    context_id: str | None
    concept_ids: tuple[str, ...]
    effect: np.ndarray = field(repr=False)
    mind_before: np.ndarray = field(repr=False)
    recovery_error: float


@dataclass(frozen=True)
class Recollection:
    cue: str
    mode: str
    partners: tuple[tuple[str, str], ...]          # (label, provenance)
    note: str


@dataclass(frozen=True)
class Imagined:
    base_event_key: str
    swapped_out: str
    swapped_in: str
    context: str
    held_in_mind: tuple[tuple[str, str], ...]      # (label, provenance) strongest first
    original_intact: bool


def _vec(record) -> np.ndarray:
    return np.asarray(record.real, dtype=np.float64) + 1j * np.asarray(record.imag, dtype=np.float64)


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n else v


def _frames_by_event(kernel) -> dict[str, int]:
    evidence = kernel.state.evidence; out = {}
    for i, frame in enumerate(kernel.state.field.history):
        for ref in frame.caused_by_refs:
            if ref in evidence:
                out.setdefault(evidence[ref].event_key, i)
    return out


def relive(kernel, event_key: str) -> RelivedExperience:
    """Recover a past experience exactly as the field recorded it."""
    history = kernel.state.field.history; i = _frames_by_event(kernel)[event_key]; frame = history[i]
    after = _vec(frame); before = _vec(history[i - 1]) if i > 0 else np.zeros_like(after)
    r = kernel.state.ecwf_policy.retention
    if not np.linalg.norm(before):
        effect, error = after, 0.0
    else:
        c = float(np.vdot(after, before).real) * r
        n = c + math.sqrt(max(0.0, c * c - (r * r) * float(np.vdot(before, before).real) + 1.0))
        effect = n * after - r * before
        error = abs(float(np.linalg.norm(effect)) - 1.0)
    context = next((kernel.state.evidence[ref].details.get("context_id") for ref in frame.caused_by_refs
                    if ref in kernel.state.evidence and kernel.state.evidence[ref].kind == EvidenceKind.OBSERVATION), None)
    return RelivedExperience(event_key, frame.cycle, context, tuple(frame.bound_concept_ids), effect, before, error)


def _bond(kernel, a: str, b: str):
    pair = tuple(sorted((a, b)))
    return next((x for x in kernel.state.plasticity_associations.values() if x.concept_ids == pair), None)


def _real_meetings(kernel, bond) -> list[str]:
    ev = kernel.state.evidence
    return sorted({ev[r].event_key for r in bond.evidence_refs if r in ev and ev[r].kind == EvidenceKind.OBSERVATION})


def _meetings_with(kernel, a: str, b: str) -> list[str]:
    """Real experiences (observation evidence) in which both concepts were present."""
    ev = kernel.state.evidence; c = kernel.state.concepts
    def events(cid):
        return {ev[r].event_key for r in c[cid].evidence_refs if r in ev and ev[r].kind == EvidenceKind.OBSERVATION}
    return sorted(events(a) & events(b))


def _relive_note(kernel, meetings: list[str]) -> str:
    frames = _frames_by_event(kernel)
    relived = [relive(kernel, m) for m in meetings if m in frames]
    contexts = {x.context_id for x in relived}
    likeness = (float(np.mean([abs(np.vdot(a.effect, b.effect)) for i, a in enumerate(relived) for b in relived[i + 1:]]))
                if len(relived) > 1 else None)
    return (f"RELIVED {len(relived)} meeting(s) in {len(contexts)} setting(s)"
            + (f", likeness {likeness:.2f}" if likeness is not None else ", only once"))


def recall(kernel, cue_label: str) -> Recollection:
    """Recall what goes with a cue, choosing how hard to look and saying how it got the answer."""
    fingerprint = kernel.fingerprint(); state = kernel.state
    label = {cid: c.label for cid, c in state.concepts.items()}; ids = {v: k for k, v in label.items()}
    if cue_label not in ids:
        return Recollection(cue_label, "unknown", (), "never met")
    cue = ids[cue_label]
    earned = {m for s in state.structures.values() if cue in s.member_concept_ids and kernel.structure_is_available(s.structure_id)
              for m in s.member_concept_ids} - {cue}
    pulled = set(VerdantCompilationPipeline().inspect(kernel, [cue]).reconstructed_concept_ids) - {cue}
    partners: list[tuple[str, str]] = []; weak = 0; notes = []
    for p in sorted(pulled):
        met = _meetings_with(kernel, cue, p)
        if p in earned:
            partners.append((label[p], "EARNED"))
        elif len(met) >= STRONG_EXPOSURES:
            partners.append((label[p], f"REMEMBERED ({len(met)} meetings)"))
        else:                                                # relive the meetings behind a weak bond
            weak += 1; partners.append((label[p], f"WEAK, {_relive_note(kernel, met)}"))
    if partners:
        mode = "relive" if weak else "pull"
        notes.append(f"{len(partners) - weak} from what it knows, {weak} checked by reliving")
    else:                                                     # search wider, checking the record before claiming "never met"
        profile = state.resonance_profiles.get(cue)
        if profile is None:
            return Recollection(cue_label, "unknown", (), "met, but never experienced as features")
        q = _vec(profile)
        scores = sorted(((abs(np.vdot(_vec(pr), q)), cid) for cid, pr in state.resonance_profiles.items() if cid != cue), reverse=True)
        for s_, c in scores[:3]:
            met = _meetings_with(kernel, cue, c)
            partners.append((label[c], f"FADED, met {len(met)} time(s), {_relive_note(kernel, met)}" if met
                             else f"SEARCHED (resemblance {s_:.2f}, never met with the cue)"))
        mode = "search"; notes.append("nothing held strongly enough to pull; looked wider and checked the record")
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Recall changed the organism.")
    return Recollection(cue_label, mode, tuple(partners), "; ".join(notes))


def imagine(kernel, event_key: str, swap_out: str, swap_in: str, *, context: str = "then", top: int = 6) -> Imagined:
    """Relive an experience with one concept swapped for another, against the mind then or now."""
    fingerprint = kernel.fingerprint(); state = kernel.state
    label = {cid: c.label for cid, c in state.concepts.items()}; ids = {v: k for k, v in label.items()}
    base = relive(kernel, event_key); out_id, in_id = ids[swap_out], ids[swap_in]
    if out_id not in base.concept_ids:
        raise ValueError(f"{swap_out!r} was not part of that experience.")
    policy = state.ecwf_policy; k = max(1, len(base.concept_ids))
    a_out, a_in = _vec(state.field_addresses[out_id]), _vec(state.field_addresses[in_id])
    p_out, p_in = _vec(state.resonance_profiles[out_id]), _vec(state.resonance_profiles[in_id])
    imagined = _unit(base.effect
                     + (policy.concept_coupling / math.sqrt(k)) * (a_in - a_out)
                     + (policy.feature_coupling / k) * (p_in - p_out))
    mind = base.mind_before if context == "then" else _vec(state.field)

    def held_by(effect):
        moment = _unit(policy.retention * mind + effect) if np.linalg.norm(mind) else effect
        out = []
        for cid, address in state.field_addresses.items():
            if cid in state.resonance_profiles:
                out.append((0.5 * abs(np.vdot(_vec(address), moment)) + 0.5 * abs(np.vdot(_vec(state.resonance_profiles[cid]), effect)), cid))
        return sorted(out, reverse=True)
    scores = held_by(imagined)
    echoes = {cid for _s, cid in held_by(base.effect)[:top]}          # what the unchanged replay calls up
    from_mind = {cid: abs(np.vdot(_vec(state.field_addresses[cid]), policy.retention * mind)) > abs(np.vdot(_vec(state.field_addresses[cid]), imagined))
                 for _s, cid in scores[:top]}

    def where(cid):
        if cid == in_id:
            return "IMAGINED (swapped in)"
        if cid in base.concept_ids:
            return "RELIVED (from the original experience)"
        if from_mind[cid]:
            return f"CONTEXT (on the mind {'then' if context == 'then' else 'now'})"
        if cid in echoes:
            return "ECHO (the unchanged memory calls it up too)"
        return "IMAGINED (called up only by the new combination)"
    held = tuple((label[c], where(c)) for _s, c in scores[:top])
    again = relive(kernel, event_key)
    intact = bool(np.allclose(again.effect, base.effect) and again.concept_ids == base.concept_ids)
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Imagining changed the organism.")
    return Imagined(event_key, swap_out, swap_in, context, held, intact)
