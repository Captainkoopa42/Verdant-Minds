# Verdant Minds Independent Rebuild — Milestone 7 Report

## Earned Proto-Object Formation

Milestone 7 adds the first evidence-preserving object-development pathway to the clean-room Verdant rebuild.

The implementation contains no LLM, pretrained vision-language model, object detector, labeled embedding model, or human-supplied object identity in the learning loop. The controlled demonstration uses numerical sensory features so that the identity and promotion rules can be tested before raw camera decoding is introduced.

## Constitutional purpose

A label must not create an object. Objecthood must be earned from a continuing pattern of experience.

Milestone 7 therefore enforces:

> A sensory pattern may remain a fluid identity candidate while evidence accumulates. It becomes a canonical proto-object only after recurrence, temporal persistence, transformation continuity, common motion, occlusion and reappearance, causal interaction, preserved provenance, and Council authorization satisfy explicit gates.

Tracking hypotheses do not automatically enter the canonical concept graph.

## Architecture

```text
native sensory evidence
        │
        ▼
controlled continuous feature observation
        │
        ▼
pure candidate-association inspection
 appearance + predicted position + motion + continuity
        │
        ├── associate with an existing candidate
        ├── create a separate candidate
        └── preserve ambiguity rather than force identity
        │
        ▼
persistent nonsemantic candidate history
 recurrence + persistence + transformation
 common motion + occlusion/reappearance + consequence
        │
        ▼
pure objecthood-promotion inspection
        │
        ▼
Data King + Forefront King + Ethics King
        │
        ▼
Council-authorized canonical proto-object
        │
        ▼
machine identity retaining every source observation
```

The object candidate layer is persistent and inspectable but remains outside the canonical concept, relation, and claim stores until promotion.

## Implemented records

### `ObjecthoodPolicy`

Persists:

- appearance, position, and motion association limits;
- association and ambiguity thresholds;
- maximum normal and occlusion frame gaps;
- minimum observations and independent episodes;
- minimum persistence, transformation, common-motion, reappearance, and causal counts;
- weighted support components;
- ambiguity penalty;
- minimum objecthood support score;
- policy revision.

These are experimental operating values, not universal cognitive constants.

### `ObjectObservationInput` and `ObjectObservationRecord`

Each retained event carries:

- episode and frame identity;
- exact native evidence reference;
- modality;
- visible, occluded, or causal-outcome kind;
- continuous appearance features;
- position and motion when visible;
- common-motion support;
- optional target candidate for occlusion or physical consequence;
- immutable metadata and commit cycle.

### `ObjectCandidateRecord`

Each candidate preserves:

- every observation and evidence reference;
- every episode in which it occurred;
- running appearance centroid;
- latest position and motion;
- visible-observation count;
- temporal-persistence count;
- transformation-continuity count;
- common-motion count;
- occlusion and reappearance counts;
- causal-interaction count;
- ambiguity count and competing candidates;
- decomposed support score;
- promotion lineage when earned.

### `ObjectObservationReport`

Observation inspection is pure. It lists every candidate considered and decomposes:

- appearance similarity;
- predicted-position fit;
- motion alignment;
- episode continuity;
- eligibility and rejection codes.

The report contains the complete proposed next candidate state and a structural fingerprint. Altered or stale reports cannot be committed.

### `ObjectPromotionReport` and `ObjectPromotionEvent`

Promotion inspection checks every objecthood gate. Commitment requires:

- an eligible report;
- the unchanged candidate snapshot;
- the full evidence lineage;
- an untampered structural fingerprint;
- a Council decision authorizing the exact operation.

Promotion creates one machine-named concept such as:

```text
proto-object-cd5a5fe8c688
```

It does not install a human category such as `cup`, `toy`, or `ball`.

## Support score

The current experimental score is:

\[
Q = 0.15R + 0.20P + 0.15T + 0.15M + 0.15O + 0.20C - 0.20A
\]

where:

- \(R\) = recurrence across episodes;
- \(P\) = temporal persistence;
- \(T\) = continuity across appearance transformation;
- \(M\) = common-motion support;
- \(O\) = occlusion and reappearance support;
- \(C\) = causal interaction evidence;
- \(A\) = unresolved identity ambiguity.

A high score alone is insufficient. Promotion separately requires all configured minimum counts and no unresolved ambiguity.

## Controlled demonstration

The demonstration presented one unnamed sensory pattern through:

1. initial appearance;
2. several changed appearances along a continuous trajectory;
3. common motion;
4. temporary occlusion;
5. reappearance at the predicted continuation;
6. recurrence in a second episode;
7. further transformation;
8. a physical outcome tied to the candidate.

A second pattern was intentionally made visually similar but placed on an incompatible trajectory with opposite motion.

### Main candidate

| Measurement | Result |
|---|---:|
| Visible observations | 6 |
| Independent episodes | 2 |
| Persistence count | 4 |
| Transformation count | 4 |
| Common-motion count | 5 |
| Occlusion count | 1 |
| Reappearance count | 1 |
| Causal-interaction count | 1 |
| Evidence records retained | 8 |
| Support score | 1.000000 |

Every support component reached its configured threshold.

### Similar lookalike

The visually similar but kinematically inconsistent pattern formed a separate candidate.

```text
candidate A != candidate B
```

Candidate B retained Candidate A as a considered competitor, but its incompatible predicted position and motion prevented an automatic identity merge.

### Semantic boundary

Before objecthood promotion:

| Canonical store | Count |
|---|---:|
| Concepts | 0 |
| Relations | 0 |
| Claims | 0 |

After Council-authorized promotion:

| Canonical store | Count |
|---|---:|
| Concepts | 1 |
| Relations | 0 |
| Claims | 0 |

Tracking therefore created no semantic truth. Promotion created exactly one earned proto-object concept.

The concept retains:

- candidate identity;
- complete observation IDs;
- complete evidence references;
- episode lineage;
- support score and components;
- policy revision;
- an explicit statement that no semantic category was preinstalled.

## Demonstration state

| Measurement | Result |
|---|---:|
| Developmental cycles | 20 |
| Evidence records | 19 |
| Object observations | 9 |
| Object candidates | 2 |
| Promoted proto-objects | 1 |
| Canonical concepts | 1 |
| Canonical relations | 0 |
| Claims | 0 |
| Council decisions | 1 |
| Field-history frames | 9 |
| Exact checkpoint reload | Passed |

## Tests

Milestone 7 adds twelve tests. The complete suite result is:

```text
77 passed
```

The new tests cover:

1. native evidence preservation without semantic promotion;
2. transformation continuity across changed appearances;
3. separation of a similar pattern with incompatible motion;
4. occlusion and reappearance continuity;
5. rejection of repetition alone as objecthood;
6. complete temporal and causal eligibility;
7. mandatory Council authorization;
8. machine-named, evidence-backed promotion;
9. pure observation inspection;
10. stale and tampered report rejection;
11. exact checkpoint recovery;
12. deterministic developmental replay.

All previous CognitiveChunk, canonical kernel, language, claim, ECWF, governance, and shard tests remain passing.

## What this milestone establishes

Milestone 7 demonstrates that the rebuilt Verdant can:

- retain unnamed sensory identity candidates outside the semantic graph;
- associate changed appearances through temporal and kinematic continuity;
- preserve occlusion and reappearance as identity evidence;
- distinguish a similar-looking pattern when its motion and position disagree;
- accumulate support across independent episodes;
- include physical consequence in objecthood evidence;
- refuse promotion when only repetition is present;
- require Council authorization for structural commitment;
- create a machine identity without assigning a human object class;
- preserve the complete source path through checkpoints;
- reproduce the same development deterministically.

This is the first rebuilt pathway where a canonical structure is earned from temporal and causal evidence rather than directly proposed by a handwritten symbolic curriculum.

## Important boundary

This milestone does **not** yet demonstrate:

- raw camera-video decoding;
- learned visual feature translation;
- autonomous attention-based region segmentation;
- depth estimation or real optical flow;
- a reflection or photograph test;
- long-term object identity across days and environments;
- semantic category learning such as `cup` or `person`;
- autonomous object naming;
- later practical-use learning;
- general intelligence or consciousness.

The association equations and thresholds are programmed. The evidence passing through them is controlled numerical sensory data. This is an architectural proof that the identity and promotion laws work cleanly before they are connected to native video.

## Next milestone

### Milestone 8 — Use-Driven Cognitive Compilation

The next phase will test Verdant's central efficiency hypothesis:

```text
repeated successful procedural sequence
→ preserved attempts and corrections
→ recurring procedural candidate
→ Council-governed procedural promotion
→ compact reusable operator
→ lower later access cost
```

The decisive measurements will include:

- correctness;
- decision latency;
- concepts and relations inspected;
- shards considered or thawed;
- workspace resource use;
- number of corrections;
- bytes added per successful trial;
- retained access to the original evidence and failed attempts.

The goal is not merely to repeat a behavior. It is to show that practiced success becomes cheaper while remaining revisable and evidence-linked.
