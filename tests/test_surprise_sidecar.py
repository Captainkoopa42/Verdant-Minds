"""Boundary tests for the opt-in surprise sidecar (IMPLEMENTED-EXPERIMENTAL)."""
from __future__ import annotations

import hashlib

from verdant_development import VerdantDevelopmentPipeline
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel
from verdant_plasticity import VerdantPlasticityPipeline
from sidecar_surprise import SurpriseDevelopmentPipeline, surprise_plasticity

DIM = 64


def _features(labels):
    vec = [0.0] * DIM
    for label in labels:
        for j in range(6):
            vec[int(hashlib.sha256(f"{label}:{j}".encode()).hexdigest(), 16) % DIM] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    return [v / norm for v in vec]


def _cmd(n, labels):
    return ExperienceCommand(event_key=f"surprise-{n}", source_ref="surprise-test", modality="text", feature_vector=_features(labels),
                             payload_sha256=hashlib.sha256(f"{n}".encode()).hexdigest(),
                             concept_proposals=[ConceptProposal(label=x) for x in labels], metadata={"context_id": f"c{n % 3}"})


FAMILIES = [tuple(f"{chr(97 + i)}{j}" for j in range(3)) for i in range(8)]


def _surprise_pipe():
    return SurpriseDevelopmentPipeline(plasticity=surprise_plasticity(VerdantPlasticityPipeline)())


def _run(pipe, rounds=4):
    kernel = VerdantKernel(seed=9, state_dim=DIM, run_label="surprise-test")
    for n in range(rounds * len(FAMILIES)):
        pipe.advance(kernel, _cmd(n, FAMILIES[n % len(FAMILIES)]))
    return kernel


def test_surprise_starts_at_one_and_falls_with_repetition():
    pipe = _surprise_pipe(); _run(pipe)
    values = [v for _, v in pipe.surprise_log]; n = len(FAMILIES)
    assert values[0] == 1.0 and all(v == 1.0 for v in values[:2])
    assert sum(values[-n:]) / n < sum(values[:n]) / n            # the last round is less surprising than the first
    assert all(0.0 <= v <= 1.0 for v in values)


def test_bonds_are_never_weaker_than_stock_and_records_match():
    stock = _run(VerdantDevelopmentPipeline()); surprised = _run(_surprise_pipe())
    assert sorted(stock.state.evidence) == sorted(surprised.state.evidence)
    assert sorted(stock.state.concepts) == sorted(surprised.state.concepts)
    common = set(stock.state.plasticity_associations) & set(surprised.state.plasticity_associations)
    assert common and set(stock.state.plasticity_associations) <= set(surprised.state.plasticity_associations)
    family_bonds = [a for a in common if len({stock.state.concepts[c].label[0] for c in stock.state.plasticity_associations[a].concept_ids}) == 1]
    assert family_bonds and all(surprised.state.plasticity_associations[a].strength >= stock.state.plasticity_associations[a].strength - 1e-9
                                for a in family_bonds)


def test_surprise_is_deterministic_and_recorded_in_state():
    a, b = _run(_surprise_pipe()), _run(_surprise_pipe())
    assert a.fingerprint() == b.fingerprint()
    tagged = [e for e in a.state.workspace_cycle_events for x in e.report.assessments
              if x.candidate.metadata.get("prediction_error_source") == "sidecar_surprise.measured"]
    assert len(tagged) == len(a.state.workspace_cycle_events)
