"""Generate the Controls and Boundaries curriculum pack and its expectations.

The pack is ordinary ``verdant.curriculum.pack.v1`` teaching material. It
supplies no P/Q identity, no promotion decision and no answer key. The
expectations are written to a *separate* file that the cultivation path never
reads; a scorer may open it only after cultivation has finished.

Everything is derived from one seed. Labels are meaningless generated tokens
so that no outside knowledge can stand in for what was taught.

    python curriculum_packs/generate_controls_pack_v0.py --out-dir curriculum_packs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

PACK_SCHEMA = "verdant.curriculum.pack.v1"
EXPECTATION_SCHEMA = "verdant.curriculum.expectations.v0"
STATE_DIM = 128
CONSONANTS = "bdfgklmnprstvz"
VOWELS = "aeiou"
RELATIONS = ("feeds", "holds", "follows", "joins", "guides", "anchors")

SHAPES = {
    "chain3": (3, ((0, 1), (1, 2))),
    "fan3": (3, ((0, 1), (0, 2))),
    "collider3": (3, ((0, 2), (1, 2))),
    "triangle3": (3, ((0, 1), (1, 2), (2, 0))),
    "chain4": (4, ((0, 1), (1, 2), (2, 3))),
    "star4": (4, ((0, 1), (0, 2), (0, 3))),
    "pair2": (2, ((0, 1),)),
}

TEMPLATES = (
    "{clauses}.",
    "In this setting, {clauses}.",
    "Seen again, {clauses}.",
    "When the surroundings change, {clauses}.",
    "In another case, {clauses}.",
)


def text_features(text: str, width: int = STATE_DIM) -> list[float]:
    """Deterministic hashed character n-grams (1-4) folded into ``width``."""
    lowered = text.lower()
    counts = [0.0] * width
    for size in (1, 2, 3, 4):
        for start in range(len(lowered) - size + 1):
            gram = lowered[start : start + size]
            digest = hashlib.sha256(f"{size}:{gram}".encode("utf-8")).digest()
            counts[int.from_bytes(digest[:4], "big") % width] += 1.0
    values = [math.log1p(value) for value in counts]
    norm = math.sqrt(sum(value * value for value in values))
    return [round(value / norm, 8) for value in values] if norm else values


class Tokens:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.used: set[str] = set()

    def new(self) -> str:
        while True:
            token = "".join(
                self.rng.choice(CONSONANTS) + self.rng.choice(VOWELS) for _ in range(3)
            )
            if token not in self.used:
                self.used.add(token)
                return token


def build(seed: int, feature_mode: str) -> tuple[dict, dict]:
    rng = random.Random(seed)
    tokens = Tokens(rng)
    families: list[dict] = []

    def family(group: str, shape: str, exposures: int, contexts: int, schedule: str,
               members: list[str] | None = None) -> dict:
        size, edges = SHAPES[shape]
        labels = members or [tokens.new() for _ in range(size)]
        record = {
            "family_id": f"{group}_{len([f for f in families if f['group'] == group]) + 1:02d}",
            "group": group,
            "shape": shape,
            "members": labels,
            "edges": [
                {"source": labels[a], "relation": rng.choice(RELATIONS), "target": labels[b]}
                for a, b in edges
            ],
            "exposures": exposures,
            "distinct_contexts": contexts,
            "schedule": schedule,
        }
        families.append(record)
        return record

    for shape in ("chain3", "fan3", "collider3", "triangle3", "chain4", "star4"):
        family("gate_pass", shape, 5, 3, "interleaved")
    for _ in range(4):
        family("under_exposed", "chain3", 2, 2, "interleaved")
    for _ in range(4):
        family("single_context", "chain3", 5, 1, "interleaved")
    for _ in range(4):
        family("pairs_only", "pair2", 5, 3, "interleaved")
    for _ in range(3):
        left = family("bridged", "chain3", 5, 3, "interleaved")
        shared = left["members"][2]
        family("bridged", "chain3", 5, 3, "interleaved",
               members=[shared, tokens.new(), tokens.new()])
        families[-1]["bridge_concept"] = shared
        left["bridge_concept"] = shared
    for _ in range(4):
        family("blocked_early", "chain3", 5, 3, "blocked_at_start")
    for _ in range(4):
        family("spaced", "chain3", 5, 3, "evenly_spaced")

    def exposure_items(record: dict) -> list[dict]:
        items = []
        for exposure in range(record["exposures"]):
            context = exposure % record["distinct_contexts"]
            clauses = " and ".join(
                f"the {edge['source']} {edge['relation']} the {edge['target']}"
                for edge in (record["edges"] if exposure % 2 == 0 else record["edges"][::-1])
            )
            text = TEMPLATES[exposure % len(TEMPLATES)].format(clauses=clauses)
            text = text[0].upper() + text[1:]
            items.append({
                "family_id": record["family_id"],
                "group": record["group"],
                "exposure": exposure + 1,
                "context_id": f"controls_{record['family_id']}_context_{context + 1}",
                "source_text": text,
                "concepts": list(record["members"]),
                "relations": list(record["edges"]),
                "claims": [],
            })
        return items

    blocked: list[dict] = []
    spaced: list[list[dict]] = []
    pool: list[dict] = []
    for record in families:
        produced = exposure_items(record)
        if record["schedule"] == "blocked_at_start":
            blocked.extend(produced)
        elif record["schedule"] == "evenly_spaced":
            spaced.append(produced)
        else:
            pool.extend(produced)

    distractor_concepts = [tokens.new() for _ in range(16)]
    seen_pairs: set[tuple[str, str]] = set()
    distractors = []
    while len(distractors) < 24:
        a, b = rng.sample(distractor_concepts, 2)
        if (a, b) in seen_pairs or (b, a) in seen_pairs:
            continue
        seen_pairs.add((a, b))
        relation = rng.choice(RELATIONS)
        distractors.append({
            "family_id": f"distractor_{len(distractors) + 1:02d}",
            "group": "distractor",
            "exposure": 1,
            "context_id": f"controls_distractor_context_{len(distractors) + 1}",
            "source_text": f"Once, the {a} {relation} the {b}.",
            "concepts": [a, b],
            "relations": [{"source": a, "relation": relation, "target": b}],
            "claims": [],
        })
    pool.extend(distractors)

    claim_cases = []
    claim_plan = (
        ("affirmed_only", ("affirmed", "affirmed", "affirmed")),
        ("negated_only", ("negated", "negated", "negated")),
        ("contested", ("affirmed", "negated", "affirmed", "negated")),
        ("never_claimed", ()),
    )
    for case, polarities in claim_plan:
        subject, obj = tokens.new(), tokens.new()
        claim_cases.append({"case": case, "subject": subject, "predicate": "holds",
                            "object": obj, "polarities": list(polarities)})
        if not polarities:
            # The two concepts are introduced with an unrelated relation so the
            # labels are known, but no "holds" claim is ever made about them.
            pool.append({
                "family_id": f"claim_{case}", "group": "claims", "exposure": 1,
                "context_id": f"controls_claim_{case}_context_1",
                "source_text": f"The {subject} is near the {obj}.",
                "concepts": [subject, obj],
                "relations": [{"source": subject, "relation": "adjacent_to", "target": obj}],
                "claims": [],
            })
        for index, polarity in enumerate(polarities, start=1):
            wording = "holds" if polarity == "affirmed" else "does not hold"
            pool.append({
                "family_id": f"claim_{case}", "group": "claims", "exposure": index,
                "context_id": f"controls_claim_{case}_context_{index}",
                "source_text": f"A teacher reports that the {subject} {wording} the {obj}.",
                "concepts": [subject, obj],
                "relations": [],
                "claims": [{
                    "subject": subject, "predicate": "holds", "object": obj,
                    "polarity": polarity, "source_class": "human_testimony",
                    "confidence": 0.9,
                    "rationale": "Controls pack fixture; teacher testimony, not observation.",
                    "attributes": {},
                }],
            })

    rng.shuffle(pool)
    # Spaced families: one exposure of each at five evenly separated points.
    ordered: list[dict] = list(blocked)
    slots = 5
    chunk = math.ceil(len(pool) / slots)
    for slot in range(slots):
        for produced in spaced:
            ordered.append(produced[slot])
        ordered.extend(pool[slot * chunk : (slot + 1) * chunk])

    items = []
    for index, raw in enumerate(ordered, start=1):
        item = {
            "item_id": f"controls_{index:04d}",
            "context_id": raw["context_id"],
            "source_text": raw["source_text"],
            "modality": "text",
            "concepts": [{"label": label} for label in raw["concepts"]],
            "relations": [
                {"source": r["source"], "relation": r["relation"], "target": r["target"],
                 "directed": True, "weight": 0.86, "confidence": 0.96}
                for r in raw["relations"]
            ],
            "claims": raw["claims"],
            "confidence": 0.96,
            "provenance": {
                "author": "Claude with Verdant VCpack patterns",
                "source": "Controls and Boundaries pack generator v0",
                "generator_seed": seed,
                "curriculum_role": "control_exposure",
                "control_group": raw["group"],
                "family_id": raw["family_id"],
                "exposure_index": raw["exposure"],
                "truth_status": "synthetic_fixture",
                "direct_observation": False,
                "design_note": "No P/Q identity, promotion, expectation or hidden weight is supplied.",
            },
            "grammar_annotation": {},
            "lexicon_annotation": [],
            "event_key": f"controls-v0-{seed}-{index:04d}",
            "source_ref": f"controls-v0::{raw['group']}::{raw['family_id']}::exposure-{raw['exposure']:02d}",
            "semantic_evidence_kind": "testimony",
        }
        if feature_mode == "text":
            item["feature_vector"] = text_features(raw["source_text"])
        items.append(item)

    probes = []
    for record in families:
        if record["group"] in {"pairs_only"}:
            continue
        probes.append({"test_id": f"probe_{record['family_id']}_full",
                       "cue_labels": list(record["members"]),
                       "notes": "Recorded cue only; not a score and not training evidence."})
        probes.append({"test_id": f"probe_{record['family_id']}_partial",
                       "cue_labels": [record["members"][0], record["members"][-1]],
                       "notes": "Reduced-cue probe; recorded only."})
    gate = [f for f in families if f["group"] == "gate_pass"]
    for left, right in zip(gate, gate[1:]):
        probes.append({"test_id": f"probe_cross_{left['family_id']}_{right['family_id']}",
                       "cue_labels": [left["members"][0], right["members"][0]],
                       "notes": "Cross-family cue. The members were never taught together."})

    section_size = 40
    sections = []
    for start in range(0, len(items), section_size):
        number = start // section_size + 1
        sections.append({
            "section_id": f"controls_phase_{number:02d}",
            "title": f"Controls phase {number}",
            "description": "Interleaved control exposures. Run phases in order; order is part of the design.",
            "enabled": True,
            "language_scaffold": {"grammar_rules": [], "lexicon": [], "notes": ""},
            "items": items[start : start + section_size],
            "tests": probes if start + section_size >= len(items) else [],
        })

    pack = {
        "schema": PACK_SCHEMA,
        "title": "Controls and Boundaries Curriculum 001",
        "description": (
            "A companion to the Vast Developmental Curriculum. It teaches small families that sit "
            "on both sides of the structure-eligibility gates, in several shapes, with shared "
            "concepts, one-off distractors, blocked and spaced schedules, and affirmed, negated, "
            "contested and never-made claims. It never supplies P/Q structures, promotion "
            "decisions or expected outcomes."
        ),
        "state_dim": STATE_DIM,
        "language_scaffold": {"grammar_rules": [], "lexicon": [],
                              "notes": "Empty. Every item supplies explicit concepts, relations and claims."},
        "sections": sections,
        "notes": (
            "All entries are synthetic fixtures with meaningless generated labels. Item order is "
            "deliberate: four families are blocked at the start, four are spaced across the run, "
            "and everything else is shuffled with a fixed seed. Expected outcomes live in a "
            "separate expectations file that cultivation must not read. "
            + ("Feature vectors are hashed character n-grams of source_text, so wording is visible to the field."
               if feature_mode == "text" else
               "No feature vectors are supplied; the Workbench compiler derives its usual label-set slot.")
        ),
    }

    def hard(eligible: bool, reason: str) -> dict:
        return {"kind": "policy_derived", "exact_candidate_promotion_eligible": eligible, "reason": reason}

    expectation_rows = []
    for record in families:
        row = {key: record[key] for key in ("family_id", "group", "shape", "members", "exposures",
                                            "distinct_contexts", "schedule")}
        group = record["group"]
        if group == "gate_pass":
            row["expectation"] = hard(True, "3-8 members, 5 recurrences, 3 contexts: every stated gate is met.")
        elif group == "under_exposed":
            row["expectation"] = hard(False, "2 exposures is below minimum_recurrence_events and minimum_evidence_events (4).")
        elif group == "single_context":
            row["expectation"] = hard(False, "1 context is below minimum_contexts (2).")
        elif group == "pairs_only":
            row["expectation"] = {"kind": "policy_derived", "no_eligible_candidate_contains_both_members": True,
                                  "reason": "2 members is below minimum_members (3)."}
        elif group == "bridged":
            row["bridge_concept"] = record["bridge_concept"]
            row["expectation"] = {"kind": "exploratory", "report": "separate_exact_candidates_or_merged",
                                  "reason": "Policy does not dictate how a shared concept is handled."}
        elif group == "blocked_early":
            row["expectation"] = {"kind": "exploratory", "report": "plastic_associations_alive_at_end",
                                  "reason": "Decay arithmetic suggests early blocked traces fade; not a stated gate."}
        else:
            row["expectation"] = {"kind": "exploratory", "report": "plastic_associations_alive_at_end",
                                  "reason": "Spaced exposure should retain traces if decay behaves as designed."}
        expectation_rows.append(row)

    expectations = {
        "schema": EXPECTATION_SCHEMA,
        "pack_title": pack["title"],
        "generator_seed": seed,
        "feature_mode": feature_mode,
        "assumed_structure_policy": {
            "minimum_members": 3, "maximum_members": 8, "minimum_recurrence_events": 4,
            "minimum_evidence_events": 4, "minimum_contexts": 2,
            "note": "Policy-derived expectations hold only under these default values.",
        },
        "families": expectation_rows,
        "distractor_concepts": distractor_concepts,
        "distractor_expectation": {"kind": "policy_derived",
                                   "no_eligible_candidate_made_only_of_distractor_concepts": True,
                                   "reason": "Each distractor pair occurs once."},
        "claims": [
            {**case,
             "expectation": (
                 {"kind": "policy_derived", "claim_record_exists": False,
                  "reason": "The claim is never made. Absence must not be recorded as a negation."}
                 if case["case"] == "never_claimed" else
                 {"kind": "exploratory",
                  "report": "status_of_each_polarity_and_any_contradiction_record",
                  "reason": "Thresholds decide the status; recorded, not asserted."})}
            for case in claim_cases
        ],
        "must_not_be_read_during_cultivation": True,
    }
    return pack, expectations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=4201)
    parser.add_argument("--features", choices=("text", "labelset"), default="text")
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    pack, expectations = build(args.seed, args.features)
    pack_text = json.dumps(pack, indent=2, ensure_ascii=False) + "\n"
    expectations["pack_sha256"] = hashlib.sha256(pack_text.encode("utf-8")).hexdigest()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    pack_path = args.out_dir / "verdant_controls_and_boundaries_curriculum_001.vcpack"
    expect_path = args.out_dir / "verdant_controls_and_boundaries_curriculum_001.expectations.json"
    pack_path.write_text(pack_text, encoding="utf-8")
    expect_path.write_text(json.dumps(expectations, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    items = sum(len(section["items"]) for section in pack["sections"])
    print(f"wrote {pack_path} ({items} items, {len(pack['sections'])} sections, sha256 {expectations['pack_sha256'][:16]})")
    print(f"wrote {expect_path}")


if __name__ == "__main__":
    main()
