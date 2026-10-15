"""Lifecycle pilot with real native P/Q, structural and corruption controls."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from test_hierarchy_phase import hierarchy_fixture, fresh
from test_cognitive_pocket_cultivation import _typed_native_sources
from verdant_kernel import RelationStatus
from verdant_pockets import cultivate_pocket, PocketIntegrityError
from verdant_pockets.dynamics import simulate, paired_cohort
from verdant_pockets.lifecycle import (
    build_lifecycle, daughter_partitions, compression_receipt,
    save_lifecycle, load_lifecycle, validate_lifecycle,
)


@pytest.fixture
def native_pocket(hierarchy_fixture):
    kernel, family, qid, _, _, _ = fresh(hierarchy_fixture)
    _typed_native_sources(kernel, family, mixed=True)
    before = kernel.fingerprint()
    pocket = cultivate_pocket(kernel, family, q_id=qid)
    assert kernel.fingerprint() == before
    return kernel, family, pocket


def test_local_stimulus_reaches_other_ps_only_with_analogical_channel(native_pocket):
    kernel, family, pocket = native_pocket
    sid = family[0]
    baseline = simulate(pocket, source_p_id=sid, mode="native_only", rounds=8)
    treatment = simulate(pocket, source_p_id=sid, mode="role_aligned", rounds=8)
    assert baseline["final_non_source_active"] == 0
    assert treatment["final_non_source_active"] > 0
    assert all(t["active_non_source_p"] == 0 for t in baseline["frames"])
    assert any(
        edge["channel"] == "hypothetical_role" and not edge["canonical_evidence_asserted"]
        for frame in treatment["frames"] for edge in frame["transfer_attempts"]
    )
    assert kernel.fingerprint() == pocket["canonical_fingerprint"]


def test_native_source_role_scramble_and_null_controls(native_pocket):
    _kernel, family, pocket = native_pocket
    sid = family[0]
    null = simulate(pocket, source_p_id=sid, mode="null", rounds=5)
    assert all(sum(row["activation"].values()) == 0 for row in null["frames"])
    aligned = simulate(pocket, source_p_id=sid, mode="role_aligned", rounds=5)
    scramble = simulate(pocket, source_p_id=sid, mode="role_scrambled", rounds=5)
    assert len(aligned["links"]) == len(scramble["links"])
    assert aligned["links"] != scramble["links"]
    assert any(
        aligned["frames"][i]["activation"] != scramble["frames"][i]["activation"]
        for i in range(1, 6)
    )
    assert all(row["input_by_channel"].get("hypothetical_role", 0) == 0
               for row in null["frames"][1:])


def test_no_cross_p_evidence_in_original_like_earned_p_q(native_pocket):
    _kernel, family, pocket = native_pocket
    cohort = paired_cohort(pocket, rounds=6)
    assert len(cohort["source_p_ids"]) == 3
    assert len(cohort["trials"]) == len(cohort["arms"]) * len(family)
    assert not pocket["evidenced_cross_p_relations"]
    assert not pocket["evidenced_cross_p_walks"]
    assert all(e["is_evidenced_compositional_gain"] is False for e in cohort["effects"])
    assert any(e["measurable_effect"] for e in cohort["effects"] if e["arm"] == "role_aligned")
    assert all(not e["measurable_effect"] for e in cohort["effects"] if e["arm"] == "native_only")


def test_matching_canonical_directed_bridge_is_distinct_from_role_match(native_pocket):
    kernel, family, _ = native_pocket
    labels = {c.normalized_label: cid for cid, c in kernel.state.concepts.items()}
    kernel.propose_relation(labels["a4"], labels["b1"], "next_stage",
        evidence_refs=kernel.state.structures[family[0]].evidence_refs,
        status=RelationStatus.SUPPORTED,
        weight=1.0,
    )
    pocket = cultivate_pocket(kernel, family)
    forward = simulate(pocket, source_p_id=family[0], mode="canonical_only", rounds=10)
    reverse = simulate(pocket, source_p_id=family[0], mode="canonical_reversed", rounds=10)
    assert any(e["kind"] == "evidenced_cross_p" for e in forward["links"])
    assert any(e["kind"] == "evidenced_cross_p" for e in reverse["links"])
    assert any(
        e["source"] != f["source"] and e["target"] != f["target"]
        for e, f in zip(
            [x for x in forward["links"] if x["kind"] == "evidenced_cross_p"],
            [x for x in reverse["links"] if x["kind"] == "evidenced_cross_p"],
        )
    )
    assert forward["frames"] != reverse["frames"]
    assert all(not e["canonical_evidence_asserted"] for fr in forward["frames"]
               for e in fr["transfer_attempts"] if e["channel"] == "hypothetical_role")


def test_partitions_conserve_every_p_and_concept(native_pocket):
    _kernel, _family, pocket = native_pocket
    cohort = paired_cohort(pocket, rounds=3)
    d = daughter_partitions(pocket, cohort)
    assert len(d["daughters"]) == 2
    assert sorted(pid for part in d["daughters"] for pid in part["p_ids"]) == sorted(pocket["p_ids"])
    assert sorted(cid for part in d["daughters"] for cid in part["concept_ids"]) == sorted(
        c["id"] for c in pocket["concepts"]
    )
    assert any(b["hypothetical_only"] for b in d["boundary_links"])
    assert all(b["kind"] != "evidenced_cross_p" for b in d["boundary_links"])


def test_chain_and_lossless_compression_and_roundtrip(native_pocket, tmp_path):
    kernel, family, pocket = native_pocket
    original = kernel.fingerprint()
    lifecycle = build_lifecycle(pocket, rounds=3)
    validate_lifecycle(lifecycle)
    assert lifecycle["compression"]["lossless_exact_reconstruction"]
    assert lifecycle["compression"]["compressed_bytes"] < lifecycle["compression"]["original_bytes"]
    assert not lifecycle["compression"]["learned_representation_compression"]
    assert len(lifecycle["history"]) == len(lifecycle["matched_cohort"]["arms"]) * len(family)
    assert lifecycle["head_hash"] == lifecycle["history"][-1]["record_hash"]
    dest = tmp_path / "sidecar.json"
    save_lifecycle(dest, lifecycle)
    restored = load_lifecycle(dest)
    assert lifecycle == restored
    assert kernel.fingerprint() == original
    with pytest.raises(FileExistsError):
        save_lifecycle(dest, lifecycle)
    assert dest.read_bytes() == json.dumps(
        lifecycle, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


@pytest.mark.parametrize("attack", [
    "activation",
    "history",
    "daughter",
    "compression",
    "canonical_fingerprint",
    "relation_evidence",
])
def test_sidecar_tampering_rejected(native_pocket, attack):
    _, _, pocket = native_pocket
    orig = build_lifecycle(pocket, rounds=2)
    altered = deepcopy(orig)
    if attack == "activation":
        altered["matched_cohort"]["trials"][0]["frames"][1]["activation"][
            next(iter(altered["matched_cohort"]["trials"][0]["frames"][1]["activation"]))
        ] = 0.777
    elif attack == "history":
        altered["history"][0]["prev_hash"] = "forged"
    elif attack == "daughter":
        altered["experimental_daughters"]["daughters"][0]["concept_ids"] = []
    elif attack == "compression":
        altered["compression"]["original_bytes"] += 1
    elif attack == "canonical_fingerprint":
        altered["parent_pocket"]["canonical_fingerprint"] = "forged"
    else:
        altered["parent_pocket"]["current_member_relations"][0]["evidence_refs"] = []
    with pytest.raises(PocketIntegrityError):
        validate_lifecycle(altered)


def test_invalid_controls_and_missing_source_rejected(native_pocket):
    _, family, pocket = native_pocket
    for arm in ("unsupported", "canonically_commit", ""):
        with pytest.raises(PocketIntegrityError):
            simulate(pocket, source_p_id=family[0], mode=arm)
    with pytest.raises(PocketIntegrityError):
        simulate(pocket, source_p_id="forged", mode="role_aligned")
    with pytest.raises(PocketIntegrityError):
        simulate(pocket, source_p_id=family[0], mode="role_aligned", rounds=999)
    with pytest.raises(PocketIntegrityError):
        simulate(pocket, source_p_id=family[0], mode="role_aligned", maximum_links_per_p=99)


def test_replay_exactly_deterministic(native_pocket):
    _, _, pocket = native_pocket
    a = build_lifecycle(pocket, rounds=4)
    b = build_lifecycle(pocket, rounds=4)
    assert a == b
    assert a["lifecycle_id"] == b["lifecycle_id"]
