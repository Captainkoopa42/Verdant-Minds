# Windows 1,000-cycle-per-arm preflight — reported result (2026-10-13)

**Source status: USER-REPORTED CONSOLE OUTPUT; NOT INDEPENDENTLY ARTIFACT-VERIFIED.**
Protocol: native long-horizon retention preflight v0.2 (`verdant_math.long_horizon_preflight.resumable`).
Parent branch: `test/long-horizon-curriculum-v0`, which preserves v0.65 frozen artifacts.

## Reported execution

- Each of three seeds (`79066`, `79067`, `79068`) completed each of four roles (`progressive`, `rehearsal`, `activity_control`, `delayed`) through cycle 1,000.
- The console recorded checkpoint publication at cycles 250, 500, 750 and 1,000 for each arm. Initial cycle-0 stages are stored by the runner.
- Total charged native operations: 12,000 = 1,000 per arm × 12 arms.
- Reported run wall time: 636.0738186 seconds (~10m 36s).
- The CLI printed both `long-horizon-resumable-1000/responses.json` and `long-horizon-resumable-1000/grades.json`, with successful grading exit status.

## Final assessment (all 20 cases, per seed)

| Role | Correct | Incorrect | Abstained |
|---|---:|---:|---:|
| Progressive | 8 | 0 | 12 |
| Rehearsal | 1 | 0 | 19 |
| Activity control | 0 | 0 | 20 |
| Delayed | 8 | 0 | 12 |

The same reported table held for all three seeds. Across twelve final per-arm evaluations (240 responses): **51 correct, 0 incorrect, 189 abstained**. These outcomes are aggregate user-reported results only, and not a separately inspected replay of the original `.vstage`, `.vdk`, response or grading files.

## Narrow interpretation

- All eight progressive teacher-supplied facts remained directly retrievable at cycle 1,000. The earliest was supplied at cycle 25, approximately 975 charged cycles prior; subsequent probes were read-only.
- The same eight explicit facts remained retrievable after the delayed arm's later lessons.
- Rehearsal recalled one repeatedly supplied fact. The activity-only control correctly abstained on the fixed test set.
- **No incorrect outputs** were reported, but abstentions still count in full 20-case denominators.
- Given the exact-fact retrieval implementation, these results support private claim persistence and checkpoint continuity only. They do **not** show generalized arithmetic, compositional skill transfer, increasing learning efficiency, autonomous discovery, causal self-repair, or a learner becoming smarter merely because more cycles elapsed.
- The three seeds share the exact lesson sequence and test set; matching outcomes are not independent task-set replication.

## Evidence outstanding

1. Preserve the complete immutable `responses.json`, `grades.json`, and `manifest.json`, and the per-arm stage directories on the user's Windows machine.
2. Independently validate each stage/replay (`python -m verdant_math.long_horizon_preflight.resumable status <folder>`), compare response SHA against grade receipt, and inspect per-probe counts and full per-case sources.
3. Inspect checkpoint size and elapsed time at each milestone; no 144,000-operation runtime estimate is established by one run.
4. Create a **new independent prospective** transfer curriculum testing whether earlier evidence helps on disjoint skills. Do not recycle evaluated questions or silently widen 0–21. Freeze matched controls, budgets and scoring before responses.

## Authority boundary

This result is a completed native persistence exercise, **not** the 12,000-cycles-per-arm (144,000 total) curriculum. It authorizes no canonical Resolution, knowledge promotion, autonomous policy change, harm inference, physical actuation or consciousness claim.