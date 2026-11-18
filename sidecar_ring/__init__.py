"""Ringing: each sense keeps its own view of each concept, and recognition rings the wave.

Claim boundary: IMPLEMENTED-EXPERIMENTAL, opt-in. No file under ``verdant_*`` is edited. Installing
this CHANGES behaviour: fields, resonance scores and fingerprints differ from stock.
See docs/RECOGNITION_IN_THE_WAVE_V0.md.

1. Per-sense views (write side, persisted in concept attributes)
   Stock keeps one profile per concept with every sense averaged in, so a thing mostly heard is
   barely recognisable by sight (measured: 0-50% naming from sight). Here every experience also
   updates the concept's view through that sense alone (a running mean of the sensed wave), and
   the resonance profile term reads the view for the query's sense when one exists.
2. Recognition rings the wave (write side)
   Stock writes only told concepts' addresses into the field; what the organism recognises is
   never written, so hearing a thing unnamed leaves no trace of the thing (priming measured: none).
   Here, before the write, the sensed wave is explained by the per-sense views (least squares, the
   same readout for every sense). Up to RING_MAX concepts that explain at least RING_SHARE of it,
   when no more than RING_UNKNOWN is unknown, add their addresses to the binding effect with
   weight = share (a told concept has weight 1). Fixed before testing.
3. Inferred is never told
   A rung concept does not update any profile or view (no learning from its own guesses). Every ring
   is logged on the concept, keyed by the field-history index, so replay stays exact
   (sidecar_recall reads it). A ring that differs from what the experience was told is logged as a
   disagreement (raw material for tension steering attention).
4. Adaptation in the wave (optional, install_ring(adapt=True); added after the first ring runs)
   The resonance profile term compares the per-sense view and the input after subtracting the
   sense's average wave (the count-weighted mean of all views), as a cosine. A sense whose inputs
   all look alike (sight here: ~96% alike) is then read by how each input differs from the usual.
"""
from __future__ import annotations

import math

import numpy as np

RING_SHARE = 0.25
RING_UNKNOWN = 0.5
RING_MAX = 2
_SETTINGS = {"adapt": False}
VIEW_PREFIX = "view::"
_ORIGINAL: dict = {}


def _views(kernel, modality: str):
    ids, vecs = [], []
    for cid, c in kernel.state.concepts.items():
        a = c.attributes.get(VIEW_PREFIX + modality)
        if a:
            ids.append(cid); vecs.append(np.asarray(a["real"]) + 1j * np.asarray(a["imag"]))
    return ids, vecs


def recognise(kernel, sensed: np.ndarray, modality: str, *, adapt: bool = False):
    """[(concept_id, share)] best first, and the unknown share, from the per-sense views kept in the organism."""
    ids, vecs = _views(kernel, modality)
    if not ids:
        return [], 1.0
    B = np.array(vecs).T; F = sensed
    if adapt:
        mean = kernel.state.concepts and _sense_mean(kernel, modality)
        if mean is not None:
            F = F - mean; B = B - mean[:, None]
    nF = float(np.vdot(F, F).real)
    if nF <= 1e-300:
        return [], 1.0
    c = np.linalg.solve(B.conj().T @ B + 1e-6 * np.eye(B.shape[1]), B.conj().T @ F)
    left = F - B @ c
    shares = sorted(((ids[j], float(np.vdot(B[:, j] * c[j], F).real / nF)) for j in range(len(ids))), key=lambda x: (-x[1], x[0]))
    return shares, float(np.vdot(left, left).real / nF)


def _sense_mean(kernel, modality):
    tot, n = None, 0
    for c in kernel.state.concepts.values():
        a = c.attributes.get(VIEW_PREFIX + modality)
        if a:
            v = (np.asarray(a["real"]) + 1j * np.asarray(a["imag"])) * a["count"]
            tot = v if tot is None else tot + v; n += a["count"]
    return None if tot is None else tot / n


def rings_of_frame(kernel, index: int) -> dict[str, float]:
    """concept_id -> ring weight for one field-history frame (empty if nothing rang)."""
    out = {}
    for cid, c in kernel.state.concepts.items():
        w = c.attributes.get("rings", {}).get(str(index))
        if w is not None:
            out[cid] = float(w)
    return out


def _set(kernel, cid, **attrs):
    c = kernel.state.concepts[cid]
    kernel.state.concepts[cid] = c.model_copy(update={"attributes": {**c.attributes, **attrs}})


def _ring_binding_effect(self, concept_ids):
    pending = getattr(self, "_ring_pending", None)
    base = _ORIGINAL["_concept_binding_effect"](self, concept_ids)
    if not pending:
        return base
    total = np.zeros(self.state.field.state_dim, dtype=np.complex128)
    told = tuple(sorted(set(concept_ids)))
    if base is not None:
        total += base * math.sqrt(max(1, len(told)))
    for cid, w in pending:
        total += w * self._address_array(self.state.field_addresses[cid])
    return self._normalize_complex(total)


def _ring_apply_field_effect(self, features, modality, *, caused_by_refs, bound_concept_ids=()):
    sensed = self._project_effect(self._validated_feature_array(features), modality)
    told = tuple(sorted(set(bound_concept_ids)))
    shares, unknown = recognise(self, sensed, modality)
    self._ring_last_reading = {"index": len(self.state.field.history), "modality": modality, "shares": shares,
                               "unknown": unknown, "told": told, "had_views": bool(_views(self, modality)[0])}
    ring = [(cid, s) for cid, s in shares[:RING_MAX] if s >= RING_SHARE and cid not in told] if unknown <= RING_UNKNOWN else []
    index = len(self.state.field.history)
    for cid, _w in ring:
        self._ensure_field_address(cid)
    self._ring_pending = ring
    try:
        _ORIGINAL["_apply_field_effect"](self, features, modality, caused_by_refs=caused_by_refs, bound_concept_ids=bound_concept_ids)
    finally:
        self._ring_pending = None
    for cid, w in ring:
        a = self.state.concepts[cid].attributes
        _set(self, cid, rings={**a.get("rings", {}), str(index): float(w)},
             ring_disagreements=int(a.get("ring_disagreements", 0)) + (1 if told else 0))
    for cid in told:                                           # the told concept's view through this sense
        a = self.state.concepts[cid].attributes.get(VIEW_PREFIX + modality)
        n = (a or {}).get("count", 0); old = (np.asarray(a["real"]) + 1j * np.asarray(a["imag"])) if a else np.zeros_like(sensed)
        new = (old * n + sensed) / (n + 1)
        _set(self, cid, **{VIEW_PREFIX + modality: {"real": [float(v) for v in new.real], "imag": [float(v) for v in new.imag], "count": n + 1}})


def _ring_profile_array(self, profile):
    modality = getattr(self, "_ring_query_modality", None)            # set only while reading resonance
    if modality and profile.concept_id in self.state.concepts:
        a = self.state.concepts[profile.concept_id].attributes.get(VIEW_PREFIX + modality)
        if a:
            v = np.asarray(a["real"]) + 1j * np.asarray(a["imag"])     # the view's own size, like a profile mean
            q = getattr(self, "_ring_query", None)
            if _SETTINGS["adapt"] and q is not None:
                # Adaptation in the wave: compare view and input after removing what this sense usually is.
                # Returns u with vdot(u, F) = cosine(view - mean, F - mean), so the stock alignment reads it.
                F, m = q; d = v - m; dF = F - m; nd, ndF = np.linalg.norm(d), np.linalg.norm(dF)
                if nd > 1e-12 and ndF > 1e-12:
                    alpha = -np.conj(np.vdot(d, m))
                    return (d + alpha * F) / (nd * ndF)
            return v
    return _ORIGINAL["_profile_array"](self, profile)


def _ring_inspect_resonance(self, features, modality, **kwargs):
    self._ring_query_modality = modality
    if _SETTINGS["adapt"]:
        m = _sense_mean(self, modality)
        self._ring_query = None if m is None else (self._project_effect(self._validated_feature_array(features), modality), m)
    try:
        return _ORIGINAL["inspect_resonance"](self, features, modality, **kwargs)
    finally:
        self._ring_query_modality = None; self._ring_query = None


def install_ring(*, adapt: bool = False) -> None:
    """adapt=True: the resonance profile term compares view and input relative to the sense's usual wave."""
    from verdant_kernel import VerdantKernel
    _SETTINGS["adapt"] = adapt
    if _ORIGINAL:
        return
    for name, fn in (("_apply_field_effect", _ring_apply_field_effect), ("_concept_binding_effect", _ring_binding_effect),
                     ("_profile_array", _ring_profile_array), ("inspect_resonance", _ring_inspect_resonance)):
        _ORIGINAL[name] = getattr(VerdantKernel, name); setattr(VerdantKernel, name, fn)


def uninstall_ring() -> None:
    from verdant_kernel import VerdantKernel
    for name, fn in _ORIGINAL.items():
        setattr(VerdantKernel, name, fn)
    _ORIGINAL.clear()


def ring_installed() -> bool:
    return bool(_ORIGINAL)


def how_known(kernel, concept_label: str) -> dict:
    """Naming as its own kind of evidence: how the organism knows a concept, kept apart by kind.

    named         experiences of reading in which it was told (text lessons naming it)
    sensed_told   per sense, experiences sensed while being told what it was (OBSERVED)
    rung          per sense, times it was recognised without being told (INFERRED)
    knows_look_of senses through which it has its own view; a concept only named has none, so the
                  organism can say "I know the word, not what it looks like"."""
    from sidecar_recall import _frames_by_event
    cid = next((c for c, x in kernel.state.concepts.items() if x.label == concept_label), None)
    if cid is None:
        return {"known": False}
    mods = {ev.event_key: str(ev.details.get("modality")) for ev in kernel.state.evidence.values()
            if ev.event_key and ev.details.get("role") == "native_payload"}
    told: dict[str, int] = {}
    for key, i in _frames_by_event(kernel).items():
        if cid in kernel.state.field.history[i].bound_concept_ids:
            m = mods.get(key, "unknown"); told[m] = told.get(m, 0) + 1
    rung: dict[str, int] = {}
    by_index = {i: mods.get(k, "unknown") for k, i in _frames_by_event(kernel).items()}
    for index in kernel.state.concepts[cid].attributes.get("rings", {}):
        m = by_index.get(int(index), "unknown"); rung[m] = rung.get(m, 0) + 1
    a = kernel.state.concepts[cid].attributes
    looks = sorted(k[len(VIEW_PREFIX):] for k in a if k.startswith(VIEW_PREFIX) and k[len(VIEW_PREFIX):] != "text")
    return {"known": True, "named": told.get("text", 0), "sensed_told": {m: n for m, n in told.items() if m != "text"},
            "rung": rung, "knows_look_of": looks}



# --- 5. Binding across moments (no code change; two existing settings) ---------------------------
# Measured (run_observer_binding.py): a thing seen and another heard at the same moment never bonded.
# Cause: what is sensed stays present for `current_evidence_persistence` = 1 kernel cycle, and the
# workspace caps carrying at 4 cycles, but one experience takes 4-5 cycles inside the organism
# (sensing, resonance, workspace, plasticity, structures). So nothing sensed is ever still present
# when the next experience arrives, and bonds need two things present together.
# Short-term memory of one experience uses the engine's own settings:
CARRY_ONE_EXPERIENCE = {"current_evidence_persistence": 7}       # DevelopmentalCycleConfig
CARRY_WORKSPACE_CAP = 8                                           # WorkspacePolicy.maximum_persistence_cycles


def carry_one_experience(kernel) -> None:
    """Set the organism's workspace cap so a sensed item can last through the next experience."""
    wp = kernel.state.workspace_policy
    kernel.state.workspace_policy = wp.model_copy(update={"maximum_persistence_cycles": CARRY_WORKSPACE_CAP, "revision": wp.revision + 1})


# --- 6. What is recognised can remind ------------------------------------------------------------
# Measured: after binding, a NAMED sound of Q brought P to mind 4/4, an unnamed one 0/4, because
# association recall starts only from told concepts. With install_inferred_association(), concepts
# that rang in this experience also start association recall; every such candidate is marked
# metadata["triggered_by_inferred"] = True and its trigger listed, so a guess stays a guess.
_ASSOC: dict = {}


def _inferred_association_candidates(self, kernel, experience):
    told = _ASSOC["orig"](self, kernel, experience)
    rung = sorted(rings_of_frame(kernel, len(kernel.state.field.history) - 1))
    rung = [c for c in rung if c not in set(experience.concept_ids)]
    if not rung:
        return told
    import dataclasses
    extra = _ASSOC["orig"](self, kernel, dataclasses.replace(experience, concept_ids=tuple(rung)))
    have = {(c.source_ref, c.binding_refs) for c in told}
    present = set(experience.concept_ids)
    marked = tuple(c.model_copy(update={"metadata": {**c.metadata, "triggered_by_inferred": True, "inferred_triggers": tuple(rung)}})
                   for c in extra if (c.source_ref, c.binding_refs) not in have and not set(c.binding_refs) & present)
    return tuple(told) + marked


def install_inferred_association() -> None:
    import verdant_development.pipeline as dev
    if not _ASSOC:
        _ASSOC["orig"] = dev.VerdantDevelopmentPipeline._association_recall_candidates
        dev.VerdantDevelopmentPipeline._association_recall_candidates = _inferred_association_candidates


def uninstall_inferred_association() -> None:
    import verdant_development.pipeline as dev
    if _ASSOC:
        dev.VerdantDevelopmentPipeline._association_recall_candidates = _ASSOC.pop("orig")


# --- 7. Tension and the unknown steer attention ------------------------------------------------------
# Stock: every current experience enters the workspace with novelty = 0.35 and contradiction_pressure
# = 0, whatever it is; the workspace weights both (0.06 and 0.14) but they are never measured.
# With install_attention(), they are measured from the wave BEFORE the experience changes memory:
#   novelty       = the unknown share of the input in its sense (1.0 if the sense has no views yet)
#   contradiction = how much a concept it was NOT told explains, beyond what the told ones explain,
#                   max(0, best_other - told), when the told concepts already have a view in this sense
# Attention decides learning (plasticity weights bonds by the winning items' scores), so this steers it.
# Each told concept also keeps a phase-aware agreement record, like the stance sidecar: +1 when the
# input agrees with it, a half turn (-1) when it conflicts, weighted by size. read_tension() gives the
# net (agreement minus conflict) and the tension (how much was said that cancelled out).
_ATTN: dict = {}


def measured_signals(kernel):
    r = getattr(kernel, "_ring_last_reading", None)
    if not r or r["index"] != len(kernel.state.field.history) - 1:
        return None
    told_share = sum(s for c, s in r["shares"] if c in r["told"])
    others = [s for c, s in r["shares"] if c not in r["told"]]
    told_have_views = any(VIEW_PREFIX + r["modality"] in kernel.state.concepts[c].attributes and
                          kernel.state.concepts[c].attributes[VIEW_PREFIX + r["modality"]]["count"] > 1 for c in r["told"])
    contradiction = max(0.0, (max(others) if others else 0.0) - told_share) if (r["told"] and told_have_views) else 0.0
    novelty = float(min(1.0, max(0.0, r["unknown"]))) if r["had_views"] else 1.0
    return {"novelty": novelty, "contradiction_pressure": float(min(1.0, contradiction)), "told_share": told_share, "reading": r}


def _attn_workspace_candidates(self, kernel, experience, resonance_event):
    out = _ATTN["orig"](self, kernel, experience, resonance_event)
    m = measured_signals(kernel)
    if m is None:
        return out
    result = []
    for c in out:
        if c.source_kind.value == "current_evidence":
            c = c.model_copy(update={"signals": c.signals.model_copy(update={"novelty": m["novelty"], "contradiction_pressure": m["contradiction_pressure"]}),
                                     "metadata": {**c.metadata, "novelty_source": "sidecar_ring.measured", "contradiction_source": "sidecar_ring.measured"}})
        result.append(c)
    for cid in experience.concept_ids:                      # phase-aware agreement record per told concept
        a = kernel.state.concepts[cid].attributes
        if VIEW_PREFIX + m["reading"]["modality"] not in a:
            continue
        agree = m["told_share"]; conflict = m["contradiction_pressure"]
        _set(kernel, cid, tension_record={"writings": a.get("tension_record", {}).get("writings", 0) + 1,
                                          "signed_sum": a.get("tension_record", {}).get("signed_sum", 0.0) + agree - conflict,
                                          "size_sum": a.get("tension_record", {}).get("size_sum", 0.0) + agree + conflict})
    return tuple(result)


def read_tension(kernel) -> dict[str, dict]:
    out = {}
    for c in kernel.state.concepts.values():
        t = c.attributes.get("tension_record")
        if t and t["writings"]:
            n = t["writings"]; out[c.label] = {"writings": n, "net": t["signed_sum"] / n, "tension": (t["size_sum"] - abs(t["signed_sum"])) / n}
    return out


def install_attention() -> None:
    import verdant_development.pipeline as dev
    if not _ATTN:
        _ATTN["orig"] = dev.VerdantDevelopmentPipeline._workspace_candidates
        dev.VerdantDevelopmentPipeline._workspace_candidates = _attn_workspace_candidates


def uninstall_attention() -> None:
    import verdant_development.pipeline as dev
    if _ATTN:
        dev.VerdantDevelopmentPipeline._workspace_candidates = _ATTN.pop("orig")


# --- 8. Binding by moment, not by time (replaces carrying everything one experience) -------------
# Measured on the 400-lesson text life: carrying every sensed item through the next experience
# (CARRY_ONE_EXPERIENCE) bound unrelated neighbouring lessons: wrong promotions 0 -> 5, cues kept
# 145 -> 139 of 148. What binding needed was the same MOMENT (a look and a sound in one context), so
# with install_moment_carry() the previous experience's told concepts are offered again only when
# the new experience shares its context; labelled "same moment: <event>", grounded slightly less.
_MOMENT: dict = {}


def _context_of_frame(kernel, index: int):
    frame = kernel.state.field.history[index]
    for ref in frame.caused_by_refs:
        ev = kernel.state.evidence.get(ref)
        if ev is not None and ev.details.get("role") == "native_payload":
            return ev.details.get("context_id"), ev.event_key, ref, tuple(frame.bound_concept_ids)
    return None, None, None, ()


def _moment_workspace_candidates(self, kernel, experience, resonance_event):
    out = _MOMENT["orig"](self, kernel, experience, resonance_event)
    h = kernel.state.field.history
    if len(h) < 2:
        return out
    now_ctx, _k, _r, _c = _context_of_frame(kernel, len(h) - 1)
    prev_ctx, prev_key, prev_ref, prev_concepts = _context_of_frame(kernel, len(h) - 2)
    prev_concepts = tuple(c for c in prev_concepts if c not in set(experience.concept_ids))
    if not now_ctx or now_ctx != prev_ctx or not prev_concepts:
        return out
    from verdant_kernel.models import WorkspaceCandidateInput, WorkspaceSignals, WorkspaceSourceKind
    extra = WorkspaceCandidateInput(
        source_kind=WorkspaceSourceKind.CURRENT_EVIDENCE, source_ref=prev_ref,
        label=f"same moment: {prev_key}", evidence_refs=(prev_ref,), resource_request=self.config.current_evidence_resource,
        persistence_cycles=1, signals=WorkspaceSignals(evidence_grounding=0.72, relevance=0.65, prediction_error=0.0, novelty=0.0),
        binding_refs=tuple(sorted(prev_concepts)), metadata={"developmental_stage": "same_moment_carry", "context_id": now_ctx})
    return tuple(out) + (extra,)


def install_moment_carry() -> None:
    import verdant_development.pipeline as dev
    if not _MOMENT:
        _MOMENT["orig"] = dev.VerdantDevelopmentPipeline._workspace_candidates
        dev.VerdantDevelopmentPipeline._workspace_candidates = _moment_workspace_candidates


def uninstall_moment_carry() -> None:
    import verdant_development.pipeline as dev
    if _MOMENT:
        dev.VerdantDevelopmentPipeline._workspace_candidates = _MOMENT.pop("orig")
