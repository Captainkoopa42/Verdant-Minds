"""Boundary tests for the opt-in stance sidecar (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import pytest

import sidecar_stance as stance
from run_observer_stance import build
from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import VerdantKernel

STOCK = {name: VerdantKernel.__dict__[name] for name in ("apply_experience", "_concept_binding_effect", "_apply_field_effect")}


def _grow():
    props, commands = build(7)
    keep = {w for p in props[::4] for w in (p["subject"], p["object"])}          # two propositions of each kind, all their lessons
    commands = [c for c in commands if keep & {x.label for x in c.concept_proposals}]
    kernel = VerdantKernel(seed=7, state_dim=128, run_label="stance-test"); pipe = VerdantDevelopmentPipeline()
    for c in commands:
        pipe.advance(kernel, c)
    return kernel


@pytest.fixture
def installed():
    import sidecar_acceleration as sa
    sa.install_long_life_acceleration(); stance.install_stance()
    yield
    stance.uninstall_stance(); sa.uninstall_long_life_acceleration()


def _claims_view(kernel):
    s = kernel.state
    return (sorted((c.claim_id, c.status.value, round(c.net_score, 9)) for c in s.claims.values()),
            sorted((x.contradiction_id, x.preferred_claim_id) for x in s.contradictions.values()), sorted(s.evidence))


def test_claims_engine_sees_exactly_the_same_world(installed):
    with_stance = _grow()
    stance.uninstall_stance()
    stock = _grow()
    assert _claims_view(with_stance) == _claims_view(stock)
    assert with_stance.fingerprint() != stock.fingerprint()          # it is a behaviour change, and says so


def test_deterministic_and_records_only_claimed_propositions(installed):
    a, b = _grow(), _grow()
    assert a.fingerprint() == b.fingerprint()
    held = stance.read_stance(a)
    assert len(held) == 10 and set(held) == {c.claim_key for c in a.state.claims.values()}   # 12 chosen, 2 never claimed
    assert all(v["writings"] >= 1 and v["tension"] >= -1e-12 for v in held.values())


def test_uninstall_restores_stock(installed):
    stance.uninstall_stance()
    assert all(VerdantKernel.__dict__[name] is fn for name, fn in STOCK.items()) and not stance.stance_installed()
