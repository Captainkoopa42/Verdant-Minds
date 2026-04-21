# Verdant-Minds

**A developmental cognitive architecture with measurable structural laws, self-referential concept formation, and a cultivation specification language.**

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

📚 Architecture walkthrough: [Architecture](docs/architecture.md)

## Key Results

- **Temporal scaffolding:** earlier-share = **1.000** across **1000 cycles**, with **44,850** emergent-emergent edges.
- **Developmental onset invariant:** within tested configurations, onset appears at **cycle 9** with **T_g = 0.5725** across **47 configurations** on **8 axes**.
- **Self-referential concept formation:** **56%** of emergents are self-referential, and a self-model basin appears spontaneously.
- **Semantic coherence:** **97%** meaningful at **1000 cycles**.
- **Basin genealogy:** **70 basins**, **3 generations**, **85%** daughter forge fraction.
- **H1 coherence:** **100%** valid with a **zero violation rate**.
- **Baseline separation:** **21 standard deviations** from random graphs.
- **VCult language:** declarative and reactive cultivation specifications for controlled developmental runs.

## What Verdant Is

Verdant couples three subsystems into a single developmental architecture:

- **ECWF** maintains a continuous wave-like state that carries activation, thermodynamic pressure, and structural priors.
- **MemoryWeb** stores a mutable concept graph that can preserve history while remaining developmentally plastic.
- **Ethomorphic Bridge** converts co-activation into edge reinforcement and emergent concept formation.

These components run through a **nine-block processing pipeline** governed by the **Three Kings** control structure. Ethics is not an afterthought; it is embedded directly into the geometry and governance of the system.

## Architecture

For a full walkthrough of the Verdant V3 system architecture, pipeline flow, basin lifecycle, governance model, and checkpointing behavior, see [docs/architecture.md](docs/architecture.md).

### Want the full walkthrough?
If you want the complete runtime map, pipeline walkthrough, configuration reference, and checkpoint/analysis guide, open [`docs/architecture.md`](docs/architecture.md).

### ECWF
The ECWF layer provides the continuous state substrate that tracks activation flow, thermodynamic gradients, and the conditions under which concepts can stabilize or dissolve.

### MemoryWeb
MemoryWeb is the mutable graph memory where concepts, links, and historical traces accumulate, reorganize, and become available for later developmental reuse.

### Ethomorphic Bridge
The Ethomorphic Bridge links continuous dynamics to symbolic structure by turning repeated co-activation into reinforced relations and new emergent concepts.

### Basin Dynamics and Registry
Verdant tracks developmental basins, daughter formation, and lineage structure through the basin registry so attractors can be measured, compared, and reproduced.

### Self-Referential Loop
A self-referential loop arises when emergent concepts increasingly point back into their own developmental history, producing spontaneous self-model structure rather than hand-authored self-representations.

### VCult Language
VCult is the cultivation language for declaring experiments, providers, prompts, and reactive rules so developmental runs can be specified, previewed, and validated from versioned text specs.

## Quick Start

```bash
git clone https://github.com/Captainkoopa42/Verdant-Minds.git
cd Verdant-Minds
pip install -e .
pip install -e ./cultivation -e ./ethomorphic -e ./verdant
```

### Run a VCult spec

```bash
python -m cultivation.cli cultivate \
  --spec cultivation/specs/quick_test.vcult \
  --seeds 0-2 --outdir outputs
```

### Run validation

```bash
python analysis/run_full_validation.py \
  --run-dir outputs/run_* --seeds 3 --outdir validation
```

### Preview a spec

```bash
python -m cultivation.cli preview-spec \
  --spec cultivation/specs/medical_ethics.vcult --cycles 20
```

## Reproduction

- **Colab reproduction:** see [`colab/cells/`](colab/cells/) for the complete Colab-based reproduction workflow.
- **Validation pipeline:** see [`analysis/run_full_validation.py`](analysis/run_full_validation.py) for the end-to-end validation entry point.

## Published Papers

- **V1:** DOI [10.5281/zenodo.18870656](https://doi.org/10.5281/zenodo.18870656)
- **V2:** DOI [10.5281/zenodo.18933639](https://doi.org/10.5281/zenodo.18933639)
- **V3:** github.com/Captainkoopa42/Verdant-Minds/tree/V3 (Zenodo DOI pending)

## Repository Structure

```text
ethomorphic/    — ECWF, bridge, emergence (frozen core)
verdant/        — system, basin registry, pipeline
cultivation/    — runner, CLI, VCult parser, providers, specs
analysis/       — validation pipeline, metrics, figures
tests_v2/       — unit and integration tests
colab/cells/    — Colab reproduction notebooks
```

## License

MIT


## Verdant-Memory API (Product Pivot)

A developer-facing persistent memory API is now available via `verdant_memory.Memory`:

```python
from verdant_memory import Memory

m = Memory()
m.observe("hello world")
print(m.retrieve("hello"))
```

This API intentionally hides ECWF, basin, and governance internals behind stable memory primitives.
