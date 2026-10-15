"""v2.2 evidence reconciliation against actually promoted native Council P/Q.

All observations are explicit controlled external TESTIMONY, never learned
autonomously and never written to the underlying native Verdant VDK.
"""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from verdant_kernel import VerdantKernel, save_checkpoint, load_checkpoint
from verdant_pockets import PocketIntegrityError, cultivate_pocket
from verdant_pockets.composition import CompositionQuery, inspect_composition
from verdant_pockets.evidence_retention import (
    new_ledger, acquire_observation, observation_from_testimony,
)
from verdant_pockets.reconciliation import (
    _hash, start_revision, observe, withdraw, reconcile_state,
    inspect_revision, validate_revision, save_revision, load_revision,
    migrate_v21,
)
from verdant_pockets.research_demo import make_native_teaching_corpus


@pytest.fixture(scope="module")
def earned():
    kernel, family, qid, names, relations = make_native_teaching_corpus(
        include_cross_p_bridge=False,
    )
    assert len(relations) == 9
    state = kernel.snapshot()
    return state, family, qid, names


@pytest.fixture
def case(earned):
    state, family, qid, names = earned
    kernel = VerdantKernel.from_state(state.model_copy(deep=True))
    pocket = cultivate_pocket(kernel, family, q_id=qid, rounds=1)
    query = CompositionQuery(names["r1"], names["s4"], maximum_hops=9)
    return kernel, pocket, names, query, family, qid


def obs(names, fr="r4", to="s1", source_ref="controlled:original-teacher"):
    return observation_from_testimony(
        source=names[fr], target=names[to],
        relation_type="precedes", source_ref=source_ref,
    )


def stage(case):
    kernel, pocket, names, query, family, qid = case
    original = obs(names)
    first = observe(pocket, start_revision(pocket), original)
    return first, _hash(original)


def test_v22_preserves_support_without_dispute(case):
    kernel, pocket, names, query, family, qid = case
    frozen = kernel.fingerprint()
    j, oid = stage(case)
    report = inspect_revision(pocket, j, query)
    assert report["disposition"] == "supported_experimental_composition"
    assert report["conditional_proof"]["witness_external_observation_ids"] == [oid]
    assert len(report["conditional_proof"]["witness_native_relation_ids"]) == 6
    assert report["flat_baseline"]["disposition"] == report["disposition"]
    assert report["historical_positive_proofs"] == []
    assert kernel.fingerprint() == frozen
    assert len(kernel.state.relations) == 9


def test_reverse_claim_suspends_then_withdrawing_challenge_restores(case):
    kernel, pocket, names, query, family, qid = case
    first, oid = stage(case)
    challenger = obs(names,"s1","r4","controlled:challenger")
    opposite = _hash(challenger)
    contested = observe(pocket, first, challenger)
    result = inspect_revision(pocket, contested, query)
    assert result["disposition"] == "suspended_contested_evidence"
    assert result["underlying_composition_disposition"] == "abstain_missing_supported_path"
    assert set(result["reconciliation"]["quarantined_observation_ids"]) == {oid, opposite}
    assert result["suspended_proof_depended_on_observation_ids"] == [oid]
    assert result["historical_positive_proofs"][0]["external_observation_ids"] == [oid]
    assert result["flat_baseline"]["disposition"] == "abstain_missing_supported_path"
    assert result["conditional_proof"]["candidate_composite"] is None
    restored = withdraw(pocket, contested, opposite,
                        source_ref="controlled:challenger", reason="challenge withdrawn by source")
    after = inspect_revision(pocket, restored, query)
    assert after["disposition"] == "supported_experimental_composition"
    assert after["suspended_proof_depended_on_observation_ids"] == []
    assert after["reconciliation"]["withdrawn_observation_ids"] == [opposite]
    assert inspect_revision(pocket, first, query)["disposition"] == "supported_experimental_composition"


def test_withdrawal_stales_only_proofs_that_depended_on_it(case):
    kernel, pocket, names, query, family, qid = case
    original, oid = stage(case)
    withdrawn = withdraw(pocket, original, oid,
                         source_ref="controlled:original-teacher",
                         reason="earlier testimony rescinded")
    blocked = inspect_revision(pocket, withdrawn, query)
    assert blocked["disposition"] == "suspended_withdrawn_evidence"
    assert blocked["suspended_proof_depended_on_observation_ids"] == [oid]
    assert blocked["flat_baseline"]["disposition"] == "abstain_missing_supported_path"
    unrelated_query = CompositionQuery(names["r1"], names["t4"], maximum_hops=9)
    other = inspect_revision(pocket, withdrawn, unrelated_query)
    assert other["disposition"] == "abstain_missing_supported_path"
    assert not other["suspended_proof_depended_on_observation_ids"]


def test_unrelated_new_evidence_does_not_disrupt_valid_witness(case):
    kernel, pocket, names, query, family, qid = case
    initial, oid = stage(case)
    distractor = obs(names, "r2","t2","controlled:unrelated")
    enhanced = observe(pocket, initial, distractor)
    result = inspect_revision(pocket, enhanced, query)
    assert result["disposition"] == "supported_experimental_composition"
    assert result["conditional_proof"]["witness_external_observation_ids"] == [oid]
    assert result["reconciliation"]["eligible_observation_ids"] == sorted([oid, _hash(distractor)])


def test_replacement_restores_without_resurrecting_withdrawn_source(case):
    kernel, pocket, names, query, family, qid = case
    initial, oid = stage(case)
    rescinded = withdraw(pocket, initial, oid, source_ref="controlled:original-teacher",
                         reason="source rescinds earlier statement")
    new = obs(names,source_ref="controlled:independent-replacement")
    replacement = observe(pocket, rescinded, new)
    report = inspect_revision(pocket, replacement, query)
    assert report["disposition"] == "supported_experimental_composition"
    assert report["conditional_proof"]["witness_external_observation_ids"] == [_hash(new)]
    assert oid in report["reconciliation"]["withdrawn_observation_ids"]
    assert report["flat_baseline"]["disposition"] == "supported_experimental_composition"


def test_unsupported_retraction_and_duplicate_source_fail_closed(case):
    kernel, pocket, names, query, family, qid = case
    initial, oid = stage(case)
    with pytest.raises(PocketIntegrityError):
        withdraw(pocket, initial, oid, source_ref="controlled:other-actor",
                 reason="illegitimate unrelated withdrawal")
    with pytest.raises(PocketIntegrityError):
        withdraw(pocket, initial, "forged", source_ref="controlled:original-teacher",
                 reason="invalid observation identity")
    with pytest.raises(PocketIntegrityError):
        observe(pocket, initial, obs(names))
    original = withdraw(pocket, initial, oid, source_ref="controlled:original-teacher",
                        reason="statement revoked")
    with pytest.raises(PocketIntegrityError):
        withdraw(pocket, original, oid, source_ref="controlled:original-teacher",
                 reason="duplicate withdrawal")
    with pytest.raises(PocketIntegrityError):
        observe(pocket, original, obs(names))


@pytest.mark.parametrize("attack", [
    "source", "observation", "record_hash", "head_hash", "sequence",
    "operation", "unsafe_writeback", "unauthorized_withdrawal",
])
def test_tampered_revision_rejected(case, attack):
    kernel, pocket, names, query, family, qid = case
    start, oid = stage(case)
    base = withdraw(pocket, start, oid, source_ref="controlled:original-teacher",
                    reason="controlled source rescission")
    forged = deepcopy(base)
    if attack == "source":
        forged["source"]["canonical_fingerprint"] = "other"
    elif attack == "observation":
        forged["events"][0]["payload"]["observation"]["target"] = names["t1"]
    elif attack == "record_hash":
        forged["events"][0]["record_hash"] = "forged"
    elif attack == "head_hash":
        forged["head_hash"] = "forged"
    elif attack == "sequence":
        forged["events"][0]["sequence"] = 5
    elif attack == "operation":
        forged["events"][0]["operation"] = "promote_to_canonical"
    elif attack == "unsafe_writeback":
        forged["native_writeback"] = True
    else:
        forged["events"][1]["payload"]["source_ref"] = "controlled:fake"
    with pytest.raises(PocketIntegrityError):
        validate_revision(forged,pocket)


def test_v21_migration_preserves_existing_report_without_editing_it(case, tmp_path):
    kernel, pocket, names, query, family, qid = case
    old = acquire_observation(pocket,new_ledger(pocket),obs(names))
    before = json.dumps(old,sort_keys=True)
    migrated = migrate_v21(pocket,old)
    assert json.dumps(old,sort_keys=True) == before
    assert len(migrated["events"]) == 1
    assert inspect_revision(pocket,migrated,query)["disposition"] == "supported_experimental_composition"
    destination = tmp_path / "revision.vpr.json"
    save_revision(destination,migrated,pocket)
    with pytest.raises(FileExistsError):
        save_revision(destination,migrated,pocket)
    restored = load_revision(destination,pocket)
    assert restored == migrated


def test_new_checkpoint_replay_and_source_mismatch_rejected(case,tmp_path):
    kernel, pocket, names, query, family, qid = case
    baseline = kernel.fingerprint()
    initial, oid = stage(case)
    disputed = observe(pocket,initial,obs(names,"s1","r4","controlled:challenger"))
    outcome = inspect_revision(pocket,disputed,query)
    native = tmp_path / "untouched-native.vdk"
    save_checkpoint(native, kernel.snapshot())
    before_bytes = native.read_bytes()
    sidecar = tmp_path / "dispute.vpr.json"
    save_revision(sidecar, disputed,pocket)
    rebuilt = VerdantKernel.from_state(load_checkpoint(native))
    fresh = cultivate_pocket(rebuilt,family,q_id=qid,rounds=1)
    loaded = load_revision(sidecar,fresh)
    assert inspect_revision(fresh,loaded,query) == outcome
    assert native.read_bytes() == before_bytes
    assert kernel.fingerprint() == baseline
    assert len(rebuilt.state.relations) == 9
    altered = deepcopy(pocket)
    altered["canonical_fingerprint"] = "other"
    with pytest.raises(PocketIntegrityError):
        validate_revision(loaded,altered)


def test_contradiction_between_experiment_and_native_is_quarantined(case):
    kernel, pocket, names, query, family, qid = case
    # Local control adds native-evidenced reverse testimony to a genuine
    # source fixture; actual user VDK is not altered.
    reverse = kernel.propose_relation(
        names["s1"], names["r4"], "precedes",
        evidence_refs=kernel.state.structures[family[1]].evidence_refs,
    )
    updated = cultivate_pocket(kernel,family,q_id=qid,rounds=1)
    j = observe(updated, start_revision(updated), obs(names))
    states = reconcile_state(updated,j)
    assert states["quarantined_observation_ids"] == [_hash(obs(names))]
    assert inspect_revision(updated,j,query)["disposition"] == "abstain_missing_supported_path"



def test_disposable_native_controlled_reconciliation_demo_replays_from_v21(case):
    from verdant_pockets.research_reconciliation_demo import run_reconciliation_demo
    report, journal, pocket = run_reconciliation_demo()
    assert report["native_primitive_relations"] == 9
    assert len(journal["events"]) == 6
    assert [x["disposition"] for x in report["stages"]] == [
        "supported_experimental_composition",
        "suspended_contested_evidence",
        "suspended_contested_evidence",
        "supported_experimental_composition",
        "suspended_withdrawn_evidence",
        "supported_experimental_composition",
    ]
    assert report["heldout_reproduced_after_native_checkpoint_reload"]
    assert report["heldout_after_restart"]["disposition"] == "supported_experimental_composition"
    assert report["unrelated_query_disposition"] == "abstain_missing_supported_path"
    assert report["source_authenticity_independently_verified"] is False
    assert report["pocket_advantage_over_flat_graph_demonstrated"] is False
    assert report["no_canonical_writeback"]
    validate_revision(journal,pocket)


def test_cli_can_migrate_existing_v21_as_new_sidecar_and_verify_independently(case,tmp_path,capsys):
    from verdant_pockets.research_reconciliation_demo import main
    from verdant_pockets.evidence_retention import save_ledger

    kernel,pocket,names,query,family,qid = case
    old = acquire_observation(
        pocket,new_ledger(pocket),
        observation_from_testimony(
            source=names["r4"],target=names["s1"],
            relation_type="precedes",
            source_ref="controlled:independent-stage-two-primitive-observation",
        ),
    )
    source=tmp_path/"original-v21.vpel.json"
    save_ledger(source,old,pocket)
    original=source.read_bytes()
    out=tmp_path/"controlled-reconciliation.json"
    newer=tmp_path/"new-revision.vpr.json"
    main(["--from-v21",str(source),"--out",str(out),"--journal",str(newer)])
    assert source.read_bytes()==original
    assert out.exists() and newer.exists()
    capsys.readouterr()
    main(["--verify",str(newer)])
    verify=json.loads(capsys.readouterr().out)
    assert verify["reconciliation_journal_verified"]
    assert verify["event_count"]==6
    assert verify["heldout_disposition"]=="supported_experimental_composition"
    with pytest.raises(SystemExit):
        main(["--from-v21",str(source),"--out",str(out),"--journal",str(newer)])
    assert source.read_bytes()==original
