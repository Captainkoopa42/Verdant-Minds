"""The long-life accelerators must be invisible: same digests, same isolation, no engine edits."""
from __future__ import annotations

import hashlib
import inspect

import pytest

import sidecar_acceleration as sa
from sidecar_acceleration.structural_copy import KERNEL_INIT_SHA256, KERNEL_SNAPSHOT_SHA256, structural_copy
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel

DIM = 32
_STOCK_INIT = inspect.getsource(VerdantKernel.__init__)
_STOCK_SNAPSHOT = inspect.getsource(VerdantKernel.snapshot)


def _cmd(n):
    labels = [(f"a{n % 5}", f"b{n % 5}", f"c{n % 5}"), (f"d{n % 3}", f"e{n % 3}", f"f{n % 3}")][n % 2]
    vec = [0.0] * DIM; vec[n % DIM] = 1.0
    return ExperienceCommand(event_key=f"long-life-{n}", source_ref="long-life-test", modality="text", feature_vector=vec,
                             payload_sha256=hashlib.sha256(f"{n}".encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=x) for x in labels], metadata={"context_id": f"c{n % 3}"})


def _run(n=18):
    kernel = VerdantKernel(seed=5, state_dim=DIM, run_label="long-life-test"); pipe = VerdantDevelopmentPipeline()
    trail = []
    for i in range(n):
        pipe.advance(kernel, _cmd(i)); trail.append(kernel.fingerprint())
    return kernel, trail


@pytest.fixture
def long_life(monkeypatch):
    monkeypatch.setenv("VERDANT_FINGERPRINT_VERIFY", "1")
    sa.install_long_life_acceleration()
    yield
    sa.uninstall_long_life_acceleration()


def test_stock_constructor_and_snapshot_have_not_drifted():
    assert hashlib.sha256(_STOCK_INIT.encode()).hexdigest() == KERNEL_INIT_SHA256
    assert hashlib.sha256(_STOCK_SNAPSHOT.encode()).hexdigest() == KERNEL_SNAPSHOT_SHA256


def test_every_beat_has_the_reference_fingerprint(long_life):
    _, fast = _run()
    sa.uninstall_long_life_acceleration()
    _, reference = _run()
    assert fast == reference


def test_structural_fingerprints_match_reference(long_life):
    kernel, _ = _run(10)
    names = sorted(n for n in vars(VerdantKernel) if n.endswith("_structural_fingerprint"))
    fast = {n: getattr(kernel, n)() for n in names}
    state = kernel.state
    sa.uninstall_long_life_acceleration()
    plain = VerdantKernel.from_state(state)
    assert len(names) >= 10 and fast == {n: getattr(plain, n)() for n in names}


def test_copy_is_isolated_and_superseded_state_is_untouched(long_life):
    kernel, _ = _run(8)
    old = kernel.state; before = old.fingerprint(); copy = structural_copy(old)
    assert copy is not old and copy.fingerprint() == before
    assert copy.evidence is not old.evidence and copy.plasticity_events is not old.plasticity_events
    VerdantDevelopmentPipeline().advance(kernel, _cmd(99))
    assert kernel.state is not old and old.fingerprint() == before and copy.fingerprint() == before


def test_uninstall_restores_stock_methods(long_life):
    sa.uninstall_long_life_acceleration()
    assert inspect.getsource(VerdantKernel.__init__) == _STOCK_INIT
    assert not sa.long_life_acceleration_installed() and not sa.fingerprint_cache_installed()
