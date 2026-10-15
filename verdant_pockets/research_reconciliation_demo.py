"""Controlled v2.2 reconciliation on genuine native Council P/Q memory.

Positive and negative arms are in a NEW disposable kernel, or resume by
migrating an existing v2.1 experimental sidecar. Never rewrite source VDK
or the old v2.1 journal; all revision events are experimental testimony.

Run:
  python -m verdant_pockets.research_reconciliation_demo --out report.json --journal current.vpr.json
  python -m verdant_pockets.research_reconciliation_demo --from-v21 old.vpel.json --out report.json --journal current.vpr.json
  python -m verdant_pockets.research_reconciliation_demo --verify current.vpr.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint
from .composition import CompositionQuery
from .evidence_retention import (
    acquire_observation, load_ledger, new_ledger, observation_from_testimony,
)
from .experiment import PocketIntegrityError, cultivate_pocket
from .reconciliation import (
    _hash, inspect_revision, load_revision, migrate_v21, observe,
    save_revision, withdraw,
)
from .research_demo import make_native_teaching_corpus


def _fresh_native():
    kernel, family, qid, names, relations = make_native_teaching_corpus(
        include_cross_p_bridge=False,
    )
    if len(relations) != 9:
        raise PocketIntegrityError("Native source unexpectedly already has cross-P evidence")
    pocket = cultivate_pocket(kernel, family, q_id=qid, rounds=1)
    return kernel, family, qid, names, pocket


def _first_v21(pocket: dict, names: dict) -> dict:
    return acquire_observation(
        pocket, new_ledger(pocket),
        observation_from_testimony(
            source=names["r4"], target=names["s1"], relation_type="precedes",
            source_ref="controlled:independent-stage-two-primitive-observation",
        ),
    )


def _step(pocket: dict, journal: dict, query: CompositionQuery, label: str) -> dict:
    result = inspect_revision(pocket, journal, query)
    return {
        "stage": label,
        "revision_event_count": len(journal["events"]),
        "disposition": result["disposition"],
        "underlying_composition_disposition": result["underlying_composition_disposition"],
        "witness_external_observation_ids": result["conditional_proof"]["witness_external_observation_ids"],
        "witness_native_relation_count": len(result["conditional_proof"]["witness_native_relation_ids"]),
        "suspended_proof_dependencies": result["suspended_proof_depended_on_observation_ids"],
        "quarantined": result["reconciliation"]["quarantined_observation_ids"],
        "withdrawn": result["reconciliation"]["withdrawn_observation_ids"],
        "eligible": result["reconciliation"]["eligible_observation_ids"],
        "flat_disposition": result["flat_baseline"]["disposition"],
        "pocket_search_expansions": result["conditional_proof"]["metrics"].get("edge_expansions"),
        "flat_search_expansions": result["flat_baseline"]["edge_expansions"],
        "proof_claim_remains_experimental": True,
    }


def run_reconciliation_demo(previous_v21: Path | None = None) -> tuple[dict, dict, dict]:
    kernel, family, qid, names, pocket = _fresh_native()
    native_sha = kernel.fingerprint()
    v21 = load_ledger(previous_v21, pocket) if previous_v21 is not None else _first_v21(pocket,names)
    if len(v21["events"]) != 1:
        raise PocketIntegrityError("Controlled v2.2 demo requires exactly one v2.1 acquired observation")
    first_obs = v21["events"][0]["observation"]
    if (first_obs["source"], first_obs["target"], first_obs["type"]) != (
            names["r4"], names["s1"], "precedes"):
        raise PocketIntegrityError("Cannot repurpose unrelated v2.1 observation as staged bridge")
    original_id = v21["events"][0]["observation_id"]
    journal = migrate_v21(pocket, v21)
    query = CompositionQuery(names["r1"],names["s4"],maximum_hops=9)
    heldout = CompositionQuery(names["r3"],names["s2"],maximum_hops=9)
    unrelated_query = CompositionQuery(names["r1"],names["t4"],maximum_hops=9)
    stages = [_step(pocket,journal,query,"original_retained_evidence")]

    challenge = observation_from_testimony(
        source=names["s1"],target=names["r4"],relation_type="precedes",
        source_ref="controlled:independent-reverse-challenge",
    )
    journal = observe(pocket,journal,challenge)
    challenge_id = _hash(challenge)
    stages.append(_step(pocket,journal,query,"reverse_challenge_quarantines"))

    irrelevant = observation_from_testimony(
        source=names["r2"],target=names["t2"],relation_type="precedes",
        source_ref="controlled:unrelated-p-evidence",
    )
    journal = observe(pocket,journal,irrelevant)
    stages.append(_step(pocket,journal,query,"unrelated_evidence_while_contested"))

    journal = withdraw(
        pocket,journal,challenge_id,
        source_ref=challenge["source_ref"],
        reason="controlled reverse challenge source rescinds its observation",
    )
    stages.append(_step(pocket,journal,query,"challenge_withdrawn_recovers"))

    journal = withdraw(
        pocket,journal,original_id,
        source_ref=first_obs["source_ref"],
        reason="original observation source withdraws initial testimony",
    )
    stages.append(_step(pocket,journal,query,"original_source_withdraws_suspends"))

    replacement = observation_from_testimony(
        source=names["r4"],target=names["s1"],relation_type="precedes",
        source_ref="controlled:second-declared-replacement-source",
    )
    journal = observe(pocket,journal,replacement)
    stages.append(_step(pocket,journal,query,"replacement_experimental_testimony_recovers"))

    expected = [
        "supported_experimental_composition",
        "suspended_contested_evidence",
        "suspended_contested_evidence",
        "supported_experimental_composition",
        "suspended_withdrawn_evidence",
        "supported_experimental_composition",
    ]
    if [x["disposition"] for x in stages] != expected:
        raise PocketIntegrityError("Controlled evidence reconciliation stages did not match expectations")
    if any(x["underlying_composition_disposition"] != x["flat_disposition"] for x in stages):
        raise PocketIntegrityError("Reconciled pocket and flat reference disagree")
    if stages[2]["eligible"] != [_hash(irrelevant)]:
        raise PocketIntegrityError("Unrelated evidence was not kept isolated from contested bridge")

    with TemporaryDirectory(prefix="verdant-v22-") as tmp:
        vdk = Path(tmp) / "source-before-reconciliation.vdk"
        save_checkpoint(vdk,kernel.snapshot())
        before_sha = sha256(vdk.read_bytes()).hexdigest()
        fresh = VerdantKernel.from_state(load_checkpoint(vdk))
        restored = cultivate_pocket(fresh,family,q_id=qid,rounds=1)
        new_heldout = inspect_revision(restored,journal,heldout)
        old_heldout = inspect_revision(pocket,journal,heldout)
        if new_heldout != old_heldout:
            raise PocketIntegrityError("Reconstructed source did not reproduce heldout revised conclusion")
        if sha256(vdk.read_bytes()).hexdigest() != before_sha:
            raise PocketIntegrityError("Temporary original native VDK changed")

    unrelated_result = inspect_revision(pocket,journal,unrelated_query)
    if unrelated_result["disposition"] != "abstain_missing_supported_path":
        raise PocketIntegrityError("Irrelevant P gained a non-evidenced conclusion")
    if kernel.fingerprint() != native_sha or len(kernel.state.relations) != 9:
        raise PocketIntegrityError("Original native kernel relation graph was modified")
    report = {
        "schema": "verdant.cognitive_pocket_reconciliation_demo.v2.2",
        "native_canonical_fingerprint": native_sha,
        "source_pocket_id": pocket["pocket_id"],
        "promoted_q_id": qid,
        "native_p_ids": list(family),
        "native_primitive_relations": 9,
        "migrated_v21_observation_id": original_id,
        "stages": stages,
        "final_full_evaluation": inspect_revision(pocket,journal,query),
        "heldout_after_restart": new_heldout,
        "heldout_reproduced_after_native_checkpoint_reload": True,
        "unrelated_query_disposition": unrelated_result["disposition"],
        "comparisons_use_identical_reconciled_evidence": True,
        "source_authenticity_independently_verified": False,
        "observations_teacher_supplied_not_discovered": True,
        "no_canonical_writeback": True,
        "no_obligation_writeback": True,
        "pocket_advantage_over_flat_graph_demonstrated": False,
        "source_v21_sidecar_changed": False,
    }
    return report,journal,pocket


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-v21",type=Path)
    parser.add_argument("--out",type=Path)
    parser.add_argument("--journal",type=Path)
    parser.add_argument("--verify",type=Path)
    args = parser.parse_args(argv)
    if args.verify is not None:
        _kernel,_ps,_q,names,pocket = _fresh_native()
        retained = load_revision(args.verify,pocket)
        result = inspect_revision(
            pocket,retained,CompositionQuery(names["r3"],names["s2"],maximum_hops=9),
        )
        if result["disposition"] != "supported_experimental_composition":
            raise PocketIntegrityError("Replayed held-out conclusion is unsupported")
        print(json.dumps({
            "reconciliation_journal_verified": True,
            "event_count": len(retained["events"]),
            "heldout_disposition": result["disposition"],
            "native_memory_unchanged": True,
        },indent=2))
        return
    if args.out is None or args.journal is None:
        parser.error("Provide --out and --journal, or --verify")
    if args.out.resolve()==args.journal.resolve():
        parser.error("Report and revision journal must be distinct")
    if args.out.exists() or args.journal.exists():
        parser.error("Outputs must not already exist; old journals are immutable")
    if args.from_v21 is not None and (
        args.from_v21.resolve()==args.out.resolve() or
        args.from_v21.resolve()==args.journal.resolve()
    ):
        parser.error("Cannot overwrite or replace the original v2.1 journal")
    report,journal,pocket = run_reconciliation_demo(args.from_v21)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.journal.parent.mkdir(parents=True,exist_ok=True)
    save_revision(args.journal,journal,pocket)
    with args.out.open("x",encoding="utf-8") as stream:
        json.dump(report,stream,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)
    print(json.dumps({
        "stages": [{k:x[k] for k in ("stage","disposition","flat_disposition")} for x in report["stages"]],
        "heldout_after_restart": report["heldout_after_restart"]["disposition"],
        "native_relations_unchanged": True,
        "source_v21_sidecar_changed": False,
        "report": str(args.out),
        "journal": str(args.journal),
    },indent=2))


if __name__=="__main__":
    main()
