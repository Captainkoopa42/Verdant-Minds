# Ethomorphic layer

This directory supplies V2's wave-state, ethical, coherence, and concept-bridge mechanics.

## Modules

| Path | Responsibility |
| --- | --- |
| `ecwf/` | Ethical Cognitive Wave Function state and evolution |
| `ethics/` | Ethomorphic ethical evaluation |
| `coherence/` | Coherence invariants and contradiction housing metrics |
| `bridge/` | Memory mappings, input observation, and emergent-concept detection |

`VerdantSystem` constructs these components and shares the bridge and memory objects with the pipeline blocks. The emergence detector records combination inputs in `parent_concepts` metadata and adds emergent concepts to the undirected memory web.

## Packaging status

`ethomorphic/pyproject.toml` is stored inside the package directory but searches beneath that directory for packages matching `ethomorphic*`. An editable install can produce distribution metadata without making `import ethomorphic` work from an unrelated working directory.

Run from the repository root using the environment described in [../INSTALL.md](../INSTALL.md). See [../docs/architecture.md](../docs/architecture.md) and [../docs/api.md](../docs/api.md) for integration details.
