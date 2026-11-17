"""Opt-in stance sidecar: the field carries what it was told about a proposition, and the tension.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited. Installing it
changes behaviour (the field write and the concept set), so fingerprints differ from stock.
``uninstall_stance()`` restores the stock methods. It never reads, writes or overrides a claim
record, a claim's status or a contradiction record: the claims engine stays the only authority
on what is believed. This is a second, independent account kept in the wave.

Reading of the origin notes it tests: phase is "synergy or conflict among facets"; contradiction
is "carried, not erased"; stability is "graceful diminishment of contradiction".

Write   Each proposition (subject, predicate, object; same key the claims engine uses) has a
        field address derived like a concept's. When an experience makes a claim, that address
        is added to the experience's field effect IN STEP if affirmed and HALF A TURN ROUND
        (x -1) if denied.
Record  Inside the same experience (before its transition is fingerprinted) a proposition
        concept (``concept_type = proposition_stance``) carries, in its attributes, what the
        field received along the proposition's address, at two speeds:
          lifelong   sum of every writing, and the sum of their sizes
          recent     a running blend that keeps half of the old each time it is told again
Read    net      = |lifelong sum| / writings          how much survives
        tension  = (sum of sizes - |sum|) / writings   what was said and cancelled
        stance   = direction of the lifelong / recent sum: 0 turns = told true, 0.5 = told false
"""
from __future__ import annotations

import math

import numpy as np

from verdant_kernel import VerdantKernel
from verdant_kernel.models import normalize_label, stable_id

__all__ = ["install_stance", "uninstall_stance", "stance_installed", "proposition_key", "read_stance", "STANCE_TYPE"]

STANCE_TYPE = "proposition_stance"
RECENT_KEEP = 0.5
_ORIGINAL: dict[str, object] = {}


def proposition_key(subject: str, predicate: str, obj: str) -> str:
    return stable_id("claimkey", stable_id("concept", normalize_label(subject)), normalize_label(predicate),
                     stable_id("concept", normalize_label(obj)))


def _address(kernel: VerdantKernel, key: str) -> np.ndarray:
    return kernel._address_array(kernel._derive_field_address(f"proposition::{key}", 0))


def _pending(kernel) -> list[tuple[str, str, float]]:
    return getattr(kernel, "_stance_pending", None) or []


def _stance_apply_experience(self, command):
    self._stance_pending = [
        (proposition_key(c.subject_label, c.predicate, c.object_label),
         f"proposition {normalize_label(c.subject_label)} {normalize_label(c.predicate)} {normalize_label(c.object_label)}",
         1.0 if c.polarity.value == "affirmed" else -1.0)
        for c in command.claim_proposals]
    try:
        return _ORIGINAL["apply_experience"](self, command)
    finally:
        self._stance_pending = None


def _stance_binding_effect(self, concept_ids):
    base = _ORIGINAL["_concept_binding_effect"](self, concept_ids)
    pending = _pending(self)
    if not pending:
        return base
    total = np.zeros(self.state.field.state_dim, dtype=np.complex128)
    if base is not None:
        total += base * math.sqrt(max(1, len(set(concept_ids))))      # undo the normalisation: one unit per concept
    for key, _label, sign in pending:
        total += sign * _address(self, key)
    return self._normalize_complex(total)


def _stance_apply_field_effect(self, features, modality, *, caused_by_refs, bound_concept_ids=()):
    pending = _pending(self)
    if not pending:
        return _ORIGINAL["_apply_field_effect"](self, features, modality, caused_by_refs=caused_by_refs,
                                                bound_concept_ids=bound_concept_ids)
    # the experience effect exactly as the kernel composes it, to read what each proposition received
    policy = self.state.ecwf_policy; bound = tuple(sorted(set(bound_concept_ids)))
    for concept_id in bound:
        self._ensure_field_address(concept_id)
    feature_effect = self._project_effect(self._validated_feature_array(features), modality)
    concept_effect = self._concept_binding_effect(bound)
    parts = [policy.feature_coupling * feature_effect] + ([policy.concept_coupling * concept_effect] if concept_effect is not None else [])
    effect = self._normalize_complex(np.sum(parts, axis=0))
    _ORIGINAL["_apply_field_effect"](self, features, modality, caused_by_refs=caused_by_refs, bound_concept_ids=bound_concept_ids)
    for key, label, _sign in pending:
        received = complex(np.vdot(_address(self, key), effect))
        concept_id = stable_id("concept", normalize_label(label))
        old = self.state.concepts[concept_id].attributes if concept_id in self.state.concepts else {}
        lifelong = complex(old.get("stance_sum_real", 0.0), old.get("stance_sum_imag", 0.0)) + received
        recent = RECENT_KEEP * complex(old.get("stance_recent_real", 0.0), old.get("stance_recent_imag", 0.0)) + received
        self.ensure_concept(label, evidence_refs=caused_by_refs, attributes={
            "concept_type": STANCE_TYPE, "proposition_key": key, "semantic_label_preinstalled": False,
            "claim_boundary": "IMPLEMENTED-EXPERIMENTAL",
            "stance_writings": int(old.get("stance_writings", 0)) + 1,
            "stance_sum_real": lifelong.real, "stance_sum_imag": lifelong.imag,
            "stance_size_sum": float(old.get("stance_size_sum", 0.0)) + abs(received),
            "stance_recent_real": recent.real, "stance_recent_imag": recent.imag})


def read_stance(kernel: VerdantKernel) -> dict[str, dict]:
    """proposition key -> what the field holds about it (empty for propositions never claimed)."""
    out = {}
    for concept in kernel.state.concepts.values():
        a = concept.attributes
        if a.get("concept_type") != STANCE_TYPE:
            continue
        n = max(1, int(a["stance_writings"])); total = complex(a["stance_sum_real"], a["stance_sum_imag"])
        recent = complex(a["stance_recent_real"], a["stance_recent_imag"])
        out[a["proposition_key"]] = {
            "writings": int(a["stance_writings"]), "net": abs(total) / n, "tension": (a["stance_size_sum"] - abs(total)) / n,
            "said": a["stance_size_sum"] / n,
            "lifelong_turns": float(np.angle(total) / (2 * np.pi)), "recent_turns": float(np.angle(recent) / (2 * np.pi)),
            "recent_strength": abs(recent)}
    return out


def stance_installed() -> bool:
    return bool(_ORIGINAL)


def install_stance() -> None:
    if _ORIGINAL:
        return
    for name, replacement in (("apply_experience", _stance_apply_experience), ("_concept_binding_effect", _stance_binding_effect),
                              ("_apply_field_effect", _stance_apply_field_effect)):
        _ORIGINAL[name] = getattr(VerdantKernel, name)          # wraps whatever is installed (e.g. the wave sidecar)
        setattr(VerdantKernel, name, replacement)


def uninstall_stance() -> None:
    for name, original in list(_ORIGINAL.items()):
        setattr(VerdantKernel, name, original)
    _ORIGINAL.clear()
