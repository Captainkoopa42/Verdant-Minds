# Long-horizon readiness and execution ledger

Updated 2026-10-13. Branch: `test/long-horizon-curriculum-v0`. Parent baseline: experimental obligation-substrate v0.65.

## Verified now

- Existing user-run nonresumable **50-cycle × 12 arms** benchmark: 600 native cycles in 6.39 s, one recalled teacher fact in progressive and rehearsal roles per seed, zero in untrained roles.
- Existing user-run nonresumable **250-cycle × 12 arms** benchmark: 3,000 native cycles in 50.83 s; progressive 5/20, rehearsal 1/20, untrained 0/20 per seed; all three seeds identical, no wrong replies; 24 saved checkpoints taking 8.75 MB.
- Native 1,000-cycle **per arm** preflight still uses explicit teacher testimony, no inferred mathematical rule. It is not the full 12,000-cycle per-arm long curriculum.
- `verdant_math/long_horizon_preflight/resumable.py` adds immutable canonical-json stages with native VDK bytes, checkpoint digest, native fingerprint, complete response probes, teaching lineage, transition chain, and per-arm stage predecessor hashes. Frozen code manifest is checked before resuming. Status and resume are explicit CLI commands.
- A run interrupted after a committed milestone resumes only the uncommitted cycles. Orphan `.part` members are discarded only under a filesystem process lock and only when their target is absent; finished members are not overwritten.
- **13/13 focused tests passed in GitHub Actions**, including real 50-cycle supplied-fact recall, simulated interruption and byte-identical completion versus uninterrupted execution, tamper rejection, source-manifest rejection, and v0.65 artifact hash guards. Workflow: https://github.com/Captainkoopa42/Verdant-Minds/actions/runs/38458796417
- **USER-REPORTED COMPLETE:** The user has now supplied console output for a 1,000-cycle-per-arm, 12-arm Windows run (12,000 operations; 636.0738186 seconds), with every arm at cycle 1,000. Final per-seed correct/20: progressive 8, rehearsal 1, activity 0, delayed 8; no incorrect answers reported. These results are logged in `docs/LONG_HORIZON_V02_WINDOWS_RESULTS.md`. Underlying run artifacts have **not** been independently replay-verified or archived in GitHub.
- **STILL MISSING:** The full 144,000-operation adaptive curriculum and its disjoint transfer tests; the entire historical test suite was not rerun for this change.

## Next steps

1. Pull the branch and run 13 focused tests on Windows. This verifies the platform-specific lock path.
2. Run a new resumable 50-cycle Windows smoke and grade; use a fresh output directory.
3. Verify the reported completed 1,000-cycle run's durable `.vstage` checkpoints and `responses.json`/`grades.json` checksum before upgrading evidence status. PowerShell instructions: `docs/LONG_HORIZON_RESUMABLE_GUIDE.md`.
4. Inspect teaching/retention curves, checkpoint sizes and per-seed failures; compare against rehearsal and delayed controls. No general learning claim from storage alone.
5. Independently implement genuinely disjoint transfer tasks and preregister threshold/evaluation controls before attempting any full 12,000-per-arm adaptive curriculum.

## Hard boundaries

Do not modify original v0.65 artifacts. Do not merge experimental milestone branches, use auto-seed-on-push, promote private lessons to canonical state, infer mathematical understanding from memorized facts, or treat an interrupted run as complete.