# The Verdant organism v0: everything that earned its place, folded in

`verdant_organism` is now the one place a Verdant life is put together (`Organism(Parts())`).
Every part is switchable and its evidence is recorded in the module docstring. The stock
heartbeat and every pinned `verdant_*` file are untouched, so old results reproduce.

## Inventory (from the live map, docs and runs)
| part | status | in the default organism |
|---|---|---|
| recurrence, bond clock, surprise + reunion, sleep | validated in full lives | yes |
| memory horizon in experiences | validated (removes revision's memory cost) | yes |
| Council convenes itself | validated, 2 lives | yes |
| heat revision (departure-aware M18, never while in mind, no twins) | validated, 4 lives | yes |
| stored questions steer sleep | validated, 4 lives | yes |
| gear | watch only (sleep control not better than the clock) | watch |
| long-life acceleration | byte-exact | yes |
| senses stack, fine ear, reader | validated in their own observers; full-life test below | candidate |
| wave + folding at any depth, two-speed profiles, stance | validated in their own observers; full-life test below | candidate |
| recall / imagine, looks, recognition, obligation detectors | read-only | exposed as capabilities |
| carry-everything | harmful (5 wrong structures) | no |
| motor | removed by decision | no |
| automatic interaction / hierarchy (M16/M17), shards | not built as automatic yet | next |

## First checks (changing life 9001)
* The default organism reproduces the validated full stack bit for bit (`26775f07...`).
* Everything on: same kept / promoted (145 / 43), but the 3 `intermittent` controls were revised
  (their sometimes-missing member was dropped), and 3 wrong structures stayed in use.
* Split: senses + reader + fine ear: clean (145 / 43, 0 wrong, 0 control revised). Wave + fold +
  profiles + stance: 145 / **45** promoted, but the 3 control revisions.
* Cause in heat revision itself, exposed by those parts: a challenge, once recorded, counted
  forever, even when the "missing" member turned up again with the rest. Fixed: observations
  wait beside the organism; a sighting of the member with the rest voids them; only an unbroken
  run of absences strong enough for M18 becomes canonical. A real reversal still matures; an
  every-other-time member never does (new test). It also stops spending kernel cycles on
  challenges that never mature.

## Gate for folding the candidates (everything vs default, new heat rule)
On the four lives: kept and promoted on the passing groups not lower; active wrong 0; no control
revised; 5/5 reversals revised on the changing lives; no promotion from a failing group.

## Results (appended): everything on, new heat rule, four lives
| life | kept | promoted | active wrong | reversals revised | controls revised | failing-group promotions |
|---|---|---|---|---|---|---|
| changing 9001 | 145/148 | 43/46 | 0 | 5/5 | 0 | 0 |
| changing 4242 | 148/148 | 43/46 | 0 | 5/5 | 0 | 0 |
| old 9001 | 148/148 | 44/46 | 0 | - | 0 | 0 |
| old 4242 | 148/148 | 46/46 | 0 | - | 0 | 0 |

Equal to the validated full stack on every life (145/43, 148/43, 148/44, 148/46), with no harm.
Challenges recorded fell from ~142 to 72 and 63 per changing life (fewer organism cycles spent).
The +2 promotions seen with the old heat rule did not survive the fix: they came with the
control revisions.

**Decision: every candidate part is now on in the default organism** (`Parts()`); `Parts().lean()`
turns off the process-global patches (senses, ear, reader, wave/fold, profiles, stance).

## Wired into the system
* `run_verdant_cultivation.py` (the hand-driven teacher console) now runs the organism by
  default (`--stock` for the original Milestone 18 heartbeat). Taught by hand, the Council now
  promotes on its own (two taught families promoted without a `promote` command).
* `run_observer_long_life.py --organism default|lean|everything`.
* Constructing `CultivationSession` without an organism (as the V5x session and its tests do)
  keeps the stock heartbeat, so nothing that existed changes behaviour.

## Still on the map, not yet automatic
* Structures of structures: generic folding (now in the organism) promotes folds of folds by the
  same Council rule (depth 3 shown in RECURSIVE_FOLD_V0), but the long lives never teach groups
  of families together, so none formed there. M17's separate Q layer remains hand-driven.
* M16 interaction (relational-shape matching between earned structures) and shards (specialised
  regions) are built but not automatic; each needs its own test world (scenes / analogies /
  crowded field) before it can earn a place.
