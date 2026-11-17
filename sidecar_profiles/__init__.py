"""Opt-in two-speed profiles: a recent part beside the lifelong one.

Claim boundary: IMPLEMENTED-EXPERIMENTAL. No file under ``verdant_*`` is edited. Installing it
changes behaviour (resonance and the concept records), so fingerprints differ from stock.

Stock: a concept's resonance profile is the running mean of every experience it was in, and
nothing fades it. After n meetings a new one moves it by 1/(n+1), so a thing whose look changes
late in life is recognised slowly, and only by an ever-smaller share.

Here: the stock lifelong profile is kept exactly as it is. Beside it, inside the same
experience (before its transition is fingerprinted), the concept's attributes carry a recent
profile: normalize(RECENT_KEEP * recent + this experience's effect). When resonance compares a
concept with an input, it uses whichever of the two matches the input better. Nothing is thrown
away: the old look is still the lifelong profile; the new look becomes the recent one.
"""
from __future__ import annotations

import numpy as np

from verdant_kernel import VerdantKernel

__all__ = ["install_profiles", "uninstall_profiles", "profiles_installed", "RECENT_KEEP"]

RECENT_KEEP = 0.6
_ORIGINAL: dict[str, object] = {}


def _update_profile(self, concept_id, feature_effect, evidence_refs):
    profile = _ORIGINAL["_update_resonance_profile"](self, concept_id, feature_effect, evidence_refs)
    concept = self.state.concepts[concept_id]; a = concept.attributes
    old = np.asarray(a.get("recent_profile_real", np.zeros(len(feature_effect)))) + 1j * np.asarray(a.get("recent_profile_imag", np.zeros(len(feature_effect))))
    recent = self._normalize_complex(RECENT_KEEP * old + feature_effect)
    self.state.concepts[concept_id] = concept.model_copy(update={"attributes": {
        **a, "recent_profile_real": [float(v) for v in recent.real], "recent_profile_imag": [float(v) for v in recent.imag],
        "recent_profile_keep": RECENT_KEEP, "recent_profile_claim_boundary": "IMPLEMENTED-EXPERIMENTAL"}})
    return profile


def _inspect_resonance(self, features, modality, **kwargs):
    self._profiles_query = self._project_effect(self._validated_feature_array(features), modality)
    try:
        return _ORIGINAL["inspect_resonance"](self, features, modality, **kwargs)
    finally:
        self._profiles_query = None


def _profile_array(self, profile):
    lifelong = _ORIGINAL["_profile_array"](self, profile)
    query = getattr(self, "_profiles_query", None)
    concept = self.state.concepts.get(profile.concept_id)
    if query is None or concept is None or "recent_profile_real" not in concept.attributes:
        return lifelong
    recent = np.asarray(concept.attributes["recent_profile_real"]) + 1j * np.asarray(concept.attributes["recent_profile_imag"])
    return recent if abs(np.vdot(recent, query)) > abs(np.vdot(lifelong, query)) else lifelong


def profiles_installed() -> bool:
    return bool(_ORIGINAL)


def install_profiles() -> None:
    if _ORIGINAL:
        return
    for name, replacement in (("_update_resonance_profile", _update_profile), ("inspect_resonance", _inspect_resonance),
                              ("_profile_array", _profile_array)):
        _ORIGINAL[name] = getattr(VerdantKernel, name)
        setattr(VerdantKernel, name, replacement)


def uninstall_profiles() -> None:
    for name, original in list(_ORIGINAL.items()):
        setattr(VerdantKernel, name, original)
    _ORIGINAL.clear()
