# Cognitive Pocket v2.2 — Reconciliation and selective proof retention

**Research-only implementation.** Native Verdant V5 Council P/Q, native typed relationships and canonical Obligation Substrate remain unchanged. Research branch: test/cognitive-pocket-evidence-reconciliation-v2-2, based on v2.1 commit 0e70caa. No earlier milestone branch is merged.

## What this stage asks

Can an experimental pocket *revoke an old conditional conclusion when its specific external observation is withdrawn or contested*, preserve unrelated memories, and recover through a separately documented observation after a restart? Does the behavior match a flat graph granted identical evidence?

**This is not autonomous acquisition or source verification.** The observations and withdrawals are externally staged by the research harness. The relational PRECEDES transitivity rule is still supplied by the experiment.

## Implemented components

- A new v2.2 bounded revision journal is anchored to the exact original native Council-P/Q pocket ID, source snapshot SHA256 and native canonical fingerprint. It never replaces a v2.1 evidence journal or writes to the original VDK.
- Experimental source-attested observations have native concept endpoints, PRECEDES predicate, direction, a bounded declared source_ref, structured payload and checksum. They are not promoted to a SUPPORTED/CONFIRMED canonical relation.
- Explicit source-matched withdrawal events target one observation ID and require a reason. They never erase the original event; the append-by-copy history retains both.
- Active, withdrawn and quarantined observations are replayed from the full history. A reverse-direction claim about the *same endpoints and predicate* conservatively quarantines BOTH active claims. A contradictory native supported/confirmed reverse edge also quarantines its experimental counterpart. No majority vote or opaque confidence threshold converts disputes into truth.
- The evaluation view includes only currently eligible experimental observations plus original native canonical relations. The actual proof comes from v2.1 exact typed rule composition and is tagged CONDITIONAL_ON_EXTERNAL_EXPERIMENTAL_TESTIMONY. A separate flat-graph BFS receives the exact same eligible evidence, and its correctness is compared at every stage.
- An earlier conditional proof is reported as suspended only when a prior actually successful proof cites an observation that has since been withdrawn/quarantined and no current valid proof remains. Unrelated testimony and unrelated withdrawal do not invalidate a still-supported query.
- New source-attested evidence can replace withdrawn testimony. Its authenticity and truth remain *unverified*: recovering a conditional proof does not certify the replacement or create a canonical fact.
- Source P/Q identity mismatch, forged field, duplicate observation, duplicate withdrawal, alien source_ref, tampered event payload, altered digest, unsupported predicate and occupied sidecar path fail closed.
- Reproducible observation history and re-derived conclusions can be verified after rebuilding the original prebridge native checkpoint. This checks serialization and deterministic evidence rules, not autonomous understanding.

## Controlled experimental sequence

A new disposable native kernel genuinely earns three P structures, one Q and nine intra-P native primitive typed relations. The **prior v2.1** journal records one external r4 PRECEDES s1 observation. The six stages are:

| Stage | Expected condition |
|---|---|
| Old observation retained | Supported experimental composition |
| Contradictory reverse s1 PRECEDES r4 arrives | Suspended due to contested evidence |
| Unrelated r2 PRECEDES t2 arrives | Still suspended; distractor retained separately |
| Reverse challenge source withdraws its observation | Supported again |
| Original bridge source withdraws its observation | Suspended due to withdrawn evidence |
| New controlled source supplies replacement r4 PRECEDES s1 | Supported by replacement only |

The original native relation graph still contains only nine canonical primitive relations. Original VDK, V2/V2.1 branches and the old v2.1 JSON journal are not changed.

The held-out question r3 PRECEDES s2 is checked after independent native checkpoint restoration. At each step the flat BFS receives the same currently eligible experimental observations.

## Claims and exclusions

- A result of SUPPORTED_EXPERIMENTAL_COMPOSITION is only conditional on the currently eligible external claim; it is not a native canonical relation and not independently corroborated by sensors.
- SHA256 chain validates accidental or casual content tampering but is **not digitally signed** and does not authenticate the declared source_ref. Someone with write access to the whole journal can recalculate hashes.
- Source-matched withdrawal merely matches a declared string. It is not an authorized identity/security protocol and is not suitable for untrusted production inputs.
- Reverse PRECEDES testimony is treated as incompatible by a hard-coded research policy. V2.2 does not implement general paraconsistent logic, confidence-weighted provenance, native belief revision, truth maintenance across arbitrary typed predicates or independent environmental validation.
- The flat comparator is small and should solve these problems as well. Neither a compute-time nor accuracy advantage of the pocket has been established.
- No autonomous evidence seeker, daughter lifetime manager, actual hardware neuron, native Obligation creation/resolution, Council promotion, or canonical merge is implemented. Those require separate prerequisites.

## Files

- verdant_pockets/reconciliation.py — bounded source-anchored journal, conservative dispute/withdrawal reducer, proof invalidation, v2.1 migration, restart load/save.
- verdant_pockets/research_reconciliation_demo.py — opt-in staged control, original v2.1 journal migration, negative controls, flat baseline, independent verification.
- tests/test_cognitive_pocket_reconciliation.py — genuine native P/Q tests, source-fingerprint preservation, tamper and replay controls.
- docs/COGNITIVE_POCKET_V22_WINDOWS.md — copy-and-paste independent Windows run guide.
