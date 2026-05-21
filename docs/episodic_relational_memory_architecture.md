# Verdant-Minds: Episodic + Relational Memory Partition Design

This document extends the scalable memory architecture with a concrete design for
**episodic** and **relational** partitions in long-term companion contexts.

It assumes prior partitioning (`domain/basin/segment`), router/indexing, proxy-edge coupling,
and thermodynamic signals are already in place.

## 1) Design goals specific to episodic/relational memory

Unlike semantic/procedural memory, episodic-relational memory must preserve:

- **Temporal sequence** (what happened before/after).
- **Affective signal** (valence/intensity/safety/repair/rupture).
- **Relational significance** (what mattered for this specific person).
- **Identity isolation** (strict user boundary in multi-human deployments).
- **Narrative continuity** (months/years without flattening to generic facts).

## 2) Partition keys and hard isolation model

Use human-scoped partition keys:

`relational/<person_id>/<year_week>/<segment>.json.zst`
`episodic/<person_id>/<year_week>/<segment>.json.zst`

Keep semantic/procedural shared unless explicitly tenant-scoped:

`semantic/shared/...`
`procedural/shared/...`

### Isolation boundary (recommended)

Enforce isolation at **three layers** (not one):

1. **Partition key layer**: person-scoped file paths and manifests.
2. **Router authorization layer**: router must carry an explicit `person_id` context and deny
   cross-person relational loads by default.
3. **Graph boundary layer**: every episodic/relational node carries immutable
   `owner_person_id`; cross-owner edges are forbidden by invariant checks.

This defense-in-depth prevents leakage from index bugs or accidental joins.

## 3) Graph pattern for temporal ordering with associative freedom

Use a **directed temporal spine + lateral associative links**.

### 3.1 Node types

- `EpisodeEvent`: one interaction moment (utterance, exchange, milestone).
- `EpisodeWindow`: grouped sequence (session/day/week).
- `RelationalPattern`: recurrent interaction motif (e.g., conflict loop, repair loop).
- `RelationalAnchor`: high-significance memory anchor (trust rupture, repair, breakthrough).

### 3.2 Edge types

- Temporal edges (directed):
  - `NEXT_EVENT`
  - `IN_WINDOW`
  - `WINDOW_NEXT`
- Associative edges (undirected or directed weighted):
  - `SIMILAR_AFFECT`
  - `SIMILAR_THEME`
  - `PATTERN_INSTANCE_OF`
  - `TRIGGERS_PATTERN`
- Cross-partition proxy edges:
  - `RELATES_TO_SEMANTIC_NODE`

### 3.3 Why this pattern

- Temporal spine preserves order and causality.
- Lateral links preserve associative retrieval and pattern completion.
- Pattern nodes compress repeated cycles and prevent event-list bloat.

This hybrid avoids the failure mode of pure timeline storage (good order, weak association) and
pure semantic graphing (good association, weak temporal causality).

## 4) Data model for episodic/relational nodes

Suggested per-event schema (stored as node attrs + event log entry):

```json
{
  "event_id": "evt_...",
  "owner_person_id": "p_...",
  "ts_utc": "2026-05-20T12:34:56Z",
  "cycle": 12345,
  "interaction_type": "supportive|conflict|repair|routine|milestone",
  "summary": "short natural-language abstraction",
  "valence": -1.0,
  "arousal": 0.0,
  "trust_delta": 0.0,
  "novelty": 0.0,
  "vulnerability_signal": 0.0,
  "evidence_refs": ["chunk_id_..."],
  "semantic_proxies": ["semantic:node_..."],
  "retention_score": 0.0
}
```

## 5) Emotional weighting, decay, and reinforcement

Do not use pure LFU/LRU. Use multi-factor retention dynamics.

### 5.1 Suggested state variables

For each event/pattern node maintain:

- `valence_abs` = `abs(valence)` (emotional magnitude)
- `arousal`
- `trust_impact` = `abs(trust_delta)`
- `novelty`
- `repair_signal` (1 when meaningful repair occurred)
- `rupture_signal` (1 when significant conflict/rupture occurred)
- `access_count`
- `last_access_cycle`
- `uniqueness`

### 5.2 Importance score (base)

```text
importance =
  w1*valence_abs +
  w2*arousal +
  w3*trust_impact +
  w4*novelty +
  w5*repair_signal +
  w6*rupture_signal +
  w7*uniqueness
```

### 5.3 Decay function (emotion-aware)

Use non-linear decay with floor for high-significance events:

```text
decay_rate = base_decay * (1 - clamp(importance, 0, 1))
strength_t+1 = max(memory_floor, strength_t * exp(-decay_rate * dt))
```

Set higher `memory_floor` for anchors (breakthroughs, ruptures, repairs).

### 5.4 Reinforcement update

On reactivation:

```text
strength += alpha * (context_match + relational_relevance)
```

On repeated pattern confirmation:

```text
pattern_confidence += beta
```

On contradiction (new evidence opposes old pattern):

```text
pattern_confidence -= gamma
uncertainty += delta
```

This prevents stale relational conclusions from becoming dogma.

## 6) Retention/eviction policy for relational memory

Relational partitions should use **tiered retention**, not simple eviction.

### 6.1 Tiers

- **Tier A (anchors)**: never evict automatically (rare, high significance).
- **Tier B (patterns)**: retain unless confidence collapses and age threshold exceeded.
- **Tier C (episodes)**: compact/merge/summarize when old and low-score.

### 6.2 Retention score

```text
retention_score =
  a*recency_score +
  b*frequency_score +
  c*importance_score +
  d*relational_significance +
  e*uniqueness_score -
  f*redundancy_penalty
```

Where:

- `relational_significance` captures trust-shift, vulnerability, repair/rupture impact.
- `uniqueness_score` rewards non-redundant moments.
- `redundancy_penalty` reduces storage of near-duplicate routine events.

### 6.3 Eviction action = summarize first

Before deleting low-score Tier C events:

1. Summarize cluster into `EpisodeWindowSummary` node.
2. Preserve pointers to major anchors/pattern nodes.
3. Store provenance references to original event IDs.

So memory compresses without narrative amnesia.

## 7) Cross-partition resonance (relational <-> semantic)

Extend proxy-edge logic with typed resonance channels.

### 7.1 Additional proxy edge metadata

Each `RELATES_TO_SEMANTIC_NODE` proxy should include:

- `resonance_type`: `theme|value|trigger|coping|boundary`
- `confidence`
- `last_confirmed_cycle`
- `owner_person_id` (for relational side)

### 7.2 Bidirectional activation rules

When relational event activates:

1. Spread in relational timeline/pattern neighborhood.
2. Emit activation over semantic proxies with gain `g_rs`.
3. Semantic partition loads top-k nodes by weighted proxy confidence and current basin affinity.

When semantic basin activates strongly:

1. Retrieve relational proxies linked to active semantic core nodes.
2. Filter by same `person_id` and recency/importance gates.
3. Surface top-n relational memories as contextual anchors.

### 7.3 Thermodynamic gating

Only allow cross-partition jumps when:

- local coherence above minimum, and
- activation spillover exceeds threshold, and
- jump does not violate privacy owner constraints.

This prevents noisy cross-partition flooding.

## 8) Companion-specific safeguards

- **No single-event overfitting**: require repeated evidence before hard pattern commits.
- **Contradiction ledger**: keep explicit counterexamples to relational patterns.
- **Repair precedence**: successful repair events should weaken deterministic negative loops.
- **Self-uncertainty exposure**: store uncertainty and confidence separately for pattern nodes.

## 9) Storage and runtime flow (Colab-friendly)

### 9.1 Online write path

Append relational/episodic events to:

`events/<run>/<seed>/<person_id>/relational_events.jsonl`

and enqueue partition updates asynchronously.

### 9.2 Background compaction

- roll up routine low-score episodes into window summaries,
- retain anchor and pattern nodes intact,
- rewrite partition snapshots atomically,
- update per-person manifest checksums.

### 9.3 Recommended graduation trigger

Move relational partitions from JSON to SQLite/LMDB when either:

- `events.jsonl` replay latency impacts cycle time, or
- per-person partitions exceed practical Drive I/O thresholds.

## 10) Minimal implementation slice (next step)

1. Add new node/edge type enums for episodic-relational graph.
2. Add per-event affect/relational fields to memory event ledger.
3. Implement retention score + tiering policy (A/B/C).
4. Add per-person router guardrails (`person_id` mandatory for relational loads).
5. Add relational<->semantic proxy metadata and resonance activation rules.
6. Add invariant tests:
   - no cross-person relational loads,
   - no cross-owner edges,
   - anchor tier never auto-evicted,
   - summarize-before-delete for low-score episodes.

---

In short: model relational memory as **time-structured, affect-weighted, person-scoped graph
partitions** with controlled semantic resonance and tiered retention. This preserves Verdant's
associative architecture while respecting companion continuity and privacy boundaries.
