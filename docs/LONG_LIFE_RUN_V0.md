# Long-life run v0 (observer; IMPLEMENTED-EXPERIMENTAL)

    python run_observer_long_life.py --lessons 2500 --arm all

Generates one continuous life (`curriculum_packs/generate_long_life_pack_v0.py`) and runs four
organisms on it: stock, + recurrence, + bond clock, + rehearsal. Resumable: rerun the same
command. Output goes to `long_life_runs/` (one `.jsonl` checkpoint log per arm).
Promotion is the same in every arm: every 20 lessons, up to 4 engine-eligible candidates go
through the ordinary Council promotion. The expectations file is used only by the read-only
checkpoint scorer.

## OBSERVED: 406-lesson life, life seed 9001, kernel seed 2301 (about 1,800-2,100 cycles per arm)
46 families meet every stated gate (11 massed, 15 short gaps, 15 long gaps, 5 returning after a silence).
| arm | promoted | massed | short gaps | long gaps | returning | cues recalled exactly | wrong promotions |
|---|---|---|---|---|---|---|---|
| stock | 9/46 | 8/11 | 1/15 | 0/15 | 0/5 | 42/148 | 0 |
| + recurrence | 14/46 | 11/11 | 3/15 | 0/15 | 0/5 | 51/148 | 0 |
| + bond clock | 31/46 | 11/11 | 15/15 | 0/15 | 5/5 | 106/148 | 0 |
| + rehearsal | 32/46 | 11/11 | 14/15 | 2/15 | 5/5 | 112/148 | 0 |
No under-exposed (14), single-context (6) or one-off (28) family was promoted in any arm, and
no distractor-only structure. A resumed run reproduces an uninterrupted run's fingerprint.

Cost: living bonds at the end were 96 (stock, recurrence) and about 230 (bond clock, full), and
the last checkpoints cost 3.1 / 4.1 / 7.8 / 9.6 s per beat. Those timings were taken with two or
three arms sharing two cores, so they overstate an idle machine, but the ordering is real: every
plasticity event stores every living bond, so remembering more costs more per beat.
One life seed, one kernel seed. Long gaps (30-90 lessons) remain mostly unsolved.
