"""Long-life curriculum v1: v0 plus a world that changes after it was learned.

v1 adds four groups to v0 (v0 itself is unchanged, so old packs reproduce byte for byte):

  reversed       a 4-member family is taught 5 times in 3 contexts; after a pause of 20-40
                 lessons the world changes for good: one member is replaced by a new concept,
                 6 more exposures in 3 contexts. The old family no longer describes the world.
  reversed3      the same with a 3-member family (Milestone 18 cannot revise below 3 members,
                 so the honest expected outcome there is UNRESOLVED).
  intermittent   control: taught 5 times; after the pause, 6 more exposures alternating whole
                 and missing one member (incomplete sightings, no replacement, no change of world).
  stable_late    control: taught 5 times; after the pause, 6 more whole exposures.


A life is a stream of lessons with the properties real experience has and a tidy
curriculum does not: things that recur at uneven gaps, things met once and never again,
things that come back after a long silence, things taught in only one setting, and claims
that are affirmed, denied, contested, reversed late, or never made.

Same rules as the Controls pack: ordinary ``verdant.curriculum.pack.v1`` material, labels
are meaningless generated tokens, no P/Q identity, promotion decision or answer key is in
the pack, and the expectations file must not be read by cultivation.

    python curriculum_packs/generate_long_life_pack_v0.py --lessons 2500 --seed 9001 --out-dir curriculum_packs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_controls_pack_v0 import (EXPECTATION_SCHEMA, PACK_SCHEMA, RELATIONS, SHAPES,  # noqa: E402
                                       STATE_DIM, TEMPLATES, Tokens, text_features)

# group -> (share of lessons, exposures, contexts, schedule, shapes)
PLAN = {
    "massed":         (0.14, 5, 3, "five exposures inside about 8 lessons", ("chain3", "fan3", "triangle3")),
    "spaced_short":   (0.19, 5, 3, "gaps of 6-14 lessons", ("chain3", "collider3", "chain4")),
    "spaced_long":    (0.19, 5, 3, "gaps of 30-90 lessons", ("chain3", "fan3", "star4")),
    "returning":      (0.10, 8, 3, "4 exposures, a silence of 250+ lessons, 4 more", ("chain3", "triangle3")),
    "under_exposed":  (0.07, 2, 2, "two exposures, gap 6-40 lessons", ("chain3",)),
    "single_context": (0.08, 5, 1, "gaps of 6-14 lessons, one context only", ("chain3",)),
    "once":           (0.07, 1, 1, "met once, never again", ("chain3", "fan3")),
    "pairs_only":     (0.03, 5, 3, "gaps of 6-14 lessons, two members", ("pair2",)),
    "reversed":       (0.13, 11, 3, "5 whole, pause 20-40, then 6 with one member replaced", ("chain4", "star4")),
    "reversed3":      (0.06, 11, 3, "5 whole, pause 20-40, then 6 with one member replaced", ("chain3", "fan3")),
    "intermittent":   (0.09, 11, 3, "5 whole, pause 20-40, then 6 alternating whole / one member missing", ("chain4", "star4")),
    "stable_late":    (0.09, 11, 3, "5 whole, pause 20-40, then 6 more whole", ("chain4", "star4")),
}
LATE = ("reversed", "reversed3", "intermittent", "stable_late")
DISTRACTOR_SHARE = 0.12


def build(lessons: int, seed: int) -> tuple[dict, dict]:
    rng = random.Random(seed); tokens = Tokens(rng)
    families: list[dict] = []; stream: list[tuple[float, int, dict]] = []; tie = 0

    def place(position: float, raw: dict) -> None:
        nonlocal tie
        tie += 1; stream.append((min(max(position, 0.0), lessons - 1e-6), tie, raw))

    def positions(group: str, exposures: int) -> list[float]:
        if group == "massed":
            gaps = [rng.uniform(1, 2.5) for _ in range(exposures - 1)]
        elif group in ("spaced_short", "single_context", "pairs_only"):
            gaps = [rng.uniform(6, 14) for _ in range(exposures - 1)]
        elif group == "spaced_long":
            gaps = [rng.uniform(30, 90) for _ in range(exposures - 1)]
        elif group == "returning":
            silence = rng.uniform(250, max(260, min(900, lessons * 0.45)))
            gaps = [rng.uniform(6, 14) for _ in range(3)] + [silence] + [rng.uniform(6, 14) for _ in range(3)]
        elif group in LATE:
            gaps = [rng.uniform(6, 14) for _ in range(4)] + [rng.uniform(20, 40)] + [rng.uniform(6, 14) for _ in range(5)]
        elif group == "under_exposed":
            gaps = [rng.uniform(6, 40)]
        else:
            gaps = []
        span = sum(gaps); start = rng.uniform(0, max(1.0, lessons - span - 1))
        out = [start]
        for gap in gaps:
            out.append(out[-1] + gap)
        return out

    for group, (share, exposures, contexts, schedule, shapes) in PLAN.items():
        count = max(2, round(lessons * share / exposures))
        for index in range(count):
            shape = shapes[index % len(shapes)]; size, edges = SHAPES[shape]
            labels = [tokens.new() for _ in range(size)]
            late_members = None; late_edges = None
            if group in LATE:
                gone = size - 1                                   # the last member (a chain end or a star leaf)
                anchor = next(a for a, b in edges if b == gone)   # the member it hung from
                if group in ("reversed", "reversed3"):
                    newcomer = tokens.new()
                    late_members = labels[:gone] + [newcomer]
                    late_edges_idx = [(a, b) for a, b in edges if b != gone] + [(anchor, gone)]
                else:
                    late_members = list(labels); late_edges_idx = list(edges)
            record = {"family_id": f"{group}_{index + 1:04d}", "group": group, "shape": shape, "members": labels,
                      "edges": [{"source": labels[a], "relation": rng.choice(RELATIONS), "target": labels[b]} for a, b in edges],
                      "exposures": exposures, "distinct_contexts": contexts, "schedule": schedule}
            where = positions(group, exposures)
            if where[-1] > lessons - 1:      # would run off the end of the life: leave it out entirely
                continue
            if group in LATE:
                late = list(late_members)
                late_rel = [{"source": late[a], "relation": record["edges"][i]["relation"] if i < len(record["edges"]) else rng.choice(RELATIONS),
                             "target": late[b]} for i, (a, b) in enumerate(late_edges_idx)]
                record["late_members"] = late; record["late_edges"] = late_rel; record["change_after_exposure"] = 5
            families.append(record)
            for exposure, position in enumerate(where):
                members, rel = list(labels), list(record["edges"])
                if group in LATE and exposure >= 5:
                    members, rel = list(record["late_members"]), list(record["late_edges"])
                    if group == "intermittent" and exposure % 2 == 0:      # every other late sighting misses one member
                        gone_label = labels[-1]
                        members = [m for m in members if m != gone_label]
                        rel = [e for e in rel if gone_label not in (e["source"], e["target"])]
                clauses = " and ".join(f"the {e['source']} {e['relation']} the {e['target']}"
                                       for e in (rel if exposure % 2 == 0 else rel[::-1]))
                text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
                place(position, {"family_id": record["family_id"], "group": group, "exposure": exposure + 1,
                                 "context_id": f"life_{record['family_id']}_context_{exposure % contexts + 1}",
                                 "source_text": text[0].upper() + text[1:], "concepts": members,
                                 "relations": rel, "claims": []})

    distractor_concepts = [tokens.new() for _ in range(max(16, lessons // 12))]
    for index in range(round(lessons * DISTRACTOR_SHARE)):
        a, b = rng.sample(distractor_concepts, 2); relation = rng.choice(RELATIONS)
        place(rng.uniform(0, lessons), {"family_id": f"distractor_{index + 1:04d}", "group": "distractor", "exposure": 1,
                                        "context_id": f"life_distractor_context_{index + 1}",
                                        "source_text": f"Once, the {a} {relation} the {b}.", "concepts": [a, b],
                                        "relations": [{"source": a, "relation": relation, "target": b}], "claims": []})

    claim_cases = []
    claim_plan = (("affirmed_only", ("affirmed",) * 3, "any"), ("negated_only", ("negated",) * 3, "any"),
                  ("contested", ("affirmed", "negated", "affirmed", "negated"), "any"),
                  ("reversed_late", ("affirmed",) * 3 + ("negated",) * 3, "split"), ("never_claimed", (), "any"))
    for repeat in range(max(1, lessons // 600)):
        for case, polarities, layout in claim_plan:
            subject, obj = tokens.new(), tokens.new(); name = f"{case}_{repeat + 1:02d}"
            claim_cases.append({"case": name, "kind": case, "subject": subject, "predicate": "holds", "object": obj,
                                "polarities": list(polarities)})
            if not polarities:
                place(rng.uniform(0, lessons), {"family_id": f"claim_{name}", "group": "claims", "exposure": 1,
                      "context_id": f"life_claim_{name}_context_1", "source_text": f"The {subject} is near the {obj}.",
                      "concepts": [subject, obj], "relations": [{"source": subject, "relation": "adjacent_to", "target": obj}], "claims": []})
            base = rng.uniform(0, lessons * 0.4)
            for index, polarity in enumerate(polarities, start=1):
                late = layout == "split" and index > len(polarities) // 2
                position = (lessons * 0.6 if late else base) + index * rng.uniform(4, 12)
                wording = "holds" if polarity == "affirmed" else "does not hold"
                place(position, {"family_id": f"claim_{name}", "group": "claims", "exposure": index,
                      "context_id": f"life_claim_{name}_context_{index}",
                      "source_text": f"A teacher reports that the {subject} {wording} the {obj}.", "concepts": [subject, obj],
                      "relations": [], "claims": [{"subject": subject, "predicate": "holds", "object": obj, "polarity": polarity,
                                                   "source_class": "human_testimony", "confidence": 0.9,
                                                   "rationale": "Long-life pack fixture; teacher testimony, not observation.",
                                                   "attributes": {}}]})

    stream.sort(key=lambda entry: (entry[0], entry[1]))
    last_lesson: dict[str, int] = {}; items = []
    for index, (_position, _tie, raw) in enumerate(stream, start=1):
        last_lesson[raw["family_id"]] = index
        items.append({
            "item_id": f"life_{index:05d}", "context_id": raw["context_id"], "source_text": raw["source_text"], "modality": "text",
            "concepts": [{"label": label} for label in raw["concepts"]],
            "relations": [{"source": r["source"], "relation": r["relation"], "target": r["target"], "directed": True,
                           "weight": 0.86, "confidence": 0.96} for r in raw["relations"]],
            "claims": raw["claims"], "confidence": 0.96,
            "provenance": {"author": "Claude with Verdant VCpack patterns", "source": "Long-life pack generator v1",
                           "generator_seed": seed, "curriculum_role": "life_exposure", "control_group": raw["group"],
                           "family_id": raw["family_id"], "exposure_index": raw["exposure"], "truth_status": "synthetic_fixture",
                           "direct_observation": False,
                           "design_note": "No P/Q identity, promotion, expectation or hidden weight is supplied."},
            "grammar_annotation": {}, "lexicon_annotation": [], "event_key": f"life-v1-{seed}-{index:05d}",
            "source_ref": f"life-v1::{raw['group']}::{raw['family_id']}::exposure-{raw['exposure']:02d}",
            "semantic_evidence_kind": "testimony", "feature_vector": text_features(raw["source_text"]),
        })

    sections = [{"section_id": f"life_phase_{start // 40 + 1:03d}", "title": f"Life phase {start // 40 + 1}",
                 "description": "A stretch of one continuous life. Run phases in order; order is the design.",
                 "enabled": True, "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": ""},
                 "items": items[start:start + 40], "tests": []} for start in range(0, len(items), 40)]
    pack = {"schema": PACK_SCHEMA, "title": f"Long Life Curriculum 001 v1, a changing world ({len(items)} lessons, seed {seed})",
            "description": ("One continuous life of generated lessons: massed, spaced, returning, under-exposed, single-context "
                            "and one-off families, one-off distractor pairs, and affirmed, denied, contested, late-reversed and "
                            "never-made claims. It never supplies P/Q structures, promotion decisions or expected outcomes."),
            "state_dim": STATE_DIM, "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": "Empty."},
            "sections": sections,
            "notes": "Synthetic fixtures with meaningless labels. Expected outcomes live in a separate file cultivation must not read."}

    def hard(eligible: bool, reason: str) -> dict:
        return {"kind": "policy_derived", "exact_candidate_promotion_eligible": eligible, "reason": reason}

    reasons = {"massed": hard(True, "5 recurrences, 3 contexts: every stated gate is met."),
               "spaced_short": hard(True, "5 recurrences, 3 contexts: every stated gate is met; only the spacing differs."),
               "spaced_long": hard(True, "5 recurrences, 3 contexts: every stated gate is met; only the spacing differs."),
               "returning": hard(True, "8 recurrences, 3 contexts: every stated gate is met, across a long silence."),
               "under_exposed": hard(False, "2 exposures is below minimum_recurrence_events (4)."),
               "single_context": hard(False, "1 context is below minimum_contexts (2)."),
               "once": hard(False, "1 exposure is below minimum_recurrence_events (4)."),
               "pairs_only": {"kind": "policy_derived", "no_eligible_candidate_contains_both_members": True,
                              "reason": "2 members is below minimum_members (3)."},
               "reversed": hard(True, "5 whole recurrences in 3 contexts before the change: every stated gate is met."),
               "reversed3": hard(True, "5 whole recurrences in 3 contexts before the change: every stated gate is met."),
               "intermittent": hard(True, "5 whole recurrences in 3 contexts: every stated gate is met."),
               "stable_late": hard(True, "11 whole recurrences in 3 contexts: every stated gate is met.")}
    rows = [{**{key: record[key] for key in ("family_id", "group", "shape", "members", "exposures", "distinct_contexts", "schedule")},
             "last_lesson": last_lesson[record["family_id"]], "expectation": reasons[record["group"]]} for record in families]
    # the changed world: what each late family is after the change, and what a correct revision may produce
    change_lesson = {}
    for index, (_p, _t, raw) in enumerate(stream, start=1):
        if raw["group"] in LATE and raw["exposure"] == 6:
            change_lesson[raw["family_id"]] = index
    for row, record in zip(rows, families):
        if record["group"] in LATE:
            row["late_members"] = record["late_members"]; row["change_lesson"] = change_lesson[record["family_id"]]
            if record["group"] in ("reversed", "reversed3"):
                kept = [m for m in record["members"] if m in record["late_members"]]
                row["revision"] = {"departed": [m for m in record["members"] if m not in record["late_members"]],
                                   "allowed_revision": kept if len(kept) >= 3 else None,
                                   "should_revise": len(kept) >= 3,
                                   "reason": ("After the change the departed member never co-occurs again; the old fold is out of date. "
                                              "Milestone 18 can revise to the remaining members." if len(kept) >= 3 else
                                              "After the change the old fold is out of date, but Milestone 18 cannot revise below "
                                              "3 members: the honest outcome is UNRESOLVED.")}
                rows.append({"family_id": record["family_id"] + "_after", "group": record["group"] + "_after", "shape": record["shape"],
                             "members": record["late_members"], "exposures": 6, "distinct_contexts": 3,
                             "schedule": "the changed family", "last_lesson": last_lesson[record["family_id"]],
                             "expectation": hard(True, "6 recurrences in 3 contexts after the change: every stated gate is met.")})
            else:
                row["revision"] = {"departed": [], "allowed_revision": None, "should_revise": False,
                                   "reason": "The world did not change; incomplete sightings are not a contradiction."}
    expectations = {
        "schema": EXPECTATION_SCHEMA, "pack_title": pack["title"], "generator_seed": seed, "lessons": len(items),
        "assumed_structure_policy": {"minimum_members": 3, "maximum_members": 8, "minimum_recurrence_events": 4,
                                     "minimum_evidence_events": 4, "minimum_contexts": 2,
                                     "note": "Policy-derived expectations hold only under these default values."},
        "families": rows, "distractor_concepts": distractor_concepts,
        "distractor_expectation": {"kind": "policy_derived", "no_eligible_candidate_made_only_of_distractor_concepts": True,
                                   "reason": "Distractor pairs are drawn at random; a pair may recur by chance but no triple is taught."},
        "claims": [{**case, "last_lesson": last_lesson.get(f"claim_{case['case']}", 0),
                    "expectation": ({"kind": "policy_derived", "claim_record_exists": False,
                                     "reason": "The claim is never made. Absence must not be recorded as a negation."}
                                    if case["kind"] == "never_claimed" else
                                    {"kind": "exploratory", "report": "status_of_each_polarity_and_any_contradiction_record",
                                     "reason": "Thresholds decide the status; recorded, not asserted."})} for case in claim_cases],
        "must_not_be_read_during_cultivation": True,
    }
    return pack, expectations


def write(lessons: int, seed: int, out_dir: Path) -> tuple[Path, Path]:
    pack, expectations = build(lessons, seed)
    text = json.dumps(pack, indent=1, ensure_ascii=False) + "\n"
    expectations["pack_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"verdant_changing_life_{lessons}_seed{seed}"
    pack_path, expect_path = out_dir / f"{stem}.vcpack", out_dir / f"{stem}.expectations.json"
    pack_path.write_text(text, encoding="utf-8")
    expect_path.write_text(json.dumps(expectations, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return pack_path, expect_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lessons", type=int, default=2500); parser.add_argument("--seed", type=int, default=9001)
    parser.add_argument("--out-dir", type=Path, default=Path("curriculum_packs"))
    args = parser.parse_args()
    pack_path, expect_path = write(args.lessons, args.seed, args.out_dir)
    pack = json.loads(pack_path.read_text(encoding="utf-8")); counts: dict[str, int] = {}
    for section in pack["sections"]:
        for item in section["items"]:
            counts[item["provenance"]["control_group"]] = counts.get(item["provenance"]["control_group"], 0) + 1
    print(f"wrote {pack_path} ({sum(counts.values())} lessons, {len(pack['sections'])} phases)\nwrote {expect_path}\nlessons by kind: {counts}")


if __name__ == "__main__":
    main()
