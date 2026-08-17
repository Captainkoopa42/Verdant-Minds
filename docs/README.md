# Verdant-V0 Documentation Index

These documents describe the files and behavior present on the `Verdant-V0` branch. They do not silently substitute designs from later Verdant branches.

## Reading paths

For a first technical review:

1. [../README.md](../README.md) — identity, verified state, and quick start
2. [architecture.md](architecture.md) — components, boundaries, and feedback paths
3. [branch-history.md](branch-history.md) — what is original V0, later-added, or a later remnant
4. [walkthrough.md](walkthrough.md) — an input moving through the runtime
5. [api.md](api.md) — callable interfaces and scripts
6. [../STATUS.md](../STATUS.md) — limitations and engineering assessment

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

## Layered history

Verdant-V0 is the oldest presented model generation, but newer work was later added to the branch. [branch-history.md](branch-history.md) records those layers without mixing them into one false chronology.

The former root `AUDIT_REPORT.md` was removed because it combined an early audit with later status additions and contradicted the current code. Its useful historical signal is preserved in the branch-history note; current technical claims belong in `STATUS.md` and the code-grounded guides.

## Specialized documents

- [../CONTRIBUTING.md](../CONTRIBUTING.md) — V0-aligned contribution and evidence rules
- [../Verdant Source Codes/CONFIGURATION_AND_MONITORING.md](../Verdant%20Source%20Codes/CONFIGURATION_AND_MONITORING.md) — integrated versus standalone utilities
- [../VERDANT_LICENSE_APPENDIX.md](../VERDANT_LICENSE_APPENDIX.md) — non-binding ethical intent under the MIT License
