# Controls and Boundaries curriculum pack v0

Research branch: `test/heartbeat-profile-entropy-trace-v0`.

No engine source, policy, checkpoint or existing pack is edited. The Vast
Developmental Curriculum pack is used exactly as supplied.

## Why this exists

The Vast pack is exposure material, and says so: its probes are recorded cues
with no expected outcome. Every one of its 120 families has the same form:
three concepts in a chain (two families use five), five exposures, five
contexts, taught in one uninterrupted block, weight 0.86 and confidence 0.96
throughout. That sits just above every default structure gate
(`minimum_members` 3, `minimum_recurrence_events` 4, `minimum_contexts` 2), so
the pack shows that eligible families form. It contains nothing that should
*not* form, nothing taught out of block order, and no stated outcome that a
run could contradict.

This pack adds those cases, with expectations kept in a separate file.

## New files

- `curriculum_packs/generate_controls_pack_v0.py` — seeded generator.
- `curriculum_packs/verdant_controls_and_boundaries_curriculum_001.vcpack` —
  183 items in 5 ordered phases, ordinary `verdant.curriculum.pack.v1`.
  Labels are meaningless generated tokens and do not overlap the Vast pack.
- `curriculum_packs/verdant_controls_and_boundaries_curriculum_001.expectations.json`
  — expected outcomes. Cultivation never reads it.
- `run_observer_pack_expectations.py` — observer-only scorer. It opens the
  expectations only after cultivation ends and the fingerprint is recorded.
- `curriculum_packs/reports/` — the two recorded runs.

## What the pack contains

| Group | Families | Design | Expectation |
|---|---:|---|---|
| gate_pass | 6 | chain, fan, collider, triangle, 4-chain, 4-star; 5 exposures, 3 contexts, interleaved | policy-derived: eligible |
| under_exposed | 4 | 2 exposures | policy-derived: not eligible |
| single_context | 4 | 5 exposures, 1 context | policy-derived: not eligible |
| pairs_only | 4 | 2 concepts | policy-derived: no eligible candidate holds both |
| bridged | 6 | 3 pairs of chains sharing one concept | exploratory |
| blocked_early | 4 | chain, 5 exposures in a row at the start | exploratory |
| spaced | 4 | chain, 5 exposures spread across the run | exploratory |
| distractors | 24 items | one-off pairs among 16 concepts | policy-derived: none eligible |
| claims | 4 cases | affirmed only, negated only, contested, never claimed | never-claimed is policy-derived |

Feature vectors are hashed character n-grams of `source_text` (width 128), so
wording is visible to the field. The Workbench default, used by the Vast
pack, is a one-hot slot chosen by hashing the sorted label set: all five
exposures of a family then look identical, and 81 of the Vast pack's 120
label sets share a slot with an unrelated family.

## Observed

Default policies, state_dim 128, fingerprint sidecar on. Kernel seeds 2301
and 7 gave the same counts.

| Group | Exact candidate | Exact and eligible | Traces alive at end | Scored |
|---|---:|---:|---:|---|
| gate_pass (6) | 3 | 0 | 5 | 0/6 |
| under_exposed (4) | 1 | 0 | 3 | 4/4 |
| single_context (4) | 3 | 0 | 4 | 4/4 |
| pairs_only (4) | 0 | 0 | 4 | 4/4 |
| bridged (6) | 3 | 0 | 6 | reported |
| blocked_early (4) | 4 | 4 | 0 | reported |
| spaced (4) | 0 | 0 | 4 | reported |

Policy-derived checks passed: 14 of 20. All six failures are the gate_pass
families. No distractor-only candidate became eligible.

Claims: affirmed-only and negated-only each reached `confirmed` (support
0.9027). The contested case left both polarities `contested` (0.7884 each)
with one active contradiction record. The never-claimed pair has no claim
record.

Order comparison on the Vast pack, first 120 items (24 families):

| Order | Eligible candidates |
|---|---:|
| As supplied (each family in a block of five) | 24 of 25 |
| Families interleaved within a section (gap of 4 items) | 23 of 25 |

First 240 items of the Vast pack as supplied: 48 of 48 families had an exact
candidate, 46 exact and eligible, plus 2 eligible five-member candidates that
merge two families sharing `actuator`. 27 of the 50 candidates had no living
plastic association left by item 240.

## Claim boundary

**OBSERVED:** In this pack, the only families that became promotion-eligible
were the four taught in an uninterrupted block. Families with the same
shape, exposures and contexts spread across the run produced no candidate.
Six families that meet every membership, recurrence and context gate, taught
interleaved at an average gap of roughly 36 items, did not become eligible.
A gap of 4 items on the Vast pack did not prevent eligibility. Candidates
stay `eligible` after every association that supported them has decayed.
The under-exposed, single-context, pair and distractor controls behaved as
the stated gates require.

**IMPLEMENTED-EXPERIMENTAL:** The generator, pack, expectations file and
observer scorer.

**PROPOSED:** (1) Run the full Vast pack in a spaced order to find the gap at
which formation stops. (2) Decide whether an `eligible` candidate whose
traces are gone should still be promotable. (3) Decide whether massed-only
formation is intended; if not, the decay rate, the strength gate, or a
review schedule are the levers, and each needs its own predeclared test.

**MISSING:** No promotion, compilation or probe scoring: this stops at
candidate eligibility. One generated pack, two kernel seeds, no variation of
pack seed. The cause of the gate_pass failures is not isolated; spacing is
the leading explanation because of the blocked-versus-spaced contrast, but
shape and text features differ from the Vast pack too. The interleaved Vast
comparison covers only 120 items. Nothing here was run on Windows or through
the Workbench queue.
