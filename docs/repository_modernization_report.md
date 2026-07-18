# Verdant Minds V4 Repository Modernization Report

Date: 2026-07-18

This report records the Phase 1 inventory and the non-destructive cleanup decisions made for this pass. The operational patched runner was treated as a behavioral specification, but the canonical `verdant/` runtime package is not present in this checkout, so runtime monkey-patch promotion could not be safely implemented here.

## Phase 1 inventory summary

A complete file-by-file inventory is stored in [`docs/repository_inventory.csv`](repository_inventory.csv).

| Classification | Count |
| --- | ---: |
| Core Runtime | 39 |
| Runtime Dependency | 9 |
| Test | 65 |
| Documentation | 19 |
| Example | 25 |
| Tooling | 41 |
| Research | 17 |
| Legacy | 2 |
| Generated Output | 83 |
| Dead Code | 0 |
| Duplicate | 0 |

## Runner divergence review

The patched operational runner identifies verified runtime corrections in these areas:

- `VerdantSystem.load_state()` should propagate the checkpoint path to `_checkpoint_path` before/while restoring state.
- `ShardedMemoryWeb.thaw()` should size its warm LRU cache from the shard manifest, self-heal missing shard entries, initialize shard canvases safely, and reload mandatory bridge ghosts after thaw.
- Memory graph edges and cached `memory_store[*]["connections"]` must be dual-written or rebuilt after pruning/regulation to avoid phantom edges.
- `ThreeKingsCouncil` state, especially `influence_weights` and interaction history, must persist in the main checkpoint with legacy sidecar compatibility where needed.
- Runtime persistence should maintain checkpoint continuity across save/load/resume.
- Mitosis runtime thresholds in the runner are tuned to larger shard caps and watch limits than older repository defaults.

## Critical blocker discovered

This checkout does not contain the `verdant/` package even though `pyproject.toml`, `README.md`, docs, tests, and the runner all reference it. Because of that, the repository cannot currently be installed as the canonical Verdant Minds V4 runtime, and the runner cannot execute without external/missing source. This pass intentionally did not recreate or copy runtime architecture from the monkey patches.

## Phase 2 deletion decisions

Deleted: nothing. No compiled Python caches, temporary editor files, or `.ipynb_checkpoints` directories were present. Generated `results/` and verification bundles were preserved because they may support papers/reproducibility and require maintainer approval before deletion.

## Phase 3 reorganization decisions

Moved/renamed: nothing in this pass. Because the primary runtime package is missing, moving tests, papers, or examples would add churn without improving runner compatibility.

## Phase 4 documentation decisions

Updated the top-level README to consistently present Verdant Minds V4, clarify the current repository layout, and flag the missing canonical `verdant/` package as a maintainer-facing blocker instead of implying `pip install -e ./verdant` works in this checkout.

## Preserved intentionally

- Patched runners: retained as behavioral specifications for V4 runtime divergence.
- `results/`: retained as generated research artifacts pending explicit approval.
- V2/V3 papers, audits, notebooks, and tests: retained as repository history/reproducibility material.
- `tests_v2/`: retained because many tests appear to exercise the intended runtime API even though the runtime package is absent in this checkout.

## Suspicious items requiring manual review

- Missing `verdant/` source package while tests import `verdant.*` and packaging advertises `verdant*`.
- Top-level `verdant_bridge.py` may be a compatibility bridge, but it is not a substitute for the missing package.
- `results/v2/` contains generated output and may be a candidate for archival outside the repo if not required for reproducibility.
- Duplicate-looking patched runner copies exist (`Verdant_Minds_Runner_Patched (2).py` and `colab/Language_Cultivation_v6_patched.py`) but were retained because they encode operational behavior.

## Runtime bugs discovered

The runner documents the bugs listed in the divergence review, but the affected modules are absent from this checkout, so this pass could not apply regression fixes directly.

## Next required maintainer action

Restore or provide the canonical `verdant/` runtime package, then apply the runner-derived fixes in the proper modules with regression tests for checkpoint continuity, shard thaw recovery/LRU sizing, graph/cache synchronization, council persistence, and mitosis tuning.
