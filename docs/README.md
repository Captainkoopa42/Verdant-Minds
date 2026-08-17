# Verdant-V0 Documentation Index

These documents describe the files and behavior present on the `Verdant-V0` branch. They do not silently substitute designs from later Verdant branches.

## Reading paths

For a first technical review:

1. [../README.md](../README.md) — identity, verified state, and quick start
2. [architecture.md](architecture.md) — components, boundaries, and feedback paths
3. [walkthrough.md](walkthrough.md) — an input moving through the runtime
4. [api.md](api.md) — callable interfaces and scripts
5. [../STATUS.md](../STATUS.md) — limitations and engineering assessment

For running experiments:

1. [../INSTALL.md](../INSTALL.md)
2. [../TESTING.md](../TESTING.md)
3. [reproducibility.md](reproducibility.md)
4. [colab.md](colab.md)

## Evidence labels

The documentation uses these distinctions:

| Label | Meaning |
|---|---|
| Implemented | a code path exists in this branch |
| Tested | an automated assertion exercises the behavior |
| Audit-verified | the documentation audit executed the path successfully |
| Reported | the included whitepaper or saved material states the result; not newly reproduced by this audit |
| Simulated | generated for explanation/presentation and not produced by the canonical runtime |

This separation matters because the repository contains real execution, sample visualizations, a simulated terminal showcase, and reported experimental results.

## Branch identity

The canonical V0 route is:

```text
usm → Verdant Source Codes/src/core/system.py → lower-case src modules
```

The top-level `verdant/` directory points toward a later runtime and imports a missing `ethomorphic` dependency. Treat it as an incomplete research remnant on this branch. Upper-case module copies under `Verdant Source Codes/src/` are also preserved, while canonical imports resolve to the lower-case modules.

## Historical documents

`AUDIT_REPORT.md` is retained as a historical engineering audit. It explains the state observed when it was written, but `STATUS.md` is the branch-aligned current summary. When the two disagree, inspect the current code and tests rather than treating the older report as live configuration.
