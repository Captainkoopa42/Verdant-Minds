"""Observer-only scorer: cultivate a curriculum pack, then check expectations.

The pack is compiled by the ordinary Workbench curriculum compiler and fed
through the ordinary ``VerdantDevelopmentPipeline`` with default policies.
The expectations file is opened only after cultivation has finished and the
final fingerprint has been recorded, so expected outcomes cannot influence
what the kernel does. This script promotes nothing and has no authority.

``policy_derived`` expectations follow from stated policy gates and are
scored pass/fail. ``exploratory`` items are reported and never scored.

    python run_observer_pack_expectations.py \
        curriculum_packs/verdant_controls_and_boundaries_curriculum_001.vcpack \
        curriculum_packs/verdant_controls_and_boundaries_curriculum_001.expectations.json \
        --accelerate --out controls_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "workbench" / "backend"))

from verdant_development import VerdantDevelopmentPipeline  # noqa: E402
from verdant_kernel import ExperienceCommand, VerdantKernel  # noqa: E402
from verdant_workbench.curriculum import (  # noqa: E402
    CurriculumCompileRequest,
    CurriculumCompiler,
    curriculum_pack_bundle_source,
)

SCHEMA = "verdant.observer.pack_expectations.v0"


def cultivate(pack_path: Path, *, seed: int, progress_every: int, rehearse: bool = False, rehearse_min_exposures: int = 2, experience_recurrence: bool = False, bond_clock: bool = False) -> tuple[VerdantKernel, dict]:
    text = pack_path.read_text(encoding="utf-8")
    pack, _bundle, _selected, probes, source = curriculum_pack_bundle_source(text, ())
    compiled = CurriculumCompiler().compile(
        CurriculumCompileRequest(
            project_id="observer",
            title=pack.title,
            source_format="teaching_bundle_json",
            source_text=source,
            state_dim=pack.state_dim,
        )
    )
    commands = [ExperienceCommand.model_validate(item) for item in compiled.compiled_commands]
    kernel = VerdantKernel(seed=seed, state_dim=pack.state_dim, run_label="pack-expectations")
    pipeline = VerdantDevelopmentPipeline()
    stages = {}
    if experience_recurrence:
        from sidecar_recurrence import ExperienceRecurrenceStructurePipeline

        stages["structures"] = ExperienceRecurrenceStructurePipeline()
    if bond_clock:
        from sidecar_bond_clock import BondClockPlasticityPipeline

        stages["plasticity"] = BondClockPlasticityPipeline()
    if stages:
        pipeline = VerdantDevelopmentPipeline(**stages)
    if rehearse:
        from sidecar_rehearsal import RehearsalConfig, RehearsingDevelopmentPipeline

        pipeline = RehearsingDevelopmentPipeline(pipeline, RehearsalConfig(min_real_exposures=rehearse_min_exposures))
    started = time.perf_counter()
    for index, command in enumerate(commands, start=1):
        pipeline.advance(kernel, command)
        if progress_every and index % progress_every == 0:
            print(f"  cultivated {index}/{len(commands)} ({time.perf_counter() - started:.0f}s)", flush=True)
    return kernel, {
        "pack_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "compiled_sha256": compiled.compiled_sha256,
        "items": len(commands),
        "recorded_probes": len(probes),
        "seconds": time.perf_counter() - started,
        "experimental_stages": sorted(stages),
        "rehearsal": None if not rehearse else {
            "config": dict(pipeline.rehearsal.config.__dict__),
            "beats_attempted": len(pipeline.reports),
            "beats_committed": sum(r.committed for r in pipeline.reports),
            "refusals": sorted({r.refusal for r in pipeline.reports if r.refusal}),
            "experiences_rehearsed": sum(len(r.selected_evidence_ids) for r in pipeline.reports if r.committed),
            "bonds_reinforced_outside_selection": sum(len(r.reinforced_outside_selection) for r in pipeline.reports),
        },
    }


def score(kernel: VerdantKernel, expectations: dict) -> dict:
    state = kernel.state
    label_of = {concept_id: concept.label for concept_id, concept in state.concepts.items()}
    id_of = {label: concept_id for concept_id, label in label_of.items()}
    candidates = [
        {
            "members": frozenset(label_of[item] for item in candidate.member_concept_ids),
            "eligible": candidate.status.value in {"eligible", "promoted"},
            "status": candidate.status.value,
            "occurrences": candidate.occurrence_count,
            "internal_cohesion": round(candidate.quality.internal_cohesion, 4),
            "reconstructability": round(candidate.quality.reconstructability, 4),
            "boundary_selectivity": round(candidate.quality.boundary_selectivity, 4),
            "evidence_diversity": round(candidate.quality.evidence_diversity, 4),
            "cross_context_stability": round(candidate.quality.cross_context_stability, 4),
        }
        for _key, candidate in sorted(state.structure_candidates.items())
    ]
    eligible = [item for item in candidates if item["eligible"]]

    def alive_associations(members: list[str]) -> int:
        ids = {id_of[label] for label in members if label in id_of}
        return sum(
            1
            for association in state.plasticity_associations.values()
            if set(association.concept_ids) <= ids
        )

    rows = []
    for family in expectations["families"]:
        members = frozenset(family["members"])
        exact = [item for item in candidates if item["members"] == members]
        merged = [item for item in eligible if members < item["members"]]
        observed = {
            "exact_candidate_exists": bool(exact),
            "exact_candidate_promotion_eligible": any(item["eligible"] for item in exact),
            "eligible_candidates_containing_family_plus_others": [
                sorted(item["members"]) for item in merged
            ],
            "eligible_candidates_overlapping_family": sum(
                1 for item in eligible if members & item["members"]
            ),
            "plastic_associations_alive_at_end": alive_associations(family["members"]),
            "exact_candidate_gates": [
                {key: value for key, value in item.items() if key != "members"} for item in exact
            ],
        }
        expectation = family["expectation"]
        verdict = None
        if expectation["kind"] == "policy_derived":
            if "exact_candidate_promotion_eligible" in expectation:
                verdict = (
                    observed["exact_candidate_promotion_eligible"]
                    == expectation["exact_candidate_promotion_eligible"]
                )
            elif "no_eligible_candidate_contains_both_members" in expectation:
                verdict = not any(members <= item["members"] for item in eligible)
        rows.append({**family, "observed": observed, "pass": verdict})

    distractors = frozenset(expectations["distractor_concepts"])
    distractor_only = [sorted(item["members"]) for item in eligible if item["members"] <= distractors]
    claim_rows = []
    for case in expectations["claims"]:
        subject, obj = id_of.get(case["subject"]), id_of.get(case["object"])
        records = [
            claim
            for claim in state.claims.values()
            if claim.subject_concept_id == subject
            and claim.object_concept_id == obj
            and claim.predicate == case["predicate"]
        ]
        keys = {claim.claim_key for claim in records}
        contradictions = [
            item for item in state.contradictions.values() if item.claim_key in keys
        ]
        observed = {
            "claim_records": [
                {
                    "polarity": claim.polarity.value,
                    "status": claim.status.value,
                    "support_score": round(claim.support_score, 4),
                    "refutation_score": round(claim.refutation_score, 4),
                }
                for claim in sorted(records, key=lambda item: item.polarity.value)
            ],
            "contradiction_records": [item.status.value for item in contradictions],
        }
        verdict = None
        if case["expectation"]["kind"] == "policy_derived":
            verdict = (len(records) > 0) == case["expectation"]["claim_record_exists"]
        claim_rows.append({**case, "observed": observed, "pass": verdict})

    scored = [row["pass"] for row in rows + claim_rows if row["pass"] is not None]
    scored.append(not distractor_only)
    return {
        "families": rows,
        "claims": claim_rows,
        "distractor_only_eligible_candidates": distractor_only,
        "distractor_pass": not distractor_only,
        "candidate_count": len(candidates),
        "eligible_candidate_count": len(eligible),
        "policy_derived_checks": len(scored),
        "policy_derived_passed": sum(1 for item in scored if item),
    }


def _print(report: dict) -> None:
    result = report["result"]
    print(
        f"\ncandidates {result['candidate_count']} | eligible {result['eligible_candidate_count']} | "
        f"policy-derived checks passed {result['policy_derived_passed']}/{result['policy_derived_checks']}"
    )
    by_group: dict[str, list[dict]] = {}
    for row in result["families"]:
        by_group.setdefault(row["group"], []).append(row)
    for group, rows in by_group.items():
        kind = rows[0]["expectation"]["kind"]
        exact = sum(1 for row in rows if row["observed"]["exact_candidate_exists"])
        elig = sum(1 for row in rows if row["observed"]["exact_candidate_promotion_eligible"])
        merged = sum(
            1 for row in rows if row["observed"]["eligible_candidates_containing_family_plus_others"]
        )
        alive = sum(1 for row in rows if row["observed"]["plastic_associations_alive_at_end"] > 0)
        passed = [row["pass"] for row in rows if row["pass"] is not None]
        verdict = f"pass {sum(passed)}/{len(passed)}" if passed else "reported only"
        print(
            f"  {group:<15} n={len(rows)}  exact candidate {exact}  exact+eligible {elig}  "
            f"inside a larger eligible {merged}  traces alive {alive}  [{kind}: {verdict}]"
        )
    print(f"  distractors      eligible candidates made only of distractors: "
          f"{len(result['distractor_only_eligible_candidates'])}  "
          f"[policy_derived: {'pass' if result['distractor_pass'] else 'FAIL'}]")
    for row in result["claims"]:
        records = ", ".join(
            f"{item['polarity']}={item['status']}({item['support_score']})"
            for item in row["observed"]["claim_records"]
        ) or "no claim record"
        verdict = "" if row["pass"] is None else f"  [policy_derived: {'pass' if row['pass'] else 'FAIL'}]"
        print(f"  claim {row['case']:<14} {records}; contradictions "
              f"{row['observed']['contradiction_records'] or 'none'}{verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("pack", type=Path)
    parser.add_argument("expectations", type=Path)
    parser.add_argument("--seed", type=int, default=2301)
    parser.add_argument("--accelerate", action="store_true",
                        help="Opt in to the byte-exact fingerprint sidecar.")
    parser.add_argument("--rehearse", action="store_true",
                        help="Opt in to the experimental rehearsal sidecar (sidecar_rehearsal).")
    parser.add_argument("--rehearse-min-exposures", type=int, default=2)
    parser.add_argument("--wave", action="store_true",
                        help="Opt in to the experimental wave sidecar (sidecar_wave). Changes fingerprints.")
    parser.add_argument("--bond-clock", action="store_true",
                        help="Opt in to the experimental bond-clock plasticity stage (sidecar_bond_clock).")
    parser.add_argument("--experience-recurrence", action="store_true",
                        help="Opt in to the experimental recurrence observer (sidecar_recurrence).")
    parser.add_argument("--progress-every", type=int, default=40)
    parser.add_argument("--out", type=Path, default=None, help="Exclusive-create JSON report path.")
    args = parser.parse_args()
    if args.accelerate:
        from sidecar_acceleration import install_fingerprint_cache

        install_fingerprint_cache()
    if args.wave:
        from sidecar_wave import install_wave

        install_wave()
    kernel, run = cultivate(args.pack, seed=args.seed, progress_every=args.progress_every, rehearse=args.rehearse, rehearse_min_exposures=args.rehearse_min_exposures,
                          experience_recurrence=args.experience_recurrence, bond_clock=args.bond_clock)
    final_fingerprint = kernel.state.fingerprint()
    # Only now is the expectations file opened.
    expectations = json.loads(args.expectations.read_text(encoding="utf-8"))
    if expectations.get("pack_sha256") != run["pack_sha256"]:
        raise SystemExit("Expectations file was generated for a different pack.")
    result = score(kernel, expectations)
    if kernel.state.fingerprint() != final_fingerprint:
        raise RuntimeError("Scoring mutated canonical state.")
    report = {
        "schema": SCHEMA,
        "pack": str(args.pack),
        "seed": args.seed,
        "run": run,
        "final_fingerprint": final_fingerprint,
        "expectations_opened_after_cultivation": True,
        "result": result,
        "behavioral_authority": False,
    }
    _print(report)
    if args.out is not None:
        with open(args.out, "x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True, default=sorted)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
