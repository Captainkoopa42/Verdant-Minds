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

## Post-release WB-11 — Curriculum Packs & Batch Cultivation

Implemented on the continuing `V5` development line after the frozen `v5.0.0` / Workbench 1.0.1 release:

- `verdant.curriculum.pack.v1` schema and deterministic backend validation;
- ordered, selectable curriculum sections containing the same explicit `EditableTeachingItem` records used by the manual builder;
- pack/section language-scaffold merge with duplicate suppression;
- deterministic flattening into `verdant.teaching.bundle.v1` before the existing curriculum compiler;
- pack compilation and freeze API routes;
- Curriculum Studio Manual Builder / Curriculum Packs modes;
- `.vcpack` JSON import, paste, validation, export, section selection, per-section preview/freeze/queue/run, and selected-section batch actions;
- optional section test cues appended as ordinary recorded `PROBE` queue items by `Run + probes`; no synthetic pass/fail judgement is added;
- three WB-11 integration/API/UI regression tests.

WB-11 does not add a privileged cognition path. Packs are an authoring/orchestration layer only; frozen execution still uses the existing `.vcurr` artifact and normal run queue.

Post-WB-11 Workbench verification is **64 passing tests** in fresh-process partitions: the prior 61-test Workbench release suite plus 3 new WB-11 pack tests. The engine source is unchanged from the 189-test V5/M19 baseline, so the development branch now has 253 known passing engine + Workbench tests. The frozen `v5.0.0` release manifest remains intentionally unchanged; a new Workbench release number should only be assigned after a clean target-machine verification and release audit.
