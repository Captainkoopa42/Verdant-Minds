# Independent Verdant Rebuild — Milestone 1 Report

## Completed scope

The independent rebuild now has a canonical state kernel connected safely to
CognitiveChunk v2.

### Canonical ownership

- concepts have one authoritative store;
- relations have one authoritative store;
- neighbor lists and graph metrics are derived views;
- duplicate relation proposals update the same canonical record;
- every concept and relation requires known evidence.

### State continuity

- complex field state is saved exactly;
- every applied experience appends a field-history frame;
- field sensitivity simulation is nonmutating;
- checkpoints are deterministic, checksummed, and atomically replaced;
- exact save/destroy/load equality is tested.

### Reproducibility

- stable identifiers derive from canonical content rather than wall-clock time;
- identical seeds and command sequences produce identical full states;
- repeated event keys are idempotent when content matches;
- reused event keys with changed content raise a replay conflict.

### CognitiveChunk v2 integration

The adapter imports native payload and translation evidence into the kernel and
updates the continuous field without promoting semantic concepts from summaries
or generated labels. This preserves the rule that semantic structure must be
earned by the later grammar and MemoryWeb pathway.

## Test gates passed

1. CognitiveChunk v2 exact text round trip.
2. Immutable observations.
3. Block write permissions.
4. Contradiction-preserving merge.
5. Video temporal-segment contract.
6. Canonical kernel exact checkpoint round trip.
7. Pure inspection and deterministic checkpoint preview.
8. Single canonical relation truth.
9. Deterministic replay and idempotent events.
10. Evidence-gated relation formation.
11. Persistent field history and nonmutating sensitivity.
12. Checkpoint tamper detection.
13. Safe CognitiveChunk v2 ingestion without premature semantics.

**Result: 13 tests passed.**

## What this does not claim

- This is not production ECWF.
- This is not production MemoryWeb.
- It does not yet learn grammar.
- It does not yet form concepts autonomously from handwritten sentences.
- It does not yet route shards, promote objects, or operate an active workspace.

## Next milestone

The next step is the handwritten-language vertical slice:

```text
curriculum text
→ CognitiveChunk v2 native preservation
→ explicit grammar/rule analysis
→ typed candidate concepts and directed relations
→ evidence gate
→ canonical graph and field update
→ exact checkpoint/reload
→ role-reversal, negation, temporal-order, and paraphrase tests
```

The first target is not fluent language. It is proof that grammar changes the
relation represented by the same vocabulary.
