# Verdant V2 core

This directory contains the active V2 cognitive system source. Its intended import name is `verdant_v2`, even though the tracked directory is named `verdant`.

## Components

| Path | Responsibility |
| --- | --- |
| `system.py` | `VerdantConfig`, `VerdantSystem`, initialization, cycle entry point, metrics, persistence hooks |
| `pipeline/` | Cognitive chunk schema, ordered processing blocks, orchestration, optional basin micro-pipelines |
| `memory/` | Undirected concept graph, activation, basin detection/state, interventions, JSON persistence |
| `governance/` | Data, Ethics, and Forefront Kings plus council arbitration |
| `thermodynamics/` | Global temperature and phase classification |

Ethomorphic wave, ethics, coherence, and emergence logic lives in [../ethomorphic](../ethomorphic).

## Pipeline order

The global pipeline runs sensory, pattern, memory, communication, reasoning, ethics, action, language, and learning blocks. Governance checkpoints occur after communication, ethics, and action. Optional basin routing runs before the global memory block and can feed basin proposals into final arbitration.

See [../docs/architecture.md](../docs/architecture.md), [../docs/walkthrough.md](../docs/walkthrough.md), and [../docs/api.md](../docs/api.md).

## Package-name defect

`pyproject.toml` declares the project `verdant_v2` and searches for `verdant_v2*` below this directory, but no such child directory exists. Active imports also use `verdant_v2.*`. An editable install can create metadata while leaving the import unavailable.

The documentation uses a temporary alias rather than renaming source during this documentation pass. Follow [../INSTALL.md](../INSTALL.md) to inspect and test the branch as it currently exists.

## Graph semantics

`MemoryWeb.graph` is a NetworkX `Graph`: associations are undirected. The `source`/`target` fields produced during serialization do not turn those associations into directed lineage. Recorded emergence parents are stored separately as node metadata.
