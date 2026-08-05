# Verdant publication evidence package

This directory is the controlled source for the first Verdant publication campaign. It separates scientific protocol, raw evidence, analysis, and narrative claims so that a result cannot quietly change while the paper is being written.

## Operating order

1. Open `../PUBLICATION_STATUS.md`.
2. Confirm the current phase and exactly one next action.
3. Read `PUBLICATION_FREEZE_POLICY.md` before changing code.
4. Use only development or validation manifests until the locked manifest is sealed in Phase 3.
5. Write experimental outputs append-only. Never overwrite a failure.
6. Connect every paper claim to `claims/claim_registry.yaml`.

## Directory roles

- `claims/` maps proposed paper claims to research questions and evidence.
- `protocol/` holds the versioned protocol and append-only deviation registry.
- `manifests/` holds development, validation, and eventually locked case manifests.
- `environments/` records the exact runtime used for each platform.
- `hashes/` records immutable hashes for candidates, manifests, raw results, and analysis outputs.
- `raw/` will contain append-only machine records from executed cases.
- `processed/`, `tables/`, and `figures/` will be generated from raw records by script.
- `failures/` will preserve cognitive failures, infrastructure failures, and exclusions with explicit classifications.
- `reproduction/` will contain cold-run and cross-platform reproduction records.
- `paper/` will contain the manuscript and technical appendix after evidence gates are evaluated.

## Important boundary

Family names and expected answers belong to the external evaluator. They are scoring labels, not semantic truths taught to Verdant. Confirmatory evidence is not valid if hidden labels or expected outcomes enter Verdant's canonical state.

No locked test manifest exists yet. Any result produced before Phase 3 is exploratory or validation evidence and must be labeled as such.

