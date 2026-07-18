# V4 Runtime Alignment Audit

This document tracks the cleanup of the `V4` branch against the runner used for current Verdant Minds cultivation runs.

## Source of truth

The cleanup treats the following as authoritative, in descending order:

1. The current working Colab runner (`Verdant_Minds_Runner_Patched (2).py` / the newer V8 runner used in live testing).
2. Checkpoints and shard layouts produced by real V4 runs.
3. `VerdantSystem`, `QueryInterface`, cultivation, persistence, sharding, evaluation, and trace-export behavior exercised by that runner.
4. The data contract consumed by the Verdant trace viewer.

Historical code is not considered part of the supported V4 runtime unless it remains executable through a documented entry point or implements a current plugin interface.

## Confirmed runtime drift

The current runner applies temporary monkey patches before importing the system. These patches identify repository behavior that must be moved into the implementation and covered by regression tests.

### P0 — persistence and sharding

- `VerdantSystem.load_state(path)` must set `_checkpoint_path` from `path` before shard operations occur.
- `ShardedMemoryWeb.thaw()` must use `manifest.defaults.lru_cache_size` instead of a hard-coded warm-cache limit.
- Missing shard files must not crash an otherwise recoverable run. Manifest and concept-index repair must be explicit, logged, and tested.
- Shard save/load tests must cover checkpoint relocation, repeated reloads, and zip upload/download workflows.

### P0 — graph consistency

- Edge removal must keep the NetworkX graph and `memory_store[*]["connections"]` synchronized.
- `prune_basin_edges()` and `regulate_density()` must not leave phantom cached edges or omit real graph edges.
- Add an invariant helper and regression tests that compare both representations after mutation-heavy operations.

### P0 — governance continuity

- `ThreeKingsCouncil.influence_weights` and bounded `interaction_history` must persist through ordinary `VerdantSystem.save_state()` / `load_state()`.
- Existing sidecar state created by the patched runner should remain readable during migration.
- New checkpoints should use one canonical state contract unless there is a demonstrated reason for a sidecar.

### P1 — mitosis configuration

- The runner's tested `watch` caps (`450` nodes / `16000` edges) and LRU size (`8`) should be represented as named V4 configuration, not hidden notebook constants.
- Forced pre-split values may remain runner-specific, but the public configuration path must be documented and validated.

### P1 — canonical runner

- Compare the repository runner and the current V8 runner line-by-line.
- Keep one canonical full cultivation runner.
- Move optional diagnostics behind flags or helper modules rather than maintaining multiple near-duplicate runners.
- Remove runtime monkey patches only after the corresponding repository fixes and tests land.

### P1 — trace viewer contract

- Define a versioned trace/export schema between Verdant and the viewer.
- The viewer should consume an adapter/export artifact rather than arbitrary internal checkpoint fields.
- Add at least one sanitized fixture and schema compatibility test.

## Repository classification rules

Every maintained file should fit one category:

| Category | Requirement |
| --- | --- |
| Runtime | Imported by a supported V4 entry point |
| Plugin | Implements a documented V4 interface |
| Test | Executes against and asserts current V4 behavior |
| Example | Runs from documented instructions |
| Analysis | Reads current V4 outputs or checkpoints |
| Documentation | Accurately describes V4 |
| Historical | Isolated from the runtime and clearly labelled |
| Delete candidate | No supported import path, interface, test value, or historical value |

Files will not be deleted merely because they are old. A deletion requires evidence that the file is unreachable or superseded and that supported tests and runners do not depend on it.

## Immediate cleanup findings

- `README.md` on V4 still called the architecture "Verdant V3".
- `verdant/system.py` still describes the top-level system and configuration as "Verdant v2" and contains a stale V3 migration TODO despite importing from the current `verdant` package.
- Search results expose older duplicated source trees and duplicated paper paths. These require classification before removal; they must not be mixed into the supported V4 package surface.
- The README test badge says tests are passing, but the cleanup must verify the exact supported test command before retaining that claim.

## Required regression test groups

1. Checkpoint path propagation and relocation.
2. LRU cache sizing from the manifest.
3. Missing-shard repair and concept-index cleanup.
4. Graph/cache edge synchronization.
5. Council persistence, including legacy sidecar migration.
6. Repeated save/load developmental continuity.
7. Mitosis followed by reload and continued ingest.
8. See-and-Say corpus and teaching-list schema validation.
9. Evaluation-isolation restore behavior.
10. Trace export schema compatibility.

## Cleanup sequence

1. Inventory supported entry points and imports.
2. Integrate monkey-patch fixes into core modules.
3. Add regression tests for each fix.
4. Canonicalize the runner and configuration.
5. Establish the trace export contract.
6. Update all V2/V3 documentation that describes the current runtime.
7. Archive historically useful superseded material.
8. Delete only confirmed dead or duplicate material.
9. Run the supported test suite and a fresh/saved-checkpoint smoke run.

## Definition of done

V4 is considered aligned when the canonical runner can execute without monkey patches, current checkpoints continue across runs, the viewer consumes a documented versioned export, all supported tests pass, and every top-level repository area is either current, explicitly historical, or removed.
