"""Executable v2.1 gap -> external evidence -> retained inference experiment.

Teacher stages only primitive native P/Q memory in a disposable native kernel.
Only after a failed query does a controlled external observation enter a
*separate experimental sidecar*. No canonical native relation is added.
A new source checkpoint is reconstructed and the sidecar tested on held-out
queries after restart. The source VDK is never overwritten.

Run:
  python -m verdant_pockets.research_acquisition_demo --out controlled.json --ledger acquired.vpel.json
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from verdant_kernel import VerdantKernel, load_checkpoint, save_checkpoint

from .composition import CompositionQuery, inspect_composition
from .evidence_retention import (
    acquire_observation, compose_with_evidence, flat_graph_control,
    gap_certificate, load_ledger, new_ledger, observation_from_testimony,
    save_ledger,
)
from .experiment import PocketIntegrityError, cultivate_pocket
from .research_demo import make_native_teaching_corpus


def run_acquisition_demo() -> tuple[dict, dict, dict]:
    kernel, ps, qid, names, primitive_ids = make_native_teaching_corpus(
        include_cross_p_bridge=False,
    )
    if len(primitive_ids) != 9:
        raise PocketIntegrityError("Controlled source mistakenly contains a cross-P bridge")
    before = kernel.fingerprint()
    pocket = cultivate_pocket(kernel, ps, q_id=qid, rounds=1)
    query = CompositionQuery(names["r1"], names["s4"], maximum_hops=9)
    heldout = CompositionQuery(names["r3"], names["s2"], maximum_hops=9)
    initial_gap = gap_certificate(pocket, query)
    initial_heldout = inspect_composition(pocket, heldout)
    if initial_gap["disposition"] != "abstain_missing_supported_path":
        raise PocketIntegrityError("Source already has a solution; gap is not genuine")
    if initial_heldout["disposition"] != "abstain_missing_supported_path":
        raise PocketIntegrityError("Held-out source answer leaked before acquisition")

    journal = new_ledger(pocket)
    obs = observation_from_testimony(
        source=names["r4"], target=names["s1"],
        relation_type="precedes",
        source_ref="controlled:independent-stage-two-primitive-observation",
    )
    acquired = acquire_observation(pocket, journal, obs)
    post = compose_with_evidence(pocket, acquired, query)
    heldout_result = compose_with_evidence(pocket, acquired, heldout)
    flat = flat_graph_control(pocket, acquired, query)

    def wrong_bridge(source: str, target: str):
        other = acquire_observation(
            pocket, new_ledger(pocket),
            observation_from_testimony(
                source=names[source], target=names[target],
                relation_type="precedes",
                source_ref="controlled:negative-evidence-arm",
            ),
        )
        return compose_with_evidence(pocket, other, query)["disposition"]

    controls = {
        "no_observation": compose_with_evidence(pocket, journal, query)["disposition"],
        "reverse_observation": wrong_bridge("s1", "r4"),
        "irrelevant_p_observation": wrong_bridge("r4", "t1"),
        "direct_answer_leak_control": wrong_bridge("r1", "s4"),
        "unlicensed_query": compose_with_evidence(
            pocket, acquired,
            CompositionQuery(names["r1"], names["s4"], "supports"),
        )["disposition"],
    }

    with TemporaryDirectory(prefix="verdant-pocket-21-") as tmp:
        checkpoint = Path(tmp) / "native-before-acquisition.vdk"
        save_checkpoint(checkpoint, kernel.snapshot())
        original_vdk_sha = sha256(checkpoint.read_bytes()).hexdigest()
        restored_kernel = VerdantKernel.from_state(load_checkpoint(checkpoint))
        new_pocket = cultivate_pocket(restored_kernel, ps, q_id=qid, rounds=1)
        if new_pocket != pocket or restored_kernel.fingerprint() != before:
            raise PocketIntegrityError("Native source did not reconstruct after restart")
        after_restart = compose_with_evidence(new_pocket, acquired, heldout)
        if after_restart != heldout_result:
            raise PocketIntegrityError("Held-out compositional result changed after restart")
        if sha256(checkpoint.read_bytes()).hexdigest() != original_vdk_sha:
            raise PocketIntegrityError("Source VDK changed during retained replay")
    if kernel.fingerprint() != before or len(kernel.state.relations) != 9:
        raise PocketIntegrityError("Acquisition unexpectedly changed canonical native relations")
    if post["disposition"] != "supported_experimental_composition":
        raise PocketIntegrityError("Post-observation proof did not resolve")
    if heldout_result["disposition"] != "supported_experimental_composition":
        raise PocketIntegrityError("Held-out source-to-target relation did not transfer")
    if flat["disposition"] != post["disposition"]:
        raise PocketIntegrityError("Flat graph and pocket disagree under identical source evidence")

    report = {
        "schema": "verdant.cognitive_pocket_acquisition_demo.v2.1",
        "source_canonical_fingerprint": before,
        "native_earned_p_ids": list(ps),
        "native_promoted_q_id": qid,
        "native_primitive_relation_count": len(primitive_ids),
        "pre_observation_gap": initial_gap,
        "post_external_observation": post,
        "heldout_new_query": heldout_result,
        "post_reload_heldout_same_result": after_restart == heldout_result,
        "flat_graph_same_evidence_control": flat,
        "controls": controls,
        "external_observation_kind": obs["evidence_kind"],
        "new_observations_harness_supplied": 1,
        "external_observation_truth_independently_verified": False,
        "new_rule_learned_by_kernel": False,
        "experimental_evidence_kept_outside_native_VDK": True,
        "native_VDK_sha256_in_temporary_replay": original_vdk_sha,
        "native_memory_modified": False,
        "comparison_proves_pocket_advantage_over_flat_graph": False,
    }
    return report, acquired, pocket


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.resolve() == args.ledger.resolve():
        parser.error("Experiment report and evidence journal must use different paths")
    if args.out.exists() or args.ledger.exists():
        parser.error("Output already exists. Use a new name; do not overwrite evidence.")
    report, ledger, pocket = run_acquisition_demo()
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    save_ledger(args.ledger, ledger, pocket)
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
    print(json.dumps({
        "gap_before_observation": report["pre_observation_gap"]["disposition"],
        "after_external_observation": report["post_external_observation"]["disposition"],
        "heldout_after_restart": report["heldout_new_query"]["disposition"],
        "post_reload_reproducible": report["post_reload_heldout_same_result"],
        "flat_graph_baseline": report["flat_graph_same_evidence_control"]["disposition"],
        "negative_controls": report["controls"],
        "external_observation_remains_experimental": True,
        "native_memory_modified": False,
        "report": str(args.out),
        "journal": str(args.ledger),
    }, indent=2))


if __name__ == "__main__":
    main()
