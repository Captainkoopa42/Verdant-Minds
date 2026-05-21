# Verdant-Minds: Scalable Compartmentalized Memory Architecture

This document proposes a practical path from a monolithic checkpoint (`state.json`) to a
compartmentalized, scalable memory system that preserves Verdant's associative graph dynamics,
thermodynamic regulation, basin structure, and ECWF coupling.

## 1) Target properties

The memory system should satisfy:

- **Selective load**: avoid loading the full graph for each cycle.
- **Context routing**: use current activation context to choose memory partitions.
- **Loose coupling**: keep partitions separable while enabling cross-partition activation.
- **Asynchronous durability**: commit writes without stalling cognition cycles.
- **Replayability**: preserve deterministic/reconstructable lineage across writes.

## 2) Partition model: domain + basin + time

Use a hybrid partition key:

- **Domain**: `episodic`, `semantic`, `relational`, `procedural`.
- **Basin shard**: e.g., `basin_12`, `basin_07`.
- **Temporal segment**: rolling segments like `2026W20` or `cycle_000000_000999`.

Suggested partition key format:

`<domain>/<basin_id>/<segment>.json.zst`

This combines conceptual specialization (domain) with dynamic topology (basin) and scalable file
size bounds (segment).

## 3) Two-tier index and router

Introduce a `MemoryRouter` with two indexes.

### 3.1 Global sparse index (always loaded)

Lightweight structure in RAM, keyed by node ID and concept hash:

- `node_id -> {partition_ids, last_seen_cycle, activation_stats}`
- `basin_id -> {hotness, partition_ids, centroid_vector}`
- `cue_token -> top-k partition_ids`

Backed by compact JSON or SQLite for Colab simplicity.

### 3.2 Partition-local index (loaded on demand)

Each partition stores:

- local node table
- local edge table
- boundary links (cross-partition pointers)
- summary vectors / signatures

The router computes candidate partitions from active nodes, active basins, and cue tokens, then
loads top-k partitions under a memory budget.

## 4) Cross-partition associative activation without full load

Use **boundary nodes + proxy edges**:

- Nodes appearing in multiple partitions are represented by canonical `node_id` and local shadow
  records.
- Cross-partition edges become `proxy edges` with lazy resolution:
  - local edge points to `(remote_partition_id, remote_node_id, weight)`
  - remote partition is loaded only when activation crosses threshold.

Activation algorithm:

1. Spread activation within loaded partitions first.
2. Accumulate spillover at boundary nodes.
3. If spillover exceeds `cross_load_threshold`, enqueue remote partition load.
4. Apply damped carryover to newly loaded partition.

This preserves associative dynamics while bounding active working set.

## 5) Thermodynamic compatibility

Treat each loaded partition as a local thermodynamic cell:

- local entropy and coherence
- local `t_g` contribution
- local basin volatility

Compute global values via weighted aggregation:

- `global_entropy = sum(w_i * entropy_i)`
- `global_coherence = sum(w_i * coherence_i)`
- `global_t_g` from weighted criticality terms plus cross-partition coupling penalty.

Add a coupling metric:

- `coupling_flux(i,j)` = activation mass transferred between partitions per cycle.

This gives thermodynamic signals that explicitly account for partition boundaries.

## 6) Holographic/distributed retrieval cues

To reduce flat key-based retrieval dependence:

- Compute a fixed-length **concept signature vector** per node (e.g., random indexing or hashed
  sparse semantic vector).
- Maintain partition centroid and basis signatures.
- Route by nearest centroid + basin affinity + recent activation priors.

Pattern:

`routing_score = a*sim(query, partition_centroid) + b*basin_affinity + c*recency + d*thermo_fit`

This approximates holographic access while remaining implementable in NetworkX + Python.

## 7) Write path (non-blocking)

Adopt a write-ahead event log (WAL-like) plus asynchronous compaction.

### 7.1 Online cycle path

- Cycle emits memory events (`node_add`, `edge_add`, `edge_update`, `activation_update`,
  `basin_move`, `ecwf_update`).
- Append events to `events/<run>/<seed>/memory_events.jsonl`.
- Return immediately (no heavy partition rewrite in critical path).

### 7.2 Background commit path

- Background worker batches events by partition key.
- Applies updates to in-memory partition cache.
- Flushes changed partitions atomically (`tmp -> rename`).
- Periodically writes `partition_manifest.json` with checksums and versions.

This pattern avoids blocking and improves crash recovery.

## 8) Data structures and patterns to use now

For current constraints (Python + Colab + NetworkX):

1. **LSM-inspired storage pattern** for events + periodic compaction.
2. **Adjacency list shards** per partition instead of one monolithic graph dump.
3. **Bloom filters** per partition for quick negative routing checks.
4. **LFU/LRU cache** for loaded partitions under RAM budget.
5. **Versioned manifests** (`schema_version`, `partition_version`, checksums).
6. **CQRS-like split**:
   - write model = append-only events
   - read model = materialized partition snapshots

## 9) Migration path from current single checkpoint

Phase M1:

- Keep current `state.json` output for compatibility.
- Also emit event stream + partition manifests.

Phase M2:

- Build loader that reconstructs active subgraph from partition files + boundary proxies.
- Use monolithic checkpoint only as fallback.

Phase M3:

- Switch primary runtime to partition-first memory.
- Keep periodic global snapshots for audits and reproducibility bundles.

## 10) Operational safeguards

- **Atomic writes**: always write to temp then rename.
- **Checksums**: verify each partition and manifest.
- **Replay tests**: reconstruct same active state from event logs.
- **Drift monitor**: compare partition-first reconstructed metrics vs periodic global snapshot.

## 11) Suggested minimum implementation slice (first build)

1. Add `MemoryRouter` interface and global sparse index.
2. Add partition file layout and manifest.
3. Emit append-only memory event log per cycle.
4. Implement background committer for one domain (`semantic`) first.
5. Add boundary proxy edges and lazy load thresholds.
6. Add partition cache with LFU eviction.
7. Add validation script: replay 100 cycles and compare graph metrics/coherence.

## 12) When to move beyond JSON

JSON+compression is fine for initial experiments. Move to SQLite/Parquet/LMDB when:

- partition count > ~1k files per run,
- event replay becomes dominant runtime cost,
- concurrent read/write pressure increases,
- Colab I/O latency dominates cycle time.

Until then, the architecture above gives most of the scalability benefit without introducing heavy
infrastructure.
