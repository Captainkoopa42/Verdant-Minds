# Verdant Minds Independent Rebuild — Milestone 6 Report

## Bounded Specialization and Evidence-Grounded Routing

Milestone 6 adds bounded specialized cognitive regions to the clean-room Verdant rebuild while preserving one canonical semantic truth.

The implementation contains no LLM or pretrained semantic model. The demonstration uses controlled handwritten curricula.

## Constitutional purpose

The previous V4 run family demonstrated real shard movement, but Export 26 also showed a critical failure: the system moved across more cognitive territory while losing direct anchoring to the presented experience.

Milestone 6 therefore enforces this boundary:

> Verdant may route among specialized regions only when the presented experience directly grounds the destination. ECWF resonance may modify ranking, but cannot independently create or authorize a route.

## Architecture

```text
canonical concepts and relations
            │
            ├── root catalog — references every canonical record
            │
            └── bounded specialized shards — reference selected records
                         │
                         ▼
              pure routing inspection
       direct cue + relation support + ECWF
        + continuity + evidence coverage
        - contamination - thaw cost
                         │
                         ▼
                  Kings and Council
                         │
                         ▼
               authorized traversal
                         │
                         ▼
          persistent bridge + route lineage
```

Shards do not contain copied concept or relation records. They contain canonical identifiers only. Consequently, there is still one authoritative graph, one claim history, and one evidence ledger.

## Implemented records

### `ShardPolicy`

Persists:

- maximum concepts per specialized shard;
- maximum relations per specialized shard;
- maximum portal concepts per bridge;
- minimum direct-grounding ratio;
- minimum route score;
- separate positive and penalty weights;
- policy revision.

### `ShardRecord`

Persists:

- shard identity and label;
- active, dormant, or root status;
- canonical concept and relation references;
- evidence supporting formation;
- specialization signature;
- parent shard;
- formation lineage.

### `ShardFormationReport` and `ShardFormationEvent`

Formation inspection is pure. Commitment requires:

- an untampered report;
- current structural state;
- bounded membership;
- preserved evidence;
- a committed Council decision authorizing the exact operation.

### `RoutingReport`

Every candidate shard exposes:

- direct grounding;
- relation support;
- ECWF resonance support;
- prior bridge or shared-portal continuity;
- evidence coverage;
- resonance contamination;
- thaw cost;
- weighted positive contribution;
- weighted penalty;
- eligibility and rejection codes.

### `RoutingEvent`

Every completed traversal preserves:

- source and target shards;
- exact direct cue concepts;
- exact evidence records;
- Council decision;
- routing report;
- bridge identity;
- cycle and transition lineage.

### `ShardBridgeRecord`

A bridge is created only by an actual completed traversal. It records:

- canonical shard endpoints;
- portal concepts;
- preserved evidence;
- traversal count;
- first and latest traversal cycles.

There is no separate store of candidate or ghost bridges.

## Routing score

The current experimental score is:

\[
R = 0.50D + 0.18L + 0.12E + 0.10C + 0.10V - 0.12N - 0.06T
\]

where:

- \(D\) = direct cue grounding;
- \(L\) = relation support;
- \(E\) = ECWF resonance support;
- \(C\) = continuity through shared portals or prior traversal;
- \(V\) = evidence coverage;
- \(N\) = unrelated resonance contamination;
- \(T\) = thaw cost from shard size.

A score is not sufficient by itself. Eligibility separately requires preserved evidence and at least `0.34` direct grounding. Therefore a highly resonant shard with no direct support cannot be selected.

These values are explicit experimental settings, not validated universal cognitive constants.

## Controlled demonstration

Three domain regions were created from handwritten lessons:

| Shard | Concepts | Relations |
|---|---:|---:|
| Physics | 4 | 3 |
| Ecology | 4 | 3 |
| Interaction | 4 | 3 |

The root catalog contained 12 concepts and 9 relations. Each specialized region remained at exactly four concept references and three relation references throughout later routing.

### Adversarial first route

The first routing trial intentionally supplied:

- a direct ecology cue involving `watershed`, `rainfall`, and `wildfire`;
- a separately generated physics-oriented ECWF resonance event.

Verdant selected the ecology shard.

| Component | Ecology result |
|---|---:|
| Route score | 0.903439 |
| Direct grounding | 1.000000 |
| Relation support | 1.000000 |
| Resonance support | 0.257824 |
| Contamination | 0.000000 |
| Thaw cost | 0.125000 |

The exact three directly presented concept identifiers and all three evidence records were carried into the routing event.

The route changed no evidence, concepts, relations, or claims. It changed only governance, shard status, bridge state, routing history, and transition history.

### Cross-shard movement

The controlled sequence was:

```text
root → ecology → physics → ecology
```

The later physics–ecology bridge recorded two completed traversals. It was not created until the first actual cross-shard route occurred.

Final bridge result:

| Bridge | Traversals |
|---|---:|
| Root–Ecology | 1 |
| Physics–Ecology | 2 |

Ghost bridges: **0**.

## Demonstration state

| Measurement | Result |
|---|---:|
| Developmental cycles | 19 |
| Evidence records | 18 |
| Canonical concepts | 12 |
| Canonical relations | 9 |
| Specialized shards | 3 |
| Total shards including root | 4 |
| Shard formation events | 3 |
| Routing events | 3 |
| Persistent bridges | 2 |
| Council decisions | 6 |
| ECWF resonance events | 1 |
| Attention candidates | 8 |
| Graph density | 6.818% |
| Exact checkpoint reload | Passed |

## Tests

Milestone 6 adds thirteen tests. The combined suite result is:

```text
65 passed
```

The new tests cover:

1. root catalog completeness and canonical-reference-only shards;
2. pure formation inspection;
3. mandatory Council authorization;
4. shard concept bounds;
5. direct-cue route selection;
6. exact cue and evidence retention;
7. rejection of resonance-only routing;
8. resistance to conflicting resonance;
9. absence of ghost bridges;
10. real bridge traversal counting;
11. exactly one active shard;
12. stale and tampered report rejection;
13. exact checkpoint recovery and deterministic replay.

All previous CognitiveChunk, kernel, language, claims, ECWF, and governance tests continue to pass.

## Important bug prevented during implementation

An early version attached every re-observed known concept to whichever shard was active at the time. That would have caused ordinary routing cues to contaminate the current shard with concepts from another domain.

The corrected rule is:

- every concept and relation remains cataloged in the root canonical view;
- a newly created concept may join the active specialized shard when capacity permits;
- merely re-observing an existing concept does not rewrite specialized membership;
- reinforcing an existing relation does not silently transplant it into another shard.

The specialized shards therefore remained stable during the complete demonstration.

## What this milestone establishes

Milestone 6 demonstrates that the rebuilt Verdant can:

- maintain bounded specialized reference regions;
- preserve one canonical semantic truth;
- subject formation and routing to Council authorization;
- route according to the presented experience rather than resonance alone;
- retain exact direct grounding through movement;
- preserve real bridge traffic;
- reject stale or altered decisions;
- survive exact checkpoint recovery;
- reproduce the same developmental history deterministically.

This directly addresses the routing-versus-grounding failure observed in the earlier run data at a controlled architectural scale.

## What it does not establish

This milestone does **not** yet demonstrate:

- autonomous discovery of optimal shard boundaries;
- raw sensory grounding;
- learned object identity;
- predictive routing from physical outcomes;
- autonomous bridge pruning or promotion;
- measured speed gains from specialization;
- object compaction;
- disk-backed million-structure scale;
- general intelligence or consciousness.

Shard membership in this demonstration is proposed from controlled domain groups and then constitutionally authorized. The root catalog is still an in-memory reference index and is not yet a hierarchical disk-backed archive.

## Next milestone

### Milestone 7 — Earned Proto-Object Formation

The next phase will move from taught symbolic groupings toward structures earned from temporal and causal experience.

The first controlled object pathway will require:

```text
native temporal observations
→ recurrence across events
→ persistence through transformation
→ common motion or consequence
→ competing proto-object candidates
→ evidence support and contradiction
→ Council-governed promotion
→ retained pointers to every source event
```

The decisive test will distinguish:

- the same object under changed viewpoint;
- a similar but different object;
- temporary occlusion and reappearance;
- a reflection or image;
- a candidate that should remain unresolved.

No label will be allowed to replace the underlying experience.
