# Cognitive Pocket v2.3 — Source-Lineage Corroboration and Distractor Scaling

**Research implementation only.** Native Verdant V5 Council P/Q, Obligation Substrate, original 336-cycle user VDK, v2.1 retained journals and v2.2 reconciliation journals remain immutable. Research branch: test/cognitive-pocket-source-corroboration-v2-3, branched from v2.2 commit 75f923c.

## Questions

1. When a source publishes copied or redistributed testimony, can we avoid falsely treating multiple citations as multiple independent observations?
2. How do contradictory, withdrawn and replacement declarations affect the eligibility of conditional multi-P conclusions?
3. What work does pocket P routing add compared with a flat graph given exactly the same corroborated evidence, while increasing unrelated-but-well-formed attestation volume?

## Implemented v2.3 protocol

1. Begin with **actual Council-promoted native P/Q** from a source snapshot containing 9 native primitive relations but NO native cross-P bridge.
2. Freeze a **controlled externally declared source manifest**, explicitly naming each source_id, information-origin lineage_family and descriptive provenance. The registry is checksum-protected and source-snapshot-bound but NOT an independent identity attestation. A malicious source/registrar can lie.
3. Each experimental attestation contains a source_ref matching a registered source_id, native endpoints, an exact typed directed predicate and a payload hash. If a citation references an earlier attestation as its derived_from parent, it automatically inherits the parent's original lineage family despite changing publisher/source strings. It cannot modify the parent's predicate, endpoints or direction.
4. A conditional cross-P bridge requires at least **two distinct eligible declared lineage families supporting the exact same directed typed claim**. One root, two newspapers reporting one original witness, or two labels mapped to one family remain provisional. Distinct *declared* families can corroborate only under the controlled-input assumption, not certify real-world independence.
5. Any active reverse-direction observation about the same PRECEDES endpoints conservatively quarantines all active competing forward/reverse claims. Reverse native supported/confirmed testimony or explicit same-direction native contradicted status also quarantines matching experimental evidence. Explicit source-matched withdrawal changes eligibility but never deletes history.
5a. **Native contradiction visibility:** the original v0 pocket schema intentionally filters unsupported cross-P relations. For source-only detached pocket replays, v2.3 cannot claim to have inspected *all* native `CONTRADICTED` cross-P records. The optional `native_kernel` argument to `status_snapshot()`/`inspect_corroboration()` verifies the exact canonical fingerprint and checks the live read-only kernel's contradicted typed rows, without modifying pocket identity or treating negatives as positive proof edges. Results explicitly disclose whether full live-native conflict inspection occurred. Detached experiments should not imply comprehensive native contradictory-evidence review.
6. Only corroborated experimental claims enter a detached v2.1 conditional composition view, with a separate reference mapping every synthesized admissible bridge back to the exact original attestation IDs and distinct lineage families. These are **experimental conditional proofs**, never promoted native canon. Current unrelated singletons remain in the journal but cannot create facts.
7. Compare the result against flat-graph BFS using the **exact same eligible relation view** and the same externally supplied PRECEDES transitivity rule. Report pocket proof expansions, P-route inspections, flat expansions, attestation replay count and registered origins. These are operation counters, NOT a wall-clock speed benchmark.
8. Source-anchored, hash-linked, bounded copy-on-write event history with exclusive-create sidecar save, independent load/replay, optional complete v2.2 journal migration. Legacy import requires explicit source_ref mapping for EVERY old observation. No inference of independence from different source strings. Source changes and invalid records fail closed.
9. A controlled scaling benchmark holds native 3-P/12-concept source and the 2-family corroborated bridge *constant*, while staging **0, 8, 16, 32 and 64 additional valid but uncorroborated decoy attestations**. Decoy statements have native concept endpoints, but single-lineage origins only. Neither pocket nor flat graph is permitted to use them as semantic proof. This tests provenance workload, NOT larger native graph memory capacity.

## Controlled seven-stage experiment

Migrate v2.2's original source-attested journal **without altering it**. At the end of v2.2, the original bridge and reverse challenge are withdrawn, the unrelated distractor remains active, and the replacement bridge has ONE eligible declared origin.

| Stage | Expected |
|---|---|
| Migrate latest v2.2 | Provisional; missing corroborated proof |
| Add copied citation from that existing replacement | Still provisional (same family) |
| Add independent *declared* second origin | Supported conditional composition |
| Add reverse contradictory origin | Quarantine; no supported proof |
| Reverse challenge withdrawn | Supported conditional composition |
| Second origin withdrawn | Provisional; no supported proof |
| Add a new distinct origin | Supported conditional composition |

The previous v2.2 criterion required a single eligible external bridge. V2.3 imposes a stricter evidence gate. Therefore initial migration from v2.2 may reduce the conclusion from "supported" to "provisional". **This is expected, not forgetting**.

A held-out r3 PRECEDES s2 query is re-evaluated after reconstructing the original source checkpoint and loading the v2.3 journal. Original VDK native relation count remains nine, without any cross-P canonical writeback.

## What results would NOT establish

- Source_ref and lineage_family are externally declared strings. Their equality, event hashes and journal replay DO NOT authenticate sources, detect collusion, prove independence, or justify calling the observation real-world verified.
- The declared PRECEDES transitivity rule is fixed Python code, not self-developed reasoning semantics. A six- or seven-edge conditional proof is not an independently learned ability.
- The two-source threshold and reverse quarantine are **hand-coded experimental policies**, not statistically calibrated truth inference or a general contradiction logic.
- Neither an unchanged graph route expansion count nor a 1-edge proof advantage establishes compute, latency or sample efficiency. Pocket routing itself consumes work, and the native graph is held fixed in this benchmark.
- No sensor observations, trust signatures, canonical claim promotion, ObligationKernel creation or resolution, independent daughter processes, native-learning merge, or full all-version legacy checkpoint verification are implemented here.
- The provenance sidecar's SHA-256 hash chain detects unintended changes but is NOT an authenticated signature. A malicious controller can re-sign/recompute the entire JSON chain.

## Research dependencies for later work

Add independently verifiable source-origin acquisition, tamper-evident external attestations with trusted public keys or authenticated data channels; multi-family native task corpora, calibration against real outcomes, abstention at mixed uncertainty thresholds; full equal-budget latency and throughput measurements as P/Q counts scale, and independent oversight for any eventual Council-facing promotion path.

## Files

- verdant_pockets/corroboration.py — bounded manifest, origin lineage inheritance, attestation events/withdrawal, materialized corroboration and flat reference.
- verdant_pockets/source_benchmark.py — fixed-native 0/8/16/32/64-attestation controlled scaling.
- verdant_pockets/research_corroboration_demo.py — seven-stage controlled study, legacy v2.2 migration and independent native replay.
- tests/test_cognitive_pocket_corroboration.py — genuine native P/Q, denial/suspension, false-root independence, duplicate and reverse control, exact sidecar replay, migration and scaling.
- docs/COGNITIVE_POCKET_V23_WINDOWS.md — Windows copy-paste local research run.
