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
Each fine label belongs to one of the five provenance kinds from the Mindspace design (kind_of):
    OBSERVED          the experience happening now (only a real beat or a simulation has one)
    REMEMBERED        EARNED, REMEMBERED, WEAK, FADED, RELIVED, ECHO, CONTEXT: all read from the record
    INFERRED          SEARCHED: a guess from resemblance, with the record checked that it was never met
    IMAGINED          IMAGINED: made by imagination; never written, never presented as remembered
    SIMULATED_RESULT  what the organism's real pipeline did on a throwaway copy (simulate)
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

__all__ = ["recall", "relive", "imagine", "simulate", "kind_of", "Recollection", "RelivedExperience", "Imagined", "Simulated"]

KINDS = ("OBSERVED", "REMEMBERED", "INFERRED", "IMAGINED", "SIMULATED_RESULT")
_KIND = {"EARNED": "REMEMBERED", "REMEMBERED": "REMEMBERED", "WEAK": "REMEMBERED", "FADED": "REMEMBERED",
         "RELIVED": "REMEMBERED", "ECHO": "REMEMBERED", "CONTEXT": "REMEMBERED", "SEARCHED": "INFERRED",
         "IMAGINED": "IMAGINED", "OBSERVED": "OBSERVED", "SIMULATED_RESULT": "SIMULATED_RESULT"}


def kind_of(provenance: str) -> str:
    """Which of the five provenance kinds a fine label belongs to."""
    head = provenance.split(",")[0].split(" (")[0].strip()
    if head not in _KIND:
        raise ValueError(f"Unknown provenance label {provenance!r}.")
    return _KIND[head]

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
    brought: tuple[tuple[str, str], ...] = ()      # second step: what the newcomer brings with it
    called_back: tuple[tuple[str, str], ...] = ()  # second step: what the rest of the scene calls back (often the swapped-out piece)
    scene: tuple[str, ...] = ()
    effect: np.ndarray | None = field(default=None, repr=False)
    sensed: np.ndarray | None = field(default=None, repr=False)
    moment: np.ndarray | None = field(default=None, repr=False)
    readout: tuple[tuple[str, float], ...] = ()


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


def _experience_parts(kernel, base: RelivedExperience) -> np.ndarray:
    """Split a relived effect back into what was sensed: effect = unit(fc*F + cc*C), with C known from the
    concepts present and |F| = 1, so the scale s solves |s*effect - cc*C| = fc (one positive root)."""
    policy = kernel.state.ecwf_policy; fc, cc = policy.feature_coupling, policy.concept_coupling
    C = kernel._concept_binding_effect(base.concept_ids)
    if C is None:
        return base.effect
    b = cc * float(np.vdot(base.effect, C).real)
    s = b + math.sqrt(max(0.0, b * b - cc * cc + fc * fc))
    return (s * base.effect - cc * C) / fc


def _scope(kernel) -> list[str]:
    state = kernel.state; shard = state.shards.get(state.active_shard_id)
    ids = shard.concept_ids if shard is not None and shard.concept_ids else state.concepts
    return sorted(c for c in ids if c in state.field_addresses)


def _readout(kernel, feature_effect, scene, moment, frames, top):
    """The organism's own resonance readout (profile, live field, recent history), on numbers only.
    Profiles of the concepts in the scene take the imagined sensing as one more exposure, as they would."""
    state = kernel.state; policy = state.ecwf_policy
    w = np.array([policy.query_profile_weight, policy.query_current_weight, policy.query_history_weight]); w = w / w.sum()
    frames = [_unit(f) for f in frames][-policy.history_window:]
    ages = [policy.history_decay ** a for a in range(len(frames))][::-1]
    out = []
    for cid in _scope(kernel):
        addr = _vec(state.field_addresses[cid]); prof = state.resonance_profiles.get(cid)
        p = 0.0
        if prof is not None:
            v = _vec(prof)
            if cid in scene:
                v = _unit(prof.exposure_count * v + feature_effect)
            p = min(1.0, abs(np.vdot(v, feature_effect)))
        elif cid in scene:
            p = 1.0
        c = min(1.0, abs(np.vdot(addr, moment)))
        h = (sum(a * min(1.0, abs(np.vdot(addr, f))) for a, f in zip(ages, frames)) / sum(ages)) if frames else 0.0
        out.append((min(1.0, w[0] * p + w[1] * c + w[2] * h), cid))
    out.sort(key=lambda x: (-x[0], x[1]))
    return out[:top]


def _brought_by(kernel, cid: str, scene: set[str], threshold: float, verb: str = "brought") -> list[tuple[str, str]]:
    """The second step: what the organism's own association recall would offer from one concept.
    Earned partners first, then bonds at or above the recall threshold (the workspace's own rule)."""
    state = kernel.state; label = {c: x.label for c, x in state.concepts.items()}; out = {}
    for s in state.structures.values():
        if cid in s.member_concept_ids and kernel.structure_is_available(s.structure_id):
            for m in s.member_concept_ids:
                if m != cid and m not in scene:
                    out[m] = f"IMAGINED ({verb} by {label[cid]}: its earned partner)"
    for b in sorted(state.plasticity_associations.values(), key=lambda x: (-x.strength, x.association_id)):
        if cid in b.concept_ids and b.strength >= threshold:
            other = b.concept_ids[0] if b.concept_ids[1] == cid else b.concept_ids[1]
            if other not in scene and other not in out:
                n = len(_meetings_with(kernel, cid, other))
                out[other] = f"IMAGINED ({verb} by {label[cid]}: bonded {b.strength:.2f}, met {n} time(s))"
    return list(out.items())


ASSOCIATION_RECALL_THRESHOLD = 0.24      # the development pipeline's default association_recall_threshold


def imagine(kernel, event_key: str, swap_out: str, swap_in: str, *, context: str = "then", top: int = 6,
            second_step: bool = True, association_threshold: float = ASSOCIATION_RECALL_THRESHOLD,
            look: tuple | None = None) -> Imagined:
    """Relive an experience with one concept swapped for another, against the mind then or now.

    Step one rebuilds the moment: the original sensing (recovered exactly from the record) with the
    swapped concept's share replaced by the newcomer's average sensing, and the concepts present
    changed. It is read with the organism's own resonance readout. Step two lets the newcomer bring
    what the organism's association recall would bring from it: earned partners and strong bonds.
    If a look (features, modality) is supplied, it replaces the guessed look; nothing else changes.
    Everything is computed on numbers derived from the record; nothing is written."""
    fingerprint = kernel.fingerprint(); state = kernel.state
    label = {cid: c.label for cid, c in state.concepts.items()}; ids = {v: k for k, v in label.items()}
    base = relive(kernel, event_key); out_id, in_id = ids[swap_out], ids[swap_in]
    if out_id not in base.concept_ids:
        raise ValueError(f"{swap_out!r} was not part of that experience.")
    policy = state.ecwf_policy; k = max(1, len(base.concept_ids))
    sensed = _experience_parts(kernel, base)
    scene = tuple(sorted((set(base.concept_ids) - {out_id}) | {in_id}))
    p_out, p_in = _vec(state.resonance_profiles[out_id]), _vec(state.resonance_profiles[in_id])
    if look is None:
        sensed_new = _unit(sensed + (p_in - p_out) / k)      # declared before testing: newcomer's average look, one share in k
    else:                                                    # a described look (features, modality), e.g. from a sketch or a sentence
        sensed_new = kernel._project_effect(kernel._validated_feature_array(look[0]), look[1])   # same scaling as real intake
    C_new = kernel._concept_binding_effect(scene)
    effect = _unit(policy.feature_coupling * sensed_new + policy.concept_coupling * C_new)

    history = state.field.history; i = _frames_by_event(kernel)[event_key]
    if context == "then":
        mind = base.mind_before; past = [_vec(f) for f in history[max(0, i - policy.history_window):i]]
    else:
        mind = _vec(state.field); past = [_vec(f) for f in history[-policy.history_window:]]
    def moment_of(e):
        return _unit(policy.retention * mind + e) if np.linalg.norm(mind) else e
    moment = moment_of(effect)
    readout = _readout(kernel, sensed_new, set(scene), moment, past + [moment], top)
    echo_moment = moment_of(base.effect)
    echoes = {cid for _s, cid in _readout(kernel, sensed, set(base.concept_ids), echo_moment, past + [echo_moment], top)}

    def where(cid):
        if cid == in_id:
            return "IMAGINED (swapped in)"
        if cid in base.concept_ids:
            return "RELIVED (from the original experience)"
        a = _vec(state.field_addresses[cid])
        if np.linalg.norm(mind) and abs(np.vdot(a, policy.retention * mind)) > abs(np.vdot(a, effect)):
            return f"CONTEXT (on the mind {context})"
        if cid in echoes:
            return "ECHO (the unchanged memory calls it up too)"
        return "IMAGINED (called up only by the new combination)"
    held = tuple((label[c], where(c)) for _s, c in readout)
    brought_ids = dict(_brought_by(kernel, in_id, set(scene), association_threshold)) if second_step else {}
    brought = tuple((label[c], how) for c, how in brought_ids.items())
    called_back = {}
    if second_step:
        for t in scene:
            if t != in_id:
                for c, how in _brought_by(kernel, t, set(scene), association_threshold, verb="called back"):
                    if c not in called_back and c not in brought_ids:
                        called_back[c] = how
    again = relive(kernel, event_key)
    intact = bool(np.allclose(again.effect, base.effect) and again.concept_ids == base.concept_ids)
    if kernel.fingerprint() != fingerprint:
        raise RuntimeError("Imagining changed the organism.")
    return Imagined(event_key, swap_out, swap_in, context, held, intact, brought=brought,
                    called_back=tuple((label[c], how) for c, how in sorted(called_back.items(), key=lambda x: label[x[0]])),
                    scene=tuple(label[c] for c in scene), effect=effect, sensed=sensed_new, moment=moment,
                    readout=tuple((label[c], float(sc)) for sc, c in readout))


@dataclass(frozen=True)
class Simulated:
    event_key: str
    observed: tuple[str, ...]                      # the concepts of the simulated experience (OBSERVED in the copy)
    came_to_mind: tuple[tuple[str, float], ...]     # the copy's real resonance readout
    brought: tuple[tuple[str, str], ...]            # (label, provenance) offered by association and earned structure
    effect: np.ndarray = field(repr=False)
    moment: np.ndarray = field(repr=False)
    organism_unchanged: bool = True


def simulate(kernel, pipeline, command) -> Simulated:
    """Run one experience through the organism's real pipeline on a throwaway copy and read what happened.

    This is the SIMULATED_RESULT kind: unlike imagining, it needs a concrete experience (its features)
    and runs every real stage. The copy is discarded; the organism's fingerprint is checked."""
    from verdant_kernel import VerdantKernel
    fingerprint = kernel.fingerprint()
    copy = VerdantKernel.from_state(kernel.state.model_copy(deep=True))
    pipeline.advance(copy, command)
    label = {c: x.label for c, x in copy.state.concepts.items()}
    x = relive(copy, command.event_key); after = _vec(copy.state.field.history[_frames_by_event(copy)[command.event_key]])
    ev = next(e for e in reversed(copy.state.resonance_events)
              if any(copy.state.evidence[r].event_key == command.event_key for r in e.evidence_refs if r in copy.state.evidence))
    came = tuple((label[c.concept_id], float(c.score)) for c in ev.query_report.candidates)
    work = next(w for w in copy.state.workspace_cycle_events if w.report.cycle == ev.committed_cycle)
    scene = set(x.concept_ids); brought = {}
    for a in work.report.assessments:
        if a.candidate.source_kind.value in ("local_association", "earned_structure") and a.carried_from_item_id is None:
            won = "won attention" if a.disposition.value == "admit" else "offered, not admitted"
            by = ", ".join(label[t] for t in a.candidate.metadata.get("trigger_concept_ids", ()))
            for m in a.candidate.binding_refs:
                if m not in scene:
                    brought.setdefault(label[m], f"SIMULATED_RESULT (brought by {by}; {won})")
    unchanged = kernel.fingerprint() == fingerprint
    if not unchanged:
        raise RuntimeError("Simulating changed the organism.")
    return Simulated(command.event_key, tuple(sorted(label[c] for c in scene)), came, tuple(sorted(brought.items())),
                     x.effect, after, unchanged)
