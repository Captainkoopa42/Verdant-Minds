# Later temporal-scaffolding paper package

This directory is the later, self-contained V2 manuscript package.

## Contents

- `Emergent Temporal Scaffolding in a Self-Organizing Concept Graph.pdf`: rendered paper;
- `verdant_v2_paper.tex`: LaTeX source;
- `verdant_v2_plaintext.txt`: text mirror;
- `references.bib` and `verdant_v2.bib`: bibliography files;
- `figures.zip`: archived figure assets;
- `results.zip`: archived derived analysis outputs.

The paper states DOI `10.5281/zenodo.18933639` and reports the representative tracked result: 187 nodes, 17,321 edges, 62 emergent concepts, 1,830 emergent–emergent edges, timestamp-shuffle z ≈ 12.73, and degree-preserving z ≈ 11.89.

## Engineering interpretation

The paper package is a preserved research artifact, not the runtime implementation. Its directional temporal-scaffolding conclusion relies on `source` and `target` endpoint positions serialized from an undirected NetworkX graph. The graph has no causal edge direction, and reversing those endpoint labels reverses the orientation statistic without changing the graph.

The archive also does not supply the source state needed to regenerate the tracked derived outputs, and the current null-model script does not expose a deterministic RNG seed.

Read [../docs/reproducibility.md](../docs/reproducibility.md) and [../docs/whitepaper_summary.md](../docs/whitepaper_summary.md) for the cross-check. The manuscript, PDF, and archives are intentionally unchanged.
