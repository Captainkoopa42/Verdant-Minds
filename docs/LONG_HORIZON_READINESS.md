# Long-horizon readiness and execution ledger

Updated 2026-10-13. Branch: `test/long-horizon-curriculum-v0`. Parent baseline: experimental obligation-substrate v0.65.

## Verified now

- Existing user-run nonresumable **50-cycle × 12 arms** benchmark: 600 native cycles in 6.39 s, one recalled teacher fact in progressive and rehearsal roles per seed, zero in untrained roles.
- Existing user-run nonresumable **250-cycle × 12 arms** benchmark: 3,000 native cycles in 50.83 s; progressive 5/20, rehearsal 1/20, untrained 0/20 per seed; all three seeds identical, no wrong replies; 24 saved checkpoints taking 8.75 MB.
- Native 1,000-cycle **per arm** preflight still uses explicit teacher testimony, no inferred mathematical rule. It is not the full 12,000-cycle per-arm long curriculum.
- `verdant_math/long_horizon_preflight/resumable.py` adds immutable canonical-json stages with native VDK bytes, checkpoint digest, native fingerprint, complete response probes, teaching lineage, transition chain, and per-arm stage predecessor hashes. Frozen code manifest is checked before resuming. Status and resume are explicit CLI commands.
- A run interrupted after a committed milestone resumes only the uncommitted cycles. Orphan `.part` members are discarded only under a filesystem process lock and only when their target is absent; finished members are not overwritten.
- **13/13 focused tests passed in GitHub Actions**, including real 50-cycle supplied-fact recall, simulated interruption and byte-identical completion versus uninterrupted execution, tamper rejection, source-manifest rejection, and v0.65 artifact hash guards. Workflow: https://github.com/Captainkoopa42/Verdant-Minds/actions/runs/38458796417
- **No full 1,000-cycle recovery cohort has yet been executed**, nor the full 144,000-operation long curriculum. The entire historical test suite was not rerun for this change.

## Next steps

1. Pull the branch and run 13 focused tests on Windows. This verifies the platform-specific lock path.
2. Run a new resumable 50-cycle Windows smoke and grade; use a fresh output directory.
3. Run 1,000 cycles per arm across four roles and three seeds, with status/resume if interrupted. Grade only after all response records are durable. PowerShell instructions: `docs/LONG_HORIZON_RESUMABLE_GUIDE.md`.
4. Inspect teaching/retention curves, checkpoint sizes and per-seed failures; compare against rehearsal and delayed controls. No general learning claim from storage alone.
5. Independently implement genuinely disjoint transfer tasks and preregister threshold/evaluation controls before attempting any full 12,000-per-arm adaptive curriculum.

## Hard boundaries

Do not modify original v0.65 artifacts. Do not merge experimental milestone branches, use auto-seed-on-push, promote private lessons to canonical state, infer mathematical understanding from memorized facts, or treat an interrupted run as complete.