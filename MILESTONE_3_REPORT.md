# Verdant Minds Independent Rebuild — Milestone 3

## Evidence-Safe Claims, Contradictions, and Revision

Milestone 3 adds a first-class epistemic layer to the canonical Verdant kernel.

The purpose of this milestone is to let Verdant preserve opposing claims, identify that they conflict, distinguish where their support came from, prefer one claim when the weighted evidence justifies it, and revise its current belief without deleting its prior belief or evidence.

This milestone uses controlled direct-observation and physical-outcome declarations passed through CognitiveChunk v2 so the claim machinery can be tested before live native media is connected.

## What was added

### Canonical typed claims

Claims are now separate from ordinary graph relations. A claim contains:

- subject concept;
- predicate;
- object concept;
- affirmed or negated polarity;
- support ledger;
- refutation ledger;
- support, refutation, and net scores;
- current status;
- evidence-preserving supersession history.

Claims with opposite polarity share one canonical claim key. This lets the kernel recognize that:

- `door has_property open`
- `door does not have_property open`

are opposed claims about the same underlying proposition rather than unrelated relations.

### Epistemic source classes

Every claim-support event carries an explicit source class:

- direct observation;
- physical outcome;
- self action;
- human testimony;
- external testimony;
- system inference;
- translation.

The default policy weights are persisted in the checkpoint:

| Source class | Default weight |
|---|---:|
| Physical outcome | 0.98 |
| Direct observation | 0.90 |
| Self action | 0.85 |
| Human testimony | 0.60 |
| External testimony | 0.50 |
| System inference | 0.40 |
| Translation | 0.20 |

These values are an explicit experimental policy, not a claim that one source class is universally truthful. They are inspectable, versioned, and replaceable.

### Bounded evidence accumulation

Independent evidence accumulates through a saturating score:

```text
score = 1 - product(1 - effective_weight_i)
```

This keeps scores in `[0, 1]`, lets repeated independent evidence strengthen a claim, and avoids unbounded confidence growth.

### Support and refutation ledgers

Evidence supporting one polarity is preserved as refuting evidence for the opposite polarity.

The original evidence record is not copied into a rewritten historical narrative. Both claims point to the same preserved evidence through opposite ledger stances.

### Localized contradictions

When both polarities have support, the kernel creates one canonical contradiction record containing:

- both claim IDs;
- detection and update cycles;
- all relevant evidence references;
- whether the conflict remains active or has a weighted preference;
- the currently preferred claim, if any;
- the latest revision event.

Equal or near-equal evidence leaves the contradiction active with no current belief.

### Revision without erasure

When the preferred claim changes, the kernel creates an immutable revision record containing:

- prior claim;
- replacement claim;
- contradiction ID;
- cycle;
- evidence references;
- policy snapshot;
- reason for the revision.

The prior claim remains in the claim store with its original support ledger. It is marked revised and points to the claim that superseded it.

### Queryable belief and history

The kernel now exposes:

- `current_belief(subject, predicate, object)`;
- `claim_history(subject, predicate, object)`;
- canonical contradiction records;
- canonical revision records.

This distinguishes current belief from historical belief.

### Language integration

Milestone 2 grammar frames now also create typed claims:

- transitive action claims;
- property claims with preserved negation;
- temporal-before claims.

The older canonical relations remain available as structural graph views, while claims carry epistemic conflict and revision semantics.

## Controlled demonstration

The demonstration performs two contradiction tests.

### Door claim

1. Handwritten teacher testimony says the door is open.
2. A controlled direct-observation declaration says the door is closed.
3. A controlled physical-outcome declaration says forward motion was blocked at the door.
4. The teacher repeats that the door is open.

Result:

- both affirmed and negated claims remain stored;
- the contradiction remains inspectable;
- the negated claim is the current preferred claim;
- one revision records the change away from the earlier affirmative belief;
- testimony is not erased;
- direct observation and outcome evidence are not overwritten by later testimony.

The final negated door claim has a net score of approximately `0.1829` under the current experimental policy.

### Indicator claim

Two equally weighted controlled direct observations support opposite claims about whether an indicator is bright.

Result:

- both claims remain contested;
- the contradiction has no preferred claim;
- `current_belief(...)` returns no answer rather than forcing a choice.

## Demonstration state

- cycles: 23
- evidence records: 69
- canonical concepts: 25
- canonical relations: 12
- canonical claims: 4
- localized contradictions: 2
- revision records: 1
- field history frames: 23
- directed relation density: 0.02
- controlled claim CognitiveChunk archives: 4

## Test result

```text
31 passed
```

The eight new Milestone 3 tests verify:

- opposing handwritten claims are localized without overwrite;
- direct observation can outweigh one human testimony;
- a belief change creates a revision record;
- physical outcome strengthens a claim without deleting conflict history;
- repeated independent testimony can change the balance while preserving observation;
- claims cannot be promoted without explicit semantic evidence;
- support and refutation ledgers share the original preserved evidence;
- checkpoint round-trip preserves claims, contradictions, revisions, and current belief;
- identical claim sequences replay deterministically.

## Bug found during testing

The first controlled-observation wrapper attempted to add generic `claim_participant` attributes to existing concepts. Because concept attributes merge canonically, this overwrote the existing `lexeme` kind on `door` and `open`, causing later language lessons to stop parsing.

The test exposed this cross-layer identity corruption immediately.

The wrapper was corrected so claim registration reuses existing concepts without changing their established type. This is exactly why the rebuild is proceeding through narrow tested milestones.

## Important boundaries

Milestone 3 does not establish:

- live sensory grounding;
- live physical-outcome grounding;
- infallibility of direct observation;
- universal correctness of the current source weights;
- unrestricted logic;
- automatic causal discovery;
- autonomous truth;
- consciousness.

A source class changes evidential weight; it does not create truth by declaration.

## Next milestone

Milestone 4 should rebuild the continuous field and its bridge to canonical claims and relations.

The next target is:

> **Pure Persistent ECWF and Evidence-Bounded Resonance**

It should add:

- exact ECWF checkpoint continuity;
- nonmutating sensitivity and counterfactual tests;
- collision-resistant concept-to-field addressing;
- separation of evidence support from resonance strength;
- resonance that may retrieve or rank claims but cannot create them;
- trace attribution showing graph evidence, field contribution, and final selection separately;
- controlled tests where high resonance conflicts with weak evidence;
- controlled tests where repeated evidence changes future field response without inventing relations.

This is the required step before shard routing, compaction, active workspace, or live sensory streams.
