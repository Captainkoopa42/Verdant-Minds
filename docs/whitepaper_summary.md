# V2 manuscript and evidence summary

V2 contains two manuscript layers that should not be treated as one consistent paper package.

## Earlier draft: `paper/`

The modular LaTeX draft describes a V1/V2 split and reports:

- 20-seed emergent count `6.7 ± 3.1`, range `5–14`;
- shuffle z `2.96 ± 0.86`, 20/20 above 2;
- deep-run shuffle z near `7.20` and degree-preserving z near `96`;
- 186 nodes, 17,205 edges;
- a separate 104-node/225-edge scaffold with share near `0.791`;
- Gini/access and mixture values not present in the later tracked representative JSON.

Its appendix says null randomness is controlled by explicit seeds, but the current null script has no seed option.

## Later standalone paper

`Emergent Temporal Scaffolding in a Self-Organizing Concept Graph/` contains a PDF, TeX, plaintext, bibliography, figures archive, and results archive. It reports:

- the same 20-seed `6.7 ± 3.1` panel;
- representative shuffle z `12.73` and degree-preserving z `11.89`;
- 187 nodes, 17,321 edges, 62 emergents, and 1,830 EE rows;
- three basins with 61/62 emergents concentrated in one basin;
- BIC difference near `-9,942`;
- DOI `10.5281/zenodo.18933639`.

Those representative values match the tracked `results/20260306T045715Z` derived artifacts. The 20-seed null panel is not included as per-seed null JSON.

## Current interpretation

The papers correctly identify dense graph growth, emergent-node production, basin concentration, and multiple observed age-gap scales in their recorded artifacts. Their central directed-lineage conclusion is not supported by the current representation because:

- the underlying graph is undirected;
- serialization endpoint order is mistaken for edge direction;
- 1,830 is the complete undirected edge count for 61 nodes;
- reversing endpoint labels reverses the reported temporal result;
- emergent `parent_concepts` are not what the current EE analysis measures.

The final paper itself notes that the complete structure follows timestamp-ordered creation plus exhaustive pair evaluation. The necessary correction is stronger: the measured “direction” is not stored direction at all.

## Recommended status labels

| Artifact | Recommended label |
| --- | --- |
| `paper/` | Earlier draft manuscript; numerically superseded/conflicting |
| Standalone PDF/TeX | Later archived manuscript; conclusion requires correction |
| `results/20260306T045715Z` | Representative derived outputs; source state absent |
| `results/seed_*` | Larger-run derived panel; not the paper's 5–14 panel |
| Analysis scripts | Executable exploratory tooling with direction/RNG defects |

Preserving these artifacts is valuable: they document the path by which the hypothesis was formed. Engineering documentation should not silently rewrite the manuscript, but readers must receive the validity warning before treating it as established evidence.
