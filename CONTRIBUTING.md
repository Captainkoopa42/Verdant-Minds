# Contributing to V5

V5 is both an executable cognitive-engine research generation and a local experimental laboratory. Changes should preserve the distinction between canonical engine state, laboratory orchestration, historical evidence, and interpretation.

## Before changing code

1. Read [STATUS.md](STATUS.md), [docs/architecture.md](docs/architecture.md), and [docs/reproducibility.md](docs/reproducibility.md).
2. Identify the layer being changed: kernel, sensory/media, developmental mechanism, earned structure, benchmark, Workbench control plane, or documentation.
3. State which canonical records, policies, fingerprints, schemas, or experiment claims are affected.
4. Preserve the existing milestone and release reports as historical records; add a correction or revalidation record rather than silently rewriting an earlier result.

## Engineering rules

- Canonical cognitive truth belongs to `KernelState`, not the Workbench database or UI.
- Preserve exact native evidence before translation.
- Translation, resonance, plasticity, perception, and structural promotion must not silently create unsupported semantic truth.
- Inspection should be pure; commitment should validate staleness, integrity, and authorization.
- Replays must be idempotent, and conflicting event-key reuse must fail.
- Historical structures and evidence must remain inspectable after revision, splitting, ablation, or branching.
- External providers produce reviewable teaching artifacts; they are not part of the cognitive substrate.
- Do not describe evaluator-selected objects as autonomously discovered.
- Keep controlled benchmark claims narrower than general capability claims.

## Required verification

Use the complete procedure in [TESTING.md](TESTING.md). Do not rely on plain `pytest -q` or the current `verify_release.py` alone when claiming the entire branch passes; each misses part or all of the Workbench suite.

For source changes, record:

- Python and dependency versions;
- every test command and result;
- current engine, Workbench, and dependency-lock hashes;
- benchmark configuration and RNG seed;
- raw result artifact and schema;
- failures, exclusions, and environmental workarounds.

## Build-identity awareness

`workbench/backend/verdant_workbench/release_identity.py` hashes all files inside every root directory named `verdant_*`, plus selected Workbench source/runtime paths. Adding a non-code file inside one of those trees changes the corresponding build identity.

Place cross-cutting documentation under `docs/` unless a package-local file is necessary and you intend that identity change. Re-run the Workbench diagnostic after any source-tree modification.

## Documentation structure

- Existing root milestone and Workbench reports are historical evidence.
- Root operating files explain how to install, test, and assess the current branch.
- `docs/` provides the canonical cross-system engineering map.
- Directory READMEs describe local artifact/test/Workbench collections without replacing the detailed historical reports.
- New corrections must name the superseded claim and the corrected evidence boundary explicitly.

## Security

Workbench is a loopback-first local laboratory. Do not weaken its default bind behavior, persist provider secrets, claim subprocess plugins are sandboxed, or present it as a production multi-user service without implementing and testing the missing security layer.
