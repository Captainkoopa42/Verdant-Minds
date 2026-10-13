# Structural Transfer v0.1 — Windows execution report (operator supplied)

Date: 2026-10-13. Experimental branch: `test/structural-transfer-v0`.

**Evidence classification:** USER-REPORTED COMPLETED RUN with locally executed stage-status and `report` validation. GitHub connector has **not downloaded** the original private `.vst` milestone artifacts, `responses.json`, or `grades.json`; independent artifact replay has not been performed.

## Procedure and completion

- Exact command family: `python -m verdant_math.structural_transfer.experiment start|status|report`.
- Native cycles: 1,000 per arm × five arms × three seeds (79101, 79102, 79103) = **15,000 cycles**.
- Console recorded durable milestones 250, 500, 750, and 1,000 for **all 15 arms**.
- All 15 arms subsequently reported `durable_cycle=1000 / 1000`; `complete_response_batch=True`.
- Native execution wall time: **788.3114301 seconds** (approximately 13 min 8 sec). The earlier 12,000-operation retention pilot took 636.0738186 seconds; throughput was approximately 19.0 versus 18.9 native operations/sec, respectively. These are two different workloads, not controlled performance comparisons.
- The built-in report verified local `responses.json` SHA-256:
  `9689857702d430a6fe11d546da46c49695933e2bbe0100157220e5955be9a71c`.
- Output: `structural-transfer-1000/responses.json`, `structural-transfer-1000/grades.json`, and preserved immutable `stages/` directory on operator's Windows machine.

## Final results per seed (20 enrolled questions per arm)

| Arm | Correct | Incorrect | Abstained |
|---|---:|---:|---:|
| Progressive | 16 | 0 | 4 |
| Exact null | 16 | 0 | 4 |
| No rule | 0 | 0 | 20 |
| Incomplete edges | 10 | 0 | 10 |
| Wrong link | 12 | 4 | 4 |

These identical outcomes were reported for all three seeds. Across all 300 final responses: **162 correct, 12 incorrect and 126 abstentions**. Do not collapse the four designed out-of-range boundary requests into answerable denominators.

## Per-split comparison across all three seeds

| Arm | Direct (12) | Short 2-hop (12) | New 3–4-hop (24) | Unreachable boundary (12) |
|---|---|---|---|---|
| Progressive | 12 correct | 12 correct | **24 correct** | 12 abstained |
| Exact null | 12 correct | 12 correct | **24 correct** | 12 abstained |
| No rule | 12 abstained | 12 abstained | 24 abstained | 12 abstained |
| Incomplete edges | 12 correct | 6 correct / 6 abstained | 12 correct / 12 abstained | 12 abstained |
| Wrong link | 12 correct | 9 correct / 3 incorrect | 15 correct / 9 incorrect | 12 abstained |

Meaningful positive finding: when supplied with individually taught opaque links and a human-supplied traversal rule, the native, fixed bounded traversal procedure returns correct endpoints for all **8/8 fresh multi-hop combinations per seed (24/24 overall)**; it preserves partial traces and appropriate abstention when links/rule are missing, and propagates a supplied wrong link into wrong multi-hop answers. All four per-seed deliberately unanswerable boundary questions abstain, as designed.

## Interpretation and limits

**OBSERVED (console evidence):** Persistent native path execution under explicit instruction, correct composition on newly combined start/length requests, complete checkpointed run and matching designated null. A causally informative wrong-link control shows dependency on testimony correctness.

**NOT OBSERVED:** Native induction of the traversal algorithm; autonomous mathematical discovery; independent checking or correction of a wrong teacher; efficiency improvement with prior training; flexible re-representation; open-ended transfer to another domain; consciousness or agency. The tests use one predetermined directed-chain task grammar across three seeds, with seed-dependent opaque labels. The evaluator knows the mapping; the responder follows the supplied rule and native stored edges. Therefore this is **scaffolded relational composition**, not unscaffolded learning or semantic generalization.

Because the complete implementation and prospective task examples were developer-defined, exact-null agreement is a necessary software-control check, not evidence of independent scientific replication. The five roles do not have equivalent supplied knowledge (by design), and 20/20 must not be claimed as success: correct counts always retain complete 20-question denominators.

## Follow-up evidence

Preserve the original local stage archive, immutable source commit and response/grade bytes. Independent replay should check stage receipt chaining and full native evidence closures if later artifacts are shared. A next prospective study could challenge trust in incorrect/conflicting sources and genuinely disjoint relation families while retaining absence-of-rule, incorrect-rule, omission and replication controls. Do not refit these already-evaluated final cases.

## Authority

Experimental only. No changes to the prior v0.65 source artifacts or 1,000-cycle retention pilot, no canonical promotion/Resolution, and no automatically launched training.