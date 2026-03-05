# Ethomorphic AI Core

The separable core engine behind Verdant-Minds v2.

**Principle:** Ethical reasoning is geometrically embedded in cognitive
state space rather than applied as an external constraint.

## What's inside

- `ecwf/` — Extended Cognitive Wave Function engine with configurable
  dimensionality (5+5 through 64+64)
- `bridge/` — Bidirectional memory-wave translation with MemoryBackend
  protocol, emergent concept detection, and semantic mapping
- `coherence/` — Coherence invariants: HCI, triangle validity,
  alpha-critical estimation
- `ethics/` — Ethical state construction and E(t)·Ψ modulation

## Key design decisions

- **Zero dependency on Verdant.** This package can be installed and
  used independently.
- **MemoryBackend is a Protocol.** Any graph implementation that
  satisfies the protocol can plug in.
- **Configurable dimensions.** ECWF dimensionality is a constructor
  parameter, not hardcoded.
- **Sentence-transformers is optional.** Graceful fallback when not
  installed.

## Install

```bash
pip install -e ./ethomorphic
```

## Test

```bash
pytest tests_v2/unit/ -v
```

## DOI

Part of Verdant-Minds: [10.5281/zenodo.18870656](https://doi.org/10.5281/zenodo.18870656)
