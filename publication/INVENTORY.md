# VPC-1 Phase 0 inventory

Inventory opened: 2026-08-05 UTC.

## Candidate repository

- Repository: `Captainkoopa42/Verdant-Minds`
- Local branch: `wb11-worker-response-sync-fix`
- Architecture baseline at inventory start: `b0f73a1`
- Q evaluation harness commit: `d3c147e`
- Remote tracking state at inventory start: local branch ahead of `origin/wb11-worker-response-sync-fix` by seven commits
- Existing release identity: Verdant Minds V5 / Workbench 1.0.1

## Runtime boundary

- Required Python: 3.11 or newer
- Phase 0 Linux interpreter: Python 3.12.13
- Dependency source: `requirements-lock.txt`
- Isolated environment: repository-local `.venv/` (ignored by Git)
- Current dependency lock SHA-256: `bb0dd24142ccb66437fac60a38d07f9a95004a85a029c3f870da7d226e598b64`
- Historical dependency lock SHA-256 recorded by `RELEASE_MANIFEST.json`: `5eb79eff88945b21695ee2f36c512fe3440ebf461d9917aea49499329616d10a`

`RELEASE_MANIFEST.json` describes the earlier Workbench 1.0.1 release audit. The publication candidate has later fixes and evaluation code, so its identity is recorded separately rather than silently rewriting that historical manifest.

## Current test boundary

- Engine and evaluator tests collected: 192
- Workbench tests collected: 75
- Total current tests collected: 267
- Previous release manifest boundary: 250 tests
- Newly included verification areas: repeated Q evaluation, explorer worker timeout policy, runtime stability guard, and WB-11 curriculum packs
- Authoritative runner: `.venv/bin/python verify_release.py`

The complete current boundary passed locally during Phase 0: 267 of 267 collected tests, followed by the startup and artifact diagnostic. The full console record and installed-package snapshot are stored under `publication/environments/`.

## Existing scientific evidence

- Historical First-Q archive with Q present -> ablated -> restored work `3 -> 4 -> 3`; retained as a case study because its query was not a truly held-out fourth P.
- Controlled Q evaluation with 16 of 18 difficult held-out positives selecting the expected Q at `0.985`.
- All 18 recorded unrelated negative structures rejected by Q.
- Two Q misses preserved correct exhaustive fallback.
- Two complete four-arm seeds passed 30 of 30 declared checks.
- One exploratory scaling seed recorded Q work of 3 while exhaustive work grew `6 -> 14 -> 22` across 0, 4, and 8 unrelated P structures.

These are feasibility and exploratory records. They justify the publication campaign but are not the sealed confirmatory dataset.

## Existing system and artifact surfaces

- Canonical engine modules for kernel, language, claims, ECWF, governance, shards, workspace, perception, plasticity, structures, compilation, interaction, hierarchy, and refolding
- FastAPI Workbench backend and dependency-free browser UI
- Checkpoint, replay, branch, event-lineage, curriculum-pack, experiment, evidence, and forensic-structure surfaces
- Milestone 1-19 reports and machine artifacts
- Workbench WB-01 through WB-11 reports, proofs, and tests
- Ethomorphism four-arm benchmark
- Repeated Q evaluation harness and bundle writer

## Known gaps at Phase 0 start

- Candidate branch and publication tag are not synchronized to the remote.
- No sealed protocol or locked manifest exists.
- Eight-family generators and multi-Q isolation tests are not yet implemented.
- Structured campaign failure records and analysis schemas are not yet implemented.
- Confirmatory sample counts have not been run.
- Windows/Linux cross-platform equivalence has not been executed for the publication subset.
- No independent cold reproduction has been completed.
