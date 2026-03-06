# Verdant-Minds Whitepaper Package

This directory contains an Overleaf-ready LaTeX package plus a plain-text mirror for archival upload.

## Contents
- `main.tex` and `sections/`: manuscript source
- `references.bib`: bibliography
- `figures/`: figure output/placeholder destination
- `plain_text/paper.txt`: non-LaTeX mirror
- `build.sh`: local build helper
- `ZENODO_METADATA.md`: deposition metadata template

## Build
```bash
bash build.sh
```

The script attempts `latexmk` first, then `pdflatex+bibtex` fallback.
