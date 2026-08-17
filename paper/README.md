# Verdant-Minds Whitepaper Materials

**Title:** *Verdant-Minds: A Hybrid Cognitive Architecture with Graph Memory, Wave-State Dynamics, and Measurable Emergent Concept Scaffolding*

**Author:** William Adams

**Date:** March 2026
**DOI:** [10.5281/zenodo.18870656](https://doi.org/10.5281/zenodo.18870656)

## Files at this level

| Path | Purpose |
|---|---|
| `verdant_whitepaper.tex` | primary LaTeX source |
| `verdant_whitepaper.bib` | bibliography |
| `verdant_whitepaper_plaintext.txt` | plain-text/archival version |
| `Verdant_Minds__...pdf` | compiled paper |
| `figures/` | paper figures |
| `paper/` | duplicated self-contained submission bundle |

The nested directory is not a second experiment or a newer architecture. It packages the paper source, bibliography, plaintext, and PDF together for upload/transfer.

## Reported evidence

The paper reports a representative state with 119 concepts and 37 emergent nodes, an emergent-edge earlier-share of 0.807, a shuffled baseline around 0.499 ± 0.083, and approximately `z = 3.71`.

Those are **reported whitepaper results**. The documentation audit verified the code paths and branch test suite but did not recreate the original provider-driven cultivation trajectory. Anyone making a replication claim should preserve the original state, provider/model settings, mapping mode, prompts, and analysis flags.

## Compile

With a LaTeX installation:

```bash
cd paper
pdflatex verdant_whitepaper.tex
bibtex verdant_whitepaper
pdflatex verdant_whitepaper.tex
pdflatex verdant_whitepaper.tex
```

Alternatively, upload the `.tex`, `.bib`, and `figures/` directory to Overleaf and compile with pdfLaTeX.

## Relationship to the code

The paper explains the hybrid graph/wave architecture and the emergent-scaffolding analysis. The executable analyzer is `scripts/analysis/scaffolding_from_state.py`. See [../docs/reproducibility.md](../docs/reproducibility.md) before comparing a new run with the paper.
