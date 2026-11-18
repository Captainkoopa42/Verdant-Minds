"""sidecar_reader: words seen separately; the field is untouched, and words always met together can be told apart."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "curriculum_packs")]
from generate_controls_pack_v0 import text_features  # noqa: E402
from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ConceptProposal, ExperienceCommand, VerdantKernel  # noqa: E402

import sidecar_reader  # noqa: E402
from sidecar_looks import imagined_look, learn_shares, reading  # noqa: E402

FAMILIES = (("alba", "eput"), ("cind", "doro"))


def _life(reader: bool):
    k = VerdantKernel(seed=3, state_dim=64, run_label="reader"); pipe = VerdantDevelopmentPipeline()
    if reader:
        sidecar_reader.install_reader()
    try:
        for n in range(4):
            for fam in FAMILIES:
                text = f"the {fam[0]} beside the {fam[1]} {'x' * n}"
                c = ExperienceCommand(event_key=f"t{n}{fam[0]}", source_ref="reader-test", modality="text",
                                      feature_vector=text_features(text, 64), payload_sha256=hashlib.sha256(text.encode()).hexdigest(),
                                      concept_proposals=[ConceptProposal(label=w) for w in fam], metadata={"context_id": "c"})
                pipe.advance(k, sidecar_reader.attach(c, text) if reader else c)
    finally:
        sidecar_reader.uninstall_reader()
    return k


def test_the_reader_leaves_the_field_and_learning_exactly_stock():
    a, b = _life(False), _life(True)
    assert a.state.field.history == b.state.field.history
    assert a.state.resonance_profiles == b.state.resonance_profiles
    assert {k: v.strength for k, v in a.state.plasticity_associations.items()} == {k: v.strength for k, v in b.state.plasticity_associations.items()}


def test_words_always_met_together_are_told_apart_by_the_reader():
    k = _life(True); ids = {c.label: cid for cid, c in k.state.concepts.items()}
    looks = sidecar_reader.word_shares(k, 64)
    assert not np.allclose(looks.share[ids["alba"]], looks.share[ids["eput"]])
    assert np.array_equal(looks.share[ids["alba"]], sidecar_reader._counts(" alba ", 64))
    assert k.state.concepts[ids["alba"]].attributes["look::reading"]["provenance"].startswith("OBSERVED")
    # imagine "the cind beside the eput", never read: the reader's looks get far closer than regression shares
    key = "t2alba"; truth = np.array(text_features("the cind beside the eput xx", 64))
    def closeness(sh):
        f, _m = sh if isinstance(sh, tuple) else imagined_look(k, sh, key, "alba", "cind")
        f = np.asarray(f); return float(f @ truth / (np.linalg.norm(f) * np.linalg.norm(truth)))
    with_words = closeness(looks)                        # word looks alone: boundary patterns belong to neither word
    regression = closeness(learn_shares(k, reading(64)))
    reread = closeness(sidecar_reader.reread_look(k, key, "alba", "cind"))
    assert np.array_equal(sidecar_reader.organ("the alba beside", 64), text_features("the alba beside", 64))
    assert reread > 1 - 1e-9 and reread > max(with_words, regression)
