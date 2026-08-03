# Verdant Workbench 1.0.1 — V5 Final Release Report

**Release:** 1.0.1  
**Repository target:** Verdant-Minds V5  
**Engine baseline:** Independent rebuild through Milestone 19  
**Workbench roadmap:** WB-00 through WB-09 complete  
**Release-audit status:** complete

## Release state

Verdant Minds V5 now packages the M19 cognitive engine with the complete local-first Verdant Workbench laboratory. The original Workbench roadmap is closed; this 1.0.1 pass was limited to release engineering, provenance, reproducibility, and laboratory-surface polish. No new cognitive mechanism was introduced.

## 1.0.1 audit corrections

- corrected stale development-version labels and refreshed backend/frontend/top-level documentation;
- made **Evidence** and **Timeline** first-class operational UI surfaces;
- added exact source/build provenance for new experiments:
  - release ID;
  - engine source SHA-256;
  - Workbench source SHA-256;
  - tested dependency-lock SHA-256;
- new build-locked `.vexp` experiments refuse execution/reproduction when a declared source/dependency hash differs from the current release;
- added `requirements-lock.txt` for the tested Python environment;
- pinned frontend source-build dependency versions while retaining the dependency-free checked-in browser `dist/` as the canonical runnable UI;
- added `verify_release.py` encoding the established safe verification partitions and node-level handling for the known long-process slowdown;
- updated the V5 quick-start and operations documentation.

## Exact build identity

```text
release_id               verdant-minds-v5-workbench-1.0.1
engine_source_sha256     62f8b3346c7efdacfea812b454a90ae78c6c7f1a19767fefc49b5d620269d77e
workbench_source_sha256  9e7ab8c3498dd8df85632c856a9b0e05eb8dc0d598155930cacd7907786a7b49
dependency_lock_sha256   323a0ffa50cfd72be26962410e28c3471704c626bad11faa99026b2c4abe61bc
```

These hashes are computed from the release source surfaces and are exposed through Engineering diagnostics. New experiment manifests freeze them for reproduction checks.

## User-facing laboratory

Workbench 1.0.1 can create/load organisms; cultivate and queue teaching; author editable curricula and grammar scaffolds; save/reopen/branch checkpoints; inspect canonical evidence; inspect P/Q structures and their provenance; replay formation without mutation; visualize recorded development; inspect run/checkpoint/event timelines; run causal ablation/restoration; freeze/run/fork/reproduce experiments; capture external provider output as editable teaching material; execute capability-limited metric plugins; and verify artifact/source integrity.

## Verification state

### Cognitive engine

```text
124 core/kernel/language/media/workspace/etc.
 32 M12-M15 development/plasticity/structures/compilation
 16 M16-M17 interaction/hierarchy
  9 M18 refolding
  8 M19 benchmark
---
189 engine tests
```

The M19 benchmark tests were rechecked with fresh node-level processes where the hosted environment exhibits cumulative long-process slowdown.

### Workbench

```text
56 pre-audit Workbench tests
 5 WB-1.0.1 release-polish/build-identity tests
---
61 Workbench tests
```

Combined verified project:

```text
189 engine
 61 Workbench
---
250 verified passing tests
```

WB-08 provider proof: `all_gates_pass = true`.  
WB-09 plugin/hardening proof: `all_gates_pass = true`.

## Packaging boundary

Workbench is a local web laboratory. It intentionally does not claim production multi-user authentication or an OS sandbox for untrusted plugins. The checked-in dependency-free frontend can run without npm. React/TypeScript source remains for future development; a trustworthy transitive npm lockfile should be generated on a normal npm registry before rebuilding/replacing the checked-in `dist/`.

## Release boundary

At 1.0.1, the V5 engine + laboratory architecture is frozen for use. Further changes should be driven by experiments: larger curricula, scaling/profiling, publication campaigns, richer visual analyses, new provider/plugin adapters, desktop packaging, stronger sandboxing, and embodiment/robotics work.
