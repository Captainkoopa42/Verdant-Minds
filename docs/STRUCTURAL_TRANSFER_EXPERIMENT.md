# Native Structural Transfer Experiment v0.1

Status: **implemented experimental** in `verdant_math/structural_transfer/experiment.py`, branch `test/structural-transfer-v0`. Exact interpretation: *compositional traversal of separately teacher-supplied opaque relations under an explicitly teacher-supplied handwritten traversal rule*. **No Windows outcome or full 1,000-cycle/arm result yet**.

## Question and prospective structure

Can Verdant's persistent native evidence graph retain individually taught, opaque directed successor relations across hundreds of unrelated native experience cycles, then support bounded 3–4-step composition of links whose complete start-to-end answer was never taught?

This is a deliberate advance over the direct fact-recall 1,000-cycle baseline. A full final answer is neither supplied as testimony nor available to the native responder. The direct question-response interface is read-only and uses only a fixed hand-written interpreter plus canonical native claims and their evidence. It is *not* a mechanism that learns the interpreter itself.

Each of three seeds 79101/79102/79103 creates 13 opaque, deterministic concept labels whose ordering is hidden in their hashes; the program's **external task specification** determines expected destinations. Each seed is copied into five privately isolated roles:

| Role | Native treatment |
|---|---|
| progressive | 12 correct links and supplied rule |
| exact_null | independently repeated exact progressive treatment |
| no_rule | all correct links, but no traversal-rule claim |
| incomplete | valid rule, but links 5 and 8 are not provided |
| wrong_link | valid rule, one erroneous edge from logical node 5 to node 9 |

The five roles share cycle count, event keys, unrelated experience schedule, checkpoint times and question sets within seed. Progressives and exact nulls must retain identical private fingerprints and complete native response traces.

## Schedule

The supplied traversal rule is introduced at cycle 25. The twelve individual links are introduced at cycles 75, 125, 175, 225, 275, 325, 375, 425, 475, 525, 575 and 625. All other charged cycles are native non-mathematical experience transitions. The initial checkpoint and probe occur at cycle 0. Additional milestones are 250, 500, 750 and 1,000. All event keys, native transition IDs and checkpoint bytes are preserved in typed, immutable stage receipts.

Earlier probes are 8 diagnostic requests, none equal to a final request. The final 20-case study comprises four direct one-hop checks, four two-hop checks, **eight distinct three/four-hop compositions**, and four deliberately out-of-chain requests. All 20 are first seen by the final responder at cycle 1,000. Requests do not contain expected destinations; the external evaluator computes them only after complete responses have been durably saved.

## Decision boundaries

- A successfully derived endpoint must cite every native traversed claim and its testimony references, plus the native traversal-rule claim.
- Missing rule, missing or contradicted edge, cycle, unsupported target or absent evidence must abstain with full partial trace.
- A wrong but properly sourced link may cause an **incorrect** result. Do not hide or drop it: it is an important control.
- Boundary probes are deliberately unanswerable with the declared twelve links; appropriate abstention is **not** generalized failure or a scoring trick. Report these four separately.
- Each 1,000-cycle role and seed gets the full 20-case denominator. Grade correct, incorrect and abstained without excluding wrong-link or incomplete paths.
- A response never mutates canonical or private knowledge. The supplied teacher claims are introduced only in isolated private kernels.
- The code source hashes, seeds, case grammar, training schedule and node identity rules are frozen before the first response; changed code on resume fails closed.
- Do not interpret procedural composition as generalization learned by Verdant. The rule is human-supplied; this is evidence-backed combinatorial execution.

## Durable evidence

The runner accepts explicit `start`, `status`, `resume`, and `grade` commands and never executes automatically on repository push. New output folders are mandatory. Every stage embeds a native VDK checkpoint, fingerprints, a hash of ordered native transitions, actual teacher-supplied/missing curriculum slots, and all read-only probes up to that stage. A predecessor hash links immutable stage snapshots; failed lineage prevents resume.

A complete `responses.json` is written before any call to `grade`. Grading separately produces `grades.json` with the response SHA-256 and case-level reasons. The same completed run can be validated/replayed without new cycles, and an interrupted run resumes after the last durable milestone.

## Verified before the user's full run

The focused GitHub suite includes native three/four-link composition without an answer fact, precise evidence tracing, no-rule/incomplete/wrong-link controls, unreachable-ceiling abstentions, case disjointness, checkpoint reload, interruption/restart byte equality, altered stage and source-manifest rejection, old v0.65 artifact hash guards, and a native 200-cycle-per-arm integration run with durable grading. See the experimental workflow `.github/workflows/structural-transfer-tests.yml`.

## Claims still missing

The current design has no spontaneous goal formation, autonomous procedure induction, general arithmetic, actual cross-domain curriculum, dynamic Attention-based lesson selection, independently acquired semantic meaning, physical control, consciousness, or canonical Resolution/promotion authority. Three seeds are replicates of one task construction, not proof of transfer to independent data distributions. A complete 12,000-cycle **per arm** study is outside this increment.

See `docs/STRUCTURAL_TRANSFER_POWERSHELL.md` for the complete Windows sequence.
