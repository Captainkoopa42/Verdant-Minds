# Heartbeat profile, Tg-input trace, and opt-in fingerprint sidecar v0

Research branch: `test/heartbeat-profile-entropy-trace-v0`, branched from
`test/cognitive-pocket-corroboration-v2-3` commit `ec310b1`.

One pre-existing source file is edited, `verdant_pockets/corroboration.py`,
to repair a defect described below. No other source file, and no policy,
checkpoint, artifact or report, is edited. `verdant_kernel/`, `verdant_math/`, `verdant_claims/` and `cognitive_chunk_v2/`
are byte-identical to the parent, so every frozen code manifest that pins them
still verifies. The Workbench `engine_source_sha256` is unchanged.

## Why this exists

Earlier reports record a "known long-process slowdown" and treat it as
environmental. This increment measures the developmental heartbeat directly
before proposing anything, then adds one opt-in, byte-exact accelerator for
the single largest measured cost.

## New files

- `run_observer_heartbeat_and_entropy.py` — observer-only script with three
  modes (`profile`, `entropy`, `regimes`). Builds a disposable kernel and a
  seeded synthetic curriculum. No behavioral authority.
- `sidecar_acceleration/` — opt-in fingerprint accelerator. Not imported by
  any engine module. Deliberately named outside the `verdant_*` prefix so it
  is not counted as engine source while it has no authority.
- `tests/test_fingerprint_accelerator.py` — ten tests for exactness, identity
  checking, tamper behavior, install/uninstall, and verify mode.

## Measured: where a heartbeat's time goes

Command: `python run_observer_heartbeat_and_entropy.py profile --cycles 60 --window 20`
(seed 2301, state_dim 128, 512-feature text translator, default policies).

| Cycles | ms per heartbeat | State size | Concepts |
|---|---:|---:|---:|
| 1-20 | 222 | 1.20 MB | 36 |
| 21-40 | 670 | 2.76 MB | 68 |
| 41-60 | 1208 | 4.59 MB | 91 |

Time per heartbeat grows in proportion to the size of the whole state, so the
cost of a run grows roughly with the square of its length. In cycles 41-60
(inclusive timings, which overlap):

- `semantic_fingerprint`: 11 calls per heartbeat, about 614 ms. Each call
  dumps and JSON-encodes the entire state.
- `fingerprint`: 2 calls, about 110 ms.
- `snapshot` deep copies: 2 calls, about 120 ms. `VerdantKernel.__init__`
  performs a further deep copy of the already-copied snapshot that this
  observer does not time separately.
- `_validate_state`: 5 calls, about 80 ms.

One reference fingerprint of the 4.59 MB state costs about 13 ms in
`model_dump`, 45 ms in `json.dumps`, and 4 ms in SHA-256.

State composition at cycle 60: `plasticity_events` 37.6%,
`resonance_profiles` 11.2%, `resonance_events` 11.1%, `field_addresses`
11.0%, `workspace_cycle_events` 9.8%, `field` 7.6%, `transitions` 5.2%. One
resonance event is about 9.9 KB because it embeds the 512 query features and
the full candidate scope.

## Implemented-experimental: byte-exact fingerprint sidecar

`KernelState.fingerprint` remains the reference definition. The sidecar
builds the identical canonical JSON bytes but reuses the encoded bytes of a
record only when its class is frozen, has no custom serialization, is deeply
immutable by annotation, has exactly its container's declared type, and the
cached entry came from that exact object. Evidence, concepts, claims,
workspace events and anything else carrying a free-form `dict` always take
the reference path. The cache is bound to one kernel and one state object and
is discarded when the state is replaced.

Enable explicitly:

```python
from sidecar_acceleration import install_fingerprint_cache
install_fingerprint_cache()
```

or for an existing test run:

```bash
VERDANT_FINGERPRINT_VERIFY=1 python -m pytest -p sidecar_acceleration.pytest_plugin tests/...
```

With `VERDANT_FINGERPRINT_VERIFY=1` every accelerated digest is recomputed by
the reference definition and any difference raises.

Same 60-cycle run with `--accelerate`:

| Cycles | Reference ms | Sidecar ms |
|---|---:|---:|
| 1-20 | 222 | 148 |
| 21-40 | 670 | 412 |
| 41-60 | 1208 | 651 |

Both runs end at the identical reference fingerprint
`a56dac4bcb094e16d48f04a03189da34e7c5556be25e5948b1f6fbc740a3792c`.

## Measured: the h_sys input to Tg

`entropy` mode, 60 cycles: h_sys mean 0.911, standard deviation 0.007, range
0.892-0.931. The value expected from a field of independent random phasors at
state_dim 128 is 0.913. Tg stayed Flexible for all 60 cycles.

`regimes` mode, 120 cycles, alternating 20-cycle blocks of one repeated
domain and a random domain each cycle:

| Statistic | Focused | Scattered | Separation |
|---|---:|---:|---:|
| h_sys | 0.9150 +- 0.0069 | 0.9089 +- 0.0070 | 0.88 pooled stdevs |
| effective present concepts | 3.36 +- 1.13 | 5.54 +- 1.93 | 1.38 pooled stdevs |

Because h_sys stays inside roughly 0.89-0.93, the Tg term
`0.1 * sin(pi * h_sys)` stays between about 0.02 and 0.03. Its whole swing is
about 0.01, against phase boundaries at 0.38 and 0.62.

## Repair found while running the whole suite: v2.3 corroboration

`verdant_pockets/corroboration.py` at parent commit `ec310b1` contained a
literal `\n` inside a dict literal (line 78). The module could not be
imported, so `tests/test_cognitive_pocket_corroboration.py` failed at
collection and the v2.3 CLI could not run. The branch's CI is manual-only, so
this was not caught on push.

After restoring the line break, two of that file's seven tests failed for
reasons the syntax error had been hiding:

1. Independence was counted as the number of distinct
   `(source_family, source_record_id)` pairs. Two observations with different
   family labels and the *same* record id therefore counted as two
   independent sources, contradicting the module docstring, the v2.3 document
   and the test. `_independent_group_count` now merges pairs that share a
   family label or a record id (directly or through a chain) and counts the
   remaining groups.
2. `run_scaling_benchmark` reported `performance_advantage_demonstrated` only
   per row; the test reads it at the top level. The top-level key is now
   present and is the constant `False`.

This is the only pre-existing source file edited on this branch.
`verdant_pockets/` is not pinned by the math code manifests.

## Verification run (Python 3.13.18, Linux, this branch)

| Suite | Result |
|---|---:|
| Engine phase tests + accelerator tests, sidecar installed, verify mode | 199 passed |
| Frozen math line (12 files), reference kernel | 1,317 passed |
| Obligations, pockets and remaining engine files (46 files) | 626 passed |
| M19 benchmark | 10 passed |
| Thermodynamics | 18 passed |
| Workbench backend | 71 passed |

Dependencies were installed at the locked versions except that this
environment provided numpy 2.5.3, pydantic 2.13.5, pytest 9.1.1 and
opencv-python-headless 5.0.0 in place of the locked builds.

## Claim boundary

**OBSERVED:** On one seeded synthetic curriculum, heartbeat time scales with
total state size and whole-state fingerprinting is the largest single cost.
The sidecar reproduces the reference digest on every call in 199 engine
tests run in verify mode and ends a 60-cycle run at the identical
fingerprint, at roughly 1.85x the reference speed by cycle 60. h_sys sits at
the random-phasor value with a standard deviation under 0.01.

**IMPLEMENTED-EXPERIMENTAL:** An opt-in sidecar with no authority, an
observer script, and ten focused tests.

**PROPOSED:** (1) Decide whether the sidecar should ever be granted default
authority; doing so means editing `verdant_kernel/` and therefore re-freezing
every code manifest that pins it. (2) The remaining growth is structural:
every heartbeat still copies, validates and hashes all history. Removing it
needs a design decision about history ownership or a content-addressed
fingerprint, both of which change canonical identity and are out of scope
here. (3) Run the detector study with a concept-level statistic recorded
beside h_sys, predeclared, on real checkpoints.

**MISSING:** No claim that this explains the multi-test pytest slowdown; that
was not reproduced or measured here. No result on a real curriculum,
checkpoint, Windows, or runs beyond 120 cycles. The regime comparison is one
seed with two hand-built regimes and is not a detector validation. The
candidate statistic is not Tg, not a replacement formula, and was not
predeclared. Wall-clock values are descriptive only.
