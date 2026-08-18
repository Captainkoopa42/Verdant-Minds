# V5 implementation and evidence status

This document reports the current `V5` branch as audited on 2026-08-18. Existing milestone, Workbench, release, and revalidation documents remain unchanged and retain their historical values.

## Engineering status

| Area | Status | Evidence or limitation |
| --- | --- | --- |
| Canonical kernel | Working | Typed Pydantic state, deterministic IDs/fingerprints, evidence gates, exact checkpoint round-trip, and replay controls pass tests. |
| Language and claims | Working on tested contracts | Handwritten grammar/lexicon, typed claims, contradictions, revisions, and evidence ledgers pass. |
| ECWF/resonance | Working on tested contracts | Pure inspection, explicit commitment, stale/tamper rejection, persistence, and deterministic sequences pass. |
| Governance | Working on tested contracts | Separate Data, Forefront, and Ethics judgments plus rule-ordered Council authorization pass. |
| Shards and routing | Working on tested contracts | Bounded formation, grounded routing, bridge traversal, persistence, and anti-ghost controls pass. |
| Native sensory/media | Working on supported formats | Exact source preservation, bounded translation, synchronization, temporal events, run packages, and tamper/path-traversal rejection pass. |
| Perception/objecthood | Working on tested contracts | Nonsemantic binding, continuity/occlusion, candidate formation, governed promotion, and exact persistence pass. |
| Developmental heartbeat | Working | Experience, field, resonance, workspace, plasticity, and structure observation commit atomically on a staged kernel. |
| Plasticity | Working on tested bounds | Local associations, causal recall, decay, competition, degree/edge caps, and replay safety pass. |
| Earned P structures | Working in controlled experiments | Candidate gates, opaque promotion, compilation, ablation/restoration, and boundary-contamination rejection pass. |
| Cross-symbolic interaction | Working in controlled experiments | Continuous retrieval requires independent symbolic verification; unrelated controls are rejected. |
| Higher-order Q structures | Working in controlled experiments | P-family observation, opaque Q promotion, causal use, negative controls, and persistence pass. |
| Refolding | Working in controlled experiments | Stable/revise/split/unresolved dispositions preserve historical parent lineage and semantic counts. |
| Oracle-free M19 harness | Revalidated | Current code promotes all natively eligible P/Q candidates before evaluator indexing; 10 benchmark tests and the audited run pass. |
| Workbench | Working as a local laboratory | UI/API, persistence, curricula, structures, explorer, experiments, providers, plugins, integrity, and WB-11 curriculum packs pass tested paths. |
| Production network deployment | Not provided | No production authentication, authorization service, TLS termination, or multi-user isolation. |
| Untrusted plugin isolation | Not provided | Capability checks and subprocess execution exist; this is not an OS sandbox. |
| Python packaging | Source-tree only | No root project metadata; dependencies install from `requirements-lock.txt`, then code runs from the repository tree. |

## Current verification

The audit installed the checked-in dependency versions under Python 3.12.13 and verified:

- 191 engine tests;
- 61 Workbench tests discovered by `verify_release.py`;
- 6 newer Workbench tests omitted by that verifier;
- 258 total current tests with zero failures;
- Workbench startup and artifact diagnostic;
- WB-08 provider proof with `all_gates_pass=true`;
- WB-09 plugin/integrity/recovery proof with `all_gates_pass=true`;
- all 21 engine/Workbench package surfaces imported;
- all active Python package trees compiled;
- the oracle-free benchmark completed with every headline check true.

The current oracle-free benchmark reproduced:

| Control | With object | Ablated | Restored |
| --- | ---: | ---: | ---: |
| P reconstruction work | 1 | 7 | 1 |
| Q family comparison work | 3 | 8 | 3 |

It formed exactly five expected P structures and one expected Q structure, with no missing or extra promoted P/Q objects in the controlled population. These are narrow benchmark results, not a general intelligence claim.

## Historical records versus current branch

| Record | What it describes | Current relationship |
| --- | --- | --- |
| `ACTIVE_CODEBASE_FILE_MANIFEST.json` | Earlier 192-file/140-test active-code snapshot | Stale relative to the 405-file branch; it lists absent paths and omits later work. |
| `RELEASE_MANIFEST.json` | Workbench 1.0.1 release snapshot | Preserved historical record with 189 engine + 61 Workbench tests and older source hashes. |
| `WORKBENCH_1_0_FINAL_REPORT.md` | 250-test release audit | Accurate for its recorded release layer, not the complete current branch. |
| `MILESTONE_19_REPORT.md` and tracked `artifacts/milestone_19_benchmark_summary.json` | Original oracle-assisted M19 result | Not valid evidence of evaluator-independent P/Q selection. |
| `MILESTONE_19_ORACLE_REVALIDATION.md` | Later oracle-free repair and 258-test remote validation | Current scientific correction and validation boundary. |
| `.github/workflows/full-suite-validation.yml` | Dynamic current-suite discovery | Most complete checked-in validation route; discovers both engine and Workbench test files. |

## Current source identity

Before adding these documentation-only files, the runtime diagnostic calculated:

```text
release_id               verdant-minds-v5-workbench-1.0.1
engine_source_sha256     c76fcee36d9e087c704bbefb1d057cff5a8780e33b5ff8c208c5235f6ed94c76
workbench_source_sha256  1f1d311a3112def9885e263688bac03aa4a878020b5c786a35da1dd57ed492ce
dependency_lock_sha256   bb0dd24142ccb66437fac60a38d07f9a95004a85a029c3f870da7d226e598b64
```

The new documentation is deliberately outside the paths included by `source_build_identity()`, so this documentation pass must not change those three content hashes.

## Highest-value next engineering work

1. Update `verify_release.py` to discover all current Workbench tests or reuse the dynamic full-suite workflow logic.
2. Produce a new machine-readable current manifest instead of treating the historical release manifest as live inventory.
3. Check in a fresh oracle-free M19 result artifact whose schema is `verdant.ethomorphism_benchmark.v2_oracle_free`.
4. Separate direct dependency pins from a complete resolved environment lock.
5. Profile large-organism memory, event-ledger, visualization, and checkpoint behavior.
6. Add production security only if Workbench is ever moved beyond its intended local laboratory boundary.
