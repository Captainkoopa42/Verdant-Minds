# V4 Audit Fixes — 2026-07-16

Permanent codebase promotions of Language Cultivation v6 monkey patches + Defect B.

## Code changes
- `verdant/governance/council.py`
  - `to_state_dict` / `from_state_dict` (MP-5 permanent)
  - `ethics_ratio()` helper
  - Peer downweight under high conflict (Defect B / MP-6)
- `verdant/system.py`
  - `load_state` sets `_checkpoint_path` (MP-1)
  - save/load `kings.council` (MP-5)
- `verdant/memory/graph.py`
  - `MemoryWeb.remove_connection` dual-write (MP-4)
  - `ShardedMemoryWeb.thaw` honours `lru_cache_size` (MP-2)
  - thaw self-heal on missing shard files (MP-2b)
  - facade `remove_connection` delegate
- `verdant/memory/basin_dynamics.py`
  - prune / regulate use `remove_connection` (MP-4)
- `tests_v2/unit/test_governance.py`
  - council roundtrip + salience-ceiling clearance tests
- `docs/architecture.md`
  - checkpoint docs updated for council persistence

## Runner
- `Verdant_Minds_Runner_Patched_v6_MP5.py` / `VERDANT_MINDS_Language_Cultivation_v6_PATCHED.py`
  - MP-1..MP-6 belt-and-suspenders for stock GitHub V4 clones
  - MP-5 prefers in-checkpoint council, sidecar fallback, atomic sidecar write
  - MP-6 peer downweight for mandatory-bridge threshold reachability

## Policy (unchanged)
- Do not fiat-write `ethics_salience_peak = 0.35`
- Do not force `bridge['mandatory'] = True` without real threshold cross
