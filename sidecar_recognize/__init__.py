"""Recognising in the wave: one readout for every sense (opt-in, read-only, EXPERIMENTAL).

Every sense enters the same field through its own fixed doorway (projection), so an input of any
sense becomes one kind of thing: a wave. This module asks of that wave, the same way for every
sense: how much of it is explained by things the organism knows, by which things, and how much is
left over as unknown. Nothing is written; every call checks the organism's fingerprint.

Two views of what is known, both read from the organism's own record:
  chord     each concept's single resonance profile (all senses layered on top of each other),
            exactly as the engine keeps it
  per_sense each concept's view through one sense: the average of what was sensed in that
            concept's experiences of that sense (recovered exactly from the field history)
Optional adaptation in the wave: subtract the sense's average wave (what that sense usually
looks like) from the input and from the per-sense views before reading.
See docs/RECOGNITION_IN_THE_WAVE_V0.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from sidecar_recall import _experience_parts, _frames_by_event, _unit, _vec, relive

__all__ = ["Reading", "read_wave", "sense_views", "sensed_wave"]


@dataclass(frozen=True)
class Reading:
    modality: str
    view: str
    known: tuple[tuple[str, float, float], ...]   # (label, share of the wave it explains, phase in turns)
    unknown: float                                # share of the wave nothing known explains
    adapted: bool = False
    coefficients: dict = field(default_factory=dict, repr=False)

    @property
    def best(self) -> str | None:
        return self.known[0][0] if self.known else None


def sensed_wave(kernel, features, modality: str) -> np.ndarray:
    """What the organism would take in: the input through its own doorway, at its own scaling."""
    return kernel._project_effect(kernel._validated_feature_array(features), modality)


def _modalities(kernel) -> dict[str, str]:
    return {ev.event_key: str(ev.details.get("modality")) for ev in kernel.state.evidence.values()
            if ev.event_key and ev.details.get("role") == "native_payload"}


_VIEWS: dict = {}


def sense_views(kernel) -> dict:
    """{modality: {"mean": wave, "views": {concept_id: (wave, count)}}} from the field history."""
    key = (id(kernel.state), kernel.state.cycle, len(kernel.state.field.history))
    if key in _VIEWS:
        return _VIEWS[key]
    mods = _modalities(kernel); sums: dict = {}
    for ev_key, i in _frames_by_event(kernel).items():
        m = mods.get(ev_key)
        if m is None:
            continue
        x = relive(kernel, ev_key); s = _experience_parts(kernel, x)
        bucket = sums.setdefault(m, {"total": np.zeros_like(s), "n": 0, "views": {}})
        bucket["total"] = bucket["total"] + s; bucket["n"] += 1
        for cid in x.concept_ids:
            v, n = bucket["views"].get(cid, (np.zeros_like(s), 0)); bucket["views"][cid] = (v + s, n + 1)
    out = {m: {"mean": b["total"] / b["n"], "views": {c: (v / n, n) for c, (v, n) in b["views"].items()}} for m, b in sums.items()}
    _VIEWS.clear(); _VIEWS[key] = out
    return out


def read_wave(kernel, features, modality: str, *, view: str = "per_sense", adapt: bool = False,
              top: int = 5, ridge: float = 1e-6, sensed: np.ndarray | None = None) -> Reading:
    """Explain an incoming wave by what is known; the rest is unknown. Same calculation for every sense."""
    fp = kernel.fingerprint(); state = kernel.state
    F = sensed if sensed is not None else sensed_wave(kernel, features, modality)
    if view == "chord":
        ids = sorted(state.resonance_profiles); B = np.array([_vec(state.resonance_profiles[c]) for c in ids]).T
        mean = None
    else:
        sv = sense_views(kernel).get(modality)
        if not sv:
            return Reading(modality, view, (), 1.0, adapt)
        ids = sorted(sv["views"]); B = np.array([sv["views"][c][0] for c in ids]).T; mean = sv["mean"]
    if adapt and mean is not None:
        F = F - mean; B = B - mean[:, None]
    nF = float(np.vdot(F, F).real)
    if nF <= 1e-300 or not ids:
        return Reading(modality, view, (), 1.0, adapt)
    G = B.conj().T @ B + ridge * np.eye(B.shape[1]); c = np.linalg.solve(G, B.conj().T @ F)
    left = F - B @ c; unknown = float(np.vdot(left, left).real / nF)
    shares = [(float(np.vdot(B[:, j] * c[j], F).real / nF), j) for j in range(len(ids))]
    shares.sort(key=lambda x: -x[0])
    label = {cid: x.label for cid, x in state.concepts.items()}
    known = tuple((label[ids[j]], s, float(np.angle(c[j]) / (2 * np.pi))) for s, j in shares[:top])
    if kernel.fingerprint() != fp:
        raise RuntimeError("Reading changed the organism.")
    return Reading(modality, view, known, unknown, adapt, {label[ids[j]]: complex(c[j]) for j in range(len(ids))})
