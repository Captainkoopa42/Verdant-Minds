"""Opt-in wave sidecar: give the field's phase a job, and let recognition lead context.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited. Installing
this CHANGES behaviour (it is not an accelerator): fields, resonance scores and therefore
fingerprints differ from stock. ``uninstall_wave()`` restores the stock methods.

1. Phase carries direction (write side)
   Stock adds the addresses of an experience's concepts with no phase offset, so the field
   cannot tell "A feeds B" from "B feeds A". Here a concept that only acts (source) is
   written in step, a concept that is only acted on (target) a quarter turn later, and a
   concept that is both (the middle of a chain) an eighth turn later. Nothing else about
   the write changes. Roles come from the experience's own directed relation proposals.

2. Recognition leads, context breaks ties (read side)
   Stock score = 0.5 profile + 0.3 live field + 0.2 history, where a concept that was
   merely recent can outrank one the input actually resembles. Here
       recognition = how far a concept's profile match stands above the crowd (2 SD = 0, 5 SD = 1)
       context     = the same measure for its presence in the live field and recent history
       score       = recognition * (0.6 + 0.4 * context) + 0.1 * context
   so context alone can never score above 0.1, and with fewer than 8 concepts in scope the
   stock score is kept. The recorded alignments and weights in each contribution are the
   stock values; only ``score`` and the ranking change.

3. ``field_direction`` (read-only observer)
   Reads who-acted-on-whom for a pair of concepts back out of the canonical field history.
"""
from __future__ import annotations

import hashlib
import inspect
import math

import numpy as np

import verdant_kernel.kernel as _kernel_module
from verdant_kernel import VerdantKernel

STOCK_INSPECT_RESONANCE_SHA256 = "528666983c32cce543e31419f60720c1dc6de669022845a53cb7f67fbad7caa1"
STOCK_BINDING_EFFECT_SHA256 = "a279b7547cae4c34e4fad7bf4652e2e4d5832211fabc8e6cc92d4015a6ccef2c"
_ANCHOR = "        ordered = sorted(unranked, key=lambda item: (-item[1], item[0]))\n"
_ORIGINAL: dict[str, object] = {}
QUARTER = 1j
EIGHTH = (1 + 1j) / math.sqrt(2)


def _stand_out(values: np.ndarray) -> np.ndarray:
    spread = values.std()
    if spread < 1e-12:
        return np.zeros_like(values)
    return np.clip(((values - values.mean()) / spread - 2.0) / 3.0, 0.0, 1.0)


def _wave_rescore(self, unranked):
    if len(unranked) < 8:
        return unranked
    profile = np.array([item[2].profile_alignment for item in unranked])
    context = np.array([0.6 * item[2].current_field_alignment + 0.4 * item[2].history_alignment for item in unranked])
    recognition, ctx = _stand_out(profile), _stand_out(context)
    scores = np.clip(recognition * (0.6 + 0.4 * ctx) + 0.1 * ctx, 0.0, 1.0)
    return [(item[0], float(scores[i]), item[2]) for i, item in enumerate(unranked)]


def _roles_for(self, command) -> dict[str, complex]:
    sources, targets = set(), set()
    for relation in getattr(command, "relation_proposals", ()) or ():
        if getattr(relation, "directed", True):
            sources.add(relation.source_label.strip().lower()); targets.add(relation.target_label.strip().lower())
    return {"sources": sources, "targets": targets}


def _wave_apply_experience(self, command):
    self._wave_roles = _roles_for(self, command)
    try:
        return _ORIGINAL["apply_experience"](self, command)
    finally:
        self._wave_roles = None


def _wave_binding_effect(self, concept_ids):
    unique_ids = tuple(sorted(set(concept_ids)))
    if not unique_ids:
        return None
    roles = getattr(self, "_wave_roles", None) or {"sources": set(), "targets": set()}
    total = np.zeros(self.state.field.state_dim, dtype=np.complex128)
    for concept_id in unique_ids:
        concept = self.state.concepts[concept_id]
        names = {concept.label.strip().lower(), concept.normalized_label.strip().lower()}
        acts, acted_on = bool(names & roles["sources"]), bool(names & roles["targets"])
        turn = EIGHTH if (acts and acted_on) else QUARTER if acted_on else 1.0
        total = total + turn * self._address_array(self.state.field_addresses[concept_id])
    return self._normalize_complex(total)


def field_direction(kernel: VerdantKernel, first_id: str, second_id: str) -> tuple[float, int]:
    """(angle in turns, frames used). Positive: ``first`` acted on ``second`` in the field's record."""
    def address(cid):
        a = kernel.state.field_addresses[cid]
        return np.asarray(a.real) + 1j * np.asarray(a.imag)
    a, b = address(first_id), address(second_id); total = 0j; used = 0
    for frame in kernel.state.field.history:
        if first_id in frame.bound_concept_ids and second_id in frame.bound_concept_ids:
            f = np.asarray(frame.real) + 1j * np.asarray(frame.imag)
            total += np.vdot(b, f) * np.conj(np.vdot(a, f)); used += 1
    return (float(np.angle(total) / (2 * math.pi)) if used else 0.0), used


def wave_installed() -> bool:
    return bool(_ORIGINAL)


def install_wave() -> None:
    if _ORIGINAL:
        return
    stock = VerdantKernel.__dict__["inspect_resonance"]; source = inspect.getsource(stock)
    if hashlib.sha256(source.encode()).hexdigest() != STOCK_INSPECT_RESONANCE_SHA256:
        raise RuntimeError("Stock inspect_resonance changed; the wave sidecar must be re-derived.")
    if hashlib.sha256(inspect.getsource(VerdantKernel._concept_binding_effect).encode()).hexdigest() != STOCK_BINDING_EFFECT_SHA256:
        raise RuntimeError("Stock _concept_binding_effect changed; the wave sidecar must be re-derived.")
    derived = inspect.cleandoc("\n" + source) if False else source
    derived = derived.replace(_ANCHOR, "        unranked = self._wave_rescore(unranked)\n" + _ANCHOR)
    namespace: dict = {}
    import textwrap
    exec(compile(textwrap.dedent(derived), "<sidecar_wave derived inspect_resonance>", "exec"), vars(_kernel_module), namespace)
    for name in ("inspect_resonance", "_concept_binding_effect", "apply_experience"):
        _ORIGINAL[name] = VerdantKernel.__dict__[name]
    VerdantKernel._wave_rescore = _wave_rescore
    VerdantKernel.inspect_resonance = namespace["inspect_resonance"]
    VerdantKernel._concept_binding_effect = _wave_binding_effect
    VerdantKernel.apply_experience = _wave_apply_experience


def uninstall_wave() -> None:
    if not _ORIGINAL:
        return
    for name, original in list(_ORIGINAL.items()):
        setattr(VerdantKernel, name, original)
    _ORIGINAL.clear()
    del VerdantKernel._wave_rescore


__all__ = ["install_wave", "uninstall_wave", "wave_installed", "field_direction"]
