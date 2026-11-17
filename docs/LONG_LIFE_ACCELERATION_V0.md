# Long-life acceleration v0 (branch `experimental/long-life-spine-v0`, local, uncommitted)

Goal: make a 12,000-cycle arm affordable. No file under `verdant_*` is edited.

## Where the time went (lesson 150, cycle ~720, fingerprint sidecar only: 3,156 ms/beat)
| share | what |
|---|---|
| 65% | fingerprints: 12.6 semantic + 2 full + 14 structural per beat, each re-encoding and re-hashing all history |
| 27% | three deep copies of the whole state per beat (2 snapshots + staged constructor) |
| 1%  | the pipelines themselves (16-40 ms) |

## Byte-exact accelerators (`install_long_life_acceleration()`, opt-in, identity unchanged)
* `structural_copy`: copies containers, shares frozen records.
* record bytes cached across beats (possible once records are shared), append-only prefix reuse
  for history lists, digest memo for repeated fingerprints of an unchanged state.
* `*_structural_fingerprint`: stock method body runs unchanged; record dumps are spliced from cache.
Relies on the frozen-record invariant (nothing mutates a dict/list inside a committed record).

OBSERVED (Vast pack prefix, seed 2301, this machine):
| lesson | fingerprint sidecar only | long-life | 
|---|---|---|
| 60  | 725 ms  | 229 ms |
| 160 | 3,045 ms | 779-825 ms |
| 320 | not run | 1,759 ms |
160 lessons: 224.6 s -> 66.2 s, final fingerprint identical (18ef1577...).

Verification: `VERDANT_FINGERPRINT_VERIFY=1 pytest -p sidecar_acceleration.pytest_long_life_plugin`
recomputes every digest by the reference definition and checks after every beat that the
superseded state is unchanged. 203 phase tests + 1,974 other tests passed that way.
5 failures in that run are the accelerators' own test files, which assume they start
uninstalled; run on their own they pass (15/15). Workbench tests were not run.

## What is left, and why it cannot be removed byte-exactly
Cost still grows about 5.5 ms per beat per lesson. The canonical fingerprint is one SHA-256
over the whole canonical JSON, and each PlasticityEvent embeds every proposed association,
so the bytes to hash grow with history times bonds.

## EXPERIMENT (not canonical): `chained_identity_experiment`
A piecewise identity (hash chain for history lists, per-record digests). Fingerprint VALUES
change. Deterministic across two runs. 320 lessons: 157 s vs 275 s; 969 ms/beat at lesson 320.
Still linear (~3 ms per lesson): the structural fingerprints, `_validate_state` and
`_derive_field_address` re-walk history every beat regardless of the identity scheme.

## Projection for one 12,000-cycle arm (~2,500 lessons), assuming the lines continue (untested past 320)
fingerprint sidecar only: 16 h or more | long-life byte-exact: about 5 h | chained identity: about 2.6 h.

## Decisions for the owner
1. Adopt a piecewise identity? Every stored fingerprint and frozen artifact would need re-freezing.
2. Make structural fingerprints and state validation incremental? That is the spine rebuild.
