"""v2.3 executable native Council P/Q corroboration and scaling study.

The supplied v2.2 journal is read-only. All old source_ref strings are
EXPLICITLY mapped to controlled provenance families; mapping cannot
authenticate real people or establish real-world independent observations.

Fresh disposable original native P/Q (9 primitive relations, NO bridge).
Required:
  python -m verdant_pockets.research_corroboration_demo --from-v22 old.vpr.json --out study.json --journal new.vpc.json
  python -m verdant_pockets.research_corroboration_demo --verify new.vpc.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from verdant_kernel import VerdantKernel,load_checkpoint,save_checkpoint
from .composition import CompositionQuery
from .corroboration import (
    _hash,attest,withdraw,inspect_corroboration,load_provenance,
    save_provenance,migrate_v22,
)
from .evidence_retention import observation_from_testimony
from .experiment import PocketIntegrityError,cultivate_pocket
from .reconciliation import load_revision,start_revision,observe as rev_observe,withdraw as rev_withdraw
from .research_demo import make_native_teaching_corpus
from .source_benchmark import benchmark_scale


LEGACY_MANIFEST={
    "v22-original":{"lineage_family":"controlled-origin-alpha","description":"v2.2 initial bridge observation"},
    "v22-reverse":{"lineage_family":"controlled-origin-gamma","description":"v2.2 reverse challenge"},
    "v22-noise":{"lineage_family":"controlled-origin-noise","description":"v2.2 unrelated observation"},
    "v22-replacement":{"lineage_family":"controlled-origin-delta","description":"v2.2 final replacement observation"},
    "new-copy":{"lineage_family":"controlled-origin-copy-claim","description":"v2.3 derived republication"},
    "new-beta":{"lineage_family":"controlled-origin-beta","description":"v2.3 external origin group B"},
    "new-reverse":{"lineage_family":"controlled-origin-reverse","description":"v2.3 contradictory source"},
    "new-epsilon":{"lineage_family":"controlled-origin-epsilon","description":"v2.3 recovery origin"},
}
LEGACY_MAP={
    "controlled:independent-stage-two-primitive-observation":"v22-original",
    "controlled:independent-reverse-challenge":"v22-reverse",
    "controlled:unrelated-p-evidence":"v22-noise",
    "controlled:second-declared-replacement-source":"v22-replacement",
}


def native_source():
    kernel,ps,qid,names,relations=make_native_teaching_corpus(include_cross_p_bridge=False)
    if len(relations)!=9:
        raise PocketIntegrityError("Staged native source unexpectedly includes cross-P relation")
    pocket=cultivate_pocket(kernel,ps,q_id=qid,rounds=1)
    return kernel,ps,qid,names,pocket


def _obs(names,a,b,source_ref):
    return observation_from_testimony(
        source=names[a],target=names[b],relation_type="precedes",source_ref=source_ref,
    )


def _staged_v22(pocket,names):
    old=start_revision(pocket)
    initial=_obs(names,"r4","s1","controlled:independent-stage-two-primitive-observation")
    reverse=_obs(names,"s1","r4","controlled:independent-reverse-challenge")
    old=rev_observe(pocket,old,initial)
    old=rev_observe(pocket,old,reverse)
    old=rev_observe(pocket,old,_obs(names,"r2","t2","controlled:unrelated-p-evidence"))
    old=rev_withdraw(pocket,old,_hash(reverse),source_ref=reverse["source_ref"],
                     reason="controlled reverse challenge source rescinds its observation")
    old=rev_withdraw(pocket,old,_hash(initial),source_ref=initial["source_ref"],
                     reason="original observation source withdraws initial testimony")
    old=rev_observe(pocket,old,_obs(
        names,"r4","s1","controlled:second-declared-replacement-source",
    ))
    return old


def _stage(pocket,journal,query,label,*,native_kernel=None):
    report=inspect_corroboration(pocket,journal,query,native_kernel=native_kernel)
    return {
        "stage":label,
        "disposition":report["disposition"],
        "flat_disposition":report["flat_baseline"]["disposition"],
        "lineage_supports":report["support_lineage_provenance"],
        "corroborated_claims":report["reconciliation"]["corroborated_claims"],
        "status_counts":report["reconciliation"]["counts"],
        "graph_work":report["cost_accounting"],
        "native_canonical_writeback":False,
        "source_authenticity_verified":False,
        "live_native_negative_relations_scanned":report["native_negative_relations_considered_from_live_source"],
    }


def run_demo(previous_v22=None):
    kernel,ps,qid,names,pocket=native_source()
    frozen=kernel.fingerprint()
    old=load_revision(previous_v22,pocket) if previous_v22 else _staged_v22(pocket,names)
    if len(old["events"])!=6:
        raise PocketIntegrityError("Expected six-stage v2.2 journal input")
    journal=migrate_v22(pocket,old,LEGACY_MAP,LEGACY_MANIFEST)
    query=CompositionQuery(names["r1"],names["s4"],maximum_hops=9)
    heldout=CompositionQuery(names["r3"],names["s2"],maximum_hops=9)
    states=[_stage(pocket,journal,query,"migrated_v22_single_active_bridge_provisional",native_kernel=kernel)]

    replacement=_obs(names,"r4","s1","v22-replacement")
    old_id=_hash(replacement)
    copied=_obs(names,"r4","s1","new-copy")
    journal=attest(pocket,journal,copied,source_id="new-copy",derived_from=old_id)
    states.append(_stage(pocket,journal,query,"copied_citation_same_origin_no_quorum",native_kernel=kernel))

    beta=_obs(names,"r4","s1","new-beta")
    journal=attest(pocket,journal,beta,source_id="new-beta")
    states.append(_stage(pocket,journal,query,"declared_second_origin_corrob_proof",native_kernel=kernel))

    reverse=_obs(names,"s1","r4","new-reverse")
    journal=attest(pocket,journal,reverse,source_id="new-reverse")
    states.append(_stage(pocket,journal,query,"contradictory_source_quarantines",native_kernel=kernel))

    journal=withdraw(pocket,journal,_hash(reverse),source_id="new-reverse",
                     reason="source withdraws its contradictory observation")
    states.append(_stage(pocket,journal,query,"challenge_withdrawn_recovers",native_kernel=kernel))

    journal=withdraw(pocket,journal,_hash(beta),source_id="new-beta",
                     reason="second independent family withdraws support")
    states.append(_stage(pocket,journal,query,"second_origin_withdrawn_loses_quorum",native_kernel=kernel))

    epsilon=_obs(names,"r4","s1","new-epsilon")
    journal=attest(pocket,journal,epsilon,source_id="new-epsilon")
    states.append(_stage(pocket,journal,query,"new_distinct_origin_recovers",native_kernel=kernel))

    expected=[
        "abstain_missing_supported_path",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
        "abstain_missing_supported_path",
        "supported_experimental_composition",
    ]
    if [x["disposition"] for x in states]!=expected:
        raise PocketIntegrityError("Corroboration research sequence did not reproduce")
    if any(x["disposition"]!=x["flat_disposition"] for x in states):
        raise PocketIntegrityError("Flat and pocket conditionals disagree")
    scaling=benchmark_scale(pocket,names,native_kernel=kernel)

    with TemporaryDirectory(prefix="verdant-v23-") as dirname:
        vdk=Path(dirname)/"prebridge-source.vdk"
        save_checkpoint(vdk,kernel.snapshot())
        old_sha=sha256(vdk.read_bytes()).hexdigest()
        reopened=VerdantKernel.from_state(load_checkpoint(vdk))
        fresh=cultivate_pocket(reopened,ps,q_id=qid,rounds=1)
        test=inspect_corroboration(fresh,journal,heldout,native_kernel=reopened)
        if test!=inspect_corroboration(pocket,journal,heldout,native_kernel=kernel):
            raise PocketIntegrityError("Post-restart held-out proof diverged")
        if sha256(vdk.read_bytes()).hexdigest()!=old_sha:
            raise PocketIntegrityError("Controlled native checkpoint changed")
    if kernel.fingerprint()!=frozen or len(kernel.state.relations)!=9:
        raise PocketIntegrityError("Native source modified during experiment")

    report={
        "schema":"verdant.cognitive_pocket_corroboration_demo.v2.3",
        "source_pocket_id":pocket["pocket_id"],
        "native_canonical_fingerprint":frozen,
        "native_p_ids":list(ps),
        "native_promoted_q_id":qid,
        "native_relation_count":9,
        "source_v22_journal_imported_without_changes":previous_v22 is not None,
        "history":states,
        "heldout_after_native_restart":test,
        "heldout_exact_replay":True,
        "unrelated_evidence_scaling":scaling,
        "declared_roots_are_NOT_authenticated":True,
        "not_independent_real_world_observations":True,
        "flat_graph_has_same_admissible_evidence":True,
        "pocket_advantage_not_established":True,
        "no_canonical_writeback":True,
        "no_obligation_writeback":True,
        "original_v22_sidecar_unmodified":True,
    }
    return report,journal,pocket


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-v22",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--journal",type=Path)
    parser.add_argument("--verify",type=Path)
    args=parser.parse_args(argv)
    if args.verify is not None:
        _kernel,_ps,_qid,names,pocket=native_source()
        journal=load_provenance(args.verify,pocket)
        probe=inspect_corroboration(pocket,journal,CompositionQuery(
            names["r3"],names["s2"],maximum_hops=9,
        ),native_kernel=_kernel)
        if probe["disposition"]!="supported_experimental_composition":
            raise PocketIntegrityError("Reconstructed provenance does not corroborate held-out task")
        print(json.dumps({
            "fresh_source_replay":True,
            "journal_events":len(journal["events"]),
            "heldout_disposition":probe["disposition"],
            "native_memory_unchanged":True,
        },indent=2))
        return
    if args.out is None or args.journal is None:
        parser.error("Provide --out and --journal for the full run, or --verify")
    if args.out.resolve()==args.journal.resolve():
        parser.error("Output and journal must differ")
    if args.from_v22 and args.from_v22.resolve() in (args.out.resolve(),args.journal.resolve()):
        parser.error("Never overwrite the original v2.2 journal")
    if args.out.exists() or args.journal.exists():
        parser.error("Destination already occupied; new sidecars must be create-only")
    report,journal,pocket=run_demo(args.from_v22)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.journal.parent.mkdir(parents=True,exist_ok=True)
    save_provenance(args.journal,journal,pocket)
    with args.out.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)
    print(json.dumps({
        "seven_stage_conditions":[{"stage":s["stage"],"result":s["disposition"]}
                                  for s in report["history"]],
        "heldout_reproduced":report["heldout_exact_replay"],
        "benchmark_levels":[r["unrelated_attestations"] for r in report["unrelated_evidence_scaling"]["results"]],
        "original_native_vdk_changed":False,
        "previous_v22_sidecar_changed":False,
        "report":str(args.out),
        "journal":str(args.journal),
    },indent=2))


if __name__=="__main__":
    main()
