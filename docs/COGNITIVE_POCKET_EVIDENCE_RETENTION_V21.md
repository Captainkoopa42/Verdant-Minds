# Cognitive Pocket v2.1 — Experimental Evidence Acquisition and Retention

Status: **experimental implementation; native read-only**. Research branch: test/cognitive-pocket-evidence-retention-v2-1. Inherits v2 composition. Original native V5 and Obligation Substrate branches are unchanged.

## Falsifiable question

Can a real Council-promoted native P/Q pocket identify an unsupported multi-P query, retain one *externally supplied* new observation in an isolated journal, then conditionally compose a previously unsupported answer and reuse that observation on another query **after restoring the pre-bridge native checkpoint**, without claiming a new canonical fact?

## Exact implemented lifecycle

1. Issue a query over genuine native P/Q memory BEFORE external evidence. Save a gap certificate with the native abstention and no oracle-specified missing bridge.
2. Stage one explicitly controlled **teacher-supplied primitive observation**. It contains native concept endpoints, exact typed predicate, direction, a source reference, and a checksum of its own structured payload. Its truth is NOT independently established.
3. Copy-append into a bounded, independent evidence journal, anchored to the native P/Q source hash and kernel canonical fingerprint. Records carry a deterministic hash chain, refuse duplicates, altered endpoints, unknown predicates, unsupported evidence kinds, missing sources and malformed payloads.
4. Retry the original task using two separate evidence streams: existing native canonical directed relations, plus the new conditional experimental observation. A complete typed path including the new observation is mandatory; direct teaching of the final answer is rejected as a non-composite.
5. Ask a different, untaught endpoint query using the same observed primitive. Restore the pre-bridge native checkpoint and replay the journal against independently reconstructed P/Q memories.
6. Compare with a flat BFS over the identical native plus experimental evidence under the same declared transitivity predicate. Report both outcomes and actual expansions; no pocket speed superiority is assumed.
7. Run matched negative arms: no observation, reverse observation, irrelevant P observation, direct-answer observation, and an unlicensed relation predicate. Record abstention rather than inventing a bridge or conclusion.

The only licensed transitivity predicate is PRECEDES, a rule externally supplied by our experiment. No other predicate obtains transitivity automatically.

## Epistemic and operational limits

- A new observation is **source-attested controlled external testimony only**. Its checksum documents bytes, not independent truth, cryptographic signing or source authenticity.
- It remains an experimental sidecar observation, never a kernel CONFIRMED/SUPPORTED native relation. A conditional result has status supported_experimental_composition. It cannot create a canonical claim or automatically trigger an obligation.
- A successful held-out query is a different query within the SAME small controlled source corpus, **not** new environmental experience, autonomously acquired knowledge or demonstrated domain transfer.
- Journal persistence proves retention and deterministic reconstruction of experimental observations, not that Verdant learned a new rule. The declared reasoning operator is still hard-coded.
- The negative original seed-81001 336-cycle VDK has no native cross-P bridge and is not silently retaught or modified.
- The flat graph baseline gets the same evidence. No earned runtime, accuracy or sample-efficiency advantage over a flat traversal has been demonstrated.
- Daughter basin independence, v4-style physical mitosis, endogenous selection of experiments, new sensor evidence, semantic compression and canonical Council writeback are deliberately outside the v2.1 authority boundary.

## Source and tests

- verdant_pockets/evidence_retention.py — source-anchored event journal, independent experimental observations, typed conditional composition, flat graph control and independent journal load/verify
- verdant_pockets/research_acquisition_demo.py — disposable native Council-P/Q demonstration, negative controls, cold source reload and create-only exports
- verdant_pockets/research_demo.py — optional bridge-free controlled native P/Q source, backward-compatible with v2
- tests/test_cognitive_pocket_evidence_retention.py — genuine native gap, held-out reuse, restart replay, matched negative and tamper tests

## Next research dependencies

Validate source identity and the observation independently; handle contradictions and evidence revocation in persistent sidecars. Compare full proof utility/cost against the flat baseline on source-held-out and task-held-out sets with matching computational budgets. Only after earned functional transfer consider an opt-in canonical proposal protocol through the Obligation Substrate and Council.
