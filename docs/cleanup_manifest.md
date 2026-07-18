# V4 Submission Cleanup Manifest

This manifest records the repository-surface cleanup performed for the V4 submission branch.
The cleanup uses archival moves rather than destructive deletion so prior research material remains reviewable.

## Retained as primary V4 surface

- `README.md` — authoritative project overview, install path, and demo command.
- `INSTALL.md` — supported local development installation path.
- `LICENSE`, `pyproject.toml`, `requirements.txt` — package metadata and dependency entry points.
- `verdant/`, `ethomorphic/`, `cultivation/` — runtime packages.
- `tests/`, `tests_v2/` — current focused and historical regression tests; `tests_v2/` is retained until it can be renamed or consolidated.
- `analysis/`, `corpus/` — validation and teaching-data assets.
- `colab/` — current V4 workflow/cells only.
- `docs/architecture.md`, `docs/api.md`, and current V4 audit docs — primary documentation surface.
- `Paper/` — current paper and selected figures.
- `Verdant_Minds_Runner_Patched (2).py` — retained but explicitly labeled experimental and outside the V4 runtime contract.

## Archived legacy material

- `archive/v2/Emergent Temporal Scaffolding in a Self-Organizing Concept Graph/` — V2 paper bundle and generated ZIP artifacts.
- `archive/v2/results_v2/` — generated V2 result outputs.
- `archive/v2/Verdant_V2_Replication.ipynb` and `archive/v2/verdant_v2_quickstart.ipynb` — V2 Colab notebooks.
- `archive/legacy/notebooks/` — older exploratory notebooks.
- `archive/legacy/scripts/` — one-off utility and experimental scripts not part of the supported V4 demo path.
- `archive/v3/results_v3/` — V3 result placeholders.
- `archive/v3/v3_*` and `archive/v3/prompts/` — V3-specific audit and prompt docs retained as research history.

## Follow-up cleanup intentionally deferred

- Rename or consolidate `tests_v2/` after confirming which tests are authoritative V4 coverage.
- Rename current paper source/PDF files once paper-version naming is finalized.
- Decide whether archived ZIP artifacts should remain in Git history or move to an external release asset store.
