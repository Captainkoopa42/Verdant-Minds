# Long-horizon readiness and execution ledger

Updated 2026-10-13. Branch: `test/long-horizon-curriculum-v0`. Starting source: v0.65 `25d47fb`.

## Current status

- **COMMITTED:** `docs/LONG_HORIZON_CURRICULUM_V0.md` is the proposed 12,000-native-cycle **per arm** curriculum design, not an approved frozen prospective protocol.
- **COMMITTED:** `verdant_math/long_horizon_preflight/__main__.py` implements a separate 0–1,000 cycle **per arm** feasibility experiment, with four native private roles and three seeds. It uses native ClaimLearningPipeline for supplied facts and native ExperienceCommand for unrelated events, read-only recall, checkpoints and explicit separate grading. It does not implement transfer beyond direct fact recall.
- **COMMITTED:** `tests/test_long_horizon_preflight.py` covers protocol schedule, private teaching, checkpoint/response boundaries, native unrelated events, changed-order rejection and v0.65 artifact hashes.
- **COMMITTED:** PowerShell run instructions in `docs/LONG_HORIZON_PREFLIGHT_RUN_GUIDE.md`.
- **GITHUB ACTIONS VERIFIED:** Branch static workflow `long-horizon-static.yml` passed syntax compilation and pytest discovery, collecting seven tests: https://github.com/Captainkoopa42/Verdant-Minds/actions/runs/38455013657
- **NOT YET DONE:** The seven tests have **not been executed**, no native 2-cycle smoke or 1,000-cycle pilot has been executed, no new measured retention/transfer results exist, and no full 12,000-per-arm runner or results exist.

## Mandatory next gates

1. In a real complete repository checkout, run `python -m pytest -q tests/test_long_horizon_preflight.py`; investigate any failure without weakening v0.65 frozen evidence.
2. Run isolated 2-cycle smoke; inspect checkpoint, canonical response-before-grade output and external grade artifact.
3. Benchmark a 50- or 100-cycle run for total runtime, growth of serialized checkpoint, RAM and CPU usage; estimate 1,000 and 12,000 per arm costs **empirically**. Do not launch the full experiment with unbounded resource use.
4. Address restart durability before long Colab execution: current preflight fails closed on occupied output paths and does not resume incomplete runs. Implement verified per-arm resume/reconstruction or use an uninterrupted reliable runtime. Treat partial output as incomplete, not a completed cohort.
5. Execute and independently revalidate all 12 one-thousand-cycle arms. Inspect learner histories; compare longitudinal correct/incorrect/abstained counts and all native checkpoint evidence. Evaluate whether the evidence supports only storage/retention, not transfer.
6. Implement actual multi-domain and disjoint reserved transfer tasks as independently versioned native adapters. Freeze their prospective protocols, resource limits, seeded controls, and quantitative pass thresholds before execution. The existing 0–21 v0.65 domain cannot be silently expanded.
7. Only after those gates implement and launch 12,000 cycles per arm, across four groups and three seeds (144,000 total) with periodic restart and complete response-before-grade receipts.
8. Rerun full existing suite, v0.65 history validation, and all 17 legacy checkpoints. This must be documented as actual execution, not inferred from reported prior results.

## Boundary

The preflight demonstrates an executable **test design and native teaching path**, not validated long-range learning. The presence of 12,000 prompt experiences across all arms cannot establish 12,000 learning cycles. If the system simply persists teacher-supplied facts, report retained testimony, not generalized cognition.

Do not deploy autonomous policy revisions, real-world actions, teacher-independent repair, or any form of claimed personhood from these tests. Never modify historical v0.65 artifacts or merge experimental versions.
