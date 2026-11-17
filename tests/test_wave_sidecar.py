"""Boundary tests for the opt-in wave sidecar (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib
import inspect

import pytest

import sidecar_wave as wave
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
from verdant_kernel.models import RelationProposal

DIM = 64
_STOCK = inspect.getsource(VerdantKernel.inspect_resonance)
_STOCK_BIND = inspect.getsource(VerdantKernel._concept_binding_effect)


def _cmd(n, a, b):
    vec = [0.0] * DIM; vec[n % DIM] = 1.0
    return ExperienceCommand(event_key=f"wave-{n}", source_ref="wave-test", modality="text", feature_vector=vec,
                             payload_sha256=hashlib.sha256(f"{n}".encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=a), ConceptProposal(label=b)],
                             relation_proposals=[RelationProposal(source_label=a, target_label=b, relation_type="feeds")],
                             metadata={"context_id": f"c{n % 2}"})


def _run():
    kernel = VerdantKernel(seed=3, state_dim=DIM, run_label="wave-test"); pipe = VerdantDevelopmentPipeline()
    pairs = [(f"s{i}", f"t{i}") for i in range(6)]
    for n in range(18):
        pipe.advance(kernel, _cmd(n, *pairs[n % 6]))
    return kernel


@pytest.fixture
def installed():
    wave.install_wave()
    yield
    wave.uninstall_wave()


def test_stock_methods_have_not_drifted():
    assert hashlib.sha256(_STOCK.encode()).hexdigest() == wave.STOCK_INSPECT_RESONANCE_SHA256
    assert hashlib.sha256(_STOCK_BIND.encode()).hexdigest() == wave.STOCK_BINDING_EFFECT_SHA256


def test_direction_is_in_the_field_only_with_the_wave(installed):
    kernel = _run(); relations = list(kernel.state.relations.values())
    assert relations and all(wave.field_direction(kernel, r.source_concept_id, r.target_concept_id)[0] > 0.15 for r in relations)
    assert all(wave.field_direction(kernel, r.target_concept_id, r.source_concept_id)[0] < -0.15 for r in relations)
    wave.uninstall_wave()
    stock = _run()
    turns = [abs(wave.field_direction(stock, r.source_concept_id, r.target_concept_id)[0]) for r in stock.state.relations.values()]
    assert max(turns) < 0.15          # stock field holds no quarter turn between source and target


def test_wave_is_deterministic_and_keeps_semantic_records(installed):
    a, b = _run(), _run()
    assert a.fingerprint() == b.fingerprint()
    wave.uninstall_wave()
    stock = _run()
    assert sorted(a.state.evidence) == sorted(stock.state.evidence) and sorted(a.state.concepts) == sorted(stock.state.concepts)
    assert sorted(a.state.relations) == sorted(stock.state.relations)
    assert a.fingerprint() != stock.fingerprint()      # it is a behaviour change, and says so


def test_context_alone_cannot_outscore_a_tenth(installed):
    kernel = _run()
    report = kernel.inspect_resonance([0.0] * (DIM - 1) + [1.0], "text", top_k=12)   # a feature no lesson used
    assert all(c.score <= 0.1 + 1e-9 or c.contribution.profile_alignment > 0 for c in report.candidates)


def test_uninstall_restores_stock(installed):
    wave.uninstall_wave()
    assert inspect.getsource(VerdantKernel.inspect_resonance) == _STOCK and not wave.wave_installed()
