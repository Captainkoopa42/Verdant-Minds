"""Boundary tests for the opt-in two-speed profile sidecar (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib, json

import numpy as np

import sidecar_profiles as profiles
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel

STOCK = {n: VerdantKernel.__dict__[n] for n in ("_update_resonance_profile", "inspect_resonance", "_profile_array")}


def _grow():
    r = np.random.default_rng(1); kernel = VerdantKernel(seed=1, state_dim=32, run_label="profiles-test"); pipe = VerdantDevelopmentPipeline()
    for n in range(24):
        f = [float(v) for v in r.standard_normal(32)]
        pipe.advance(kernel, ExperienceCommand(event_key=f"p{n}", source_ref="profiles-test", modality="visual", feature_vector=f,
                     payload_sha256=hashlib.sha256(json.dumps(f).encode()).hexdigest(), concept_proposals=[ConceptProposal(label=f"t{n % 4}")]))
    return kernel


def test_lifelong_profiles_are_exactly_stock_and_run_is_deterministic():
    stock = _grow(); profiles.install_profiles()
    try:
        a, b = _grow(), _grow()
    finally:
        profiles.uninstall_profiles()
    assert a.fingerprint() == b.fingerprint() and a.fingerprint() != stock.fingerprint()
    assert {k: (v.real, v.imag, v.exposure_count) for k, v in a.state.resonance_profiles.items()} == \
           {k: (v.real, v.imag, v.exposure_count) for k, v in stock.state.resonance_profiles.items()}
    assert all("recent_profile_real" in c.attributes for c in a.state.concepts.values())


def test_uninstall_restores_stock():
    profiles.install_profiles(); profiles.uninstall_profiles()
    assert all(VerdantKernel.__dict__[n] is fn for n, fn in STOCK.items()) and not profiles.profiles_installed()
