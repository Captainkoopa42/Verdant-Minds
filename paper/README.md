# Earlier V2 paper draft

This directory is an earlier modular LaTeX paper package. It is retained as part of the V2 research record.

## Contents

- `main.tex` and `sections/`: manuscript source;
- `plain_text/paper.txt`: text mirror;
- `references.bib`: bibliography;
- `build.sh`: local LaTeX build helper;
- `ZENODO_METADATA.md`: draft deposit metadata.

## Relationship to the later paper package

The repository also contains [../Emergent Temporal Scaffolding in a Self-Organizing Concept Graph](../Emergent%20Temporal%20Scaffolding%20in%20a%20Self-Organizing%20Concept%20Graph), a later self-contained paper package with PDF, TeX, text, figures, and result archives.

The two packages report different representative graph and null-model values. This draft includes the 20-seed `6.7 ± 3.1` emergence panel and earlier deep-run values; the later package reports the tracked representative result with 187 nodes, 17,321 edges, 62 emergents, and null z-scores of approximately 12.73 and 11.89. They should be cited by package and protocol, not blended.

## Evidence warning

Both manuscript layers interpret positional endpoints of an undirected memory graph as directed temporal edges. That direction is not represented by `MemoryWeb.graph`; it is an artifact of how an undirected edge is serialized. The tracked result directories also omit their source state, and the current null-model script has no explicit RNG seed.

The manuscripts themselves remain unchanged. Read [../docs/reproducibility.md](../docs/reproducibility.md) and [../docs/whitepaper_summary.md](../docs/whitepaper_summary.md) before treating the reported temporal-direction result as validated.
