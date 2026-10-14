# Auto-P promotion v0.2 — continuous developmental curriculum research

**Status:** opt-in experimental branch `test/vast-auto-p-promotion-v0`, forked from `test/vast-integrated-development-v0`. Nothing in V5, V5-X, the active Obligation Substrate research, or the user's prior 20/60/200-experience outputs was changed.

## Why

The user's first 200 experiences showed that genuine full V5/V5-X development produced 66 local plastic associations and 42 P candidates but zero promoted P structures. The original Workbench's **Promote** button invokes `VerdantStructurePipeline.promote`, which requires native quality/recurrent evidence and an actual Council authorization. The earlier headless curriculum runner never invoked that operation, so zero promoted structures is a **missing automated transition**, not evidence that earned P cannot function.

Baseline measurements: first section 20 experiences per arm: V5/V5-X 96 native cycles, 12 associations, 4 candidates; at ten sections: 200 experiences per arm, 962 native cycles, 66 associations, 42 candidates; checkpoint size 26.31 MiB per full arm, 3.16 MiB kernel-only; wall time 1981.05 seconds for all three arms. Full-state copying, validation, and cumulative-history serialization are plausible performance contributors, **not yet profiled causal estimates**.

## Experimental design

New fourth arm `v5x_auto_p` is added to the original three independent arms `v5`, `v5x_observe`, `kernel_only`. The first two remain **no-promotion matched controls** and must keep identical canonical fingerprints. The auto-P arm has the same teacher experiences and V5-X observer-only thermodynamics with **thermodynamic control off**, but uses the native Workbench-equivalent gated promotion action at predeclared section boundaries. Kernel-only remains a teaching-storage control. All arms share one seed within a cohort, independent durable VDK histories, and identical compiled teaching input hashes.

The auto-P policy is source-frozen external research scaffolding:
1. After completing one 20-item section, find current native candidates marked `ELIGIBLE`; sort by decreasing occurrence count and deterministic candidate ID.
2. Limit to **four successful promotions per section** (not four candidates of guaranteed success). Do not change any native quality thresholds, recurrence requirements, evidence-kind gates or Council policy.
3. Re-run `VerdantStructurePipeline.inspect_promotion` against the current state, check the resulting eligible disposition; then build the exact native `promotion_council_proposal` and read-only Council `inspect`. Denials are documented without an attempted unauthorized commit.
4. Only with native Council authorization call `VerdantStructurePipeline.promote`. This revalidates and commits actual native Council and structure events. Never forge authorization, assign a human semantic label or treat P as an externally validated truth.
5. Preserve each promotion's candidate ID, resulting P structure ID, Council-decision event and promotion-event ID, plus denial and cap reasons in the immutable section receipt. Validate that promotions survived in the checkpoint with their native Council provenance.
6. Take *read-only* Workbench compilation and obligation observations after the boundary promotion. Compare the resulting P reuse possibilities against the two unpromoted developmental controls.

The four arms do **not** have equal computational work: a promoted P triggers extra Council and structure transitions and can affect subsequent workspace/compilation behavior. Report both the fixed teacher-experience denominator and measured internal native cycles/time. The contrast isolates **policy-controlled P promotion** in a specific bounded curriculum, not algorithm learning.

## Strict exclusions

- No automatic Q formation or Q promotion; no `VerdantStructureInteractionPipeline` or `VerdantHierarchyPipeline` invocation. Those require separate experimental contracts after P promotion behavior is characterized.
- No automatic obligations, inquiry, self-directed scheduling, simulator writeback, policy rewriting or autonomous semantic truth.
- No behavior-changing thermodynamic policy. Access pressure and thermo remain observer-only, preserving the existing negative detector findings.
- The original 200-experience baseline artifacts are immutable and **cannot be resumed using a different source-locked experiment revision**. Clone this new branch into a new Windows folder; start a **fresh** output directory. Never copy old stages or manifest into it.
- No auto-promote candidate without native quality eligibility and Council authorization. Some or all of the 42 observed candidates may be TRACKING rather than ELIGIBLE. Zero promotions is a possible legitimate outcome.
- No automatic correct-answer scoring: the 240 `.vcpack` probes are teacher-specified cue inspections, not a held-out knowledge examination.
- The P scheduler itself is deterministic, pre-programmed evaluator policy. A positive result does not demonstrate that Verdant learned *when* to promote without supplied control logic.

## Next evidence

Pass narrow automated tests for pre-eligibility refusal, Council-backed promotion, preservation of semantic identities, source-tamper detection, interrupted multi-section recovery, and the original unpromoted native controls. Then run **one section × one seed** with the real operator VCpack and measure how many candidates are ELIGIBLE at its first checkpoint. If at least one is eligible and authorized, check P reuse via compilation probes; if zero, first inspect native quality rejections and whether the curriculum's section contexts support cross-context stability. Continue three sections only after the first cohort is validated. Do **not** launch the expensive 30-section curriculum without measuring memory and runtime.
