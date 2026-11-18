"""Looks across senses: recover what a sense organ handed in, learn each piece's own share, imagine a look.

Read-only and opt-in (nothing in verdant_* is changed). See docs/LOOKS_ACROSS_SENSES_V0.md.

* recover_input(kernel, event_key, sense) -> the organ's own description of a past experience,
  recovered from memory (the sensed part of the field frame, turned back through the fixed projection).
* Sense: how one sense combines the pieces of a scene (a space where pieces add, and the way back).
* learn_shares(kernel, sense) -> each concept's own share in that sense (INFERRED from the record),
  plus the common part no known concept explains.
* imagined_look(kernel, shares, event_key, swap_out, swap_in) -> (features, modality) for
  sidecar_recall.imagine(..., look=...): the memory's own description with one piece's share
  replaced by another's. The result is IMAGINED.
Every public call checks the organism's fingerprint is unchanged.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.optimize import minimize_scalar

from sidecar_recall import _experience_parts, _frames_by_event, relive

__all__ = ["Sense", "reading", "hearing", "sight", "placed_sight", "unknown_sense", "recover_input", "learn_shares",
           "imagined_look", "Shares", "modality_of"]


@dataclass(frozen=True)
class Sense:
    name: str
    modality: str
    width: int
    to_mix: Callable[[np.ndarray, float], np.ndarray]   # (unit-length description, its lost size) -> space where pieces add
    from_mix: Callable[[np.ndarray], np.ndarray]        # and back
    averages: bool = False                              # pieces average (sight) rather than add
    assumption: str = ""
    fit_scale: bool = False                             # the organism takes every input at unit size; refit the lost size from the record
    slots: int = 0                                      # placed sight: objects in places, left to right
    slot_width: int = 0                                 # numbers per place: the object's look, then where it is (x, y)


# --- reading: log1p(counts of hashed letter patterns), unit length -------------------------------
def _text_counts(x: np.ndarray, _scale: float = 1.0) -> np.ndarray:
    """Counts are whole numbers, so the unknown length is the one that makes them whole."""
    x = np.where(x > 1e-6, x, 0.0)
    if not x.any():
        return x
    best = None
    for c_small in range(1, 6):                          # the smallest pattern count present, tried 1..5
        norm = math.log1p(c_small) / x[x > 0].min()
        counts = np.expm1(x * norm); err = float(np.max(np.abs(counts - np.round(counts))))
        if best is None or err < best[0]:
            best = (err, np.round(counts) if err < 0.05 else counts)
    return best[1]


def _text_back(counts: np.ndarray) -> np.ndarray:
    v = np.log1p(np.maximum(counts, 0.0)); n = np.linalg.norm(v)
    return v / n if n else v


def reading(width: int = 128, modality: str = "text") -> Sense:
    return Sense("reading", modality, width, _text_counts, _text_back)


# --- hearing: mean-centred log energy per band -----------------------------------------------------
def _energy(x: np.ndarray, scale: float = 1.0) -> np.ndarray:
    z = scale * x; e = np.exp(z - z.max()); return e / e.sum()


def _energy_back(e: np.ndarray) -> np.ndarray:
    v = np.log(np.maximum(e, 1e-9 * max(float(np.max(e)), 1e-12))); return v - v.mean()


def hearing(width: int = 48, modality: str = "audio") -> Sense:
    return Sense("hearing", modality, width, _energy, _energy_back, fit_scale=True)


# --- sight: perception's per-object appearances, pooled --------------------------------------------
def sight(width: int, modality: str = "visual") -> Sense:
    return Sense("sight", modality, width, lambda x, s=1.0: s * np.asarray(x, dtype=np.float64), lambda m: m, averages=True, fit_scale=True)


def placed_sight(look_width: int, slots: int = 2, modality: str = "visual") -> Sense:
    """Sight that keeps what is where: per place, the object's look then its position. Pieces occupy
    places; a piece's share is its look (wherever it was); the adding space sums the looks over places."""
    sw = look_width + 2

    def to_mix(x, s=1.0):
        x = s * np.asarray(x, dtype=np.float64); return sum(x[i * sw:i * sw + look_width] for i in range(slots))
    return Sense("placed sight", modality, slots * sw, to_mix, lambda m: m, fit_scale=True, slots=slots, slot_width=sw)


def unknown_sense(width: int, modality: str) -> Sense:
    return Sense("unknown", modality, width, lambda x, s=1.0: s * np.asarray(x, dtype=np.float64), lambda m: m, fit_scale=True,
                 assumption="pieces assumed to add in the description itself")


# --- recovering what the organ handed in -----------------------------------------------------------
def _modalities(kernel) -> dict[str, str]:
    return {ev.event_key: str(ev.details.get("modality")) for ev in kernel.state.evidence.values()
            if ev.event_key and ev.details.get("role") == "native_payload"}


def modality_of(kernel, event_key: str) -> str:
    return _modalities(kernel)[event_key]


_PROJECTIONS: dict = {}


def _projection(kernel, modality: str, width: int) -> tuple[np.ndarray, np.ndarray]:
    key = (kernel._projection_seed(modality, width), width, kernel.state.field.state_dim)
    if key not in _PROJECTIONS:
        rng = np.random.default_rng(key[0]); scale = 1.0 / math.sqrt(width); D = key[2]
        real = rng.normal(0.0, scale, size=(width, D)); imag = rng.normal(0.0, scale, size=(width, D))
        P = np.hstack([real, imag]); _PROJECTIONS[key] = (P, np.linalg.pinv(P.T))
    return _PROJECTIONS[key]


def _invert(projection, sensed: np.ndarray) -> tuple[np.ndarray, float]:
    """sensed = unit(tanh(3 F P_r) + i tanh(3 F P_i)): find the scale s and F with arctanh(s*y)/3 = F P."""
    P, pinv = projection
    y = np.concatenate([sensed.real, sensed.imag]); top = 0.9999999 / float(np.max(np.abs(y)))

    def fit(s):
        t = np.arctanh(s * y) / 3.0; F = pinv @ t
        return F, float(np.linalg.norm(P.T @ F - t) / (np.linalg.norm(t) + 1e-300))
    grid = np.linspace(top * 0.02, top, 60); errs = [fit(s)[1] for s in grid]; i = int(np.argmin(errs))
    lo, hi = grid[max(0, i - 1)], grid[min(len(grid) - 1, i + 1)]
    s = minimize_scalar(lambda s: fit(s)[1], bounds=(lo, hi), method="bounded", options={"xatol": 1e-12}).x
    return fit(s)


def recover_input(kernel, event_key: str, sense: Sense, *, _checked: bool = True) -> tuple[np.ndarray, float]:
    """The organ's own description of a past experience, recovered from memory; and the fit residual.
    Possible when 2 x field width > the sense's width (more equations than unknowns)."""
    if 2 * kernel.state.field.state_dim <= sense.width:          # the lost size takes one more number
        raise ValueError(f"{sense.name}: the field is too narrow to recover a {sense.width}-wide description.")
    fp = kernel.fingerprint() if _checked else None
    sensed = _experience_parts(kernel, relive(kernel, event_key))
    F, residual = _invert(_projection(kernel, sense.modality, sense.width), sensed)
    if _checked and kernel.fingerprint() != fp:
        raise RuntimeError("Recovering changed the organism.")
    return F, residual


# --- shares -----------------------------------------------------------------------------------------
@dataclass
class Shares:
    sense: Sense
    concept_ids: list[str]
    share: dict[str, np.ndarray] = field(repr=False)     # concept id -> its own share (adding space)
    common: np.ndarray = field(repr=False)                # what no known concept explains, on average
    unknown: dict[str, float] = field(default_factory=dict)   # event key -> leftover fraction
    experiences: int = 0
    max_recovery_residual: float = 0.0
    scales: dict[str, float] = field(default_factory=dict)  # event key -> refitted size of its description
    word_looks: bool = False                                  # shares are observed whole-word looks (sidecar_reader)


def learn_shares(kernel, sense: Sense, *, ridge: float = 1e-3, event_keys: list[str] | None = None) -> Shares:
    """Each concept's own share in this sense, solved from every relived experience of the sense."""
    fp = kernel.fingerprint(); state = kernel.state; frames = _frames_by_event(kernel)
    mods = _modalities(kernel)
    keys = [k for k in (event_keys or sorted(frames)) if mods.get(k) == sense.modality]
    units, present, worst = [], [], 0.0
    for k in keys:
        F, r = recover_input(kernel, k, sense, _checked=False); worst = max(worst, r)
        units.append(F); present.append(list(state.field.history[frames[k]].bound_concept_ids))
    ids = sorted({c for p in present for c in p}); col = {c: j for j, c in enumerate(ids)}
    M = np.zeros((len(units), len(ids) + 1)); M[:, -1] = 1.0
    for i, p in enumerate(present):
        for c in p:
            M[i, col[c]] = 1.0 / len(p) if sense.averages else 1.0
    A = M.T @ M + ridge * np.eye(M.shape[1]); A[-1, -1] -= ridge          # no ridge on the common part
    scales = np.ones(len(units))

    def solve(scales):
        X = np.array([sense.to_mix(u, s) for u, s in zip(units, scales)]); return X, np.linalg.solve(A, M.T @ X)
    X, S = solve(scales)
    if sense.fit_scale:
        # The organism takes every input at unit size, so each experience's own size is lost. Refit it from
        # the record. Fit is judged against the experience's contrast (not its total), because otherwise
        # shrinking everything toward flat explains anything (found by tests; see the doc).
        def contrast_err(m, target):
            return float(np.linalg.norm(m - target) / (np.linalg.norm(m - m.mean()) + 1e-300))
        if sense.name == "hearing":
            grid = np.geomspace(0.25, 64.0, 33); best = None
            for c in grid:                                    # one shared size for the sense first
                X, S = solve(np.full(len(units), c)); e = np.mean([contrast_err(x, M[i] @ S) for i, x in enumerate(X)])
                if best is None or e < best[0]:
                    best = (e, c)
            scales[:] = best[1]; X, S = solve(scales)
            for _round in range(3):                           # then each experience within a factor of two
                for i, u in enumerate(units):
                    target = M[i] @ S
                    scales[i] = minimize_scalar(lambda c, u=u, t=target: contrast_err(sense.to_mix(u, c), t),
                                                bounds=(best[1] / 2, best[1] * 2), method="bounded").x
                X, S = solve(scales)
        else:                                                 # linear senses: the size enters linearly
            for _round in range(8):
                for i, u in enumerate(units):
                    t = M[i] @ S; m1 = sense.to_mix(u, 1.0); scales[i] = max(1e-6, float(m1 @ t) / float(m1 @ m1))
                scales /= np.mean(scales); X, S = solve(scales)
    left = X - M @ S
    unknown = {k: float(np.linalg.norm(l) / (np.linalg.norm(x) + 1e-300)) for k, l, x in zip(keys, left, X)}
    if kernel.fingerprint() != fp:
        raise RuntimeError("Learning shares changed the organism.")
    return Shares(sense, ids, {c: S[col[c]] for c in ids}, S[-1], unknown, len(keys), worst,
                  scales={k: float(v) for k, v in zip(keys, scales)})


def imagined_look(kernel, shares: Shares, event_key: str, swap_out: str, swap_in: str) -> tuple[list[float], str]:
    """The memory's own description with one piece's share replaced by another's (IMAGINED)."""
    label_to_id = {c.label: cid for cid, c in kernel.state.concepts.items()}
    o, n = label_to_id[swap_out], label_to_id[swap_in]
    if o not in shares.share or n not in shares.share:
        raise KeyError("No share learned for one of the pieces in this sense.")
    F, _ = recover_input(kernel, event_key, shares.sense)
    if shares.sense.slots:                        # placed sight: replace what is in the out-piece's place, keep where
        sense = shares.sense; lw = sense.slot_width - 2; full = shares.scales.get(event_key, 1.0) * np.asarray(F)
        def cos(a, b):
            return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-300))
        common = shares.common / sense.slots                       # each place's share of what every scene has
        def part(i):
            return full[i * sense.slot_width:i * sense.slot_width + lw]
        place = max(range(sense.slots), key=lambda i: cos(part(i) - common, shares.share[o]))
        full = full.copy()
        full[place * sense.slot_width:place * sense.slot_width + lw] = part(place) - shares.share[o] + shares.share[n]
        return [float(v) for v in full], sense.modality
    mix = shares.sense.to_mix(F, shares.scales.get(event_key, 1.0))
    k = len(kernel.state.field.history[_frames_by_event(kernel)[event_key]].bound_concept_ids)
    w = 1.0 / k if shares.sense.averages else 1.0
    if shares.word_looks:                        # how many times the word is in this memory (fixed rule: least squares, 1..3)
        g = shares.share[o]; w = float(np.clip(np.round(float(mix @ g) / float(g @ g)), 1, 3)) if g @ g > 0 else 1.0
    new = mix - w * shares.share[o] + w * shares.share[n]
    if shares.sense.name == "reading":
        new = np.maximum(new, 0.0)
    if shares.sense.name == "hearing":
        new = np.maximum(new, 0.0); new = new / new.sum() if new.sum() > 0 else mix
    return [float(v) for v in shares.sense.from_mix(new)], shares.sense.modality
