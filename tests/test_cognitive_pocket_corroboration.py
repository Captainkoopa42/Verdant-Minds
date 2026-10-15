"""V2.3 controlled P/Q provenance tests, adversarial lineage and flat controls."""
from __future__ import annotations

from copy import deepcopy
import json

import pytest

from verdant_kernel import VerdantKernel,save_checkpoint,load_checkpoint
from verdant_pockets import cultivate_pocket,PocketIntegrityError
from verdant_pockets.composition import CompositionQuery
from verdant_pockets.research_demo import make_native_teaching_corpus
from verdant_pockets.evidence_retention import observation_from_testimony
from verdant_pockets.reconciliation import start_revision, observe as v22_observe, withdraw as v22_withdraw
from verdant_pockets.corroboration import (
    _hash,new_provenance,attest,withdraw,status_snapshot,inspect_corroboration,
    save_provenance,load_provenance,migrate_v22,validate_provenance,
)


@pytest.fixture(scope="module")
def source_fixture():
    kernel, family, qid, names, relations = make_native_teaching_corpus(include_cross_p_bridge=False)
    assert len(relations)==9
    return kernel.snapshot(),family,qid,names


@pytest.fixture
def case(source_fixture):
    state,ps,qid,names=source_fixture
    kernel=VerdantKernel.from_state(state.model_copy(deep=True))
    pocket=cultivate_pocket(kernel,ps,q_id=qid,rounds=1)
    return kernel,pocket,names,ps,qid


def manifest():
    return {
        "origin-alpha":{"lineage_family":"single-observation-1","description":"controlled independent witness alpha"},
        "alpha-copy":{"lineage_family":"republication-channel-2","description":"controlled repost of origin alpha"},
        "origin-beta":{"lineage_family":"single-observation-2","description":"controlled independent witness beta"},
        "origin-gamma":{"lineage_family":"single-observation-3","description":"controlled opposing witness gamma"},
        "origin-delta":{"lineage_family":"single-observation-4","description":"controlled replacement witness delta"},
        "noise-root":{"lineage_family":"single-observation-5","description":"unrelated evidence witness family"},
    }


def observed(names,sid="origin-alpha",a="r4",b="s1"):
    return observation_from_testimony(
        source=names[a],target=names[b],relation_type="precedes",source_ref=sid,
    )


def question(names):
    return CompositionQuery(names["r1"],names["s4"],maximum_hops=9)


def testified(case):
    kernel,pocket,names,ps,qid=case
    first=observed(names)
    journal=attest(pocket,new_provenance(pocket,manifest()),first,source_id="origin-alpha")
    return journal,_hash(first)


def test_single_source_provisional_no_invented_canonical_proof(case):
    kernel,pocket,names,ps,qid=case
    before=kernel.fingerprint()
    journal,alpha=testified(case)
    result=inspect_corroboration(pocket,journal,question(names))
    assert result["disposition"]=="abstain_missing_supported_path"
    assert result["reconciliation"]["status_by_observation_id"][alpha]=="provisional_single_lineage"
    assert result["reconciliation"]["corroborated_claims"]==[]
    assert kernel.fingerprint()==before
    assert len(kernel.state.relations)==9


def test_republisher_inherits_parent_lineage_despite_false_independent_manifest(case):
    _,pocket,names,_,_=case
    journal,alpha=testified(case)
    copy=observed(names,"alpha-copy")
    journal=attest(pocket,journal,copy,source_id="alpha-copy",derived_from=alpha)
    state=status_snapshot(pocket,journal)
    assert state["counts"]["provisional_single_lineage"]==2
    assert state["counts"]["corroborated_experimental"]==0
    assert inspect_corroboration(pocket,journal,question(names))["disposition"]=="abstain_missing_supported_path"
    with pytest.raises(PocketIntegrityError):
        attest(pocket,journal,observed(names,"origin-beta",a="r3"),source_id="origin-beta",derived_from=alpha)


def test_second_registered_origin_corrob_and_proof_retains_both_sources(case):
    kernel,pocket,names,ps,qid=case
    journal,alpha=testified(case)
    beta=observed(names,"origin-beta")
    journal=attest(pocket,journal,beta,source_id="origin-beta")
    report=inspect_corroboration(pocket,journal,question(names))
    assert report["disposition"]=="supported_experimental_composition"
    assert report["flat_baseline"]["disposition"]==report["disposition"]
    assert len(report["support_lineage_provenance"])==1
    lineage=report["support_lineage_provenance"][0]
    assert lineage["supporting_observation_ids"]==sorted([alpha,_hash(beta)])
    assert lineage["lineage_families"]==["single-observation-1","single-observation-2"]
    assert len(report["proof"]["witness_native_relation_ids"])==6
    assert len(report["proof"]["witness_external_observation_ids"])==1
    assert report["corroboration_not_source_authentication"] is True
    assert report["no_native_writeback"] is True


def test_one_reverse_attestation_quarantines_all_fwd_claims(case):
    _,pocket,names,_,_=case
    journal,_=testified(case)
    journal=attest(pocket,journal,observed(names,"origin-beta"),source_id="origin-beta")
    contrary=observed(names,"origin-gamma","s1","r4")
    journal=attest(pocket,journal,contrary,source_id="origin-gamma")
    state=status_snapshot(pocket,journal)
    assert state["counts"]["disputed_quarantined"]==3
    assert inspect_corroboration(pocket,journal,question(names))["disposition"]=="abstain_missing_supported_path"
    restored=withdraw(pocket,journal,_hash(contrary),source_id="origin-gamma",
                      reason="challenger retracts testimony")
    assert inspect_corroboration(pocket,restored,question(names))["disposition"]=="supported_experimental_composition"


def test_withdrawal_loses_quorum_then_new_origin_restores_it(case):
    _,pocket,names,_,_=case
    journal,alpha=testified(case)
    beta=observed(names,"origin-beta")
    journal=attest(pocket,journal,beta,source_id="origin-beta")
    journal=withdraw(pocket,journal,alpha,source_id="origin-alpha",reason="original source retracts claim")
    result=inspect_corroboration(pocket,journal,question(names))
    assert result["disposition"]=="abstain_missing_supported_path"
    assert result["reconciliation"]["status_by_observation_id"][alpha]=="withdrawn"
    delta=observed(names,"origin-delta")
    journal=attest(pocket,journal,delta,source_id="origin-delta")
    result=inspect_corroboration(pocket,journal,question(names))
    assert result["disposition"]=="supported_experimental_composition"
    assert result["support_lineage_provenance"][0]["supporting_observation_ids"]==sorted([_hash(beta),_hash(delta)])


def test_unrelated_evidence_never_enables_unjustified_relation(case):
    _,pocket,names,_,_=case
    journal,alpha=testified(case)
    noise=observed(names,"noise-root","r2","t2")
    journal=attest(pocket,journal,noise,source_id="noise-root")
    assert inspect_corroboration(pocket,journal,question(names))["disposition"]=="abstain_missing_supported_path"
    assert inspect_corroboration(pocket,journal,CompositionQuery(names["r1"],names["t4"],maximum_hops=9))["disposition"]=="abstain_missing_supported_path"


def test_manifest_identity_source_and_invalid_retraction_fail_closed(case):
    _,pocket,names,_,_=case
    journal,alpha=testified(case)
    with pytest.raises(PocketIntegrityError):
        attest(pocket,journal,observed(names,"origin-beta"),source_id="unregistered")
    with pytest.raises(PocketIntegrityError):
        attest(pocket,journal,observed(names,"origin-alpha"),source_id="origin-alpha")
    with pytest.raises(PocketIntegrityError):
        withdraw(pocket,journal,alpha,source_id="origin-beta",reason="foreign withdraw")
    with pytest.raises(PocketIntegrityError):
        withdraw(pocket,journal,"forged",source_id="origin-alpha",reason="foreign withdraw")


@pytest.mark.parametrize("attack",[
    "source","manifest","history","payload","origin","head","canonical","extra",
])
def test_corruption_and_native_scope_fail_closed(case,attack):
    _,pocket,names,_,_=case
    journal,_=testified(case)
    forged=deepcopy(journal)
    if attack=="source":
        forged["source"]["canonical_fingerprint"]="forged"
    elif attack=="manifest":
        forged["registered_sources"]["origin-alpha"]["lineage_family"]="forged"
    elif attack=="history":
        forged["events"][0]["record_hash"]="forged"
    elif attack=="payload":
        forged["events"][0]["payload"]["observation"]["observation_body"]["object"]="wrong"
    elif attack=="origin":
        forged["events"][0]["payload"]["source_id"]="origin-beta"
    elif attack=="head":
        forged["head_hash"]="forged"
    elif attack=="canonical":
        forged["native_writeback"]=True
    else:
        forged["unexpected"]="write"
    with pytest.raises(PocketIntegrityError):
        validate_provenance(forged,pocket)


def test_source_bound_sidecar_retains_same_result_after_fresh_vdk_rebuild(case,tmp_path):
    kernel,pocket,names,ps,qid=case
    native=tmp_path/"before.vdk"
    save_checkpoint(native,kernel.snapshot())
    old_bytes=native.read_bytes()
    journal,alpha=testified(case)
    journal=attest(pocket,journal,observed(names,"origin-beta"),source_id="origin-beta")
    result=inspect_corroboration(pocket,journal,question(names))
    archive=tmp_path/"corroborated.vpc.json"
    save_provenance(archive,journal,pocket)
    with pytest.raises(FileExistsError):
        save_provenance(archive,journal,pocket)
    fresh=VerdantKernel.from_state(load_checkpoint(native))
    copied=cultivate_pocket(fresh,ps,q_id=qid,rounds=1)
    loaded=load_provenance(archive,copied)
    assert inspect_corroboration(copied,loaded,question(names))==result
    assert native.read_bytes()==old_bytes
    assert len(fresh.state.relations)==9
    tampered=archive.read_bytes()+b" "
    archive.write_bytes(tampered)
    with pytest.raises(PocketIntegrityError):
        load_provenance(archive,copied)


def test_controlled_v22_journal_migration_does_not_grant_corrob(case):
    kernel,pocket,names,ps,qid=case
    legacy=start_revision(pocket)
    alpha=observed(names,"origin-alpha")
    beta=observed(names,"origin-beta")
    legacy=v22_observe(pocket,legacy,alpha)
    legacy=v22_observe(pocket,legacy,beta)
    original=deepcopy(legacy)
    revised=migrate_v22(pocket,legacy,{
        "origin-alpha":"origin-alpha","origin-beta":"origin-beta",
    },manifest())
    assert legacy==original
    assert len(revised["events"])==2
    assert inspect_corroboration(pocket,revised,question(names))["disposition"]=="supported_experimental_composition"
    with pytest.raises(PocketIntegrityError):
        migrate_v22(pocket,legacy,{"origin-alpha":"origin-alpha"},manifest())


def test_source_manifest_common_lineage_not_distinct_independence(case):
    _,pocket,names,_,_=case
    registered=manifest()
    registered["origin-beta"]["lineage_family"]=registered["origin-alpha"]["lineage_family"]
    j=new_provenance(pocket,registered)
    j=attest(pocket,j,observed(names,"origin-alpha"),source_id="origin-alpha")
    j=attest(pocket,j,observed(names,"origin-beta"),source_id="origin-beta")
    state=status_snapshot(pocket,j)
    assert state["counts"]["corroborated_experimental"]==0
    assert inspect_corroboration(pocket,j,question(names))["disposition"]=="abstain_missing_supported_path"



def test_controlled_unrelated_evidence_scaling_has_matched_flat_inputs(case):
    from verdant_pockets.source_benchmark import benchmark_scale
    _kernel,pocket,names,_ps,_q=case
    result=benchmark_scale(pocket,names)
    assert [row["unrelated_attestations"] for row in result["results"]]==[0,8,16,32,64]
    assert all(x["eligible_experimental_bridges"]==1 for x in result["results"])
    assert all(x["pocket_disposition"]=="supported_experimental_composition" for x in result["results"])
    assert all(x["flat_disposition"]==x["pocket_disposition"] for x in result["results"])
    assert result["source_count_held_constant"]
    assert not result["pocket_advantage_demonstrated"]
    assert result["results"][-1]["provenance_attestations_replayed"]==66



def test_end_to_end_controlled_native_v23_provenance_and_scaling_demo():
    from verdant_pockets.research_corroboration_demo import run_demo
    report,journal,pocket=run_demo()
    assert [step["disposition"] for step in report["history"]]==[
        "abstain_missing_supported_path",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
    ]
    assert report["heldout_after_native_restart"]["disposition"]=="supported_experimental_composition"
    assert report["heldout_exact_replay"] is True
    assert len(journal["events"])==12
    assert report["native_relation_count"]==9
    assert report["declared_roots_are_NOT_authenticated"]
    assert not report["flat_graph_has_same_admissible_evidence"] is False
    assert report["pocket_advantage_not_established"]
    validate_provenance(journal,pocket)


def test_user_compatible_v22_journal_migration_and_verification_cli(case,tmp_path,capsys):
    from verdant_pockets.research_corroboration_demo import (
        main, LEGACY_MANIFEST, LEGACY_MAP,
    )
    from verdant_pockets.reconciliation import save_revision
    _kernel,pocket,names,_ps,_qid=case
    legacy=start_revision(pocket)
    a=observation_from_testimony(source=names["r4"],target=names["s1"],
        relation_type="precedes",source_ref="controlled:independent-stage-two-primitive-observation")
    c=observation_from_testimony(source=names["s1"],target=names["r4"],
        relation_type="precedes",source_ref="controlled:independent-reverse-challenge")
    noise=observation_from_testimony(source=names["r2"],target=names["t2"],
        relation_type="precedes",source_ref="controlled:unrelated-p-evidence")
    d=observation_from_testimony(source=names["r4"],target=names["s1"],
        relation_type="precedes",source_ref="controlled:second-declared-replacement-source")
    legacy=v22_observe(pocket,legacy,a)
    legacy=v22_observe(pocket,legacy,c)
    legacy=v22_observe(pocket,legacy,noise)
    legacy=v22_withdraw(pocket,legacy,_hash(c),source_ref=c["source_ref"],reason="controlled challenger withdrawn")
    legacy=v22_withdraw(pocket,legacy,_hash(a),source_ref=a["source_ref"],reason="controlled origin withdrawn")
    legacy=v22_observe(pocket,legacy,d)
    old=tmp_path/"prior.vpr.json"
    save_revision(old,legacy,pocket)
    original=old.read_bytes()
    output=tmp_path/"corroboration.json"
    journal=tmp_path/"provenance.vpc.json"
    main(["--from-v22",str(old),"--out",str(output),"--journal",str(journal)])
    assert original==old.read_bytes()
    report=json.loads(output.read_text(encoding="utf-8"))
    assert report["source_v22_journal_imported_without_changes"]
    assert report["history"][0]["disposition"]=="abstain_missing_supported_path"
    assert report["history"][-1]["disposition"]=="supported_experimental_composition"
    capsys.readouterr()
    main(["--verify",str(journal)])
    verified=json.loads(capsys.readouterr().out)
    assert verified["fresh_source_replay"]
    assert verified["heldout_disposition"]=="supported_experimental_composition"
    assert original==old.read_bytes()



def test_explicit_native_contradicted_same_direction_blocks_attested_bridge(case):
    from verdant_kernel import RelationStatus
    kernel,_pocket,names,ps,qid=case
    kernel.propose_relation(
        names["r4"],names["s1"],"precedes",
        evidence_refs=kernel.state.structures[ps[0]].evidence_refs,
        status=RelationStatus.CONTRADICTED,directed=True,
    )
    revised=cultivate_pocket(kernel,ps,q_id=qid,rounds=1)
    manifest_sources=manifest()
    j=new_provenance(revised,manifest_sources)
    j=attest(revised,j,observed(names,"origin-alpha"),source_id="origin-alpha")
    j=attest(revised,j,observed(names,"origin-beta"),source_id="origin-beta")
    state=status_snapshot(revised,j)
    assert state["counts"]["disputed_quarantined"]==2
    assert inspect_corroboration(revised,j,question(names))["disposition"]=="abstain_missing_supported_path"
