# Verdant-V0: Older Branch, Later Additions

`Verdant-V0` is the lowest preserved Verdant research generation, but the branch is not an untouched copy of the project as it existed on one early date. Newer research, tests, tooling, and documents were added to the older model over time.

That distinction is necessary for reading the branch correctly.

## What the branch name means

`Verdant-V0` identifies the underlying architecture generation being presented: the `usm` entry point, `UnifiedSystem`, nine-block pipeline, MemoryWeb, ECWF bridge, and Three Kings governance.

It does **not** mean that every file on the branch originated during the first V0 development period.

## Evidence of layered development

The branch itself contains several visible time layers:

| Material | What it shows |
|---|---|
| original audit dated January 2025 | an earlier assessment of the V0-era codebase |
| post-audit statements dated February 2026 | later implementation claims had been appended to that older assessment |
| whitepaper dated March 2026 | research publication and scaffolding evidence were added later |
| cultivation, coherence-feedback, pconnect, and persistence tests | later testing and instrumentation exist around the older architecture |
| top-level `verdant/` directory | part of a later development direction is preserved, but its `ethomorphic` dependency is absent here |

The old root audit combined these layers and described them as one current state. It was removed during documentation reconciliation because it contradicted both the present branch contents and the newer code-grounded status document.

## How to interpret features

A feature found on `Verdant-V0` can fall into one of three categories:

1. **V0 architecture** — part of the canonical model generation and its main execution path.
2. **Later addition to V0** — a test, feedback mechanism, persistence path, cultivation tool, analysis tool, or research document added after the initial architecture.
3. **Later-generation remnant** — material preserved on the branch that is not integrated into the runnable V0 path.

Presence on the branch proves that the file or implementation is part of the branch as currently presented. It does not by itself prove when the idea originated.

## Current classification

| Area | Classification on this branch |
|---|---|
| `usm` and `Verdant Source Codes/src/core/system.py` | canonical V0 execution path |
| nine lower-case block modules | canonical V0 pipeline |
| MemoryWeb, ECWFCore, MemoryECWFBridge | canonical V0 memory/wave architecture |
| Three Kings layer | canonical V0 governance architecture |
| coherence feedback and HCI integration | present and tested; later work layered into this branch |
| JSON cultivation state and scaffolding analysis | present support/research tooling added around V0 |
| March 2026 whitepaper | later research document describing results associated with this lineage |
| `verdant/` | incomplete later-generation remnant, not the V0 runtime |
| YAML configuration profiles and enhanced logging | standalone utilities not automatically integrated into `UnifiedSystem` |

## Documentation rule

The current documentation describes **what the branch contains and does now**. When historical origin matters, it explicitly says whether material is canonical V0, a later addition to V0, or an incomplete later-generation remnant.

This prevents two opposite mistakes:

- dismissing working newer additions merely because they appear on an older branch;
- claiming that every newer file or result was already part of the original V0 model.

## Source of truth

For the present branch state:

- [../README.md](../README.md) identifies the runnable system;
- [../STATUS.md](../STATUS.md) records verified behavior and limitations;
- [architecture.md](architecture.md) maps the canonical runtime;
- [../Verdant Source Codes/CONFIGURATION_AND_MONITORING.md](../Verdant%20Source%20Codes/CONFIGURATION_AND_MONITORING.md) separates integrated and standalone support tooling;
- [../paper/README.md](../paper/README.md) labels whitepaper evidence as reported rather than newly reproduced.
