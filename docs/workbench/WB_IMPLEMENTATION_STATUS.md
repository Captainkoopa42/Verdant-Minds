# Verdant Workbench Implementation Status — V5 / 1.0.1

## Baseline

Engine: Milestone 19 / 189-test Ethomorphism benchmark baseline.  
Workbench: WB-00 through WB-09 complete, followed by the 1.0.1 release-audit/polish pass.  
Engineering specification: `ENGINEERING_SPEC_v0.1.md`.

## Completed Workbench chain

- **WB-00** Architecture Freeze and Scaffold — complete.
- **WB-01** Engine Adapter + Isolated Worker — complete.
- **WB-02** Project / Run / Checkpoint persistence + branching — complete.
- **WB-03** Live API + Cultivation Console — complete.
- **WB-04** Curriculum Studio + Grammar Lab — complete.
- **WB-04.1** Editable Teaching Records — complete correction.
- **WB-05** Structures + Forensic Explorer — complete.
- **WB-06** Living Explorer — complete.
- **WB-07** Experiment Manager / Verification Packages — complete.
- **WB-08** Provider Connections — complete.
- **WB-09** Plugin SDK / Packaging / Hardening — complete for the local-laboratory scope.

## 1.0.1 release-audit additions

- corrected stale Workbench milestone/version labels and documentation;
- promoted **Evidence** and **Timeline** to first-class operational laboratory surfaces;
- added exact release/build identity (`release_id`, engine source SHA-256, Workbench source SHA-256, dependency-lock SHA-256);
- new `.vexp` manifests lock those exact source/build identities and refuse execution if a declared build hash does not match the current release;
- added `requirements-lock.txt` for the tested Python environment;
- pinned frontend source-build package versions while keeping the checked-in dependency-free `dist/` as the canonical runnable UI;
- added `verify_release.py` to encode the safe verification partitions and final diagnostics;
- refreshed the top-level V5 quick-start and release documentation.

## Verification state

- Cognitive engine: **189 passing tests** in established fresh partitions.
- Workbench: **61 passing integration/contract tests** (56 prior + 5 release-polish tests), verified with fresh-process execution where necessary.
- Combined verified total: **250 tests**.
- WB-08 and WB-09 machine proofs remain the final provider/plugin hardening gates.

The hosted build environment still shows a cumulative slowdown when many heavy numerical pytest partitions are run under one long parent process. The release therefore records the exact safe partitions/node-level commands in `verify_release.py`; individual fresh-process partitions pass and are the authoritative verification method for this environment.

## Release boundary

The original WB-00 through WB-09 roadmap is closed. Workbench 1.0.1 is the V5 laboratory release candidate. Further work is post-1.0 research/product work: scaling, larger curricula, publication campaigns, richer analyses, provider adapters, plugin kinds, desktop packaging, stronger sandboxing, and robotics interfaces.
