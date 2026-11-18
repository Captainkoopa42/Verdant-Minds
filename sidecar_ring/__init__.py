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
