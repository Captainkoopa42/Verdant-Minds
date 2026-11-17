"""Opt-in fingerprint accelerator: byte-exact, identity-checked, no authority."""
from __future__ import annotations

import hashlib

import pytest

import sidecar_acceleration as acceleration
from sidecar_acceleration import fingerprint_cache
from sidecar_acceleration.fingerprint_cache import cached_state_fingerprint
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import (
    EvidenceKind,
    ExperienceCommand,
    RelationProposal,
    VerdantKernel,
)
from verdant_kernel.models import FieldFrame, KernelState, PlasticityEvent, ResonanceEvent


def _command(index: int) -> ExperienceCommand:
    left, right = f"n{index % 7}", f"n{(index % 7) + 1}"
    key = f"accelerator:{index}:{left}:{right}"
    return ExperienceCommand(
        event_key=key,
        source_ref="accelerator:test",
        modality="text",
        payload_sha256=hashlib.sha256(key.encode("utf-8")).hexdigest(),
        feature_vector=(1.0, 0.25 * (index % 4), 0.5),
        concept_labels=(left, right),
        relation_proposals=(
            RelationProposal(
                source_label=left,
                target_label=right,
                relation_type="linked",
                directed=False,
                weight=0.8,
                confidence=1.0,
            ),
        ),
        semantic_evidence_kind=EvidenceKind.TESTIMONY,
        semantic_evidence_details={"accelerator_test": True},
        metadata={"context_id": f"context:{index % 2}"},
    )


def _grown_kernel(cycles: int = 12) -> VerdantKernel:
    kernel = VerdantKernel(seed=4107, state_dim=16, run_label="accelerator-test")
    pipeline = VerdantDevelopmentPipeline()
    for index in range(cycles):
        pipeline.advance(kernel, _command(index))
    return kernel


@pytest.fixture()
def reference_methods():
    """Guarantee the reference kernel methods regardless of how pytest was run."""
    was_installed = acceleration.fingerprint_cache_installed()
    acceleration.uninstall_fingerprint_cache()
    yield
    if was_installed:
        acceleration.install_fingerprint_cache()


def test_accelerated_digest_equals_reference_for_both_fingerprints(reference_methods):
    kernel = _grown_kernel()
    cache: dict = {}
    for include in (True, False):
        reference = kernel.state.fingerprint(include_transitions=include)
        first = cached_state_fingerprint(kernel.state, include_transitions=include, cache=cache)
        second = cached_state_fingerprint(kernel.state, include_transitions=include, cache=cache)
        assert first == second == reference
    assert cache, "The developmental state should contain reusable immutable records."


def test_heavy_history_records_are_proven_immutable_and_reused(reference_methods):
    for cls in (FieldFrame, ResonanceEvent, PlasticityEvent):
        assert fingerprint_cache._class_cacheable(cls)
    kernel = _grown_kernel()
    cache: dict = {}
    cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)
    cached_ids = set(cache)
    assert {id(item) for item in kernel.state.resonance_events} <= cached_ids
    assert {id(item) for item in kernel.state.field.history} <= cached_ids


def test_records_with_mutable_payloads_are_never_cached(reference_methods):
    kernel = _grown_kernel()
    cache: dict = {}
    cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)
    # Evidence carries a free-form details dict, so it always takes the
    # reference encoding path.
    assert not ({id(item) for item in kernel.state.evidence.values()} & set(cache))
    evidence_id = sorted(kernel.state.evidence)[0]
    kernel.state.evidence[evidence_id].details["tampered_in_place"] = True
    assert cached_state_fingerprint(
        kernel.state, include_transitions=True, cache=cache
    ) == kernel.state.fingerprint()


def test_replacing_a_cached_record_changes_the_digest_exactly_as_reference(reference_methods):
    kernel = _grown_kernel()
    cache: dict = {}
    before = cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)
    original = kernel.state.resonance_events[0]
    kernel.state.resonance_events[0] = original.model_copy(
        update={"committed_cycle": original.committed_cycle + 1}
    )
    after = cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)
    assert after != before
    assert after == kernel.state.fingerprint()


def test_mutable_scalars_and_policies_are_always_reencoded(reference_methods):
    kernel = _grown_kernel()
    cache: dict = {}
    before = cached_state_fingerprint(kernel.state, include_transitions=False, cache=cache)
    kernel.state.cycle += 1
    kernel.state.field.real[0] += 0.125
    kernel.update_plasticity_policy(decay_rate=0.05)
    after = cached_state_fingerprint(kernel.state, include_transitions=False, cache=cache)
    assert after != before
    assert after == kernel.state.fingerprint(include_transitions=False)


def test_stale_cache_from_another_state_object_cannot_leak(reference_methods):
    kernel = _grown_kernel()
    cache: dict = {}
    cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)
    copied = kernel.snapshot()
    copied.resonance_events[0] = copied.resonance_events[0].model_copy(
        update={"committed_cycle": copied.resonance_events[0].committed_cycle + 5}
    )
    # Reusing the first state's cache on a different state must still be exact,
    # because every entry is checked by object identity.
    assert cached_state_fingerprint(
        copied, include_transitions=True, cache=cache
    ) == copied.fingerprint()


def test_install_is_explicit_reversible_and_digest_preserving(reference_methods):
    kernel = _grown_kernel()
    reference_full = kernel.fingerprint()
    reference_semantic = kernel.semantic_fingerprint()
    assert not acceleration.fingerprint_cache_installed()
    acceleration.install_fingerprint_cache()
    try:
        assert acceleration.fingerprint_cache_installed()
        assert kernel.fingerprint() == reference_full
        assert kernel.semantic_fingerprint() == reference_semantic
        # A staged heartbeat replaces kernel.state; the per-kernel cache must
        # follow the new state object rather than trust the old one.
        VerdantDevelopmentPipeline().advance(kernel, _command(99))
        assert kernel.fingerprint() == kernel.state.fingerprint()
        assert kernel._fingerprint_cache_owner is kernel.state
    finally:
        acceleration.uninstall_fingerprint_cache()
    assert not acceleration.fingerprint_cache_installed()
    assert kernel.fingerprint() == kernel.state.fingerprint()


def test_accelerated_run_reaches_the_identical_final_state(reference_methods):
    reference = _grown_kernel(cycles=10).state.fingerprint()
    acceleration.install_fingerprint_cache()
    try:
        accelerated = _grown_kernel(cycles=10).state.fingerprint()
    finally:
        acceleration.uninstall_fingerprint_cache()
    assert accelerated == reference


def test_verify_mode_raises_on_any_divergence(reference_methods, monkeypatch):
    kernel = _grown_kernel(cycles=4)
    monkeypatch.setenv("VERDANT_FINGERPRINT_VERIFY", "1")
    cache: dict = {}
    assert cached_state_fingerprint(
        kernel.state, include_transitions=True, cache=cache
    ) == kernel.state.fingerprint()
    # Forge one cached entry while keeping its identity guard intact.
    target = kernel.state.resonance_events[0]
    cache[id(target)] = (target, b'{"forged":true}')
    with pytest.raises(fingerprint_cache.FingerprintCacheMismatch):
        cached_state_fingerprint(kernel.state, include_transitions=True, cache=cache)


def test_kernel_state_itself_is_plainly_serialized(reference_methods):
    # The accelerator assumes KernelState dumps exactly its declared fields.
    assert fingerprint_cache._has_plain_serialization(KernelState)
